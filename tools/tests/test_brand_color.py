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


def _shell():
    """지표 뼈대(make_indicator_pages.SHELL)를 원본 파일 글자에서 읽는다 — 다른 시험이 모듈 값을 바꿔 두면 순서에 따라 갈렸다."""
    src = _read('tools/make_indicator_pages.py')
    i = src.index('SHELL = """')
    return src[i:src.index('"""', i + 12)]


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
    shell = _shell()
    assert _tokens(shell.replace('__BRAND__', N.BRAND_TOKENS)) == CANON and '__BRAND__' in shell
    import make_weekly_page as MW
    skel = ':root{--ink:#131e24;--ink2:#4c5f66}\n.bottomnav{height:62px;background:var(--ink);}\n.cta{background:var(--ink);color:#fff}'
    out = MW.put_brand(skel)
    assert _tokens(out) == CANON and 'background:var(--ink)' not in out, out
    assert MW.put_brand(out) == out, '두 번 돌리면 토큰이 겹친다'
    old = skel.replace(':root{--ink:#131e24;', ':root{--ink:#131e24;' + N.BRAND_TOKENS.replace('#16325c', '#000000') + ';')
    out2 = MW.put_brand(old)
    assert out2.count('--brand:') == 1 and _tokens(out2) == CANON, '값이 바뀐 옛 토큰 줄이 남아 겹쳤다(2026-11-11 실제로 났다)'


def test_tabbar_is_navy_everywhere():
    """하단 탭바 규칙(.bottomnav{…})의 바탕은 어디서나 남색이다.

    변이(확인): faq/index.html 의 .bottomnav 바탕을 var(--ink) 로 되돌리면 빨강.
    """
    srcs = {rel: _read(rel) for rel in HAND}
    srcs['app.css'] = _read('app.css')
    srcs['SHELL'] = _shell()
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


def test_up_down_text_on_white_is_one_pair():
    """흰 바탕 등락 글자는 한 벌(site_nav.UP_INK·DN_INK)이다 — 색 감사(11-11)에서 '상승' 글자 빨강 네 벌·'하락' 파랑 세 벌이었다.
    판정 '부족'(g2)은 지도와 같은 빨강 계열이다(노랑이면 신호등 '보통'과 겹친다).

    변이(각각 확인): 지표 뼈대 --up 을 #b23b2e 로 되돌리면 빨강, put_brand 의 --up2 바꾸기를 지우면 빨강, app.css
          .sc-tier.g2 를 노랑(#8f5806)으로 되돌리면 빨강.
    픽스처: 저장소의 실제 스타일 원본과, 옛 주간 뼈대 값(--up2:#8f2318·--dn2:#123c5c)을 담은 합성 :root.
    """
    import make_weekly_page as MW
    import make_sido_pages as MS
    assert '--up:%s;--dn:%s;' % (N.UP_INK, N.DN_INK) in _shell()
    out = MW.put_brand(':root{--ink:#131e24;--up:#c0392b;--up2:#8f2318;--dn:#3a7bd5;--dn2:#123c5c}')
    assert '--up2:%s' % N.UP_INK in out and '--dn2:%s' % N.DN_INK in out, out
    css = _read('app.css')
    ups = re.findall(r'td\.up\{color:(#[0-9a-fA-F]{6})', css)
    dns = re.findall(r'td\.dn\{color:(#[0-9a-fA-F]{6})', css)
    assert ups and set(ups) == {N.UP_INK} and dns and set(dns) == {N.DN_INK}, (ups, dns)
    g2 = re.search(r'\.sc-tier\.g2\{background:#([0-9a-f]{6});color:#([0-9a-f]{6})\}', css)
    for h in (g2.group(1), g2.group(2), MS.GRADE_COLOR['g2'][1:]):
        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
        assert r > g and r > b and not (g > b + 40), '부족(g2)이 빨강 계열이 아니다: #%s' % h


