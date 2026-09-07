"""Promote the exact v1.41 archive only after the declared 40-game review passes."""

import argparse
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from scripts.fastchess_matches import FAILURES, score_summary
from scripts.improvement_review import audited, paired_bound
from training.fastchess_data import ROOT

RUN = ROOT / 'runs/improvement-loop-20260907/confirmation-01'
CANDIDATE = ROOT / 'candidates/compiled-qsearch-endgames-v1'
VERSION = 'v1.41'
EXPECTED = 'e4b66bd0f5a16418a49119c0547a818c3bb79a3c9e209b3eca7210907e072f63'


def main(repo):
    review = json.loads((RUN / 'review.json').read_text(encoding='utf-8'))
    assert review['status'] == 'complete' and review['eligible_for_promotion'] and not review['reasons']
    assert review['candidate'] == CANDIDATE.relative_to(ROOT).as_posix()
    reports = {stage: audited(RUN / stage / 'results.json') for stage in ['comparison', 'rated']}
    assert [len(reports[s]['games']) for s in ['comparison', 'rated']] == [24, 16]
    for stage, report in reports.items():
        assert sha256(RUN / stage / 'results.json') == review['source_sha256'][stage]
        assert score_summary(report['games']) == review[stage]
        assert all(g['termination'] not in FAILURES for g in report['games'])
    assert paired_bound(reports['comparison']['games'], 1) == review['paired_bound']
    assert review['paired_bound']['lower_score_bound'] > .5
    archive = CANDIDATE.with_suffix('.zip')
    assert sha256(archive) == review['candidate_sha256'] == EXPECTED
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None
        assert all(zipped.read(n) == (CANDIDATE / n).read_bytes() for n in zipped.namelist())
    check = json.loads((RUN.parent / 'compiled-qsearch-endgames-v1-readonly.json').read_text(encoding='utf-8'))
    assert check['sha256'] == EXPECTED and check['elementary_endgames_verified']
    assert check['init_ms'] < 90000 and check['peak_working_set_bytes'] < 2_000_000_000
    assert all(v == 'blocked' for v in check['read_only_checks'].values())
    repo = repo.resolve()
    assert (repo / '.git').is_dir()
    assert subprocess.check_output(['git', 'remote', 'get-url', 'origin'], cwd=repo, text=True).strip() == 'https://github.com/68pm/Chessathon-agent.git'
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
    public = repo / 'chessity-agent'
    registry = json.loads((public / 'versions.json').read_text(encoding='utf-8'))
    assert len(registry['versions']) == 42 and registry['recommended'] in ('v1.14', VERSION)
    selected = next(r for r in registry['versions'] if r['version'] == VERSION)
    assert sha256(public / selected['archive']) == EXPECTED
    # Every assertion above runs before changing any download or recommendation.
    selected.update(recommended=True, status='selected after independent 23W/1D/0L confirmation versus v1.14; consistent 2600 target not reached')
    for record in registry['versions']:
        if record['version'] != VERSION and record['recommended']:
            record.update(recommended=False, status='preserved former champion; superseded by v1.41 after independent confirmation')
            save_json(public / 'versions' / record['version'] / 'version.json', record)
    registry['recommended'] = VERSION
    save_json(public / 'versions' / VERSION / 'version.json', selected)
    save_json(public / 'versions.json', registry)
    shutil.copy2(archive, public / 'latest/chessity-agent.zip')
    save_json(public / 'latest/version.json', selected)
    shutil.copy2(archive, ROOT.parent / 'chessity-agent.zip')
    shutil.copy2(archive, ROOT.parent / f'chessity-agent-{VERSION}.zip')
    metadata = dict(name='chessity-agent', version=VERSION, source_candidate=CANDIDATE.name,
                    sha256=EXPECTED, time_control='120+0.5', results=review['rated'],
                    comparison=review['comparison'], read_only_checks=check['read_only_checks'],
                    selected_evidence='docs/IMPROVEMENT_RESULTS.md', goal_achieved=False)
    save_json(ROOT.parent / 'chessity-agent-version.json', metadata)
    selection = dict(status='complete', selected_path=CANDIDATE.relative_to(ROOT).as_posix(),
                     public_version=VERSION, selected_zip_sha256=EXPECTED, candidate_promoted=True,
                     previous='v1.14', comparison=review['comparison'], rated=review['rated'],
                     paired_bound=review['paired_bound'], read_only_validation=check,
                     highest_setting_defeated=review['highest_setting_defeated'], goal_achieved=False,
                     promoted_utc=datetime.now(timezone.utc).isoformat())
    save_json(RUN / 'selection.json', selection)
    evidence = ROOT / 'docs/evidence/improvement-20260907'
    for label in ['review', 'selection']:
        shutil.copy2(RUN / f'{label}.json', evidence / f'confirmation-01--{label}.json')
    for stage in ['comparison', 'rated']:
        shutil.copy2(RUN / stage / 'results.json', evidence / f'confirmation-01--{stage}--results.json')
    rows = []
    for opponent, stats in [('v1.14', review['comparison']['incumbent']), *review['rated'].items()]:
        rows.append(f"| {opponent} | {stats['wins']} | {stats['draws']} | {stats['losses']} |")
    document = '\n'.join([
        '# Current selected agent: chessity-agent v1.41', '',
        '**Recommended competition upload: v1.41.** The exact ZIP is available through the latest download. '
        'It passed the predeclared independent promotion rule over v1.14. The continuing 2600 programme remains active.', '',
        '| Opponent | Wins | Draws | Losses |', '|---|---:|---:|---:|', *rows, '',
        'All 40 games used 120+0.5 and passed legal-move, clock, increment, outcome and frozen-source audits, '
        'without runtime failures. The comparison used 12 distinct paired starting groups; the rated tests '
        'used 4 further groups in both colours. The conservative comparison score lower bound was 58.7%, '
        'above 50%, with attempt-adjusted alpha 0.025. It assumes independent groups and stable conditions.', '',
        f"Highest nominal setting defeated in this set: **{review['highest_setting_defeated']}**. "
        'These Stockfish handicap numbers are not calibrated Chess.com/FIDE ratings. This sample does not '
        'establish consistent 2600 wins or the strongest possible engine. Earlier development and failed '
        'experiments remain visible; no games were added to chase a win.', '',
        'The improvement comes from our original compiled search, faster quiescence terminal checks and '
        'exact elementary endgame tables. It preserves the previously trained Classical/Witty/Magnus root '
        'policy and bounded optional Alien preference. The new residual network did not demonstrate a '
        'matched playing-strength gain and was not merged into the selected runtime.', '',
        'Strict read-only/no-network/no-subprocess inference passed, including table probes. '
        f"Initialization was {check['init_ms']/1000:.2f}s and peak measured memory {check['peak_working_set_bytes']/1e6:.1f}MB. "
        'Only original Python source and own weights plus attributed permitted table data ship; '
        'compilation occurs in memory. The prior full suite passed 108 tests, and four additional '
        'successor-data tests passed separately.', '',
        f'ZIP SHA-256: `{EXPECTED}`. All 42 historical versions through v1.41 remain available. '
        'No competition upload or repository write-access grant was performed.', '',
        'Next: analyse the rated games and verify played-versus-preferred successor targets before '
        'another bounded learning experiment. Once used for development, these rated opening groups '
        'must not be reused as fresh confirmation. The full-project backup is refreshed separately.', '',
    ])
    # Write the current report and public copies, without altering any frozen runtime.
    (ROOT / 'docs/IMPROVEMENT_RESULTS.md').write_text(document, encoding='utf-8', newline='\n')
    (public / 'reports/IMPROVEMENT_RESULTS.md').write_text(document, encoding='utf-8', newline='\n')
    for source in evidence.glob('confirmation-01--*.json'):
        shutil.copy2(source, public / 'reports/evidence/improvement-20260907' / source.name)
    status = ('# chessity-agent\n\n**Best verified upload: v1.41 — Efficient compiled search with endgame tables.**\n\n'
              '[Download the competition ZIP](latest/chessity-agent.zip). Upload the agent ZIP directly.\n\n'
              '[Completed confirmation and actual results](reports/IMPROVEMENT_RESULTS.md): '
              '23W/1D/0L against v1.14, with rated results and limitations in the report. '
              '**Consistent 2600 strength is not established; improvement work continues.**\n\n'
              '[Search findings](reports/IMPROVEMENT_CYCLE_01.md) · [Learning critique](reports/IMPROVEMENT_CYCLE_02.md) '
              '· [Historical elite results](reports/ELITE_LEARNING_RESULTS.md)\n\n')
    readme = public / 'README.md'
    current = readme.read_text(encoding='utf-8')
    current = status + current[current.index('## Read-only runtime and repository access'):]
    for record in registry['versions']:
        if record['version'] in ('v1.14', VERSION):
            lines = current.splitlines()
            replacement = f"| [{record['version']}]({record['archive']}) | {record['title']} | {record['status']} |"
            current = '\n'.join(replacement if line.startswith(f"| [{record['version']}]") else line for line in lines) + '\n'
    readme.write_text(current, encoding='utf-8', newline='\n')
    (public / 'versions' / VERSION / 'README.md').write_text(
        '# chessity-agent v1.41\n\n**Current selected competition agent after independent confirmation.** '
        'See [results and limitations](../../reports/IMPROVEMENT_RESULTS.md). '
        'Consistent 2600 strength is not established.\n\n'
        f'ZIP: `chessity-agent-v1.41.zip`. SHA-256: `{EXPECTED}`. Source and weights match the archive.\n',
        encoding='utf-8', newline='\n')
    root_readme = repo / 'README.md'
    title = root_readme.read_text(encoding='utf-8').split('## chessity-agent releases')[0].rstrip()
    root_readme.write_text(title + '\n\n## chessity-agent releases\n\n'
        '[Download the selected agent (v1.41)](chessity-agent/latest/chessity-agent.zip) · '
        '[All 42 versions](chessity-agent/README.md) · [Actual results](chessity-agent/reports/IMPROVEMENT_RESULTS.md)\n\n'
        'v1.41 passed independent promotion over v1.14. The programme continues toward consistent 2600 wins; '
        'that target has not been reached. Inference is read-only; public visitors have read access.\n',
        encoding='utf-8', newline='\n')
    assert all(sha256(p) == EXPECTED for p in [archive, public / 'latest/chessity-agent.zip', ROOT.parent / 'chessity-agent.zip'])
    print(json.dumps(selection, indent=2), flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    main(parser.parse_args().repo)
