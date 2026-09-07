"""Independently replay the completed fixed study before applying any pool change."""

import json
import statistics
from datetime import datetime, timezone

import chess

from scripts.alien_rating_ladder import save_json, sha256
from scripts.improvement_consistency import assess_blocks
from scripts.improvement_review import audited
from scripts.magnus_benchmark import manifest
from scripts.prepare_consistency_study import (
    ARCHIVE_SHA,
    CANDIDATE,
    OUT,
    catalog,
    exposure_inventory,
    make_schedule,
)
from training.fastchess_data import ROOT
from training.puzzle_verifier import duplicate_key


def read(path):
    return json.loads(path.read_text(encoding='utf-8'))


def verify_opponent_calls(game):
    """Verify one clock-controlled opponent call for every recorded opponent move."""
    board = chess.Board(game['start_fen'])
    expected = []
    for move in game['moves']:
        if board.turn != game['candidate_white']:
            expected.append(board.ply())
        board.push_uci(move['uci'])
    actual = [limit['ply'] for limit in game['uci_limits']]
    extra = 1 if game.get('failed_colour') == ('black' if game['candidate_white'] else 'white') else 0
    if actual[:len(expected)] != expected or len(actual) != len(expected) + extra:
        raise ValueError('Missing, duplicate, or unexpected clock-controlled opponent calls.')
    if game['termination'] == 'ply_cap':
        assert board.ply() >= 600 and game['score'] == .5
    for duration in game['init_ms'].values():
        assert 0 <= duration < 90000


