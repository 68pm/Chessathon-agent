import io
import json
import random
from pathlib import Path

import chess
import chess.pgn
import pytest

from engine.openings import ALIEN_LINE
from training.history_batches import collect, export_parts, load_json, write_json
from training.parallel_history import process
from training.style_analysis import analyze
from training.style_samples import prepare

PLAYER = "synthetic-player"
PREFIX = f"https://api.chess.com/pub/player/{PLAYER}/games/"


def test_parallel_history_preserves_analysis_and_global_fen_dedup(tmp_path):
    games = []
    for i in range(20):
        game = fixture_game(i)
        game["pgn"] = '[Link "https://example.invalid/game/' + str(i) + '"]\n' + game["pgn"]
        games.append(game)
    games.append({**games[0], "uuid": "same-pgn-different-raw-id"})
    source = tmp_path / "source.json"
    write_json(source, {"games": games})
    _, snapshot = export_parts([source], tmp_path / "exports")
    serial = analyze([snapshot / "all-available-games.pgn"], PLAYER)
    parallel, sample = process(
        [source], snapshot, PLAYER, tmp_path / "scratch", workers=2, maximum=20
    )
    assert parallel["counts"] == serial["counts"]
    assert parallel["rates"] == serial["rates"]
    rows = [
        json.loads(line) for line in (snapshot / "style-samples.jsonl").read_text().splitlines()
    ]
    fens = [" ".join(row["fen"].split()[:4]) for row in rows]
    assert len(fens) == len(set(fens)) == sample["counts"]["positions"]
    assert any(row["alien_sacrifice"] for row in rows)


def test_atomic_checkpoint_retries_transient_windows_lock(tmp_path, monkeypatch):
    original, calls = Path.replace, []

    def locked_once(source, destination):
        calls.append(destination)
        if len(calls) == 1:
            raise PermissionError("Synthetic transient Windows sharing violation")
        return original(source, destination)

    monkeypatch.setattr(Path, "replace", locked_once)
    monkeypatch.setattr("training.history_batches.time.sleep", lambda _delay: None)
    target = tmp_path / "status.json"
    write_json(target, {"saved": True})
    assert load_json(target) == {"saved": True} and len(calls) == 2


def test_capped_sample_spans_history_and_keeps_late_alien(tmp_path):
    games = []
    for number in range(30):
        board, rng = chess.Board(), random.Random(number)
        for _ in range(30):
            moves = list(board.legal_moves)
            if not moves:
                break
            board.push(rng.choice(moves))
        game = chess.pgn.Game.from_board(board)
        game.headers.update(
            White=PLAYER,
            Black="synthetic-opponent",
            Round=str(number),
            Date="2015.01.01" if number < 15 else "2026.01.01",
            Result="1-0",
        )
        games.append(str(game))
    games.append(fixture_game(999)["pgn"])
    pgn, output = tmp_path / "synthetic.pgn", tmp_path / "samples.jsonl"
    pgn.write_text("\n\n".join(games), encoding="utf-8")
    report = prepare(pgn, output, PLAYER, max_positions=12)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert report["counts"]["parsed_games"] == 31 and len(rows) == 12
    assert {"2015", "2026"} <= {r["date"][:4] for r in rows}
    assert any(r["alien_sacrifice"] for r in rows)


def fixture_game(number):
    b = chess.Board()
    for san in ALIEN_LINE:
        b.push_san(san)
    g = chess.pgn.Game.from_board(b)
    g.headers.update(
        {"White": PLAYER, "Black": "synthetic-opponent", "Round": str(number), "Result": "1-0"}
    )
    return {"uuid": str(number), "pgn": str(g), "rules": "chess"}


def responses():
    return {
        PREFIX + "archives": {"archives": [PREFIX + "2026/01", PREFIX + "2026/02"]},
        PREFIX + "2026/01": {"games": [fixture_game(i) for i in range(60)]},
        PREFIX + "2026/02": {
            "games": [fixture_game(i) for i in range(60, 122)]
            + [{"uuid": "missing"}]
            + [fixture_game(i) for i in range(5)]
        },
    }


