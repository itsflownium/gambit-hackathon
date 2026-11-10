"""Use registered host handlers, including surface identity and real saved turns."""
import json
import sys
import threading
import time
from types import SimpleNamespace

import chess
import pytest

from conftest import FakeEngine, PGN
from gambit import tools
from gambit.storage import import_pgn


class HeldReply(FakeEngine):
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def candidates(self, board, strength="balanced"):
        self.started.set()
        assert self.release.wait(2), "The test failed to release the fixture engine"
        preferred = "e7e5" if board.turn == chess.BLACK else "e2e4"
        move = preferred if chess.Move.from_uci(preferred) in board.legal_moves else next(iter(board.legal_moves)).uci()
        return {"choices": [move], "recommended": move, "lines": [], "engine": "fixture"}


class HostContext:
    def __init__(self, surface):
        self.surface = surface
        self.tools = {}
        self.commands = {}
        self.hooks = {}

    def session_surface(self):
        return self.surface

    def register_tool(self, **kwargs):
        self.tools[kwargs["name"]] = kwargs["handler"]

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler

    def register_hook(self, name, handler):
        self.hooks[name] = handler

    def register_skill(self, *args, **kwargs):
        pass


def registered(service, monkeypatch, *, surface="cli", session_id="chat-a"):
    context = HostContext(surface)
    monkeypatch.setitem(sys.modules, "gateway.session_context", SimpleNamespace(
        get_session_env=lambda name, default="": default))
    monkeypatch.setattr(tools, "session_candidates", lambda kwargs=None: [session_id] if session_id else [])
    tools.register_tools(context, lambda: service)
    return context


def wait_state(service, *, ply=2):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        current = service.state("chat-a")
        if current["board"]["ply"] == ply and not current["board"]["pending"]:
            return current
        time.sleep(.005)
    pytest.fail("The saved opponent turn did not complete")


@pytest.mark.parametrize("surface", ["cli", "tui"])
@pytest.mark.parametrize("mode", ["normal", "coach"])
def test_terminal_move_waits_for_one_reply_and_claims_only_its_feedback(service, monkeypatch, surface, mode):
    engine = HeldReply()
    service.engine = engine
    context = registered(service, monkeypatch, surface=surface)
    started = json.loads(context.tools["chess_start"]({"mode": mode}))
    game_id = started["board"]["id"]
    # A different delivery request must survive this turn's auto-review claim.
    service.notify_chat("chat-a", "A separate requested recap.", game_id=game_id, kind="summary")
    unrelated = service.store.session("chat-a")["coaching_queue"][0]
    results = []
    completed = threading.Event()
    def move():
        try:
            results.append(json.loads(context.tools["chess_move"](
                {"move": "e4", "revision": started["board"]["revision"], "game_id": game_id}, platform="local")))
        finally:
            completed.set()
    worker = threading.Thread(target=move)
    worker.start()
    try:
        assert engine.started.wait(1)
        assert not completed.wait(.03), "CLI/TUI returned before the committed opponent reply"
        engine.release.set()
        worker.join(timeout=2)
        assert completed.is_set() and len(results) == 1
        value = results[0]
        assert value["surface"] == "terminal_chat" and value["board"]["pending"] is None
        assert value["board"]["ply"] == 2 and value["board"]["turn"] == "white"
        assert value["board"]["last_reply"]["san"] == "e5"
        assert "GAMBIT" in value["terminal_board"] and "your turn" in value["terminal_board"]
        assert service.store.game(game_id)["moves"] == ["e2e4", "e7e5"]
        if mode == "coach":
            assert "chess_review" in value["coaching_prompt"] and "e4" in value["coaching_prompt"]
            assert game_id in value["coaching_prompt"]
        else:
            assert "coaching_prompt" not in value
        queued = service.store.session("chat-a")["coaching_queue"]
        assert [event["id"] for event in queued] == [unrelated["id"]]
        again = json.loads(context.tools["chess_state"]({}))
        assert "coaching_prompt" not in again and again["board"]["ply"] == 2
        assert service.store.session("chat-a")["coaching_queue"] == queued
    finally:
        engine.release.set()
        worker.join(timeout=2)


@pytest.mark.parametrize("surface", ["desktop", "local", "", None])
def test_other_surfaces_keep_asynchronous_board_delivery_and_do_not_guess_from_platform(service, monkeypatch, surface):
    engine = HeldReply()
    service.engine = engine
    context = registered(service, monkeypatch, surface=surface)
    started = json.loads(context.tools["chess_start"]({"mode": "coach"}, platform="cli"))
    try:
        moved = json.loads(context.tools["chess_move"](
            {"move": "e4", "revision": started["board"]["revision"]}, platform="cli"))
        assert engine.started.wait(1)
        assert moved["board"]["ply"] == 1 and moved["board"]["pending"]
        assert "terminal_board" not in moved and "coaching_prompt" not in moved
        engine.release.set()
        state = wait_state(service)
        deadline = time.monotonic() + 1
        while time.monotonic() < deadline and not service.store.session("chat-a").get("coaching_queue"):
            time.sleep(.005)
        queue = service.store.session("chat-a")["coaching_queue"]
        assert len(queue) == 1 and queue[0]["id"] == state["board"]["last_reply"]["token"]
        json.loads(context.tools["chess_state"]({}))
        assert service.store.session("chat-a")["coaching_queue"] == queue
    finally:
        engine.release.set()


