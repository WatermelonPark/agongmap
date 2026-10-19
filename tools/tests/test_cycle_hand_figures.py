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
    픽스처: 저장소 STATS 에서 수도권 매매지수를 1.1배(차트가 달라지게) 한 사본 — 두 unit 을 픽스처 안에서 **직접** 같은 옛
            기준으로 둔 경우와 매매 unit 만 새 기준으로 바꾼 경우(통합 검토가 재현한 '매매만 복구' 회차). 저장소 unit 을 그대로
            쓰면 배치가 두 지수를 새 기준으로 다시 받은 날(2026-09-30 첫 재수집 회차) 두 경우가 같아져 게이트가 데이터 커밋을
            막았다 — 데이터가 앞으로 가도 초록이게 기준을 픽스처가 정한다.
    """
    S = RF.load_stats()
    old = json.loads(re.search(r'const D=(\{.*?\});\n', io.open(RF.PAGE, encoding='utf-8').read(), re.S).group(1))
    S['매매지수']['series']['수도권'] = [None if v is None else round(v * 1.1, 2)
                                      for v in S['매매지수']['series']['수도권']]
    for k in RC.INDEX_KEYS:
        S[k]['unit'] = '지수(2017.11=100)'
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
    # --write 는 보관 분석(RC.ANALYSIS)도 늘 쓴다(C-7) — 저장소 tools/data/cycle_analysis.json 을 픽스처로 덮지 않게 tmp 로 돌린다.
    monkeypatch.setattr(RC, 'ANALYSIS', str(tmp_path / 'analysis.json'))
    out = str(tmp_path / 'a.json')
    monkeypatch.setattr(sys, 'argv', ['x', '--write', '--json', out])
    with pytest.raises(SystemExit):
        RC.main()
    assert not wrote and not os.path.exists(RC.ANALYSIS), '크게 다른 결과를 --force 없이 썼다'
    monkeypatch.setattr(sys, 'argv', ['x', '--write', '--force', '--json', out])
    RC.main()
    assert wrote == [1]


def test_rebuild_write_with_json_still_updates_the_archived_analysis(monkeypatch, tmp_path):
    """--write 는 페이지(cycle/index.html)를 고친 회차의 결과를 보관 분석(tools/data/cycle_analysis.json)에도 늘 쓰고, --json 은
    그 사본을 하나 더 쓴다. 보관 분석이 옛 판으로 남으면 test_prose_is_what_the_analysis_computed 가 '페이지와 보관 분석의
    prose가 다르다'로 다음 배치 게이트에서 데이터 커밋을 막는다.

    재현하는 실제 상태: 사람이 결과 사본을 남기려고 `--write --json <사본>` 으로 재산정해 커밋한 회차(전수리뷰 C-7 — 예전
    main 은 `path = a.json or ANALYSIS` 라 보관 분석을 건드리지 않았다. 개인 작업 트리에서 그대로 돌려 게이트 실패 재현).
    변이(실제로 확인): main 을 옛 `path = a.json or ANALYSIS` 한 곳 쓰기로 되돌리면 보관 분석 단정이 빨개진다. --json 사본
          쓰기를 빼면 사본 단정이 빨개진다.
    픽스처: 재산정 결과 D 하나(prose 두 칸)와 tmp 의 보관 분석·사본 경로. 페이지 쓰기(splice)·입력 읽기는 가짜로 둔다.
    """
    D = {'prose': {'seoul_sync': '0.55', 'l6_sig': '11'}}
    monkeypatch.setattr(RC, 'load_stats', lambda p=None: {})
    monkeypatch.setattr(RC, 'build', lambda st: D)
    monkeypatch.setattr(RC, 'report', lambda D: None)
    monkeypatch.setattr(RC, 'current_payload', lambda page: D)
    monkeypatch.setattr(RC, 'splice', lambda page, D: 0)
    monkeypatch.setattr(RC, 'ANALYSIS', str(tmp_path / 'data' / 'cycle_analysis.json'))
    copy_path = str(tmp_path / 'copy.json')
    monkeypatch.setattr(sys, 'argv', ['x', '--write', '--json', copy_path])
    RC.main()
    for where, path in (('보관 분석', RC.ANALYSIS), ('--json 사본', copy_path)):
        assert os.path.exists(path), '%s을 쓰지 않았다 — 페이지와 다른 회차로 남는다' % where
        assert json.loads(io.open(path, encoding='utf-8').read()) == D, where


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


def _demol_stats(apt, allh, done, region='서울'):
    """연간 아파트멸실·주택멸실({해: 호})과 해별 준공 합({해: 호} — 열두 달에 고르게 나눔)으로 만든 STATS 조각."""
    ys = sorted(apt)
    mdates = ['%d.%02d' % (y, m) for y in sorted(done) for m in range(1, 13)]
    mvals = [done[int(d[:4])] / 12.0 for d in mdates]
    return {'아파트멸실': {'dates': [str(y) for y in ys], 'series': {region: [apt[y] for y in ys]}},
            '주택멸실': {'dates': [str(y) for y in ys], 'series': {region: [allh[y] for y in ys]}},
            '준공': {'dates': mdates, 'series': {region: mvals}}}


# 2026-10 data.js 의 서울 값(아파트멸실·주택멸실 연간, 준공 해별 합) — 옛 손 문장 '35만 호 중 26.6만 호(76%)'의 재료
_SEOUL_APT = {2014: 3837, 2015: 1791, 2016: 10573, 2017: 14738, 2018: 7306, 2019: 12481, 2020: 9329, 2021: 7488,
              2022: 1210, 2023: 4544, 2024: 2300}
_SEOUL_ALL = {2014: 21955, 2015: 25271, 2016: 42579, 2017: 47534, 2018: 33459, 2019: 32370, 2020: 30012,
              2021: 33489, 2022: 17168, 2023: 16337, 2024: 13322}
_SEOUL_DONE = {2014: 43996, 2015: 22694, 2016: 35388, 2017: 29201, 2018: 38853, 2019: 45860, 2020: 54355,
               2021: 43729, 2022: 31836, 2023: 38028, 2024: 32988, 2025: 49973}


def test_seoul_demolition_compares_apartments_with_apartments():
    """참고 ④ '왜 이것이 사슬과 겹치면 위험한가'의 서울 멸실 비율은 아파트 멸실 ÷ 아파트 준공이고, 주택 전체 멸실은 따로
    이름을 단 보조 값이다(전수리뷰 D3, 대표 결정 2026-10-05). 옛 손 문장은 아파트 준공 35만 호를 주택 전체 멸실 26.6만 호와
    견줘 '76% 상쇄'라 했고, 아파트로는 어느 해도 멸실이 준공을 넘지 않는데 '2015~17년 재고 순감소'라 했다.
    본문 칸은 이 함수의 값(D.prose)이고, 손으로 적은 옛 수·순감소 주장은 남지 않는다.

    변이(각각 실제로 확인): demol_prose 의 비율 분자를 주택멸실(h)로 바꾸면 dm_apt_pct 가 76 이 되어, 창 검사에서 준공
          열두 달 조건(months.get(y) == 12)을 빼면 열한 달 픽스처의 dm_span 이, 본문 순증 칸을 손 숫자와 옛 '재고가
          순감소' 문장으로 되돌리면 칸·손 문장 단정이 빨개진다.
    픽스처: 2026-10 data.js 의 서울 실제 값(위 상수 — 아파트 멸실 계열은 2024 에서 끝나고 준공은 2025 까지 다 찼다), 그리고
          창의 한 해(2019) 준공이 열한 달뿐인 모양(새 해 멸실이 준공보다 먼저 온 회차) — 창을 한 해 당긴다.
    """
    got = RF.demol_prose(_demol_stats(_SEOUL_APT, _SEOUL_ALL, _SEOUL_DONE))
    assert got == {'dm_span': '2016~2024', 'dm_done': '35', 'dm_apt': '7.0', 'dm_apt_pct': '20',
                   'dm_net_pct': '80', 'dm_all': '26.6'}, got
    st = _demol_stats(_SEOUL_APT, _SEOUL_ALL, _SEOUL_DONE)
    j = st['준공']['dates'].index('2024.12')
    st['준공']['series']['서울'][j] = None
    assert RF.demol_prose(st)['dm_span'] == '2015~2023'
    # 페이지: 칸이 모두 본문에 있고 D.prose 와 같다(게이트는 생성기 뒤에 돈다), 옛 손 수·순감소 주장은 없다
    D, s = _page()
    ref4 = _para(s, 'id="ref4"')
    for k in RF.DM_KEYS:
        assert '<span data-d="%s">' % k in ref4, '참고 ④에 %s 칸이 없다' % k
    bare = re.sub(r'<span data-d="[a-z0-9_]+">[^<]*</span>', '', ref4)
    for old in ('26.6만 호(76%)', '35만 호 중', '순감소'):
        assert old not in bare, '멸실 절에 옛 손 문장이 남았다: %s' % old
    assert '주택 전체' in bare and '단독·다세대' in bare, '주택 전체 멸실을 보조 지표로 밝히는 말이 없다'
    # 사이클 재산정(rebuild_cycle_analysis.splice)은 매일 배치가 data.js 에서 채우는 칸(jr_·dm_)을 지우지 않는다 — 지우면
    # 재산정 직후 본문 칸 채우기가 '값이 D.prose 에 없다'로 멈춘다. (변이: DAILY_PROSE_PREFIX 에서 'dm_' 를 빼면 빨개진다.)
    assert all(k.startswith(RC.DAILY_PROSE_PREFIX) and k.startswith(RC.BATCH_PROSE_PREFIX) for k in RF.DM_KEYS + RF.JR_KEYS)


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
    assert re.search(r'<span data-d="span_y">\d{4}~\d{4}</span> 분기·연', hero), '자료 기간이 칸이 아니다'
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


def _boom_gap(z):
    """2019Q2→2021Q4(전국 동반 상승기, theory_link3 의 2019.06→2021.12 와 같은 창) 매매 상승률 − 전세 상승률(%p).
    비율이라 지수 기준시점(2017.11=100 이든 2026.06=100 이든)에 따라 바뀌지 않는다."""
    a, b = z['t'].index(2019.25), z['t'].index(2021.75)
    return (z['maemae'][b] / z['maemae'][a] - z['jeonse'][b] / z['jeonse'][a]) * 100


def test_zone_captions_compare_growth_not_index_levels():
    """/cycle/ 지역별 매매·전세 차트와 금리 오버레이 캡션은 **상승률**로 말하고, 그 말이 같은 화면 차트 데이터와 맞는다.

    예전 캡션('수도권만 2021년 매매가 전세를 크게 따돌린다', '매매가 전세를 크게 이탈해 솟구쳤다')은 두 지수의 **높이**를
    견줬다. 높이 차는 기준시점에 따라 달라져, 두 지수를 2026.06=100 으로 다시 받는 날 부산(17.0)이 수도권(13.7)보다 커져
    거짓이 됐다(통합 검토). 상승률의 차는 기준시점과 무관하다(2026-09-30 실측: 수도권 31.7%p · 대전 26.0 · 부산 10.8 · 대구 7.2).
    변이(실제로 확인): 캡션 지역을 '대전'으로 바꾸거나, 옛 높이 문구('수도권만 … 따돌린다')로 되돌리면 빨개진다.
    픽스처: 저장소 cycle/index.html 의 D.zones·D.rate_overlay 와 두 캡션.
    """
    page = io.open(RF.PAGE, encoding='utf-8').read()
    D = json.loads(re.search(r'const D=(\{.*?\});\n', page, re.S).group(1))
    gaps = {r: _boom_gap(z) for r, z in D['zones'].items()}
    m = re.search(r'매매 상승률이 전세를 가장 크게 앞선 곳은 ([^<.]+?)이다', page)
    assert m, '지역 차트 캡션을 못 찾았다 — 문구를 바꿨으면 이 시험도 고칠 것'
    assert m.group(1) == max(gaps, key=gaps.get), (m.group(1), gaps)
    assert '따돌린다' not in page and '크게 이탈해' not in page, '두 지수의 높이를 견주는 캡션이 남았다'
    ov = D['rate_overlay']
    a, b = ov['t'].index(2019.25), ov['t'].index(2021.75)
    ma, je = ov['maemae'][b] / ov['maemae'][a] - 1, ov['jeonse'][b] / ov['jeonse'][a] - 1
    assert '매매(빨강)가 전세(보라)보다 훨씬 가파르게' in page and ma > 1.5 * je, (ma, je)


# ---------------------------------------------------------------- 마크업·범위 기호 (전수리뷰 C-12·C-14)

_VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr',
         'path', 'circle', 'rect', 'line', 'polyline', 'polygon', 'stop', 'use', 'ellipse'}


def _tag_faults(html):
    """짝 없는 닫는 태그(stray)와 닫히지 않은 여는 태그(unclosed)를 (종류, 태그, 행) 목록으로."""
    from html.parser import HTMLParser

    class _P(HTMLParser):
        def __init__(self):
            super().__init__()
            self.st, self.bad = [], []

        def handle_starttag(self, t, a):
            if t not in _VOID:
                self.st.append((t, self.getpos()[0]))

        def handle_endtag(self, t):
            if t in _VOID:
                return
            if not any(x[0] == t for x in self.st):
                self.bad.append(('stray', t, self.getpos()[0]))
                return
            while self.st:
                x = self.st.pop()
                if x[0] == t:
                    break
                self.bad.append(('unclosed', x[0], x[1]))
    p = _P()
    p.feed(html)
    return p.bad + [('unclosed', t, ln) for t, ln in p.st]


def test_cycle_markup_is_balanced_and_ranges_use_tilde():
    """/cycle/ 손 서술은 태그 짝이 맞고, 연도·수 범위를 '~'로 쓴다(날짜 두 단계 결정 — 범위는 '~', 백로그 36-1).

    고리⑥ '그리고 다시 처음으로.' 상자는 <p> 없이 </p> 로 닫혀 브라우저가 빈 문단(아래 여백 14px)을 만들었다(C-12).
    '2020–23년'·'2020–22년' 두 곳만 en 대시로 남아 같은 페이지의 '2011~17'·'1988~95년'과 모양이 갈렸다(C-14).
    변이(실제로 확인): 그 상자 끝에 '</p>' 를 되돌리면 첫 단정이, '2020~23년' 을 '2020–23년' 으로 되돌리면 둘째 단정이
    빨개진다. 검사기 자체는 아래 합성 조각(짝 없는 </p>)으로 헛돌지 않음을 본다.
    픽스처: 저장소 cycle/index.html(손 서술 — 배치는 const D·data-d 칸·const ZN·dateModified 만 다시 쓴다).
    """
    assert _tag_faults('<div class="note"><b>x</b> y.</p></div>') == [('stray', 'p', 1)]
    _, s = _page()
    assert _tag_faults(s) == [], '/cycle/ 태그 짝이 어긋난다: %s' % _tag_faults(s)[:5]
    body = s[s.find('<body'):s.find('<script>', s.find('</footer>'))]
    text = re.sub(r'<[^>]+>', '', body)
    dash = re.findall(r'\d[–—]\d', text)
    assert not dash, '/cycle/ 본문 범위에 en 대시가 남았다(정본은 ~): %s' % dash
    assert re.search(r'\d~\d', text), '범위 검사가 헛돈다 — 본문에서 ~ 범위를 하나도 못 찾았다'


# ---------------------------------------------------------------- 지역 이름 뒤 조사 (전수리뷰 C-8·X1-7)

_PAIRS = {'은': ('은', '는'), '는': ('은', '는'), '이': ('이', '가'), '가': ('이', '가'),
          '을': ('을', '를'), '를': ('을', '를'), '과': ('과', '와'), '와': ('과', '와')}


def _particle_faults(text, names):
    """화면 이름 뒤(괄호 칸 하나는 건너뛴다) 조사가 그 이름의 받침(RC._jong)과 맞지 않는 곳. '이다'(서술격)는 보지 않는다."""
    pat = re.compile('(%s)(\\([^)]*\\))?(은|는|이|가|을|를|과|와)' % '|'.join(
        map(re.escape, sorted(names, key=len, reverse=True))))
    bad, seen = [], 0
    for m in pat.finditer(text):
        if m.group(3) == '이' and text[m.end():m.end() + 1] == '다':
            continue
        seen += 1
        want = _PAIRS[m.group(3)][0 if RC._jong(m.group(1)) else 1]
        if m.group(3) != want:
            bad.append(m.group(0))
    return bad, seen


def test_cycle_particles_follow_the_display_name():
    """/cycle/ 본문에서 지역 화면 이름 뒤 조사(은/는·이/가·을/를·과/와)는 그 이름의 받침을 따른다.

    백로그 46(10-17)이 '전남광주(78%)는'의 이름만 '광주·전남'으로 바꿔 받침 있는 '남' 뒤에 '는'이 남았다(C-8·X1-7). 이제 그
    자리의 이름·조사는 칸(jr_jnl_nm·jr_jnl_j — refresh_cycle_data.jratio_prose 가 SZ.disp·RC._jong 으로)이다.
    변이(실제로 확인): jratio_prose 의 jr_jnl_j 를 '는' 고정으로 바꾸고 refresh 를 돌리면(아래 픽스처 경로) 첫 단정이, 본문 칸을
    옛 손 글자 '광주·전남(…)는'으로 되돌리면 페이지 단정이 빨개진다.
    픽스처: ① 저장소 STATS 로 굽는 jratio_prose(화면 이름이 바뀌어도 조사가 따라오는지 — 받침 없는 가상 이름 '전남광주'로도 본다),
            ② 게이트 시점 cycle/index.html 의 보이는 글자(칸 값 포함).
    """
    lvl = [{'region': r, 'val': v} for r, v in (('서울', 52.3), ('전남광주', 78.1), ('대구', 70.9), ('대전', 71.8))]
    got = RF.jratio_prose(lvl, '2026.08')
    assert got['jr_jnl_nm'] == RF.SZ.disp('전남광주')
    assert got['jr_jnl_j'] == ('은' if RC._jong(got['jr_jnl_nm']) else '는')
    import unittest.mock as um
    with um.patch.object(RF.SZ, 'disp', lambda k: '전남광주' if k == '전남광주' else k):
        assert RF.jratio_prose(lvl, '2026.08')['jr_jnl_j'] == '는', '받침 없는 이름에 조사가 따라오지 않는다'
    assert _particle_faults('광주·전남(78%)는 서울(52%)은', ['광주·전남', '서울']) == (['광주·전남(78%)는'], 2)
    _, s = _page()
    body = s[s.find('<body'):s.find('<script>', s.find('</footer>'))]
    text = re.sub(r'<[^>]+>', '', body)
    names = {RF.SZ.disp(k) for k in RF.SZ.ORDER}
    bad, seen = _particle_faults(text, names)
    assert seen >= 10, '조사 검사가 헛돈다(%d곳)' % seen
    assert not bad, '/cycle/ 지역 이름 뒤 조사가 받침과 맞지 않는다: %s' % bad


# ---------------------------------------------------------------- 고리⑥ 반응 시차 칸 (전수리뷰 C-3)

def test_link6_caption_counts_come_from_the_chart_rows():
    """고리⑥ 캡션·읽기 칸의 '유의한 지방 N곳 가운데 a곳은 즉시, b곳은 한 분기 뒤, 수도권(…)'은 같은 차트 데이터(D.link6_regional)
    에서 센 칸(RC.link6_lag_prose — l6p_)이다. 6편 블로그 초안(make_theory_post.link6_values)도 같은 함수를 읽는다.

    손 캡션 '유의한 지역만 보면 지방은 즉시'는 같은 막대 툴팁('지방 · 1분기 뒤' — 대구·전북·부산·울산)과 처음부터 어긋났다.
    변이(실제로 확인): link6_lag_prose 의 l6p_late 를 `lag == 0` 으로 세면 합성 뒤집기 단정이, 캡션을 옛 손 문장으로 되돌리면
    칸·옛 문장 단정이 빨개진다.
    픽스처: 게이트 시점 페이지 D(생성기가 방금 구운 값)와, 그 행에서 유의한 지방 한 곳의 시차를 1→0(또는 0→1)으로 바꾼 합성 행.
    """
    D, s = _page()
    rows = D['link6_regional']
    want = RC.link6_lag_prose(rows)
    assert {k: D['prose'].get(k) for k in want} == want, '고리⑥ 시차 칸이 차트 데이터와 다르다 — refresh_cycle_data 를 돌릴 것'
    prov = [x for x in rows if x['sig'] and x['zone'] != '수도권']
    assert prov and int(want['l6p_now']) + int(want['l6p_late']) == len(prov) == int(want['l6p_sig'])
    flip = copy.deepcopy(rows)
    x = next(r for r in flip if r['sig'] and r['zone'] != '수도권')
    x['lag'] = 1 - x['lag']
    got = RC.link6_lag_prose(flip)
    d = 1 if x['lag'] == 0 else -1
    assert (int(got['l6p_now']), int(got['l6p_late'])) == (int(want['l6p_now']) + d, int(want['l6p_late']) - d), got
    sec = _para(s, 'id="link6"')
    cap = re.search(r'<div class="cap">(.*?)</div>\s*<div class="cwrap tall"><canvas id="cL6"', sec, re.S).group(1)
    for k in want:
        assert '<span data-d="%s">' % k in cap, 'cL6 캡션에 %s 칸이 없다' % k
    bare = re.sub(r'<span data-d="[a-z0-9_]+">[^<]*</span>', '', sec)
    for old in ('지방은 즉시', '대체로 즉시'):
        assert old not in bare, '고리⑥에 차트와 어긋나는 손 문장이 남았다: %s' % old


# ---------------------------------------------------------------- 재산정 칸 뒤 손 문장 (전수리뷰 C-10)

# 칸 값의 끝 글자가 바뀌어도 받침이 늘 같은 칸 — 뒤에 손 조사를 둬도 된다(_years 는 '…년'·'…남짓'으로만 끝난다).
_FIXED_TAIL = {'lead_old_y', 'lead_new_y'}


def test_hand_particles_and_claims_hold_for_any_recomputed_value():
    """재산정 칸 바로 뒤에는 값에 기대는 손 조사를 두지 않고, 칸 값의 방향·순서를 단정하는 손 문장은 RC.claim_breaks 가 본다.

    예전 본문은 '−0.30으로 약하다'·'−0.40으로 살아난다'·'0.55로 가장 느슨'처럼 지금 값의 끝 숫자에 맞춘 조사였고(−0.31 이면
    '−0.31으로'), 공급 많은 분기 상승률이 +0.1 이 되면 같은 절이 '0.1%로 꺾였다'와 '소폭 하락으로 돌아선다'를 함께 말했다.
    변이(실제로 확인): 본문 l6_prov 뒤를 옛 '으로 약하다'로 되돌리면 칸 뒤 조사 단정이, claim_breaks 의 공급 많은 분기 부호 검사를
    지우면 그 뒤집기 단정이, RC.splice 의 claim_breaks 호출을 지우면 쓰기 거절 단정이 빨개진다.
    픽스처: 게이트 시점 페이지 D·본문(그 칸은 손 재산정에서만 바뀐다 — 매일 배치는 건드리지 않는다)과, 그 D 에서 전제를 하나씩
            뒤집은 합성 사본.
    """
    D, s = _page()
    body = s[s.find('<body'):s.find('<script>', s.find('</footer>'))]
    bad = []
    for m in re.finditer(r'<span data-d="([a-z0-9_]+)">([^<]*)</span>((?:</(?:b|strong)>)*)(으로|로|은|는|이|가|을|를|과|와)', body):
        if m.group(1) not in _FIXED_TAIL:
            bad.append(m.group(0))
    assert not bad, '재산정 칸 바로 뒤에 값에 기대는 손 조사가 있다(칸으로 만들거나 조사 없는 말로): %s' % bad
    assert RC.claim_breaks(D) == [], RC.claim_breaks(D)

    def broken(fn):
        x = copy.deepcopy(D)
        fn(x)
        return RC.claim_breaks(x)

    def seoul_top(x):
        next(r for r in x['sync'] if r['region'] == '서울')['corr'] = 0.99
    flips = {
        '소폭 하락': lambda x: x['link1_new'].__setitem__('jeonse_rise', x['link1_new']['jeonse_rise'][:2] + [0.1]),
        '계단처럼': lambda x: x['link1_new'].__setitem__('jeonse_rise', [1.0, 2.0, -0.4]),
        '서울은 가장 느슨': seoul_top,
        '지방 대도시': lambda x: [r.__setitem__('corr', 0.98) for r in x['sync'] if r['region'] not in RC.METRO][:1],
        '광역시는 강하고': lambda x: x['prose'].update(l6_metro='−0.20'),
        '살아난다': lambda x: x['prose'].update(sudo_l6='−0.05'),
        '서울은 예외': lambda x: [r.__setitem__('sig', True) for r in x['link6_regional'] if r['region'] == '서울'],
        '수도권은 한 분기 뒤': lambda x: [r.__setitem__('lag', 0) for r in x['link6_regional'] if r['zone'] == '수도권'],
    }
    for why, fn in flips.items():
        got = broken(fn)
        assert any(why in g for g in got), '%s 전제를 뒤집었는데 claim_breaks 가 못 봤다: %s' % (why, got)
    # 쓰기(RC.splice)는 전제가 깨진 재산정을 쓰지 않는다 — 페이지 사본으로 본다
    import tempfile
    with tempfile.TemporaryDirectory() as td:
        page = os.path.join(td, 'index.html')
        io.open(page, 'w', encoding='utf-8', newline='').write(s)
        x = copy.deepcopy(D)
        x['link1_new']['jeonse_rise'][2] = 0.1
        with pytest.raises(SystemExit) as e:
            RC.splice(page, x)
        assert '소폭 하락' in str(e.value)
        assert io.open(page, encoding='utf-8').read() == s, '전제가 깨진 재산정으로 페이지를 고쳤다'
        RC.splice(page, copy.deepcopy(D))      # 전제가 서면 쓴다


# ---------------------------------------------------------------- 페이지 스크립트를 node 로 돌려 본다 (전수리뷰 C-2·C-6·C-13)

# cycle/index.html 의 본문 스크립트(initReport 가 든 <script>)를 가짜 DOM·가짜 Chart 위에서 돌려, 차트마다 넘긴 설정(데이터셋 색·축)과
# 지역 전환 단추의 상태를 JSON 으로 돌려준다. 차트 라이브러리를 늦게 싣는 부트 경로(load → setTimeout → script onload)도 그대로 탄다.
# 인자: 페이지 경로, (선택) const D 를 갈아 끼울 JSON 경로.
_PAGE_JS = r"""const fs=require('fs'),vm=require('vm');
const A=process.argv.slice(2);const html=fs.readFileSync(A[0],"utf8"),over=A[1]?JSON.parse(fs.readFileSync(A[1],"utf8")):null;
const scripts=[...html.matchAll(/<script>([\s\S]*?)<\/script>/g)].map(m=>m[1]);
let src=scripts.find(x=>x.includes('function initReport()'));
if(over) src=src.replace(/const D=\{.*?\};\n/s,()=>'const D='+JSON.stringify(over)+';\n');
function El(tag,id){this.tagName=tag.toUpperCase();this.id=id||'';this.attrs={};this.children=[];this.style={};this.textContent='';
  const cl=new Set();this.classList={add:c=>cl.add(c),remove:c=>cl.delete(c),contains:c=>cl.has(c),toggle:()=>{}};this._cl=cl;}