def test_download_parts_resume_and_use_data(tmp_path):
    data, calls = responses(), []

    def request(url, _agent):
        calls.append(url)
        return json.dumps(data[url]).encode(), data[url]

    first = collect(PLAYER, tmp_path, "synthetic test only", "test", request=request, delay=0)
    assert len(calls) == 3
    assert first["status"] == "complete_json_with_missing_pgn"
    assert first["unique_games"] == 123 and first["parts"] == 3
    snapshot = tmp_path / first["export"]
    manifest = load_json(snapshot / "manifest.json")
    assert [p["games"] for p in manifest["parts"]] == [50, 50, 23]
    assert manifest["duplicates_removed"] == 5
    assert manifest["pgn_games"] == 122
    assert load_json(snapshot / "style-analysis.json")["counts"]["alien_sacrifices"] == 122
    samples = [
        json.loads(line) for line in (snapshot / "style-samples.jsonl").read_text().splitlines()
    ]
    assert samples and any(row["alien_sacrifice"] for row in samples)
    for row in samples:
        assert chess.Move.from_uci(row["played_uci"]) in chess.Board(row["fen"]).legal_moves
    second = collect(PLAYER, tmp_path, "synthetic test only", "test", request=request, delay=0)
    assert second["export"] == first["export"] and len(calls) == 3


def test_interrupted_run_resumes_only_missing_month(tmp_path):
    data, calls = responses(), []

    def interrupted(url, _agent):
        if url.endswith("2026/02"):
            raise ConnectionError("synthetic interruption")
        return json.dumps(data[url]).encode(), data[url]

    with pytest.raises(ConnectionError):
        collect(PLAYER, tmp_path, "synthetic", "test", request=interrupted, delay=0)
    assert load_json(tmp_path / "download-status.json")["status"] == "partial"

    def resumed(url, _agent):
        calls.append(url)
        return json.dumps(data[url]).encode(), data[url]

    collect(PLAYER, tmp_path, "synthetic", "test", request=resumed, delay=0)
    assert calls == [PREFIX + "2026/02"]
    (tmp_path / "months/2026-01.json").write_text("corrupt")
    calls.clear()
    collect(PLAYER, tmp_path, "synthetic", "test", request=resumed, delay=0)
    assert calls == [PREFIX + "2026/01"]


def test_no_network_without_authorisation_and_offline_never_fetches(tmp_path):
    def forbidden(*_args):
        pytest.fail("Unexpected network request")

    target = tmp_path / "fresh"
    with pytest.raises(ValueError, match="authorisation"):
        collect(PLAYER, target, "", "test", request=forbidden)
    assert not target.exists()
    for url, data in responses().items():
        name = (
            "archives.json"
            if url.endswith("archives")
            else "months/" + "-".join(url.rsplit("/", 2)[-2:]) + ".json"
        )
        write_json(target / name, data)
    result = collect(
        PLAYER, target, "", "test", offline=True, refresh=True, request=forbidden, delay=0
    )
    assert result["unique_games"] == 123


def test_refresh_retains_previous_exports(tmp_path):
    data = responses()

    def request(url, _agent):
        return json.dumps(data[url]).encode(), data[url]

    first = collect(PLAYER, tmp_path, "synthetic", "test", request=request, delay=0)
    data[PREFIX + "2026/02"]["games"].append(fixture_game(999))
    second = collect(PLAYER, tmp_path, "synthetic", "test", request=request, delay=0, refresh=True)
    assert first["export"] != second["export"]
    assert (tmp_path / first["export"] / "manifest.json").exists()
    assert second["unique_games"] == 124


def test_invalid_archive_and_stop_do_not_fetch_months(tmp_path):
    calls = []

    def malformed(url, _agent):
        calls.append(url)
        data = {"archives": ["https://example.invalid/unexpected"]}
        return json.dumps(data).encode(), data

    with pytest.raises(ValueError, match="Unexpected"):
        collect(PLAYER, tmp_path, "synthetic", "test", request=malformed, delay=0)
    assert calls == [PREFIX + "archives"]
    (tmp_path / "STOP_DOWNLOAD").touch()
    with pytest.raises(InterruptedError):
        collect(PLAYER, tmp_path, "synthetic", "test", request=malformed, delay=0)
    assert len(calls) == 1


def test_export_repair_and_no_cross_split_fen_duplicates(tmp_path):
    source = tmp_path / "source.json"
    write_json(source, {"games": [fixture_game(i) for i in range(101)]})
    report, snapshot = export_parts([source], tmp_path)
    assert [p["games"] for p in report["parts"]] == [50, 50, 1]
    (snapshot / "part-000001.pgn").write_text("corrupt")
    export_parts([source], tmp_path)
    assert chess.pgn.read_game(io.StringIO((snapshot / "part-000001.pgn").read_text()))
    output = tmp_path / "samples.jsonl"
    manifest = prepare(snapshot / "all-available-games.pgn", output, PLAYER)
    rows = [json.loads(line) for line in output.read_text().splitlines()]
    assert manifest["counts"]["positions"] == len(rows)
    keys = [tuple(row["fen"].split()[:4]) for row in rows]
    assert len(set(keys)) == len(keys)
    games = {}
    for row in rows:
        assert games.setdefault(row["game_id"], row["split"]) == row["split"]
