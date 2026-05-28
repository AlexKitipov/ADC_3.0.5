# ADC_3.0.5
„Архив и експериментална платформа за форекс стратегия. Съдържа генерирани данни, исторически записи, дневник на сделки, графики за equity и drawdown, JSON метрики за награди. Проектът е принципен вариант, който може да се развива и подобрява.“

import yfinance as yf
import pandas as pd
import numpy as np
import os
import matplotlib.pyplot as plt
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import random
import time
import threading

# Install ta if not already installed
try:
    from ta.momentum import RSIIndicator
    from ta.trend import MACD
    from ta.volatility import BollingerBands, AverageTrueRange
except ImportError:
    !pip install ta
    from ta.momentum import RSIIndicator
    from ta.trend import MACD
    from ta.volatility import BollingerBands, AverageTrueRange

# Install stable_baselines3 if not already installed
try:
    from stable_baselines3 import PPO, DQN, A2C, SAC
    from stable_baselines3.common.vec_env import DummyVecEnv
    from gymnasium import Env
    from gymnasium.spaces import Discrete, Box
except ImportError:
    !pip install stable-baselines3 gymnasium
    from stable_baselines3 import PPO, DQN, A2C, SAC
    from stable_baselines3.common.vec_env import DummyVecEnv
    from gymnasium import Env
    from gymnasium.spaces import Discrete, Box

from google.colab import drive
import json
import uuid
import ipywidgets as widgets
from IPython.display import display, HTML, clear_output
from datetime import datetime, timedelta

# --- MQL4-like Order Types ---
OP_BUY = 0
OP_SELL = 1
OP_BUYSTOP = 2
OP_SELLSTOP = 3
OP_BUYLIMIT = 4
OP_SELLLIMIT = 5

# --- MQL4-like Error Codes ---
ERR_NO_ERROR = 0
ERR_COMMON_ERROR = 1
ERR_NO_CONNECTION = 2
ERR_INVALID_TRADE_PARAMETERS = 3
ERR_SERVER_BUSY = 4
ERR_OLD_VERSION = 5
ERR_NO_CHANGES = 6
ERR_TRADE_CONTEXT_BUSY = 129
ERR_PRICE_CHANGED = 130
ERR_OFF_QUOTES = 131
ERR_INVALID_STOPS = 132
ERR_TRADE_DISABLED = 133
ERR_NOT_ENOUGH_MONEY = 134
ERR_MARKET_CLOSED = 135
ERR_LOCK_TIMEOUT = 136
ERR_ORDER_EXPIRED = 137
ERR_REQUOTE = 138
ERR_BROKER_BUSY = 139
ERR_INVALID_TICKET = 140
ERR_MALFUNCTIONAL_TRADE = 141
ERR_TOO_MANY_REQUESTS = 142
ERR_INVALID_PRICE = 146
ERR_CLOSE_TIMEOUT = 147

# --- Custom Exception Classes ---
class OrderError(Exception):
    """Base exception for order-related errors."""
    pass

class BrokerConnectionError(OrderError):
    """Exception for broker connection issues."""
    pass

class TradeContextBusyError(OrderError):
    """Exception when the trade context is busy."""
    pass

class InvalidPriceError(OrderError):
    """Exception for invalid or changed prices."""
    pass

class InvalidStopLossError(OrderError):
    """Exception when stop loss/take profit levels are too close to market."""
    pass

class TradeRejectedError(OrderError):
    """Exception for general trade rejections by the broker/server."""
    pass

class MalfunctionalTradeError(OrderError):
    """Exception for malfunctional trade operations."""
    pass

class WebSocketError(Exception):
    """Base exception for WebSocket-related errors."""
    pass

# Map error codes to custom exception classes for easier handling
ERROR_MAP = {
    ERR_NO_CONNECTION: BrokerConnectionError,
    ERR_TRADE_CONTEXT_BUSY: TradeContextBusyError,
    ERR_INVALID_PRICE: InvalidPriceError,
    ERR_OFF_QUOTES: InvalidPriceError,
    ERR_REQUOTE: InvalidPriceError,
    ERR_PRICE_CHANGED: InvalidPriceError,
    ERR_INVALID_STOPS: InvalidStopLossError,
    ERR_BROKER_BUSY: TradeContextBusyError,
    ERR_MALFUNCTIONAL_TRADE: MalfunctionalTradeError,
    ERR_INVALID_TICKET: TradeRejectedError,
    ERR_ORDER_EXPIRED: TradeRejectedError,
    ERR_CLOSE_TIMEOUT: TradeRejectedError
}

# --- Helper Functions ---
def _normalize_double_helper(value: float, digits: int) -> float:
    """Replicates MQL4's NormalizeDouble function to round a float to a specified number of decimal places."""
    return round(value, digits)

def exponential_backoff_sleep(mean_time: float, max_time: float):
    """Simulates MQL4's OrderReliable_SleepRandomTime with exponential backoff."""
    if mean_time <= 0:
        return
    base_sleep = random.uniform(0.5, 1.5) * mean_time
    sleep_duration = min(base_sleep, max_time)
    time.sleep(sleep_duration)

def ensure_valid_stop_level(symbol: str, price: float, stop_level: float, is_buy_order: bool, market_info: dict) -> float:
    """Adjusts stop loss/take profit levels to ensure they are legal according to broker rules.
    Replicates MQL4's OrderReliable_EnsureValidStop.

    market_info should contain 'MODE_STOPLEVEL' and 'MODE_POINT'.
    """
    if stop_level == 0:
        return 0.0

    # Default values for common forex symbols; a real API would provide these
    mode_stoplevel = market_info.get('MODE_STOPLEVEL', 20) # 20 points
    mode_point = market_info.get('MODE_POINT', 0.00001) # For 5-digit brokers, 0.00001 per point
    digits = market_info.get('MODE_DIGITS', 5)

    servers_min_stop = mode_stoplevel * mode_point

    if servers_min_stop <= 0: # If broker has no minimum stop level
        return stop_level

    # Check if the desired stop_level is too close to the current price
    if abs(price - stop_level) < servers_min_stop:
        # Adjust SL to be exactly servers_min_stop away from price, in the correct direction
        if is_buy_order: # For buy order, SL must be below price
            # If stop_level was originally below price, keep it below but ensure min distance
            if stop_level < price:
                stop_level = price - servers_min_stop
            # If stop_level was above price (invalid for SL on buy), default to min distance below
            else:
                stop_level = price - servers_min_stop
        else: # For sell order, SL must be above price
            # If stop_level was originally above price, keep it above but ensure min distance
            if stop_level > price:
                stop_level = price + servers_min_stop
            # If stop_level was below price (invalid for SL on sell), default to min distance above
            else:
                stop_level = price + servers_min_stop

        stop_level = _normalize_double_helper(stop_level, digits)

    return stop_level

# --- New: normalize_price function ---
def normalize_price(symbol: str, value: float, broker_api) -> float:
    market_info = broker_api.get_market_info(symbol)
    digits = market_info.get('MODE_DIGITS', 5)
    return _normalize_double_helper(value, digits)

# --- MockBrokerAPI Class Definition (based on comprehensive analysis) ---
class MockBrokerAPI:
    def __init__(self, error_rate=0.0):
        self._trade_allowed = False
        self._open_orders = {}
        self._next_ticket = 100000
        self._market_data = {
            "EURUSD": {"bid": 1.08500, "ask": 1.08510, "MODE_POINT": 0.00001, "MODE_STOPLEVEL": 20, "MODE_DIGITS": 5},
            "TSLA": {"bid": 200.00, "ask": 200.10, "MODE_POINT": 0.01, "MODE_STOPLEVEL": 1, "MODE_DIGITS": 2}
        }
        self.error_rate = error_rate

    def get_market_info(self, symbol: str) -> dict:
        self.refresh_rates(symbol)
        return self._market_data.get(symbol, {"bid": 0.0, "ask": 0.0, "MODE_POINT": 0.00001, "MODE_STOPLEVEL": 20, "MODE_DIGITS": 5})

    def is_trade_allowed(self) -> bool:
        return self._trade_allowed

    def refresh_rates(self, symbol: str):
        # Simulate minor price fluctuations for more dynamic testing
        if symbol in self._market_data:
            data = self._market_data[symbol]
            digits = data.get('MODE_DIGITS', 5)
            fluctuation = random.uniform(-0.0001, 0.0001) if digits == 5 else random.uniform(-0.01, 0.01)
            data["bid"] = _normalize_double_helper(data["bid"] + fluctuation, digits)
            data["ask"] = _normalize_double_helper(data["ask"] + fluctuation, digits)
            # Ensure ask > bid
            if data["ask"] <= data["bid"]:
                data["ask"] = _normalize_double_helper(data["bid"] + data["MODE_POINT"], digits)

    def send_order(self, symbol: str, cmd: int, volume: float, price: float, slippage: int, stoploss: float, takeprofit: float, comment: str, magic: int) -> int:
        if not self._trade_allowed:
            return -1 # Simulate trade disabled

        if random.random() < self.error_rate:
            self._last_error = random.choice([ERR_COMMON_ERROR, ERR_SERVER_BUSY, ERR_PRICE_CHANGED, ERR_INVALID_TRADE_PARAMETERS])
            return -1

        market_info = self.get_market_info(symbol)
        digits = market_info.get('MODE_DIGITS', 5)
        point = market_info.get('MODE_POINT', 0.00001)

        # Simulate slippage
        actual_price = price
        if cmd == OP_BUY or cmd == OP_BUYLIMIT or cmd == OP_BUYSTOP:
            # For Buy orders, slippage adjusts entry price upwards or is met
            if actual_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_REQUOTE # Price moved too much
                return -1
            actual_price = _normalize_double_helper(max(actual_price, market_info["ask"] - slippage * point), digits)
        elif cmd == OP_SELL or cmd == OP_SELLLIMIT or cmd == OP_SELLSTOP:
            # For Sell orders, slippage adjusts entry price downwards or is met
            if actual_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_REQUOTE # Price moved too much
                return -1
            actual_price = _normalize_double_helper(min(actual_price, market_info["bid"] + slippage * point), digits)

        # Basic stop level validation
        is_buy = (cmd == OP_BUY or cmd == OP_BUYLIMIT or cmd == OP_BUYSTOP)
        stoploss = ensure_valid_stop_level(symbol, actual_price, stoploss, is_buy, market_info)
        takeprofit = ensure_valid_stop_level(symbol, actual_price, takeprofit, is_buy, market_info)

        if (stoploss != 0 and is_buy and stoploss >= actual_price) or \
           (stoploss != 0 and not is_buy and stoploss <= actual_price):
            self._last_error = ERR_INVALID_STOPS
            return -1
        if (takeprofit != 0 and is_buy and takeprofit <= actual_price) or \
           (takeprofit != 0 and not is_buy and takeprofit >= actual_price):
            self._last_error = ERR_INVALID_STOPS
            return -1

        ticket = self._next_ticket
        self._next_ticket += 1
        self._open_orders[ticket] = {
            "ticket": ticket,
            "symbol": symbol,
            "cmd": cmd,
            "volume": volume,
            "open_price": actual_price,
            "sl": stoploss,
            "tp": takeprofit,
            "comment": comment,
            "magic": magic,
            "open_time": datetime.now(),
            "status": "open"
        }
        self._last_error = ERR_NO_ERROR
        return ticket

    def close_order(self, ticket: int, volume: float, close_price: float, slippage: int) -> bool:
        if random.random() < self.error_rate:
            self._last_error = random.choice([ERR_COMMON_ERROR, ERR_SERVER_BUSY, ERR_PRICE_CHANGED, ERR_MALFUNCTIONAL_TRADE])
            return False

        if ticket not in self._open_orders or self._open_orders[ticket]["status"] != "open":
            self._last_error = ERR_INVALID_TICKET
            return False

        order = self._open_orders[ticket]
        market_info = self.get_market_info(order["symbol"])
        digits = market_info.get('MODE_DIGITS', 5)
        point = market_info.get('MODE_POINT', 0.00001)

        # Simulate slippage on close
        actual_close_price = close_price
        if order["cmd"] == OP_BUY or order["cmd"] == OP_BUYLIMIT or order["cmd"] == OP_BUYSTOP:
            # Closing a buy, so we sell at bid (or slightly below with slippage)
            if actual_close_price > market_info["bid"] + slippage * point:
                self._last_error = ERR_PRICE_CHANGED # Price moved too much
                return False
            actual_close_price = _normalize_double_helper(min(actual_close_price, market_info["bid"] + slippage * point), digits)
        elif order["cmd"] == OP_SELL or order["cmd"] == OP_SELLLIMIT or order["cmd"] == OP_SELLSTOP:
            # Closing a sell, so we buy at ask (or slightly above with slippage)
            if actual_close_price < market_info["ask"] - slippage * point:
                self._last_error = ERR_PRICE_CHANGED # Price moved too much
                return False
            actual_close_price = _normalize_double_helper(max(actual_close_price, market_info["ask"] + slippage * point), digits)

        # Update order status to closed
        order["close_price"] = actual_close_price
        order["close_time"] = datetime.now()
        order["status"] = "closed"
        self._last_error = ERR_NO_ERROR
        return True

    def get_last_error(self) -> int:
        return getattr(self, '_last_error', ERR_NO_ERROR)

# --- OrderManager Class Definition (based on comprehensive analysis) ---
class OrderManager:
    def __init__(self, broker_api: MockBrokerAPI, retry_attempts=5, sleep_time=0.1, sleep_maximum=1.0, max_close_duration=10.0, on_order_closed=None):
        self.broker_api = broker_api
        self.retry_attempts = retry_attempts
        self.sleep_time = sleep_time
        self.sleep_maximum = sleep_maximum
        self.max_close_duration = max_close_duration
        self.on_order_closed = on_order_closed # Callback for when an order is successfully closed
        self._last_error = ERR_NO_ERROR

    def _handle_error(self, error_code: int, message: str):
        self._last_error = error_code
        exception_class = ERROR_MAP.get(error_code, OrderError)
        raise exception_class(f"Error {error_code}: {message}")

    def send_order_reliable(self, symbol: str, cmd: int, volume: float, price: float, slippage: int, stoploss: float, takeprofit: float, comment: str, magic: int) -> int:
        for attempt in range(self.retry_attempts):
            try:
                ticket = self.broker_api.send_order(symbol, cmd, volume, price, slippage, stoploss, takeprofit, comment, magic)
                if ticket != -1: # Success
                    return ticket
                else:
                    error_code = self.broker_api.get_last_error()
                    if error_code in [ERR_TRADE_CONTEXT_BUSY, ERR_SERVER_BUSY, ERR_BROKER_BUSY]:
                        exponential_backoff_sleep(self.sleep_time * (2 ** attempt), self.sleep_maximum)
                        continue # Retry
                    elif error_code == ERR_PRICE_CHANGED or error_code == ERR_REQUOTE:
                        # For price changes, update price and retry immediately
                        market_info = self.broker_api.get_market_info(symbol)
                        if cmd == OP_BUY or cmd == OP_BUYSTOP or cmd == OP_BUYLIMIT:
                            price = market_info['ask']
                        elif cmd == OP_SELL or cmd == OP_SELLSTOP or cmd == OP_SELLLIMIT:
                            price = market_info['bid']
                        continue # Retry with new price
                    else:
                        self._handle_error(error_code, f"Failed to send order after {attempt+1} attempts.")

            except OrderError as e:
                self._last_error = self.broker_api.get_last_error()
                print(f"Order management exception during send_order: {e}")
                # Decide if this error is retryable or critical
                if isinstance(e, (TradeContextBusyError, InvalidPriceError)) and attempt < self.retry_attempts - 1:
                    exponential_backoff_sleep(self.sleep_time * (2 ** attempt), self.sleep_maximum)
                    continue
                return -1 # Critical failure, do not retry
            except Exception as e:
                self._last_error = ERR_COMMON_ERROR
                print(f"Unexpected error during send_order: {e}")
                return -1
        self._last_error = ERR_COMMON_ERROR # Indicate failure after retries
        return -1

    def send_market_order_reliable(self, symbol: str, cmd: int, volume: float, initial_price: float, slippage: int, stoploss: float, takeprofit: float, comment: str, magic: int) -> int:
        # Market orders typically use current market price, but initial_price can be a reference
        market_info = self.broker_api.get_market_info(symbol)
        current_price = 0.0
        if cmd == OP_BUY:
            current_price = market_info['ask']
        elif cmd == OP_SELL:
            current_price = market_info['bid']
        else:
            # For other types, fallback to bid for safety (though market orders are usually buy/sell)
            current_price = market_info['bid']

        # Use current_price for reliable sending, not initial_price
        return self.send_order_reliable(symbol, cmd, volume, current_price, slippage, stoploss, takeprofit, comment, magic)

    def close_order_reliable(self, ticket: int, volume: float, close_price: float, slippage: int, pnl: float = 0.0, order_details: dict = None, exit_reason: str = "") -> bool:
        start_time = time.time()
        while time.time() - start_time < self.max_close_duration:
            try:
                success = self.broker_api.close_order(ticket, volume, close_price, slippage)
                if success:
                    if self.on_order_closed: # Call the callback if provided
                        self.on_order_closed(ticket, True, close_price, pnl, order_details, exit_reason)
                    return True
                else:
                    error_code = self.broker_api.get_last_error()
                    if error_code in [ERR_TRADE_CONTEXT_BUSY, ERR_SERVER_BUSY, ERR_BROKER_BUSY, ERR_CLOSE_TIMEOUT]:
                        exponential_backoff_sleep(self.sleep_time, self.sleep_maximum) # No exponential backoff for close retries
                        continue
                    elif error_code == ERR_PRICE_CHANGED:
                        # For price changes on close, update close_price and retry
                        order = self.broker_api._open_orders.get(ticket)
                        if order:
                            market_info = self.broker_api.get_market_info(order["symbol"])
                            if order["cmd"] == OP_BUY:
                                close_price = market_info['bid']
                            elif order["cmd"] == OP_SELL:
                                close_price = market_info['ask']
                        continue # Retry with new price
                    else:
                        self._handle_error(error_code, f"Failed to close order {ticket} after multiple attempts.")

            except OrderError as e:
                self._last_error = self.broker_api.get_last_error()
                print(f"Order management exception during close_order: {e}")
                if self.on_order_closed: # Call the callback even on failure
                    self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
                return False
            except Exception as e:
                self._last_error = ERR_COMMON_ERROR
                print(f"Unexpected error during close_order: {e}")
                if self.on_order_closed: # Call the callback even on failure
                    self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
                return False

        self._last_error = ERR_CLOSE_TIMEOUT # Indicate timeout
        if self.on_order_closed: # Call the callback on timeout as well
            self.on_order_closed(ticket, False, close_price, pnl, order_details, exit_reason)
        return False

    def get_last_error(self) -> int:
        return self._last_error


