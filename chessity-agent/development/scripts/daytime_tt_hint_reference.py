"""Load the frozen parent through its real agent package in an isolated process."""
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, manifest, save


def run():
    check_stop()
    out=RUN/'tt-hint-02'
    path=out/'reference.json'
    assert not path.exists()
    prep=json.loads((out/'preparation.json').read_text())
    candidate=ROOT/prep['candidates']['baseline']
    assert manifest(candidate)==prep['candidate_files']['baseline']
    for name in list(sys.modules):
        if name=='engine' or name.startswith('engine.'):
            del sys.modules[name]
    sys.path.insert(0,str(candidate))
    tick=time.perf_counter()
    import chess

    import agent
    from scripts.daytime_tt_hint_test_call import call

    core=sys.modules['engine.compiled_core']
    assert Path(core.__file__).resolve()==candidate/'engine/compiled_core.py'
    init=time.perf_counter()-tick
    assert init<90 and agent._search.blend==0
    scores={}
    for fen in [chess.STARTING_FEN,
        '4k3/pp3ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/4K3 w - - 0 15',
        '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
        'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1']:
        check_stop()
        score,control,_=call(core,chess.Board(fen),seed=False,maximum=1000000)
        assert control[1]==0
        scores[fen]=dict(score=int(score),nodes=int(control[0]),interrupted=int(control[1]))
    unchanged=manifest(candidate)==prep['candidate_files']['baseline']
    save(path,dict(status='complete' if unchanged else 'failed',scores=scores,
        candidate_files=prep['candidate_files']['baseline'],frozen_candidate=unchanged,
        init_seconds=init,finished_utc=datetime.now(timezone.utc).isoformat()))
    assert unchanged
    print('Isolated parent reference complete',flush=True)


if __name__=='__main__':
    run()