El.prototype.setAttribute=function(k,v){this.attrs[k]=String(v)};El.prototype.getAttribute=function(k){return k in this.attrs?this.attrs[k]:null};
El.prototype.appendChild=function(c){this.children.push(c);c.parentElement=this;return c};El.prototype.remove=function(){};
El.prototype.matches=function(){return false};El.prototype.querySelector=function(){return null};
const ids=[...html.matchAll(/<canvas id="(\w+)"/g)].map(m=>m[1]);
const canv={};ids.forEach(i=>canv[i]=new El('canvas',i));
const ztog=new El('div','ztog');let scriptEl=null;const charts={};const loads=[];
const document={fonts:undefined,readyState:'loading',head:{appendChild:e=>{scriptEl=e}},body:{classList:{toggle(){}}},documentElement:{scrollHeight:0},
  getElementById:i=>i==='ztog'?ztog:(canv[i]||null),createElement:t=>new El(t),
  querySelector:q=>q==='#ztog button'?ztog.children[0]:(q==='canvas'?canv[ids[0]]:null),
  querySelectorAll:q=>q==='#ztog button'?ztog.children:(q==='canvas'?ids.map(i=>canv[i]):[])};
function Chart(el,cfg){charts[el.id]=cfg;this.destroy=()=>{};this.update=()=>{};}
Chart.getChart=()=>null;Chart.defaults={font:{},plugins:{legend:{}}};
const ctx=Object.assign({document,Chart,console,JSON,Math,Object,Array,Number,String,isNaN,
  window:{addEventListener:(e,f)=>{if(e==='load')loads.push(f)}},addEventListener(){},requestAnimationFrame(){},
  setTimeout:f=>f(),navigator:{},location:{search:''},innerHeight:800,scrollY:0},canv);
