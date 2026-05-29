"""Strategy and simulation parameter metadata schemas."""

from typing import TypeAlias

from pydantic import BaseModel, Field

StrategyParameterValue: TypeAlias = str | int | float | bool | None


class StrategyParameterSpec(BaseModel):
    """Metadata describing one backend-owned strategy form parameter."""

    name: str
    group: str
    label: str
    default: StrategyParameterValue = None
    min_value: float | int | None = None
    max_value: float | int | None = None
    step: float | int | None = None
    options: list[StrategyParameterValue] = Field(default_factory=list)
    description: str = ""


__all__ = ["StrategyParameterSpec", "StrategyParameterValue"]
