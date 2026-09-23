# -*- coding: utf-8 -*-
"""naver_serp 호출 간격·재시도·실패 표시(백로그 26).

기본 실행은 검색 API를 24회(키워드 8 × 코퍼스 3) 쉬지 않고 던졌다. 한도에 걸려 429가 나면
probe()가 그 코퍼스를 빈 목록으로 채워 "경쟁 글 없음"·"상위 10에는 없음"과 구별되지 않았고,
--record면 빈 상위 목록이 다음 회차의 비교 기준으로 남았다.

픽스처가 재현하는 실제 상태: urlopen을 가짜로 바꿔 NAVER API HUB 게이트웨이의 응답을 흉내 낸다 —
한도 초과(HTTP 429, 본문 JSON), 인증 실패(401), 소켓 타임아웃, 정상 응답(items 목록). 시계와 잠도
가짜라 실제로 기다리지 않고 네트워크에도 나가지 않는다. 이력 파일은 tmp_path로 돌린다.
"""
import io
import json
import os
import socket
import sys
import urllib.error

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import naver_serp as NS  # noqa: E402

ITEMS = {'items': [{'title': '<b>대구</b> 미분양 전망', 'link': 'https://blog.naver.com/other/1',
                    'bloggername': '다른 블로그', 'postdate': '20260920'}]}


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _http(code):
    body = json.dumps({'error': {'errorCode': str(code), 'message': 'rate limit' if code == 429 else 'x'}})
    return urllib.error.HTTPError(NS.API % 'blog', code, 'err', {}, io.BytesIO(body.encode()))


class _Clock:
    def __init__(self):
        self.t = 0.0
        self.sleeps = []

    def now(self):
        return self.t

    def sleep(self, d):
        self.sleeps.append(d)
        self.t += d


class _Api:
    """코퍼스별 응답 대본. script[kind]는 순서대로 소비하고, 마지막 항목은 계속 되풀이한다.
    항목이 int면 그 HTTP 코드, 예외 인스턴스면 그 예외, 'ok'면 정상 응답."""

    def __init__(self, script):
        self.script = {k: list(v) for k, v in script.items()}
        self.calls = {}

    def urlopen(self, req, timeout=None):
        kind = req.full_url.split('/search/v1/')[1].split('?')[0]
        self.calls[kind] = self.calls.get(kind, 0) + 1
        seq = self.script.get(kind, ['ok'])
        step = seq.pop(0) if len(seq) > 1 else seq[0]
        if step == 'ok':
            return _Resp(json.dumps(ITEMS).encode())
        if isinstance(step, int):
            raise _http(step)
        raise step


@pytest.fixture
def api(monkeypatch, tmp_path):
    monkeypatch.setenv('NAVER_CLIENT_ID', 'test-id')
    monkeypatch.setenv('NAVER_CLIENT_SECRET', 'test-secret')
    clock = _Clock()
    monkeypatch.setattr(NS, '_sleep', clock.sleep)
    monkeypatch.setattr(NS, '_now', clock.now)
    monkeypatch.setattr(NS, '_last_call', [None])
    monkeypatch.setattr(NS, 'HIST', str(tmp_path / 'serp-history.jsonl'))

    def make(script):
        a = _Api(script)
        a.clock = clock
        monkeypatch.setattr(NS.urllib.request, 'urlopen', a.urlopen)
        return a
    return make


def test_429_then_success_is_retried_with_backoff(api):
    """한도 초과 한 번은 잠깐 쉬었다 다시 부르면 넘어간다 — 결과를 그대로 돌려줘야 한다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): RETRY_CODES에서 429를 빼면 RuntimeError('HTTP 429')가
    그대로 올라와 빨개진다. 재시도 대기(_sleep(BACKOFF[attempt]))를 지우면 대기 단정이 빨개진다.
    """
    a = api({'blog': [429, 'ok']})
    d = NS._get('blog', '대구 미분양')
    assert d == ITEMS
    assert a.calls == {'blog': 2}
    assert NS.BACKOFF[0] in a.clock.sleeps, a.clock.sleeps


