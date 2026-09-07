"""Classify imported competition games without inventing a local match schedule."""

import json

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_phase_report import error_signals, phase_details
from training.fastchess_data import ROOT


def main():
    out = ROOT / 'runs/improvement-loop-20260907/competition-20260907'
    source = out / 'recent/results.json'
    matches = json.loads(source.read_text())
    context = json.loads((out / 'recent-audit/context.json').read_text())
    assert context['source_sha256'] == sha256(source)
    audit = json.loads((out / 'recent-audit/audit.json').read_text())
    assert audit['status'] == matches['status'] == 'complete'
    assert audit['games'] == len(matches['games']) == 3
    rows = list(map(json.loads, (out / 'recent-audit/positions.jsonl').read_text().splitlines()))
    assert len(rows) == audit['own_moves'] == 194
    games, targets = [], []
    for game in matches['games']:
        observations = []
        for row in rows:
            if row['game_id'] != game['id']:
                continue
            board = chess.Board(row['start_fen'])
            for move in row['history']:
                board.push_uci(move)
            assert board.fen() == row['fen'] and board.turn == game['candidate_white']
            move = chess.Move.from_uci(row['played'])
            assert move in board.legal_moves
            signals = error_signals(row)
            observation = dict(id=row['id'], **phase_details(board), **signals,
                san=board.san(move), played=row['played'], clock_ms=row['clock_ms'],
                regret_cp=row['minimum_verified_regret_cp'], verification=row['verification'])
            observations.append(observation)
            if signals['large_cp_error'] or signals['mate_loss_transition']:
                targets.append({**row, 'phase': observation['phase'], 'san': observation['san'],
                    'source_game_id': f'competition:{game["id"]}', 'version': game['candidate_version_inference'],
                    'acceptance': 'Development diagnosis only; not accepted for fitting or future fresh testing.'})
        def first(*keys):
            return next((r for r in observations if any(r[k] for k in keys)), None)
        games.append(dict(round=game['id'], opponent=game['opponent'], score=game['score'],
            version=game['candidate_version_inference'], own_moves=len(observations),
            large_errors=sum(r['large_cp_error'] for r in observations),
            first_warning=first('large_cp_error', 'losing_transition', 'mate_loss_transition'),
            first_losing_transition=first('losing_transition'),
            first_squandered_advantage=first('squandered_advantage')))
    assert not (out / 'recent-phase.json').exists()
    save_json(out / 'recent-phase.json', dict(status='complete', games=games,
        source_sha256=sha256(source), audit_sha256=sha256(out / 'recent-audit/positions.jsonl'),
        source_code_sha256=sha256(__file__), new_teacher_nodes=0,
        scope='Same finite verified phase signals applied to imported real competition games; no fabricated local schedule or rating claim.'))
    (out / 'targets.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in targets), encoding='utf-8', newline='\n')
    print(json.dumps(dict(games=3, own_moves=194, targets=len(targets),
        diagnostics=[dict(round=g['round'], large_errors=g['large_errors'],
            first_warning=g['first_warning']['san'] if g['first_warning'] else None,
            first_warning_phase=g['first_warning']['phase'] if g['first_warning'] else None,
            squandered=g['first_squandered_advantage']['san'] if g['first_squandered_advantage'] else None)
            for g in games])), flush=True)


if __name__ == '__main__':
    main()