def fetch_data(symbol, timeframe='1d', alpha_key=None, start_date=None, end_date=None, broker_api: MockBrokerAPI = None):
    if timeframe == '1d':
        data = yf.download(symbol, interval='1d', start=start_date, end=end_date)
        if isinstance(data.columns, pd.MultiIndex):
            data.columns = [col[0] for col in data.columns]
        data.columns = pd.Index([str(col).strip() for col in data.columns])
        data.columns.name = None
        data.columns = [col.upper() for col in data.columns]
        if 'ADJ CLOSE' in data.columns and 'CLOSE' not in data.columns:
            data = data.rename(columns={'ADJ CLOSE': 'CLOSE'})
        data = data[['OPEN', 'HIGH', 'LOW', 'CLOSE', 'VOLUME']]
        data.columns = [col.capitalize() for col in data.columns]
    else:
        if not alpha_key:
            raise ValueError("Alpha Vantage API key is required for intraday timeframes.")

        url = f"https://www.alphavantage.co/query"
        params = {
            "function": "TIME_SERIES_INTRADAY",
            "symbol": symbol,
            "interval": timeframe,
            "apikey": alpha_key,
            "outputsize": "full"
        }
        response = requests.get(url, params=params)
        json_data = response.json()

        if "Time Series (" + timeframe + ")" not in json_data:
            print(f"Error fetching data from Alpha Vantage for {symbol} ({timeframe}): {json_data.get('Note', 'Unknown error')}")
            return pd.DataFrame()

        key = f"Time Series ({timeframe})"
        df = pd.DataFrame.from_dict(json_data[key], orient='index')
        df = df.rename(columns={
            '1. open': 'Open',
            '2. high': 'High',
            '3. low': 'Low',
            '4. close': 'Close',
            '5. volume': 'Volume'
        })
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        data = df.astype(float)

        if start_date:
            data = data[data.index >= pd.to_datetime(start_date)]
        if end_date:
            data = data[data.index <= pd.to_datetime(end_date)]

    # Add Symbol column and normalize prices
    data['Symbol'] = symbol
    if broker_api:
        for col in ['Open', 'High', 'Low', 'Close']:
            data[col] = data[col].apply(lambda x: normalize_price(symbol, x, broker_api))

    return data

# --- Helper Function: calculate_pivots ---
def calculate_pivots(df):
    df = df.copy()
    df["Pivot"] = (df["High"] + df["Low"] + df["Close"]) / 3
    df["R1"] = 2 * df["Pivot"] - df["Low"]
    df["S1"] = 2 * df["Pivot"] - df["High"]
    df["R2"] = df["Pivot"] + (df["High"] - df["Low"])
    df["S2"] = df["Pivot"] - (df["High"] - df["Low"])
    return df

# --- Helper Function: count_rsi_crosses ---
def count_rsi_crosses(series, upper=70, lower=30, window=20):
    crosses = []
    for i in range(len(series)):
        if i < window:
            crosses.append(0)
        else:
            window_rsi = series[i-window:i].dropna()
            count = ((window_rsi > upper) | (window_rsi < lower)).sum()
            crosses.append(count)
    return crosses

# --- Helper Function: create_lstm_model ---
def create_lstm_model(input_shape, output_dim, lstm_units_1, lstm_units_2, learning_rate):
    model = Sequential([
        LSTM(lstm_units_1, return_sequences=True, input_shape=input_shape),
        LSTM(lstm_units_2),
        Dense(output_dim, activation='linear')
    ])
    model.compile(optimizer=Adam(learning_rate), loss='mse')
    return model

# --- New Helper Function: _generate_lstm_data ---
def _generate_lstm_data(data, features, params, output_area, broker_api: MockBrokerAPI = None, symbol: str = None):
    with output_area:
        scaler = MinMaxScaler()
        data_scaled = data[features].copy().astype(np.float32)
        data_scaled[:] = scaler.fit_transform(data_scaled)

        sequence_length = params['sequence_length']
        lstm_units_1 = params['lstm_units_1']
        lstm_units_2 = params['lstm_units_2']
        lstm_learning_rate = params['lstm_learning_rate']
        lstm_epochs = params['lstm_epochs']
        lstm_batch_size = params['lstm_batch_size']

        X, y = [], []
        if len(data_scaled) > sequence_length + 1:
            for i in range(len(data_scaled) - sequence_length - 1):
                X.append(data_scaled.iloc[i:i+sequence_length].values)
                y.append(data_scaled.iloc[i+sequence_length].values)
            X, y = np.array(X), np.array(y)
        else:
            X, y = np.array([]), np.array([])

        generated_df = pd.DataFrame(columns=features)

        if len(X) > 0 and len(y) > 0:
            lstm_model = create_lstm_model((sequence_length, len(features)), len(features),
                                         lstm_units_1, lstm_units_2, lstm_learning_rate)
            print(f"Training LSTM model for {lstm_epochs} epochs...")
            # Assuming early stopping and model checkpointing might be added later if needed
            lstm_model.fit(X, y, epochs=lstm_epochs, batch_size=lstm_batch_size, validation_split=0.2, verbose=0)

            generated = []
            seed = X[-1]
            for _ in range(len(data)):
                pred = lstm_model.predict(seed.reshape(1, sequence_length, len(features)), verbose=0)[0]
                generated.append(pred)
                seed = np.vstack([seed[1:], pred])

            generated_df = pd.DataFrame(generated, columns=features)
            generated_df[features] = scaler.inverse_transform(generated_df[features])

            # Normalize generated prices
            if broker_api and symbol:
                for col in ['Open', 'High', 'Low', 'Close']:
                    if col in generated_df.columns:
                        generated_df[col] = generated_df[col].apply(lambda x: normalize_price(symbol, x, broker_api))

            generated_df = calculate_pivots(generated_df)
            print("LSTM model trained and generated data.")
        else:
            print("Not enough data to train LSTM model or generate candles. Skipping LSTM training.")
        return generated_df

# --- Helper Function: send_email_with_attachments ---
def send_email_with_attachments(sender_email, sender_password, recipient_email, subject, body, attachment_paths):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = subject

    msg.attach(MIMEText(body, 'plain'))

    for attachment_path in attachment_paths:
        if not os.path.exists(attachment_path):
            print(f"Warning: Attachment not found: {attachment_path}")
            continue
        try:
            with open(attachment_path, "rb") as attachment:
                part = MIMEMultipart()
                part.set_payload(attachment.read())
            encoders.encode_base64(part)
            part.add_header('Content-Disposition', f"attachment; filename= {os.path.basename(attachment_path)}")
            msg.attach(part)
        except Exception as e:
            print(f"Error attaching {attachment_path}: {e}")

    try:
        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(sender_email, sender_password)
        text = msg.as_string()
        server.sendmail(sender_email, recipient_email, text)
        server.quit()
        print("Email sent successfully!")
    except Exception as e:
        print(f"Error sending email: {e}")

