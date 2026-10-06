# -*- coding: utf-8 -*-
"""/llms.txt — AI 검색이 읽는 사이트 요약(홈 마케팅 검수 D5, 2026-09-28 대표 승인).

형식은 llmstxt.org 제안을 따른다: `# 이름` → `> 한 줄 요약` → 본문 문단 → `## 섹션` 아래 `- [제목](절대 URL): 설명` 목록.

지키는 것
  - **숫자를 넣지 않는다**(세대수·%·호·날짜·분기 값). 배치마다 묵어 AI 가 옛 숫자를 인용하게 된다. 숫자는 페이지에 있다.
    예외는 창 길이('3년'·'4년', sido_zones.LEAD_Q·BACKLOG_WINDOW 에서)와 발표 요일(weekly_release 에서)뿐이다 —
    데이터 값이 아니라 산식·일정의 정의다. 시험(test_llms_txt)이 이 규칙을 그대로 본다.
  - 식의 이름은 sido_zones.formula_text()(숫자 없이 부른 일반식)를 그대로 쓴다 — 홈 산출 방법·카드 ⓘ·시도 리포트와 같은 말.
  - **시도 목록은 손으로 적지 않는다.** 방금 구운 sitemap.xml 의 `/zone/<이름>/` 주소를 전부 싣고(생성기 순서상 make_sido_pages
    뒤, make_feed 뒤에 돈다), 순서는 sido_zones(집계 AGG 먼저, 그다음 DISPLAY_ORDER)로 정한다. sitemap 에 있는데 sido_zones 에
    없는 이름은 버리지 않고 맨 뒤에 sitemap 순서로 싣는다 — sitemap 에 있으면 배포된 페이지이고, 이 파일이 배포된 페이지를
    빠뜨리는 쪽이 더 나쁘다(모델과 sitemap 의 어긋남은 make_sido_pages·sitemap 시험이 따로 본다). 그때 표준 오류에 경고를 남긴다.
  - 페이지 설명은 숫자 없는 기존 문장이 있으면 그것을 쓴다: /monthly/ 는 make_monthly_page.DESC, /feed.xml 은 make_feed.DESC,
    /faq/·/about/ 은 그 손 페이지의 meta description. 나머지는 여기서 짧게 적는다(숫자 금지).
  - 데이터 출처 기관 표기는 /about/ 의 '출처를 전부 밝힙니다' 줄과 같은 이름·순서다(시험이 대조).
  - 오늘 날짜를 읽지 않는다 — 같은 입력이면 같은 바이트. 도메인은 CNAME(make_feed.host).

이 파일은 배치가 매 회차 굽는 산출물이다(TARGETS 에 llms.txt). PR 에 싣지 않는다.
표준 라이브러리만 쓴다(배치의 생성기 단계는 pip 설치 전에 돈다).

사용: python tools/make_llms_txt.py
"""
import html
import io
import os
import re
import sys
import urllib.parse

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import sido_zones as SZ  # noqa: E402  (식·창 길이·등급 이름·시도 순서의 정본)
import weekly_release as WR  # noqa: E402  (발표 요일)
import make_feed as F  # noqa: E402  (도메인·사이트 이름·피드 설명)
import make_monthly_page as MP  # noqa: E402  (/monthly/ 설명)
import make_sido_pages as SP  # noqa: E402  (미분양 출처 기관 정본 UN_SOURCE)
import ping_indexnow as P  # noqa: E402  (sitemap 읽기 — IndexNow 와 같은 눈)

OUT = os.path.join(ROOT, 'llms.txt')
SITEMAP = os.path.join(ROOT, 'sitemap.xml')
PATH = '/llms.txt'
ZONE_RE = re.compile(r'^/zone/([^/]+)/$')

