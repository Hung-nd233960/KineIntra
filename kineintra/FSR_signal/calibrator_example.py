"""Example usage of the calibrator module."""

from kineintra.FSR_signal.calibrator import Calibrator

# Example data: resistance (R) and force (F)
R = [2200, 1800, 1500, 1200]
F = [5, 10, 20, 35]

# Create and fit exponential model
cal = Calibrator("exp")
model = cal.fit(R, F)

print("=== Model Statistics ===")
print(model.stats)

# Save model
cal.save("fsr_model.json")
print("\nModel saved to fsr_model.json")

# Make predictions
print("\n=== Predictions ===")
test_resistances = [2000, 1600, 1300]
for r in test_resistances:
    prediction = cal.predict(r)
    print(f"R={r}Ω -> F={prediction:.2f}")

# Load model and test
print("\n=== Loading Model ===")
loaded = Calibrator.load("fsr_model.json")
print("Model loaded successfully")
print(f"Prediction for R=1600Ω: {loaded.predict(1600):.2f}")

# Test polynomial model
print("\n=== Polynomial Model ===")
cal_poly = Calibrator("poly")
model_poly = cal_poly.fit(R, F)
print("Polynomial model statistics:")
print(model_poly.stats)

print("\nAll tests passed!")
