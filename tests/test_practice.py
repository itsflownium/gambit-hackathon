import importlib.util
import sys
import time
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from conftest import PGN, FakeEngine
from gambit.errors import GambitError, StalePosition
from gambit.storage import board_for, import_pgn
from gambit.tools import dispatch


def replay(service, *, username="Alice", ply=0):
    game = service.store.create(record=import_pgn(PGN, source="lichess", source_id="practice-source", username=username))
    state = service.open_replay("chat-a", game_id=game["id"], ply=ply)
    return game, state["board"]


def replied(service, sid="chat-a", timeout=2):
    until = time.monotonic() + timeout
    while time.monotonic() < until:
        board = service.state(sid)["board"]
        if board["last_reply"] and not board["pending"]:
            return board
        time.sleep(.01)
    raise AssertionError("Practice opponent did not finish exactly one reply")


def test_completed_source_offers_moves_at_live_replay_positions(service):
    original, board = replay(service)
    assert board["result"] == "1-0" and board["position_result"] == "*"
    assert board["practice"] is None
    assert "e2e4" in {move["uci"] for move in board["legal_moves"]}
    ended = service.seek("chat-a", len(original["moves"]))["board"]
    assert ended["legal_moves"] == [] and ended["position_result"] == "1-0"


def test_replay_move_branches_and_repeats_one_recorded_opponent_reply(service):
    original, board = replay(service)
    service.engine.candidates = lambda *_: pytest.fail("A matching branch must use the recorded opponent move")
    service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="normal", move="e4")
    current = replied(service)
    branch = service.store.game(current["id"])
    assert current["id"] != original["id"] and current["mode"] == "play"
    assert current["source"] == "hermes" and current["human"] == "white"
    assert current["practice"] == {"game_id": original["id"], "start_ply": 0,
                                   "white": "Alice", "black": "Bob", "username": "Alice"}
    assert branch["moves"] == ["e2e4", "e7e5"]
    assert current["last_reply"]["origin"] == "recorded"
    assert current["last_reply"]["recorded_review"]["ply"] == 2
    assert not service.store.session("chat-a").get("coaching_queue")
    token = current["last_reply"]["token"]
    assert service._commit_reply(branch["id"], "chat-a", token, "g8f6", "recorded", "late") is None
    service.ensure_reply(branch["id"], "chat-a")
    assert service.store.game(branch["id"])["moves"] == ["e2e4", "e7e5"]
    service.move("chat-a", "Qh5", current["revision"], current["id"])
    following = replied(service)
    assert following["last_move"] == "b8c6" and following["ply"] == 4
    assert service.store.game(original["id"]) == original


def test_deviation_uses_one_calculated_reply_and_keeps_source_intact(service):
    original, board = replay(service)
    calls = []
    def calculate(position, strength):
        calls.append(position.fen())
        return {"choices": ["d7d5"], "recommended": "d7d5", "lines": [], "engine": "fixture"}
    service.engine.candidates = calculate
    service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="normal", move="d4")
    current = replied(service)
    assert current["last_reply"]["origin"] == "engine"
    assert service.store.game(current["id"])["moves"] == ["d2d4", "d7d5"]
    assert len(calls) == 1 and current["turn"] == current["human"]
    assert service.store.game(original["id"]) == original
    comparison = service.review("chat-a")["source_comparison"]
    assert comparison["played_san"] == "e4" and comparison["same_move"] is False
    assert comparison["evidence"]["ply"] == 1


@pytest.mark.parametrize("username,ply,expected,human", [
    ("Alice", 1, ["e2e4", "e7e5"], "white"),
    ("Bob", 0, ["e2e4"], "black"),
    ("Bob", 2, ["e2e4", "e7e5", "d1h5"], "black"),
])
def test_play_from_opponent_turn_advances_only_one_source_half_move(service, username, ply, expected, human):
    original, board = replay(service, username=username, ply=ply)
    service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="normal")
    current = replied(service)
    assert service.store.game(current["id"])["moves"] == expected
    assert current["turn"] == current["human"] == human
    assert current["last_reply"]["origin"] == "recorded"
    assert service.store.game(original["id"]) == original


def test_play_from_human_turn_waits_for_the_user(service):
    original, board = replay(service, ply=2)
    result = service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="coach")["board"]
    assert result["ply"] == 2 and result["pending"] is None and result["last_reply"] is None
    assert result["turn"] == result["human"] == "white" and result["play_mode"] == "coach"


@pytest.mark.parametrize("username,move", [("Alice", "e2e5"), ("Bob", "e7e5")])
def test_invalid_first_move_does_not_create_or_select_a_branch(service, username, move):
    original, board = replay(service, username=username)
    session = service.store.session("chat-a")
    with pytest.raises(GambitError):
        service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], move=move)
    assert service.store.session("chat-a") == session
    assert len(service.store.list_games()) == 1 and service.store.game(original["id"]) == original