# --- PivotEnv Class Definition ---
class PivotEnv(Env):
    def __init__(self, hist_df, gen_df,
                 broker_api, order_manager, # New parameters
                 grid_levels=3,
                 grid_step_pct=0.005,
                 martingale_factor=1.1,
                 max_total_exposure=10.0,
                 grid_tp_multiplier=1.5,
                 grid_sl_multiplier=1.0,
                 base_position_size=1.0,
                 volatility_inverse_factor=0.01,
                 drawdown_penalty_percentage=0.05,
                 drawdown_high_watermark_bonus=0.005,
                 transaction_cost_pct=0.0005,
                 time_decay_threshold_steps=5,
                 time_decay_penalty_per_step=-0.02,
                 profit_threshold_for_decay=0.01,
                 early_exit_lookahead_steps=5,
                 early_exit_reward_factor=0.5,
                 early_exit_pnl_threshold_pct=0.001,
                 adaptive_averaging_enabled=False,
                 averaging_trigger_pct=0.01,
                 max_averaging_levels=2,
                 averaging_step_pct=0.005,
                 averaging_tp_sl_mode='consolidated',
                 averaging_volatility_threshold_atr=0.5,
                 max_averaging_drawdown_pct=0.05,
                 dynamic_martingale_rsi_extreme_threshold=20,
                 dynamic_martingale_macd_neutral_threshold=0.01,
                 averaging_tp_improvement_factor=0.001,
                 averaging_bonus_factor=0.1,
                 averaging_penalty_factor=-0.05,
                 atr_filter_threshold=0.5,
                 bb_width_filter_threshold=10.0,
                 macd_signal_coincide_threshold=0.005,
                 rsi_oversold_bonus_threshold=30,
                 rsi_overbought_bonus_threshold=70,
                 macd_strong_trend_threshold=0.1,
                 rsi_extreme_threshold=20,
                 macd_cross_threshold=0.05):
        super().__init__()
        self.hist_df = hist_df
        self.gen_df = gen_df
        self.broker_api = broker_api # Store new instance
        self.order_manager = order_manager # Store new instance
        self.current_step = 0
        self.observation_space = Box(low=-np.inf, high=np.inf, shape=(17,), dtype=np.float32)
        self.action_space = Discrete(5)
        self.rewards_history = []
        self.balance = 10000.0
        self.open_trades = []
        self.pending_orders = []
        self.closed_trades = []
        self.equity_history = []
        self.max_equity_so_far = self.balance

        self.grid_levels = grid_levels
        self.grid_step_pct = grid_step_pct
        self.martingale_factor = martingale_factor
        self.max_total_exposure = max_total_exposure
        self.grid_tp_multiplier = grid_tp_multiplier
        self.grid_sl_multiplier = grid_sl_multiplier

        self.base_position_size = base_position_size
        self.volatility_inverse_factor = volatility_inverse_factor
        self.drawdown_penalty_percentage = drawdown_penalty_percentage
        self.drawdown_high_watermark_bonus = drawdown_high_watermark_bonus
        self.transaction_cost_pct = transaction_cost_pct
        self.time_decay_threshold_steps = time_decay_threshold_steps
        self.time_decay_penalty_per_step = time_decay_penalty_per_step
        self.profit_threshold_for_decay = profit_threshold_for_decay
        self.early_exit_lookahead_steps = early_exit_lookahead_steps
        self.early_exit_reward_factor = early_exit_reward_factor
        self.early_exit_pnl_threshold_pct = early_exit_pnl_threshold_pct
        self.adaptive_averaging_enabled = adaptive_averaging_enabled
        self.averaging_trigger_pct = averaging_trigger_pct
        self.max_averaging_levels = max_averaging_levels
        self.averaging_step_pct = averaging_step_pct
        self.averaging_tp_sl_mode = averaging_tp_sl_mode
        self.averaging_volatility_threshold_atr = averaging_volatility_threshold_atr
        self.max_averaging_drawdown_pct = max_averaging_drawdown_pct
        self.dynamic_martingale_rsi_extreme_threshold = dynamic_martingale_rsi_extreme_threshold
        self.dynamic_martingale_macd_neutral_threshold = dynamic_martingale_macd_neutral_threshold
        self.averaging_tp_improvement_factor = averaging_tp_improvement_factor
        self.averaging_bonus_factor = averaging_bonus_factor
        self.averaging_penalty_factor = averaging_penalty_factor

        self.atr_filter_threshold = atr_filter_threshold
        self.bb_width_filter_threshold = bb_width_filter_threshold
        self.macd_signal_coincide_threshold = macd_signal_coincide_threshold
        self.rsi_oversold_bonus_threshold = rsi_oversold_bonus_threshold
        self.rsi_overbought_bonus_threshold = rsi_overbought_bonus_threshold
        self.macd_strong_trend_threshold = macd_strong_trend_threshold
        self.rsi_extreme_threshold = rsi_extreme_threshold
        self.macd_cross_threshold = macd_cross_threshold

        self.active_grids = {}

    def _generate_grid_id(self):
        return str(uuid.uuid4())

    def reset(self, seed=None, options=None):
        super().reset(seed=seed)
        self.current_step = 0
        self.rewards_history.clear()
        # When resetting, ensure balance reflects the overall simulation rather than just env's internal balance
        # For now, we'll keep the env's balance separate for internal reward calculation
        self.balance = 10000.0 # Reset internal env balance
        self.open_trades = []
        self.pending_orders = []
        self.closed_trades = []
        self.equity_history = []
        self.max_equity_so_far = self.balance
        self.active_grids = {}
        return self._get_obs(), {}

    def _get_obs(self):
        row = self.hist_df.iloc[self.current_step]
        prev_row = self.hist_df.iloc[self.current_step - 1] if self.current_step > 0 else row

        # Calculate current equity based on trades managed by the environment (not necessarily broker_api's)
        # This needs to be carefully aligned if broker_api is truly the source of truth
        current_equity = self.balance
        for trade in self.open_trades:
            if trade['type'] == 'Buy Market' or trade['type'] == 'Buy Stop':
                current_equity += (row['Close'] - trade['entry_price']) * trade['size']
            elif trade['type'] == 'Sell Market' or trade['type'] == 'Sell Stop':
                current_equity += (trade['entry_price'] - row['Close']) * trade['size']
        self.equity_history.append(current_equity)

        if self.max_equity_so_far > 0:
            drawdown_metric = (current_equity / self.max_equity_so_far) - 1
        else:
            drawdown_metric = 0.0

        current_close = row["Close"]
        pivot_levels = [row["Pivot"], row["R1"], row["S1"], row["R2"], row["S2"]]
        min_pivot_dist_pct = min(abs((level - current_close) / (current_close + 1e-9)) * 100 for level in pivot_levels)
        rsi_slope = row["RSI"] - prev_row["RSI"]
        current_macd_hist = row["MACD"] - row["MACD_Signal"]
        prev_macd_hist = prev_row["MACD"] - prev_row["MACD_Signal"]
        macd_hist_trend = current_macd_hist - prev_macd_hist
        bb_width = (row["Bb_Upper"] - row["Bb_Lower"])
        normalized_bb_width = bb_width / (row["Bb_Middle"] + 1e-9) if row["Bb_Middle"] != 0 else 0.0

        return np.array([
            row["Pivot"], row["R1"], row["S1"], row["R2"], row["S2"],
            row["RSI"], row["MACD"], row["MACD_Signal"],
            row["Bb_Middle"], row["Bb_Upper"], row["Bb_Lower"],
            row["ATR"],
            drawdown_metric,
            min_pivot_dist_pct,
            rsi_slope,
            macd_hist_trend,
            normalized_bb_width
        ], dtype=np.float32)

    def step(self, action):
        epsilon = 1e-6

        TP_ATR_MULTIPLIER = 1.5
        SL_ATR_MULTIPLIER = 1.0
        TRAILING_SL_ATR_MULTIPLIER = 0.5

        reward = 0.0
        just_closed_trades_current_step = []

        if self.current_step >= len(self.hist_df) or self.current_step >= len(self.gen_df):
            last_valid_hist_close = self.hist_df.iloc[min(len(self.hist_df), self.current_step) - 1]["Close"]

            # Logic for closing open trades at the end of simulation
            for trade in self.open_trades:
                pnl_gross = 0
                if trade['type'] == 'Buy Market' or trade['type'] == 'Buy Stop':
                    pnl_gross = (last_valid_hist_close - trade['entry_price']) * trade['size']
                elif trade['type'] == 'Sell Market' or trade['type'] == 'Sell Stop':
                    pnl_gross = (trade['entry_price'] - last_valid_hist_close) * trade['size']

                cost = (trade['entry_price'] * trade['size']) * self.transaction_cost_pct
                pnl = pnl_gross - cost

                self.balance += pnl
                self.closed_trades.append({
                    'entry_date': trade['entry_date'],
                    'exit_date': self.hist_df.index[min(len(self.hist_df), self.current_step) - 1],
                    'type': trade['type'],
                    'entry_price': last_valid_hist_close,
                    'exit_price': last_valid_hist_close,
                    'tp': trade.get('tp', 0),
                    'sl': trade.get('sl', 0),
                    'pnl': pnl,
                    'size': trade['size'],
                    'balance_after': self.balance,
                    'grid_id': trade.get('grid_id', None),
                    'exit_reason': 'End of Simulation'
                })
            self.open_trades = []

            # Logic for cancelling pending orders at the end of simulation
            for p_order in self.pending_orders:
                self.closed_trades.append({
                    'entry_date': p_order['entry_date'],
                    'exit_date': self.hist_df.index[min(len(self.hist_df), self.current_step) - 1],
                    'type': p_order['type'],
                    'entry_price': p_order['entry_price'],
                    'exit_price': 'N/A',
                    'tp': p_order.get('tp', 0),
                    'sl': p_order.get('sl', 0),
                    'pnl': 0,
                    'size': p_order['size'],
                    'balance_after': self.balance,
                    'grid_id': p_order.get('grid_id', None),
                    'exit_reason': 'Cancelled (End of Sim)'
                })
            self.pending_orders = []
            self.active_grids = {}

            self.equity_history.append(self.balance)
            return np.zeros(self.observation_space.shape, dtype=np.float32), 0.0, True, False, {}

        hist = self.hist_df.iloc[self.current_step]
        gen = self.gen_df.iloc[self.current_step]

        current_rsi = hist["RSI"]
        current_macd = hist["MACD"]
        current_macd_signal = hist["MACD_Signal"]
        current_macd_diff = current_macd - current_macd_signal
        current_close = hist["Close"]
        current_high = hist["High"]
        current_low = hist["Low"]
        current_atr = hist["ATR"]
        volatility = (current_high - current_low)

        current_equity = self.balance
        for trade in self.open_trades:
            if trade['type'] == 'Buy Market' or trade['type'] == 'Buy Stop':
                current_equity += (current_close - trade['entry_price']) * trade['size']
            elif trade['type'] == 'Sell Market' or trade['type'] == 'Sell Stop':
                current_equity += (trade['entry_price'] - current_close) * trade['size']
        self.equity_history.append(current_equity)

        if current_equity > self.max_equity_so_far:
            reward += self.drawdown_high_watermark_bonus
            self.max_equity_so_far = current_equity
        elif self.max_equity_so_far > 0 and (self.max_equity_so_far - current_equity) / self.max_equity_so_far > self.drawdown_penalty_percentage:
            reward -= self.drawdown_penalty_percentage * 5

        triggered_pending_orders = []
        for p_order in self.pending_orders:
            if p_order['type'] == 'Buy Stop':
                if current_high >= p_order['entry_price']:
                    triggered_pending_orders.append(p_order)
            elif p_order['type'] == 'Sell Stop':
                if current_low <= p_order['entry_price']:
                    triggered_pending_orders.append(p_order)

        for triggered_order in triggered_pending_orders:
            self.pending_orders.remove(triggered_order)

            if 'grid_id' in triggered_order and triggered_order['grid_id'] in self.active_grids:
                grid_id = triggered_order['grid_id']
                grid = self.active_grids[grid_id]

                triggered_order['status'] = 'filled'
                grid['filled_orders'].append(triggered_order)

                triggered_order_for_open_trades = triggered_order.copy()
                triggered_order_for_open_trades['tp'] = grid['current_tp']
                triggered_order_for_open_trades['sl'] = grid['current_sl']

                if 'highest_price_seen' in triggered_order_for_open_trades: del triggered_order_for_open_trades['highest_price_seen']
                if 'lowest_price_seen' in triggered_order_for_open_trades: del triggered_order_for_open_trades['lowest_price_seen']

                self.open_trades.append(triggered_order_for_open_trades)

                total_value = sum(t['entry_price'] * t['size'] for t in grid['filled_orders'])
                grid['total_filled_size'] = sum(t['size'] for t in grid['filled_orders'])
                grid['current_avg_price'] = total_value / grid['total_filled_size'] if grid['total_filled_size'] > 0 else 0

                if grid['type'] == 'BuyGrid':
                    grid['current_tp'] = grid['current_avg_price'] + (current_atr * self.grid_tp_multiplier)
                    grid['current_sl'] = grid['current_avg_price'] - (current_atr * self.grid_sl_multiplier)
                else:
                    grid['current_tp'] = grid['current_avg_price'] - (current_atr * self.grid_tp_multiplier)
                    grid['current_sl'] = grid['current_avg_price'] + (current_atr * self.grid_sl_multiplier)

                num_filled_in_grid = len(grid['filled_orders'])
                if num_filled_in_grid < len(grid['pending_grid_orders_full_list']):
                    next_grid_order_to_place = grid['pending_grid_orders_full_list'][num_filled_in_grid]
                    self.pending_orders.append(next_grid_order_to_place)

            else:
                initial_highest_price_seen = triggered_order['entry_price']
                initial_lowest_price_seen = triggered_order['entry_price']

                if triggered_order['type'] == 'Buy Stop':
                    initial_highest_price_seen = current_high
                    initial_lowest_price_seen = triggered_order['entry_price']
                elif triggered_order['type'] == 'Sell Stop':
                    initial_lowest_price_seen = current_low
                    initial_highest_price_seen = triggered_order['entry_price']

                self.open_trades.append({
                    'entry_date': self.hist_df.index[self.current_step],
                    'entry_step': self.current_step,
                    'type': triggered_order['type'],
                    'entry_price': triggered_order['entry_price'],
                    'tp': triggered_order['tp'],
                    'sl': triggered_order['sl'],
                    'initial_sl': triggered_order['initial_sl'],
                    'size': self.base_position_size,
                    'highest_price_seen': initial_highest_price_seen,
                    'lowest_price_seen': initial_lowest_price_seen
                })

        trades_to_close = []
        for i, trade in enumerate(self.open_trades):
            if 'grid_id' in trade and trade['grid_id'] in self.active_grids:
                continue

            trade_closed = False
            pnl_gross = 0
            exit_price = current_close
            closure_reason = ""

            if trade['type'] == 'Buy Market' or trade['type'] == 'Buy Stop':
                if current_high > trade['highest_price_seen']:
                    trade['highest_price_seen'] = current_high
                new_trailing_sl = trade['highest_price_seen'] - (current_atr * TRAILING_SL_ATR_MULTIPLIER)
                trade['sl'] = max(trade['sl'], new_trailing_sl, trade['initial_sl'])
                if current_close > trade['entry_price']:
                    trade['sl'] = max(trade['sl'], trade['entry_price'])

            elif trade['type'] == 'Sell Market' or trade['type'] == 'Sell Stop':
                if current_low < trade['lowest_price_seen']:
                    trade['lowest_price_seen'] = current_low
                new_trailing_sl = trade['lowest_price_seen'] + (current_atr * TRAILING_SL_ATR_MULTIPLIER)
                trade['sl'] = min(trade['sl'], new_trailing_sl, trade['initial_sl'])
                if current_close < trade['entry_price']:
                    trade['sl'] = min(trade['sl'], trade['entry_price'])

            if trade['type'] in ['Buy Market', 'Buy Stop']:
                tp_hit = (current_high >= trade['tp'])
                sl_hit = (current_low <= trade['sl'])
                rsi_close_condition = (current_rsi < self.rsi_overbought_bonus_threshold)

                if sl_hit:
                    pnl_at_sl = (trade['sl'] - trade['entry_price']) * trade['size']
                    pnl_gross = pnl_at_sl
                    exit_price = trade['sl']
                    trade_closed = True
                    closure_reason = "SL Hit (profit)" if pnl_at_sl > 0 else "SL Hit (loss)"
                elif tp_hit:
                    pnl_gross = (trade['tp'] - trade['entry_price']) * trade['size']
                    exit_price = trade['tp']
                    trade_closed = True
                    closure_reason = "TP Hit"
                elif (self.current_step - trade['entry_step']) > self.time_decay_threshold_steps:
                    unrealized_pnl = (current_close - trade['entry_price']) * trade['size']
                    if (abs(trade['entry_price'] * trade['size']) + epsilon) > 0:
                        percentage_return = unrealized_pnl / (abs(trade['entry_price'] * trade['size']) + epsilon)
                    else:
                        percentage_return = -1.0

                    if percentage_return < self.profit_threshold_for_decay:
                        pnl_gross = unrealized_pnl
                        exit_price = current_close
                        trade_closed = True
                        closure_reason = "Time Decay Closure"
                elif rsi_close_condition:
                    pnl_gross = (current_close - trade['entry_price']) * trade['size']
                    exit_price = current_close
                    trade_closed = True
                    closure_reason = "RSI Reversal"

            elif trade['type'] in ['Sell Market', 'Sell Stop']:
                tp_hit = (current_low <= trade['tp'])
                sl_hit = (current_high >= trade['sl'])
                rsi_close_condition = (current_rsi > self.rsi_oversold_bonus_threshold)

                if sl_hit:
                    pnl_at_sl = (trade['entry_price'] - trade['sl']) * trade['size']
                    pnl_gross = pnl_at_sl
                    exit_price = trade['sl']
                    trade_closed = True
                    closure_reason = "SL Hit (profit)" if pnl_at_sl > 0 else "SL Hit (loss)"
                elif tp_hit:
                    pnl_gross = (trade['entry_price'] - trade['tp']) * trade['size']
                    exit_price = trade['tp']
                    trade_closed = True
                    closure_reason = "TP Hit"
                elif (self.current_step - trade['entry_step']) > self.time_decay_threshold_steps:
                    unrealized_pnl = (trade['entry_price'] - current_close) * trade['size']
                    if (abs(trade['entry_price'] * trade['size']) + epsilon) > 0:
                        percentage_return = unrealized_pnl / (abs(trade['entry_price'] * trade['size']) + epsilon)
                    else:
                        percentage_return = -1.0

                    if percentage_return < self.profit_threshold_for_decay:
                        pnl_gross = unrealized_pnl
                        exit_price = current_close
                        trade_closed = True
                        closure_reason = "Time Decay Closure"
                elif rsi_close_condition:
                    pnl_gross = (trade['entry_price'] - current_close) * trade['size']
                    exit_price = current_close
                    trade_closed = True
                    closure_reason = "RSI Reversal"

            if not trade_closed and (self.current_step - trade['entry_step']) > self.time_decay_threshold_steps:
                unrealized_pnl = 0
                if trade['type'] in ['Buy Market', 'Buy Stop']:
                    unrealized_pnl = (current_close - trade['entry_price']) * trade['size']
                elif trade['type'] in ['Sell Market', 'Sell Stop']:
                    unrealized_pnl = (trade['entry_price'] - current_close) * trade['size']
                if (abs(trade['entry_price'] * trade['size']) + epsilon) > 0:
                    percentage_return = unrealized_pnl / (abs(trade['entry_price'] * trade['size']) + epsilon)
                else:
                    percentage_return = -1.0
                if percentage_return < self.profit_threshold_for_decay:
                    reward += self.time_decay_penalty_per_step

            if trade_closed:
                cost = (trade['entry_price'] * trade['size']) * self.transaction_cost_pct
                pnl = pnl_gross - cost

                self.balance += pnl
                reward += pnl / current_close
                self.closed_trades.append({
                    'entry_date': trade['entry_date'],
                    'exit_date': self.hist_df.index[self.current_step],
                    'type': trade['type'],
                    'entry_price': exit_price,
                    'exit_price': exit_price,
                    'tp': trade['tp'],
                    'sl': trade['sl'],
                    'pnl': pnl,
                    'size': trade['size'],
                    'balance_after': self.balance,
                    'grid_id': trade.get('grid_id', None),
                    'exit_reason': closure_reason
                })
                just_closed_trades_current_step.append({
                    'exit_step_idx': self.current_step,
                    'type': trade['type'],
                    'entry_price': trade['entry_price'],
                    'actual_pnl_gross': pnl_gross,
                    'size': trade['size'],
                    'exit_reason': closure_reason
                })
                trades_to_close.append(i)

        for i in sorted(trades_to_close, reverse=True):
            del self.open_trades[i]

        grids_to_close = []
        for grid_id, grid in list(self.active_grids.items()):
            grid_closed = False
            closure_reason = ""
            grid_pnl_gross = 0
            exit_price = current_close

            if grid['type'] == 'BuyGrid':
                if current_high > grid['highest_price_seen']:
                    grid['highest_price_seen'] = current_high
                new_trailing_sl = grid['highest_price_seen'] - (current_atr * TRAILING_SL_ATR_MULTIPLIER)
                grid['current_sl'] = max(grid['current_sl'], new_trailing_sl)
            else:
                if current_low < grid['lowest_price_seen']:
                    grid['lowest_price_seen'] = current_low
                new_trailing_sl = grid['lowest_price_seen'] + (current_atr * TRAILING_SL_ATR_MULTIPLIER)
                grid['current_sl'] = min(grid['current_sl'], new_trailing_sl)

            if grid['type'] == 'BuyGrid':
                tp_hit = (current_high >= grid['current_tp'])
                sl_hit = (current_low <= grid['current_sl'])
                rsi_reversal = (current_rsi < self.rsi_oversold_bonus_threshold)

                if sl_hit:
                    grid_pnl_at_sl = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_sl += (grid['current_sl'] - filled_trade['entry_price']) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_sl
                    exit_price = grid['current_sl']
                    grid_closed = True
                    closure_reason = "SL Hit (profit)" if grid_pnl_at_sl > 0 else "SL Hit (loss)"
                elif tp_hit:
                    grid_pnl_at_tp = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_tp += (grid['current_tp'] - filled_trade['entry_price']) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_tp
                    exit_price = grid['current_tp']
                    grid_closed = True
                    closure_reason = "TP Hit"
                elif (self.current_step - grid['initial_entry_step']) > self.time_decay_threshold_steps:
                    unrealized_grid_pnl = 0
                    for filled_trade in grid['filled_orders']:
                        unrealized_grid_pnl += (current_close - filled_trade['entry_price']) * filled_trade['size']
                    if (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon) > 0:
                        percentage_return = unrealized_grid_pnl / (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon)
                    else:
                        percentage_return = -1.0

                    if percentage_return < self.profit_threshold_for_decay:
                        grid_pnl_gross = unrealized_grid_pnl
                        exit_price = current_close
                        grid_closed = True
                        closure_reason = "Time Decay Closure"
                elif rsi_reversal:
                    grid_pnl_at_current = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_current += (current_close - filled_trade['entry_price']) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_current
                    exit_price = current_close
                    grid_closed = True
                    closure_reason = "RSI Reversal"

            else:
                tp_hit = (current_low <= grid['current_tp'])
                sl_hit = (current_high >= grid['current_sl'])
                rsi_reversal = (current_rsi > self.rsi_oversold_bonus_threshold)

                if sl_hit:
                    grid_pnl_at_sl = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_sl += (filled_trade['entry_price'] - grid['current_sl']) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_sl
                    exit_price = grid['current_sl']
                    grid_closed = True
                    closure_reason = "SL Hit (profit)" if grid_pnl_at_sl > 0 else "SL Hit (loss)"
                elif tp_hit:
                    grid_pnl_at_tp = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_tp += (filled_trade['entry_price'] - grid['current_tp']) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_tp
                    exit_price = grid['current_tp']
                    grid_closed = True
                    closure_reason = "TP Hit"
                elif (self.current_step - grid['initial_entry_step']) > self.time_decay_threshold_steps:
                    unrealized_grid_pnl = 0
                    for filled_trade in grid['filled_orders']:
                        unrealized_grid_pnl += (filled_trade['entry_price'] - current_close) * filled_trade['size']
                    if (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon) > 0:
                        percentage_return = unrealized_grid_pnl / (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon)
                    else:
                        percentage_return = -1.0

                    if percentage_return < self.profit_threshold_for_decay:
                        grid_pnl_gross = unrealized_grid_pnl
                        exit_price = current_close
                        grid_closed = True
                        closure_reason = "Time Decay Closure"
                elif rsi_reversal:
                    grid_pnl_at_current = 0
                    for filled_trade in grid['filled_orders']:
                        grid_pnl_at_current += (filled_trade['entry_price'] - current_close) * filled_trade['size']
                    grid_pnl_gross = grid_pnl_at_current
                    exit_price = current_close
                    grid_closed = True
                    closure_reason = "RSI Reversal"

            if not grid_closed and grid['total_filled_size'] > self.max_total_exposure:
                grid_pnl_at_current = 0
                for filled_trade in grid['filled_orders']:
                    if grid['type'] == 'BuyGrid':
                        grid_pnl_at_current += (current_close - filled_trade['entry_price']) * filled_trade['size']
                    else:
                        grid_pnl_at_current += (filled_trade['entry_price'] - current_close) * filled_trade['size']
                grid_pnl_gross = grid_pnl_at_current
                exit_price = current_close
                grid_closed = True
                closure_reason = "Max Exposure Reached"

            if not grid_closed and (self.current_step - grid['initial_entry_step']) > self.time_decay_threshold_steps:
                unrealized_grid_pnl = 0
                for filled_trade in grid['filled_orders']:
                    if grid['type'] == 'BuyGrid':
                        unrealized_grid_pnl += (current_close - filled_trade['entry_price']) * filled_trade['size']
                    else:
                        unrealized_grid_pnl += (filled_trade['entry_price'] - current_close) * filled_trade['size']

                if (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon) > 0:
                    percentage_return = unrealized_grid_pnl / (abs(grid['current_avg_price'] * grid['total_filled_size']) + epsilon)
                else:
                    percentage_return = -1.0

                if percentage_return < self.profit_threshold_for_decay:
                    reward += self.time_decay_penalty_per_step

            if grid_closed and grid['total_filled_size'] > 0:
                total_entry_value = 0
                for filled_trade in grid['filled_orders']:
                    total_entry_value += (filled_trade['entry_price'] * filled_trade['size'])

                total_cost = total_entry_value * self.transaction_cost_pct
                grid_pnl = grid_pnl_gross - total_cost

                self.balance += grid_pnl
                reward += grid_pnl / current_close if current_close != 0 else 0
                self.closed_trades.append({
                    'entry_date': grid['initial_entry_date'],
                    'exit_date': self.hist_df.index[self.current_step],
                    'type': grid['type'],
                    'entry_price': grid['current_avg_price'],
                    'exit_price': exit_price,
                    'tp': grid['current_tp'],
                    'sl': grid['current_sl'],
                    'pnl': grid_pnl,
                    'size': grid['total_filled_size'],
                    'balance_after': self.balance,
                    'grid_id': grid_id,
                    'exit_reason': closure_reason
                })
                just_closed_trades_current_step.append({
                    'exit_step_idx': self.current_step,
                    'type': grid['type'],
                    'entry_price': grid['current_avg_price'],
                    'actual_pnl_gross': grid_pnl_gross,
                    'size': grid['total_filled_size'],
                    'exit_reason': closure_reason
                })
                grids_to_close.append(grid_id)

        for grid_id_to_close in grids_to_close:
            self.open_trades = [trade for trade in self.open_trades if trade.get('grid_id') != grid_id_to_close]
            self.pending_orders = [p_order for p_order in self.pending_orders if p_order.get('grid_id') != grid_id_to_close]
            del self.active_grids[grid_id_to_close]

        for closed_info in just_closed_trades_current_step:
            exit_step_idx = closed_info['exit_step_idx']
            trade_type = closed_info['type']
            trade_entry_price = closed_info['entry_price']
            actual_pnl_gross = closed_info['actual_pnl_gross']
            trade_size = closed_info['size']

            lookahead_start_step = exit_step_idx + 1
            lookahead_end_step = lookahead_start_step + self.early_exit_lookahead_steps

            if lookahead_end_step < len(self.hist_df):
                lookahead_slice = self.hist_df.iloc[lookahead_start_step : lookahead_end_step + 1]
                potential_pnl_gross = 0

                final_lookahead_price = lookahead_slice['Close'].iloc[-1]

                if trade_type in ['Buy Market', 'Buy Stop', 'BuyGrid']:
                    potential_pnl_gross = (final_lookahead_price - trade_entry_price) * trade_size
                elif trade_type in ['Sell Market', 'Sell Stop', 'SellGrid']:
                    potential_pnl_gross = (trade_entry_price - final_lookahead_price) * trade_size

                pnl_difference = potential_pnl_gross - actual_pnl_gross

                if abs(pnl_difference) > (trade_entry_price * trade_size * self.early_exit_pnl_threshold_pct):
                    if pnl_difference > 0:
                        reward -= (pnl_difference / self.balance) * self.early_exit_reward_factor
                    else:
                        reward += (abs(pnl_difference) / self.balance) * self.early_exit_reward_factor

        if self.adaptive_averaging_enabled:
            for grid_id, grid in list(self.active_grids.items()):
                num_filled_orders = len(grid['filled_orders'])
                if num_filled_orders >= self.max_averaging_levels:
                    continue

                unrealized_grid_pnl = 0
                for filled_trade in grid['filled_orders']:
                    if grid['type'] == 'BuyGrid':
                        unrealized_grid_pnl += (current_close - filled_trade['entry_price']) * filled_trade['size']
                    else:
                        unrealized_grid_pnl += (filled_trade['entry_price'] - current_close) * filled_trade['size']

                current_grid_value = grid['current_avg_price'] * grid['total_filled_size']
                if current_grid_value > 0:
                    grid_drawdown_pct = unrealized_grid_pnl / current_grid_value
                else:
                    grid_drawdown_pct = 0.0

                trigger_averaging = False
                if grid['type'] == 'BuyGrid':
                    if current_close < grid['current_avg_price'] * (1 - self.averaging_trigger_pct):
                        trigger_averaging = True
                else:
                    if current_close > grid['current_avg_price'] * (1 + self.averaging_trigger_pct):
                        trigger_averaging = True

                if trigger_averaging and \
                   current_atr > 0 and current_atr < self.averaging_volatility_threshold_atr and \
                   abs(grid_drawdown_pct) < self.max_averaging_drawdown_pct:

                    averaging_entry_price = 0
                    if grid['type'] == 'BuyGrid':
                        averaging_entry_price = current_close
                    else:
                        averaging_entry_price = current_close

                    prev_order_size = grid['filled_orders'][-1]['size'] if grid['filled_orders'] else self.base_position_size
                    averaging_size = prev_order_size * self.martingale_factor

                    if grid['type'] == 'BuyGrid':
                        if current_rsi < self.dynamic_martingale_rsi_extreme_threshold and current_macd_diff < self.dynamic_martingale_macd_neutral_threshold:
                            averaging_size *= 1.2
                        elif current_rsi < self.rsi_oversold_bonus_threshold:
                             averaging_size *= 1.1
                    else:
                        if current_rsi > (100 - self.dynamic_martingale_rsi_extreme_threshold) and current_macd_diff > self.dynamic_martingale_macd_neutral_threshold:
                            averaging_size *= 1.2
                        elif current_rsi > self.rsi_overbought_bonus_threshold:
                            averaging_size *= 1.1
                    averaging_size = max(0.1, averaging_size)

                    new_averaging_order = {
                        'entry_date': self.hist_df.index[self.current_step],
                        'entry_step': self.current_step,
                        'type': f"{grid['type'].replace('Grid', '')} Market",
                        'entry_price': averaging_entry_price,
                        'tp': grid['current_tp'],
                        'sl': grid['current_sl'],
                        'initial_sl': grid['current_sl'],
                        'size': averaging_size,
                        'grid_id': grid_id,
                        'order_level': num_filled_orders
                    }

                    self.open_trades.append(new_averaging_order)
                    grid['filled_orders'].append(new_averaging_order)

                    total_value = sum(t['entry_price'] * t['size'] for t in grid['filled_orders'])
                    grid['total_filled_size'] = sum(t['size'] for t in grid['filled_orders'])
                    grid['current_avg_price'] = total_value / grid['total_filled_size'] if grid['total_filled_size'] > 0 else 0

                    if self.averaging_tp_sl_mode == 'consolidated':
                        if grid['type'] == 'BuyGrid':
                            grid['current_tp'] = grid['current_avg_price'] + (current_atr * self.grid_tp_multiplier) * (1 + self.averaging_tp_improvement_factor)
                            grid['current_sl'] = grid['current_avg_price'] - (current_atr * self.grid_sl_multiplier)
                        else:
                            grid['current_tp'] = grid['current_avg_price'] - (current_atr * self.grid_tp_multiplier) * (1 + self.averaging_tp_improvement_factor)
                            grid['current_sl'] = grid['current_avg_price'] + (current_atr * self.grid_sl_multiplier)

                    reward += self.averaging_bonus_factor

                elif trigger_averaging and \
                     (current_atr == 0 or current_atr >= self.averaging_volatility_threshold_atr or \
                      abs(grid_drawdown_pct) >= self.max_averaging_drawdown_pct):
                    reward += self.averaging_penalty_factor

        original_action = action
        filtered = False
        filter_penalty = -0.1 * 0.5

        if action != 0:
            if current_atr < self.atr_filter_threshold:
                action = 0
                reward += filter_penalty
                filtered = True
            elif (hist["Bb_Upper"] - hist["Bb_Lower"]) < self.bb_width_filter_threshold:
                action = 0
                reward += filter_penalty
                filtered = True
            elif abs(current_macd_diff) < self.macd_signal_coincide_threshold:
                action = 0
                reward += filter_penalty
                filtered = True

        if action == 1:
            if not filtered and (
                hist["R1"] > hist["Pivot"] and
                hist["RSI"] < self.rsi_overbought_bonus_threshold and
                hist["MACD"] > hist["MACD_Signal"]
            ):
                grid_id = self._generate_grid_id()
                initial_stop_price = hist["R1"]
                initial_tp = gen["R2"]
                initial_sl = hist["S1"]
                dynamic_tp = initial_stop_price + (current_atr * self.grid_tp_multiplier)
                dynamic_sl = initial_stop_price - (current_atr * self.grid_sl_multiplier)

                first_grid_order = {
                    'entry_date': self.hist_df.index[self.current_step],
                    'entry_step': self.current_step,
                    'type': 'Buy Stop',
                    'entry_price': initial_stop_price,
                    'tp': dynamic_tp,
                    'sl': dynamic_sl,
                    'initial_sl': dynamic_sl,
                    'size': self.base_position_size,
                    'grid_id': grid_id,
                    'order_level': 0
                }

                new_grid = {
                    'type': 'BuyGrid',
                    'initial_entry_date': self.hist_df.index[self.current_step],
                    'initial_entry_step': self.current_step,
                    'initial_entry_price': initial_stop_price,
                    'total_filled_size': 0,
                    'current_avg_price': 0,
                    'filled_orders': [],
                    'pending_grid_orders_full_list': [],
                    'current_tp': dynamic_tp,
                    'current_sl': dynamic_sl,
                    'highest_price_seen': current_high,
                    'lowest_price_seen': initial_stop_price
                }
                new_grid['pending_grid_orders_full_list'].append(first_grid_order)

                prev_size = self.base_position_size
                for level in range(self.grid_levels):
                    grid_order_price = initial_stop_price - (initial_stop_price * self.grid_step_pct * (level + 1))
                    grid_order_size = prev_size * self.martingale_factor
                    prev_size = grid_order_size

                    new_grid['pending_grid_orders_full_list'].append({
                        'entry_date': self.hist_df.index[self.current_step],
                        'entry_step': self.current_step,
                        'type': 'Buy Stop',
                        'entry_price': grid_order_price,
                        'tp': dynamic_tp,
                        'sl': dynamic_sl,
                        'initial_sl': dynamic_sl,
                        'size': grid_order_size,
                        'grid_id': grid_id,
                        'order_level': level + 1
                    })

                self.active_grids[grid_id] = new_grid
                self.pending_orders.append(first_grid_order)
                reward += 0.2 * 0.1
            else:
                reward += -0.1 * 0.5

        elif action == 2:
            if not filtered and (
                hist["S1"] < hist["Pivot"] and
                hist["RSI"] > self.rsi_oversold_bonus_threshold and
                hist["MACD"] < self.macd_cross_threshold
            ):
                grid_id = self._generate_grid_id()
                initial_stop_price = hist["S1"]
                initial_tp = gen["S2"]
                initial_sl = hist["R1"]
                dynamic_tp = initial_stop_price - (current_atr * self.grid_tp_multiplier)
                dynamic_sl = initial_stop_price + (current_atr * self.grid_sl_multiplier)

                first_grid_order = {
                    'entry_date': self.hist_df.index[self.current_step],
                    'entry_step': self.current_step,
                    'type': 'Sell Stop',
                    'entry_price': initial_stop_price,
                    'tp': dynamic_tp,
                    'sl': dynamic_sl,
                    'initial_sl': dynamic_sl,
                    'size': self.base_position_size,
                    'grid_id': grid_id,
                    'order_level': 0
                }

                new_grid = {
                    'type': 'SellGrid',
                    'initial_entry_date': self.hist_df.index[self.current_step],
                    'initial_entry_step': self.current_step,
                    'initial_entry_price': initial_stop_price,
                    'total_filled_size': 0,
                    'current_avg_price': 0,
                    'filled_orders': [],
                    'pending_grid_orders_full_list': [],
                    'current_tp': dynamic_tp,
                    'current_sl': dynamic_sl,
                    'highest_price_seen': initial_stop_price,
                    'lowest_price_seen': current_low
                }
                new_grid['pending_grid_orders_full_list'].append(first_grid_order)

                prev_size = self.base_position_size
                for level in range(self.grid_levels):
                    grid_order_price = initial_stop_price + (initial_stop_price * self.grid_step_pct * (level + 1))
                    grid_order_size = prev_size * self.martingale_factor
                    prev_size = grid_order_size

                    new_grid['pending_grid_orders_full_list'].append({
                        'entry_date': self.hist_df.index[self.current_step],
                        'entry_step': self.current_step,
                        'type': 'Sell Stop',
                        'entry_price': grid_order_price,
                        'tp': dynamic_tp,
                        'sl': dynamic_sl,
                        'initial_sl': dynamic_sl,
                        'size': grid_order_size,
                        'grid_id': grid_id,
                        'order_level': level + 1
                    })

                self.active_grids[grid_id] = new_grid
                self.pending_orders.append(first_grid_order)
                reward += 0.2 * 0.1
            else:
                reward += -0.1 * 0.5

        elif action == 3:
            if not filtered and (
                current_rsi > self.rsi_overbought_bonus_threshold and
                current_macd > current_macd_signal
            ):
                grid_id = self._generate_grid_id()
                entry = hist["Close"]
                trade_size = self.base_position_size

                if current_atr > 0:
                    trade_size *= (1 - (current_atr * self.volatility_inverse_factor))
                if current_rsi > self.rsi_overbought_bonus_threshold:
                    trade_size *= 1.2
                if current_macd_diff > self.macd_strong_trend_threshold:
                    trade_size *= 1.1
                trade_size = max(0.1, trade_size)

                dynamic_tp = entry + (current_atr * self.grid_tp_multiplier)
                dynamic_sl = entry - (current_atr * self.grid_sl_multiplier)

                first_grid_order = {
                    'entry_date': self.hist_df.index[self.current_step],
                    'entry_step': self.current_step,
                    'type': 'Buy Market',
                    'entry_price': entry,
                    'tp': dynamic_tp,
                    'sl': dynamic_sl,
                    'initial_sl': dynamic_sl,
                    'size': trade_size,
                    'grid_id': grid_id,
                    'order_level': 0
                }

                new_grid = {
                    'type': 'BuyGrid',
                    'initial_entry_date': self.hist_df.index[self.current_step],
                    'initial_entry_step': self.current_step,
                    'initial_entry_price': entry,
                    'total_filled_size': trade_size,
                    'current_avg_price': entry,
                    'filled_orders': [first_grid_order],
                    'pending_grid_orders_full_list': [],
                    'current_tp': dynamic_tp,
                    'current_sl': dynamic_sl,
                    'highest_price_seen': current_high,
                    'lowest_price_seen': current_low
                }
                self.open_trades.append(first_grid_order)

                prev_size = trade_size
                for level in range(self.grid_levels):
                    grid_order_price = entry - (entry * self.grid_step_pct * (level + 1))
                    grid_order_size = prev_size * self.martingale_factor
                    prev_size = grid_order_size

                    pending_grid_order = {
                        'entry_date': self.hist_df.index[self.current_step],
                        'entry_step': self.current_step,
                        'type': 'Buy Stop',
                        'entry_price': grid_order_price,
                        'tp': dynamic_tp,
                        'sl': dynamic_sl,
                        'initial_sl': dynamic_sl,
                        'size': grid_order_size,
                        'grid_id': grid_id,
                        'order_level': level + 1
                    }
                    new_grid['pending_grid_orders_full_list'].append(pending_grid_order)

                self.active_grids[grid_id] = new_grid

                if len(new_grid['pending_grid_orders_full_list']) > 0:
                    self.pending_orders.append(new_grid['pending_grid_orders_full_list'][0])

                reward += 0.2 * 0.5
            else:
                reward += -0.1 * 0.5

        elif action == 4:
            if not filtered and (
                current_rsi < self.rsi_oversold_bonus_threshold and
                current_macd < current_macd_signal
            ):
                grid_id = self._generate_grid_id()
                entry = hist["Close"]
                trade_size = self.base_position_size

                if current_atr > 0:
                    trade_size *= (1 - (current_atr * self.volatility_inverse_factor))
                if current_rsi < self.rsi_oversold_bonus_threshold:
                    trade_size *= 1.2
                if current_macd_diff < -self.macd_strong_trend_threshold:
                    trade_size *= 1.1
                trade_size = max(0.1, trade_size)

                dynamic_tp = entry - (current_atr * self.grid_tp_multiplier)
                dynamic_sl = entry + (current_atr * self.grid_sl_multiplier)

                first_grid_order = {
                    'entry_date': self.hist_df.index[self.current_step],
                    'entry_step': self.current_step,
                    'type': 'Sell Market',
                    'entry_price': entry,
                    'tp': dynamic_tp,
                    'sl': dynamic_sl,
                    'initial_sl': dynamic_sl,
                    'size': trade_size,
                    'grid_id': grid_id,
                    'order_level': 0
                }

                new_grid = {
                    'type': 'SellGrid',
                    'initial_entry_date': self.hist_df.index[self.current_step],
                    'initial_entry_step': self.current_step,
                    'initial_entry_price': entry,
                    'total_filled_size': trade_size,
                    'current_avg_price': entry,
                    'filled_orders': [first_grid_order],
                    'pending_grid_orders_full_list': [],
                    'current_tp': dynamic_tp,
                    'current_sl': dynamic_sl,
                    'highest_price_seen': current_high,
                    'lowest_price_seen': current_low
                }
                self.open_trades.append(first_grid_order)

                prev_size = trade_size
                for level in range(self.grid_levels):
                    grid_order_price = entry + (entry * self.grid_step_pct * (level + 1))
                    grid_order_size = prev_size * self.martingale_factor
                    prev_size = grid_order_size

                    pending_grid_order = {
                        'entry_date': self.hist_df.index[self.current_step],
                        'entry_step': self.current_step,
                        'type': 'Sell Stop',
                        'entry_price': grid_order_price,
                        'tp': dynamic_tp,
                        'sl': dynamic_sl,
                        'initial_sl': dynamic_sl,
                        'size': grid_order_size,
                        'grid_id': grid_id,
                        'order_level': level + 1
                    }
                    new_grid['pending_grid_orders_full_list'].append(pending_grid_order)

                self.active_grids[grid_id] = new_grid

                if len(new_grid['pending_grid_orders_full_list']) > 0:
                    self.pending_orders.append(new_grid['pending_grid_orders_full_list'][0])

                reward += 0.2 * 0.5
            else:
                reward += -0.1 * 0.5

        else:
            reward += -0.1
            if (
                40 < current_rsi < 60 and
                abs(current_macd_diff) < 0.05
            ):
                reward += 0.2

            elif not (
                (40 < current_rsi < 60) and
                (abs(current_macd_diff) < 0.05)
            ):
                if (current_rsi > self.rsi_overbought_bonus_threshold or current_rsi < self.rsi_oversold_bonus_threshold or
                    abs(current_macd_diff) > self.macd_strong_trend_threshold):
                    reward -= 0.05

        self.rewards_history.append(reward)

        self.current_step += 1

        done = self.current_step >= len(self.hist_df) or self.current_step >= len(self.gen_df)

        if done:
            next_obs = np.zeros(self.observation_space.shape, dtype=np.float32)
        else:
            next_obs = self._get_obs()

        return next_obs, reward, done, False, {}

