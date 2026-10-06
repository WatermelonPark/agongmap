# -*- coding: utf-8 -*-
"""/weekly/ 주간 시세 랜딩에 그 주의 답을 굽는다.

2026-09-15 고객 점검: 블로그에서 들어온 사람이 가장 먼저 닿는 페이지인데, 변동률이 스크립트로만
그려져 검색엔진과 카카오·네이버 링크 미리보기에 결론이 보이지 않았다. 답(시군구 TOP·서울 구)을
보려면 한 번 더 눌러야 했고, 광주·전남 타일은 판정 단위가 합쳐진 뒤에도 따로 나왔다.

페이지 뼈대(스타일·더 둘러보기·네비)는 손으로 관리하고, 아래 자리만 이 도구가 채운다.
  <!--WK:HEAD-->   … <!--/WK:HEAD-->    조사일·발표일·다음 발표·결론 제목·시도 타일
  <!--WK:ANSWER--> … <!--/WK:ANSWER-->  시군구 상승·하락 TOP 3, 서울 구별 요약
  <!--WK:SHARE-->  … <!--/WK:SHARE-->   공유 버튼(B8·VIRAL-1). 표식이 없으면 ANSWER 뒤에 자리를 낸다
  <!--WK:TABLE-->  … <!--/WK:TABLE-->   시군구 전체 표(C10②·SEO-2③). 표식이 없으면 SHARE 뒤에 자리를 낸다
  <meta name="description">, og:description, 'N개 시도' 문구
  구조화 데이터(Dataset)의 url, '숫자의 출처' 문단 — 홈 마케팅 검수 A4·A6(2026-09-27). 뼈대에 손으로 적혀 있던
  것을 생성기가 맡는다(Dataset url 이 '/#stats-market' 라 검색엔진에는 홈 주소였고, 출처 문단은 근거 없는
  '뉴스 기사보다 하루 빠르다'를 말했다). 손으로 되돌려도 다음 배치가 다시 고친다.

⚠️ 값은 전부 data.js 에서 온다. 시도 목록은 sido_zones.DISPLAY_ORDER, 시군구 이름은 index.html 의
   SGG_QNAME(홈 TOP 10 과 같은 표)을 쓴다. 반올림은 사이트 pv2r 와 같은 규칙이다 — 여기서 다르게
   반올림하면 같은 주 같은 지역이 홈과 이 페이지에서 끝자리가 갈린다.
⚠️ 전남광주 가격은 R-ONE 이 발표하는 통합 노드 값이다(update_adv_data 의 sido() 가 집는다).
   광주·전남을 우리가 합친 값이 아니다.

사용: python tools/make_weekly_page.py
"""
import html
import io
import json
import math
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import sido_zones as SZ  # noqa: E402
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import weekly_release as WR  # noqa: E402  (조사일·발표일·다음 발표 — 홈 주간 격자와 같은 규칙)
import site_nav as N  # noqa: E402  (하단 탭바 정본 — 홈 마케팅 검수 C2)
import blog_feed as BF  # noqa: E402  (최신 주간 해설 글 — 홈 주간 구역과 같은 pick, 홈 마케팅 검수 B5)
import page_share as PS  # noqa: E402  (공유 버튼 — 홈 마케팅 검수 B8)
import weekly_moves as WM  # noqa: E402  (방향 표지·시군구 순위 이동 정본 — 홈 마케팅 검수 B7)
import robots_meta as RM  # noqa: E402  (검색 로봇 메타 정본 — 홈 마케팅 검수 D2)

PAGE = os.path.join(ROOT, 'weekly', 'index.html')
SIDO = [z for z in SZ.DISPLAY_ORDER if z not in SZ.AGG]


def load():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'/\*ADV_DATA_START\*/const ADV=(\{.*?\});', s, re.S).group(1))
    h = HS.home_source()
    m = re.search(r'const SGG_QNAME=(\{.*?\});', h)
    if not m:
        raise SystemExit('index.html 에서 SGG_QNAME 을 찾지 못했다 — 시군구 이름표 위치가 바뀌었는지 볼 것')
    # 다음 발표가 연휴에 걸리는지는 배치가 특일정보 API 로 채운 ADV.holidays 로 본다(홈 JS 와 같은 입력).
    # 반환 모양(W, Q)을 바꾸지 않으려고 W 사본에 얹는다 — 합성 픽스처처럼 없으면 공휴일 없음으로 본다.
    W = dict(adv['weekly'], holidays=adv.get('holidays') or [])
    return W, json.loads(m.group(1))


def pv2r(v):
    """사이트 pv2r 와 같다: 절대값을 소수 둘째에서 반올림(half-up)하고 부호를 붙인다."""
    if v is None:
        return None
    r = (-1 if v < 0 else 1) * math.floor(abs(v) * 100 + 0.5) / 100
    return r + 0.0


def pv2(v):
    r = pv2r(v)
    if r is None:
        return '·'
    return ('+' if r > 0 else '') + '%.2f' % r


def sign(v):
    r = pv2r(v)
    return 'up' if r and r > 0 else ('dn' if r and r < 0 else '')


md = SZ.day_text   # '2026-09-28' → '9/28' — 읽는 자리의 날짜(날짜 두 단계, 정본은 sido_zones)


def pub(p):
    """조사기준일(월) → 발표일(목). make_weekly_share._pubdate 와 같은 규칙(정본은 weekly_release)."""
    return WR.status(p)['pub']


# '숫자의 출처' 문단. 예전 문장('호가·광고가 아닌 국가 통계라, 뉴스 기사보다 하루 빠르다')은 확인한 적 없는
# 비교였다 — 부동산원 주간 동향은 발표 당일 기사화되는 일이 많고, 배치가 멈춘 주에는 정면으로 틀린 말이
# 된다(TRUST-8). 우리가 확인할 수 있고 지킬 수 있는 사실만 적는다. 반영이 늦는 주는 위 날짜 줄이 스스로 알린다.
SOURCE_TEXT = ('한국부동산원 「전국주택가격동향조사」 아파트 매매·전세가격지수 변동률을 그대로 쓴다. '
               '호가·광고가가 아닌 국가 통계다. 매주 목요일 발표분을 발표 당일 반영하고, 반영이 늦어지면 '
               '맨 위 날짜 줄에 \'%s\'라고 적는다.' % WR.WAIT)


H1_WEEK = '이번 주'   # 결론 제목 머리. 발표가 늦은 주에는 스크립트가 이 말을 발표일로 바꾼다


def when_line(W, p):
    """머리줄 날짜 — '9/21 조사 · 9/24 발표 · 다음 발표 10/1(목)'과, 배치가 멈췄을 때 스스로 바꿔 적는 스크립트.

    페이지는 배치가 구울 때만 바뀐다. 배치가 멈추면 '다음 발표' 날짜가 지난 채로 남으므로, 그 날짜(휴일이면
    영업일로 민 날, weekly_release.status 의 due)가 다 지났는데도 이 페이지면 문구를 '반영 대기'로 바꾸고 제목의
    '이번 주'도 발표일로 바꾼다(TRUST-1③ — 홈 주간 구역 h2 와 같은 처리). 그래서 스크립트는 h1 뒤에 둔다.
    날짜 셈은 여기(파이썬)에서 끝내고 스크립트는 오늘(KST)과 문자열 비교만 한다 — 셈을 세 번 구현하지 않는다.
    """
    st = WR.status(p, holidays=W.get('holidays') or ())
    late = WR.when_text(dict(st, stale=True))
    script = ('<script>(function(){try{if(new Date(Date.now()+324e5).toISOString().slice(0,10)>%s){'
              'var e=document.getElementById(\'wk-when\');if(e)e.textContent=%s;'
              'var h=document.querySelector(\'header h1\'),t=h&&h.firstChild;'
              'if(t&&t.nodeType===3)t.nodeValue=t.nodeValue.replace(%s,%s);}}catch(x){}})();</script>'
              % (json.dumps(st['due']), json.dumps(late, ensure_ascii=False),
                 json.dumps(H1_WEEK, ensure_ascii=False), json.dumps(WR.pub_lead(dict(st, stale=True)), ensure_ascii=False)))
    return '<span id="wk-when">%s</span>' % html.escape(WR.when_text(st)), script


