"""Scheduling utilities for short/long range rollouts."""
from __future__ import annotations

from dataclasses import dataclass
from typing import List


@dataclass(frozen=True)
class Schedule:
    steps: List[int]
    total_hours: int
    mode: str


def _decompose_hours(total: int, steps: List[int]) -> List[int]:
    if total < 0:
        raise ValueError("total must be >= 0")
    steps = sorted([s for s in steps if s > 0], reverse=True)
    out: List[int] = []
    remaining = total
    for s in steps:
        while remaining >= s:
            out.append(s)
            remaining -= s
    if remaining != 0:
        raise ValueError(f"cannot decompose {total} with steps {steps}")
    return out


def build_schedule(
    target_hours: int,
    short_until: int = 84,
    short_step: int = 1,
    long_step: int = 24,
    mode: str = "full",
    available_steps: List[int] | None = None,
    strategy: str = "default",
) -> Schedule:
    if target_hours <= 0:
        raise ValueError("target_hours must be > 0")
    if short_step <= 0 or long_step <= 0:
        raise ValueError("step size must be > 0")
    if mode not in {"short", "long", "full"}:
        raise ValueError("mode must be one of: short|long|full")

    steps: List[int] = []
    avail = available_steps or [24, 6, 3, 1]
    if strategy not in {"default", "pangu_ref", "kong2er_ref"}:
        raise ValueError("strategy must be one of: default|pangu_ref|kong2er_ref")
    # Keep backward compatibility: kong2er_ref equals pangu_ref schedule policy.
    if strategy == "kong2er_ref":
        strategy = "pangu_ref"
    if mode in {"short", "full"}:
        short_target = min(target_hours, short_until)
        if short_step in avail:
            steps.extend([short_step] * (short_target // short_step))
            remainder = short_target % short_step
            if remainder:
                steps.extend(_decompose_hours(remainder, avail))
        else:
            steps.extend(_decompose_hours(short_target, avail))

    if mode in {"long", "full"} and target_hours > short_until:
        start = short_until if mode == "full" else 0
        remaining = target_hours - start
        steps.extend([long_step] * (remaining // long_step))
        rem = remaining % long_step
        if rem:
            steps.extend(_decompose_hours(rem, avail))

    if strategy == "pangu_ref":
        # Enforce: 1h only up to 84h; after 84h, use 24/6/3 only.
        steps = []
        if mode == "short":
            steps.extend(_decompose_hours(min(target_hours, short_until), [24, 6, 3, 1]))
        elif mode == "long":
            steps.extend(_decompose_hours(target_hours, [24, 6, 3]))
        else:
            steps.extend(_decompose_hours(min(target_hours, short_until), [24, 6, 3, 1]))
            if target_hours > short_until:
                steps.extend(_decompose_hours(target_hours - short_until, [24, 6, 3]))

    total = sum(steps)
    if total != target_hours:
        raise ValueError(f"schedule total {total} != target_hours {target_hours}")

    return Schedule(steps=steps, total_hours=target_hours, mode=mode)
