"""Guard against foreign-history scores and verify hint-only behaviour."""
import ast
import json
from pathlib import Path

import chess
import pytest

from experiments import daytime_tt_hint_core as core
from scripts.daytime_common import RUN
from scripts.daytime_tt_hint_test_call import call
from training.rule_value import arrays


@pytest.mark.parametrize('wrong_context,wrong_clock,illegal_hint',[
    (True,False,False),(False,True,False),(True,True,False),
    (True,False,True),(False,False,False),
])
def test_foreign_history_score_cannot_cut_off(wrong_context,wrong_clock,illegal_hint):
    position=chess.Board('7k/8/5KQ1/8/8/8/8/8 w - - 8 1')
    score,control,_=call(core,position,wrong_context,wrong_clock,illegal_hint)
    assert score==(29999 if wrong_context or wrong_clock else 12345)
    assert control[1]==0


@pytest.mark.parametrize('wrong_context,wrong_clock',[(True,False),(False,True),(True,True)])
def test_foreign_hint_is_searched_first_but_cannot_supply_its_score(wrong_context,wrong_clock):
    position=chess.Board()
    score,control,hashes=call(core,position,wrong_context,wrong_clock,
        maximum=2,depth=1,uci='g1f3')
    assert score==0 and control[1]==1 and control[0]==2
    position.push_uci('g1f3')
    assert hashes[1]==core.position_hash(*arrays(position))


@pytest.fixture(scope='module')
def original():
    reference=json.loads((RUN/'tt-hint-02/reference.json').read_text())
    assert reference['status']=='complete' and reference['frozen_candidate']
    return reference['scores']


@pytest.mark.parametrize('fen',[
    chess.STARTING_FEN,
    '4k3/pp3ppp/2n5/3pp3/3PP3/2N5/PPP2PPP/4K3 w - - 0 15',
    '4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 1',
    'r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1',
])
def test_completed_full_width_score_matches_parent(fen,original):
    position=chess.Board(fen)
    a=original[fen]
    b=call(core,position,seed=False,maximum=1000000)
    assert a['interrupted']==b[1][1]==0 and a['score']==b[0]


def test_only_search_hint_guard_changed():
    before=ast.parse((RUN/'fast-legal-01/prototype/engine/compiled_core.py').read_text())
    after=ast.parse(Path(core.__file__).read_text())
    a={n.name:ast.dump(n) for n in before.body if isinstance(n,ast.FunctionDef)}
    b={n.name:ast.dump(n) for n in after.body if isinstance(n,ast.FunctionDef)}
    assert a.keys()==b.keys() and all(a[k]==b[k] for k in a if k!='search')
