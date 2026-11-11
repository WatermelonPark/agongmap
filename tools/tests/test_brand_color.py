# -*- coding: utf-8 -*-
"""틀 강조색(2026-11-11 대표 결정 B안 '남색 + 형광 표시', 정본 site_nav.BRAND_TOKENS).

색 감사(11-11)에서 사이트 틀이 먹색·회색뿐이었다 — 18개 페이지 종류 가운데 9개가 틀(내비·단추·칩·링크·태그)에 유채색 0%.
이제 틀은 남색(--brand), 결론 숫자는 노랑 형광(--mark), 콘텐츠 분류 태그는 연노랑(--mark-bg)이다. 여기서 잠그는 것:
  1. 모든 스타일 정본(app.css·지표 뼈대·손 페이지·주간 뼈대 생성기)이 같은 토큰 값을 싣는다 — 한 곳만 바꾸면 페이지마다 색이 갈린다.
  2. 하단 탭바(데스크톱에서는 위 내비)는 어느 페이지에서나 남색이다.
  3. 데이터 그림(지도·표·차트)은 강조색을 쓰지 않는다 — 남색이 하락 파랑과 섞여 읽히지 않게.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import site_nav as N  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
HAND = ('404.html', 'about/index.html', 'faq/index.html', 'privacy/index.html',
        'burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html')


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _tokens(text):
    return dict(re.findall(r'(--(?:brand|mark)[\w-]*)\s*:\s*(#[0-9a-fA-F]{6})', text))


CANON = _tokens(N.BRAND_TOKENS)


def test_every_style_source_carries_the_canonical_tokens():
    """app.css·지표 뼈대(콘텐츠·월간·지표 페이지)·손 페이지·주간 뼈대가 정본과 같은 토큰을 싣는다.

    변이(각각 확인): app.css 의 --brand 값을 바꾸면 빨강, about/index.html :root 에서 토큰을 지우면 빨강,
          make_indicator_pages 뼈대의 __BRAND__ 자리를 지우면 빨강.
    픽스처: 저장소의 실제 파일들(주간은 생성기가 뼈대에 넣는 결과 — put_brand 를 빈 :root 에 돌려 본다).
    """
    assert len(CANON) == 6 and CANON['--brand'] == '#16325c', CANON
    assert _tokens(_read('app.css')) == CANON, 'app.css 토큰이 정본과 다르다'
    for rel in HAND:   # 홈은 app.css 를 읽는다
        assert _tokens(_read(rel)) == CANON, '%s 의 :root 토큰이 정본과 다르다' % rel
    import make_indicator_pages as MI
    assert _tokens(MI.SHELL.replace('__BRAND__', N.BRAND_TOKENS)) == CANON and '__BRAND__' in MI.SHELL
    import make_weekly_page as MW
    skel = ':root{--ink:#131e24;--ink2:#4c5f66}\n.bottomnav{height:62px;background:var(--ink);}\n.cta{background:var(--ink);color:#fff}'
    out = MW.put_brand(skel)
    assert _tokens(out) == CANON and 'background:var(--ink)' not in out, out
    assert MW.put_brand(out) == out, '두 번 돌리면 토큰이 겹친다'


def test_tabbar_is_navy_everywhere():
    """하단 탭바 규칙(.bottomnav{…})의 바탕은 어디서나 남색이다.

    변이(확인): faq/index.html 의 .bottomnav 바탕을 var(--ink) 로 되돌리면 빨강.
    """
    import make_indicator_pages as MI
    srcs = {rel: _read(rel) for rel in HAND}
    srcs['app.css'] = _read('app.css')
    srcs['SHELL'] = MI.SHELL
    for name, text in srcs.items():
        rules = re.findall(r'(?:^|[}\s])\.bottomnav\{([^}]*)\}', text)
        assert rules, '%s: 탭바 규칙이 없다' % name
        for r in rules:
            if 'background' in r:
                assert N.NAV_BG_CSS in r, '%s: 탭바 바탕이 남색이 아니다 — %s' % (name, r[:80])


def test_data_graphics_never_use_the_brand_color():
    """지도·표·차트 코드에는 강조색이 없다 — 남색(#16325c)이 하락 파랑과 섞여 읽히지 않게(데이터는 의미색만).

    변이(확인): make_weekly_page.MAP_CSS 에 var(--brand) 를 넣으면 빨강.
    """
    import make_weekly_page as MW
    import make_content_pages as MC
    import home_src as HS
    stats = next(t for f, t in HS.home_files() if f.endswith('home-stats.js'))
    chart = '\n'.join(re.findall(r'(?m)^\.c[bx][\w-]*[^{\n]*\{[^}]*\}', MC.EXTRA_CSS))   # 차트 부품(.cx-·.cb-)만
    assert chart.count('{') >= 3, '차트 CSS 를 못 찾았다'
    for name, text in (('home-stats.js', stats), ('MAP_CSS', MW.MAP_CSS),
                       ('TABLE_CSS', MW.TABLE_CSS), ('콘텐츠 차트 CSS', chart)):
        assert not re.search(r'--brand|--mark|#16325c|#ffe066', text), '%s 에 틀 강조색이 들어갔다' % name
