import importlib.util
import sys
from pathlib import Path

from fastapi.testclient import TestClient
import httpx

from conftest import PGN


def test_native_board_api_roundtrip_and_stale_move(tmp_path):
    root=Path(__file__).resolve().parents[1]
    spec=importlib.util.spec_from_file_location('gambit_local_preview',root/'serve.py')
    module=importlib.util.module_from_spec(spec)
    sys.modules[spec.name]=module
    spec.loader.exec_module(module)
    app=module.app_for(tmp_path)
    runtime=module.runpy.run_path(str(root/'bootstrap.py'))['runtime']()
    from conftest import FakeEngine
    service=runtime.service();service.engine=FakeEngine()
    service.initialize('api-test')
    service.start('api-test',mode='normal')
    service.stopped.set()
    client=TestClient(app)
    board=client.get('/api/plugins/gambit/state',params={'session_id':'api-test'}).json()['board']
    body={'session_id':'api-test','action':'move','move':'e4','revision':board['revision']}
    moved=client.post('/api/plugins/gambit/action',json=body).json()
    assert moved['board']['pieces']['e4']=='P'
    stale=client.post('/api/plugins/gambit/action',json=body).json()
    assert stale['ok'] is False and stale['error']=='stale_position'
    assert client.post('/api/plugins/gambit/action',json=body,headers={'Origin':'https://unrelated.example'}).status_code==403
    assert client.post('/api/plugins/gambit/diagnostic',json={'event':'desktop_registered'}).json()['ok']


def test_import_button_refreshes_newly_published_first_game(tmp_path):
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location('gambit_first_game_preview', root / 'serve.py')
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    client = TestClient(module.app_for(tmp_path))
    service = module.runpy.run_path(str(root / 'bootstrap.py'))['runtime']().service()
    published = False
    def response(request):
        if request.url.path.endswith('/archives'):
            return httpx.Response(200, json={'archives': ['https://api.chess.com/pub/player/alice/games/2026/11']})
        game = {'url': 'https://www.chess.com/game/live/1234', 'rules': 'chess', 'pgn': PGN,
                'white': {'username': 'Alice'}, 'black': {'username': 'Bob'}, 'end_time': 1794010000}
        return httpx.Response(200, json={'games': [game] if published else []})
    service.importer.transport = httpx.MockTransport(response)
    body = {'session_id': 'first-game', 'action': 'find_games', 'platform': 'chess.com', 'username': 'Alice'}
    try:
        assert client.post('/api/plugins/gambit/action', json=body).json()['games'] == []
        published = True
        found = client.post('/api/plugins/gambit/action', json={**body, 'refresh': True}).json()
        assert found['ok'] and found['games'][0]['source_id'] == '1234' and not found['cached']
    finally:
        service.stop()
