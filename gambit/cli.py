"""The supported ``hermes gambit`` terminal entry point."""
from __future__ import annotations

import argparse
import re
import sqlite3
import sys
import uuid
from functools import partial

from .errors import GambitError

_SESSION_ID = re.compile(r"terminal:[0-9a-f]{32}\Z")


def _session_id(value):
    if not isinstance(value, str) or not _SESSION_ID.fullmatch(value):
        raise argparse.ArgumentTypeError("Use the terminal session ID shown by a previous Gambit launch.")
    return value


def setup_parser(parser):
    """Build only the plugin's argparse tree; loading help opens no services."""
    parser.description = "Play chess with Hermes in a terminal board and coaching dashboard."
    parser.epilog = (
        "Examples:\n"
        "  hermes gambit\n"
        "  hermes gambit play --colour black --mode normal\n"
        "  hermes gambit --session terminal:<saved-id>\n\n"
        "Enter moves such as e4 or e2e4. Press ? in the dashboard for controls.\n"
        "Each launch saves a separate terminal game in the active Hermes profile."
    )
    parser.add_argument("gambit_command", nargs="?", choices=("play", "help"), default="play",
                        help="launch the dashboard (default: play), or show help")
    parser.add_argument("--session", type=_session_id, metavar="ID",
                        help="resume a saved terminal session in this profile")
    parser.add_argument("--colour", "--color", choices=("white", "black"), default="white",
                        help="your colour for a new game (default: white)")
    parser.add_argument("--strength", choices=("learning", "balanced", "strong"), default="balanced",
                        help="opponent strength for a new game (default: balanced)")
    parser.add_argument("--mode", choices=("coach", "normal"), default="coach",
                        help="coaching mode for a new game (default: coach)")
    parser.add_argument("--ascii", dest="ascii_pieces", action="store_true",
                        help="use letters for pieces")
    parser.set_defaults(_gambit_parser=parser)


def _resolve_session(service, session_id=None):
    """Use plugin-owned terminal identities, never inferred Hermes chat identities."""
    if session_id is not None:
        try:
            _session_id(session_id)
        except argparse.ArgumentTypeError as exc:
            raise GambitError(str(exc)) from exc
        saved = service.store.session(session_id)
        if (saved.get("id") != session_id or not saved.get("initialized")
                or saved.get("surface") != "terminal"):
            raise GambitError("That saved terminal session was not found in this Hermes profile.")
        return session_id

    session_id = "terminal:" + uuid.uuid4().hex
    saved = service.store.session(session_id)
    if saved.get("id") != session_id or saved.get("initialized"):
        raise GambitError("Unable to create a new terminal session. Please try again.")
    service.store.initialize(session_id)
    service.store.mutate_session(session_id, lambda session: session.update(surface="terminal"))
    return session_id


def _run_terminal(service, session_id, **options):
    # Help and plugin registration remain available without loading curses.
    from .terminal import run_terminal
    return run_terminal(service, session_id, **options)


def command(args, get_service):
    """Launch a profile-local terminal session; return a Hermes CLI exit code."""
    if getattr(args, "gambit_command", "play") == "help":
        parser = getattr(args, "_gambit_parser", None)
        if parser is None:
            parser = argparse.ArgumentParser(prog="hermes gambit", formatter_class=argparse.RawDescriptionHelpFormatter)
            setup_parser(parser)
        parser.print_help()
        return 0
    if not sys.stdin.isatty() or not sys.stdout.isatty():
        print("Gambit needs an interactive terminal. Run `hermes gambit` in a terminal, "
              "or use `hermes gambit --help`.", file=sys.stderr)
        return 2

    current = None
    try:
        current = get_service()
        session_id = _resolve_session(current, getattr(args, "session", None))
        print(f"Resume with: hermes gambit --session {session_id}", flush=True)
        return _run_terminal(current, session_id,
                             colour=getattr(args, "colour", "white"),
                             strength=getattr(args, "strength", "balanced"),
                             mode=getattr(args, "mode", "coach"),
                             ascii_pieces=getattr(args, "ascii_pieces", False))
    except GambitError as exc:
        print(f"Gambit: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        return 130
    except (OSError, sqlite3.Error):
        print("Gambit could not open its terminal or saved game data. Check the terminal and profile, then retry.",
              file=sys.stderr)
        return 1
    finally:
        if current is not None:
            current.stop()


def register_cli(ctx, get_service):
    """Register through Hermes's public plugin CLI API."""
    ctx.register_cli_command(
        name="gambit",
        help="Play chess in a terminal board and coaching dashboard",
        description="Play chess with Hermes, or resume a saved terminal game.",
        setup_fn=setup_parser,
        handler_fn=partial(command, get_service=get_service),
    )
