from enum import Enum


class MeasuringResistor(Enum):
    """Enum to indicate which resistor is being measured in a voltage divider."""

    KNOWN_RESISTOR = 1
    UNKNOWN_RESISTOR = 2


def adc_signal_to_voltage(
    adc_signal: int, max_voltage: float = 1.024, resolution: int = 1024
) -> float:
    """Convert ADC signal to voltage.

    Args:
        adc_signal (int): The ADC signal value.
        max_voltage (float, optional): The maximum reference voltage. Defaults to 1.024V.
        resolution (int, optional): The ADC resolution. Defaults to 1024.

    Returns:
        float: The corresponding voltage.
    """
    voltage = (adc_signal / resolution) * max_voltage
    return voltage


def voltage_to_resistance(
    source_voltage: float,
    known_resistance: float,
    measured_voltage: float,
    measuring_resistance: MeasuringResistor = MeasuringResistor.UNKNOWN_RESISTOR,
) -> float:
    """Calculate resistance from voltage divider.
    Voltage divider formula:
    Vout = Vin * (R2 / (R1 + R2))
    Rearranged to find R2:
    R2 = R1 * (Vout / (Vin - Vout))  (if R2 is unknown resistor)
    R1 = R2 * ((Vin - Vout) / Vout)  (if R1 is unknown resistor)
    Args:
        source_voltage (float): The source voltage.
        measured_voltage (float): The measured voltage across the known resistor.
        known_resistance (float): The known resistance value.
        measuring_resistance (MeasuringResistor, optional): Indicates which resistor is being measured.
        Defaults to MeasuringResistor.UNKNOWN_RESISTOR.

    Returns:
        float: The calculated resistance.
    """
    if measured_voltage == 0:
        raise ValueError("Measured voltage cannot be zero.")
    if measuring_resistance == MeasuringResistor.UNKNOWN_RESISTOR:
        resistance = (known_resistance * measured_voltage) / (
            source_voltage - measured_voltage
        )
    else:
        resistance = (
            known_resistance * (source_voltage - measured_voltage)
        ) / measured_voltage

    return resistance


def adc_signal_to_resistance(
    adc_signal: int,
    source_voltage: float,
    known_resistance: float,
    measuring_resistance: MeasuringResistor = MeasuringResistor.UNKNOWN_RESISTOR,
    max_voltage: float = 1.024,
    resolution: int = 1024,
) -> float:
    """Convert ADC signal to resistance using voltage divider principles.

    Args:
        adc_signal (int): The ADC signal value.
        source_voltage (float): The source voltage.
        known_resistance (float): The known resistance value.
        measuring_resistance (MeasuringResistor, optional): Indicates which resistor is being measured.
            Defaults to MeasuringResistor.UNKNOWN_RESISTOR.
        max_voltage (float, optional): The maximum reference voltage. Defaults to 1.024V.
        resolution (int, optional): The ADC resolution. Defaults to 1024.

    Returns:
        float: The calculated resistance.
    """
    measured_voltage = adc_signal_to_voltage(
        adc_signal, max_voltage=max_voltage, resolution=resolution
    )
    resistance = voltage_to_resistance(
        source_voltage,
        known_resistance,
        measured_voltage,
        measuring_resistance,
    )
    return resistance
