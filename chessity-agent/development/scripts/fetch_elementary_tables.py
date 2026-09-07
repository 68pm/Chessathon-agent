"""Download small public Syzygy data fixtures with pinned Git blob verification."""

import hashlib
import json
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def main():
    api = 'https://api.github.com/repos/niklasf/python-chess'
    with urllib.request.urlopen(api + '/commits/master', timeout=30) as response:
        commit = json.load(response)['sha']
    with urllib.request.urlopen(api + '/contents/data/syzygy/regular?ref=' + commit, timeout=30) as response:
        listing = json.load(response)
    out = ROOT / 'data/elementary-syzygy'
    out.mkdir(exist_ok=True)
    rows = []
    for entry in listing:
        name = entry['name']
        if name.split('.')[0] not in {'KQvK', 'KRvK', 'KPvK', 'KBvK', 'KNvK'} and name != 'SOURCE.txt':
            continue
        assert entry['size'] < 100000
        url = f'https://raw.githubusercontent.com/niklasf/python-chess/{commit}/data/syzygy/regular/{name}'
        with urllib.request.urlopen(url, timeout=30) as response:
            content = response.read(100001)
        assert len(content) == entry['size']
        blob = hashlib.sha1(f'blob {len(content)}\0'.encode() + content).hexdigest()
        assert blob == entry['sha']
        if (out / name).exists():
            assert (out / name).read_bytes() == content
        else:
            (out / name).write_bytes(content)
        rows.append(dict(name=name, url=url, bytes=len(content), git_blob_sha1=blob,
                         sha256=hashlib.sha256(content).hexdigest()))
    (out / 'manifest.json').write_text(json.dumps(dict(source_commit=commit, files=rows,
        provenance='Syzygy data fixtures from the python-chess maintainer; see SOURCE.txt. No engine code copied.',
        use='Elementary three-piece endgame data. Explicitly permitted by https://aichessathon.com/docs.'), indent=2) + '\n', encoding='utf-8')
    print(json.dumps(dict(files=len(rows), total_bytes=sum(r['bytes'] for r in rows), commit=commit)))


if __name__ == '__main__':
    main()
