"""Exercise the asynchronous coaching boundary with real saved chess positions."""
import asyncio
import contextvars
import json
import threading
import time
from types import SimpleNamespace

import chess
import pytest

from conftest import FakeEngine, PGN
from gambit.errors import GambitError
from gambit.service import Service
from gambit.storage import board_for, import_pgn
from gambit.terminal_coach import TerminalCoach


class EvidenceEngine(FakeEngine):
    def candidates(self, board, strength="balanced"):
        preferred = "e7e5" if board.turn == chess.BLACK else "e2e4"
        choice = preferred if chess.Move.from_uci(preferred) in board.legal_moves else next(iter(board.legal_moves)).uci()
        return {"choices": [choice], "recommended": choice, "lines": [], "engine": "fixture"}

    def position(self, board, **kwargs):
        return {"lines": [{"uci": "g1f3", "line_san": ["Nf3"]}]}

    def review(self, game, ply, store):
        before = board_for(game, max(0, ply - 1))
        move = chess.Move.from_uci(game["moves"][ply - 1]) if ply else None
        return {"game_id": game["id"], "ply": ply,
                "mover": "white" if before.turn else "black",
                "played_san": before.san(move) if move else None,
                "played_uci": move.uci() if move else None,
                "classification": "sound move", "loss_cp": 0,
                "facts": ["This is a legal move in the recorded position."]}


class PublicModel:
    def __init__(self, *, block=False, fail=None, parsed=None):
        self.calls = []
        self.started = threading.Event()
        self.release = threading.Event()
        self.block = block
        self.fail = fail
        self.parsed = parsed or {"explanation": "A sound move in this recorded position."}

    async def acomplete_structured(self, **kwargs):
        self.calls.append(kwargs)
        self.started.set()
        while self.block and not self.release.is_set():
            await asyncio.sleep(.005)
        if self.fail:
            raise self.fail
        return SimpleNamespace(parsed=self.parsed, reasoning="private reasoning must never appear")


@pytest.fixture
def coaching_service(store):
    model = PublicModel()
    context = SimpleNamespace(llm=model, get_config=lambda key, default: default)
    service = Service(store, ctx=context, engine=EvidenceEngine())
    service.move_seconds = .3  # The fixture engine supplies moves; only coaching calls the model.
    service.initialize("terminal-fixture")
    yield service, model
    model.release.set()
    service.stop()


def wait_for_reply(service):
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline:
        state = service.state("terminal-fixture")
        if state["board"]["last_reply"] and not state["board"]["pending"]:
            return state
        time.sleep(.005)
    pytest.fail("The fixture opponent did not finish its one reply")


def wait_for_event(coach, request_id, *, timeout=2):
    seen = []
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        seen.extend(coach.poll())
        terminal = [event for event in seen if event["request_id"] == request_id
                    and event["phase"] in {"complete", "fallback", "cancelled", "stale", "unavailable"}]
        if terminal:
            return terminal[-1], seen
        time.sleep(.005)
    pytest.fail(f"The coaching request did not finish; phases were {[event['phase'] for event in seen]}")


def played_game(service, *, mode="coach"):
    started = service.start("terminal-fixture", mode=mode)
    service.move("terminal-fixture", "e4", started["board"]["revision"])
    return wait_for_reply(service)


def test_normal_mode_suppresses_auto_feedback_but_allows_a_requested_review(coaching_service):
    service, model = coaching_service
    state = played_game(service, mode="normal")
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        for _ in range(5):
            coach.observe(state)
        assert coach.poll() == [] and model.calls == []
        request_id = coach.submit_review(ply=1)
        result, _ = wait_for_event(coach, request_id)
        assert result["phase"] == "complete" and result["automatic"] is False
        assert result["anchor"]["game_id"] == state["board"]["id"]
        assert result["anchor"]["ply"] == 1
        assert result["explanation"] == model.parsed["explanation"]
        assert len(model.calls) == 1
    finally:
        coach.close()


def test_coach_observation_reviews_the_human_move_only_once(coaching_service):
    service, model = coaching_service
    state = played_game(service)
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        for _ in range(12):
            coach.observe(state)
        events = []
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            events.extend(coach.poll())
            if any(event["phase"] == "complete" for event in events):
                break
            time.sleep(.005)
        completed = [event for event in events if event["phase"] == "complete"]
        assert len(completed) == 1 and completed[0]["automatic"] is True
        assert completed[0]["anchor"]["ply"] == 1
        assert completed[0]["evidence"]["played_san"] == "e4"
        for _ in range(5):
            coach.observe(service.state("terminal-fixture"))
        assert coach.poll() == [] and len(model.calls) == 1
    finally:
        coach.close()


