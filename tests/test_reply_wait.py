"""Terminal waits own one turn, including its completed coaching delivery queue."""
import threading

import pytest

from conftest import FakeEngine
from gambit.errors import StalePosition


def wait_in_thread(service, pending, game_id):
    entered = threading.Event()
    finished = threading.Event()
    outcome = {}

    def wait():
        entered.set()
        try:
            outcome["state"] = service.wait_for_reply(
                "chat-a", game_id, pending["token"], pending["deadline"])
        except Exception as exc:
            outcome["error"] = exc
        finally:
            finished.set()

    thread = threading.Thread(target=wait, name="gambit-test-wait", daemon=True)
    thread.start()
    assert entered.wait(1)
    return finished, outcome, thread


def test_wait_includes_winning_deadline_publish_and_exact_coaching_claim(service, monkeypatch):
    notify_entered = threading.Event()
    release_notify = threading.Event()
    candidate_returning = threading.Event()

    class RacingEngine(FakeEngine):
        def candidates(self, board, strength="balanced"):
            assert notify_entered.wait(2)
            candidate_returning.set()
            return super().candidates(board, strength)

    service.engine = RacingEngine()
    original_notify = service.notify_chat

    def delayed_notify(*args, **kwargs):
        notify_entered.set()
        assert release_notify.wait(3)
        return original_notify(*args, **kwargs)

    monkeypatch.setattr(service, "notify_chat", delayed_notify)
    started = service.start("chat-a")
    moved = service.move("chat-a", "e4", started["board"]["revision"])
    game_id = moved["board"]["id"]
    pending = moved["board"]["pending"]
    finished, outcome, waiter = wait_in_thread(service, pending, game_id)
    publisher = threading.Thread(
        target=service._deadline, args=(game_id, "chat-a", pending["token"]), daemon=True)
    publisher.start()
    try:
        assert notify_entered.wait(1)
        assert candidate_returning.wait(1)
        # A metadata refresh also announces board.changed after the reply is
        # committed. That must not mistake unfinished publication for Undo.
        service.action("chat-a", "set_mode", mode="coach")
        assert service.state("chat-a")["board"]["pending"] is None
        assert not service.store.session("chat-a").get("coaching_queue")
        assert not finished.wait(.15), "The waiter returned before coaching was queued"

        release_notify.set()
        assert finished.wait(1)
        assert "error" not in outcome
        state = outcome["state"]
        assert state["board"]["ply"] == 2
        assert state["board"]["last_reply"]["token"] == pending["token"]
        event = service.take_terminal_coaching("chat-a", game_id, token=pending["token"])
        assert event and event["id"] == pending["token"]
        assert event["review"]["ply"] == 1
        assert service.take_terminal_coaching("chat-a", game_id, token=pending["token"]) is None
        assert service.store.session("chat-a")["coaching_queue"] == []
    finally:
        release_notify.set()
        service.stop()
        publisher.join(1)
        waiter.join(1)


@pytest.mark.parametrize("cancel", ["undo", "new_game"])
def test_wait_wakes_when_original_turn_is_invalidated(service, cancel):
    calculating = threading.Event()
    release_engine = threading.Event()

    class BlockedEngine(FakeEngine):
        def candidates(self, board, strength="balanced"):
            calculating.set()
            assert release_engine.wait(3)
            return super().candidates(board, strength)

    service.engine = BlockedEngine()
    started = service.start("chat-a")
    moved = service.move("chat-a", "e4", started["board"]["revision"])
    game_id = moved["board"]["id"]
    pending = moved["board"]["pending"]
    finished, outcome, waiter = wait_in_thread(service, pending, game_id)
    try:
        assert calculating.wait(1)
        if cancel == "undo":
            current = service.action("chat-a", "undo", revision=moved["board"]["revision"])
            assert current["board"]["id"] == game_id and current["board"]["ply"] == 0
        else:
            current = service.start("chat-a")
            assert current["board"]["id"] != game_id

        assert finished.wait(.5), "A canceled turn kept waiting for its old move deadline"
        assert isinstance(outcome.get("error"), StalePosition)
        assert "state" not in outcome
        assert not service.store.session("chat-a").get("coaching_queue")
    finally:
        release_engine.set()
        service.stop()
        waiter.join(1)


def test_terminal_claim_leaves_unrelated_and_requested_feedback_queued(service):
    state = service.start("chat-a")
    game_id = state["board"]["id"]
    service.notify_chat("chat-a", "Earlier automatic feedback", token="earlier", game_id=game_id)
    service.notify_chat("chat-a", "Requested summary", token="summary", game_id=game_id, kind="summary")
    service.notify_chat("chat-a", "This turn", token="selected", game_id=game_id)

    event = service.take_terminal_coaching("chat-a", game_id, token="selected")
    assert event and event["id"] == "selected"
    assert [event["id"] for event in service.store.session("chat-a")["coaching_queue"]] == [
        "earlier", "summary"]