def test_every_chart_uses_the_site_series_colors():
    """그래프 계열색은 사이트 공통 한 벌(site_nav.SERIES_COL — 매매 빨강·전세 보라·공급 초록, 2026-11-11 대표 결정 '사이클 색으로
    통일'). app.css 토큰, 지표 뼈대 토큰(콘텐츠 글 그림이 읽는다), 기본통계 DS_COLOR 의 가격·공급 계열, 콘텐츠 그림 CSS 가 같은 값을
    쓴다. 예전엔 기본통계 착공이 '하락' 파랑(#3a7bd5), 준공이 보라(전세색)였고 콘텐츠 그림은 먹색뿐이었다.

    변이(각각 확인): DS_COLOR 착공을 '#3a7bd5' 로, 콘텐츠 .cl 선을 var(--ink) 로, 지표 뼈대의 __SERIES__ 자리를 지우면 빨강.
    픽스처: 저장소의 실제 스타일·스크립트 원본.
    """
    import make_content_pages as MC
    import home_src as HS
    S = N.SERIES_COL
    assert _tok(N.SERIES_TOKENS) == {'--maemae': S['ma'], '--jeonse': S['je'], '--stock': S['sup']}
    assert {k: v for k, v in _tok(_read('app.css')).items() if k in ('--maemae', '--jeonse', '--stock')} == _tok(N.SERIES_TOKENS)
    shell = _shell()
    assert '__SERIES__' in shell and _read('tools/make_indicator_pages.py').count("replace('__SERIES__', N.SERIES_TOKENS)") == 1
    stats = next(t for f, t in HS.home_files() if f.endswith('home-stats.js'))
    ds = dict(re.findall(r"([가-힣0-9]+):'(#[0-9a-f]{6})'", re.search(r'const DS_COLOR=\{(.*?)\};', stats, re.S).group(1)))
    assert ds['매매지수'] == S['ma'] and ds['전세지수'] == S['je'], ds
    for k in ('인허가', '착공', '분양', '준공'):
        assert ds[k] == S['sup'], (k, ds[k])
    css = MC.EXTRA_CSS
    assert '.cl{fill:none;stroke:var(--maemae)' in css and '.cl-je{stroke:var(--jeonse)' in css
    assert '.cb{fill:var(--stock)' in css


def _tok(text):
    return dict(re.findall(r'(--[\w-]+)\s*:\s*(#[0-9a-fA-F]{6})', text))


def test_up_text_has_one_red_on_every_screen():
    """등락 글자·표지·인허가 막대는 흰 바탕 한 벌(UP_INK·DN_INK)이다 — 계열 빨강(#c0392b)이나 옛 #d2342a·#e0564a 가 글자로 남지 않는다.
    실제 상태(2026-11-12 디자인 마감 점검): 순위 표 머리 ▲ 와 규모별 표 상승 글자가 #c0392b, 기본통계 증감 .chg-up 이 #d2342a,
    /weekly/ 머리 결론 숫자 상승만 --up(지도 빨강), 인허가 막대 #e0564a·#3a7bd5 와 표 칸 글자 #a93226·#1a5276 이 두 벌이었다.
    변이(각각 확인): home-stats.js 순위 머리 ▲ 를 #c0392b 로, app.css .chg-up 을 #d2342a 로, put_brand 의 h1 em.up 바꾸기를
          지우면, 인허가 막대 lo 를 #e0564a 로 되돌리면 빨강.
    픽스처: 저장소의 실제 스타일·스크립트 원본과 옛 주간 뼈대 줄."""
    import home_src as HS
    import make_weekly_page as MW
    stats = next(t for f, t in HS.home_files() if f.endswith('home-stats.js'))
    texts = set(re.findall(r'color:(#[0-9a-fA-F]{6})', stats))
    assert not texts & {'#c0392b', '#d2342a', '#e0564a', '#3a7bd5'}, sorted(texts)
    assert N.UP_INK in texts and N.DN_INK in texts, sorted(texts)
    bar = re.search(r"const cols=vals\.map\(v=>\{const c=permitCls\(reg,v\);return c==='hi'\?'(#\w{6})':\(c==='lo'\?'(#\w{6})'", stats)
    assert bar and bar.groups() == (N.DN_INK, N.UP_INK), bar and bar.groups()
    assert re.search(r'\.chg-up\{color:(#\w{6})\}', _read('app.css')).group(1) == N.UP_INK
    out = MW.put_brand(':root{--ink:#131e24;--up:#c0392b;--up2:#8f2318;--dn2:#123c5c}\n  h1 em.up{color:var(--up)}')
    assert 'h1 em.up{color:var(--up2)}' in out, out
