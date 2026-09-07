"""Headless Task Scheduler entry point, without a persistent PowerShell wrapper."""
import argparse
import json
import os
import sys
import traceback
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json
from training.fastchess_data import ROOT


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--plan',type=Path,required=True)
    args = parser.parse_args()
    plan = json.loads(args.plan.read_text())
    out = ROOT / plan['output']
    out.mkdir(parents=True,exist_ok=True)
    save_json(out / 'service-start.json',dict(pid=os.getpid(),started_utc=datetime.now(timezone.utc).isoformat(),
        plan=str(args.plan),executable=sys.executable))
    with (out / 'service.stdout.log').open('a',encoding='utf-8',buffering=1) as stdout, (
            out / 'service.stderr.log').open('a',encoding='utf-8',buffering=1) as stderr:
        sys.stdout, sys.stderr = stdout,stderr
        from scripts.improvement_cycle_driver import main as run
        try:
            run()
        except BaseException:
            traceback.print_exc()
            raise


if __name__ == '__main__':
    main()
