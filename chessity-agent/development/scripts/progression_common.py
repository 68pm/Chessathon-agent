"""Fresh bounds for continued improvement authorised after the evening report."""
from datetime import datetime, timezone
from scripts.daytime_common import ROOT, digest, manifest, save

RUN = ROOT / 'runs/progression-20260909'
BASE = ROOT / 'runs/daytime-20260909/move-buffers-01/prototype'
DEADLINE = datetime(2026, 9, 9, 21, 0, tzinfo=timezone.utc)


def check_stop():
    if any(p.exists() for p in (ROOT / 'STOP_TRAINING', ROOT / 'STOP_BENCHMARK', RUN / 'STOP')):
        raise InterruptedError('User stop flag')
    if datetime.now(timezone.utc) >= DEADLINE:
        raise InterruptedError('Bounded progression task deadline reached')
