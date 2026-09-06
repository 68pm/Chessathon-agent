"""Resumable monthly collection, 50-game exports and local style analysis.

Network collection for engine development requires the prior written permission
described in docs/WITTY_ALIEN_PERMISSION_NOTE.md. Offline tests use synthetic archives.
"""

import argparse
import hashlib
import json
import re
import time
from datetime import datetime, timezone
from pathlib import Path

from training.chesscom_history import fetch
from training.style_analysis import analyze
from training.style_samples import prepare


def atomic_write(path, content):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(path.name + ".tmp")
    if isinstance(content, bytes):
        temporary.write_bytes(content)
    else:
        temporary.write_text(content, encoding="utf-8", newline="\n")
    # Windows viewers/antivirus can briefly open the destination without delete sharing.
    for attempt in range(20):
        try:
            temporary.replace(path)
            break
        except PermissionError:
            if attempt == 19:
                raise
            time.sleep(0.1 * min(attempt + 1, 5))


def write_json(path, value):
    atomic_write(path, json.dumps(value, ensure_ascii=False, indent=2) + "\n")


def load_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))


def monthly_urls(index, player):
    urls = index.get("archives")
    if not isinstance(urls, list):
        raise ValueError("The archive index has no archives list")
    prefix = f"https://api.chess.com/pub/player/{player}/games/"
    if any(
        not isinstance(url, str)
        or not re.fullmatch(re.escape(prefix) + r"\d{4}/(0[1-9]|1[0-2])", url)
        for url in urls
    ):
        raise ValueError("Unexpected monthly archive URL; collection stopped")
    return sorted(set(urls))


def valid_month(raw):
    data = json.loads(raw)
    if not isinstance(data, dict) or not isinstance(data.get("games"), list):
        raise ValueError("Monthly response does not contain a games list")
    if any(not isinstance(game, dict) for game in data["games"]):
        raise ValueError("Monthly response contains an invalid game record")
    return data


def identity(game):
    return str(
        game.get("uuid")
        or game.get("url")
        or hashlib.sha256(json.dumps(game, sort_keys=True).encode()).hexdigest()
    )


def export_parts(archives, out, batch_size=50):
    """Build an immutable export snapshot; switch latest.json only after completion."""
    if not 1 <= batch_size <= 50:
        raise ValueError("Batch size must be between 1 and 50")
    out = Path(out)
    sources = [
        {"file": str(path), "sha256": hashlib.sha256(Path(path).read_bytes()).hexdigest()}
        for path in archives
    ]
    digest = hashlib.sha256(
        json.dumps({"sources": sources, "batch_size": batch_size}, sort_keys=True).encode()
    ).hexdigest()
    snapshot = out / "exports" / digest[:20]
    snapshot.mkdir(parents=True, exist_ok=True)
    done = snapshot / "manifest.json"
    if done.exists():
        report = load_json(done)
        # Reuse only a fully intact snapshot, including each JSON/PGN pair and combined PGN.
        files = [entry for part in report["parts"] for entry in part["files"]] + [
            report["combined"]
        ]
        if all(
            (snapshot / item["file"]).exists()
            and hashlib.sha256((snapshot / item["file"]).read_bytes()).hexdigest() == item["sha256"]
            for item in files
        ):
            write_json(
                out / "latest.json",
                {"export": str(snapshot.relative_to(out)), "manifest": str(done.relative_to(out))},
            )
            return report, snapshot
    parts, buffer, seen = [], [], set()
    duplicates, missing, total = 0, 0, 0
    combined_path = snapshot / "all-available-games.pgn"
    combined_tmp = combined_path.with_suffix(".pgn.tmp")

    def flush():
        number = len(parts) + 1
        name = f"part-{number:06d}"
        raw_path, pgn_path = snapshot / (name + ".json"), snapshot / (name + ".pgn")
        write_json(raw_path, {"games": buffer})
        atomic_write(
            pgn_path,
            "\n\n".join(
                g["pgn"].strip()
                for g in buffer
                if isinstance(g.get("pgn"), str) and g["pgn"].strip()
            )
            + "\n\n",
        )
        parts.append(
            {
                "part": number,
                "games": len(buffer),
                "pgn_games": sum(
                    isinstance(g.get("pgn"), str) and bool(g["pgn"].strip()) for g in buffer
                ),
                "files": [
                    {"file": p.name, "sha256": hashlib.sha256(p.read_bytes()).hexdigest()}
                    for p in [raw_path, pgn_path]
                ],
            }
        )
        buffer.clear()

    with combined_tmp.open("w", encoding="utf-8", newline="\n") as combined:
        for path in archives:
            for game in valid_month(Path(path).read_bytes())["games"]:
                uid = identity(game)
                if uid in seen:
                    duplicates += 1
                    continue
                seen.add(uid)
                total += 1
                buffer.append(game)
                pgn = game.get("pgn")
                if isinstance(pgn, str) and pgn.strip():
                    combined.write(pgn.strip() + "\n\n")
                else:
                    missing += 1
                if len(buffer) == batch_size:
                    flush()
        if buffer:
            flush()
    combined_tmp.replace(combined_path)
    report = {
        "status": "complete",
        "source_digest": digest,
        "batch_size": batch_size,
        "unique_games": total,
        "duplicates_removed": duplicates,
        "missing_pgn_games": missing,
        "pgn_games": total - missing,
        "sources": sources,
        "parts": parts,
        "combined": {
            "file": combined_path.name,
            "sha256": hashlib.sha256(combined_path.read_bytes()).hexdigest(),
        },
        "note": "All unique raw records are retained, including games without PGN and chess variants. Analysis reports its own exclusions.",
    }
    write_json(done, report)
    write_json(
        out / "latest.json",
        {"export": str(snapshot.relative_to(out)), "manifest": str(done.relative_to(out))},
    )
    return report, snapshot


