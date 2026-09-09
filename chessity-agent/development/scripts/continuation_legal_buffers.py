"""Full legal-existence buffer reuse on exact v1.56; frozen warmed ABBA harness."""
import argparse
import json
import queue
import shutil
import subprocess
import sys
import threading
from datetime import datetime, timezone
from pathlib import Path

from scripts import daytime_pawn_extrema as trial
from scripts.continuation_common import ROOT, RUN, check_stop, digest, manifest, save
from scripts.continuation_legal_buffers_transform import transform

OUT=RUN/'legal-buffers-01'
BASE=ROOT/'runs/daytime-20260909/move-buffers-01/prototype'


def prepare():
    from scripts.overnight_archive_challenge import archive_matches
    check_stop()
    assert not OUT.exists()
    selected=json.loads((ROOT.parent/'chessity-agent-version.json').read_text())
    assert selected['version']=='v1.56'
    assert digest(ROOT.parent/'chessity-agent.zip')==selected['sha256']
    archive_matches(ROOT.parent/'chessity-agent.zip',BASE)
    supervisor=RUN/'field-review-supervisor-01/supervisor.json'
    assert json.loads(supervisor.read_text())['status']=='complete'
    prototype=OUT/'prototype'
    shutil.copytree(BASE,prototype,ignore=shutil.ignore_patterns('__pycache__','*.pyc'))
    source=transform((BASE/'engine/compiled_core.py').read_text())
    (prototype/'engine/compiled_core.py').write_text(source,encoding='utf-8',newline='\n')
    experiment=ROOT/'experiments/continuation_legal_buffers_core.py'
    assert not experiment.exists()
    experiment.write_text(source,encoding='utf-8',newline='\n')
    import chess.pgn,io
    sources=[RUN/'field-review-01'/f'{label}-games.json' for label in ('own','leader')]
    roots=[]
    for path in sources:
        for record in json.loads(path.read_text())['games']:
            game=chess.pgn.read_game(io.StringIO(record['pgn']))
            roots.append(dict(id=path.stem+'-'+str(record['id']),start_fen=game.board().fen(),
                              history=[],fen=game.board().fen()))
    assert len(roots)==6
    prior=ROOT/'runs/daytime-20260909/move-buffers-01/preparation.json'
    roots+=json.loads(prior.read_text())['roots'][:6]
    assert len(roots)==12 and len({r['fen'] for r in roots})==12
    paths=[Path(__file__),Path(trial.__file__),ROOT/'scripts/continuation_common.py',
        ROOT/'scripts/continuation_legal_buffers_transform.py',experiment,supervisor,prior,*sources,
        ROOT/'tests/test_continuation_legal_buffers.py',ROOT/'docs/CONTINUATION_LEGAL_BUFFERS_PLAN_20260909.md']
    save(OUT/'preparation.json',dict(created_utc=datetime.now(timezone.utc).isoformat(),
        candidates={'baseline':str(BASE.relative_to(ROOT)),'prototype':str(prototype.relative_to(ROOT))},
        candidate_files={'baseline':manifest(BASE),'prototype':manifest(prototype)},roots=roots,
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in paths},
        protocol=dict(fixed_nodes=250000,fixed_seconds_cap=12,clock_seconds=1,
            order=['baseline','prototype','prototype','baseline'],minimum_cpu_ratio=1.05),
        scope='Exact existing generator in per-ply legal-existence storage; no move/value/order changes.'))
    print('Prepared exact v1.56 legal-existence buffer trial',flush=True)


class Worker(trial.WarmWorker):
    def __init__(self,label):
        self.label=label
        self.log=(OUT/f'{label}.log').open('w',encoding='utf-8')
        self.answers=queue.Queue()
        self.process=subprocess.Popen([sys.executable,'-X','utf8','-m','scripts.continuation_legal_buffers',
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
