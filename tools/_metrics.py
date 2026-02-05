#!/usr/bin/env python3
import numpy as np
import netCDF4 as nc


def load_latitude(path: str) -> np.ndarray:
    ds = nc.Dataset(path)
    try:
        if "latitude" in ds.variables:
            lat = ds["latitude"][:]
        elif "lat" in ds.variables:
            lat = ds["lat"][:]
        else:
            raise ValueError("latitude variable not found")
        return np.asarray(lat).astype(np.float64)
    finally:
        ds.close()


def lat_weights(lat: np.ndarray) -> np.ndarray:
    return np.cos(np.deg2rad(lat))


def _broadcast_weights(w: np.ndarray, shape: tuple) -> np.ndarray:
    if len(shape) == 2:
        return w.reshape((-1, 1))
    if len(shape) == 3:
        return w.reshape((1, -1, 1))
    raise ValueError(f"unsupported shape for weights: {shape}")


def rmse(pred: np.ndarray, gt: np.ndarray) -> float:
    diff = pred.astype(np.float64) - gt.astype(np.float64)
    return float(np.sqrt(np.nanmean(diff * diff)))


def rmse_latw(pred: np.ndarray, gt: np.ndarray, lat: np.ndarray) -> float:
    if pred.shape != gt.shape:
        raise ValueError(f"shape mismatch pred={pred.shape} gt={gt.shape}")
    w = lat_weights(lat)
    w2 = _broadcast_weights(w, pred.shape)
    diff2 = (pred.astype(np.float64) - gt.astype(np.float64)) ** 2
    mask = np.isfinite(diff2)
    ww = np.where(mask, w2, 0.0)
    num = np.sum(ww * diff2)
    den = np.sum(ww)
    if den == 0:
        raise ValueError("no valid points for weighted RMSE")
    return float(np.sqrt(num / den))


def acc_simple(pred: np.ndarray, gt: np.ndarray, lat: np.ndarray | None = None) -> float:
    if pred.shape != gt.shape:
        raise ValueError(f"shape mismatch pred={pred.shape} gt={gt.shape}")
    if gt.ndim == 3:
        clim = np.nanmean(gt, axis=0)
    else:
        clim = np.nanmean(gt)
    pred_anom = pred - clim
    gt_anom = gt - clim

    if lat is None:
        x = pred_anom.ravel().astype(np.float64)
        y = gt_anom.ravel().astype(np.float64)
        mask = np.isfinite(x) & np.isfinite(y)
        x = x[mask]
        y = y[mask]
        if x.size == 0:
            raise ValueError("no valid points for ACC")
        x = x - x.mean()
        y = y - y.mean()
        denom = np.sqrt((x * x).mean() * (y * y).mean())
        return float((x * y).mean() / denom) if denom != 0 else float("nan")

    w = lat_weights(lat)
    w2 = _broadcast_weights(w, pred.shape).astype(np.float64)
    x = pred_anom.astype(np.float64)
    y = gt_anom.astype(np.float64)
    mask = np.isfinite(x) & np.isfinite(y)
    ww = np.where(mask, w2, 0.0)
    wsum = np.sum(ww)
    if wsum == 0:
        raise ValueError("no valid points for weighted ACC")
    x_mean = np.sum(ww * x) / wsum
    y_mean = np.sum(ww * y) / wsum
    x0 = x - x_mean
    y0 = y - y_mean
    cov = np.sum(ww * x0 * y0) / wsum
    varx = np.sum(ww * x0 * x0) / wsum
    vary = np.sum(ww * y0 * y0) / wsum
    denom = np.sqrt(varx * vary)
    return float(cov / denom) if denom != 0 else float("nan")
