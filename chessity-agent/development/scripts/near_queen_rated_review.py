"""Review the completed v1.53 rated screen once, with bounded teacher work."""
import json
from pathlib import Path

from scripts import improvement_audit
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_matches import audited
from training.fastchess_data import ROOT


def main():
    run = ROOT / 'runs/improvement-loop-20260907'
    out = run / 'near-queen-rated-review'
    source = run / 'near-queen-rated-01/rated-compiled-near-queen-checks-v1/results.json'
    controller = run / 'near-queen-rated-controller/controller.json'
    assert json.loads(controller.read_text())['status'] == 'complete'
    report = audited(source)
    assert len(report['games']) == len(report['schedule']) == 4
    assert sorted(g['candidate_white'] for g in report['games']) == [False, False, True, True]
    assert not (out / 'preparation.json').exists(), 'Preserve the original review attempt'
    out.mkdir(parents=True, exist_ok=False)
    assert {g['elo'] for g in report['games']} == {2400, 2600}
    count = sum(m['white'] == g['candidate_white'] for g in report['games'] for m in g['moves'])
    paths = ['scripts/near_queen_rated_review.py', 'scripts/improvement_audit.py',
             'scripts/improvement_phase_report.py', 'training/puzzle_verifier.py',
             'configs/near-queen-rated-review-cycle.json',
             'docs/NEAR_QUEEN_RATED_REVIEW_20260908.md']
    prep = dict(matches_sha256=sha256(source), own_moves=count,
                maximum_requested_nodes=count * 840000,
                source_files={p: sha256(ROOT / p) for p in paths},
                candidate_files=manifest(ROOT / 'candidates/compiled-near-queen-checks-v1'))
    save_json(out / 'preparation.json', prep)
    original_evaluate = improvement_audit.evaluate
    original_verifier = improvement_audit.Verifier
    requested = 0

    def guarded_evaluate(engine, board, nodes, move=None):
        nonlocal requested
        if any((ROOT / flag).exists() for flag in ['STOP_TRAINING', 'STOP_BENCHMARK']):
            raise InterruptedError('User stop flag')
        assert nodes in (20000, 80000, 320000)
        requested += nodes
        assert requested <= prep['maximum_requested_nodes']
        return original_evaluate(engine, board, nodes, move)

    class GuardedVerifier(original_verifier):
        def __init__(self, executable):
            wait_for_capacity(out / 'teacher-launch-capacity.json')
            super().__init__(executable)

    improvement_audit.evaluate = guarded_evaluate
    improvement_audit.Verifier = GuardedVerifier
    try:
        improvement_audit.review(source, out / 'audit')
        assert sha256(source) == prep['matches_sha256']
        assert all(sha256(ROOT / p) == digest for p, digest in prep['source_files'].items())
        assert manifest(ROOT / 'candidates/compiled-near-queen-checks-v1') == prep['candidate_files']
        result = json.loads((out / 'audit/audit.json').read_text())
        assert result['own_moves'] == count and result['games'] == 4
        save_json(out / 'limits.json', dict(status='complete', requested_teacher_nodes=requested,
                  maximum_requested_nodes=prep['maximum_requested_nodes'], new_games=0,
                  new_fits=0, source_sha256=sha256(Path(__file__))))
    finally:
        improvement_audit.evaluate = original_evaluate
        improvement_audit.Verifier = original_verifier


if __name__ == '__main__':
    main()
