"""Model storage and persistence utilities."""

import json
from pathlib import Path
from typing import Union

from kineintra.FSR_signal.calibrator.algorithms import ALGO_REGISTRY
from kineintra.FSR_signal.calibrator.models.calibration_model import CalibrationModel


def save_model(model: CalibrationModel, path: Union[str, Path]) -> None:
    """Save calibration model to JSON file.

    Args:
        model: The calibration model to save.
        path: File path for saving the model.
    """
    path_obj = Path(path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)

    with open(path_obj, "w", encoding="utf-8") as f:
        json.dump(model.to_dict(), f, indent=2)


def load_model(path: Union[str, Path]) -> CalibrationModel:
    """Load calibration model from JSON file.

    Args:
        path: File path to load the model from.

    Returns:
        Loaded CalibrationModel instance.

    Raises:
        FileNotFoundError: If the file does not exist.
        json.JSONDecodeError: If the file is not valid JSON.
        KeyError: If the algorithm class is not found in registry.
    """
    path_obj = Path(path)

    with open(path_obj, encoding="utf-8") as f:
        data = json.load(f)

    return CalibrationModel.from_dict(data, ALGO_REGISTRY)
