"""Acquire a complete small material class, verifying full bytes from two sources."""

import hashlib
import json
import shutil
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = '0c6bdaccfcb3b09cdbe94b0f81e948cb2a356015'
AUTHOR = '0bb8aeee525f364bb750f96df312a1a7c9b54398'
SIZES = {
    'KRBvKR.rtbw': 2035280, 'KRBvKR.rtbz': 575440,
    'KRBvK.rtbw': 2832, 'KRBvK.rtbz': 261776,
    'KRvKB.rtbw': 32912, 'KRvKB.rtbz': 9936,
    'KRvKR.rtbw': 12944, 'KRvKR.rtbz': 3408,
}


def fetch(url, cap):
    with urllib.request.urlopen(url, timeout=60) as response:
        content = response.read(cap + 1)
    if len(content) > cap:
        raise ValueError(f'Size cap exceeded: {url}')
    return content


def main():
    out = ROOT / 'data/rook-bishop-syzygy-v1'
    if out.exists():
        raise ValueError('Immutable dataset already exists; do not replace it.')
    listing = json.loads(fetch(
        f'https://api.github.com/repos/niklasf/python-chess/contents/data/syzygy/regular?ref={FIXTURES}',
        1000000))
    entries = {item['name']: item for item in listing}
    checksums = {}
    for name in ['wdl345.txt', 'dtz345.txt']:
        raw = fetch(f'https://raw.githubusercontent.com/syzygy1/tb/{AUTHOR}/checksums/{name}', 100000)
        checksums.update(dict(line.split(': ') for line in raw.decode().splitlines() if ': ' in line))
    # Complete all network verification before creating the immutable destination.
    downloaded, rows = {}, []
    for name, size in SIZES.items():
        if name.startswith('KRBvKR.'):
            kind = 'wdl' if name.endswith('.rtbw') else 'dtz'
            url = f'https://tablebase.lichess.ovh/tables/standard/3-4-5-{kind}/{name}'
            content = fetch(url, size)
            mirror = f'http://tablebase.sesse.net/syzygy/3-4-5/{name}'
            other = fetch(mirror, size)
            if content != other:
                raise ValueError(f'Independent mirror differs: {name}')
            verification = dict(independent_mirror=mirror, entire_file_equal=True)
        else:
            url = f'https://raw.githubusercontent.com/niklasf/python-chess/{FIXTURES}/data/syzygy/regular/{name}'
            content = fetch(url, size)
            blob = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
            if blob != entries[name]['sha'] or size != entries[name]['size']:
                raise ValueError(f'Pinned Git blob mismatch: {name}')
            verification = dict(git_blob_sha1=blob, source_commit=FIXTURES)
        if len(content) != size:
            raise ValueError(f'Unexpected file size: {name}')
        downloaded[name] = content
        rows.append(dict(name=name, url=url, bytes=len(content),
                         sha256=hashlib.sha256(content).hexdigest(),
                         published_embedded_checksum=checksums[name], **verification))
    source = ROOT / 'data/elementary-syzygy'
    old = json.loads((source / 'manifest.json').read_text(encoding='utf-8'))
    old_rows = {row['name']: row for row in old['files']}
    for path in sorted(source.glob('*.rtb?')):
        content = path.read_bytes()
        if hashlib.sha256(content).hexdigest() != old_rows[path.name]['sha256']:
            raise ValueError(f'Changed elementary source: {path.name}')
        downloaded[path.name] = content
        rows.append(old_rows[path.name])
    assert len(downloaded) == 18 and sum(map(len, downloaded.values())) < 4000000
    out.mkdir(parents=True)
    for name, content in downloaded.items():
        (out / name).write_bytes(content)
    shutil.copy2(source / 'SOURCE.txt', out / 'ELEMENTARY-SOURCE.txt')
    (out / 'SOURCE.txt').write_text(
        'Generated Syzygy endgame data only; no generator or engine code copied.\n'
        'KRBvKR: public Lichess HTTPS mirror, full-file equality with independent Sesse mirror.\n'
        'Capture subtables: pinned python-chess fixtures, Git blob verified.\n'
        'Three-piece files: exact verified copies of the existing pinned dataset.\n'
        f'Generator author redistribution terms: https://github.com/syzygy1/tb/blob/{AUTHOR}/README.md\n'
        'Published embedded checksums are recorded as provenance, not recalculated by this downloader.\n'
        'Full-file SHA256 values are computed here, not falsely attributed to the generator author.\n'
        'Original elementary provenance:\n' + (source / 'SOURCE.txt').read_text(encoding='utf-8'),
        encoding='utf-8')
    manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(),
                    material_classes=['KRBvKR', 'KRBvK', 'KRvKB', 'KRvKR', 'KQvK', 'KRvK', 'KBvK', 'KNvK', 'KPvK'],
                    source_commit=FIXTURES, author_checksum_commit=AUTHOR,
                    license='Generated table data freely redistributable per original generator author README.',
                    verification='Whole-file cross-mirror equality or pinned Git blob; SHA256 for every file. Published embedded checksums recorded, not recomputed.',
                    total_table_bytes=sum(map(len, downloaded.values())), files=rows)
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(directory=str(out), files=len(downloaded), bytes=manifest['total_table_bytes'])))


if __name__ == '__main__':
    main()
