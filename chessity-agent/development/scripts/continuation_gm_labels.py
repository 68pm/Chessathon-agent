"""History-preserving, independently labelled master-game position curriculum."""
import argparse
import json
from pathlib import Path

import chess
import chess.pgn

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save
from scripts.overnight_value_labels import duplicate, restore

OUT = RUN/'gm-values-01'
CURRICULUM = RUN/'opening-curriculum-03'


def active(board):
    return (board.is_valid() and not board.is_check() and board.halfmove_clock < 70
            and not board.is_repetition(2) and not board.is_game_over(claim_draw=True))


def prepare():
    check_stop()
    assert not OUT.exists(), 'Preserve consumed preparations.'
    source = CURRICULUM/'state.json'
    curriculum = json.loads(source.read_text())
    assert curriculum['status'] == 'complete_unlabelled'
    planned, protected, sources = [], set(), {str(source): digest(source)}
    for row in curriculum['games']:
        path = CURRICULUM/row['pgn_file']
        assert digest(path) == row['sha256']
        sources[str(path)] = digest(path)
        with path.open(encoding='utf-8') as stream:
            game = chess.pgn.read_game(stream)
        assert game is not None and not game.errors
        board = game.board()
        reserved = row['split'] == 'reserved_test'
        plies = (20,26,32,38,44,50,56,62,68,74,80,86) if reserved else (20,28,36,44,60,80)
        if reserved: protected.add(duplicate(board))
        for ply, node in enumerate(game.mainline(), 1):
            assert node.move in board.legal_moves
            board.push(node.move)
            if reserved: protected.add(duplicate(board))
            if ply in plies:
                planned.append(dict(id=f'{row["game_hash"]}-{ply}', group=row['game_hash'],
                    family=row['family'], split=row['split'], start_fen=game.board().fen(),
                    history=[m.uci() for m in board.move_stack], fen=board.fen(),
                    key=duplicate(board), previously_available=row['previously_available']))
    assert len(planned) <= 120
    sources.update({str(p): digest(p) for p in (Path(__file__), ROOT/'scripts/continuation_common.py',
        ROOT/'training/game_feedback.py', ROOT/'docs/CONTINUATION_VALUE_CURRICULUM_PLAN_20260909.md')})
    save(OUT/'preparation.json', dict(rows=planned, reserved_full_game_keys=sorted(protected),
        sources=sources, teacher_budgets=[80000,320000], maximum_teacher_nodes=48000000,
        no_runtime_lookup=True, raw_source_publication=False))
    print(json.dumps(dict(planned=len(planned), reserved=sum(r['split']=='reserved_test' for r in planned))),flush=True)


def label(partition):
    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback
    check_stop()
    prep = json.loads((OUT/'preparation.json').read_text())
    assert all(digest(Path(p)) == h for p,h in prep['sources'].items())
    path = OUT/(partition+'.json')
    assert not path.exists()
    wait_for_capacity(OUT/(partition+'-capacity.json'), minimum_memory_mb=1400, wait_seconds=0)
    used = set()
    frozen = None
    if partition == 'reserved_test':
        fit = RUN/'curriculum-value-01'
        state = json.loads((fit/'state.json').read_text())
        assert state['status'] == 'weights_frozen_before_reserved_labels'
        frozen = state['model_sha256']
        assert digest(fit/'value.npz') == frozen
        used = {r['key'] for r in json.loads((fit/'preparation.json').read_text())['rows']}
    else:
        used = set(prep['reserved_full_game_keys'])
    game_feedback.stop_check = check_stop
    teacher = game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1', OUT)
    state = dict(status='running', rows=[], frozen_model_sha256=frozen,
                 preparation_sha256=digest(OUT/'preparation.json'))
    try:
        for row in prep['rows']:
            if row['split'] != partition: continue
            check_stop()
            board = restore(row)
            item = dict(row, eligible=False)
            if row['key'] in used:
                item['exclusion'] = 'exact/mirror overlap or duplicate'
            elif not active(board):
                item['exclusion'] = 'check/terminal/repetition/draw clock'
            else:
                labels = [teacher.analyse(board,n) for n in prep['teacher_budgets']]
                cp = [r['cp'] for r in labels]
                finite = all(v is not None for v in cp) and all(r['mate'] is None for r in labels)
                eligible = finite and max(map(abs,cp)) <= 1500 and abs(cp[0]-cp[1]) <= 100
                item.update(teacher=labels,eligible=bool(eligible),
                    target_stm_cp=sum(cp)/2 if eligible else None)
                if not eligible:item['exclusion']='mate/nonfinite/large/disagreeing labels'
                used.add(row['key'])
            state['rows'].append(item)
            save(path,state)
        state.update(status='complete', eligible=sum(r['eligible'] for r in state['rows']))
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        teacher.close()
        state['requested_teacher_nodes'] = teacher.requested_nodes
        assert teacher.requested_nodes <= prep['maximum_teacher_nodes']
        if frozen:assert digest(RUN/'curriculum-value-01/value.npz') == frozen
        save(path,state)
    print(json.dumps({k:v for k,v in state.items() if k!='rows'}),flush=True)


if __name__ == '__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=['prepare','train','reserved_test'],required=True)
    mode=parser.parse_args().mode
    prepare() if mode=='prepare' else label(mode)