# 데이터 출처(기관 이름, 주소, 무엇을 가져오나). 이름·순서는 /about/ 의 출처 줄과 같다(test_llms_txt 가 대조).
# 미분양은 출처 기관 정본(make_sido_pages.UN_SOURCE, 전수 리뷰 #21) 줄에 붙인다 — 예전엔 한국부동산원 줄에 손으로 적어
# 시도 리포트·/monthly/(국토교통부)와 갈렸다(전수리뷰 B5).
_SOURCES = (
    ('KOSIS', 'https://kosis.kr', '국가통계포털 — 인허가·착공·준공 실적과 가격지수·전세가율 원자료'),
    ('한국부동산원', 'https://www.reb.or.kr/r-one/', '주간·월간 아파트 가격 동향'),
    ('국토교통부', 'https://www.molit.go.kr', '주택건설실적통계(인허가·착공·준공)'),
    ('한국은행', 'https://www.bok.or.kr', '금리'),
)
assert SP.UN_SOURCE in [n for n, _, _ in _SOURCES], '미분양 출처 기관(UN_SOURCE)이 출처 목록에 없다'
SOURCES = tuple((n, u, d + (' · 미분양주택현황' if n == SP.UN_SOURCE else '')) for n, u, d in _SOURCES)


def site(root=ROOT):
    return 'https://' + F.host(root)


SITE = site()   # 정식 도메인 — 생성기 SITE 상수들과 같은지 test_indexnow_changed 가 본다


def meta_description(rel, root=ROOT):
    """손 페이지의 meta description(숫자 없는 기존 문장 재사용). 없으면 SystemExit — 조용히 빈 설명을 싣지 않는다."""
    t = io.open(os.path.join(root, rel), encoding='utf-8').read()
    m = re.search(r'<meta name="description" content="([^"]*)"', t)
    if not m or not m.group(1).strip():
        raise SystemExit('%s 에서 meta description 을 읽지 못했다' % rel)
    return html.unescape(m.group(1)).strip()


def zone_locs(sitemap_xml, base):
    """sitemap 의 /zone/<이름>/ 주소 → [(이름(디코딩), loc 그대로)] (sitemap 순서). 허브(/zone/)는 뺀다."""
    out = []
    for loc, _ in P.sitemap_entries(sitemap_xml):
        if not loc.startswith(base + '/'):
            continue
        m = ZONE_RE.match(urllib.parse.unquote(loc[len(base):]))
        if m:
            out.append((m.group(1), loc))
    return out


def zone_order(pairs):
    """집계(AGG) 먼저, 그다음 DISPLAY_ORDER, sido_zones 에 없는 이름은 맨 뒤(sitemap 순서)."""
    def key(ix):
        i, (name, _) = ix
        if name in SZ.AGG:
            return (0, SZ.AGG.index(name), i)
        if name in SZ.DISPLAY_ORDER:
            return (1, SZ.DISPLAY_ORDER.index(name), i)
        return (2, 0, i)
    return [p for _, p in sorted(enumerate(pairs), key=key)]


def years(q):
    return '%g년' % (q / 4.0)


