"""Stop and provenance helpers for the authorised 9 September daytime run."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RUN = ROOT / 'runs/daytime-20260909'
BASE = ROOT / 'candidates/compiled-reductions-v1'
DEADLINE = datetime(2026, 9, 9, 14, 40, tzinfo=timezone.utc)


def check_stop():
    if any(p.exists() for p in (ROOT / 'STOP_TRAINING', ROOT / 'STOP_BENCHMARK', RUN / 'STOP')):
        raise InterruptedError('User stop flag')
    if datetime.now(timezone.utc) >= DEADLINE:
        raise InterruptedError('Daytime heavy-work deadline reached')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def manifest(path):
    return {p.relative_to(path).as_posix(): digest(p) for p in sorted(path.rglob('*'))
            if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}


def save(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')
