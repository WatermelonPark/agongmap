# -*- coding: utf-8 -*-
"""/feed.xml(RSS 2.0) — 사이트의 새 소식 세 가지를 싣는다(홈 마케팅 검수 D1·SEO-6, 2026-09-27).

왜: 네이버 색인이 08월 사본에 머물러 있었다. sitemap 과 IndexNow 말고 검색엔진이 새 글을 알아채는 길이 하나 더
필요하다 — 네이버 서치어드바이저는 'RSS 제출'로 피드를 받아 새 항목의 주소를 수집한다(대표가 배포 뒤 한 번 등록).

항목(각 종류의 최신 판 하나씩, 날짜 내림차순)
  - 주간 발표   /weekly/   제목·설명은 /weekly/ 의 og:title·meta description 그대로(make_weekly_page.titles·build).
                          guid 에 발표일을 넣는다(agongmap-weekly-2026-09-24) — 발표마다 새 항목.
  - 시도 리포트 /zone/     기준 분기가 바뀔 때 새 항목(guid agongmap-zone-2026Q2). 설명은 홈 설명과 같은 전국 판정 문장.
  - 월간 통계   /monthly/  가장 최신 기준월이 바뀔 때 새 항목(guid agongmap-monthly-2026-08). 설명은 /monthly/ 의 설명.

⚠️ pubDate 의 뜻은 한 가지다: **그 판이 사이트에 처음 실린 날**(발행 시점). 판이 생길 수 없는 과거 날짜(기준 분기·기준월의
   1일 따위)를 적지 않는다 — make_monthly_page 의 PUBLISHED 주석이 금지한 '없던 날짜에 발행' 신호다(D1 검토 B1).
     주간  : 발표일 = weekly_release.status(조사일)['pub'] (홈·/weekly/ JSON-LD datePublished·공유 카드와 같은 정본)
     시도  : 새 guid 가 처음 구워진 회차에 허브(/zone/) JSON-LD 의 dateModified — 새 분기가 들어온 날 허브 내용이 바뀌어
             make_sido_pages.keep_dates 가 그날로 굽는다. 그 뒤로는 커밋된 feed.xml 의 같은 guid 날짜를 물려받는다.
     월간  : 같은 규칙으로 /monthly/ JSON-LD dateModified(같은 keep_dates) → 그 뒤로는 물려받는다.
   이 생성기는 오늘 날짜를 읽지 않는다 — 날짜는 페이지(생성기가 방금 구운 것)와 이전 feed.xml 에서만 온다. 그래서 같은 입력으로
   두 번 돌리면 바이트가 같다. lastBuildDate 는 항목 날짜 가운데 가장 늦은 날, 시각은 00:00 KST(+0900)로 적는다.
⚠️ 문장은 새로 만들지 않는다. 제목·설명은 그 페이지를 굽는 생성기의 함수에서 가져온다(사이트 정본과 다른 말 금지).
⚠️ 채널·항목 주소는 CNAME 의 도메인에서 만든다(정식 도메인의 정본). sitemap 에는 넣지 않는다 — 피드는 문서가 아니다.

이 파일은 배치가 매 회차 굽는 산출물이다(TARGETS 에 feed.xml). PR 에 싣지 않는다.
표준 라이브러리만 쓴다(배치의 생성기 단계는 pip 설치 전에 돈다).

사용: python tools/make_feed.py
"""
import datetime
import email.utils
import html
import io
import os
import re
import sys
import xml.etree.ElementTree as ET

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import weekly_release as WR  # noqa: E402  (발표일 정본)
import make_weekly_page as MW  # noqa: E402  (주간 결론·설명·제목 말 — /weekly/ 와 같은 함수)
import make_monthly_page as MP  # noqa: E402  (월간 기준월·설명 — /monthly/ 와 같은 함수)
import make_home_summary as MHS  # noqa: E402  (전국 판정 문장 — 홈 설명과 같은 함수)
import make_sido_pages as SP  # noqa: E402  (페이지 JSON-LD 날짜 읽기 ld_date — keep_dates 와 같은 눈)

OUT = os.path.join(ROOT, 'feed.xml')
ZONE_PAGE = os.path.join('zone', 'index.html')        # 시도 리포트 항목의 링크(허브)
MONTHLY_PAGE = os.path.join('monthly', 'index.html')
PATH = '/feed.xml'


def host(root=ROOT):
    """정식 도메인(CNAME 파일 첫 줄)."""
    h = io.open(os.path.join(root, 'CNAME'), encoding='utf-8').read().strip().split()[0]
    if not re.match(r'^[a-z0-9.-]+\.[a-z]{2,}$', h):
        raise SystemExit('CNAME 에서 도메인을 읽지 못했다: %r' % h)
    return h


SITE = 'https://' + host()
TITLE = '아공맵 — 아파트 공급 지도'
DESC = ('국가 통계로 보는 시도별 아파트 공급과 주간 시세. 한국부동산원 주간 발표, 시도 공급 리포트 분기 갱신, '
        '이달의 공급 통계를 알립니다.')
KINDS = ('weekly', 'zone', 'monthly')   # 같은 날짜일 때의 순서

_DAYS = ('Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat', 'Sun')
_MONTHS = ('Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec')


def rfc822(iso):
    """'2026-09-24' → 'Thu, 24 Sep 2026 00:00:00 +0900'. 로캘에 기대는 strftime(%a·%b)을 쓰지 않는다."""
    d = datetime.date(*(int(x) for x in iso.split('-')))
    return '%s, %02d %s %d 00:00:00 +0900' % (_DAYS[d.weekday()], d.day, _MONTHS[d.month - 1], d.year)


