import pytest
from scripts.evening_screen import challenger_passes,all_required_pass

def pair(scores):
    return [dict(candidate_white=white,score=score,termination='checkmate' if score in (0,1) else 'threefold_repetition',failed_colour=None)
        for white,score in zip((True,False),scores,strict=True)]

def played():
    return {'versus56-b12':pair((1,.5)),'versus56-d48':pair((1,.5)),
        'rated2400':pair((.5,.5)),'rated2600':pair((0,.5))}

def test_threshold_and_no_best_of_selection():
    assert all_required_pass(played())
    assert not challenger_passes([pair((1,.5)),pair((.5,.5))])
    assert not challenger_passes([pair((1,1))])

@pytest.mark.parametrize('label',list(played()))
def test_missing_colour_never_passes(label):
    p=played();p[label][1]['candidate_white']=True
    assert not all_required_pass(p)

@pytest.mark.parametrize('failure',['flag','crash','illegal','init','both_failed'])
def test_operational_wins_do_not_qualify(failure):
    p=played();p['versus56-b12'][0]['termination']=failure
    assert not all_required_pass(p)

@pytest.mark.parametrize('label,scores',[('rated2400',(0,.5)),('rated2600',(0,0)),('versus56-d48',(.5,.5))])
def test_failed_required_gate_retains_release(label,scores):
    p=played();p[label]=pair(scores)
    assert not all_required_pass(p)