def test_429_forever_is_reported_as_failure_not_as_no_competitors(api, capsys):
    """재시도까지 429면 그 코퍼스는 **실패**다 — 빈 목록([])이면 "경쟁 글 없음"과 구별되지 않는다.
    화면에는 '없음' 대신 '판단 불가'가 나오고, 종료 코드는 1, --record는 빈 상위 목록을 남기지 않는다.
    재시도는 유한해야 한다(한 호출이 끝없이 매달리면 안 된다).

    무엇을 깨뜨리면 빨개지나(실제로 확인):
      - probe()의 실패 분기를 예전처럼 `out['hits'][label] = rows`([])로 되돌리면 → None 단정.
      - main()의 '--record and 블로그 실패면 기록 안 함' 분기를 지우면 → 이력 파일 단정.
      - main()이 실패가 있어도 0을 돌려주면 → 종료 코드 단정.
    """
    a = api({'blog': [429]})
    out = NS.probe('대구 미분양')
    assert out['hits']['블로그'] is None
    assert out['failed'] == ['블로그']
    assert out['hits']['웹문서'] and out['hits']['카페'], '다른 코퍼스는 정상이어야 한다'
    assert a.calls['blog'] == 1 + len(NS.BACKOFF)
    assert len(NS.BACKOFF) <= 4 and sum(NS.BACKOFF) <= 15, '재시도가 유한하고 짧아야 한다'

    capsys.readouterr()
    rc = NS.main(['대구 미분양', '--record'])
    txt = capsys.readouterr().out
    assert rc == 1
    assert '상위 10에는 없음' not in txt
    assert '블로그 -- 조회 실패' in txt and '판단 불가' in txt
    assert not os.path.exists(NS.HIST), '실패한 회차의 빈 상위 목록이 비교 기준으로 기록됐다'


def test_success_run_still_records_and_exits_zero(api, capsys):
    """위 시험의 대조군 — 정상이면 기록하고 0으로 끝난다(이력 파일 경로 치환이 실제로 먹는지 확인).

    무엇을 깨뜨리면 빨개지나(실제로 확인): 기록 분기를 `elif False:`로 막으면 빨개진다.
    """
    api({})
    rc = NS.main(['대구 미분양', '--record'])
    assert rc == 0
    rec = [json.loads(line) for line in open(NS.HIST, encoding='utf-8')]
    assert rec and rec[0]['top'] == ['대구 미분양 전망']


def test_auth_error_is_not_retried(api):
    """401은 다시 불러도 같다 — 바로 올려 사람이 키를 확인하게 한다(쿼터·시간 낭비 없음).

    무엇을 깨뜨리면 빨개지나(실제로 확인): _retryable()이 HTTPError면 무조건 True를 돌려주게 하면
    호출이 4회가 되어 빨개진다.
    """
    a = api({'blog': [401]})
    with pytest.raises(RuntimeError, match='HTTP 401'):
        NS._get('blog', '대구 미분양')
    assert a.calls == {'blog': 1}


def test_timeouts_are_retried(api):
    """소켓 타임아웃(URLError로 싸여 오는 것과 맨 TimeoutError 둘 다)도 한 번의 흔들림으로 본다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): _retryable()의 isinstance 목록에서 URLError를 빼면 빨개진다.
    """
    a = api({'blog': [urllib.error.URLError(socket.timeout('timed out')), TimeoutError('timed out'), 'ok']})
    assert NS._get('blog', '대구 미분양') == ITEMS
    assert a.calls == {'blog': 3}


def test_calls_are_spaced(api):
    """연달아 부르면 호출 사이를 MIN_INTERVAL 이상 띄운다 — 24회를 한꺼번에 던지지 않는다.
    가짜 시계는 스스로 흐르지 않으므로 두 번째 호출부터 MIN_INTERVAL만큼 잠들어야 한다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): _get()에서 _space() 호출을 지우면 빨개진다.
    """
    a = api({})
    for _ in range(3):
        NS._get('blog', '대구 미분양')
    assert a.calls == {'blog': 3}
    assert a.clock.sleeps == [NS.MIN_INTERVAL, NS.MIN_INTERVAL], a.clock.sleeps
    assert NS.MIN_INTERVAL >= 0.1
