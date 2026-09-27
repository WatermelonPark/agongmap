# -*- coding: utf-8 -*-
"""/feed.xml(RSS 2.0) — 배치가 굽는 새 소식 피드(홈 마케팅 검수 D1·SEO-6, 2026-09-27).

지키는 것
  ① RSS 2.0 으로 읽힌다: 채널 필수 칸, 항목마다 title·link·guid·pubDate·description, guid 유일, 주소는 CNAME 도메인.
  ② 날짜는 데이터 시점에서만 나온다: '오늘'을 바꿔도 같은 바이트, 항목 날짜 = 같은 대상을 재는 다른 자리의 값
     (주간 = /weekly/ JSON-LD datePublished, 월간 = sitemap 의 /monthly/ lastmod, 시도 = 기준 분기 마지막 달 1일).
  ③ 주간 항목의 guid 에 발표일(weekly_release 정본)이 들어가 발표마다 새 항목이 된다.
  ④ 배치가 구웠다(디스크의 feed.xml = 생성기 출력). 홈 <head> 가 피드를 알리고, 서비스워커는 가로채지 않으며,
     sitemap 에는 넣지 않고 robots.txt 가 막지 않는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - make_feed.render 의 lastBuildDate 를 KST.today_iso() 로 → '오늘'을 바꿔도 같은가 시험이 빨강
  - monthly_item 의 date 를 mod_iso 로(공개일과의 max 를 빼면) → sitemap lastmod 와 다르다고 빨강 — 지금 데이터(기준 8월 →
    09-01)에선 같아 초록이라, 대신 date 를 MP.sort_key(raw) + '-15' 로 바꿔 빨강을 확인했다
  - weekly_item 의 guid 에서 발표일을 조사일(p)로 바꾸면 → ③ 빨강
  - render 에서 guid 줄을 지우면 → ① 빨강
  - 배치 커밋 잡·ci-tests 에서 make_feed 를 빼면 → 게이트에서 feed.xml 이 없거나 옛 판이라 ④ 빨강
  - sw.js 의 NO_SW 줄(fetch 처리기의 return)을 지우면 → 서비스워커 시험 빨강
  - index.html 의 alternate 링크를 지우면 → 빨강
픽스처: 저장소의 실제 data.js·data-core.js 와 생성기가 방금 구운 feed.xml·weekly/index.html·sitemap.xml. ③은 실제 주간
계열 끝에 다음 월요일 행을 하나 붙인 '다음 주 발표가 들어온 날' 모양이다(설명 문장은 고정값으로 바꿔 시군구 표를 새로 만들지 않는다).
"""
import datetime
import email.utils
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_feed as F  # noqa: E402
import weekly_release as WR  # noqa: E402
import make_monthly_page as MP  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import kst as KST  # noqa: E402
import home_src as HS  # noqa: E402  (홈 마크업 파일 위치의 정본)

FEED = os.path.join(ROOT, 'feed.xml')


def _read(*p):
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


@pytest.fixture(scope='module')
def items():
    return F.items()


def _feed():
    assert os.path.exists(FEED), 'feed.xml 이 없다 — python tools/make_feed.py (배치는 생성기 단계에서 굽는다)'
    return _read('feed.xml')


def test_feed_on_disk_is_what_the_generator_makes(items):
    assert _feed() == F.render(items), 'feed.xml 이 지금 데이터로 구운 판과 다르다 — python tools/make_feed.py'


def test_rss20_shape_and_unique_guids():
    root = ET.fromstring(_feed().encode('utf-8'))
    assert root.tag == 'rss' and root.get('version') == '2.0'
    ch = root.find('channel')
    host = _read('CNAME').strip()
    for tag in ('title', 'link', 'description', 'language', 'lastBuildDate'):
        assert (ch.findtext(tag) or '').strip(), '채널에 %s 가 없다' % tag
    assert ch.findtext('link') == 'https://%s/' % host
    its = ch.findall('item')
    assert len(its) == 3, '항목은 주간·시도·월간 셋이다: %d개' % len(its)
    guids = []
    for it in its:
        for tag in ('title', 'link', 'guid', 'pubDate', 'description'):
            assert (it.findtext(tag) or '').strip(), '항목에 %s 가 없다' % tag
        assert it.findtext('link').startswith('https://%s/' % host)
        assert it.find('guid').get('isPermaLink') == 'false'
        d = email.utils.parsedate_to_datetime(it.findtext('pubDate'))
        assert d.utcoffset() == datetime.timedelta(hours=9)
        guids.append(it.findtext('guid'))
    assert len(set(guids)) == len(guids), 'guid 가 겹친다: %s' % guids
    assert {g.split('-')[1] for g in guids} == set(F.KINDS)
    dates = [email.utils.parsedate_to_datetime(it.findtext('pubDate')) for it in its]
    assert dates == sorted(dates, reverse=True), '항목이 날짜 내림차순이 아니다'
    assert email.utils.parsedate_to_datetime(ch.findtext('lastBuildDate')) == dates[0]


