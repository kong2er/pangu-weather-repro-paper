from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, Mapping, Sequence

import numpy as np

# === Canonical contract (aligned with Pangu-Weather public repo README) ===
SURFACE_VARS = ("msl", "u10", "v10", "t2m")
UPPER_VARS = ("z", "q", "t", "u", "v")
PRESSURE_LEVELS = (
    1000,
    925,
    850,
    700,
    600,
    500,
    400,
    300,
    250,
    200,
    150,
    100,
    50,
)
LAT_SIZE = 721
LON_SIZE = 1440
DTYPE = np.float32
LAT_RANGE = (90.0, -90.0)
LON_RANGE = (0.0, 359.75)
GRID_RESOLUTION_DEG = 0.25

SURFACE_SHAPE = (len(SURFACE_VARS), LAT_SIZE, LON_SIZE)
UPPER_SHAPE = (len(UPPER_VARS), len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE)
SURFACE_SHAPE_WITH_TIME = (len(SURFACE_VARS), 1, LAT_SIZE, LON_SIZE)
UPPER_SHAPE_WITH_TIME = (len(UPPER_VARS), 1, len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE)

ONNX_UPPER_KEY = "input"
ONNX_SURFACE_KEY = "input_surface"


class ContractError(ValueError):
    """Raised when inputs violate the Pangu-Weather tensor contract."""


@dataclass(frozen=True)
class InputSpec:
    name: str
    shape: Sequence[int | None]


def _shape_str(shape: Sequence[int | None]) -> str:
    return "(" + ", ".join("?" if s is None else str(int(s)) for s in shape) + ")"


def _ensure_dtype(name: str, arr: np.ndarray) -> None:
    if arr.dtype != DTYPE:
        raise ContractError(
            f"{name}: dtype mismatch. expected={DTYPE}, got={arr.dtype}. "
            "Tip: cast to float32 before feeding the model."
        )


def validate_surface(arr: np.ndarray, *, allow_time_dim: bool = True, name: str = "surface") -> None:
    arr = np.asarray(arr)
    if allow_time_dim:
        if arr.ndim not in (3, 4):
            raise ContractError(
                f"{name}: rank mismatch. expected 3 or 4 dims (C,H,W or C,1,H,W), got {arr.ndim}."
            )
    else:
        if arr.ndim != 3:
            raise ContractError(
                f"{name}: rank mismatch. expected 3 dims (C,H,W), got {arr.ndim}."
            )

    if arr.ndim == 4:
        if arr.shape[1] != 1:
            raise ContractError(
                f"{name}: time dim must be singleton. expected shape {SURFACE_SHAPE_WITH_TIME}, got {arr.shape}."
            )
        expected = SURFACE_SHAPE_WITH_TIME
    else:
        expected = SURFACE_SHAPE

    if tuple(arr.shape) != expected:
        raise ContractError(
            f"{name}: shape mismatch. expected {expected}, got {arr.shape}. "
            "Tip: check variable order and grid size (721x1440)."
        )

    _ensure_dtype(name, arr)


def validate_upper(arr: np.ndarray, *, allow_time_dim: bool = True, name: str = "upper") -> None:
    arr = np.asarray(arr)
    if allow_time_dim:
        if arr.ndim not in (4, 5):
            raise ContractError(
                f"{name}: rank mismatch. expected 4 or 5 dims (C,L,H,W or C,1,L,H,W), got {arr.ndim}."
            )
    else:
        if arr.ndim != 4:
            raise ContractError(
                f"{name}: rank mismatch. expected 4 dims (C,L,H,W), got {arr.ndim}."
            )

    if arr.ndim == 5:
        if arr.shape[1] != 1:
            raise ContractError(
                f"{name}: time dim must be singleton. expected shape {UPPER_SHAPE_WITH_TIME}, got {arr.shape}."
            )
        expected = UPPER_SHAPE_WITH_TIME
    else:
        expected = UPPER_SHAPE

    if tuple(arr.shape) != expected:
        raise ContractError(
            f"{name}: shape mismatch. expected {expected}, got {arr.shape}. "
            "Tip: check variable order, pressure levels (13), and grid size (721x1440)."
        )

    _ensure_dtype(name, arr)


def normalize_surface(arr: np.ndarray) -> np.ndarray:
    """Normalize surface input to (C,H,W) float32."""
    arr = np.asarray(arr, dtype=DTYPE)
    validate_surface(arr, allow_time_dim=True, name="surface")
    if arr.ndim == 4:
        return arr[:, 0]
    return arr


def normalize_upper(arr: np.ndarray) -> np.ndarray:
    """Normalize upper-air input to (C,L,H,W) float32."""
    arr = np.asarray(arr, dtype=DTYPE)
    validate_upper(arr, allow_time_dim=True, name="upper")
    if arr.ndim == 5:
        return arr[:, 0]
    return arr


def build_feed_dict(
    upper: np.ndarray,
    surface: np.ndarray,
    *,
    upper_key: str = ONNX_UPPER_KEY,
    surface_key: str = ONNX_SURFACE_KEY,
) -> dict[str, np.ndarray]:
    upper_n = normalize_upper(upper)
    surface_n = normalize_surface(surface)
    validate_upper(upper_n, allow_time_dim=False, name="upper")
    validate_surface(surface_n, allow_time_dim=False, name="surface")
    return {upper_key: upper_n, surface_key: surface_n}


def _shape_matches(actual: Sequence[int], expected: Sequence[int | None]) -> bool:
    if len(actual) != len(expected):
        return False
    for a, e in zip(actual, expected):
        if e is None:
            continue
        if int(a) != int(e):
            return False
    return True


def validate_feed_against_onnx_inputs(
    feed: Mapping[str, np.ndarray],
    input_specs: Iterable[InputSpec],
) -> None:
    specs = list(input_specs)
    expected_names = {s.name for s in specs}
    missing = [n for n in expected_names if n not in feed]
    extra = [n for n in feed.keys() if n not in expected_names]
    if missing or extra:
        raise ContractError(
            "feed dict keys mismatch. "
            f"missing={missing or None}, extra={extra or None}. "
            "Tip: verify ONNX input names (e.g., input, input_surface)."
        )

    for spec in specs:
        arr = np.asarray(feed[spec.name])
        if not _shape_matches(arr.shape, spec.shape):
            raise ContractError(
                f"feed[{spec.name}]: shape mismatch. expected {_shape_str(spec.shape)}, got {arr.shape}."
            )
        _ensure_dtype(f"feed[{spec.name}]", arr)
