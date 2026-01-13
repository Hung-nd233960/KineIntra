---

# 📘 Calibrator Module — Technical Specification

This document defines the architecture, required classes, and serialization behavior for a modular **FSR Calibration System**.
The goal is:

* plug-and-play calibration algorithms
* uniform API (`learn()`, `predict()`)
* easy saving/loading
* clean stats reporting
* minimal boilerplate for new algorithms

---

# 1. Directory Structure

```
calibrator/
│
├── algorithms/
│   ├── base.py
│   ├── exponential.py
│   ├── polynomial.py
│   ├── inverse.py
│   ├── spline.py
│   └── sklearn_wrapper.py
│
├── models/
│   └── calibration_model.py
│
├── io/
│   ├── storage.py
│   └── csv_loader.py        (optional)
│
├── analysis/
│   ├── statistics.py
│   └── outlier.py           (optional)
│
├── calibrator.py
└── __init__.py
```

---

# 2. `Algorithm` Interface (core)

Path: `calibrator/algorithms/base.py`

```python
from abc import ABC, abstractmethod

class Algorithm(ABC):
    """
    Base interface for all calibration algorithms.
    """
    name: str = "base"

    @abstractmethod
    def learn(self, X, y):
        """Train algorithm with inputs X (resistance) and outputs y (weight)."""
        pass

    @abstractmethod
    def predict(self, X):
        """Predict weight from resistance values."""
        pass

    def stat(self):
        """Optional algorithm-specific stats. Return dict."""
        return {}

    def to_dict(self):
        """
        Serialize algorithm parameters.

        Default behavior:
        - serialize all instance attributes automatically via vars(self)
        - include a 'class' field for algorithm reconstruction
        """
        d = vars(self).copy()
        d["class"] = self.name
        return d

    @classmethod
    def from_dict(cls, d):
        """
        Reconstruct algorithm instance from dictionary.
        Uses kwargs unpacking into __init__.
        """
        d = d.copy()
        d.pop("class", None)
        return cls(**d)
```

**Notes for Implementers:**

* All algorithms must define `name`, `learn`, and `predict`.
* No algorithm needs to override `to_dict()` or `from_dict()` unless it stores unserializable objects.
* New attributes added to an algorithm auto-serialize.

---

# 3. Example Algorithms

## 3.1 Exponential Model

Path: `calibrator/algorithms/exponential.py`

```python
import numpy as np
from .base import Algorithm

class ExpModel(Algorithm):
    name = "exp"

    def __init__(self, a=None, b=None):
        self.a = a
        self.b = b

    def learn(self, X, y):
        """
        Fit model: F = a * exp(bR)
        Implemented via linear regression on log(F).
        """
        R = np.array(X)
        F = np.array(y)

        logF = np.log(F)
        A = np.vstack([R, np.ones(len(R))]).T
        b, loga = np.linalg.lstsq(A, logF, rcond=None)[0]

        self.b = float(b)
        self.a = float(np.exp(loga))

    def predict(self, X):
        return self.a * np.exp(self.b * np.array(X))
```

## 3.2 Polynomial Model

Path: `calibrator/algorithms/polynomial.py`

```python
import numpy as np
from .base import Algorithm

class PolyModel(Algorithm):
    name = "poly"

    def __init__(self, degree=3, coeffs=None):
        self.degree = degree
        self.coeffs = coeffs

    def learn(self, X, y):
        self.coeffs = np.polyfit(X, y, self.degree).tolist()

    def predict(self, X):
        return np.polyval(self.coeffs, X)
```

---

# 4. Algorithm Registry

Path: `calibrator/algorithms/__init__.py`

```python
from .exponential import ExpModel
from .polynomial import PolyModel

ALGO_REGISTRY = {
    cls.name: cls
    for cls in [ExpModel, PolyModel]
}
```

---

# 5. Calibration Model Structure

Path: `calibrator/models/calibration_model.py`

