from pangu_weather_repro.infer.scheduler import build_schedule


def test_short_schedule_total():
    sched = build_schedule(target_hours=6, short_step=1, long_step=24, mode="short")
    assert sum(sched.steps) == 6


def test_full_schedule_total():
    sched = build_schedule(target_hours=90, short_step=1, long_step=24, mode="full")
    assert sum(sched.steps) == 90


def test_long_schedule_total():
    sched = build_schedule(target_hours=96, short_step=1, long_step=24, mode="long")
    assert sum(sched.steps) == 96


def test_no_unsupported_step():
    sched = build_schedule(target_hours=360, short_step=1, long_step=24, mode="full")
    assert 12 not in sched.steps


def test_pangu_ref_long_mode():
    sched = build_schedule(target_hours=276, short_step=1, long_step=24, mode="long", strategy="pangu_ref")
    assert all(s in (24, 6, 3) for s in sched.steps)
