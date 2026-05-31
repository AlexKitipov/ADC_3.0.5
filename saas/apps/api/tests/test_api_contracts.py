"""Static API contract tests for backend/frontend integration.

These tests intentionally use only the Python standard library so they can run
before optional FastAPI dependencies are installed. They guard the route family,
canonical base path, frontend client paths, and documentation coverage.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = REPO_ROOT / "saas" / "apps" / "api"
WEB_ROOT = REPO_ROOT / "saas" / "apps" / "web"
DOCS_ROOT = REPO_ROOT / "saas" / "docs" / "api"

EXPECTED_BASE_PATH = "/api/v1"

EXPECTED_BACKEND_ROUTES = {
    ("GET", "/auth/status"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("GET", "/dashboard/summary"),
    ("GET", "/dashboard/stats"),
    ("GET", "/dashboard/equity-curve"),
    ("GET", "/dashboard/drawdown-curve"),
    ("GET", "/settings"),
    ("GET", "/settings/user-settings"),
    ("PUT", "/settings/user-settings"),
    ("GET", "/signals"),
    ("POST", "/signals/create"),
    ("POST", "/signals/generate"),
    ("GET", "/signals/latest"),
    ("GET", "/signals/by-symbol/{symbol}"),
    ("GET", "/trades"),
    ("POST", "/trades/open"),
    ("POST", "/trades/close/{trade_id}"),
    ("GET", "/trades/open"),
    ("GET", "/trades/closed"),
    ("GET", "/strategy/parameters"),
    ("POST", "/simulations"),
    ("GET", "/simulations/{simulation_id}"),
    ("GET", "/simulations/{simulation_id}/artifacts"),
    ("GET", "/market-data/ohlcv"),
    ("POST", "/indicators/calculate"),
    ("POST", "/rl/train"),
    ("GET", "/rl/jobs/{job_id}"),
    ("GET", "/rl/models/{model_id}"),
    ("POST", "/lstm/train"),
    ("POST", "/lstm/generate"),
    ("GET", "/lstm/jobs/{job_id}"),
    ("POST", "/orders"),
    ("GET", "/orders/open"),
    ("GET", "/orders/{ticket}"),
    ("POST", "/orders/{ticket}/close"),
    ("POST", "/sessions"),
    ("GET", "/sessions/current"),
    ("POST", "/sessions/{session_id}/start"),
    ("POST", "/sessions/{session_id}/stop"),
    ("GET", "/sessions/{session_id}/events"),
    ("GET", "/market-stream/{symbol}"),
    ("POST", "/notifications/test"),
    ("POST", "/notifications/simulation-results"),
    ("GET", "/trade-journal"),
    ("GET", "/trade-journal/{entry_id}"),
    ("POST", "/trade-journal/import"),
    ("GET", "/trade-journal/export"),
}

FRONTEND_CONSUMED_BACKEND_ROUTES = {
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("GET", "/dashboard/stats"),
    ("GET", "/dashboard/equity-curve"),
    ("GET", "/dashboard/drawdown-curve"),
    ("GET", "/settings/user-settings"),
    ("PUT", "/settings/user-settings"),
    ("GET", "/signals/latest"),
    ("GET", "/signals/by-symbol/{symbol}"),
    ("POST", "/trades/open"),
    ("POST", "/trades/close/{trade_id}"),
    ("GET", "/trades/open"),
    ("GET", "/trades/closed"),
    ("GET", "/strategy/parameters"),
    ("POST", "/simulations"),
    ("GET", "/simulations/{simulation_id}"),
    ("GET", "/simulations/{simulation_id}/artifacts"),
    ("GET", "/market-data/ohlcv"),
    ("POST", "/indicators/calculate"),
    ("POST", "/rl/train"),
    ("GET", "/rl/jobs/{job_id}"),
    ("GET", "/rl/models/{model_id}"),
    ("POST", "/lstm/train"),
    ("POST", "/lstm/generate"),
    ("GET", "/lstm/jobs/{job_id}"),
    ("POST", "/orders"),
    ("GET", "/orders/open"),
    ("GET", "/orders/{ticket}"),
    ("POST", "/orders/{ticket}/close"),
    ("POST", "/sessions"),
    ("GET", "/sessions/current"),
    ("POST", "/sessions/{session_id}/start"),
    ("POST", "/sessions/{session_id}/stop"),
    ("GET", "/sessions/{session_id}/events"),
    ("GET", "/market-stream/{symbol}"),
    ("POST", "/notifications/test"),
    ("POST", "/notifications/simulation-results"),
    ("GET", "/trade-journal"),
    ("GET", "/trade-journal/{entry_id}"),
    ("POST", "/trade-journal/import"),
    ("GET", "/trade-journal/export"),
}

DOCUMENTED_FAMILIES = {
    "auth",
    "dashboard",
    "settings",
    "signals",
    "trades",
    "strategy parameters",
    "simulation",
    "market data",
    "indicators",
    "rl",
    "lstm",
    "orders",
    "sessions",
    "market stream",
    "notifications",
    "trade journal",
}


def _router_prefixes() -> dict[str, str]:
    router_file = API_ROOT / "app" / "api" / "v1" / "api.py"
    tree = ast.parse(router_file.read_text())
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Attribute) or node.func.attr != "include_router":
            continue
        if not node.args or not isinstance(node.args[0], ast.Attribute):
            continue
        module_name = node.args[0].value.id
        prefix = ""
        for keyword in node.keywords:
            if keyword.arg == "prefix" and isinstance(keyword.value, ast.Constant):
                prefix = keyword.value.value
        prefixes[module_name] = prefix
    return prefixes


def _backend_routes() -> set[tuple[str, str]]:
    routes: set[tuple[str, str]] = set()
    prefixes = _router_prefixes()
    endpoints_dir = API_ROOT / "app" / "api" / "v1" / "endpoints"
    for endpoint_file in endpoints_dir.glob("*.py"):
        if endpoint_file.name == "__init__.py":
            continue
        prefix = prefixes[endpoint_file.stem]
        tree = ast.parse(endpoint_file.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            for decorator in node.decorator_list:
                if not isinstance(decorator, ast.Call):
                    continue
                if not isinstance(decorator.func, ast.Attribute):
                    continue
                if decorator.func.attr not in {"get", "post", "put", "patch", "delete"}:
                    continue
                path = ""
                if decorator.args and isinstance(decorator.args[0], ast.Constant):
                    path = decorator.args[0].value
                routes.add((decorator.func.attr.upper(), f"{prefix}{path}"))
    return routes


def test_backend_contract_route_set_is_explicit_and_stable() -> None:
    assert _backend_routes() == EXPECTED_BACKEND_ROUTES


def test_frontend_consumed_routes_exist_in_backend_contract() -> None:
    backend_routes = _backend_routes()
    missing = FRONTEND_CONSUMED_BACKEND_ROUTES - backend_routes
    assert not missing


def test_canonical_base_path_is_documented_and_used_by_clients() -> None:
    main_text = (API_ROOT / "app" / "main.py").read_text()
    web_client_text = (WEB_ROOT / "src" / "api" / "client.ts").read_text()
    market_stream_text = (WEB_ROOT / "src" / "api" / "marketStream.ts").read_text()
    docs_text = (DOCS_ROOT / "README.md").read_text()

    assert f'prefix="{EXPECTED_BASE_PATH}"' in main_text
    assert f"http://localhost:8000{EXPECTED_BASE_PATH}" in web_client_text
    assert f"http://localhost:8000{EXPECTED_BASE_PATH}" in market_stream_text
    assert EXPECTED_BASE_PATH in docs_text


def test_api_documentation_covers_all_endpoint_families_and_auth() -> None:
    docs_text = (DOCS_ROOT / "README.md").read_text().lower()
    backend_readme_text = (API_ROOT / "README.md").read_text().lower()
    missing_families = [family for family in DOCUMENTED_FAMILIES if family not in docs_text]

    assert not missing_families
    assert "authorization: bearer" in docs_text
    assert "oauth2passwordbearer" in docs_text
    assert "contract" in docs_text
    assert "contract" in backend_readme_text


def test_frontend_path_templates_stay_inside_versioned_api_namespace() -> None:
    client_text = (WEB_ROOT / "src" / "api" / "client.ts").read_text()
    assert re.search(r"VITE_API_URL \?\? ['\"]http://localhost:8000/api/v1['\"]", client_text)

    for path in (WEB_ROOT / "src" / "api").glob("*.ts"):
        if path.name.endswith(".test.ts"):
            continue
        text = path.read_text()
        assert "http://localhost:8000/api/" not in text.replace(
            "http://localhost:8000/api/v1", ""
        )
