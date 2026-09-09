"""Bounded v1.54 depth traces and forced defensive alternatives; no engine edits."""
import argparse
import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save

OUT = RUN / 'defence-trace-01'
CANDIDATE = RUN / 'pawn-extrema-01/prototype'


def prepare():
    from scripts.feedback_matches_windows import feedback_path
    from scripts.overnight_value_labels import restore

    check_stop()
    assert not OUT.exists()
    field = json.loads((RUN / 'field-04/state.json').read_text())
    assert field['status'] == 'complete'
    selected = json.loads((ROOT.parent / 'chessity-agent-version.json').read_text())
    assert selected['version'] == 'v1.54'
    assert digest(ROOT.parent / 'chessity-agent.zip') == selected['sha256']
    diagnosis_path = RUN / 'pawn-progress-02/diagnosis.json'
    targets = json.loads(diagnosis_path.read_text())['targets']
    roots, source_files = [], [diagnosis_path, RUN / 'field-04/state.json', Path(__file__)]
    for label, white, move in [('rated2400', True, 23), ('rated2400', True, 24),
                               ('rated2600', False, 22), ('rated2600', False, 23)]:
        rows = [r for r in targets if r['match'] == label and r['candidate_white'] == white
                and r['fullmove'] == move]
        assert len(rows) == 1
        roots.append(dict(id=f'{label}-{white}-{move}', **rows[0]))
    for label, moves in [('own', [27, 33, 44]), ('leader', [40])]:
        files = list(feedback_path(RUN / 'field-04' / (label + '-review')).glob('games/*/review.json'))
        rows = [(p, r) for p in files for r in json.loads(p.read_text())['rows']
                if r['fullmove'] in moves and r['reward'] is not None and r['reward'] < 0]
        assert len(rows) == len(moves)
        for p, row in rows:
            source_files.append(p)
            roots.append(dict(id=f'field-{label}-{row["fullmove"]}', **row))
    assert len(roots) == 8
    for row in roots:
        board = restore(row)
        assert row['policy_target'] and row['policy_target'] != row['played']
        assert row['policy_target'] in [m.uci() for m in board.legal_moves]
    save(OUT / 'preparation.json', dict(candidate=str(CANDIDATE.relative_to(ROOT)),
        files=manifest(CANDIDATE), selected_sha256=selected['sha256'], roots=roots,
        sources={str(p): digest(p) for p in source_files},
        protocol=dict(whole_root_seconds=2.5, branch_seconds=2.0, branch_max_depth=7,
            maximum_nodes_per_call=500000, reductions=[True, False], roots=8, calls=48),
        scope='Exposed diagnostic roots, cold tables for each call, existing policy retained. '
              'Forced alternatives are counterfactual searches, not independent labels or strength games.'))
    print('Prepared eight defensive roots', flush=True)


def run():
    from scripts.overnight_capacity import wait_for_capacity

    check_stop()
    prep = json.loads((OUT / 'preparation.json').read_text())
    assert not (OUT / 'state.json').exists()
    assert all(digest(Path(p)) == h for p, h in prep['sources'].items())
    assert manifest(CANDIDATE) == prep['files']
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    result = dict(status='initializing', pid=os.getpid(), rows=[])
    save(OUT / 'state.json', result)
    sys.path.insert(0, str(CANDIDATE))
    tick = time.perf_counter()
    import chess

    import agent

    driver = sys.modules['engine.compiled_driver']
    core = driver.core
    assert Path(core.__file__).resolve() == CANDIDATE / 'engine/compiled_core.py'
    result['init_seconds'] = time.perf_counter() - tick
    assert result['init_seconds'] < 90
    original = core.root_iteration
    signatures = tuple(map(str, original.signatures))
    trace, forced = [], None

    def traced(*args):
        modified = list(args)
        if forced is not None:
            indices = [i for i, move in enumerate(args[4]) if driver.decode(int(move)).uci() == forced]
            assert len(indices) == 1
            modified[4] = args[4][indices].copy()
            modified[5] = args[5][indices].copy()
        started = time.perf_counter()
        move, score, complete = original(*modified)
        trace.append(dict(depth=int(args[2]), uci=driver.decode(int(move)).uci(),
            score=int(score) if complete else None, complete=bool(complete),
            nodes=int(args[13][0]), seconds=time.perf_counter() - started))
        return move, score, complete

    core.root_iteration = traced
    try:
        result['status'] = 'running'
        for row in prep['roots']:
            board = chess.Board(row['start_fen'])
            for uci in row['history']:
                board.push_uci(uci)
            assert board.fen() == row['fen'] and board.is_valid()
            history = list(board.move_stack)
            for reductions in (True, False):
                for mode, forced in [('whole', None), ('played', row['played']), ('defence', row['policy_target'])]:
                    check_stop()
                    for key in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
                        getattr(agent._search, key).fill(0)
                    agent._search.reductions = reductions
                    trace.clear()
                    seconds = 2.5 if mode == 'whole' else 2.0
                    response = agent._search.run(board, seconds=seconds, soft=seconds,
                        max_depth=64 if mode == 'whole' else 7, max_nodes=500000)
                    assert board.fen() == row['fen'] and list(board.move_stack) == history
                    assert response.elapsed <= seconds + .3 and response.nodes <= 500000
                    assert response.move in board.legal_moves
                    assert tuple(map(str, original.signatures)) == signatures
                    if forced is not None and response.depth:
                        assert response.move.uci() == forced
                    result['rows'].append(dict(id=row['id'], reductions=reductions, mode=mode,
                        requested_move=forced, uci=response.move.uci(), score=response.score,
                        depth=response.depth, nodes=response.nodes, seconds=response.elapsed,
                        iterations=list(trace)))
                    save(OUT / 'state.json', result)
            print(f'Traced {row["id"]}', flush=True)
        result.update(status='complete', decision='inspect_common_completed_depths_before_any_patch')
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        core.root_iteration = original
        result.update(frozen_candidate=manifest(CANDIDATE) == prep['files'],
            finished_utc=datetime.now(timezone.utc).isoformat())
        if not result['frozen_candidate']:
            result.update(status='failed', error='Candidate files changed')
        save(OUT / 'state.json', result)
    print(json.dumps({k: v for k, v in result.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    prepare() if parser.parse_args().prepare else run()
