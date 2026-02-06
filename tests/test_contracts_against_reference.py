from pangu_weather_repro.contracts import (
    LAT_SIZE,
    LON_SIZE,
    LAT_RANGE,
    LON_RANGE,
    GRID_RESOLUTION_DEG,
    PRESSURE_LEVELS,
    SURFACE_VARS,
    UPPER_VARS,
)


def test_reference_contracts_constants():
    assert SURFACE_VARS == ("msl", "u10", "v10", "t2m")
    assert UPPER_VARS == ("z", "q", "t", "u", "v")
    assert PRESSURE_LEVELS == (
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
    assert (LAT_SIZE, LON_SIZE) == (721, 1440)
    assert LAT_RANGE == (90.0, -90.0)
    assert LON_RANGE == (0.0, 359.75)
    assert GRID_RESOLUTION_DEG == 0.25
