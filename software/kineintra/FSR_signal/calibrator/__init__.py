"""FSR Calibration System.

A modular calibration framework for Force Sensitive Resistors (FSR).

Features:
- Plug-and-play calibration algorithms
- Uniform API (learn(), predict())
- Multi-sensor support with per-sensor profiles
- Sensor ID / Serial Number tracking
- Easy saving/loading with timestamps
- Clean statistics reporting
- Minimal boilerplate for new algorithms

Example (Single Sensor):
    >>> from kineintra.FSR_signal.calibrator import Calibrator
    >>>
    >>> R = [2200, 1800, 1500, 1200]
    >>> F = [5, 10, 20, 35]
    >>>
    >>> cal = Calibrator("exp")
    >>> model = cal.fit(R, F)
    >>> cal.save("fsr_model.json")
    >>>
    >>> print(model.stats)
    >>>
    >>> loaded = Calibrator.load("fsr_model.json")
    >>> print(loaded.predict(1600))

Example (Multi-Sensor):
    >>> from kineintra.FSR_signal.calibrator import MultiSensorCalibrator
    >>>
    >>> cal = MultiSensorCalibrator()
    >>>
    >>> # Calibrate sensor 1
    >>> profile1 = cal.calibrate("SENSOR001", R1, F1, algorithm_name="exp")
    >>>
    >>> # Calibrate sensor 2
    >>> profile2 = cal.calibrate("SENSOR002", R2, F2, algorithm_name="poly")
    >>>
    >>> # Predict
    >>> force1 = cal.predict("SENSOR001", 1600)
    >>> force2 = cal.predict("SENSOR002", 1800)
    >>>
    >>> # List all sensors
    >>> print(cal.list_sensors())
"""

from .algorithms import ALGO_REGISTRY, Algorithm, ExpModel, PolyModel
from .analysis import mae, r2, rmse
from .calibrator import Calibrator
from .io import JSONFileStorage, Storage, load_model, save_model
from .models import CalibrationModel, SensorCalibrationProfile
from .multi_sensor_calibrator import MultiSensorCalibrator
from .registry import AlgorithmRegistry, get_global_registry

__all__ = [
    # Main calibrators
    "Calibrator",
    "MultiSensorCalibrator",
    # Algorithms
    "Algorithm",
    "ExpModel",
    "PolyModel",
    "ALGO_REGISTRY",
    # Models
    "CalibrationModel",
    "SensorCalibrationProfile",
    # Registry
    "AlgorithmRegistry",
    "get_global_registry",
    # Storage
    "Storage",
    "JSONFileStorage",
    "save_model",
    "load_model",
    # Statistics
    "rmse",
    "mae",
    "r2",
]

__version__ = "0.2.0"
