"""Bounded deeper verification of the unresolved Petroff collapse; no automatic fit."""
import json
from pathlib import Path

import chess

from scripts.continuation_common import ROOT,RUN,check_stop,digest,save
from scripts.overnight_value_labels import restore
from scripts.overnight_capacity import wait_for_capacity
from training import game_feedback

OUT=RUN/'petroff-turning-point-01'


def run():
    check_stop();assert not OUT.exists()
    assert json.loads((RUN/'curriculum-value-03/state.json').read_text())['passed'] is False
    records=RUN/'field-review-01/own-games.json'
    game=next(r for r in json.loads(records.read_text())['games'] if r['id']==83)
    _,identity=game_feedback.normalise_game(game)
    source=RUN/'field-review-01/own-review/games'/identity['game_key']/'review.json'
    review=json.loads(source.read_text());assert review['status']=='complete'
    roots=[r for r in review['rows'] if r['fullmove'] in (21,22,23) and not r['white']]
    assert len(roots)==3
    save(OUT/'preparation.json',dict(roots=roots,source_sha256={str(p):digest(p) for p in (Path(__file__),records,source)},
        budgets=[640000,2560000],maximum_teacher_nodes=19200000,
        reason='Root23 shallow values were uncertain and the actual continuation fell from roughly-1.6 to-5 pawns by move24.',
        scope='Deeper root move verification only. No leaf score copying, no automatic fit and no rating evidence.'))
    wait_for_capacity(OUT/'capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop
    teacher=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',rows=[],automatic_training=False)
    try:
        for root in roots:
            check_stop();board=restore(root);labels=[]
            for budget in (640000,2560000):
                best=teacher.analyse(board,budget)
                played=best if best['pv'][0]==root['played'] else teacher.analyse(board,budget,chess.Move.from_uci(root['played']))
                labels.append(dict(nodes=budget,best=best,played=played))
            grade=game_feedback.grade(labels,root['played'],board.legal_moves.count())
            item=dict(fullmove=root['fullmove'],san=root['san'],fen=root['fen'],start_fen=root['start_fen'],
                history=root['history'],initial_labels=root['labels'],labels=labels,grade=grade,
                best_line=board.variation_san([chess.Move.from_uci(m) for m in labels[-1]['best']['pv'][:10]]),
                played_line=board.variation_san([chess.Move.from_uci(m) for m in labels[-1]['played']['pv'][:10]]))
            state['rows'].append(item);save(OUT/'state.json',state)
        state['status']='complete'
    except BaseException as error:
        state.update(status='failed',error=repr(error));raise
    finally:
        teacher.close();state['requested_teacher_nodes']=teacher.requested_nodes
        assert teacher.requested_nodes<=19200000;save(OUT/'state.json',state)
    for row in state['rows']:
        print(json.dumps({k:v for k,v in row.items() if k not in ('initial_labels','history','start_fen','fen','labels')},ensure_ascii=False),flush=True)
        print(json.dumps(dict(fullmove=row['fullmove'],scores=[(r['best']['cp'],r['played']['cp']) for r in row['labels']])),flush=True)


if __name__=='__main__':run()
