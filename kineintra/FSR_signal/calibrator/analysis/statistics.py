"""Statistical metrics for model evaluation."""

from typing import Union

import numpy as np
import numpy.typing as npt


def rmse(
    y_true: Union[npt.ArrayLike, list[float]],
    y_pred: Union[npt.ArrayLike, list[float]],
) -> float:
    """Calculate Root Mean Squared Error (RMSE).
    
    Args:
        y_true: True values.
        y_pred: Predicted values.
        
    Returns:
        RMSE value.
    """
    y_true_arr = np.array(y_true, dtype=np.float64)
    y_pred_arr = np.array(y_pred, dtype=np.float64)
    return float(np.sqrt(np.mean((y_true_arr - y_pred_arr) ** 2)))


def mae(
    y_true: Union[npt.ArrayLike, list[float]],
    y_pred: Union[npt.ArrayLike, list[float]],
) -> float:
    """Calculate Mean Absolute Error (MAE).
    
    Args:
        y_true: True values.
        y_pred: Predicted values.
        
    Returns:
        MAE value.
    """
    y_true_arr = np.array(y_true, dtype=np.float64)
    y_pred_arr = np.array(y_pred, dtype=np.float64)
    return float(np.mean(np.abs(y_true_arr - y_pred_arr)))


def r2(
    y_true: Union[npt.ArrayLike, list[float]],
    y_pred: Union[npt.ArrayLike, list[float]],
) -> float:
    """Calculate R² (coefficient of determination).
    
    Args:
        y_true: True values.
        y_pred: Predicted values.
        
    Returns:
        R² value.
    """
    y_true_arr = np.array(y_true, dtype=np.float64)
    y_pred_arr = np.array(y_pred, dtype=np.float64)
    
    ss_res = np.sum((y_true_arr - y_pred_arr) ** 2)
    ss_tot = np.sum((y_true_arr - y_true_arr.mean()) ** 2)
    
    return float(1 - ss_res / ss_tot)