def test_black_terminal_start_returns_the_actual_opening_and_black_orientation(service, monkeypatch):
    engine = HeldReply()
    engine.release.set()
    service.engine = engine
    context = registered(service, monkeypatch, surface="tui")
    value = json.loads(context.tools["chess_start"]({"colour": "black", "mode": "coach"}))
    assert value["board"]["ply"] == 1 and value["board"]["turn"] == value["board"]["human"] == "black"
    assert value["board"]["last_san"] == "e4" and value["board"]["pending"] is None
    assert "h g f e d c b a" in value["terminal_board"]
    assert "Black to move" in value["terminal_board"]
    assert "Black" in value["coaching_prompt"] and "Please review my" not in value["coaching_prompt"]
    assert not service.store.session("chat-a").get("coaching_queue")


def test_terminal_practice_waits_for_one_recorded_reply_and_preserves_original(service, monkeypatch):
    original = service.store.create(record=import_pgn(PGN, source="lichess", source_id="terminal-tool-source", username="Alice"))
    source = service.open_replay("chat-a", game_id=original["id"], ply=1)["board"]
    service.engine.candidates = lambda *args, **kwargs: pytest.fail("The next matching reply belongs to the source recording")
    context = registered(service, monkeypatch)
    value = json.loads(context.tools["chess_replay"](
        {"action": "practice", "game_id": original["id"], "view_revision": source["view_revision"], "mode": "normal"}))
    board = value["board"]
    assert board["id"] != original["id"] and board["ply"] == 2 and board["pending"] is None
    assert board["last_reply"]["origin"] == "recorded" and board["last_reply"]["san"] == "e5"
    assert board["match"]["source_id"] == "terminal-tool-source"
    assert "Recorded opponent: e5" in value["terminal_board"] and "terminal-tool-source" in value["terminal_board"]
    assert "coaching_prompt" not in value
    assert service.store.game(original["id"]) == original


def test_terminal_slash_commands_return_text_and_the_completed_move_board(service, monkeypatch):
    engine = HeldReply()
    engine.release.set()
    service.engine = engine
    context = registered(service, monkeypatch)
    command = context.commands["chess"]
    help_text = command("help")
    assert isinstance(help_text, str) and "/chess play" in help_text and "hermes gambit" in help_text
    started = command("play white normal")
    assert isinstance(started, str) and "GAMBIT" in started
    moved = command("move e4")
    assert isinstance(moved, str) and "e5" in moved and "your turn" in moved
    assert service.state("chat-a")["board"]["ply"] == 2
    status = command("status")
    assert isinstance(status, str) and "GAMBIT" in status
    assert not service.store.session("chat-a").get("coaching_queue")
    assert "terminal_board" in context.hooks["pre_llm_call"]()["context"]


@pytest.mark.parametrize("surface", ["cli", "tui"])
def test_bare_chess_in_a_fresh_terminal_chat_starts_and_displays_its_board(service, monkeypatch, surface):
    sid = "fresh-" + surface
    assert not service.store.session(sid)["initialized"]
    context = registered(service, monkeypatch, surface=surface, session_id=sid)
    text = context.commands["chess"]("")
    state = service.state(sid)
    board = state["board"]
    assert isinstance(text, str) and "GAMBIT" in text and "White to move" in text
    assert state["session"]["initialized"] and board["human"] == "white" and board["play_mode"] == "coach"
    assert board["ply"] == 0 and board["pending"] is None and board["mode"] == "play"
    assert len(service.store.list_games()) == 1
    repeated = context.commands["chess"]("")
    assert "GAMBIT" in repeated and service.state(sid)["board"]["id"] == board["id"]
    assert service.state(sid)["board"]["revision"] == board["revision"]
    assert len(service.store.list_games()) == 1


def test_bare_chess_in_a_fresh_desktop_chat_only_initializes_it(service, monkeypatch):
    sid = "fresh-desktop"
    context = registered(service, monkeypatch, surface="desktop", session_id=sid)
    text = context.commands["chess"]("")
    assert isinstance(text, str) and "ready" in text.lower()
    assert service.store.session(sid)["initialized"]
    assert service.state(sid)["board"] is None and service.store.list_games() == []


def test_missing_canonical_host_session_does_not_create_a_synthetic_game(service, monkeypatch):
    context = registered(service, monkeypatch, surface="cli", session_id="")
    result = json.loads(context.tools["chess_start"]({"mode": "normal"}))
    assert result["ok"] is False
    assert service.store.list_games() == []
    assert not service.store.session("terminal:default")["initialized"]
    assert not service.store.session("cli-default")["initialized"]


@pytest.mark.parametrize("surface,terminal", [("cli", True), ("tui", True), ("desktop", False), ("local", False)])
def test_context_instruction_uses_the_host_surface_method_only(service, monkeypatch, surface, terminal):
    context = registered(service, monkeypatch, surface=surface)
    value = context.hooks["pre_llm_call"](platform="cli")["context"]
    assert ("This is a CLI/TUI chat." in value) is terminal
