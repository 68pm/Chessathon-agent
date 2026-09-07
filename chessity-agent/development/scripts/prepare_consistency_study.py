"""Choose fresh balanced groups without loading or testing the candidate engine."""

import csv
import hashlib
import io
import json
import re
from collections import defaultdict
from datetime import datetime, timezone

import chess
import chess.pgn

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF, manifest
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier, duplicate_key

OUT = ROOT / 'runs/improvement-loop-20260907/consistency-01'
REFERENCE = ROOT / 'data/three-phase-pack/opening-reference.tsv'
SEED = 2026090791
CANDIDATE = 'candidates/compiled-qsearch-endgames-v1'
ARCHIVE_SHA = 'e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63'


def rank(value):
    return hashlib.sha256(f'{SEED}:{value}'.encode()).hexdigest()


def stopped():
    if any((ROOT / name).exists() for name in ['STOP_TRAINING', 'STOP_BENCHMARK']):
        raise InterruptedError('User stop flag')


def catalog():
    rows, lookup = [], defaultdict(set)
    with REFERENCE.open(encoding='utf-8', newline='') as stream:
        for index, source in enumerate(csv.DictReader(stream, delimiter='\t')):
            game = chess.pgn.read_game(io.StringIO(source['pgn']))
            assert game and not game.errors
            board = game.end().board()
            assert board.fen() == chess.Board(source['fen']).fen() and board.is_valid()
            key = duplicate_key(board)
            row = dict(source_index=index, group=source['eco'], name=source['name'],
                       start_fen=board.fen(), opening=[], key=key, pgn=source['pgn'])
            rows.append(row)
            for position in [board, board.mirror()]:
                for fen in [position.fen(), position.fen(en_passant='fen')]:
                    lookup[' '.join(fen.split()[:4])].add((key, row['group']))
    return rows, lookup


def exposure_inventory(lookup):
    keys, groups, records, legacy_setups = set(), set(), [], []
    seen_pgn, seen_openings = set(), set()
    def observe(fen):
        for key, group in lookup.get(' '.join(fen.split()[:4]), set()):
            keys.add(key)
            groups.add(group)
    def walk(value):
        touched = False
        if isinstance(value, dict):
            group = value.get('opening_group', value.get('group') if 'start_fen' in value else None)
            if isinstance(group, str) and re.fullmatch('[A-E][0-9]{2}', group):
                groups.add(group)
                touched = True
            opening = value.get('opening')
            if isinstance(opening, list) and all(isinstance(m, str) and re.fullmatch('[a-h][1-8][a-h][1-8][qrbn]?', m) for m in opening):
                identity = (value.get('start_fen', chess.STARTING_FEN), tuple(opening))
                if identity not in seen_openings:
                    board = chess.Board(identity[0])
                    observe(board.fen())
                    try:
                        for move in opening:
                            board.push_uci(move)
                            observe(board.fen())
                    except chess.IllegalMoveError:
                        # Older exports name the already-played opening's final
                        # FEN start_fen while also retaining its full move list.
                        board = chess.Board()
                        for move in opening:
                            board.push_uci(move)
                            observe(board.fen())
                        legacy_setups.append(dict(recorded_start_fen=identity[0], opening=opening,
                                                  replayed_from=chess.STARTING_FEN, final_fen=board.fen()))
                    seen_openings.add(identity)
                touched = True
            for key, child in value.items():
                if key == 'pgn' and isinstance(child, str) and '[Result ' in child:
                    identifier = hashlib.sha256(child.encode()).hexdigest()
                    if identifier not in seen_pgn:
                        game = chess.pgn.read_game(io.StringIO(child))
                        if game is None or game.errors:
                            raise ValueError('Cannot certify exposure inventory from a malformed recorded game.')
                        board = game.board()
                        observe(board.fen())
                        for move in game.mainline_moves():
                            board.push(move)
                            observe(board.fen())
                        seen_pgn.add(identifier)
                    touched = True
                elif isinstance(child, str) and child.count('/') == 7 and len(child.split()) == 6:
                    observe(child)
                    touched = True
                elif isinstance(child, (dict, list)):
                    touched = walk(child) or touched
        elif isinstance(value, list):
            for child in value:
                if isinstance(child, (dict, list)):
                    touched = walk(child) or touched
        return touched
    paths = sorted((ROOT / 'runs').rglob('*.json')) + sorted((ROOT / 'configs').glob('*opening*.json'))
    for path in paths:
        if OUT in path.parents or path.name.endswith('.current.json') or '__pycache__' in path.parts:
            continue
        stopped()
        value = json.loads(path.read_text(encoding='utf-8-sig'))
        if walk(value):
            records.append(dict(path=path.relative_to(ROOT).as_posix(), sha256=sha256(path)))
    return dict(excluded_keys=sorted(keys), excluded_groups=sorted(groups), sources=records,
                distinct_recorded_pgns=len(seen_pgn), distinct_setups=len(seen_openings),
                legacy_final_fen_plus_full_opening=legacy_setups,
                scope='Prior local JSON match/diagnostic records and opening configs, including exact/mirrored catalogue boards. Related historic training theory is not claimed unseen.')