# ── 이번 주 결론 한 줄(홈 마케팅 검수 B1·IA-4, 2026-09-27) ─────────────────────────────────────────
# /weekly/ 제목(h1)·홈 첫 화면 '이번 주' 띠·홈 주간 구역 h2 가 **이 함수 하나**의 문장을 쓴다. split_data 가 결과를
# ADV.weekly.head 로 구워 싣고 홈은 읽기만 한다 — 홈 JS 가 같은 규칙을 다시 만들면(이중 구현) 한쪽만 고쳐질 때
# 두 화면이 다른 결론을 말한다(home-app.js 카드 문구와 같은 원칙). 일치는 test_home_first_screen 이 고정한다.
HEAD_UP, HEAD_DN, HEAD_FLAT = '가장 크게 올랐습니다', '가장 크게 내렸습니다', '시도 모두 보합입니다'


def conclusion(W):
    """최신 주의 결론: 표시값(pv2r) 기준 절대 변동이 가장 큰 시도(동률이면 표시 순서가 앞선 곳).

    돌려주는 것 {'p': 조사일, 'text': '경기 +0.23%, 가장 크게 올랐습니다', 'dir': 'up'|'dn'|'',
    'who': '경기', 'val': '+0.23%', 'verb': '가장 크게 올랐습니다'}. 모두 보합이면 who·val 이 None 이고
    text 는 '시도 모두 보합입니다'. 시도 값이 절반도 없거나 날짜 모양이 다르면 None — 반쯤 빈 결론을 싣지 않는다.
    """
    rows = W.get('rows') or []
    if not rows:
        return None
    row = rows[-1]
    p = row.get('p') or ''
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', p):
        return None
    regs = W.get('regions') or []
    ma = row.get('ma') or []
    val = {r: ma[i] for i, r in enumerate(regs) if i < len(ma)}
    sido = [(z, val[z]) for z in SIDO if val.get(z) is not None]
    if len(sido) < len(SIDO) // 2:
        return None
    best = max(sido, key=lambda x: abs(pv2r(x[1])))
    r = pv2r(best[1])
    if r == 0:
        return {'p': p, 'text': HEAD_FLAT, 'dir': '', 'who': None, 'val': None, 'verb': HEAD_FLAT, 'best': best}
    verb = HEAD_UP if r > 0 else HEAD_DN
    return {'p': p, 'text': '%s %s%%, %s' % (best[0], pv2(best[1]), verb), 'dir': sign(best[1]),
            'who': best[0], 'val': pv2(best[1]) + '%', 'verb': verb, 'best': best}


def head_payload(W):
    """split_data 가 ADV.weekly.head 로 싣는 모양(홈이 읽는 필드만). 결론을 못 만들면 None."""
    c = conclusion(W)
    return None if c is None else {k: c[k] for k in ('p', 'text', 'dir')}


def h1_html(c):
    """/weekly/ 제목. 결론 문장 앞에 '이번 주 아파트,'(발표가 늦은 주에는 스크립트가 '이번 주'를 발표일로 바꾼다)."""
    if c['who'] is None:
        return '%s 아파트,<br>%s' % (H1_WEEK, c['text'])
    return ('%s 아파트,<br><em class="%s">%s %s</em>, %s'
            % (H1_WEEK, c['dir'], html.escape(c['who']), c['val'], c['verb']))




# ── 전국 시군구 지도(2026-10-02 대표 요청 — 머리의 시도 타일을 걷고 그 자리에 둔다). 홈 sggMapSvg(home-app.js)의 거울이다:
# 같은 배치(NATION_TILE — 홈 소스에서 읽는다)·같은 색(mapColor, 만색 기준 WK_MAP_REF)·같은 글자(pv2)로 같은 마크업을 굽고,
# 둘이 한 글자도 다르지 않은지는 test_sgg_map 이 node 로 대조한다. 칸(이름·값)을 누르면 홈 통계 시장동향의 그 지역
# 주간 그래프(/#stats-market-week~코드 → applyHash → openTrendRegion). 이 페이지는 매매만 싣는다(홈 주간 구역과 같다).
MAP_HREF = '/#stats-market-week~%s'
MAP_CSS = ('.mm-scroll{overflow-x:auto;-webkit-overflow-scrolling:touch}'
           '.mm-scroll svg a{cursor:pointer}.mm-scroll svg a:hover>g>rect:first-child{stroke:#1b2426}'
           '.mm-scroll svg a:focus:not(:focus-visible){outline:none}.mm-scroll svg a:focus-visible>g>rect{stroke:#1b2426;stroke-width:1.6}'
           '.mm-swipe{display:none}@media(max-width:520px){.mm-swipe{display:inline}}')


def _home_const(src, name):
    m = re.search(r'^(?:const|var|let) %s=(.*?);\s*(?://.*)?$' % name, src, re.M)
    if not m:
        raise SystemExit('홈 소스에서 %s 를 찾지 못했다 — 시군구 지도 거울을 굽지 않는다' % name)
    return m.group(1)


def nation_tile(src=None):
    """홈 NATION_TILE({cols,rows,t:[[코드,이름,x,y,머리칸]]}) — JS 객체 글자라 키에 따옴표를 달아 읽는다."""
    raw = _home_const(src or HS.home_source(), 'NATION_TILE')
    return json.loads(re.sub(r'([{,])(cols|rows|t):', r'\1"\2":', raw))


def _js_num(x):
    """JS 가 숫자를 글자로 만드는 모양 — 정수는 소수점 없이(30, -1.5, 30.5)."""
    if float(x) == int(x):
        return str(int(x))
    return repr(float(x))


def _to_fixed3(x):
    """JS toFixed(3) — 두 배수 사이 한가운데면 큰 쪽(양수만 쓴다). 파이썬 '%.3f' 는 짝수 쪽이라 갈릴 수 있다."""
    from decimal import Decimal, ROUND_HALF_UP
    return str(Decimal(x).quantize(Decimal('0.001'), rounding=ROUND_HALF_UP))


def map_color(v, ref):
    """홈 mapColor 의 거울 — 글자가 0.00 인 칸은 무색, 아니면 원값 크기로 빨강·파랑 알파."""
    if v is None or pv2r(v) == 0:
        return '#e8ecea'
    a = min(abs(v) / (ref or 0.4), 1)
    al = _to_fixed3(0.14 + 0.72 * a)
    return ('rgba(224,86,74,%s)' if v > 0 else 'rgba(58,123,213,%s)') % al


