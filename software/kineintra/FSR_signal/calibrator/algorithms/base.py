"""Base interface for calibration algorithms."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Type, TypeVar, Union

import numpy as np
import numpy.typing as npt

T = TypeVar("T", bound="Algorithm")


class Algorithm(ABC):
    """Base interface for all calibration algorithms.

    All calibration algorithms must inherit from this class and implement
    the learn() and predict() methods. The class provides automatic
    serialization/deserialization capabilities.
    """

    name: str = "base"

    @abstractmethod
    def learn(
        self,
        X: Union[npt.ArrayLike, list[float]],
        y: Union[npt.ArrayLike, list[float]],
    ) -> None:
        """Train algorithm with inputs X (resistance) and outputs y (weight).

        Args:
            X: Input features (resistance values).
            y: Target values (weight/force values).
        """
        ...

    @abstractmethod
    def predict(
        self,
        X: Union[npt.ArrayLike, list[float], float],
    ) -> Union[npt.NDArray[np.float64], float]:
        """Predict weight from resistance values.

        Args:
            X: Input features (resistance values).

        Returns:
            Predicted weight/force values.
        """
        ...

    @abstractmethod
    def stats(self) -> Dict[str, Any]:
        """Return training statistics and model quality metrics.

        Returns:
            Dictionary containing at minimum:
            - 'rmse': Root Mean Squared Error
            - 'r2': Coefficient of determination
            - 'n_samples': Number of training samples
        """
        ...

    def to_dict(self) -> Dict[str, Any]:
        """Serialize algorithm parameters.

        Default behavior:
        - serialize all instance attributes automatically via vars(self)
        - include a 'class' field for algorithm reconstruction

        Returns:
            Dictionary representation of the algorithm.
        """
        d = vars(self).copy()
        d["class"] = self.name
        return d

    @classmethod
    def from_dict(cls: Type[T], d: Dict[str, Any]) -> T:
        """Reconstruct algorithm instance from dictionary.

        Uses kwargs unpacking into __init__.

        Args:
            d: Dictionary representation of the algorithm.

        Returns:
            Reconstructed algorithm instance.
        """
        d = d.copy()
        d.pop("class", None)
        return cls(**d)
