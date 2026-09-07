"""Small, cached, history-preserving successor-value pilot from verified own errors."""

import argparse
import json
from collections import defaultdict
from pathlib import Path

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier, duplicate_key


def restore_root(row):
    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        board.push_uci(uci)
    assert board.is_valid() and board.fen() == row['fen']
    return board


def branch_position(row, branch):
    board = restore_root(row)
    root_turn = board.turn
    pv = row['verification'][-1][branch]['pv']
    expected = row['played'] if branch == 'played' else pv[0]
    assert pv and pv[0] == expected
    for index, uci in enumerate(pv[:4]):
        board.push_uci(uci)
        if board.is_game_over(claim_draw=True):
            return None, 'terminal endpoint'
        if not board.is_check():
            if board.halfmove_clock >= 70:
                return None, 'draw-clock margin'
            return dict(board=board, root_turn=root_turn, branch_plies=index + 1), None
    return None, 'no non-check endpoint within four recorded plies'


def assess_pair(branches, root_scores):
    for label in ('best', 'played'):
        values = branches[label]['analysis']
        cps = [v['cp'] for v in values]
        if len(cps) != 2 or None in cps or any(v.get('mate') is not None for v in values):
            return False, 'non-finite or mate-scored endpoint'
        if max(map(abs, cps)) > 1500 or abs(cps[0] - cps[1]) > 75:
            return False, 'endpoint score unstable or outside training range'
        if abs(branches[label]['root_pov_cp'][-1] - root_scores[label]) > 150:
            return False, 'endpoint changed the source branch assessment'
    gaps = [a - b for a, b in zip(branches['best']['root_pov_cp'], branches['played']['root_pov_cp'], strict=True)]
    if min(gaps) < 100:
        return False, 'verified successor gap below100cp'
    return True, None


def root_pov_scores(analysis, board_turn, root_turn):
    sign = 1 if board_turn == root_turn else -1
    return [sign * v['cp'] if v['cp'] is not None else None for v in analysis]


def prepare(audit, source, out, max_pairs=16):
    assert 1 <= max_pairs <= 16
    report = json.loads(source.read_text())
    audit_report = json.loads((audit / 'audit.json').read_text())
    audit_context = json.loads((audit / 'context.json').read_text())
    assert report['status'] == audit_report['status'] == 'complete'
    assert audit_context['source_sha256'] == sha256(source)
    validation = ROOT / 'runs/improvement-loop-20260907/residual-pilot-01/dataset-manifest.json'
    protected = {duplicate_key(chess.Board(r['fen'])) for r in json.loads(validation.read_text())['rows'] if r['split'] == 1}
    context = dict(source_sha256=sha256(source), audit_sha256=sha256(audit / 'positions.jsonl'),
                   validation_sha256=sha256(validation), source_code_sha256=sha256(__file__),
                   teacher_sha256=sha256(SF), budgets=[80000, 320000], max_pairs=max_pairs)
    out.mkdir(parents=True, exist_ok=True)
    if (out / 'context.json').exists():
        assert json.loads((out / 'context.json').read_text()) == context
    else:
        save_json(out / 'context.json', context)
    if (out / 'report.json').exists():
        assert json.loads((out / 'report.json').read_text())['status'] == 'complete'
        return
    by_game = defaultdict(list)
    for line in (audit / 'positions.jsonl').read_text().splitlines():
        row = json.loads(line)
        if row['label'] == 'verified_200cp_error' and len(by_game[row['game_id']]) < 2:
            by_game[row['game_id']].append(row)
    selected = [by_game[g][i] for i in range(2) for g in sorted(by_game) if len(by_game[g]) > i][:max_pairs]
    games = {g['id']: g for g in report['games']}
    cache = out / 'attempts.jsonl'
    cached = {r['id']: r for r in map(json.loads, cache.read_text().splitlines())} if cache.exists() else {}
    results = []
    teacher = Verifier(SF)
    try:
        for row in selected:
            if (ROOT / 'STOP_TRAINING').exists() or (ROOT / 'STOP_BENCHMARK').exists():
                raise InterruptedError('User stop flag')
            identity = context['source_sha256'] + ':' + row['id']
            if identity in cached:
                results.append(cached[identity])
                continue
            result = dict(id=identity, source_id=row['id'], source_game_id=f"{context['source_sha256']}:{row['game_id']}",
                          source_group=games[row['game_id']].get('opening_group'), split='development',
                          root_fen=row['fen'], branches={}, accepted=False, reason=None)
            for label in ('best', 'played'):
                endpoint, reason = branch_position(row, label)
                if reason:
                    result['reason'] = reason
                    break
                board = endpoint['board']
                if duplicate_key(board) in protected:
                    result['reason'] = 'protected validation position'
                    break
                analysis = [evaluate(teacher.engine, board, n) for n in context['budgets']]
                result['branches'][label] = dict(fen=board.fen(), start_fen=board.root().fen(),
                    history=[m.uci() for m in board.move_stack], branch_plies=endpoint['branch_plies'],
                    analysis=analysis, root_pov_cp=root_pov_scores(analysis, board.turn, endpoint['root_turn']))
            if not result['reason']:
                root_scores = {label: row['verification'][-1][label]['cp'] for label in ('best', 'played')}
                result['accepted'], result['reason'] = assess_pair(result['branches'], root_scores)
            with cache.open('a', encoding='utf-8') as stream:
                stream.write(json.dumps(result) + '\n')
            results.append(result)
            print(f"Counterfactual {len(results)}/{len(selected)}: {result['accepted']} {result['reason']}", flush=True)
    finally:
        teacher.close()
    accepted = [r for r in results if r['accepted']]
    (out / 'verified-pairs.jsonl').write_text(''.join(json.dumps(r) + '\n' for r in accepted), encoding='utf-8')
    save_json(out / 'report.json', dict(status='complete', attempted=len(results), accepted_pairs=len(accepted),
              successor_positions=2 * len(accepted), context=context,
              retired_source_groups=sorted({g['opening_group'] for g in report['games'] if g.get('opening_group')}),
              pairs_sha256=sha256(out / 'verified-pairs.jsonl'),
              limitations='Finite teacher endpoint estimates with full recorded history. Pair endpoints may be different distances from the root. Static network cannot represent repetition history. These are development labels, not fresh test results. No model fit or strength gain claimed.'))


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--max-pairs', type=int, default=16)
    args = parser.parse_args()
    prepare(args.audit, args.source, args.out, args.max_pairs)
