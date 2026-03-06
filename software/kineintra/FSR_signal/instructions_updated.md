Below is a **clean, streamlined Markdown specification** you can hand directly to an AI coding agent. It contains **no ambiguity**, and fully integrates the idea that **each calibration is tied to a physical sensor with its own ID/serial number**.

---

# FSR Calibration Module — Specification Document

This document defines the architecture, data structures, and interfaces required to build a **Force Sensing Resistor (FSR) Calibrator Module**.
The goal is to create a modular system that supports **multiple calibration algorithms**, **per-sensor calibration profiles**, **serialization**, and **future extensibility**.

---

# 1. System Overview

The system calibrates individual FSR sensors by learning a **transfer function**:

```
Force (N or kg)  =  H(Resistance)
```

Each physical sensor has a unique **Sensor ID / Serial Number**, and each one must maintain its own calibration profile.

The calibrator module must support:

* Multiple algorithms (e.g., polynomial regression, exponential model).
* Pluggable algorithm interface (uniform API).
* Saving/loading calibration models to/from files.
* Multiple sensors, each with its own calibration record.
* Extra metadata: timestamps, calibration statistics, fit quality, etc.

---
---

# 3. Algorithm Interface

All calibration algorithms must extend an abstract base class.

```python
from abc import ABC, abstractmethod

class Algorithm(ABC):
    name: str = "base"

    @abstractmethod
    def learn(self, X, y):
        """Train the calibration model."""

    @abstractmethod
    def predict(self, X):
        """Predict force from measured resistance."""

    @abstractmethod
    def stats(self) -> dict:
        """
        Return training statistics:
        - RMSE
        - R^2
        - residuals
        - etc.
        """

    @abstractmethod
    def to_dict(self) -> dict:
        """Return serializable parameters."""

    @classmethod
    @abstractmethod
    def from_dict(cls, d: dict):
        """Reconstruct model from serialized parameters."""
```

### Notes

* `to_dict()` and `from_dict()` **must produce JSON-serializable structures only**.
* `stats()` is mandatory for quality control.

---

# 4. Example Algorithms

### 4.1 Polynomial Regression (`Algorithm` subclass)

* Stores polynomial coefficients.
* `to_dict()` contains:

  ```json
  {
    "degree": 3,
    "coeffs": [ ... ]
  }
  ```

### 4.2 Exponential Regression (`Algorithm` subclass)

Models:

```
Force = a * exp(b * Resistance) + c
```

Stored as:

```json
{
  "a": ..., 
  "b": ..., 
  "c": ...
}
```

---

# 5. Sensor Calibration Profile

Each sensor has a calibration profile object:

```python
class SensorCalibrationProfile:
    sensor_id: str
    algorithm_name: str
    algorithm: Algorithm
    created_at: datetime
    updated_at: datetime
    metadata: dict
```

### Required Methods

```python
def to_dict(self) -> dict:
    """Serialize including algorithm.to_dict()."""

@classmethod
def from_dict(cls, d: dict, algorithm_registry):
    """
    Reconstruct profile:
    1. Lookup algorithm class via registry.
    2. Call Algorithm.from_dict().
    """
```

---

# 6. Algorithm Registry

Allows lookup by algorithm name so profiles can be loaded generically.

```python
class AlgorithmRegistry:
    def __init__(self):
        self._registry = {}

    def register(self, algo_cls):
        self._registry[algo_cls.name] = algo_cls

    def get(self, name):
        return self._registry[name]
```

Examples:

```python
registry.register(PolynomialRegression)
registry.register(ExponentialRegression)
```

---

# 7. Calibrator (Main Controller)

Responsible for:

* Taking calibration data.
* Choosing algorithm.
* Training.
* Saving/loading sensor calibration profiles.

### Required Methods

```python
class Calibrator:
    def __init__(self, algorithm_registry, storage):
        self.registry = algorithm_registry
        self.storage = storage  # file/db handler

    def calibrate(self, sensor_id, X, y, algorithm_name):
        """
        1. Create algorithm instance.
        2. Learn from (X, y).
        3. Construct SensorCalibrationProfile.
        4. Save profile via storage.
        5. Return profile.
        """

    def load_profile(self, sensor_id):
        """Return SensorCalibrationProfile."""

    def predict(self, sensor_id, resistance):
        """Use loaded profile and algorithm.predict()."""
```

---

# 8. Storage Layer

Plug-in architecture for JSON, YAML, or tiny DB.

### Simplest form: JSON file per sensor

```
calibration_data/
    SENSOR123.json
    SENSOR124.json
```

### Storage Interface

```python
class Storage:
    def save(self, sensor_id, profile_dict):
        pass

    def load(self, sensor_id) -> dict:
        pass
```

---

# 9. Calibration Data Format

Input to calibrate:

```
time    force(kg)   resistance(ohm)
-----------------------------------
t1      f1          r1
t2      f2          r2
...
```

Calibrator receives only:

* `X = resistance values`
* `y = known force values`

Time is ignored for now.

---

# 10. Output Requirements

Every calibration produces:

```json
{
  "sensor_id": "SN12345",
  "algorithm_name": "polynomial",
  "algorithm_params": { ... },
  "stats": {
    "rmse": ...,
    "r2": ...,
    "samples": N
  },
  "created_at": "...",
  "updated_at": "...",
  "metadata": {
    "operator": "...",
    "environment": "...",
    "notes": "...",
  }
}
```

---

# 11. Future Extensions (optional)

* Add hysteresis analysis model (based on time dimension).
* Add temperature compensation models.
* Add multi-step calibration pipelines.
* Add automatic model selection.
* Add GUI (Streamlit, PyQt, etc.).

---

# End of Specification

Let me know if you want a version formatted as a **GitHub README**, a **UML diagram**, or a **folder scaffold with empty Python files**.
