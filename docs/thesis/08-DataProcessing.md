# Data Processing & Analysis

## 8.1 Data Processing Pipeline

### 8.1.1 Overview

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│  Raw Data   │────►│  Cleaning   │────►│ Conversion  │────►│  Analysis   │
│ (CSV/Serial)│     │  & Metadata │     │ (ADC→Force) │     │ & Graphing  │
└─────────────┘     └─────────────┘     └─────────────┘     └─────────────┘
       │                   │                   │                   │
       ▼                   ▼                   ▼                   ▼
  Timestamps,         Clean CSV,         Voltage,           Graphs,
  ADC values          Headers            Resistance,        Statistics,
                                         Force              Reports
```

### 8.1.2 Pipeline Stages

| Stage | Input | Output | Tools |
|-------|-------|--------|-------|
| **Acquisition** | Device DATA frames | Timestamped CSV | CLI `--record` |
| **Cleaning** | Raw CSV with metadata | Clean CSV | `delete_hioki_metadata.py` |
| **Conversion** | ADC values | Physical units | `adc_signal.py` |
| **Analysis** | Clean data files | Graphs, statistics | `experiment_analyzer.py` |

## 8.2 Data Acquisition

### 8.2.1 Recording via CLI

```bash
# Record to CSV while monitoring
python -m kineintra.cli connect --port /dev/ttyUSB0 --monitor --record data.csv

# Record for specific duration
python -m kineintra.cli connect --port /dev/ttyUSB0 --start --record --duration 60
```

### 8.2.2 CSV Format

```csv
Timestamp_MCU_ms,ADC_Raw,Voltage_V,Status,PC_Time
12345,1234,0.5432,NORMAL,14:32:05.123
12445,1235,0.5438,NORMAL,14:32:05.223
12545,1236,0.5445,NORMAL,14:32:05.323
```

### 8.2.3 Multi-Sensor Format

```csv
Timestamp_ms,Sensor0,Sensor1,Sensor2,Sensor3,Sensor4,Sensor5,Sensor6,Sensor7
12345,1234,2345,3456,4567,1111,2222,3333,4444
12445,1235,2346,3457,4568,1112,2223,3334,4445
```

## 8.3 Signal Conversion

### 8.3.1 ADC to Voltage

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_voltage

# ADS1115 with GAIN_FOUR: ±1.024V range, 16-bit resolution
voltage = adc_signal_to_voltage(
    adc_signal=1234,
    max_voltage=1.024,
    resolution=32768  # 2^15 for signed 16-bit
)
# Result: 0.0386V
```

**Formula:**
$$V_{out} = \frac{ADC_{value}}{Resolution} \times V_{max}$$

### 8.3.2 Voltage to Resistance (Voltage Divider)

```python
from kineintra.FSR_signal.adc_signal import (
    voltage_to_resistance,
    MeasuringResistor
)

# Voltage divider: Vcc ─┬─ R_known ─┬─ R_fsr ─┬─ GND
#                       │           │         │
#                       │           └─ V_out ─┘
#                       │
#                       └─ V_source

resistance = voltage_to_resistance(
    source_voltage=3.3,
    known_resistance=1000.0,  # 1kΩ
    measured_voltage=0.5,
    measuring_resistance=MeasuringResistor.UNKNOWN_RESISTOR
)
# Result: ~178.6Ω
```

**Formulas:**

- Unknown resistor (R₂): $R_2 = R_1 \times \frac{V_{out}}{V_{in} - V_{out}}$
- Known resistor (R₁): $R_1 = R_2 \times \frac{V_{in} - V_{out}}{V_{out}}$

### 8.3.3 Combined ADC to Resistance

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance

resistance = adc_signal_to_resistance(
    adc_signal=1234,
    source_voltage=3.3,
    known_resistance=1000.0,
    measuring_resistance=MeasuringResistor.UNKNOWN_RESISTOR,
    max_voltage=1.024,
    resolution=32768
)
```

### 8.3.4 Resistance to Force (FSR Calibration)

FSR sensors exhibit a non-linear resistance-to-force relationship. The calibration framework in `kineintra.FSR_signal.calibrator` provides a modular system for fitting and applying calibration models.

#### Basic Calibration Workflow

```python
from kineintra.FSR_signal.calibrator import Calibrator

