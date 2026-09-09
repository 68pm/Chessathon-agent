"""Collect bounded exact-table student continuations, then independently label them."""
import argparse
import hashlib
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, check_stop, digest, manifest, save

OUT = RUN / 'student-descendants-01'


def search_score(score, complete):
    """Keep search mate-band scores separate from finite centipawn diagnostics."""
    value = int(score) if complete else None
    mate_band = value is not None and abs(value) >= 29000
    return dict(complete=bool(complete), engine_score=value, mate_band=mate_band,
                score_stm_cp=value if value is not None and not mate_band else None)


def restore(row):
    import chess

    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.fen() == row['fen'] and board.is_valid()
    return board


def prepare():
    from scripts.feedback_matches_windows import feedback_path
    from scripts.overnight_archive_challenge import archive_matches

    check_stop()
    assert not OUT.exists()
    screen = json.loads((RUN / 'pawn-bitboards-screen-01/state.json').read_text())
    assert screen['status'] == 'complete' and all(r['status'] == 'complete' for r in screen['stages'])
    metadata_path = ROOT.parent / 'chessity-agent-version.json'
    metadata = json.loads(metadata_path.read_text())
    candidate = ROOT / metadata['source_version']
    assert candidate in (RUN / 'pawn-extrema-01/prototype', RUN / 'pawn-bitboards-01/prototype')
    archive_matches(ROOT.parent / 'chessity-agent.zip', candidate)
    assert digest(ROOT.parent / 'chessity-agent.zip') == metadata['sha256']
    source = RUN / 'defence-trace-02/preparation.json'
    wanted = {'rated2400-True-24', 'rated2600-False-23', 'field-own-33', 'field-own-44'}
    roots = [r for r in json.loads(source.read_text())['roots'] if r['id'] in wanted]
    assert {r['id'] for r in roots} == wanted
    recent = next(r for r in screen['matches'] if r['label'] == 'rated2400')
    result_path = ROOT / recent['result_path']
    assert digest(result_path) == recent['sha256']
    recent_sources = [result_path]
    feedback = feedback_path(result_path.parent / 'postgame-feedback')
    for marker in sorted((feedback / 'completed').glob('*.json')):
        completed = json.loads(marker.read_text())
        review_path = feedback / completed['review']
        review = json.loads(review_path.read_text())
        white = review['identity']['game']['candidate_white']
        wanted_move = 35 if white else 15
        rows = [r for r in review['rows'] if r['fullmove'] == wanted_move
                and r['reward'] is not None and r['reward'] < 0 and r['policy_target']]
        assert len(rows) == 1
        roots.append(dict(id=f'bitboards2400-{white}-{wanted_move}', **rows[0]))
        recent_sources += [marker, review_path]
    assert len(roots) == 6
    for row in roots:
        assert row['played'] != row['policy_target']
        restore(row)
    paths = [Path(__file__), ROOT / 'docs/DAYTIME_STUDENT_DESCENDANTS_PLAN_20260909.md',
        ROOT / 'scripts/daytime_common.py', ROOT / 'scripts/daytime_student_value_diagnosis.py',
        ROOT / 'training/game_feedback.py',
        ROOT / 'training/daytime_small_value.py', ROOT / 'scripts/improvement_audit.py',
        source, RUN / 'defence-trace-02/state.json',
        RUN / 'pawn-bitboards-screen-01/state.json', metadata_path, *recent_sources]
    save(OUT / 'preparation.json', dict(candidate=str(candidate.relative_to(ROOT)), files=manifest(candidate),
        selected_version=metadata['version'], selected_sha256=metadata['sha256'], roots=roots,
        sources={str(p): digest(p) for p in paths}, child_depth=7, branch_nodes=2000000,
        branch_seconds=5.0, quiescence_nodes=100000, quiescence_seconds=2.0, max_leaves=72,
        teacher_budgets=[80000,320000], max_teacher_nodes=28800000,
        scope='Exposed diagnostic descendants; each leaf requires independent value labels. No automatic fit or validation claim.'))
    print('Prepared six diagnostic roots and twelve branches', flush=True)


def verify(prep):
    assert all(digest(Path(p)) == h for p,h in prep['sources'].items())
    assert manifest(ROOT / prep['candidate']) == prep['files']


