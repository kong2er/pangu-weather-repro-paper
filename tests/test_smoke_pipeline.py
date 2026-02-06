import numpy as np

from pangu_weather_repro.contracts import (
    LAT_SIZE,
    LON_SIZE,
    PRESSURE_LEVELS,
    SURFACE_VARS,
    UPPER_VARS,
    InputSpec,
    build_feed_dict,
    validate_feed_against_onnx_inputs,
)


def test_smoke_pipeline_feed_contract():
    surface = np.zeros((len(SURFACE_VARS), 1, LAT_SIZE, LON_SIZE), dtype=np.float32)
    upper = np.zeros(
        (len(UPPER_VARS), 1, len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE), dtype=np.float32
    )

    feed = build_feed_dict(upper, surface)

    specs = [
        InputSpec(
            name="input",
            shape=(len(UPPER_VARS), len(PRESSURE_LEVELS), LAT_SIZE, LON_SIZE),
        ),
        InputSpec(name="input_surface", shape=(len(SURFACE_VARS), LAT_SIZE, LON_SIZE)),
    ]

    validate_feed_against_onnx_inputs(feed, specs)
