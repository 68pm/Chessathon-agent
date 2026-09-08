"""Offline, history-aware move rewards for every completed game, regardless of result."""

import hashlib
import io
import json
import os
from collections import Counter
from pathlib import Path

import chess
import chess.pgn

from scripts.alien_rating_ladder import sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF
from scripts.overnight_capacity import wait_for_capacity
from training.puzzle_verifier import Verifier

ROOT = Path(__file__).resolve().parents[1]
BUDGETS = (80000, 320000)
SCHEMA = 'stockfish-move-feedback-v1'


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True).encode()).hexdigest()


def write_json(path, value):
    """Replace only our own state file atomically, preserving complete prior records."""
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    pending = path.with_suffix(path.suffix + '.pending')
    pending.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n', encoding='utf-8')
    os.replace(pending, path)


def stop_check():
    if any((ROOT / name).exists() for name in ('STOP_TRAINING', 'STOP_BENCHMARK')):
        raise InterruptedError('User stop flag; preserve completed feedback')


def normalise_game(record):
    """PGN is the authority for the actual start position and played history."""
    game = chess.pgn.read_game(io.StringIO(record['pgn']))
    if game is None or game.errors:
        raise ValueError('Invalid PGN')
    board = game.board()
    if not board.is_valid():
        raise ValueError('Invalid start position')
    moves = []
    for node in game.mainline():
        if node.move not in board.legal_moves:
            raise ValueError('Illegal PGN move')
        moves.append(node.move.uci())
        board.push(node.move)
    if record.get('final_fen') and record['final_fen'] != board.fen():
        raise ValueError('PGN and result final position disagree')
    result = game.headers.get('Result', '*')
    if result not in ('1-0', '0-1', '1/2-1/2'):
        raise ValueError('A finished result is required')
    if type(record.get('candidate_white')) is not bool:
        raise ValueError('Explicit candidate colour is required')
    score = .5 if result == '1/2-1/2' else float((result == '1-0') == record['candidate_white'])
    if record.get('score') is not None and record['score'] != score:
        raise ValueError('Result and candidate score disagree')
    if board.is_game_over() and board.result() != result:
        raise ValueError('Board outcome and PGN result disagree')
    info = dict(start_fen=game.board().fen(), moves=moves,
        candidate_white=record['candidate_white'], score=score,
        candidate_version=record.get('candidate_version', record.get('candidate_path', 'unknown')),
        source_game_id=str(record.get('source_game_id', record.get('id', 'unknown'))),
        opponent=record.get('opponent', record.get('family', 'unknown')),
        termination=record.get('termination', game.headers.get('Termination', 'unknown')),
        operational_failure=record.get('failed_colour'),
        pgn_sha256=hashlib.sha256(record['pgn'].encode()).hexdigest())
    info['game_key'] = digest(info)
    return game, info


def grade(labels, played, legal_count):
    """Two independent budgets; result/opponent rating never enter reward arithmetic."""
    result = dict(reward=None, label='uncertain', policy_target=None,
        policy_weight=0., regret_cp=None, confidence='two-budget engine estimate')
    if len(labels) != 2:
        return result
    best, actual = ([r[key] for r in labels] for key in ('best', 'played'))
    target = best[-1]['pv'][0]
    same_target = best[0]['pv'][0] == target
    if legal_count == 1:
        return dict(result, reward=0., label='forced_move')
    if all(v['mate'] is None and v['cp'] is not None for v in best + actual):
        gaps = [a['cp'] - b['cp'] for a, b in zip(best, actual, strict=True)]
        result['regret_cp'] = gaps
        if (min(gaps) < -30 or abs(best[0]['cp'] - best[1]['cp']) > 100
                or abs(actual[0]['cp'] - actual[1]['cp']) > 100):
            return result
        if max(gaps) <= 25:
            return dict(result, reward=1., label='good_move', policy_target=played,
                        policy_weight=1.)
        if min(gaps) >= 70:
            severity = min(1., min(gaps) / 300.)
            return dict(result, reward=-severity,
                label='major_mistake' if min(gaps) >= 200 else 'inaccuracy',
                policy_target=target if same_target else None,
                policy_weight=severity if same_target else 0.)
        return dict(result, reward=0., label='small_or_uncertain_difference')
    def positive_mate(value):
        return value['mate'] is not None and value['mate'] > 0

    def negative_mate(value):
        return value['mate'] is not None and value['mate'] < 0
    if all(positive_mate(v) for v in best + actual):
        return dict(result, reward=1., label='preserves_engine_mate',
                    policy_target=played, policy_weight=1.)
    if all(negative_mate(v) for v in best + actual):
        return dict(result, reward=0., label='already_in_engine_forced_loss')
    missed_mate = all(positive_mate(v) for v in best) and all(
        not positive_mate(v) for v in actual)
    allows_mate = all(negative_mate(v) for v in actual) and all(
        not negative_mate(v) for v in best)
    if missed_mate or allows_mate:
        return dict(result, reward=-1., label='missed_engine_mate' if missed_mate else 'allows_engine_mate',
                    policy_target=target if same_target else None,
                    policy_weight=1. if same_target else 0.)
    return result