def student():
    from scripts.overnight_capacity import wait_for_capacity

    check_stop()
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    path = OUT / 'student.json'
    assert not path.exists()
    wait_for_capacity(OUT / 'student-capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    state = dict(status='initializing', branches=[], leaves=[])
    save(path, state)
    core, original, search, original_policy = None, None, None, None
    try:
        for name in list(sys.modules):
            if name == 'engine' or name.startswith('engine.'):
                del sys.modules[name]
        candidate = ROOT / prep['candidate']
        sys.path.insert(0, str(candidate))
        tick = time.perf_counter()
        import numpy as np

        import agent

        driver = sys.modules['engine.compiled_driver']
        core, search = driver.core, agent._search
        assert search.blend == 0.0, 'This diagnosis is declared for the selected classical evaluator.'
        assert Path(core.__file__).resolve() == candidate / 'engine/compiled_core.py'
        state['init_seconds'] = time.perf_counter() - tick
        assert state['init_seconds'] < 90
        original = core.root_iteration
        signatures = tuple(map(str, original.signatures))
        original_policy = search.policy
        search.policy = None  # Isolate forced-branch position values from root preference.
        forced, root_context = None, 0
        leaves = {}

        def restricted(*args):
            nonlocal root_context
            indices = [i for i,m in enumerate(args[4]) if driver.decode(int(m)).uci() == forced]
            assert len(indices) == 1
            modified = list(args)
            modified[4], modified[5] = args[4][indices].copy(), args[5][indices].copy()
            root_context = sum(map(int,args[6][max(0,args[7]-args[1][3]-1):args[7]])) & ((1 << 64)-1)
            return original(*modified)

        core.root_iteration = restricted

        def clear():
            for key in ('ttkey','ttcontext','ttdata','killers','history'):
                getattr(search,key).fill(0)

        def add(board, row, origin):
            history = [m.uci() for m in board.move_stack]
            identity = hashlib.sha256(json.dumps([row['id'],board.root().fen(),history]).encode()).hexdigest()
            if identity not in leaves:
                pieces, position = driver.arrays(board)
                leaves[identity] = dict(id=identity, root_id=row['id'], root_white=restore(row).turn,
                    start_fen=board.root().fen(), history=history, fen=board.fen(), origins=[],
                    static_stm_cp=int(core.classical(pieces,position,search.conversion)),
                    terminal=board.is_game_over(claim_draw=True))
            leaves[identity]['origins'].append(origin)
            assert len(leaves) <= prep['max_leaves']
            return identity

        def advance(board, move, context):
            old_rights = board.castling_rights
            board.push(move)
            key = int(core.position_hash(*driver.arrays(board)))
            return key if board.halfmove_clock == 0 or board.castling_rights != old_rights else (context+key) & ((1 << 64)-1)

        for row in prep['roots']:
            for branch, forced in [('played',row['played']),('defence',row['policy_target'])]:
                check_stop()
                board = restore(row)
                saved_history = list(board.move_stack)
                clear()
                response = search.run(board, seconds=prep['branch_seconds'], soft=prep['branch_seconds'],
                    max_depth=prep['child_depth']+1, max_nodes=prep['branch_nodes'])
                assert board.fen() == row['fen'] and list(board.move_stack) == saved_history
                assert response.elapsed <= prep['branch_seconds']+.3 and response.nodes <= prep['branch_nodes']
                assert tuple(map(str,original.signatures)) == signatures
                record = dict(root_id=row['id'],branch=branch,forced=forced,depth=response.depth,
                    nodes=response.nodes,seconds=response.elapsed,score_root=response.score,
                    full_requested_depth=response.depth==prep['child_depth']+1,entries=[],leaf_ids=[])
                if response.depth:
                    import chess

                    assert response.move.uci() == forced
                    context = advance(board,chess.Move.from_uci(forced),root_context)
                    remaining, plies = response.depth-1, 1
                    reason = 'quiescence_boundary'
                    while remaining > 0:
                        if board.is_game_over(claim_draw=True):
                            reason = 'terminal_or_claimable_draw'
                            break
                        key = int(core.position_hash(*driver.arrays(board)))
                        slot = key & (len(search.ttkey)-1)
                        entry = search.ttdata[slot]
                        if not (int(search.ttkey[slot])==key and int(search.ttcontext[slot])==context
                                and entry[4]==board.halfmove_clock and entry[0]>=remaining and entry[2]==0):
                            reason = 'missing_or_nonexact_transposition'
                            break
                        move = driver.decode(int(entry[3])) if entry[3] else None
                        if move not in board.legal_moves:
                            reason = 'missing_or_illegal_table_move'
                            break
                        record['entries'].append(dict(ply=plies,depth=int(entry[0]),bound=int(entry[2]),
                            uci=move.uci(),san=board.san(move),fen=board.fen()))
                        context = advance(board,move,context)
                        remaining -= 1
                        plies += 1
                        if plies in (3,5,7):
                            record['leaf_ids'].append(add(board,row,dict(kind='student-intermediate',branch=branch,plies=plies)))
                    record['leaf_ids'].append(add(board,row,dict(kind='student-endpoint',branch=branch,plies=plies,stop=reason)))
                    record['stop'] = reason
                state['branches'].append(record)
                state['leaves'] = list(leaves.values())
                save(path,state)
        for row in prep['roots']:
            for branch in ('best','played'):
                for length in (4,8):
                    line = row['labels'][-1][branch]['pv'][:length]
                    if len(line) != length:
                        continue
                    board = restore(row)
                    for move in line:
                        board.push_uci(move)
                    add(board,row,dict(kind='teacher-counterfactual',branch=branch,plies=length))
        core.root_iteration = original
        search.policy = original_policy
        for leaf in leaves.values():
            check_stop()
            if leaf['terminal']:
                continue
            board = restore(leaf)
            pieces, position = driver.arrays(board)
            saved = pieces.copy(), position.copy()
            clear()
            replay = board.copy(stack=True)
            past = []
            for _ in range(min(board.halfmove_clock,len(board.move_stack))+1):
                past.append(int(core.position_hash(*driver.arrays(replay))))
                if not replay.move_stack:
                    break
                replay.pop()
            past.reverse()
            hashes = np.zeros(800,dtype=np.uint64)
            hashes[:len(past)] = past
            context = np.uint64(sum(past) & ((1 << 64)-1))
            accumulator = core.build_accumulator(pieces,search.weights,search.bias)
            saved_accumulator = accumulator.copy()
            control = np.array([0,0,prep['quiescence_nodes']],dtype=np.int64)
            sigs = tuple(map(str,core.search.signatures))
            tick = time.perf_counter()
            score = core.search(pieces,position,0,-31000,31000,0,0,hashes,len(past),context,
                search.ttkey,search.ttcontext,search.ttdata,search.killers,search.history,control,
                tick+prep['quiescence_seconds'],search.weights,search.bias,search.output,search.blend,
                search.conversion,search.reductions,accumulator)
            elapsed = time.perf_counter()-tick
            assert tuple(map(str,core.search.signatures))==sigs
            assert np.array_equal(pieces,saved[0]) and np.array_equal(position,saved[1])
            assert np.array_equal(accumulator,saved_accumulator)
            assert list(map(int,hashes[:len(past)]))==past
            assert elapsed <= prep['quiescence_seconds']+.3 and control[0] <= prep['quiescence_nodes']
            leaf['quiescence'] = dict(**search_score(score,not bool(control[1])),
                nodes=int(control[0]),seconds=elapsed)
            state['leaves'] = list(leaves.values())
            save(path,state)
        assert len(state['branches']) == 12
        state.update(status='complete',leaves=list(leaves.values()))
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        if core is not None and original is not None:
            core.root_iteration = original
        if search is not None:
            search.policy = original_policy
        state['frozen_candidate'] = manifest(ROOT / prep['candidate']) == prep['files']
        if not state['frozen_candidate']:
            state.update(status='failed',error='Candidate source changed during diagnosis')
        state['finished_utc'] = datetime.now(timezone.utc).isoformat()
        save(path,state)
    assert state['status'] == 'complete'
    print(json.dumps(dict(status=state['status'],branches=len(state['branches']),leaves=len(state['leaves']))),flush=True)


def teacher():
    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback
    from training.daytime_small_value import active

    check_stop()
    prep = json.loads((OUT / 'preparation.json').read_text())
    verify(prep)
    source_path = OUT / 'student.json'
    source = json.loads(source_path.read_text())
    assert source['status']=='complete' and source['frozen_candidate']
    assert len(source['leaves']) <= prep['max_leaves']
    path = OUT / 'teacher.json'
    assert not path.exists()
    wait_for_capacity(OUT / 'teacher-capacity.json',minimum_memory_mb=1400,wait_seconds=120)
    game_feedback.stop_check = check_stop
    engine = game_feedback.CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1',OUT)
    state = dict(status='running',student_sha256=digest(source_path),rows=[],automatic_fitting=False)
    save(path,state)
    try:
        for leaf in source['leaves']:
            check_stop()
            board = restore(leaf)
            row = dict(**leaf,eligible=False)
            if not leaf['terminal']:
                labels = [engine.analyse(board,b) for b in prep['teacher_budgets']]
                cp = [v['cp'] for v in labels]
                finite = all(v is not None for v in cp) and all(v['mate'] is None for v in labels)
                stable = finite and max(map(abs,cp))<=1500 and abs(cp[0]-cp[1])<=100
                eligible = stable and active(board)
                row.update(teacher=labels,eligible=eligible,target_stm_cp=sum(cp)/2 if eligible else None)
                if finite:
                    row['static_minus_teacher_cp'] = [leaf['static_stm_cp']-v for v in cp]
                    qscore = leaf.get('quiescence',{}).get('score_stm_cp')
                    row['quiescence_minus_teacher_cp'] = [qscore-v for v in cp] if qscore is not None else None
            state['rows'].append(row)
            save(path,state)
        state.update(status='complete',eligible=sum(r['eligible'] for r in state['rows']))
    except BaseException as error:
        state.update(status='failed',error=repr(error))
        raise
    finally:
        engine.close()
        state.update(requested_teacher_nodes=engine.requested_nodes,finished_utc=datetime.now(timezone.utc).isoformat())
        assert engine.requested_nodes<=prep['max_teacher_nodes']
        save(path,state)
    print(json.dumps({k:v for k,v in state.items() if k!='rows'}),flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--mode',required=True,choices=('prepare','student','teacher'))
    args = parser.parse_args()
    {'prepare':prepare,'student':student,'teacher':teacher}[args.mode]()
