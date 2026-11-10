"""Standalone board and public Hermes conversation in a standard terminal.

The controller uses the same public service methods as the desktop board.
Rendering uses only the Python standard library; model explanations are
provided by ``TerminalCoach`` without exposing model reasoning or prompts.
"""
from __future__ import annotations

import asyncio
import copy
import inspect
import queue
import shlex
import sys
import threading
import time

from .errors import GambitError
from .terminal_view import (PIECES, board_grid, board_lines, clip_columns, display_width,
                            layout_for, safe_text, wrapped_lines)


HELP = """Enter SAN or UCI moves: e4, Nf3, e2e4, e7e8q.
hint [1-4]   Request the next hint level, or one specific level.
review       Ask Hermes to explain your preceding recorded move.
mode coach   Automatic brief move reviews; mode normal turns them off.
new [white|black] [coach|normal] [learning|balanced|strong]
saved       List saved matches; open NUMBER selects from the latest list.
import lichess USERNAME   Search public games (also chess.com).
replay      Review the current match; replay ID opens a saved match.
seek PLY    Jump to an exact half-move; first, prev, next, last also work.
practice    Play from the replay position; source returns to its recording.
resume      Resume an unfinished match against Hermes.
undo | resign | draw | export
PgUp/PgDn scroll the public conversation. Empty-input arrows navigate replay.
q quits. Your recorded game remains saved."""


def _call(function, *args, **kwargs):
    result = function(*args, **kwargs)
    return asyncio.run(result) if inspect.isawaitable(result) else result


class _CommandError(ValueError):
    pass


def _error_text(exc):
    if isinstance(exc, (GambitError, _CommandError)):
        return safe_text(str(exc) or "The action could not be completed.")
    # Provider exceptions may include credentials or raw model responses.
    return "The action could not be completed. Try again or check the local service logs."


def _integer(value, message):
    try:
        return int(value)
    except (ValueError, TypeError):
        raise _CommandError(message) from None


def _hint_text(evidence: dict) -> str:
    level = evidence.get("level", 1)
    parts = [f"Hint {level}/4", evidence.get("clue", "")]
    if evidence.get("piece"):
        parts.append(f"Consider your {evidence['piece']} on {evidence.get('from', '?')}.")
    if evidence.get("to"):
        parts.append(f"Look at {evidence['to']}.")
    if evidence.get("move"):
        parts.append(f"Move: {evidence['move']}.")
    if evidence.get("line"):
        line = evidence["line"]
        parts.append("Continuation: " + (" ".join(map(str, line)) if isinstance(line, list) else str(line)))
    return "\n".join(str(part) for part in parts if part)


def _review_text(evidence: dict) -> str:
    label = evidence.get("played_san") or "Recorded move"
    classification = evidence.get("classification")
    first = f"{label}: {classification}." if classification else str(label)
    facts = evidence.get("facts") or []
    return "\n".join([first] + [str(fact) for fact in facts])


