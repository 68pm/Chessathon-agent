"""One canonical runner request without the earlier diagnostic launch wrapper."""
import argparse
import json
import time
from pathlib import Path

import chess

from harness.sandbox import RUNNER, AgentFailure, local
from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import manifest
from scripts.overnight_capacity import wait_for_capacity
from scripts.overnight_resources import memory


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=False)
    frozen = manifest(args.candidate)
    capacity = wait_for_capacity(args.out / 'capacity.json')
    agent = local(args.candidate)
    record = dict(status='running', passed=False, candidate=str(args.candidate),
        files=frozen, source_sha256=sha256(__file__), runner_sha256=sha256(RUNNER),
        capacity_before=capacity, command=agent.command, periodic_stack_dumps=False,
        diagnostic_launch_wrapper=False, initialization_budget_seconds=90,
        move_clock_ms=120000, scope='One canonical harness request, not a match, rating, repeated strength attempt or proof of the cause of earlier crashes.')
    save_json(args.out / 'report.json', record)
    started = time.perf_counter()
    stage = 'initialization'
    try:
        agent.start(90)
        record['init_seconds'] = time.perf_counter() - started
        stage = 'first_response'
        board = chess.Board('r1bqkb1r/ppp2ppp/5n2/n2Pp1N1/2B5/8/PPPP1PPP/RNBQK2R w KQkq - 1 6')
        tick = time.perf_counter()
        answer = agent.move(board.fen(), 120000)
        record['response_seconds'] = time.perf_counter() - tick
        record['uci'] = answer
        record['legal'] = chess.Move.from_uci(answer) in board.legal_moves
        record['passed'] = record['legal'] and record['init_seconds'] < 90 and record['response_seconds'] < 120
    except (AgentFailure, ValueError) as error:
        record.update(error=repr(error), failed_stage=stage)
    finally:
        record['exit_code_before_stop'] = agent._process.poll() if agent._process is not None else None
        agent.stop()
        record.update(status='complete', total_seconds=time.perf_counter() - started,
            memory_after=memory())
        assert manifest(args.candidate) == frozen
        (args.out / 'stderr.log').write_text(agent.stderr_tail[-16000:], encoding='utf-8')
        save_json(args.out / 'report.json', record)
    print(json.dumps(record), flush=True)


if __name__ == '__main__':
    main()
