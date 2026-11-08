import asyncio
import time
from types import SimpleNamespace

from conftest import FakeEngine
from gambit.service import Service


def finished(service, seconds):
    until = time.monotonic() + seconds
    while time.monotonic() < until:
        board = service.state("chat-a")["board"]
        if board and board["last_reply"]:
            return board
        time.sleep(.01)
    raise AssertionError("The move deadline was missed")


def test_stalled_engine_cannot_hold_board_past_deadline(store):
    class Slow(FakeEngine):
        def candidates(self, board, strength="balanced"):
            time.sleep(.8)
            return super().candidates(board, strength)
    service = Service(store, engine=Slow())
    service.move_seconds = .3
    service.initialize("chat-a")
    start = service.start("chat-a")
    began = time.monotonic()
    service.move("chat-a", "e4", start["board"]["revision"])
    board = finished(service, .7)
    assert time.monotonic() - began < .65
    assert board["last_reply"]["origin"] == "legal_recovery"
    time.sleep(.9)
    assert service.state("chat-a")["board"]["ply"] == 2
    service.stop()


def test_stalled_model_gets_one_deadline_move_and_late_result_is_ignored(store):
    class LLM:
        async def acomplete_structured(self, **kwargs):
            time.sleep(5)  # A deliberately non-cooperative provider, independent of async timeout.
            return SimpleNamespace(parsed={"move": "a7a6", "explanation": "late"})
    class Ctx:
        llm = LLM()
        def get_config(self, key, default): return default
    service = Service(store, ctx=Ctx(), engine=FakeEngine())
    service.move_seconds = 4.2
    service.initialize("chat-a")
    start = service.start("chat-a")
    began = time.monotonic()
    service.move("chat-a", "e4", start["board"]["revision"])
    board = finished(service, 4.3)
    assert time.monotonic() - began < 4.25
    assert board["last_reply"]["origin"] == "engine_deadline"
    assert board["ply"] == 2
    time.sleep(1.5)
    assert service.state("chat-a")["board"]["ply"] == 2
    service.stop()


def test_user_setting_can_never_extend_move_budget_above_one_minute(store):
    class Ctx:
        def get_config(self, key, default):
            return 999 if key == "move_timeout_seconds" else default
    service = Service(store, ctx=Ctx(), engine=FakeEngine())
    assert service.move_seconds == 60
    service.stop()
