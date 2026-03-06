"""
Signal Generation for Virtual Device

Provides configurable signal generators for simulating sensor data.
Developers can extend this to create custom signal patterns.
"""

from abc import ABC, abstractmethod
from typing import List, Optional
import random


class SignalGenerator(ABC):
    """Abstract base class for signal generators."""

    @abstractmethod
    def generate_samples(self, n_sensors: int, bits_per_sensor: List[int]) -> List[int]:
        """
        Generate samples for active sensors.

        Args:
            n_sensors: Number of active sensors
            bits_per_sensor: Bits per sample for each sensor

        Returns:
            List of sample values (one per active sensor)
        """


class RandomSignalGenerator(SignalGenerator):
    """
    Default signal generator producing random values within valid ranges.

    Each sensor generates values in [0, 2^bits - 1] range with some baseline offset.
    Useful for basic testing and protocol validation.
    """

    def __init__(self, seed: Optional[int] = None, baseline_ratio: float = 0.3):
        """
        Initialize random signal generator.

        Args:
            seed: Random seed for reproducibility
            baseline_ratio: Baseline offset as ratio of max value (default 0.3)
        """
        self.baseline_ratio = baseline_ratio
        if seed is not None:
            random.seed(seed)

    def generate_samples(self, n_sensors: int, bits_per_sensor: List[int]) -> List[int]:
        """Generate random samples within protocol-defined ranges."""
        samples = []
        for i in range(n_sensors):
            bits = bits_per_sensor[i] if i < len(bits_per_sensor) else 12
            max_val = (1 << bits) - 1
            baseline = int(max_val * self.baseline_ratio)

            # Generate value around baseline with some variation
            variation_range = max_val - baseline
            value = baseline + random.randint(0, variation_range)
            value = min(value, max_val)  # Clamp to valid range

            samples.append(value)

        return samples


class SineWaveGenerator(SignalGenerator):
    """
    Generates sinusoidal signals for each sensor.

    Useful for testing DSP pipelines and visualizing real-time data.
    Each sensor can have different frequency and phase.
    """

    def __init__(
        self, frequencies: Optional[List[float]] = None, sample_rate: float = 100.0
    ):
        """
        Initialize sine wave generator.

        Args:
            frequencies: Frequency in Hz for each sensor (default: [1, 2, 3, ...])
            sample_rate: Sampling rate in Hz
        """
        import math

        self.math = math
        self.frequencies = frequencies or [1.0, 2.0, 3.0, 5.0, 8.0, 13.0, 21.0, 34.0]
        self.sample_rate = sample_rate
        self.sample_count = 0

    def generate_samples(self, n_sensors: int, bits_per_sensor: List[int]) -> List[int]:
        """Generate sinusoidal samples."""
        samples = []
        t = self.sample_count / self.sample_rate

        for i in range(n_sensors):
            bits = bits_per_sensor[i] if i < len(bits_per_sensor) else 12
            max_val = (1 << bits) - 1

            freq = self.frequencies[i % len(self.frequencies)]
            # Sine wave from 0 to max_val
            normalized = (self.math.sin(2 * self.math.pi * freq * t) + 1) / 2
            value = int(normalized * max_val)

            samples.append(value)

        self.sample_count += 1
        return samples


class StaticSignalGenerator(SignalGenerator):
    """
    Generates static/constant values for testing.

    Useful for calibration testing and baseline verification.
    """

    def __init__(self, values: Optional[List[int]] = None, default_value: int = 2048):
        """
        Initialize static signal generator.

        Args:
            values: Fixed values for each sensor (default: use default_value for all)
            default_value: Default value when sensor index exceeds values list
        """
        self.values = values or []
        self.default_value = default_value

    def generate_samples(self, n_sensors: int, bits_per_sensor: List[int]) -> List[int]:
        """Generate static samples."""
        samples = []
        for i in range(n_sensors):
            if i < len(self.values):
                value = self.values[i]
            else:
                bits = bits_per_sensor[i] if i < len(bits_per_sensor) else 12
                max_val = (1 << bits) - 1
                value = min(self.default_value, max_val)

            samples.append(value)

        return samples