```python
import time

class CalibrationModel:
    """
    Wraps a trained algorithm + metadata + statistics.
    """

    def __init__(self, algorithm, metadata=None, stats=None):
        self.algorithm = algorithm
        self.metadata = metadata or {}
        self.stats = stats or {}
        self.metadata.setdefault("timestamp", time.time())

    def predict(self, resistance):
        return self.algorithm.predict(resistance)

    def to_dict(self):
        return {
            "algorithm": self.algorithm.to_dict(),
            "metadata": self.metadata,
            "stats": self.stats,
        }

    @classmethod
    def from_dict(cls, d, registry):
        algo_dict = d["algorithm"]
        algo_class = registry[algo_dict["class"]]
        algorithm = algo_class.from_dict(algo_dict)
        return cls(
            algorithm=algorithm,
            metadata=d.get("metadata", {}),
            stats=d.get("stats", {})
        )
```

---

# 6. Model Storage

Path: `calibrator/io/storage.py`

```python
import json
from calibrator.algorithms import ALGO_REGISTRY
from calibrator.models.calibration_model import CalibrationModel

def save_model(model, path):
    with open(path, "w") as f:
        json.dump(model.to_dict(), f, indent=2)

def load_model(path):
    with open(path) as f:
        data = json.load(f)
    return CalibrationModel.from_dict(data, ALGO_REGISTRY)
```

---

# 7. Statistics Module

Path: `calibrator/analysis/statistics.py`

```python
import numpy as np

def rmse(y_true, y_pred):
    return float(np.sqrt(np.mean((np.array(y_true) - np.array(y_pred))**2)))

def mae(y_true, y_pred):
    return float(np.mean(np.abs(np.array(y_true) - np.array(y_pred))))

def r2(y_true, y_pred):
    y_true = np.array(y_true)
    y_pred = np.array(y_pred)
    ss_res = ((y_true - y_pred)**2).sum()
    ss_tot = ((y_true - y_true.mean())**2).sum()
    return float(1 - ss_res/ss_tot)
```

---

# 8. Calibrator Orchestrator

Path: `calibrator/calibrator.py`

```python
from calibrator.algorithms import ALGO_REGISTRY
from calibrator.io.storage import save_model, load_model
from calibrator.models.calibration_model import CalibrationModel
from calibrator.analysis.statistics import rmse, mae, r2

class Calibrator:
    """
    High-level interface for performing calibration, evaluating,
    saving, and loading models.
    """

    def __init__(self, algorithm_name="exp"):
        self.algorithm = ALGO_REGISTRY[algorithm_name]()
        self.model = None

    def fit(self, X, y):
        self.algorithm.learn(X, y)

        # compute statistics
        y_pred = self.algorithm.predict(X)
        stats = {
            "rmse": rmse(y, y_pred),
            "mae": mae(y, y_pred),
            "r2": r2(y, y_pred),
            "n": len(X),
        }

        self.model = CalibrationModel(self.algorithm, stats=stats)
        return self.model

    def predict(self, resistance):
        return self.model.predict(resistance)

    def save(self, path):
        save_model(self.model, path)

    @staticmethod
    def load(path):
        model = load_model(path)
        calib = Calibrator(model.algorithm.name)
        calib.algorithm = model.algorithm
        calib.model = model
        return calib
```

---

# 9. Example Usage

```python
from calibrator import Calibrator

R = [2200, 1800, 1500, 1200]
F = [5, 10, 20, 35]

cal = Calibrator("exp")
model = cal.fit(R, F)
cal.save("fsr_model.json")

print(model.stats)

loaded = Calibrator.load("fsr_model.json")
print(loaded.predict(1600))
```

---

# ✔️ Required Features Summary

| Component          | Requirement                                                                                    |
| ------------------ | ---------------------------------------------------------------------------------------------- |
| `Algorithm`        | Must implement `learn()`, `predict()`. Auto-serialization via `vars(self)`. Optional `stat()`. |
| Algorithms         | At least `ExpModel` and `PolyModel` implemented as examples.                                   |
| Registry           | `ALGO_REGISTRY` mapping algorithm names → classes.                                             |
| `CalibrationModel` | Wraps algorithm + metadata + stats. Fully serializable.                                        |
| Storage            | JSON save/load with algorithm reconstruction.                                                  |
| Stats              | RMSE, MAE, R².                                                                                 |
| Calibrator         | High-level API: `fit()`, `predict()`, `save()`, `load()`.                                      |