class TerminalController:
    """Synchronous, testable terminal actions; the UI supplies its own worker.

    ``close`` only closes this terminal's coaching work. It never stops the
    shared service or cancels a committed opponent reply.
    """

    def __init__(self, service, session_id: str, *, colour="white", strength="balanced", mode="coach"):
        self.service = service
        self.session_id = session_id
        self.colour, self.strength, self.mode = colour, strength, mode
        self.state = {}
        self.messages = []
        self.busy = "Opening session"
        self.last_error = ""
        self.closed = False
        self._lock = threading.RLock()
        self._coach = None
        self._choices = []
        self._choice_kind = ""
        self._search = {}
        self._seen = set()
        self._message_counter = 0

    def snapshot(self):
        with self._lock:
            return {"state": copy.deepcopy(self.state), "messages": copy.deepcopy(self.messages),
                    "busy": self.busy, "error": self.last_error, "closed": self.closed}

    def _append(self, role, text, *, message_id=None):
        text = safe_text(text).strip()
        if not text:
            return
        with self._lock:
            if message_id is not None:
                if message_id in self._seen:
                    return
                self._seen.add(message_id)
            self._message_counter += 1
            self.messages.append({"id": str(self._message_counter), "role": role, "text": text})
            del self.messages[:-200]

    def _accept_state(self, state):
        if not isinstance(state, dict):
            return
        if state.get("ok") is False:
            raise _CommandError("The action could not be completed. Refresh and try again.")
        if "board" in state or "session" in state:
            with self._lock:
                self.state = state

    def initialize(self):
        state = _call(self.service.state, self.session_id)
        self._accept_state(state)
        if not (state.get("session") or {}).get("initialized"):
            _call(self.service.initialize, self.session_id)
        try:
            from .terminal_coach import TerminalCoach
        except ImportError:
            # The board can still run when the optional conversational adapter
            # is unavailable; direct hints/reviews remain real engine evidence.
            pass
        else:
            self._coach = TerminalCoach(self.service, self.session_id)
        if not state.get("board"):
            self._accept_state(_call(self.service.start, self.session_id, self.colour, self.strength, self.mode))
        self._append("status", "Enter a move such as e4 or Nf3. Use hint when you want help; ? lists commands.")
        with self._lock:
            self.busy = ""
        self.refresh()
        return self.state

    def _collect_coaching(self):
        if not self._coach or self.closed:
            return
        self._coach.observe(self.state)
        for event in self._coach.poll():
            phase = event.get("phase")
            prefix = "coach:" + str(event.get("request_id"))
            key = prefix + ":" + str(phase)
            evidence = event.get("evidence") or {}
            if evidence and phase not in {"stale", "cancelled"}:
                text = _hint_text(evidence) if event.get("kind") == "hint" else _review_text(evidence)
                self._append("hint" if event.get("kind") == "hint" else "review", text,
                             message_id=prefix + ":public-evidence")
            if phase in {"complete", "fallback", "unavailable"}:
                explanation = event.get("explanation") or ""
                if explanation:
                    role = "hermes" if event.get("origin") == "hermes" else "engine"
                    self._append(role, explanation, message_id=key)
                elif event.get("status"):
                    self._append("status", event["status"], message_id=key)
            elif event.get("status"):
                self._append("status", event["status"], message_id=key)

    def _collect_public_messages(self):
        # Only an explicit public transcript extension is accepted. The service
        # session's delivery queue contains prompts, not conversational output.
        getter = getattr(self.service, "terminal_messages", None)
        if not callable(getter):
            return
        for message in _call(getter, self.session_id) or []:
            if not isinstance(message, dict) or message.get("private"):
                continue
            if message.get("channel") in {"analysis", "reasoning", "thinking"}:
                continue
            role = str(message.get("role", "hermes")).lower()
            if role not in {"assistant", "hermes", "user", "coach", "hint", "status", "error"}:
                continue
            text = message.get("text") or message.get("content")
            if not isinstance(text, str):
                continue
            key = "public:" + str(message.get("id", role + ":" + text))
            self._append("hermes" if role == "assistant" else role, text, message_id=key)

    def _collect_reply(self):
        board = self.state.get("board") or {}
        reply = board.get("last_reply") or {}
        if not reply or reply.get("ply", 0) > board.get("ply", 0):
            return
        san = reply.get("san") or reply.get("move") or "a move"
        origin = reply.get("origin")
        if origin == "hermes":
            text = f"Hermes played {san}."
        elif origin == "recorded":
            text = f"Original opponent played the recorded reply {san}."
        elif origin == "legal_recovery":
            text = f"Legal recovery reply: {san}. Local engine analysis was unavailable at the move deadline."
        elif origin == "engine_deadline":
            text = f"Engine-assisted fallback: {san}. The move deadline was reached."
        elif origin == "engine_fallback":
            text = f"Engine-assisted fallback: {san}. Hermes's model was unavailable or did not finish in time."
        else:
            text = f"Local engine played {san} (engine-assisted reply)."
        key = "reply:" + str(board.get("id")) + ":" + str(reply.get("token", reply.get("ply")))
        self._append("move", text, message_id=key)

    def _collect_match_identity(self):
        board = self.state.get("board") or {}
        match = board.get("match") or {}
        if not match:
            return
        source_id = match.get("source_id") or match.get("game_id") or board.get("id")
        platform = match.get("platform") or "Recorded"
        text = (f"{platform} match {source_id}\n"
                f"White: {match.get('white', '?')} | Black: {match.get('black', '?')}\n"
                f"Perspective: {str(match.get('colour', board.get('human', 'white'))).title()}"
                + (f" | {match['date']}" if match.get("date") else ""))
        self._append("match", text, message_id="match:" + str(board.get("id")) + ":" + str(match.get("colour")))

    def refresh(self):
        if self.closed:
            return self.state
        self._accept_state(_call(self.service.state, self.session_id))
        self._collect_match_identity()
        self._collect_reply()
        self._collect_coaching()
        self._collect_public_messages()
        return self.state

    def _board(self):
        board = self.state.get("board")
        if not board:
            raise _CommandError("Start a match with new white coach.")
        return board

    def _action(self, action, **kwargs):
        board = self._board()
        return _call(self.service.action, self.session_id, action, revision=board.get("revision"),
                     game_id=board.get("id"), view_revision=board.get("view_revision"), **kwargs)

    def _list_choices(self, result, kind):
        self._choices = result.get("games") or []
        self._choice_kind = kind
        if not self._choices:
            self._append("status", "No matching games were found.")
        for index, game in enumerate(self._choices, 1):
            opponent = game.get("opponent")
            if isinstance(opponent, dict):
                opponent = opponent.get("username") or opponent.get("name")
            players = f"{game.get('white', '?')} - {game.get('black', '?')}"
            label = f"vs {opponent}" if opponent else players
            date = game.get("ended_at_utc") or game.get("date") or game.get("end_time") or game.get("played_at") or ""
            self._append("games", f"{index}. {label}  {game.get('result', '*')}  {date}")
        if self._choices:
            self._append("status", "Use open NUMBER to choose a match from this list.")

    def execute(self, command: str):
        """Execute one submitted line. All mutations retain backend revisions."""
        if self.closed:
            return {"ok": False, "message": "This terminal is closed."}
        raw = command.strip()
        if not raw:
            return {"ok": True}
        self._append("user", raw)
        with self._lock:
            self.last_error = ""
            self.busy = "Working"
        try:
            try:
                parts = shlex.split(raw.lstrip("/:"))
            except ValueError:
                raise _CommandError("Close any quoted text before submitting the command.") from None
            if not parts:
                return {"ok": True}
            name, args = parts[0].lower(), parts[1:]
            board = self.state.get("board") or {}
            result = None
            if name in {"q", "quit", "exit"}:
                self.close()
                return {"ok": True, "quit": True}
            if name in {"?", "help"}:
                self._append("help", HELP)
            elif name in {"hint", "h", "review"}:
                if name == "review":
                    if args:
                        raise _CommandError("Use review to explain the preceding move.")
                    if self._coach:
                        self._coach.submit_review()
                    else:
                        result = _call(self.service.review, self.session_id)
                        self._append("review", _review_text(result.get("evidence") or {}))
                else:
                    if len(args) > 1:
                        raise _CommandError("Use hint, or hint LEVEL from 1 to 4.")
                    level = _integer(args[0], "Hint levels run from 1 to 4.") if args else None
                    if level is not None and not 1 <= level <= 4:
                        raise _CommandError("Hint levels run from 1 to 4.")
                    if self._coach:
                        self._coach.submit_hint(level)
                    else:
                        result = _call(self.service.hint, self.session_id, level)
                        self._append("hint", _hint_text(result))
                if result is None:
                    result = {"ok": True, "status": "queued"}
            elif name == "mode":
                if len(args) != 1 or args[0].lower() not in {"normal", "coach"}:
                    raise _CommandError("Use mode coach or mode normal.")
                result = self._action("set_mode", mode=args[0].lower())
                self._append("status", f"{args[0].title()} mode enabled.")
            elif name in {"new", "start"}:
                colour, mode, strength = self.colour, self.mode, self.strength
                for arg in map(str.lower, args):
                    if arg in {"white", "black"}:
                        colour = arg
                    elif arg in {"normal", "coach"}:
                        mode = arg
                    elif arg in {"learning", "gentle", "balanced", "strong"}:
                        strength = "learning" if arg == "gentle" else arg
                    else:
                        raise _CommandError("Use new [white|black] [coach|normal] [learning|balanced|strong].")
                result = _call(self.service.start, self.session_id, colour, strength, mode)
                self._append("status", f"New match: you play {colour.title()} in {mode.title()} mode.")
            elif name in {"saved", "games"}:
                result = _call(self.service.action, self.session_id, "saved")
                self._list_choices(result, "saved")
            elif name in {"import", "find"}:
                if len(args) != 2:
                    raise _CommandError("Use import lichess USERNAME or import chess.com USERNAME.")
                result = _call(self.service.find_games, self.session_id, args[0], args[1])
                self._search = {"platform": result.get("platform", args[0]), "username": result.get("username", args[1])}
                self._list_choices(result, "import")
            elif name in {"open", "replay"}:
                if len(args) > 1:
                    raise _CommandError("Use open NUMBER or replay GAME_ID.")
                if name == "open" and args and args[0].isdigit():
                    index = int(args[0]) - 1
                    if not 0 <= index < len(self._choices):
                        raise _CommandError("Choose a number from the latest saved or imported match list.")
                    chosen = self._choices[index]
                    if self._choice_kind == "import":
                        result = _call(self.service.open_replay, self.session_id,
                                       source_id=chosen.get("source_id"), **self._search)
                    else:
                        result = _call(self.service.open_replay, self.session_id, game_id=chosen["id"])
                else:
                    game_id = args[0] if args else self._board()["id"]
                    result = _call(self.service.open_replay, self.session_id, game_id=game_id)
                self._append("status", "Replay opened. Use arrow keys, next, prev, first, last, or seek PLY.")
            elif name in {"seek", "next", "n", "prev", "previous", "p", "first", "last"}:
                board = self._board()
                if board.get("mode") != "replay":
                    raise _CommandError("Use replay before navigating recorded moves.")
                if name == "seek":
                    if len(args) != 1:
                        raise _CommandError("Use seek PLY, where 0 is the initial position.")
                    ply = _integer(args[0], "Use seek PLY, where 0 is the initial position.")
                elif args:
                    raise _CommandError("Replay navigation takes no extra arguments.")
                elif name in {"next", "n"}:
                    ply = min(board.get("total_plies", 0), board.get("ply", 0) + 1)
                elif name in {"prev", "previous", "p"}:
                    ply = max(0, board.get("ply", 0) - 1)
                else:
                    ply = 0 if name == "first" else board.get("total_plies", 0)
                result = _call(self.service.seek, self.session_id, ply,
                               view_revision=board.get("view_revision"), game_id=board.get("id"))
            elif name in {"practice", "play"}:
                mode = args[0].lower() if args else None
                if len(args) > 1 or (mode is not None and mode not in {"normal", "coach"}):
                    raise _CommandError("Use practice [coach|normal] from a replay position.")
                result = self._action("practice", mode=mode)
                self._append("status", "Practice branch started. The recorded match stays saved.")
            elif name in {"source", "recorded"}:
                result = self._action("replay_source")
                self._append("status", "Returned to the recorded match.")
            elif name in {"resume", "undo", "resign", "draw", "export"}:
                if args:
                    raise _CommandError(f"Use {name} without extra arguments.")
                result = self._action("claim_draw" if name == "draw" else name)
                if name == "export":
                    self._append("status", "PGN exported to " + str(result.get("path", "the saved exports directory")))
                elif name == "resign":
                    self._append("status", "You resigned this match. Use new to play again, or replay to review it.")
            elif name in {"ask", "chat"}:
                chat = getattr(self.service, "chat", None)
                if not callable(chat):
                    raise _CommandError("Use review for a move explanation, or hint for help with this position.")
                if not args:
                    raise _CommandError("Use ask followed by your chess question.")
                result = _call(chat, self.session_id, " ".join(args))
                if isinstance(result, str):
                    self._append("hermes", result)
                    result = {"ok": True}
            else:
                notation = args[0] if name == "move" and len(args) == 1 else raw
                board = self._board()
                if board.get("mode") == "replay":
                    result = _call(self.service.practice, self.session_id, game_id=board.get("id"),
                                   view_revision=board.get("view_revision"), move=notation)
                else:
                    result = _call(self.service.move, self.session_id, notation,
                                   board.get("revision"), board.get("id"))
            if isinstance(result, dict):
                self._accept_state(result)
            self.refresh()
            return result if isinstance(result, dict) else {"ok": True}
        except Exception as exc:
            message = _error_text(exc)
            with self._lock:
                self.last_error = message
            self._append("error", message)
            return {"ok": False, "message": message}
        finally:
            with self._lock:
                self.busy = ""

    def close(self):
        with self._lock:
            self.closed = True
        if self._coach:
            self._coach.close()


