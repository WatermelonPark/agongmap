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
    """그림 글자가 휴대폰에서도, 데스크톱에서도 13px 이상 — 단이 좁아지면 viewBox 단위를 올리고, 겹치지 않게 대표 값만 적는다.

    단 폭은 실제 뼈대에서 센다: .wrap 최대 폭(--col-read) - 좌우 여백. 2026-11-07 디자인 검수 때까지 이 시험은 단을 640px 까지
    넓어지는 것으로 잡아(min(640, 화면-48)) 600px 이상 화면의 글 단이 516px 인 것을 놓쳤다 — 13 단위가 10.5px 로 그려졌는데
    초록이었다.
    변이(실제로 확인): 기본 규칙을 13px 로 되돌리면(그날 상태) 600px 이상 화면에서, 400px 이하 규칙의 26px 를 지우면 375px 에서
    빨개지고, _bars_svg 의 cb-k·cb-x2 표지를 지우면 넷째 단정이 빨개진다.
    픽스처: 막대 8개 합성 그림, EXTRA_CSS 의 미디어 규칙, 뼈대(make_indicator_pages.SHELL)와 app.css 의 단 폭 토큰.
    """
    import make_indicator_pages as I
    sizes = {int(w): float(px) for w, px in re.findall(
        r'@media \(max-width:(\d+)px\)\{\.cb-v,\.cb-x,\.cb-rl\{font-size:(\d+)px\}', MC.EXTRA_CSS)}
    assert sizes, '그림 글자 미디어 규칙이 없다'
    base = re.search(r'(?<![{,])\n\.cb-v,\.cb-x,\.cb-rl\{font-size:(\d+)px\}', MC.EXTRA_CSS)
    assert base, '그림 글자 기본 규칙이 없다'
    base = float(base.group(1))
    assert base == MC.CH_UNIT and max(sizes.values()) == MC.CH_UNIT_MAX, '생성기의 글자 단위 상수와 CSS 가 다르다'
    col_read = int(re.search(r'--col-read:(\d+)px', io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()).group(1))
    pad = int(re.search(r'\.wrap\{max-width:var\(--col-read\);margin:0 auto;padding:0 (\d+)px\}', I.SHELL).group(1))
    for vw in range(310, 1700, 3):
        hit = [w for w in sizes if vw <= w]       # 나중 규칙(더 좁은 max-width)이 이긴다 — 가장 좁게 걸린 규칙
        unit = sizes[min(hit)] if hit else base
        col = min(MC.CH_W, col_read - 2 * pad, vw - 2 * pad)
        assert unit * col / MC.CH_W >= 12.9, '%dpx 화면에서 그림 글자가 %.1fpx 다' % (vw, unit * col / MC.CH_W)
    spec = {'alt': 'x', 'series': [{'points': [('20%02d' % i, 100 + i * 37 % 300) for i in range(8)]}], 'rule': None}
    svg = MC._bars_svg(spec)
    assert 1 <= svg.count('cb-v cb-k') <= 2 and svg.count('cb-x cb-x2') == 4, '휴대폰용 대표 값·x 축 걸러 적기 표지가 없다'
    assert '.cb-v:not(.cb-k),.cb-x2{display:none}' in MC.EXTRA_CSS


