"""LSTM model for price generation module.

Builds and trains LSTM models to generate synthetic price sequences.
Replaces notebook widget-based training with return-value based API.
"""

from typing import Tuple, Optional
import pandas as pd
import numpy as np
from sklearn.preprocessing import MinMaxScaler
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, Dense
from tensorflow.keras.optimizers import Adam
import logging

logger = logging.getLogger(__name__)


class LSTMPriceGenerator:
    """Generates synthetic price data using LSTM neural networks."""

    def __init__(self):
        """Initialize the LSTM price generator."""
        self.scaler = None
        self.model = None

    @staticmethod
    def create_model(
        input_shape: Tuple[int, int],
        output_dim: int,
        lstm_units_1: int = 50,
        lstm_units_2: int = 50,
        learning_rate: float = 0.001,
    ) -> Sequential:
        """Create LSTM model architecture.
        
        Args:
            input_shape: (sequence_length, num_features).
            output_dim: Number of output features.
            lstm_units_1: Units in first LSTM layer.
            lstm_units_2: Units in second LSTM layer.
            learning_rate: Adam optimizer learning rate.
            
        Returns:
            Compiled Sequential model.
        """
        model = Sequential([
            LSTM(lstm_units_1, return_sequences=True, input_shape=input_shape),
            LSTM(lstm_units_2),
            Dense(output_dim, activation='linear')
        ])
        model.compile(optimizer=Adam(learning_rate=learning_rate), loss='mse')
        return model

    def prepare_sequences(
        self,
        data: pd.DataFrame,
        features: list,
        sequence_length: int = 60,
    ) -> Tuple[np.ndarray, np.ndarray, MinMaxScaler]:
        """Prepare training sequences from data.
        
        Args:
            data: DataFrame with feature columns.
            features: List of column names to use.
            sequence_length: Length of each sequence.
            
        Returns:
            Tuple of (X, y, scaler) where:
            - X: Input sequences of shape (n_samples, sequence_length, n_features)
            - y: Target values of shape (n_samples, n_features)
            - scaler: Fitted MinMaxScaler for normalization.
        """
        scaler = MinMaxScaler()
        data_scaled = data[features].copy().astype(np.float32)
        data_scaled[:] = scaler.fit_transform(data_scaled)
        
        X, y = [], []
        if len(data_scaled) > sequence_length + 1:
            for i in range(len(data_scaled) - sequence_length - 1):
                X.append(data_scaled.iloc[i:i+sequence_length].values)
                y.append(data_scaled.iloc[i+sequence_length].values)
            X, y = np.array(X), np.array(y)
        else:
            X, y = np.array([]), np.array([])
        
        self.scaler = scaler
        return X, y, scaler

    def train(
        self,
        data: pd.DataFrame,
        features: list,
        sequence_length: int = 60,
        lstm_units_1: int = 50,
        lstm_units_2: int = 50,
        learning_rate: float = 0.001,
        epochs: int = 50,
        batch_size: int = 32,
        validation_split: float = 0.2,
        verbose: int = 0,
    ) -> dict:
        """Train LSTM model on data.
        
        Args:
            data: DataFrame with OHLCV data.
            features: List of column names to use.
            sequence_length: Length of input sequences.
            lstm_units_1: Units in first LSTM layer.
            lstm_units_2: Units in second LSTM layer.
            learning_rate: Adam optimizer learning rate.
            epochs: Number of training epochs.
            batch_size: Batch size for training.
            validation_split: Fraction of data to use for validation.
            verbose: Verbosity level (0=silent).
            
        Returns:
            Dictionary with training results and model reference.
        """
        X, y, scaler = self.prepare_sequences(data, features, sequence_length)
        
        if len(X) == 0 or len(y) == 0:
            logger.warning(
                f"Insufficient data for LSTM training. Need at least {sequence_length + 1} rows, got {len(data)}."
            )
            return {
                "success": False,
                "message": "Insufficient data for training",
                "model": None,
                "scaler": None,
            }
        
        self.model = self.create_model(
            (sequence_length, len(features)),
            len(features),
            lstm_units_1,
            lstm_units_2,
            learning_rate,
        )
        
        logger.info(f"Training LSTM model for {epochs} epochs...")
        history = self.model.fit(
            X, y,
            epochs=epochs,
            batch_size=batch_size,
            validation_split=validation_split,
            verbose=verbose,
        )
        
        return {
            "success": True,
            "message": "Model trained successfully",
            "model": self.model,
            "scaler": scaler,
            "history": history.history,
            "final_loss": float(history.history['loss'][-1]),
            "final_val_loss": float(history.history['val_loss'][-1]),
        }

    def generate(
        self,
        seed_data: np.ndarray,
        num_steps: int = 100,
        features_list: Optional[list] = None,
    ) -> pd.DataFrame:
        """Generate synthetic price sequences.
        
        Args:
            seed_data: Initial sequence (sequence_length, n_features).
            num_steps: Number of steps to generate.
            features_list: Optional list of feature names for DataFrame columns.
            
        Returns:
            DataFrame with generated data.
        """
        if self.model is None or self.scaler is None:
            raise RuntimeError("Model not trained. Call train() first.")
        
        generated = []
        seed = seed_data.copy()
        sequence_length = seed.shape[0]
        num_features = seed.shape[1]
        
        logger.info(f"Generating {num_steps} synthetic candles...")
        for step in range(num_steps):
            pred = self.model.predict(seed.reshape(1, sequence_length, num_features), verbose=0)[0]
            generated.append(pred)
            seed = np.vstack([seed[1:], pred])
        
        generated = np.array(generated)
        
        # Inverse transform to original scale
        generated_original = self.scaler.inverse_transform(generated)
        
        if features_list is None:
            features_list = [f"Feature_{i}" for i in range(num_features)]
        
        generated_df = pd.DataFrame(generated_original, columns=features_list)
        logger.info(f"Generated {len(generated_df)} synthetic candles.")
        
        return generated_df

    def generate_with_indicators(
        self,
        seed_data: np.ndarray,
        num_steps: int = 100,
        features_list: Optional[list] = None,
    ) -> pd.DataFrame:
        """Generate synthetic data and add pivot points.
        
        Args:
            seed_data: Initial sequence (sequence_length, n_features).
            num_steps: Number of steps to generate.
            features_list: Optional list of feature names.
            
        Returns:
            DataFrame with generated data and pivot levels.
        """
        generated_df = self.generate(seed_data, num_steps, features_list)
        
        # Add pivots if OHLC columns exist
        if all(col in generated_df.columns for col in ['Open', 'High', 'Low', 'Close']):
            generated_df["Pivot"] = (generated_df["High"] + generated_df["Low"] + generated_df["Close"]) / 3
            generated_df["R1"] = 2 * generated_df["Pivot"] - generated_df["Low"]
            generated_df["S1"] = 2 * generated_df["Pivot"] - generated_df["High"]
            generated_df["R2"] = generated_df["Pivot"] + (generated_df["High"] - generated_df["Low"])
            generated_df["S2"] = generated_df["Pivot"] - (generated_df["High"] - generated_df["Low"])
        
        return generated_df