# Calibration data: resistance (R) and force (F)
R = [2200, 1800, 1500, 1200]  # Resistance values (Ω)
F = [5, 10, 20, 35]            # Force values (N or g)

# Create and train calibrator with exponential model
cal = Calibrator("exp")
model = cal.fit(R, F)

# View statistics
print(model.stats)
# {'rmse': 0.491, 'mae': 0.399, 'r2': 0.998, 'n': 4}

# Make predictions
predicted_force = cal.predict(1600)
print(f"Force at 1600Ω: {predicted_force:.2f}N")

# Save model for later use
cal.save("fsr_model.json")

# Load model in another session
loaded_cal = Calibrator.load("fsr_model.json")
```

#### Available Calibration Algorithms

| Algorithm | Name | Model | Use Case |
|-----------|------|-------|----------|
| **Exponential** | `"exp"` | $F = a \cdot e^{bR}$ | FSR typical response curve |
| **Polynomial** | `"poly"` | $F = \sum_{i=0}^{n} c_i R^i$ | Complex non-linear response |

#### Exponential Model Details

The exponential model fits the characteristic FSR response:

$$F = a \cdot e^{bR}$$

Implementation uses linear regression on log-transformed force values:

$$\ln(F) = bR + \ln(a)$$

```python
from kineintra.FSR_signal.calibrator import Calibrator

cal = Calibrator("exp")
model = cal.fit(R, F)

# Access fitted parameters
print(f"a = {model.algorithm.a:.4f}")
print(f"b = {model.algorithm.b:.6f}")
```

#### Polynomial Model Details

For sensors with more complex characteristics, a polynomial fit may be appropriate:

$$F = c_n R^n + c_{n-1} R^{n-1} + \ldots + c_1 R + c_0$$

```python
from kineintra.FSR_signal.calibrator import Calibrator

# Default is 3rd degree polynomial
cal = Calibrator("poly")
model = cal.fit(R, F)
```

## 8.4 FSR Signal Processing Module

The `kineintra.FSR_signal` module provides a complete signal processing pipeline for Force Sensitive Resistors.

### 8.4.1 Module Architecture

```
FSR_signal/
├── adc_signal.py              # ADC to physical units conversion
├── calibrator/
│   ├── calibrator.py          # Single-sensor calibrator
│   ├── multi_sensor_calibrator.py  # Multi-sensor management
│   ├── algorithms/
│   │   ├── base.py            # Abstract Algorithm interface
│   │   ├── exponential.py     # F = a*exp(b*R) model
│   │   └── polynomial.py      # Polynomial model
│   ├── models/
│   │   ├── calibration_model.py    # Model wrapper
│   │   └── sensor_profile.py       # Per-sensor profile
│   ├── io/
│   │   ├── storage.py              # Single model JSON I/O
│   │   └── multi_sensor_storage.py # Multi-sensor storage
│   └── analysis/
│       └── statistics.py      # RMSE, MAE, R² functions
```

### 8.4.2 Algorithm Interface

All calibration algorithms implement a uniform interface:

```python
from abc import ABC, abstractmethod

class Algorithm(ABC):
    """Base interface for calibration algorithms."""
    
    name: str = "base"
    
    @abstractmethod
    def learn(self, X, y) -> None:
        """Train algorithm with resistance (X) and force (y) data."""
        ...
    
    @abstractmethod
    def predict(self, X) -> float | ndarray:
        """Predict force from resistance values."""
        ...
    
    @abstractmethod
    def stats(self) -> dict:
        """Return training statistics (rmse, r2, n_samples)."""
        ...
    
    def to_dict(self) -> dict:
        """Serialize algorithm parameters to dictionary."""
        ...
    
    @classmethod
    def from_dict(cls, d) -> "Algorithm":
        """Reconstruct algorithm from dictionary."""
        ...