class _TerminalWorker:
    def __init__(self, controller, poll_interval):
        self.controller = controller
        self.poll_interval = max(0.05, float(poll_interval))
        self.commands = queue.Queue()
        self.stopped = threading.Event()
        self.thread = threading.Thread(target=self._run, name="gambit-terminal", daemon=True)

    def _run(self):
        try:
            self.controller.initialize()
        except Exception as exc:
            self._report_error(exc)
            self.controller._append("status", "The board could not start. Commands remain available: "
                                    "fix the engine and use new to retry, saved to open a match, ? for help, or q to quit.")
        while not self.stopped.is_set() and not self.controller.closed:
            try:
                command = self.commands.get(timeout=self.poll_interval)
            except queue.Empty:
                try:
                    self.controller.refresh()
                except Exception as exc:
                    self._report_error(exc)
                continue
            if command is None:
                break
            try:
                self.controller.execute(command)
            except Exception as exc:
                self._report_error(exc)

    def _report_error(self, exc):
        message = _error_text(exc)
        self.controller._append("error", message, message_id="worker:" + message)
        with self.controller._lock:
            self.controller.last_error = message
            self.controller.busy = ""

    def start(self):
        self.thread.start()

    def submit(self, command):
        self.commands.put(command)

    def close(self):
        self.stopped.set()
        self.commands.put(None)
        self.controller.close()


