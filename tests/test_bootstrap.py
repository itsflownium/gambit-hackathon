import runpy
from pathlib import Path


def test_agent_and_dashboard_share_runtime_but_reload_changed_source(tmp_path):
    loader = tmp_path / 'bootstrap.py'
    loader.write_text((Path(__file__).parents[1] / 'bootstrap.py').read_text())
    package = tmp_path / 'gambit'
    package.mkdir()
    (package / '__init__.py').write_text('from .value import marker\nservices = {}\n')
    value = package / 'value.py'
    value.write_text("marker = 'old'\n")
    agent_runtime = runpy.run_path(str(loader))['runtime']
    dashboard_runtime = runpy.run_path(str(loader))['runtime']
    first = agent_runtime()
    first.services['ordinary-chat'] = 'active'
    assert dashboard_runtime() is first
    assert dashboard_runtime().services['ordinary-chat'] == 'active'

    # Change the source without relying on file size or one-second bytecode
    # timestamps. A newly loaded agent and an already loaded dashboard must
    # adopt the same new generation.
    value.write_text("marker = 'updated'\n")
    reloaded = runpy.run_path(str(loader))['runtime']()
    assert reloaded is not first
    assert reloaded.marker == 'updated'
    assert dashboard_runtime() is reloaded
    assert agent_runtime() is reloaded
