"""Tests for trade journal artifact endpoints."""

from uuid import uuid4

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def register_and_login() -> str:
    suffix = uuid4().hex
    payload = {
        "email": f"journal_{suffix}@example.com",
        "username": f"journal_{suffix}",
        "password": "correct-horse-battery-staple",
    }
    assert client.post("/api/v1/auth/register", json=payload).status_code == 201
    response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["username"], "password": payload["password"]},
    )
    assert response.status_code == 200
    return response.json()["access_token"]


def auth_headers(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def test_trade_journal_import_list_get_and_export_metadata() -> None:
    token = register_and_login()
    output_dir = f"simulation_output/test_journal_{uuid4().hex}"
    csv_payload = (
        "entry_date,exit_date,type,entry_price,exit_price,size,pnl,exit_reason,balance_after\n"
        "2026-05-29,2026-05-30,BUY,100,112,1,12,take_profit,1012\n"
    )

    import_response = client.post(
        f"/api/v1/trade-journal/import?output_dir={output_dir}&artifact_type=trades",
        files={"file": ("trades.csv", csv_payload, "text/csv")},
        headers=auth_headers(token),
    )
    list_response = client.get(
        f"/api/v1/trade-journal?output_dir={output_dir}",
        headers=auth_headers(token),
    )
    entry_response = client.get(
        f"/api/v1/trade-journal/1?output_dir={output_dir}",
        headers=auth_headers(token),
    )
    export_response = client.get(
        f"/api/v1/trade-journal/export?output_dir={output_dir}",
        headers=auth_headers(token),
    )

    assert import_response.status_code == 200
    assert import_response.json()["rows_imported"] == 1
    assert list_response.status_code == 200
    assert list_response.json()["entries"][0]["pnl"] == 12.0
    assert "Broker/order records" in list_response.json()["relationships"]["broker_order_records"]
    assert entry_response.status_code == 200
    assert entry_response.json()["entry_price"] == 100.0
    assert export_response.status_code == 200
    assert export_response.json()["artifact_count"] == 1


def test_trade_journal_import_validates_artifact_extension() -> None:
    token = register_and_login()

    response = client.post(
        "/api/v1/trade-journal/import?artifact_type=performance",
        files={"file": ("performance.csv", "{}", "text/csv")},
        headers=auth_headers(token),
    )

    assert response.status_code == 422
    assert response.json()["detail"] == "performance imports require a .json file."