vm.createContext(ctx);vm.runInContext(src,ctx);
loads.forEach(f=>f());
if(!scriptEl)throw new Error('차트 스크립트를 싣지 않았다');
scriptEl.onload();
const btn=()=>ztog.children.map(b=>({text:b.textContent,type:b.type||null,pressed:b.getAttribute('aria-pressed')}));
const out={charts:{},buttons0:btn(),c5_0:{role:canv.c5&&canv.c5.getAttribute('role'),label:canv.c5&&canv.c5.getAttribute('aria-label')}};
if(ztog.children.length>1){ztog.children[1].onclick();out.buttons1=btn();out.c5_1={role:canv.c5.getAttribute('role'),label:canv.c5.getAttribute('aria-label')};}
for(const [k,c] of Object.entries(charts)){out.charts[k]={datasets:c.data.datasets.map(d=>({label:d.label||null,bg:d.backgroundColor,border:typeof d.borderColor==='string'?d.borderColor:null,data:d.data})),labels:c.data.labels,scales:JSON.parse(JSON.stringify(c.options.scales||{}))};}
process.stdout.write(JSON.stringify(out));
"""


def _run_page_js(tmp_path, D=None):
    import shutil
    import subprocess
    if not shutil.which('node'):
        pytest.skip('node 없음')
    h = tmp_path / 'harness.js'
    h.write_text(_PAGE_JS, encoding='utf-8')
    args = ['node', str(h), PAGE]
    if D is not None:
        d = tmp_path / 'D.json'
        d.write_text(json.dumps(D, ensure_ascii=False), encoding='utf-8')
        args.append(str(d))
    proc = subprocess.run(args, capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode('utf-8', 'replace')
    return json.loads(proc.stdout.decode('utf-8'))


def test_jratio_spectrum_axis_widens_for_values_outside_the_default_band(tmp_path):
    """참고② 전세가율 스펙트럼(c4)의 가로축은 값이 50~82 밖이어도 막대를 담는다(전수리뷰 C-2).

    축을 min:50·max:82 로 박아 두면 세종 49.9(2019.04~2025.12 내내 50 미만) 같은 막대가 그림 영역 밖에 그려져 이름표만 남고,
    82 를 넘는 막대(전북 2019.12 82.7)는 82 에서 잘린다. 지금은 suggestedMin·suggestedMax 라 Chart.js 가 값에 맞춰 넓힌다.
    변이(실제로 확인): c4 축을 옛 `min:50,max:82` 로 되돌리면 빨개진다.
    픽스처: 저장소 페이지 D 에서 전세가율 가장 낮은 곳을 45.0, 가장 높은 곳을 85.0 으로 바꾼 사본(실제로 있었던 범위 밖 달의 모양).
    """
    D, _ = _page()
    D = copy.deepcopy(D)
    D['jratio_level'][0]['val'] = 45.0
    D['jratio_level'][-1]['val'] = 85.0
    out = _run_page_js(tmp_path, D)
    x = out['charts']['c4']['scales']['x']
    vals = out['charts']['c4']['datasets'][0]['data']
    assert min(vals) == 45.0 and max(vals) == 85.0, vals
    assert x.get('min', -1e9) <= min(vals) and x.get('max', 1e9) >= max(vals), '전세가율 축이 값을 담지 못한다: %s' % x


def _cap_of(s, cid):
    for body, c in re.findall(r'<div class="chartbox"[^>]*>(.*?)<canvas id="(\w+)"', s, re.S):
        if c == cid:
            return ' '.join(re.findall(r'<div class="cap"[^>]*>(.*?)</div>', body, re.S))
    raise AssertionError('%s 캡션이 없다' % cid)


def _word(w):
    w = w.strip('(),.')
    return w if w in COLOR_WORDS else w[:-1] if w.endswith('색') and w[:-1] in COLOR_WORDS else w


def test_caption_colour_pairs_match_the_rows(tmp_path):
    """캡션이 말하는 '색 = 대상' 짝이 막대·선의 실제 색과 맞는다 — 색 이름이 차트 어딘가에 있는지만 보던 시험(위)을 짝 단위로 좁힌다
    (전수리뷰 C-6: c6·cL6 의 수도권·지방 색을 서로 바꿔도 초록이었다).

    차트별 짝: c6·cL6 '청록=수도권, 황갈=지방'(cL6 은 '회색=효과 약함'), cL3 '살아있는 곳(r 0.3 이상)은 초록, … (0~0.3)은 호박색,
    … 끊긴 곳은 회색', cRate '매매(빨강)·전세(보라)', '금리(노랑, …)'. 색 이름은 캡션에서 읽고, 대상 조건은 차트 스크립트의 조건과 같다.
    변이(각각 실제로 확인): c6 `r.sudo?COL.sudo:COL.jib` 를 `r.sudo?COL.jib:COL.sudo` 로, cL6 의 수도권·지방 색을 서로, cL3 의
    COL.cut·COL.live 를 서로, cRate 매매·전세 borderColor 를 서로 바꾸면 각각 빨개진다.
    픽스처: 저장소 페이지 D 에 모든 갈래(수도권·지방 / 유의·비유의 / r≥0.3·0~0.3·음)가 반드시 있도록 합성 행을 더한 사본.
    """
    D, s = _page()
    D = copy.deepcopy(D)
    D['sync'] += [{'region': '합성수도권', 'corr': 0.5, 'sudo': True}, {'region': '합성지방', 'corr': 0.6, 'sudo': False}]
    D['link3_regional'] += [{'region': '합성강', 'r': 0.45, 'sudo': False}, {'region': '합성중', 'r': 0.1, 'sudo': False},
                            {'region': '합성끊김', 'r': -0.2, 'sudo': True}]
    D['link6_regional'] += [dict(region='합성수도권', r=-0.4, lag=1, zone='수도권', sig=True, lagtxt='1분기 뒤'),
                            dict(region='합성지방', r=-0.4, lag=0, zone='지방', sig=True, lagtxt='즉시'),
                            dict(region='합성약함', r=-0.1, lag=0, zone='지방', sig=False, lagtxt='효과 약함')]
    out = _run_page_js(tmp_path, D)['charts']
    rules = {
        'c6': ('sync', [(r'(\S+?)=수도권', lambda r: r['sudo']), (r'(\S+?)=지방', lambda r: not r['sudo'])]),
        'cL6': ('link6_regional', [(r'(\S+?)=수도권', lambda r: r['sig'] and r['zone'] == '수도권'),
                                   (r'(\S+?)=지방', lambda r: r['sig'] and r['zone'] != '수도권'),
                                   (r'(\S+?)=효과 약함', lambda r: not r['sig'])]),
        'cL3': ('link3_regional', [(r'살아있는 곳\([^)]*\)은 (\S+?),', lambda r: r['r'] >= 0.3),
                                   (r'이어진 곳\([^)]*\)은 (\S+?),', lambda r: 0 <= r['r'] < 0.3),
                                   (r'끊긴 곳은 (\S+?)이다', lambda r: r['r'] < 0)]),
    }
    checked = 0
    for cid, (key, pairs) in rules.items():
        cap = _cap_of(s, cid)
        rows = D[key]
        if cid == 'c6':
            rows = sorted(rows, key=lambda r: -r['corr'])     # 페이지가 그리기 전에 동조성 내림차순으로 정렬한다
        bg = out[cid]['datasets'][0]['bg']
        assert len(bg) == len(rows), cid
        for pat, pred in pairs:
            m = re.search(pat, cap)
            assert m, '%s 캡션에서 색 짝을 못 찾았다(%s) — 문구를 바꿨으면 이 시험도 고칠 것' % (cid, pat)
            word = _word(m.group(1))
            assert word in COLOR_WORDS, (cid, word)
            hit = [(r['region'], c) for r, c in zip(rows, bg) if pred(r)]
            assert hit, '%s 의 %s 갈래 행이 없다 — 픽스처가 헛돈다' % (cid, pat)
            wrong = [(n, c) for n, c in hit if c.lower() not in COLOR_WORDS[word]]
            assert not wrong, '%s 캡션은 %s 이라 하는데 다른 색으로 칠했다: %s' % (cid, word, wrong[:3])
            checked += 1
    cap = _cap_of(s, 'cRate')
    ds = {d['label']: (d['border'] or '').lower() for d in out['cRate']['datasets']}
    for pat, label in ((r'매매\((\S+?)\)', '매매'), (r'전세\((\S+?)\)', '전세'), (r'금리\((\S+?),', 'CD금리')):
        m = re.search(pat, cap)
        assert m and label in ds, (pat, sorted(ds))
        assert ds[label] in COLOR_WORDS[_word(m.group(1))], 'cRate %s 선이 캡션 색(%s)이 아니다: %s' % (label, m.group(1), ds[label])
        checked += 1
    assert checked == 11, checked


def test_region_toggle_reports_its_state_to_assistive_tech(tmp_path):
    """참고① 지역별 매매·전세 추이의 지역 전환 단추는 묶음 이름(role=group·aria-label)과 눌림 상태(aria-pressed)를 갖고, 차트 이름에
    고른 지역을 싣는다(전수리뷰 C-13 — 홈 map-mode·tb-view, zone.js zm-seg 와 같은 꼴).

    변이(실제로 확인): onclick 에서 누른 단추의 aria-pressed 를 'true' 로 바꾸는 줄을 빼면 누른 뒤 단정이, dz() 의 role='img' 를 빼면
    (아래 캔버스 이름 루프는 이름이 이미 있으면 건너뛴다) 역할 단정이, #ztog 의 role="group" 을 빼면 첫 단정이 빨개진다.
    픽스처: 저장소 cycle/index.html(D.zones 의 지역 넷) — 둘째 단추를 누른 상태까지 본다.
    """
    _, s = _page()
    assert re.search(r'<div class="toggle" id="ztog" role="group" aria-label="[^"]+">', s), '#ztog 에 묶음 역할·이름이 없다'
    out = _run_page_js(tmp_path)
    b0, b1 = out['buttons0'], out['buttons1']
    assert len(b0) >= 2 and all(b['type'] == 'button' for b in b0), b0
    assert [b['pressed'] for b in b0] == ['true'] + ['false'] * (len(b0) - 1), b0
    assert [b['pressed'] for b in b1] == ['false', 'true'] + ['false'] * (len(b1) - 2), b1
    for st, b in ((out['c5_0'], b0[0]), (out['c5_1'], b1[1])):
        assert st['role'] == 'img' and st['label'] and st['label'].endswith(b['text']), (st, b)


# ---------------------------------------------------------------- 공급 흐름·노후 재고 (전수리뷰 C-4)

def _advance_flows(S):
    """인허가(연내 누계)·착공·준공을 마지막 달 뒤로 이어 그해(마지막 달이 12월이면 다음 해)를 열두 달 채우고, 노후주택30년에 다음
    해를 하나 더한 사본. 돌려주는 값: (사본, 새로 다 찬 해)."""
    S = copy.deepcopy(S)
    last = S['인허가']['dates'][-1]
    y, m = int(last[:4]), int(last[5:7])
    if m == 12:
        y, m = y + 1, 0
    for key in ('인허가', '착공', '준공'):
        blk = S[key]
        assert blk['dates'][-1] == last, '세 계열의 마지막 달이 다르다 — 픽스처를 고칠 것'
        for mm in range(m + 1, 13):
            blk['dates'].append('%d.%02d' % (y, mm))
            for r, ser in blk['series'].items():
                prev = ser[-1] if (key == '인허가' and mm > 1 and ser[-1] is not None) else 0.0
                ser.append(prev + 1000.0)
    b = S['노후주택30년']
    ny = int(str(b['dates'][-1])[:4]) + 1
    b['dates'].append(str(ny))
    for r, ser in b['series'].items():
        ser.append(None if r != '전국' else (ser[-1] or 0) * 1.1)
    return S, y, ny


def test_flow_chain_and_old_stock_follow_data_js(monkeypatch, tmp_path):
    """고리④⑤ 공급 흐름(D.flow_chain)과 참고④ '30년 이상 아파트 … N배'(D.super.stock30)는 매일 배치가 data.js 에서 다시 쓴다.

    예전엔 둘 다 07-30 에 손으로 구운 값이라, 새해 실적·소급 정정이 와도 공급 흐름은 2025 에서, 본문은 '2024년 252만·5배'에서
    멈췄다(data.js 에는 이미 2025 295만이 있었다).
    변이(실제로 확인): main 의 flow_chain splice 를 지우면 전진 단정이, stock30 을 어제 판(prev)으로 두면 노후 재고 전진 단정이,
    build_flow 의 연 합을 RC.y_sum 대신 열두 달을 따지지 않는 합으로 바꾸면 반쯤 찬 해 단정이 빨개진다.
    픽스처: 저장소 STATS 를 마지막 달 뒤로 이어 그해를 다 채운 사본(새해 실적이 들어온 날)과, 그 직전(그해가 덜 찬) 상태.
    """
    S = RF.load_stats()
    D, s = _page()
    # 게이트 시점 페이지: 차트 데이터는 data.js 에서 다시 만든 값이다(생성기 뒤)
    assert D['flow_chain'] == RF.build_flow(S, None), '공급 흐름 차트가 data.js 와 다르다 — refresh_cycle_data 를 돌릴 것'
    assert D['super'].get('stock30') == RF.stock30(S, None) and 'stock30_2024' not in D['super']
    last = S['인허가']['dates'][-1]
    if last[5:7] != '12':
        assert int(last[:4]) not in RF.build_flow(S, None)['t'], '덜 찬 해를 공급 흐름에 실었다'
    S2, y, ny = _advance_flows(S)
    (tmp_path / 'adv').mkdir()
    D2 = _run_refresh(monkeypatch, tmp_path / 'adv', S2)
    fc = D2['flow_chain']
    assert fc['t'][-1] == y, '새로 다 찬 해(%d)를 공급 흐름에 싣지 않았다: %s' % (y, fc['t'][-3:])
    pm = RC.m_y_sum(RF.SZ.permit_monthly(S2, '전국'))[str(y)]
    assert fc['permit'][-1] == round(pm / 1000.0, 1) and fc['start'][-1] > 0 and fc['done'][-1] > 0, fc
    st = D2['super']['stock30']
    assert st['to'] == ny and st['from'] == int(str(S['노후주택30년']['dates'][0])[:4]), st
    assert D2['prose']['sup_s30_y'] == str(ny) and D2['prose']['sup_stock30'] == str(RC._man(st['to_v']))
    assert D2['prose']['sup_s30_x'] == str(RF.SZ.half_up(float(st['to_v']) / st['from_v']))
    ref4 = _para(s, 'id="ref4"')
    for k in ('sup_s30_y0', 'sup_s30_v0', 'sup_s30_y', 'sup_stock30', 'sup_s30_x'):
        assert '<span data-d="%s">' % k in ref4, '참고 ④에 %s 칸이 없다' % k
    bare = re.sub(r'<span data-d="[a-z0-9_]+">[^<]*</span>', '', ref4)
    assert '2024년' not in bare and '5배' not in bare, '노후 재고 문장에 손으로 적은 해·배수가 남았다'


# ---------------------------------------------------------------- 싣는 하위 필드 (전수리뷰 C-11)

def _fields(k, v):
    if k == 'zones':
        return [set(z) for z in v.values()]
    if isinstance(v, list):
        return [set(x) for x in v]
    return [set(v)]


def _with_dead_fields(D):
    """09-12 이후에도 남아 있던 '아무도 읽지 않는 하위 값'을 되살린 사본(2026-10-18 저장소 D 의 모양)."""
    D = copy.deepcopy(D)
    D['rate_overlay']['jratio'] = [60.0] * len(D['rate_overlay']['t'])
    for x in D['jratio_level']:
        x['sudo'] = x['region'] in ('서울', '경기', '인천')
    for x in D['link6_regional']:
        x['p'] = 0.01
    D['link1_new'].update(r=-0.37, p=0.009, lag=1)
    D['super'].update(need_annual=210000, stock2030_2024=3763170)
    return D


def test_payload_sub_fields_are_exactly_what_readers_use(monkeypatch, tmp_path):
    """/cycle/ const D 의 키마다 하위 필드는 RC.SHIP_FIELDS(페이지 스크립트·본문 칸·블로그 이론편이 읽는 것)와 같다.

    최상위 키 시험(test_cycle_payload.test_every_payload_key_is_read_by_the_page)은 하위 값을 못 봐, rate_overlay.jratio(매일 47분기)
    ·jratio_level[].sudo·link6_regional[].p·link1_new.r·p·lag·super.need_annual·stock2030_2024 가 아무도 읽지 않는 채 실렸다.
    변이(실제로 확인): refresh_cycle_data.main 의 SHIP_FIELDS 깎기 루프를 지우면 되살린 사본 단정이, RC.splice 의 깎기를 지우면
    재산정 단정이, build_overlay 에 jratio 를 되살리면(루프가 깎지만) 함수 단정이 빨개진다.
    픽스처: ① 게이트 시점 페이지 D, ② 그 D 에 옛 죽은 하위 값을 되살린 페이지 사본(2026-10-18 저장소의 모양)으로 돈 배치·재산정.
    """
    D, s = _page()
    extra = sorted(set(D) - set(RC.SHIP_FIELDS) - {'prose'})
    assert not extra, 'SHIP_FIELDS 에 없는 키가 D 에 있다(읽는 하위 필드를 등록할 것): %s' % extra

    def check(D, where):
        for k, f in RC.SHIP_FIELDS.items():
            assert k in D, '%s: D 에 %s 가 없다' % (where, k)
            rows = _fields(k, D[k])
            assert rows, '%s: %s 가 비었다' % (where, k)
            bad = [r for r in rows if r != set(f)]
            assert not bad, '%s: %s 의 하위 필드가 SHIP_FIELDS 와 다르다: %s' % (where, k, sorted(bad[0] ^ set(f)))
    check(D, '게이트 페이지')
    assert 'jratio' not in RF.build_overlay(RF.load_stats())
    assert all('sudo' not in x for x in RF.build_jratio(RF.load_stats())[0])
    # 배치: 죽은 하위 값이 남은 옛 페이지에서 돌아도 깎아 낸다
    dead = _with_dead_fields(D)
    old = s.replace(re.search(r'const D=(\{.*?\});\n', s, re.S).group(1), json.dumps(dead, ensure_ascii=False), 1)
    page = tmp_path / 'index.html'
    page.write_text(old, encoding='utf-8')
    monkeypatch.setattr(RF, 'PAGE', str(page))
    monkeypatch.setattr(RF.I, 'bump_sitemap', lambda *a, **k: None)
    RF.main()
    check(json.loads(re.search(r'const D=(\{.*?\});\n', page.read_text(encoding='utf-8'), re.S).group(1)), '배치')
    # 재산정 쓰기(RC.splice): 재산정 결과(보관 분석 모양 — p·lag 포함)를 받아도 페이지에는 깎아 싣는다
    page.write_text(old, encoding='utf-8')
    RC.splice(str(page), copy.deepcopy(dead))
    got = json.loads(re.search(r'const D=(\{.*?\});\n', page.read_text(encoding='utf-8'), re.S).group(1))
    for k in ('link1_new', 'link6_regional'):
        bad = [r for r in _fields(k, got[k]) if r != set(RC.SHIP_FIELDS[k])]
        assert not bad, '재산정: %s 에 읽지 않는 하위 값이 실렸다: %s' % (k, bad[0])


# ---------------------------------------------------------------- 바뀐 날만 날짜를 올린다 (전수리뷰 C-5, 백로그 29)

def test_cycle_date_moves_only_when_the_content_changes(monkeypatch, tmp_path):
    """/cycle/ 의 JSON-LD dateModified 와 sitemap lastmod 는 데이터 칸이 실제로 바뀐 회차에만 오늘(KST)로 오른다.

    조건이 풀리면 매일 배치가 /cycle/ 날짜·sitemap 을 오늘로 올려 매일 커밋·IndexNow 핑이 나가고 검색엔진에 '매일 갱신' 신호가
    간다 — 게이트는 초록이었다(조건을 `if True:` 로 바꿔도 222 passed).
    변이(실제로 확인): main 의 `if _strip_date(page) != _strip_date(RM.ensure(old)):` 를 `if True:` 로 바꾸면 같은 데이터 둘째
    회차 단정이, `RM.ensure(old)` 를 `old` 로 바꾸면 로봇 메타 한 줄만 빠진 옛 판 단정이, 날짜 올리기·bump 를 지우면 값이 바뀐 회차
    단정이 빨개진다.
    픽스처: 저장소 페이지 사본과 저장소 STATS — ① 같은 데이터로 두 번, ② 전세가율 기준월의 서울 한 칸을 +0.7 바꾼 STATS,
            ③ 로봇 메타 줄만 빠진 옛 판(D2 이전 페이지의 모양). 오늘은 가짜 날('1999-12-31')로 둔다.
    """
    import make_indicator_pages as I
    fake = '1999-12-31'
    bumps = []
    page = tmp_path / 'index.html'
    page.write_text(io.open(RF.PAGE, encoding='utf-8').read(), encoding='utf-8')
    monkeypatch.setattr(RF, 'PAGE', str(page))
    monkeypatch.setattr(RF, '_today_kst', lambda: fake)
    monkeypatch.setattr(RF.I, 'bump_sitemap', lambda rows, *a, **k: bumps.append(list(rows)))
    S = RF.load_stats()
    monkeypatch.setattr(RF, 'load_stats', lambda: copy.deepcopy(S))

    def date():
        return re.search(r'"dateModified":\s*"([^"]*)"', page.read_text(encoding='utf-8')).group(1)
    RF.main()                       # 첫 회차는 저장소 판이 이미 최신이면 그대로, 아니면 오늘로
    d1, first = date(), bumps[:]
    del bumps[:]
    RF.main()                       # ① 같은 데이터 둘째 회차 — 날짜·sitemap 그대로
    assert date() == d1 and bumps == [], '데이터가 그대로인데 날짜를 올렸다: %s %s' % (date(), bumps)
    assert d1 == fake or not first, (d1, first)
    # ③ 로봇 메타 한 줄만 빠진 옛 판 — 메타는 넣되 날짜는 그대로
    txt = page.read_text(encoding='utf-8')
    meta = re.search(r'<meta name="robots"[^>]*>\n', txt)
    assert meta, '로봇 메타 줄이 없다 — 픽스처 전제가 깨졌다'
    page.write_text(txt.replace(meta.group(0), '', 1), encoding='utf-8')
    RF.main()
    assert date() == d1 and bumps == [], '로봇 메타 한 줄 때문에 날짜를 올렸다'
    assert '<meta name="robots"' in page.read_text(encoding='utf-8')
    # ② 전세가율 한 칸이 바뀐 회차 — 오늘로, sitemap 도
    page.write_text(page.read_text(encoding='utf-8').replace('"dateModified": "%s"' % d1, '"dateModified": "2000-01-01"'),
                    encoding='utf-8')
    S2 = copy.deepcopy(S)
    k = I.jeonse_ref_index(S2['전세가율'], I.JEONSE_NEED)
    S2['전세가율']['series']['서울'][k] += 0.7
    monkeypatch.setattr(RF, 'load_stats', lambda: copy.deepcopy(S2))
    RF.main()
    assert date() == fake and bumps == [[('/cycle/', fake)]], (date(), bumps)


# ---------------------------------------------------------------- '14개 시도 N년'의 햇수 (전수리뷰 C overflow)

def test_span_years_come_from_the_data_span(monkeypatch, tmp_path):
    """'14개 시도 20년'의 햇수는 자료 기간(D.zones → RC.span_years)에서 나온다. 생성기가 쓰는 자리(/cycle/ 메타 설명·og·JSON-LD,
    블로그 초안 '더 보기')는 그 값이고, 손 페이지(홈 사이클 배너·FAQ)의 손 햇수는 그 값을 넘지 않는다(넘으면 과장 — 자료 기간은
    해마다 늘기만 하므로 이 단정은 데이터가 앞으로 가도 초록이다).

    변이(실제로 확인): refresh_cycle_data.main 에서 fill_meta_span 호출을 지우면 한 해 전진 단정이, make_naver_post '더 보기'의
    햇수를 옛 손 글자 '20년'으로 되돌리면 블로그 원문 단정이, 홈 배너 햇수를 99 로 바꾸면 손 페이지 단정이 빨개진다.
    픽스처: 게이트 시점 페이지 D·머리, 그 D 의 zones 한 지역에 한 해 뒤 분기를 더한 사본(새해 자료가 들어온 날), 홈·FAQ 원문.
    """
    import home_src as HS
    import make_naver_post as P
    D, s = _page()
    n = RC.span_years(D['zones'])
    a, b = D['prose']['span_y'].split('~')
    assert n == int(b) - int(a) and n > 0
    head = s[:s.find('</head>')]
    metas = re.findall(r'\d+개 시도 (\d+)년', head)
    assert len(metas) >= 3 and set(metas) == {str(n)}, '/cycle/ 머리의 햇수가 자료 기간과 다르다: %s vs %d' % (metas, n)
    assert P.CYCLE_SPAN_N == n
    assert any('%d개 시도 %d년 데이터' % (P.CYCLE_SYNC_N, n) in r['desc'] for r in P.MORE_ROTATION)
    src = io.open(P.__file__, encoding='utf-8').read()
    assert not re.search(r'개 시도 \d+년', src), '블로그 도구에 손으로 적은 햇수가 있다 — CYCLE_SPAN_N 을 쓸 것'
    # 새해 자료가 들어온 날 — 햇수가 따라 오른다
    adv = copy.deepcopy(D)
    z0 = next(iter(adv['zones'].values()))
    z0['t'].append(z0['t'][-1] + 1)
    z0['maemae'].append(z0['maemae'][-1])
    z0['jeonse'].append(z0['jeonse'][-1])
    assert RC.span_years(adv['zones']) == n + 1
    monkeypatch.setattr(RF, 'build_zones', lambda S: copy.deepcopy(adv['zones']))
    monkeypatch.setattr(RF, 'index_bases_agree', lambda S: True)     # 지수 기준이 갈린 날에도 이 갈래를 돈다
    page = tmp_path / 'index.html'
    page.write_text(s, encoding='utf-8')
    monkeypatch.setattr(RF, 'PAGE', str(page))
    monkeypatch.setattr(RF.I, 'bump_sitemap', lambda *a, **k: None)
    RF.main()
    head2 = page.read_text(encoding='utf-8')
    head2 = head2[:head2.find('</head>')]
    assert set(re.findall(r'\d+개 시도 (\d+)년', head2)) == {str(n + 1)}, '새해 자료가 들어와도 메타 햇수가 그대로다'
    monkeypatch.setattr(P, 'cycle_d', lambda: adv)
    assert P._cycle_span_years() == n + 1
    # 손 페이지 — 과장하지 않는다
    home = HS.home_source()
    faq = io.open(os.path.join(ROOT, 'faq', 'index.html'), encoding='utf-8').read()
    hand = [('홈 배너', re.findall(r'<div class="hs-kicker">\d+개 시도 · (\d+)년</div>', home)),
            ('홈 배너 설명', re.findall(r'(\d+)년 데이터로 검증한 순환', home)),
            ('FAQ', re.findall(r'검증한 시도의 (\d+)년 데이터', faq))]
    for where, got in hand:
        assert got, '%s 의 햇수 자리를 못 찾았다 — 문구를 바꿨으면 이 시험도 고칠 것' % where
        assert all(int(x) <= n for x in got), '%s 이 자료 기간(%d년)보다 긴 %s년을 말한다' % (where, n, got)
