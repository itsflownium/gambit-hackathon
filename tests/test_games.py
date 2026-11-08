import io
import time

import chess
import chess.pgn
import pytest

from conftest import PGN
from gambit.errors import GambitError, StalePosition
from gambit.storage import Store, board_for, import_pgn, game_pgn


def imported(store):
    return store.create(record=import_pgn(PGN, source="lichess", source_id="abcdefgh", username="Alice"))


def test_recorded_match_replays_every_move_and_resumes(service):
    game = imported(service.store)
    service.open_replay("chat-a", game_id=game["id"])
    expected = ["e2e4", "e7e5", "d1h5", "b8c6", "f1c4", "g8f6", "h5f7"]
    assert game["moves"] == expected
    for ply in range(8):
        state = service.seek("chat-a", ply)
        assert state["board"]["ply"] == ply
        assert state["board"]["total_plies"] == 7
        assert state["board"]["last_move"] == (expected[ply-1] if ply else None)
    assert board_for(game).is_checkmate()
    assert service.state("chat-a")["board"]["position_result"] == "1-0"
    reopened = Store(service.store.directory)
    assert reopened.session("chat-a")["cursor"] == 7
    assert reopened.game(game["id"])["moves"] == expected
    assert 'Date "2026.11.07"' in game_pgn(game)
    assert list(chess.pgn.read_game(io.StringIO(game_pgn(game))).mainline_moves()) == list(board_for(game).move_stack)


def test_import_is_deduplicated_and_retains_original(store):
    one = imported(store)
    two = imported(store)
    assert one["id"] == two["id"]
    assert len(store.list_games()) == 1
    assert one["original_pgn"] == PGN


@pytest.mark.parametrize("text,username", [(PGN.replace('1-0', '*'), "Alice"),
    (PGN.replace('e4 e5', 'e4 e9'), "Alice"), (PGN, "Mallory"),
    (PGN.replace('[Event', '[Variant "Crazyhouse"]\n[Event'), "Alice")])
def test_bad_or_ineligible_import_rejected(text, username):
    with pytest.raises(GambitError):
        import_pgn(text, source="lichess", source_id="abcdefgh", username=username)


def test_moves_require_current_revision_and_correct_turn(service):
    a = service.start("chat-a")
    service.stopped.set()  # Keep the pending opponent turn in place for this rule check.
    b = service.move("chat-a", "e4", a["board"]["revision"])
    with pytest.raises(StalePosition):
        service.move("chat-a", "d4", a["board"]["revision"])
    with pytest.raises(GambitError):
        service.move("chat-a", "e5", b["board"]["revision"])
    assert service.store.game(b["board"]["id"])["moves"] == ["e2e4"]


@pytest.mark.parametrize("fen,move,square,piece", [
    ("r3k2r/8/8/8/8/8/8/R3K2R w KQkq - 0 1", "O-O", "f1", "R"),
    ("4k3/8/8/3pP3/8/8/8/4K3 w - d6 0 2", "exd6", "d6", "P"),
    ("4k3/P7/8/8/8/8/8/4K3 w - - 0 1", "a8=N", "a8", "N"),
])
def test_special_moves_are_committed_by_service(service, fen, move, square, piece):
    state = service.start("chat-a")
    game = service.store.game(state["board"]["id"])
    game = service.store.mutate(game["id"], game["revision"], lambda g: g.update(initial_fen=fen))
    service.stopped.set()
    result = service.move("chat-a", move, game["revision"])
    assert result["board"]["pieces"][square] == piece
    if move == "exd6":
        assert "d5" not in result["board"]["pieces"]


def test_replay_cannot_mutate_recorded_game(service):
    game = imported(service.store)
    service.open_replay("chat-a", game_id=game["id"])
    with pytest.raises(GambitError):
        service.move("chat-a", "e4", game["revision"])
    assert service.store.game(game["id"])["moves"] == game["moves"]


def test_two_chats_keep_games_and_replay_positions_separate(service):
    service.initialize("chat-b")
    a = service.start("chat-a")
    game = imported(service.store)
    service.open_replay("chat-b", game_id=game["id"], ply=4)
    service.seek("chat-b", 7)
    assert service.state("chat-a")["board"]["id"] == a["board"]["id"]
    assert service.state("chat-a")["board"]["ply"] == 0
    assert service.state("chat-b")["board"]["ply"] == 7


def test_delete_detaches_sessions_and_removes_analysis(service):
    game = imported(service.store)
    service.open_replay("chat-a", game_id=game["id"], ply=1)
    service.review("chat-a")
    service.store.cache("analyses", "example", {"game_id": game["id"]})
    service.action("chat-a", "delete")
    assert service.state("chat-a")["board"] is None
    assert service.store.cached("analyses", "example") is None


def test_undo_cancels_pending_reply_without_late_move(service):
    a = service.start("chat-a")
    service.stopped.set()
    b = service.move("chat-a", "e4", a["board"]["revision"])
    c = service.action("chat-a", "undo", revision=b["board"]["revision"])
    assert c["board"]["ply"] == 0
    assert c["board"]["pending"] is None
    assert c["board"]["revision"] > b["board"]["revision"]
