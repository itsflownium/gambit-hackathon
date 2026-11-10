"""The dashboard renders and controls the same persisted game as the service."""
import copy
import threading
import time
from types import SimpleNamespace

import chess
import pytest

from conftest import FakeEngine, PGN
from gambit.errors import EngineUnavailable
from gambit.storage import import_pgn
from gambit.terminal import TerminalController, _TerminalWorker, run_terminal
from gambit.terminal_view import board_grid, board_lines, clip_columns, display_width, layout_for, safe_text, wrapped_lines


class ReplyEngine(FakeEngine):
    def candidates(self, board, strength="balanced"):
        move = chess.Move.from_uci("e7e5" if board.turn == chess.BLACK else "e2e4")
        choice = move.uci() if move in board.legal_moves else next(iter(board.legal_moves)).uci()
        return {"choices": [choice], "recommended": choice, "lines": [], "engine": "fixture"}

    def position(self, board, **kwargs):
        return {"lines": [{"uci": "g1f3", "line_san": ["Nf3"]}]}


class BlockingEngine(ReplyEngine):
    def __init__(self):
        self.started = threading.Event()
        self.release = threading.Event()

    def candidates(self, board, strength="balanced"):
        self.started.set()
        assert self.release.wait(2), "The test failed to release the fixture engine"
        return super().candidates(board, strength)


def finished(controller, *, ply=2):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = controller.refresh()
        board = state["board"]
        if board["ply"] == ply and not board["pending"]:
            return board
        time.sleep(.005)
    pytest.fail("The terminal did not refresh to the committed reply")


def wait_until(predicate, description):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        if predicate():
            return
        time.sleep(.005)
    pytest.fail(description)


def test_startup_engine_failure_keeps_commands_available_and_can_recover_in_place(service):
    class RecoveringEngine(ReplyEngine):
        ready = False
        def health(self):
            if not self.ready:
                raise EngineUnavailable("The local chess engine is unavailable.")
            return super().health()
    engine = RecoveringEngine()
    service.engine = engine
    terminal = TerminalController(service, "chat-a", mode="normal")
    worker = _TerminalWorker(terminal, .05)
    worker.start()
    try:
        wait_until(lambda: bool(terminal.snapshot()["error"]) and
                   any("Commands remain available" in message["text"] for message in terminal.snapshot()["messages"]),
                   "Startup failure and recovery guidance were not visible")
        assert terminal.snapshot()["busy"] == ""
        assert any("Commands remain available" in message["text"] for message in terminal.snapshot()["messages"])
        worker.submit("?")
        wait_until(lambda: any(message["role"] == "help" for message in terminal.snapshot()["messages"]),
                   "The command worker stopped after engine startup failed")
        worker.submit("saved")
        wait_until(lambda: any("No matching games" in message["text"] for message in terminal.snapshot()["messages"]),
                   "Saved-match controls were unavailable after engine startup failed")
        engine.ready = True
        worker.submit("new white normal")
        wait_until(lambda: bool(terminal.snapshot()["state"].get("board")) and terminal.snapshot()["busy"] == "",
                   "Starting a game did not recover after the engine became available")
        worker.submit("e4")
        current = finished(terminal)
        assert service.store.game(current["id"])["moves"] == ["e2e4", "e7e5"]
        assert current["turn"] == current["human"] == "white"
        assert len(service.store.list_games()) == 1
    finally:
        worker.close()
        worker.thread.join(timeout=1)
    assert not worker.thread.is_alive() and not service.stopped.is_set()


def test_move_refresh_changes_the_rendered_position_once_and_preserves_history(service):
    service.engine = ReplyEngine()
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        initial = terminal.initialize()["board"]
        initial_text = board_lines(initial, ascii_pieces=True)
        assert terminal.execute("e4")["ok"]
        board = finished(terminal)
        assert service.store.game(board["id"])["moves"] == ["e2e4", "e7e5"]
        assert [item["san"] for item in board["history"]] == ["e4", "e5"]
        assert board["turn"] == board["human"] == "white"
        assert board_lines(board, ascii_pieces=True) != initial_text
        squares = {square.name: square for row in board_grid(board) for square in row}
        assert squares["e4"].piece == "P" and squares["e5"].piece == "p"
        assert squares["e2"].piece == squares["e7"].piece == ""
        assert {square.name for square in squares.values() if square.last_move} == {"e7", "e5"}
        for _ in range(12):
            terminal.refresh()
        assert service.store.game(board["id"])["moves"] == ["e2e4", "e7e5"]
        assert not service.store.session("chat-a").get("coaching_queue")
    finally:
        terminal.close()


def test_illegal_move_has_a_visible_error_without_advancing_the_saved_position(service):
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        initial = terminal.initialize()["board"]
        record = service.store.game(initial["id"])
        result = terminal.execute("e2e5")
        assert result["ok"] is False
        assert "legal" in result["message"].lower()
        assert terminal.snapshot()["error"] == result["message"]
        assert terminal.messages[-1]["role"] == "error"
        assert service.store.game(initial["id"]) == record
        assert terminal.execute("new white normal learning")["ok"]
        assert service.store.game(terminal.state["board"]["id"])["strength"] == "learning"
    finally:
        terminal.close()