def test_bar_labels_stay_inside_the_picture():
    """막대 값·연도 글자가 그림(viewBox 640) 밖으로 나가지 않는다 — 가장 큰 글자 단위(휴대폰 32)로 잰다.

    2026-11-07 디자인 검수(치명): 서울 13개 막대의 마지막 값 '15,287'이 375px 에서 오른쪽이 잘려 '15,28'로 읽혔다(가운데 맞춤
    중심 612.6, 26 단위 6자 폭 약 86). 끝 막대 글자는 끝 맞춤(cx-e)·첫 막대는 앞 맞춤(cx-s)으로 바꾼다.
    변이(실제로 확인): _anchor 가 늘 가운데(cx, '')를 돌려주면 빨개진다.
    픽스처: 그날 그림과 같은 모양의 합성 13개 막대(2017~2029, 값 2만~5만대, 마지막 15,287) — 그리고 5개 막대(가운데 모인 그림).
    또 연도 글자 윗선(기준선 - 32 단위 × 0.72)이 막대 밑단보다 아래인지 본다(26 이던 아래 여백에서 글자 위로 막대가 덮였다).
    """
    def spans(svg):
        out = []
        for x, y, cls, txt in re.findall(r'<text x="([\d.]+)" y="([\d.]+)" class="([^"]+)">([^<]+)</text>', svg):
            w = len(txt) * MC.CH_EM * MC.CH_UNIT_MAX
            x = float(x)
            lo = x if 'cx-s' in cls else (x - w if 'cx-e' in cls else x - w / 2)
            out.append((lo, lo + w, cls, txt, float(y)))
        return out
    vals = [29201, 33000, 41000, 54355, 40000, 31000, 36000, 33000, 38000, 32000, 21000, 25000, 15287]
    for pts in ([('%d' % (2017 + i), v) for i, v in enumerate(vals)], [('%d' % (2026 + i), v) for i, v in enumerate([978, 2339, 3342, 1200, 615])]):
        svg = MC._bars_svg({'alt': 'x', 'series': [{'points': pts}], 'rule': None})
        for lo, hi, cls, txt, _y in spans(svg):
            assert lo >= 0 and hi <= MC.CH_W, '%s 글자가 그림 밖(%.0f~%.0f)으로 나간다 — %s' % (txt, lo, hi, cls)
        bottom = max(float(y) + float(h) for y, h in re.findall(r'<rect x="[\d.]+" y="([\d.]+)" width="[\d.]+" height="([\d.]+)"', svg))
        base = min(y for _lo, _hi, cls, _t, y in spans(svg) if cls.startswith('cb-x'))
        assert base - MC.CH_UNIT_MAX * 0.72 >= bottom, '연도 글자 윗선이 막대 밑단(%.0f)에 붙는다' % bottom
    # 데스크톱 기본 단위(17)로 값이 간격에 안 들어가는 13개 그림은 대표 둘만 적는다(cb-dense), 5개 그림은 다 적는다.
    assert 'cchart-svg cb-dense' in MC._bars_svg({'alt': 'x', 'series': [{'points': [('%d' % i, v) for i, v in enumerate(vals)]}], 'rule': None})
    assert 'cb-dense' not in MC._bars_svg({'alt': 'x', 'series': [{'points': [('a', 978), ('b', 2339), ('c', 615)]}], 'rule': None})
    assert '.cb-dense .cb-v:not(.cb-k){display:none}' in MC.EXTRA_CSS


def test_weekly_line_chart_has_ticks_and_the_last_value():
    """주간 변동률 꺾은선에 눈금(최고·0·최저)과 마지막 값이 있다 — 숫자 없는 선이라 폭이 +0.1 인지 +1.0 인지 안 보였다(2026-11-07).

    변이(실제로 확인): _lines_svg 의 눈금 글자(cl-t) 줄을 지우면 첫 단정이, 마지막 값 줄을 지우면 둘째 단정이 빨개진다.
    픽스처: 매매 +0.05~+1.19, 전세 -0.12~+0.30 의 합성 두 계열(그날 수원 영통구 모양 — 0 아래로 내려간 주가 있다).
    """
    ma = [('2026-05-%02d' % (i + 1), v) for i, v in enumerate([0.05, 0.2, 1.19, 0.3, 0.43])]
    je = [(p, v) for (p, _), v in zip(ma, [0.1, 0.3, 0.2, -0.12, 0.05])]
    svg = MC._lines_svg({'alt': 'x', 'series': [{'name': '매매', 'points': ma}, {'name': '전세', 'points': je}]})
    ticks = re.findall(r'class="cb-x cx-s cl-t">([^<]+)<', svg)
    assert ticks and ticks[0] == '0' and '+1.19%' in ticks, ticks
    assert re.search(r'class="cb-v cb-k cx-e cl-t">\+0\.43%<', svg), '마지막 값이 없다'
    assert MC.CH_LINE_H >= 190, '눈금 글자 줄이 선과 겹친다(높이 150 이었다)'


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
