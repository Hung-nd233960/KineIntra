"""Polynomial calibration model implementation."""

from typing import Optional, Union

import numpy as np
import numpy.typing as npt

from .base import Algorithm


class PolyModel(Algorithm):
    """Polynomial calibration model.

    Fits a polynomial of specified degree to the calibration data.
    Uses numpy's polyfit for least-squares fitting.
    """

    name: str = "poly"

    def __init__(
        self,
        degree: int = 3,
        coeffs: Optional[list[float]] = None,
        training_stats: Optional[dict] = None,
    ) -> None:
        """Initialize polynomial model.

        Args:
            degree: Degree of the polynomial (default: 3).
            coeffs: Polynomial coefficients (default: None, to be fitted).
            training_stats: Training statistics (default: None, computed during fit).
        """
        self.degree = degree
        self.coeffs = coeffs
        self.training_stats = training_stats or {}

    def learn(
        self,
        X: Union[npt.ArrayLike, list[float]],
        y: Union[npt.ArrayLike, list[float]],
    ) -> None:
        """Fit polynomial model to data.

        Args:
            X: Resistance values.
            y: Force/weight values.
        """
        from ..analysis.statistics import mae, r2, rmse

        X_arr = np.array(X, dtype=np.float64)
        y_arr = np.array(y, dtype=np.float64)

        coeffs_arr = np.polyfit(X_arr, y_arr, self.degree)
        self.coeffs = coeffs_arr.tolist()

        # Compute training statistics
        y_pred = self.predict(X)
        self.training_stats = {
            "rmse": rmse(y_arr, y_pred),
            "mae": mae(y_arr, y_pred),
            "r2": r2(y_arr, y_pred),
            "n_samples": len(X_arr),
        }

    def predict(
        self,
        X: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray[np.float64], float]:
        """Predict force from resistance values using fitted polynomial.

        Args:
            X: Resistance values.

        Returns:
            Predicted force values.

        Raises:
            ValueError: If model has not been trained yet.
        """
        if self.coeffs is None:
            raise ValueError(
                "Model must be trained before prediction. Call learn() first."
            )

        X_arr = np.array(X, dtype=np.float64)
        result = np.polyval(self.coeffs, X_arr)

        # Return scalar if input was scalar
        if np.isscalar(X):
            return float(result)
        return result.astype(np.float64)

    def stats(self) -> dict:
        """Return training statistics.

        Returns:
            Dictionary of training statistics.
        """
        return self.training_stats.copy()
