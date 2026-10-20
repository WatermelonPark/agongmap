# -*- coding: utf-8 -*-
"""데스크톱 틀(desk.css) — 1024px 이상에서 모든 탭바 페이지가 같은 상단 내비와 화면별 넓은 배치를 쓴다(2026-10-06 대표 결정
'데스크톱 전체 개편, 권장안').

재현하는 실제 상태(2026-10-06 실측, 1280px): 홈(#stats·#zones 포함)만 상단 내비·2단이었고, 시도 리포트·/weekly/·/monthly/·
/cycle/·지표·FAQ·소개·퀴즈는 하단 탭바와 516~832px 한 단이라 홈에서 리포트로 들어가면 메뉴가 아래로 내려갔다.
바꾼 것: 규칙은 루트 desk.css 하나, 싣는 글자는 site_nav.desk_link() 하나(주소에 내용 해시), 배치는 <body data-desk="종류">.

이 파일의 시험은 배치·CI 처럼 생성기를 먼저 돌린 저장소에서 돈다(test_site_nav 와 같다).

변이(각각 실제로 확인):
  · 손 페이지 하나(about/index.html)에서 desk 링크를 지우거나 옛 해시(?v=00000000)로 두면 → 링크 시험 빨강.
  · 손 페이지 <body> 의 data-desk 를 지우거나 없는 종류('wid')로 두면 → 링크 시험 빨강.
  · desk.css 에 범위 없는 규칙(.bottomnav{top:0})을 더하면 → 범위 시험 빨강(표지 없는 페이지까지 바뀐다).
  · make_weekly_page.put_desk 를 아무것도 안 하게 하면, make_indicator_pages.fill 의 __DESKLINK__ 치환을 지우면 → 생성기 시험 빨강.
  · /cycle/ 목차의 앵커 하나를 없는 id 로 바꾸면, FAQ 에서 DTOC_JS 를 지우면 → 목차 시험 빨강.
  · desk.css 목차 글자를 12px 로 내리면 → 글자 하한 시험 빨강.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_monthly_page as MM  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import site_nav as N  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SKIP_DIRS = ('drafts', 'logs', 'node_modules')
DESK_LINK = re.compile(r'<link rel="stylesheet" href="/desk\.css[^"]*"[^>]*>')
BODY = re.compile(r'<body\b([^>]*)>')


def _pages():
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = [x for x in dirs if not x.startswith('.') and x not in SKIP_DIRS]
        for f in files:
            if f.endswith('.html'):
                rel = os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/')
                yield rel, io.open(os.path.join(d, f), encoding='utf-8').read()


def _css():
    return re.sub(r'/\*.*?\*/', '', io.open(N.DESK_CSS, encoding='utf-8').read(), flags=re.S)


def test_every_tabbar_page_loads_the_canonical_desk_sheet_and_picks_a_layout():
    """탭바가 있는 모든 페이지가 정본 링크(현재 해시) 하나와 <body data-desk="종류"> 를 갖는다. 탭바가 없는 페이지(퀴즈 점수
    공유 페이지·통합 안내)는 desk.css 를 싣지 않는다 — 실어도 규칙이 body[data-desk] 에만 걸리지만 쓸데없는 요청이다."""
    want = N.desk_link()
    bad, seen = {}, []
    for rel, html in _pages():
        has_nav = '<nav class="bottomnav">' in html
        links = DESK_LINK.findall(html)
        if not has_nav:
            if links:
                bad[rel] = 'desk.css 를 싣는데 탭바가 없다'
            continue
        seen.append(rel)
        body = BODY.findall(html)
        kind = re.search(r'\bdata-desk="([^"]*)"', body[0]) if len(body) == 1 else None
        if links != [want]:
            bad[rel] = '링크 %s (정본 %s)' % (links, want)
        elif not kind or kind.group(1) not in N.DESK_KINDS:
            bad[rel] = '<body> 데스크톱 배치 %s' % (kind and kind.group(1))
    assert 'index.html' in seen and 'cycle/index.html' in seen and any(p.startswith('zone/') for p in seen), seen
    assert not bad, '데스크톱 틀이 정본과 다른 페이지(desk.css 를 고쳤으면 손 페이지 링크의 v= 도 바꾼다): %s' % bad


def test_every_rule_is_scoped_to_flagged_pages():
    """desk.css 의 모든 규칙은 body[data-desk…] 아래에 걸린다 — 표지가 없는 페이지와 1023px 이하(media 조건)는 그대로다.
    쓰는 배치 이름은 모두 site_nav.DESK_KINDS 안에 있고, 손으로 레이아웃을 갖는 종류(wide·doc·report·weekly)는 규칙이 있다."""
    css = _css()
    sels = []
    for block in re.findall(r'([^{}@]+)\{[^{}]*\}', re.sub(r'@media[^{]*\{', '', css)):
        sels += [x.strip() for x in block.split(',') if x.strip()]
    assert len(sels) > 20, sels
    loose = [s for s in sels if not (s.startswith('body[data-desk') or s.startswith('html:has(body[data-desk'))]
    assert not loose, '범위 없는 규칙: %s' % loose
    kinds = set(re.findall(r'data-desk=([a-z]+)\]', css))
    assert kinds <= set(N.DESK_KINDS), kinds - set(N.DESK_KINDS)
    for k in ('wide', 'doc', 'report', 'weekly'):
        assert k in kinds, '%s 배치 규칙이 없다' % k


def test_top_nav_height_matches_the_body_offset_and_the_home_rule():
    """위 내비 높이 = 본문 위 여백 — 다르면 첫 줄이 내비 밑에 깔리거나 빈 줄이 생긴다. 홈(app.css body.home-app)과 같은 높이다."""
    css = _css()
    h = int(re.search(r'body\[data-desk\] \.bottomnav\{[^}]*height:(\d+)px', css).group(1))
    assert re.search(r'body\[data-desk\]\{[^}]*padding-top:%dpx' % h, css), h
    app = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    assert 'body.home-app .bottomnav{top:0;bottom:auto;height:%dpx' % h in app, '홈 상단 내비와 높이가 다르다'


def test_generators_bake_the_shell():
    """생성기 템플릿이 정본 링크와 배치를 굽는다 — 이미 구운 페이지가 우연히 맞는 것에 기대지 않는다.
    /weekly/ 는 페이지 파일이 곧 뼈대라, 링크·표지가 없는 옛 뼈대(2026-10-06 이전 모양)와 옛 해시 뼈대를 픽스처로 만든다."""
    page = I.fill(I.SHELL, title='t', body='<header><div class="wrap"><h1>t</h1></div></header>')
    assert N.desk_link() in page and 'data-desk="wide"' in page
    assert 'data-desk="doc"' in I.fill(I.SHELL, desk='doc', body='')
    src = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    assert "'desk_link': N.desk_link(), 'desk_body': N.desk_body(desk)" in src and "desk='read')" in src

    cur = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    bare = BODY.sub('<body>', DESK_LINK.sub('', cur), count=1)
    stale = DESK_LINK.sub('<link rel="stylesheet" href="/desk.css?v=00000000" media="(min-width:1024px)">', cur)
    for old in (bare, stale):
        got = MW.put_nav(old)   # 배치가 부르는 입구(put_nav → put_desk)
        assert DESK_LINK.findall(got) == [N.desk_link()], DESK_LINK.findall(got)
        assert len(re.findall(r'<body data-desk="weekly">', got)) == 1


def test_left_toc_points_at_real_sections():
    """doc 배치의 왼쪽 목차(.dtoc): hidden(좁은 화면엔 없다)·앵커가 모두 그 페이지에 있다·지금 절 표시 스크립트를 싣는다.
    /monthly/ 는 절 이동 칩과 같은 목록(TOC_ITEMS)에서 나온다."""
    found = 0
    for rel, html in _pages():
        tocs = re.findall(r'<nav class="dtoc"([^>]*)>(.*?)</nav>', html, re.S)
        if not tocs:
            continue
        found += 1
        assert len(tocs) == 1 and ' hidden' in tocs[0][0], rel
        assert 'data-desk="doc"' in html, '%s: 목차가 있는데 doc 배치가 아니다' % rel
        assert html.count(N.DTOC_JS) == 1, '%s: 목차 스크립트(site_nav.DTOC_JS)가 없다' % rel
        ids = set(re.findall(r'\bid="([^"]+)"', html))
        miss = [a for a in re.findall(r'href="#([^"]+)"', tocs[0][1]) if a not in ids]
        assert not miss, '%s: 목차가 없는 절을 가리킨다 %s' % (rel, miss)
    assert found >= 3, '목차 페이지(/cycle/·/monthly/·FAQ)를 못 찾았다: %d' % found
    mon = io.open(os.path.join(ROOT, 'monthly', 'index.html'), encoding='utf-8').read()
    chips = re.search(r'<nav class="toc"[^>]*>(.*?)</nav>', mon, re.S).group(1)
    assert re.findall(r'href="#([^"]+)"', chips) == [i for i, _ in MM.TOC_ITEMS]


def test_desk_text_is_at_least_13px():
    """화면 글자 하한 13px(2026-09-28·10-06 대표 결정)을 데스크톱 규칙도 지킨다."""
    sizes = [float(x) for x in re.findall(r'font-size:\s*([\d.]+)px', _css())]
    assert sizes and min(sizes) >= 13, sizes


def test_sticky_heads_fit_the_window():
    """붙박이(sticky) 왼쪽 머리는 화면에 들어갈 때만 붙는다(전수리뷰 2차 H1-2).

    재현한 실제 상태(Playwright, 저장소 생성 페이지): /weekly/ 머리(결론+시군구 지도)는 1024px 폭 1165px·1280px 이상 1318px 라 예전 조건
    min-height:900px 이 맞는 1280×900·1440×900·1920×1080 창에서 붙어, 지도 아래 줄(전남~제주)·범례·TOP 10 링크가 오른쪽 단을 끝까지
    내릴 때까지 화면 밖에 남았다. 시도 리포트 머리는 지역마다 781~888px(대체 글꼴, 제주 최대)라 900px 창에서 아래가 5~40px 넘쳤다.
    고친 뒤 1024×960·1280×960·1440×1000·1920×1080 에서 리포트 머리 19장 모두 붙되 안쪽 스크롤 0, /weekly/ 는 붙지 않는다.
    CI 에는 브라우저가 없어 높이를 못 재므로 그 조건을 글로 고정한다: weekly 머리에는 sticky 가 없고, report 머리 sticky 는 min-height 가
    가장 긴 머리(888px)+위 내비 52px 보다 높은 창에서만이며 화면보다 길어지면 머리 안에서 내려 읽는다(max-height·overflow-y).
    변이(각각 실제로 확인): weekly 의 옛 `@media(min-height:900px){…weekly>header{position:sticky…}}` 를 되살리면, report 조건을 900px 로
    되돌리면, report 의 max-height 를 지우면 빨개진다.
    """
    css = _css()
    assert not re.search(r'body\[data-desk=weekly\]>header\{[^}]*position:sticky', css), '/weekly/ 머리가 다시 붙박이다'
    rep = re.findall(r'@media\(min-height:(\d+)px\)\{body\[data-desk=report\]>header\{([^}]*)\}\}', css)
    assert len(rep) == 1, rep
    h, body = rep[0]
    assert int(h) >= 888 + 52 + 20, h
    assert 'position:sticky' in body and 'max-height:calc(100vh - 52px)' in body and 'overflow-y:auto' in body, body
