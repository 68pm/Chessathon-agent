"""Review only the fresh own rounds and current leader's latest completed games."""
import argparse
import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from scripts.continuation_common import ROOT, RUN, check_stop, digest, save
from scripts.feedback_matches_windows import feedback_path

OUT=RUN/'field-review-01'


def prepare():
    check_stop()
    assert not OUT.exists()
    source=RUN/'field-01/state.json'
    state=json.loads(source.read_text())
    assert state['status']=='downloaded_awaiting_review'
    prior=ROOT/'runs/daytime-20260909/field-07/state.json'
    previous=json.loads(prior.read_text())
    cutoff=max(r['record']['id'] for r in previous['new_games'] if r['label']=='own')
    selected=json.loads((ROOT.parent/'chessity-agent-version.json').read_text())
    assert selected['version']=='v1.56'
    policy=ROOT/selected['source_version']/'models/player-policy.npz'
    prep=dict(status='prepared',source_hashes={str(p):digest(p) for p in (source,prior,Path(__file__),policy)},
        own_round_cutoff=cutoff,selected=selected['version'],selected_sha256=selected['sha256'],
        policy_path=str(policy),groups={},excluded=[],scope='Fresh public games, submission hashes unknown; exposed development data.')
    for label in ('own','leader'):
        rows=[r for r in state['new_games'] if r['label']==label]
        keep=[r for r in rows if label!='own' or r['record']['id']>cutoff]
        prep['excluded'] += [dict(label=r['label'],url=r['url'],round=r['record']['id'],
                                 reason='Older own round outside requested recent-game window') for r in rows if r not in keep]
        records=[r['record'] for r in keep]
        save(OUT/(label+'-games.json'),dict(status='complete',games=records))
        prep['groups'][label]=dict(games=len(records),source_sha256=digest(OUT/(label+'-games.json')),
                                  urls=[r['url'] for r in keep])
    save(OUT/'preparation.json',prep)
    print(json.dumps({'groups':prep['groups'],'excluded':prep['excluded']}),flush=True)


def review():
    check_stop()
    prep=json.loads((OUT/'preparation.json').read_text())
    assert all(digest(Path(p))==h for p,h in prep['source_hashes'].items())
    state_path=OUT/'state.json'
    assert not state_path.exists()
    from scripts.overnight_capacity import wait_for_capacity
    from scripts import feedback_batch
    from training import game_feedback
    wait_for_capacity(OUT/'capacity.json',minimum_memory_mb=1400,wait_seconds=0)
    game_feedback.stop_check=check_stop
    state=dict(status='reviewing',groups=[],started_utc=datetime.now(timezone.utc).isoformat())
    save(state_path,state)
    try:
        for label in ('own','leader'):
            check_stop()
            source=OUT/(label+'-games.json')
            assert digest(source)==prep['groups'][label]['source_sha256']
            if not prep['groups'][label]['games']:continue
            sys.argv=['scripts.feedback_batch','--source',str(source),'--out',
                str(feedback_path(OUT/(label+'-review'))),'--initial-policy',prep['policy_path']]
            feedback_batch.main()
            state['groups'].append(dict(label=label,status='complete',games=prep['groups'][label]['games']))
            save(state_path,state)
        state['status']='complete'
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        state['finished_utc']=datetime.now(timezone.utc).isoformat()
        save(state_path,state)
    print(json.dumps(state),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',choices=('prepare','review'),required=True)
    {'prepare':prepare,'review':review}[parser.parse_args().mode]()
