"""Comprehensive examples for multi-sensor FSR calibration system."""

from datetime import datetime

from kineintra.FSR_signal.calibrator import MultiSensorCalibrator

print("=" * 60)
print("Multi-Sensor FSR Calibration System Examples")
print("=" * 60)

# Example 1: Basic Multi-Sensor Calibration
print("\n### Example 1: Calibrate Multiple Sensors ###\n")

# Create calibrator
cal = MultiSensorCalibrator()

# Calibration data for Sensor 1 (high sensitivity)
R1 = [2500, 2000, 1600, 1200, 800]
F1 = [2, 5, 10, 20, 50]  # Avoid 0 for exponential model

# Calibration data for Sensor 2 (low sensitivity)
R2 = [3000, 2500, 2000, 1500, 1000]
F2 = [0, 10, 25, 50, 100]

# Calibration data for Sensor 3
R3 = [2200, 1800, 1500, 1200, 900]
F3 = [5, 10, 20, 35, 60]

# Calibrate each sensor with metadata
profile1 = cal.calibrate(
    sensor_id="FSR_SN12345",
    X=R1,
    y=F1,
    algorithm_name="exp",
    metadata={
        "operator": "John Doe",
        "location": "Lab A",
        "notes": "High sensitivity FSR, 500g max",
    },
)

profile2 = cal.calibrate(
    sensor_id="FSR_SN12346",
    X=R2,
    y=F2,
    algorithm_name="poly",
    metadata={
        "operator": "Jane Smith",
        "location": "Lab B",
        "notes": "Low sensitivity FSR, 1kg max",
    },
)

profile3 = cal.calibrate(
    sensor_id="FSR_SN12347",
    X=R3,
    y=F3,
    algorithm_name="exp",
    metadata={
        "operator": "John Doe",
        "location": "Lab A",
        "notes": "Standard FSR",
    },
)

print(f"✓ Calibrated sensor: {profile1.sensor_id}")
print(f"  Algorithm: {profile1.algorithm_name}")
print(f"  Stats: {profile1.get_stats()}")

print(f"\n✓ Calibrated sensor: {profile2.sensor_id}")
print(f"  Algorithm: {profile2.algorithm_name}")
print(f"  Stats: {profile2.get_stats()}")

print(f"\n✓ Calibrated sensor: {profile3.sensor_id}")
print(f"  Algorithm: {profile3.algorithm_name}")
print(f"  Stats: {profile3.get_stats()}")

# Example 2: Make Predictions
print("\n\n### Example 2: Make Predictions ###\n")

test_resistance = 1600

for sensor_id in ["FSR_SN12345", "FSR_SN12346", "FSR_SN12347"]:
    force = cal.predict(sensor_id, test_resistance)
    print(f"Sensor {sensor_id}: R={test_resistance}Ω → F={force:.2f}N")

# Example 3: List All Sensors
print("\n\n### Example 3: List All Sensors ###\n")

all_sensors = cal.list_sensors()
print(f"Total sensors: {len(all_sensors)}")
print(f"Sensor IDs: {all_sensors}")

# Get summary
summary = cal.get_summary()
print(f"\nSummary:")
for sensor_info in summary["sensors"]:
    print(f"  - {sensor_info['sensor_id']}")
    print(f"    Algorithm: {sensor_info['algorithm_name']}")
    print(f"    Created: {sensor_info['created_at']}")
    print(f"    Updated: {sensor_info['updated_at']}")

# Example 4: Update Metadata
print("\n\n### Example 4: Update Metadata ###\n")

cal.update_metadata(
    "FSR_SN12345",
    last_calibration_check=datetime.now().isoformat(),
    status="active",
    temperature="25°C",
)

print("✓ Updated metadata for FSR_SN12345")

# Example 5: Export/Import Profiles
print("\n\n### Example 5: Export/Import Profiles ###\n")

# Export a profile
cal.export_profile("FSR_SN12345", "exported_sensor_FSR_SN12345.json")
print("✓ Exported FSR_SN12345 to exported_sensor_FSR_SN12345.json")

# Delete from memory
del cal._profiles["FSR_SN12345"]
print("✓ Deleted FSR_SN12345 from memory")

# Reload
cal.load_profile("FSR_SN12345")
print("✓ Reloaded FSR_SN12345 from storage")

# Example 6: Get Statistics
print("\n\n### Example 6: Get Statistics ###\n")

for sensor_id in all_sensors:
    stats = cal.get_stats(sensor_id)
    print(f"\nSensor: {sensor_id}")
    print(f"  RMSE: {stats['rmse']:.4f}")
    print(f"  MAE: {stats['mae']:.4f}")
    print(f"  R²: {stats['r2']:.4f}")
    print(f"  Samples: {stats['n_samples']}")

# Example 7: Batch Predictions
print("\n\n### Example 7: Batch Predictions ###\n")

resistance_values = [2000, 1600, 1200, 800]

print("Resistance values:", resistance_values)
print("\nPredictions:")
for sensor_id in all_sensors[:2]:  # Just first 2 for brevity
    forces = cal.predict(sensor_id, resistance_values)
    print(f"\n{sensor_id}:")
    for r, f in zip(resistance_values, forces):
        print(f"  R={r}Ω → F={f:.2f}N")

# Example 8: Working with Custom Storage Path
print("\n\n### Example 8: Custom Storage Path ###\n")

from kineintra.FSR_signal.calibrator import JSONFileStorage

custom_storage = JSONFileStorage(base_path="my_custom_calibrations")
custom_cal = MultiSensorCalibrator(storage=custom_storage)

# This will save to my_custom_calibrations/ directory
custom_cal.calibrate(
    sensor_id="CUSTOM_SENSOR_001",
    X=[2000, 1500, 1000],
    y=[10, 25, 50],
    algorithm_name="exp",
)

print("✓ Created calibration in custom storage path")
print(f"  Stored at: my_custom_calibrations/CUSTOM_SENSOR_001.json")

# Example 9: Check if Profile Exists
print("\n\n### Example 9: Check Profile Existence ###\n")

sensors_to_check = ["FSR_SN12345", "FSR_SN99999"]

for sensor_id in sensors_to_check:
    exists = cal.profile_exists(sensor_id)
    status = "exists" if exists else "does not exist"
    print(f"Sensor {sensor_id}: {status}")

print("\n" + "=" * 60)
print("All examples completed successfully!")
print("=" * 60)

# Cleanup
import shutil

shutil.rmtree("calibration_data", ignore_errors=True)
shutil.rmtree("my_custom_calibrations", ignore_errors=True)
import os

if os.path.exists("exported_sensor_FSR_SN12345.json"):
    os.remove("exported_sensor_FSR_SN12345.json")
