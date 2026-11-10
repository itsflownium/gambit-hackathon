"""Pure layout and board helpers for Gambit's dependency-free terminal UI."""
from __future__ import annotations

from dataclasses import dataclass
import re
import textwrap
import unicodedata


_ANSI = re.compile(r"\x1b(?:\[[0-?]*[ -/]*[@-~]|\][^\x07]*(?:\x07|\x1b\\))")
PIECES = dict(zip("KQRBNPkqrbnp", "♔♕♖♗♘♙♚♛♜♝♞♟"))


def safe_text(value) -> str:
    """Keep terminal control sequences out of imported names and public text."""
    text = _ANSI.sub("", str(value if value is not None else ""))
    return "".join(c for c in text if c in "\n\t" or not unicodedata.category(c).startswith("C"))


def display_width(value: str) -> int:
    return sum(0 if unicodedata.combining(c) else 2 if unicodedata.east_asian_width(c) in {"W", "F"} else 1
               for c in value)


def clip_columns(value: str, width: int) -> str:
    """Clip by screen cells so an imported wide name cannot overrun a panel."""
    result, used = [], 0
    for char in value:
        size = display_width(char)
        if used + size > width:
            break
        result.append(char)
        used += size
    return "".join(result)


def wrapped_lines(value, width: int) -> list[str]:
    width = max(1, width)
    lines = []
    for paragraph in safe_text(value).expandtabs(4).splitlines() or [""]:
        for line in textwrap.wrap(paragraph, width, break_long_words=True,
                                  break_on_hyphens=False) or [""]:
            while display_width(line) > width:
                part = clip_columns(line, width)
                if not part:
                    # A two-cell symbol cannot fit a one-cell viewport.
                    part, line = "?", line[1:]
                else:
                    line = line[len(part):]
                lines.append(part)
            lines.append(line)
    return lines


@dataclass(frozen=True)
class Rect:
    y: int
    x: int
    height: int
    width: int

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def right(self):
        return self.x + self.width


@dataclass(frozen=True)
class Layout:
    width: int
    height: int
    board: Rect
    feed: Rect
    footer: Rect
    stacked: bool
    compact: bool


def layout_for(width: int, height: int) -> Layout:
    """Return viewport-bounded rectangles, including for very small windows."""
    width, height = max(0, int(width)), max(0, int(height))
    margin = 1 if width > 2 else 0
    top = min(3, height)
    footer_height = min(3, max(0, height - top))
    body_height = max(0, height - top - footer_height)
    available = max(0, width - 2 * margin)
    footer = Rect(height - footer_height, margin, footer_height, available)
    side_by_side = width >= 76 and body_height >= 12
    if side_by_side:
        board_width = min(43, max(34, (available - 2) // 2))
        board = Rect(top, margin, body_height, board_width)
        feed_x = min(width, board.right + 2)
        feed = Rect(top, feed_x, body_height, max(0, width - margin - feed_x))
    elif body_height >= 24:
        board = Rect(top, margin, 14, available)
        feed = Rect(board.bottom + 1, margin, max(0, body_height - 15), available)
    else:
        board = Rect(top, margin, body_height, available)
        feed = Rect(top + body_height, margin, 0, available)
    return Layout(width, height, board, feed, footer, not side_by_side,
                  width < 34 or body_height < 12)


@dataclass(frozen=True)
class BoardSquare:
    name: str
    piece: str
    light: bool
    last_move: bool
    check: bool


def board_grid(board: dict | None) -> tuple[tuple[BoardSquare, ...], ...]:
    """Return visual rows top-to-bottom, rotated for a Black perspective."""
    board = board or {}
    black = board.get("perspective", board.get("human", "white")) == "black"
    files = "hgfedcba" if black else "abcdefgh"
    ranks = "12345678" if black else "87654321"
    pieces = board.get("pieces") or {}
    last = board.get("last_move") or ""
    changed = {last[:2], last[2:4]} if len(last) >= 4 else set()
    return tuple(tuple(BoardSquare(
        name=file + rank,
        piece=pieces.get(file + rank, ""),
        light=(ord(file) - ord("a") + int(rank) - 1) % 2 == 1,
        last_move=file + rank in changed,
        check=board.get("check_square") == file + rank,
    ) for file in files) for rank in ranks)


def board_lines(board: dict | None, *, ascii_pieces: bool = False) -> list[str]:
    """A plain board rendering useful for logs, accessibility, and tests."""
    grid = board_grid(board)
    files = "  " + " ".join(square.name[0] for square in grid[0])
    lines = [files]
    for row in grid:
        pieces = [square.piece if ascii_pieces else PIECES.get(square.piece, "") for square in row]
        lines.append(row[0].name[1] + " " + " ".join(piece or "." for piece in pieces))
    return lines + [files]
