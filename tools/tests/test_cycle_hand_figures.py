# -*- coding: utf-8 -*-
"""/cycle/ 손 서술과 사이클 도구의 방어선(전수 리뷰 2026-09-30, 묶음 C: #25·#30·#61·#62·#63·#64·#66·#69·#73·#24).

각 시험의 독스트링에 ① 무엇을 되돌리면 빨개지는지(실제로 깨뜨려 확인) ② 픽스처가 재현하는 실제 상태를 적는다.
페이지를 읽는 시험은 게이트 안에서(생성기 뒤) 돈다 — 기대값은 페이지의 D 에서 유도하고 실데이터 값을 박지 않는다.
"""
import copy
import io
import json
import os
import re
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..'))
import rebuild_cycle_analysis as RC  # noqa: E402
import refresh_cycle_data as RF  # noqa: E402

ROOT = os.path.join(HERE, '..', '..')
PAGE = os.path.join(ROOT, 'cycle', 'index.html')


def _page():
    s = io.open(PAGE, encoding='utf-8').read()
    m = re.search(r'const D=(\{.*?\});\n', s, re.S)
    assert m, 'cycle 페이지에서 const D를 찾지 못했다'
    return json.loads(m.group(1)), s


# ---------------------------------------------------------------- 지수 기준 단절 (#61·#73)

def _index_fixture(cut=None, regions=('서울', '경기', '부산', '대구')):
    """평평하지 않은 합성 월별 지수 2020.01~2026.08. cut 달부터 모든 지역이 새 기준(그 해 6월=100 근처)으로 바뀐다.

    2026-09-28 배치 뒤 data.js 의 모양: 서울 매매 2025.12 189.83 → 2026.01 94.62 처럼 한 달에 절반이 된다.
    """
    dates = ['%d.%02d' % (y, m) for y in range(2020, 2027) for m in range(1, 13)][:80]
    ser = {}
    for j, r in enumerate(regions):
        v, out = 100.0 + 20 * j, []
        for k, d in enumerate(dates):
            v *= 1.0 + 0.004 * ((k % 7) - 2) / 3.0      # 오르내림이 있는 계열
            out.append(round(v, 2))
        if cut:
            k0 = dates.index(cut)
            scale = 100.0 / out[k0]
            out = out[:k0] + [round(x * scale * (1 + 0.01 * j), 2) for x in out[k0:]]
        ser[r] = out
    return {'dates': dates, 'series': ser}


def test_index_break_is_detected_and_a_real_jump_is_not():
    """기준 단절 판정(RC.index_breaks).

    판정 정본은 update_adv_data.index_breaks 이고 RC.index_breaks 는 그 이름이다(아래 단정 — 두 코드가 따로 재면 안 된다).
    변이(실제로 확인): update_adv_data.index_breaks 의 `jump > BREAK_JUMP` 를 `jump > 0.6` 으로 풀면(절반 떨어짐을 못 봄) 첫 단정이
    빨강. BREAK_REGIONS 를 1 로 좁히면 셋째 단정(한 지역만 16% 뛴 달)이 빨강.
    픽스처: 네 지역이 2026.01 에 함께 새 기준으로 바뀐 합성 계열(2026-09-28 배치의 모양), 단절 없는 같은 계열,
    한 지역만 한 달 16% 뛴 계열(실측 최대 13.4% — 제주 전세 2014.05 — 보다 큰 단일 급등).
    """
    st = {'매매지수': _index_fixture('2026.01'), '전세지수': _index_fixture()}
    import update_adv_data as U
    assert RC.index_breaks is U.index_breaks and set(RC.INDEX_KEYS) == set(U.BASIS_SERIES), \
        '사이클 도구가 기준 단절을 수집과 다른 코드로 잰다 — 정본은 update_adv_data.index_breaks'
    br = RC.index_breaks(st)
    assert [(k, d) for k, d, _, _ in br] == [('매매지수', '2026.01')], br
    assert RC.first_break(st, '매매지수') == '2026.01' and RC.first_break(st, '전세지수') is None
    one = _index_fixture()
    one['series']['부산'][40] = round(one['series']['부산'][39] * 1.16, 2)
    assert RC.index_breaks({'매매지수': one, '전세지수': _index_fixture()}) == []