def test_black_opening_is_not_reviewed_as_a_human_move(coaching_service):
    service, model = coaching_service
    service.start("terminal-fixture", colour="black", mode="coach")
    state = wait_for_reply(service)
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        coach.observe(state)
        assert state["board"]["ply"] == 1 and state["board"]["turn"] == "black"
        assert coach.poll() == [] and model.calls == []
    finally:
        coach.close()


def test_hint_levels_withhold_later_details_from_both_output_and_model(coaching_service):
    service, model = coaching_service
    source = service.store.create(record=import_pgn(PGN, source="fixture", source_id="terminal-hints", username="Alice"))
    service.open_replay("terminal-fixture", game_id=source["id"])
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        for level in range(1, 5):
            result, _ = wait_for_event(coach, coach.submit_hint())
            evidence = result["evidence"]
            assert result["phase"] == "complete" and evidence["level"] == level
            assert "clue" in evidence
            if level == 1:
                assert not {"piece", "from", "to", "move", "line"} & evidence.keys()
            elif level == 2:
                assert evidence["piece"] == "knight" and evidence["from"] == "g1"
                assert not {"to", "move", "line"} & evidence.keys()
            elif level == 3:
                assert evidence["to"] == "f3" and not {"move", "line"} & evidence.keys()
            else:
                assert evidence["move"] == "Nf3" and evidence["line"] == ["Nf3"]
            payload = json.loads(model.calls[-1]["input"][0]["text"])
            assert "fen" not in payload and "fen" not in payload.get("anchor", {})
            assert payload["evidence"] == evidence
            model_evidence = json.dumps({key: value for key, value in payload["evidence"].items()
                                         if key not in {"game_id", "ply"}})
            if level < 4:
                assert "Nf3" not in model_evidence
            if level < 3:
                assert "f3" not in model_evidence
    finally:
        coach.close()


def test_undo_during_model_work_discards_feedback_for_the_removed_move(coaching_service):
    service, model = coaching_service
    state = played_game(service)
    model.block = True
    model.parsed = {"explanation": "late feedback for the removed e4 move"}
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        request_id = coach.submit_review(ply=1)
        assert model.started.wait(1)
        current = service.state("terminal-fixture")["board"]
        service.action("terminal-fixture", "undo", revision=current["revision"])
        model.release.set()
        result, events = wait_for_event(coach, request_id)
        assert result["phase"] in {"stale", "cancelled"}
        assert not any(event.get("explanation") == model.parsed["explanation"] for event in events)
        assert service.state("terminal-fixture")["board"]["ply"] == 0
    finally:
        model.release.set()
        coach.close()


def test_cancel_and_close_are_prompt_and_do_not_stop_the_shared_service(coaching_service):
    service, model = coaching_service
    service.start("terminal-fixture", mode="normal")
    model.block = True
    model.parsed = {"explanation": "cancelled explanation must not appear"}
    coach = TerminalCoach(service, "terminal-fixture")
    coach.submit_hint()
    assert model.started.wait(1)
    began = time.monotonic()
    coach.cancel()
    coach.close()
    assert time.monotonic() - began < .3
    model.release.set()
    assert not service.stopped.is_set()
    assert all(event.get("explanation") != model.parsed["explanation"] for event in coach.poll())
    current = service.state("terminal-fixture")
    service.move("terminal-fixture", "e4", current["board"]["revision"])
    assert wait_for_reply(service)["board"]["ply"] == 2


def test_close_rejects_a_concurrent_submit_before_dispatching_task_cancellation(coaching_service):
    service, _ = coaching_service
    service.start("terminal-fixture", mode="normal")
    cancelled = threading.Event()
    class CancellableModel(PublicModel):
        async def acomplete_structured(self, **kwargs):
            try:
                return await super().acomplete_structured(**kwargs)
            except asyncio.CancelledError:
                cancelled.set()
                raise
    model = CancellableModel(block=True)
    service.ctx.llm = model
    coach = TerminalCoach(service, "terminal-fixture")
    coach.submit_hint()
    assert model.started.wait(1)
    cancellation_entered = threading.Event()
    allow_cancellation = threading.Event()
    # Pause at the real async cancellation boundary. The UI is closing while
    # another thread tries to submit a fresh request at this exact interleaving.
    with coach._lock:
        request = coach._active
        real_loop = request.loop
        class CancellationBoundary:
            def is_closed(self):
                return real_loop.is_closed()
            def call_soon_threadsafe(self, callback, *args):
                cancellation_entered.set()
                assert allow_cancellation.wait(2)
                return real_loop.call_soon_threadsafe(callback, *args)
        request.loop = CancellationBoundary()
    closing = threading.Thread(target=coach.close)
    closing.start()
    try:
        assert cancellation_entered.wait(1)
        with pytest.raises(GambitError, match="closed"):
            coach.submit_hint()
        assert len(model.calls) == 1
        assert coach.poll() == [] and not service.stopped.is_set()
        allow_cancellation.set()
        closing.join(timeout=1)
        assert not closing.is_alive() and cancelled.wait(1)
        assert coach.poll() == [] and len(model.calls) == 1
    finally:
        allow_cancellation.set()
        model.release.set()
        closing.join(timeout=1)
        coach.close()


