"""Strategy metadata API endpoints."""

from fastapi import APIRouter

from app.schemas import StrategyParameterSpec
from app.services.strategy_settings import strategy_parameter_specs

router = APIRouter()


@router.get("/parameters", response_model=list[StrategyParameterSpec])
def list_strategy_parameters() -> list[dict[str, object]]:
    """Return backend-owned metadata for strategy/simulation form fields."""

    return strategy_parameter_specs()
