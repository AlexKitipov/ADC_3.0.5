"""Tests for stateless technical indicator API endpoint."""

from fastapi.testclient import TestClient

from app.main import app


def _ohlcv_payload(rows: int = 40) -> list[dict[str, object]]:
    return [
        {
            "timestamp": f"2026-01-{(index % 28) + 1:02d}T00:00:00",
            "symbol": "aapl",
            "open": 100 + index - 0.25,
            "high": 100 + index + 1,
            "low": 100 + index - 1,
            "close": 100 + index,
            "volume": 1000 + index,
        }
        for index in range(rows)
    ]


def test_calculate_indicators_returns_stateless_indicator_rows() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/indicators/calculate",
        json={"rows": _ohlcv_payload()},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["calculation_mode"] == "stateless"
    assert body["row_count"] == 40
    assert body["parameters"]["rsi_period"] == 14
    assert body["rows"][0]["symbol"] == "AAPL"
    assert body["rows"][-1]["close"] == 139.0
    assert body["rows"][-1]["indicators"].keys() >= {
        "rsi",
        "macd",
        "macd_signal",
        "macd_hist",
        "bollinger_upper",
        "bollinger_middle",
        "bollinger_lower",
        "atr",
        "pivot",
        "r1",
        "s1",
        "r2",
        "s2",
        "rsi_crosses",
    }


def test_calculate_indicators_accepts_custom_parameters() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/indicators/calculate",
        json={
            "rows": _ohlcv_payload(8),
            "parameters": {
                "rsi_period": 3,
                "macd_fast": 3,
                "macd_slow": 5,
                "macd_signal": 2,
                "bollinger_period": 3,
                "bollinger_std": 1.5,
                "atr_period": 3,
            },
        },
    )

    assert response.status_code == 200
    assert response.json()["parameters"] == {
        "rsi_period": 3,
        "macd_fast": 3,
        "macd_slow": 5,
        "macd_signal": 2,
        "bollinger_period": 3,
        "bollinger_std": 1.5,
        "atr_period": 3,
    }


def test_calculate_indicators_rejects_invalid_macd_windows() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/indicators/calculate",
        json={
            "rows": _ohlcv_payload(40),
            "parameters": {"macd_fast": 12, "macd_slow": 12},
        },
    )

    assert response.status_code == 422
    assert "macd_fast must be less than macd_slow" in response.text


def test_calculate_indicators_rejects_too_few_rows_for_requested_windows() -> None:
    client = TestClient(app)

    response = client.post(
        "/api/v1/indicators/calculate",
        json={"rows": _ohlcv_payload(3)},
    )

    assert response.status_code == 422
    assert "at least 26 OHLCV rows are required" in response.text
