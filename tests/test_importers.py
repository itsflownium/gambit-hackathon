import json
import time

import httpx
import pytest

from conftest import PGN
from gambit.errors import ImportFailure
from gambit.importers import Importer, listing, _RESUME


def test_chesscom_username_import_reads_archive_and_hides_pgn_from_model_listing(store):
    paths=[]
    def response(request):
        paths.append(str(request.url))
        if request.url.path.endswith('/archives'):
            return httpx.Response(200,json={"archives":["https://api.chess.com/pub/player/alice/games/2026/11"]})
        return httpx.Response(200,json={"games":[{"url":"https://www.chess.com/game/live/1234","rules":"chess",
            "white":{"username":"Alice"},"black":{"username":"Bob"},"pgn":PGN,"end_time":1794010000}]})
    importer=Importer(store,httpx.MockTransport(response))
    result=importer.search('chess.com','Alice')
    assert result['games'][0]['source_id']=='1234'
    assert importer.selected('chess.com','1234')['pgn']==PGN
    assert 'pgn' not in listing(result)['games'][0]
    assert len(paths)==2
    assert importer.search('chess.com','Alice')['cached']
    assert len(paths)==2


def test_lichess_streamed_public_finished_games(store):
    def response(request):
        assert request.url.params['ongoing']=='false'
        assert request.url.params['finished']=='true'
        raw={"id":"abcdefgh","variant":"standard","status":"mate","lastMoveAt":1794010000000,
             "players":{"white":{"user":{"name":"Alice"}},"black":{"user":{"name":"Bob"}}},"pgn":PGN}
        return httpx.Response(200,content=json.dumps(raw)+'\n\n',headers={'Content-Type':'application/x-ndjson'})
    result=Importer(store,httpx.MockTransport(response)).search('lichess','Alice',limit=3)
    assert result['games'][0]['white']=='Alice'
    assert result['games'][0]['url']=='https://lichess.org/abcdefgh'


@pytest.mark.parametrize('recheck', ['refresh', 'expired_empty'])
def test_first_published_game_replaces_empty_search_without_hour_wait(store, recheck):
    published = False
    requests = []
    def response(request):
        requests.append(str(request.url))
        if request.url.path.endswith('/archives'):
            return httpx.Response(200, json={'archives': ['https://api.chess.com/pub/player/alice/games/2026/11']})
        game = {'url': 'https://www.chess.com/game/live/1234', 'rules': 'chess', 'pgn': PGN,
                'white': {'username': 'Alice'}, 'black': {'username': 'Bob'}, 'end_time': 1794010000}
        return httpx.Response(200, json={'games': [game] if published else []})
    importer = Importer(store, httpx.MockTransport(response))
    empty = importer.search('chess.com', 'Alice', limit=10)
    assert empty['games'] == []
    assert importer.search('chess.com', 'Alice', limit=10)['cached']
    assert len(requests) == 2
    published = True
    if recheck == 'expired_empty':
        key = 'chess.com:alice:10:None'
        empty['fetched_at'] = time.time() - 31
        store.cache('imports', key, empty)
    found = importer.search('chess.com', 'Alice', limit=10, refresh=recheck == 'refresh')
    assert [game['source_id'] for game in found['games']] == ['1234']
    assert not found['cached'] and len(requests) == 4


@pytest.mark.parametrize('saved_games', [False, True])
def test_refresh_failure_does_not_present_saved_empty_list_as_success(store, saved_games):
    cached = {'platform': 'lichess', 'username': 'Alice', 'games': [{'source_id': 'abcdefgh'}] if saved_games else [],
              'fetched_at': time.time()}
    store.cache('imports', 'lichess:alice:20:None', cached)
    importer = Importer(store, httpx.MockTransport(lambda request: httpx.Response(503)))
    if saved_games:
        result = importer.search('lichess', 'Alice', refresh=True)
        assert result['cached'] and result['games'] == cached['games'] and result['notice']
    else:
        with pytest.raises(ImportFailure, match='HTTP 503'):
            importer.search('lichess', 'Alice', refresh=True)


def test_source_errors_are_distinct_from_empty_game_list(store,monkeypatch):
    importer=Importer(store,httpx.MockTransport(lambda r:httpx.Response(404)))
    with pytest.raises(ImportFailure,match='not found'):
        importer.search('lichess','Alice')
    importer=Importer(store,httpx.MockTransport(lambda r:httpx.Response(429)))
    monkeypatch.setitem(_RESUME,'lichess',0)
    with pytest.raises(ImportFailure,match='rate-limiting'):
        importer.search('lichess','Alice')
    with pytest.raises(ImportFailure,match='asked us to wait'):
        importer.search('lichess','Alice')


@pytest.mark.parametrize('username',['https://lichess.org/@/Alice','../Alice','Alice?key=secret','Alice\nBob'])
def test_username_cannot_be_a_url_or_path(store,username):
    importer=Importer(store,httpx.MockTransport(lambda r:pytest.fail('No request should be sent')))
    with pytest.raises(ImportFailure):
        importer.search('lichess',username)