def _move_status(state, now=None):
    board = state.get("board") or {}
    if not board:
        if (state.get("session") or {}).get("initialized"):
            return "No active board - use new or saved"
        return "Opening the chess session"
    if board.get("mode") == "replay":
        return f"Replay - ply {board.get('ply', 0)} / {board.get('total_plies', 0)}"
    if board.get("result", "*") != "*":
        termination = str(board.get("termination") or "match complete").replace("_", " ")
        return f"{board['result']} - {termination}"
    pending = board.get("pending")
    if pending:
        deadline = pending.get("deadline")
        if isinstance(deadline, (int, float)):
            remaining = max(0, int(deadline - (time.time() if now is None else now) + 0.999))
            return f"Hermes reply pending - {remaining}s budget remaining"
        return "Hermes reply pending"
    turn = str(board.get("turn", "white")).title()
    check = " - CHECK" if board.get("check_square") else ""
    return f"Your turn - {turn}{check}"


class _Screen:
    def __init__(self, screen, curses, controller, worker, ascii_pieces):
        self.screen, self.curses = screen, curses
        self.controller, self.worker = controller, worker
        self.ascii_pieces = ascii_pieces
        self.text = ""
        self.cursor = 0
        self.scroll = 0
        self.history = []
        self.history_index = 0
        self.colours = False
        self._setup_colours()

    def _setup_colours(self):
        c = self.curses
        try:
            c.curs_set(1)
        except c.error:
            pass
        self.screen.keypad(True)
        self.screen.timeout(100)
        if not c.has_colors():
            return
        try:
            c.start_color()
            c.use_default_colors()
            c.init_pair(1, c.COLOR_CYAN, -1)
            c.init_pair(2, c.COLOR_GREEN, -1)
            c.init_pair(3, c.COLOR_YELLOW, -1)
            c.init_pair(4, c.COLOR_RED, -1)
            light, dark = (230, 65) if c.COLORS >= 256 else (c.COLOR_WHITE, c.COLOR_GREEN)
            selected = 143 if c.COLORS >= 256 else c.COLOR_YELLOW
            for number, foreground, background in [
                (10, c.COLOR_BLACK, light), (11, c.COLOR_BLACK, dark),
                (12, c.COLOR_BLACK, selected), (13, c.COLOR_WHITE, c.COLOR_RED),
            ]:
                c.init_pair(number, foreground, background)
            self.colours = True
        except c.error:
            self.colours = False

    def _attr(self, number, extra=0):
        return (self.curses.color_pair(number) if self.colours else 0) | extra

    def _put(self, y, x, text, attr=0, width=None):
        height, columns = self.screen.getmaxyx()
        if y < 0 or y >= height or x < 0 or x >= columns:
            return
        available = max(0, columns - x - (1 if y == height - 1 else 0))
        if width is not None:
            available = min(available, max(0, width))
        text = clip_columns(safe_text(text).replace("\n", " ").replace("\t", " "), available)
        try:
            if text:
                self.screen.addstr(y, x, text, attr)
        except (self.curses.error, UnicodeEncodeError):
            pass

    def _board(self, rect, state):
        c = self.curses
        board = state.get("board") or {}
        if rect.height < 1 or rect.width < 1:
            return
        self._put(rect.y, rect.x, "BOARD", self._attr(1, c.A_BOLD), rect.width)
        if not board:
            text = ("No active board. Use new to retry, or saved to open a recorded match."
                    if (state.get("session") or {}).get("initialized") else "Opening your saved board...")
            for index, line in enumerate(wrapped_lines(text, rect.width)):
                if index + 2 < rect.height:
                    self._put(rect.y + index + 2, rect.x, line, c.A_DIM, rect.width)
            return
        match = board.get("match") or {}
        if rect.height < (13 if match else 12) or rect.width < 28:
            for index, line in enumerate(board_lines(board, ascii_pieces=self.ascii_pieces)):
                if index + 1 < rect.height:
                    self._put(rect.y + index + 1, rect.x, line, 0, rect.width)
            return
        mode = "REPLAY" if board.get("mode") == "replay" else str(board.get("play_mode", "coach")).upper()
        self._put(rect.y + 1, rect.x, mode + "  /  YOU: " + str(board.get("human", "white")).upper(), c.A_DIM, rect.width)
        names = str(board.get("white", "White")) + "  vs  " + str(board.get("black", "Black"))
        self._put(rect.y + 2, rect.x, names, 0, rect.width)
        cell_width = 4 if rect.width >= 37 else 3
        cell_height = 2 if rect.height >= 26 else 1
        origin_x = rect.x + max(2, (rect.width - 8 * cell_width) // 2)
        if match:
            identity = str(match.get("platform") or "Recorded").upper() + "  " + str(match.get("source_id") or match.get("game_id") or "")
            self._put(rect.y + 3, rect.x, identity, self._attr(3), rect.width)
        origin_y = rect.y + (5 if match else 4)
        grid = board_grid(board)
        for col, square in enumerate(grid[0]):
            self._put(origin_y - 1, origin_x + col * cell_width + cell_width // 2,
                      square.name[0], c.A_DIM)
        for row_index, row in enumerate(grid):
            y = origin_y + row_index * cell_height
            self._put(y + cell_height // 2, origin_x - 2, row[0].name[1], c.A_DIM)
            for col, square in enumerate(row):
                x = origin_x + col * cell_width
                colour = 13 if square.check else 12 if square.last_move else 10 if square.light else 11
                attr = self._attr(colour)
                if not self.colours:
                    attr |= c.A_REVERSE if square.light else 0
                    attr |= c.A_BOLD if square.last_move else 0
                for inner in range(cell_height):
                    self._put(y + inner, x, " " * cell_width, attr, cell_width)
                piece = square.piece if self.ascii_pieces else PIECES.get(square.piece, "")
                if piece:
                    # Piece colour remains explicit in monochrome and ASCII;
                    # Unicode glyphs themselves distinguish White and Black.
                    self._put(y + cell_height // 2, x + cell_width // 2, piece,
                              attr | (c.A_BOLD if square.piece.isupper() else 0), 1)
        bottom = origin_y + 8 * cell_height
        for col, square in enumerate(grid[-1]):
            if bottom < rect.bottom:
                self._put(bottom, origin_x + col * cell_width + cell_width // 2,
                          square.name[0], c.A_DIM)
        row = bottom + 2
        if row < rect.bottom:
            label = f"Last move: {board.get('last_san') or '-'}"
            if board.get("mode") == "replay":
                label += f"    {board.get('ply', 0)}/{board.get('total_plies', 0)} plies"
            self._put(row, rect.x, label, self._attr(2), rect.width)
        history = [entry for entry in board.get("history", []) if entry.get("ply", 0) <= board.get("ply", 0)]
        moves = []
        for entry in history[-14:]:
            ply = entry.get("ply", 1)
            prefix = f"{(ply + 1) // 2}." if entry.get("colour") == "white" else ""
            moves.append(prefix + str(entry.get("san", "")))
        for index, line in enumerate(wrapped_lines(" ".join(moves), rect.width)):
            if row + 2 + index < rect.bottom:
                self._put(row + 2 + index, rect.x, line, c.A_DIM, rect.width)

    def _feed(self, rect, snapshot):
        if rect.height < 1 or rect.width < 1:
            return
        c = self.curses
        self._put(rect.y, rect.x, "HERMES", self._attr(1, c.A_BOLD), rect.width)
        self._put(rect.y + 1, rect.x, "PUBLIC COACHING & HINTS", c.A_DIM, rect.width)
        status = snapshot["busy"] or _move_status(snapshot["state"])
        status_lines = wrapped_lines(status, rect.width)
        row = rect.y + 3
        for line in status_lines[:2]:
            if row < rect.bottom:
                self._put(row, rect.x, line, self._attr(3), rect.width)
                row += 1
        row += 1
        available = max(0, rect.bottom - row)
        if not available:
            return
        rendered = []
        for message in snapshot["messages"]:
            role = message["role"].upper()
            colour = 4 if role == "ERROR" else 2 if role in {"HERMES", "HINT", "REVIEW"} else 1
            rendered.append((role, self._attr(colour, c.A_BOLD)))
            rendered.extend((line, 0) for line in wrapped_lines(message["text"], rect.width))
            rendered.append(("", 0))
        self.scroll = min(self.scroll, max(0, len(rendered) - available))
        end = max(0, len(rendered) - self.scroll)
        start = max(0, end - available)
        for offset, (line, attr) in enumerate(rendered[start:end]):
            self._put(row + offset, rect.x, line, attr, rect.width)

    def draw(self):
        c = self.curses
        height, width = self.screen.getmaxyx()
        layout = layout_for(width, height)
        snapshot = self.controller.snapshot()
        board = snapshot["state"].get("board") or {}
        self.screen.erase()
        self._put(0, 1 if width > 2 else 0, "GAMBIT", self._attr(2, c.A_BOLD))
        self._put(0, 10, "CHESS WITH HERMES", c.A_DIM)
        mode = "REPLAY" if board.get("mode") == "replay" else str(board.get("play_mode", "coach")).upper()
        self._put(0, max(31, width - len(mode) - 2), mode, self._attr(1, c.A_BOLD))
        if height > 1:
            self._put(1, 1 if width > 2 else 0, "=" * max(0, width - 2), c.A_DIM)
        if not layout.stacked:
            for y in range(layout.board.y, layout.board.bottom):
                self._put(y, layout.board.right, "|", c.A_DIM)
        self._board(layout.board, snapshot["state"])
        self._feed(layout.feed, snapshot)
        footer = layout.footer
        if footer.height:
            help_text = "e4 move | hint | review | mode coach/normal | replay | ? help | q quit"
            self._put(footer.y, footer.x, help_text, c.A_DIM, footer.width)
        cursor_y = footer.y + 1
        if footer.height >= 2:
            available = max(1, footer.width - 2)
            start = max(0, self.cursor - available + 1)
            while start < self.cursor and display_width(self.text[start:self.cursor]) >= available:
                start += 1
            self._put(cursor_y, footer.x, "> ", self._attr(2, c.A_BOLD), footer.width)
            self._put(cursor_y, footer.x + 2, self.text[start:start + available], 0, available)
        if footer.height >= 3:
            if snapshot["error"]:
                line, attr = snapshot["error"], self._attr(4)
            elif snapshot["busy"]:
                line, attr = snapshot["busy"], self._attr(3)
            elif layout.feed.height == 0 and snapshot["messages"]:
                latest = snapshot["messages"][-1]
                line, attr = latest["role"].title() + ": " + latest["text"].splitlines()[0], 0
            else:
                line, attr = _move_status(snapshot["state"]), self._attr(3)
            if self.scroll:
                line += f" | Scroll: {self.scroll} lines"
            self._put(footer.y + 2, footer.x, line, attr, footer.width)
        try:
            if footer.height >= 2 and width > 3:
                self.screen.move(cursor_y, min(width - 1, footer.x + 2 + display_width(self.text[start:self.cursor])))
            self.screen.refresh()
        except c.error:
            pass

    def _submit(self, command):
        command = command.strip()
        if command:
            self.worker.submit(command)
            self.history.append(command)
            self.history_index = len(self.history)
            self.scroll = 0
        self.text, self.cursor = "", 0

    def run(self):
        c = self.curses
        while not self.controller.closed:
            self.draw()
            try:
                key = self.screen.get_wch()
            except c.error:
                continue
            if key in ("\n", "\r", c.KEY_ENTER):
                if self.text.strip().lower() in {"q", "quit", "exit", "/q", "/quit"}:
                    return 0
                self._submit(self.text)
            elif key in ("\x03", "\x04"):
                return 0
            elif key == "\x15":
                self.text, self.cursor = "", 0
            elif key in (c.KEY_BACKSPACE, "\x7f", "\b"):
                if self.cursor:
                    self.text = self.text[:self.cursor - 1] + self.text[self.cursor:]
                    self.cursor -= 1
            elif key == c.KEY_DC:
                self.text = self.text[:self.cursor] + self.text[self.cursor + 1:]
            elif key in (c.KEY_LEFT, c.KEY_RIGHT):
                if not self.text and (self.controller.snapshot()["state"].get("board") or {}).get("mode") == "replay":
                    self.worker.submit("prev" if key == c.KEY_LEFT else "next")
                else:
                    self.cursor = max(0, min(len(self.text), self.cursor + (-1 if key == c.KEY_LEFT else 1)))
            elif key in (c.KEY_HOME, c.KEY_END):
                self.cursor = 0 if key == c.KEY_HOME else len(self.text)
            elif key in (c.KEY_UP, c.KEY_DOWN):
                delta = -1 if key == c.KEY_UP else 1
                self.history_index = max(0, min(len(self.history), self.history_index + delta))
                self.text = self.history[self.history_index] if self.history_index < len(self.history) else ""
                self.cursor = len(self.text)
            elif key in (c.KEY_PPAGE, c.KEY_NPAGE):
                self.scroll = max(0, self.scroll + (8 if key == c.KEY_PPAGE else -8))
            elif key == c.KEY_RESIZE:
                c.update_lines_cols()
            elif isinstance(key, str) and key.isprintable() and len(self.text) < 512:
                self.text = self.text[:self.cursor] + key + self.text[self.cursor:]
                self.cursor += 1
        return 0


def run_terminal(service, session_id: str, *, colour="white", strength="balanced", mode="coach",
                 poll_interval=0.25, ascii_pieces=False) -> int:
    """Open a reusable terminal dashboard, preserving a session's current game.

    No terminal state or game data is changed when standard input/output are
    redirected. The caller owns service lifetime and session selection.
    """
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Gambit's interactive dashboard needs a terminal. Use --help for command-line options.", file=sys.stderr)
        return 2
    try:
        import curses
    except ImportError:
        print("This Python installation does not provide curses terminal support.", file=sys.stderr)
        return 2
    controller = TerminalController(service, session_id, colour=colour, strength=strength, mode=mode)
    worker = _TerminalWorker(controller, poll_interval)

    def main(screen):
        ui = _Screen(screen, curses, controller, worker, ascii_pieces)
        worker.start()
        return ui.run()

    try:
        return curses.wrapper(main)
    except KeyboardInterrupt:
        return 0
    except curses.error as exc:
        print("The terminal could not be opened: " + safe_text(str(exc)), file=sys.stderr)
        return 2
    finally:
        worker.close()
