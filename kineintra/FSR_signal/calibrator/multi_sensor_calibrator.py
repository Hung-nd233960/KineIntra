"""Multi-sensor calibrator with per-sensor profile management."""

from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy.typing as npt

from .io.multi_sensor_storage import JSONFileStorage, Storage
from .models.sensor_profile import SensorCalibrationProfile
from .registry import AlgorithmRegistry, get_global_registry


class MultiSensorCalibrator:
    """High-level interface for multi-sensor FSR calibration.

    Manages calibration profiles for multiple sensors, each with its own
    unique sensor ID/serial number. Supports:
    - Per-sensor calibration with different algorithms
    - Loading/saving sensor-specific profiles
    - Predictions for individual sensors
    - Metadata management (operator, environment, notes)
    """

    def __init__(
        self,
        storage: Optional[Storage] = None,
        registry: Optional[AlgorithmRegistry] = None,
    ) -> None:
        """Initialize multi-sensor calibrator.

        Args:
            storage: Storage backend (default: JSONFileStorage).
            registry: Algorithm registry (default: global registry).
        """
        self.registry = registry if registry is not None else get_global_registry()
        self.storage = (
            storage if storage is not None else JSONFileStorage(registry=self.registry)
        )
        self._profiles: Dict[str, SensorCalibrationProfile] = {}

    def calibrate(
        self,
        sensor_id: str,
        X: Union[npt.ArrayLike, list[float]],
        y: Union[npt.ArrayLike, list[float]],
        algorithm_name: str = "exp",
        metadata: Optional[Dict[str, Any]] = None,
        auto_save: bool = True,
    ) -> SensorCalibrationProfile:
        """Calibrate a sensor with training data.

        Args:
            sensor_id: Unique sensor identifier or serial number.
            X: Resistance values (training inputs).
            y: Force/weight values (training targets).
            algorithm_name: Name of calibration algorithm to use.
            metadata: Additional metadata (operator, environment, notes, etc.).
            auto_save: Automatically save profile to storage (default: True).

        Returns:
            Calibrated SensorCalibrationProfile.

        Raises:
            KeyError: If algorithm_name is not in registry.
        """
        # Create and train algorithm
        algo_class = self.registry.get(algorithm_name)
        algorithm = algo_class()
        algorithm.learn(X, y)

        # Create calibration profile
        profile = SensorCalibrationProfile(
            sensor_id=sensor_id,
            algorithm=algorithm,
            metadata=metadata or {},
        )

        # Store in memory
        self._profiles[sensor_id] = profile

        # Save to storage if requested
        if auto_save:
            self.storage.save(profile)

        return profile

    def load_profile(
        self, sensor_id: str, cache: bool = True
    ) -> SensorCalibrationProfile:
        """Load a sensor calibration profile from storage.

        Args:
            sensor_id: Sensor identifier.
            cache: Cache profile in memory (default: True).

        Returns:
            Loaded SensorCalibrationProfile.

        Raises:
            FileNotFoundError: If profile does not exist in storage.
        """
        # Check cache first
        if sensor_id in self._profiles:
            return self._profiles[sensor_id]

        # Load from storage
        profile = self.storage.load(sensor_id)

        if cache:
            self._profiles[sensor_id] = profile

        return profile

    def predict(
        self,
        sensor_id: str,
        resistance: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray, float]:
        """Predict force/weight from resistance for a specific sensor.

        Args:
            sensor_id: Sensor identifier.
            resistance: Resistance value(s).

        Returns:
            Predicted force/weight value(s).

        Raises:
            ValueError: If sensor profile is not loaded.
        """
        if sensor_id not in self._profiles:
            # Try to load from storage
            try:
                self.load_profile(sensor_id)
            except FileNotFoundError:
                available = self.list_sensors()
                raise ValueError(
                    f"No calibration profile found for sensor '{sensor_id}'. "
                    f"Available sensors: {available}"
                )

        profile = self._profiles[sensor_id]
        return profile.predict(resistance)

    def save_profile(self, sensor_id: str) -> None:
        """Save a sensor profile to storage.

        Args:
            sensor_id: Sensor identifier.

        Raises:
            ValueError: If sensor profile is not loaded.
        """
        if sensor_id not in self._profiles:
            raise ValueError(f"Sensor '{sensor_id}' not found in memory")

        profile = self._profiles[sensor_id]
        self.storage.save(profile)

    def update_metadata(
        self,
        sensor_id: str,
        auto_save: bool = True,
        **kwargs: Any,
    ) -> None:
        """Update metadata for a sensor profile.

        Args:
            sensor_id: Sensor identifier.
            auto_save: Automatically save after update (default: True).
            **kwargs: Metadata fields to update.

        Raises:
            ValueError: If sensor profile is not loaded.
        """
        if sensor_id not in self._profiles:
            self.load_profile(sensor_id)

        profile = self._profiles[sensor_id]
        profile.update_metadata(**kwargs)

        if auto_save:
            self.storage.save(profile)

    def get_stats(self, sensor_id: str) -> Dict[str, Any]:
        """Get calibration statistics for a sensor.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            Dictionary of training statistics.
        """
        if sensor_id not in self._profiles:
            self.load_profile(sensor_id)

        return self._profiles[sensor_id].get_stats()

    def list_sensors(self) -> List[str]:
        """List all sensors with saved profiles.

        Returns:
            List of sensor IDs.
        """
        return self.storage.list_sensors()

    def list_loaded_sensors(self) -> List[str]:
        """List sensors currently loaded in memory.

        Returns:
            List of sensor IDs.
        """
        return list(self._profiles.keys())

    def profile_exists(self, sensor_id: str) -> bool:
        """Check if a profile exists for a sensor.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            True if profile exists, False otherwise.
        """
        return self.storage.exists(sensor_id)

    def delete_profile(self, sensor_id: str, from_memory: bool = True) -> None:
        """Delete a sensor calibration profile.

        Args:
            sensor_id: Sensor identifier.
            from_memory: Also remove from memory cache (default: True).

        Raises:
            FileNotFoundError: If profile does not exist in storage.
        """
        self.storage.delete(sensor_id)

        if from_memory and sensor_id in self._profiles:
            del self._profiles[sensor_id]

    def export_profile(
        self,
        sensor_id: str,
        output_path: Union[str, Path],
    ) -> None:
        """Export a sensor profile to a specific file.

        Args:
            sensor_id: Sensor identifier.
            output_path: Output file path.

        Raises:
            ValueError: If sensor profile is not loaded.
        """
        import json

        if sensor_id not in self._profiles:
            self.load_profile(sensor_id)

        profile = self._profiles[sensor_id]
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(profile.to_dict(), f, indent=2, ensure_ascii=False)

    def import_profile(
        self,
        input_path: Union[str, Path],
        auto_save: bool = True,
    ) -> SensorCalibrationProfile:
        """Import a sensor profile from a file.

        Args:
            input_path: Input file path.
            auto_save: Save to storage after import (default: True).

        Returns:
            Imported SensorCalibrationProfile.
        """
        import json

        input_path = Path(input_path)

        with open(input_path, encoding="utf-8") as f:
            profile_dict = json.load(f)

        profile = SensorCalibrationProfile.from_dict(
            profile_dict,
            self.registry._registry,  # type: ignore[attr-defined]
        )

        self._profiles[profile.sensor_id] = profile

        if auto_save:
            self.storage.save(profile)

        return profile

    def get_summary(self) -> Dict[str, Any]:
        """Get summary of all sensor profiles.

        Returns:
            Dictionary with sensor count and list of sensor info.
        """
        if isinstance(self.storage, JSONFileStorage):
            all_info = self.storage.list_all_info()
        else:
            all_info = [{"sensor_id": sid} for sid in self.list_sensors()]

        return {
            "total_sensors": len(all_info),
            "sensors": all_info,
        }

    def __repr__(self) -> str:
        """String representation."""
        loaded = len(self._profiles)
        total = len(self.list_sensors())
        return f"MultiSensorCalibrator(loaded={loaded}, total={total})"