def test_rebuild_and_study_stop_on_a_broken_index():
    """재산정(build)과 등급 구간 재현(study_grade_bands)은 끊긴 지수로 계산하지 않는다(#73).

    변이(실제로 확인): build() 첫 줄의 require_continuous 를 지우면 SystemExit 대신 prep 이 돌아 빨강.
    study_grade_bands 에서 RC.require_continuous 줄을 지우거나 ECOS 호출 뒤로 옮기면 원문 검사가 빨강.
    픽스처: _index_fixture 의 2026.01 단절(2026-09-28 배치의 매매지수 모양).
    """
    st = {'매매지수': _index_fixture('2026.01'), '전세지수': _index_fixture('2025.12')}
    with pytest.raises(SystemExit, match='기준 단절'):
        RC.build(st)
    src = io.open(os.path.join(ROOT, 'tools', 'study_grade_bands.py'), encoding='utf-8').read()
    i = src.find("RC.require_continuous(st")
    assert i > 0 and i < src.find("os.environ['ECOS_API_KEY']"), '물가를 받기 전에 지수 연속성을 보지 않는다'


def _run_refresh(monkeypatch, tmp_path, S):
    page = tmp_path / 'index.html'
    page.write_text(io.open(RF.PAGE, encoding='utf-8').read(), encoding='utf-8')
    monkeypatch.setattr(RF, 'PAGE', str(page))
    monkeypatch.setattr(RF, 'load_stats', lambda: copy.deepcopy(S))
    monkeypatch.setattr(RF.I, 'bump_sitemap', lambda *a, **k: None)
    RF.main()
    txt = page.read_text(encoding='utf-8')
    return json.loads(re.search(r'const D=(\{.*?\});\n', txt, re.S).group(1))


def test_refresh_keeps_the_overlay_charts_while_index_bases_differ(monkeypatch, tmp_path):
    """매매·전세지수의 기준시점이 다르면(한 계열만 재수집에 성공 — 수집은 계열마다 따로 재수집·보류한다) 두 지수를 한 축에
    겹치는 zones·rate_overlay 는 어제 판을 둔다. 기준이 같으면 예전처럼 새로 굽는다.

    변이(실제로 확인): main 의 `if index_bases_agree(S):` 를 `if True:` 로 두면 첫 단정이, index_basis 가 늘 None 을
    돌려주면(기준 비교가 헛돎) 첫 단정이 빨개진다.
    픽스처: 저장소 STATS 에서 수도권 매매지수를 1.1배(차트가 달라지게) 한 사본 — 매매 unit 만 '지수(2026.06=100)'로 바꾼
            경우(통합 검토가 재현한 '매매만 복구' 회차)와 두 unit 이 같은 경우.
    """
    S = RF.load_stats()
    old = json.loads(re.search(r'const D=(\{.*?\});\n', io.open(RF.PAGE, encoding='utf-8').read(), re.S).group(1))
    S['매매지수']['series']['수도권'] = [None if v is None else round(v * 1.1, 2)
                                      for v in S['매매지수']['series']['수도권']]
    split = copy.deepcopy(S)
    split['매매지수']['unit'] = '지수(2026.06=100)'
    assert not RF.index_bases_agree(split) and RF.index_bases_agree(S)
    (tmp_path / 'split').mkdir()
    D = _run_refresh(monkeypatch, tmp_path / 'split', split)
    assert D['zones'] == old['zones'] and D['rate_overlay'] == old['rate_overlay'], '기준이 다른 두 지수를 한 축에 겹쳤다'
    (tmp_path / 'same').mkdir()
    D = _run_refresh(monkeypatch, tmp_path / 'same', S)
    assert D['zones'] != old['zones'], '기준이 같은데 차트를 새로 굽지 않았다'