```

### 8.4.3 Creating Custom Algorithms

To add a new calibration algorithm:

```python
from kineintra.FSR_signal.calibrator.algorithms.base import Algorithm
import numpy as np

class PowerLawModel(Algorithm):
    """Power law model: F = k / R^n"""
    
    name = "power"
    
    def __init__(self, k=None, n=None):
        self.k = k
        self.n = n
        self.training_stats = {}
    
    def learn(self, X, y):
        # Log-linear regression: log(F) = log(k) - n*log(R)
        logR = np.log(X)
        logF = np.log(y)
        n_val, logk = np.polyfit(logR, logF, 1)
        self.n = -n_val
        self.k = np.exp(logk)
    
    def predict(self, X):
        return self.k / (np.array(X) ** self.n)
    
    def stats(self):
        return self.training_stats.copy()
```

Register in `algorithms/__init__.py`:

```python
from .power_law import PowerLawModel

ALGO_REGISTRY = {
    cls.name: cls 
    for cls in [ExpModel, PolyModel, PowerLawModel]
}
```

### 8.4.4 Model Persistence Format

Models are saved as JSON with algorithm parameters and metadata:

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

### 8.4.5 Evaluation Metrics

| Metric | Formula | Description |
|--------|---------|-------------|
| **RMSE** | $\sqrt{\frac{1}{n}\sum(y_i - \hat{y}_i)^2}$ | Root Mean Squared Error |
| **MAE** | $\frac{1}{n}\sum|y_i - \hat{y}_i|$ | Mean Absolute Error |
| **R²** | $1 - \frac{SS_{res}}{SS_{tot}}$ | Coefficient of Determination |

Target values for a good calibration:

- RMSE: As low as possible (sensor-dependent)
- MAE: < 5% of full scale
- R²: > 0.95 (ideally > 0.99)

## 8.5 Multi-Sensor Calibration

### 8.5.1 Overview

For systems with multiple FSR sensors, the `MultiSensorCalibrator` manages individual calibration profiles per sensor, each identified by a unique sensor ID or serial number.

```python
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator

# Initialize multi-sensor calibrator
msc = MultiSensorCalibrator()

# Calibrate individual sensors
msc.calibrate("FSR_001", R1, F1, algorithm_name="exp")
msc.calibrate("FSR_002", R2, F2, algorithm_name="poly")
msc.calibrate("FSR_003", R3, F3, algorithm_name="exp")

# Predict for specific sensor
force = msc.predict("FSR_001", resistance=1500)

# List all calibrated sensors
sensors = msc.list_sensors()
print(sensors)  # ['FSR_001', 'FSR_002', 'FSR_003']
```

### 8.5.2 Sensor Profile Management

Each sensor has an individual calibration profile with metadata:

```python
profile = msc.calibrate(
    sensor_id="FSR_THUMB_01",
    X=resistance_data,
    y=force_data,
    algorithm_name="exp",
    metadata={
        "operator": "John Doe",
        "environment": "Lab Room A, 25°C, 60% RH",
        "notes": "Calibrated with 50g-500g weights",
        "sensor_location": "Thumb fingertip",
    },
    auto_save=True,  # Automatically persist to storage
)

# Access profile metadata
print(profile.sensor_id)
print(profile.metadata)
print(profile.calibration_date)
```

### 8.5.3 Profile Persistence

Profiles are automatically saved to a storage directory:

```
calibration_profiles/
├── FSR_001.json
├── FSR_002.json
└── FSR_003.json
```

Load profiles in a new session:

```python
msc = MultiSensorCalibrator()

# Load specific profile
profile = msc.load_profile("FSR_001")

