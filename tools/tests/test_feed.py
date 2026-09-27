# -*- coding: utf-8 -*-
"""/feed.xml(RSS 2.0) — 배치가 굽는 새 소식 피드(홈 마케팅 검수 D1·SEO-6, 2026-09-27).

지키는 것
  ① RSS 2.0 으로 읽힌다: 채널 필수 칸, 항목마다 title·link·guid·pubDate·description, guid 유일, 주소는 CNAME 도메인.
  ② pubDate 는 '그 판이 사이트에 처음 실린 날' 한 뜻이다(D1 검토 B1): 주간 = /weekly/ JSON-LD datePublished(발표일),
     시도·월간 = 새 판이 처음 구워진 회차의 그 페이지 JSON-LD dateModified(keep_dates) → 그 뒤로는 이전 feed.xml 에서
     물려받는다. 판이 생길 수 없는 과거(기준 분기·기준월의 1일)를 적지 않는다. 생성기는 오늘 날짜를 읽지 않는다 —
     datetime·time·kst 를 모두 먼 날로 바꿔도 같은 바이트.
  ③ 주간 항목의 guid 에 발표일(weekly_release 정본)이 들어가 발표마다 새 항목이 된다. 제목·설명은 /weekly/ 의
     og:title·meta description 그대로라 말투가 섞이지 않는다.
  ④ 배치가 구웠다(디스크의 feed.xml = 생성기 출력). 홈 <head> 가 피드를 알리고, 서비스워커는 가로채지 않으며,
     sitemap 에는 넣지 않고 robots.txt 가 막지 않는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - make_feed.render 의 lastBuildDate 를 KST.today_iso() 로, 또는 datetime.date.today() 로 → '오늘' 시험이 빨강
  - zone_item 의 날짜를 옛 규칙(MP.sort_key(L) + '-01')으로 되돌리면 → 페이지 날짜 일치 시험이 빨강
  - published() 가 이전 피드를 보지 않으면(prev.get 을 지우면) → 물려받기 시험이 빨강
  - make_monthly_page 가 dateModified 를 다시 기준월 1일로 적으면 → 월간 페이지 날짜 시험이 빨강
  - weekly_item 제목을 결론 문장(합쇼체)으로 되돌리면 → 제목·설명 정본 시험이 빨강
  - weekly_item 의 guid 에서 발표일을 조사일(p)로 바꾸면 → ③ 빨강
  - render 에서 guid 줄을 지우면 → ① 빨강
  - 배치 커밋 잡·ci-tests 에서 make_feed 를 빼면 → 게이트에서 feed.xml 이 없거나 옛 판이라 ④ 빨강
  - sw.js 의 NO_SW 줄(fetch 처리기의 return)을 지우면 → 서비스워커 시험 빨강
  - index.html 의 alternate 링크를 지우면 → 빨강
픽스처: 저장소의 실제 data.js·data-core.js 와 생성기가 방금 구운 feed.xml·weekly/·zone/·monthly/ 페이지·sitemap.xml.
'처음 구운 날'은 이전 피드가 없는 경로(tmp)로, '물려받기'는 같은 guid 에 다른 날짜를 적은 이전 피드(tmp)로 재현한다.
월간 페이지 날짜 시험은 /monthly/ 를 tmp 에 세 번 굽는다(처음·그대로·내용 바뀜, 날마다 다른 '오늘'). ③은 실제 주간
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
import make_sido_pages as SP  # noqa: E402
import time  # noqa: E402
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


def _fake_clock(monkeypatch, day):
    """datetime.date·datetime.datetime·time.time·kst 를 모두 그 날 정오로 돌린다(검토자 feedcheck 방식)."""
    real_dt, real_d = datetime.datetime, datetime.date
    off = real_dt(day.year, day.month, day.day, 12) - real_dt.now()

    class FD(datetime.date):
        @classmethod
        def today(cls):
            return real_d(day.year, day.month, day.day)

    class FDT(real_dt):
        @classmethod
        def now(cls, tz=None):
            return real_dt.now(tz) + off

        @classmethod
        def utcnow(cls):
            return real_dt.utcnow() + off

        @classmethod
        def today(cls):
            return real_dt.now() + off

    rt = time.time
    monkeypatch.setattr(datetime, 'date', FD)
    monkeypatch.setattr(datetime, 'datetime', FDT)
    monkeypatch.setattr(time, 'time', lambda: rt() + off.total_seconds())
    monkeypatch.setattr(KST, 'today', lambda now=None: day)
    monkeypatch.setattr(KST, 'today_iso', lambda now=None: day.isoformat())


def test_dates_do_not_depend_on_today(monkeypatch, items):
    """'오늘'을 먼 과거·먼 미래로 바꿔 두 번 구워도 바이트가 같다(실행한 날을 쓰면 — kst 든 datetime 이든 — 빨개진다)."""
    outs = []
    for day in (datetime.date(2001, 1, 1), datetime.date(2039, 12, 31)):
        with monkeypatch.context() as m:
            _fake_clock(m, day)
            assert datetime.date.today().year == day.year and KST.today() == day   # 가짜 시계가 먹었는지
            outs.append(F.render(F.items()))
    assert outs[0] == outs[1] == F.render(items)


def _fresh(tmp_path):
    """이전 피드가 없는 첫 굽기 — 모든 판이 '처음 실린' 회차다."""
    return {x['kind']: x for x in F.items(prev_path=str(tmp_path / 'none.xml'))}


def test_first_bake_takes_each_pages_own_date(tmp_path):
    """새 판의 발행일 = 그 페이지 JSON-LD 가 말하는 날(같은 keep_dates·같은 ld_date). 페이지가 생기기 전 날짜는 없다."""
    by = _fresh(tmp_path)
    wk = _read('weekly', 'index.html')
    assert by['weekly']['date'] == SP.ld_date(wk, 'datePublished'), '주간 발행일이 /weekly/ datePublished(발표일)와 다르다'
    for kind, rel in (('zone', ('zone', 'index.html')), ('monthly', ('monthly', 'index.html'))):
        page = _read(*rel)
        assert by[kind]['date'] == SP.ld_date(page, 'dateModified'), '%s 발행일이 페이지 dateModified 와 다르다' % kind
        assert by[kind]['date'] >= SP.ld_date(page, 'datePublished'), '%s 발행일이 페이지가 생기기 전이다' % kind
    sm = re.search(r'<loc>[^<]*/monthly/</loc>\s*<lastmod>([^<]+)</lastmod>', _read('sitemap.xml'))
    assert sm and sm.group(1) == by['monthly']['date'], '/monthly/ sitemap lastmod 와 JSON-LD dateModified 가 다르다'
    L = re.search(r'"L":"(\d{4}Q[1-4])"', _read('data-core.js')).group(1)
    assert by['zone']['guid'] == 'agongmap-zone-' + L


def test_an_edition_keeps_its_first_date(tmp_path):
    """같은 guid 는 이전 피드의 날짜를 물려받고, 처음 보는 guid(다음 기준월)는 페이지 날짜를 받는다."""
    fresh = _fresh(tmp_path)
    old = [dict(fresh['zone'], date='2026-08-15'),
           dict(fresh['monthly'], guid='agongmap-monthly-2001-01', date='2001-02-20')]
    prev = tmp_path / 'feed.xml'
    prev.write_text(F.render(old), encoding='utf-8')
    by = {x['kind']: x for x in F.items(prev_path=str(prev))}
    assert by['zone']['date'] == '2026-08-15', '같은 분기 판인데 발행일을 물려받지 않았다'
    assert by['monthly']['date'] == fresh['monthly']['date'], '새 기준월 판이 옛 판 날짜를 가져갔다'


def test_monthly_page_date_is_the_day_its_content_changed(tmp_path, monkeypatch):
    """/monthly/ dateModified·sitemap lastmod 는 내용이 바뀐 날(/zone/ 과 같은 keep_dates). 기준월의 1일이 아니다."""
    out, seen = tmp_path / 'monthly', []
    monkeypatch.setattr(MP, 'OUT', str(out))
    monkeypatch.setattr(MP.I, 'update_sitemap', lambda entries: seen.append(dict(entries)['/monthly/']))
    page = out / 'index.html'
    for day in ('2031-03-03', '2031-03-04', '2031-03-05'):
        monkeypatch.setattr(MP.KST, 'today_iso', lambda now=None, d=day: d)
        if day == '2031-03-05':   # 내용이 바뀐 날 — 표 제목 한 곳을 옛 판에서 바꿔 둔다
            page.write_text(page.read_text(encoding='utf-8').replace('이번 달 통계, 한 화면에서', '옛 제목', 1),
                            encoding='utf-8')
        assert MP.main() == 0
        h = page.read_text(encoding='utf-8')
        assert SP.ld_date(h, 'datePublished') == MP.PUBLISHED
    assert seen == ['2031-03-03', '2031-03-03', '2031-03-05'], seen
    assert SP.ld_date(h) == '2031-03-05'


def test_weekly_title_and_description_are_the_pages_own(items):
    """주간 항목 제목 = /weekly/ og:title, 설명 = meta description(한 페이지의 정본 두 문장 — 말투가 섞이지 않는다)."""
    wk = {x['kind']: x for x in items}['weekly']
    page = _read('weekly', 'index.html')
    og = re.search(r'<meta property="og:title" content="([^"]*)">', page).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)">', page).group(1)
    import html as _h
    assert wk['title'] == _h.unescape(og) and wk['desc'] == _h.unescape(desc)
    assert '습니다' not in wk['title']


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
