"""Describe independently labelled student errors before choosing a value-fit change."""
import json
from collections import Counter
from pathlib import Path
from statistics import mean, median

from scripts.daytime_common import RUN, digest, save

SOURCE = RUN / 'student-descendants-03'
OUT = RUN / 'student-value-diagnosis-03'


def distribution(values):
    return dict(n=len(values), mean=float(mean(values)) if values else None,
                median=float(median(values)) if values else None,
                maximum=float(max(values)) if values else None)


def run():
    assert not OUT.exists(), 'Preserve consumed diagnoses.'
    prep_path, student_path, teacher_path = [SOURCE / f'{name}.json'
        for name in ('preparation', 'student', 'teacher')]
    prep, student, teacher = [json.loads(p.read_text())
        for p in (prep_path, student_path, teacher_path)]
    assert student['status'] == teacher['status'] == 'complete'
    assert student['frozen_candidate'] and teacher['student_sha256'] == digest(student_path)
    assert len(student['leaves']) == len(teacher['rows']) <= prep['max_leaves']
    by_id = {row['id']: row for row in teacher['rows']}
    assert len(by_id) == len(teacher['rows'])
    rows, cohort_counts = [], Counter()
    for source in teacher['rows']:
        labels = source.get('teacher', [])
        finite = len(labels) == 2 and all(r['cp'] is not None and r['mate'] is None for r in labels)
        row = dict(id=source['id'], root_id=source['root_id'], fen=source['fen'],
            origins=source['origins'], terminal=source['terminal'], eligible=source['eligible'],
            finite_teacher=finite, teacher=labels, static_stm_cp=source['static_stm_cp'],
            quiescence=source.get('quiescence'))
        if finite:
            target = mean(r['cp'] for r in labels)
            row.update(teacher_mean_stm_cp=target,
                static_error_cp=source['static_stm_cp']-target,
                teacher_disagreement_cp=abs(labels[0]['cp']-labels[1]['cp']))
            q = source.get('quiescence', {})
            if q.get('complete') and q.get('score_stm_cp') is not None:
                row['quiescence_error_cp'] = q['score_stm_cp']-target
            if source['eligible']:
                residual = source['target_stm_cp']-source['static_stm_cp']
                cohort_counts['negative' if residual <= -25 else 'positive' if residual >= 25 else 'near_zero'] += 1
        rows.append(row)
    by_diagnostic_id = {r['id']: r for r in rows}
    branches = []
    for branch in student['branches']:
        leaves = [by_diagnostic_id[key] for key in dict.fromkeys(branch['leaf_ids'])]
        branches.append(dict(root_id=branch['root_id'], branch=branch['branch'],
            depth=branch['depth'], full_requested_depth=branch['full_requested_depth'],
            stop=branch.get('stop'), nodes=branch['nodes'], seconds=branch['seconds'],
            score_root=branch['score_root'], leaves=len(leaves),
            eligible=sum(r['eligible'] for r in leaves),
            static_absolute_error=distribution([abs(r['static_error_cp']) for r in leaves if 'static_error_cp' in r]),
            quiescence_absolute_error=distribution([abs(r['quiescence_error_cp']) for r in leaves if 'quiescence_error_cp' in r])))
    matched = [r for r in rows if r['eligible'] and 'quiescence_error_cp' in r]
    result = dict(status='complete', selected_version=prep['selected_version'], selected_sha256=prep['selected_sha256'],
        source_sha256={str(p): digest(p) for p in (prep_path,student_path,teacher_path,Path(__file__))},
        independent_teacher_nodes=teacher['requested_teacher_nodes'],
        scope='Exposed diagnostic positions with independent labels; no fit, held-out validation or rating claim.',
        total_leaves=len(rows), eligible=sum(r['eligible'] for r in rows),
        correction_cohorts=dict(cohort_counts),
        matched_eligible_static_absolute_error=distribution([abs(r['static_error_cp']) for r in matched]),
        matched_eligible_quiescence_absolute_error=distribution([abs(r['quiescence_error_cp']) for r in matched]),
        branches=branches, rows=rows,
        largest_eligible_static_errors=[r['id'] for r in sorted((r for r in rows if r['eligible']),
            key=lambda r:abs(r['static_error_cp']), reverse=True)[:12]])
    save(OUT / 'diagnosis.json', result)
    print(json.dumps({k:v for k,v in result.items() if k not in ('rows','source_sha256')}), flush=True)


if __name__ == '__main__':
    run()
