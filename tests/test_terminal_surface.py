"""Canonical client identity wins; legacy TUI's explicit source remains usable."""
import sys
from types import SimpleNamespace

import pytest

from gambit import tools


class Context:
    def __init__(self, surface):
        self.surface = surface
        self.hooks = {}
        self.commands = {}

    def session_surface(self):
        return self.surface

    def register_hook(self, name, handler):
        self.hooks[name] = handler

    def register_command(self, name, handler, **kwargs):
        self.commands[name] = handler

    def register_tool(self, **kwargs):
        pass

    def register_skill(self, *args, **kwargs):
        pass


@pytest.mark.parametrize("surface,source,terminal", [
    ("cli", "desktop", True),
    ("tui", "desktop", True),
    ("desktop", "tui", False),
    ("local", "tui", False),
    ("", "tui", True),
    (None, "cli", True),
    ("", "desktop", False),
    ("", "local", False),
    ("", "", False),
])
def test_explicit_legacy_source_is_used_only_when_public_surface_is_blank(
        service, monkeypatch, surface, source, terminal):
    source_reads = []

    def get_session_env(name, default=""):
        source_reads.append(name)
        assert name == "HERMES_SESSION_SOURCE"
        return source

    monkeypatch.setitem(sys.modules, "gateway.session_context", SimpleNamespace(get_session_env=get_session_env))
    monkeypatch.setattr(tools, "session_candidates", lambda kwargs=None: ["chat-a"])
    context = Context(surface)
    tools.register_tools(context, lambda: service)
    policy = context.hooks["pre_llm_call"](platform="cli")["context"]

    assert ("This is a CLI/TUI chat." in policy) is terminal
    assert bool(source_reads) is (not bool(surface))


def test_legacy_tui_slash_returns_the_active_text_board(service, monkeypatch):
    monkeypatch.setitem(sys.modules, "gateway.session_context", SimpleNamespace(
        get_session_env=lambda name, default="": "tui" if name == "HERMES_SESSION_SOURCE" else default))
    monkeypatch.setattr(tools, "session_candidates", lambda kwargs=None: ["chat-a"])
    context = Context("")
    tools.register_tools(context, lambda: service)
    service.start("chat-a", mode="normal")

    result = context.commands["chess"]("")

    assert "GAMBIT" in result and "White to move" in result
    assert "knight button" not in result