# --- Helper function to get default dates ---
def get_default_dates():
    today = datetime.now()
    end_date_str = today.strftime('%Y-%m-%d')
    start_date_str = (today - timedelta(days=365*2)).strftime('%Y-%m-%d')
    return start_date_str, end_date_str

default_start_date, default_end_date = get_default_dates()

# --- RedirectedMockWebSocketClient definition ---
class RedirectedMockWebSocketClient:
    def __init__(self, output_widget, broker_api: MockBrokerAPI, symbol="EURUSD", initial_price=1.20000, price_volatility=0.0001, stream_interval=1.0, on_data_received=None):
        self.output_widget = output_widget
        self.broker_api = broker_api # Store broker_api
        self.symbol = symbol
        self._current_price = initial_price
        self.price_volatility = price_volatility
        self.stream_interval = stream_interval
        self.on_data_received = on_data_received
        self._streaming = False
        self._thread = None
        self._lock = threading.Lock()

    def _simulate_price_stream(self):
        while self._streaming:
            with self._lock:
                market_info = self.broker_api.get_market_info(self.symbol)
                digits = market_info.get('MODE_DIGITS', 5)
                change = (random.random() - 0.5) * self.price_volatility
                self._current_price = _normalize_double_helper(self._current_price + change, digits)
                market_data = {'symbol': self.symbol, 'price': self._current_price, 'timestamp': datetime.now().isoformat()}

            with self.output_widget:
                self.output_widget.append_stdout(f"WS Stream: {market_data['symbol']} Price: {market_data['price']}\n")

            if self.on_data_received:
                self.on_data_received(market_data)

            time.sleep(self.stream_interval)

    def connect(self):
        if not self._streaming:
            self._streaming = True
            self._thread = threading.Thread(target=self._simulate_price_stream)
            self._thread.daemon = True
            self._thread.start()
            with self.output_widget:
                self.output_widget.append_stdout(f"WebSocket stream STARTED for {self.symbol}.\n")

    def disconnect(self):
        if self._streaming:
            self._streaming = False
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=self.stream_interval * 2)
            with self.output_widget:
                self.output_widget.append_stdout(f"WebSocket stream STOPPED for {self.symbol}.\n")