def make_schedule(starts):
    if len(starts) != 64 or len({s['group'] for s in starts}) != 64 or len({s['key'] for s in starts}) != 64:
        raise ValueError('Exactly64 distinct groups and canonical boards are required.')
    jobs = []
    for pair, start in enumerate(starts):
        for level in ([2400, 2600] if pair % 2 == 0 else [2600, 2400]):
            for white in [True, False]:
                jobs.append(dict(id=len(jobs) + 1, family=f'stockfish:{level}', elo=level,
                    block=1 + pair // 32, pair=pair, opening_group=start['group'],
                    start_fen=start['start_fen'], opening=[], candidate_path=CANDIDATE,
                    candidate_white=white))
    return jobs


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    state_path = OUT / 'preparation.json'
    if state_path.exists():
        raise ValueError('Preparation is single-use; preserve failed selection evidence.')
    state = dict(status='running', started_utc=datetime.now(timezone.utc).isoformat(),
                 source_code_sha256=sha256(__file__), seed=SEED,
                 predeclaration_sha256=sha256(ROOT / 'docs/IMPROVEMENT_CONSISTENCY_01.md'))
    save_json(state_path, state)
    try:
        assert sha256((ROOT / CANDIDATE).with_suffix('.zip')) == ARCHIVE_SHA
        frozen = manifest(ROOT / CANDIDATE)
        rows, lookup = catalog()
        inventory = exposure_inventory(lookup)
        save_json(OUT / 'prior-exposure.json', inventory)
        excluded_keys, excluded_groups = set(inventory['excluded_keys']), set(inventory['excluded_groups'])
        buckets = defaultdict(list)
        for row in rows:
            board = chess.Board(row['start_fen'])
            if (row['key'] not in excluded_keys and row['group'] not in excluded_groups
                    and 10 <= board.ply() <= 24 and len(board.piece_map()) >= 24
                    and board.halfmove_clock < 10 and not board.is_check() and not board.is_game_over(claim_draw=True)):
                buckets[row['group']].append(row)
        print(json.dumps(dict(catalogue=len(rows), excluded_groups=len(excluded_groups), eligible_groups=len(buckets))), flush=True)
        selected, attempted, used = [], [], set()
        teacher = Verifier(SF)
        try:
            option = teacher.engine.options['UCI_Elo']
            supported = dict(min=option.min, max=option.max, requested=[2400,2600])
            assert option.min <= 2400 < 2600 <= option.max
            for group in sorted(buckets, key=rank):
                for row in sorted(buckets[group], key=lambda r: rank(r['pgn']))[:8]:
                    if len(attempted) >= 512:
                        break
                    stopped()
                    if row['key'] in used:
                        continue
                    board = chess.Board(row['start_fen'])
                    small = evaluate(teacher.engine, board, 20000)
                    deep = evaluate(teacher.engine, board, 80000)
                    accepted = (small['cp'] is not None and deep['cp'] is not None
                                and abs(small['cp']) <= 60 and abs(deep['cp']) <= 60
                                and abs(small['cp'] - deep['cp']) <= 40)
                    attempted.append(dict(**row, small=small, deep=deep, accepted=accepted))
                    save_json(OUT / 'balance-attempts.json', attempted)
                    if accepted:
                        selected.append(dict(**row, small=small, deep=deep))
                        used.add(row['key'])
                        print(f'Balanced {len(selected)}/64: {group}', flush=True)
                        break
                if len(selected) == 64 or len(attempted) >= 512:
                    break
        finally:
            teacher.close()
        assert len(selected) == 64, f'Only{len(selected)} fresh balanced groups; do not relax criteria.'
        selected.sort(key=lambda r: rank('assignment:' + r['group']))
        save_json(OUT / 'starts.json', selected)
        assert frozen == manifest(ROOT / CANDIDATE)
        study = dict(status='prepared', label='consistency-01', candidate=CANDIDATE,
            candidate_sha256=ARCHIVE_SHA, files={CANDIDATE:frozen}, seed=SEED,
            config=dict(base_ms=120000, increment_ms=500, ply_cap=600, workers=2),
            source_sha256={REFERENCE.relative_to(ROOT).as_posix():sha256(REFERENCE),
                'docs/IMPROVEMENT_CONSISTENCY_01.md':state['predeclaration_sha256'],
                'scripts/prepare_consistency_study.py':sha256(__file__)},
            starts_sha256=sha256(OUT / 'starts.json'), exposure_sha256=sha256(OUT / 'prior-exposure.json'),
            balance_sha256=sha256(OUT / 'balance-attempts.json'), stockfish_sha256=sha256(SF),
            opponent_supported_range=supported, teacher_preparation_complete=True,
            selected_groups=64, balance_candidates=len(attempted),
            max_requested_teacher_nodes=100000 * len(attempted), schedule=make_schedule(selected),
            attempts={'2400':1,'2600':2},
            scope='Frozen new performance groups with both colours and no adaptive fitting; not a pristine historic-training holdout, human/site Elo or unconditional independence guarantee.')
        save_json(OUT / 'study.json', study)
        state.update(status='complete', selected_groups=64, study_sha256=sha256(OUT / 'study.json'))
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        state['completed_utc'] = datetime.now(timezone.utc).isoformat()
        save_json(state_path, state)


if __name__ == '__main__':
    main()