def build(root=ROOT, sitemap_xml=None):
    """llms.txt 문자열. sitemap_xml 을 주지 않으면 저장소의 sitemap.xml 을 읽는다. 오늘 날짜를 읽지 않는다."""
    base = site(root)
    if sitemap_xml is None:
        sitemap_xml = io.open(os.path.join(root, 'sitemap.xml'), encoding='utf-8').read()
    zones = zone_order(zone_locs(sitemap_xml, base))
    if not zones:
        raise SystemExit('sitemap.xml 에서 /zone/ 시도 주소를 하나도 못 읽었다 — make_sido_pages 가 먼저 돌았는지 볼 것')
    unknown = [n for n, _ in zones if n not in SZ.DISPLAY_ORDER]
    if unknown:
        sys.stderr.write('⚠️ sitemap 에 있으나 sido_zones 에 없는 시도 리포트: %s — 맨 뒤에 싣는다\n' % ', '.join(unknown))

    ahead, past = years(SZ.LEAD_Q), years(SZ.BACKLOG_WINDOW)
    grades = '·'.join(SZ.GRADE_LABS[k] for k in SZ.GRADE_KEYS)
    est = '·'.join(z for z in SZ.DISPLAY_ORDER if z in SZ.EST)
    srcs = '·'.join(n for n, _, _ in SOURCES)

    out = ['# %s' % F.TITLE, '',
           '> 국가 통계로 시도별 앞으로 %s 아파트 공급이 모자란지 남는지를 판정하고, 한국부동산원 주간 아파트 시세를 '
           '싣는 사이트입니다.' % ahead, '',
           '부족 세대는 「%s」으로 셉니다. 적정물량은 기준표에서 가져온 고정 상수이고, 입주 추정은 국토교통부 착공 '
           '실적을 %s 뒤로 민 값이며, 지난 %s 쌓인 부족은 그동안의 준공(멸실을 뺀 값)이 적정물량에 못 미친 만큼의 합입니다. 지난 %s 동안 '
           '적정물량보다 더 지은 곳은 남은 재고를 뺍니다. 부족(또는 남는) 세대가 그 지역 한 해 적정물량의 몇 배인지로 등급(%s)을 '
           '나누고, 순위는 등급 다음 절대량으로 정합니다. 지역 칸의 동그라미는 판정과 별개로, 앞으로 해마다 들어올 입주가 한 해 '
           '적정물량에 견줘 적음·보통·많음인지를 보입니다. 인허가는 착공하지 않는 계획이 섞여 판정에 쓰지 않습니다.'
           % (SZ.formula_text(), ahead, past, past, grades), '',
           '공급·가격 숫자는 원천이 발표한 값을 그대로 씁니다. 원천이 합쳐서 발표한 값을 비율로 나눠 채우지 않습니다'
           '(안분 추정 없음). 적정물량은 해마다 다시 계산하지 않는 기준선이며, 기준표에 따로 없는 지역(%s)은 추정한 값입니다. '
           '자료는 %s에서 가져오고 모든 숫자에 원출처를 붙입니다.' % (est, srcs), '',
           '공급 판정은 분기마다, 시세는 매주 한국부동산원 발표일(%s요일)에 새 발표를 반영합니다. 공급 기준의 판정이며 '
           '가격 예측이나 투자 자문이 아닙니다.' % WR.pub_weekday(), '']

    def item(title, url, desc):
        return '- [%s](%s): %s' % (title, url, desc)

    out += ['## 시도 리포트', '',
            item('시도별 아파트 공급', base + '/zone/',
                 '전국·수도권·지방과 시도별 공급 판정을 한 화면에 모은 허브입니다. 각 장은 분기별 공급, '
                 '%s 적정물량 대비 판정, 부족 세대의 식에 그 지역 숫자를 넣은 검산, 시군구 주간 시세를 담습니다.' % ahead)]
    for name, loc in zones:
        if name in SZ.AGG:
            note = '집계 리포트(시도 순위에는 넣지 않습니다)'
        elif name in SZ.DISPLAY_ORDER:
            note = '시도 리포트'
        else:
            note = '리포트'
        out.append(item('%s 아파트 공급' % name, loc, note))
    out += ['',
            '## 시세와 통계', '',
            item('주간 아파트 시세', base + '/weekly/',
                 '한국부동산원 주간 통계로 본 이번 주 시도·시군구·서울 구별 매매가격 변동과 방향이 이어진 곳'),
            item('이달의 통계', base + '/monthly/', MP.DESC),
            item('아파트 입주물량', base + '/moveins/',
                 '시도별 연간 입주물량 — 준공 실적과 착공 기준 추정, 적정물량과 견준 부족·과잉'),
            item('전세가율', base + '/jeonse-ratio/', '매매가 대비 전세가 비율의 시도별 현황과 사이클 신호로서의 뜻'),
            item('아파트 사이클 리포트', base + '/cycle/',
                 '공급 부족 → 전세 상승 → 매매 상승 → 신축 공급 → 입주 → 전세 하락 → 매매 하락의 고리를 국가 통계로 검증한 리포트'),
            '',
            '## 사이트 안내', '',
            item('자주 묻는 질문', base + '/faq/', meta_description(os.path.join('faq', 'index.html'), root)),
            item('소개', base + '/about/', meta_description(os.path.join('about', 'index.html'), root)),
            item('새 소식 피드(RSS)', base + F.PATH, F.DESC),
            '',
            '## 데이터 출처', '']
    out += [item(n, u, d) for n, u, d in SOURCES]
    return '\n'.join(out) + '\n'


def main():
    body = build()
    old = io.open(OUT, encoding='utf-8').read() if os.path.exists(OUT) else None
    if old == body:
        print('llms.txt 변경 없음')
        return 0
    io.open(OUT, 'w', encoding='utf-8', newline='\n').write(body)
    print('wrote llms.txt')
    return 0


if __name__ == '__main__':
    sys.exit(main())
