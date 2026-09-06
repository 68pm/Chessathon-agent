"""Wall-clock allocation. No reliance on an increment arriving before we move."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Budget:
    soft: float
    hard: float


def allocate(time_left_ms: int, fullmove: int, moves: int, *, adaptive=False, in_check=False) -> Budget:
    remaining = max(0.0, time_left_ms / 1000.0)
    reserve = min(0.15, max(0.030 if adaptive else 0.015, remaining * 0.04))
    available = max(0.0, remaining - reserve)
    expected = max(20, 44 - fullmove // 3)
    complexity = min(1.25, max(0.70, moves / 30))
    # A fraction of the nominal 0.5s increment, capped by money already on the clock.
    soft = min(available * 0.30, (remaining / expected + 0.20) * complexity)
    if adaptive and in_check:
        soft = min(available * 0.30, soft * 1.2)
    hard = min(available, max(soft, soft * 1.7))
    return Budget(soft, hard)
