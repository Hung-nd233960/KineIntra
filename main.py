from machine import Pin, ADC
import time

adc = ADC(Pin(4))
adc.atten(ADC.ATTN_11DB)
adc.width(ADC.WIDTH_12BIT)

try:
    while True:
        value = adc.read()
        voltage = value / 4095 * 3.3
        print("ADC value:", value, "Voltage:", round(voltage,2))
        time.sleep(0.1)   # important: small sleep allows REPL to be responsive
except KeyboardInterrupt:
    print("Stopped by user")
