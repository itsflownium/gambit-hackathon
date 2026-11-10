"""One profile-scoped runtime, shared by Hermes entry points."""
from __future__ import annotations

import threading
from pathlib import Path

from .actions import Action, board_action
from .service import Service
from .storage import Store

_contexts = {}
_services = {}
_lock = threading.RLock()
_standalone = None


def configure_standalone(directory, engine_path=""):
    global _standalone
    from .engine import Engine
    store = Store(Path(directory))
    _standalone = Service(store, engine=Engine(store.directory, engine_path))
    return _standalone


def service():
    if _standalone is not None:
        return _standalone
    from hermes_constants import get_hermes_home
    from plugins.plugin_storage import plugin_data_dir
    home = str(get_hermes_home().resolve())
    with _lock:
        ctx = _contexts.get(home)
        current = _services.get(home)
        if current is None or current.stopped.is_set():
            if ctx is None:
                # A secondary profile's dashboard host can precede chat loading.
                # Keep settings and host-owned model routing in that profile.
                from .host import DashboardContext
                ctx = DashboardContext()
            current = Service(Store(plugin_data_dir("gambit")), ctx=ctx)
            _services[home] = current
        elif current.ctx is not ctx and home in _contexts:
            current.bind_context(ctx)
        return current


def register(ctx):
    from hermes_constants import get_hermes_home
    from .cli import register_cli
    from .tools import register_tools
    home = str(get_hermes_home().resolve())
    _contexts[home] = ctx
    register_tools(ctx, service)
    register_cli(ctx, service)
    def unload():
        with _lock:
            current = _services.pop(home, None)
            _contexts.pop(home, None)
        if current:
            current.stop()
    ctx.on_unload(unload)
