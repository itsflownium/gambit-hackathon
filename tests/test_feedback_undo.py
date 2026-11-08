"""Feedback follows the retained move line across Undo and background completion."""
import threading
import time

import pytest

from conftest import PGN
from gambit.errors import StalePosition
from gambit.storage import game_pgn, import_pgn
from gambit.tools import compact, dispatch


def ready(service, ply):
    until = time.monotonic() + 2
    while time.monotonic() < until:
        state = service.state("chat-a")
        board = state["board"]
        events = state["session"].get("coaching_queue", [])
        if (board["ply"] == ply and not board["pending"] and board["last_reply"]
                and any(event["id"] == board["last_reply"]["token"] for event in events)):
            return state
        time.sleep(.005)
    raise AssertionError("The opponent reply and its coaching event did not finish")


def first_turn(service):
    board = service.start("chat-a", mode="coach")["board"]
    assert board["review_anchor"] is None
    service.move("chat-a", "e4", board["revision"])
    return ready(service, 2)


def test_undo_prunes_only_obsolete_feedback_and_annotations_before_a_different_move(service, monkeypatch):
    first = first_turn(service)
    first_event = first["session"]["coaching_queue"][0]
    service.move("chat-a", "Nf3", first["board"]["revision"])
    second = ready(service, 4)
    gid = second["board"]["id"]
    second_event = second["session"]["coaching_queue"][1]
    assert first_event["review"]["ply"] == 1 and second_event["review"]["ply"] == 3
    assert f'game_id="{gid}"' in second_event["prompt"] and "ply=3" in second_event["prompt"]
    assert second_event["review"]["position_key"] in second_event["prompt"]
    assert compact(second)["board"]["review_anchor"] == second["board"]["review_anchor"]
    service.store.mutate(gid, second["board"]["revision"], lambda game: game.update(annotations={
        "1": {"text": "Keep the e4 review"}, "3": {"text": "Discarded Nf3 review"},
        "4": {"text": "Discarded opponent reply review"}}))
    service.notify_chat("chat-a", "Legacy unanchored Nf3 feedback", game_id=gid, token="legacy-feedback")
    service.notify_chat("chat-a", "Complete four-ply recap", game_id=gid, kind="summary",
                        expected_game=service.store.game(gid))

    undone = service.action("chat-a", "undo")["board"]
    events = service.store.session("chat-a")["coaching_queue"]
    assert undone["ply"] == 2 and events == [first_event]
    assert service.store.game(gid)["annotations"] == {"1": {"text": "Keep the e4 review"}}
    monkeypatch.setattr(service, "ensure_reply", lambda *_: None)
    changed = service.move("chat-a", "Bc4", undone["revision"])["board"]
    pgn = game_pgn(service.store.game(gid))
    assert "Bc4" in pgn and "Keep the e4 review" in pgn and "Discarded" not in pgn
    with pytest.raises(StalePosition):
        dispatch(service, "chat-a", "chess_review", second_event["review"])
    with pytest.raises(StalePosition):
        service.review("chat-a", ply=1, game_id="different-game")
    assert dispatch(service, "chat-a", "chess_review", first_event["review"])["evidence"]["ply"] == 1
    assert changed["review_anchor"]["ply"] == 3


@pytest.mark.parametrize("action", ["undo", "normal"])
def test_reply_committed_before_undo_or_normal_cannot_enqueue_delayed_feedback(service, monkeypatch, action):
    first = first_turn(service)
    entered, release = threading.Event(), threading.Event()
    original_notify = service.notify_chat
    queued = []
    def delayed_notify(*args, **kwargs):
        if kwargs.get("review_ply") == 3:
            entered.set()
            assert release.wait(2), "The delayed notification was not released"
            result = original_notify(*args, **kwargs)
            queued.append(result)
            return result
        return original_notify(*args, **kwargs)
    monkeypatch.setattr(service, "notify_chat", delayed_notify)
    try:
        service.move("chat-a", "Nf3", first["board"]["revision"])
        assert entered.wait(1), "The second reply did not reach notification delivery"
        committed = service.store.game(first["board"]["id"])
        assert len(committed["moves"]) == 4
        if action == "undo":
            current = service.action("chat-a", "undo", revision=committed["revision"])["board"]
            assert current["ply"] == 2
        else:
            service.action("chat-a", "set_mode", mode="normal", revision=committed["revision"])
        release.set()
        until = time.monotonic() + 1
        while not queued and time.monotonic() < until:
            time.sleep(.005)
        assert queued == [False]
        events = service.store.session("chat-a")["coaching_queue"]
        assert all(event.get("review", {}).get("ply") != 3 for event in events)
        assert len(events) == (1 if action == "undo" else 0)
    finally:
        release.set()


def test_undone_checkmate_rejects_terminal_feedback_and_late_full_match_recap(service, monkeypatch):
    board = service.start("chat-a", mode="coach")["board"]
    record = import_pgn(PGN, source="fixture", source_id="mate", username="Alice")
    game = service.store.mutate(board["id"], board["revision"], lambda current: current.update(moves=record["moves"][:6]))
    original_notify = service.notify_chat
    completed = []
    def undo_before_enqueue(*args, **kwargs):
        if kwargs.get("kind", "auto") == "auto" and kwargs.get("expected_game", {}).get("result") == "1-0":
            completed.append(kwargs["expected_game"])
            current = service.store.game(game["id"])
            service.action("chat-a", "undo", revision=current["revision"])
        return original_notify(*args, **kwargs)
    monkeypatch.setattr(service, "notify_chat", undo_before_enqueue)
    current = service.move("chat-a", "Qxf7#", game["revision"])["board"]
    assert completed and completed[0]["result"] == "1-0"
    assert current["ply"] == 6 and current["turn"] == "white" and current["result"] == "*"
    assert service.store.session("chat-a").get("coaching_queue", []) == []
    # A summary worker holds the original snapshot while the active game is undone.
    service._summary_worker("chat-a", completed[0], "late-summary", "white")
    assert service.store.cached("analyses", "late-summary")["status"] == "complete"
    assert service.store.session("chat-a").get("coaching_queue", []) == []
    with pytest.raises(StalePosition):
        service.summary("chat-a", game_id=game["id"], position_key=service._position_key(completed[0], include_result=True))