# --- Global Paths ---
# drive.mount('/content/drive') # Commented out to prevent credential propagation error when run by agent
base_path = "/content/drive/MyDrive/GeneratedDefinition"
journal_path = os.path.join(base_path, "TradeJournal")

os.makedirs(base_path, exist_ok=True)
os.makedirs(os.path.join(journal_path, "charts"), exist_ok=True)

# --- TradingSession Class to encapsulate global trading components ---
class TradingSession:
    def __init__(self, market_manager_output_area):
        self.market_manager_output_area = market_manager_output_area
        self.mock_broker_api = MockBrokerAPI(error_rate=0.1) # Moderate error rate for testing
        self.order_manager = OrderManager(
            broker_api=self.mock_broker_api,
            retry_attempts=3,
            sleep_time=0.1,
            sleep_maximum=0.5,
            max_close_duration=5.0,
            on_order_closed=self.manual_order_closed_callback
        )
        self.mock_websocket_client = RedirectedMockWebSocketClient(
            output_widget=self.market_manager_output_area,
            broker_api=self.mock_broker_api,
            symbol="EURUSD",
            initial_price=1.20000,
            price_volatility=0.0001,
            stream_interval=1.0,
            on_data_received=lambda data: None # Placeholder for strategy data processing
        )
        self.is_trading_active = False

    def manual_order_closed_callback(self, ticket_id: int, success: bool, close_price: float, pnl: float, order_details: dict, exit_reason: str):
        event_details = {
            'ticket_id': ticket_id,
            'success': success,
            'close_price': close_price,
            'pnl': pnl,
            'order_details': order_details,
            'exit_reason': exit_reason,
            'timestamp': time.time()
        }
        # Assuming `closed_orders_log_manual` is still needed for global logging or specific analysis
        # For now, it's commented out to simplify; if needed, it should be made an attribute of TradingSession or passed to it.
        # closed_orders_log_manual.append(event_details)
        with self.market_manager_output_area:
            if success:
                self.market_manager_output_area.append_stdout(f"CALLBACK: Order {ticket_id} successfully closed at {close_price} (PnL: {pnl:.2f})\n")
            else:
                self.market_manager_output_area.append_stdout(f"CALLBACK: Order {ticket_id} failed to close. Final price: {close_price} (Reason: {exit_reason})\n")


# --- Output Areas ---
output_area = widgets.Output() # For main simulation output
market_manager_output_area = widgets.Output() # For Market Manager output

# --- Create a single global instance of TradingSession ---
trading_session = TradingSession(market_manager_output_area=market_manager_output_area)


# --- Widget Definitions ---
# Note: default_start_date, default_end_date are defined above.
data_fetching_widgets = {
    'symbol': widgets.Text(value='TSLA', description='Symbol:', disabled=False),
    'timeframe': widgets.Dropdown(options=['1d', '5min', '15min', '30min', '60min'], value='1d', description='Timeframe:'),
    'start_date': widgets.Text(value=default_start_date, description='Start Date:', disabled=False),
    'end_date': widgets.Text(value=default_end_date, description='End Date:', disabled=False),
    'alpha_vantage_api_key': widgets.Text(
        value='YOUR_ALPHA_VANTAGE_API_KEY',
        description='AV API Key:',
        disabled=False
    ),
    'broker_selection': widgets.Dropdown(
        options=[
            'None', 'Interactive Brokers', 'IG Markets', 'CMC Markets', 'Tradier',
            'Capital.com', 'FOREX.com', 'Dukascopy', 'Binance', 'Bybit', 'Kraken',
            'MetaTrader 5', 'QuantConnect', 'Tastytrade', 'Zacks Trade', 'Optimus Futures'
        ],
        value='None',
        description='Broker:'
    ),
    'broker_api_key': widgets.Text(
        value='YOUR_BROKER_API_KEY',
        description='Broker API Key:',
        disabled=False
    )
}
lstm_widgets = {
    'sequence_length': widgets.IntSlider(value=20, min=5, max=100, step=5, description='Seq Length:'),
    'lstm_epochs': widgets.IntSlider(value=50, min=10, max=100, step=10, description='LSTM Epochs:'),
    'lstm_batch_size': widgets.IntSlider(value=64, min=16, max=128, step=16, description='LSTM Batch Size:'),
    'lstm_learning_rate': widgets.FloatSlider(value=0.001, min=0.0001, max=0.01, step=0.0001, description='LSTM LR:'),
    'lstm_units_1': widgets.IntSlider(value=64, min=16, max=128, step=16, description='LSTM Units 1:'),
    'lstm_units_2': widgets.IntSlider(value=32, min=16, max=128, step=16, description='LSTM Units 2:')
}
pivot_env_widgets = {
    'balance': widgets.FloatSlider(value=10000.0, min=1000.0, max=100000.0, step=1000.0, description='Balance:'),
    'base_position_size': widgets.FloatSlider(value=1.0, min=0.01, max=10.0, step=0.01, description='Base Pos Size:'),
    'volatility_inverse_factor': widgets.FloatSlider(value=0.01, min=0.0, max=0.1, step=0.001, description='Vol Inv Factor:'),
    'drawdown_penalty_percentage': widgets.FloatSlider(value=0.05, min=0.01, max=0.2, step=0.01, description='DD Penalty %:'),
    'drawdown_high_watermark_bonus': widgets.FloatSlider(value=0.005, min=0.001, max=0.05, step=0.001, description='DD HW Bonus:'),
    'transaction_cost_pct': widgets.FloatSlider(value=0.0005, min=0.0001, max=0.001, step=0.0001, description='Tx Cost %:'),
    'time_decay_threshold_steps': widgets.IntSlider(value=5, min=1, max=20, step=1, description='Time Decay Threshold:'),
    'time_decay_penalty_per_step': widgets.FloatSlider(value=-0.02, min=-0.1, max=0.0, step=0.01, description='Time Decay Penalty:'),
    'profit_threshold_for_decay': widgets.FloatSlider(value=0.01, min=0.0, max=0.1, step=0.005, description='Profit Thresh Decay:'),
    'early_exit_lookahead_steps': widgets.IntSlider(value=5, min=1, max=10, step=1, description='Early Exit Lookahead:'),
    'early_exit_reward_factor': widgets.FloatSlider(value=0.5, min=0.0, max=1.0, step=0.1, description='Early Exit Reward Factor:'),
    'early_exit_pnl_threshold_pct': widgets.FloatSlider(value=0.001, min=0.0, max=0.01, step=0.0001, description='Early Exit PnL Thresh %:'),
    'grid_levels': widgets.IntSlider(value=3, min=1, max=5, step=1, description='Grid Levels:'),
    'grid_step_pct': widgets.FloatSlider(value=0.005, min=0.001, max=0.01, step=0.001, description='Grid Step %:'),
    'martingale_factor': widgets.FloatSlider(value=1.1, min=1.0, max=2.0, step=0.1, description='Martingale Factor:'),
    'max_total_exposure': widgets.FloatSlider(value=10.0, min=1.0, max=50.0, step=1.0, description='Max Total Exposure:'),
    'grid_tp_multiplier': widgets.FloatSlider(value=1.5, min=0.5, max=3.0, step=0.1, description='Grid TP Multiplier:'),
    'grid_sl_multiplier': widgets.FloatSlider(value=1.0, min=0.5, max=3.0, step=0.1, description='Grid SL Multiplier:'),
    'adaptive_averaging_enabled': widgets.Checkbox(
        value=False,
        description='Adaptive Averaging Enabled:',
        disabled=False
    ),
    'averaging_trigger_pct': widgets.FloatSlider(
        value=0.01,
        min=0.001,
        max=0.05,
        step=0.001,
        description='Avg Trigger %:'
    ),
    'max_averaging_levels': widgets.IntSlider(
        value=2,
        min=0,
        max=5,
        step=1,
        description='Max Avg Levels:'
    ),
    'averaging_step_pct': widgets.FloatSlider(
        value=0.005,
        min=0.001,
        max=0.02,
        step=0.001,
        description='Avg Step %:'
    ),
    'averaging_tp_sl_mode': widgets.Dropdown(
        options=['consolidated', 'individual'],
        value='consolidated',
        description='Avg TP/SL Mode:'
    ),
    'averaging_volatility_threshold_atr': widgets.FloatSlider(
        value=0.5,
        min=0.1,
        max=2.0,
        step=0.1,
        description='Avg Vol Threshold ATR:'
    ),
    'max_averaging_drawdown_pct': widgets.FloatSlider(
        value=0.05,
        min=0.01,
        max=0.1,
        step=0.01,
        description='Max Avg DD %:'
    ),
    'dynamic_martingale_rsi_extreme_threshold': widgets.IntSlider(
        value=20,
        min=10,
        max=40,
        step=5,
        description='Dyn Martingale RSI Ext Thresh:'
    ),
    'dynamic_martingale_macd_neutral_threshold': widgets.FloatSlider(
        value=0.01,
        min=0.0,
        max=0.05,
        step=0.001,
        description='Dyn Martingale MACD Neut Thresh:'
    ),
    'averaging_tp_improvement_factor': widgets.FloatSlider(
        value=0.001,
        min=0.0,
        max=0.01,
        step=0.0001,
        description='Avg TP Improve Factor:'
    ),
    'averaging_bonus_factor': widgets.FloatSlider(
        value=0.1,
        min=0.0,
        max=0.5,
        step=0.01,
        description='Avg Bonus Factor:'
    ),
    'averaging_penalty_factor': widgets.FloatSlider(
        value=-0.05,
        min=-0.2,
        max=0.0,
        step=0.01,
        description='Avg Penalty Factor:'
    ),
    'atr_filter_threshold': widgets.FloatSlider(
        value=0.00,
        min=0.0,
        max=1.0,
        step=0.01,
        description='ATR Filter Thresh:'
    ),
    'bb_width_filter_threshold': widgets.FloatSlider(
        value=0.0,
        min=0.0,
        max=20.0,
        step=0.1,
        description='BB Width Filter Thresh:'
    ),
    'macd_signal_coincide_threshold': widgets.FloatSlider(
        value=0.00,
        min=0.0,
        max=0.1,
        step=0.005,
        description='MACD Signal Coincide Thresh:'
    ),
    'rsi_oversold_bonus_threshold': widgets.IntSlider(
        value=30,
        min=10,
        max=40,
        step=1,
        description='RSI Oversold Thresh:'
    ),
    'rsi_overbought_bonus_threshold': widgets.IntSlider(
        value=70,
        min=60,
        max=90,
        step=1,
        description='RSI Overbought Thresh:'
    ),
    'macd_strong_trend_threshold': widgets.FloatSlider(
        value=0.0,
        min=0.00,
        max=0.2,
        step=0.01,
        description='MACD Strong Trend Thresh:'
    ),
    'rsi_extreme_threshold': widgets.IntSlider(
        value=0,
        min=0,
        max=30,
        step=1,
        description='RSI Extreme Thresh:'
    ),
    'macd_cross_threshold': widgets.FloatSlider(
        value=0.00,
        min=0.00,
        max=0.1,
        step=0.01,
        description='MACD Cross Thresh:'
    )
}
ppo_widgets = {
    'ppo_total_timesteps': widgets.IntSlider(value=50000, min=10000, max=500000, step=10000, description='PPO Total Timesteps:'),
    'rl_algorithm': widgets.Dropdown(
        options=['PPO', 'DQN', 'A2C', 'SAC'],
        value='PPO',
        description='RL Algorithm:'
    )
}

