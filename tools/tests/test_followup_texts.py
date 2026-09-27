# -*- coding: utf-8 -*-
"""점검후속 ③④⑤⑥⑦ (2026-09-15) — 기간 정본·갱신 주기·카드 부호·입주물량 해설·병합 안내.
홈 마케팅 검수 A4·A6·C1 (2026-09-27) — 첫 화면 라벨·h1·부제, title, 제목 계층, 지도 행동 안내, 주간 입구 이름.

⚠️ 생성된 페이지를 라이브 데이터로 단정하지 않는다(배치는 pytest를 페이지 생성보다 먼저
돌린다). 함수와 원본(생성기·손으로 쓴 홈)과 저장된 값끼리의 일치로 본다.
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import sido_zones as SZ  # noqa: E402
import make_sido_pages as P  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def _src(rel):
    if HS.is_home(rel):
        return HS.home_source()
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _adv():
    return json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/',
                                _src('data.js'), re.S).group(1))


# ---- ③ 기간 정본 ----

def test_period_constants_follow_the_analysis():
    """정본 상수는 재산정한 리드타임과 같아야 한다. 재측정으로 값이 바뀌면 여기서 걸린다."""
    a = json.load(io.open(os.path.join(ROOT, 'tools', 'data', 'cycle_analysis.json'), encoding='utf-8'))
    assert a['leadtime']['old_months'] == SZ.START_DONE_MONTHS_OLD
    assert a['leadtime']['new_months'] == SZ.START_DONE_MONTHS_NEW


def test_permit_text_describes_nature_not_an_unmeasured_period():
    """인허가→입주 기간은 측정된 적이 없다(전국 집계 시차 0은 사업 단위 시차가 아니다).

    2026-09-15에 '약 3년'으로 박았다가 PM 반대 의견으로 되돌렸다. 기간 대신 성격을 쓴다.
    """
    assert not hasattr(SZ, 'PERMIT_TO_MOVEIN'), '인허가→입주 기간 상수가 되살아났다'
    assert SZ.PERMIT_NATURE in P.REFNOTE['pm']
    period = re.compile(r'\d+\s*(?:~\s*\d+)?\s*년 뒤 입주')
    for rel in ('tools/make_sido_pages.py', 'tools/make_monthly_page.py'):
        assert not period.search(_src(rel)), '%s가 인허가→입주 기간을 단정한다' % rel
    home = _src('index.html')
    HS.require(home, 'const MATRIX_REGIONS', what='홈 스크립트')
    pm = re.search(r"pm:'([^']*)'", home).group(1)
    assert SZ.PERMIT_NATURE in pm, '홈 인허가 안내문 사본이 정본 서술과 다르다'
    assert '약 3년 뒤 입주' not in home


# ---- ④ 갱신 주기 ----

def test_quarterly_verdict_is_not_described_as_weekly():
    s = _src('tools/make_sido_pages.py')
    assert '매주 자동 갱신' not in s
    assert '분기마다 갱신' in s
    assert SZ.quarter_text('2026Q2') == '2026년 2분기'
    assert _adv()['sido'].get('Ltxt') == SZ.quarter_text(_adv()['sido']['L'])


def test_home_supply_captions_say_quarterly():
    home = _src('index.html')
    HS.require(home, 'const MATRIX_REGIONS', what='홈 스크립트')
    for bad in ('분기 합산 · 홈 공급표와 같은 값 · 매주 자동 갱신', '지수 전월비 환산) · 매주 자동 갱신'):
        assert bad not in home, bad


# ---- ⑤ 카드 부호와 용어 (+ 홈 마케팅 검수 B2 퍼센트 해석, 2026-09-27) ----

def test_card_text_never_pairs_a_minus_sign_with_shortfall():
    """부호 이중 부정 제거(09-15 ⑤)는 그대로, 비율은 '3년 필요량의 60%만큼'으로(B2·HERO-4 — '60%만 지어진다'로도 읽혔다).

    변이: card_parts 의 '%%만큼' 을 옛 '%%' 로 되돌리면 빨개진다(확인). 음수 부호를 붙이면 첫 단정이 빨개진다.
    픽스처: 실제 카드 넷 — 전국(686,396 부족·60%), 인천(13,237 여유·19%), 세종(907 부족·13%), 충북(281 부족·1%).
    """
    for dtot, ratio in ((686396, 0.60), (-13237, -0.19), (907, 0.126), (281, 0.009)):
        t = SZ.card_text(dtot, ratio)
        assert '−' not in t and '-' not in t, t
        assert ('부족' in t) == (dtot > 0) and ('여유' in t) == (dtot < 0), t
        num, dirw, share = SZ.card_parts(dtot, ratio)
        assert t == '%s %s · %s' % (num, dirw, share), t
        assert share == '3년 필요량의 %d%%만큼' % int(round(abs(ratio) * 100)), share
    assert SZ.card_text(686396, 0.60) == '686,396세대 부족 · 3년 필요량의 60%만큼'
    assert SZ.card_text(0, 0.004) == '3년 필요량과 거의 같음'


@pytest.fixture(scope='module')
def split_stale(tmp_path_factory):
    """저장소 data.js 사본의 판정 문구를 **옛 문구로 덮은 뒤** split 을 돌린다(저장소에는 쓰지 않는다).

    재현하는 실제 상태: 문구 함수를 고친 PR 이 병합된 날 — data.js 의 ADV.sido 는 다음 배치의 update_adv_data 가 점수를
    다시 쓸 때까지 옛 문구('… · 3년 필요량의 60%', cnum·ftxt 없음)를 싣는다. 홈 data-core 는 그날도 새 문구여야 한다.
    """
    import shutil
    import split_data as S
    d = tmp_path_factory.mktemp('split_ft')
    src = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    m = re.search(r'(/\*ADV_DATA_START\*/\s*const ADV=)(\{.*?\})(;?\s*/\*ADV_DATA_END\*/)', src, re.S)
    adv = json.loads(m.group(2))
    for z in adv['sido']['zones']:
        z['ctxt'] = 'STALE'
        for k in ('cnum', 'cdir', 'cpct', 'ftxt'):
            z.pop(k, None)
    for k in ('dist', 'dist_g0', 'ktxt'):
        adv['sido'].pop(k, None)
    src = src[:m.start(2)] + json.dumps(adv, ensure_ascii=False) + src[m.end(2):]
    io.open(str(d / 'data.js'), 'w', encoding='utf-8').write(src)
    paths = {'SRC': d / 'data.js', 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    trend = json.loads(paths['TREND'].read_text(encoding='utf-8'))
    return adv, core_adv, trend['ADV'], str(d)


def test_stored_cards_match_the_function_and_the_display_integer(split_stale, monkeypatch):
    """저장된 순부족 정수(dtot)는 카드 세 정수로 검산되고, 화면이 읽는 카드 문구는 **지금의 정본 함수**다.

    예전엔 data.js 에 저장된 ctxt 를 함수와 대조했다. 문구 함수를 고치면 data.js 는 다음 배치까지 옛 문구라 그 PR 의 CI
    가 빨갛고, 병합 뒤 배치 전까지 홈도 옛말을 했다. 이제 split_data·make_sido_pages 가 읽을 때 refresh_texts 로 다시
    구우므로, 옛 문구를 넣은 사본에서도 data-core·data-trend·허브가 새 문구인지를 본다.
    변이: split_data 에서 `_SZ.refresh_texts(core_adv['sido'])` 를 지우면 data-core 에 'STALE' 이 남아 빨개진다(확인).
          make_sido_pages.load 의 refresh_texts 를 지우면 마지막 단정이 빨개진다(확인).
    """
    stale, core, trend, root = split_stale
    H = stale['sido']['H']
    for z in stale['sido']['zones']:
        want = P.rnd(z['ref']) * H - P.rnd(z['fut']) - P.rnd(z['inow'])
        assert z['dtot'] == want, z['z']
    for payload in (core, trend):
        sido = payload['sido']
        for z in sido['zones']:
            assert z['ctxt'] == SZ.card_text(z['dtot'], z['ratio'], H), z['z']
            for k, v in SZ.zone_texts(z, H).items():
                assert z[k] == v, (z['z'], k)
        assert sido['dist'] == SZ.dist_text(sido['zones'])
        assert sido['dist_g0'] == SZ.dist_names(sido['zones'])
        assert sido['ktxt'] == SZ.legend_text(H, SZ.BACKLOG_WINDOW)
    monkeypatch.setattr(P, 'ROOT', root)   # 같은 옛 문구 사본을 허브·리포트 생성기가 읽는다
    adv, _ = P.load()
    for z in adv['sido']['zones']:
        assert z['ctxt'] == SZ.card_text(z['dtot'], z['ratio'], adv['sido']['H']), z['z']
        assert z['ftxt'] == SZ.zone_texts(z, adv['sido']['H'])['ftxt'], z['z']


def test_home_and_hub_read_the_baked_card_text():
    home = _src('index.html')
    HS.require(home, 'const MATRIX_REGIONS', what='홈 스크립트')
    assert "z.ctxt" in home
    for f in ('z.cnum', 'z.cdir', 'z.cpct', 'z.ftxt', 'ADV.sido.dist', 'ADV.sido.ktxt'):
        assert f in home, '홈 카드가 구워 둔 %s 를 읽지 않는다' % f
    assert "tbSigned(z.tot)+'세대'+(z.rtxt" not in home, '홈 카드가 옛 부호 문구를 만든다'
    assert not re.search(r"'만큼'|필요량의'\s*\+", HS.home_source()), '홈이 카드 비율 문구를 따로 만든다 — 이중 구현'
    hub = _src('tools/make_sido_pages.py')
    assert "esc(o['ctxt'])" in hub
    assert '모자란 재고' not in hub and "'지난 4년 재고'" not in hub


def test_unsold_multiple_reads_as_percent_below_one():
    assert P.umx(0.05) == '5%' and P.umx(0.53) == '53%' and P.umx(2.4) == '2.4배'


def test_home_legend_says_what_the_color_means_and_when():
    """범례 뜻 한 줄은 판정의 정의 그대로 — 지난 4년 덜 지은 몫까지 더해 3년 필요량을 채우는지(B2·TRUST-2①, 2026-09-27).

    예전 '앞으로 3년 필요한 만큼 지어지는지'는 지난 4년 누적 부족을 빼고 말해, 충북(앞으로 3년 78%)이 '균형'인 까닭과
    카드의 686,396(= 425,873 + 지난 4년 260,523)을 홈에서 검산할 수 없었다. 문구는 sido_zones.legend_text 가 구워 싣고
    (ADV.sido.ktxt) 홈은 읽기만 한다 — 옛 문구는 옛 캐시의 대체값으로만 남는다.
    변이: legend_text 를 옛 문구로 되돌리면 첫 단정이, 홈이 ktxt 를 안 읽으면 둘째가 빨개진다(확인).
    """
    assert SZ.legend_text() == '지난 4년 덜 지은 몫까지 더해 3년 필요량을 채우는지'
    assert '4년' in SZ.legend_text(W=SZ.BACKLOG_WINDOW) and '2년' in SZ.legend_text(W=8)   # 창에서 센다
    home = _src('index.html')
    HS.require(home, 'const MATRIX_REGIONS', what='홈 스크립트')
    assert "(ADV.sido.ktxt||'앞으로 3년 필요한 만큼 지어지는지')" in home and 'ADV.sido.Ltxt' in home
    assert '적정물량 대비 누적 순부족 · 기준' not in home


# ---- ⑥ 입주물량 ----

def test_moveins_page_explains_the_gap_to_the_verdict():
    s = _src('tools/make_indicator_pages.py')
    assert '지역 판정' in s and '/zone/' in s
    assert '착공한 물량의 약' in s
    assert '매주 갱신.</div>' not in s


# ---- ⑦ 병합 안내 (2026-09-15 사용자 결정으로 제거) ----

# 전남광주를 한 곳으로 보는 건 당연해 본문에 설명을 두지 않는다. 옛 주소 안내 페이지
# (/zone/광주/, /zone/전남/)만 예외다 — 그 페이지는 옮겨졌다는 사실 자체가 내용이다.
MERGE_EXPLAINER = re.compile(r'통합 발표|통합에 따라|한 곳으로 본|한 지역으로 봅니다|'
                             r'한 행으로 싣|두 지역(의)? 합으로 병합|왜 합쳐졌')


def test_no_merge_explainer():
    assert not hasattr(P, 'merge_note'), '통합 리포트 병합 안내가 되살아났다'
    srcs = ['tools/make_sido_pages.py', 'tools/make_monthly_page.py',
            'faq/index.html', 'cycle/index.html']
    for rel in srcs:
        text = _src(rel)
        if rel.endswith('.py'):
            # 주석·독스트링의 개발 기록은 화면에 안 나온다 — 따옴표 문자열 줄만 본다
            text = '\n'.join(l for l in text.splitlines()
                             if l.strip().startswith(("'", '"', "('", '("'))
                             or re.search(r"\bh\.append|return \(", l))
        m = MERGE_EXPLAINER.search(text)
        assert not m, '%s에 병합 설명 문구가 있다: %r' % (rel, m.group(0))


# ---- 홈 첫 화면 문구 (홈 마케팅 검수 A6·C1, 2026-09-27) ----
# 재현하는 실제 상태: 09-26 라이브 첫 화면 — 라벨 '아공맵', h1 '국가 통계로 보는 3년 공급'(무엇의 어느 방향 3년인지,
# '아파트'가 첫 화면 어디에도 없었다), 범례 속 11.5px 회색 '지역을 누르면 상세 리포트', title 의 '입주물량'.
HERO_KICK = '아공맵 · 아파트 공급 지도'
HERO_H1 = '공급은 3년, 시세는 매주'
HERO_SUB = '국토교통부 착공·준공 실적으로 시도별 3년 공급을 판정하고, 한국부동산원 주간 시세를 매주 싣습니다.'
FONTS = os.path.join(ROOT, 'tools', 'fonts')


def _home_hero():
    s = _src('index.html')
    m = re.search(r'<header class="home-hero">(.*?)</header>', s, re.S)
    assert m, '홈 히어로를 찾지 못했다'
    return m.group(1)


def test_home_hero_label_title_and_subtitle():
    """C1(09-26 대표 승인): 라벨·h1·부제 한 문장. 옛 h1 이 되살아나면 빨개진다(변이: h1 을 옛 문구로 되돌려 확인)."""
    hero = _home_hero()
    assert '<span class="hero-kick">%s</span>' % HERO_KICK in hero
    h1 = re.search(r'<h1 class="hero-msg">(.*?)<i class="hero-ramp"', hero, re.S)
    assert h1 and h1.group(1) == HERO_H1, h1 and h1.group(1)
    assert '<p class="hero-sub">%s</p>' % HERO_SUB in hero
    assert '국가 통계로 보는 3년 공급' not in _src('index.html')


def _css_rule(css, selector):
    m = re.search(r'(?:^|[}\s])' + re.escape(selector) + r'\{([^}]*)\}', css)
    assert m, 'app.css 에서 %s 규칙을 찾지 못했다' % selector
    return m.group(1)


def _clamp(rule, vw):
    lo, mid, hi = re.search(r'font-size:clamp\(([\d.]+)px,([\d.]+)vw,([\d.]+)px\)', rule).groups()
    return min(max(float(lo), float(mid) * vw / 100), float(hi))


def _content_width(css, vw):
    pad = int(re.search(r'padding:0 (\d+)px', _css_rule(css, '.wrap')).group(1))
    col = int(re.search(r'--col-wide:\s*(\d+)px', css).group(1))
    return min(vw, col) - 2 * pad


def _lines(font, text, width):
    """word-break:keep-all 처럼 띄어쓰기에서만 줄을 바꾼다(브라우저보다 줄바꿈 자리가 적어 보수적이다)."""
    out, cur = [], ''
    for w in text.split(' '):
        c = (cur + ' ' + w) if cur else w
        if cur and font.getlength(c) > width:
            out.append(cur)
            cur = w
        else:
            cur = c
    return out + [cur]


def test_home_h1_stays_on_one_line():
    """h1 은 한 줄이 조건이다(app.css .hero-msg nowrap, 09-15 결정). 320·375·1280px 에서 운영 글꼴로 잰 폭이 본문 폭 안.

    Chromium 에 같은 글꼴을 물려 잰 폭과 같다(2026-09-27 playwright 실측, 글자 폭/본문 폭: 320px 213.0/272 ·
    375px 239.6/327 · 1280px 355.0/772, 세 폭 모두 한 줄). 변이: h1 을 '공급은 3년 판정, 시세는 매주 발표'로 늘리면 320px 에서 빨개진다(확인).
    """
    ImageFont = pytest.importorskip('PIL.ImageFont')
    css = _src('app.css')
    rule = _css_rule(css, '.home-hero h1.hero-msg')
    track = float(re.search(r'letter-spacing:(-?[\d.]+)em', rule).group(1))
    h1 = re.search(r'<h1 class="hero-msg">(.*?)<i class="hero-ramp"', _home_hero(), re.S).group(1)   # 화면에 실제로 있는 문구
    for vw in (320, 375, 1280):
        size = _clamp(rule, vw)
        f = ImageFont.truetype(os.path.join(FONTS, 'Pretendard-Bold.subset.ttf'), round(size))
        w = f.getlength(h1) + track * size * len(h1)
        assert w <= _content_width(css, vw), '%dpx 에서 h1 이 %.0fpx 로 본문 폭을 넘는다' % (vw, w)


def test_home_subtitle_is_two_lines_at_most_on_mobile():
    """부제는 모바일 두 줄 이내(C1). 변이: .hero-sub 글자를 clamp(14px,…) 로 키우면 320px 에서 세 줄이 되어 빨개진다(확인)."""
    ImageFont = pytest.importorskip('PIL.ImageFont')
    css = _src('app.css')
    rule = _css_rule(css, '.home-hero .hero-sub')
    sub = re.search(r'<p class="hero-sub">(.*?)</p>', _home_hero(), re.S).group(1)
    for vw in (320, 360, 375, 414):
        size = _clamp(rule, vw)
        f = ImageFont.truetype(os.path.join(FONTS, 'Pretendard-Medium.subset.ttf'), round(size * 2) / 2)
        n = len(_lines(f, sub, _content_width(css, vw)))
        assert n <= 2, '%dpx 에서 부제가 %d줄' % (vw, n)


def test_home_title_drops_the_moveins_term():
    """A6·SEO-5: 홈 title 에서 '입주물량'을 빼고 '시도별 3년 공급·이번 주 시세'를 담는다(기존 형식 유지).
    변이: 옛 title('시도별 입주물량·주간 시세')로 되돌리면 빨개진다(확인)."""
    t = re.search(r'<title>(.*?)</title>', _src('index.html')).group(1)
    assert t == '전국 아파트 공급 지도 — 시도별 3년 공급·이번 주 시세 | 아공맵', t


def test_home_section_headings_are_one_level():
    """A6·SEO-6: 사이클 구역 제목이 h3 이라 퀴즈 절의 하위 제목으로 읽혔다. 홈 뷰 구역 제목은 모두 h2.
    변이: 사이클 제목을 h3 로 되돌리면 빨개진다(확인)."""
    s = _src('index.html')
    home = s[s.index('<div id="view-home">'):s.index('<!-- ===== 통계보기 대시보드 ===== -->')]
    assert '<h2>집값은 왜 돌고 도는가</h2>' in home
    assert not re.search(r'<h3[\s>]', home), '홈 뷰 본문에 h3 가 남았다'


def test_map_action_line_is_body_text_not_a_footnote():
    """A6·HERO-5①: 행동 안내를 범례 각주(11.5px 회색)에서 본문색 13~14px 문장으로.
    변이: 옛 '지역을 누르면 상세 리포트' 각주로 되돌리거나 .map-act 글자를 12px 로 줄이면 빨개진다(확인)."""
    home = HS.home_source()
    assert "<p class=\"map-act\">지도에서 지역을 누르면 공급 리포트가 열립니다</p>" in home
    assert 'tk-n">지역을 누르면 상세 리포트' not in home
    rule = _css_rule(_src('app.css'), '.home-sec .map-act')
    size = float(re.search(r'font-size:([\d.]+)px', rule).group(1))
    assert 13 <= size <= 14 and 'color:var(--ink)' in rule, rule


def test_home_weekly_entrances_are_named_by_destination():
    """A4·IA-3·MOB-3: 주간 구역 버튼은 통계 탭 시군구 지도로 가는 **링크**이고 이름이 목적지를 말한다.
    격자·푸터는 /weekly/. 변이: 옛 `<button onclick="goStats('market')">이번 주 시세 지도 보기` 로 되돌리면 빨개진다."""
    s = _src('index.html')
    home = s[s.index('<div id="view-home">'):s.index('<!-- ===== 통계보기 대시보드 ===== -->')]
    assert re.search(r'<a class="home-cta" href="#stats-market"[^>]*>시군구 시세 지도·TOP 10 보기</a>', home)
    assert "goStats('market')" not in home and '이번 주 시세 지도 보기' not in home
    assert re.search(r'<a href="/weekly/"[^>]*>이번 주 시세 지도</a>', home), '푸터 주간 링크가 /weekly/ 가 아니다'
    assert 'class="wg-link" href="/weekly/"' in HS.home_source()


def test_data_core_size_comment_is_not_the_old_estimate():
    """A6·MOB-8: data-core 크기 주석이 '48KB'(실제 약 128KB)였다. 옛 값이 되살아나면 빨개진다(확인)."""
    s = _src('index.html')
    assert '홈이 쓰는 조각만(48KB)' not in s and 'data.js(393KB)' not in s
