"""High-level calibrator orchestrator for FSR calibration."""

from pathlib import Path
from typing import Optional, Union

import numpy as np
import numpy.typing as npt

from .algorithms import ALGO_REGISTRY
from .analysis.statistics import mae, r2, rmse
from .io import load_model, save_model  # noqa: F401
from .models.calibration_model import CalibrationModel


class Calibrator:
    """High-level interface for performing calibration.

    Provides methods for:
    - Training calibration models
    - Making predictions
    - Evaluating model performance
    - Saving and loading models
    """

    def __init__(self, algorithm_name: str = "exp") -> None:
        """Initialize calibrator with specified algorithm.

        Args:
            algorithm_name: Name of the algorithm to use (default: "exp").
                Must be a key in ALGO_REGISTRY.

        Raises:
            KeyError: If algorithm_name is not found in registry.
        """
        if algorithm_name not in ALGO_REGISTRY:
            available = ", ".join(ALGO_REGISTRY.keys())
            raise KeyError(
                f"Algorithm '{algorithm_name}' not found. "
                f"Available algorithms: {available}"
            )

        self.algorithm = ALGO_REGISTRY[algorithm_name]()
        self.model: Optional[CalibrationModel] = None

    def fit(
        self,
        X: Union[npt.ArrayLike, list[float]],
        y: Union[npt.ArrayLike, list[float]],
    ) -> CalibrationModel:
        """Fit calibration model to data.

        Trains the algorithm and computes evaluation statistics.

        Args:
            X: Input features (resistance values).
            y: Target values (force/weight values).

        Returns:
            Trained CalibrationModel instance.
        """
        self.algorithm.learn(X, y)

        # Compute statistics
        X_arr = np.asarray(X)
        y_pred = self.algorithm.predict(X)
        stats = {
            "rmse": rmse(y, y_pred),
            "mae": mae(y, y_pred),
            "r2": r2(y, y_pred),
            "n": len(X_arr),
        }

        self.model = CalibrationModel(self.algorithm, stats=stats)
        return self.model

    def predict(
        self,
        resistance: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray, float]:
        """Predict force/weight from resistance values.

        Args:
            resistance: Resistance values.

        Returns:
            Predicted force/weight values.

        Raises:
            ValueError: If model has not been fitted yet.
        """
        if self.model is None:
            raise ValueError(
                "Model must be fitted before prediction. Call fit() first."
            )

        return self.model.predict(resistance)

    def save(self, path: Union[str, Path]) -> None:
        """Save calibration model to file.

        Args:
            path: File path for saving the model.

        Raises:
            ValueError: If model has not been fitted yet.
        """
        if self.model is None:
            raise ValueError("Model must be fitted before saving. Call fit() first.")

        save_model(self.model, path)

    @staticmethod
    def load(path: Union[str, Path]) -> "Calibrator":
        """Load calibration model from file.

        Args:
            path: File path to load the model from.

        Returns:
            Calibrator instance with loaded model.

        Raises:
            FileNotFoundError: If the file does not exist.
            json.JSONDecodeError: If the file is not valid JSON.
            KeyError: If the algorithm class is not found in registry.
        """
        model = load_model(path)
        calib = Calibrator(model.algorithm.name)
        calib.algorithm = model.algorithm
        calib.model = model
        return calib