# --- New: RL Algorithm Hyperparameters ---
rl_algo_hyperparameters_widgets = {}

# PPO Parameters
ppo_core_params = [
    widgets.IntSlider(value=2048, min=128, max=8192, step=128, description='PPO n_steps:'),
    widgets.IntSlider(value=64, min=16, max=256, step=16, description='PPO batch_size:'),
    widgets.IntSlider(value=10, min=1, max=20, step=1, description='PPO n_epochs:'),
    widgets.FloatSlider(value=0.0003, min=0.00001, max=0.001, step=0.00001, description='PPO learning_rate:'),
    widgets.FloatSlider(value=0.99, min=0.9, max=0.999, step=0.001, description='PPO gamma:'),
    widgets.FloatSlider(value=0.95, min=0.8, max=0.99, step=0.01, description='PPO gae_lambda:')
]
ppo_policy_value_params = [
    widgets.FloatSlider(value=0.2, min=0.05, max=0.5, step=0.01, description='PPO clip_range:'),
    widgets.FloatSlider(value=0.0, min=0.0, max=0.1, step=0.001, description='PPO ent_coef:'),
    widgets.FloatSlider(value=0.5, min=0.1, max=1.0, step=0.1, description='PPO vf_coef:'),
    widgets.FloatSlider(value=0.5, min=0.1, max=1.0, step=0.1, description='PPO max_grad_norm:')
]
ppo_vbox_core = widgets.VBox(ppo_core_params)
ppo_vbox_policy = widgets.VBox(ppo_policy_value_params)
ppo_tab_children = [ppo_vbox_core, ppo_vbox_policy]
ppo_tab_titles = ['Core Parameters', 'Policy & Value Function']
ppo_param_tabs = widgets.Tab(children=ppo_tab_children)
for i, title in enumerate(ppo_tab_titles): ppo_param_tabs.set_title(i, title)
rl_algo_hyperparameters_widgets['PPO'] = ppo_param_tabs

# DQN Parameters
dqn_core_params = [
    widgets.FloatSlider(value=0.99, min=0.9, max=0.999, step=0.001, description='DQN gamma:'),
    widgets.IntSlider(value=100000, min=10000, max=1000000, step=10000, description='DQN buffer_size:'),
    widgets.IntSlider(value=32, min=16, max=128, step=16, description='DQN batch_size:'),
    widgets.FloatSlider(value=0.0001, min=0.00001, max=0.001, step=0.00001, description='DQN learning_rate:'),
    widgets.IntSlider(value=50000, min=10000, max=200000, step=10000, description='DQN learning_starts:')
]
dqn_target_expl_params = [
    widgets.FloatSlider(value=1.0, min=0.5, max=1.0, step=0.05, description='DQN tau:'),
    widgets.IntSlider(value=10000, min=1000, max=50000, step=1000, description='DQN target_update_interval:'),
    widgets.IntSlider(value=4, min=1, max=10, step=1, description='DQN train_freq (steps):'),
    widgets.IntSlider(value=1, min=1, max=5, step=1, description='DQN gradient_steps:'),
    widgets.FloatSlider(value=0.1, min=0.01, max=0.5, step=0.01, description='DQN exploration_fraction:'),
    widgets.FloatSlider(value=1.0, min=0.1, max=1.0, step=0.05, description='DQN exploration_initial_eps:'),
    widgets.FloatSlider(value=0.05, min=0.01, max=0.2, step=0.01, description='DQN exploration_final_eps:')
]
dqn_vbox_core = widgets.VBox(dqn_core_params)
dqn_vbox_target_expl = widgets.VBox(dqn_target_expl_params)
dqn_tab_children = [dqn_vbox_core, dqn_vbox_target_expl]
dqn_tab_titles = ['Core Parameters', 'Target Network & Exploration']
dqn_param_tabs = widgets.Tab(children=dqn_tab_children)
for i, title in enumerate(dqn_tab_titles): dqn_param_tabs.set_title(i, title)
rl_algo_hyperparameters_widgets['DQN'] = dqn_param_tabs

# A2C Parameters
a2c_core_params = [
    widgets.FloatSlider(value=0.99, min=0.9, max=0.999, step=0.001, description='A2C gamma:'),
    widgets.IntSlider(value=5, min=1, max=20, step=1, description='A2C n_steps:'),
    widgets.FloatSlider(value=0.0007, min=0.00001, max=0.001, step=0.00001, description='A2C learning_rate:'),
    widgets.FloatSlider(value=0.95, min=0.8, max=0.99, step=0.01, description='A2C gae_lambda:')
]
a2c_policy_value_params = [
    widgets.FloatSlider(value=0.5, min=0.1, max=1.0, step=0.1, description='A2C vf_coef:'),
    widgets.FloatSlider(value=0.0, min=0.0, max=0.1, step=0.001, description='A2C ent_coef:'),
    widgets.FloatSlider(value=0.5, min=0.1, max=1.0, step=0.1, description='A2C max_grad_norm:')
]
a2c_vbox_core = widgets.VBox(a2c_core_params)
a2c_vbox_policy = widgets.VBox(a2c_policy_value_params)
a2c_tab_children = [a2c_vbox_core, a2c_vbox_policy]
a2c_tab_titles = ['Core Parameters', 'Policy & Value Function']
a2c_param_tabs = widgets.Tab(children=a2c_tab_children)
for i, title in enumerate(a2c_tab_titles): dqn_param_tabs.set_title(i, title)
rl_algo_hyperparameters_widgets['A2C'] = a2c_param_tabs

# SAC Parameters
sac_core_params = [
    widgets.FloatSlider(value=0.99, min=0.9, max=0.999, step=0.001, description='SAC gamma:'),
    widgets.IntSlider(value=1000000, min=100000, max=2000000, step=100000, description='SAC buffer_size:'),
    widgets.IntSlider(value=256, min=16, max=512, step=16, description='SAC batch_size:'),
    widgets.FloatSlider(value=0.0003, min=0.00001, max=0.001, step=0.00001, description='SAC learning_rate:')
]
sac_target_expl_params = [
    widgets.FloatSlider(value=0.005, min=0.001, max=0.01, step=0.001, description='SAC tau:'),
    widgets.IntSlider(value=1, min=1, max=10, step=1, description='SAC train_freq (steps):'),
    widgets.IntSlider(value=1, min=1, max=5, step=1, description='SAC gradient_steps:'),
    widgets.FloatSlider(value=0.0, min=0.0, max=0.1, step=0.001, description='SAC ent_coef (auto=0.0):'),
    widgets.IntSlider(value=10000, min=1000, max=50000, step=1000, description='SAC learning_starts:')
]
sac_vbox_core = widgets.VBox(sac_core_params)
sac_vbox_target_expl = widgets.VBox(sac_target_expl_params)
sac_tab_children = [sac_vbox_core, sac_vbox_target_expl]
sac_tab_titles = ['Core Parameters', 'Target Network & Exploration']
sac_param_tabs = widgets.Tab(children=sac_tab_children)
for i, title in enumerate(sac_tab_titles): dqn_param_tabs.set_title(i, title)
rl_algo_hyperparameters_widgets['SAC'] = sac_param_tabs

# Create the main Tab widget for RL Algorithm Hyperparameters
rl_algo_tab_children = []
rl_algo_tab_titles = []

for algo_name, algo_widgets_tab in rl_algo_hyperparameters_widgets.items():
    rl_algo_tab_children.append(algo_widgets_tab)
    rl_algo_tab_titles.append(algo_name)

rl_algo_param_tabs = widgets.Tab(children=rl_algo_tab_children)
for i, title in enumerate(rl_algo_tab_titles): rl_algo_param_tabs.set_title(i, title)

