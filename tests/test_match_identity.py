import datetime as dt
import importlib.util
import json
import sys
from pathlib import Path

import httpx
import pytest
from fastapi.testclient import TestClient

from conftest import PGN, FakeEngine
from gambit.errors import GambitError
from gambit.storage import import_pgn
from gambit.tools import compact, dispatch


ENDED = dt.datetime(2026, 11, 7, tzinfo=dt.timezone.utc).timestamp()


@pytest.fixture
def searched(service):
    def games(username, limit, before):
        records = [{"source_id": "abcdefgh", "platform": "lichess", "username": username,
                    "white": "Alice", "black": "Bob", "result": "1-0", "ended_at": ENDED,
                    "url": "https://lichess.org/abcdefgh", "pgn": PGN}]
        if username.casefold() == "alice":
            records.append({**records[0], "source_id": "ijklmnop", "black": "Carol", "ended_at": ENDED - 86400,
                            "url": "https://lichess.org/ijklmnop", "pgn": PGN.replace('"Bob"', '"Carol"')})
        return records[:limit]
    service.importer._lichess = games
    return service


def test_chat_search_username_controls_same_cached_match_for_either_player(searched):
    service = searched
    service.initialize("chat-b")
    alice = service.find_games("chat-a", "lichess", "Alice")
    service.find_games("chat-b", "lichess", "Bob")
    assert service.importer.selected("lichess", "abcdefgh")["username"] == "Bob"
    first = service.open_replay("chat-a", game_number=1)["board"]
    second = service.open_replay("chat-b", game_number=1)["board"]
    assert first["id"] == second["id"]
    assert first["human"] == first["match"]["colour"] == "white"
    assert second["human"] == second["match"]["colour"] == "black"
    assert first["match"]["username"] == "Alice" and second["match"]["username"] == "Bob"
    assert alice["games"][0]["number"] == 1 and alice["games"][1]["number"] == 2
    assert alice["games"][0]["opponent"] == "Bob" and alice["games"][0]["colour"] == "white"
    assert service.store.session("chat-a")["last_search"]["source_ids"] == ["abcdefgh", "ijklmnop"]
    assert "pgn" not in json.dumps(service.store.session("chat-a")["last_search"])