# Or let predict() auto-load
force = msc.predict("FSR_001", resistance=1500)
```

## 8.6 Complete Signal Processing Pipeline

### 8.6.1 End-to-End Example

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance, MeasuringResistor
from kineintra.FSR_signal.calibrator import Calibrator

# Step 1: Load calibration model
cal = Calibrator.load("fsr_model.json")

# Step 2: Read ADC value from sensor
adc_value = 512  # From hardware

# Step 3: Convert ADC to resistance
resistance = adc_signal_to_resistance(
    adc_signal=adc_value,
    source_voltage=3.3,
    known_resistance=10000,  # 10kΩ reference resistor
    measuring_resistance=MeasuringResistor.UNKNOWN_RESISTOR,
    max_voltage=1.024,       # ADS1115 GAIN_FOUR
    resolution=32768,        # 16-bit ADC
)

# Step 4: Convert resistance to force
force = cal.predict(resistance)
print(f"Applied force: {force:.2f}N")
```

### 8.6.2 Real-Time Processing

```python
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance
from kineintra.FSR_signal.calibrator import Calibrator

# Load calibration once at startup
cal = Calibrator.load("fsr_model.json")

def process_sample(adc_value: int) -> float:
    """Process single ADC sample to force value."""
    resistance = adc_signal_to_resistance(
        adc_signal=adc_value,
        source_voltage=3.3,
        known_resistance=10000,
    )
    return cal.predict(resistance)

# Use in data acquisition loop
for adc_sample in sensor_stream:
    force = process_sample(adc_sample)
    print(f"Force: {force:.2f}N")
```

## 8.7 Data Cleaning

### 8.7.1 Metadata Removal

```python
# delete_hioki_metadata.py
# Removes instrument-specific headers from Hioki data logger exports

def clean_hioki_csv(input_path: str, output_path: str):
    """Remove Hioki metadata lines and extract pure data."""
    with open(input_path, 'r') as f:
        lines = f.readlines()

    # Find data start (skip metadata)
    data_start = 0
    for i, line in enumerate(lines):
        if line.startswith('Time') or line.startswith('Timestamp'):
            data_start = i
            break

    # Write clean data
    with open(output_path, 'w') as f:
        f.writelines(lines[data_start:])
```

### 8.7.2 Data Validation

```python
def validate_data(df: pd.DataFrame) -> pd.DataFrame:
    """Clean and validate sensor data."""
    # Remove rows with NaN
    df = df.dropna()

    # Remove outliers (>3σ)
    for col in df.columns:
        if col.startswith('Sensor'):
            mean, std = df[col].mean(), df[col].std()
            df = df[(df[col] - mean).abs() <= 3 * std]

    # Ensure monotonic timestamps
    df = df.sort_values('Timestamp_ms')

    return df
```

## 8.8 Experiment Organization

### 8.8.1 Directory Structure

```
data_processing/
├── exp_13_12/                    # Experiment: December 13
│   ├── baseline.csv              # Baseline (no load)
│   ├── soft_cap/                 # Soft cap condition
│   │   ├── load1.csv             # Loading sequence
│   │   ├── load2.csv
│   │   ├── unload1.csv           # Unloading sequence
│   │   └── ...
│   ├── solid_cap/                # Solid cap condition
│   │   ├── run1/
│   │   └── run2/
│   └── graphs/                   # Generated visualizations
│
├── silicon_22_12/                # Experiment: December 22
│   ├── run1/
│   │   ├── 0g_unload.csv         # Named by weight
│   │   ├── 10g_load.csv
│   │   ├── 10g_unload.csv
│   │   ├── 100g_load.csv
│   │   └── ...
│   └── run2/
│
├── delete_hioki_metadata.py      # Cleaning utility
└── experiment_analyzer.py        # Analysis framework
```

### 8.8.2 Naming Conventions

| Pattern | Example | Description |
|---------|---------|-------------|
| `{weight}g_load.csv` | `100g_load.csv` | Loading at 100g |
| `{weight}g_unload.csv` | `100g_unload.csv` | Unloading from 100g |
| `baseline.csv` | `baseline.csv` | No load reference |
| `run{n}/` | `run1/` | Repeated trials |

## 8.9 Experiment Analyzer

### 8.9.1 Analysis Framework

