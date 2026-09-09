"""Check the selected release on five public turning points before behavioural edits."""
import argparse
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save

OUT = RUN/'field-selected-probe-01'


def restore(row):
    import chess

    board = chess.Board(row['start_fen'])
    for move in row['history']:
        board.push_uci(move)
    assert board.fen() == row['fen'] and board.is_valid()
    return board


def verify(prep):
    assert all(digest(Path(p)) == h for p,h in prep['sources'].items())
    assert manifest(ROOT/prep['candidate']) == prep['files']


def prepare():
    from scripts.overnight_archive_challenge import archive_matches

    check_stop()
    assert not OUT.exists(), 'Preserve consumed probes.'
    supervisor = RUN/'fast-legal-screen-supervisor-01/supervisor.json'
    screen = RUN/'fast-legal-screen-01/state.json'
    assert json.loads(supervisor.read_text())['status'] == 'complete'
    assert json.loads(screen.read_text())['status'] == 'complete'
    metadata_path = ROOT.parent/'chessity-agent-version.json'
    metadata = json.loads(metadata_path.read_text())
    candidate = ROOT/metadata['source_version']
    assert digest(ROOT.parent/'chessity-agent.zip') == metadata['sha256']
    archive_matches(ROOT.parent/'chessity-agent.zip',candidate)
    diagnosis_path = RUN/'field-diagnosis-01/diagnosis.json'
    diagnosis = json.loads(diagnosis_path.read_text())
    assert diagnosis['status'] == 'complete'
    wanted = {
        ('own','chessathon:ed1f0087-21bb-44ac-99e2-dd31c7a4d2ba'):[10,11,13],
        ('own','chessathon:9cdd05d7-1511-4355-8b64-d773743f0be5'):[18],
        ('leader','chessathon:5d694849-41bb-4f6b-8eaf-a37d95cdd515'):[130],
    }
    roots = []
    for game in diagnosis['games']:
        key = game['label'],game['identity']['source_game_id']
        for row in game['negatives']:
            if row['fullmove'] not in wanted.get(key,[]):
                continue
            assert row['policy_target'] and row['policy_target'] != row['played']
            restore(row)
            roots.append(dict(id=f'{key[0]}-{key[1].split(":")[1]}-{row["fullmove"]}',
                source_game_id=key[1], **row))
    assert len(roots)==5
    sources = [Path(__file__), ROOT/'docs/DAYTIME_FIELD_SELECTED_PROBE_20260909.md',
        ROOT/'scripts/daytime_common.py', ROOT/'training/game_feedback.py',
        supervisor,screen,metadata_path,diagnosis_path]
    save(OUT/'preparation.json',dict(candidate=str(candidate.relative_to(ROOT)),
        selected_version=metadata['version'],selected_sha256=metadata['sha256'],
        files=manifest(candidate),sources={str(p):digest(p) for p in sources},roots=roots,
        seconds=[1.0,3.0],max_nodes=5000000,teacher_budgets=[80000,320000],
        scope='Five exposed public turning points, cold tables and retained root policy. No fit, promotion or Elo inference.'))
    print('Prepared five public turning points for '+metadata['version'],flush=True)


