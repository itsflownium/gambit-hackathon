"""Terminal-safe text views and command actions, using the shared chess service."""
from __future__ import annotations

import re

import chess

from .errors import GambitError


def clean(value):
    return re.sub(r"[\x00-\x1f\x7f-\x9f]", " ", str(value))[:500]


def board_text(state):
    board = state.get("board")
    if not board:
        return "No game selected. Use /chess play white coach, or run hermes gambit for the terminal dashboard."
    position = chess.Board(board["fen"])
    black = board.get("perspective", board["human"]) == "black"
    files = list(reversed(range(8))) if black else list(range(8))
    ranks = list(range(8)) if black else list(reversed(range(8)))
    lines = ["GAMBIT | " + clean(board.get("play_mode", "coach")).title()]
    match = board.get("match")
    if match:
        lines.append(clean(f"{match.get('platform')} @{match.get('username')} | {match.get('source_id')}"))
        lines.append(clean(f"{match.get('white')} vs {match.get('black')} | {match.get('result')}"))
    for rank in ranks:
        row = []
        for file in files:
            piece = position.piece_at(chess.square(file, rank))
            row.append(piece.symbol() if piece else ".")
        lines.append(f"{rank + 1}  " + " ".join(row))
    lines.append("   " + " ".join(chess.FILE_NAMES[file] for file in files))
    if board.get("mode") == "replay":
        lines.append(f"Recorded match: {board['ply']}/{board['total_plies']} half-moves")
    elif board.get("result") != "*":
        lines.append("Result: " + clean(board["result"]))
    elif board.get("pending"):
        lines.append("Hermes is calculating its reply.")
    else:
        lines.append(clean(board["turn"]).title() + " to move" + (" — your turn" if board["turn"] == board["human"] else ""))
    reply = board.get("last_reply")
    if reply:
        origin = reply.get("origin")
        label = "Recorded opponent" if origin == "recorded" else "Hermes" if origin == "hermes" else "Local engine (fallback)"
        lines.append(f"{label}: {clean(reply.get('san', reply.get('move', '')))}")
    return "\n".join(lines)


def settle(service, sid, state):
    board = state.get("board") or {}
    pending, reply = board.get("pending"), board.get("last_reply")
    token = pending.get("token") if pending else reply.get("token") if reply else None
    if token:
        return service.wait_for_reply(sid, board["id"], token, pending.get("deadline") if pending else None)
    return service.state(sid)


def tool_result(service, sid, result, *, wait=False):
    """Return an authoritative board plus this turn's exact feedback request to the active agent."""
    if "board" not in result:
        return result
    from .tools import compact
    state = settle(service, sid, result) if wait else service.state(sid)
    expected = result.get("board")
    if expected and (not state.get("board") or state["board"]["id"] != expected["id"]):
        raise GambitError("The selected game changed. Show the board again.")
    value = compact(state)
    value["terminal_board"] = board_text(state)
    value["surface"] = "terminal_chat"
    board = state.get("board")
    if wait and board and not board.get("pending") and board.get("play_mode") == "coach":
        reply = board.get("last_reply") or {}
        event = service.take_terminal_coaching(sid, board["id"], token=reply.get("token"),
                                               ply=board["ply"] if board["result"] != "*" else None)
        if event:
            value["coaching_prompt"] = event["prompt"]
    return value


def games_text(result):
    lines = [f"Matches for {clean(result.get('username', ''))} on {clean(result.get('platform', ''))}:"]
    for index, game in enumerate(result.get("games", []), 1):
        lines.append(clean(f"{game.get('number', index)}. {game.get('white')} vs {game.get('black')} | "
                          f"{game.get('ended_at_utc') or game.get('date') or 'Date unavailable'} | "
                          f"{game.get('colour')} | {game.get('result')} | {game.get('source_id')}"))
    if not result.get("games"):
        lines.append("No completed public standard games found. Retry after the source publishes the game.")
    else:
        lines.append("Choose an exact match with /chess open NUMBER.")
    return "\n".join(lines)


def hint_text(value):
    lines = [f"Hint {value['level']}/4: {clean(value.get('clue', ''))}"]
    for key in ("piece", "from", "to", "move", "line"):
        if key in value:
            item = value[key]
            lines.append(f"{key}: " + clean(" ".join(map(str, item)) if isinstance(item, list) else item))
    return "\n".join(lines)


def command(service, sid, parts):
    """Handle terminal-friendly slash actions; no terminal process runs in the gateway."""
    name, args = parts[0].lower(), parts[1:]
    if name in {"dashboard", "terminal"}:
        return "Run hermes gambit in a terminal for the side-by-side board and Hermes coaching. Use /chess here for this chat's own game."
    if name == "status":
        return board_text(service.state(sid))
    if name in {"chess.com", "lichess"} and len(args) == 1:
        return games_text(service.find_games(sid, name, args[0], refresh=True))
    if name == "hint":
        return hint_text(service.hint(sid, **({"level": int(args[0])} if args else {})))
    if name == "open" and len(args) == 1:
        return board_text(service.open_replay(sid, game_number=int(args[0])))
    state = service.state(sid)
    board = state.get("board")
    if name == "saved":
        saved = service.action(sid, "saved")
        return "Saved matches:\n" + "\n".join(clean(f"{g['id']} | {g['white']} vs {g['black']} | {g['result']}") for g in saved["games"])
    if name == "resume" and len(args) == 1:
        return board_text(service.action(sid, "resume", game_id=args[0]))
    if not board:
        raise GambitError("Start a game with /chess play white coach, or search /chess lichess USERNAME.")
    if name in {"next", "previous", "prev", "first", "last"}:
        target = {"next": board["ply"] + 1, "previous": board["ply"] - 1, "prev": board["ply"] - 1,
                  "first": 0, "last": board["total_plies"]}[name]
        return board_text(service.seek(sid, max(0, min(board["total_plies"], target)),
                                      game_id=board["id"], view_revision=board["view_revision"]))
    if name == "practice":
        return board_text(settle(service, sid, service.practice(sid, game_id=board["id"], view_revision=board["view_revision"])))
    if name == "source":
        return board_text(service.replay_source(sid, game_id=board["id"]))
    if name in {"undo", "resign", "export", "normal", "coach"}:
        action = "set_mode" if name in {"normal", "coach"} else name
        value = service.action(sid, action, game_id=board["id"], revision=board["revision"],
                               mode=name if action == "set_mode" else None)
        return value["pgn"] if name == "export" else board_text(value)
    move = args[0] if name == "move" and len(args) == 1 else parts[0] if len(parts) == 1 else None
    if move:
        value = (service.practice(sid, game_id=board["id"], view_revision=board["view_revision"], move=move)
                 if board["mode"] == "replay" else service.move(sid, move, board["revision"], board["id"]))
        return board_text(settle(service, sid, value))
    raise GambitError("Use /chess help for the available commands.")
