"""Review frozen clock choices only after a new overnight efficiency gate passes."""

import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from scripts.overnight_geometry_trial import ROOT, check_stop, digest, manifest, save


def run(directory):
    import chess

    from scripts.overnight_capacity import wait_for_capacity
    from training.game_feedback import CachedTeacher

    directory = directory.resolve()
    assert directory.is_relative_to(ROOT / 'runs/overnight-20260909')
    prep = json.loads((directory / 'preparation.json').read_text(encoding='utf-8'))
    trial = json.loads((directory / 'state.json').read_text(encoding='utf-8'))
    assert trial['status'] == 'complete' and trial['passed'] and trial['frozen_candidates']
    # Trial controllers write their final state after closing both student workers.
    assert all(manifest(ROOT / p) == prep['candidate_files'][label]
               for label, p in prep['candidates'].items())
    out = directory / 'clock-quality-01'
    assert not out.exists(), 'Preserve completed/partial reviews; no implicit retry'
    out.mkdir()
    state = dict(status='running', passed=False, rows=[], trial_sha256=digest(directory / 'state.json'),
                 source_code_sha256=digest(Path(__file__)))
    save(out / 'state.json', state)
    check_stop()
    wait_for_capacity(out / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    teacher = CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', out)
    try:
        for index, root in enumerate(prep['roots']):
            check_stop()
            board = chess.Board(root['start_fen'])
            for uci in root['history']:
                board.push_uci(uci)
            assert board.fen() == root['fen']
            choices = [r for r in trial['rows'] if r['root'] == index and r['regime'] == 'clock']
            assert len(choices) == 4 and all(sum(r['label'] == label for r in choices) == 2
                                            for label in ('baseline', 'prototype'))
            bests = [teacher.analyse(board, n) for n in (80000, 320000)]
            values = {}
            for uci in sorted({c['uci'] for c in choices}):
                assert chess.Move.from_uci(uci) in board.legal_moves
                values[uci] = [best if best['pv'][0] == uci else teacher.analyse(board, n,
                    chess.Move.from_uci(uci)) for n, best in zip((80000, 320000), bests, strict=True)]
            reviewed = []
            for choice in choices:
                value = values[choice['uci']]
                regret = [max(0, b['cp'] - v['cp']) if b['cp'] is not None and v['cp'] is not None else None
                          for b, v in zip(bests, value, strict=True)]
                reviewed.append(dict(**choice, values=value, regret_cp=regret,
                    major=all(v is not None and v >= 200 for v in regret),
                    mate_loss=any(v['mate'] is not None and v['mate'] < 0 for v in value)))
            state['rows'].append(dict(id=root['id'], best=bests, choices=reviewed,
                                      start_fen=root['start_fen'], history=root['history']))
            state['requested_teacher_nodes'] = teacher.requested_nodes
            save(out / 'state.json', state)
        finite = [r for r in state['rows'] if all(v is not None for c in r['choices'] for v in c['regret_cp'])]
        assert finite, 'No jointly finite roots to evaluate'
        means = {label: [statistics.mean(c['regret_cp'][i] for r in finite for c in r['choices']
                 if c['label'] == label) for i in range(2)] for label in ('baseline', 'prototype')}
        new_major, new_mate, repairs = [], [], []
        for row in state['rows']:
            a = [c for c in row['choices'] if c['label'] == 'baseline']
            b = [c for c in row['choices'] if c['label'] == 'prototype']
            if sum(c['major'] for c in b) > sum(c['major'] for c in a):
                new_major.append(row['id'])
            if sum(c['mate_loss'] for c in b) > sum(c['mate_loss'] for c in a):
                new_mate.append(row['id'])
            if row in finite and all(statistics.mean(c['regret_cp'][i] for c in a) -
                statistics.mean(c['regret_cp'][i] for c in b) >= 100 for i in range(2)):
                repairs.append(row['id'])
        passed = not new_major and not new_mate and all(p <= b for p, b in zip(
            means['prototype'], means['baseline'], strict=True))
        state.update(status='complete', passed=bool(passed), finite_roots=len(finite),
            mean_regret_cp=means, new_major=new_major, new_mate=new_mate, repaired=repairs,
            decision='needs_readonly_and_four_game_incumbent_comparison' if passed else 'reject_clock_quality',
            limitation='Exposed position diagnostics; no new games, promotion or Elo.')
    except BaseException as error:
        state.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        state['completed_utc'] = datetime.now(timezone.utc).isoformat()
        state['frozen_candidates'] = all(manifest(ROOT / p) == prep['candidate_files'][label]
                                        for label, p in prep['candidates'].items())
        if not state['frozen_candidates']:
            state.update(status='failed', passed=False, error='Frozen candidate mutated')
        save(out / 'state.json', state)
    print(json.dumps({k: v for k, v in state.items() if k != 'rows'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    args = parser.parse_args()
    run(args.run)
