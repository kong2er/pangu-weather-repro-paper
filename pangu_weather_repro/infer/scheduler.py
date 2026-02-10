"""Scheduling utilities for short/long range rollouts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Schedule:
    steps: List[int]
    total_hours: int
    mode: str


def build_schedule(
    target_hours: int,
    short_until: int = 84,
    short_step: int = 1,
    long_step: int = 24,
    mode: str = "full",
) -> Schedule:
    if target_hours <= 0:
        raise ValueError("target_hours must be > 0")
    if short_step <= 0 or long_step <= 0:
        raise ValueError("step size must be > 0")
    if mode not in {"short", "long", "full"}:
        raise ValueError("mode must be one of: short|long|full")

    steps: List[int] = []
    if mode in {"short", "full"}:
        short_target = min(target_hours, short_until)
        steps.extend([short_step] * (short_target // short_step))
        remainder = short_target % short_step
        if remainder:
            steps.append(remainder)

    if mode in {"long", "full"} and target_hours > short_until:
        start = short_until if mode == "full" else 0
        remaining = target_hours - start
        steps.extend([long_step] * (remaining // long_step))
        rem = remaining % long_step
        if rem:
            steps.append(rem)

    total = sum(steps)
    if total != target_hours:
        raise ValueError(f"schedule total {total} != target_hours {target_hours}")

    return Schedule(steps=steps, total_hours=target_hours, mode=mode)