```python
class ExperimentAnalyzer:
    """Framework for analyzing sensor experiments."""

    def __init__(self, experiment_dir: str):
        self.exp_dir = Path(experiment_dir)
        self.data = {}
        self.results = {}

    def load_all_runs(self) -> None:
        """Load all CSV files in experiment directory."""
        for csv_file in self.exp_dir.glob('**/*.csv'):
            name = csv_file.stem
            self.data[name] = pd.read_csv(csv_file)

    def compute_statistics(self) -> Dict[str, Dict]:
        """Compute statistics for each run."""
        for name, df in self.data.items():
            self.results[name] = {
                'mean': df['ADC_Raw'].mean(),
                'std': df['ADC_Raw'].std(),
                'min': df['ADC_Raw'].min(),
                'max': df['ADC_Raw'].max(),
                'samples': len(df)
            }
        return self.results

    def plot_time_series(self, run_name: str, save_path: str = None):
        """Plot ADC values over time."""
        df = self.data[run_name]
        plt.figure(figsize=(12, 6))
        plt.plot(df['Timestamp_ms'], df['ADC_Raw'])
        plt.xlabel('Time (ms)')
        plt.ylabel('ADC Value')
        plt.title(f'Time Series: {run_name}')
        if save_path:
            plt.savefig(save_path)
        plt.show()

    def plot_load_unload_hysteresis(self, load_runs: List[str], 
                                     unload_runs: List[str]):
        """Plot hysteresis curve (load vs unload)."""
        # Extract weights from run names
        load_data = [(self._extract_weight(r), self.data[r]['ADC_Raw'].mean()) 
                     for r in load_runs]
        unload_data = [(self._extract_weight(r), self.data[r]['ADC_Raw'].mean()) 
                       for r in unload_runs]

        plt.figure(figsize=(10, 8))
        plt.plot(*zip(*sorted(load_data)), 'b-o', label='Loading')
        plt.plot(*zip(*sorted(unload_data)), 'r-s', label='Unloading')
        plt.xlabel('Weight (g)')
        plt.ylabel('Mean ADC Value')
        plt.title('Load-Unload Hysteresis')
        plt.legend()
        plt.grid(True)
        plt.show()
```

### 8.9.2 Typical Analysis Workflow

```python
# 1. Load experiment
analyzer = ExperimentAnalyzer('data_processing/silicon_22_12/run1')
analyzer.load_all_runs()

# 2. Compute statistics
stats = analyzer.compute_statistics()
print(pd.DataFrame(stats).T)

# 3. Plot time series
analyzer.plot_time_series('100g_load', save_path='graphs/100g_load.png')

# 4. Plot hysteresis
load_runs = ['10g_load', '20g_load', '50g_load', '100g_load', '200g_load', '500g_load']
unload_runs = ['500g_unload', '200g_unload', '100g_unload', '50g_unload', '20g_unload', '10g_unload']
analyzer.plot_load_unload_hysteresis(load_runs, unload_runs)

# 5. Generate report
analyzer.generate_report('experiment_report.html')
```

## 8.10 Visualization Types

### 8.10.1 Time Series

```
ADC Value
   │     ┌────────────────────┐
   │     │  100g applied      │
3000┤    │                    │
   │ ────┘                    └────
2000┤
   │ ──────────────────────────────  (baseline)
1000┤
   │
   └───────────────────────────────► Time (ms)
       0    1000   2000   3000
```

### 8.10.2 Calibration Curve

```
Force (g)
   │
500┤                        ●
   │                    ●
200┤                ●
100┤            ●
50 ┤        ●
20 ┤    ●
10 ┤  ●
   └───────────────────────────────► ADC Value
      1000  1500  2000  2500  3000
```

### 8.10.3 Hysteresis Loop

```
ADC Value
   │
3000┤  ●───────────●
   │  │ Loading    │ Unloading
   │  ↓            ↑
2000┤  ●───────────●
   │  │            │
   │  ↓            ↑
1000┤  ●───────────●
   │
   └───────────────────────────────► Weight (g)
      0   100   200   300   400   500
```

## 8.11 Performance Metrics

### 8.11.1 Sensor Characterization