# --- Main Simulation Function ---
def run_simulation_with_params(b):
    with output_area:
        clear_output()
        print("Running simulation with selected parameters...")

        params = {}
        for key, widget in data_fetching_widgets.items(): params[key] = widget.value
        for key, widget in lstm_widgets.items(): params[key] = widget.value
        for key, widget in pivot_env_widgets.items(): params[key] = widget.value
        for key, widget in ppo_widgets.items(): params[key] = widget.value

        # Collect algorithm-specific hyperparameters
        selected_algo = params['rl_algorithm']
        params['algo_hyperparams'] = {selected_algo: {}}

        if selected_algo == 'PPO':
            for widget in ppo_core_params:
                param_name = widget.description.replace('PPO ', '').replace(':', '')
                params['algo_hyperparams'][selected_algo][param_name] = widget.value
            for widget in ppo_policy_value_params:
                param_name = widget.description.replace('PPO ', '').replace(':', '')
                params['algo_hyperparams'][selected_algo][param_name] = widget.value
        elif selected_algo == 'DQN':
            for widget in dqn_core_params:
                param_name = widget.description.replace('DQN ', '').replace(' (steps):', '').replace(':', '')
                params['algo_hyperparams'][selected_algo][param_name] = widget.value
            for widget in dqn_target_expl_params:
                param_name = widget.description.replace('DQN ', '').replace(' (steps):', '').replace(':', '')
                if param_name == 'train_freq':
                    params['algo_hyperparams'][selected_algo][param_name] = (widget.value, 'step')
                else:
                    params['algo_hyperparams'][selected_algo][param_name] = widget.value
        elif selected_algo == 'A2C':
            for widget in a2c_core_params:
                param_name = widget.description.replace('A2C ', '').replace(':', '')
                params['algo_hyperparams'][selected_algo][param_name] = widget.value
            for widget in a2c_policy_value_params:
                param_name = widget.description.replace('A2C ', '').replace(':', '')
                params['algo_hyperparams'][selected_algo][param_name] = widget.value
        elif selected_algo == 'SAC':
            # Check action space compatibility for SAC
            if isinstance(env.action_space.original_space, Discrete): # Check original_space if wrapped in DummyVecEnv
                print(f"? Error: The SAC algorithm in Stable Baselines3 is primarily designed for continuous (Box) action spaces. "
                      f"Your environment's action space is Discrete({env.action_space.original_space.n}). "
                      f"Please choose PPO, DQN, or A2C, or modify the environment's action space to be continuous to use SAC.")
                return # Exit the simulation function early
            else:
                # If it somehow supports Box for discrete actions, proceed
                model = SAC("MlpPolicy", env, verbose=0, **params['algo_hyperparams']['SAC'])
        else:
            raise NotImplementedError(f"RL algorithm {params['rl_algorithm']} is not yet implemented or recognized.")

        print("\n--- Collected Parameters ---")
        for k, v in params.items(): print(f"{k}: {v}")
        print("--------------------------")

        try:
            print(f"Fetching data for {params['symbol']} ({params['timeframe']})...")
            data = fetch_data(params['symbol'],
                              timeframe=params['timeframe'],
                              alpha_key=params['alpha_vantage_api_key'],
                              start_date=params['start_date'],
                              end_date=params['end_date'],
                              broker_api=trading_session.mock_broker_api)

            if data.empty:
                raise ValueError(f"No data fetched for {params['symbol']} with timeframe {params['timeframe']}. Exiting.")

            data.columns = [col.capitalize() for col in data.columns]
            close_series = data["Close"].squeeze()
            rsi = RSIIndicator(close=close_series, window=14)
            macd = MACD(close=close_series)
            data["RSI"] = rsi.rsi()
            data["MACD"] = macd.macd()
            data["MACD_Signal"] = macd.macd_signal()

            bb = BollingerBands(close=close_series, window=20, window_dev=2)
            data["Bb_Middle"] = bb.bollinger_mavg()
            data["Bb_Upper"] = bb.bollinger_hband()
            data["Bb_Lower"] = bb.bollinger_lband()

            atr = AverageTrueRange(high=data["High"], low=data["Low"], close=data["Close"], window=14)
            data["ATR"] = atr.average_true_range()
            data["RSI_Cross_Count"] = count_rsi_crosses(data["RSI"])

            data.dropna(inplace=True)
            print("Data fetched and indicators calculated.")

            original_df = calculate_pivots(data.copy())
            print("Pivot points calculated for original data.")

            features = ["Open", "High", "Low", "Close", "Volume", "RSI", "MACD", "MACD_Signal", "RSI_Cross_Count", "Bb_Middle", "Bb_Upper", "Bb_Lower", "ATR"]
            missing_features = [f for f in features if f not in data.columns]
            if missing_features:
                raise ValueError(f"Missing required features in DataFrame: {missing_features}")

            # Call the new helper function for LSTM data generation
            generated_df = _generate_lstm_data(data, features, params, output_area, broker_api=trading_session.mock_broker_api, symbol=params['symbol'])

            # Save with index=True to preserve DatetimeIndex
            original_df.to_csv(os.path.join(base_path, "historical_df.csv"), index=True)
            generated_df.to_csv(os.path.join(base_path, "generated_df.csv"), index=True)
            print("Historical and generated data saved.")

            # Load with index_col=0 and parse_dates=True to restore DatetimeIndex
            historical_df_ppo = pd.read_csv(os.path.join(base_path, "historical_df.csv"), index_col=0, parse_dates=True)
            generated_df_ppo = pd.read_csv(os.path.join(base_path, "generated_df.csv"), index_col=0, parse_dates=True)

            close_series_ppo = historical_df_ppo["Close"].squeeze()
            if not isinstance(close_series_ppo, pd.Series):
                close_series_ppo = pd.Series(close_series_ppo)

            rsi_ppo = RSIIndicator(close=close_series_ppo, window=14)
            macd_ppo = MACD(close=close_series_ppo)
            historical_df_ppo["RSI"] = rsi_ppo.rsi()
            historical_df_ppo["MACD"] = macd_ppo.macd()
            historical_df_ppo["MACD_Signal"] = macd_ppo.macd_signal()

            bb_ppo = BollingerBands(close=close_series_ppo, window=20, window_dev=2)
            historical_df_ppo["Bb_Middle"] = bb_ppo.bollinger_mavg()
            historical_df_ppo["Bb_Upper"] = bb_ppo.bollinger_hband()
            historical_df_ppo["Bb_Lower"] = bb_ppo.bollinger_lband()

            atr_ppo = AverageTrueRange(high=historical_df_ppo["High"], low=historical_df_ppo["Low"], close=historical_df_ppo["Close"], window=14)
            historical_df_ppo["ATR"] = atr_ppo.average_true_range()

            historical_df_ppo.dropna(inplace=True)

            min_len_for_ppo_env = min(len(historical_df_ppo), len(generated_df_ppo))

            if min_len_for_ppo_env < 2:
                print("Not enough data for PPO environment after cleaning and alignment (min_len < 2). Skipping PPO training and visualization due to insufficient data.")
            else:
                historical_df_ppo = historical_df_ppo.iloc[:min_len_for_ppo_env] # Truncate, keep DatetimeIndex
                generated_df_ppo = generated_df_ppo.iloc[:min_len_for_ppo_env] # Truncate, keep DatetimeIndex

                env = DummyVecEnv([lambda: PivotEnv(
                    hist_df=historical_df_ppo,
                    gen_df=generated_df_ppo,
                    broker_api=trading_session.mock_broker_api, # Pass the mock broker API
                    order_manager=trading_session.order_manager, # Pass the order manager
                    grid_levels=params['grid_levels'],
                    grid_step_pct=params['grid_step_pct'],
                    martingale_factor=params['martingale_factor'],
                    max_total_exposure=params['max_total_exposure'],
                    grid_tp_multiplier=params['grid_tp_multiplier'],
                    grid_sl_multiplier=params['grid_sl_multiplier'],
                    base_position_size=params['base_position_size'],
                    volatility_inverse_factor=params['volatility_inverse_factor'],
                    drawdown_penalty_percentage=params['drawdown_penalty_percentage'],
                    drawdown_high_watermark_bonus=params['drawdown_high_watermark_bonus'],
                    transaction_cost_pct=params['transaction_cost_pct'],
                    time_decay_threshold_steps=params['time_decay_threshold_steps'],
                    time_decay_penalty_per_step=params['time_decay_penalty_per_step'],
                    profit_threshold_for_decay=params['profit_threshold_for_decay'],
                    early_exit_lookahead_steps=params['early_exit_lookahead_steps'],
                    early_exit_reward_factor=params['early_exit_reward_factor'],
                    early_exit_pnl_threshold_pct=params['early_exit_pnl_threshold_pct'],
                    adaptive_averaging_enabled=params['adaptive_averaging_enabled'],
                    averaging_trigger_pct=params['averaging_trigger_pct'],
                    max_averaging_levels=params['max_averaging_levels'],
                    averaging_step_pct=params['averaging_step_pct'],
                    averaging_tp_sl_mode=params['averaging_tp_sl_mode'],
                    averaging_volatility_threshold_atr=params['averaging_volatility_threshold_atr'],
                    max_averaging_drawdown_pct=params['max_averaging_drawdown_pct'],
                    dynamic_martingale_rsi_extreme_threshold=params['dynamic_martingale_rsi_extreme_threshold'],
                    dynamic_martingale_macd_neutral_threshold=params['dynamic_martingale_macd_neutral_threshold'],
                    averaging_tp_improvement_factor=params['averaging_tp_improvement_factor'],
                    averaging_bonus_factor=params['averaging_bonus_factor'],
                    averaging_penalty_factor=params['averaging_penalty_factor'],
                    atr_filter_threshold=params['atr_filter_threshold'],
                    bb_width_filter_threshold=params['bb_width_filter_threshold'],
                    macd_signal_coincide_threshold=params['macd_signal_coincide_threshold'],
                    rsi_oversold_bonus_threshold=params['rsi_oversold_bonus_threshold'],
                    rsi_overbought_bonus_threshold=params['rsi_overbought_bonus_threshold'],
                    macd_strong_trend_threshold=params['macd_strong_trend_threshold'],
                    rsi_extreme_threshold=params['rsi_extreme_threshold'],
                    macd_cross_threshold=params['macd_cross_threshold']
                )])

                print(f"Training {params['rl_algorithm']} model for {params['ppo_total_timesteps']} timesteps...")

                model = None
                # Use collected algorithm-specific hyperparameters when initializing the model
                if params['rl_algorithm'] == 'PPO':
                    model = PPO("MlpPolicy", env, verbose=0, **params['algo_hyperparams']['PPO'])
                elif params['rl_algorithm'] == 'DQN':
                    model = DQN("MlpPolicy", env, verbose=0, **params['algo_hyperparams']['DQN'])
                elif params['rl_algorithm'] == 'A2C':
                    model = A2C("MlpPolicy", env, verbose=0, **params['algo_hyperparams']['A2C'])
                elif params['rl_algorithm'] == 'SAC':
                    # Check action space compatibility for SAC
                    if isinstance(env.action_space.original_space, Discrete): # Check original_space if wrapped in DummyVecEnv
                        print(f"? Error: The SAC algorithm in Stable Baselines3 is primarily designed for continuous (Box) action spaces. "
                              f"Your environment's action space is Discrete({env.action_space.original_space.n}). "
                              f"Please choose PPO, DQN, or A2C, or modify the environment's action space to be continuous to use SAC.")
                        return # Exit the simulation function early
                    else:
                        # If it somehow supports Box for discrete actions, proceed
                        model = SAC("MlpPolicy", env, verbose=0, **params['algo_hyperparams']['SAC'])
                else:
                    raise NotImplementedError(f"RL algorithm {params['rl_algorithm']} is not yet implemented or recognized.")

                model.learn(total_timesteps=params['ppo_total_timesteps'])
                model.save(os.path.join(base_path, f"{params['rl_algorithm'].lower()}_pivot_model_v2"))
                print(f"? {params['rl_algorithm']} model trained and saved.")

                actions, prices, indices, records = [], [], [], []
                env_instance = PivotEnv(
                    hist_df=historical_df_ppo,
                    gen_df=generated_df_ppo,
                    broker_api=trading_session.mock_broker_api, # Pass the mock broker API
                    order_manager=trading_session.order_manager, # Pass the order manager
                    grid_levels=params['grid_levels'],
                    grid_step_pct=params['grid_step_pct'],
                    martingale_factor=params['martingale_factor'],
                    max_total_exposure=params['max_total_exposure'],
                    grid_tp_multiplier=params['grid_tp_multiplier'],
                    grid_sl_multiplier=params['grid_sl_multiplier'],
                    base_position_size=params['base_position_size'],
                    volatility_inverse_factor=params['volatility_inverse_factor'],
                    drawdown_penalty_percentage=params['drawdown_penalty_percentage'],
                    drawdown_high_watermark_bonus=params['drawdown_high_watermark_bonus'],
                    transaction_cost_pct=params['transaction_cost_pct'],
                    time_decay_threshold_steps=params['time_decay_threshold_steps'],
                    time_decay_penalty_per_step=params['time_decay_penalty_per_step'],
                    profit_threshold_for_decay=params['profit_threshold_for_decay'],
                    early_exit_lookahead_steps=params['early_exit_lookahead_steps'],
                    early_exit_reward_factor=params['early_exit_reward_factor'],
                    early_exit_pnl_threshold_pct=params['early_exit_pnl_threshold_pct'],
                    adaptive_averaging_enabled=params['adaptive_averaging_enabled'],
                    averaging_trigger_pct=params['averaging_trigger_pct'],
                    max_averaging_levels=params['max_averaging_levels'],
                    averaging_step_pct=params['averaging_step_pct'],
                    averaging_tp_sl_mode=params['averaging_tp_sl_mode'],
                    averaging_volatility_threshold_atr=params['averaging_volatility_threshold_atr'],
                    max_averaging_drawdown_pct=params['max_averaging_drawdown_pct'],
                    dynamic_martingale_rsi_extreme_threshold=params['dynamic_martingale_rsi_extreme_threshold'],
                    dynamic_martingale_macd_neutral_threshold=params['dynamic_martingale_macd_neutral_threshold'],
                    averaging_tp_improvement_factor=params['averaging_tp_improvement_factor'],
                    averaging_bonus_factor=params['averaging_bonus_factor'],
                    averaging_penalty_factor=params['averaging_penalty_factor'],
                    atr_filter_threshold=params['atr_filter_threshold'],
                    bb_width_filter_threshold=params['bb_width_filter_threshold'],
                    macd_signal_coincide_threshold=params['macd_signal_coincide_threshold'],
                    rsi_oversold_bonus_threshold=params['rsi_oversold_bonus_threshold'],
                    rsi_overbought_bonus_threshold=params['rsi_overbought_bonus_threshold'],
                    macd_strong_trend_threshold=params['macd_strong_trend_threshold'],
                    rsi_extreme_threshold=params['rsi_extreme_threshold'],
                    macd_cross_threshold=params['macd_cross_threshold']
                )
                obs, _ = env_instance.reset()

                while True:
                    action, _ = model.predict(obs, deterministic=True)
                    action_scalar = action.item() if isinstance(action, np.ndarray) else action

                    current_step_for_record = env_instance.current_step

                    if current_step_for_record < len(historical_df_ppo):
                        row = historical_df_ppo.iloc[current_step_for_record]
                        price = row["Close"]
                        rsi = row["RSI"]
                        macd = row["MACD"]
                        signal = row["MACD_Signal"]

                        actions.append(action_scalar)
                        prices.append(price)
                        indices.append(current_step_for_record)

                        action_type = {
                            0: "None", 1: "Buy Stop", 2: "Sell Stop", 3: "Buy Market", 4: "Sell Market"
                        }.get(action_scalar, "Unknown")

                        records.append({
                            "Index": historical_df_ppo.index[current_step_for_record],
                            "Action": action_type,
                            "Price": price,
                            "RSI": rsi,
                            "MACD": macd,
                            "MACD_Signal": signal
                        })

                    obs, reward, done, _, _ = env_instance.step(action_scalar)
                    if done:
                        break

                ppo_rewards_series = pd.Series(env_instance.rewards_history, index=historical_df_ppo.index[:len(env_instance.rewards_history)])
                print(f"? Extracted rewards history with length: {len(ppo_rewards_series)}")

                trades_df = pd.DataFrame(env_instance.closed_trades)
                if not trades_df.empty:
                    trades_df.to_csv(os.path.join(journal_path, "trades_v2.csv"), index=False)
                    print("? Trades recorded in trades_v2.csv")
                else:
                    print("? No closed trades to record in trades_v2.csv")

                equity_curve = pd.Series(env_instance.equity_history)
                daily_drawdown = pd.Series()
                max_drawdown = 0.0

                if not equity_curve.empty:
                    roll_max = equity_curve.cummax()
                    daily_drawdown = (equity_curve - roll_max) / roll_max
                    max_drawdown = daily_drawdown.min()

                performance_stats = {"total_trades": len(env_instance.closed_trades)}
                if not trades_df.empty:
                    winning_trades = trades_df['pnl'][trades_df['pnl'] > 0]
                    losing_trades = trades_df['pnl'][trades_df['pnl'] < 0]

                    performance_stats["win_rate"] = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0
                    performance_stats["avg_profit"] = winning_trades.mean() if not winning_trades.empty else 0
                    performance_stats["avg_loss"] = losing_trades.mean() if not losing_trades.empty else 0
                    performance_stats["expectancy"] = (performance_stats["win_rate"] * performance_stats["avg_profit"]) + \
                                                    ((1 - performance_stats["win_rate"]) * performance_stats["avg_loss"])
                    performance_stats["max_drawdown"] = max_drawdown
                else:
                    performance_stats["max_drawdown"] = 0.0

                with open(os.path.join(journal_path, "performance_v2.json"), "w") as f:
                    json.dump(performance_stats, f, indent=4)
                print("? Performance statistics recorded: performance_v2.json")

                print("\nContent of performance_v2.json (after grid logic implementation):\n")
                print(json.dumps(performance_stats, indent=4))

                orders_df = pd.DataFrame(records)
                orders_df.to_csv(os.path.join(base_path, "pending_orders_v2.csv"), index=False)
                print("? Orders recorded in pending_orders_v2.csv")

                with output_area:
                    plt.figure(figsize=(18, 6))
                    plt.plot(historical_df_ppo.index, historical_df_ppo["Close"], label="Исторически Close", color="black", linewidth=1.5)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["Pivot"], label="Исторически Pivot", linestyle="--", color="green", linewidth=1.0)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["R1"], label="Исторически R1", linestyle="--", color="orange", linewidth=1.0)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["S1"], label="Исторически S1", linestyle="--", color="red", linewidth=1.0)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["R2"], label="Исторически R2", linestyle="--", color="purple", linewidth=1.0)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["S2"], label="Исторически S2", linestyle="--", color="brown", linewidth=1.0)

                    gen_indices_plot = pd.to_datetime(historical_df_ppo.index.max()) + pd.to_timedelta(np.arange(len(generated_df_ppo)) + 1, unit='d')
                    plt.plot(gen_indices_plot, generated_df_ppo["Close"], label="Генериран Товарен Цена", color="blue", linewidth=1.0)
                    plt.plot(gen_indices_plot, generated_df_ppo["Pivot"], label="Генериран Pivot", linestyle="-", color="darkgreen", linewidth=1.0, marker='o', markersize=3)
                    plt.plot(gen_indices_plot, generated_df_ppo["R1"], label="Генериран R1", linestyle="-", color="darkorange", linewidth=1.0, marker='x', markersize=3)
                    plt.plot(gen_indices_plot, generated_df_ppo["S1"], label="Генериран S1", linestyle="-", color="darkred", linewidth=1.0, marker='+', markersize=3)
                    plt.plot(gen_indices_plot, generated_df_ppo["R2"], label="Генериран R2", linestyle="-", color="darkmagenta", linewidth=1.0, marker='o', markersize=3)
                    plt.plot(gen_indices_plot, generated_df_ppo["S2"], label="Генериран S2", linestyle="-", color="saddlebrown", linewidth=1.0, marker='x', markersize=3)

                    plt.plot(historical_df_ppo.index, historical_df_ppo["Bb_Upper"], label="Исторически Bb Upper", linestyle=":", color="cyan", linewidth=0.8)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["Bb_Middle"], label="Исторически Bb Middle", linestyle=":", color="darkblue", linewidth=0.8)
                    plt.plot(historical_df_ppo.index, historical_df_ppo["Bb_Lower"], label="Исторически Bb Lower", linestyle=":", color="lightcyan", linewidth=0.8)

                    plt.plot(gen_indices_plot, generated_df_ppo["Bb_Upper"], label="Генериран Bb Upper", linestyle="--", color="blue", linewidth=0.8)
                    plt.plot(gen_indices_plot, generated_df_ppo["Bb_Middle"], label="Генериран Bb Middle", linestyle="--", color="navy", linewidth=0.8)
                    plt.plot(gen_indices_plot, generated_df_ppo["Bb_Lower"], label="Генериран Bb Lower", linestyle="--", color="teal", linewidth=0.8)

                    plt.plot(historical_df_ppo.index, historical_df_ppo["ATR"], label="Исторически ATR", linestyle=":", color="magenta", linewidth=0.8)

                    for i, act_val in enumerate(actions):
                        if indices[i] < len(historical_df_ppo):
                            plt.scatter(historical_df_ppo.index[indices[i]], prices[i], color="green" if act_val in [1,3] else "red",
                                        marker="^" if (act_val in [1,3]) else ("v" if (act_val in [2,4]) else "."), s=100, alpha=0.7,
                                        label="Buy" if (act_val in [1,3] and i == 0) else ("Sell" if (act_val in [2,4] and i == 0) else ""))

                    plt.title(f"{params['symbol']} — Исторически, Генерирани данни и действия на PPO агента (Ново Обучение v2)")
                    plt.xlabel("Дата")
                    plt.ylabel("Цена")
                    plt.legend(loc='best')
                    plt.grid(True)
                    plt.show()

                if not equity_curve.empty:
                    with output_area:
                        plt.figure(figsize=(12, 6))
                        equity_curve.plot(title="Equity Curve")
                        plt.xlabel("Step")
                        plt.ylabel("Balance")
                        plt.savefig(os.path.join(journal_path, "charts", "equity_curve_v2.png"))
                        plt.show()
                        print("? Графика на баланса записана: equity_curve_v2.png")

                    with output_area:
                        plt.figure(figsize=(12, 6))
                        daily_drawdown.plot(title="Drawdown")
                        plt.xlabel("Step")
                        plt.ylabel("Drawdown (%)")
                        plt.savefig(os.path.join(journal_path, "charts", "drawdown_v2.png"))
                        plt.show()
                        print("? Графика на drawdown записана: drawdown_v2.png")

                # User-provided email sending code
                send_email_with_attachments(
                    sender_email="aeksandar.kitipov@gmail.com",
                    sender_password="jtor pisd dgsx jsgo",  # това е паролата за приложение, която си създал
                    recipient_email="aleksandar.kitipov@abv.bg",
                    subject="Colab Simulation Results - " + datetime.now().strftime("%Y-%m-%d %H:%M"),
                    body="Здравейте,\n\nПрикачени са резултатите от симулацията на търговската стратегия, изпълнена в Colab.\n\nПоздрави,\nВашият Colab Агент",
                    attachment_paths=[
                        os.path.join(base_path, "historical_df.csv"),
                        os.path.join(base_path, "generated_df.csv"),
                        os.path.join(journal_path, "trades_v2.csv"),
                        os.path.join(journal_path, "performance_v2.json"),
                        os.path.join(journal_path, "charts", "equity_curve_v2.png"),
                        os.path.join(journal_path, "charts", "drawdown_v2.png"),
                    ]
                )
                print("? Email sent with simulation results.")

        except Exception as e:
            print(f"An error occurred during simulation: {e}")

