"""Fresh bounds for the user's9September request for evidence before promotion."""
from datetime import datetime,timezone
from scripts.daytime_common import ROOT,digest,manifest,save
RUN=ROOT/'runs/evening-20260909'
DEADLINE=datetime(2026,9,9,18,30,tzinfo=timezone.utc)

def check_stop():
    if any(p.exists() for p in (ROOT/'STOP_TRAINING',ROOT/'STOP_BENCHMARK',RUN/'STOP')):
        raise InterruptedError('User stop flag')
    if datetime.now(timezone.utc)>=DEADLINE:
        raise InterruptedError('Bounded evening task deadline reached')
