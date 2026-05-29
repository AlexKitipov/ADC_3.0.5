"""Authentication and account schemas for the ADC Trading Platform API."""

from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr


class UserCreate(BaseModel):
    """Payload for registering a user account."""

    email: EmailStr
    username: str
    password: str


class User(BaseModel):
    """Public user response."""

    id: int
    email: str
    username: str
    is_active: bool
    created_at: datetime

    model_config = ConfigDict(from_attributes=True)


class Token(BaseModel):
    """JWT bearer token response."""

    access_token: str
    token_type: str


__all__ = ["Token", "User", "UserCreate"]