def collect(
    player,
    out,
    authorisation,
    user_agent,
    batch_size=50,
    refresh=False,
    offline=False,
    request=fetch,
    delay=1.0,
    preparation_workers=1,
    scratch=None,
):
    player = player.strip().lower()
    if not re.fullmatch(r"[a-z0-9_-]+", player):
        raise ValueError("Player name may contain letters, numbers, underscores and hyphens")
    if not offline and not authorisation.strip():
        raise ValueError(
            "A reference to prior written Chess.com authorisation is required before network collection for this project"
        )
    if not 1 <= batch_size <= 50:
        raise ValueError("Batch size must be between 1 and 50")
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    manifest = out / "download-status.json"
    previous = load_json(manifest) if manifest.exists() else {}
    if previous.get("player", player) != player:
        raise ValueError("This output folder belongs to a different player; choose another folder")
    months = dict(previous.get("months", {}))
    state = {
        "player": player,
        "status": "running",
        "authorisation_reference": authorisation
        or previous.get("authorisation_reference", "offline supplied archives"),
        "updated_utc": datetime.now(timezone.utc).isoformat(),
        "months": months,
        "archives_listed": previous.get("archives_listed"),
        "scope": "Completed games exposed by the public monthly index. Private, deleted or unexposed games are outside this scope.",
    }

    def save():
        state["updated_utc"] = datetime.now(timezone.utc).isoformat()
        write_json(manifest, state)

    def stop_if_requested():
        if (out / "STOP_DOWNLOAD").exists():
            raise InterruptedError("STOP_DOWNLOAD requested; completed months are saved")

    try:
        stop_if_requested()
        index_path = out / "archives.json"
        # A normal resume uses the saved index; --refresh fetches a new index and all months.
        if offline or (index_path.exists() and not refresh):
            index = load_json(index_path)
        else:
            raw, index = request(
                f"https://api.chess.com/pub/player/{player}/games/archives", user_agent
            )
            monthly_urls(index, player)
            atomic_write(index_path, raw)
            if delay:
                time.sleep(delay)
        urls = monthly_urls(index, player)
        state["archives_listed"] = len(urls)
        save()
        paths = []
        for number, url in enumerate(urls, 1):
            stop_if_requested()
            label = "-".join(url.rsplit("/", 2)[-2:])
            path = out / "months" / f"{label}.json"
            old = months.get(label, {})
            cached = path.exists() and hashlib.sha256(path.read_bytes()).hexdigest() == old.get(
                "sha256"
            )
            if offline:
                raw = path.read_bytes()
                if old.get("sha256") and hashlib.sha256(raw).hexdigest() != old["sha256"]:
                    raise ValueError(f"Cached archive failed its hash check: {path}")
                month = valid_month(raw)
            elif cached and not refresh:
                raw = path.read_bytes()
                month = valid_month(raw)
            else:
                raw, _ = request(url, user_agent)
                month = valid_month(raw)
                atomic_write(path, raw)
                if delay:
                    time.sleep(delay)
            months[label] = {
                "url": url,
                "file": str(path.relative_to(out)),
                "games": len(month["games"]),
                "sha256": hashlib.sha256(raw).hexdigest(),
            }
            paths.append(path)
            save()
            print(
                f"Month {number}/{len(urls)}: {label}, {len(month['games'])} games {'(saved)' if cached and not refresh else ''}",
                flush=True,
            )
        stop_if_requested()
        exports, snapshot = export_parts(paths, out, batch_size)
        state["export"] = str(snapshot.relative_to(out))
        state["unique_games"] = exports["unique_games"]
        state["parts"] = len(exports["parts"])
        state["missing_pgn_games"] = exports["missing_pgn_games"]
        save()
        if preparation_workers > 1:
            from training.parallel_history import process

            if scratch is None:
                raise ValueError(
                    "Provide an intermediate scratch directory for parallel preparation"
                )
            analysis, samples = process(paths, snapshot, player, scratch, preparation_workers)
        else:
            analysis = analyze([snapshot / "all-available-games.pgn"], player)
            write_json(snapshot / "style-analysis.json", analysis)
            samples = prepare(
                snapshot / "all-available-games.pgn", snapshot / "style-samples.jsonl", player
            )
            write_json(snapshot / "style-samples.manifest.json", samples)
        state["analysis"] = str((snapshot / "style-analysis.json").relative_to(out))
        state["style_samples"] = str((snapshot / "style-samples.jsonl").relative_to(out))
        state["training_positions_prepared"] = samples["counts"].get("positions", 0)
        state["status"] = (
            "complete" if not exports["missing_pgn_games"] else "complete_json_with_missing_pgn"
        )
        return state
    except BaseException as error:
        state["status"] = (
            "paused" if isinstance(error, (KeyboardInterrupt, InterruptedError)) else "partial"
        )
        state["error"] = str(error)
        raise
    finally:
        save()


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--player", default="witty_alien")
    p.add_argument("--out", type=Path, default=Path("data/witty_alien-history"))
    p.add_argument("--batch-size", type=int, default=50)
    p.add_argument("--preparation-workers", type=int, choices=range(1, 5), default=1)
    p.add_argument("--scratch", type=Path)
    p.add_argument("--authorisation-reference", default="")
    p.add_argument("--user-agent", default="ChessAgentHistory/1.0 (local educational project)")
    p.add_argument(
        "--refresh",
        action="store_true",
        help="Refresh the archive index and all months; previous export snapshots remain",
    )
    p.add_argument(
        "--offline",
        action="store_true",
        help="Process supplied local archives only; never make a network request",
    )
    a = p.parse_args()
    try:
        state = collect(
            a.player,
            a.out,
            a.authorisation_reference,
            a.user_agent,
            a.batch_size,
            a.refresh,
            a.offline,
            preparation_workers=a.preparation_workers,
            scratch=a.scratch,
        )
    except KeyboardInterrupt:
        p.exit(130, "Paused. Completed months remain saved; rerun the same command to resume.\n")
    except (ValueError, OSError) as error:
        p.exit(2, str(error) + "\n")
    print(json.dumps({k: v for k, v in state.items() if k != "months"}, indent=2))


if __name__ == "__main__":
    main()
