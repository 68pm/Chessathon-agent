"""Create an atomic local project snapshot while improvement workers are idle."""

import hashlib
import json
import os
import time
import zipfile
from datetime import datetime, timezone

from scripts.alien_rating_ladder import save_json, sha256
from training.fastchess_data import ROOT


def main():
    run = ROOT / 'runs/improvement-loop-20260907'
    for controller in run.glob('**/controller.json'):
        state = json.loads(controller.read_text(encoding='utf-8'))
        assert state['status'] in ('complete', 'failed'), f'Controller still active: {controller}'
    excluded = {'.git', '.venv', '__pycache__', '.pytest_cache', '.ruff_cache'}
    paths = sorted(p for p in ROOT.rglob('*') if p.is_file()
                   and not (set(p.relative_to(ROOT).parts) & excluded)
                   and p.suffix not in ('.pyc', '.tmp', '.lock'))
    destination = (ROOT.parent / 'chess-agent-project.zip').resolve()
    pending = (ROOT.parent / 'chess-agent-project.pending.zip').resolve()
    assert destination.parent == pending.parent == ROOT.parent.resolve()
    assert ROOT.resolve().is_relative_to(destination.parent)
    records = []
    with zipfile.ZipFile(pending, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=3) as zipped:
        for path in paths:
            before = path.stat()
            identity = path.relative_to(ROOT).as_posix()
            date = time.localtime(before.st_mtime)[:6]
            info = zipfile.ZipInfo(identity, date_time=date)
            info.compress_type = zipfile.ZIP_DEFLATED
            digest = hashlib.sha256()
            with path.open('rb') as source, zipped.open(info, 'w', force_zip64=True) as target:
                for chunk in iter(lambda: source.read(1 << 20), b''):
                    digest.update(chunk)
                    target.write(chunk)
            after = path.stat()
            assert (before.st_size, before.st_mtime_ns) == (after.st_size, after.st_mtime_ns), identity
            records.append(dict(path=identity, bytes=before.st_size, sha256=digest.hexdigest()))
        manifest = dict(created_utc=datetime.now(timezone.utc).isoformat(), files=records,
                        scope='Local full project snapshot. Includes local data/evidence; not a competition upload or public raw-data export. Excludes Git history, environments and caches.')
        zipped.writestr('BACKUP_MANIFEST.json', json.dumps(manifest, indent=2))
    with zipfile.ZipFile(pending) as zipped:
        assert zipped.testzip() is None
        assert len(zipped.namelist()) == len(records) + 1
    # Both absolute paths were verified above. Replace only this task's generated ZIP.
    os.replace(pending, destination)
    result = dict(path=str(destination), sha256=sha256(destination), zip_bytes=destination.stat().st_size,
                  project_files=len(records), created_utc=manifest['created_utc'], crc_verified=True)
    save_json(ROOT.parent / 'chess-agent-project-backup.json', result)
    print(json.dumps(result, indent=2), flush=True)


if __name__ == '__main__':
    main()
