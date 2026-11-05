# -*- coding: utf-8 -*-
"""콘텐츠 2차 디자인 리뷰(2026-10-31)에서 고친 것들 — 표·그림·면책·날짜·낱말.

재현한 실제 상태(2026-10-31 main, Chromium 375px·1280px):
- 글 페이지를 읽는 단(read, 516px)으로 바꾼 뒤 표가 그 단에 갇혀 11열 표 행이 88px 로 접혔고, '핵심 숫자' 표는 칸마다 한 줄로
  묶여 값 열이 화면 밖에 있었다.
- 그림 글자(viewBox 640 단위 11)가 375px 단에서 5.7px 로 그려졌다.
- 공용 푸터에 면책이 들어간 뒤 글 끝 .cdisc 와 같은 문장이 두 번 연달아 나왔다.
- 출처 줄의 '주간 아파트가격동향(2026-10-19 조사)' 가 손으로 박혀, 배치가 고치는 같은 글 그림 각주(10-26)와 시점이 갈렸다.
- 꺾은선 양 끝 눈금이 '05-04'·'10-26' ISO 조각이었다.
- 도시 허브 카드·/moveins/ 도시 목록 각주가 '적정 입주량'(옛 낱말)을 썼다 — 원고 검사는 원고만 보고 생성기 글자를 못 봤다.
"""
import glob
import io
import os
import re
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import content_md as CM            # noqa: E402
import content_tables as CT        # noqa: E402
import make_content_pages as MC    # noqa: E402
import sido_zones as SZ            # noqa: E402


def test_long_cells_wrap_and_tables_widen_past_the_read_column():
    """긴 글자 칸은 줄을 바꾸고(tx), 데스크톱에서는 표만 읽는 단 밖으로 960px 까지 넓힌다.

    변이(실제로 확인): _cls 의 길이 조건(LONG_CELL)을 지우면 첫 단정이, EXTRA_CSS 의 1024px 넓힘 규칙을 지우면 셋째 단정이 빨개진다.
    픽스처: '핵심 숫자' 표 모양의 합성 두 열 표(값 칸이 '22평형 96, 27평형 160, …').
    """
    h = MC._table_html(['항목', '값'], [['평형별 대지지분', '22평형 96, 27평형 160, 32평형 200'], ['세대수', '1,234']])
    tds = re.findall(r'<td([^>]*)>([^<]*)</td>', h)
    assert tds[0][0] == ' class="tx"', '긴 값 칸이 한 줄로 묶인다 — %s' % tds[0]
    assert tds[1][0] == '', '짧은 숫자 칸까지 줄바꿈 칸이 됐다'
    m = re.search(r'@media \(min-width:1024px\)\{\s*\.ctab\{([^}]*)\}', MC.EXTRA_CSS)
    assert m and 'min(960px' in m.group(1) and 'min-width:100%' in m.group(1), '데스크톱에서 표가 읽는 단 밖으로 넓어지지 않는다'


def test_chart_labels_hold_13px_on_a_phone():
    """그림 글자가 휴대폰에서도 13px 이상 — 단이 좁아지면 viewBox 단위를 올리고, 겹치지 않게 대표 값만 적는다.

    변이(실제로 확인): 400px 이하 규칙의 26px 를 지우면(11 단위로 돌아가면) 계산한 화면 크기가 13px 아래로 내려가 빨개지고,
    _bars_svg 의 cb-k·cb-x2 표지를 지우면 넷째 단정이 빨개진다.
    픽스처: 막대 8개 합성 그림과 EXTRA_CSS 의 미디어 규칙. 375px 단 폭은 375 - 좌우 24px = 327px 로 잡는다.
    """
    sizes = {int(w): float(px) for w, px in re.findall(
        r'@media \(max-width:(\d+)px\)\{\.cb-v,\.cb-x,\.cb-rl\{font-size:(\d+)px\}', MC.EXTRA_CSS)}
    assert sizes, '그림 글자 미디어 규칙이 없다'
    for vw in range(310, 1024, 3):
        hit = [w for w in sizes if vw <= w]       # 나중 규칙(더 좁은 max-width)이 이긴다 — 가장 좁게 걸린 규칙
        unit = sizes[min(hit)] if hit else 13.0
        col = min(MC.CH_W, vw - 48)
        assert unit * col / MC.CH_W >= 12.9, '%dpx 화면에서 그림 글자가 %.1fpx 다' % (vw, unit * col / MC.CH_W)
    spec = {'alt': 'x', 'series': [{'points': [('20%02d' % i, 100 + i * 37 % 300) for i in range(8)]}], 'rule': None}
    svg = MC._bars_svg(spec)
    assert 1 <= svg.count('cb-v cb-k') <= 2 and svg.count('cb-x cb-x2') == 4, '휴대폰용 대표 값·x 축 걸러 적기 표지가 없다'
    assert '.cb-v:not(.cb-k),.cb-x2{display:none}' in MC.EXTRA_CSS


