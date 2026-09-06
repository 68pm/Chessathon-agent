"""Bounded CPU parallelism for offline analysis; all network collection stays serial."""

import hashlib
import heapq
import json
import re
from collections import Counter, defaultdict
from concurrent.futures import ProcessPoolExecutor, as_completed
from pathlib import Path

from training.style_analysis import analyze
from training.style_samples import prepare


def worker(path, player, maximum):
    path = Path(path)
    analysis = analyze([path], player)
    samples = path.with_suffix(".jsonl")
    manifest = prepare(path, samples, player, max_positions=maximum)
    return analysis, str(samples), manifest


def process(archives, snapshot, player, scratch, workers=4, maximum=50000, seed=20260906):
    if not 1 <= workers <= 4:
        raise ValueError("Use one to four offline workers")
    scratch = Path(scratch)
    scratch.mkdir(parents=True, exist_ok=True)
    paths = [scratch / f"shard-{i}.pgn" for i in range(workers)]
    streams = [path.open("w", encoding="utf-8", newline="\n") for path in paths]
    seen = set()
    try:
        for archive in archives:
            for game in json.loads(Path(archive).read_bytes())["games"]:
                identity = str(
                    game.get("uuid")
                    or game.get("url")
                    or hashlib.sha256(json.dumps(game, sort_keys=True).encode()).hexdigest()
                )
                if identity in seen:
                    continue
                seen.add(identity)
                pgn = game.get("pgn")
                if not isinstance(pgn, str) or not pgn.strip():
                    continue
                # Equal PGN Links share a worker so semantic game deduplication is retained.
                link = re.search(r'^\[Link "([^"\r\n]+)"\]', pgn, re.MULTILINE)
                shard = (
                    int(hashlib.sha256(link.group(1).encode()).hexdigest()[:8], 16) % workers
                    if link
                    else 0
                )
                streams[shard].write(pgn.strip() + "\n\n")
    finally:
        for stream in streams:
            stream.close()
    print(f"Offline analysis and sampling split across {workers} CPU workers", flush=True)
    results = {}
    with ProcessPoolExecutor(max_workers=workers) as pool:
        futures = {pool.submit(worker, path, player, maximum): i for i, path in enumerate(paths)}
        for future in as_completed(futures):
            results[futures[future]] = future.result()
            print(f"Completed offline worker {len(results)}/{workers}", flush=True)
    totals, opening_counts, clocks, sample_counts = (
        Counter(),
        Counter(),
        defaultdict(Counter),
        Counter(),
    )
    selected, heap = {}, []
    for i in sorted(results):
        analysis, samples, manifest = results[i]
        totals.update(analysis["counts"])
        opening_counts.update(analysis["openings"])
        for clock, counts in analysis["by_time_control"].items():
            clocks[clock].update(counts)
        sample_counts.update(manifest["counts"])
        with Path(samples).open(encoding="utf-8") as stream:
            for line in stream:
                row = json.loads(line)
                key = tuple(row["fen"].split()[:4])
                if key in selected:
                    continue
                priority = (
                    -1
                    if row["alien_sacrifice"]
                    else int(hashlib.sha256(f"{seed}:{key}".encode()).hexdigest(), 16)
                )
                if len(selected) >= maximum and priority >= -heap[0][0]:
                    continue
                if len(selected) >= maximum:
                    _, removed = heapq.heappop(heap)
                    del selected[removed]
                selected[key] = row
                heapq.heappush(heap, (-priority, key))
    rates = {
        "checks_per_100_moves": 100 * totals["checks"] / totals["player_moves"]
        if totals["player_moves"]
        else None,
        "captures_per_100_moves": 100 * totals["captures"] / totals["player_moves"]
        if totals["player_moves"]
        else None,
        "mean_castling_fullmove_when_castled": totals["castling_fullmove_sum"] / totals["castles"]
        if totals["castles"]
        else None,
    }
    merged_analysis = {
        **results[0][0],
        "counts": dict(totals),
        "rates": rates,
        "openings": dict(opening_counts),
        "by_time_control": dict(clocks),
    }
    for key in ["positions", "train", "validation", "test", "alien_positions"]:
        sample_counts[key] = 0
    target = Path(snapshot) / "style-samples.jsonl"
    with target.open("w", encoding="utf-8", newline="\n") as sink:
        for key in sorted(selected):
            row = selected[key]
            sink.write(json.dumps(row, separators=(",", ":")) + "\n")
            sample_counts["positions"] += 1
            sample_counts[row["split"]] += 1
            sample_counts["alien_positions"] += int(row["alien_sacrifice"])
    merged_samples = {
        **results[0][2],
        "counts": dict(sample_counts),
        "sha256": hashlib.sha256(target.read_bytes()).hexdigest(),
        "workers": workers,
        "merge": "Global bottom-k FEN hashes from each worker's bottom-k sample; final exact FEN deduplication. Same PGN Link assigned to the same worker. All games without Link share worker zero to preserve semantic game deduplication. Related positions can remain across splits.",
    }
    for name, data in [
        ("style-analysis.json", merged_analysis),
        ("style-samples.manifest.json", merged_samples),
    ]:
        (Path(snapshot) / name).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return merged_analysis, merged_samples
