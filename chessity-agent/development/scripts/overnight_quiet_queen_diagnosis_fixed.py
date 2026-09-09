"""Bounded frozen-search diagnosis of the D65 quiet queen threat; no fitting."""

import json
import sys
import subprocess
import time
from pathlib import Path


from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save

OUT = ROOT / 'runs/overnight-20260909/quiet-queen-diagnosis-02'


def run():
    import chess

    check_stop()
    assert not OUT.exists()
    source = ROOT / 'runs/overnight-20260909/guarded-leaf-02'
    preparation = json.loads((source / 'preparation.json').read_text(encoding='utf-8'))
    candidate = ROOT / preparation['candidates']['prototype']
    assert manifest(candidate) == preparation['candidate_files']['prototype']
    root = next(r for r in preparation['roots'] if r['id'] == 'd65-game-2-move-35')
    OUT.mkdir()
    report = dict(status='running', source_sha256=digest(source / 'preparation.json'),
        script_sha256=digest(Path(__file__)), candidate=str(candidate.relative_to(ROOT)), rows=[])
    save(OUT / 'state.json', report)
    subprocess.run([sys.executable, '-m', 'scripts.overnight_capacity', '--out', str(OUT / 'capacity.json'), '--minimum-memory-mb', '1400', '--wait-seconds', '120'], check=True, capture_output=True)
    tick = time.monotonic()
    sys.path.insert(0, str(candidate))
    import agent
    from engine import compiled_core as core
    from engine.compiled_driver import arrays

    report['init_seconds'] = time.monotonic() - tick
    assert report['init_seconds'] < 90
    try:
        for line in ([], ['f4d4'], ['f4d4', 'c6b6'], ['f4d6']):
            board = chess.Board(root['start_fen'])
            for uci in root['history']:
                board.push_uci(uci)
            san = []
            for uci in line:
                san.append(board.san(chess.Move.from_uci(uci)))
                board.push_uci(uci)
            for max_depth in (3, 5):
                check_stop()
                for name in ('ttkey', 'ttcontext', 'ttdata', 'killers', 'history'):
                    getattr(agent._search, name).fill(0)
                before, history = board.fen(), board.move_stack.copy()
                result = agent._search.run(board, seconds=3., soft=3., max_depth=max_depth, max_nodes=500000)
                assert board.fen() == before and board.move_stack == history
                pieces, state = arrays(board)
                acc = core.build_accumulator(pieces, agent._search.weights, agent._search.bias)
                report['rows'].append(dict(line=line, san=san, fen=before, max_depth=max_depth,
                    chosen=result.move.uci(), chosen_san=board.san(result.move), score=result.score,
                    depth=result.depth, nodes=result.nodes, seconds=result.elapsed,
                    static_classical=core.classical(pieces, state),
                    static_guarded=core.evaluate_accumulator(pieces, state, agent._search.output,
                        agent._search.rule_weights, agent._search.blend, False, acc)))
                save(OUT / 'state.json', report)
        report.update(status='complete', scope='Exposed development continuation diagnosis; no model or search change, teacher query, game, release or Elo claim.')
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        report['frozen_candidate'] = manifest(candidate) == preparation['candidate_files']['prototype']
        save(OUT / 'state.json', report)
        print(json.dumps(report), flush=True)


if __name__ == '__main__':
    run()
