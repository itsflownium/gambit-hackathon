"""Bounded, local UCI calculations. Fresh processes isolate strength settings."""
from __future__ import annotations

import hashlib
import json
import shutil
import threading
from contextlib import contextmanager
from pathlib import Path

import chess
import chess.engine

from .errors import EngineUnavailable
from .storage import board_for


class Engine:
    def __init__(self, directory: Path, configured_path="", seconds=0.4):
        self.directory = Path(directory)
        self.configured_path = configured_path
        self.seconds = max(0.05, min(float(seconds), 3.0))
        self.slots = threading.BoundedSemaphore(2)

    def executable(self) -> str:
        candidates = [self.configured_path, str(self.directory / "engine" / "stockfish"),
                      shutil.which("stockfish"), "/opt/homebrew/bin/stockfish", "/usr/local/bin/stockfish"]
        for candidate in candidates:
            if candidate and Path(candidate).is_file():
                return str(Path(candidate).resolve())
        raise EngineUnavailable("Stockfish is not configured. Set Gambit's Stockfish executable in Hermes plugin settings.")

    @contextmanager
    def process(self):
        if not self.slots.acquire(timeout=4):
            raise EngineUnavailable("The chess engine is busy. Try again in a moment.")
        engine = None
        try:
            engine = chess.engine.SimpleEngine.popen_uci([self.executable()], timeout=4)
            engine.configure({"Threads": 1, "Hash": 64})
            yield engine
        except (OSError, chess.engine.EngineError, TimeoutError) as exc:
            raise EngineUnavailable("The chess engine could not complete this calculation. Check the Stockfish path and retry.") from exc
        finally:
            if engine is not None:
                engine.close()
            self.slots.release()

    def health(self) -> dict:
        with self.process() as engine:
            engine.ping()
            return {"ready": True, "name": engine.id.get("name", "Stockfish"), "path": self.executable()}

    @staticmethod
    def line(board: chess.Board, info: dict) -> dict:
        position = board.copy()
        san, uci = [], []
        for move in info.get("pv", [])[:8]:
            if move not in position.legal_moves:
                break
            san.append(position.san(move))
            uci.append(move.uci())
            position.push(move)
        score = info.get("score")
        white = score.white() if score is not None else None
        return {"uci": uci[0] if uci else None, "line_uci": uci, "line_san": san,
                "score_white_cp": white.score() if white else None,
                "mate_white": white.mate() if white else None, "depth": info.get("depth")}

    def position(self, board: chess.Board, *, seconds=None, multipv=2) -> dict:
        outcome = board.outcome()
        if outcome:
            return {"terminal": outcome.result(), "termination": outcome.termination.name,
                    "lines": [], "engine": "rules", "budget_seconds": 0}
        budget = self.seconds if seconds is None else max(0.05, min(float(seconds), 3.0))
        with self.process() as engine:
            infos = engine.analyse(board, chess.engine.Limit(time=budget), multipv=min(multipv, board.legal_moves.count()))
            return {"lines": [self.line(board, info) for info in infos],
                    "engine": engine.id.get("name", "Stockfish"), "budget_seconds": budget}

    def candidates(self, board: chess.Board, strength="balanced") -> dict:
        with self.process() as engine:
            if "Skill Level" in engine.options:
                engine.configure({"Skill Level": {"learning": 3, "balanced": 10, "strong": 20}[strength]})
            chosen = engine.play(board, chess.engine.Limit(time=0.45)).move
            infos = engine.analyse(board, chess.engine.Limit(time=0.35), multipv=min(3, board.legal_moves.count()))
            lines = [self.line(board, info) for info in infos]
            choices = [chosen.uci()] if chosen else []
            choices.extend(line["uci"] for line in lines if line["uci"] and line["uci"] not in choices)
            return {"choices": choices, "recommended": choices[0], "lines": lines,
                    "engine": engine.id.get("name", "Stockfish")}

    @staticmethod
    def cache_key(game: dict, ply: int, seconds: float, engine_path: str) -> str:
        # Preserve history: equal FENs can have different repetition claims.
        engine_file = Path(engine_path)
        stamp = (engine_file.stat().st_mtime_ns, engine_file.stat().st_size)
        payload = [game["id"], game["initial_fen"], game["moves"][:ply], seconds, str(engine_file), stamp]
        return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()

    def review(self, game: dict, ply: int, store) -> dict:
        if not 1 <= ply <= len(game["moves"]):
            return {"ply": ply, "message": "This is the starting position. Make or replay a move to review it."}
        key = self.cache_key(game, ply, self.seconds, self.executable())
        cached = store.cached("analyses", key)
        if cached:
            return cached
        before = board_for(game, ply - 1)
        move = chess.Move.from_uci(game["moves"][ply - 1])
        mover = before.turn
        san = before.san(move)
        capture = before.piece_at(move.to_square)
        prior = self.position(before)
        after = before.copy()
        after.push(move)
        following = self.position(after, multipv=1)
        first = prior["lines"][0] if prior["lines"] else {}
        second = following["lines"][0] if following["lines"] else {}
        if following.get("terminal") == "1/2-1/2":
            second = {"score_white_cp": 0}
        loss = self._loss(first, second, mover)
        bad_mate = second.get("mate_white") is not None and second["mate_white"] * (1 if mover else -1) < 0
        if ((loss is not None and loss >= 150) or bad_mate) and not after.is_game_over():
            prior = self.position(before, seconds=max(self.seconds, 1.0), multipv=2)
            following = self.position(after, seconds=max(self.seconds, 1.0), multipv=1)
            first, second = prior["lines"][0], following["lines"][0]
            loss = self._loss(first, second, mover)
            bad_mate = second.get("mate_white") is not None and second["mate_white"] * (1 if mover else -1) < 0
        facts = []
        if capture:
            facts.append("Captured a " + chess.piece_name(capture.piece_type) + ".")
        if before.is_en_passant(move):
            facts.append("Captured a pawn en passant.")
        if before.is_castling(move):
            facts.append("Castled to connect the king and rook.")
        if after.is_checkmate():
            facts.append("Delivered checkmate.")
        elif after.is_check():
            facts.append("Gave check.")
        if after.is_stalemate():
            facts.append("Ended the game in stalemate.")
        if bad_mate:
            facts.append(f"The engine finds forced mate for {'Black' if mover else 'White'} in {abs(second['mate_white'])} moves from the resulting position.")
        already_mated = first.get("mate_white") is not None and first["mate_white"] * (1 if mover else -1) < 0
        piece = after.piece_at(move.to_square)
        if piece and piece.piece_type != chess.KING:
            legal_captures = [m.uci() for m in after.legal_moves if m.to_square == move.to_square]
            if legal_captures and not after.attackers(mover, move.to_square):
                facts.append(f"The {chess.piece_name(piece.piece_type)} on {chess.square_name(move.to_square)} is undefended and can be legally captured.")
        classification = (
            "major error" if loss is not None and loss >= 250 else
            "mistake" if loss is not None and loss >= 120 else
            "small inaccuracy" if loss is not None and loss >= 40 else "sound move")
        if after.is_checkmate():
            classification = "checkmate"
        elif bad_mate:
            classification = "forced mate remains" if already_mated else "allows forced mate"
        result = {"game_id": game["id"], "ply": ply, "move_number": before.fullmove_number,
                  "mover": "white" if mover else "black", "played_san": san, "played_uci": move.uci(),
                  "classification": classification, "loss_cp": loss, "facts": facts,
                  "before": prior, "after": following, "better_alternative": first,
                  "fen_before": before.fen(), "fen_after": after.fen(),
                  "scope": "Retrospective analysis of the move just played; not a suggestion for the next player move."}
        store.cache("analyses", key, result)
        return result

    @staticmethod
    def _loss(first, second, mover):
        a, b = first.get("score_white_cp"), second.get("score_white_cp")
        if a is None or b is None:
            return None
        return max(0, (a - b) * (1 if mover else -1))
