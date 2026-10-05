# -*- coding: utf-8 -*-
"""홈 데스크톱 배치 — 1024px 이상에서 히어로 아래 2단과 상단 내비(홈 마케팅 검수 C7·HERO-9, 2026-09-27).

재현하는 실제 상태: 09-26 까지 홈은 모든 폭에서 820px 단 하나였다. 1366px 창에서 좌우가 비었고, 주간 시세 격자는 공급
지도(예약 높이 786px) 아래 두 화면 밑에 있었다(HERO-9). 하단 탭바는 데스크톱에서도 화면 아래에 붙어 있었다.
바꾼 것: 1024px 이상에서만 왼쪽 = 공급 지도 구역, 오른쪽 = 이번 주 격자와 다음 발표일(주간 구역), 표 보기는 두 단을 다
쓴다. 하단 탭바는 같은 <nav class="bottomnav"> 를 CSS 로 위로 옮긴다(라벨·순서·주소가 정본 site_nav 와 저절로 같다).
1023px 이하는 규칙이 전부 꺼져 예전과 같다. 지도 예약 높이는 1px 간격 실측으로 폭을 따라가는 식이 됐다.

픽스처: 저장소 index.html·app.css·sido-geo.js(홈 마크업은 tools/home_src 로 읽는다). 브라우저 실측(1024·1280·1440px
2단·넘침 없음·CLS, 320~1440px 예약 높이 어긋남 0px)은 3차 배포 보고에 남겼다 — 여기서는 그 결과를 지키는 규칙을 고정한다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import site_nav as N  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
DESKTOP = 1024   # 요청서 C7: '1024px 이상에서'


def _css():
    return io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()


def _home():
    return HS.home_source()


def _index():
    s = _home()
    return s[:s.index('</html>') + len('</html>')]   # home_source 는 index.html 이 앞에 온다


def _media_blocks(css):
    """[(조건, 안쪽 CSS)] — 중괄호 짝으로 자른다."""
    out = []
    for m in re.finditer(r'@media\s*([^{]+)\{', css):
        i, depth = m.end(), 1
        while depth:
            depth += {'{': 1, '}': -1}.get(css[i], 0)
            i += 1
        out.append((m.group(1).strip(), css[m.end():i - 1]))
    return out


def _outside_media(css):
    out, i = [], 0
    for m in re.finditer(r'@media\s*[^{]+\{', css):
        if m.start() < i:
            continue
        out.append(css[i:m.start()])
        j, depth = m.end(), 1
        while depth:
            depth += {'{': 1, '}': -1}.get(css[j], 0)
            j += 1
        i = j
    out.append(css[i:])
    return re.sub(r'/\*.*?\*/', '', ''.join(out), flags=re.S)


def _desktop_css():
    blocks = [b for c, b in _media_blocks(_css()) if re.fullmatch(r'\(min-width:\s*%dpx\)' % DESKTOP, c)]
    assert blocks, 'app.css 에 @media(min-width:%dpx) 블록이 없다' % DESKTOP
    return re.sub(r'/\*.*?\*/', '', '\n'.join(blocks), flags=re.S)


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])%s\{([^}]*)\}' % re.escape(sel), css)
    assert m, 'CSS 규칙 %s 를 찾지 못했다' % sel
    return m.group(1)


def test_two_columns_hold_the_supply_map_and_this_weeks_grid_from_1024px_only():
    """1024px 이상: .home-duo 가 두 단 격자(왼쪽 가변 · 오른쪽 고정 폭)이고, 지도 구역은 왼쪽, 주간 구역은 오른쪽 첫 줄,
    표 보기에서는 지도 구역이 두 단을 다 쓰고 주간 구역은 그 아래로 내려간다. .home-duo 를 건드리는 규칙은 이 폭 밖에 없다
    (1023px 이하 변화 없음). 마크업: .home-duo 가 지도 구역과 주간 구역(격자·발표 머리줄이 든 구역) 둘만 감싼다.
    변이(각각 실제로 확인): 2단 블록의 폭을 900px 로 바꾸면(태블릿까지 2단) 첫 단정, 표 보기 예외(grid-column:1/-1)를 지우면
          표 단정, 여는 상자를 퀴즈 구역 뒤에서 닫으면(세 구역을 감쌈) 마크업 단정, .home-duo{display:grid} 를 미디어 밖에
          두면 '폭 밖 규칙 없음' 단정이 빨개진다.
    """
    d = _desktop_css()
    duo = _rule(d, '.home-duo')
    assert 'display:grid' in duo
    cols = re.search(r'grid-template-columns:\s*minmax\(0,\s*1fr\)\s+(\d+)px', duo)
    assert cols, duo
    assert int(cols.group(1)) // 4 >= 85, '오른쪽 단이 좁아 주간 격자 4열 칸이 85px 아래다: %s' % cols.group(1)
    assert 'grid-column:1' in _rule(d, '.home-duo>#sec-score') and 'grid-row:1' in _rule(d, '.home-duo>#sec-score')
    wk = _rule(d, '.home-duo>#sec-score~.home-sec')
    assert 'grid-column:2' in wk and 'grid-row:1' in wk
    assert 'grid-column:1/-1' in _rule(d, '.home-duo>#sec-score.vm-table')
    assert 'grid-column:1/-1' in _rule(d, '.home-duo>#sec-score.vm-table~.home-sec')
    assert '.home-duo' not in _outside_media(_css()), '.home-duo 규칙이 데스크톱 폭 밖에도 있다 — 1023px 이하가 바뀐다'
    for c, b in _media_blocks(_css()):
        if '.home-duo' in b:
            assert re.fullmatch(r'\(min-width:\s*%dpx\)' % DESKTOP, c), '.home-duo 가 %s 에도 걸린다' % c

    idx = _index()
    a = idx.index('<div class="home-duo">')
    b = idx.index('</div><!-- /.home-duo -->')
    inner = idx[a:b]
    secs = re.findall(r'<section class="([^"]*)"(?: id="([^"]*)")?', inner)
    assert [s[1] for s in secs] == ['sec-score', ''] and 'id="home-weekly-grid"' in inner and 'id="wk-h2"' in inner, secs
    assert inner.count('<section') == inner.count('</section>') == 2


RIGHT_COL = '.home-duo>#sec-score:not(.vm-table)~.home-sec '   # 두 단일 때의 주간 구역(오른쪽 단)


def test_first_screen_boxes_are_reserved_in_the_right_column():
    """주간 구역이 1024px 이상에서 첫 화면에 올라오므로, 부팅 때 채워지는 격자(빈 상자 → 그린 뒤 629.5px — 2026-09-28 작은 글씨 정리 전에는 718px)와 결론 h2(두 줄)의
    높이를 데스크톱 블록이 미리 잡는다(없으면 1024·1280·1440px 에서 아래 버튼이 밀려 CLS 0.014 — 실측). 발표 머리줄도 연휴 주
    문구가 360px 단에서 두 줄(운영 글꼴 367px)이라 두 줄을 잡는다.
    세 예약은 두 단일 때(오른쪽 360px 단)만 건다 — 표 보기(.vm-table)에서는 주간 구역이 전폭이라 결론·머리줄이 한 줄인데
    두 줄 예약이 남으면 제목 아래 47px·머리줄 아래 21px 가 빈다(묶음 M 검토 5, 1024·1280·1440px 실측).
    픽스처: 저장소 app.css 의 1024px 블록과 index.html 의 두 단 마크업(지도 구역 #sec-score 다음 형제가 주간 구역).
    값(630px 등)은 브라우저 실측이라 여기서 박지 않는다 — 규칙이 있고, 오른쪽 단에만 걸리고, 그 선택자가 실제 마크업의
    주간 구역을 가리키는지만 본다.
    변이(각각 실제로 확인): 격자 예약이나 h2 예약을 지우면, 머리줄 예약을 되살리면, 셋 중 하나의 선택자를 '.home-duo #wk-h2'처럼 표 보기까지
          덮는 옛 모양으로 되돌리면, 주간 구역을 지도 구역 앞으로 옮겨 '~' 형제 관계가 끊기면 빨개진다.
    """
    d = _desktop_css()
    assert re.search(r'min-height:\s*(\d+)px', _rule(d, RIGHT_COL + '#home-weekly-grid:empty')), '주간 격자 예약 높이가 없다'
    assert 'min-height' in _rule(d, RIGHT_COL + '#wk-h2')
    # 발표 머리줄(.hs-kicker)은 2026-10-03 대표 요청으로 뺐다 — 마크업에도 예약 규칙에도 없어야 한다(빈 자리 예약이 남으면 빈 줄이 된다)
    assert not re.search(re.escape(RIGHT_COL + '.hs-kicker') + r'\s*\{', d), '없어진 발표 머리줄의 예약 규칙이 남았다'
    # 표 보기까지 덮는 예약이 남아 있지 않다(두 단 밖에서도 걸리는 min-height)
    for sel, body in re.findall(r'(?:^|[}\s])([^{}]*?(?:#home-weekly-grid|#wk-h2|\.hs-kicker)[^{}]*)\{([^}]*)\}', d):
        if 'min-height' in body:
            assert sel.strip().startswith(RIGHT_COL.strip()), '%s 예약이 표 보기(전폭)에도 걸린다' % sel.strip()
    # 선택자가 가리키는 마크업: .home-duo 안에서 #sec-score 뒤 형제 구역에 머리줄·h2·격자가 있다
    idx = _index()
    inner = idx[idx.index('<div class="home-duo">'):idx.index('</div><!-- /.home-duo -->')]
    after = inner[inner.index('id="sec-score"'):]
    after = after[after.index('</section>'):]
    for k in ('id="wk-h2"', 'id="home-weekly-grid"'):
        assert re.search(r'<section class="home-sec"[^>]*>.*' + re.escape(k), after, re.S), '%s 가 지도 구역 뒤 형제 구역에 없다' % k


def test_top_nav_is_the_one_canonical_tabbar_moved_up_on_home_only():
    """1024px 이상 홈에서 하단 탭바를 상단 내비로: 새 내비를 따로 만들지 않고 같은 <nav class="bottomnav"> 를 위로 옮긴다 —
    그래서 라벨·순서가 정본(site_nav.TABS)과 같다. 규칙은 body.home-app 에만 걸려 app.css 를 쓰는 다른 페이지(시도
    리포트·소개 등)의 탭바는 그대로다. 본문은 내비 높이만큼 위를 비우고 아래 여백(하단 탭바 자리)은 없앤다.
    변이(각각 실제로 확인): body 의 home-app 표지를 지우면, 규칙에서 body.home-app 범위를 빼면(.bottomnav{top:0…} — 모든
          app.css 페이지가 바뀜), 본문 위 여백을 내비 높이와 다르게(40px) 두면, 홈에 두 번째 내비(상단용 복제)를 넣으면,
          건너뛰기 링크의 z-index 올림을 지우면 빨개진다.
    """
    idx = _index()
    assert re.search(r'<body class="[^"]*\bhome-app\b[^"]*">', idx), '홈 <body> 에 home-app 표지가 없다'
    navs = re.findall(r'<nav class="bottomnav">(.*?)</nav>', idx, re.S)
    assert len(navs) == 1 and '<nav class="topnav"' not in idx, '홈 탭바는 하나여야 한다(상단용 복제 금지)'
    labels = re.findall(r'<span>([^<]*)</span>', navs[0])
    assert tuple(labels) == N.LABELS, labels

    d = _desktop_css()
    nav = _rule(d, 'body.home-app .bottomnav')
    assert 'top:0' in nav and 'bottom:auto' in nav
    h = int(re.search(r'height:(\d+)px', nav).group(1))
    body = _rule(d, 'body.home-app')
    assert 'padding-bottom:0' in body and ('padding-top:%dpx' % h) in body, (body, h)
    assert 'flex-direction:row' in _rule(d, 'body.home-app .nav-btn')
    # 본문 건너뛰기 링크(.skip, top:8px)는 내비와 같은 z-index 라 나중에 오는 내비 밑에 깔린다 — 위로 올린다
    nav_z = int(re.search(r'\.bottomnav\{[^}]*z-index:(\d+)', _outside_media(_css())).group(1))
    assert int(re.search(r'z-index:(\d+)', _rule(d, 'body.home-app .skip')).group(1)) > nav_z, '건너뛰기 링크가 내비 밑에 깔린다'
    # 범위 밖(.bottomnav 전역)을 옮기는 규칙이 없다
    for c, b in _media_blocks(_css()):
        for sel, body_ in re.findall(r'(?:^|[}\s])([^{}]*?\.bottomnav)\{([^}]*)\}', re.sub(r'/\*.*?\*/', '', b, flags=re.S)):
            if 'top:0' in body_:
                assert 'body.home-app' in sel, '%s 에서 탭바를 범위 없이 위로 옮긴다: %s' % (c, sel)


def test_map_reserve_follows_the_map_geometry():
    """지도 예약 높이(#map-wrap:not([data-done]) — 3차 B3 로 :empty 대신 '아직 안 그림'에 건다): 528px 이하와 데스크톱 2단의 좁은
    구간(1024~1047px — 오른쪽 단 480px 때문에 왼쪽 단이 지도 상한 480px 보다 좁다)은 'K·vw − 고정분' 식이고 K 는 지도 도형의
    세로/가로 비(SIDO_GEO h/w ×100, 소수 첫째)다 — 지도 폭이 화면 폭을 따라 늘어 높이가 폭에 비례하기 때문이다. 나머지는 고정값.
    판정 카드는 2026-10-04 에 #map-wrap 밖(#agg-wrap)으로 나가 그 예약도 따로 있다(1px 간격 실측 320~1440px 어긋남 0.5px 이하).
    변이(각각 실제로 확인): 134.5vw 를 130vw 로 바꾸면 비율 단정, 카드 예약(#agg-wrap:empty)을 지우면 둘째 단정이, 데스크톱 블록에
          상한(max-width) 없이 예약을 덮으면 마지막 단정이 빨개진다. 픽스처: 저장소 sido-geo.js 좌표(지도를 다시 만들면 K 가 따라가야 한다).
    """
    geo = io.open(os.path.join(ROOT, 'sido-geo.js'), encoding='utf-8').read()
    g = json.loads(re.search(r'SIDO_GEO\s*=\s*(\{.*\})\s*;?\s*$', geo, re.S).group(1))
    k = round(g['h'] / g['w'] * 100, 1)
    css = _css()
    calcs = []
    for c, b in _media_blocks(css):
        for v in re.findall(r'#map-wrap:not\(\[data-done\]\)\{min-height:([^}]*)\}', b):
            calcs.append((c, v))
    fixed = re.findall(r'#map-wrap:not\(\[data-done\]\)\{min-height:([\d.]+)px\}', _outside_media(css))
    assert fixed, '기본(가장 넓은 폭) 예약 높이가 없다'
    assert re.search(r'#agg-wrap:empty\{min-height:[\d.]+px', _outside_media(css)), '판정 카드 자리(#agg-wrap) 예약이 없다'
    vw = [(c, v) for c, v in calcs if 'vw' in v]
    assert vw, '폭을 따라가는 예약 식이 없다'
    for c, v in vw:
        m = re.fullmatch(r'calc\(([\d.]+)vw - ([\d.]+)px\)', v)
        assert m and float(m.group(1)) == k, '%s 의 예약 식 %s — 지도 비 %.1fvw 와 다르다' % (c, v, k)
        assert int(re.search(r'max-width:\s*(\d+)px', c).group(1)) <= 1047, c
    assert all('max-width' in c for c, _ in calcs if 'min-width' in c), '데스크톱 블록이 상한 없이 지도 예약을 덮는다 — 2단 실측과 다르다'