def test_line_chart_ends_use_the_tick_date_form():
    """꺾은선 양 끝 날짜는 눈금 꼴 '5/4'(sido_zones.day_text) — '05-04' ISO 조각이 아니다.

    변이(실제로 확인): _lines_svg 를 ends[0][5:] 로 되돌리면 빨개진다.
    픽스처: 두 점짜리 합성 꺾은선.
    """
    spec = {'alt': 'x', 'series': [{'name': '매매', 'points': [('2026-05-04', 0.1), ('2026-10-26', 0.2)]}]}
    svg = MC._lines_svg(spec)
    ends = re.findall(r'class="cb-x cx-[se]">([^<]+)<', svg)
    assert ends == ['5/4', '10/26'], ends


def test_post_page_has_one_disclaimer_and_styled_crumb_and_lists():
    """구워진 글 페이지에 면책이 한 번(공용 푸터)만, 빵부스러기 링크가 기본 파랑이 아니고, 목록이 단 여백 안이다.

    변이(실제로 확인): build_page 에 <p class="cdisc"> 를 되살리면 첫 단정이 빨개진다.
    픽스처: 생성기를 먼저 돌린 저장소의 구워진 글 하나(게이트와 같은 순서) — 없으면 건너뛴다(CI 에서는 건너뜀도 실패).
    """
    built = CM.built(ROOT)
    if not built:
        pytest.skip('구워진 글이 없다')
    sec, slug, _ = built[0]
    page = io.open(os.path.join(ROOT, sec, slug, 'index.html'), encoding='utf-8').read()
    import site_nav as N
    assert page.count(N.DISCLAIMER) == 1 and 'class="cdisc"' not in page, '면책이 두 번 나온다'
    assert '.crumb a{color:var(--ink2)' in page
    assert '.cbody ul,.cbody ol,.csrc{padding-left:' in page


def test_weekly_source_date_follows_the_data():
    """출처 줄의 주간 조사일은 자리표(v:asof:weekly)로 데이터에서 온다 — 손으로 박은 '(2026-10-19 조사)' 가 없다.

    변이(실제로 확인): fill_meta 에서 sources 채우기를 지우면 둘째 단정이, 원고 하나를 손 날짜로 되돌리면 셋째 단정이 빨개진다.
    픽스처: 실제 데이터(주간 최신 조사일)와 저장소의 원고 전부.
    """
    data = CT.load()
    rows = (data.get('weekly') or {}).get('rows') or []
    if not rows:
        pytest.skip('주간 자료가 없다')
    want = SZ.day_text(rows[-1]['p'])
    assert CT.value(data, 'asof', ['weekly']) == want
    meta = CT.fill_meta({'title': 't', 'summary': 's', 'sources': ['한국부동산원 주간 아파트가격동향({{v:asof:weekly}} 조사)']}, data)
    assert meta['sources'] == ['한국부동산원 주간 아파트가격동향(%s 조사)' % want]
    hand = [p for _, _, p in CM.posts(ROOT)
            if re.search(r'\(20\d\d-\d\d-\d\d 조사\)', io.open(p, encoding='utf-8').read())]
    assert not hand, '출처 조사일을 손으로 적은 원고: %s' % hand


def test_generated_pages_do_not_use_the_old_word():
    """구워진 페이지 어디에도 옛 낱말 '적정 입주량'이 없고, 콘텐츠 페이지에는 '적정 대비'도 없다(CLAUDE.md '같은 개념은 한 이름').

    원고 검사(content_check)는 원고만 본다 — 생성기가 쓰는 글자(허브 카드 설명·/moveins/ 도시 목록 각주)는 이 시험이 본다.
    변이(실제로 확인): make_content_pages 의 도시 허브 카드 설명을 '적정 입주량'으로 되돌리면 빨개진다.
    픽스처: 생성기를 먼저 돌린 저장소의 모든 .html(문서·초안 폴더 제외).
    """
    bad = []
    for p in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        rel = os.path.relpath(p, ROOT).replace(os.sep, '/')
        if rel.split('/')[0] in ('docs', 'drafts', 'art_raw', 'tools', 'node_modules'):
            continue
        t = io.open(p, encoding='utf-8').read()
        if re.search(r'적정\s+입주량', t):
            bad.append(rel)
        top = rel.split('/')[0]
        if (top in CM.SECTIONS or top == MC.REPORTS_DIR) and re.search(r'적정\s+대비', t):
            bad.append(rel + ' (적정 대비)')
    assert not bad, '옛 낱말이 남은 페이지: %s' % bad[:10]
