"""Replay existing teacher lines into an explicitly unlabelled development queue.

No engine, model import, network access, fitting or descendant score inference.
"""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

import chess

from scripts.daytime_common import ROOT, RUN, check_stop, digest, save


OUT = RUN / 'move-buffers-unlabelled-queue-01'
WANTED = [('rated2600', False, 15), ('rated2400', False, 24),
          ('rated2400', False, 26), ('rated2600', True, 53)]


def restore(row):
    board = chess.Board(row['start_fen'])
    for uci in row['history']:
        move = chess.Move.from_uci(uci)
        assert move in board.legal_moves
        board.push(move)
    assert board.is_valid() and board.fen() == row['fen']
    return board


def run():
    check_stop()
    assert not OUT.exists(), 'Preserve completed queues.'
    source = RUN / 'move-buffers-progress-02/diagnosis.json'
    metadata = ROOT.parent / 'chessity-agent-version.json'
    failed = RUN / 'student-descendants-supervisor-03/supervisor.json'
    source_data = json.loads(source.read_text())
    selected = json.loads(metadata.read_text())
    failure = json.loads(failed.read_text())
    assert selected['version'] == 'v1.56'
    assert digest(ROOT.parent / 'chessity-agent.zip') == selected['sha256']
    assert source_data['status'] == 'complete' and source_data['completed_pairs'] == 4
    assert failure['status'] == 'failed' and failure['stages'] == []
    assert not (RUN / 'student-descendants-03').exists()
    source_hashes = {str(p.relative_to(ROOT)) if p.is_relative_to(ROOT) else str(p): digest(p)
                     for p in (source, metadata, failed, Path(__file__),
                               ROOT / 'docs/DAYTIME_UNLABELLED_QUEUE_PLAN_20260909.md')}
    roots, leaves, skipped = [], {}, []
    for match, white, number in WANTED:
        rows = [r for r in source_data['targets']
                if (r['match'], r['candidate_white'], r['fullmove']) == (match, white, number)]
        assert len(rows) == 1
        row = rows[0]
        board = restore(row)
        assert board.turn == white and row['policy_target'] != row['played']
        root_id = f"{match}-{'white' if white else 'black'}-{number}"
        root = dict(id=root_id, game_key=row['game_key'], match=match,
                    candidate_white=white, fullmove=number, played=row['played'],
                    alternative=row['policy_target'], phase=row['phase'], label=row['label'],
                    root_labels=row['labels'], root_fen=row['fen'],
                    root_history=row['history'], start_fen=row['start_fen'])
        roots.append(root)
        for branch, expected in [('played', row['played']), ('best', row['policy_target'])]:
            label = row['labels'][-1]
            pv = label[branch]['pv']
            assert pv and pv[0] == expected
            full = board.copy(stack=True)
            san = []
            for uci in pv:
                move = chess.Move.from_uci(uci)
                assert move in full.legal_moves, (root_id, branch, uci)
                san.append(full.san(move))
                full.push(move)
            root[branch + '_teacher_line_san'] = san
            for length in (4, 8):
                if len(pv) < length:
                    skipped.append(dict(root_id=root_id, branch=branch, plies=length,
                                        reason='teacher line shorter than requested prefix'))
                    continue
                child = board.copy(stack=True)
                for uci in pv[:length]:
                    child.push_uci(uci)
                replay = dict(start_fen=row['start_fen'],
                              history=[m.uci() for m in child.move_stack], fen=child.fen())
                assert restore(replay).fen() == child.fen()
                key = hashlib.sha256(json.dumps([row['game_key'], replay['start_fen'],
                                                replay['history']]).encode()).hexdigest()
                terminal = child.outcome(claim_draw=True)
                if key not in leaves:
                    leaves[key] = dict(id=key, game_key=row['game_key'], **replay,
                        side_to_move='white' if child.turn else 'black',
                        in_check=child.is_check(), terminal=terminal is not None,
                        legal_terminal_reason=terminal.termination.name if terminal else None,
                        legal_terminal_result=terminal.result() if terminal else None,
                        origins=[], development_only=True, independently_labelled=False,
                        value_target=None, training_eligible=False,
                        next_action='Preserve exact terminal outcome outside finite regression'
                            if terminal else 'Independently evaluate this replay at both teacher budgets')
                leaves[key]['origins'].append(dict(root_id=root_id, branch=branch, plies=length,
                    source_requested_nodes=label['nodes'], continuation=pv[:length],
                    san=san[:length]))
    result = dict(status='complete_unlabelled_queue', created_utc=datetime.now(timezone.utc).isoformat(),
        selected_version=selected['version'], selected_sha256=selected['sha256'],
        source_sha256=source_hashes, scope='Existing teacher PVs, not actual student search leaves. '
            'All are exposed development positions. Root labels are not descendant value targets.',
        root_count=len(roots), game_groups=len({r['game_key'] for r in roots}),
        leaf_count=len(leaves), legal_terminals=sum(r['terminal'] for r in leaves.values()),
        requested_new_teacher_nodes=0, model_updates=0, roots=roots,
        leaves=list(leaves.values()), skipped=skipped,
        future_requirements=['Independently label each nonterminal full replay before finite training.',
            'Keep checked, mate, unstable and terminal cases explicit.',
            'Collect actual student continuations separately once capacity recovers.',
            'Keep game groups together and check FEN/mirror overlap; this queue supplies no holdout.',
            'Preserve the selected playing weights until a new short comparison qualifies.'])
    assert all(r['value_target'] is None and not r['training_eligible'] for r in leaves.values())
    assert len(roots) == 4 and len(leaves) <= 16
    save(OUT / 'queue.json', result)
    print(json.dumps({k: result[k] for k in ('status', 'root_count', 'game_groups', 'leaf_count',
        'legal_terminals', 'requested_new_teacher_nodes', 'model_updates')}))


if __name__ == '__main__':
    run()
