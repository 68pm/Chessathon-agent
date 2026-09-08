"""Four frozen v1.53 games at nominal2400/2600, with per-launch capacity guards."""
import json
import sys

import chess.engine

from scripts import overnight_game, overnight_matches
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/near-queen-rated-controller'
    prep = json.loads((out / 'preparation.json').read_text())
    context_path = out / 'rated-context.json'
    if context_path.exists():
        raise ValueError('No unchanged rated-screen retry')

    def verify():
        assert manifest(ROOT / prep['candidate']) == prep['candidate_files']
        assert all(sha256(ROOT / name) == digest for name, digest in prep['source_files'].items())

    verify()
    state = dict(status='running', stage='four-serial-games', preparation_sha256=sha256(out / 'preparation.json'))
    save_json(context_path, state)
    try:
        launches = 0

        def guard():
            nonlocal launches
            launches += 1
            wait_for_capacity(out / f'launch-{launches}-capacity.json')

        original_local = overnight_game.local
        original_popen = chess.engine.SimpleEngine.popen_uci

        def guarded_local(folder):
            guard()
            return original_local(folder)

        def guarded_opponent(*args, **kwargs):
            guard()
            return original_popen(*args, **kwargs)

        overnight_game.local = guarded_local
        chess.engine.SimpleEngine.popen_uci = staticmethod(guarded_opponent)
        overnight_matches.wait_for_memory = wait_for_capacity
        sys.argv = ['overnight_matches', '--candidate', prep['candidate'], '--stage', 'rated',
            '--pairs', '1', '--cycle', 'near-queen-rated-01', '--levels', '2400', '2600',
            '--openings', 'configs/near-queen-rated-openings.json']
        overnight_matches.main()
        path = ROOT / 'runs/improvement-loop-20260907/near-queen-rated-01/rated-compiled-near-queen-checks-v1/results.json'
        report = overnight_matches.audited(path)
        assert len(report['games']) == 4
        assert {g['elo'] for g in report['games']} == {2400, 2600}
        verify()
        state.update(status='complete', stage='awaiting-review', summary=report['summary'], results_sha256=sha256(path))
        print(json.dumps(state), flush=True)
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(context_path, state)


if __name__ == '__main__':
    main()
