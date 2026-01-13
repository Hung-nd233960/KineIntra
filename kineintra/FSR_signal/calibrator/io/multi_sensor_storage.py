"""Multi-sensor storage system for calibration profiles."""

import json
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Dict, List, Optional, Union

from ..models.sensor_profile import SensorCalibrationProfile
from ..registry import get_global_registry


class Storage(ABC):
    """Abstract base class for calibration profile storage."""

    @abstractmethod
    def save(self, profile: SensorCalibrationProfile) -> None:
        """Save a sensor calibration profile.

        Args:
            profile: SensorCalibrationProfile to save.
        """
        pass

    @abstractmethod
    def load(self, sensor_id: str) -> SensorCalibrationProfile:
        """Load a sensor calibration profile.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            Loaded SensorCalibrationProfile.
        """
        pass

    @abstractmethod
    def exists(self, sensor_id: str) -> bool:
        """Check if a profile exists for a sensor.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            True if profile exists, False otherwise.
        """
        pass

    @abstractmethod
    def list_sensors(self) -> List[str]:
        """List all sensor IDs with saved profiles.

        Returns:
            List of sensor IDs.
        """
        pass

    @abstractmethod
    def delete(self, sensor_id: str) -> None:
        """Delete a sensor calibration profile.

        Args:
            sensor_id: Sensor identifier.
        """
        pass


class JSONFileStorage(Storage):
    """JSON file-based storage for sensor calibration profiles.

    Each sensor profile is stored in a separate JSON file named
    by the sensor ID in the specified directory.

    Example structure:
        calibration_data/
            SENSOR001.json
            SENSOR002.json
            FSR_SN12345.json
    """

    def __init__(
        self,
        base_path: Union[str, Path] = "calibration_data",
        registry: Optional[object] = None,
    ) -> None:
        """Initialize JSON file storage.

        Args:
            base_path: Directory path for storing calibration files.
            registry: Algorithm registry (default: global registry).
        """
        self.base_path = Path(base_path)
        self.registry = registry if registry is not None else get_global_registry()
        self.base_path.mkdir(parents=True, exist_ok=True)

    def _get_file_path(self, sensor_id: str) -> Path:
        """Get file path for a sensor ID.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            Path to the JSON file.
        """
        # Sanitize sensor_id for filesystem
        safe_id = sensor_id.replace("/", "_").replace("\\", "_")
        return self.base_path / f"{safe_id}.json"

    def save(self, profile: SensorCalibrationProfile) -> None:
        """Save a sensor calibration profile to JSON file.

        Args:
            profile: SensorCalibrationProfile to save.
        """
        file_path = self._get_file_path(profile.sensor_id)
        profile_dict = profile.to_dict()

        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(profile_dict, f, indent=2, ensure_ascii=False)

    def load(self, sensor_id: str) -> SensorCalibrationProfile:
        """Load a sensor calibration profile from JSON file.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            Loaded SensorCalibrationProfile.

        Raises:
            FileNotFoundError: If profile file does not exist.
            json.JSONDecodeError: If file contains invalid JSON.
        """
        file_path = self._get_file_path(sensor_id)

        if not file_path.exists():
            raise FileNotFoundError(
                f"No calibration profile found for sensor '{sensor_id}' "
                f"at {file_path}"
            )

        with open(file_path, encoding="utf-8") as f:
            profile_dict = json.load(f)

        return SensorCalibrationProfile.from_dict(
            profile_dict,
            self.registry._registry,  # type: ignore[attr-defined]
        )

    def exists(self, sensor_id: str) -> bool:
        """Check if a profile exists for a sensor.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            True if profile exists, False otherwise.
        """
        return self._get_file_path(sensor_id).exists()

    def list_sensors(self) -> List[str]:
        """List all sensor IDs with saved profiles.

        Returns:
            List of sensor IDs (sorted alphabetically).
        """
        json_files = self.base_path.glob("*.json")
        sensor_ids = [f.stem for f in json_files]
        return sorted(sensor_ids)

    def delete(self, sensor_id: str) -> None:
        """Delete a sensor calibration profile.

        Args:
            sensor_id: Sensor identifier.

        Raises:
            FileNotFoundError: If profile does not exist.
        """
        file_path = self._get_file_path(sensor_id)

        if not file_path.exists():
            raise FileNotFoundError(
                f"No calibration profile found for sensor '{sensor_id}'"
            )

        file_path.unlink()

    def get_profile_info(self, sensor_id: str) -> Dict[str, str]:
        """Get basic information about a sensor profile without full load.

        Args:
            sensor_id: Sensor identifier.

        Returns:
            Dictionary with sensor_id, algorithm_name, created_at, updated_at.
        """
        file_path = self._get_file_path(sensor_id)

        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)

        return {
            "sensor_id": data["sensor_id"],
            "algorithm_name": data["algorithm_name"],
            "created_at": data["created_at"],
            "updated_at": data["updated_at"],
        }

    def list_all_info(self) -> List[Dict[str, str]]:
        """List information for all stored sensor profiles.

        Returns:
            List of dictionaries with basic info for each sensor.
        """
        return [self.get_profile_info(sid) for sid in self.list_sensors()]

    def __repr__(self) -> str:
        """String representation."""
        n_sensors = len(self.list_sensors())
        return f"JSONFileStorage(path='{self.base_path}', sensors={n_sensors})"
