import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from gambit.storage import Store
from gambit.service import Service

PGN = '''[Event "Recorded teaching game"]
[Site "Local fixture"]
[Date "2026.11.07"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]

1. e4 e5 2. Qh5 Nc6 3. Bc4 Nf6 4. Qxf7# 1-0
'''


class FakeEngine:
    configured_path = "fixture"
    def health(self):
        return {"ready": True, "name": "fixture"}
    def candidates(self, board, strength="balanced"):
        choices = [m.uci() for m in board.legal_moves]
        return {"choices": choices[:3], "recommended": choices[0], "lines": [], "engine": "fixture"}
    def review(self, game, ply, store):
        return {"game_id": game["id"], "ply": ply, "mover": "white" if ply % 2 else "black",
                "played_san": "e4", "classification": "sound move", "facts": [], "loss_cp": 0}


@pytest.fixture
def store(tmp_path):
    return Store(tmp_path)


@pytest.fixture
def service(store):
    s = Service(store, engine=FakeEngine())
    s.initialize("chat-a")
    yield s
    s.stop()
