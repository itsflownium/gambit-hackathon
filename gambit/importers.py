"""Public, completed-game imports. No browser automation or account credentials."""
from __future__ import annotations

import datetime as dt
import json
import re
import threading
import time
from urllib.parse import quote

import httpx

from .errors import ImportFailure

_LOCKS = {"chess.com": threading.Lock(), "lichess": threading.Lock()}
_RESUME = {"chess.com": 0.0, "lichess": 0.0}
AGENT = "Hermes-Gambit/0.2.2 (local chess coaching; https://github.com/itsflownium)"


def platform_name(value: str) -> str:
    value = str(value).strip().lower()
    aliases = {"chesscom": "chess.com", "chess.com": "chess.com", "lichess.org": "lichess", "lichess": "lichess"}
    if value not in aliases:
        raise ImportFailure("Choose Chess.com or Lichess.")
    return aliases[value]


def valid_username(value: str) -> str:
    if not isinstance(value, str) or not re.fullmatch(r"[A-Za-z0-9_-]{2,50}", value):
        raise ImportFailure("Enter the player's username, without a profile URL.")
    return value


class Importer:
    def __init__(self, store, transport=None):
        self.store = store
        self.transport = transport

    def _request(self, platform: str, url: str, *, params=None, accept="application/json") -> bytes:
        with _LOCKS[platform]:
            wait = _RESUME[platform] - time.monotonic()
            if wait > 0:
                raise ImportFailure(f"{platform} asked us to wait. Retry in {int(wait) + 1} seconds.")
            try:
                with httpx.Client(timeout=httpx.Timeout(25, connect=6), follow_redirects=False,
                                  transport=self.transport, headers={"User-Agent": AGENT, "Accept": accept}) as client:
                    with client.stream("GET", url, params=params) as response:
                        if response.status_code == 429:
                            try:
                                retry = int(response.headers.get("Retry-After", "60"))
                            except ValueError:
                                retry = 60
                            _RESUME[platform] = time.monotonic() + max(60, min(retry, 3600))
                            raise ImportFailure(f"{platform} is rate-limiting requests. Cached games remain available; retry after a minute.")
                        if response.status_code == 404:
                            raise ImportFailure("That username or game archive was not found.")
                        if response.status_code != 200:
                            raise ImportFailure(f"{platform} could not provide games (HTTP {response.status_code}). Try again later.")
                        data = bytearray()
                        for chunk in response.iter_bytes():
                            data.extend(chunk)
                            if len(data) > 32_000_000:
                                raise ImportFailure("That archive is too large. Choose a narrower date range.")
                        return bytes(data)
            except httpx.HTTPError as exc:
                raise ImportFailure(f"Could not reach {platform}. Your saved matches remain available.") from exc

    def search(self, platform: str, username: str, *, limit=20, before=None, refresh=False) -> dict:
        platform = platform_name(platform)
        username = valid_username(username)
        if type(limit) is not int or not 1 <= limit <= 50:
            raise ImportFailure("Choose between 1 and 50 games per search.")
        if before is not None and (type(before) not in {int, float} or before <= 0):
            raise ImportFailure("Use a valid date for older games.")
        key = f"{platform}:{username.casefold()}:{limit}:{before}"
        old = self.store.cached("imports", key)
        # A first game can appear shortly after an initially empty archive.
        # Keep negative results briefly; explicit refresh always rechecks the source.
        cache_seconds = 3600 if old and old.get("games") else 30
        if old and not refresh and time.time() - old.get("fetched_at", 0) < cache_seconds:
            return {**old, "cached": True}
        try:
            games = self._chesscom(username, limit, before) if platform == "chess.com" else self._lichess(username, limit, before)
        except ImportFailure:
            if old and old.get("games"):
                return {**old, "cached": True, "notice": "The source is unavailable. Showing saved results."}
            raise
        result = {"platform": platform, "username": username, "games": games,
                  "fetched_at": time.time(), "cached": False,
                  "older_than": min((g["ended_at"] for g in games), default=0) or None}
        self.store.cache("imports", key, result)
        for game in games:
            self.store.cache("imports", f"game:{platform}:{game['source_id']}", game)
            self.store.cache("imports", f"game:{platform}:{username.casefold()}:{game['source_id']}", game)
        return result

    def selected(self, platform: str, source_id: str, *, username=None) -> dict:
        platform = platform_name(platform)
        if not isinstance(source_id, str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,100}", source_id):
            raise ImportFailure("Select a game from the username search results.")
        game = None
        if username is not None:
            username = valid_username(username)
            game = self.store.cached("imports", f"game:{platform}:{username.casefold()}:{source_id}")
        if game is None:
            # Older cached searches predate per-username selection keys. Their
            # PGN remains usable, but callers must supply their own perspective.
            game = self.store.cached("imports", f"game:{platform}:{source_id}")
        if game is None:
            raise ImportFailure("Search for the username first, then choose a returned game ID.")
        return game

    def _chesscom(self, username, limit, before):
        escaped = quote(username.lower(), safe="")
        root = f"https://api.chess.com/pub/player/{escaped}/games"
        try:
            archives = json.loads(self._request("chess.com", root + "/archives"))["archives"]
            if not isinstance(archives, list):
                raise ValueError("archives")
            games = []
            fetched = 0
            for archive in reversed(archives):
                # Reconstruct the URL instead of following server-supplied arbitrary URLs.
                match = re.fullmatch(re.escape(root) + r"/(\d{4})/(\d{2})", archive, re.I)
                if not match:
                    continue
                year, month = map(int, match.groups())
                month_start = dt.datetime(year, month, 1, tzinfo=dt.timezone.utc).timestamp()
                if before and month_start >= before:
                    continue
                batch = json.loads(self._request("chess.com", f"{root}/{year}/{month:02d}"))["games"]
                fetched += 1
                for raw in batch:
                    url = raw.get("url", "")
                    identity = re.fullmatch(r"https://www\.chess\.com/game/(?:live|daily)/(\d+)", url)
                    if not identity or raw.get("rules", "chess") != "chess" or not raw.get("pgn"):
                        continue
                    ended = raw.get("end_time", 0)
                    if before and ended >= before:
                        continue
                    games.append(self._metadata(raw, identity[1], username, url, ended, "chess.com"))
                if len(games) >= limit or fetched >= 4:
                    break
            return sorted(games, key=lambda g: g["ended_at"], reverse=True)[:limit]
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
            raise ImportFailure("Chess.com returned an unreadable archive. Try refreshing later.") from exc

    def _lichess(self, username, limit, before):
        params = {"max": limit, "ongoing": "false", "finished": "true", "pgnInJson": "true",
                  "moves": "true", "tags": "true", "clocks": "true", "sort": "dateDesc"}
        if before:
            params["until"] = max(1, int(before * 1000) - 1)
        body = self._request("lichess", f"https://lichess.org/api/games/user/{quote(username, safe='')}",
                             params=params, accept="application/x-ndjson")
        games = []
        try:
            for line in body.splitlines():
                if not line.strip():
                    continue
                raw = json.loads(line)
                if raw.get("variant", "standard") != "standard" or raw.get("status") in {"created", "started", "aborted"}:
                    continue
                gid = raw["id"]
                if not re.fullmatch(r"[A-Za-z0-9]{8,12}", gid) or not raw.get("pgn"):
                    continue
                players = raw.get("players", {})
                normalized = {
                    "white": {"username": players.get("white", {}).get("user", {}).get("name", "White"),
                              "rating": players.get("white", {}).get("rating")},
                    "black": {"username": players.get("black", {}).get("user", {}).get("name", "Black"),
                              "rating": players.get("black", {}).get("rating")},
                    "pgn": raw["pgn"], "time_class": raw.get("speed"),
                }
                games.append(self._metadata(normalized, gid, username, "https://lichess.org/" + gid,
                                            raw.get("lastMoveAt", raw.get("createdAt", 0)) / 1000, "lichess"))
            return games
        except (ValueError, TypeError, KeyError) as exc:
            raise ImportFailure("Lichess returned an incomplete game export. Try again later.") from exc

    @staticmethod
    def _metadata(raw, gid, username, url, ended, source):
        import io
        import chess.pgn
        headers = chess.pgn.read_headers(io.StringIO(raw["pgn"])) or {}
        return {"source_id": gid, "platform": source, "username": username, "url": url,
                "white": raw.get("white", {}).get("username", headers.get("White", "White")),
                "black": raw.get("black", {}).get("username", headers.get("Black", "Black")),
                "white_rating": raw.get("white", {}).get("rating"),
                "black_rating": raw.get("black", {}).get("rating"),
                "result": headers.get("Result", "*"), "ended_at": ended,
                "time_class": raw.get("time_class"), "pgn": raw["pgn"]}


def listing(result: dict) -> dict:
    games = []
    for number, game in enumerate(result["games"], 1):
        public = {k: v for k, v in game.items() if k != "pgn"}
        public["number"] = number
        username = result["username"]
        public["username"] = username
        colour = "white" if str(game.get("white", "")).casefold() == username.casefold() else "black" if str(game.get("black", "")).casefold() == username.casefold() else None
        public["colour"] = colour
        public["opponent"] = game.get("black" if colour == "white" else "white") if colour else None
        try:
            public["ended_at_utc"] = dt.datetime.fromtimestamp(game["ended_at"], dt.timezone.utc).isoformat()
        except (KeyError, ValueError, TypeError, OverflowError, OSError):
            public["ended_at_utc"] = None
        games.append(public)
    return {**result, "games": games}