def test_refresh_holds_the_index_from_the_break_on():
    """배치(refresh_cycle_data)는 단절 달부터 지수를 싣지 않는다(대표 결정 09-30 ①: 재수집 전까지 보류).

    변이(실제로 확인): main 의 `SI = hold_index_breaks(S)` 를 `SI = S` 로 두면 원문 검사가, hold_index_breaks 가
    자르지 않고 그대로 돌려주면 값 단정이 빨강(2026Q1 에 새 기준 값 ~100 이 실린다).
    픽스처: 매매 2026.01·전세 2025.12 부터 새 기준인 합성 수도권 계열(2026-09-28 data.js 의 두 단절 달).
    """
    ma = _index_fixture('2026.01', regions=('수도권', '서울', '경기'))
    je = _index_fixture('2025.12', regions=('수도권', '서울', '경기'))
    S = {'매매지수': ma, '전세지수': je}
    H = RF.hold_index_breaks(S)
    z = RF.quarterly(H['매매지수'], '수도권', 2020)
    assert max(z) == 2025.75, '단절 달(2026.01) 이후 분기가 남았다'
    assert H['전세지수']['series']['수도권'][je['dates'].index('2025.12')] is None
    assert S['매매지수']['series']['수도권'] == ma['series']['수도권'], '원래 계열을 고쳐 썼다'
    # 단절이 없으면 손대지 않는다
    clean = {'매매지수': _index_fixture(regions=('수도권',)), '전세지수': _index_fixture(regions=('수도권',))}
    assert RF.hold_index_breaks(clean) == clean
    body = io.open(os.path.join(ROOT, 'tools', 'refresh_cycle_data.py'), encoding='utf-8').read()
    body = body[body.find('def main('):]
    assert 'SI = hold_index_breaks(S)' in body and 'build_zones(SI)' in body and 'build_overlay(SI)' in body


def test_rebuild_write_refuses_a_big_drift_without_force(monkeypatch, tmp_path):
    """재산정 결과가 지금 페이지와 크게 다르면 --force 없이는 쓰지 않는다(#73).

    변이(실제로 확인): main 의 `if not a.force:` 가드를 지우면 첫 호출이 splice 를 불러 빨강. drift 의 상관 문턱을
    0.5 로 풀면 서울 동조성 0.55→0.82 를 못 봐 빨강.
    픽스처: 리뷰가 단절 계열로 재현한 값(서울 동조성 0.55→0.82, 고리⑥ 유의 11→3곳, 고리① 적은 분기 2.66→0.86).
    """
    cur = {'prose': {'seoul_sync': '0.55', 'l6_sig': '11', 'rate_r': '−0.57'},
           'link1_new': {'jeonse_rise': [2.66, 1.74, -0.36]},
           'cycle_strength': [{'region': '서울', 'score': 1}]}
    new = copy.deepcopy(cur)
    assert RC.drift(cur, new) == []
    new['prose'].update(seoul_sync='0.82', l6_sig='3')
    new['link1_new']['jeonse_rise'][0] = 0.86
    moved = RC.drift(cur, new)
    assert len(moved) == 3, moved

    wrote = []
    monkeypatch.setattr(RC, 'load_stats', lambda p=None: {})
    monkeypatch.setattr(RC, 'build', lambda st: new)
    monkeypatch.setattr(RC, 'report', lambda D: None)
    monkeypatch.setattr(RC, 'current_payload', lambda page: cur)
    monkeypatch.setattr(RC, 'splice', lambda page, D: wrote.append(1) or 0)
    out = str(tmp_path / 'a.json')
    monkeypatch.setattr(sys, 'argv', ['x', '--write', '--json', out])
    with pytest.raises(SystemExit):
        RC.main()
    assert not wrote, '크게 다른 결과를 --force 없이 썼다'
    monkeypatch.setattr(sys, 'argv', ['x', '--write', '--force', '--json', out])
    RC.main()
    assert wrote == [1]


# ---------------------------------------------------------------- 금리 자릿수 (#30)

def test_cd_rate_keeps_two_decimals():
    """CD금리는 원천(한국은행)처럼 소수 둘째 자리로 싣는다.

    변이(실제로 확인): build_overlay 의 `nd=2` 를 빼면 2.9 가 나와 빨강.
    픽스처: 2026Q3 원천처럼 두 달만 들어온 분기(2.91·2.97 → 2.94). 매매·전세는 첫째 자리 그대로.
    """
    dates = ['2026.04', '2026.05', '2026.06', '2026.07', '2026.08']
    S = {'매매지수': {'dates': dates, 'series': {'수도권': [100.04, 100.11, 100.2, 100.3, 100.44]}},
         '전세지수': {'dates': dates, 'series': {'수도권': [99.0, 99.1, 99.2, 99.3, 99.4]}},
         '전세가율': {'dates': dates, 'series': {'수도권': [60.0] * 5}},
         '금리': {'dates': dates, 'series': {'CD(91일)': [2.82, 2.82, 2.91, 2.91, 2.97]}}}
    o = RF.build_overlay(S)
    assert o['t'] == [2026.25, 2026.5]
    assert o['rate'] == [2.85, 2.94], o['rate']
    assert o['maemae'] == [100.1, 100.4]


