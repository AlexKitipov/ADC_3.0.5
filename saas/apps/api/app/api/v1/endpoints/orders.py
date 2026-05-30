"""Manual broker order API endpoints."""

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, status

from app.models import User
from app.schemas.orders import BrokerResult, Order, OrderClose, OrderCreate, OrderType
from app.security import get_current_user
from app.services.broker.base import BrokerClient
from app.services.broker.providers import get_broker_client
from app.services.order_management import (
    ERR_BROKER_BUSY,
    ERR_CLOSE_TIMEOUT,
    ERR_COMMON_ERROR,
    ERR_INVALID_PRICE,
    ERR_INVALID_STOPS,
    ERR_INVALID_TICKET,
    ERR_MALFUNCTIONAL_TRADE,
    ERR_NO_CONNECTION,
    ERR_NOT_ENOUGH_MONEY,
    ERR_OFF_QUOTES,
    ERR_ORDER_EXPIRED,
    ERR_PRICE_CHANGED,
    ERR_REQUOTE,
    ERR_SERVER_BUSY,
    ERR_TRADE_CONTEXT_BUSY,
    ERR_TRADE_DISABLED,
    OP_BUY,
    OP_BUYLIMIT,
    OP_BUYSTOP,
    OP_SELL,
    OP_SELLLIMIT,
    OP_SELLSTOP,
)

router = APIRouter()

_ORDER_TYPE_TO_CMD = {
    OrderType.BUY: OP_BUY,
    OrderType.SELL: OP_SELL,
    OrderType.BUYSTOP: OP_BUYSTOP,
    OrderType.SELLSTOP: OP_SELLSTOP,
    OrderType.BUYLIMIT: OP_BUYLIMIT,
    OrderType.SELLLIMIT: OP_SELLLIMIT,
}
_CMD_TO_ORDER_TYPE = {
    command: order_type for order_type, command in _ORDER_TYPE_TO_CMD.items()
}

# Manual broker orders remain separate from persisted Trade rows. Ownership is
# tracked in process so authenticated users only see orders submitted through
# their own session while broker state remains non-durable.
_order_owners: dict[int, int] = {}

_ERROR_STATUS = {
    ERR_NO_CONNECTION: status.HTTP_503_SERVICE_UNAVAILABLE,
    ERR_TRADE_CONTEXT_BUSY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ERR_SERVER_BUSY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ERR_BROKER_BUSY: status.HTTP_503_SERVICE_UNAVAILABLE,
    ERR_TRADE_DISABLED: status.HTTP_403_FORBIDDEN,
    ERR_INVALID_STOPS: status.HTTP_422_UNPROCESSABLE_ENTITY,
    ERR_INVALID_PRICE: status.HTTP_409_CONFLICT,
    ERR_PRICE_CHANGED: status.HTTP_409_CONFLICT,
    ERR_OFF_QUOTES: status.HTTP_409_CONFLICT,
    ERR_REQUOTE: status.HTTP_409_CONFLICT,
    ERR_NOT_ENOUGH_MONEY: status.HTTP_409_CONFLICT,
    ERR_INVALID_TICKET: status.HTTP_404_NOT_FOUND,
    ERR_ORDER_EXPIRED: status.HTTP_409_CONFLICT,
    ERR_CLOSE_TIMEOUT: status.HTTP_504_GATEWAY_TIMEOUT,
    ERR_MALFUNCTIONAL_TRADE: status.HTTP_502_BAD_GATEWAY,
    ERR_COMMON_ERROR: status.HTTP_502_BAD_GATEWAY,
}

_ERROR_MESSAGES = {
    ERR_NO_CONNECTION: "Broker connection is unavailable.",
    ERR_TRADE_CONTEXT_BUSY: "Trade context is busy; retry the request.",
    ERR_SERVER_BUSY: "Broker server is busy; retry the request.",
    ERR_BROKER_BUSY: "Broker is busy; retry the request.",
    ERR_TRADE_DISABLED: "Trading is disabled for the broker.",
    ERR_INVALID_STOPS: "Stop loss or take profit violates broker stop-level rules.",
    ERR_INVALID_PRICE: "Order price is invalid for current market conditions.",
    ERR_PRICE_CHANGED: "Market price changed before execution.",
    ERR_OFF_QUOTES: "Broker returned off quotes.",
    ERR_REQUOTE: "Broker requoted the order price.",
    ERR_NOT_ENOUGH_MONEY: "Broker rejected the order for insufficient funds.",
    ERR_INVALID_TICKET: "Order ticket was not found.",
    ERR_ORDER_EXPIRED: "Order expired before execution.",
    ERR_CLOSE_TIMEOUT: "Timed out while closing the order.",
    ERR_MALFUNCTIONAL_TRADE: "Broker reported a malfunctional trade operation.",
    ERR_COMMON_ERROR: "Broker rejected the order.",
}


