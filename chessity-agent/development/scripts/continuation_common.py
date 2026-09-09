"""Bounds for the user-authorised continuation after the 9 September deadline."""
from datetime import datetime, timezone
from scripts.daytime_common import ROOT, digest, manifest, save

RUN = ROOT / 'runs/continuation-20260909'
DEADLINE = datetime(2026, 9, 9, 16, 45, tzinfo=timezone.utc)


def check_stop():
    if any(p.exists() for p in (ROOT/'STOP_TRAINING', ROOT/'STOP_BENCHMARK', RUN/'STOP')):
        raise InterruptedError('User stop flag')
    if datetime.now(timezone.utc) >= DEADLINE:
        raise InterruptedError('Bounded continuation deadline reached')
