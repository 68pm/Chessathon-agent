"""Frozen-weight additional Black-to-move check; never feeds back into this fit."""
import json
from pathlib import Path

import chess
import chess.pgn
import numpy as np

from scripts.continuation_common import ROOT,RUN,check_stop,digest,save
from scripts.continuation_gm_labels import active,CURRICULUM
from scripts.overnight_value_labels import duplicate,restore
from scripts.overnight_capacity import wait_for_capacity
from training.continuation_curriculum_value import classical,OUT as FIT
from training.residual_value import forward
from training.rule_value import arrays,features

OUT=RUN/'curriculum-black-check-01'


def run():
    check_stop()
    assert not OUT.exists()
    fit=json.loads((FIT/'state.json').read_text())
    assert fit['status']=='complete' and fit['passed']
    assert digest(FIT/'value.npz')==fit['model_sha256']
    prep=json.loads((FIT/'preparation.json').read_text())
    used={r['key'] for r in prep['rows']}
    curriculum=json.loads((CURRICULUM/'state.json').read_text())
    planned=[]
    for row in curriculum['games']:
        if row['split']!='reserved_test':continue
        path=CURRICULUM/row['pgn_file']
        assert digest(path)==row['sha256']
        with path.open(encoding='utf-8') as stream:game=chess.pgn.read_game(stream)
        assert game and not game.errors
        board=game.board()
        for ply,node in enumerate(game.mainline(),1):
            assert node.move in board.legal_moves
            board.push(node.move)
            if ply in (21,33,45,57,69,81):
                assert board.turn==chess.BLACK
                planned.append(dict(id=f'{row["game_hash"]}-{ply}',group=row['game_hash'],
                    start_fen=game.board().fen(),history=[m.uci() for m in board.move_stack],
                    fen=board.fen(),key=duplicate(board)))
    assert len(planned)<=18
    save(OUT/'preparation.json',dict(rows=planned,model_sha256=fit['model_sha256'],
        sources={str(p):digest(p) for p in (Path(__file__),FIT/'state.json',FIT/'preparation.json',
          ROOT/'docs/CONTINUATION_VALUE_RUNTIME_PLAN_20260909.md')},maximum_teacher_nodes=7200000))
    wait_for_capacity(OUT/'capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    fn=classical(ROOT/prep['candidate'])
    with np.load(FIT/'value.npz',allow_pickle=False) as data:
        p=[data['weights'],data['bias'],data['output']/200.]
    from training import game_feedback
    game_feedback.stop_check=check_stop
    teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',passed=False,rows=[],model_sha256=fit['model_sha256'])
    try:
        for row in planned:
            check_stop();board=restore(row);item=dict(row,eligible=False)
            if row['key'] not in used and active(board):
                labels=[teacher.analyse(board,n) for n in (80000,320000)]
                cp=[r['cp'] for r in labels]
                finite=all(v is not None for v in cp) and all(r['mate'] is None for r in labels)
                eligible=finite and max(map(abs,cp))<=1500 and abs(cp[0]-cp[1])<=100
                item.update(teacher=labels,eligible=eligible)
                if eligible:
                    truth=sum(cp)/2;base=float(fn(*arrays(board),False))
                    value=base+fit['value_blend']*float(np.clip(forward(features(board)[None,:768],p)[0][0]*200.,-500,500))
                    item.update(target_stm_cp=truth,before_cp=base,after_cp=value,
                        before_error_cp=abs(base-truth),after_error_cp=abs(value-truth))
                used.add(row['key'])
            state['rows'].append(item);save(OUT/'state.json',state)
        eligible=[r for r in state['rows'] if r['eligible']]
        before=float(np.mean([r['before_error_cp'] for r in eligible])) if eligible else None
        after=float(np.mean([r['after_error_cp'] for r in eligible])) if eligible else None
        major_before=sum(r['before_error_cp']>=200 for r in eligible)
        major_after=sum(r['after_error_cp']>=200 for r in eligible)
        state.update(status='complete',passed=bool(len(eligible)>=9 and after<=before and major_after<=major_before),
            eligible=len(eligible),before_mae_cp=before,after_mae_cp=after,
            major_before=major_before,major_after=major_after)
    except BaseException as error:
        state.update(status='failed',passed=False,error=repr(error));raise
    finally:
        teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        assert teacher.requested_nodes<=7200000
        assert digest(FIT/'value.npz')==fit['model_sha256']
        save(OUT/'state.json',state)
    print(json.dumps({k:v for k,v in state.items() if k!='rows'}),flush=True)


if __name__=='__main__':run()