def _broker_exception(error_code: int, fallback: str) -> HTTPException:
    """Convert a broker error code into a consistent HTTP error."""

    detail = {
        "status": "rejected",
        "error_code": error_code,
        "message": _ERROR_MESSAGES.get(error_code, fallback),
    }
    return HTTPException(
        status_code=_ERROR_STATUS.get(error_code, status.HTTP_502_BAD_GATEWAY),
        detail=detail,
    )


def _owned_order(
    ticket: int, user_id: int, broker_client: BrokerClient
) -> dict[str, Any]:
    """Return an order if it belongs to the user, otherwise raise 404."""

    order = broker_client.get_order(ticket)
    if order is None or _order_owners.get(ticket) != user_id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail={
                "status": "not_found",
                "error_code": ERR_INVALID_TICKET,
                "message": "Order not found.",
            },
        )
    return order


def _serialize_order(
    order: dict[str, Any],
    *,
    slippage: int | None = None,
    message: str = "Order loaded."
) -> Order:
    """Serialize a broker order dictionary to the public response model."""

    return Order(
        ticket=order["ticket"],
        symbol=order["symbol"],
        order_type=_CMD_TO_ORDER_TYPE[order["cmd"]],
        volume=order["volume"],
        price=order["open_price"],
        stop_loss=order["sl"],
        take_profit=order["tp"],
        slippage=slippage,
        status=order["status"],
        broker_result=BrokerResult(
            status=order["status"], error_code=0, message=message
        ),
        open_time=order["open_time"],
        close_price=order.get("close_price"),
        close_time=order.get("close_time"),
    )


@router.post("", response_model=Order, status_code=status.HTTP_201_CREATED)
def create_order(
    order: OrderCreate,
    current_user: User = Depends(get_current_user),
    broker_client: BrokerClient = Depends(get_broker_client),
) -> Order:
    """Submit a manual broker order without persisting a Trade row."""

    broker_order = broker_client.place_order(order)
    ticket = broker_order.get("ticket", -1)
    if ticket == -1:
        raise _broker_exception(broker_client.get_last_error(), "Order was rejected.")

    _order_owners[ticket] = current_user.id
    return _serialize_order(
        broker_order, slippage=order.slippage, message="Order accepted by broker."
    )


@router.post("/{ticket}/close", response_model=Order)
def close_order(
    ticket: int,
    order_close: OrderClose,
    current_user: User = Depends(get_current_user),
    broker_client: BrokerClient = Depends(get_broker_client),
) -> Order:
    """Close an authenticated user's manual broker order."""

    broker_order = _owned_order(ticket, current_user.id, broker_client)
    if broker_order["status"] != "open":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail={
                "status": "closed",
                "error_code": ERR_INVALID_TICKET,
                "message": "Order is already closed.",
            },
        )

    closed_order = broker_client.close_order(ticket, order_close)
    if closed_order.get("status") != "closed":
        raise _broker_exception(
            broker_client.get_last_error(), "Order close was rejected."
        )

    return _serialize_order(
        closed_order,
        slippage=order_close.slippage,
        message="Order closed by broker.",
    )


@router.get("/open", response_model=list[Order])
def get_open_orders(
    current_user: User = Depends(get_current_user),
    broker_client: BrokerClient = Depends(get_broker_client),
) -> list[Order]:
    """Return currently open manual broker orders for the authenticated user."""

    return [
        _serialize_order(order)
        for order in broker_client.get_open_orders()
        if _order_owners.get(order["ticket"]) == current_user.id
    ]


@router.get("/{ticket}", response_model=Order)
def get_order(
    ticket: int,
    current_user: User = Depends(get_current_user),
    broker_client: BrokerClient = Depends(get_broker_client),
) -> Order:
    """Return one manual broker order for the authenticated user."""

    return _serialize_order(_owned_order(ticket, current_user.id, broker_client))
