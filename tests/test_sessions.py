import time

import pytest

from conftest import PGN
from gambit.errors import StalePosition
from gambit.storage import import_pgn


def test_gateway_desktop_and_stored_ids_resolve_to_same_chat(service):
    service.store.add_session_aliases('chat-a',['local-ui-a','ses-durable-a','agent:main:local:dm:local-ui-a'])
    state=service.start('local-ui-a')
    assert service.state('ses-durable-a')['board']['id']==state['board']['id']
    service.notify_chat('agent:main:local:dm:local-ui-a','Review this move',game_id=state['board']['id'],token='event-a')
    assert service.state('local-ui-a')['session']['coaching_queue'][0]['id']=='event-a'
    service.acknowledge_coaching('ses-durable-a','event-a')
    assert service.state('chat-a')['session']['coaching_queue']==[]


def test_aliases_cannot_merge_two_initialized_conversations(service):
    service.initialize('chat-b')
    service.store.add_session_aliases('chat-a',['ui-a'])
    with pytest.raises(StalePosition):
        service.store.add_session_aliases('chat-b',['ui-a'])


def test_late_reply_from_old_match_cannot_coach_new_match(service):
    a=service.start('chat-a')
    b=service.start('chat-a')
    service.notify_chat('chat-a','old feedback',game_id=a['board']['id'])
    assert service.state('chat-a')['board']['id']==b['board']['id']
    assert service.store.session('chat-a').get('coaching_queue',[])==[]


def test_switching_to_normal_removes_pending_automatic_feedback(service):
    a=service.start('chat-a')
    service.notify_chat('chat-a','automatic',game_id=a['board']['id'])
    service.notify_chat('chat-a','explicitly requested summary',game_id=a['board']['id'],kind='summary')
    service.action('chat-a','set_mode',mode='normal')
    assert [e['kind'] for e in service.store.session('chat-a')['coaching_queue']]==['summary']


def test_same_imported_match_can_be_reviewed_from_either_username(service):
    source={'pgn':PGN,'username':'Alice','url':'https://lichess.org/abcdefgh','source_id':'abcdefgh'}
    service.importer.selected=lambda platform,source_id,**kwargs:source
    first=service.open_replay('chat-a',platform='lichess',source_id='abcdefgh',username='Alice',ply=2)
    second=service.open_replay('chat-a',platform='lichess',source_id='abcdefgh',username='Bob',ply=2)
    assert first['board']['id']==second['board']['id']
    assert first['board']['human']=='white'
    assert second['board']['human']=='black'
    assert service.review('chat-a')['perspective']=='black'