def sgg_map_svg(vals, names, ref, href=None, tile=None):
    """홈 sggMapSvg(vals, {ref, names, href}) 와 같은 SVG. vals: 값 줄마다 {코드: 값}. href: 코드 → 주소(없으면 링크 없음)."""
    N = tile or nation_tile()
    n = len(vals)
    TW, NH, G = 30, 15, 2
    VH = 12 if n > 2 else 13
    rowH = NH + n * (VH + 1)
    W = N['cols'] * (TW + G) - G
    H = N['rows'] * (rowH + G) - G
    MAP_FS, MAP_MIN_PX = 9, 11
    minW = math.ceil((W + 4) * MAP_MIN_PX / MAP_FS)
    sv = ['<svg viewBox="-2 -2 %s %s" xmlns="http://www.w3.org/2000/svg" style="width:100%%;max-width:640px;min-width:%spx;'
          'margin:0 auto;display:block"%s aria-label="전국 시군구 변동률 지도">'
          % (W + 4, H + 4, minW, ' role="group"' if href else ' role="img"')]

    def grp(c):
        if c[0] == 'a':
            if c == 'a0':
                return 'a0'
            if c.startswith('a7'):
                return 'a7'
            if c.startswith('a8'):
                return 'a8'
            return 'a9'
        return c[:2]
    SI_PARENT = ['a80203', 'a80103', 'a80202', 'a80102', 'a80602', 'a80301', 'a80302', 'a80305']

    def cl(c):
        if c in SI_PARENT:
            return c
        for p in SI_PARENT:
            if c.startswith(p):
                return p
        return None

    def tcol(v):
        r = pv2r(v) or 0
        return '#8f2318' if r > 0 else ('#123c5c' if r < 0 else '#5e6f74')
    # 칸 설명의 앞말(홈 pre 의 거울) — 구는 소속 시(수원 장안), 그 밖은 소속 시도(서울 강남), 시도 머리 칸은 없음
    hn = {c: nm for c, nm, _x, _y, h in N['t'] if h and len(c) == 2}
    hn.update({c: nm for c, nm, _x, _y, _h in N['t'] if c in SI_PARENT})

    def pre(c):
        if len(c) <= 2:
            return ''
        k = cl(c)
        p = hn.get(k) if (k and k != c) else hn.get(grp(c))
        return p + ' ' if p else ''
    tb = int(math.floor(VH / 2 + 0.5)) + 3   # JS Math.round(반올림 위로) — 파이썬 round 는 짝수 쪽이다
    for c, nm, x, y, h in N['t']:
        px, py = x * (TW + G), y * (rowH + G)
        fit = (' textLength="%s" lengthAdjust="spacingAndGlyphs"' % (TW - 3)) if len(nm) >= 4 else ''
        g = ('<g transform="translate(%s,%s)">' % (px, py) +
             '<rect width="%s" height="%s" rx="4" fill="%s" stroke="%s"/>'
             % (TW, NH, '#1e2846' if h else ('#34456b' if c in SI_PARENT else '#eef1f8'), '#1e2846' if h else '#d6dced') +
             '<text x="%s" y="%s" text-anchor="middle" font-size="%s"%s font-weight="600" fill="%s">%s</text>'
             % (_js_num(TW / 2), NH - 4, MAP_FS, fit, '#fff' if (h or c in SI_PARENT) else '#1b2426', nm))
        for j, m in enumerate(vals):
            v = m.get(c)
            ry = NH + 1 + j * (VH + 1)
            g += ('<rect y="%s" width="%s" height="%s" rx="3" fill="%s" stroke="#d8dfdc"/>' % (ry, TW, VH, map_color(v, ref)) +
                  '<text x="%s" y="%s" text-anchor="middle" font-size="%s" font-weight="600" fill="%s">%s</text>'
                  % (_js_num(TW / 2), ry + tb, MAP_FS, tcol(v), pv2(v)))
        lab = '%s%s %s' % (pre(c), nm, ' · '.join('%s %s%%' % (names[j], pv2(m.get(c))) for j, m in enumerate(vals)))
        g += ('' if href else '<title>%s</title>' % lab) + '</g>'
        sv.append(('<a href="%s" data-code="%s" aria-label="%s">%s</a>' % (href(c), c, lab, g)) if href else g)
    pos_g = {(x, y): grp(c) for c, _, x, y, _h in N['t']}
    bl = []
    for c, _, x, y, _h in N['t']:
        g, px, py = grp(c), x * (TW + G), y * (rowH + G)
        J = _js_num
        if pos_g.get((x, y - 1)) != g:
            bl.append('M%s %sH%s' % (J(px - 1.5), J(py - 1.5), J(px + TW + 1.5)))
        if pos_g.get((x, y + 1)) != g:
            bl.append('M%s %sH%s' % (J(px - 1.5), J(py + rowH + 1.5), J(px + TW + 1.5)))
        if pos_g.get((x - 1, y)) != g:
            bl.append('M%s %sV%s' % (J(px - 1.5), J(py - 1.5), J(py + rowH + 1.5)))
        if pos_g.get((x + 1, y)) != g:
            bl.append('M%s %sV%s' % (J(px + TW + 1.5), J(py - 1.5), J(py + rowH + 1.5)))
    sv.append('<path d="%s" stroke="#5e6f74" stroke-width="1.4" fill="none" opacity=".9" pointer-events="none"/>' % ''.join(bl))
    pos_c = {(x, y): cl(c) for c, _, x, y, _h in N['t']}
    dl = []
    for c, _, x, y, _h in N['t']:
        k = cl(c)
        if not k:
            continue
        px, py = x * (TW + G), y * (rowH + G)
        J = _js_num
        if pos_c.get((x, y - 1)) != k:
            dl.append('M%s %sH%s' % (J(px + 0.5), J(py + 0.5), J(px + TW - 0.5)))
        if pos_c.get((x, y + 1)) != k:
            dl.append('M%s %sH%s' % (J(px + 0.5), J(py + rowH - 0.5), J(px + TW - 0.5)))
        if pos_c.get((x - 1, y)) != k:
            dl.append('M%s %sV%s' % (J(px + 0.5), J(py + 0.5), J(py + rowH - 0.5)))
        if pos_c.get((x + 1, y)) != k:
            dl.append('M%s %sV%s' % (J(px + TW - 0.5), J(py + 0.5), J(py + rowH - 0.5)))
    sv.append('<path d="%s" stroke="#34456b" stroke-width="0.8" stroke-dasharray="0.6 1" stroke-linecap="round" fill="none" '
              'opacity=".85" pointer-events="none"/>' % ''.join(dl))
    sv.append('</svg>')
    return ''.join(sv)


def week_map(W, src=None):
    """머리 지도: 시군구 최신 회차 매매 값 → (SVG, 조사일). 만색 기준은 홈 WK_MAP_REF 를 읽는다(한 상수)."""
    src = src or HS.home_source()
    S = W['sgg']
    srow = S['rows'][-1]
    v = {c: srow['ma'][i] for i, c in enumerate(S['codes']) if i < len(srow['ma'])}
    ref = float(_home_const(src, 'WK_MAP_REF'))
    return sgg_map_svg([v], ['매매'], ref, href=lambda c: MAP_HREF % c, tile=nation_tile(src)), srow['p']


def counts(vals):
    up = sum(1 for v in vals if pv2r(v) > 0)
    dn = sum(1 for v in vals if pv2r(v) < 0)
    return up, dn, len(vals) - up - dn


def count_text(total_label, vals):
    up, dn, flat = counts(vals)
    parts = ['%d곳 상승' % up, '%d곳 하락' % dn] + (['%d곳 보합' % flat] if flat else [])
    return '%s 중 %s' % (total_label, ', '.join(parts))


def top3(items):
    """items [(이름, 값)] → (오른 곳 상위 3, 내린 곳 상위 3). 순서는 홈 TOP 10 과 같다.

    홈은 값 내림차순 정렬 뒤 앞 10개·뒤 10개를 뒤집어 쓴다(안정 정렬). 여기서도 같은 정렬을 쓰되,
    '하락'에는 실제로 내린 곳만 싣는다 — 모두 오른 주에 가장 덜 오른 곳을 '하락'이라 적지 않는다.
    """
    arr = sorted(items, key=lambda x: -x[1])
    up = [x for x in arr if pv2r(x[1]) > 0][:3]
    dn = [x for x in reversed(arr) if pv2r(x[1]) < 0][:3]
    return up, dn


def rank_list(title, cls, items, empty):
    lis = ''.join('<li><span class="nm">%s</span><b class="%s">%s%%</b></li>'
                  % (html.escape(n), sign(v), pv2(v)) for n, v in items)
    if not lis:
        lis = '<li class="none">%s</li>' % empty
    return '<div class="rk"><h3 class="%s">%s</h3><ol>%s</ol></div>' % (cls, title, lis)


