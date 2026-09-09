"""Independently label bounded descendants from the completed pawn screen's reviews."""

import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, digest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_portable_fast_screen import audit_feedback
from scripts.overnight_value_labels import duplicate, restore
from training.daytime_small_value import active
from training.game_feedback import normalise_game

OUT = RUN / 'signed-targets-01'


def prepare():
    check_stop()
    assert not OUT.exists()
    screen_path = RUN / 'pawn-screen-01/state.json'
    screen = json.loads(screen_path.read_text())
    assert screen['status'] == 'complete' and screen['frozen_candidates']
    assert all(r['status'] == 'complete' for r in screen['stages'])
    targets, sources, seen, exclusions = [], {}, set(), []
    for match in screen['matches']:
        path = ROOT / match['result_path']
        assert digest(path) == match['sha256']
        report = audit_feedback(path)
        sources[str(path.relative_to(ROOT))] = digest(path)
        feedback = feedback_path(path.parent / 'postgame-feedback')
        for game in report['games']:
            _, identity = normalise_game(game)
            marker = json.loads((feedback/'completed'/(identity['game_key']+'.json')).read_text())
            review_path = feedback / marker['review']
            review = json.loads(review_path.read_text())
            normal_path = path.parent / 'postgame-feedback' / marker['review']
            sources[str(normal_path.relative_to(ROOT))] = digest(review_path)
            usable = [r for r in review['rows'] if active(restore(r))]
            negative = [r for r in usable if r['reward'] is not None and r['reward'] < 0]
            positive = [r for r in usable if r['reward'] is not None and r['reward'] > 0]
            chosen = [(r, role) for r in negative[:2] for role in ('best','played')]
            if positive:
                chosen.append((positive[len(positive)//2], 'played'))
            for row, role in chosen:
                board = restore(row)
                line = row['labels'][-1][role]['pv'][:4]
                for uci in line:
                    board.push_uci(uci)
                key = duplicate(board)
                identity_string = f'{identity["game_key"]}-ply{row["ply"]}-{role}'
                if len(line) < 4 or not active(board) or key in seen:
                    exclusions.append(dict(id=identity_string, reason='short_line_inactive_or_duplicate'))
                    continue
                seen.add(key)
                targets.append(dict(id=identity_string, group=game['opening_group'], split='train',
                    game_key=identity['game_key'], match=match['label'], parent_ply=row['ply'],
                    parent_san=row['san'], branch=role, parent_label=row['label'],
                    start_fen=row['start_fen'], history=[m.uci() for m in board.move_stack],
                    fen=board.fen(), duplicate_key=key))
    assert targets and len(targets) <= 50
    for path in (screen_path, Path(__file__), ROOT/'training/daytime_small_value.py',
                 ROOT/'training/game_feedback.py', ROOT/'docs/DAYTIME_SIGNED_TARGETS_20260909.md'):
        sources[str(path.relative_to(ROOT))] = digest(path)
    save(OUT/'preparation.json', dict(created_utc=datetime.now(timezone.utc).isoformat(), targets=targets,
        exclusions=exclusions, source_sha256=sources, budgets=[80000,320000],
        maximum_teacher_nodes=len(targets)*400000,
        scope='Exposed training descendants from frozen reviewed games. New independent values, never root rewards or inferred Elo.'))
    print(json.dumps(dict(prepared=len(targets), maximum_teacher_nodes=len(targets)*400000)))


def run():
    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback

    check_stop()
    assert not (OUT/'state.json').exists()
    prep = json.loads((OUT/'preparation.json').read_text())
    assert all(digest(feedback_path(ROOT/p)) == h for p,h in prep['source_sha256'].items())
    wait_for_capacity(OUT/'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    game_feedback.stop_check = check_stop
    teacher = game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1', OUT)
    state = dict(status='running',rows=[])
    save(OUT/'state.json',state)
    try:
        for target in prep['targets']:
            check_stop()
            board = restore(target)
            assert active(board)
            labels = [teacher.analyse(board, budget) for budget in prep['budgets']]
            cp = [label['cp'] for label in labels]
            valid = (all(value is not None for value in cp) and all(label['mate'] is None for label in labels)
                     and max(map(abs,cp)) <= 1500 and abs(cp[0]-cp[1]) <= 100)
            state['rows'].append(dict(**target,teacher=labels,eligible=valid,
                target_stm_cp=sum(cp)/2 if valid else None,
                exclusion=None if valid else 'mate_nonfinite_large_or_unstable_value'))
            save(OUT/'state.json',state)
        state.update(status='complete',eligible=sum(r['eligible'] for r in state['rows']))
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        teacher.close()
        state.update(requested_teacher_nodes=teacher.requested_nodes,finished_utc=datetime.now(timezone.utc).isoformat())
        assert teacher.requested_nodes <= prep['maximum_teacher_nodes']
        save(OUT/'state.json',state)
    print(json.dumps({k:v for k,v in state.items() if k!='rows'}))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare',action='store_true')
    prepare() if parser.parse_args().prepare else run()