def phase(board):
    units = sum(len(board.pieces(piece, colour)) * weight
        for colour in chess.COLORS for piece, weight in
        ((chess.KNIGHT, 1), (chess.BISHOP, 1), (chess.ROOK, 2), (chess.QUEEN, 4)))
    if units <= 8:
        return 'endgame'
    return 'opening' if board.fullmove_number <= 12 else 'middlegame'


class CachedTeacher:
    def __init__(self, cache, progress):
        self.cache, self.progress = Path(cache), Path(progress)
        self.identity = dict(schema=SCHEMA, executable_sha256=sha256(SF),
            evaluate_sha256=sha256(ROOT / 'scripts/improvement_audit.py'),
            settings={'Threads': 1, 'Hash': 32, 'UCI_LimitStrength': False})
        self.verifier = None
        self.requested_nodes = 0
        self.hits = 0

    def analyse(self, board, nodes, move=None):
        stop_check()
        key = digest(dict(teacher=self.identity, start_fen=board.root().fen(),
            history=[m.uci() for m in board.move_stack], fen=board.fen(),
            root_move=move.uci() if move else None, nodes=nodes))
        target = self.cache / (key + '.json')
        if target.exists():
            cached = json.loads(target.read_text(encoding='utf-8'))
            if cached['key'] != key:
                raise ValueError('Feedback cache mismatch')
            self.hits += 1
            return cached['analysis']
        if self.verifier is None:
            wait_for_capacity(self.progress / 'teacher-capacity.json')
            self.verifier = Verifier(SF)
        answer = evaluate(self.verifier.engine, board, nodes, move)
        if move is not None and answer['pv'][0] != move.uci():
            raise ValueError('Restricted teacher search returned another move')
        test = board.copy(stack=True)
        for uci in answer['pv']:
            candidate = chess.Move.from_uci(uci)
            if candidate not in test.legal_moves:
                raise ValueError('Illegal teacher continuation')
            test.push(candidate)
        self.requested_nodes += nodes
        write_json(target, dict(key=key, analysis=answer))
        return answer

    def close(self):
        if self.verifier is not None:
            self.verifier.close()
            self.verifier = None


