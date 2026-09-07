"""Conservative statistical component of the fixed-strength retirement gate.

Call only after independent provenance, clocks, freshness and interruption audits.
This function cannot by itself certify freshness or mutate the opponent pool.
"""

import math

from scripts.fastchess_matches import FAILURES


def assess_blocks(blocks, attempt, level):
    if attempt < 1 or len(blocks) != 2 or any(len(b) != 64 for b in blocks):
        raise ValueError('Use a registered positive attempt and two fixed64-game blocks.')
    if len({g['candidate_path'] for b in blocks for g in b}) != 1:
        raise ValueError('Both blocks must use the same frozen candidate.')
    if {g['elo'] for b in blocks for g in b} != {level}:
        raise ValueError('Do not mix opponent strengths in a consistency gate.')
    alpha = .05 / (attempt * (attempt + 1))
    seen_groups, results = set(), []
    for block in blocks:
        if len({g['id'] for g in block}) != 64:
            raise ValueError('Duplicate game IDs within a block.')
        values = []
        for pair in sorted({g['pair'] for g in block}):
            games = [g for g in block if g['pair'] == pair]
            if len(games) != 2 or {g['candidate_white'] for g in games} != {True, False}:
                raise ValueError('Each opening group needs both colours exactly once.')
            groups = {g['opening_group'] for g in games}
            if len(groups) != 1 or next(iter(groups)) in seen_groups:
                raise ValueError('Opening groups must be distinct within and across blocks.')
            if games[0]['opening'] != games[1]['opening'] or games[0].get('start_fen') != games[1].get('start_fen'):
                raise ValueError('Paired starting setups must match.')
            seen_groups.update(groups)
            if any(g['score'] not in (0, .5, 1) for g in games):
                raise ValueError('Invalid game result.')
            values.append(sum(g['score'] == 1 for g in games) / 2)
        if len(values) != 32:
            raise ValueError('Exactly32 paired groups are required per block.')
        wins = sum(g['score'] == 1 for g in block)
        draws = sum(g['score'] == .5 for g in block)
        failures = sum(g['termination'] in FAILURES for g in block)
        mean = sum(values) / len(values)
        lower = max(0., mean - math.sqrt(math.log(1 / (alpha / 2)) / (2 * len(values))))
        results.append(dict(wins=wins, draws=draws, losses=64 - wins - draws,
                            pairs=len(values), outright_win_fraction=mean,
                            one_sided_alpha=alpha / 2, lower_win_bound=lower,
                            runtime_failures=failures,
                            statistical_gate_passed=wins > 32 and lower > .5 and failures == 0))
    return dict(attempt=attempt, nominal_level=level, attempt_alpha=alpha, blocks=results,
                statistical_gate_passed=all(r['statistical_gate_passed'] for r in results),
                separate_provenance_clock_freshness_and_interruption_audits_required=True,
                scope='Outright wins, not half-credit draws. Bounded colour-pair Hoeffding bound; independent groups and stable conditions assumed. Not a calibrated Elo or automatic pool mutation.')
