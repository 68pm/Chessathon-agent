"""Resumable first-error audit; analyse actual moves with their recorded history."""

import argparse
import json
from pathlib import Path

import chess
import chess.engine

from scripts.alien_rating_ladder import save_json, sha256
from scripts.magnus_benchmark import SF
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier

RUN = ROOT / 'runs/improvement-loop-20260907'


def evaluate(engine, board, nodes, move=None):
    engine.configure({'Clear Hash': None})
    options = {'root_moves': [move]} if move else {}
    # Single PV provides more useful search depth per teacher node than scoring every move.
    with engine.analysis(board, chess.engine.Limit(nodes=nodes), game=object(), **options) as stream:
        completed = None
        for info in stream:
            if ('score' in info and info.get('pv') and not info.get('lowerbound')
                    and not info.get('upperbound')):
                score = info['score'].pov(board.turn)
                completed = dict(cp=score.score(), mate=score.mate(), depth=info.get('depth'),
                                 pv=[m.uci() for m in info['pv']], nodes=info.get('nodes'))
    if completed is None:
        raise ValueError('No completed unbounded single-PV score')
    return completed


def review(report_path, out):
    source = json.loads(report_path.read_text())
    out.mkdir(parents=True, exist_ok=True)
    cache_path = out / 'positions.jsonl'
    cached = {r['id']: r for r in map(json.loads, cache_path.read_text().splitlines())} if cache_path.exists() else {}
    context = dict(source_sha256=sha256(report_path), teacher_sha256=sha256(SF),
                   source_code_sha256=sha256(__file__), screen_nodes=20000, verify_nodes=[80000, 320000])
    if (out / 'context.json').exists():
        assert json.loads((out / 'context.json').read_text()) == context
    else:
        save_json(out / 'context.json', context)
    teacher = Verifier(SF)
    rows = []
    try:
        for game in source['games']:
            board = chess.Board(game.get('start_fen', chess.STARTING_FEN))
            for uci in game['opening']:
                board.push_uci(uci)
            board = chess.Board(board.fen())
            for ply, record in enumerate(game['moves']):
                assert board.fen() == record['fen']
                move = chess.Move.from_uci(record['uci'])
                if record['white'] == game['candidate_white']:
                    uid = f"game-{game['id']:03}-ply-{ply:03}"
                    if uid not in cached:
                        best = evaluate(teacher.engine, board, 20000)
                        played = best if best['pv'][0] == move.uci() else evaluate(teacher.engine, board, 20000, move)
                        suspicious = best['mate'] is not None or played['mate'] is not None or best['cp'] - played['cp'] >= 80
                        verified = []
                        if suspicious:
                            for budget in [80000, 320000]:
                                a = evaluate(teacher.engine, board, budget)
                                b = a if a['pv'][0] == move.uci() else evaluate(teacher.engine, board, budget, move)
                                verified.append(dict(best=a, played=b))
                        cp_gaps = [p['best']['cp'] - p['played']['cp'] for p in verified
                                   if p['best']['cp'] is not None and p['played']['cp'] is not None]
                        label = 'screen_only_no_large_error'
                        if len(cp_gaps) == 2:
                            label = 'verified_200cp_error' if min(cp_gaps) >= 200 else 'verified_smaller_error'
                        elif verified:
                            label = 'mate_scored_requires_tactical_review'
                        row = dict(id=uid, game_id=game['id'], game_score=game['score'],
                                   opponent=game['family'], fen=board.fen(), played=move.uci(),
                                   clock_ms=record['clock_before_ms'], elapsed_ms=record['elapsed_ms'],
                                   screen=dict(best=best, played=played), verification=verified,
                                   minimum_verified_regret_cp=min(cp_gaps) if len(cp_gaps) == 2 else None,
                                   label=label, source_game_id=f"old-baseline:{game['id']}", split='development',
                                   history=[m.uci() for m in board.move_stack],
                                   start_fen=board.root().fen())
                        with cache_path.open('a', encoding='utf-8') as stream:
                            stream.write(json.dumps(row) + '\n')
                        cached[uid] = row
                    rows.append(cached[uid])
                board.push(move)
            print(f"Audited game {game['id']}: {len(rows)} own moves", flush=True)
        first = []
        for game in source['games']:
            errors = [r for r in rows if r['game_id'] == game['id'] and r['label'] == 'verified_200cp_error']
            first.append(dict(game_id=game['id'], score=game['score'],
                              first_large_error=errors[0] if errors else None,
                              all_large_errors=len(errors)))
        report = dict(status='complete', context=context, games=len(source['games']), own_moves=len(rows),
                      first_errors=first, large_errors=sum(r['label'] == 'verified_200cp_error' for r in rows),
                      mate_scored=sum(r['label'] == 'mate_scored_requires_tactical_review' for r in rows),
                      scope='Screen every own move at 20k nodes; verify suspected errors at 80k/320k. Finite teacher estimates, not proofs. Old evaluation games become development data and cannot support fresh claims.')
        save_json(out / 'audit.json', report)
        print(json.dumps({k: v for k, v in report.items() if k not in {'first_errors', 'context'}}, indent=2), flush=True)
    finally:
        teacher.close()


if __name__ == '__main__':
    p = argparse.ArgumentParser()
    p.add_argument('--source', type=Path, default=ROOT / 'docs/evidence/threephase-baseline.json')
    p.add_argument('--out', type=Path, default=RUN / 'baseline-audit')
    a = p.parse_args()
    review(a.source, a.out)
