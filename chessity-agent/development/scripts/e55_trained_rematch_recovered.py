"""Four games at 2400/2600; two at 2800 only after a played 2600 win."""
import json
import os
import sys
from pathlib import Path

import chess.engine

from scripts import overnight_game, overnight_matches
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from training.fastchess_data import ROOT

OUT = ROOT / 'runs/e55-trained-rematch-ready-20260908'


def qualifying_win(games):
    return any(g['elo'] == 2600 and g['score'] == 1 and g['failed_colour'] is None
        and g['termination'] == 'checkmate' for g in games)


def main():
    prep = json.loads((OUT / 'preparation.json').read_text())
    path = OUT / 'context.json'
    assert not path.exists(), 'No unchanged match retries'

    def verify():
        assert sha256(OUT / 'read-only-check-recovered.json') == prep['read_only_sha256']
        check = json.loads((OUT / 'read-only-check-recovered.json').read_text())
        assert check['status'] == 'complete' and check['init_ms'] < 90000 and check['legal_calls'] == 2
        assert manifest(ROOT / prep['candidate']) == prep['candidate_files']
        assert all(sha256(ROOT / name) == digest for name, digest in prep['source_files'].items())

    verify()
    state = dict(status='running', pid=os.getpid(), stage='2400-and-2600', completed=[],
        preparation_sha256=sha256(OUT / 'preparation.json'), conditional_2800='not_evaluated')
    save_json(path, state)
    original_local = overnight_game.local
    original_popen = chess.engine.SimpleEngine.popen_uci
    launches = 0

    def guard():
        nonlocal launches
        launches += 1
        wait_for_capacity(OUT / f'launch-{launches}-capacity.json')

    def guarded_local(folder):
        guard()
        return original_local(folder)

    def guarded_opponent(*args, **kwargs):
        guard()
        return original_popen(*args, **kwargs)

    def run(levels, cycle):
        sys.argv = ['overnight_matches', '--candidate', prep['candidate'], '--stage', 'rated',
            '--pairs', '1', '--cycle', cycle, '--levels', *map(str, levels),
            '--openings', prep['openings']]
        target = ROOT / 'runs/improvement-loop-20260907' / cycle / ('rated-' + Path(prep['candidate']).name) / 'results.json'
        assert not target.exists(), 'Preserve all attempts; this wrapper never resumes a match run'
        overnight_matches.main()
        report = overnight_matches.audited(target)
        assert len(report['games']) == len(levels) * 2
        assert {g['elo'] for g in report['games']} == set(levels)
        verify()
        state['completed'].append(dict(path=target.relative_to(ROOT).as_posix(),
            sha256=sha256(target), summary=report['summary']))
        save_json(path, state)
        return report

    try:
        overnight_game.local = guarded_local
        chess.engine.SimpleEngine.popen_uci = staticmethod(guarded_opponent)
        overnight_matches.wait_for_memory = wait_for_capacity
        initial = run([2400, 2600], 'e55-trained-rematch-03')
        if qualifying_win(initial['games']):
            state.update(conditional_2800='triggered_by_played_2600_win', stage='2800')
            save_json(path, state)
            run([2800], 'e55-trained-rematch-2800-03')
        else:
            state['conditional_2800'] = 'skipped_no_played_2600_win'
        state.update(status='complete', stage='awaiting-review')
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        overnight_game.local = original_local
        chess.engine.SimpleEngine.popen_uci = original_popen
        save_json(path, state)


if __name__ == '__main__':
    main()
