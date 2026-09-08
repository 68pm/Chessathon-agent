"""Review existing local/competition games and fit a separate reward policy checkpoint."""

import argparse
import json
from pathlib import Path

from training.game_feedback import review_batch
from training.reward_policy import fit


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    parser.add_argument('--initial-policy', type=Path, required=True)
    args = parser.parse_args()
    data = json.loads(args.source.read_text(encoding='utf-8'))
    if data['status'] != 'complete':
        raise ValueError('Input games have not completed')
    paths = review_batch(data['games'], args.out)
    result = fit(paths, args.initial_policy, args.out / 'reward-policy')
    print(json.dumps(result), flush=True)


if __name__ == '__main__':
    main()
