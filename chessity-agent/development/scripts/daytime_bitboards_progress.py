"""Audit completed screen pairs and preserve actionable root targets without more engines."""

import argparse
import json
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from scripts.daytime_common import ROOT, RUN, digest, save
from scripts.feedback_matches_windows import feedback_path
from scripts.overnight_portable_fast_screen import audit_feedback
from training.game_feedback import normalise_game


def run(out):
    out = out.resolve()
    assert out.is_relative_to(RUN) and not out.exists()
    source = RUN / 'pawn-bitboards-screen-01/state.json'
    state = json.loads(source.read_text())
    snapshot = dict(created_utc=datetime.now(timezone.utc).isoformat(),
        source_state_sha256=digest(source), source_state=state, code_sha256=digest(Path(__file__)),
        scope='Completed pairs only. Root policy examples and diagnostic targets; no descendant values or new fit.',
        matches=[], targets=[], positive_examples=[])
    phases, errors, positives = Counter(), Counter(), Counter()
    for match in state['matches']:
        path = ROOT / match['result_path']
        assert digest(path) == match['sha256']
        result = audit_feedback(path)
        folder = feedback_path(path.parent / 'postgame-feedback')
        snapshot['matches'].append(dict(label=match['label'], summary=result['summary'],
            files=result['files'], result_sha256=digest(path), game_count=len(result['games'])))
        for game in result['games']:
            _, identity = normalise_game(game)
            marker_path = folder / 'completed' / (identity['game_key'] + '.json')
            marker = json.loads(marker_path.read_text())
            review_path = folder / marker['review']
            review = json.loads(review_path.read_text())
            for row in review['rows']:
                phase = next((p for p in ('opening', 'middlegame', 'endgame') if p in row['tags']), 'unclassified')
                phases[phase] += 1
                reward = row['reward']
                if reward is None or reward == 0:
                    continue
                common = dict(match=match['label'], game_key=identity['game_key'], game_id=game['id'],
                    result=game['score'], candidate_white=game['candidate_white'], phase=phase,
                    review_sha256=digest(review_path), marker_sha256=digest(marker_path),
                    **{key:row[key] for key in ('ply','fullmove','fen','start_fen','history','played','san','label','reward','tags','policy_target','labels')})
                if reward < 0:
                    errors[phase] += 1
                    finite = all(label['best']['cp'] is not None and label['played']['cp'] is not None for label in row['labels'])
                    common.update(action='Inspect quiet mating/defensive alternatives; preserve mate labels' if not finite
                        else 'Replay verified root alternative and diagnose search/evaluation before independent descendant labelling',
                        static_value_target=None)
                    snapshot['targets'].append(common)
                else:
                    positives[phase] += 1
                    if sum(p['phase'] == phase for p in snapshot['positive_examples']) < 2:
                        snapshot['positive_examples'].append(common)
    snapshot.update(status='complete', phases=dict(phases), positive_counts=dict(positives),
        negative_counts=dict(errors), completed_pairs=len(snapshot['matches']))
    save(out / 'diagnosis.json', snapshot)
    print(json.dumps({k:snapshot[k] for k in ('status','completed_pairs','phases','positive_counts','negative_counts')}))
    print(json.dumps([dict(game=t['game_id'],move=t['fullmove'],san=t['san'],phase=t['phase'],label=t['label'],
        alternative=t['policy_target']) for t in snapshot['targets']]))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, type=Path)
    run(parser.parse_args().out)
