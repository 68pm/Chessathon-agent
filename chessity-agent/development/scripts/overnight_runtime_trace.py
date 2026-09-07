"""Bounded startup/first-move diagnosis; no changes to the frozen agent."""
import argparse
import faulthandler
import hashlib
import json
import os
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def child(candidate):
    started, cpu = time.perf_counter(),time.process_time()
    def record(stage, **details):
        print(json.dumps(dict(stage=stage,wall_seconds=time.perf_counter()-started,
            cpu_seconds=time.process_time()-cpu,**details)),flush=True)
    faulthandler.enable()
    faulthandler.dump_traceback_later(30,repeat=True)
    record('before_import')
    sys.path.insert(0,str(candidate.resolve()))
    import chess

    import agent
    from engine import compiled_core as core
    record('initialized',root_signatures=[str(v) for v in core.root_iteration.signatures])
    search_run = agent._search.run
    def traced_search(*args, **kwargs):
        record('before_search',seconds=args[1],soft=args[2])
        result = search_run(*args,**kwargs)
        record('after_search',depth=result.depth,nodes=result.nodes,elapsed=result.elapsed)
        return result
    agent._search.run = traced_search
    if agent._search.policy is not None:
        policy = agent._search.policy.bonuses
        def traced_policy(*args, **kwargs):
            record('before_policy')
            result = policy(*args,**kwargs)
            record('after_policy')
            return result
        agent._search.policy.bonuses = traced_policy
    for label,fen in [('C58','r1bqkb1r/ppp2ppp/5n2/n2Pp1N1/2B5/8/PPPP1PPP/RNBQK2R w KQkq - 1 6'),
                      ('start',chess.STARTING_FEN)]:
        agent._last = None
        record('before_move',case=label)
        move = agent.get_move(fen,120000)
        assert chess.Move.from_uci(move) in chess.Board(fen).legal_moves
        record('after_move',case=label,uci=move,
            root_signatures=[str(v) for v in core.root_iteration.signatures])
    faulthandler.cancel_dump_traceback_later()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate',type=Path,default=ROOT / 'candidates/compiled-qsearch-endgames-v1')
    parser.add_argument('--out',type=Path,default=ROOT / 'runs/improvement-loop-20260907/overnight-runtime-trace-01')
    parser.add_argument('--child',action='store_true')
    args = parser.parse_args()
    if args.child:
        child(args.candidate)
        return
    # This diagnostic must not run beside either the timed games or cycle17.
    for name in ['overnight-serial-controller','overnight-aspiration-controller']:
        state = json.loads((ROOT / 'runs/improvement-loop-20260907' / name / 'controller.json').read_text())
        assert state['status'] in ['complete','failed'], 'Wait for existing compute first.'
    assert not any((ROOT / flag).exists() for flag in ['STOP_TRAINING','STOP_BENCHMARK'])
    args.out.mkdir(parents=True,exist_ok=False)
    def digest(path):
        return hashlib.sha256(path.read_bytes()).hexdigest()
    files = {p.relative_to(args.candidate).as_posix():digest(p) for p in args.candidate.rglob('*')
        if p.is_file() and '__pycache__' not in p.parts and p.suffix != '.pyc'}
    context = dict(status='running',candidate=str(args.candidate),files=files,
        trace_source_sha256=digest(Path(__file__)),timeout_seconds=180,
        scope='Diagnostic only: stack dumps and wall/CPU time, not competition validation or rating evidence. The watchdog may exceed the competition init budget; report measured90s violations separately.')
    path = args.out / 'context.json'
    path.write_text(json.dumps(context,indent=2)+'\n')
    try:
        with (args.out / 'stages.jsonl').open('w') as stdout, (args.out / 'stacks.log').open('w') as stderr:
            process = subprocess.Popen([sys.executable,'-m','scripts.overnight_runtime_trace','--child',
                '--candidate',str(args.candidate)],cwd=ROOT,stdout=stdout,stderr=stderr,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0)
            context['child_pid'] = process.pid
            path.write_text(json.dumps(context,indent=2)+'\n')
            try:
                returncode = process.wait(timeout=180)
            except subprocess.TimeoutExpired:
                # On Windows the venv launcher may have a Python child. Stop only
                # this owned tree before closing the diagnostic's pipe handles.
                if os.name == 'nt':
                    subprocess.run(['taskkill','/PID',str(process.pid),'/T','/F'],
                        stdout=stderr,stderr=stderr,timeout=20,
                        creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    process.kill()
                process.wait(timeout=20)
                raise
        context.update(status='complete' if returncode == 0 else 'failed',exit_code=returncode)
    except subprocess.TimeoutExpired:
        context.update(status='timed_out',error='180s diagnostic watchdog; inspect the last stage and stack dumps.')
    finally:
        path.write_text(json.dumps(context,indent=2)+'\n')
    print(json.dumps(context),flush=True)


if __name__ == '__main__':
    main()