def test_requested_hint_displays_exact_engine_move_beside_the_public_model_explanation(service):
    class Model:
        async def acomplete_structured(self, **kwargs):
            return SimpleNamespace(parsed={"explanation": "Consider your options carefully."})
    service.engine = ReplyEngine()
    service.ctx = SimpleNamespace(llm=Model())
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        terminal.initialize()
        assert terminal.execute("hint 4")["ok"]
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            terminal.refresh()
            if any(message["role"] == "hermes" for message in terminal.messages):
                break
            time.sleep(.005)
        hint = [message for message in terminal.messages if message["role"] == "hint"]
        assert len(hint) == 1 and "Hint 4/4" in hint[0]["text"] and "Move: Nf3" in hint[0]["text"]
        assert any(message["role"] == "hermes" and message["text"] == "Consider your options carefully."
                   for message in terminal.messages)
        for _ in range(8):
            terminal.refresh()
        assert len([message for message in terminal.messages if message["role"] == "hint"]) == 1
        assert service.state("chat-a")["board"]["ply"] == 0
        assert not service.store.session("chat-a").get("coaching_queue")
    finally:
        terminal.close()


def test_unexpected_provider_error_is_not_rendered_as_private_diagnostic_text(service, monkeypatch):
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        terminal.initialize()
        def unavailable(*args, **kwargs):
            raise RuntimeError("PRIVATE_PROVIDER_DIAGNOSTIC")
        monkeypatch.setattr(service, "find_games", unavailable)
        result = terminal.execute("import lichess Alice")
        assert result["ok"] is False
        assert "PRIVATE_PROVIDER_DIAGNOSTIC" not in result["message"]
        assert all("PRIVATE_PROVIDER_DIAGNOSTIC" not in message["text"] for message in terminal.messages)
    finally:
        terminal.close()


def test_closing_and_reopening_terminal_keeps_one_committed_opponent_turn(service):
    engine = BlockingEngine()
    service.engine = engine
    first = TerminalController(service, "chat-a", mode="normal")
    first.initialize()
    second = None
    try:
        assert first.execute("e4")["ok"]
        assert engine.started.wait(1)
        pending = copy.deepcopy(service.state("chat-a")["board"])
        assert pending["ply"] == 1 and pending["pending"]
        began = time.monotonic()
        first.close()
        assert time.monotonic() - began < .3 and not service.stopped.is_set()
        assert service.state("chat-a")["board"]["pending"]["token"] == pending["pending"]["token"]
        second = TerminalController(service, "chat-a", colour="black", mode="coach")
        reopened = second.initialize()["board"]
        assert reopened["id"] == pending["id"] and reopened["human"] == "white"
        engine.release.set()
        current = finished(second)
        for _ in range(10):
            second.refresh()
        assert current["last_reply"]["token"] == pending["pending"]["token"]
        assert service.store.game(current["id"])["moves"] == ["e2e4", "e7e5"]
        assert len(service.store.list_games()) == 1
    finally:
        engine.release.set()
        first.close()
        if second:
            second.close()


def test_undo_cancels_a_pending_turn_and_late_worker_cannot_restore_it(service):
    engine = BlockingEngine()
    service.engine = engine
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        terminal.initialize()
        terminal.execute("e4")
        assert engine.started.wait(1)
        assert terminal.execute("undo")["ok"]
        engine.release.set()
        for _ in range(20):
            terminal.refresh()
            time.sleep(.005)
        board = terminal.state["board"]
        assert board["ply"] == 0 and board["pending"] is None and board["last_reply"] is None
        assert service.store.game(board["id"])["moves"] == []
    finally:
        engine.release.set()
        terminal.close()


def test_replay_commands_restore_exact_position_and_practice_keeps_source_unchanged(service):
    original = service.store.create(record=import_pgn(PGN, source="lichess", source_id="terminal-replay", username="Alice"))
    service.open_replay("chat-a", game_id=original["id"], ply=2)
    terminal = TerminalController(service, "chat-a", colour="black", mode="normal")
    try:
        current = terminal.initialize()["board"]
        assert current["id"] == original["id"] and current["ply"] == 2 and current["mode"] == "replay"
        assert terminal.execute("first")["ok"] and terminal.state["board"]["ply"] == 0
        assert terminal.execute("next")["ok"] and terminal.state["board"]["last_san"] == "e4"
        assert terminal.execute("seek 2")["ok"] and terminal.state["board"]["last_san"] == "e5"
        assert terminal.execute("seek 99")["ok"] is False
        assert terminal.state["board"]["ply"] == 2
        assert terminal.execute("first")["ok"]
        assert terminal.execute("practice normal")["ok"]
        branch_id = terminal.state["board"]["id"]
        assert branch_id != original["id"] and terminal.state["board"]["mode"] == "play"
        service.engine.candidates = lambda *args: pytest.fail("A matching source line has exactly one recorded reply")
        assert terminal.execute("e4")["ok"]
        current = finished(terminal)
        assert current["last_reply"]["origin"] == "recorded"
        assert service.store.game(branch_id)["moves"] == original["moves"][:2]
        assert current["match"]["source_id"] == "terminal-replay"
        assert service.store.game(original["id"]) == original
        assert terminal.execute("source")["ok"]
        restored = terminal.state["board"]
        assert restored["id"] == original["id"] and restored["ply"] == 0 and restored["mode"] == "replay"
        assert service.store.game(original["id"]) == original
    finally:
        terminal.close()


