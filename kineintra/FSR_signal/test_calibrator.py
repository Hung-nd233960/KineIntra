"""Comprehensive tests for the calibrator module."""

from pathlib import Path

import numpy as np

from kineintra.FSR_signal.calibrator import (
    ALGO_REGISTRY,
    Calibrator,
    ExpModel,
    PolyModel,
    mae,
    r2,
    rmse,
)


def test_statistics():
    """Test statistical functions."""
    print("Testing statistics functions...")
    y_true = [1, 2, 3, 4, 5]
    y_pred = [1.1, 2.1, 2.9, 4.2, 4.8]

    rmse_val = rmse(y_true, y_pred)
    mae_val = mae(y_true, y_pred)
    r2_val = r2(y_true, y_pred)

    assert rmse_val > 0, "RMSE should be positive"
    assert mae_val > 0, "MAE should be positive"
    assert 0 <= r2_val <= 1, "R² should be between 0 and 1"
    print(f"  RMSE: {rmse_val:.4f}")
    print(f"  MAE: {mae_val:.4f}")
    print(f"  R²: {r2_val:.4f}")
    print("✓ Statistics tests passed\n")


def test_exp_model():
    """Test exponential model."""
    print("Testing ExpModel...")
    R = [2200, 1800, 1500, 1200]
    F = [5, 10, 20, 35]

    model = ExpModel()
    model.learn(R, F)

    assert model.a is not None, "Parameter 'a' should be fitted"
    assert model.b is not None, "Parameter 'b' should be fitted"

    # Test prediction
    pred = model.predict(1600)
    assert isinstance(pred, (float, np.floating)), "Single prediction should be float"
    assert pred > 0, "Predicted force should be positive"

    # Test array prediction
    preds = model.predict([1600, 1400])
    assert len(preds) == 2, "Should predict for all inputs"

    print(f"  Fitted parameters: a={model.a:.2f}, b={model.b:.6f}")
    print(f"  Prediction at 1600Ω: {pred:.2f}")
    print("✓ ExpModel tests passed\n")


def test_poly_model():
    """Test polynomial model."""
    print("Testing PolyModel...")
    R = [2200, 1800, 1500, 1200]
    F = [5, 10, 20, 35]

    model = PolyModel(degree=3)
    model.learn(R, F)

    assert model.coeffs is not None, "Coefficients should be fitted"
    assert len(model.coeffs) == 4, "Should have 4 coefficients for degree 3"

    # Test prediction
    pred = model.predict(1600)
    assert isinstance(pred, (float, np.floating)), "Single prediction should be float"
    assert pred > 0, "Predicted force should be positive"

    print(f"  Coefficients: {model.coeffs}")
    print(f"  Prediction at 1600Ω: {pred:.2f}")
    print("✓ PolyModel tests passed\n")


def test_serialization():
    """Test algorithm serialization."""
    print("Testing algorithm serialization...")

    # Test ExpModel
    exp = ExpModel(a=10.5, b=-0.001)
    exp_dict = exp.to_dict()
    assert exp_dict["class"] == "exp", "Should include class name"
    assert exp_dict["a"] == 10.5, "Should serialize parameter a"

    exp_restored = ExpModel.from_dict(exp_dict)
    assert exp_restored.a == 10.5, "Should restore parameter a"
    assert exp_restored.b == -0.001, "Should restore parameter b"

    # Test PolyModel
    poly = PolyModel(degree=2, coeffs=[1.0, 2.0, 3.0])
    poly_dict = poly.to_dict()
    poly_restored = PolyModel.from_dict(poly_dict)
    assert poly_restored.degree == 2, "Should restore degree"
    assert poly_restored.coeffs == [1.0, 2.0, 3.0], "Should restore coefficients"

    print("✓ Serialization tests passed\n")


def test_calibrator():
    """Test Calibrator class."""
    print("Testing Calibrator...")
    R = [2200, 1800, 1500, 1200]
    F = [5, 10, 20, 35]

    # Test initialization
    cal = Calibrator("exp")
    assert cal.model is None, "Model should be None before fitting"

    # Test fitting
    model = cal.fit(R, F)
    assert model is not None, "Model should be created after fitting"
    assert "rmse" in model.stats, "Should compute RMSE"
    assert "mae" in model.stats, "Should compute MAE"
    assert "r2" in model.stats, "Should compute R²"
    assert model.stats["n"] == 4, "Should record number of samples"

    # Test prediction
    pred = cal.predict(1600)
    assert pred > 0, "Prediction should be positive"

    print(f"  Model stats: {model.stats}")
    print(f"  Prediction at 1600Ω: {pred:.2f}")
    print("✓ Calibrator tests passed\n")


def test_save_load():
    """Test model persistence."""
    print("Testing save/load...")
    R = [2200, 1800, 1500, 1200]
    F = [5, 10, 20, 35]

    # Create and save model
    cal = Calibrator("exp")
    cal.fit(R, F)

    test_file = Path("test_model.json")
    cal.save(test_file)
    assert test_file.exists(), "Model file should be created"

    # Load model
    loaded_cal = Calibrator.load(test_file)
    assert loaded_cal.model is not None, "Loaded model should not be None"

    # Compare predictions
    pred1 = cal.predict(1600)
    pred2 = loaded_cal.predict(1600)
    assert abs(pred1 - pred2) < 1e-6, "Predictions should match"

    # Clean up
    test_file.unlink()

    print(f"  Original prediction: {pred1:.6f}")
    print(f"  Loaded prediction: {pred2:.6f}")
    print("✓ Save/load tests passed\n")


def test_registry():
    """Test algorithm registry."""
    print("Testing algorithm registry...")
    assert "exp" in ALGO_REGISTRY, "Registry should contain exp"
    assert "poly" in ALGO_REGISTRY, "Registry should contain poly"
    assert ALGO_REGISTRY["exp"] == ExpModel, "Should map to ExpModel"
    assert ALGO_REGISTRY["poly"] == PolyModel, "Should map to PolyModel"
    print("✓ Registry tests passed\n")


def test_error_handling():
    """Test error handling."""
    print("Testing error handling...")

    # Test prediction before fitting
    cal = Calibrator("exp")
    try:
        cal.predict(1000)
        assert False, "Should raise error when predicting before fitting"
    except ValueError as e:
        assert "fitted" in str(e).lower(), "Error message should mention fitting"

    # Test invalid algorithm
    try:
        Calibrator("invalid_algo")
        assert False, "Should raise error for invalid algorithm"
    except KeyError as e:
        assert "invalid_algo" in str(e), "Error should mention invalid algorithm"

    print("✓ Error handling tests passed\n")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Running Calibrator Module Tests")
    print("=" * 60 + "\n")

    test_statistics()
    test_exp_model()
    test_poly_model()
    test_serialization()
    test_calibrator()
    test_save_load()
    test_registry()
    test_error_handling()

    print("=" * 60)
    print("✓ All tests passed successfully!")
    print("=" * 60)


if __name__ == "__main__":
    main()
