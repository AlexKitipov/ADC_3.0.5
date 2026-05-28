"""Trading signal API endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("")
def list_signals() -> dict[str, list[dict[str, str]]]:
    """Return the current trading signal collection."""

    return {"signals": []}