def test_number_selection_resolves_exact_current_chat_match_and_latest_is_explicit(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    assert service.state("chat-a")["board"] is None
    selected = dispatch(service, "chat-a", "chess_replay", {"action": "open", "game_number": 2, "username": "Alice"})["board"]
    assert selected["match"]["source_id"] == "ijklmnop" and selected["match"]["black"] == "Carol"
    latest = service.open_replay("chat-a", latest=True)["board"]
    assert latest["match"]["source_id"] == "abcdefgh"
    agreed = service.open_replay("chat-a", game_number=2, source_id="ijklmnop")["board"]
    assert agreed["match"]["black"] == "Carol"


@pytest.mark.parametrize("options", [{"game_number": 0}, {"game_number": 3}, {"game_number": True},
    {"game_number": 1, "source_id": "ijklmnop"}, {"game_number": 1, "platform": "chess.com"},
    {"game_number": 1, "latest": True}])
def test_invalid_number_or_inconsistent_identity_never_opens_another_match(searched, options):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    with pytest.raises(GambitError):
        service.open_replay("chat-a", **options)
    assert service.state("chat-a")["board"] is None and service.store.list_games() == []


def test_explicit_username_is_validated_even_when_import_is_already_deduplicated(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    first = service.open_replay("chat-a", game_number=1)["board"]
    switched = service.open_replay("chat-a", game_id=first["id"], username="bOb")["board"]
    assert switched["human"] == switched["match"]["colour"] == "black" and switched["match"]["username"] == "Bob"
    session = service.store.session("chat-a")
    for options in [{"source_id": "abcdefgh", "platform": "lichess", "username": "Mallory"},
                    {"game_id": first["id"], "username": "Mallory"}]:
        with pytest.raises(GambitError, match="not a player"):
            service.open_replay("chat-a", **options)
    assert service.store.session("chat-a") == session and len(service.store.list_games()) == 1


def test_source_selection_never_inherits_another_chats_cached_username(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    service.initialize("chat-b")
    with pytest.raises(GambitError, match="username"):
        service.open_replay("chat-b", platform="lichess", source_id="abcdefgh")
    selected = service.open_replay("chat-b", platform="lichess", source_id="abcdefgh", username="Bob")["board"]
    assert selected["human"] == "black" and selected["match"]["username"] == "Bob"


def test_legacy_search_without_numbered_ids_still_binds_its_own_username(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    service.store.mutate_session("chat-a", lambda s: s.update(last_search={"platform": "lichess", "username": "Bob"}))
    selected = service.open_replay("chat-a", source_id="abcdefgh")["board"]
    assert selected["match"]["username"] == "Bob" and selected["human"] == "black"


def test_saved_match_uses_chat_search_perspective_when_that_match_was_returned(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    source = service.open_replay("chat-a", game_number=1)["board"]
    service.initialize("chat-b")
    service.find_games("chat-b", "lichess", "Bob")
    reopened = service.open_replay("chat-b", game_id=source["id"])["board"]
    assert reopened["match"]["username"] == "Bob" and reopened["human"] == "black"


def test_unrelated_search_does_not_prevent_resuming_a_saved_source(searched):
    service = searched
    unrelated = service.store.create(record=import_pgn(PGN.replace('"Alice"', '"Carol"'), source="lichess",
                                    source_id="savedother", username="Bob"))
    service.find_games("chat-a", "lichess", "Alice")
    reopened = service.action("chat-a", "resume", game_id=unrelated["id"])["board"]
    assert reopened["human"] == "black" and reopened["match"]["username"] == "Bob"


def test_practice_keeps_original_identity_after_original_is_deleted(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    source = service.open_replay("chat-a", game_number=1)["board"]
    expected = source["match"]
    assert expected == {"game_id": source["id"], "platform": "lichess", "username": "Alice", "colour": "white",
                        "source_id": "abcdefgh", "url": "https://lichess.org/abcdefgh", "date": "2026-11-07",
                        "ended_at": ENDED, "white": "Alice", "black": "Bob", "result": "1-0"}
    branch = service.practice("chat-a", view_revision=source["view_revision"], mode="normal")["board"]
    assert branch["match"] == expected and branch["white"] == "You" and branch["black"] == "Hermes"
    service.store.delete(source["id"])
    assert service.state("chat-a")["board"]["match"] == expected
    assert compact(service.state("chat-a"))["board"]["match"] == expected


def test_legacy_practice_recovers_original_identity_and_keeps_known_names_if_missing(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Bob")
    source = service.open_replay("chat-a", game_number=1, ply=1)["board"]
    branch = service.practice("chat-a", view_revision=source["view_revision"], mode="normal")["board"]
    service.store.mutate(branch["id"], branch["revision"], lambda g: g.pop("source_match"))
    recovered = service.state("chat-a")["board"]["match"]
    assert recovered == source["match"] and recovered["colour"] == "black"
    service.store.delete(source["id"])
    partial = service.state("chat-a")["board"]["match"]
    assert partial["white"] == "Alice" and partial["black"] == partial["username"] == "Bob"
    assert partial["colour"] == "black" and partial["platform"] is None and partial["result"] is None


def test_returning_from_a_saved_practice_replay_preserves_the_selected_source_player(searched):
    service = searched
    service.find_games("chat-a", "lichess", "Alice")
    source = service.open_replay("chat-a", game_number=1)["board"]
    branch = service.practice("chat-a", view_revision=source["view_revision"], mode="normal")["board"]
    selected = service.open_replay("chat-a", game_id=branch["id"], username="Bob")["board"]
    assert selected["match"]["colour"] == selected["human"] == "black"
    restored = service.replay_source("chat-a", game_id=branch["id"])["board"]
    assert restored["match"]["colour"] == restored["human"] == "black" and restored["match"]["username"] == "Bob"


def test_imported_date_falls_back_to_pgn_and_live_game_has_no_source_identity(service):
    game = service.store.create(record=import_pgn(PGN, source="lichess", source_id="dateonly", username="Alice"))
    source = service.open_replay("chat-a", game_id=game["id"])["board"]
    assert source["match"]["date"] == "2026-11-07" and source["match"]["ended_at"] is None
    assert service.start("chat-a", mode="normal")["board"]["match"] is None


@pytest.mark.parametrize("platform,source_id", [("lichess", "abcdefgh"), ("chess.com", "1234")])
def test_import_picker_api_searches_both_platforms_in_fresh_chat_and_opens_exact_row(tmp_path, platform, source_id):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("gambit_match_preview", root / "serve.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    client = TestClient(module.app_for(tmp_path))
    runtime = module.runpy.run_path(str(root / "bootstrap.py"))["runtime"]()
    service = runtime.service()
    service.engine = FakeEngine()
    def response(request):
        if platform == "lichess":
            if request.url.params.get("until") and int(request.url.params["until"]) < ENDED * 1000:
                return httpx.Response(200, content="")
            raw = {"id": source_id, "variant": "standard", "status": "mate", "lastMoveAt": ENDED * 1000,
                   "players": {"white": {"user": {"name": "Alice"}}, "black": {"user": {"name": "Bob"}}}, "pgn": PGN}
            return httpx.Response(200, content=json.dumps(raw) + "\n")
        if request.url.path.endswith("/archives"):
            return httpx.Response(200, json={"archives": ["https://api.chess.com/pub/player/alice/games/2026/11"]})
        return httpx.Response(200, json={"games": [{"url": f"https://www.chess.com/game/live/{source_id}", "rules": "chess",
            "white": {"username": "Alice"}, "black": {"username": "Bob"}, "pgn": PGN, "end_time": ENDED}]})
    service.importer.transport = httpx.MockTransport(response)
    try:
        found = client.post("/api/plugins/gambit/action", json={"session_id": "fresh-import", "action": "find_games",
                            "platform": platform, "username": "Alice", "limit": 10}).json()
        assert found["ok"] and found["games"][0]["number"] == 1 and found["games"][0]["source_id"] == source_id
        assert "pgn" not in json.dumps(found)
        assert service.store.session("fresh-import")["initialized"] and service.state("fresh-import")["board"] is None
        # Generic board act() includes its old current game_id; source row identity wins.
        opened = client.post("/api/plugins/gambit/action", json={"session_id": "fresh-import", "action": "open_replay",
                             "game_id": "old-board-id", "platform": platform, "username": "Alice",
                             "source_id": source_id, "game_number": 1}).json()
        assert opened["ok"] and opened["board"]["match"]["platform"] == platform
        assert opened["board"]["match"]["username"] == "Alice" and opened["board"]["match"]["source_id"] == source_id
        older = client.post("/api/plugins/gambit/action", json={"session_id": "fresh-import", "action": "find_games",
                            "platform": platform, "username": "Alice", "before": ENDED}).json()
        assert older["ok"] and older["games"] == []
        assert service.store.session("fresh-import")["last_search"]["older_than"] is None
        assert client.post("/api/plugins/gambit/action", json={"session_id": "fresh-import", "action": "find_games",
                           "platform": platform, "username": "Alice"}, headers={"Origin": "https://unrelated.example"}).status_code == 403
    finally:
        service.stop()
