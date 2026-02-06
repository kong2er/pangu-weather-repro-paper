import numpy as np
import pytest

from pangu_weather_repro.contracts import (
    LAT_SIZE,
    LON_SIZE,
    PRESSURE_LEVELS,
    SURFACE_VARS,
    UPPER_VARS,
    ContractError,
    normalize_surface,
    normalize_upper,
    validate_surface,
    validate_upper,
)


def test_validate_surface_accepts_time_dim():
    arr = np.zeros((len(SURFACE_VARS), 1, LAT_SIZE, LON_SIZE), dtype=np.float32)
    validate_surface(arr, allow_time_dim=True)
    norm = normalize_surface(arr)
    assert norm.shape == (len(SURFACE_VARS), LAT_SIZE, LON_SIZE)


def test_validate_upper_accepts_time_dim():
    arr = np.zeros(
        (len(UPPER_VARS), 1, len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE), dtype=np.float32
    )
    validate_upper(arr, allow_time_dim=True)
    norm = normalize_upper(arr)
    assert norm.shape == (len(UPPER_VARS), len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE)


def test_surface_rank_error():
    arr = np.zeros((len(SURFACE_VARS), LAT_SIZE, LON_SIZE, 1), dtype=np.float32)
    with pytest.raises(ContractError):
        validate_surface(arr, allow_time_dim=True)


def test_upper_shape_error():
    arr = np.zeros((len(UPPER_VARS), len(PRESSURE_LEVELS), 720, LON_SIZE), dtype=np.float32)
    with pytest.raises(ContractError):
        validate_upper(arr, allow_time_dim=False)
