"""Verify selected probe moves with actual history, keeping both teacher budgets."""

import argparse
import json
from pathlib import Path

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_audit import evaluate
from scripts.magnus_benchmark import SF, manifest
from training.counterfactual_value import restore_root
from training.fastchess_data import ROOT
from training.puzzle_verifier import Verifier


def compare(audit, directory):
    source = audit / 'positions.jsonl'
    audit_context = json.loads((audit / 'context.json').read_text(encoding='utf-8'))
    assert audit_context['teacher_sha256'] == sha256(SF)
    assert audit_context['source_code_sha256'] == sha256(ROOT / 'scripts/improvement_audit.py')
    assert json.loads((audit / 'audit.json').read_text(encoding='utf-8'))['status'] == 'complete'
    rows = {r['id']: r for r in map(json.loads, source.read_text(encoding='utf-8').splitlines())
            if r['label'] == 'verified_200cp_error'}
    assert 4 <= len(rows) <= 6
    probes = {name: json.loads((directory / f'{name}.json').read_text(encoding='utf-8'))
              for name in ['bare', 'full', 'quarter']}
    assert all(p['audit_sha256'] == sha256(source) for p in probes.values())
    assert len({p['source_code_sha256'] for p in probes.values()}) == 1
    assert probes['bare']['source_code_sha256'] == sha256(ROOT / 'scripts/improvement_probe.py')
    assert probes['full']['candidate'] == probes['quarter']['candidate']
    assert Path(probes['bare']['candidate']).name == 'compiled-qsearch-endgames-v1'
    assert Path(probes['full']['candidate']).name == 'compiled-paired-ranking-v1'
    assert probes['bare']['value_blend_override'] is None
    assert all(p['requested_seconds'] == 1. and p['requested_nodes'] is None
               and p['max_depth'] == 64 for p in probes.values())
    choices = {name: {r['id']: r for r in p['results']} for name, p in probes.items()}
    assert all(set(c) == set(rows) for c in choices.values())
    assert probes['quarter']['value_blend_override'] == .25
    assert probes['full']['value_blend_override'] in (None, 1.)
    context = dict(audit_sha256=sha256(source), teacher_sha256=sha256(SF),
                   source_code_sha256=sha256(__file__), budgets=[80000, 320000],
                   candidate_files={p['candidate']: manifest(ROOT / p['candidate']) for p in probes.values()},
                   probes={name: sha256(directory / f'{name}.json') for name in probes})
    context_file = directory / 'regret-context.json'
    if context_file.exists():
        assert json.loads(context_file.read_text(encoding='utf-8')) == context
    else:
        save_json(context_file, context)
    cache = directory / 'regret-cache.jsonl'
    cached = {r['id']: r for r in map(json.loads, cache.read_text(encoding='utf-8').splitlines())} if cache.exists() else {}
    teacher = Verifier(SF)
    records, requested = [], 0
    try:
        for uid, row in sorted(rows.items()):
            board = restore_root(row)
            assert all(c[uid]['fen'] == board.fen() for c in choices.values())
            record = dict(id=uid, fen=board.fen(), variants={})
            for name, selected in choices.items():
                uci = selected[uid]['uci']
                move = chess.Move.from_uci(uci)
                assert move in board.legal_moves
                values = []
                for index, budget in enumerate(context['budgets']):
                    key = f'{uid}:{uci}:{budget}'
                    if key not in cached:
                        if (ROOT / 'STOP_TRAINING').exists() or (ROOT / 'STOP_BENCHMARK').exists():
                            raise InterruptedError('User stop flag')
                        original = row['verification'][index]
                        reused = True
                        if uci == row['played']:
                            value = original['played']
                        elif uci == original['best']['pv'][0]:
                            value = original['best']
                        else:
                            value = evaluate(teacher.engine, board, budget, move)
                            reused = False
                            requested += budget
                        item = dict(id=key, analysis=value, reused_original=reused, budget=budget)
                        cached[key] = item
                        with cache.open('a', encoding='utf-8') as f:
                            f.write(json.dumps(item) + '\n')
                    values.append(cached[key]['analysis'])
                finite = all(v['cp'] is not None for v in values)
                mate_signs = [1 if v['mate'] and v['mate'] > 0 else -1 if v['mate'] and v['mate'] < 0 else 0 for v in values]
                mate = mate_signs[0] if mate_signs[0] == mate_signs[1] else 0
                regrets = [max(0, row['verification'][i]['best']['cp'] - v['cp']) for i, v in enumerate(values)] if finite else None
                record['variants'][name] = dict(uci=uci, analysis=values, finite=finite,
                    stable_mate_sign=mate, unresolved=not finite and mate == 0, regret_cp=regrets)
            records.append(record)
            print(f'Verified selected moves {len(records)}/{len(rows)}', flush=True)
    finally:
        teacher.close()
    comparable = [r for r in records if all(v['finite'] for v in r['variants'].values())]
    summary = {}
    for name in probes:
        means = [sum(min(1000, r['variants'][name]['regret_cp'][i]) for r in comparable) / len(comparable) for i in range(2)] if comparable else None
        summary[name] = dict(mean_capped_regret_cp_by_budget=means,
            verified_mate_losses=sum(r['variants'][name]['stable_mate_sign'] == -1 for r in records),
            unresolved=sum(r['variants'][name]['unresolved'] for r in records))
    b, f, q = (summary[n] for n in ['bare', 'full', 'quarter'])
    passed = (len(comparable) >= 4 and not any(s['unresolved'] for s in summary.values())
              and q['verified_mate_losses'] <= min(b['verified_mate_losses'], f['verified_mate_losses'])
              and all(x < y and x <= z for x, y, z in zip(q['mean_capped_regret_cp_by_budget'],
                  f['mean_capped_regret_cp_by_budget'], b['mean_capped_regret_cp_by_budget'], strict=True)))
    total = sum(r['budget'] for r in cached.values() if not r['reused_original'])
    assert total <= 7200000
    report = dict(status='complete', gate_passed=passed, context=context, roots=len(records),
                  comparable_roots=len(comparable), summary=summary, records=records,
                  newly_requested_teacher_nodes=requested, total_requested_teacher_nodes=total,
                  scope='Finite two-budget analysis of selected failure positions. No rating, strength, or exhaustive mate proof inferred.')
    save_json(directory / 'regret-review.json', report)
    print(json.dumps({k: v for k, v in report.items() if k not in ['records', 'context']}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    args = parser.parse_args()
    compare(args.audit, args.directory)
