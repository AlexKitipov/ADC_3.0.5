"""Trade API endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_trades() -> dict[str, list[dict[str, str]]]:
    """Return the current trade collection."""

    return {"trades": []}
