"""Prepare balanced held-out-ECO starting positions before candidate confirmation."""

import json

import chess
import numpy as np

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier, duplicate_key


def main():
    out = ROOT / 'runs/improvement-loop-20260907/confirmation-starts'
    out.mkdir(exist_ok=True)
    source = ROOT / 'runs/unattended-20260905-away/data-300000/dataset.npz'
    with np.load(source, allow_pickle=False) as data:
        cp, groups, splits, fens = data['cp'], data['group'], data['split'], data['fen']
    manifest = json.loads((ROOT / 'runs/improvement-loop-20260907/residual-pilot-01/dataset-manifest.json').read_text())
    used = {duplicate_key(chess.Board(row['fen'])) for row in manifest['rows']}
    rng = np.random.default_rng(2026090732)
    eligible = (splits == 2) & (abs(cp) <= 80)
    selected, attempts = [], []
    teacher = Verifier(SF)
    try:
        for family in sorted(np.unique(groups[eligible])):
            indices = np.flatnonzero(eligible & (groups == family))
            rng.shuffle(indices)
            checked = 0
            for index in indices:
                board = chess.Board(str(fens[index]))
                key = duplicate_key(board)
                if (not 6 <= board.fullmove_number <= 22 or board.is_check() or board.halfmove_clock >= 10
                        or len(board.piece_map()) < 16 or key in used):
                    continue
                a = evaluate(teacher.engine, board, 20000)
                if a['cp'] is None or abs(a['cp']) > 90:
                    continue
                b = evaluate(teacher.engine, board, 80000)
                checked += 1
                accepted = b['cp'] is not None and abs(b['cp']) <= 60 and abs(a['cp'] - b['cp']) <= 40
                attempts.append(dict(source_index=int(index), family=str(family), small=a, deep=b, accepted=accepted))
                if accepted:
                    selected.append(dict(name=f'{family}-{int(index)}', group=str(family), start_fen=board.fen(),
                                         opening=[], source_index=int(index), teacher_cp=b['cp']))
                    used.add(key)
                    print(f'Balanced confirmation start {len(selected)}: {family}', flush=True)
                    break
                if checked >= 12:
                    break
        assert len(selected) >= 16, 'Insufficient independently balanced groups'
        save_json(out / 'starts.json', selected)
        save_json(out / 'manifest.json', dict(source_sha256=sha256(source), teacher_sha256=sha256(SF),
                  source_code_sha256=sha256(__file__), seed=2026090732, positions=len(selected),
                  source_split=2, attempts=attempts,
                  scope='New frozen match starting positions from original held-out ECO groups, excluded from current residual training and validation. Both colours start from each FEN with fresh repetition history. Older policy training can contain related opening theory; no claim that all positions are novel to every historic model. Candidate outcomes never select starting positions.'))
    finally:
        teacher.close()


if __name__ == '__main__':
    main()
