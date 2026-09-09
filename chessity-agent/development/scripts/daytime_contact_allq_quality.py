"""Review bounded quiet-mate clock choices before any playing test."""
import argparse
import json
import statistics
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, check_stop, digest, manifest, save

SOURCE = ROOT / 'runs/daytime-20260909/contact-allq-02'
OUT = ROOT / 'runs/daytime-20260909/contact-allq-quality-02'


def prepare():
    check_stop()
    assert not OUT.exists()
    state = json.loads((SOURCE / 'state.json').read_text())
    assert state['status'] == 'complete' and state['passed']
    assert json.loads((SOURCE.parent / 'contact-allq-measure-supervisor-02/supervisor.json').read_text())['status'] == 'complete'
    prep = json.loads((SOURCE / 'preparation.json').read_text())
    assert all(manifest(ROOT / p) == prep['candidate_files'][label]
               for label, p in prep['candidates'].items())
    save(OUT / 'preparation.json', dict(source=str(SOURCE.relative_to(ROOT)),
        files={str(p.relative_to(ROOT)): digest(p) for p in
               (SOURCE / 'state.json', SOURCE / 'preparation.json', Path(__file__),
                ROOT / 'scripts/daytime_common.py')},
        rule='Strictly lower three-second mean finite regret at both budgets, no new major/mate regressions at either time budget, at least one sacrificed Bxh7+ root repaired in both repeats.',
        budgets=[80000, 320000], scope='Exposed development clock probes, not independent strength evidence.'))
    print('Prepared clock-choice review', flush=True)


def run():
    import chess

    from scripts.overnight_capacity import wait_for_capacity
    from training import game_feedback

    prep = json.loads((OUT / 'preparation.json').read_text())
    assert not (OUT / 'state.json').exists()
    assert all(digest(ROOT / p) == h for p, h in prep['files'].items())
    source = json.loads((SOURCE / 'state.json').read_text())
    original = json.loads((SOURCE / 'preparation.json').read_text())
    check_stop()
    wait_for_capacity(OUT / 'capacity.json', minimum_memory_mb=1400, wait_seconds=120)
    game_feedback.stop_check = check_stop
    teacher = game_feedback.CachedTeacher(ROOT / 'data/postgame-feedback/cache-v1', OUT)
    result = dict(status='running', passed=False, review=[])
    save(OUT / 'state.json', result)
    try:
        for index, root in enumerate(original['roots']):
            check_stop()
            board = chess.Board(root['start_fen'])
            for uci in root['history']:
                board.push_uci(uci)
            assert board.fen() == root['fen']
            choices = [r for r in source['rows'] if r['root'] == index ]
            assert len(choices) == 8
            bests = [teacher.analyse(board, budget) for budget in prep['budgets']]
            values = {uci: [best if best['pv'][0] == uci else teacher.analyse(
                board, budget, chess.Move.from_uci(uci)) for budget, best in
                zip(prep['budgets'], bests, strict=True)] for uci in sorted({c['uci'] for c in choices})}
            reviewed = []
            for choice in choices:
                selected = values[choice['uci']]
                regret = [max(0, a['cp'] - b['cp']) if a['cp'] is not None and b['cp'] is not None else None
                          for a, b in zip(bests, selected, strict=True)]
                reviewed.append(dict(**choice, values=selected, regret_cp=regret,
                    major=all(v is not None and v >= 200 for v in regret),
                    mate_loss=any(v['mate'] is not None and v['mate'] < 0 for v in selected)))
            result['review'].append(dict(id=root['id'], best=bests, choices=reviewed))
            save(OUT / 'state.json', result)
            print(f'{index + 1}/{len(original["roots"])} clock roots reviewed', flush=True)
        finite = [r for r in result['review'] if all(v is not None for c in r['choices']
            if c['regime']=='three_second' for v in c['regret_cp'])]
        assert finite
        means = {label:[statistics.mean(c['regret_cp'][i] for r in finite for c in r['choices']
            if c['label']==label and c['regime']=='three_second') for i in range(2)]
            for label in ('baseline','prototype')}
        regressions={field:[] for field in ('major','mate_loss')}
        for root in result['review']:
            for regime in ('one_second','three_second'):
                choices=[c for c in root['choices'] if c['regime']==regime]
                for field in regressions:
                    if sum(c[field] for c in choices if c['label']=='prototype') > sum(c[field] for c in choices if c['label']=='baseline'):
                        regressions[field].append(root['id']+':'+regime)
        repaired=[]
        for identity,target in original['sacrifice_roots'].items():
            root=next(r for r in result['review'] if r['id']==identity)
            choices=[c for c in root['choices'] if c['label']=='prototype' and c['regime']=='three_second']
            if all(c['uci']==target for c in choices) and all(b['pv'][0]==target for b in root['best']):
                repaired.append(identity)
        passed=bool(repaired) and not any(regressions.values()) and all(a < b for a,b in zip(means['prototype'],means['baseline'],strict=True))
        result.update(status='complete',passed=passed,mean_regret_cp=means,finite_roots=len(finite),
            regressions=regressions,repaired_sacrifices=repaired,
            decision='eligible_short_match_screen' if passed else 'retain_v155_and_diagnose')
    except BaseException as error:
        result.update(status='failed', error=repr(error))
        raise
    finally:
        teacher.close()
        result['requested_teacher_nodes'] = teacher.requested_nodes
        result['finished_utc'] = datetime.now(timezone.utc).isoformat()
        result['frozen_candidates'] = all(manifest(ROOT / p) == original['candidate_files'][label]
                                          for label, p in original['candidates'].items())
        if not result['frozen_candidates']:
            result.update(status='failed', passed=False, error='Playing source changed')
        save(OUT / 'state.json', result)
        print(json.dumps({k:v for k,v in result.items() if k != 'review'}), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--prepare', action='store_true')
    args = parser.parse_args()
    prepare() if args.prepare else run()