| Metric | Description | Typical Value |
|--------|-------------|---------------|
| **Sensitivity** | ΔV / ΔForce | ~5 mV/g |
| **Linearity** | R² of linear fit | >0.95 |
| **Hysteresis** | Max deviation load/unload | <5% FS |
| **Repeatability** | σ over repeated trials | <2% FS |
| **Response time** | 10–90% rise time | <10 ms |

### 8.11.2 System Characterization

| Metric | Description | Measured |
|--------|-------------|----------|
| **Sample rate** | Actual vs configured | 99.8% accuracy |
| **Timing jitter** | σ of sample intervals | <1 ms |
| **Data loss** | Dropped frames | 0% (CRC protected) |
| **Latency** | Command to response | <5 ms |

## 8.12 End-to-End Workflow Example

This section demonstrates a complete data processing pipeline from sensor acquisition through calibration to analysis.

### 8.12.1 Complete Calibration and Analysis Pipeline

```python
"""Complete FSR data processing pipeline example."""

import pandas as pd
from pathlib import Path
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance, MeasuringResistor
from kineintra.FSR_signal.calibrator import Calibrator, MultiSensorCalibrator

# ============================================================
# STEP 1: Load raw calibration data
# ============================================================
calibration_data = {
    # Known weights (g) -> measured ADC values (averaged)
    "weights": [0, 10, 20, 50, 100, 200, 500],
    "adc_values": [32000, 28500, 25000, 18000, 12000, 6500, 2000],
}

# Convert ADC to resistance for calibration
CIRCUIT_CONFIG = {
    "source_voltage": 3.3,
    "known_resistance": 10000,  # 10kΩ reference
    "max_voltage": 1.024,       # ADS1115 GAIN_FOUR
    "resolution": 32768,        # 16-bit signed
}

resistances = [
    adc_signal_to_resistance(
        adc_signal=adc,
        source_voltage=CIRCUIT_CONFIG["source_voltage"],
        known_resistance=CIRCUIT_CONFIG["known_resistance"],
        measuring_resistance=MeasuringResistor.UNKNOWN_RESISTOR,
        max_voltage=CIRCUIT_CONFIG["max_voltage"],
        resolution=CIRCUIT_CONFIG["resolution"],
    )
    for adc in calibration_data["adc_values"]
]

# ============================================================
# STEP 2: Train and save calibration model
# ============================================================
calibrator = Calibrator("exp")
model = calibrator.fit(resistances, calibration_data["weights"])

print(f"Calibration Statistics:")
print(f"  RMSE: {model.stats['rmse']:.3f} g")
print(f"  MAE:  {model.stats['mae']:.3f} g")
print(f"  R²:   {model.stats['r2']:.4f}")

# Save for production use
calibrator.save("fsr_sensor_01.json")

# ============================================================
# STEP 3: Process experiment data
# ============================================================
def process_experiment_file(csv_path: str, calibrator: Calibrator) -> pd.DataFrame:
    """Process a raw experiment CSV file."""
    df = pd.read_csv(csv_path)
    
    # Convert ADC to resistance
    df["Resistance_Ohm"] = df["ADC_Raw"].apply(
        lambda adc: adc_signal_to_resistance(
            adc_signal=int(adc),
            **CIRCUIT_CONFIG,
            measuring_resistance=MeasuringResistor.UNKNOWN_RESISTOR,
        )
    )
    
    # Convert resistance to force using calibration
    df["Force_g"] = df["Resistance_Ohm"].apply(calibrator.predict)
    
    return df

# Process all experiment files
experiment_dir = Path("data_processing/silicon_22_12/run1")
results = {}

for csv_file in experiment_dir.glob("*.csv"):
    df = process_experiment_file(str(csv_file), calibrator)
    results[csv_file.stem] = {
        "mean_force": df["Force_g"].mean(),
        "std_force": df["Force_g"].std(),
        "min_force": df["Force_g"].min(),
        "max_force": df["Force_g"].max(),
        "samples": len(df),
    }

# ============================================================
# STEP 4: Generate analysis report
# ============================================================
report_df = pd.DataFrame(results).T
print("\nExperiment Analysis Report:")
print(report_df.to_string())

# Save processed data
report_df.to_csv("experiment_results.csv")
```