def student():
    from scripts.overnight_capacity import wait_for_capacity

    check_stop()
    prep = json.loads((OUT/'preparation.json').read_text())
    verify(prep)
    path = OUT/'student.json'
    assert not path.exists()
    wait_for_capacity(OUT/'student-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
    state = dict(status='initializing',rows=[])
    save(path,state)
    original,core = None,None
    try:
        # Capacity helpers can import the project engine before this frozen agent.
        for name in list(sys.modules):
            if name=='engine' or name.startswith('engine.'):
                del sys.modules[name]
        candidate = ROOT/prep['candidate']
        sys.path.insert(0,str(candidate))
        tick = time.perf_counter()
        import agent

        driver = sys.modules['engine.compiled_driver']
        core = driver.core
        assert Path(core.__file__).resolve() == candidate/'engine/compiled_core.py'
        state['init_seconds'] = time.perf_counter()-tick
        assert state['init_seconds']<90
        original = core.root_iteration
        signatures = tuple(map(str,original.signatures))
        trace = []

        def observed(*args):
            move,score,complete = original(*args)
            finite = bool(complete) and abs(score)<29000
            trace.append(dict(depth=int(args[2]),uci=driver.decode(int(move)).uci(),
                engine_score=int(score) if complete else None,
                cp=int(score) if finite else None,complete=bool(complete),
                nodes=int(args[13][0])))
            return move,score,complete

        core.root_iteration = observed
        state['status']='running'
        for root in prep['roots']:
            for seconds in prep['seconds']:
                check_stop()
                board = restore(root)
                history = list(board.move_stack)
                for key in ('ttkey','ttcontext','ttdata','killers','history'):
                    getattr(agent._search,key).fill(0)
                trace.clear()
                response = agent._search.run(board,seconds=seconds,soft=seconds,
                    max_depth=64,max_nodes=prep['max_nodes'])
                assert board.fen()==root['fen'] and list(board.move_stack)==history
                assert response.move in board.legal_moves
                assert response.elapsed<=seconds+.3 and response.nodes<=prep['max_nodes']
                assert tuple(map(str,original.signatures))==signatures
                state['rows'].append(dict(root_id=root['id'],requested_seconds=seconds,
                    uci=response.move.uci(),san=board.san(response.move),depth=response.depth,
                    engine_score=response.score,cp=response.score if abs(response.score)<29000 else None,
                    nodes=response.nodes,seconds=response.elapsed,iterations=list(trace)))
                save(path,state)
            print('Probed '+root['id'],flush=True)
        state['status']='complete'
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        if original is not None:
            core.root_iteration=original
        state.update(finished_utc=datetime.now(timezone.utc).isoformat(),
            frozen_candidate=manifest(ROOT/prep['candidate'])==prep['files'])
        if not state['frozen_candidate']:
            state.update(status='failed',error='Candidate source changed')
        save(path,state)


def teacher():
    import chess

    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback

    check_stop()
    prep=json.loads((OUT/'preparation.json').read_text())
    verify(prep)
    student_path=OUT/'student.json'
    student_state=json.loads(student_path.read_text())
    assert student_state['status']=='complete' and student_state['frozen_candidate']
    path=OUT/'diagnosis.json'
    assert not path.exists()
    wait_for_capacity(OUT/'teacher-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
    game_feedback.stop_check=check_stop
    engine=game_feedback.CachedTeacher(ROOT/'data/postgame-feedback/cache-v1',OUT)
    state=dict(status='running',selected_version=prep['selected_version'],
        selected_sha256=prep['selected_sha256'],student_sha256=digest(student_path),roots=[])
    save(path,state)
    try:
        for root in prep['roots']:
            check_stop()
            board=restore(root)
            choices=[r for r in student_state['rows'] if r['root_id']==root['id']]
            assert len(choices)==2
            best=[engine.analyse(board,b) for b in prep['teacher_budgets']]
            moves={r['uci'] for r in choices}|{root['played'],root['policy_target']}
            values={uci:[top if top['pv'][0]==uci else engine.analyse(board,b,chess.Move.from_uci(uci))
                for b,top in zip(prep['teacher_budgets'],best,strict=True)] for uci in sorted(moves)}
            reviews=[]
            for row in choices:
                value=values[row['uci']]
                regret=[max(0,a['cp']-b['cp']) if a['cp'] is not None and b['cp'] is not None else None
                    for a,b in zip(best,value,strict=True)]
                reviews.append(dict(**row,values=value,regret_cp=regret,
                    matches_verified_target=row['uci']==root['policy_target']))
            state['roots'].append(dict(id=root['id'],played=root['played'],
                earlier_target=root['policy_target'],best=best,values=values,choices=reviews))
            save(path,state)
        state.update(status='complete',scope='Exposed diagnostic positions; no strength estimate or automatic weight update.')
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        engine.close()
        state.update(requested_teacher_nodes=engine.requested_nodes,
            finished_utc=datetime.now(timezone.utc).isoformat(),
            frozen_candidate=manifest(ROOT/prep['candidate'])==prep['files'])
        if not state['frozen_candidate']:
            state.update(status='failed',error='Candidate source changed')
        save(path,state)
        print(json.dumps({k:v for k,v in state.items() if k!='roots'}),flush=True)


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','student','teacher'))
    args=parser.parse_args()
    {'prepare':prepare,'student':student,'teacher':teacher}[args.stage]()
