"""Frozen, resumable 120+0.5 comparison and 2400/2600 screens."""

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
    parser.add_argument('--pairs', type=int, default=4)
    parser.add_argument('--offset', type=int, default=0)
    parser.add_argument('--cycle', default='cycle-01')
    parser.add_argument('--openings', default='configs/elite-evaluation-openings.json')
    args = parser.parse_args()
    config = dict(base_ms=120000, increment_ms=500, ply_cap=600, workers=2)
    source = json.loads((ROOT / args.openings).read_text())
    openings = source if isinstance(source, list) else source['openings']
    selected = openings[args.offset:args.offset + args.pairs]
    assert len(selected) == args.pairs
    jobs = []
    families = [('incumbent', dict(opponent_path=args.opponent))] if args.stage == 'comparison' else [
        (f'stockfish:{elo}', dict(elo=elo)) for elo in [2400, 2600]]
    for family, extra in families:
        for pair, opening in enumerate(selected):
            if isinstance(opening, dict):
                opening = opening['moves']
            for white in [True, False]:
                jobs.append(dict(id=len(jobs) + 1, candidate_path=args.candidate, family=family,
                                 pair=pair, opening=opening, candidate_white=white, **extra))
    out = RUN / args.cycle / f"{args.stage}-{args.candidate.split('/')[-1]}"
    paths = {args.candidate, *([args.opponent] if args.stage == 'comparison' else [])}
    frozen = {p: manifest(ROOT / p) for p in paths}
    sources = {p: sha256(ROOT / p) for p in ['scripts/improvement_matches.py', 'scripts/fastchess_matches.py', 'harness/sandbox.py']}
    report_path = out / 'results.json'
    if report_path.exists():
        report = json.loads(report_path.read_text())
        assert report['schedule'] == jobs and report['files'] == frozen and report['source_files'] == sources
        if report['status'] == 'complete':
            return
    else:
        out.mkdir(parents=True, exist_ok=True)
        report = dict(status='running', config=config, schedule=jobs, games=[], files=frozen,
                      source_files=sources, stockfish_sha256=sha256(SF),
                      started_utc=datetime.now(timezone.utc).isoformat(),
                      scope='Development screen unless explicitly designated confirmation; prior exposed openings cannot establish fresh generalisation. Fixed 120+0.5, full losses retained.')
    done = {r['id']: r for r in report['games']}
    for job in jobs:
        path = out / f"game-{job['id']:03}.json"
        if path.exists():
            row = json.loads(path.read_text())
            assert all(row[k] == v for k, v in job.items())
            done[job['id']] = row
    report.update(status='running', games=list(done.values()))
    save_json(report_path, report)
    try:
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            pending = [pool.submit(run_game, job, config, out) for job in jobs if job['id'] not in done]
            for future in concurrent.futures.as_completed(pending):
                row = future.result()
                audit_game(row, config)
                report['games'].append(row)
                report['games'].sort(key=lambda r: r['id'])
                report['summary'] = score_summary(report['games'])
                save_json(report_path, report)
                print(f"{args.stage} {len(report['games'])}/{len(jobs)}: {row['family']} {row['score']} {row['termination']}", flush=True)
        assert frozen == {p: manifest(ROOT / p) for p in paths}
        report.update(status='complete', completed_utc=datetime.now(timezone.utc).isoformat())
    except BaseException as error:
        report.update(status='failed', error=repr(error))
        raise
    finally:
        save_json(report_path, report)


if __name__ == '__main__':
    main()
