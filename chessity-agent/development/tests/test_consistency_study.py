from collections import Counter

import chess
import pytest

from scripts.improvement_consistency import assess_blocks
from scripts.prepare_consistency_study import make_schedule
from scripts.review_consistency_study import verify_opponent_calls


def starts():
    return [dict(group=f'group-{i}', key=f'board-{i}', start_fen=chess.STARTING_FEN) for i in range(64)]


def test_fixed_schedule_balances_levels_colours_and_separates_blocks():
    schedule = make_schedule(starts())
    assert len(schedule) == len({g['id'] for g in schedule}) == 256
    assert Counter((g['elo'],g['block']) for g in schedule) == {(2400,1):64,(2600,1):64,(2400,2):64,(2600,2):64}
    assert all(g['block'] == 1 for g in schedule[:128])
    assert all(g['block'] == 2 for g in schedule[128:])
    for offset in range(0,256,4):
        group = schedule[offset:offset + 4]
        assert len({g['opening_group'] for g in group}) == 1
        assert {(g['elo'],g['candidate_white']) for g in group} == {(2400,True),(2400,False),(2600,True),(2600,False)}
    assert [g['elo'] for g in schedule[:8:2]] == [2400,2600,2600,2400]


def test_duplicate_group_or_board_cannot_inflate_independent_sample():
    for field in ['group','key']:
        values = starts()
        values[1][field] = values[0][field]
        with pytest.raises(ValueError):
            make_schedule(values)


@pytest.mark.parametrize('level,attempt,required', [(2400,1,49),(2600,2,51)])
def test_predeclared_required_win_thresholds(level,attempt,required):
    jobs = make_schedule(starts())
    for wins, expected in [(required - 1,False),(required,True)]:
        blocks = []
        for block in [1,2]:
            games = [dict(g) for g in jobs if g['elo'] == level and g['block'] == block]
            for i, game in enumerate(games):
                game.update(score=int(i < wins), termination='checkmate')
            blocks.append(games)
        assert assess_blocks(blocks,attempt,level)['statistical_gate_passed'] == expected


def test_missing_or_duplicate_opponent_clock_calls_rejected():
    game = dict(start_fen=chess.STARTING_FEN, candidate_white=True,
                moves=[dict(uci='e2e4'),dict(uci='e7e5')], uci_limits=[dict(ply=1)],
                termination='unfinished', init_ms={'white':1000,'black':20}, failed_colour=None)
    verify_opponent_calls(game)
    for calls in [[],[dict(ply=1),dict(ply=1)],[dict(ply=0)]]:
        with pytest.raises(ValueError):
            verify_opponent_calls(dict(game, uci_limits=calls))
