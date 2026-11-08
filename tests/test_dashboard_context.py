import runpy
import sys
import time
from pathlib import Path
from types import SimpleNamespace

from conftest import FakeEngine


def test_dashboard_first_move_uses_profile_settings_and_model(tmp_path, monkeypatch):
    root = Path(__file__).resolve().parents[1]
    runtime = runpy.run_path(str(root / 'bootstrap.py'))['runtime']()
    monkeypatch.setattr(runtime, '_standalone', None)
    monkeypatch.setattr(runtime, '_contexts', {})
    monkeypatch.setattr(runtime, '_services', {})
    calls = []

    class Model:
        def __init__(self, plugin_id):
            assert plugin_id == 'gambit'
        async def acomplete_structured(self, **kwargs):
            calls.append(kwargs)
            move = kwargs['json_schema']['properties']['move']['enum'][0]
            return SimpleNamespace(parsed={'move': move, 'explanation': 'A legal developing move.'})

    monkeypatch.setitem(sys.modules, 'hermes_constants', SimpleNamespace(get_hermes_home=lambda: tmp_path))
    monkeypatch.setitem(sys.modules, 'plugins.plugin_storage', SimpleNamespace(plugin_data_dir=lambda name: tmp_path / name))
    monkeypatch.setitem(sys.modules, 'agent.plugin_llm', SimpleNamespace(PluginLlm=Model))
    settings = {'engine_path': '/configured/stockfish', 'analysis_seconds': 0.7, 'move_timeout_seconds': 12}
    monkeypatch.setitem(sys.modules, 'hermes_cli.config', SimpleNamespace(
        load_config_readonly=lambda: {'plugins': {'entries': {'gambit': {'settings': settings}}}}))
    service = runtime.service()
    try:
        assert service.engine.configured_path == '/configured/stockfish'
        assert service.engine.seconds == 0.7
        assert service.move_seconds == 12
        service.engine = FakeEngine()
        service.start('dashboard-first', mode='normal')
        game = service.state('dashboard-first')['board']
        service.move('dashboard-first', 'e4', game['revision'], game['id'])
        deadline = time.monotonic() + 2
        while time.monotonic() < deadline:
            reply = service.state('dashboard-first')['board']['last_reply']
            if reply:
                break
            time.sleep(0.01)
        assert calls and reply['origin'] == 'hermes'
        assert service.state('dashboard-first')['board']['total_plies'] == 2

        registered = SimpleNamespace(llm=Model('gambit'), get_config=lambda key, default=None: {
            'engine_path': '/updated/stockfish', 'analysis_seconds': 1.2,
            'move_timeout_seconds': 20}.get(key, default))
        runtime._contexts[str(tmp_path.resolve())] = registered
        assert runtime.service() is service
        assert service.ctx is registered
        assert service.engine.configured_path == '/updated/stockfish'
        assert service.move_seconds == 20
    finally:
        service.stop()