# ---------------------------------------------------------------- 종합 절 (#62)

def _para(s, anchor):
    i = s.find(anchor)
    assert i >= 0, anchor
    return s[i:s.find('</section>', i)]


def test_strength_paragraph_follows_the_score_chart():
    """'종합' 절의 가장 센 곳·약한 곳은 같은 절 차트(D.cycle_strength)에서 나온다.

    변이(실제로 확인): strength_prose 의 hi 를 min 으로 바꾸면 str_top 이 최저점 지역이 되어 빨강. 문단을 옛 손
    문장('수도권·경기·인천·강원·경남은 … 세종·충북은 거의 돌지 않는다')으로 되돌리면 손 지역명 단정이 빨강.
    픽스처: 게이트 시점 페이지의 D(생성기가 방금 구운 값) — 기대값을 거기서 유도한다.
    """
    D, s = _page()
    cs = D['cycle_strength']
    want = RC.strength_prose(cs)
    hi = max(x['score'] for x in cs)
    assert set(want['str_top'].split('·')) == {x['region'] for x in cs if x['score'] == hi}
    assert {k: D['prose'].get(k) for k in want} == want, '본문 칸이 차트 점수와 다르다 — refresh_cycle_data 를 돌릴 것'
    p = _para(s, 'id="score"')
    p = p[:p.find('<div class="chartbox">')]
    bare = re.sub(r'<span data-d="[a-z0-9_]+">[^<]*</span>', '', p)
    named = [x['region'] for x in cs if x['region'] in bare and x['region'] != '서울']
    assert not named, '종합 절에 점수와 무관하게 손으로 적은 지역명이 남았다: %s' % named
    assert RC.strength_prose([{'region': '제주', 'score': 5}, {'region': '울산', 'score': 1}])['str_top_j'] == '는'


# ---------------------------------------------------------------- 멸실 절 (#66, 대표 결정 ⑦)

def test_demolition_figures_come_from_the_chart_data():
    """참고 ④의 수·연도는 같은 화면 차트 데이터(D.super)에서 채운다.

    변이(실제로 확인): super_prose 가 연평균을 17개 해로 나누면(옛 '33만') 연평균 단정이, 상한 넘는 시나리오를
    melt 10 대신 5 로 고르면 완료 연도 단정이 빨강. 캡션을 옛 '2051년'·'2038년' 문구로 되돌리면 손 수치 단정이 빨강.
    픽스처: 게이트 시점 페이지의 D.super(1980~2005 준공 타임라인, 멸실 속도 시나리오 다섯).
    """
    D, s = _page()
    sp = D['super']
    got = RC.super_prose(sp)
    reach = [t for t in sp['timeline'] if t['reach40'] >= RC.SUPER_FROM]
    assert got['sup_avg'] == str(int(sum(t['units'] for t in reach) / len(reach) / 10000 + 0.5))
    fail = [x for x in sp['melt_scenarios'] if not x['ok']]
    fast_fail = max(fail, key=lambda x: x['melt'])
    assert got['sup_fail_done'] == str(fast_fail['done'])
    assert got['sup_ok_min'] == str(min(x['melt'] for x in sp['melt_scenarios'] if x['ok']))
    assert {k: D['prose'].get(k) for k in got} == got, '멸실 절 칸이 차트 데이터와 다르다'
    ref4 = _para(s, 'id="ref4"')
    bare = re.sub(r'<span data-d="[a-z0-9_]+">[^<]*</span>', '', ref4)
    for old in ('33만', '2051', '2038', '566만', '16분의', '연 20만', '연 2만', '43만', '239만'):
        assert old not in bare, '멸실 절에 손으로 적은 수가 남았다: %s' % old
    m = re.search(r'const SUPER_FROM=(\d{4});', s)
    assert m and int(m.group(1)) == RC.SUPER_FROM, '차트 색 문턱과 본문 도달 연도의 기준이 다르다'
    assert 'reach40>=SUPER_FROM' in s


