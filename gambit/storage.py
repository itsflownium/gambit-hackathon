"""Profile-local, transactional chess state. One revision for every mutation."""
from __future__ import annotations

import io
import datetime as dt
import json
import math
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path

import chess
import chess.pgn

from .errors import GambitError, StalePosition


class Store:
    def __init__(self, directory: Path):
        self.directory = Path(directory)
        self.directory.mkdir(parents=True, exist_ok=True)
        self.path = self.directory / "gambit.sqlite3"
        with self.db() as db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS games (
                    id TEXT PRIMARY KEY, source_key TEXT UNIQUE, record TEXT NOT NULL,
                    revision INTEGER NOT NULL DEFAULT 0, updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sessions (
                    id TEXT PRIMARY KEY, record TEXT NOT NULL, updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS session_aliases (
                    alias TEXT PRIMARY KEY, canonical TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS analyses (
                    key TEXT PRIMARY KEY, record TEXT NOT NULL, updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS imports (
                    key TEXT PRIMARY KEY, record TEXT NOT NULL, updated REAL NOT NULL
                );
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT, game_id TEXT NOT NULL,
                    kind TEXT NOT NULL, record TEXT NOT NULL, created REAL NOT NULL
                );
                PRAGMA user_version = 1;
            """)

    @contextmanager
    def db(self):
        conn = sqlite3.connect(self.path, timeout=10)
        conn.row_factory = sqlite3.Row
        try:
            with conn:
                yield conn
        finally:
            conn.close()

    def session(self, sid: str) -> dict:
        if not sid:
            raise GambitError("Open a Hermes chat and initialize it with /chess first.")
        with self.db() as db:
            alias = db.execute("SELECT canonical FROM session_aliases WHERE alias=?", (sid,)).fetchone()
            if alias:
                sid = alias[0]
            row = db.execute("SELECT record FROM sessions WHERE id=?", (sid,)).fetchone()
        return json.loads(row[0]) if row else {
            "id": sid, "initialized": False, "game_id": None, "mode": "play",
            "cursor": 0, "view_revision": 0, "perspective": "white", "hint": 0,
        }

    def save_session(self, session: dict) -> dict:
        with self.db() as db:
            db.execute("INSERT INTO sessions VALUES(?,?,?) ON CONFLICT(id) DO UPDATE SET "
                       "record=excluded.record,updated=excluded.updated",
                       (session["id"], json.dumps(session), time.time()))
        return session

    def mutate_session(self, sid: str, function) -> dict:
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            alias = db.execute("SELECT canonical FROM session_aliases WHERE alias=?", (sid,)).fetchone()
            if alias:
                sid = alias[0]
            row = db.execute("SELECT record FROM sessions WHERE id=?", (sid,)).fetchone()
            if row is None:
                raise GambitError("Initialize this chat with /chess first.")
            record = json.loads(row[0])
            function(record)
            db.execute("UPDATE sessions SET record=?,updated=? WHERE id=?",
                       (json.dumps(record), time.time(), sid))
        return record

    def add_session_aliases(self, canonical: str, aliases):
        canonical = self.session(canonical)["id"]
        with self.db() as db:
            for alias in set(aliases) | {canonical}:
                if not isinstance(alias, str) or not alias or len(alias) > 256:
                    continue
                existing = db.execute("SELECT canonical FROM session_aliases WHERE alias=?", (alias,)).fetchone()
                if existing and existing[0] != canonical:
                    raise StalePosition("These session identities are already bound to different chess chats.")
                db.execute("INSERT OR IGNORE INTO session_aliases VALUES(?,?)", (alias, canonical))

    def session_aliases(self, sid: str):
        canonical = self.session(sid)["id"]
        with self.db() as db:
            aliases = [row[0] for row in db.execute("SELECT alias FROM session_aliases WHERE canonical=?", (canonical,))]
        return sorted(set(aliases) | {canonical})

    def initialize(self, sid: str) -> dict:
        s = self.session(sid)
        if s["initialized"]:
            return s
        s["initialized"] = True
        return self.save_session(s)

    def attach(self, sid: str, game_id: str, mode: str, perspective: str, cursor=0) -> dict:
        def attach(s):
            s.update(initialized=True, game_id=game_id, mode=mode, perspective=perspective,
                     cursor=cursor, hint=0, view_revision=s.get("view_revision", 0) + 1)
        return self.mutate_session(sid, attach)

    def game(self, gid: str) -> dict:
        with self.db() as db:
            row = db.execute("SELECT record,revision FROM games WHERE id=?", (gid,)).fetchone()
        if row is None:
            raise GambitError("That game was not found in this Hermes profile.")
        value = json.loads(row[0])
        value["revision"] = row[1]
        return value

    def create(self, human="white", strength="balanced", *, mode="coach", record: dict | None = None) -> dict:
        if human not in {"white", "black"} or strength not in {"learning", "balanced", "strong"}:
            raise GambitError("Choose White or Black and Learning, Balanced, or Strong.")
        if mode not in {"normal", "coach"}:
            raise GambitError("Choose Normal or Coach mode.")
        now = time.time()
        value = record or {
            "id": uuid.uuid4().hex, "source": "hermes", "source_key": None,
            "initial_fen": chess.STARTING_FEN, "moves": [], "human": human,
            "white": "You" if human == "white" else "Hermes",
            "black": "Hermes" if human == "white" else "You",
            "strength": strength, "play_mode": mode, "result": "*", "created": now,
            "pending": None, "last_reply": None, "annotations": {},
        }
        with self.db() as db:
            if value.get("source_key"):
                old = db.execute("SELECT id FROM games WHERE source_key=?", (value["source_key"],)).fetchone()
                if old:
                    return self.game(old[0])
            db.execute("INSERT INTO games VALUES(?,?,?,?,?)",
                       (value["id"], value.get("source_key"), json.dumps(value), 0, now))
        return self.game(value["id"])

    def practice(self, sid: str, game_id: str, *, view_revision=None, mode=None, prepare=None) -> dict:
        """Create and select a branch only if the displayed source position is still current."""
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            alias = db.execute("SELECT canonical FROM session_aliases WHERE alias=?", (sid,)).fetchone()
            if alias:
                sid = alias[0]
            row = db.execute("SELECT record FROM sessions WHERE id=?", (sid,)).fetchone()
            if row is None:
                raise GambitError("Initialize this chat with /chess first.")
            session = json.loads(row[0])
            if session.get("game_id") != game_id or session.get("mode") != "replay":
                raise StalePosition("The selected replay changed. Refresh the board and try again.")
            if view_revision is not None and (type(view_revision) is not int or session.get("view_revision", 0) != view_revision):
                raise StalePosition("The replay position changed. Refresh the board and try again.")
            row = db.execute("SELECT record FROM games WHERE id=?", (game_id,)).fetchone()
            if row is None:
                raise GambitError("The original match is no longer saved.")
            source = json.loads(row[0])
            ply = session.get("cursor", 0)
            if type(ply) is not int or not 0 <= ply <= len(source["moves"]):
                raise StalePosition("The replay position changed. Refresh the board and try again.")
            board = board_for(source, ply)
            if board.is_game_over():
                raise GambitError("This position has ended. Move back in the replay to play from an earlier position.")
            human = session.get("perspective", source["human"])
            chosen_mode = mode or source.get("play_mode", "coach")
            if chosen_mode not in {"normal", "coach"}:
                raise GambitError("Choose Normal or Coach mode.")
            original = source
            if source.get("practice_of"):
                row = db.execute("SELECT record FROM games WHERE id=?", (source["practice_of"]["game_id"],)).fetchone()
                if row is not None:
                    original = json.loads(row[0])
            identity = match_context(source, human, original=original if original is not source else None)
            now = time.time()
            game = {
                "id": uuid.uuid4().hex, "source": "hermes", "source_key": None,
                "initial_fen": source["initial_fen"], "moves": source["moves"][:ply], "human": human,
                "white": "You" if human == "white" else "Hermes",
                "black": "Hermes" if human == "white" else "You",
                "strength": source.get("strength", "balanced"), "play_mode": chosen_mode,
                "result": "*", "created": now, "pending": None, "last_reply": None, "annotations": {},
                "practice_of": {"game_id": identity["game_id"] if identity else original["id"], "start_ply": ply,
                                "white": identity["white"] if identity else original["white"],
                                "black": identity["black"] if identity else original["black"],
                                "username": identity["username"] if identity else original[human]},
                "source_match": identity,
            }
            if prepare:
                # Validation and the first move belong to this transaction. A rejected
                # gesture must not leave an empty branch or change the selected match.
                prepare(game)
            db.execute("INSERT INTO games VALUES(?,?,?,?,?)",
                       (game["id"], None, json.dumps(game), 0, now))
            session.update(game_id=game["id"], mode="play", perspective=human, cursor=0,
                           hint=0, view_revision=session.get("view_revision", 0) + 1)
            db.execute("UPDATE sessions SET record=?,updated=? WHERE id=?", (json.dumps(session), now, sid))
            db.execute("INSERT INTO events(game_id,kind,record,created) VALUES(?,?,?,?)",
                       (game["id"], "practice_started", json.dumps({"revision": 0, "moves": game["moves"],
                                                                  "result": game["result"]}), now))
        return self.game(game["id"])

    def mutate(self, gid: str, revision: int, function, kind="action", *, pending_token=None) -> dict:
        with self.db() as db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT record,revision FROM games WHERE id=?", (gid,)).fetchone()
            if row is None:
                raise GambitError("This game no longer exists.")
            g = json.loads(row[0])
            if pending_token is not None:
                if not g.get("pending") or g["pending"]["token"] != pending_token:
                    raise StalePosition("The pending turn was cancelled.")
                # Reviews and mode changes may revise metadata during calculation.
                # The pending token identifies this exact turn under the write lock.
                revision = row[1]
            elif type(revision) is not int or row[1] != revision:
                raise StalePosition("The position changed. Refresh the board and try again.")
            function(g)
            new_revision = revision + 1
            db.execute("UPDATE games SET record=?,revision=?,updated=? WHERE id=?",
                       (json.dumps(g), new_revision, time.time(), gid))
            db.execute("INSERT INTO events(game_id,kind,record,created) VALUES(?,?,?,?)",
                       (gid, kind, json.dumps({"revision": new_revision, "moves": g["moves"],
                                              "result": g["result"]}), time.time()))
        return self.game(gid)

    def list_games(self, limit=30) -> list[dict]:
        with self.db() as db:
            rows = db.execute("SELECT id FROM games ORDER BY updated DESC LIMIT ?", (min(100, limit),)).fetchall()
        return [self.game(row[0]) for row in rows]

    def cached(self, table: str, key: str, max_age: float | None = None):
        if table not in {"analyses", "imports"}:
            raise ValueError("Invalid cache")
        with self.db() as db:
            row = db.execute(f"SELECT record,updated FROM {table} WHERE key=?", (key,)).fetchone()
        if not row or (max_age is not None and time.time() - row[1] > max_age):
            return None
        return json.loads(row[0])

    def cache(self, table: str, key: str, record: dict):
        if table not in {"analyses", "imports"}:
            raise ValueError("Invalid cache")
        with self.db() as db:
            db.execute(f"INSERT INTO {table} VALUES(?,?,?) ON CONFLICT(key) DO UPDATE SET "
                       "record=excluded.record,updated=excluded.updated",
                       (key, json.dumps(record), time.time()))

    def delete(self, gid: str):
        with self.db() as db:
            db.execute("DELETE FROM games WHERE id=?", (gid,))
            db.execute("DELETE FROM events WHERE game_id=?", (gid,))
            db.execute("DELETE FROM analyses WHERE json_extract(record,'$.game_id')=? OR key LIKE ?",
                       (gid, f"summary:{gid}:%"))
            rows = db.execute("SELECT id,record FROM sessions").fetchall()
            for row in rows:
                s = json.loads(row[1])
                if s.get("game_id") == gid:
                    s.update(game_id=None, cursor=0, hint=0)
                    db.execute("UPDATE sessions SET record=? WHERE id=?", (json.dumps(s), row[0]))


def board_for(game: dict, ply: int | None = None) -> chess.Board:
    board = chess.Board(game["initial_fen"])
    for uci in game["moves"][:ply]:
        move = chess.Move.from_uci(uci)
        if move not in board.legal_moves:
            raise GambitError("The saved game contains an invalid move.")
        board.push(move)
    return board


def parse_move(board: chess.Board, notation: str) -> chess.Move:
    if not isinstance(notation, str) or len(notation) > 24:
        raise GambitError("Use a legal move such as Nf3 or g1f3.")
    try:
        return board.parse_uci(notation.strip())
    except ValueError:
        try:
            return board.parse_san(notation.strip())
        except ValueError as exc:
            raise GambitError("That move is not legal in the current position.") from exc


def game_pgn(game: dict, *, annotated=True) -> str:
    pgn = chess.pgn.Game()
    pgn.setup(chess.Board(game["initial_fen"]))
    if game.get("original_pgn"):
        pgn.headers.update(chess.pgn.read_headers(io.StringIO(game["original_pgn"])) or {})
    pgn.headers.update(White=game["white"], Black=game["black"], Result=game["result"],
                       Event="Hermes Gambit", Site=game.get("url") or "Local")
    node = pgn
    for index, uci in enumerate(game["moves"], 1):
        node = node.add_variation(chess.Move.from_uci(uci))
        if annotated:
            note = game.get("annotations", {}).get(str(index), {})
            node.comment = note.get("text", "")
    return str(pgn)


def import_pgn(text: str, *, source: str, source_id: str, username: str,
               url: str = "", metadata: dict | None = None) -> dict:
    if not isinstance(text, str) or not text or len(text.encode()) > 2_000_000:
        raise GambitError("The game has no usable PGN or exceeds the import limit.")
    pgn = chess.pgn.read_game(io.StringIO(text))
    if pgn is None or pgn.errors:
        raise GambitError("The source game contains incomplete or invalid chess notation.")
    if pgn.headers.get("Variant", "Standard").lower() not in {"standard", "chess", "from position"}:
        raise GambitError("This release supports standard chess games.")
    if pgn.headers.get("Result", "*") == "*":
        raise GambitError("Choose a completed match for coaching replay.")
    board = pgn.board()
    if not board.is_valid() or board.chess960:
        raise GambitError("The game does not start from a valid standard chess position.")
    initial_fen = board.fen()
    moves = []
    for node in pgn.mainline():
        if node.move not in board.legal_moves:
            raise GambitError("The game contains an illegal move.")
        board.push(node.move)
        moves.append(node.move.uci())
        if len(moves) > 2500:
            raise GambitError("The game exceeds the supported length.")
    white, black = pgn.headers.get("White", "White"), pgn.headers.get("Black", "Black")
    if username.casefold() not in {white.casefold(), black.casefold()}:
        raise GambitError("The selected username is not a player in this match.")
    return {
        "id": uuid.uuid4().hex, "source": source, "source_key": f"{source}:{source_id}",
        "source_id": source_id, "url": url, "username": username, "white": white, "black": black,
        "human": "white" if white.casefold() == username.casefold() else "black",
        "initial_fen": initial_fen, "moves": moves, "result": pgn.headers["Result"],
        "original_pgn": text, "created": time.time(), "metadata": metadata or {},
        "pending": None, "last_reply": None, "annotations": {}, "strength": "strong",
    }


def match_context(game: dict, perspective: str, *, original: dict | None = None) -> dict | None:
    """Return source identity independently of a practice game's You/Hermes labels."""
    practice = game.get("practice_of")
    if practice:
        if original is not None and original.get("id") != game["id"]:
            identity = match_context(original, perspective)
        else:
            identity = game.get("source_match")
        if identity:
            identity = dict(identity)
            identity.update(colour=perspective, username=identity.get(perspective) or identity.get("username"))
            return identity
        # Older practice records retain player names even if the original was deleted.
        white, black = practice.get("white", "White"), practice.get("black", "Black")
        return {"game_id": practice["game_id"], "platform": None, "username": white if perspective == "white" else black,
                "colour": perspective, "source_id": None, "url": None, "date": None, "ended_at": None,
                "white": white, "black": black, "result": None}
    if game.get("source") == "hermes":
        return None
    metadata = game.get("metadata") or {}
    ended = metadata.get("ended_at")
    if type(ended) not in {int, float} or not math.isfinite(ended) or ended <= 0:
        ended = None
    date = None
    if ended is not None:
        try:
            date = dt.datetime.fromtimestamp(ended, dt.timezone.utc).date().isoformat()
        except (OverflowError, ValueError, OSError):
            ended = None
    if date is None and game.get("original_pgn"):
        headers = chess.pgn.read_headers(io.StringIO(game["original_pgn"])) or {}
        for name in ["UTCDate", "Date"]:
            try:
                date = dt.datetime.strptime(headers.get(name, ""), "%Y.%m.%d").date().isoformat()
                break
            except ValueError:
                pass
    return {"game_id": game["id"], "platform": game.get("source"), "username": game[perspective],
            "colour": perspective, "source_id": game.get("source_id"), "url": game.get("url") or None,
            "date": date, "ended_at": ended, "white": game["white"], "black": game["black"], "result": game["result"]}


def snapshot(game: dict, session: dict, *, original: dict | None = None) -> dict:
    replay = session.get("mode") == "replay"
    ply = max(0, min(int(session.get("cursor", 0)), len(game["moves"]))) if replay else len(game["moves"])
    board = board_for(game, ply)
    moves = [{"uci": m.uci(), "from": chess.square_name(m.from_square),
              "to": chess.square_name(m.to_square), "san": board.san(m),
              "promotion": chess.piece_symbol(m.promotion) if m.promotion else None}
             for m in board.legal_moves]
    history_board = chess.Board(game["initial_fen"])
    history = []
    for i, uci in enumerate(game["moves"]):
        move = chess.Move.from_uci(uci)
        history.append({"ply": i + 1, "san": history_board.san(move), "uci": uci,
                        "colour": "white" if history_board.turn else "black"})
        history_board.push(move)
    outcome = board.outcome()
    return {
        "id": game["id"], "revision": game["revision"], "mode": session["mode"],
        "play_mode": game.get("play_mode", "coach"),
        "view_revision": session.get("view_revision", 0), "fen": board.fen(),
        "pieces": {chess.square_name(s): p.symbol() for s, p in board.piece_map().items()},
        "legal_moves": moves if (replay or game["result"] == "*") and outcome is None else [],
        "turn": "white" if board.turn else "black", "human": session.get("perspective", game["human"]) if replay else game["human"],
        "perspective": session.get("perspective", game["human"]), "white": game["white"],
        "black": game["black"], "source": game["source"], "source_url": game.get("url"),
        "ply": ply, "total_plies": len(game["moves"]), "history": history,
        "last_move": game["moves"][ply - 1] if ply else None,
        "last_san": history[ply - 1]["san"] if ply else None,
        "check_square": chess.square_name(board.king(board.turn)) if board.is_check() else None,
        "result": game["result"], "position_result": outcome.result() if outcome else "*",
        "claimable_draw": board.can_claim_draw() if not replay and game["result"] == "*" else False,
        "pending": game.get("pending"), "last_reply": game.get("last_reply"),
        "practice": game.get("practice_of"), "termination": game.get("termination"),
        "match": match_context(game, session.get("perspective", game["human"]) if replay else game["human"], original=original),
        "annotation": game.get("annotations", {}).get(str(ply)),
    }