### 8.12.2 Multi-Sensor Real-Time Processing

```python
"""Multi-sensor real-time data processing example."""

from kineintra.api import DeviceClient
from kineintra.FSR_signal.adc_signal import adc_signal_to_resistance
from kineintra.FSR_signal.calibrator import MultiSensorCalibrator
import csv
from datetime import datetime

# ============================================================
# SETUP: Load calibration profiles for all sensors
# ============================================================
msc = MultiSensorCalibrator()

# Load pre-calibrated sensor profiles
sensor_ids = ["FSR_THUMB", "FSR_INDEX", "FSR_MIDDLE", "FSR_RING", "FSR_PINKY"]
for sid in sensor_ids:
    try:
        msc.load_profile(sid)
        print(f"Loaded profile: {sid}")
    except FileNotFoundError:
        print(f"Warning: No profile for {sid}, using default")

# ============================================================
# REAL-TIME PROCESSING
# ============================================================
def process_data_frame(payload, msc, writer):
    """Process incoming DATA frame and write to CSV."""
    timestamp = payload.timestamp
    
    row = {"timestamp_ms": timestamp}
    
    for sensor_idx, adc_value in payload.samples.items():
        # Convert ADC to resistance
        resistance = adc_signal_to_resistance(
            adc_signal=adc_value,
            source_voltage=3.3,
            known_resistance=10000,
        )
        
        # Get sensor ID and predict force
        sensor_id = sensor_ids[sensor_idx] if sensor_idx < len(sensor_ids) else f"S{sensor_idx}"
        
        try:
            force = msc.predict(sensor_id, resistance)
        except ValueError:
            force = None  # No calibration available
        
        row[f"{sensor_id}_adc"] = adc_value
        row[f"{sensor_id}_resistance"] = resistance
        row[f"{sensor_id}_force_g"] = force
    
    writer.writerow(row)
    return row

# ============================================================
# MAIN ACQUISITION LOOP
# ============================================================
client = DeviceClient()

if client.connect(port="/dev/ttyUSB0"):
    # Open output file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    with open(f"acquisition_{timestamp}.csv", "w", newline="") as f:
        writer = None
        
        def on_data(payload):
            nonlocal writer
            row = process_data_frame(payload, msc, writer) if writer else None
            if row and writer is None:
                # Initialize CSV with headers from first row
                writer = csv.DictWriter(f, fieldnames=row.keys())
                writer.writeheader()
                writer.writerow(row)
        
        client.on_data(on_data)
        client.start_measure(seq=1)
        
        try:
            input("Press Enter to stop acquisition...")
        finally:
            client.stop_measure(seq=2)
            client.disconnect()
```

## 8.13 File References

| Component | File |
|-----------|------|
| ADC conversion | [kineintra/FSR_signal/adc_signal.py](../../kineintra/FSR_signal/adc_signal.py) |
| Single-sensor calibrator | [kineintra/FSR_signal/calibrator/calibrator.py](../../kineintra/FSR_signal/calibrator/calibrator.py) |
| Multi-sensor calibrator | [kineintra/FSR_signal/calibrator/multi_sensor_calibrator.py](../../kineintra/FSR_signal/calibrator/multi_sensor_calibrator.py) |
| Exponential algorithm | [kineintra/FSR_signal/calibrator/algorithms/exponential.py](../../kineintra/FSR_signal/calibrator/algorithms/exponential.py) |
| Polynomial algorithm | [kineintra/FSR_signal/calibrator/algorithms/polynomial.py](../../kineintra/FSR_signal/calibrator/algorithms/polynomial.py) |
| Metadata cleaner | [data_processing/delete_hioki_metadata.py](../../data_processing/delete_hioki_metadata.py) |
| Analyzer | [data_processing/experiment_analyzer.py](../../data_processing/experiment_analyzer.py) |
| Experiment data | [data_processing/exp_13_12](../../data_processing/exp_13_12), [data_processing/silicon_22_12](../../data_processing/silicon_22_12) |
