# Multi-Sensor FSR Calibration System — Implementation Summary

## Overview

The FSR Calibration System has been successfully enhanced to support **multi-sensor calibration** with **sensor ID/serial number tracking**, **timestamps**, and **comprehensive metadata management**.

## ✅ Implemented Features

### 1. **Sensor ID / Serial Number Support**
- Each sensor has a unique identifier stored in calibration profiles
- Sensor IDs are used for file naming and lookup
- Supports any string format (e.g., "FSR_SN12345", "SENSOR001", etc.)

### 2. **Multi-Sensor Management**
- `MultiSensorCalibrator`: New high-level API for managing multiple sensors
- Per-sensor calibration profiles with independent algorithms
- In-memory caching for performance
- List, load, save, delete operations for sensor profiles

### 3. **Timestamp Support**
- **created_at**: ISO 8601 timestamp when profile is created
- **updated_at**: ISO 8601 timestamp when profile is modified
- Automatic timestamp generation using `datetime.now().isoformat()`
- Timestamps preserved in JSON exports

### 4. **Metadata System**
- Flexible metadata dictionary for each sensor profile
- Common metadata fields:
  - `operator`: Person performing calibration
  - `location`: Lab or testing location
  - `notes`: Additional information
  - Custom fields as needed
- `update_metadata()` method for easy updates

### 5. **Algorithm Registry**
- `AlgorithmRegistry`: Centralized algorithm management
- Global registry with pre-registered algorithms
- Easy registration of custom algorithms
- Dynamic algorithm selection by name

### 6. **Storage System**
- Abstract `Storage` interface for pluggable backends
- `JSONFileStorage`: File-based storage implementation
- One JSON file per sensor
- Directory structure: `calibration_data/{SENSOR_ID}.json`
- Export/import capabilities for backup and sharing

### 7. **Statistics Integration**
- Mandatory `stats()` method in Algorithm base class
- Auto-computed during training:
  - **RMSE** (Root Mean Squared Error)
  - **MAE** (Mean Absolute Error)
  - **R²** (Coefficient of Determination)
  - **n_samples** (Number of training samples)
- Statistics stored in profiles and exported to JSON

## 📁 File Structure

```
calibrator/
├── __init__.py                      # Package exports
├── calibrator.py                    # Original single-sensor calibrator
├── multi_sensor_calibrator.py       # NEW: Multi-sensor calibrator
├── registry.py                      # NEW: Algorithm registry
├──algorithms/
│   ├── __init__.py
│   ├── base.py                      # UPDATED: Added stats() method
│   ├── exponential.py               # UPDATED: Stats computation
│   └── polynomial.py                # UPDATED: Stats computation
├── models/
│   ├── __init__.py                  # UPDATED: Added SensorCalibrationProfile
│   ├── calibration_model.py         # UPDATED: Added sensor_id support
│   └── sensor_profile.py            # NEW: Sensor calibration profile
├── io/
│   ├── __init__.py                  # UPDATED: Added new storage classes
│   ├── storage.py                   # Original storage
│   └── multi_sensor_storage.py      # NEW: Multi-sensor storage
└── analysis/
    ├── __init__.py
    └── statistics.py                # Statistics functions
```

## 📊 JSON Export Format

Each sensor profile is exported with complete metadata and timestamps:

```json
{
  "sensor_id": "FSR_SN12345",
  "algorithm_name": "exp",
  "algorithm_params": {
    "a": 372.67,
    "b": -0.00197,
    "training_stats": {
      "rmse": 1.9769,
      "mae": 1.2704,
      "r2": 0.9871,
      "n_samples": 5
    },
    "class": "exp"
  },
  "stats": {
    "rmse": 1.9769,
    "mae": 1.2704,
    "r2": 0.9871,
    "n_samples": 5
  },
  "created_at": "2026-01-11T19:10:38.324594",
  "updated_at": "2026-01-11T19:10:38.324603",
  "metadata": {
    "operator": "John Doe",
    "location": "Lab A",
    "notes": "High sensitivity FSR, 500g max",
    "timestamp": 1768134638.324584
  }
}
```

## 🚀 Usage Examples

### Basic Multi-Sensor Calibration

```python
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator

# Create calibrator
cal = MultiSensorCalibrator()

# Calibrate sensors with different algorithms
profile1 = cal.calibrate(
    sensor_id="FSR_SN12345",
    X=[2500, 2000, 1600, 1200],
    y=[2, 5, 10, 20],
    algorithm_name="exp",
    metadata={
        "operator": "John Doe",
        "location": "Lab A",
        "notes": "Standard FSR",
    },
)

profile2 = cal.calibrate(
    sensor_id="FSR_SN12346",
    X=[3000, 2500, 2000, 1500],
    y=[0, 10, 25, 50],
    algorithm_name="poly",
    metadata={
        "operator": "Jane Smith",
        "location": "Lab B",
    },
)

# Make predictions
force1 = cal.predict("FSR_SN12345", 1600)
force2 = cal.predict("FSR_SN12346", 2000)

# Get statistics
stats1 = cal.get_stats("FSR_SN12345")
print(f"RMSE: {stats1['rmse']:.4f}, R²: {stats1['r2']:.4f}")

# List all sensors
sensors = cal.list_sensors()
print(f"Total sensors: {len(sensors)}")

# Update metadata
cal.update_metadata(
    "FSR_SN12345",
    last_check=datetime.now().isoformat(),
    status="active",
)

# Export/import profiles
cal.export_profile("FSR_SN12345", "backup/sensor1.json")
cal.import_profile("backup/sensor1.json")
```