def test_dates_do_not_depend_on_today(monkeypatch, items):
    """'오늘'을 먼 과거·먼 미래로 바꿔 두 번 구워도 바이트가 같다(실행한 날을 쓰면 빨개진다)."""
    outs = []
    for day in (datetime.date(2001, 1, 1), datetime.date(2039, 12, 31)):
        monkeypatch.setattr(KST, 'today', lambda now=None, d=day: d)
        monkeypatch.setattr(KST, 'today_iso', lambda now=None, d=day: d.isoformat())
        outs.append(F.render(F.items()))
    assert outs[0] == outs[1] == F.render(items)


def test_item_dates_equal_the_same_date_elsewhere(items):
    """항목 날짜는 같은 대상을 재는 다른 자리의 값과 같다 — 둘이 따로 재면 한쪽만 바뀌어도 아무것도 안 빨개진다."""
    by = {x['kind']: x for x in items}
    wk = re.search(r'"datePublished":\s*"(\d{4}-\d{2}-\d{2})"', _read('weekly', 'index.html'))
    assert wk and by['weekly']['date'] == wk.group(1), '주간 항목 날짜가 /weekly/ 발표일(datePublished)과 다르다'
    sm = re.search(r'<loc>[^<]*/monthly/</loc>\s*<lastmod>([^<]+)</lastmod>', _read('sitemap.xml'))
    assert sm and by['monthly']['date'] == sm.group(1), '월간 항목 날짜가 /monthly/ sitemap lastmod 와 다르다'
    L = re.search(r'"L":"(\d{4}Q[1-4])"', _read('data-core.js')).group(1)
    y, q = int(L[:4]), int(L[-1])
    assert by['zone']['date'] == '%d-%02d-01' % (y, q * 3)
    assert by['zone']['guid'] == 'agongmap-zone-' + L


def test_weekly_guid_carries_the_release_date(monkeypatch):
    W, Q = MW.load()
    p = W['rows'][-1]['p']
    assert F.weekly_item(W, Q)['guid'] == 'agongmap-weekly-' + WR.status(p)['pub']
    nxt = (datetime.date(*map(int, p.split('-'))) + datetime.timedelta(days=7)).isoformat()
    W2 = dict(W, rows=W['rows'] + [dict(W['rows'][-1], p=nxt)])
    monkeypatch.setattr(MW, 'build', lambda W, Q: (None, None, '설명', None))
    it = F.weekly_item(W2, Q)
    assert it['guid'] == 'agongmap-weekly-' + WR.status(nxt)['pub'] and it['date'] == WR.status(nxt)['pub']
    assert WR.week_label(nxt, year=True) in it['title']


def test_rfc822_does_not_depend_on_locale():
    assert F.rfc822('2026-09-24') == 'Thu, 24 Sep 2026 00:00:00 +0900'
    assert F.rfc822('2027-01-01') == 'Fri, 01 Jan 2027 00:00:00 +0900'


def test_home_announces_the_feed():
    host = _read('CNAME').strip()
    h = io.open(os.path.join(HS.ROOT, HS.HOME), encoding='utf-8').read()
    head = h[:h.lower().find('</head>')]
    links = re.findall(r'<link rel="alternate" type="application/rss\+xml"[^>]*>', head)
    assert len(links) == 1 and 'href="https://%s%s"' % (host, F.PATH) in links[0], links


def test_service_worker_leaves_the_feed_alone():
    sw = _read('sw.js')
    m = re.search(r'const NO_SW = new Set\(\[([^\]]*)\]\)', sw)
    assert m and "'%s'" % F.PATH in m.group(1), 'sw.js NO_SW 에 /feed.xml 이 없다'
    fetch = sw[sw.index("addEventListener('fetch'"):]
    ret = fetch.find('if (NO_SW.has(url.pathname)) return;')
    assert -1 < ret < fetch.find('e.respondWith('), '서비스워커가 /feed.xml 을 응답하기 전에 놓아주지 않는다'


def test_feed_is_not_in_the_sitemap_and_not_blocked():
    assert 'feed.xml' not in _read('sitemap.xml')
    rb = _read('robots.txt')
    assert not re.search(r'(?im)^Disallow:\s*/(feed\.xml)?\s*$', rb), 'robots.txt 가 피드를 막는다'