# ── 공유 카드 주소와 하단 탭(홈 마케팅 검수 A7·A5, 2026-09-27). 뼈대에 손으로 적혀 있던 것을 생성기가 맡는다.
# 공유 카드는 make_weekly_share 가 매주 **같은 이름**으로 덮어쓴다(감시 check_freshness 가 이 주소에서 조사일을 읽는다).
SITE = 'https://www.agongmap.co.kr'
# 카드 파일의 사이트 상대 경로 — 정본은 여기 하나다. make_weekly_share 는 이 경로(ROOT 아래)에 굽고, 이 페이지의
# og:image·twitter:image 는 SITE 뒤에 이 경로를 붙여 가리킨다. 두 생성기가 경로를 따로 적으면 한쪽만 바뀌어도
# 미리보기가 없는 파일을 가리키는데 아무것도 빨개지지 않았다(A7 검토 지적, test_weekly_share_version).
SHARE_REL = 'share/weekly-map.png'
SHARE_IMG = SITE + '/' + SHARE_REL
# 카드 크기(가로·세로 px). make_weekly_share 가 이 크기로 굽고, 공유 버튼의 카카오 피드가 이 비율로 싣는다.
# 뼈대의 og:image:width·height 와 같은지는 test_weekly_share_buttons 가 본다.
SHARE_SIZE = (900, 1130)
SHARE_SOURCE = 'weekly_share'   # 공유 링크의 utm_source(유입 장치) — 홈 주간 격자·/weekly/ 버튼이 같은 값
# 이 페이지가 켜는 하단 탭. 홈 '시세'(식별자 stats) 탭의 기본 화면이 주간 시세 지도라 이 페이지는 그 탭 아래에
# 있다(IA-6 1단계). 탭바 마크업·라벨은 site_nav 가 정본이다 — 뼈대의 손 탭바를 통째로 정본으로 갈아 끼우므로
# 탭 이름을 바꿔도(C2 '통계' → '시세') 이 페이지를 손으로 고칠 일이 없다.
NAV_TAB = 'stats'
NAV_ON = N.HREF[NAV_TAB]
# 데스크톱 머리 위 빈칸(백로그 36-9, 2026-10-06 대표 결정) — 머리 위 여백 52px 이 넓은 화면에서는 첫 줄 앞 빈 띠로 보였다.
# 720px 이상에서만 24px 로 줄인다(모바일은 그대로). 뼈대는 배치 산출물이라 생성기가 없으면 넣는다(put_nav).
HEAD_DESKTOP_CSS = '@media(min-width:720px){header{padding-top:24px}}'
NAV_ON_CSS = '.nav-btn.on{color:#fff}'   # 이 페이지는 공용 시트를 안 읽으므로 규칙을 같이 싣는다
_NAV_A = re.compile(r'<a class="nav-btn(?: on)?"(?: aria-current="page")? href="([^"]*)"')
_NAV_BLOCK = re.compile(r'<nav class="bottomnav">.*?</nav>', re.S)
_FOOTER_CSS = re.compile(r'((?:^|[}\s])footer\{[^}]*?font-size:)[\d.]+px')
_NAV_BTN_CSS = re.compile(r'((?:^|[}\s])\.nav-btn\{[^}]*?font-size:)[\d.]+px')
# 뼈대 CSS 주석의 옛 문장들 → 지금 문장. 앞의 것은 A5 이전, 뒤의 것은 A5(2026-09-27 1차 배포) 문장이다.
_NAV_NOTES_OLD = ('활성 탭 없음 — 주간 지도는 네 탭 어디에도 속하지 않는다(퀴즈 뷰와 같은 처리).',
                  "활성 탭은 '통계' — 홈 통계 탭의 기본 화면이 주간 시세다(생성기 put_nav 가 켠다, 2026-09-27).")
_NAV_NOTE = ("활성 탭은 '%s' — 홈 %s 탭의 기본 화면이 주간 시세다(생성기 put_nav 가 켠다, 2026-09-27)."
             % (N.LABEL[NAV_TAB], N.LABEL[NAV_TAB]))


def share_version(p):
    """주간 공유 카드의 판 = 그 카드 머리에 찍힌 발표일. make_weekly_share 도 이 함수로 날짜를 찍는다.

    카드 파일은 매주 같은 이름이라, 이미지 주소로 미리보기를 보관하는 카카오톡·네이버에는 지난주 지도가
    남는다(VIRAL-2). og:image 주소에 이 값을 쿼리(?v=)로 붙여 주마다 다른 주소로 만든다. 파일 이름에 넣지
    않은 이유: 매주 share/ 에 파일이 쌓이고, 감시가 조사일을 읽는 고정 주소도 바뀐다.
    """
    return pub(p)


PNG_SIG = b'\x89PNG\r\n\x1a\n'


def png_text(path):
    """PNG 파일의 tEXt 청크 → {키: 값}. 파일이 없거나 PNG 가 아니면 {}."""
    try:
        with open(path, 'rb') as f:
            raw = f.read()
    except OSError:
        return {}
    return png_text_bytes(raw)


def png_text_bytes(raw):
    """PNG 바이트의 tEXt 청크 → {키: 값}. PNG 가 아니면 {}.

    PIL 없이 읽는다 — 이 생성기와 감시(check_freshness.live_card_basis)는 pip 앞, 설치 없이 돈다. 두 코드가 이 함수
    하나로 카드 메타를 읽는다(전수 리뷰 통합 — 예전엔 같은 읽기를 두 벌 적었다). 청크는 [길이4][타입4][데이터][CRC4]
    배열이고 tEXt 데이터는 키와 값을 NUL 하나로 이은 것이다.
    """
    if raw[:8] != PNG_SIG:
        return {}
    out, i = {}, 8
    while i + 8 <= len(raw):
        n = int.from_bytes(raw[i:i + 4], 'big')
        typ = raw[i + 4:i + 8]
        if typ == b'IEND':
            break
        if typ == b'tEXt':
            k, _, v = raw[i + 8:i + 8 + n].partition(b'\x00')
            out[k.decode('latin-1')] = v.decode('latin-1')
        i += 12 + n
    return out


def card_version(root=None):
    """디스크에 **실제로 구워진** 주간 카드의 판(PNG 메타 agongmap-pub = 카드 머리의 발표일). 읽지 못하면 None."""
    return png_text(os.path.join(root or ROOT, *SHARE_REL.split('/'))).get('agongmap-pub') or None


def share_img(W, root=None):
    """og:image·twitter:image·공유 버튼 그림의 주소 — 카드?v=**카드가 실제로 그린 판**.

    예전엔 판을 데이터(최신 주차의 발표일)에서만 셈했다. 카드 생성기는 배치에서 게이트 뒤에 돌고 실패해도 경고로만
    넘어가므로, 카드가 안 구워진 회차엔 새 판 주소(?v=새 발표일)가 지난 카드를 가리킨 채 커밋됐다. 카카오톡·네이버는
    이미지 주소 단위로 미리보기를 보관하므로, 그때 긁힌 옛 그림이 새 판 주소에 붙어 그 주 내내 나갔다 — ?v= 가 막으려던
    바로 그 상태다(전수리뷰 #85). 이제 판은 카드 PNG 메타에서 읽는다: 카드가 실패하면 주소는 옛 판 그대로(그림과
    주소가 같은 판)이고, 카드가 구워지면 make_weekly_share 가 restamp_share 로 같은 회차 안에 주소를 새 판으로 고친다.
    카드 파일이나 메타가 없을 때만(저장소 밖 임시 폴더 등) 데이터의 발표일로 둔다.
    """
    v = card_version(root) or share_version(W['rows'][-1]['p'])
    return '%s?v=%s' % (SHARE_IMG, v)


_SHARE_IMG_RE = re.compile(re.escape(SHARE_IMG) + r'\?v=[0-9A-Za-z-]+')


def restamp_share(root=None):
    """카드를 구운 **뒤** 카드 주소의 판(?v=)을 카드 메타의 판으로 고쳐 쓴다 → 고친 파일 목록.

    페이지(/weekly/)와 홈 데이터(split_data 의 ADV.weekly.share)는 카드보다 먼저 구워지므로(카드는 pillow 가 깔리는
    게이트 뒤), 카드가 새로 구워진 회차엔 그 둘이 아직 지난 판을 가리킨다. 카드 생성기가 성공한 직후 이 함수를 불러
    같은 커밋 안에서 주소를 맞춘다. 판 말고는 아무것도 바꾸지 않는다.
    """
    root = root or ROOT
    v = card_version(root)
    if not v:
        return []
    names = [os.path.join('weekly', 'index.html'), 'data-core.js'] + sorted(
        f for f in (os.listdir(root) if os.path.isdir(root) else []) if re.match(r'^data-[\w-]+\.json$', f))
    done = []
    for rel in names:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            continue
        with io.open(path, encoding='utf-8', newline='') as f:
            old = f.read()
        new = _SHARE_IMG_RE.sub(SHARE_IMG + '?v=' + v, old)
        if new != old:
            with io.open(path, 'w', encoding='utf-8', newline='') as f:
                f.write(new)
            done.append(rel.replace(os.sep, '/'))
    return done


