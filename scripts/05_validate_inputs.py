import numpy as np

surface = np.load("/root/autodl-tmp/pangu-weather-repro/processed/surface.npy")
pressure = np.load("/root/autodl-tmp/pangu-weather-repro/processed/pressure.npy")

assert surface.shape == (4, 1, 721, 1440)
assert pressure.shape == (5, 1, 13, 721, 1440)

print("✅ Input validation passed")
print("surface:", surface.shape)
print("pressure:", pressure.shape)
