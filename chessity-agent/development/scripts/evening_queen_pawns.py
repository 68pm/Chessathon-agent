"""Isolated queen-pawns integration, reusing the frozen evening quality gate."""
import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from datetime import datetime,timezone
from pathlib import Path
from scripts import evening_pawn_threat as trial
from scripts.evening_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.evening_queen_pawns_transform import transform

OUT=RUN/'queen-pawns-01'
BASE=ROOT/'runs/daytime-20260909/move-buffers-01/prototype'

def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    check_stop();assert not OUT.exists()
    previous=RUN/'king-pressure-01'
    old=json.loads((previous/'state.json').read_text())
    assert old['status']=='complete' and not old['passed'] and old['frozen_candidates']
    assert not (RUN/'pawn-threat-screen-01').exists()
    archive_matches(ROOT.parent/'chessity-agent.zip',BASE)
    original=json.loads((previous/'preparation.json').read_text())
    prototype=OUT/'prototype'
    shutil.copytree(BASE,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    source=transform((BASE/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(source,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/evening_queen_pawns_core.py'
    assert not experiment.exists();experiment.write_text(source,encoding='utf-8',newline='\n')
    paths=[Path(__file__),Path(trial.__file__),ROOT/'scripts/daytime_pawn_extrema.py',
        ROOT/'scripts/evening_common.py',ROOT/'scripts/evening_queen_pawns_transform.py',experiment,
        ROOT/'tests/test_evening_queen_pawns.py',ROOT/'docs/EVENING_QUEEN_PAWNS_PLAN_20260909.md',
        ROOT/'configs/evening-september9-gate-openings.json',ROOT/'training/game_feedback.py',
        previous/'state.json',previous/'preparation.json']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        parent=str(BASE.relative_to(ROOT)),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},
        roots=original['roots'],protocol=original['protocol'],
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        scope='Coordinated queen-pawns only on exactv1.56; no rejected search changes.'))
    print('Prepared isolated queen-pawns integration',flush=True)

class Worker(trial.Worker):
    def __init__(self,label):
        self.label=label;self.log=(OUT/f'{label}.log').open('w',encoding='utf-8');self.answers=queue.Queue()
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m','scripts.evening_queen_pawns',
            '--worker',label],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
            text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in self.process.stdout:self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read,daemon=True).start()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true');parser.add_argument('--worker',choices=('baseline','prototype'))
    args=parser.parse_args()
    if args.prepare:prepare()
    elif args.worker:
        trial.trial.OUT,trial.trial.check_stop=OUT,check_stop
        trial.trial.worker(args.worker)
    else:
        trial.OUT,trial.Worker=OUT,Worker
        trial.controller()
