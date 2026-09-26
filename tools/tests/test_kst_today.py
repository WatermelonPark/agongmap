# -*- coding: utf-8 -*-
"""날짜를 찍는 생성기는 모두 한국 시각(KST)의 오늘을 한 곳(tools/kst.py)에서 읽는다(2026-09-26 데이터 감사).

러너는 TZ=UTC 다. make_sido_pages 가 `datetime.date.today()` 로 /zone/·허브 JSON-LD, 지역 sitemap lastmod,
홈·/weekly/ 도장(.home_stamp)을 찍고 refresh_cycle_data 는 utcnow()+9h 로 /cycle/ 을 찍어서, 15:00~24:00 UTC
(00~09시 KST)에 돈 배치 한 커밋 안에서 날짜가 하루 갈렸다. 목요일 1차 예약(22:00 UTC)이 그 창에 있고,
2026-08-13T22:44Z 봇 커밋이 실제로 UTC 날짜를 찍었다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - kst.py 의 `hours=9` 를 0 으로 바꾸면 → 경계 시각 단정이 빨강
  - make_sido_pages._today() 를 `datetime.date.today().isoformat()` 로 되돌리면 → 출처 단정이 빨강
  - head() 의 JSON-LD 날짜를 _today() 대신 date.today() 로 찍으면 → head 단정·원문 단정이 빨강
  - refresh_cycle_data._today_kst() 를 utcnow()+9h 로 되돌리면 → 출처 단정·원문 단정이 빨강
픽스처: 감사가 재현한 두 순간(2026-10-01 16:30 UTC = 10-02 01:30 KST, 14:59 UTC = 23:59 KST)과, 진짜 오늘과
절대 겹치지 않는 가짜 오늘(1999-12-31). 생성기 목록은 update-cloud.yml 커밋 잡이 pip 설치 전에 부르는
도구에서 뽑는다(손 목록 아님).
"""
import ast
import datetime
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import kst as K  # noqa: E402
import make_sido_pages as P  # noqa: E402
import refresh_cycle_data as RF  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
UTC = datetime.timezone.utc
FAKE = datetime.date(1999, 12, 31)


def test_kst_day_turns_at_15_utc():
    assert K.today(datetime.datetime(2026, 10, 1, 16, 30, tzinfo=UTC)) == datetime.date(2026, 10, 2)
    assert K.today(datetime.datetime(2026, 10, 1, 14, 59, tzinfo=UTC)) == datetime.date(2026, 10, 1)
    assert K.today_iso(datetime.datetime(2026, 10, 1, 15, 0, tzinfo=UTC)) == '2026-10-02'


def test_generators_read_today_from_the_kst_helper(monkeypatch):
    monkeypatch.setattr(K, 'today', lambda now=None: FAKE)
    assert P._today() == FAKE.isoformat(), 'make_sido_pages 가 kst 가 아닌 곳에서 오늘을 읽는다'
    assert RF._today_kst() == FAKE.isoformat(), 'refresh_cycle_data 가 kst 가 아닌 곳에서 오늘을 읽는다'
    h = P.head('서울', 'd', 't')
    assert '"datePublished": "%s"' % FAKE.isoformat() in h and '"dateModified": "%s"' % FAKE.isoformat() in h, (
        '지역 페이지 JSON-LD 날짜가 _today() 를 따르지 않는다 — keep_dates 의 datePublished 치환도 어긋난다')


def _pre_pip_generators():
    """update-cloud.yml 커밋 잡에서 pip 설치 **전에** 부르는 도구 = 배치 생성기."""
    y = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    job = y[y.index('\n  commit:'):]
    job = job[:job.index('pip install')]
    return sorted(set(re.findall(r'python3? tools/(\w+)\.py', job)))


def _runner_clock_calls(path):
    """date.today()·datetime.now()·utcnow() 호출 자리(주석·문자열은 보지 않는다)."""
    tree = ast.parse(io.open(path, encoding='utf-8').read(), path)
    out = []
    for n in ast.walk(tree):
        if not (isinstance(n, ast.Call) and isinstance(n.func, ast.Attribute)):
            continue
        v, a = n.func.value, n.func.attr
        owner = v.attr if isinstance(v, ast.Attribute) else getattr(v, 'id', '')
        if a == 'utcnow' or (a == 'today' and owner == 'date') or (a == 'now' and owner == 'datetime'):
            out.append('%s.%s() %d행' % (owner, a, n.lineno))
    return out


def test_no_generator_stamps_the_runner_date():
    gens = _pre_pip_generators()
    assert {'make_sido_pages', 'refresh_cycle_data'} <= set(gens), gens
    bad = []
    for g in gens:
        bad += ['%s: %s' % (g, c) for c in _runner_clock_calls(os.path.join(ROOT, 'tools', g + '.py'))]
    assert not bad, '러너(UTC) 날짜로 오늘을 찍는 생성기 — kst.today() 를 쓸 것: %s' % bad
