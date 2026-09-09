"""Summarise completed public feedback without fitting or new engine work."""
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import chess

from scripts.daytime_common import ROOT, RUN, digest, save

SOURCE = RUN / 'field-07'
OUT = RUN / 'field-diagnosis-02'


def run():
    assert not OUT.exists(), 'Keep consumed diagnoses immutable.'
    source = json.loads((SOURCE / 'state.json').read_text())
    supervisor = RUN / 'field-supervisor-08/supervisor.json'
    assert source['status'] == 'complete'
    assert json.loads(supervisor.read_text())['status'] == 'complete'
    result = dict(status='complete', created_utc=datetime.now(timezone.utc).isoformat(),
        source_sha256={str(p.relative_to(ROOT)):digest(p) for p in
            (Path(__file__), SOURCE/'state.json', supervisor)}, games=[],
        scope='Public games with unverified submission hashes. Development diagnostics, not current-release strength evidence.')
    for label in ('own', 'leader'):
        for path in sorted((SOURCE/(label+'-review/games')).glob('*/review.json')):
            review = json.loads(path.read_text())
            assert review['status'] == 'complete'
            identity = review['identity']['game']
            negatives, uncertain = [], []
            for row in review['rows']:
                if (row.get('reward') or 0) < 0:
                    board = chess.Board(row['fen'])
                    target = row.get('policy_target')
                    negatives.append(dict(**row, target_san=board.san(chess.Move.from_uci(target)) if target else None))
                elif row.get('reward') is None:
                    uncertain.append({k:row.get(k) for k in ('fullmove','white','san','label','confidence')})
            result['source_sha256'][str(path.relative_to(ROOT))] = digest(path)
            result['games'].append(dict(label=label, identity=identity,
                rows=len(review['rows']), rewarded=review['rewarded'], penalised=review['penalised'],
                labels=dict(Counter(r['label'] for r in review['rows'])),
                negative_phases=dict(Counter(t for r in negatives for t in r['tags']
                    if t in ('opening','middlegame','endgame'))),
                negatives=negatives, uncertain=uncertain))
    result['totals'] = {label:{k:sum(g[k] for g in result['games'] if g['label']==label)
        for k in ('rows','rewarded','penalised')} for label in ('own','leader')}
    save(OUT/'diagnosis.json', result)
    print(json.dumps(dict(status=result['status'], totals=result['totals'],
        games=[{k:g[k] for k in ('label','labels','negative_phases')} for g in result['games']])))


if __name__ == '__main__':
    run()
