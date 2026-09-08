"""One strict package check and the two already declared cycle35 games."""
import json
import sys
import zipfile

from scripts import overnight_game, overnight_matches
from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_king_coordination_gate import child
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/cycle-35-practical'
    prep = json.loads((out / 'preparation.json').read_text())
    state_path = out / 'context.json'
    if state_path.exists():
        raise ValueError('Preserve this attempt; no unchanged practical retry')
    candidate = ROOT / prep['candidate']
    base = ROOT / 'candidates/compiled-king-coordination-v1'
    archive = out / 'candidate.zip'

    def verify():
        assert sha256(archive) == prep['zip_sha256']
        assert manifest(candidate) == prep['candidate_files']
        assert manifest(base) == prep['baseline_files']
        assert all(sha256(ROOT / name) == digest for name, digest in prep['source_files'].items())
        assert json.loads((ROOT / prep['gate']).read_text())['passed'] is True
        with zipfile.ZipFile(archive) as package:
            assert all(package.read(name) == (candidate / name).read_bytes() for name in package.namelist())

    verify()
    state = dict(status='running', stage='read-only', preparation_sha256=sha256(out / 'preparation.json'))
    save_json(state_path, state)
    try:
        wait_for_capacity(out / 'readonly-capacity.json')
        readonly_path = out / 'read-only-check.json'
        child(['-m', 'scripts.validate_package', '--zip', str(archive), '--out', str(readonly_path),
            '--clock-ms', '120000', '--calls', '2'], out / 'read-only.log')
        check = json.loads(readonly_path.read_text())
        assert check['sha256'] == prep['zip_sha256'] and check['legal_calls'] == 2
        assert check['clock_ms'] == 120000 and check['init_ms'] < 90000
        assert all(v == 'blocked' for v in check['read_only_checks'].values())
        assert check['selective_alien_verified'] and check['elementary_endgames_verified']
        verify()
        state['stage'] = 'two-games-vs52'
        save_json(state_path, state)
        # Preserve old harness files; add both resource limits before each game
        # and immediately before each fresh agent process in this new wrapper.
        original_local = overnight_game.local
        launches = 0

        def guarded_local(folder):
            nonlocal launches
            launches += 1
            wait_for_capacity(out / f'agent-launch-{launches}-capacity.json')
            return original_local(folder)

        overnight_game.local = guarded_local
        overnight_matches.wait_for_memory = wait_for_capacity
        sys.argv = ['overnight_matches', '--candidate', prep['candidate'],
            '--opponent', 'candidates/compiled-king-coordination-v1', '--stage', 'comparison',
            '--pairs', '1', '--cycle', 'cycle-35-pair',
            '--openings', 'configs/near-queen-checks-openings.json']
        overnight_matches.main()
        results_path = ROOT / 'runs/improvement-loop-20260907/cycle-35-pair' / ('comparison-' + candidate.name) / 'results.json'
        report = overnight_matches.audited(results_path)
        assert len(report['games']) == 2
        assert sorted(g['candidate_white'] for g in report['games']) == [False, True]
        verify()
        summary = report['summary']['incumbent']
        clean = all(g.get('failed_colour') is None and g['termination'] not in overnight_game.FAILURES
            for g in report['games'])
        decision = dict(status='complete', passed=clean and summary['score'] >= .5,
            automatic_promotion=False, summary=summary, clean_games=clean,
            readonly_sha256=sha256(readonly_path), results_sha256=sha256(results_path),
            scope='Two predeclared games after a tactical pass; selection review required, no calibrated Elo.')
        save_json(out / 'decision.json', decision)
        state.update(status='complete', stage='awaiting-selection-review', passed=decision['passed'])
        print(json.dumps(decision), flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(state_path, state)


if __name__ == '__main__':
    main()
