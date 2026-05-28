"""Authentication API endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/status")
def auth_status() -> dict[str, str]:
    """Return authentication service readiness."""

    return {"status": "auth-ready"}