def review_game(record, out, teacher):
    game, info = normalise_game(record)
    directory = Path(out) / info['game_key']
    directory.mkdir(parents=True, exist_ok=True)
    path = directory / 'review.json'
    identity = dict(schema=SCHEMA, game=info, teacher=teacher.identity,
        reviewer_sha256=sha256(__file__), budgets=list(BUDGETS))
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else dict(
        identity=identity, status='running', rows=[])
    if state['identity'] != identity:
        raise ValueError('Existing feedback used different data, code or settings')
    if state['status'] == 'complete':
        return path
    board = game.board()
    old = {row['ply']: row for row in state['rows']}
    rows = []
    try:
        for ply, node in enumerate(game.mainline()):
            stop_check()
            move = node.move
            if board.turn == info['candidate_white']:
                if ply in old:
                    row = old[ply]
                    if row['fen'] != board.fen() or row['played'] != move.uci():
                        raise ValueError('Feedback resume history mismatch')
                else:
                    labels = []
                    for budget in BUDGETS:
                        best = teacher.analyse(board, budget)
                        actual = best if best['pv'][0] == move.uci() else teacher.analyse(board, budget, move)
                        labels.append(dict(nodes=budget, best=best, played=actual))
                    reward = grade(labels, move.uci(), board.legal_moves.count())
                    tags = [phase(board)]
                    if board.is_check():
                        tags.append('defence_in_check')
                    if board.gives_check(move):
                        tags.append('forcing_check')
                    if board.is_capture(move):
                        tags.append('capture_or_exchange')
                    if move.promotion:
                        tags.append('promotion')
                    if reward['reward'] == 1 and all(v['played']['cp'] is not None
                            and v['played']['cp'] >= 150 for v in labels):
                        tags.append('preserves_estimated_advantage')
                    row = dict(ply=ply, fullmove=board.fullmove_number, white=board.turn,
                        fen=board.fen(), start_fen=game.board().fen(),
                        history=[m.uci() for m in board.move_stack], played=move.uci(), san=board.san(move),
                        clock_after_seconds=node.clock(), labels=labels, tags=tags, **reward)
                    # The move policy encodes clocks/rights but not repetition history.
                    if board.is_repetition(2) or board.can_claim_draw():
                        row.update(policy_target=None, policy_weight=0.,
                            policy_exclusion='Repetition context is absent from policy features')
                    row['static_value_target'] = None
                    row['value_training_note'] = 'Root action reward only; independently label quiet descendants before value fitting.'
                rows.append(row)
                state.update(rows=rows, status='running', requested_nodes_this_process=teacher.requested_nodes)
                write_json(path, state)
            board.push(move)
        expected = sum((game.board().turn if i % 2 == 0 else not game.board().turn)
                       == info['candidate_white'] for i in range(len(info['moves'])))
        if len(rows) != expected:
            raise ValueError('Incomplete move coverage')
        state.update(status='complete', own_moves=len(rows),
            labels=dict(Counter(row['label'] for row in rows)),
            rewarded=sum(row['reward'] is not None and row['reward'] > 0 for row in rows),
            penalised=sum(row['reward'] is not None and row['reward'] < 0 for row in rows),
            policy_examples=sum(row['policy_target'] is not None for row in rows),
            limitation='Teacher estimates, not proof of strategy or Elo. Outcome does not determine move reward.')
        annotated = chess.pgn.read_game(io.StringIO(record['pgn']))
        indexed = {r['ply']: r for r in rows}
        for ply, node in enumerate(annotated.mainline()):
            if ply in indexed:
                row = indexed[ply]
                note = f"Feedback: {row['label']}; reward={row['reward']}; regret_cp={row['regret_cp']}"
                node.comment = (node.comment + ' ' + note).strip()
        (directory / 'annotated.pgn').write_text(str(annotated) + '\n', encoding='utf-8')
        (directory / 'original.pgn').write_text(record['pgn'], encoding='utf-8')
        write_json(path, state)
        return path
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        write_json(path, state)
        raise


def review_batch(records, out):
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', out)
    paths = []
    try:
        for record in records:
            path = review_game(record, out / 'games', teacher)
            paths.append(path)
            info = json.loads(path.read_text(encoding='utf-8'))
            print(json.dumps(dict(game=info['identity']['game']['source_game_id'],
                moves=info['own_moves'], rewarded=info['rewarded'], penalised=info['penalised'])), flush=True)
        report = dict(status='complete', games=[p.relative_to(out).as_posix() for p in paths],
            source_code_sha256=sha256(__file__), requested_nodes=teacher.requested_nodes,
            cache_hits=teacher.hits, new_games_played=0)
        write_json(out / 'manifest.json', report)
        return paths
    finally:
        teacher.close()