def test_stale_replay_view_does_not_create_a_branch(service):
    original, board = replay(service)
    service.seek("chat-a", 2, view_revision=board["view_revision"], game_id=original["id"])
    session = service.store.session("chat-a")
    with pytest.raises(StalePosition):
        service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], move="e4")
    assert service.store.session("chat-a") == session and len(service.store.list_games()) == 1
    with pytest.raises(StalePosition):
        service.seek("chat-a", 4, game_id="another-game")


def test_terminal_source_position_cannot_start_practice(service):
    original, board = replay(service, ply=7)
    with pytest.raises(GambitError):
        service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"])
    assert len(service.store.list_games()) == 1


def test_return_to_original_restores_cursor_and_selected_colour(service):
    original, board = replay(service, username="Bob", ply=3)
    current = service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"])["board"]
    restored = service.action("chat-a", "replay_source", game_id=current["id"])["board"]
    assert restored["id"] == original["id"] and restored["mode"] == "replay"
    assert restored["ply"] == 3 and restored["human"] == "black" and restored["practice"] is None
    assert service.store.game(original["id"]) == original


def test_practice_undo_keeps_the_selected_source_prefix(service):
    original, board = replay(service, ply=3)
    service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="normal")
    current = replied(service)
    with pytest.raises(GambitError):
        service.action("chat-a", "undo", revision=current["revision"])
    service.move("chat-a", "Bc4", current["revision"])
    current = replied(service)
    undone = service.action("chat-a", "undo", revision=current["revision"])["board"]
    assert undone["ply"] == 4 and undone["turn"] == "white"
    assert service.store.game(undone["id"])["moves"] == original["moves"][:4]


def test_chat_move_can_branch_from_a_replay_with_a_current_view(service):
    original, board = replay(service)
    service.stopped.set()
    result = dispatch(service, "chat-a", "chess_move", {"move": "d4", "revision": board["revision"],
                      "game_id": original["id"], "view_revision": board["view_revision"]})
    assert result["board"]["practice"]["game_id"] == original["id"]
    assert result["board"]["ply"] == 1 and result["board"]["pending"]


def test_reply_commits_once_even_when_a_review_revises_metadata_before_commit(service, monkeypatch):
    original, board = replay(service)
    mutate = service.store.mutate
    raced = []
    def concurrent_review(gid, revision, function, kind="action", **kwargs):
        if kind == "hermes_move" and not raced:
            raced.append(True)
            mutate(gid, revision, lambda g: g["annotations"].update({"1": {"text": "Concurrent review"}}), "review")
        return mutate(gid, revision, function, kind, **kwargs)
    monkeypatch.setattr(service.store, "mutate", concurrent_review)
    service.practice("chat-a", game_id=original["id"], view_revision=board["view_revision"], mode="normal", move="e4")
    current = replied(service)
    assert raced and current["ply"] == 2 and current["last_move"] == "e7e5"
    assert service.store.game(current["id"])["annotations"]["1"]["text"] == "Concurrent review"


def test_native_api_starts_without_chat_then_branches_and_restores_source(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("gambit_practice_preview", root / "serve.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    app = module.app_for(tmp_path)
    runtime = module.runpy.run_path(str(root / "bootstrap.py"))["runtime"]()
    service = runtime.service()
    service.engine = FakeEngine()
    client = TestClient(app)
    try:
        started = client.post("/api/plugins/gambit/action", json={"session_id": "direct-start", "action": "start", "mode": "normal"}).json()
        assert started["ok"] and started["session"]["initialized"]
        assert started["board"]["play_mode"] == "normal" and started["board"]["turn"] == "white"
        game = service.store.create(record=import_pgn(PGN, source="fixture", source_id="api-practice", username="Alice"))
        source = service.open_replay("direct-start", game_id=game["id"])["board"]
        failed = client.post("/api/plugins/gambit/action", json={"session_id": "direct-start", "action": "practice_move",
                  "game_id": game["id"], "view_revision": source["view_revision"], "move": "e5"}).json()
        assert failed["ok"] is False and len(service.store.list_games()) == 2
        moved = client.post("/api/plugins/gambit/action", json={"session_id": "direct-start", "action": "practice_move",
                 "game_id": game["id"], "view_revision": source["view_revision"], "mode": "normal", "move": "e4"}).json()
        assert moved["ok"] and moved["board"]["practice"]["game_id"] == game["id"]
        current = replied(service, "direct-start")
        assert current["ply"] == 2 and current["last_reply"]["origin"] == "recorded"
        restored = client.post("/api/plugins/gambit/action", json={"session_id": "direct-start", "action": "replay_source", "game_id": current["id"]}).json()
        assert restored["board"]["id"] == game["id"] and restored["board"]["ply"] == 0
    finally:
        service.stop()
