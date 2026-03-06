"""Exponential calibration model implementation."""

from typing import Optional, Union

import numpy as np
import numpy.typing as npt

from .base import Algorithm


class ExpModel(Algorithm):
    """Exponential calibration model.

    Fits the model: F = a * exp(b*R)
    where F is force, R is resistance, and a, b are fitted parameters.

    Implementation uses linear regression on log-transformed force values.
    """

    name: str = "exp"

    def __init__(
        self,
        a: Optional[float] = None,
        b: Optional[float] = None,
        training_stats: Optional[dict] = None,
    ) -> None:
        """Initialize exponential model.

        Args:
            a: Multiplicative coefficient (default: None, to be fitted).
            b: Exponential coefficient (default: None, to be fitted).
            training_stats: Training statistics (default: None, computed during fit).
        """
        self.a = a
        self.b = b
        self.training_stats = training_stats or {}

    def learn(
        self,
        X: Union[npt.ArrayLike, list[float]],
        y: Union[npt.ArrayLike, list[float]],
    ) -> None:
        """Fit model: F = a * exp(bR).

        Implemented via linear regression on log(F).

        Args:
            X: Resistance values.
            y: Force/weight values.
        """
        from ..analysis.statistics import mae, r2, rmse

        R = np.array(X, dtype=np.float64)
        F = np.array(y, dtype=np.float64)

        logF = np.log(F)
        A = np.vstack([R, np.ones(len(R))]).T
        result = np.linalg.lstsq(A, logF, rcond=None)
        b_val, loga = result[0]

        self.b = float(b_val)
        self.a = float(np.exp(loga))

        # Compute training statistics
        y_pred = self.predict(X)
        self.training_stats = {
            "rmse": rmse(y, y_pred),
            "mae": mae(y, y_pred),
            "r2": r2(y, y_pred),
            "n_samples": len(R),
        }

    def predict(
        self,
        X: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray[np.float64], float]:
        """Predict force from resistance values.

        Args:
            X: Resistance values.

        Returns:
            Predicted force values.

        Raises:
            ValueError: If model has not been trained yet.
        """
        if self.a is None or self.b is None:
            raise ValueError(
                "Model must be trained before prediction. Call learn() first."
            )

        X_arr = np.array(X, dtype=np.float64)
        result = self.a * np.exp(self.b * X_arr)

        # Return scalar if input was scalar
        if np.isscalar(X):
            return float(result)
        return result

    def stats(self) -> dict:
        """Return training statistics.

        Returns:
            Dictionary of training statistics.
        """
        return self.training_stats.copy()
