"""A resignation stays final even when the opponent finishes thinking later."""
import threading
import time

import pytest

from gambit.storage import Store, game_pgn


@pytest.mark.parametrize("colour,result", [("white", "0-1"), ("black", "1-0")])
def test_resign_records_loss_and_late_opponent_cannot_change_the_next_game(
    service, monkeypatch, colour, result
):
    calculating = threading.Event()
    release = threading.Event()
    candidates = service.engine.candidates

    def delayed_candidates(*args, **kwargs):
        calculating.set()
        assert release.wait(2), "The test did not release the opponent calculation"
        return candidates(*args, **kwargs)

    monkeypatch.setattr(service.engine, "candidates", delayed_candidates)
    try:
        state = service.start("chat-a", colour=colour)
        if colour == "white":
            state = service.move("chat-a", "e4", state["board"]["revision"])
        assert calculating.wait(1), "The opponent never started calculating"
        pending = state["board"]
        assert pending["pending"] is not None

        ended = service.action(
            "chat-a", "resign", game_id=pending["id"], revision=pending["revision"]
        )["board"]
        assert ended["result"] == result
        assert ended["pending"] is None
        assert ended["legal_moves"] == []
        assert ended["ply"] == pending["ply"]
        saved = Store(service.store.directory).game(ended["id"])
        assert saved["result"] == result
        assert f'[Result "{result}"]' in game_pgn(saved)

        # Match the UI's automatic reset before the old calculation completes.
        fresh = service.start("chat-a", colour="white")["board"]
        assert fresh["id"] != ended["id"]
        assert fresh["result"] == "*"
        assert fresh["ply"] == 0
        assert len(fresh["legal_moves"]) == 20

        release.set()
        until = time.monotonic() + 1
        while time.monotonic() < until:
            with service.lock:
                if pending["pending"]["token"] not in service.jobs:
                    break
            time.sleep(.005)
        else:
            pytest.fail("The released opponent calculation did not finish")

        current = service.state("chat-a")
        assert current["board"]["id"] == fresh["id"]
        assert current["board"]["ply"] == 0
        assert current["board"]["result"] == "*"
        assert current["session"].get("coaching_queue", []) == []
        old = service.store.game(ended["id"])
        assert old["result"] == result
        assert old["moves"] == saved["moves"]
        assert old["pending"] is None
        assert old["last_reply"] is None
    finally:
        release.set()
