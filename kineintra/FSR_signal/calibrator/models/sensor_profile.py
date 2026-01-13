"""Sensor calibration profile for individual FSR sensors."""

from datetime import datetime
from typing import Any, Dict, Optional

from ..algorithms.base import Algorithm


class SensorCalibrationProfile:
    """Calibration profile for a single FSR sensor.

    Each physical sensor has its own unique ID/serial number and maintains
    its own calibration parameters, statistics, and metadata.
    """

    def __init__(
        self,
        sensor_id: str,
        algorithm: Algorithm,
        created_at: Optional[datetime] = None,
        updated_at: Optional[datetime] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> None:
        """Initialize sensor calibration profile.

        Args:
            sensor_id: Unique sensor identifier or serial number.
            algorithm: Trained calibration algorithm.
            created_at: Creation timestamp (default: now).
            updated_at: Last update timestamp (default: now).
            metadata: Additional metadata (operator, environment, notes, etc.).
        """
        self.sensor_id = sensor_id
        self.algorithm = algorithm
        self.created_at = created_at or datetime.now()
        self.updated_at = updated_at or datetime.now()
        self.metadata = metadata or {}

        # Store algorithm name for easy access
        self.algorithm_name = algorithm.name

    def predict(self, resistance: Any) -> Any:
        """Predict force/weight from resistance values.

        Args:
            resistance: Resistance value(s).

        Returns:
            Predicted force/weight value(s).
        """
        return self.algorithm.predict(resistance)

    def get_stats(self) -> Dict[str, Any]:
        """Get algorithm training statistics.

        Returns:
            Dictionary of training statistics.
        """
        return self.algorithm.stats()

    def to_dict(self) -> Dict[str, Any]:
        """Serialize profile to dictionary.

        Returns:
            Dictionary representation including all metadata and timestamps.
        """
        return {
            "sensor_id": self.sensor_id,
            "algorithm_name": self.algorithm_name,
            "algorithm_params": self.algorithm.to_dict(),
            "stats": self.algorithm.stats(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(
        cls,
        d: Dict[str, Any],
        algorithm_registry: Dict[str, Any],
    ) -> "SensorCalibrationProfile":
        """Reconstruct profile from dictionary.

        Args:
            d: Dictionary representation of the profile.
            algorithm_registry: Registry for looking up algorithm classes.

        Returns:
            Reconstructed SensorCalibrationProfile instance.

        Raises:
            KeyError: If algorithm is not found in registry.
        """
        algo_name = d["algorithm_name"]
        algo_class = algorithm_registry[algo_name]
        algorithm = algo_class.from_dict(d["algorithm_params"])  # type: ignore[attr-defined]

        return cls(
            sensor_id=d["sensor_id"],
            algorithm=algorithm,
            created_at=datetime.fromisoformat(d["created_at"]),
            updated_at=datetime.fromisoformat(d["updated_at"]),
            metadata=d.get("metadata", {}),
        )

    def update_metadata(self, **kwargs: Any) -> None:
        """Update metadata fields.

        Args:
            **kwargs: Key-value pairs to update in metadata.
        """
        self.metadata.update(kwargs)
        self.updated_at = datetime.now()

    def __repr__(self) -> str:
        """String representation of the profile."""
        return (
            f"SensorCalibrationProfile(sensor_id='{self.sensor_id}', "
            f"algorithm='{self.algorithm_name}', "
            f"created_at='{self.created_at.isoformat()}')"
        )
