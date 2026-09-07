"""Bounded resource guard for local overnight jobs; never alters other apps."""
import argparse
import ctypes
import json
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json
from training.fastchess_data import ROOT


class MemoryStatus(ctypes.Structure):
    _fields_ = [('length',ctypes.c_ulong),('load',ctypes.c_ulong),
        ('total_physical',ctypes.c_ulonglong),('available_physical',ctypes.c_ulonglong),
        ('total_page',ctypes.c_ulonglong),('available_page',ctypes.c_ulonglong),
        ('total_virtual',ctypes.c_ulonglong),('available_virtual',ctypes.c_ulonglong),
        ('available_extended',ctypes.c_ulonglong)]


def memory():
    state = MemoryStatus()
    state.length = ctypes.sizeof(state)
    if not ctypes.windll.kernel32.GlobalMemoryStatusEx(ctypes.byref(state)):
        raise OSError('Cannot read host memory status')
    return dict(utc=datetime.now(timezone.utc).isoformat(), load_percent=state.load,
        available_mb=round(state.available_physical / 2**20, 1),
        total_mb=round(state.total_physical / 2**20, 1))


def wait_for_memory(out, minimum_mb=768, wait_seconds=1200):
    started = time.monotonic()
    while True:
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING','STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')
        sample = memory()
        elapsed = time.monotonic() - started
        ready = sample['available_mb'] >= minimum_mb
        save_json(out, dict(status='ready' if ready else 'waiting_for_memory',
            elapsed_seconds=round(elapsed,1), minimum_mb=minimum_mb, sample=sample))
        if ready:
            return sample
        if elapsed >= wait_seconds:
            raise RuntimeError('Host memory remained below the declared guard; preserve this interruption and do not launch games.')
        time.sleep(min(15, wait_seconds - elapsed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--minimum-mb', type=int, default=768)
    parser.add_argument('--wait-seconds', type=int, default=1200)
    args = parser.parse_args()
    print(json.dumps(wait_for_memory(args.out,args.minimum_mb,args.wait_seconds)), flush=True)