def test_import_picker_opens_the_exact_numbered_match_without_touching_other_sources(service):
    def games(username, limit, before):
        return [{"source_id": "terminal-older", "platform": "lichess", "username": username,
                 "white": "Alice", "black": "Bob", "result": "1-0", "ended_at": 1794000000,
                 "url": "https://lichess.org/terminal-older", "pgn": PGN},
                {"source_id": "terminal-newer", "platform": "lichess", "username": username,
                 "white": "Alice", "black": "Carol", "result": "1-0", "ended_at": 1794100000,
                 "url": "https://lichess.org/terminal-newer", "pgn": PGN.replace('"Bob"', '"Carol"')}][:limit]
    service.importer._lichess = games
    terminal = TerminalController(service, "chat-a", mode="normal")
    try:
        terminal.initialize()
        assert terminal.execute("import lichess Alice")["ok"]
        choices = service.store.session("chat-a")["last_search"]["source_ids"]
        assert len(choices) == 2
        assert terminal.execute("open 2")["ok"]
        board = terminal.state["board"]
        assert board["match"]["source_id"] == choices[1]
        assert board["human"] == board["match"]["colour"] == "white"
        assert board["match"]["username"] == "Alice" and board["mode"] == "replay"
        selected = service.store.game(board["id"])
        assert terminal.execute("open 9")["ok"] is False
        assert terminal.state["board"]["id"] == selected["id"]
        assert service.store.game(selected["id"]) == selected
    finally:
        terminal.close()


@pytest.mark.parametrize("colour,first,last,king", [("white", "a8", "h1", "e1"), ("black", "h1", "a8", "e8")])
def test_board_rendering_rotates_files_ranks_and_pieces_together(service, colour, first, last, king):
    service.engine = ReplyEngine()
    terminal = TerminalController(service, "chat-a", colour=colour, mode="normal")
    try:
        board = terminal.initialize()["board"]
        if colour == "black":
            board = finished(terminal, ply=1)
        grid = board_grid(board)
        assert len(grid) == 8 and all(len(row) == 8 for row in grid)
        assert grid[0][0].name == first and grid[-1][-1].name == last
        assert len({square.name for row in grid for square in row}) == 64
        rendered = board_lines(board, ascii_pieces=True)
        assert rendered[0].split() == list("abcdefgh" if colour == "white" else "hgfedcba")
        assert [line[0] for line in rendered[1:-1]] == list("87654321" if colour == "white" else "12345678")
        own_king = next(square for row in grid for square in row if square.name == king)
        assert own_king.piece == ("K" if colour == "white" else "k")
    finally:
        terminal.close()


@pytest.mark.parametrize("width,height", [(140, 42), (100, 28), (80, 24), (60, 40), (40, 18), (20, 8), (2, 2), (0, 0)])
def test_resize_layout_stays_inside_the_viewport_without_overlapping_panels(width, height):
    layout = layout_for(width, height)
    rectangles = [layout.board, layout.feed, layout.footer]
    for rectangle in rectangles:
        assert min(rectangle.x, rectangle.y, rectangle.width, rectangle.height) >= 0
        assert rectangle.right <= width and rectangle.bottom <= height
    occupied = [rectangle for rectangle in rectangles if rectangle.width and rectangle.height]
    for index, left in enumerate(occupied):
        for right in occupied[index + 1:]:
            assert left.right <= right.x or right.right <= left.x or left.bottom <= right.y or right.bottom <= left.y
    if width >= 76 and height >= 18:
        assert not layout.stacked and layout.feed.width > 0


def test_imported_display_text_cannot_issue_terminal_controls():
    visible = safe_text("Alice\x1b[2J vs Bob\x1b]0;spoofed title\x07\x00")
    assert visible == "Alice vs Bob"


def test_wide_player_names_wrap_by_screen_columns_without_losing_characters():
    name = "棋手名字André"
    lines = wrapped_lines(name, 4)
    assert "".join(lines) == name
    assert all(display_width(line) <= 4 for line in lines)
    assert clip_columns("棋手", 3) == "棋"


def test_direct_dashboard_non_tty_guard_never_touches_the_service(monkeypatch, capsys):
    import io
    import sys
    class ForbiddenService:
        def __getattr__(self, name):
            pytest.fail(f"Redirected launch accessed service.{name}")
    monkeypatch.setattr(sys, "stdin", io.StringIO())
    monkeypatch.setattr(sys, "stdout", io.StringIO())
    assert run_terminal(ForbiddenService(), "missing") == 2
    assert "terminal" in capsys.readouterr().err.lower()
