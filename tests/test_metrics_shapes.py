import numpy as np

from tools._metrics import acc_simple, rmse, rmse_latw


def test_rmse_basic():
    pred = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    gt = np.array([[1.0, 1.0], [5.0, 3.0]], dtype=np.float32)
    val = rmse(pred, gt)
    assert abs(val - np.sqrt(((0**2) + (1**2) + (2**2) + (1**2)) / 4)) < 1e-6


def test_rmse_latw_and_acc():
    pred = np.array([[1.0, 2.0], [3.0, 4.0]], dtype=np.float32)
    gt = pred.copy()
    lat = np.array([0.0, 60.0], dtype=np.float64)
    assert rmse_latw(pred, gt, lat) == 0.0
    assert abs(acc_simple(pred, gt, lat) - 1.0) < 1e-6
