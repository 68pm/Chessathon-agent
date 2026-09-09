"""Verify every required gate and reviewed game before a numbered release."""
import argparse
import json
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from scripts.progression_common import ROOT,RUN,digest,manifest,save
from scripts.progression_screen import all_required_pass
from scripts.daytime_move_buffers_screen import qualifies_2800
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_archive_challenge import archive_matches
from scripts.overnight_portable_fast_screen import audit_feedback
from training.game_feedback import normalise_game

def summarise(games):
    return dict(games=len(games),wins=sum(g['score']==1 for g in games),draws=sum(g['score']==.5 for g in games),
        losses=sum(g['score']==0 for g in games),terminations=dict(Counter(g['termination'] for g in games)))

def audit(screen):
    screen=screen.resolve();assert screen.is_relative_to(RUN)
    out=screen/'release-audit.json';assert not out.exists()
    prep=json.loads((screen/'preparation.json').read_text());state=json.loads((screen/'state.json').read_text())
    assert state['status']=='complete' and state['passed'] and state['frozen_candidates']
    assert all(r['status']=='complete' for r in state['stages'])
    assert all(manifest(ROOT/p)==h for p,h in prep['files'].items())
    assert all(digest(ROOT/p)==h for p,h in prep['source_sha256'].items())
    quality=json.loads((ROOT/prep['candidate']).parent.joinpath('state.json').read_text())
    assert quality['status']=='complete' and quality['passed'] and quality['frozen_candidates']
    before,after=quality['mean_regret_cp']['baseline'],quality['mean_regret_cp']['prototype']
    assert len(before)==len(after)==2 and all(a<=b for a,b in zip(after,before))
    assert any(a<=.9*b for a,b in zip(after,before)) and quality['finite_roots']>=12
    assert not quality['regressions']['major'] and not quality['regressions']['mate_loss']
    assert digest(ROOT.parent/'chessity-agent.zip')==prep['selected_sha256']
    package=screen/'challenger.zip'
    assert digest(package)==prep['package_sha256'];archive_matches(package,ROOT/prep['candidate'])
    validation=json.loads((screen/'validation.json').read_text())
    assert validation['status']=='complete' and validation['sha256']==prep['package_sha256']
    assert validation['init_ms']<90000 and validation['legal_calls']==2
    assert all(v=='blocked' for v in validation['read_only_checks'].values())
    games={};reviews=[];sources={}
    for item in state['matches']:
        assert item['label'] not in games, 'Duplicate match label'
        path=ROOT/item['result_path'];assert digest(path)==item['sha256']
        result=audit_feedback(path);games[item['label']]=result['games'];sources[str(path.relative_to(ROOT))]=digest(path)
        assert result['config']['base_ms']==120000 and result['config']['increment_ms']==500
        feedback=feedback_path(path.parent/'postgame-feedback')
        for game in result['games']:
            _,identity=normalise_game(game)
            marker=json.loads((feedback/'completed'/(identity['game_key']+'.json')).read_text())
            review=json.loads((feedback/marker['review']).read_text())
            reviews.append(dict(match=item['label'],game_key=identity['game_key'],own_moves=review['own_moves'],
                rewarded=review['rewarded'],penalised=review['penalised'],
                correction_phases=dict(Counter('endgame' if 'endgame' in r['tags'] else 'opening' if 'opening' in r['tags'] else 'middlegame'
                    for r in review['rows'] if r['reward'] is not None and r['reward']<0))))
    assert all_required_pass(games)
    assert ('rated2800' in games)==qualifies_2800(games['rated2600'])
    for path in (screen/'state.json',screen/'preparation.json',screen/'validation.json'):
        sources[str(path.relative_to(ROOT))]=digest(path)
    groups={label:summarise(rows) for label,rows in games.items()}
    groups['versus56']=summarise(games['versus56-c42']+games['versus56-e04']+games['versus56-b33'])
    highest=max((int(label.removeprefix('rated')) for label,rows in games.items() if label.startswith('rated') and any(g['score']==1 for g in rows)),default=None)
    result=dict(status='complete',eligible=True,created_utc=datetime.now(timezone.utc).isoformat(),
        candidate=prep['candidate'],package=str(package.relative_to(ROOT)),sha256=digest(package),
        previous_sha256=prep['selected_sha256'],files=prep['files'],source_sha256=sources,groups=groups,reviews=reviews,
        reviewed_moves=sum(r['own_moves'] for r in reviews),positive_labels=sum(r['rewarded'] for r in reviews),
        negative_labels=sum(r['penalised'] for r in reviews),highest_nominal_win=highest,calibrated_elo=None,
        validation=validation,site_submission='not verified by this audit',
        scope='Strict short practical gate against exactv1.56; no universal strength or calibrated Elo claim.')
    save(out,result);print(json.dumps({k:result[k] for k in ('eligible','groups','reviewed_moves','highest_nominal_win')}),flush=True)

if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--screen',type=Path,required=True)
    args=parser.parse_args();audit(args.screen)