def main():
    destination = OUT / 'consistency-review.json'
    if destination.exists():
        raise ValueError('The final review and pool update are single-use.')
    source = audited(OUT / 'results.json')
    study, starts = read(OUT / 'study.json'), read(OUT / 'starts.json')
    pool_path = ROOT / 'configs/improvement-opponent-pool.json'
    assert source['pool_sha256'] == sha256(pool_path) == sha256(OUT / 'registration.json')
    assert source['study_sha256'] == sha256(OUT / 'study.json')
    assert source['files'] == {CANDIDATE:manifest(ROOT / CANDIDATE)}
    assert sha256((ROOT / CANDIDATE).with_suffix('.zip')) == ARCHIVE_SHA
    assert source['schedule'] == study['schedule'] == make_schedule(starts)
    assert len(source['games']) == 256 and len(starts) == 64
    for name, expected in study['source_sha256'].items():
        assert sha256(ROOT / name) == expected
    assert study['starts_sha256'] == sha256(OUT / 'starts.json')
    assert study['exposure_sha256'] == sha256(OUT / 'prior-exposure.json')
    assert study['balance_sha256'] == sha256(OUT / 'balance-attempts.json')
    inventory = read(OUT / 'prior-exposure.json')
    for row in inventory['sources']:
        assert sha256(ROOT / row['path']) == row['sha256']
    rows, lookup = catalog()
    assert exposure_inventory(lookup) == inventory
    indexed = {r['source_index']:r for r in rows}
    assert not set(inventory['excluded_groups']).intersection(s['group'] for s in starts)
    assert not set(inventory['excluded_keys']).intersection(s['key'] for s in starts)
    assert len({duplicate_key(chess.Board(s['start_fen'])) for s in starts}) == 64
    for start in starts:
        assert all(start[k] == indexed[start['source_index']][k] for k in indexed[start['source_index']])
        a, b = start['small'], start['deep']
        assert a['mate'] is None and b['mate'] is None and abs(a['cp']) <= 60 and abs(b['cp']) <= 60
        assert abs(a['cp'] - b['cp']) <= 40
        for line in [a,b]:
            board = chess.Board(start['start_fen'])
            for uci in line['pv']:
                board.push_uci(uci)
    for game in source['games']:
        assert game == read(OUT / f"game-{game['id']:03}.json")
        verify_opponent_calls(game)
    readonly = ROOT / 'runs/improvement-loop-20260907/compiled-qsearch-endgames-v1-readonly.json'
    assert source['readonly_sha256'] == sha256(readonly)
    assert read(readonly)['sha256'] == ARCHIVE_SHA
    pool = read(pool_path)
    ratings = {}
    for level in [2400,2600]:
        blocks = [[g for g in source['games'] if g['elo'] == level and g['block'] == block] for block in [1,2]]
        registered = next(r for r in pool['qualification_attempts'] if r['nominal_level'] == level)
        assert registered['attempt'] == study['attempts'][str(level)] and registered['status'] == 'registered'
        result = assess_blocks(blocks, registered['attempt'], level)
        result['audits_passed'] = True
        result['uninterrupted'] = not source['interruptions']
        result['qualified'] = result['statistical_gate_passed'] and result['uninterrupted']
        result['total'] = {k:sum(b[k] for b in result['blocks']) for k in ['wins','draws','losses']}
        result['total']['score_fraction'] = (result['total']['wins'] + .5 * result['total']['draws']) / 128
        ratings[str(level)] = result
    loads = [g['host_cpu_busy_fraction'] for g in source['games'] if g.get('host_cpu_busy_fraction') is not None]
    completed = datetime.now(timezone.utc).isoformat()
    review = dict(status='complete', completed_utc=completed, candidate='v1.41', candidate_sha256=ARCHIVE_SHA,
        games=256, time_control='120+0.5', source_sha256=sha256(OUT / 'results.json'),
        study_sha256=sha256(OUT / 'study.json'), code_sha256=sha256(__file__),
        independent_audits=dict(schedule=True, runtime_source=True, clocks_increments_and_opponent_calls=True,
            legal_moves_and_pgn_outcomes=True, starting_group_exclusion=True, board_and_mirror_deduplication=True,
            frozen_readonly_archive=True, no_recorded_interruption=not source['interruptions']),
        ratings=ratings, host_load=dict(min=min(loads), median=statistics.median(loads), max=max(loads)) if loads else None,
        assumptions='Colour-paired ECO groups are operational independent clusters; related theory and shared-host load limit generalisation. No training or teacher work was scheduled during matches. Handicap settings are not calibrated human/site Elo.',
        pool_before=pool['active_nominal_levels'], pool_after=[pool['replacement_after_verified_consistency'].get(str(level), level)
            if ratings.get(str(level), {}).get('qualified') else level for level in pool['active_nominal_levels']])
    save_json(destination, review)
    for record in pool['qualification_attempts']:
        result = ratings[str(record['nominal_level'])]
        record.update(status='complete', qualified=result['qualified'], completed_utc=completed,
                      review_sha256=sha256(destination), total=result['total'], blocks=result['blocks'])
        if result['qualified']:
            pool['retired_nominal_levels'].append(record['nominal_level'])
    pool['active_nominal_levels'] = sorted(review['pool_after'])
    pool['development_focus'] = min(pool['active_nominal_levels'])
    pool['qualification_status'] = '; '.join(f"{level}: {'qualified' if result['qualified'] else 'did not qualify'}" for level,result in ratings.items())
    save_json(pool_path, pool)
    lines = ['# Independent consistency results — v1.41', '', '256 completed games at 120s + 0.5s. Full schedule, clocks, source and outcome audit passed.', '',
             '| Nominal opponent | Block | Wins | Draws | Losses | Lower outright-win bound | Passed |',
             '|---|---|---:|---:|---:|---:|---|']
    for level, result in ratings.items():
        for index, block in enumerate(result['blocks'], 1):
            lines.append(f"| {level} | {index} | {block['wins']} | {block['draws']} | {block['losses']} | {block['lower_win_bound']:.1%} | {block['statistical_gate_passed']} |")
        total = result['total']
        lines.append(f"| {level} | Total | {total['wins']} | {total['draws']} | {total['losses']} | — | {result['qualified']} |")
    lines += ['', review['assumptions'], '', 'Active pool: ' + ', '.join(map(str,pool['active_nominal_levels'])) + '.',
              'The recommended upload remains the exact v1.41 archive.']
    (OUT / 'RESULTS.md').write_text('\n'.join(lines) + '\n', encoding='utf-8', newline='\n')
    print(json.dumps(review), flush=True)


if __name__ == '__main__':
    main()
