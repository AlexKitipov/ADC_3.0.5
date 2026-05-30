"""Yahoo Finance market-data provider."""

from __future__ import annotations

import pandas as pd
import yfinance as yf


class YahooMarketDataProvider:
    """Fetch daily OHLCV data from Yahoo Finance via yfinance."""

    def get_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start: str | None = None,
        end: str | None = None,
    ) -> pd.DataFrame:
        """Fetch standardized daily OHLCV rows from Yahoo Finance."""

        if timeframe != "1d":
            raise ValueError(
                "Alpha Vantage API key required for intraday timeframes. "
                "Set MARKET_DATA_PROVIDER=alpha_vantage for intraday data."
            )

        try:
            data = yf.download(
                symbol,
                interval="1d",
                start=start,
                end=end,
                progress=False,
            )
        except Exception as exc:
            raise RuntimeError(
                f"Error fetching daily data for {symbol}: {exc}"
            ) from exc

        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [column[0] for column in data.columns]

        data.columns = pd.Index(
            [str(column).strip().upper() for column in data.columns]
        )
        data.columns.name = None

        if "ADJ CLOSE" in data.columns and "CLOSE" not in data.columns:
            data = data.rename(columns={"ADJ CLOSE": "CLOSE"})

        required_columns = ["OPEN", "HIGH", "LOW", "CLOSE", "VOLUME"]
        available_columns = [
            column for column in required_columns if column in data.columns
        ]
        data = data.loc[:, available_columns]
        data.columns = [column.capitalize() for column in data.columns]
        data["Symbol"] = symbol

        return data

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1d",
        start_date: str | None = None,
        end_date: str | None = None,
    ) -> pd.DataFrame:
        """Backward-compatible alias for earlier provider seam tests."""

        return self.get_ohlcv(symbol, timeframe, start_date, end_date)


__all__ = ["YahooMarketDataProvider"]
