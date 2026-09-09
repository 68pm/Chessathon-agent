"""Isolated repetition cost trial on exact selectedv1.56."""
import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from datetime import datetime,timezone
from pathlib import Path
from scripts import daytime_pawn_extrema as trial
from scripts.evening_common import ROOT,RUN,check_stop,digest,manifest,save
from scripts.evening_repetition_transform import transform

OUT=RUN/'repetition-01'
BASE=ROOT/'runs/daytime-20260909/move-buffers-01/prototype'

def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    import chess
    check_stop()
    assert not OUT.exists()
    selected=json.loads((ROOT.parent/'chessity-agent-version.json').read_text())
    assert selected['version']=='v1.56'
    assert digest(ROOT.parent/'chessity-agent.zip')==selected['sha256']
    archive_matches(ROOT.parent/'chessity-agent.zip',BASE)
    prior=ROOT/'runs/continuation-20260909/legal-buffers-01/preparation.json'
    roots=json.loads(prior.read_text())['roots'][:10]
    for cycles in (1,2):
        board=chess.Board()
        moves=['g1f3','g8f6','f3g1','f6g8']*cycles
        for move in moves:board.push_uci(move)
        roots.append(dict(id=f'legal-knight-cycle-{cycles}',start_fen=chess.STARTING_FEN,
                          history=moves,fen=board.fen()))
    assert len(roots)==12
    prototype=OUT/'prototype'
    shutil.copytree(BASE,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    source=transform((BASE/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(source,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/evening_repetition_core.py'
    assert not experiment.exists()
    experiment.write_text(source,encoding='utf-8',newline='\n')
    paths=[Path(__file__),Path(trial.__file__),ROOT/'scripts/evening_common.py',
        ROOT/'scripts/evening_repetition_transform.py',experiment,prior,
        ROOT/'tests/test_evening_repetition.py',ROOT/'docs/EVENING_REPETITION_PLAN_20260909.md',
        ROOT/'configs/evening-september9-gate-openings.json']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},roots=roots,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(fixed_nodes=250000,fixed_seconds_cap=12,clock_seconds=1,
            order=['baseline','prototype','prototype','baseline'],minimum_cpu_ratio=1.05),
        scope='Exact legal-history repetition query; no ordering/value/clock changes.'))
    print('Prepared frozen repetition trial',flush=True)

class Worker(trial.WarmWorker):
    def __init__(self,label):
        self.label=label
        self.log=(OUT/f'{label}.log').open('w',encoding='utf-8')
        self.answers=queue.Queue()
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m','scripts.evening_repetition',
            '--worker',label],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=self.log,
            text=True,encoding='utf-8',creationflags=subprocess.CREATE_NO_WINDOW)
        def read():
            for line in self.process.stdout:self.answers.put(line)
            self.answers.put(None)
        threading.Thread(target=read,daemon=True).start()

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    parser.add_argument('--worker',choices=('baseline','prototype'))
    args=parser.parse_args()
    if args.prepare:prepare()
    else:
        trial.OUT,trial.BASE,trial.WarmWorker,trial.check_stop=OUT,BASE,Worker,check_stop
        trial.worker(args.worker) if args.worker else trial.controller()