def share_campaign(p):
    """공유 링크의 회차(utm_campaign) — 'week_' + 발표일(YYYYMMDD). og:image 판(share_version)과 같은 날짜다.

    카카오톡은 페이지 주소 단위로 미리보기를 보관하므로(VIRAL-2) 링크 주소가 주마다 달라야 새로 긁어 간다.
    """
    return 'week_' + share_version(p).replace('-', '')


def share_payload(W, root=None):
    """주간 공유 내용 — /weekly/ 공유 버튼과 홈 주간 격자 공유 버튼(split_data → ADV.weekly.share)이 **이것 하나**를 쓴다.

    돌려주는 것: {'p': 조사일, 'ct': 'weekly', 'url': 공유 링크, 'title', 'text', 'img': 카드 주소(?v=발표일), 'w', 'h',
    'btn': 카카오 피드 버튼 글자}. 결론을 못 만드는 주(시도 값이 반도 없음)는 None — 반쯤 빈 카드를 보내지 않는다.
    """
    rows = W.get('rows') or []
    c = conclusion(W)
    if not rows or c is None:
        return None
    p = rows[-1]['p']
    regs = W.get('regions') or []
    ma = rows[-1].get('ma') or []
    i = regs.index('전국') if '전국' in regs else len(ma)
    nation = ma[i] if i < len(ma) else None
    text = c['text'] + ('' if nation is None else ' · 전국 %s%%' % pv2(nation))
    return {'p': p, 'ct': 'weekly', 'url': PS.link(SITE + '/weekly/', SHARE_SOURCE, share_campaign(p)),
            'title': '이번 주 아파트 시세 · %s 발표' % md(pub(p)), 'text': text,
            'img': share_img(W, root), 'w': SHARE_SIZE[0], 'h': SHARE_SIZE[1],
            'btn': '이번 주 시세 보기'}


def share_html(W, root=None):
    d = share_payload(W, root)
    return PS.block(d, '') if d else ''   # 버튼 위 권유 문구('단톡방에 보내 보세요')는 뺐다(2026-10-03 대표 요청 — 군더더기)


# ── 시군구 전체 표(C10②·SEO-2③, 2026-09-27) ───────────────────────────────────────────────────
# 예전엔 시군구 값이 TOP 3 여섯 곳만 HTML 에 있고 나머지는 홈 해시(/#stats-market)의 스크립트 지도로 넘겼다 — 검색엔진이
# 보는 이 페이지에는 '우리 동네' 답이 없었다. 홈 TOP 10 과 같은 대상(SGG_QNAME 에 이름이 있고 값이 있는 시군구)을 전부
# 굽는다. 순위·이동은 weekly_moves.rank_moves(홈 TOP 10 sggRanks 와 같은 규칙, 블로그도 같은 함수)가 낸다.
# 표는 접어 둔다(<details>) — 펼치지 않아도 HTML 에 있어 검색엔진은 읽고, 사람은 결론·TOP 3 뒤에 긴 표를 밀어내지 않는다.
TABLE_CSS = ('.sggt summary{cursor:pointer;font-size:15px;font-weight:600;color:var(--ink);padding:12px 0;'
             'border-top:1.5px solid var(--ink);border-bottom:1px solid var(--line)}'
             '.sggt .tbl{overflow-x:auto}'
             '.sggt table{width:100%;border-collapse:collapse;font-size:13.5px;font-variant-numeric:tabular-nums}'
             '.sggt thead th{font-size:12px;font-weight:600;color:var(--muted);text-align:right;padding:8px 5px;'
             'border-bottom:1.5px solid var(--ink);white-space:nowrap;cursor:pointer;user-select:none}'
             '.sggt thead th:first-child,.sggt tbody th{text-align:left}'
             '.sggt tbody th{font-weight:400;color:var(--ink);padding:7px 5px;border-bottom:1px solid var(--line)}'
             '.sggt td{padding:7px 5px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap;color:var(--ink2)}'
             '.sggt td.up{color:var(--up2)}.sggt td.dn{color:var(--dn2)}'
             '.sggt .note{font-size:12.5px;color:var(--muted);margin:10px 0 0}'
             # 본문 링크가 브라우저 기본 파랑이었다(백로그 36-9) — 사이트 링크 어휘(먹색 + 옅은 밑줄)
             '.note a:not([class]),p a:not([class]){color:var(--ink);text-decoration:underline;text-decoration-color:var(--line);text-underline-offset:3px}')


# 시군구 전체 표의 앵커. 시도 리포트 주간 표(make_sido_pages, D4)의 '전국 시군구 전체 표 →' 가 이 주소로 온다. 표가 접힌
# <details> 안이라 앵커로 들어오면(또는 같은 페이지에서 해시가 바뀌면) 펼치는 짧은 스크립트를 함께 싣는다.
TABLE_ID = 'sgg-table'
TABLE_URL = '/weekly/#' + TABLE_ID
TABLE_OPEN_JS = ('<script>(function(){function o(){if(location.hash==="#%s"){var d=document.getElementById("%s");'
                 'if(d){d.open=true;d.scrollIntoView();}}}o();addEventListener("hashchange",o);})();</script>' % (TABLE_ID, TABLE_ID))


def _pct_cell(v):
    k = sign(v)
    return '<td%s>%s</td>' % ((' class="%s"' % k) if k else '', pv2(v))


def table_html(W, Q):
    """시군구 전체 표 구역(스타일·정렬 스크립트 포함). 시군구 값이 없으면 빈 문자열."""
    import make_indicator_pages as I   # 정렬 스크립트 정본(SORT_SCRIPT). 쓸 때 가져온다
    S = W.get('sgg') or {}
    ranks = WM.rank_moves(S, Q)
    if not ranks:
        return ''
    srow = S['rows'][-1]
    je = srow.get('je') or []
    idx = {c: i for i, c in enumerate(S['codes'])}
    prev_p = S['rows'][-2]['p'] if len(S['rows']) > 1 else None
    trs = []
    for c, v, r, d in ranks:
        j = idx[c]
        jv = je[j] if j < len(je) else None
        trs.append('<tr><th scope="row">%s</th>%s%s<td>%d</td><td data-v="%s">%s</td></tr>'
                   % (html.escape(Q[c]), _pct_cell(v), _pct_cell(jv), r, '' if d is None else d, WM.move_text(d)))
    basis = '%s 조사 · %s 발표' % (md(srow['p']), md(pub(srow['p'])))
    how = ('순위는 매매 변동률 순(1 = 가장 많이 오른 곳)이고, 전주 대비는 %s 순위와의 차입니다(▲ 순위 상승).'
           % (('지난주(%s 조사)' % md(prev_p)) if prev_p else '지난주'))
    return '\n'.join([
        '<section class="sggt"><div class="wrap">',
        '  <h2>시군구 전체 표</h2>',
        '  <p class="sub">매매·전세가격 전주 대비(%%) · 시군구 %d곳 · %s</p>' % (len(ranks), basis),
        '  <details id="%s"><summary>시군구 %d곳 펼쳐 보기</summary>' % (TABLE_ID, len(ranks)),
        '  <div class="tbl"><table id="utable" aria-label="시군구 주간 매매·전세 변동률">'
        '<thead><tr><th scope="col">시군구</th><th scope="col" data-num>매매</th><th scope="col" data-num>전세</th>'
        '<th scope="col" data-num>순위</th><th scope="col" data-num>전주 대비</th></tr></thead><tbody>',
        '\n'.join(trs),
        '  </tbody></table></div>',
        '  <p class="note">%s 표두를 누르면 정렬합니다.</p>' % how,
        '  </details>',
        # RET-7: 두 주기를 느슨하게 잇는다 — 타일에 판정 칩을 붙이지 않고 한 줄로 시도 리포트 목록(/zone/)에 보낸다.
        # 가는 곳이 시도 목록이라 문구도 '시도별'이다('이 지역'이라 적으면 그 시군구의 리포트로 가는 줄 안다 — 3차 검토).
        '  <p class="note"><a href="/zone/">시도별 공급 판정 보기 →</a></p>',
        '</div></section>',
        '<style>%s</style>' % TABLE_CSS,
        I.SORT_SCRIPT,
        TABLE_OPEN_JS,
    ])


