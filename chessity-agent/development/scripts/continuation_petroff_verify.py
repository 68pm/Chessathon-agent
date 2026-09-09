"""Resolve one horizon-sensitive public-game target with bounded deeper labels."""
import json
from pathlib import Path
import chess
from scripts.continuation_common import ROOT,RUN,check_stop,digest,save
from scripts.overnight_value_labels import restore
from scripts.overnight_capacity import wait_for_capacity
from training import game_feedback

OUT=RUN/'petroff-turning-point-02'

def run():
    check_stop();assert not OUT.exists()
    source=RUN/'petroff-turning-point-01/state.json';previous=json.loads(source.read_text())
    assert previous['status']=='complete'
    root=next(r for r in previous['rows'] if r['fullmove']==23)
    assert root['grade']['label']=='uncertain'
    board=restore(root);played=chess.Move.from_uci(root['labels'][-1]['played']['pv'][0])
    assert board.san(played)=='Re6'
    save(OUT/'preparation.json',dict(source_sha256={str(p):digest(p) for p in (source,Path(__file__))},
        root=root,budgets=[2560000,10240000],maximum_teacher_nodes=25600000,
        reason='640k and2.56M restricted Re6 searches differed by379cp; verify before any reward.',
        automatic_fitting=False,descendant_value_label=None))
    wait_for_capacity(OUT/'capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop
    teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',labels=[],automatic_fitting=False)
    try:
        for n in (2560000,10240000):
            check_stop();best=teacher.analyse(board,n)
            actual=best if best['pv'][0]==played.uci() else teacher.analyse(board,n,played)
            state['labels'].append(dict(nodes=n,best=best,played=actual));save(OUT/'state.json',state)
        state.update(status='complete',grade=game_feedback.grade(state['labels'],played.uci(),board.legal_moves.count()),
            best_line=board.variation_san([chess.Move.from_uci(m) for m in state['labels'][-1]['best']['pv'][:12]]),
            played_line=board.variation_san([chess.Move.from_uci(m) for m in state['labels'][-1]['played']['pv'][:12]]))
    except BaseException as error:
        state.update(status='failed',error=repr(error));raise
    finally:
        teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        assert teacher.requested_nodes<=25600000;save(OUT/'state.json',state)
    print(json.dumps(state),flush=True)

if __name__=='__main__':run()
