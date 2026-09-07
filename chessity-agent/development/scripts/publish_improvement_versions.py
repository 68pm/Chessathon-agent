"""Prepare one chronological build or a progress snapshot; never pushes or promotes."""

import argparse
import json
import shutil
import subprocess
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT

BUILDS = [
    ('compiled-search-v1', 'Original compiled search preflight', 'failed Windows import preflight; archival only; do not upload', None),
    ('compiled-search-v2', 'Original compiled classical search', '8W0D0L versus v1.14 in development; not independently promoted', 'compiled-search-v2-readonly.json'),
    ('compiled-residual-v1', 'Original trained leaf residual evaluator', '2W4D2L versus compiled control; no demonstrated gain; not promoted', 'compiled-residual-v1-readonly.json'),
    ('compiled-endgames-v1', 'Compiled search with elementary endgame tables', 'conversion drills and read-only checks passed; no ordinary matches', 'compiled-endgames-v1-full-readonly.json'),
    ('compiled-residual-incremental-v1', 'Incremental residual evaluation', 'numerical and read-only checks passed; no ordinary matches', 'compiled-residual-incremental-v1-readonly.json'),
    ('compiled-qsearch-v1', 'Efficient quiescence terminal checks', 'fixed-node parity and read-only checks passed; no ordinary matches', 'compiled-qsearch-v1-readonly.json'),
    ('compiled-qsearch-endgames-v1', 'Efficient compiled search with endgame tables', 'independent confirmation in progress; not yet promoted', 'compiled-qsearch-endgames-v1-readonly.json'),
    ('compiled-reductions-v1', 'Conservative late quiet move reductions', '1W5D2L versus v1.41 in development; rated screen continuing; not promoted', 'compiled-reductions-v1-readonly.json'),
    ('compiled-rook-bishop-v1', 'Verified rook-bishop conversion tables', 'conversion and read-only checks passed; ordinary matches queued; not promoted', 'compiled-rook-bishop-v1-readonly.json'),
    ('compiled-transposition-hints-v1', 'History-safe transposition move ordering', 'correctness, diagnostic and read-only gates passed; fixed development matches running; not promoted', 'compiled-transposition-hints-v1-readonly.json'),
    ('compiled-paired-score-control-v1', 'Matched score-only residual learning control', 'six-epoch own-trained control; read-only and model-parity checks passed; experimental', 'compiled-paired-score-control-v1-readonly.json'),
    ('compiled-paired-ranking-v1', 'Verified counterfactual preference learning', 'matched static learning gate passed; runtime search gate in progress; not promoted', 'compiled-paired-ranking-v1-readonly.json'),
    ('compiled-paired-quarter-v1', 'Calibrated quarter-weight learned evaluation', 'fixed selected-move regret and read-only gates passed; 16 development games queued; not promoted', 'compiled-paired-quarter-v1-readonly.json'),
]


def add_build(repo, index):
    assert 35 <= index <= 47
    public = repo / 'chessity-agent'
    registry = json.loads((public / 'versions.json').read_text(encoding='utf-8'))
    assert len(registry['versions']) == index
    incumbent = registry['recommended']
    assert incumbent == ('v1.14' if index <= 41 else 'v1.41')
    incumbent_sha = next(row['sha256'] for row in registry['versions'] if row['version'] == incumbent)
    preserved_archives = {row['archive']: row['sha256'] for row in registry['versions']}
    assert all(sha256(public / path) == digest for path, digest in preserved_archives.items())
    candidate, title, status, probe = BUILDS[index - 35]
    source = ROOT / 'candidates' / candidate
    original = source.with_suffix('.zip')
    version = f'v1.{index}'
    destination = public / 'versions' / version
    assert not destination.exists()
    manifest = json.loads(source.with_suffix('.manifest.json').read_text(encoding='utf-8'))
    assert manifest['sha256'] == sha256(original)
    check = None
    if probe:
        check = json.loads((ROOT / 'runs/improvement-loop-20260907' / probe).read_text(encoding='utf-8'))
        assert check['sha256'] == manifest['sha256']
        assert all(v == 'blocked' for v in check['read_only_checks'].values())
    destination.mkdir(parents=True)
    archive = destination / f'chessity-agent-{version}.zip'
    shutil.copy2(original, archive)
    with zipfile.ZipFile(archive) as zipped:
        assert zipped.testzip() is None and sum(i.file_size for i in zipped.infolist()) < 50_000_000
        for name in zipped.namelist():
            path = Path(name)
            assert not path.is_absolute() and '..' not in path.parts
            assert path.suffix in {'.py', '.json', '.npz', '.txt', '.rtbw', '.rtbz'}
            assert zipped.read(name) == (source / name).read_bytes()
        zipped.extractall(destination / 'source')
    if check:
        save_json(destination / 'read-only-check.json', check)
    else:
        save_json(destination / 'failed-preflight.json', dict(status='failed',
                  reason='Windows Python platform fallback spawned a hostname subprocess during Numba import; strict audit rejected it. Fixed in v1.36 without relaxing the audit.',
                  games_played=0, recommended=False))
    record = dict(version=version, name='chessity-agent', title=title, status=status,
                  recommended=False, source_version=f'candidates/{candidate}', sha256=sha256(archive),
                  zip_bytes=archive.stat().st_size, created_utc=datetime.fromtimestamp(original.stat().st_ctime, timezone.utc).isoformat(),
                  archive=f'versions/{version}/{archive.name}', read_only_smoke_calls=check['legal_calls'] if check else 0,
                  read_only_status='passed' if check else 'failed', archive_json_formatting_differs_from_local_folder=[])
    save_json(destination / 'version.json', record)
    (destination / 'README.md').write_text(
        f'# chessity-agent {version}\n\n{title}. **Status: {status}.**\n\n'
        f'Archive: `{archive.name}`. SHA-256: `{record["sha256"]}`. Source and own trained weights '
        'beside the ZIP match its bytes. A later version number does not establish stronger play. '
        f'The recommended download remains {incumbent} until independent confirmation supports promotion.\n\n'
        'This experiment uses original Python source with the permitted in-memory Numba compiler. '
        'No external chess engine implementation, native executable or pretrained chess network is shipped. '
        'Table-enabled builds contain permitted Syzygy data with source attribution.\n',
        encoding='utf-8', newline='\n')
    registry['versions'].append(record)
    save_json(public / 'versions.json', registry)
    readme = public / 'README.md'
    text = readme.read_text(encoding='utf-8')
    marker = '\nAll '
    row = f'| [{version}]({record["archive"]}) | {title} | {status} |\n'
    assert marker in text
    text = text[:text.index(marker)].rstrip() + '\n' + row + '\n' + (
        f'All {len(registry["versions"])} versions are retained in development order with version tags. '
        'Source and own trained weights beside each ZIP match its bytes. v1.35 is a failed preflight '
        'preserved for audit and should not be uploaded. New experimental versions are not automatically '
        'recommended. Downloaded raw player histories and external engine executables are excluded.\n')
    readme.write_text(text, encoding='utf-8', newline='\n')
    root_readme = repo / 'README.md'
    root_readme.write_text(root_readme.read_text(encoding='utf-8').replace(
        f'All {index} versions', f'All {index + 1} versions'), encoding='utf-8', newline='\n')
    assert sha256(public / 'latest/chessity-agent.zip') == incumbent_sha
    assert all(sha256(public / path) == digest for path, digest in preserved_archives.items())
    print(json.dumps(record), flush=True)


