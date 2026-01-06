# Calibration Procedure for KineIntra FSR Sensor Block

## Protocol Version 1.1 - Calibration Supplement

This document defines the specific, multi-step communication and host-side data collection procedure required to calibrate the Force Sensitive Resistor (FSR) sensor block.

---

## 1. New Command Definition

To support the calibration procedure, the following command is introduced:

### 7.2 Command IDs (Updated Supplement)

| CmdID (hex) | Name | Description |
| --- | --- | --- |
| `0x09` | **END_CALIBRATE** | Stop data acquisition for the current calibration phase and transition the device state. |

### 7.4 Command Arguments (Updated Supplement)

| CmdID | Args Format | Notes |
| --- | --- | --- |
| END_CALIBRATE | none | Sent by Host to end a specific sensor's calibration cycle or the entire calibration sequence. |

---

## 2. Calibration Communication Procedure

The device MUST be in the **IDLE** state (`0x00`) before the Host initiates the calibration. The device operational state during active calibration is **CALIBRATING** (`0x02`).

### 2.1 State Transition and Per-Sensor Cycle

The procedure involves multiple cycles, one for each sensor to be calibrated.

| Step | Initiator | Frame Type / CmdID | Payload Details / Action | Expected Device State | Notes |
| --- | --- | --- | --- | --- | --- |
| 0 | Host | `COMMAND` / **`CALIBRATE`** (`0x08`) | Start calibration sequence. Previous state MUST be IDLE. | IDLE  CALIBRATING | Device sends `ACK` (0x00=OK) then `STATUS`. |
| 1 | Device | `STATUS` (`0x01`) | Report current device/sensor status. | CALIBRATING | Transmitted after successful `CALIBRATE` command ACK. |
| 2 | Host | `COMMAND` / **`SET_ACTIVEMAP`** (`0x07`) | `uint32 ActiveMap` to enable **ONE** sensor only. | CALIBRATING | If more than one sensor is enabled, device DENIES with `ACK` (`0x05`=NOT_ALLOWED). Device sends `ACK` (0x00=OK) upon success. |
| 3 | Host | `COMMAND` / **`START_MEASURE`** (`0x02`) | Initiates data streaming for the single active sensor. | CALIBRATING  MEASURING | Device sends `ACK` (0x00=OK). |
| 4 | Device | `DATA` (`0x02`) | Transmits sensor samples at **** as per current spec. | MEASURING | Data streaming continues until a `STOP_MEASURE` or `END_CALIBRATE` command is received. |
| 5 | Host | `COMMAND` / **`END_CALIBRATE`** (`0x09`) | Stops data acquisition for the current sensor calibration cycle. | MEASURING  CALIBRATING | Device sends `ACK` (0x00=OK). **Repeat Steps 2-5** until all required sensors are calibrated. |
| 6 | Host | `COMMAND` / **`END_CALIBRATE`** (`0x09`) | Ends the entire calibration sequence. | CALIBRATING  IDLE | Device sends `ACK` (0x00=OK) and may optionally send a final `STATUS` frame. |

### 2.2 Device Responsibilities During Calibration

* Device SHALL transmit a `STATUS` frame in response to a `COMMAND` / `GET_STATUS` request.
* Device SHALL **NOT** transmit periodic `STATUS` frames while in the CALIBRATING or MEASURING states during the calibration procedure.
* An incomplete calibration sequence MUST render the sensor unusable until successfully calibrated.

---

## 3. Host Data Acquisition Mission (FSR)

The Host is responsible for controlling the physical stimuli and collecting the resulting sensor data over a fixed duration  for multiple weights  and repetitions .

### 3.1 Data Acquisition Parameters (Version 1.0)

| Parameter | Value | Description |
| --- | --- | --- |
| **Data Acquisition Rate (F)** | **10Hz** | The expected rate of `DATA` frames from the device. |
| **Acquisition Time (T)** | **120s** | The duration for collecting data per weight/state (baseline, loaded). |
| **Test Weights (W)** | **10g, 20g, 50g, 100g, 200g, 500g** | The set of physical weights applied to the FSR sensor. |
| **Repetitions (N)** | **3** | The number of times the full weight cycle (baseline  load  release) is repeated. |

### 3.2 Host Procedure Steps

The Host performs the following steps for **EACH** sensor index:

1. **Baseline Measurement:** Send `START_MEASURE`. Collect sensor data for **T** seconds (baseline resistance). Send `END_CALIBRATE` to stop data streaming.
2. **Load Cycle (Repeat N times):**
a. **Apply Weight :** For each weight **W** in the defined set, physically apply it to the sensor.
b. **Measure Loaded:** Send `START_MEASURE`. Collect sensor data for  seconds. Send `END_CALIBRATE` to stop data streaming.
c. **Release Weight :** Physically remove the weight **W** from the sensor.
d. **Measure Released:** Send `START_MEASURE`. Collect sensor data for **T** seconds. Send `END_CALIBRATE` to stop data streaming.
3. **Data Processing:** Upon completion of all **N** cycles for all weights , the Host SHALL perform exponential regression on the collected data to derive the correlation function between the raw sensor values (e.g., resistance, ADC counts) and the applied weight .
4. **Reporting:** Export the calibration accuracy and results for the sensor.
a. Accuracy includes:
- Error rate
- Average unload resistance