# --- Market Manager Buttons ---
b_connect_broker = widgets.Button(description="Connect Broker", button_style='success')
b_disconnect_broker = widgets.Button(description="Disconnect Broker", button_style='danger')
b_start_trading = widgets.Button(description="Start Trading", button_style='primary')
b_stop_trading = widgets.Button(description="Stop Trading", button_style='warning')
b_open_buy = widgets.Button(description="Open Buy Order", button_style='success')
b_open_sell = widgets.Button(description="Open Sell Order", button_style='danger')
b_close_all = widgets.Button(description="Close All Positions", button_style='info')
b_view_positions = widgets.Button(description="View Open Positions", button_style='info')

# --- Button Handler Functions ---
def on_connect_broker_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        trading_session.market_manager_output_area.append_stdout("Connecting to broker (simulated)...\n")
        trading_session.mock_broker_api._trade_allowed = True
        trading_session.market_manager_output_area.append_stdout("Broker connected (simulated). Trading allowed: True.\n")

def on_disconnect_broker_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        trading_session.market_manager_output_area.append_stdout("Disconnecting from broker (simulated)...\n")
        trading_session.mock_broker_api._trade_allowed = False
        trading_session.market_manager_output_area.append_stdout("Broker disconnected (simulated). Trading allowed: False.\n")

def on_start_trading_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if not trading_session.is_trading_active:
            trading_session.is_trading_active = True
            trading_session.mock_websocket_client.connect()
            trading_session.market_manager_output_area.append_stdout("Trading strategy STARTED.\n")
        else:
            trading_session.market_manager_output_area.append_stdout("Trading strategy is already running.\n")

def on_stop_trading_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if trading_session.is_trading_active:
            trading_session.is_trading_active = False
            trading_session.mock_websocket_client.disconnect()
            trading_session.market_manager_output_area.append_stdout("Trading strategy STOPPED.\n")
        else:
            trading_session.market_manager_output_area.append_stdout("Trading strategy is already stopped.\n")

def on_open_buy_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if not trading_session.mock_broker_api.is_trade_allowed():
            trading_session.market_manager_output_area.append_stdout("ERROR: Cannot open BUY order. Broker is not connected or trading is not allowed.\n")
            return
        symbol = trading_session.mock_websocket_client.symbol
        current_ask = trading_session.mock_broker_api.get_market_info(symbol)['ask']

        trading_session.market_manager_output_area.append_stdout(f"Attempting to place BUY order for {symbol} at {current_ask}...\n")
        ticket = trading_session.order_manager.send_market_order_reliable(
            symbol=symbol,
            cmd=OP_BUY,
            volume=0.1,
            initial_price=current_ask,
            slippage=5,
            stoploss=0,
            takeprofit=0,
            comment="Manual Buy",
            magic=random.randint(1000, 9999)
        )
        if ticket != -1:
            trading_session.market_manager_output_area.append_stdout(f"BUY Order placed successfully: Ticket {ticket}, Volume: {trading_session.mock_broker_api._open_orders[ticket]['volume']:.2f}\n")
        else:
            trading_session.market_manager_output_area.append_stdout(f"Failed to place BUY order. Last error: {trading_session.order_manager.get_last_error()}\n")

def on_open_sell_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if not trading_session.mock_broker_api.is_trade_allowed():
            trading_session.market_manager_output_area.append_stdout("ERROR: Cannot open SELL order. Broker is not connected or trading is not allowed.\n")
            return
        symbol = trading_session.mock_websocket_client.symbol
        current_bid = trading_session.mock_broker_api.get_market_info(symbol)['bid']

        trading_session.market_manager_output_area.append_stdout(f"Attempting to place SELL order for {symbol} at {current_bid}...\n")
        ticket = trading_session.order_manager.send_market_order_reliable(
            symbol=symbol,
            cmd=OP_SELL,
            volume=0.1,
            initial_price=current_bid,
            slippage=5,
            stoploss=0,
            takeprofit=0,
            comment="Manual Sell",
            magic=random.randint(1000, 9999)
        )
        if ticket != -1:
            trading_session.market_manager_output_area.append_stdout(f"SELL Order placed successfully: Ticket {ticket}, Volume: {trading_session.mock_broker_api._open_orders[ticket]['volume']:.2f}\n")
        else:
            trading_session.market_manager_output_area.append_stdout(f"Failed to place SELL order. Last error: {trading_session.order_manager.get_last_error()}\n")

def on_close_all_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if not trading_session.mock_broker_api.is_trade_allowed():
            trading_session.market_manager_output_area.append_stdout("ERROR: Cannot close orders. Broker is not connected or trading is not allowed.\n")
            return

        open_orders_to_close = list(trading_session.mock_broker_api._open_orders.keys()) # Make a copy to iterate safely
        if not open_orders_to_close:
            trading_session.market_manager_output_area.append_stdout("No open positions to close.\n")
            return

        trading_session.market_manager_output_area.append_stdout(f"Attempting to close all {len(open_orders_to_close)} open positions...\n")
        for ticket_id in open_orders_to_close:
            if ticket_id not in trading_session.mock_broker_api._open_orders or trading_session.mock_broker_api._open_orders[ticket_id]['status'] != 'open':
                continue

            order_details = trading_session.mock_broker_api._open_orders[ticket_id]
            symbol = order_details['symbol']
            volume_to_close = order_details['volume']

            current_market_info = trading_session.mock_broker_api.get_market_info(symbol)
            if order_details['cmd'] == OP_BUY:
                closing_price = current_market_info['bid']
            elif order_details['cmd'] == OP_SELL:
                closing_price = current_market_info['ask']
            else:
                closing_price = current_market_info['bid'] # Default for pending, though should be handled by order manager

            # Calculate potential PnL for the callback
            pnl_gross = 0
            if order_details['cmd'] == OP_BUY:
                pnl_gross = (closing_price - order_details['open_price']) * order_details['volume']
            elif order_details['cmd'] == OP_SELL:
                pnl_gross = (order_details['open_price'] - closing_price) * order_details['volume']

            trading_session.market_manager_output_area.append_stdout(f"  Closing Ticket {ticket_id} (Volume: {volume_to_close:.2f})...\n")
            closed = trading_session.order_manager.close_order_reliable(ticket_id, volume_to_close, closing_price, 5, pnl=pnl_gross, order_details=order_details, exit_reason="Manual Close All")
            if closed:
                trading_session.market_manager_output_area.append_stdout(f"  Ticket {ticket_id} successfully closed.\n")
            else:
                trading_session.market_manager_output_area.append_stdout(f"  Failed to close Ticket {ticket_id}. Last error: {trading_session.order_manager.get_last_error()}\n")

def on_view_positions_clicked(b):
    with trading_session.market_manager_output_area:
        clear_output(wait=True)
        if not trading_session.mock_broker_api.is_trade_allowed():
            trading_session.market_manager_output_area.append_stdout("ERROR: Cannot view positions. Broker is not connected or trading is not allowed.\n")
            return

        open_positions = [order for order_id, order in trading_session.mock_broker_api._open_orders.items() if order['status'] == 'open']
        if not open_positions:
            trading_session.market_manager_output_area.append_stdout("No open positions to display.\n")
            return

        trading_session.market_manager_output_area.append_stdout(f"\n--- Open Positions ({len(open_positions)}) ---\n")
        for order in open_positions:
            cmd_str = "BUY" if order['cmd'] == OP_BUY else ("SELL" if order['cmd'] == OP_SELL else "PENDING")

            current_market_info = trading_session.mock_broker_api.get_market_info(order['symbol'])
            current_price = 0.0
            profit = 0.0

            if order['cmd'] == OP_BUY:
                current_price = current_market_info['bid']
                profit = (current_price - order['open_price']) * order['volume']
            elif order['cmd'] == OP_SELL:
                current_price = current_market_info['ask']
                profit = (order['open_price'] - current_price) * order['volume']
            elif order['cmd'] in [OP_BUYSTOP, OP_SELLSTOP, OP_BUYLIMIT, OP_SELLLIMIT]:
                current_price = current_market_info['bid'] # For pending, use bid as reference
                profit = 0.0 # No profit until filled

            trading_session.market_manager_output_area.append_stdout(
                f"Ticket: {order['ticket']}, Symbol: {order['symbol']}, Type: {cmd_str}, "
                f"Volume: {order['volume']:.2f}, Entry Price: {order['open_price']:.5f}, "
                f"Current Price: {current_price:.5f}, Profit: {profit:.2f}\n"
            )
        trading_session.market_manager_output_area.append_stdout("---------------------------\n")

# --- Organize ALL widgets into tabs/sections (Main Simulation Parameters) ---
tab_children = []
tab_titles = []

# Data Fetching Tab
df_vbox = widgets.VBox(list(data_fetching_widgets.values()))
tab_children.append(df_vbox)
tab_titles.append('Data Fetching')

# LSTM Parameters Tab
lstm_vbox = widgets.VBox(list(lstm_widgets.values()))
tab_children.append(lstm_vbox)
tab_titles.append('LSTM Parameters')

# PivotEnv Core Parameters (Balance, Pos Size, Costs, Decay, Early Exit)
pivot_core_widgets_list = [
    pivot_env_widgets['balance'], pivot_env_widgets['base_position_size'],
    pivot_env_widgets['volatility_inverse_factor'], pivot_env_widgets['transaction_cost_pct'],
    pivot_env_widgets['drawdown_penalty_percentage'], pivot_env_widgets['drawdown_high_watermark_bonus'],
    pivot_env_widgets['time_decay_threshold_steps'], pivot_env_widgets['time_decay_penalty_per_step'],
    pivot_env_widgets['profit_threshold_for_decay'],
    pivot_env_widgets['early_exit_lookahead_steps'], pivot_env_widgets['early_exit_reward_factor'],
    pivot_env_widgets['early_exit_pnl_threshold_pct']
]
pivot_core_vbox = widgets.VBox(pivot_core_widgets_list)
tab_children.append(pivot_core_vbox)
tab_titles.append('Env Core Params')

# Grid Strategy Parameters
grid_widgets_list = [
    pivot_env_widgets['grid_levels'], pivot_env_widgets['grid_step_pct'],
    pivot_env_widgets['martingale_factor'], pivot_env_widgets['max_total_exposure'],
    pivot_env_widgets['grid_tp_multiplier'], pivot_env_widgets['grid_sl_multiplier']
]
grid_vbox = widgets.VBox(grid_widgets_list)
tab_children.append(grid_vbox)
tab_titles.append('Grid Strategy')

# Adaptive Averaging Parameters
avg_widgets_list = [
    pivot_env_widgets['adaptive_averaging_enabled'], pivot_env_widgets['averaging_trigger_pct'],
    pivot_env_widgets['max_averaging_levels'], pivot_env_widgets['averaging_step_pct'],
    pivot_env_widgets['averaging_tp_sl_mode'], pivot_env_widgets['averaging_volatility_threshold_atr'],
    pivot_env_widgets['max_averaging_drawdown_pct'], pivot_env_widgets['dynamic_martingale_rsi_extreme_threshold'],
    pivot_env_widgets['dynamic_martingale_macd_neutral_threshold'],
    pivot_env_widgets['averaging_tp_improvement_factor'], pivot_env_widgets['averaging_bonus_factor'],
    pivot_env_widgets['averaging_penalty_factor']
]
avg_vbox = widgets.VBox(avg_widgets_list)
tab_children.append(avg_vbox)
tab_titles.append('Adaptive Averaging')

# Filtering/Indicator Thresholds Parameters
filter_widgets_list = [
    pivot_env_widgets['atr_filter_threshold'], pivot_env_widgets['bb_width_filter_threshold'],
    pivot_env_widgets['macd_signal_coincide_threshold'], pivot_env_widgets['rsi_oversold_bonus_threshold'],
    pivot_env_widgets['rsi_overbought_bonus_threshold'], pivot_env_widgets['macd_strong_trend_threshold'],
    pivot_env_widgets['rsi_extreme_threshold'], pivot_env_widgets['macd_cross_threshold']
]
filter_vbox = widgets.VBox(filter_widgets_list)
tab_children.append(filter_vbox)
tab_titles.append('Filters/Indicators')

# PPO Training Tab (now just basic PPO training params + RL algorithm selection)
ppo_vbox = widgets.VBox(list(ppo_widgets.values()))
tab_children.append(ppo_vbox)
tab_titles.append('PPO Training Core')

# New: RL Algorithm Hyperparameters Tab
# rl_algo_tab_children and rl_algo_tab_titles are already defined above when creating the individual algo tabs
# Consolidate them into the main param_tabs. No need to redefine here.
# Re-using the already defined `rl_algo_param_tabs` object.
tab_children.append(rl_algo_param_tabs)
tab_titles.append('RL Algo Hyperparameters')

# Create the main Tab widget for simulation parameters
param_tabs = widgets.Tab(children=tab_children)
for i, title in enumerate(tab_titles):
    param_tabs.set_title(i, title)


# --- Attach Handlers to Buttons ---
run_button = widgets.Button(description="Run Simulation") # Define run_button
run_button.on_click(run_simulation_with_params)
b_connect_broker.on_click(on_connect_broker_clicked)
b_disconnect_broker.on_click(on_disconnect_broker_clicked)
b_start_trading.on_click(on_start_trading_clicked)
b_stop_trading.on_click(on_stop_trading_clicked)
b_open_buy.on_click(on_open_buy_clicked)
b_open_sell.on_click(on_open_sell_clicked)
b_close_all.on_click(on_close_all_clicked)
b_view_positions.on_click(on_view_positions_clicked)

# --- Organize Market Manager UI ---
connection_buttons = widgets.HBox([b_connect_broker, b_disconnect_broker])
trading_control_buttons = widgets.HBox([b_start_trading, b_stop_trading])
manual_order_buttons = widgets.HBox([b_open_buy, b_open_sell, b_close_all])
position_view_button = widgets.HBox([b_view_positions])

market_manager_layout = widgets.VBox([
    widgets.Label("Broker Connection:"),
    connection_buttons,
    widgets.Label("Trading Control:"),
    trading_control_buttons,
    widgets.Label("Manual Orders:"),
    manual_order_buttons,
    widgets.Label("Positions:"),
    position_view_button,
    widgets.Label("Output:"),
    trading_session.market_manager_output_area
])

# Display the UIs
display(HTML('<h2>Strategy Configuration Parameters</h2>'))
display(param_tabs)

display(HTML('<h2>Run Simulation</h2>'))
display(run_button, output_area)

display(HTML('<h2>Market Manager Interface</h2>'))
display(market_manager_layout)

print("Interactive trading simulation environment is ready!")
print("Please interact with the displayed widgets to configure and run the simulation.")
