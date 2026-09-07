"""Wait for disk and memory headroom after a recorded ENOSPC interruption."""
import argparse
import json
import shutil
import time
from pathlib import Path

from scripts.alien_rating_ladder import save_json
from scripts.overnight_resources import memory
from training.fastchess_data import ROOT


def wait_for_capacity(out, minimum_disk_mb=2048, minimum_memory_mb=768, wait_seconds=1200):
    out.parent.mkdir(parents=True, exist_ok=True)
    started = time.monotonic()
    while True:
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')
        sample = memory()
        free_mb = round(shutil.disk_usage(ROOT).free / 2**20, 1)
        elapsed = time.monotonic() - started
        ready = free_mb >= minimum_disk_mb and sample['available_mb'] >= minimum_memory_mb
        report = dict(status='ready' if ready else 'waiting_for_capacity',
            elapsed_seconds=round(elapsed, 1), disk_free_mb=free_mb,
            minimum_disk_mb=minimum_disk_mb, minimum_memory_mb=minimum_memory_mb,
            sample=sample)
        save_json(out, report)
        if ready:
            return report
        if elapsed >= wait_seconds:
            raise RuntimeError('Insufficient disk or memory headroom; no engine work launched.')
        time.sleep(min(15, wait_seconds - elapsed))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--minimum-disk-mb', type=int, default=2048)
    parser.add_argument('--minimum-memory-mb', type=int, default=768)
    parser.add_argument('--wait-seconds', type=int, default=1200)
    args = parser.parse_args()
    print(json.dumps(wait_for_capacity(args.out, args.minimum_disk_mb,
        args.minimum_memory_mb, args.wait_seconds)), flush=True)
