"""Serial public archive importer. Prepared but not run without written authorisation.

Supplying a reference records the user's authorisation assertion; this program cannot
determine its legal scope. Review that scope before invocation. No credentials needed.
"""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path


def fetch(url, user_agent):
    for attempt in range(5):
        try:
            request = urllib.request.Request(
                url, headers={"User-Agent": user_agent, "Accept": "application/json"}
            )
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read()
            return raw, json.loads(raw)
        except urllib.error.HTTPError as error:
            if error.code not in {429, 500, 502, 503, 504} or attempt == 4:
                raise
            retry = error.headers.get("Retry-After")
            if retry and (not retry.isdigit() or int(retry) > 60):
                raise RuntimeError(f"Server requested Retry-After={retry}; resume later") from error
            time.sleep(max(2**attempt, int(retry or 0)))
    raise RuntimeError("Unreachable")


def export_games(archives, pgn_path):
    seen, total, missing, duplicates = set(), 0, 0, 0
    with pgn_path.open("w", encoding="utf-8", newline="\n") as output:
        for path in archives:
            for game in json.loads(path.read_text(encoding="utf-8"))["games"]:
                pgn = game.get("pgn", "")
                identity = (
                    game.get("uuid")
                    or game.get("url")
                    or hashlib.sha256(json.dumps(game, sort_keys=True).encode()).hexdigest()
                )
                if identity in seen:
                    duplicates += 1
                    continue
                seen.add(identity)
                total += 1
                if not pgn:
                    missing += 1
                    continue
                output.write(pgn.strip() + "\n\n")
    return {
        "unique_games": total,
        "pgn_games": total - missing,
        "missing_pgn_games": missing,
        "duplicates_removed": duplicates,
    }


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--player", default="witty_alien")
    p.add_argument(
        "--authorisation-reference",
        required=True,
        help="Reference to actual prior written Chess.com permission covering this collection and engine-development use",
    )
    p.add_argument(
        "--user-agent",
        required=True,
        help="Descriptive application name and contact, as the API documentation recommends",
    )
    p.add_argument("--out", type=Path, required=True)
    a = p.parse_args()
    player = a.player.lower()
    if not re.fullmatch(r"[a-z0-9_-]+", player) or not a.authorisation_reference.strip():
        p.error("Valid player and actual written authorisation reference required")
    a.out.mkdir(parents=True, exist_ok=True)
    prefix = f"https://api.chess.com/pub/player/{player}/games/"
    raw, index = fetch(prefix + "archives", a.user_agent)
    (a.out / "archives.json").write_bytes(raw)
    archives = sorted(set(index["archives"]))
    report = {
        "player": player,
        "retrieved_utc": datetime.now(timezone.utc).isoformat(),
        "authorisation_reference": a.authorisation_reference,
        "archives_listed": len(archives),
        "months": [],
        "status": "running",
        "scope": "All completed games exposed by the public monthly archive index at collection time. Not deleted/private/unexposed games or a guarantee of live completeness.",
    }
    paths = []
    try:
        for url in archives:
            if not re.fullmatch(re.escape(prefix) + r"\d{4}/(0[1-9]|1[0-2])", url):
                raise ValueError(f"Unexpected archive URL: {url}")
            label = "-".join(url.rsplit("/", 2)[-2:])
            path = a.out / f"{label}.json"
            # Refresh each month to include corrections and newly completed daily games.
            month_raw, month = fetch(url, a.user_agent)
            if not isinstance(month.get("games"), list):
                raise ValueError(f"Missing games in {url}")
            path.write_bytes(month_raw)
            paths.append(path)
            report["months"].append(
                {
                    "url": url,
                    "file": path.name,
                    "games": len(month["games"]),
                    "sha256": hashlib.sha256(month_raw).hexdigest(),
                }
            )
            (a.out / "manifest.json").write_text(json.dumps(report, indent=2))
            print(f"{label}: {len(month['games'])} games", flush=True)
        report.update(export_games(paths, a.out / "all-available-games.pgn"))
        report["status"] = (
            "complete" if not report["missing_pgn_games"] else "complete_json_with_missing_pgn"
        )
    except Exception as error:
        report["status"], report["error"] = "partial", repr(error)
        raise
    finally:
        (a.out / "manifest.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "months"}, indent=2))


if __name__ == "__main__":
    main()
