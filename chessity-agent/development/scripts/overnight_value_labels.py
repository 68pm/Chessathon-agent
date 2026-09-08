"""Independently label counterfactual descendant positions, with source-group splits."""

import argparse
import hashlib
import itertools
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'runs/overnight-20260909/value-labels-02'
SOURCES = ROOT / 'runs/all-game-feedback-20260908/review/games'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(path, value):
    path.write_text(json.dumps(value, indent=2) + '\n', encoding='utf-8')


def restore(row):
    import chess

    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.fen() == row['fen'] and board.is_valid()
    return board


def duplicate(board):
    # Ignore fullmove and draw clock for stricter train/validation duplicate removal.
    return min(' '.join(board.fen().split()[:4]), ' '.join(board.mirror().fen().split()[:4]))


def prepare():
    assert not OUT.exists(), 'Preserve completed and partial preparations'
    OUT.mkdir(parents=True)
    documents = [(path, json.loads(path.read_text(encoding='utf-8'))) for path in sorted(SOURCES.glob('*/review.json'))]
    assert len(documents) == 8 and all(d['status'] == 'complete' for _, d in documents)
    groups = {}
    for _, doc in documents:
        game = doc['identity']['game']
        # All four E55 local games have the same starting position and stay together.
        group = hashlib.sha256(game['start_fen'].encode()).hexdigest()
        groups.setdefault(group, []).append(game['game_key'])
    alternatives = []
    names = sorted(groups)
    for count in range(1, len(names)):
        for subset in itertools.combinations(names, count):
            size = sum(len(groups[g]) for g in subset)
            tie = hashlib.sha256(('202609092330:' + ':'.join(subset)).encode()).hexdigest()
            alternatives.append((abs(size - 2), count, tie, subset))
    heldout = set(min(alternatives)[-1])
    planned, exclusions = [], []
    for path, doc in documents:
        game = doc['identity']['game']
        group = hashlib.sha256(game['start_fen'].encode()).hexdigest()
        split = 'validation' if group in heldout else 'train'
        negatives = [r for r in doc['rows'] if (r.get('reward') or 0) < 0]
        negatives.sort(key=lambda r: (-abs(r['reward']), r['ply']))
        positives = [r for r in doc['rows'] if (r.get('reward') or 0) > 0]
        # Spread useful positive examples across the game rather than all near mate.
        positive_indices = sorted({round(i * (len(positives) - 1) / 3) for i in range(4)}) if positives else []
        chosen = negatives[:4] + [positives[i] for i in positive_indices]
        count = 0
        for root in chosen:
            for branch in ('best', 'played'):
                board = restore(root)
                pv = root['labels'][-1][branch]['pv']
                for depth, uci in enumerate(pv[:4], 1):
                    board.push_uci(uci)
                    if depth not in (2, 4):
                        continue
                    if count >= 24:
                        break
                    if (board.is_check() or board.is_game_over(claim_draw=True) or
                            board.is_repetition(2) or board.halfmove_clock >= 70):
                        exclusions.append(dict(game=game['game_key'], ply=root['ply'],
                            branch=branch, depth=depth, reason='check/terminal/repetition/draw-clock'))
                        continue
                    history = [m.uci() for m in board.move_stack]
                    identity = hashlib.sha256(json.dumps([game['game_key'], root['ply'], branch, depth, history]).encode()).hexdigest()
                    planned.append(dict(id=identity, source=str(path.relative_to(ROOT)),
                        source_game_id=game['source_game_id'], game_key=game['game_key'], group=group,
                        split=split, root_ply=root['ply'], branch=branch, descendant_plies=depth,
                        start_fen=board.root().fen(), history=history, fen=board.fen(),
                        duplicate_key=duplicate(board), original_move_reward=root['reward'],
                        note='Parent action reward is provenance only; this position needs its own value label.'))
                    count += 1
    protected = {r['duplicate_key'] for r in planned if r['split'] == 'validation'}
    kept, seen = [], set()
    for row in sorted(planned, key=lambda r: (r['split'] != 'validation', r['id'])):
        key = row['duplicate_key']
        if key in seen or (row['split'] == 'train' and key in protected):
            exclusions.append(dict(id=row['id'], reason='duplicate/mirror or validation collision'))
            continue
        kept.append(row)
        seen.add(key)
    assert 16 <= len(kept) <= 192 and {r['split'] for r in kept} == {'train', 'validation'}
    save(OUT / 'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256={str(p.relative_to(ROOT)): sha(p) for p, _ in documents} |
                      {str(Path(__file__).relative_to(ROOT)): sha(Path(__file__))},
        groups=groups, heldout_groups=sorted(heldout), targets=kept, exclusions=exclusions,
        max_teacher_nodes=len(kept) * 400000,
        scope='Counterfactual descendants independently relabelled; split by starting-position/game groups before labels. Historical exposure remains possible.'))
    print(json.dumps({'targets': len(kept), 'train': sum(r['split'] == 'train' for r in kept),
                      'validation': sum(r['split'] == 'validation' for r in kept)}), flush=True)


def run():
    from scripts.overnight_capacity import wait_for_capacity
    from scripts.overnight_geometry_trial import check_stop
    from training.game_feedback import CachedTeacher

    prep = json.loads((OUT / 'preparation.json').read_text(encoding='utf-8'))
    assert all(sha(ROOT / p) == h for p, h in prep['source_sha256'].items())
    path = OUT / 'state.json'
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
        status='running', preparation_sha256=sha(OUT / 'preparation.json'), rows=[])
    assert state['preparation_sha256'] == sha(OUT / 'preparation.json')
    if state['status'] == 'complete':
        return
    check_stop()
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)
    done = {r['id'] for r in state['rows']}
    try:
        for target in prep['targets']:
            check_stop()
            if target['id'] in done:
                continue
            board = restore(target)
            values = [teacher.analyse(board, nodes) for nodes in (80000, 320000)]
            cp = [v['cp'] for v in values]
            eligible = (all(v is not None for v in cp) and all(v['mate'] is None for v in values)
                        and max(map(abs, cp)) <= 1500 and abs(cp[0] - cp[1]) <= 100)
            state['rows'].append(dict(**target, teacher=values, eligible=eligible,
                target_stm_cp=sum(cp) / 2 if eligible else None,
                exclusion=None if eligible else 'mate/non-finite/outside1500cp/unstable_over100cp'))
            state.update(status='running', requested_nodes_this_process=teacher.requested_nodes)
            save(path, state)
            print(f"{len(state['rows'])}/{len(prep['targets'])} labelled; eligible={eligible}", flush=True)
        state.update(status='complete', train=sum(r['eligible'] and r['split'] == 'train' for r in state['rows']),
            validation=sum(r['eligible'] and r['split'] == 'validation' for r in state['rows']))
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        state['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save(path, state)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else run()