def weekly_item(W, Q):
    """최신 주간 발표. 제목은 /weekly/ og:title, 설명은 meta description — 한 페이지의 정본 두 문장이라 말투가 섞이지 않는다."""
    rows = W.get('rows') or []
    p = rows[-1].get('p') if rows else None
    if not p or not re.match(r'^\d{4}-\d{2}-\d{2}$', p):
        return None
    pub = WR.status(p)['pub']
    title = MW.titles(p)[1]
    desc = MW.build(W, Q)[2]
    return {'kind': 'weekly', 'title': title, 'link': SITE + '/weekly/', 'guid': 'agongmap-weekly-' + pub,
            'date': pub, 'desc': desc}


def first_dates(path=None):
    """이전 feed.xml 의 guid → 발행일('YYYY-MM-DD'). 없거나 못 읽으면 {} — 그때는 새 판처럼 페이지 날짜를 쓴다."""
    try:
        root = ET.fromstring(io.open(path or OUT, encoding='utf-8').read().encode('utf-8'))
    except (IOError, OSError, ET.ParseError):
        return {}
    out = {}
    for it in root.iter('item'):
        g, d = (it.findtext('guid') or '').strip(), (it.findtext('pubDate') or '').strip()
        try:
            out[g] = email.utils.parsedate_to_datetime(d).date().isoformat()
        except (TypeError, ValueError):
            continue
    return out


def page_date(rel):
    """그 페이지 JSON-LD 의 dateModified(방금 구운 판). 페이지나 날짜가 없으면 None."""
    try:
        return SP.ld_date(io.open(os.path.join(ROOT, rel), encoding='utf-8').read())
    except (IOError, OSError):
        return None


def published(guid, rel, prev):
    """판의 발행일: 이전 피드에 있던 guid 면 그 날, 처음 보는 guid 면 그 페이지의 dateModified(새 판이 구워진 날)."""
    return prev.get(guid) or page_date(rel)


def zone_item(core, prev=None):
    """시도 리포트 — 기준 분기(ADV.sido.L). 설명은 홈 설명 첫 문장과 같은 전국 판정."""
    sido = core.get('sido') or {}
    L = sido.get('L') or ''
    m = re.match(r'^(\d{4})Q([1-4])$', L)
    if not m:
        return None
    f = MHS.facts(core)
    mt = MHS.meta_texts(dict(f, wk=None)) if f.get('nat') else None
    desc = mt[0] if mt else '시도별 아파트 공급 판정을 %s 기준으로 갱신했습니다.' % (sido.get('Ltxt') or L)
    guid = 'agongmap-zone-' + L
    date = published(guid, ZONE_PAGE, prev or {})
    if not date:
        return None
    return {'kind': 'zone', 'title': '시도별 아파트 공급 분석 — %s 기준' % (sido.get('Ltxt') or L),
            'link': SITE + '/zone/', 'guid': guid, 'date': date, 'desc': desc}


def monthly_item(adv, sts, prev=None):
    """이달의 통계 — 다섯 지표 가운데 가장 최신 기준월."""
    _, basis = MP.build(adv, sts)
    raw = MP.newest_basis(basis)
    key = MP.sort_key(raw)
    if not re.match(r'^\d{4}-\d{2}$', key):
        return None
    guid = 'agongmap-monthly-' + key
    date = published(guid, MONTHLY_PAGE, prev or {})
    if not date:
        return None
    return {'kind': 'monthly', 'title': '이달의 공급 통계 — %s 기준' % MP.month_label(raw),
            'link': SITE + '/monthly/', 'guid': guid, 'date': date, 'desc': MP.DESC}


def items(prev_path=None):
    """저장소의 데이터(data.js·data-core.js)·방금 구운 페이지·이전 feed.xml 에서 항목을 만든다. 오늘 날짜를 읽지 않는다."""
    prev = first_dates(prev_path)
    W, Q = MW.load()
    adv, sts = MP.load()
    out = [weekly_item(W, Q), zone_item(MHS.load_core(), prev), monthly_item(adv, sts, prev)]
    return [x for x in out if x]


def _x(s):
    return html.escape(str(s), quote=False)


def render(its):
    """항목 → RSS 2.0 문자열. 같은 입력이면 같은 바이트."""
    its = sorted(its, key=lambda x: (x['date'], -KINDS.index(x['kind'])), reverse=True)
    last = max((x['date'] for x in its), default=None)
    out = ['<?xml version="1.0" encoding="UTF-8"?>',
           '<rss version="2.0" xmlns:atom="http://www.w3.org/2005/Atom">',
           '<channel>',
           '  <title>%s</title>' % _x(TITLE),
           '  <link>%s/</link>' % SITE,
           '  <description>%s</description>' % _x(DESC),
           '  <language>ko</language>',
           '  <atom:link href="%s%s" rel="self" type="application/rss+xml"/>' % (SITE, PATH)]
    if last:
        out.append('  <lastBuildDate>%s</lastBuildDate>' % rfc822(last))
    for x in its:
        out += ['  <item>',
                '    <title>%s</title>' % _x(x['title']),
                '    <link>%s</link>' % _x(x['link']),
                '    <guid isPermaLink="false">%s</guid>' % _x(x['guid']),
                '    <pubDate>%s</pubDate>' % rfc822(x['date']),
                '    <description>%s</description>' % _x(x['desc']),
                '  </item>']
    out += ['</channel>', '</rss>']
    return '\n'.join(out) + '\n'


def main():
    body = render(items())
    old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
    if old == body:
        print('feed.xml 변경 없음')
        return 0
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote feed.xml (%d개 항목)' % body.count('<item>'))
    return 0


if __name__ == '__main__':
    sys.exit(main())
