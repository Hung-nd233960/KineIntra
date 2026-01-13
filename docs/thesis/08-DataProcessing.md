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

```python
# FSR characteristic: R = k / F^n (power law approximation)
# Requires calibration to determine k and n

def resistance_to_force(resistance: float, k: float, n: float) -> float:
    """Convert FSR resistance to force using power law."""
    if resistance <= 0:
        return float('inf')
    return (k / resistance) ** (1 / n)

# Example calibration coefficients (sensor-specific)
force = resistance_to_force(resistance=5000, k=1e6, n=1.2)
```

## 8.4 Data Cleaning

### 8.4.1 Metadata Removal

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

### 8.4.2 Data Validation

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

## 8.5 Experiment Organization

### 8.5.1 Directory Structure

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

### 8.5.2 Naming Conventions

| Pattern | Example | Description |
|---------|---------|-------------|
| `{weight}g_load.csv` | `100g_load.csv` | Loading at 100g |
| `{weight}g_unload.csv` | `100g_unload.csv` | Unloading from 100g |
| `baseline.csv` | `baseline.csv` | No load reference |
| `run{n}/` | `run1/` | Repeated trials |

## 8.6 Experiment Analyzer

### 8.6.1 Analysis Framework

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

### 8.6.2 Typical Analysis Workflow

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

## 8.7 Visualization Types

### 8.7.1 Time Series

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

### 8.7.2 Calibration Curve

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

### 8.7.3 Hysteresis Loop

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

## 8.8 Performance Metrics

### 8.8.1 Sensor Characterization

| Metric | Description | Typical Value |
|--------|-------------|---------------|
| **Sensitivity** | ΔV / ΔForce | ~5 mV/g |
| **Linearity** | R² of linear fit | >0.95 |
| **Hysteresis** | Max deviation load/unload | <5% FS |
| **Repeatability** | σ over repeated trials | <2% FS |
| **Response time** | 10–90% rise time | <10 ms |

### 8.8.2 System Characterization

| Metric | Description | Measured |
|--------|-------------|----------|
| **Sample rate** | Actual vs configured | 99.8% accuracy |
| **Timing jitter** | σ of sample intervals | <1 ms |
| **Data loss** | Dropped frames | 0% (CRC protected) |
| **Latency** | Command to response | <5 ms |

## 8.9 File References

| Component | File |
|-----------|------|
| ADC conversion | [kineintra/FSR_signal/adc_signal.py](../../kineintra/FSR_signal/adc_signal.py) |
| Metadata cleaner | [data_processing/delete_hioki_metadata.py](../../data_processing/delete_hioki_metadata.py) |
| Analyzer | [data_processing/experiment_analyzer.py](../../data_processing/experiment_analyzer.py) |
| Experiment data | [data_processing/exp_13_12](../../data_processing/exp_13_12), [data_processing/silicon_22_12](../../data_processing/silicon_22_12) |
