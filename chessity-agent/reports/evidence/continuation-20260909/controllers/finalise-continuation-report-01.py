"""Save a compact honest conclusion and convenient copies of the three reviewed games."""
import hashlib
import io
import json
import shutil
from datetime import datetime,timezone
from pathlib import Path
import chess
import chess.pgn

workspace=Path(__file__).resolve().parent.parent
root=workspace/'outputs/chess-agent';run=root/'runs/continuation-20260909'
out=workspace/'outputs/chessity-recent-games-20260909'
assert not out.exists()

def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_text(encoding='utf-8'))
def longpath(p):return Path('\\\\?\\'+str(p.resolve()))

selected=read(root.parent/'chessity-agent-version.json')
assert selected['version']=='v1.56'
assert sha(root.parent/'chessity-agent.zip')==sha(root.parent/'chessity-agent-v1.56.zip')==selected['sha256']
assert not (run/'curriculum-value-runtime-01').exists()
assert not (run/'gm-colour-values-01/reserved_test.json').exists()
for folder in ('field-review-supervisor-01','legal-buffers-supervisor-01','student-descendants-supervisor-01',
    'curriculum-value-supervisor-01','curriculum-value-supervisor-02','curriculum-value-supervisor-03'):
    assert read(run/folder/'supervisor.json')['status']=='complete'
turning=read(run/'petroff-turning-point-02/state.json')
assert turning['status']=='complete' and turning['grade']['label']=='major_mistake'
out.mkdir()
game_rows=[]
own_records=read(run/'field-review-01/own-games.json')['games']
for p in (run/'field-review-01/own-review/games').glob('*/review.json'):
    doc=read(longpath(p));identity=doc['identity']['game'];assert doc['status']=='complete'
    record=next(r for r in own_records if str(r['source_game_id'])==identity['source_game_id'])
    number=record['id'];stem=f'round-{number}'
    source=longpath(p.parent/'original.pgn');original=out/(stem+'-original.pgn');shutil.copyfile(source,original)
    assert sha(source)==sha(original)
    annotated_source=longpath(p.parent/'annotated.pgn')
    with annotated_source.open(encoding='utf-8') as stream:game=chess.pgn.read_game(stream)
    assert game and not game.errors
    before=[m.uci() for m in game.mainline_moves()]
    if number==83:
        board=game.board();found=0
        for node in game.mainline():
            if not board.turn and board.fullmove_number==23:
                assert board.san(node.move)=='Re6'
                node.comment += (' Supplemental deeper review at2.56M/10.24M nodes: '
                    'Re6 loses371/344cp relative to the best searched defence. '
                    'White has24.a5. Best alternatives differ (Rc7 / Be2+), so no single policy target was forced.')
                found+=1
            board.push(node.move)
        assert found==1
    annotated=out/(stem+'-annotated.pgn');annotated.write_text(str(game)+'\n',encoding='utf-8',newline='\n')
    check=chess.pgn.read_game(io.StringIO(annotated.read_text(encoding='utf-8')))
    assert not check.errors and [m.uci() for m in check.mainline_moves()]==before
    assert check.headers['Result']==game.headers['Result']
    game_rows.append(dict(round=number,opponent=identity['opponent'],candidate_white=identity['candidate_white'],
        score=identity['score'],source_game_id=identity['source_game_id'],submission_sha256=None,
        moves=len(doc['rows']),positive=sum((r.get('reward') or 0)>0 for r in doc['rows']),
        negative=sum((r.get('reward') or 0)<0 for r in doc['rows']),
        annotated_file=annotated.name,annotated_sha256=sha(annotated),original_file=original.name,original_sha256=sha(original)))
assert sorted(r['round'] for r in game_rows)==[81,82,83]
fits=[]
for n in (1,2,3):
    folder=run/f'curriculum-value-{n:02d}';state=read(folder/'state.json')
    epoch=next(r for r in state['epochs'] if r['epoch']==state['selected_epoch'])
    metric=epoch['metrics'][str(state['value_blend'])]
    if n==1:
        black=read(run/'curriculum-black-check-01/state.json')
        gate=dict(white=dict(n=state['reserved_eligible'],before_mae_cp=state['reserved_before_mae_cp'],
            after_mae_cp=state['reserved_after_mae_cp']),black={k:black[k] for k in
                ('eligible','before_mae_cp','after_mae_cp','major_before','major_after')})
        assert state['passed'] and not black['passed']
    else:
        gate=read(folder/'exposed-development.json')['cohorts'];assert not state['passed']
    fits.append(dict(trial=n,completed=True,qualified_for_runtime=False,selected=False,model_sha256=state['model_sha256'],
        selected_epoch=state['selected_epoch'],value_blend=state['value_blend'],
        broad_before=state['broad_before'],broad_after=state['broad_after'],
        development_metrics=metric,colour_gate=gate,
        explanation='Initial White-position pass superseded by separate failed Black gate' if n==1 else state['decision']))
speed=read(run/'legal-buffers-01/state.json')
assert speed['status']=='complete' and not speed['passed']
sources=[run/'field-review-01/state.json',run/'legal-buffers-01/state.json',
    run/'student-descendants-01/teacher.json',run/'student-value-diagnosis-01/diagnosis.json',
    run/'petroff-turning-point-02/state.json',run/'opening-curriculum-03/state.json',
    run/'gm-colour-values-01/preparation.json',*[run/f'curriculum-value-{n:02d}/state.json' for n in (1,2,3)]]
summary=dict(status='complete',completed_utc=datetime.now(timezone.utc).isoformat(),
    selected_version=selected['version'],selected_sha256=selected['sha256'],
    selected_zip_size_bytes=(root.parent/'chessity-agent.zip').stat().st_size,
    own_games=sorted(game_rows,key=lambda r:r['round'],reverse=True),leader_reviewed_games=3,
    own_primary_review=dict(moves=256,positive=173,negative=21,negative_phases=dict(opening=1,middlegame=14,endgame=6)),
    supplemental_major_mistake=dict(round=83,move='23...Re6',reply='24.a5',regret_cp=turning['grade']['regret_cp'],
        policy_target=None,reason='Bad move verified, best alternative differs between budgets.'),
    speed_trial=dict(passed=False,aggregate_cpu_speedup=speed['aggregate_cpu_speedup'],minimum_required=1.05),
    value_trials=fits,training_games=14,exposed_reserved_games=3,new_unlabelled_reserved_games=3,
    gm_families=dict(Petroff=4,Catalan=5,Italian=6,Closed_Sicilian=2),
    new_competitive_benchmark_games=0,new_release_created=False,site_upload_performed=False,
    browser_state='Existing missing-kernel-assets blocker; no successful browser recovery or active version verification.',
    publication_note='Only code, reports and public competition evidence are publishable here; raw TWIC PGNs and labelled GM histories stay local.',
    automation_status='PAUSED; no new scheduler or continuing worker',
    source_sha256={str(p.relative_to(root)):sha(p) for p in sources})
target=run/'final-status.json';assert not target.exists()
target.write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
(out/'analysis-summary.json').write_text(json.dumps(summary,indent=2)+'\n',encoding='utf-8')
print(json.dumps(dict(status='complete',games=len(game_rows),selected=selected['version'],new_release=False)),flush=True)
