"""Algorithm registry for managing calibration algorithms."""

from typing import Dict, Optional, Type

from .algorithms.base import Algorithm


class AlgorithmRegistry:
    """Registry for managing and looking up calibration algorithms.

    Provides a centralized way to register and retrieve algorithm classes
    by their name, enabling dynamic algorithm selection and deserialization.
    """

    def __init__(self) -> None:
        """Initialize empty registry."""
        self._registry: Dict[str, Type[Algorithm]] = {}

    def register(self, algo_cls: Type[Algorithm]) -> None:
        """Register an algorithm class.

        Args:
            algo_cls: Algorithm class to register (must have 'name' attribute).

        Raises:
            ValueError: If algorithm name is already registered.
        """
        if algo_cls.name in self._registry:
            raise ValueError(
                f"Algorithm '{algo_cls.name}' is already registered. "
                "Use overwrite=True to replace."
            )
        self._registry[algo_cls.name] = algo_cls

    def register_overwrite(self, algo_cls: Type[Algorithm]) -> None:
        """Register an algorithm class, overwriting if exists.

        Args:
            algo_cls: Algorithm class to register.
        """
        self._registry[algo_cls.name] = algo_cls

    def get(self, name: str) -> Type[Algorithm]:
        """Get algorithm class by name.

        Args:
            name: Algorithm name.

        Returns:
            Algorithm class.

        Raises:
            KeyError: If algorithm is not registered.
        """
        if name not in self._registry:
            available = ", ".join(self._registry.keys())
            raise KeyError(
                f"Algorithm '{name}' not found in registry. " f"Available: {available}"
            )
        return self._registry[name]

    def has(self, name: str) -> bool:
        """Check if algorithm is registered.

        Args:
            name: Algorithm name.

        Returns:
            True if algorithm is registered, False otherwise.
        """
        return name in self._registry

    def list_algorithms(self) -> list[str]:
        """List all registered algorithm names.

        Returns:
            List of algorithm names.
        """
        return list(self._registry.keys())

    def __contains__(self, name: str) -> bool:
        """Support 'in' operator."""
        return self.has(name)

    def __getitem__(self, name: str) -> Type[Algorithm]:
        """Support dictionary-style access."""
        return self.get(name)

    def __repr__(self) -> str:
        """String representation."""
        algos = ", ".join(self.list_algorithms())
        return f"AlgorithmRegistry({algos})"


# Create default global registry
_global_registry: Optional[AlgorithmRegistry] = None


def get_global_registry() -> AlgorithmRegistry:
    """Get or create the global algorithm registry.

    Returns:
        Global AlgorithmRegistry instance.
    """
    global _global_registry
    if _global_registry is None:
        from .algorithms import ExpModel, PolyModel

        _global_registry = AlgorithmRegistry()
        _global_registry.register(ExpModel)
        _global_registry.register(PolyModel)
    return _global_registry
