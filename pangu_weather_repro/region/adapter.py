"""Region adapter interface and a global grid crop implementation."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Tuple

import numpy as np


class RegionDatasetAdapter(ABC):
    """Abstract adapter that converts region data into model inputs."""

    @abstractmethod
    def to_model_inputs(self) -> Tuple[np.ndarray, np.ndarray]:
        """Return (pressure, surface) arrays compatible with the model."""
        raise NotImplementedError

    @abstractmethod
    def metadata(self) -> dict:
        """Return adapter metadata for provenance and audit."""
        raise NotImplementedError


@dataclass
class GlobalGridCropAdapter(RegionDatasetAdapter):
    """Crop global ERA5-style arrays to a region bbox.

    Assumes latitude grid: 90 -> -90 (721)
    Assumes longitude grid: 0 -> 360 (1440)
    """

    pressure: np.ndarray
    surface: np.ndarray
    lat_min: float
    lat_max: float
    lon_min: float
    lon_max: float

    def _grid(self) -> Tuple[np.ndarray, np.ndarray]:
        lat = np.linspace(90.0, -90.0, self.surface.shape[-2])
        lon = np.linspace(0.0, 360.0, self.surface.shape[-1], endpoint=False)
        return lat, lon

    def _slice_indices(self) -> Tuple[slice, slice]:
        lat, lon = self._grid()
        lat_lo, lat_hi = sorted([self.lat_min, self.lat_max])
        lon_lo, lon_hi = sorted([self.lon_min, self.lon_max])
        lat_mask = (lat >= lat_lo) & (lat <= lat_hi)
        lon_mask = (lon >= lon_lo) & (lon <= lon_hi)
        if not lat_mask.any() or not lon_mask.any():
            raise ValueError("bbox does not overlap grid")
        lat_idx = np.where(lat_mask)[0]
        lon_idx = np.where(lon_mask)[0]
        return slice(lat_idx.min(), lat_idx.max() + 1), slice(lon_idx.min(), lon_idx.max() + 1)

    def to_model_inputs(self) -> Tuple[np.ndarray, np.ndarray]:
        lat_slice, lon_slice = self._slice_indices()
        pressure = self.pressure[..., lat_slice, lon_slice]
        surface = self.surface[..., lat_slice, lon_slice]
        return pressure, surface

    def metadata(self) -> dict:
        lat_slice, lon_slice = self._slice_indices()
        return {
            "type": "GlobalGridCropAdapter",
            "lat_min": self.lat_min,
            "lat_max": self.lat_max,
            "lon_min": self.lon_min,
            "lon_max": self.lon_max,
            "lat_slice": [lat_slice.start, lat_slice.stop],
            "lon_slice": [lon_slice.start, lon_slice.stop],
        }


@dataclass
class PaddedRegionAdapter(RegionDatasetAdapter):
    """Pad a region back to a full global grid with a fill value.

    This is a utility adapter for plugging region data into full-grid models.
    Note: fill_value should be chosen carefully for your application.
    """

    region_pressure: np.ndarray
    region_surface: np.ndarray
    global_shape_pressure: Tuple[int, int, int, int]
    global_shape_surface: Tuple[int, int, int]
    lat_slice: slice
    lon_slice: slice
    fill_value: float = 0.0

    def to_model_inputs(self) -> Tuple[np.ndarray, np.ndarray]:
        pressure = np.full(self.global_shape_pressure, self.fill_value, dtype=np.float32)
        surface = np.full(self.global_shape_surface, self.fill_value, dtype=np.float32)
        pressure[..., self.lat_slice, self.lon_slice] = self.region_pressure
        surface[..., self.lat_slice, self.lon_slice] = self.region_surface
        return pressure, surface

    def metadata(self) -> dict:
        return {
            "type": "PaddedRegionAdapter",
            "fill_value": self.fill_value,
            "global_shape_pressure": list(self.global_shape_pressure),
            "global_shape_surface": list(self.global_shape_surface),
            "lat_slice": [self.lat_slice.start, self.lat_slice.stop],
            "lon_slice": [self.lon_slice.start, self.lon_slice.stop],
        }
