# -*- coding: utf-8 -*-
"""홈·시세 탭 디자인 검수 수정(2026-11-07, 영역 B)이 되돌아가지 않는다.

재현하는 실제 상태(검수 캡처, Chromium 375px·1280px, 11/2 조사 주):
  stats-1  1280px 표 보기에서 경기 › 성남 분당구를 고르면(.gsec.sel-one — 한 지역 표 compact) '⇄ 행열 전환'이 보이는데, compact 를
           굽는 renderTrendTables 는 TRANSP 를 읽지 않아 눌러도 단추만 검게 켜지고 표는 그대로였다.
  stats-2  1단 모드(.smode 상자 넷)·2단 주간|월간(13.5px 알약)·3단 순위|지도|그래프|표(붙은 분절)·4단 기간(1단과 같은 상자 넷) — 꼴이
           셋이고 1단과 4단이 같은 189×40px 상자로 두 번 섰다.
  stats-3  375px 시세 탭 지도 보기에서 지도가 y≈455 에서 시작했다(위에 제목·버튼·설명·모드·주간|월간·제목 줄·분절·기준 줄·칸 줄).
  stats-4  그래프 축이 본문 서브셋(AgongHome)이 아닌 대체 글꼴·10px·45° 강제 회전이었다.
  stats-5  지도·표·순위의 빨강 = 상승인데 그래프의 빨강(#e0564a) = 매매 계열, 보라 = 전세였다.
  stats-6  투자지표 입주물량 설명·산식 문장, 공용 푸터 면책이 13px(읽는 문장 14px 하한 미달 — 2026-11-06 대표 결정).
  stats-7  한 지역 표 첫 열 머리는 가운데·칸은 왼쪽, 1280px 에서 세 열이 772px 를 다 써 숫자가 243px 열 가운데 떴다.
  stats-9  그래프 위 범례는 가운데, 단위 줄은 오른쪽 — 짧은 두 줄의 축이 갈렸다.
  stats-10 상승 TOP 10 1~3위에만 메달 이모지, 켜진 정렬 열 머리는 켜진 탭과 같은 먹색 채움, 머리 꼬리 '매매 기준'은 겹말.
  home-1   시세 모드에서도 지도 아래 단추가 공급용('시도별로 자세히 보기')이었고 주간 전용 입구 TOP 10 은 600px 아래였다.
  home-2   주간 구역에서 노란 카카오톡 공유가 주 행동(TOP 10)보다 위에 있었다.
  home-3/6 히어로 부제 13.5px·산출 방법 본문 13px, 히어로 이름표가 제목의 60% 라 375px 에서 제목/본문 2.0배.
  home-9   퀴즈 단추 셋만 컬러 이모지. home-10 '순환의 6개 고리'인데 아래 도식은 네 칸. home-12 '최근 리포트' 제목(15px)이 안의 카드
           제목(16px)보다 작았다.

브라우저 실측은 배치 게이트(pytest·pillow 만)에서 돌 수 없어, 그 화면을 정하는 규칙·마크업·함수를 대조하고 함수는 node 로 돌린다.
각 시험 독스트링에 변이(실제로 넣어 빨간 것을 확인)를 적는다. 픽스처: 저장소 index.html·app.css·home-*.js(home_src) 원문과 합성 DOM.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import site_nav as NAV  # noqa: E402

READ_PX = getattr(NAV, 'READ_PX', 14)   # 읽는 문장 하한(2026-11-06 대표 결정) — 정본은 site_nav.READ_PX(영역 D)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _css():
    return re.sub(r'/\*.*?\*/', '', io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read(), flags=re.S)


def _index():
    return dict(HS.home_files())['index.html']


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])' + re.escape(sel) + r'\{([^}]*)\}', css)
    assert m, '%s 규칙을 찾지 못했다' % sel
    return m.group(1)


def _media_block(css, cond):
    i = css.index('@media(%s){' % cond)
    depth = 0
    for j in range(css.index('{', i), len(css)):
        depth += {'{': 1, '}': -1}.get(css[j], 0)
        if depth == 0:
            return css[i:j + 1]
    raise AssertionError(cond)


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, '%s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))


def _px(rule, prop='font-size'):
    m = re.search(r'(?<![\w-])%s:([\d.]+)px' % prop, rule)
    assert m, (prop, rule)
    return float(m.group(1))


# ── 시세 탭 ────────────────────────────────────────────────────────────────────

def test_transpose_button_hides_where_it_cannot_apply():
    """stats-1: 넓은 화면(721px 이상)에서 지역을 고른 시장동향 표(.gsec.sel-one — compact 표)에는 행열 전환 단추 줄이 없다.
    compact 를 굽는 코드는 TRANSP 를 읽지 않으므로(전환할 축이 없다 — 행 = 기간, 열 = 매매·전세) 단추를 숨기는 것이 맞다.
    sel-one 은 시장동향(week·month) 표에만 붙어 인허가·입주물량 표의 단추는 그대로다.

    변이(실제로 확인): app.css 의 '.gsec.sel-one .tr-row{display:none}' 를 지우면, 또는 그 규칙을 721px 미디어 밖 다른 조건으로
    옮기면 빨개진다. compact 생성이 TRANSP 를 읽게 되면(전환을 실제로 구현하면) 둘째 단정이 알린다 — 그때는 단추를 되살린다.
    """
    css = _css()
    wide = _media_block(css, 'min-width:721px')
    assert re.search(r'\.gsec\.sel-one \.tr-row\{display:none\}', wide), '한 지역 표에서 행열 전환 단추를 숨기지 않는다'
    src = HS.home_source()
    fn = _js_func(src, 'renderTrendTables')
    compact = fn[fn.index('const CR='):]
    assert 'TRANSP' not in compact, 'compact 표가 행열 전환을 읽는다 — 단추를 숨길 까닭이 없어졌다(규칙을 걷을 것)'
    assert "classList.toggle('sel-one'" in fn
    assert src.count("toggle('sel-one'") == 1, 'sel-one 을 시장동향 밖 표에도 단다 — 그 표의 행열 전환까지 숨는다'


def test_market_head_is_one_row_of_segmented_controls():
    """stats-2·3: 시장동향 머리 — 주간|월간(.adv-tabs, 구역 밖 하나라 왼쪽에 띄운다)과 각 구역의 순위|지도|그래프|표(.mk-gt, 구역 첫 줄)가
    한 줄이고, 제목 줄(.adv-h)은 그 아래다. 2단 탭(.adv-tabs)과 그래프 기간(.period.trp)은 3단 보기(.gt)와 같은 붙은 분절(테두리는
    묶음에, 단추 사이 틈 0)이다 — 떨어진 상자 넷은 1단 모드(.smode)만. 시세 탭 머리 버튼 아래 설명 줄은 없다.

    변이(각각 실제로 확인): .adv-tabs 를 옛 'display:flex;gap:8px' 로 되돌리면, .period.trp 규칙을 지우면, 주간 구역의 .gt 를 .adv-h
    안으로 되돌리면, #stats-market .adv-tabs 의 float 를 지우면, .shero-link 에 <span> 설명을 되살리면 빨개진다.
    """
    css = _css()
    gt = _rule(css, '.gt')
    for sel in ('.adv-tabs', '.period.trp'):
        r = _rule(css, sel)
        assert 'inline-flex' in r and 'border:1.5px solid var(--line)' in r and 'overflow:hidden' in r, (sel, r)
        assert not re.search(r'(?<![\w-])gap:(?!0)', r), (sel, r)
    for sel in ('.adv-tabs button', '.period.trp button'):
        r = _rule(css, sel)
        assert 'border:0' in r and 'min-height:40px' in r, (sel, r)   # 높이 40px 은 test_speed_a11y 의 터치 하한
    assert 'border:1.5px solid var(--line)' in gt
    assert 'float:left' in _rule(css, '#stats-market .adv-tabs')
    assert 'clear:left' in _rule(css, '#stats-market .adv-h')
    assert 'min-width:max-content' in _rule(css, '#stats-market .gt-head.mk-gt'), '좁은 폭에서 단추 넷이 잘린다(줄째 내려가야 한다)'
    h = _index()
    for k in ('week', 'month'):
        sec = re.search(r'<section class="adv-sec gsec gm-m" id="sec-%s"[^>]*>(.*?)</section>' % k, h, re.S).group(1)
        assert sec.lstrip().startswith('<div class="gt-head mk-gt"><div class="gt">'), k
        assert sec.index('mk-gt') < sec.index('<div class="adv-h">'), k
        assert 'class="gt"' not in re.search(r'<div class="adv-h">.*?</div>', sec, re.S).group(0), k
    tabs = h.index('<div class="adv-tabs" role="tablist" aria-label="시장동향 주기">')
    assert tabs < h.index('id="sec-week"')
    assert re.search(r'<p class="shero-link"><a href="/monthly/">[^<]*</a></p>', h), '시세 탭 머리 버튼 아래 설명 줄이 되살아났다'


def test_stats_map_basis_and_cell_meaning_share_one_line_above_the_map():
    """stats-3·8: 지도 위 기준 줄('11/2 기준 · 한국부동산원')과 칸 줄의 뜻('칸 숫자: 위 = 매매 · 아래 = 전세')은 한 줄(.map-top, 폭이
    모자라면 꺾인다)이고 지도·순위보다 앞이다. 순위 보기에서는 칸 줄을 숨긴다(지도가 없다).

    변이(실제로 확인): drawNationMap 에서 .map-top 감싸기를 빼면, 순위 보기 숨김 목록에서 .gsec.gm-r .map-rows 를 빼면 빨개진다.
    """
    draw = _js_func(HS.home_source(), 'drawNationMap')
    top = draw.index("'<div class=\"map-top\">'+mapDateChip(")
    assert top < draw.index("'<p class=\"map-rows\">칸 숫자: '") < draw.index('rankTables(S') < draw.index('map-scroll'), draw[:400]
    css = _css()
    hide = re.search(r'([^{}]*\.gsec\.gm-m \.map-rank[^{}]*)\{display:none\}', css).group(1)
    assert '.gsec.gm-r .map-rows' in hide
    assert 'flex-wrap:wrap' in _rule(css, '.map-top')


def test_trend_chart_series_colors_follow_the_site_series_colors():
    """그래프 계열 색은 TR_COL 하나이고 사이트 공통 계열색(site_nav.SERIES_COL — 매매 빨강·전세 보라·월세 초록, 2026-11-11 대표 결정
    '사이클 색으로 통일')과 같으며 범례 네모(.cl-ma·.cl-je·.cl-wo)와 같다. 11-07 stats-5 의 먹·회청(#131e24·#7a8b91)과 옛 연보라
    #a98be0·옛 빨강 #e0564a 는 쓰지 않는다.

    변이(실제로 확인): TR_COL.ma 를 옛 '#131e24' 로 되돌리면, .cl-je 범례를 '#a98be0' 로 되돌리면, TR_COL.je 만 바꾸고 범례를 그대로
    두면 빨개진다.
    """
    import site_nav as N
    src = HS.home_source()
    m = re.search(r"^const TR_COL=\{ma:'(#[0-9a-f]{6})',je:'(#[0-9a-f]{6})',wo:'(#[0-9a-f]{6})'\};", src, re.M)
    assert m, 'TR_COL 이 없다'
    col = dict(zip(('ma', 'je', 'wo'), m.groups()))
    assert col == {'ma': N.SERIES_COL['ma'], 'je': N.SERIES_COL['je'], 'wo': N.SERIES_COL['sup']}, col
    css = _css()
    for k, cls in (('ma', 'cl-ma'), ('je', 'cl-je'), ('wo', 'cl-wo')):
        assert ('background:%s' % col[k]) in _rule(css, '.chart-legend .%s::before' % cls), (k, cls)
    draw = _js_func(src, 'drawTrendChart')
    for bad in ('#e0564a', '#131e24', '#7a8b91', '#a98be0'):
        assert bad not in draw and bad not in set(col.values()), bad
    for k in ('ma', 'je', 'wo'):
        assert 'TR_COL.%s' % k in draw, k


def test_trend_chart_axis_uses_the_home_font_and_turns_only_when_needed():
    """stats-4: 그래프 글꼴(FONT, Chart.defaults)은 홈 body 글꼴 목록의 앞 두 항목(서브셋 AgongHome → Pretendard Variable)으로
    시작하고, 시장동향 축 눈금은 11px 이상·x 축 최소 회전 0(눕힘은 autoSkip 뒤 필요할 때만)이다.

    변이(실제로 확인): FONT 를 옛 "'Pretendard Variable',…" 로 되돌리면, minRotation 을 45 로, 눈금 크기를 10 으로 되돌리면 빨개진다.
    """
    src = HS.home_source()
    font = re.search(r'^const FONT="([^"]+)";', src, re.M).group(1)
    body = re.search(r"body\.home-app\{font-family:([^}]+)\}", _index()).group(1)
    head = [x.strip() for x in body.split(',')][:2]
    assert [x.strip() for x in font.split(',')][:2] == head, (font, head)
    draw = _js_func(src, 'drawTrendChart')
    assert 'minRotation:0' in draw and 'minRotation:45' not in draw
    sizes = [int(x) for x in re.findall(r'font:\{size:(\d+)\}', draw)]
    assert sizes and min(sizes) >= 11, sizes


def test_trend_chart_legend_and_unit_share_one_row():
    """stats-9: 그래프 위 범례(왼쪽)와 단위·기간(오른쪽)은 한 줄(.chart-top)이다 — 두 시장동향 구역 모두.

    변이(실제로 확인): index.html 의 .chart-top 감싸기를 한 구역에서 빼면, .chart-top .chart-legend 를 가운데 정렬로 되돌리면 빨개진다.
    """
    h = _index()
    for k in ('week', 'month'):
        assert re.search(r'<div class="chart-top"><div class="chart-legend">.*?</div><div class="chart-unit" id="%s-unit">' % k, h), k
    css = _css()
    assert 'justify-content:flex-start' in _rule(css, '.chart-top .chart-legend')
    assert 'margin:0 0 0 auto' in _rule(css, '.chart-top .chart-unit')


def test_single_region_table_is_narrow_and_its_first_head_follows_the_cells():
    """stats-7: 한 지역 표(compact)는 폭이 묶이고(세 열이 772px 를 다 쓰지 않는다) 첫 열(날짜) 머리는 칸과 같은 왼쪽이다. 전 지역
    매트릭스 머리는 2026-07-22 원칙(가운데) 그대로.

    변이(실제로 확인): '.adv-tblwrap.compact{max-width:520px}' 를 지우면, compact 첫 머리 왼쪽 규칙을 지우면 빨개진다.
    """
    css = _css()
    assert any('max-width:520px' in r for r in re.findall(r'(?:^|[}\s])\.adv-tblwrap\.compact\{([^}]*)\}', css))
    assert 'text-align:left' in _rule(css, '.adv-tblwrap.compact table.adv thead th:first-child')
    assert '\ntable.adv thead th:first-child{text-align:center}' in css   # 전 지역 매트릭스는 원칙(가운데) 그대로


def test_rank_tables_have_no_medals_or_black_sort_head():
    """stats-10: TOP 10 두 표에 메달 이모지가 없고(1~3위는 굵기·먹색 — 두 표 같은 규칙), 켜진 정렬 열 머리는 먹색 채움이 아니라 밑줄,
    머리 꼬리 '매매 기준'은 없다(정렬 열 머리가 같은 말을 한다).

    변이(실제로 확인): rankTables 에 메달(🥇)을 되살리면, .rk-sort.on 을 'background:var(--ink)' 로 되돌리면, 머리에 basis 를
    되살리면 빨개진다.
    """
    fn = re.sub(r'/\*.*?\*/', '', _js_func(HS.home_source(), 'rankTables'), flags=re.S)   # 주석 속 옛 사례(🥈김제)는 뺀다
    assert not re.search('[\U0001F947-\U0001F949]', fn) and 'rk-medal' not in fn
    assert '기준</span>' not in fn and 'basis' not in fn
    css = _css()
    on = _rule(css, '.rank-tbl thead th.rk-sort.on')
    assert 'background' not in on and 'var(--ink)' in on, on
    assert 'font-weight:700' in _rule(css, '.rank-tbl tbody tr:nth-child(-n+3) td:first-child')
    assert '.rk-medal' not in css


def test_reading_sentences_on_the_stats_tab_are_14px():
    """stats-6: 투자지표 설명 문장(.adv-note)은 14px 이고 입주물량 산식은 그 문장에 있다(출처 줄 13px 캡션에는 기관·주기만). 홈·
    시세·퀴즈 푸터의 면책 고지(.legal-disc)도 14px — 홈에서 13px 로 다시 덮지 않는다.

    변이(실제로 확인): .adv-note 를 13px 로, .legal-disc 를 13px 로 되돌리면, #view-home 묶음에 .legal-disc 를 되살리면, 산식을
    출처 줄로 되돌리면 빨개진다.
    """
    css = _css()
    assert _px(_rule(css, '.adv-note')) >= READ_PX
    assert _px(_rule(css, '.legal-disc')) >= READ_PX
    assert _px(_rule(css, '.disc')) >= READ_PX   # 면책 문장(.disc) 도 같은 하한
    for m in re.finditer(r'([^{}]+)\{([^}]*)\}', css):
        if re.search(r'\.(legal-disc|disc)(?![\w-])', m.group(1)) and 'font-size' in m.group(2):
            assert _px(m.group(2)) >= READ_PX, m.group(0)
    h = _index()
    occ = h[h.index('id="sec-occ"'):]
    occ = occ[:occ.index('</section>')]
    note = re.search(r'class="adv-note">([^<]*)<', occ).group(1)
    src = re.search(r'class="src-note">(.*?)</div>', occ).group(1)
    assert '3년 뒤로 민 추정' in note and '전환율' in note and '전환율' not in src and '3년 뒤로' not in src, (note, src)


# ── 홈 ────────────────────────────────────────────────────────────────────────

SCORE_DOM = r'''
%(fns)s
var sent=[];
function track(e,p){ sent.push([e,p.to]); }
function A(href,txt,onc){ var at={href:href,onclick:onc}, L=[];
  return {dataset:{},textContent:txt,getAttribute:function(k){return k in at?at[k]:null},setAttribute:function(k,v){at[k]=v},
    removeAttribute:function(k){delete at[k]},addEventListener:function(t,f){L.push(f)},click:function(){L.forEach(function(f){f()});}}; }
var MORE=A('/zone/','시도별로 자세히 보기 →',"track('home_cta',{to:'zone_hub'})");
var SUB=A('/monthly/','이달의 통계 한 화면으로 보기 →',"track('home_cta',{to:'monthly'})");
var document={querySelector:function(q){ return q==='#sec-score .tb-more a'?MORE:(q==='#sec-score .tb-sub a'?SUB:null); }};
var out=[];
function snap(){ out.push([MORE.getAttribute('href'),MORE.textContent,MORE.getAttribute('onclick'),SUB.getAttribute('href'),SUB.textContent]);
  MORE.click(); SUB.click(); }
scoreCta('weekly'); snap(); scoreCta('monthly'); snap(); scoreCta('supply'); snap(); scoreCta('weekly'); snap();
process.stdout.write(JSON.stringify({out:out,sent:sent}));
'''


def test_map_buttons_follow_the_map_mode():
    """home-1: 지도 아래 두 단추는 모드의 다음 행동이다 — 주간: 시군구 TOP 10(먹색, '#stats-market-week-rank')·이번 주 요약(/weekly/),
    월간: 이달의 통계(먹색)·시군구 월간 TOP 10('#stats-market-month-rank'), 공급: 손으로 쓴 HTML 그대로(되돌린다). to 값은 입구마다
    따로이고 snake_case 이며, 공급으로 돌아오면 원래 값(zone_hub·monthly)을 보낸다. mapMode 가 모드를 바꿀 때 부른다.

    변이(각각 실제로 확인): scoreCta 가 공급(C 없음)일 때 되돌리지 않고 돌아가면 셋째 상태가, 클릭 측정을 onclick 속성에 남긴 채(지우지 않고)
    두면 같은 클릭이 두 번(옛 to + 새 to) 잡혀, mapMode 에서 scoreCta(m) 호출을 빼면 마지막 단정이 빨개진다.
    픽스처: 저장소 scoreCta·SCORE_CTA 와 단추 둘의 합성 DOM(속성·클릭 처리기).
    """
    src = HS.home_source()
    const = re.search(r'^const SCORE_CTA=\{.*?^\};', src, re.M | re.S).group(0)
    got = _node(SCORE_DOM % {'fns': const + '\n' + _js_func(src, 'scoreCta')})
    w, mo, sup, w2 = got['out']
    assert w[:3] == ['#stats-market-week-rank', '시군구 상승·하락 TOP 10 보기', None] and w[3:] == ['/weekly/', '이번 주 요약 보기 →'], w
    assert mo[0] == '/monthly/' and mo[3] == '#stats-market-month-rank' and 'TOP 10' in mo[4], mo
    assert sup == ['/zone/', '시도별로 자세히 보기 →', None, '/monthly/', '이달의 통계 한 화면으로 보기 →'], sup
    assert w2 == w
    tos = [t for _, t in got['sent']]
    assert tos == ['score_week_rank', 'score_weekly', 'score_monthly', 'score_month_rank', 'zone_hub', 'monthly',
                   'score_week_rank', 'score_weekly'], tos
    assert all(re.match(r'^[a-z][a-z0-9_]*$', t) for t in tos)
    assert 'scoreCta(m);' in _js_func(src, 'mapMode')
    # 같은 주소로 가는 다른 입구와 to 값이 겹치지 않는다(test_home_cta 의 홈 뷰 값들)
    assert not {'score_week_rank', 'score_weekly', 'score_monthly', 'score_month_rank'} & set(
        re.findall(r"track\('home_cta',\{to:'([^']*)'\}\)", _index()))


def test_weekly_share_sits_after_the_main_action_and_is_not_yellow():
    """home-2: 주간 구역 순서 = h2 → (지난 방문 줄·'지도에서 보기'·요약 링크) → TOP 10(먹색) → 공유 둘. 공유는 renderWeeklyGrid 가
    #home-weekly-share(TOP 10 단추 아래)에 굽고, 카카오 단추는 노란 채움 없이 흰 바탕·먹선(큰 버튼 한 규칙)이며 카카오임은 아이콘이 말한다.

    변이(실제로 확인): index.html 의 #home-weekly-share 를 .hs-cta 앞으로 옮기면, renderWeeklyGrid 가 공유를 다시 상자(box) 안에 붙이면,
    .wg-sh-k 에 'background:#FEE500' 를 되살리면 빨개진다.
    """
    h = _index()
    sec = h[h.index('id="wk-h2"'):]
    sec = sec[:sec.index('</section>')]
    assert sec.index('id="home-weekly-grid"') < sec.index('<div class="hs-cta">') < sec.index('<div id="home-weekly-share"></div>')
    fn = _js_func(HS.home_source(), 'renderWeeklyGrid')
    assert "document.getElementById('home-weekly-share')" in fn and 'shBox.innerHTML=share' in fn
    assert "+(shBox?'':share)" in fn, '공유 상자가 있는데도 주간 상자 안에 공유를 또 붙인다'
    css = _css()
    k = _rule(css, '.wg-sh-k')
    assert 'background' not in k and 'FEE500' not in k.upper(), k
    assert '#FEE500' in fn, '카카오 아이콘(노란 네모)이 없다 — 카카오 단추임을 알 수 없다'


def test_home_reading_text_is_14px_and_the_title_leads():
    """home-3·6·12: 산출 방법 본문은 14px, 히어로 부제 하한 14px(두 줄 조건은 test_followup_texts), 히어로 제목은 이름표의 2배 이상
    (375·1280px), 홈 '최근 리포트' 제목은 다른 홈 구역 제목(.home-sec h2)과 같은 크기다(시도 리포트 '이 지역 글' 15px 는 그대로).

    변이(실제로 확인): .sc-how .body 를 13px 로, .hero-kick 을 옛 clamp(15px,4.5vw,24px) 로 되돌리면, #view-home .crecent h2 규칙을
    지우면 빨개진다.
    """
    css = _css()
    assert _px(_rule(css, '.sc-how .body')) >= READ_PX

    def clamp(rule, vw):
        lo, mid, hi = map(float, re.search(r'font-size:clamp\(([\d.]+)px,([\d.]+)vw,([\d.]+)px\)', rule).groups())
        return min(max(lo, mid * vw / 100), hi)
    kick, h1, sub = (_rule(css, s) for s in ('.home-hero .hero-kick', '.home-hero h1.hero-msg', '.home-hero .hero-sub'))
    for vw in (320, 375, 1280):
        assert clamp(h1, vw) >= 2 * clamp(kick, vw) - 0.5, (vw, clamp(h1, vw), clamp(kick, vw))
        assert clamp(sub, vw) >= READ_PX, vw
    assert _rule(css, '#view-home .crecent h2').split('font-size:')[1].split(';')[0] == \
        _rule(css, '.home-sec h2').split('font-size:')[1].split(';')[0]
    assert '15px' in _rule(css, '.crecent h2')


def test_home_quiz_buttons_have_no_emoji_and_cycle_text_has_no_count():
    """home-9·10: 홈 퀴즈 단추 셋에 컬러 이모지가 없고, 사이클 구역 문장은 고리 수를 말하지 않는다(아래 축약 도식은 칸 넷 — 고리 수 6은
    /cycle/ 안에서만).

    변이(실제로 확인): 부린이 단추에 '🐣 '를 되살리면, 문장을 '순환의 6개 고리입니다'로 되돌리면 빨개진다.
    """
    h = _index()
    home = h[h.index('<div id="view-home">'):h.index('<!-- ===== 통계보기 대시보드 ===== -->')]
    btns = re.findall(r'<a class="home-cta[^"]*" href="/(?:burini|investor|redev)-test/"[^>]*>([^<]*)</a>', home)
    assert len(btns) == 3, btns
    assert all(not re.search('[\U0001F000-\U0001FAFF☀-➿️]', b) for b in btns), btns
    cyc = re.search(r'<h2>집값은 왜 돌고 도는가</h2>\s*(?:<!--.*?-->\s*)?<p>([^<]*)</p>', home, re.S).group(1)
    assert not re.search(r'\d+\s*개\s*고리', cyc), cyc
