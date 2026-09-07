"""Frozen, serial120+0.5 diagnostics with a bounded host-memory guard."""
import argparse
import json
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_pool_matches import selected_levels
from scripts.magnus_benchmark import SF, manifest
from scripts.overnight_game import run_game, score_summary
from scripts.overnight_resources import wait_for_memory
from scripts.record_fastchess import audit_game
from training.fastchess_data import ROOT


def audited(path):
    report = json.loads(path.read_text())
    assert report['status'] == 'complete'
    assert report['config'] == dict(base_ms=120000,increment_ms=500,ply_cap=600,workers=1)
    assert len(report['games']) == len(report['schedule'])
    schedule = {g['id']:g for g in report['schedule']}
    assert len(schedule) == len(report['schedule'])
    assert {g['id'] for g in report['games']} == set(schedule)
    for game in report['games']:
        assert all(game[k] == v for k,v in schedule[game['id']].items())
        audit_game(game,report['config'])
    assert report['files'] == {p:manifest(ROOT / p) for p in report['files']}
    assert report['source_files'] == {p:sha256(ROOT / p) for p in report['source_files']}
    assert report['stockfish_sha256'] == sha256(SF)
    assert report['opponent_pool_sha256'] == sha256(ROOT / report['opponent_pool_path'])
    assert report['openings_sha256'] == sha256(ROOT / report['openings_path'])
    return report


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--candidate',required=True)
    p.add_argument('--opponent',default='candidates/compiled-qsearch-endgames-v1')
    p.add_argument('--stage',choices=['rated','comparison'],required=True)
    p.add_argument('--pairs',type=int,default=1)
    p.add_argument('--offset',type=int,default=0)
    p.add_argument('--cycle',required=True)
    p.add_argument('--openings',required=True)
    p.add_argument('--pool',default='configs/overnight-opponent-pool.json')
    p.add_argument('--levels',type=int,nargs='+')
    args = p.parse_args()
    assert args.pairs > 0 and args.offset >= 0
    pool = json.loads((ROOT / args.pool).read_text())
    levels = selected_levels(pool,args.levels)
    starts = json.loads((ROOT / args.openings).read_text())['openings'][args.offset:args.offset+args.pairs]
    assert len(starts) == args.pairs
    families = [('incumbent',dict(opponent_path=args.opponent))] if args.stage == 'comparison' else [
        (f'stockfish:{level}',dict(elo=level)) for level in levels]
    jobs = []
    for family, extra in families:
        for pair, opening in enumerate(starts):
            for white in [True,False]:
                jobs.append(dict(id=len(jobs)+1,candidate_path=args.candidate,family=family,pair=pair,
                    opening=opening['moves'],opening_group=opening['group'],candidate_white=white,**extra))
    config = dict(base_ms=120000,increment_ms=500,ply_cap=600,workers=1)
    out = ROOT / 'runs/improvement-loop-20260907' / args.cycle / f'{args.stage}-{Path(args.candidate).name}'
    out.mkdir(parents=True,exist_ok=True)
    path = out / 'results.json'
    paths = {args.candidate,*([args.opponent] if args.stage == 'comparison' else [])}
    frozen = {folder:manifest(ROOT / folder) for folder in paths}
    source_files = {name:sha256(ROOT / name) for name in ['scripts/overnight_matches.py',
        'scripts/overnight_game.py','scripts/overnight_resources.py','harness/sandbox.py',
        'scripts/record_fastchess.py','scripts/improvement_pool_matches.py']}
    immutable = dict(config=config,schedule=jobs,files=frozen,source_files=source_files,
        opponent_pool=pool,opponent_pool_path=args.pool,opponent_pool_sha256=sha256(ROOT / args.pool),
        openings_path=args.openings,openings_sha256=sha256(ROOT / args.openings),selected_levels=levels,
        stockfish_sha256=sha256(SF))
    if path.exists():
        report = json.loads(path.read_text())
        assert all(report[k] == v for k,v in immutable.items())
        if report['status'] == 'complete':
            audited(path)
            return
    else:
        report = dict(**immutable,status='running',games=[],started_utc=datetime.now(timezone.utc).isoformat(),
            scope='Serial local diagnostic after preserved operational failures. All losses retained; startup/flag wins do not establish playing strength. Not a calibrated Elo test.')
    done = {g['id']:g for g in report['games']}
    for job in jobs:
        saved = out / f"game-{job['id']:03}.json"
        if saved.exists():
            row = json.loads(saved.read_text())
            assert all(row[k] == v for k,v in job.items())
            audit_game(row,config)
            done[job['id']] = row
    report.update(status='running',games=sorted(done.values(),key=lambda r:r['id']))
    save_json(path,report)
    try:
        for job in jobs:
            if job['id'] in done:
                continue
            wait_for_memory(out / 'resources.json')
            row = run_game(job,config,out)
            audit_game(row,config)
            report['games'].append(row)
            report['summary'] = score_summary(report['games'])
            save_json(path,report)
            print(f"{len(report['games'])}/{len(jobs)}: {row['family']} score={row['score']} termination={row['termination']}",flush=True)
        report.update(status='complete',completed_utc=datetime.now(timezone.utc).isoformat())
        save_json(path,report)
        audited(path)
    except BaseException as error:
        report.update(status='failed',error=repr(error))
        raise
    finally:
        save_json(path,report)


if __name__ == '__main__':
    main()
