"""Region data adapter interface."""
from .adapter import GlobalGridCropAdapter, PaddedRegionAdapter, RegionDatasetAdapter

__all__ = ["RegionDatasetAdapter", "GlobalGridCropAdapter", "PaddedRegionAdapter"]