def put_share_image(s, W, root=None):
    url = share_img(W, root)
    s = put_meta(s, 'property', 'og:image', url)
    return put_meta(s, 'name', 'twitter:image', url)


def put_nav(s):
    """하단 탭바를 정본(site_nav)으로 갈아 끼우고 NAV_TAB(시세) 탭 하나만 켠다. 예전엔 켜진 탭이 없어 블로그 독자가
    착지하는 이 페이지가 사이트의 어느 메뉴인지 보이지 않았다(IA-6). 탭 라벨도 정본을 따른다(C2) — 옛 뼈대처럼
    켜짐 표시만 바꾸면 '통계' 라벨이 이 페이지에만 남는다. 공용 시트를 안 읽는 페이지라 켜진 색 규칙도 여기서 챙긴다."""
    blocks = _NAV_BLOCK.findall(s)
    if len(blocks) != 1 or _NAV_A.findall(blocks[0]).count(NAV_ON) != 1:
        raise SystemExit('weekly/index.html 하단 탭바에서 %s 탭을 찾지 못했다(%s)'
                         % (NAV_ON, [_NAV_A.findall(b) for b in blocks]))
    nav = N.bottomnav(NAV_TAB)
    if '\r\n' in s:
        nav = nav.replace('\n', '\r\n')
    s = _NAV_BLOCK.sub(lambda m: nav, s)
    if NAV_ON_CSS not in s:
        anchor = '.nav-btn svg{display:block}'
        if s.count(anchor) != 1:
            raise SystemExit('weekly/index.html 에서 하단 탭 스타일 자리를 찾지 못했다')
        s = s.replace(anchor, anchor + ('\r\n' if '\r\n' in s else '\n') + NAV_ON_CSS, 1)
    if N.NAV_FOCUS_CSS not in s:     # 탭바 키보드 초점(백로그 36-8) — 뼈대는 배치 산출물이라 여기서 넣는다
        s = s.replace(NAV_ON_CSS, NAV_ON_CSS + ('\r\n' if '\r\n' in s else '\n') + N.NAV_FOCUS_CSS, 1)
    if HEAD_DESKTOP_CSS not in s:    # 데스크톱 머리 위 빈칸(백로그 36-9)
        s = s.replace(NAV_ON_CSS, NAV_ON_CSS + ('\r\n' if '\r\n' in s else '\n') + HEAD_DESKTOP_CSS, 1)
    # 탭 라벨 글자 크기도 정본(site_nav.LABEL_PX — 홈 화면 글자 하한 13px, 2026-09-28)으로 맞춘다. 뼈대 <style> 은 배치 산출물이라
    # PR 로 고치지 않고 여기서 고쳐 쓴다(옛 뼈대 11.5px).
    rules = _NAV_BTN_CSS.findall(s)
    if len(rules) != 1:
        raise SystemExit('weekly/index.html 에서 하단 탭 글자 규칙(.nav-btn{…font-size…})을 찾지 못했다(%d개)' % len(rules))
    s = _NAV_BTN_CSS.sub(lambda m: m.group(1) + '%gpx' % N.LABEL_PX, s)
    # 푸터 글자도 13px 하한(백로그 36-3 — 옛 뼈대 12.5px). 뼈대는 배치 산출물이라 여기서 고쳐 쓴다.
    s = _FOOTER_CSS.sub(lambda m: m.group(1) + '%gpx' % N.FOOTER_PX, s)
    for old in _NAV_NOTES_OLD:
        s = s.replace(old, _NAV_NOTE)
    return put_desk(s)


_DESK_LINK = re.compile(r'<link rel="stylesheet" href="/desk\.css[^"]*"[^>]*>')
_BODY_TAG = re.compile(r'<body\b[^>]*>')


