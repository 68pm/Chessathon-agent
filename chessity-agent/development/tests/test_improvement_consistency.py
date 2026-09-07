import pytest

from scripts.improvement_consistency import assess_blocks
from scripts.improvement_pool_matches import selected_levels


def blocks(score=1):
    return [[dict(id=2 * p + int(white), pair=p, opening_group=f'{b}:{p}',
                  candidate_white=white, candidate_path='frozen-agent', elo=2400,
                  opening=[], score=score, termination='checkmate')
             for p in range(32) for white in [False, True]] for b in range(2)]


def test_small_screen_and_draws_cannot_retire_a_level():
    with pytest.raises(ValueError):
        assess_blocks([blocks()[0][:8], blocks()[1][:8]], 1, 2400)
    assert not assess_blocks(blocks(.5), 1, 2400)['statistical_gate_passed']
    assert assess_blocks(blocks(), 1, 2400)['statistical_gate_passed']
    later = assess_blocks(blocks(), 2, 2400)
    assert later['blocks'][0]['lower_win_bound'] < assess_blocks(blocks(), 1, 2400)['blocks'][0]['lower_win_bound']


def test_reused_groups_mixed_agent_and_runtime_failures_rejected():
    reused = blocks()
    reused[1][0]['opening_group'] = reused[1][1]['opening_group'] = '0:0'
    with pytest.raises(ValueError):
        assess_blocks(reused, 1, 2400)
    mixed = blocks()
    mixed[1][0]['candidate_path'] = 'other-agent'
    with pytest.raises(ValueError):
        assess_blocks(mixed, 1, 2400)
    failed = blocks()
    failed[0][0]['termination'] = 'flag'
    assert not assess_blocks(failed, 1, 2400)['statistical_gate_passed']


def test_retired_level_cannot_be_scheduled_in_new_pool():
    pool = dict(active_nominal_levels=[2600, 2800])
    assert selected_levels(pool) == [2600, 2800]
    assert selected_levels(pool, [2600]) == [2600]
    for invalid in [[2400], [2600, 2600], []]:
        with pytest.raises(ValueError):
            selected_levels(pool, invalid)
    with pytest.raises(ValueError):
        selected_levels(dict(active_nominal_levels=[2400, 2600], retired_nominal_levels=[2400]))
