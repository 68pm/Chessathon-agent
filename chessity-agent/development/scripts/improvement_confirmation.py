"""Independent frozen confirmation from balanced held-out-ECO starting FENs."""

import argparse
import concurrent.futures
import json
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import run_game, score_summary
from scripts.magnus_benchmark import SF, manifest
from scripts.record_fastchess import audit_game
from training.fastchess_data import ROOT

RUN = ROOT / 'runs/improvement-loop-20260907'


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--candidate', required=True)
    parser.add_argument('--opponent', default='candidates/classical-witty-magnus-v1')
    parser.add_argument('--stage', choices=['comparison', 'rated'], required=True)
    parser.add_argument('--pairs', type=int, default=12)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--label', required=True)
    args = parser.parse_args()
    source = RUN / 'confirmation-starts/starts.json'
    starts = json.loads(source.read_text())[args.offset:args.offset + args.pairs]
    assert len(starts) == args.pairs
    assert len({s['group'] for s in starts}) == len(starts)
    config = dict(base_ms=120000, increment_ms=500, ply_cap=600, workers=2)
    families = [('incumbent', dict(opponent_path=args.opponent))] if args.stage == 'comparison' else [
        (f'stockfish:{elo}', dict(elo=elo)) for elo in [2400, 2600]]
    jobs = []
    for family, extra in families:
        for pair, start in enumerate(starts):
            for white in [True, False]:
                jobs.append(dict(id=len(jobs) + 1, family=family, pair=pair, opening=[],
                                 start_fen=start['start_fen'], opening_group=start['group'],
                                 candidate_path=args.candidate, candidate_white=white, **extra))
    out = RUN / args.label / args.stage
    out.mkdir(parents=True, exist_ok=True)
    paths = {args.candidate, *([args.opponent] if args.stage == 'comparison' else [])}
    frozen = {p: manifest(ROOT / p) for p in paths}
    sources = {p: sha256(ROOT / p) for p in ['scripts/improvement_confirmation.py',
               'scripts/fastchess_matches.py', 'harness/sandbox.py', 'scripts/record_fastchess.py']}
    path = out / 'results.json'
    if path.exists():
        report = json.loads(path.read_text())
        assert report['schedule'] == jobs and report['files'] == frozen and report['source_files'] == sources
        assert report['starts_sha256'] == sha256(source)
        if report['status'] == 'complete':
            return
    else:
        report = dict(status='running', config=config, schedule=jobs, games=[], files=frozen,
                      source_files=sources, starts_sha256=sha256(source), stockfish_sha256=sha256(SF),
                      started_utc=datetime.now(timezone.utc).isoformat(),
                      scope='Frozen weights/source. New balanced starting FENs from held-out ECO groups, one family per colour pair. Prior root policies may know related opening theory. Nominal engine settings, not human/site ratings. No teacher/training CPU work scheduled during confirmation.')
    done = {r['id']: r for r in report['games']}
    for job in jobs:
        game_path = out / f"game-{job['id']:03}.json"
        if game_path.exists():
            row = json.loads(game_path.read_text())
            assert all(row[k] == v for k, v in job.items())
            audit_game(row, config)
            done[job['id']] = row
    report.update(status='running', games=sorted(done.values(), key=lambda r: r['id']))
    save_json(path, report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            futures = [pool.submit(run_game, job, config, out) for job in jobs if job['id'] not in done]
            for future in concurrent.futures.as_completed(futures):
                row = future.result()
                audit_game(row, config)
                report['games'].append(row)
                report['games'].sort(key=lambda r: r['id'])
                report['summary'] = score_summary(report['games'])
                save_json(path, report)
                print(f"{args.label}/{args.stage} {len(report['games'])}/{len(jobs)}: {row['family']} {row['score']}", flush=True)
        assert frozen == {p: manifest(ROOT / p) for p in paths}
        assert sources == {p: sha256(ROOT / p) for p in sources}
        report.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(path, report)


if __name__ == '__main__':
    main()
