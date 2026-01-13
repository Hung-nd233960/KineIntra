# Quick Start: Multi-Sensor FSR Calibration

## Installation

No additional dependencies needed beyond numpy. The module is ready to use.

## Basic Usage

### 1. Import

```python
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator
```

### 2. Create Calibrator

```python
cal = MultiSensorCalibrator()
```

### 3. Calibrate a Sensor

```python
# Your calibration data
resistance = [2500, 2000, 1600, 1200, 800]
force = [2, 5, 10, 20, 50]

# Calibrate with metadata
profile = cal.calibrate(
    sensor_id="FSR_SN12345",
    X=resistance,
    y=force,
    algorithm_name="exp",  # or "poly"
    metadata={
        "operator": "Your Name",
        "location": "Lab A",
        "notes": "Standard calibration",
    },
)

print(f"Calibrated! R² = {profile.get_stats()['r2']:.4f}")
```

### 4. Make Predictions

```python
# Predict force from resistance
measured_resistance = 1600
force = cal.predict("FSR_SN12345", measured_resistance)
print(f"Force at {measured_resistance}Ω: {force:.2f}N")
```

### 5. List All Sensors

```python
sensors = cal.list_sensors()
print(f"Calibrated sensors: {sensors}")
```

### 6. Get Statistics

```python
stats = cal.get_stats("FSR_SN12345")
print(f"RMSE: {stats['rmse']:.4f}")
print(f"MAE: {stats['mae']:.4f}")
print(f"R²: {stats['r2']:.4f}")
print(f"Samples: {stats['n_samples']}")
```

### 7. Update Metadata

```python
from datetime import datetime

cal.update_metadata(
    "FSR_SN12345",
    last_check=datetime.now().isoformat(),
    status="active",
    temperature="25°C",
)
```

### 8. Export/Import

```python
# Export for backup
cal.export_profile("FSR_SN12345", "backups/sensor1.json")

# Import later
cal.import_profile("backups/sensor1.json")
```

## Complete Example

```python
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator
from datetime import datetime

# Initialize
cal = MultiSensorCalibrator()

# Calibration data
R = [2500, 2000, 1600, 1200, 800]
F = [2, 5, 10, 20, 50]

# Calibrate
profile = cal.calibrate(
    sensor_id="FSR_SN12345",
    X=R,
    y=F,
    algorithm_name="exp",
    metadata={
        "operator": "John Doe",
        "date": datetime.now().isoformat(),
        "notes": "Initial calibration",
    },
)

# Check quality
stats = profile.get_stats()
if stats['r2'] > 0.95:
    print("✓ Good calibration quality!")
else:
    print("⚠ Poor calibration, consider recalibrating")

# Use it
force = cal.predict("FSR_SN12345", 1600)
print(f"Measured force: {force:.2f}N")

# Summary
summary = cal.get_summary()
print(f"\nTotal sensors: {summary['total_sensors']}")
for s in summary['sensors']:
    print(f"  - {s['sensor_id']}: {s['algorithm_name']}")
```

## Storage

By default, calibrations are saved to `calibration_data/` directory:

```
calibration_data/
├── FSR_SN12345.json
├── FSR_SN12346.json
└── FSR_SN12347.json
```

### Custom Storage Path

```python
from kineintra.FSR_signal.calibrator import (
    MultiSensorCalibrator,
    JSONFileStorage,
)

storage = JSONFileStorage(base_path="my_calibrations")
cal = MultiSensorCalibrator(storage=storage)
```

## Algorithms

### Exponential Model (`"exp"`)

Best for typical FSR behavior: `F = a * exp(b*R)`

```python
cal.calibrate(sensor_id, X, y, algorithm_name="exp")
```

### Polynomial Model (`"poly"`)

Best for complex relationships: `F = c_n*R^n + ... + c_1*R + c_0`

```python
cal.calibrate(sensor_id, X, y, algorithm_name="poly")
```

## Tips

1. **Avoid zero force values with exp model**: Use small positive values instead
2. **Check R² values**: Should be > 0.95 for good fits
3. **Use descriptive sensor IDs**: e.g., "FSR_SN12345", not "sensor1"
4. **Add metadata**: Operator, location, conditions help track calibrations
5. **Regular backups**: Export important profiles periodically

## Integration with ADC

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator

# Load calibrator
cal = MultiSensorCalibrator()

# Read ADC
adc_value = 512

# Convert to resistance
resistance = adc_signal_to_resistance(
    adc_signal=adc_value,
    source_voltage=5.0,
    known_resistance=10000,
)

# Get force
force = cal.predict("FSR_SN12345", resistance)
print(f"Force: {force:.2f}N")
```

## Error Handling

```python
try:
    force = cal.predict("UNKNOWN_SENSOR", 1600)
except ValueError as e:
    print(f"Error: {e}")
    # Sensor not found, list available sensors
    print(f"Available: {cal.list_sensors()}")
```

## Next Steps

- See [MULTI_SENSOR_IMPLEMENTATION.md](MULTI_SENSOR_IMPLEMENTATION.md) for full documentation
- See [multi_sensor_example.py](multi_sensor_example.py) for complete examples
- See [calibrator/README.md](calibrator/README.md) for algorithm details

## Support

For issues or questions, refer to the full documentation or example files.
