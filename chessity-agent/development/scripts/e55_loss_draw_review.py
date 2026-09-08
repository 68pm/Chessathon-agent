"""One bounded review of the exact v1.53 E55 win, losses and draw."""
import io
import json
import os

import chess.pgn

from scripts import improvement_audit, improvement_phase_report
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_matches import audited
from training.fastchess_data import ROOT

OUT = ROOT / 'runs/e55-loss-draw-review-20260908'
SOURCE = ROOT / ('runs/improvement-loop-20260907/competition-conditional-rated-01/'
                 'rated-compiled-near-queen-checks-v1/results.json')


def main():
    assert not (OUT / 'context.json').exists(), 'Preserve every attempt'
    report = audited(SOURCE)
    assert len(report['games']) == 4
    assert [(g['elo'], g['score']) for g in report['games']] == [
        (2400, 1), (2400, 0), (2600, .5), (2600, 0)]
    count = sum(m['white'] == g['candidate_white'] for g in report['games'] for m in g['moves'])
    paths = ['scripts/e55_loss_draw_review.py', 'scripts/improvement_audit.py',
             'scripts/improvement_phase_report.py', 'training/puzzle_verifier.py',
             'docs/E55_LOSS_DRAW_REVIEW_20260908.md']
    prep = dict(matches_sha256=sha256(SOURCE), own_moves=count,
        maximum_requested_nodes=count * 840000,
        source_files={p: sha256(ROOT / p) for p in paths},
        candidate_files=manifest(ROOT / 'candidates/compiled-near-queen-checks-v1'))
    save_json(OUT / 'preparation.json', prep)
    pgn_dir = OUT / 'pgns'
    pgn_dir.mkdir(exist_ok=False)
    for game in report['games']:
        pgn = chess.pgn.read_game(io.StringIO(game['pgn']))
        assert not pgn.errors and pgn.end().board().fen() == game['final_fen']
        role = {0: 'loss', .5: 'draw', 1: 'win-control'}[game['score']]
        (pgn_dir / f"game-{game['id']:03}-{game['elo']}-{role}.pgn").write_text(
            game['pgn'], encoding='utf-8', newline='\n')
    state = dict(status='running', pid=os.getpid(), requested_teacher_nodes=0,
                 maximum_requested_nodes=prep['maximum_requested_nodes'], new_games=0, new_fits=0)
    save_json(OUT / 'context.json', state)
    original_evaluate, original_verifier = improvement_audit.evaluate, improvement_audit.Verifier

    def guarded_evaluate(engine, board, nodes, move=None):
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')
        assert nodes in (20000, 80000, 320000)
        state['requested_teacher_nodes'] += nodes
        assert state['requested_teacher_nodes'] <= prep['maximum_requested_nodes']
        save_json(OUT / 'context.json', state)
        return original_evaluate(engine, board, nodes, move)

    class GuardedVerifier(original_verifier):
        def __init__(self, executable):
            wait_for_capacity(OUT / 'teacher-launch-capacity.json')
            super().__init__(executable)

    try:
        improvement_audit.evaluate, improvement_audit.Verifier = guarded_evaluate, GuardedVerifier
        improvement_audit.review(SOURCE, OUT / 'audit')
        improvement_phase_report.report(SOURCE, OUT / 'audit', OUT / 'phase.json', 'v53-e55')
        assert sha256(SOURCE) == prep['matches_sha256']
        assert all(sha256(ROOT / p) == h for p, h in prep['source_files'].items())
        assert manifest(ROOT / 'candidates/compiled-near-queen-checks-v1') == prep['candidate_files']
        assert json.loads((OUT / 'audit/audit.json').read_text())['own_moves'] == count
        state['status'] = 'complete'
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        improvement_audit.evaluate, improvement_audit.Verifier = original_evaluate, original_verifier
        save_json(OUT / 'context.json', state)


if __name__ == '__main__':
    main()
