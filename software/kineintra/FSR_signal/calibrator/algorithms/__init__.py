"""Algorithm registry for calibration models."""

from typing import Dict, Type

from .base import Algorithm
from .exponential import ExpModel
from .polynomial import PolyModel

# Registry mapping algorithm names to their classes
ALGO_REGISTRY: Dict[str, Type[Algorithm]] = {
    ExpModel.name: ExpModel,
    PolyModel.name: PolyModel,
}

__all__ = ["Algorithm", "ExpModel", "PolyModel", "ALGO_REGISTRY"]
