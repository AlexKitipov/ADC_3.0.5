"""Broker provider factory."""

from __future__ import annotations

import os
from functools import lru_cache

from app.core.config import settings
from app.services.broker.base import BrokerClient
from app.services.broker.mock_broker import MockBrokerClient

_PROVIDER_ALIASES = {
    "mock": "mock",
    "paper": "mock",
    "demo": "mock",
}


@lru_cache
def _get_cached_broker_client(provider: str) -> BrokerClient:
    """Instantiate the configured broker client once per process."""

    if provider == "mock":
        return MockBrokerClient()

    supported = ", ".join(sorted(_PROVIDER_ALIASES))
    raise ValueError(
        f"Unsupported BROKER_PROVIDER '{provider}'. Supported providers: {supported}."
    )


def get_broker_client() -> BrokerClient:
    """Return the broker client selected by ``BROKER_PROVIDER``."""

    configured_provider = os.getenv("BROKER_PROVIDER") or settings.BROKER_PROVIDER
    provider = _PROVIDER_ALIASES.get(configured_provider.strip().lower())
    if provider is None:
        supported = ", ".join(sorted(_PROVIDER_ALIASES))
        raise ValueError(
            f"Unsupported BROKER_PROVIDER '{configured_provider}'. Supported providers: {supported}."
        )
    return _get_cached_broker_client(provider)


def reset_broker_client_cache() -> None:
    """Clear cached broker instances for tests."""

    _get_cached_broker_client.cache_clear()


__all__ = ["get_broker_client", "reset_broker_client_cache"]
