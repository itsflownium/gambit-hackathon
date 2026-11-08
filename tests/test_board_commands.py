import json
import time

from gambit import tools


def board_command(service, monkeypatch, sid='ordinary-chat'):
    commands = {}

    class Context:
        def register_tool(self, **kwargs):
            pass

        def register_command(self, name, handler, **kwargs):
            commands[name] = handler

        def register_hook(self, *args, **kwargs):
            pass

        def register_skill(self, *args, **kwargs):
            pass

    monkeypatch.setattr(tools, 'session_candidates', lambda kwargs=None: [sid, 'ui-' + sid])
    tools.register_tools(Context(), lambda: service)

    def request(path, body=None, method=None):
        options = {'method': method or ('POST' if body else 'GET')}
        if body is not None:
            options['body'] = body
        return json.loads(commands['chess']('__board__ ' + json.dumps({'path': path, 'options': options})))

    return request, commands['chess']


def test_normal_chat_board_uses_bound_session_and_shared_action_validation(service, monkeypatch):
    request, _ = board_command(service, monkeypatch)
    initial = request('/state?session_id=some-other-chat')
    assert not initial['session']['initialized']
    assert initial['board'] is None
    started = request('/action', {'action': 'start', 'session_id': 'some-other-chat', 'mode': 'normal'})
    assert started['ok'] and started['board']['play_mode'] == 'normal'
    assert not service.store.session('some-other-chat')['initialized']
    assert request('/state')['board']['id'] == started['board']['id']
    assert service.state('ui-ordinary-chat')['board']['id'] == started['board']['id']
    moved = request('/action', {'action': 'move', 'move': 'e4', 'game_id': started['board']['id'],
                                'revision': started['board']['revision']})
    assert moved['ok']
    deadline = time.monotonic() + 2
    while time.monotonic() < deadline and request('/state')['board']['pending']:
        time.sleep(0.01)
    assert request('/state')['board']['ply'] == 2
    assert not request('/action', {'action': 'move', 'move': 'd4', 'revision': 0})['ok']


def test_board_command_rejects_invalid_or_unscoped_operations(service, monkeypatch):
    request, command = board_command(service, monkeypatch)
    assert not request('/../another-plugin', {'action': 'start'})['ok']
    assert not request('/action', {'action': 'start'}, method='GET')['ok']
    assert not request('/action', {'action': 'start', 'colour': 'ultraviolet'})['ok']
    for raw in ['{broken', '[]', '{"options": []}', 'x' * 16400]:
        assert not json.loads(command('__board__ ' + raw))['ok']
