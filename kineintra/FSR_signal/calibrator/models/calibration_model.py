"""Calibration model wrapper with metadata and statistics."""

import time
from datetime import datetime
from typing import Any, Dict, Optional, Union

import numpy.typing as npt

from ..algorithms.base import Algorithm


class CalibrationModel:
    """Wraps a trained algorithm with metadata and statistics.

    This class encapsulates a calibration algorithm along with:
    - Metadata (e.g., creation timestamp, sensor info)
    - Statistics (e.g., RMSE, MAE, R²)

    Provides serialization/deserialization capabilities.
    """

    def __init__(
        self,
        algorithm: Algorithm,
        metadata: Optional[Dict[str, Any]] = None,
        stats: Optional[Dict[str, Any]] = None,
        sensor_id: Optional[str] = None,
    ) -> None:
        """Initialize calibration model.

        Args:
            algorithm: The calibration algorithm instance.
            metadata: Optional metadata dictionary.
            stats: Optional statistics dictionary.
            sensor_id: Optional sensor identifier/serial number.
        """
        self.algorithm = algorithm
        self.metadata = metadata or {}
        self.stats = stats or {}
        self.sensor_id = sensor_id

        # Add timestamps if not present
        now = datetime.now()
        self.metadata.setdefault("timestamp", time.time())
        self.metadata.setdefault("created_at", now.isoformat())
        self.metadata.setdefault("updated_at", now.isoformat())

    def predict(
        self,
        resistance: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray, float]:
        """Predict force/weight from resistance values.

        Args:
            resistance: Resistance values.

        Returns:
            Predicted force/weight values.
        """
        return self.algorithm.predict(resistance)

    def to_dict(self) -> Dict[str, Any]:
        """Serialize model to dictionary.

        Returns:
            Dictionary representation of the model.
        """
        result: Dict[str, Any] = {
            "algorithm": self.algorithm.to_dict(),
            "metadata": self.metadata,
            "stats": self.stats,
        }
        if self.sensor_id is not None:
            result["sensor_id"] = self.sensor_id
        return result

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        registry: Dict[str, Any],
    ) -> "CalibrationModel":
        """Reconstruct model from dictionary.

        Args:
            d: Dictionary representation of the model.
            registry: Algorithm registry for reconstructing the algorithm.

        Returns:
            Reconstructed CalibrationModel instance.

        Raises:
            KeyError: If algorithm class is not found in registry.
        """
        algo_dict = d["algorithm"]
        algo_class = registry[algo_dict["class"]]
        algorithm = algo_class.from_dict(algo_dict)  # type: ignore[attr-defined]
        return cls(
            sensor_id=d.get("sensor_id"),
            algorithm=algorithm,
            metadata=d.get("metadata", {}),
            stats=d.get("stats", {}),
        )
