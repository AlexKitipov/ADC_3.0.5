"""Focused manual order endpoint tests.

The canonical authenticated trading endpoint module also covers these cases;
this file keeps the order-specific pytest selection stable for broker PRs.
"""

from tests.test_trading_endpoints import (  # noqa: F401
    test_manual_order_lifecycle_is_user_scoped_and_not_persisted_trade,
    test_manual_order_validation_and_broker_errors_are_consistent,
)
