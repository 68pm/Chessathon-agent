"""Bounded streaming annotated CC0 PGNs, never a runtime lookup database."""

import argparse
import hashlib
import io
import json
import random
import re
import urllib.request
from collections import Counter
from pathlib import Path

import chess
import chess.pgn
import numpy as np
import zstandard

from engine.evaluation import phase
from engine.features import encode


class BoundedReader:
    def __init__(self, response, limit):
        self.response, self.left = response, limit
        self.hash = hashlib.sha256()
        self.bytes = 0

    def read(self, size=-1):
        if self.left <= 0:
            return b""
        chunk = self.response.read(min(size if size >= 0 else 131072, self.left))
        self.left -= len(chunk)
        self.bytes += len(chunk)
        self.hash.update(chunk)
        return chunk


def choose_source():
    html = urllib.request.urlopen("https://database.lichess.org/", timeout=30).read().decode()
    match = re.search(r'href="([^"]*standard_rated_2026-07\.pgn\.zst)"', html)
    if not match:
        raise RuntimeError("Cannot discover the July 2026 standard PGN source")
    from urllib.parse import urljoin

    return urljoin("https://database.lichess.org/", match.group(1))


def split_group(group, seed):
    value = int(hashlib.sha256(f"{seed}:{group}".encode()).hexdigest()[:8], 16) % 100
    return 0 if value < 80 else 1 if value < 90 else 2


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--source")
    p.add_argument("--positions", type=int, default=50000)
    p.add_argument("--max-compressed-mb", type=int, default=128)
    p.add_argument("--seed", type=int, default=20260905)
    p.add_argument("--out", type=Path, default=Path("data/lichess-50k"))
    a = p.parse_args()
    if a.positions < 100:
        p.error("At least 100 positions are required")
    source = a.source or choose_source()
    if not source.startswith("https://database.lichess.org/"):
        p.error("This importer is restricted to the CC0 Lichess database")
    print(f"Streaming {source}; compressed cap {a.max_compressed_mb} MB", flush=True)
    rng, seen, buckets = random.Random(a.seed), set(), Counter()
    samples, scanned, analysed = [], 0, 0
    response = urllib.request.urlopen(source, timeout=60)
    raw = BoundedReader(response, a.max_compressed_mb * 1_000_000)
    quota = max(100, (a.positions + 14) // 15)
    with response, zstandard.ZstdDecompressor().stream_reader(raw) as stream:
        text = io.TextIOWrapper(stream, encoding="utf-8")
        while len(samples) < a.positions:
            # Filter before parsing SAN: most public games have no engine annotations.
            headers, body = [], []
            line = text.readline()
            while line and not line.startswith("[Event "):
                line = text.readline()
            if not line:
                break
            headers.append(line)
            while True:
                line = text.readline()
                if not line or not line.strip():
                    break
                headers.append(line)
            while True:
                line = text.readline()
                if not line or not line.strip():
                    break
                body.append(line)
            scanned += 1
            if not any("[%eval" in line for line in body):
                continue
            game = chess.pgn.read_game(io.StringIO("".join(headers) + "\n" + "".join(body)))
            if game is None or game.errors or game.headers.get("Variant", "Standard") != "Standard":
                continue
            analysed += 1
            board = game.board()
            # All positions in an ECO opening family remain together, not randomly split.
            group = game.headers.get("ECO")
            if not group or group == "?":
                group = game.headers.get(
                    "Site", hashlib.sha256("".join(headers).encode()).hexdigest()
                )
            split = split_group(group, a.seed)
            candidates = []
            for node in game.mainline():
                board.push(node.move)
                label = node.eval()
                if label is None or board.ply() < 8 or not board.is_valid() or board.is_game_over():
                    continue
                cp = label.pov(board.turn).score(mate_score=10000)
                if cp is None:
                    continue
                normalized = " ".join(board.fen().split()[:4])
                if normalized in seen:
                    continue
                ph = phase(board)
                stage = 0 if ph > 0.8 else 1 if ph > 0.3 else 2
                bucket = (
                    0
                    if cp < -600
                    else 1
                    if cp < -150
                    else 2
                    if cp <= 150
                    else 3
                    if cp <= 600
                    else 4
                )
                candidates.append((normalized, board.fen(), cp, stage, bucket, split, group))
            rng.shuffle(candidates)
            for normalized, fen, cp, stage, bucket, split, group in candidates[:40]:
                if normalized in seen or buckets[stage, bucket] >= quota:
                    continue
                seen.add(normalized)
                buckets[stage, bucket] += 1
                samples.append((fen, cp, stage, bucket, split, group))
                if len(samples) >= a.positions:
                    break
            if analysed % 250 == 0:
                print(
                    f"{len(samples)} positions; {analysed} annotated / {scanned} games", flush=True
                )
    if len(samples) < 100:
        raise RuntimeError(
            f"Only {len(samples)} samples collected; increase bounded budget or use another source"
        )
    a.out.mkdir(parents=True, exist_ok=True)
    x = np.stack([encode(chess.Board(s[0])) for s in samples])
    cp = np.array([s[1] for s in samples], dtype=np.float32)
    splits = np.array([s[4] for s in samples], dtype=np.uint8)
    dataset = a.out / "dataset.npz"
    np.savez_compressed(
        dataset,
        x=x,
        y=np.tanh(np.clip(cp, -10000, 10000) / 600)[:, None],
        cp=cp,
        split=splits,
        fen=np.array([s[0] for s in samples]),
        group=np.array([s[5] for s in samples]),
    )
    metadata = {
        "source": source,
        "licence": "CC0 https://database.lichess.org/",
        "seed": a.seed,
        "positions": len(samples),
        "requested_positions": a.positions,
        "scanned_games": scanned,
        "annotated_games": analysed,
        "compressed_bytes_read": raw.bytes,
        "compressed_prefix_sha256": raw.hash.hexdigest(),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "splits": dict(Counter(map(int, splits))),
        "buckets": {str(k): v for k, v in buckets.items()},
        "groups": len({s[5] for s in samples}),
        "split_rule": "SHA256(seed:ECO) mod 100; <80 train, <90 validation, else test. Missing ECO: source game URL.",
        "label": "PGN engine annotation; converted by python-chess to mover perspective; tanh(cp/600); mates +/-10000cp",
        "sampling": "Bounded chronological prefix, up to 40 shuffled positions/game, deduplicated, quota per phase/value bucket.",
        "limitations": "Prefix sampling is not uniform over the month. Annotated game selection and teacher depth are uncontrolled. Sparse buckets may remain underfilled.",
    }
    (a.out / "metadata.json").write_text(json.dumps(metadata, indent=2))
    print(json.dumps(metadata), flush=True)


if __name__ == "__main__":
    main()
