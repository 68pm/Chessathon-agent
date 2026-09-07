"""Report the four-game diagnostic without rating certification or promotion."""

import json

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_review import audited
from training.fastchess_data import ROOT


def main():
    run = ROOT / 'runs/improvement-loop-20260907'
    out = run / 'quick-check-01'
    groups = {}
    for level in [2400,2600]:
        matches = run / f'quick-check-01-{level}/rated-compiled-qsearch-endgames-v1/results.json'
        source = audited(matches)
        assert len(source['games']) == 2 and {g['elo'] for g in source['games']} == {level}
        assert {g['candidate_white'] for g in source['games']} == {True,False}
        phase = json.loads((out / f'phase-{level}.json').read_text(encoding='utf-8'))
        assert phase['matches_sha256'] == sha256(matches)
        groups[str(level)] = dict(summary=source['summary'][f'stockfish:{level}'],
                                 phase=phase['groups'][f'stockfish:{level}'],
                                 results_sha256=sha256(matches), phase_sha256=sha256(out / f'phase-{level}.json'))
    result = dict(status='complete', selected='v1.41', games=4, time_control='120+0.5', groups=groups,
        decision='Use first-warning evidence to choose the next bounded improvement. No qualification, pool retirement, or promotion follows from four games.',
        source_code_sha256=sha256(__file__))
    save_json(out / 'review.json', result)
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