def reports(repo):
    public = repo / 'chessity-agent'
    for directory in ['experiments', 'training', 'scripts', 'configs', 'tests']:
        for source in (ROOT / directory).rglob('*'):
            if source.is_file() and source.suffix in {'.py', '.json'} and '__pycache__' not in source.parts:
                target = public / 'development' / source.relative_to(ROOT)
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_text(source.read_text(encoding='utf-8'), encoding='utf-8', newline='\n')
    shutil.copy2(ROOT / 'requirements-compiled.txt', public / 'development/requirements-compiled.txt')
    for source in (ROOT / 'docs').glob('IMPROVEMENT_*.md'):
        shutil.copy2(source, public / 'reports' / source.name)
    for source in (ROOT / 'docs/evidence/improvement-20260907').glob('*.json'):
        target = public / 'reports/evidence/improvement-20260907' / source.name
        target.parent.mkdir(parents=True, exist_ok=True)
        data = json.loads(source.read_text(encoding='utf-8'))
        if source.name.endswith('dataset-manifest.json'):
            data.pop('rows', None)
            data['public_export_note'] = 'Raw training-position rows retained locally; provenance, counts and hashes published.'
        save_json(target, data)
    readme = public / 'README.md'
    text = readme.read_text(encoding='utf-8')
    note = ('The new improvement programme is active. Original compiled search scored 8W/0D/0L against v1.14 '
            'in development, 1W/1D/2L at nominal 2400 and 0W/1D/3L at nominal 2600. The newly trained leaf '
            'network tied its compiled control 2W/4D/2L, then scored 1W/0D/3L at 2400 and 0W/0D/4L at 2600. '
            'Independent confirmation of the faster classical build is in progress. **Consistent 2600 strength '
            'has not been achieved.** These settings are not calibrated human/site Elo.\n\n'
            '[Search findings](reports/IMPROVEMENT_CYCLE_01.md) · [Learning critique](reports/IMPROVEMENT_CYCLE_02.md) '
            '· [Fixed confirmation plan](reports/IMPROVEMENT_CONFIRMATION_01.md)\n\n')
    text = text.replace('## Read-only runtime and repository access', note + '## Read-only runtime and repository access', 1)
    readme.write_text(text, encoding='utf-8', newline='\n')
    root_readme = repo / 'README.md'
    text = root_readme.read_text(encoding='utf-8')
    text += ('\n[Active search and learning improvements, versions v1.35–v1.41]'
             '(chessity-agent/reports/IMPROVEMENT_CYCLE_01.md). Independent confirmation is in progress; '
             'the recommended download remains v1.14. v1.35 is an archived failed preflight.\n')
    root_readme.write_text(text, encoding='utf-8', newline='\n')
    print('Prepared completed evidence, own development code and active-programme snapshot', flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--repo', type=Path, required=True)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--index', type=int)
    group.add_argument('--reports', action='store_true')
    args = parser.parse_args()
    repo = args.repo.resolve()
    assert (repo / '.git').is_dir()
    assert not subprocess.check_output(['git', 'status', '--porcelain'], cwd=repo, text=True).strip()
    reports(repo) if args.reports else add_build(repo, args.index)
