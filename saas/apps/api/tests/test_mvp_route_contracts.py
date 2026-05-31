"""Static MVP API route contract checks.

These checks intentionally keep readiness/demo endpoints available while making the
MVP product-data contract explicit. They do not import FastAPI app modules, so they
remain cheap and focused on route declarations and frontend client usage.
"""

from __future__ import annotations

import ast
import re
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[4]
API_ROOT = REPO_ROOT / "saas" / "apps" / "api"
WEB_ROOT = REPO_ROOT / "saas" / "apps" / "web"

READINESS_DEMO_ROUTES = {
    ("GET", "/dashboard/summary"),
    ("GET", "/settings"),
    ("GET", "/signals"),
    ("GET", "/trades"),
}

MVP_CORE_ROUTES = {
    ("GET", "/auth/status"),
    ("POST", "/auth/register"),
    ("POST", "/auth/login"),
    ("GET", "/auth/me"),
    ("GET", "/settings/user-settings"),
    ("PUT", "/settings/user-settings"),
    ("GET", "/dashboard/stats"),
    ("GET", "/dashboard/equity-curve"),
    ("GET", "/dashboard/drawdown-curve"),
    ("GET", "/signals/latest"),
    ("GET", "/signals/by-symbol/{symbol}"),
    ("POST", "/signals/generate"),
    ("GET", "/trades/open"),
    ("GET", "/trades/closed"),
    ("POST", "/trades/open"),
    ("POST", "/trades/close/{trade_id}"),
    ("GET", "/market-data/ohlcv"),
    ("POST", "/indicators/calculate"),
}

READINESS_TAG = "Readiness / Demo"
_READINESS_LITERAL_RE = re.compile(
    r"(?P<quote>['\"])(?:/dashboard/summary|/settings|/signals|/trades)(?P=quote)"
)


def _literal_value(node: ast.AST) -> Any:
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.List):
        return [_literal_value(element) for element in node.elts]
    return None


def _router_prefixes() -> dict[str, str]:
    router_file = API_ROOT / "app" / "api" / "v1" / "api.py"
    tree = ast.parse(router_file.read_text())
    prefixes: dict[str, str] = {}
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if (
            not isinstance(node.func, ast.Attribute)
            or node.func.attr != "include_router"
        ):
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


def _route_metadata() -> dict[tuple[str, str], dict[str, Any]]:
    routes: dict[tuple[str, str], dict[str, Any]] = {}
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
                metadata = {
                    "function": node.name,
                    "docstring": ast.get_docstring(node) or "",
                    "file": endpoint_file.relative_to(REPO_ROOT).as_posix(),
                }
                for keyword in decorator.keywords:
                    metadata[keyword.arg or ""] = _literal_value(keyword.value)
                routes[(decorator.func.attr.upper(), f"{prefix}{path}")] = metadata
    return routes


def test_mvp_core_and_readiness_demo_route_sets_do_not_overlap() -> None:
    assert MVP_CORE_ROUTES.isdisjoint(READINESS_DEMO_ROUTES)


def test_mvp_core_and_readiness_demo_routes_are_declared() -> None:
    declared_routes = set(_route_metadata())

    assert MVP_CORE_ROUTES <= declared_routes
    assert READINESS_DEMO_ROUTES <= declared_routes


def test_readiness_demo_routes_are_tagged_and_documented_as_non_product_data() -> None:
    route_metadata = _route_metadata()

    for route in READINESS_DEMO_ROUTES:
        metadata = route_metadata[route]
        assert metadata["tags"] == [READINESS_TAG]
        assert "readiness" in metadata["summary"].lower()
        assert "not" in metadata["docstring"].lower()
        assert "product data endpoint" in metadata["docstring"].lower()


def test_mvp_frontend_api_clients_do_not_call_readiness_demo_routes() -> None:
    offenders: list[str] = []
    for path in (WEB_ROOT / "src" / "api").glob("*.ts"):
        if path.name.endswith(".test.ts"):
            continue
        for line_number, line in enumerate(path.read_text().splitlines(), start=1):
            if _READINESS_LITERAL_RE.search(line):
                relative_path = path.relative_to(REPO_ROOT).as_posix()
                offenders.append(f"{relative_path}:{line_number}: {line.strip()}")

    assert not offenders