# ---------------------------------------------------------------- 캡션 색 (#63)

# 캡션이 부르는 색 이름 → 그 이름으로 부를 수 있는 hex. 같은 이름이 서로 먼 색을 가리키지 않게 좁게 둔다.
COLOR_WORDS = {'빨강': {'#e0564a', '#c0392b'}, '초록': {'#2f8f6f', '#3aa17e', '#1f8a70'},
               '청록': {'#127a70'}, '황갈': {'#a89578'}, '회색': {'#a5b5ad', '#c6d0cb', '#c0cbc5'},
               '호박': {'#e0a93b'}, '노랑': {'#e8b84b'}, '보라': {'#a98be0'}}


def _chart_hexes(s, cid, col):
    i = s.find('new Chart(%s,' % cid)
    assert i >= 0, cid
    j = s.find('new Chart(', i + 10)
    blk = s[i:j if j > 0 else len(s)]
    hexes = set(h.lower() for h in re.findall(r"#[0-9a-fA-F]{6}", blk))
    hexes |= {col[k] for k in re.findall(r'COL\.(\w+)', blk)}
    return hexes, blk


def test_caption_colour_names_match_the_bars():
    """차트 캡션(과 축 제목)이 부르는 색 이름은 그 차트가 실제로 칠하는 색이어야 한다.

    변이(실제로 확인): COL.sudo 를 '#e0564a'(빨강)로 바꾸고 캡션을 '청록=수도권'으로 두면 c6·cL6 이 빨강. cL3 캡션을
    옛 '끊긴 곳은 빨강'으로 되돌리면 빨강. cSuper 축 제목을 '빨강=…'으로 되돌리면 빨강.
    픽스처: 실제 cycle/index.html — 캡션은 chartbox 안에서 canvas 와 짝지어 읽는다.
    """
    _, s = _page()
    m = re.search(r'const COL=\{(.*?)\};', s, re.S)
    assert m, '막대 색 상수 COL 이 없다'
    col = {k: v.lower() for k, v in re.findall(r"(\w+):'(#[0-9a-fA-F]{6})'", m.group(1))}
    checked = 0
    for box in re.findall(r'<div class="chartbox"[^>]*>(.*?)<canvas id="(\w+)"', s, re.S):
        body, cid = box
        cap = ' '.join(re.findall(r'<div class="cap"[^>]*>(.*?)</div>', body, re.S))
        hexes, blk = _chart_hexes(s, cid, col)
        titles = ' '.join(re.findall(r"text:'([^']*)'", blk))
        for word, allowed in COLOR_WORDS.items():
            if word in cap or word in titles:
                checked += 1
                assert hexes & allowed, '%s 캡션이 %s 이라 부르지만 그 색으로 칠하지 않는다(%s)' % (cid, word, sorted(hexes))
    assert checked >= 8, '대조한 색 이름이 너무 적다 — 파서가 헛돈다(%d)' % checked


# ---------------------------------------------------------------- 30초 요약·도식 번호 (#64)

CIRC = '①②③④⑤⑥⑦⑧⑨'


def _badges(s):
    out = {}
    for sid, badge in re.findall(r'<section class="step" id="(link\w+)">.*?<span class="badge">([^<]*)</span>', s, re.S):
        out[sid] = badge
    return out


