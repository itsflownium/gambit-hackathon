"""The installed command must be useful before it creates any saved state."""
import argparse
import io
import re
import sys

import pytest

from gambit import cli


class TerminalStream(io.StringIO):
    def __init__(self, *, tty=True):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty


def arguments(*values):
    parser = argparse.ArgumentParser(prog="hermes gambit")
    cli.setup_parser(parser)
    return parser.parse_args(values)


def streams(monkeypatch, *, input_tty=True, output_tty=True):
    incoming = TerminalStream(tty=input_tty)
    outgoing = TerminalStream(tty=output_tty)
    errors = TerminalStream()
    monkeypatch.setattr(sys, "stdin", incoming)
    monkeypatch.setattr(sys, "stdout", outgoing)
    monkeypatch.setattr(sys, "stderr", errors)
    return outgoing, errors


@pytest.mark.parametrize("values", [(), ("play",)])
def test_command_parser_has_a_play_default_and_explicit_play(values):
    args = arguments(*values)
    assert args.gambit_command == "play"
    assert (args.colour, args.strength, args.mode, args.ascii_pieces) == (
        "white", "balanced", "coach", False
    )


def test_command_parser_keeps_user_options_and_rejects_invalid_choices():
    saved = "terminal:" + "a" * 32
    args = arguments("play", "--session", saved, "--color", "black", "--strength", "learning",
                     "--mode", "normal", "--ascii")
    assert (args.session, args.colour, args.strength, args.mode, args.ascii_pieces) == (
        saved, "black", "learning", "normal", True
    )
    for option, value in [("--colour", "blue"), ("--strength", "unlimited"), ("--mode", "secret"),
                          ("--session", "chat-a"), ("--session", "terminal-alias")]:
        with pytest.raises(SystemExit) as failure:
            arguments(option, value)
        assert failure.value.code == 2


def test_help_works_without_a_terminal_or_service(monkeypatch):
    outgoing, errors = streams(monkeypatch, input_tty=False, output_tty=False)
    def unavailable():
        pytest.fail("Help must not load the engine, host model, or profile service")
    assert cli.command(arguments("help"), get_service=unavailable) == 0
    assert "--session" in outgoing.getvalue() and "--mode" in outgoing.getvalue()
    assert errors.getvalue() == ""


@pytest.mark.parametrize("input_tty,output_tty", [(False, True), (True, False), (False, False)])
def test_non_interactive_command_fails_before_loading_or_creating_state(monkeypatch, input_tty, output_tty):
    outgoing, errors = streams(monkeypatch, input_tty=input_tty, output_tty=output_tty)
    def unavailable():
        pytest.fail("A redirected command must not open a profile or create a session")
    assert cli.command(arguments(), get_service=unavailable) == 2
    assert "interactive terminal" in errors.getvalue().lower()
    assert "--help" in errors.getvalue()
    assert "Resume with:" not in outgoing.getvalue()


def test_launch_creates_a_resumable_profile_local_terminal_session(service, monkeypatch):
    outgoing, errors = streams(monkeypatch)
    launches = []
    def launch(current, sid, **options):
        launches.append((current, sid, options))
        saved = current.store.session(sid)
        assert saved["initialized"] and saved["surface"] == "terminal"
        return 0
    monkeypatch.setattr(cli, "_run_terminal", launch)
    args = arguments("--colour", "black", "--strength", "strong", "--mode", "normal", "--ascii")
    assert cli.command(args, get_service=lambda: service) == 0
    assert len(launches) == 1
    current, sid, options = launches[0]
    assert current is service and re.fullmatch(r"terminal:[0-9a-f]{32}", sid)
    assert options == {"colour": "black", "strength": "strong", "mode": "normal", "ascii_pieces": True}
    assert f"hermes gambit --session {sid}" in outgoing.getvalue()
    assert errors.getvalue() == ""
    assert service.stopped.is_set()


def test_resume_selects_the_exact_saved_terminal_session(service, monkeypatch):
    streams(monkeypatch)
    sid = "terminal:" + "a" * 32
    service.initialize(sid)
    service.store.mutate_session(sid, lambda s: s.update(surface="terminal"))
    selected = []
    monkeypatch.setattr(cli, "_run_terminal", lambda current, session_id, **kwargs: selected.append(session_id) or 0)
    assert cli.command(arguments("--session", sid), get_service=lambda: service) == 0
    assert selected == [sid]


@pytest.mark.parametrize("requested", ["terminal:" + letter * 32 for letter in ("b", "d", "e")])
def test_resume_never_invents_a_saved_session_or_takes_over_a_chat(service, monkeypatch, requested):
    outgoing, errors = streams(monkeypatch)
    terminal_sid = "terminal:" + "c" * 32
    service.initialize(terminal_sid)
    service.store.mutate_session(terminal_sid, lambda s: s.update(surface="terminal"))
    service.initialize("terminal:" + "d" * 32)  # An ordinary initialized record lacks the terminal marker.
    service.store.add_session_aliases(terminal_sid, ["terminal:" + "e" * 32])
    before = service.store.session(requested)
    monkeypatch.setattr(cli, "_run_terminal", lambda *args, **kwargs: pytest.fail("An invalid resume must not enter curses"))
    assert cli.command(arguments("--session", requested), get_service=lambda: service) == 2
    assert service.store.session(requested) == before
    assert errors.getvalue()
    assert "Resume with:" not in outgoing.getvalue()


def test_keyboard_interrupt_cleans_up_the_standalone_service(service, monkeypatch):
    streams(monkeypatch)
    def interrupted(*args, **kwargs):
        raise KeyboardInterrupt
    monkeypatch.setattr(cli, "_run_terminal", interrupted)
    assert cli.command(arguments(), get_service=lambda: service) == 130
    assert service.stopped.is_set()


def test_registration_uses_the_host_cli_hook_and_remains_lazy():
    registered = []
    class Context:
        def register_cli_command(self, **kwargs):
            registered.append(kwargs)
    def unavailable():
        pytest.fail("Registration must not initialize a profile")
    cli.register_cli(Context(), get_service=unavailable)
    assert len(registered) == 1 and registered[0]["name"] == "gambit"
    assert callable(registered[0]["handler_fn"])
    assert callable(registered[0]["setup_fn"])
