from pangu_weather_repro.app.plot_filters import parse_product_name


def test_parse_fill_name():
    assert parse_product_name("product_z500_t+024.png") == ("fill", "z500", "024")


def test_parse_diff_name():
    assert parse_product_name("product_diff_z500_t+030.png") == ("diff", "z500", "030")


def test_parse_vector_name():
    assert parse_product_name("product_vector_uv10_t+024.png") == ("vector", "uv10", "024")


def test_parse_msl_wind_name():
    assert parse_product_name("product_msl_wind_t+030.png") == ("msl_wind", "msl_wind", "030")


def test_parse_wind_speed_name():
    assert parse_product_name("product_wind_speed_t+024.png") == ("wind_speed", "wind_speed", "024")


def test_parse_invalid_name():
    assert parse_product_name("other_plot.png") == ("other", "other", "other")
