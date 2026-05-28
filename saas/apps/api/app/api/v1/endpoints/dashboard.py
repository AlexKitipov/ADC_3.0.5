"""Dashboard API endpoints."""

from fastapi import APIRouter

router = APIRouter()


@router.get("/summary")
def dashboard_summary() -> dict[str, str]:
    """Return a placeholder dashboard summary response."""

    return {"status": "dashboard-ready"}
