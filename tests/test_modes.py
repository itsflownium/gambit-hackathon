import time
from types import SimpleNamespace

from conftest import FakeEngine, PGN
from gambit.service import Service
from gambit.storage import import_pgn


def test_normal_mode_plays_hermes_without_auto_coaching_and_keeps_hints(store):
    class LLM:
        async def acomplete_structured(self, **kwargs):
            move=kwargs['json_schema']['properties']['move']['enum'][0]
            return SimpleNamespace(parsed={'move':move,'explanation':'A legal developing move.'})
    class Ctx:
        llm=LLM()
        def get_config(self,key,default): return default
    service=Service(store,ctx=Ctx(),engine=FakeEngine())
    service.initialize('chat-a')
    game=service.start('chat-a',mode='normal')
    service.move('chat-a','e4',game['board']['revision'])
    for _ in range(100):
        current=service.state('chat-a')['board']
        if current['last_reply']:break
        time.sleep(.01)
    assert current['play_mode']=='normal'
    assert current['last_reply']['origin']=='hermes'
    assert current['ply']==2
    assert service.store.session('chat-a').get('coaching_queue',[])==[]
    # Requested hints are allowed in Normal mode; use an actual bounded engine-shaped result.
    service.engine.position=lambda board,**kwargs:{'lines':[{'uci':'g1f3','line_san':['Nf3']}]}
    hint=service.hint('chat-a',1)
    assert hint['level']==1 and 'move' not in hint
    changed=service.action('chat-a','set_mode',mode='coach')
    assert changed['board']['play_mode']=='coach'
    service.stop()


def test_playing_black_starts_with_hermes_and_does_not_review_a_phantom_human_move(service):
    service.start('chat-a',colour='black',mode='coach')
    for _ in range(100):
        state=service.state('chat-a')
        if state['board']['last_reply'] and state['session'].get('coaching_queue'):break
        time.sleep(.01)
    assert state['board']['human']=='black'
    assert state['board']['turn']=='black'
    assert state['board']['ply']==1
    prompt=state['session']['coaching_queue'][0]['prompt']
    assert 'Black' in prompt
    assert 'review' not in prompt.lower()


def test_progressive_hints_withhold_later_details_and_reset_at_a_new_position(service):
    calls=[]
    def calculate(board,**kwargs):
        calls.append(board.fen())
        return {'lines':[{'uci':'g1f3','line_san':['Nf3']}]}
    service.engine.position=calculate
    game=service.store.create(record=import_pgn(PGN,source='fixture',source_id='hints',username='Alice'))
    service.open_replay('chat-a',game_id=game['id'])
    first=service.hint('chat-a')
    assert first['level']==1 and not {'piece','from','to','move','line'} & first.keys()
    second=service.hint('chat-a')
    assert second['level']==2 and second['piece']=='knight' and second['from']=='g1'
    assert 'to' not in second and 'move' not in second
    third=service.hint('chat-a')
    assert third['level']==3 and third['to']=='f3' and 'move' not in third
    fourth=service.hint('chat-a')
    assert fourth['level']==4 and fourth['move']=='Nf3' and fourth['line']==['Nf3']
    assert len(calls)==1
    service.seek('chat-a',2)
    assert service.hint('chat-a')['level']==1
    assert len(calls)==2
