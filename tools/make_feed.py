# -*- coding: utf-8 -*-
"""/feed.xml(RSS 2.0) — 사이트의 새 소식 세 가지를 싣는다(홈 마케팅 검수 D1·SEO-6, 2026-09-27).

왜: 네이버 색인이 08월 사본에 머물러 있었다. sitemap 과 IndexNow 말고 검색엔진이 새 글을 알아채는 길이 하나 더
필요하다 — 네이버 서치어드바이저는 'RSS 제출'로 피드를 받아 새 항목의 주소를 수집한다(대표가 배포 뒤 한 번 등록).

항목(각 종류의 최신 판 하나씩, 날짜 내림차순)
  - 주간 발표   /weekly/   제목 '주간 아파트가격 동향 2026년 9월 셋째 주 · 결론 문장', 설명은 /weekly/ 의 meta description.
                          guid 에 발표일을 넣는다(agongmap-weekly-2026-09-24) — 발표마다 새 항목.
  - 시도 리포트 /zone/     기준 분기가 바뀔 때 새 항목(guid agongmap-zone-2026Q2). 설명은 홈 설명과 같은 전국 판정 문장.
  - 월간 통계   /monthly/  가장 최신 기준월이 바뀔 때 새 항목(guid agongmap-monthly-2026-08). 설명은 /monthly/ 의 설명.

⚠️ 날짜는 데이터 시점에서만 나온다 — 실행한 날(오늘)을 쓰지 않는다. 같은 데이터로 두 번 돌리면 바이트가 같아야 배치가
   데이터가 그대로인 날 빈 커밋을 만들지 않고, 피드를 읽는 쪽도 '매일 새 글'이라는 틀린 신호를 받지 않는다.
     주간  : 발표일 = weekly_release.status(조사일)['pub'] (홈·/weekly/·공유 카드와 같은 정본)
     시도  : 기준 분기(ADV.sido.L)를 make_monthly_page.sort_key 로 그 분기 마지막 달로 바꾼 달의 1일
             (월간 통계 dateModified 와 같은 '기준 시점 달의 1일' 규칙)
     월간  : make_monthly_page.newest_basis 의 dateModified 와 공개일 중 늦은 날 — /monthly/ 의 sitemap lastmod 와 같은 값
   lastBuildDate 는 항목 날짜 가운데 가장 늦은 날이다. 시각은 00:00 KST(+0900)로 적는다(발표 시각은 원천이 약속하지 않는다).
⚠️ 문장은 새로 만들지 않는다. 결론·설명은 그 페이지를 굽는 생성기의 함수에서 가져온다(사이트 정본과 다른 말 금지).
⚠️ 채널·항목 주소는 CNAME 의 도메인에서 만든다(정식 도메인의 정본). sitemap 에는 넣지 않는다 — 피드는 문서가 아니다.

이 파일은 배치가 매 회차 굽는 산출물이다(TARGETS 에 feed.xml). PR 에 싣지 않는다.
표준 라이브러리만 쓴다(배치의 생성기 단계는 pip 설치 전에 돈다).

사용: python tools/make_feed.py
"""
import datetime
import html
import io
import os
import re
import sys

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

OUT = os.path.join(ROOT, 'feed.xml')
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
    """최신 주간 발표. 결론을 못 만들면(시도 값이 절반도 없는 주) 제목에서 결론만 빠진다."""
    rows = W.get('rows') or []
    p = rows[-1].get('p') if rows else None
    if not p or not re.match(r'^\d{4}-\d{2}-\d{2}$', p):
        return None
    pub = WR.status(p)['pub']
    c = MW.conclusion(W)
    title = '%s %s' % (MW.TITLE_KW, WR.week_label(p, year=True)) + ((' · ' + c['text']) if c else '')
    desc = MW.build(W, Q)[2]
    return {'kind': 'weekly', 'title': title, 'link': SITE + '/weekly/', 'guid': 'agongmap-weekly-' + pub,
            'date': pub, 'desc': desc}


def zone_item(core):
    """시도 리포트 — 기준 분기(ADV.sido.L). 설명은 홈 설명 첫 문장과 같은 전국 판정."""
    sido = core.get('sido') or {}
    L = sido.get('L') or ''
    m = re.match(r'^(\d{4})Q([1-4])$', L)
    if not m:
        return None
    f = MHS.facts(core)
    mt = MHS.meta_texts(dict(f, wk=None)) if f.get('nat') else None
    desc = mt[0] if mt else '시도별 아파트 공급 판정을 %s 기준으로 갱신했습니다.' % (sido.get('Ltxt') or L)
    return {'kind': 'zone', 'title': '시도별 아파트 공급 분석 — %s 기준' % (sido.get('Ltxt') or L),
            'link': SITE + '/zone/', 'guid': 'agongmap-zone-' + L, 'date': MP.sort_key(L) + '-01', 'desc': desc}


def monthly_item(adv, sts):
    """이달의 통계 — 다섯 지표 가운데 가장 최신 기준월."""
    _, basis = MP.build(adv, sts)
    raw, mod_iso = MP.newest_basis(basis)
    key = MP.sort_key(raw)
    if not re.match(r'^\d{4}-\d{2}$', key):
        return None
    return {'kind': 'monthly', 'title': '이달의 공급 통계 — %s 기준' % MP.month_label(raw),
            'link': SITE + '/monthly/', 'guid': 'agongmap-monthly-' + key,
            'date': max(mod_iso, MP.PUBLISHED), 'desc': MP.DESC}


def items():
    """저장소의 데이터(data.js·data-core.js)에서 항목을 만든다. 오늘 날짜를 읽지 않는다."""
    W, Q = MW.load()
    adv, sts = MP.load()
    out = [weekly_item(W, Q), zone_item(MHS.load_core()), monthly_item(adv, sts)]
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