### Custom Storage Path

```python
from kineintra.FSR_signal.calibrator import (
    MultiSensorCalibrator,
    JSONFileStorage,
)

# Use custom storage directory
storage = JSONFileStorage(base_path="my_calibrations")
cal = MultiSensorCalibrator(storage=storage)

# Calibrations will be saved to my_calibrations/
cal.calibrate("SENSOR001", X, y, algorithm_name="exp")
```

### Profile Management

```python
# Check if profile exists
if cal.profile_exists("FSR_SN12345"):
    profile = cal.load_profile("FSR_SN12345")
    print(f"Last updated: {profile.updated_at}")

# Get summary of all sensors
summary = cal.get_summary()
for sensor_info in summary["sensors"]:
    print(f"- {sensor_info['sensor_id']}: {sensor_info['algorithm_name']}")

# Delete a profile
cal.delete_profile("OLD_SENSOR")
```

## 🔧 API Reference

### MultiSensorCalibrator

**Main Methods:**
- `calibrate(sensor_id, X, y, algorithm_name, metadata, auto_save)` → SensorCalibrationProfile
- `predict(sensor_id, resistance)` → force values
- `load_profile(sensor_id, cache)` → SensorCalibrationProfile
- `save_profile(sensor_id)` → None
- `update_metadata(sensor_id, **kwargs)` → None
- `get_stats(sensor_id)` → dict
- `list_sensors()` → list[str]
- `profile_exists(sensor_id)` → bool
- `delete_profile(sensor_id, from_memory)` → None
- `export_profile(sensor_id, output_path)` → None
- `import_profile(input_path, auto_save)` → SensorCalibrationProfile
- `get_summary()` → dict

### SensorCalibrationProfile

**Attributes:**
- `sensor_id`: str
- `algorithm`: Algorithm
- `algorithm_name`: str
- `created_at`: datetime
- `updated_at`: datetime
- `metadata`: dict

**Methods:**
- `predict(resistance)` → force values
- `get_stats()` → dict
- `update_metadata(**kwargs)` → None
- `to_dict()` → dict
- `from_dict(d, registry)` → SensorCalibrationProfile (classmethod)

### AlgorithmRegistry

**Methods:**
- `register(algo_cls)` → None
- `register_overwrite(algo_cls)` → None
- `get(name)` → Type[Algorithm]
- `has(name)` → bool
- `list_algorithms()` → list[str]

### Storage Interface

**Abstract Methods:**
- `save(profile)` → None
- `load(sensor_id)` → SensorCalibrationProfile
- `exists(sensor_id)` → bool
- `list_sensors()` → list[str]
- `delete(sensor_id)` → None

**JSONFileStorage Additional:**
- `get_profile_info(sensor_id)` → dict
- `list_all_info()` → list[dict]

## 🎯 Key Improvements Over Original

1. **Multi-sensor support**: Manage unlimited sensors vs. single sensor
2. **Sensor identification**: Unique IDs for each physical sensor
3. **Timestamps**: ISO 8601 formatted creation and update times
4. **Metadata system**: Flexible key-value storage per sensor
5. **Algorithm registry**: Dynamic algorithm selection and management
6. **Pluggable storage**: Abstract interface for different backends
7. **Statistics**: Mandatory statistics computed during training
8. **Export/import**: Easy backup and sharing of profiles
9. **Better type safety**: Comprehensive type hints throughout
10. **Production-ready**: Error handling, validation, documentation

## 🧪 Testing

Comprehensive test examples provided in:
- `multi_sensor_example.py`: Complete workflow demonstration
- All features tested and verified working
- Statistics computed correctly
- Timestamps in ISO 8601 format
- JSON export/import working perfectly

## 📈 Performance Characteristics

- **In-memory caching**: Loaded profiles cached for fast access
- **Lazy loading**: Profiles loaded on-demand
- **JSON storage**: Human-readable, version-controllable
- **File per sensor**: Parallel access, easy management
- **No database required**: Simple file-based storage

## 🔄 Backward Compatibility

The original `Calibrator` class remains unchanged and fully functional:

```python
from kineintra.FSR_signal.calibrator import Calibrator

# Original single-sensor API still works
cal = Calibrator("exp")
model = cal.fit(X, y)
cal.save("model.json")
loaded = Calibrator.load("model.json")
```

## ✅ Best Practices

1. **Use descriptive sensor IDs**: "FSR_SN12345" vs. "sensor1"
2. **Include metadata**: operator, location, conditions, notes
3. **Check statistics**: Ensure R² > 0.95 for good fits
4. **Regular backups**: Use `export_profile()` for important sensors
5. **Update metadata**: Track calibration checks and status
6. **Custom storage paths**: Organize by project or date
7. **Validate predictions**: Check if profile exists before predicting

## 🚧 Future Enhancements (Suggestions)

1. Database backend (SQLite, PostgreSQL)
2. Calibration history tracking
3. Automatic model selection
4. Temperature compensation
5. Hysteresis analysis
6. Web API for remote access
7. GUI for non-programmers
8. Batch calibration from CSV
9. Statistical quality control
10. Calibration certificate generation

---

**Version:** 0.2.0  
**Date:** January 11, 2026  
**Status:** Production Ready ✅
