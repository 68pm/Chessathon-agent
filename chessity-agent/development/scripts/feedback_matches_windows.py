"""Run the unchanged feedback entrypoint with Windows-safe paths and saved games."""

import os
from pathlib import Path

from scripts import feedback_matches, overnight_matches


class FeedbackPath(type(Path())):
    def glob(self, pattern, **kwargs):
        for path in super().glob(pattern, **kwargs):
            # Live game-001.current.json snapshots are not completed PGNs.
            if pattern == 'game-*.json' and not path.stem.removeprefix('game-').isdigit():
                continue
            yield path


def feedback_path(path):
    value = str(Path(path).absolute())
    if os.name == 'nt' and not value.startswith('\\\\?\\'):
        value = ('\\\\?\\UNC\\' + value[2:]) if value.startswith('\\\\') else ('\\\\?\\' + value)
    return FeedbackPath(value)


def main():
    previous = feedback_matches.ROOT, overnight_matches.ROOT
    try:
        feedback_matches.ROOT = feedback_path(previous[0])
        overnight_matches.ROOT = feedback_path(previous[1])
        feedback_matches.main()
    finally:
        feedback_matches.ROOT, overnight_matches.ROOT = previous


if __name__ == '__main__':
    main()
