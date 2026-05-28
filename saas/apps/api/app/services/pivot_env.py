"""Reinforcement-learning trading environment for pivot-grid strategy simulations.

This module ports the notebook/README ``PivotEnv`` into a backend service
module.  The environment exposes a Gymnasium-compatible discrete-action API
for historical OHLCV data enriched with pivot, RSI, MACD, Bollinger Band, and
ATR features, while tracking grid, averaging, drawdown, time-decay, and
transaction-cost reward effects.
"""

from __future__ import annotations

import uuid

import numpy as np
from gymnasium import Env
from gymnasium.spaces import Box, Discrete


class PivotEnv(Env):
    def __init__(self, hist_df, gen_df,
                 broker_api, order_manager, # New parameters
                 initial_balance=10000.0,
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
        self.initial_balance = float(initial_balance)
        self.balance = self.initial_balance
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
        self.balance = self.initial_balance # Reset internal env balance
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


__all__ = ["PivotEnv"]