def test_replay_seek_discards_an_explanation_for_the_old_view(coaching_service):
    service, model = coaching_service
    source = service.store.create(record=import_pgn(PGN, source="fixture", source_id="terminal-seek", username="Alice"))
    service.open_replay("terminal-fixture", game_id=source["id"], ply=1)
    model.block = True
    model.parsed = {"explanation": "feedback for the view the user has left"}
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        request_id = coach.submit_review()
        assert model.started.wait(1)
        service.seek("terminal-fixture", 3)
        model.release.set()
        result, events = wait_for_event(coach, request_id)
        assert result["phase"] in {"stale", "cancelled"}
        assert not any(event.get("explanation") == model.parsed["explanation"] for event in events)
        assert service.state("terminal-fixture")["board"]["ply"] == 3
    finally:
        model.release.set()
        coach.close()


def test_host_request_context_is_preserved_on_the_model_worker(coaching_service):
    service, _ = coaching_service
    service.start("terminal-fixture", mode="normal")
    route = contextvars.ContextVar("terminal_test_host_route", default="missing")
    observed = []
    class ContextModel:
        async def acomplete_structured(self, **kwargs):
            observed.append(route.get())
            assert not {"model", "provider", "api_key", "base_url", "reasoning_effort"} & kwargs.keys()
            return SimpleNamespace(parsed={"explanation": "Consider a quiet improving move."})
    service.ctx.llm = ContextModel()
    coach = TerminalCoach(service, "terminal-fixture")
    token = route.set("active-profile-route")
    try:
        request_id = coach.submit_hint(1)
    finally:
        route.reset(token)
    try:
        result, _ = wait_for_event(coach, request_id)
        assert result["phase"] == "complete"
        assert observed == ["active-profile-route"]
    finally:
        coach.close()


@pytest.mark.parametrize("leaked_explanation", ["Play Nf3 now.", "Move your knight to f3.", "Develop the knight."])
def test_first_hint_rejects_a_model_that_reveals_later_levels(coaching_service, leaked_explanation):
    service, model = coaching_service
    service.start("terminal-fixture", mode="normal")
    model.parsed = {"explanation": leaked_explanation}
    coach = TerminalCoach(service, "terminal-fixture")
    try:
        result, events = wait_for_event(coach, coach.submit_hint(1))
        assert result["phase"] == "fallback"
        assert result["evidence"]["level"] == 1
        assert not {"piece", "from", "to", "move", "line"} & result["evidence"].keys()
        assert not any(event.get("explanation") == leaked_explanation for event in events)
        assert "Nf3" not in result["explanation"] and "f3" not in result["explanation"]
    finally:
        coach.close()


@pytest.mark.parametrize("failure", ["timeout", "private_error", "invalid_structured_result"])
def test_unavailable_model_returns_bounded_public_engine_evidence(coaching_service, failure):
    service, model = coaching_service
    service.start("terminal-fixture", mode="normal")
    if failure == "timeout":
        model.block = True
    elif failure == "private_error":
        model.fail = RuntimeError("PRIVATE_TOKEN=secret-value")
    else:
        model.parsed = {"explanation": "untrusted answer", "reasoning": "PRIVATE_TOKEN=secret-value"}
    coach = TerminalCoach(service, "terminal-fixture", timeout_seconds=.1)
    try:
        began = time.monotonic()
        result, events = wait_for_event(coach, coach.submit_hint(), timeout=1)
        assert time.monotonic() - began < .9
        assert result["phase"] in {"fallback", "unavailable"}
        assert result["evidence"]["level"] == 1
        assert result["explanation"]
        public = json.dumps(events)
        assert "PRIVATE_TOKEN" not in public and "secret-value" not in public
        assert "private reasoning" not in public and "untrusted answer" not in public
    finally:
        model.release.set()
        coach.close()