def put_desk(s):
    """데스크톱 틀(desk.css, 2026-10-06): 정본 링크(site_nav.desk_link — 주소에 내용 해시)를 싣고 <body data-desk="weekly">
    로 왼쪽 결론+지도·오른쪽 순위·표 배치를 고른다. 뼈대는 배치 산출물이라 여기서 갈아 끼운다(옛 해시 링크는 바꾼다)."""
    nl = '\r\n' if '\r\n' in s else '\n'
    link = N.desk_link()
    if _DESK_LINK.search(s):
        s = _DESK_LINK.sub(lambda m: link, s, count=1)
    else:
        if s.count('</head>') != 1:
            raise SystemExit('weekly/index.html 에서 </head> 를 찾지 못했다')
        s = s.replace('</head>', link + nl + '</head>', 1)
    if len(_BODY_TAG.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 <body> 를 찾지 못했다')
    return _BODY_TAG.sub(lambda m: N.desk_body('weekly'), s, count=1)


def build(W, Q):
    regs = W['regions']
    miss = [z for z in SZ.DISPLAY_ORDER if z not in regs]
    if miss:
        raise SystemExit('주간 계열에 없는 지역: %s — 결론에서 그 지역이 조용히 빠진다' % ', '.join(miss))
    row = W['rows'][-1]
    p = row['p']
    if not re.match(r'^\d{4}-\d{2}-\d{2}$', p or ''):
        raise SystemExit('주간 최신 회차 날짜 형식이 다르다: %r' % p)
    val = {r: row['ma'][i] for i, r in enumerate(regs)}
    sido = [(z, val[z]) for z in SIDO if val.get(z) is not None]
    if len(sido) < len(SIDO) // 2:
        raise SystemExit('시도 값이 %d곳뿐이다 — 반쯤 빈 결론을 굽지 않는다' % len(sido))
    nation = val.get('전국')
    survey, release = md(p), md(pub(p))
    datestr = '%s 조사 · %s 발표' % (survey, release)
    when, stale_js = when_line(W, p)

    # ── 결론 한 줄: 규칙은 conclusion() 하나 — 홈 띠·홈 주간 구역 h2 와 같은 문장이다(B1·IA-4)
    c = conclusion(W)
    best = c['best']
    h1 = h1_html(c)
    # 머리에는 광역(시도) 단위를 싣지 않는다 — 시도 타일·방향 표지·'방향이 바뀐 곳' 줄·시도 집계 리드 문장('시도 16곳 중 …')을
    # 모두 걷고 결론 제목과 시군구 지도만 둔다(2026-10-02·10-03 대표 요청). 뼈대 <style> 은 손으로 관리하는 자리라 지도
    # 규칙(MAP_CSS)은 HEAD 표식 안에 싣는다(배치가 매주 다시 쓴다).
    svg, sp = week_map(W)
    cap_when = '' if sp == p else ' · %s 조사 기준' % md(sp)
    head = '\n'.join([
        '  <p class="eyebrow"><span class="wk-label">%s</span> · %s · 한국부동산원 주간 통계</p>'
        % (WR.week_label(p, year=True), when),
        '  <h1>%s</h1>' % h1,
        '  ' + stale_js,
        '  <div class="minimap">',
        '    <div class="mm-scroll">%s</div>' % svg,
        '    <div class="mm-cap"><span><i style="background:#e0564a"></i>상승</span>'
        '<span><i style="background:#3a7bd5"></i>하락</span><span>시군구 매매가격 전주 대비%s</span>'
        '<span>지역을 누르면 주간 그래프<span class="mm-swipe"> · 옆으로 밀어 전체 보기</span></span>'
        '<a class="go" href="/#stats-market">TOP 10 →</a></div>' % cap_when,
        '  </div>',
        '  <style>%s</style>' % MAP_CSS,
    ])

    # ── 시군구 TOP 3 (홈 TOP 10 과 같은 대상: SGG_QNAME 에 이름이 있고 값이 있는 곳)
    S = W['sgg']
    srow = S['rows'][-1]
    sgg = [(Q[c], srow['ma'][i]) for i, c in enumerate(S['codes'])
           if c in Q and i < len(srow['ma']) and srow['ma'][i] is not None]
    if len(sgg) < 10:
        raise SystemExit('시군구 값이 %d곳뿐이다 — TOP 3 를 굽지 않는다' % len(sgg))
    su, sd = top3(sgg)
    sgg_note = '매매가격 전주 대비 · 시군구 %d곳' % len(sgg)
    if srow['p'] != p:
        sgg_note += ' · %s 조사 기준' % md(srow['p'])

    # ── 서울 구별
    se = W['seoul']
    serow = se['rows'][-1]
    gu = [(g, serow['ma'][i]) for i, g in enumerate(se['regions'])
          if i < len(serow['ma']) and serow['ma'][i] is not None]
    gu_up, gu_dn = top3(gu)
    gu_text = count_text('서울 %d개 구' % len(gu), [v for _, v in gu]) + '.'
    if serow['p'] != p:
        gu_text += ' (%s 조사 기준)' % md(serow['p'])

    answer = '\n'.join([
        '<section class="ans"><div class="wrap">',
        '  <h2>시군구 상승·하락 TOP 3</h2>',
        '  <p class="sub">%s · %s</p>' % (sgg_note, datestr),
        '  <div class="rk2">%s%s</div>' % (
            rank_list('▲ 상승', 'up', su, '이번 주 오른 시군구가 없다'),
            rank_list('▼ 하락', 'dn', sd, '이번 주 내린 시군구가 없다')),
        '  <h2 class="h2-gap">서울 구별</h2>',
        '  <p class="sub">%s</p>' % gu_text,
        '  <div class="rk2">%s%s</div>' % (
            rank_list('▲ 상승', 'up', gu_up, '이번 주 오른 구가 없다'),
            rank_list('▼ 하락', 'dn', gu_dn, '이번 주 내린 구가 없다')),
        '  <a class="cta" href="/#stats-market">전체 TOP 10 · 시군구 지도 보기</a>',
        '</div></section>',
    ])

    desc_bits = ['%s 기준 이번 주 아파트 매매가격은' % datestr]
    desc_bits.append(('전국 %s%%, ' % pv2(nation) if nation is not None else '')
                     + ('%s %s%%로 %s.' % (best[0], pv2(best[1]), '가장 크게 올랐다' if pv2r(best[1]) > 0 else '가장 크게 내렸다')
                        if pv2r(best[1]) != 0 else '시도 모두 보합이다.'))
    if su:
        desc_bits.append('시군구 상승 1위 %s %s%%%s.' % (su[0][0], pv2(su[0][1]),
                         (', 하락 1위 %s %s%%' % (sd[0][0], pv2(sd[0][1]))) if sd else ''))
    desc = ' '.join(desc_bits) + ' 한국부동산원 주간 통계로 전국 시군구·서울 구별 변동률을 본다.'
    # 전국 값이 없는 주(R-ONE 부분 응답)엔 desc·리드·공유 문구처럼 전국 조각을 뺀다 — '전국 ·%' 를 굽지 않는다(전수리뷰 #29).
    og = '%s · %s%s %s%%. 시군구·서울 구별 변동률 지도.' % (
        datestr, ('전국 %s%%, ' % pv2(nation)) if nation is not None else '', best[0], pv2(best[1]))
    return head, answer, desc, og


def ensure_block(s, name, after, nl):
    """표식 구간 WK:name 이 없으면 WK:after 구간 바로 뒤에 빈 구간을 만든다 — 뼈대(생성 페이지)를 PR 로 고치지 않고
    생성기가 첫 배치에서 자리를 낸다(생성 페이지를 PR 에 싣지 않는 규칙. 뼈대 CSS 를 채우는 put_nav 와 같은 방식)."""
    if '<!--WK:%s-->' % name in s:
        return s
    end = '<!--/WK:%s-->' % after
    if s.count(end) != 1:
        raise SystemExit('weekly/index.html 에 %s 가 %d개다 — WK:%s 자리를 낼 수 없다' % (end, s.count(end), name))
    return s.replace(end, end + nl + '<!--WK:%s-->' % name + nl + '<!--/WK:%s-->' % name, 1)


def put(s, name, body, nl):
    pat = re.compile(r'(<!--WK:%s-->)(.*?)(<!--/WK:%s-->)' % (name, name), re.S)
    n = len(pat.findall(s))
    if n != 1:
        raise SystemExit('weekly/index.html 에 WK:%s 표식이 %d개다 — 1개여야 한다' % (name, n))
    return pat.sub(lambda m: m.group(1) + nl + body.replace('\n', nl) + nl + m.group(3), s)


def put_meta(s, key, attr, text):
    pat = re.compile(r'(<meta %s="%s" content=")[^"]*(">)' % (key, re.escape(attr)))
    if len(pat.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 %s 메타를 찾지 못했다' % attr)
    return pat.sub(lambda m: m.group(1) + html.escape(text, quote=True) + m.group(2), s)


def put_dataset_url(s):
    """구조화 데이터 Dataset 의 url 을 이 페이지(canonical)로. 예전엔 '/#stats-market' 이라 검색엔진에는 홈
    주소('/')였다 — 주간 시세 검색어를 홈과 나눠 가지면서 정작 이 페이지를 가리키지 않았다(SEO-2①)."""
    canon = re.findall(r'<link rel="canonical" href="([^"]+)">', s)
    if len(canon) != 1:
        raise SystemExit('weekly/index.html 에서 canonical 을 찾지 못했다')
    # [^{}] — Dataset 자신의 url 만 잡는다. '.*?' 였으면 Dataset 의 url 줄이 빠졌을 때 그 뒤 중첩 객체(creator 등)의
    # url 을 조용히 덮어쓰고 개수 검사(==1)도 통과했다(1차 배포 검토). 이제는 못 찾아 SystemExit 로 드러난다.
    pat = re.compile(r'("@type":\s*"Dataset",[^{}]*?"url":\s*")[^"]*(")', re.S)
    if len(pat.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 Dataset url 을 찾지 못했다 — 구조화 데이터 모양이 바뀌었는지 볼 것')
    return pat.sub(lambda m: m.group(1) + canon[0] + m.group(2), s)


def put_source(s):
    pat = re.compile(r'(<h2>숫자의 출처</h2>\s*<p>)(.*?)(</p>)', re.S)
    if len(pat.findall(s)) != 1:
        raise SystemExit("weekly/index.html 에서 '숫자의 출처' 문단을 찾지 못했다")
    return pat.sub(lambda m: m.group(1) + SOURCE_TEXT + m.group(3), s)


# ── 검색어 정렬(홈 마케팅 검수 B4·SEO-3①·SEO-4, 2026-09-27) ────────────────────────────────────────
# title 이 생성기가 안 쓰는 고정 문구('이번 주 아파트 시세 지도…')라, 배치가 멈추면 검색 결과에 '이번 주' 제목 아래 지난
# 발표가 보였고 사람들이 실제로 치는 '주간아파트가격동향'·'9월 셋째 주'가 제목에 없었다. 블로그 주간 글 제목 라벨과 같은
# 말(TITLE_KW)과 같은 주차 서수(weekly_release.week_label)를 굽는다 — 블로그가 링크로 보내는 페이지가 같은 주를 같은 이름으로
# 부른다. 연도를 붙여 갱신이 늦어도 '날짜가 박힌 지난주'로 보이게 한다. og:title·twitter:title·JSON-LD name 도 같은 값.
TITLE_KW = '주간 아파트가격 동향'   # 한국부동산원 보도자료 이름 — make_naver_post 주간 글 제목 라벨도 이 값을 쓴다


def titles(p):
    """(title, og:title) — '주간 아파트가격 동향 2026년 9월 셋째 주 | 아파트 시세 지도 | 아공맵'."""
    lab = '%s %s' % (TITLE_KW, WR.week_label(p, year=True))
    return '%s | 아파트 시세 지도 | 아공맵' % lab, '%s · 전국·서울 아파트 시세 지도' % lab


def put_titles(s, p):
    title, og = titles(p)
    pat = re.compile(r'(<title>)[^<]*(</title>)')
    if len(pat.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 <title> 을 찾지 못했다')
    s = pat.sub(lambda m: m.group(1) + html.escape(title, quote=False) + m.group(2), s)
    s = put_meta(s, 'property', 'og:title', og)
    s = put_meta(s, 'name', 'twitter:title', og)
    # JSON-LD WebPage 자신의 name([^{}] — 중첩 객체 isPartOf·about 의 name 은 건드리지 않는다)
    pat = re.compile(r'("@type":\s*"WebPage",[^{}]*?"name":\s*")[^"]*(")', re.S)
    if len(pat.findall(s)) != 1:
        raise SystemExit('weekly/index.html 에서 WebPage name 을 찾지 못했다')
    return pat.sub(lambda m: m.group(1) + og.replace('\\', '\\\\').replace('"', '\\"') + m.group(2), s)


def put_ld_dates(s, pub_iso):
    """JSON-LD WebPage 에 발표일을 datePublished·dateModified 로(SEO-4). 이 페이지는 발표마다 새 판이 되므로 둘 다 발표일이다.
    뼈대에 없으면 WebPage 의 @type 줄 뒤에 넣고, 있으면 값만 바꾼다(zone·monthly·moveins·cycle 은 이미 있었다)."""
    for key in ('dateModified', 'datePublished'):   # 넣을 때는 @type 바로 뒤에 차례로 끼우므로 역순
        pat = re.compile(r'("%s":\s*")[^"]*(")' % key)
        n = len(pat.findall(s))
        if n == 1:
            s = pat.sub(lambda m: m.group(1) + pub_iso + m.group(2), s)
            continue
        if n > 1:
            raise SystemExit('weekly/index.html 에 %s 가 %d개다' % (key, n))
        at = re.compile(r'("@type":\s*"WebPage",)([ \t]*\r?\n[ \t]*)')
        if len(at.findall(s)) != 1:
            raise SystemExit('weekly/index.html 에서 JSON-LD WebPage 를 찾지 못했다')
        s = at.sub(lambda m: m.group(1) + m.group(2) + '"%s": "%s",' % (key, pub_iso) + m.group(2), s, 1)
    return s


# ── 해설 글(네이버 블로그) 칸(홈 마케팅 검수 B5·RET-4·SEO-8, 2026-09-27) ──────────────────────────────────
# 최신 주간 글(blog_feed.pick — 홈 주간 구역과 같은 선택·같은 말)과 블로그 첫 화면 링크를 '더 둘러보기' 앞에 굽는다.
# 뼈대에 표식이 없으면 이 생성기가 넣는다(뼈대는 배치 산출물이라 손으로 커밋하지 않는다). 글을 못 골랐으면 글 줄만 빠진다.
_BLOG_ANCHOR = re.compile(r'(<section><div class="wrap">\s*<h2>더 둘러보기</h2>)')
_BLOG_MARK = re.compile(r'(<!--WK:BLOG-->)(.*?)(<!--/WK:BLOG-->)', re.S)


# 클릭 측정: 이 페이지에는 홈의 track() 이 없어, 다른 생성 페이지(시도 리포트 공유·월간 view)처럼 gtag 이벤트를 직접
# 보낸다. 이벤트 이름 blog_link, to = weekly_post(최신 글)·weekly_home(블로그 첫 화면). GA 차단·제외 기기에서는 조용히 넘어간다.
def _track(to):
    return ' onclick="try{gtag(\'event\',\'blog_link\',{to:\'%s\'})}catch(e){}"' % to


def blog_html(b):
    rows = []
    if b:
        # 홈 해설 카드와 같은 두 말 — 결론(head)을 이름으로, '지난주 해설 · 네이버 블로그 9/27'(meta)을 곁말로(2026-10-03)
        rows.append('    <a href="%s" target="_blank" rel="noopener"%s>%s<span>%s</span></a>'
                    % (html.escape(b['url']), _track('weekly_post'), html.escape(b['head']), html.escape(b['meta'])))
    if BF.BLOG_HOME:
        rows.append('    <a href="%s" target="_blank" rel="noopener"%s>%s<span>%s</span></a>'
                    % (BF.BLOG_HOME, _track('weekly_home'), BF.HOME_TEXT, BF.LABEL))
    if not rows:
        return ''
    return '\n'.join(['<section class="blog"><div class="wrap">', '  <h2>해설 글</h2>', '  <div class="links">']
                     + rows + ['  </div>', '</div></section>'])


def put_blog(s, W):
    nl = '\r\n' if '\r\n' in s else '\n'
    if '<!--WK:BLOG-->' not in s:
        m = _BLOG_ANCHOR.findall(s)
        if len(m) == 1:
            s = _BLOG_ANCHOR.sub(lambda x: '<!--WK:BLOG-->' + nl + '<!--/WK:BLOG-->' + nl + nl + x.group(1), s, 1)
        elif s.count('</main>') == 1:
            s = s.replace('</main>', '<!--WK:BLOG-->' + nl + '<!--/WK:BLOG-->' + nl + '</main>', 1)
        else:
            raise SystemExit('weekly/index.html 에서 해설 글 칸을 넣을 자리를 찾지 못했다')
    b = BF.pick(BF.read(), pub(W['rows'][-1]['p']))
    body = blog_html(b)
    if not body:   # 블로그 주소를 못 만든 경우(blog_feed.BLOG_HOME None) — 칸을 비운다
        return _BLOG_MARK.sub(lambda m: m.group(1) + nl + m.group(3), s, 1)
    return put(s, 'BLOG', body, nl)


def render(s, W, Q, root=None):
    """root: 공유 카드를 읽을 저장소 뿌리(시험이 임시 폴더를 준다). 없으면 ROOT."""
    nl = '\r\n' if '\r\n' in s else '\n'
    head, answer, desc, og = build(W, Q)
    s = put(s, 'HEAD', head, nl)
    s = put(s, 'ANSWER', answer, nl)
    # 공유 버튼(B8)·시군구 전체 표(C10②) — 표식이 없던 뼈대에는 ANSWER 뒤에 자리를 낸다
    s = put(ensure_block(s, 'SHARE', 'ANSWER', nl), 'SHARE', share_html(W, root), nl)
    s = put(ensure_block(s, 'TABLE', 'SHARE', nl), 'TABLE', table_html(W, Q), nl)
    s = put_meta(s, 'name', 'description', desc)
    s = put_meta(s, 'property', 'og:description', og)
    s = put_dataset_url(s)
    s = put_source(s)
    p = W['rows'][-1]['p']
    s = put_titles(s, p)               # title·og:title·twitter:title·WebPage name 에 연도·주차(B4)
    s = put_ld_dates(s, pub(p))        # JSON-LD 발표일(B4)
    # 시도 수는 모델에서 센다(CLAUDE.md 데이터 원칙). '전국 16개 시도'가 통합 뒤에도 남는 종류의 결함.
    # ⚠️ put_blog **앞에서** 한다 — 해설 칸은 RSS 에서 온 남의 글 제목이라, 뒤에서 치환하면 '5개 시도만 올랐습니다' 같은
    #    제목을 '16개 시도만'으로 고쳐 인용했다(전수리뷰 #26). BLOG 구간은 put_blog 가 매번 통째로 다시 쓰므로 여기서
    #    지난 회차 제목이 치환돼 있어도 남지 않는다.
    s = re.sub(r'(?<!\d)\d+개 시도', '%d개 시도' % len(SIDO), s)
    s = put_blog(s, W)                 # 해설 글(네이버 블로그) 칸(B5)
    s = put_share_image(s, W, root)   # og:image·twitter:image 에 카드가 그린 판(A7·전수리뷰 #85)
    s = put_nav(s)              # 하단 탭바 정본·'시세' 탭 켜기(A5·C2)
    s = RM.ensure(s)            # 검색 로봇 메타 max-image-preview:large(D2) — 뼈대에 없으면 viewport 뒤에 넣는다
    return s


def main():
    W, Q = load()
    s = io.open(PAGE, encoding='utf-8', newline='').read()
    out = render(s, W, Q)
    if out != s:
        io.open(PAGE, 'w', encoding='utf-8', newline='').write(out)
        print('wrote weekly/index.html (%s)' % W['rows'][-1]['p'])
    else:
        print('weekly/index.html 변경 없음 (%s)' % W['rows'][-1]['p'])


if __name__ == '__main__':
    main()
