"""Tests for the end-to-end simulation runner."""

from pathlib import Path

import numpy as np
import pandas as pd

from app.services.simulation_runner import SimulationParameters, SimulationRunner


class StaticDataLoader:
    """Return deterministic OHLCV data without network access."""

    def __init__(self, data: pd.DataFrame) -> None:
        self.data = data
        self.calls: list[tuple[str, str, str | None, str | None]] = []

    def fetch_data(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        self.calls.append((symbol, timeframe, start_date, end_date))
        return self.data.copy()


def build_ohlcv(rows: int = 90) -> pd.DataFrame:
    index = pd.date_range("2024-01-01", periods=rows, freq="D")
    close = np.linspace(100.0, 118.0, rows) + np.sin(np.arange(rows) / 3) * 0.5
    open_ = close - 0.2
    high = close + 0.8
    low = close - 0.8
    volume = np.linspace(1_000, 2_000, rows)
    return pd.DataFrame(
        {
            "Open": open_,
            "High": high,
            "Low": low,
            "Close": close,
            "Volume": volume,
        },
        index=index,
    )


def test_parameters_accept_readme_aliases_and_ignore_unknown_keys() -> None:
    params = SimulationParameters.from_mapping(
        {"ppo_total_timesteps": 123, "base_path": "out", "ignored": "value"}
    )

    assert params.rl_total_timesteps == 123
    assert params.output_dir == "out"


def test_runner_persists_outputs_without_heavy_training(tmp_path: Path) -> None:
    data_loader = StaticDataLoader(build_ohlcv())
    runner = SimulationRunner(data_loader=data_loader)

    result = runner.run(
        {
            "symbol": "TEST",
            "output_dir": str(tmp_path),
            "train_lstm": False,
            "train_rl": False,
            "save_charts": False,
            "sequence_length": 10,
        }
    )

    assert data_loader.calls == [("TEST", "1d", None, None)]
    assert result.trained_lstm is False
    assert result.trained_rl is False
    assert result.total_steps > 0
    assert Path(result.historical_data_path).exists()
    assert Path(result.generated_data_path).exists()
    assert Path(result.orders_path).exists()
    assert Path(result.trades_path).exists()
    assert Path(result.rewards_path).exists()
    assert Path(result.performance_path).exists()
    assert Path(result.equity_curve_path).exists()
    assert Path(result.drawdown_path).exists()
    assert result.performance["symbol"] == "TEST"
    assert result.performance["total_trades"] >= 0

    historical = pd.read_csv(result.historical_data_path)
    generated = pd.read_csv(result.generated_data_path)
    for column in ["Pivot", "R1", "S1", "R2", "S2", "RSI_Cross_Count"]:
        assert column in historical.columns
        assert column in generated.columns