def test_summary_and_diagram_numbers_match_the_section_badges():
    """30초 요약 목록·순환 도식의 고리 번호는 링크한 본문 절의 배지 번호와 같다.

    변이(실제로 확인): 요약의 '⑥ 입주 → 전세 누름' 을 옛 '⑤'로 되돌리면(→ #link6 배지 '고리 ⑥') 빨강. 도식의
    '전세 ↓' 원을 옛 '5' 로 되돌리면 빨강. 요약의 '↓'(②의 역방향)를 옛 '⑥'(→ #link2)으로 되돌리면 빨강.
    픽스처: 실제 cycle/index.html(본문 배지 ①②③④⑤⑥ = 작동 점수의 l1~l6).
    """
    _, s = _page()
    badges = _badges(s)
    assert set(badges) >= {'link1', 'link2', 'link3', 'link45', 'link6'}, badges
    steps = re.findall(r'<li><a href="#(\w+)"[^>]*><span class="ts-n">([^<]*)</span>',
                       s[s.find('class="tldr-steps"'):s.find('</ol>', s.find('class="tldr-steps"'))])
    assert len(steps) >= 6, steps
    seen = []
    for href, n in steps:
        nums = [c for c in n if c in CIRC]
        for c in nums:
            assert c in badges.get(href, ''), '요약 %s 이 #%s(배지 %r)로 간다' % (n, href, badges.get(href))
        seen += nums
    assert sorted(seen) == sorted(CIRC[:6]), '요약의 고리 번호가 ①~⑥ 한 번씩이 아니다: %s' % seen
    svg = s[s.find('<svg viewBox="0 0 460 460"'):s.find('</svg>')]
    boxes = re.findall(r'<a href="#(\w+)" class="cycbox"[^>]*>(.*?)</a>', svg, re.S)
    dia = []
    for href, body in boxes:
        lab = re.findall(r'fill="#fff">([^<]*)</text>', body)
        if not lab:
            continue
        txt = lab[-1]
        m = re.match(r'^(\d)(?:~(\d))?$', txt)
        if not m:
            continue              # '시작' 처럼 번호가 아닌 표지
        a, b = int(m.group(1)), int(m.group(2) or m.group(1))
        assert CIRC[a - 1] in badges.get(href, ''), '도식 %s 이 #%s(배지 %r)로 간다' % (txt, href, badges.get(href))
        for k in range(a, b + 1):
            assert any(CIRC[k - 1] in v for v in badges.values()), '도식 번호 %d 의 본문 절이 없다' % k
        dia += list(range(a, b + 1))
    assert sorted(dia) == [1, 2, 3, 4, 5, 6], '도식 번호가 1~6 한 번씩이 아니다: %s' % dia


# ---------------------------------------------------------------- 박힌 수 (#69)

def test_no_hand_counted_faq_size_or_data_span():
    """'FAQ 8문답'(실제 11문항)과 '2006–2026' 같은 손 수가 돌아오지 않는다.

    변이(실제로 확인): 링크 설명을 '기초 개념 8문답'으로 되돌리면 빨강(FAQ 는 문답이 11개). 머리 설명의 자료 기간을
    칸 밖 손 글자로 되돌리면 빨강.
    픽스처: 실제 cycle/index.html·faq/index.html.
    """
    _, s = _page()
    faq = io.open(os.path.join(ROOT, 'faq', 'index.html'), encoding='utf-8').read()
    n_faq = len(re.findall(r'<details', faq))
    for m in re.finditer(r'(\d+)\s*문답', s):
        assert int(m.group(1)) == n_faq, '/cycle/ 이 FAQ 를 %s문답이라 부르지만 실제 %d개다' % (m.group(1), n_faq)
    hero = s[s.find('<header class="hero">'):s.find('</header>')]
    assert re.search(r'<span data-d="span_y">\d{4}–\d{4}</span> 분기·연', hero), '자료 기간이 칸이 아니다'
    D, _ = _page()
    assert D['prose'].get('span_y') == RC.span_prose(D['zones'])['span_y']


def test_cycle_jeonse_month_uses_the_shared_need():
    """/cycle/ 전세가율 기준월은 /jeonse-ratio/ 와 같은 필요 지역(JEONSE_NEED, 전국 포함)으로 고른다(#24·#106).

    변이(실제로 확인): build_jratio 의 `I.jeonse_ref_index(D, I.JEONSE_NEED)` 를 `(D, SIDO)` 로 되돌리면 빨강.
    픽스처: 모든 시도는 2026.08 까지 찼는데 전국만 2026.08 이 빈 합성 계열(2026.06·07 원천 행 이름 변경 때의 모양).
    """
    import make_indicator_pages as I
    ser = {r: [70.0, 71.0] for r in RF.SIDO}
    ser['전국'] = [69.0, None]
    lvl, _, _, prd = RF.build_jratio({'전세가율': {'dates': ['2026.07', '2026.08'], 'series': ser}})
    assert prd == '2026.07' == ['2026.07', '2026.08'][I.jeonse_ref_index({'dates': ['2026.07', '2026.08'],
                                                                           'series': ser}, I.JEONSE_NEED)]
