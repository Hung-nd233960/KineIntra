# FSR Calibrator Module

A modular calibration framework for Force Sensitive Resistors (FSR).

## Features

- **Plug-and-play calibration algorithms**: Easy to add new calibration models
- **Uniform API**: All algorithms implement `learn()` and `predict()` methods
- **Serialization**: Easy saving/loading of trained models to/from JSON
- **Statistics**: Automatic computation of RMSE, MAE, and R² metrics
- **Type safety**: Full type hints for better IDE support and fewer bugs

## Directory Structure

```
calibrator/
├── __init__.py                 # Main package exports
├── calibrator.py               # High-level Calibrator orchestrator
├── algorithms/
│   ├── __init__.py            # Algorithm registry
│   ├── base.py                # Abstract Algorithm base class
│   ├── exponential.py         # Exponential model: F = a * exp(b*R)
│   └── polynomial.py          # Polynomial model: F = sum(c_i * R^i)
├── models/
│   ├── __init__.py
│   └── calibration_model.py   # Model wrapper with metadata
├── io/
│   ├── __init__.py
│   └── storage.py             # JSON save/load utilities
└── analysis/
    ├── __init__.py
    └── statistics.py          # RMSE, MAE, R² functions
```

## Quick Start

### Basic Usage

```python
from kineintra.FSR_signal.calibrator import Calibrator

# Calibration data: resistance (R) and force (F)
R = [2200, 1800, 1500, 1200]
F = [5, 10, 20, 35]

# Create and train calibrator
cal = Calibrator("exp")  # Use exponential model
model = cal.fit(R, F)

# View statistics
print(model.stats)
# {'rmse': 0.491, 'mae': 0.399, 'r2': 0.998, 'n': 4}

# Make predictions
predicted_force = cal.predict(1600)
print(f"Force at 1600Ω: {predicted_force:.2f}N")

# Save model
cal.save("my_fsr_model.json")

# Load model later
loaded_cal = Calibrator.load("my_fsr_model.json")
print(loaded_cal.predict(1600))
```

### Available Algorithms

#### Exponential Model (`"exp"`)
Fits the model: `F = a * exp(b*R)`

```python
cal = Calibrator("exp")
model = cal.fit(R, F)
```

#### Polynomial Model (`"poly"`)
Fits a polynomial of degree n: `F = c_n*R^n + ... + c_1*R + c_0`

```python
from kineintra.FSR_signal.calibrator import Calibrator

# Default is 3rd degree polynomial
cal = Calibrator("poly")
model = cal.fit(R, F)
```

## Creating Custom Algorithms

To add a new calibration algorithm:

1. Create a new file in `algorithms/` directory
2. Inherit from `Algorithm` base class
3. Implement `learn()` and `predict()` methods
4. Add to the registry

Example:

```python
from .base import Algorithm
import numpy as np

class MyCustomModel(Algorithm):
    name = "custom"
    
    def __init__(self, param1=None):
        self.param1 = param1
    
    def learn(self, X, y):
        # Your training logic here
        self.param1 = np.mean(y) / np.mean(X)
    
    def predict(self, X):
        # Your prediction logic here
        return self.param1 * np.array(X)
```

Then add to `algorithms/__init__.py`:

```python
from .custom import MyCustomModel

ALGO_REGISTRY = {
    cls.name: cls 
    for cls in [ExpModel, PolyModel, MyCustomModel]
}
```

## Model Persistence

Models are saved as JSON with the following structure:

```json
{
  "algorithm": {
    "class": "exp",
    "a": 372.67,
    "b": -0.00197
  },
  "metadata": {
    "timestamp": 1768131836.05
  },
  "stats": {
    "rmse": 0.491,
    "mae": 0.399,
    "r2": 0.998,
    "n": 4
  }
}
```

## API Reference

### `Calibrator`

Main interface for calibration operations.

**Methods:**
- `__init__(algorithm_name: str = "exp")`: Initialize with specified algorithm
- `fit(X, y) -> CalibrationModel`: Train model on data
- `predict(resistance) -> float | ndarray`: Predict force from resistance
- `save(path)`: Save model to file
- `load(path)` (static): Load model from file

### `Algorithm` (Base Class)

Abstract base class for all calibration algorithms.

**Required Methods:**
- `learn(X, y)`: Train the algorithm
- `predict(X)`: Make predictions

**Optional Methods:**
- `stat() -> dict`: Return algorithm-specific statistics
- `to_dict() -> dict`: Serialize parameters (auto-implemented)
- `from_dict(d) -> Algorithm`: Deserialize (auto-implemented)

### Statistics Functions

- `rmse(y_true, y_pred) -> float`: Root Mean Squared Error
- `mae(y_true, y_pred) -> float`: Mean Absolute Error  
- `r2(y_true, y_pred) -> float`: Coefficient of Determination

## Integration with ADC Signals

Combine with the `adc_signal` module for complete FSR processing:

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance
from kineintra.FSR_signal.calibrator import Calibrator

# Load calibration model
cal = Calibrator.load("fsr_model.json")

# Read ADC signal
adc_value = 512  # From sensor

# Convert to resistance
resistance = adc_signal_to_resistance(
    adc_signal=adc_value,
    source_voltage=5.0,
    known_resistance=10000,
)

# Predict force
force = cal.predict(resistance)
print(f"Applied force: {force:.2f}N")
```

## Best Practices

1. **Collect diverse calibration data**: Cover the full range of expected forces
2. **Multiple measurements**: Take several measurements at each force level
3. **Check R² values**: Values > 0.95 indicate good fit
4. **Save metadata**: Include sensor ID, date, environmental conditions
5. **Regular recalibration**: FSR characteristics may drift over time

## Type Hints

All functions are fully typed for better IDE support:

```python
def fit(
    self,
    X: Union[npt.ArrayLike, list[float]],
    y: Union[npt.ArrayLike, list[float]],
) -> CalibrationModel: ...
```

## Requirements

- Python >= 3.9
- numpy >= 1.20
- No other dependencies!

## License

Part of the BioMechanics_Microprocessor project.
