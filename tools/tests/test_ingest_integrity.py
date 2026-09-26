# -*- coding: utf-8 -*-
"""수집 정합(2026-09-26 데이터 감사 #4·#5·#7·#8)의 회귀 시험.

원천 호출 없이 돈다 — kosis·_rone_recent_rows·check_freshness.get_json 을 픽스처로 바꿔 끼운다. 픽스처는
**저장소 data.js 의 실제 STATS·ADV 를 잘라** 원천 응답 모양으로 되돌린 것이고, 기대값도 같은 저장분에서
뽑는다(데이터가 매일 바뀌어도 시험이 낡지 않는다). 지역 이름은 모델(sido_zones)·정본(merge_regions)에서
가져온다. 저장소 파일은 읽기만 한다. 각 시험 독스트링에 ① 변이(실제로 적용해 빨개짐을 확인)와
② 픽스처가 재현하는 실제 상태를 적었다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402
import sido_zones as SZ      # noqa: E402
import check_freshness as C  # noqa: E402
from merge_regions import SRC, DST, W_GJ, WEIGHTED  # noqa: E402

KOSIS_AGG = {v: k for k, v in U.BASIC_REGMAP.items()}      # '전국' → '총계' …
# 국토교통부 주택건설실적통계가 광주·전남을 '전남광주' 한 행으로 내기 시작한 달(원천 최종변경일 2026-08-31,
# merge_regions·merged_sido_rows 머리말). 그 전 달은 원천이 두 옛 이름으로만 준다.
SWITCH = (2026, 7)


def _stats():
    return copy.deepcopy(U.read_current_stats())


def _idx(D, ym):
    for i, d in enumerate(D['dates']):
        if U._label_ym(d) == ym:
            return i
    raise KeyError(ym)


def _window(end, n):
    y, m = end
    out = []
    for _ in range(n):
        out.append((y, m))
        y, m = (y - 1, 12) if m == 1 else (y, m - 1)
    return sorted(out)


def _next(ym):
    return (ym[0] + 1, 1) if ym[1] == 12 else (ym[0], ym[1] + 1)


def _split(v):
    """저장된 통합 값을 두 옛 조각으로 되돌린다(합이 저장값과 같다)."""
    g = int(v) // 3
    return g, int(v) - g


# ── #4 기본통계(인허가·착공·준공)도 옛 두 이름을 접는다 ─────────────────────────────
def _mltm_rows(D, months, bump=None):
    """DT_MLTM_1948/5387/5373 응답 모양(C1=지역, C2=유형). SWITCH 전 달은 전남광주 대신 광주·전남 두 행.

    bump=(ym, 값)이면 그 달 전남 조각과 그것을 품는 집계(총계·지방소계·기타지방)에 값을 더한다 —
    원천이 통합 전 달 전남을 소급 정정한 회차."""
    rows = []
    for ym in months:
        i = _idx(D, ym)
        prd = '%d%02d' % ym
        for k, (reg, arr) in enumerate(D['series'].items()):
            v = arr[i]
            if v is None:
                continue
            add = bump[1] if (bump and bump[0] == ym) else 0
            if reg == DST and ym < SWITCH:
                g, j = _split(v)
                pieces = ((SRC[0], g), (SRC[1], j + add))
            else:
                bumped = reg in ('전국', '지방', '기타지방')
                pieces = ((KOSIS_AGG.get(reg, reg), int(v) + (add if bumped else 0)),)
            for n, (nm, x) in enumerate(pieces):
                rows.append({'C1_NM': nm, 'C1': 'r%03d' % (k * 2 + n), 'C2_NM': '아파트',
                             'PRD_DE': prd, 'DT': str(x)})
    return rows


@pytest.mark.parametrize('name', [n for n, c in U.BASIC_CONF.items() if c['mode'] == 'mltm'])
def test_basic_folds_old_names_so_a_source_correction_keeps_the_sum(monkeypatch, name):
    """창 안의 통합 전 달을 원천이 광주·전남 두 이름으로 다시 주면 전남광주로 접혀 저장분에 실린다. 그 달
    전남이 소급 정정돼도 전남광주·전국·지방이 함께 움직여 시도합=전국 게이트가 초록이다.

    변이: _fetch_basic_one 끝의 `for vals in out.values(): _fold_gj(vals, weighted)` 두 줄을 지우면
          merge_basic 이 두 옛 이름을 버려 전남광주가 병합 스냅숏에 굳고, check_sido_sum 이 '시도합=전국 어긋남'
          '지방=나머지13 어긋남'을 내 빨개진다(확인).
    픽스처: 저장 STATS 의 해당 계열에서 SWITCH 로 끝나는 8개월 창(배치의 BASIC_MONTHS)을 원천 응답 모양으로
            되돌렸다. SWITCH 전 달은 전남광주가 광주·전남 두 행(DT_MLTM_* 의 2026.06까지 실제 모양), SWITCH 달은
            통합 행 하나. 마지막 통합 전 달에 전남 +50 소급 정정(총계·지방소계·기타지방도 +50).
    """
    st = _stats()
    D = st[name]
    months = _window(SWITCH, U.BASIC_MONTHS)
    last_old = max(m for m in months if m < SWITCH)
    before = D['series'][DST][_idx(D, last_old)]
    assert before is not None, '픽스처: 통합 전 달의 저장값이 비어 있다'
    rows = _mltm_rows(D, months, bump=(last_old, 50))
    monkeypatch.setattr(U, 'kosis', lambda p: [r for r in rows if r['PRD_DE'] == p['startPrdDe']])
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    fetched, _ = U._fetch_basic_one(name, months=len(months), upto=SWITCH)
    assert all(not (set(SRC) & set(v)) for v in fetched.values()), '옛 이름이 남았다'
    U.merge_basic(D, fetched)
    assert D['series'][DST][_idx(D, last_old)] == before + 50, '소급 정정이 전남광주에 안 실렸다'
    assert C.check_sido_sum({name: D}) == []


def test_basic_index_series_fold_by_weighted_mean(monkeypatch):
    """지수 계열(merge_regions.WEIGHTED)은 합이 아니라 W_GJ 가중평균으로 접고, 원천 통합 행이 있으면 그걸 쓰며,
    한 조각만 온 달은 전남광주를 만들지 않는다(저장값을 건드리지 않는다).

    변이: _fetch_basic_one 의 `weighted = name in _GJ_WEIGHTED` 를 `weighted = False` 로 바꾸면 두 조각 달이
          합(두 배 가까운 지수)이 되어 빨개진다(확인). 한 조각 규칙은 test_three_ingest_paths_share_one_fold_rule 이 본다.
    픽스처: 저장 STATS 매매지수(KOSIS DT_KAB_11672_S1, R-ONE 월간 지수)의 마지막 확정 3달. R-ONE 은 2026.06부터
            통합 지수를 함께 내고 그 전은 광주·전남만 준다 — 첫 달은 두 조각만, 둘째 달은 두 조각+통합 행, 셋째
            달은 광주 한 조각만(원천 순단).
    """
    name = '매매지수'
    assert name in WEIGHTED
    st = _stats()
    D = st[name]
    conf = [i for i, d in enumerate(D['dates']) if 'p' not in d][-3:]
    months = [U._label_ym(D['dates'][i]) for i in conf]
    rows = []
    for n, i in enumerate(conf):
        prd = '%d%02d' % months[n]
        for k, (reg, arr) in enumerate(D['series'].items()):
            if arr[i] is None or reg == DST:
                continue
            rows.append({'ITM_NM': '지수', 'C1_NM': reg, 'C1': 'k%03d' % k, 'PRD_DE': prd, 'DT': str(arr[i])})
        g, j = 100.0 + n, 120.0 + 2 * n
        pieces = [(SRC[0], g), (SRC[1], j)] if n < 2 else [(SRC[0], g)]
        if n == 1:
            pieces.append((DST, 555.55))
        for m, (nm, v) in enumerate(pieces):
            rows.append({'ITM_NM': '지수', 'C1_NM': nm, 'C1': 'g%02d' % m, 'PRD_DE': prd, 'DT': str(v)})
    monkeypatch.setattr(U, 'kosis', lambda p: rows)
    fetched, _ = U._fetch_basic_one(name, months=3, upto=months[-1])
    a, b, c = months
    assert fetched[a][DST] == round(W_GJ * 100.0 + (1 - W_GJ) * 120.0, 2)
    assert fetched[b][DST] == 555.55, '원천 통합 행이 있으면 그 값을 써야 한다'
    assert DST not in fetched[c] and not (set(SRC) & set(fetched[c]))
    stored_c = D['series'][DST][conf[-1]]
    U.merge_basic(D, fetched)
    assert D['series'][DST][conf[-1]] == stored_c, '한 조각만 온 달이 저장값을 덮었다'


SHAPES = {
    'both': {SRC[0]: 1188, SRC[1]: 3014},
    'one': {SRC[0]: 1188},
    'merged': {DST: 4202},
    'merged+one': {DST: 4202, SRC[1]: 3014},
    'merged+both': {DST: 4202, SRC[0]: 1100, SRC[1]: 3000},
    'none': {},
}


@pytest.mark.parametrize('shape', sorted(SHAPES))
def test_three_ingest_paths_share_one_fold_rule(monkeypatch, shape):
    """인허가 표(ADV.permits)·기본통계(STATS 인허가)·공급(분양·미분양) 세 경로가 같은 원천 모양을 같은 전남광주로 접는다.

    변이: _merge_gj 를 예전 규칙(한 조각만 와도 `vals[_GJ_NEW] = sum(parts)`, 원천 통합 행을 덮어씀)으로 되돌리면
          'one'·'merged+one'·'merged+both' 가, _fetch_basic_one 의 접기 두 줄을 지우면 'both'·'one'·'merged+one'·
          'merged+both' 가 빨개진다(둘 다 확인).
    픽스처: 2026 전환기에 원천이 실제로 줄 수 있는 모양 여섯(두 조각·한 조각·통합 행·통합+옛 행 섞임·빈 달).
            값은 09-26 저장분의 2026.06 인허가 누계(광주 1188·전남 3014 = 전남광주 4202)다.
    """
    vals = SHAPES[shape]
    permits = U._fold_old_permits(dict(vals))
    supply = U._merge_gj({(2026, 6): dict(vals)})[(2026, 6)]
    rows = [{'C1_NM': r, 'C1': 'c%d' % k, 'C2_NM': '아파트', 'PRD_DE': '202606', 'DT': str(v)}
            for k, (r, v) in enumerate(vals.items())]
    monkeypatch.setattr(U, 'kosis', lambda p: rows)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    basic = U._fetch_basic_one('인허가', months=1, upto=(2026, 6))[0].get((2026, 6), {})
    got = {k: (d.get(DST), tuple(sorted(set(SRC) & set(d)))) for k, d in
           (('permits', permits), ('supply', supply), ('basic', basic))}
    assert len(set(got.values())) == 1, got
    want = {'both': 4202, 'one': None, 'merged': 4202, 'merged+one': 4202, 'merged+both': 4202, 'none': None}
    assert got['permits'] == (want[shape], ())


# ── #7 공급: 한 조각만 온 달은 보류(과소 집계 금지), 감시와 같은 판정 ─────────────────────
def _supply_rows(D, months, last_shape=None):
    """R-ONE 미분양표(T237973129847263) 응답 모양 — 시도 '<지역>>계' 행. 저장 전남광주는 광주·전남 두 행으로 되돌린다.
    months 의 마지막 달이 저장분에 없으면(새 달) 직전 달 값에 +10 을 한 값으로 만든다. last_shape 는 새 달의
    광주·전남 모양(SHAPES 의 키)이다."""
    rows = []
    for ym in months:
        try:
            i, bump = _idx(D, ym), 0
        except KeyError:
            i, bump = len(D['dates']) - 1, 10
        vals = {r: D['series'][r][i] for r in U.SUPPLY_SIDO}
        gj = vals.pop(DST)
        if bump:
            vals = {r: v + bump for r, v in vals.items()}
            shape = {k: v for k, v in SHAPES[last_shape].items()}
            vals.update(shape)
        else:
            g, j = _split(gj)
            vals.update({SRC[0]: g, SRC[1]: j})
        for r, v in vals.items():
            rows.append({'WRTTIME_IDTFR_ID': '%d%02d' % ym, 'CLS_FULLNM': '%s>계' % r, 'DTA_VAL': str(v)})
    return rows


def _run_supply(monkeypatch, st, rows):
    tbl = U.SUPPLY_CONF['미분양']['tbl']
    monkeypatch.setattr(U, '_rone_recent_rows',
                        lambda t, need, cycle='WK', since=None: [dict(r) for r in rows] if t == tbl else [])
    monkeypatch.setattr(U, 'SUPPLY_STALLED', [])
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    failed = []
    U.update_supply(st, failed=failed)
    return failed


def test_supply_month_with_one_piece_is_held_not_undercounted(monkeypatch):
    """원천이 새 달에 광주만 채우고 전남을 아직 안 채웠으면 그 달을 받지 않는다(전남광주·전국이 전남만큼
    모자란 채 저장되는 경로를 막는다). 완비된 옛 달은 그대로 들어온다.

    변이: _merge_gj 를 예전 규칙(`parts = [x for x in (g, j) if x is not None]; if parts: vals[_GJ_NEW] = sum(parts)`)
          으로 되돌리면 새 달이 전남광주 = 광주 조각으로 붙어 빨개진다(확인 — 전국도 전남만큼 적다).
    픽스처: 저장 STATS 미분양의 마지막 두 달(광주·전남 두 행으로 되돌림) + 그 다음 새 달. 새 달은 R-ONE 이 광주·전남을
            개편 중인 지금(2026-09-26 배치 로그 'supply 미분양: 2026-07 제외, 시도 1곳 결측(전남광주)')에서 한 조각만
            먼저 채운 모양이다.
    """
    st = _stats()
    D0 = copy.deepcopy(st['미분양'])
    last = U._label_ym(D0['dates'][-1])
    months = [U._label_ym(D0['dates'][-2]), last, _next(last)]
    failed = _run_supply(monkeypatch, st, _supply_rows(D0, months, 'one'))
    D = st['미분양']
    assert U._label_ym(D['dates'][-1]) == last, '한 조각만 온 달이 붙었다 — 전남광주·전국이 과소 집계된다'
    assert D['series'] == D0['series'] and not failed and not U.SUPPLY_STALLED


@pytest.mark.parametrize('shape', sorted(SHAPES))
def test_supply_batch_and_watchdog_agree_on_the_latest_complete_month(monkeypatch, shape):
    """배치가 받아 붙이는 마지막 달과 그 달 시도 합이, 감시(check_freshness.rone_latest_complete)가 원천의
    '완비된 최신 달'로 보는 것과 같다. 기준이 갈리면 한쪽 방어선이 다른 쪽 고장을 덮는다 — 배치가 한 조각 달을
    싣고 감시는 그 달을 미완비로 봐 '우리가 더 새것'으로 넘어가 값 대조를 건너뛰던 것이 감사 #7 이다.

    변이: _merge_gj 를 예전 규칙(한 조각만 와도 그 조각을 통합 지역에 싣고 원천 통합 행을 덮음)으로 되돌리면 'one'
          (배치는 새 달, 감시는 직전 달)과 'merged+one'(배치는 전남 조각, 감시는 통합 행)이 빨개진다(확인).
          감시의 접기를 예전 인라인 규칙(두 조각이 다 있으면 `v['전남광주'] = v.pop(old_a) + v.pop(old_b)` 로 통합 행을
          덮음)으로 되돌리면 'merged+both'(배치 4202, 감시 4100)가 빨개진다(2026-09-26 감사 #7 잔여, 확인).
    픽스처: 저장 STATS 미분양의 마지막 달(광주·전남 두 행) + 새 달. 새 달의 광주·전남 모양을 SHAPES 여섯으로 바꾼다
            ('merged+both' 는 통합 행과 값이 다른 두 조각이 함께 오는 전환기 모양이다).
    """
    st = _stats()
    D0 = copy.deepcopy(st['미분양'])
    last = U._label_ym(D0['dates'][-1])
    months = [last, _next(last)]
    rows = _supply_rows(D0, months, shape)
    _run_supply(monkeypatch, st, rows)
    D = st['미분양']
    b_last = U._label_ym(D['dates'][-1])
    b_total = sum(D['series'][r][-1] or 0 for r in U.SUPPLY_SIDO)

    def get_json(url):
        return {'SttsApiTblData': [{'head': [{'list_total_count': len(rows)}]}, {'row': rows}]}
    monkeypatch.setattr(C, 'get_json', get_json)
    monkeypatch.setattr(C, '_COMPLETE_CACHE', {})
    w_last, w_total = C.rone_latest_complete(U.SUPPLY_CONF['미분양']['tbl'], want_total=True)
    assert '%d%02d' % b_last == w_last, (b_last, w_last)
    assert abs(b_total - w_total) < 1e-6, (b_total, w_total)


# ── #5 준공·착공 끝 분기가 갈라지면 STATS 단계에서 되돌린다 ───────────────────────────────
def _next_quarter_months(D):
    """저장분 마지막 달 뒤로 다음 분기를 닫을 때까지의 달들."""
    ym = U._label_ym(D['dates'][-1])
    out = []
    while True:
        ym = _next(ym)
        out.append(ym)
        if ym[1] % 3 == 0:
            return out


def _basic_run(monkeypatch, st, give):
    """update_basic 을 저장 STATS 사본 위에서 돌린다. give = {계열: fetched 또는 예외}."""
    monkeypatch.setattr(U, 'read_current_stats', lambda: st)
    monkeypatch.setattr(U, 'write_stats', lambda s: None)
    for fn in ('update_rate', 'update_size', 'update_supply', 'update_annual'):
        monkeypatch.setattr(U, fn, lambda *a, **k: [])
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)

    def fetch(name, *a, **k):
        g = give.get(name, {})
        if isinstance(g, Exception):
            raise g
        return copy.deepcopy(g), {}
    monkeypatch.setattr(U, '_fetch_basic_one', fetch)
    failed = []
    changed = U.update_basic(failed)
    return failed, changed


def _new_quarter(D):
    last = {r: v[-1] for r, v in D['series'].items() if v[-1] is not None}
    return {ym: dict(last) for ym in _next_quarter_months(D)}


def test_quarter_closing_month_on_one_series_only_is_held(monkeypatch):
    """분기를 닫는 달이 처음 들어오는 회차에 준공만 새 분기를 받고 착공 호출이 죽으면(부분 실패, rc=0), 준공·착공을
    병합 전으로 두고 'sido-h' 를 남긴다 — STATS 가 정합(H == lead)한 채라 make_sido_pages 가 ABORT 하지 않고 그날
    데이터(주간·월간 시세 등)가 커밋된다. 둘 다 받은 회차는 그대로 새 분기로 간다(대조군).

    변이: update_basic 의 `if _hold_horizon(stats, before, failed):` 블록을 지우면 준공만 새 분기로 가 H = lead − 1 이
          되어 빨개진다(확인 — 그 STATS 로 make_sido_pages 는 'ABORT: 준공(~…)과 착공(~…)의 끝 분기가 달라' 로 죽는다).
    픽스처: 저장 STATS 준공·착공(둘 다 같은 달에서 끝남)과 그 뒤 분기를 닫는 달들. 준공 표(DT_MLTM_5373)는 새 달을
            주고 착공 표(DT_MLTM_5387) 호출은 KOSIS 오류 — 감사 #5 재현(2026-08-07 '착공만 늦게 도착' 사례와 같은 모양).
    """
    st = _stats()
    before = SZ.calc(st)
    assert before['H'] == before['lead'], '픽스처: 저장분이 이미 어긋나 있다'
    j0, c0 = copy.deepcopy(st['준공']), copy.deepcopy(st['착공'])
    failed, changed = _basic_run(monkeypatch, st, {'준공': _new_quarter(j0),
                                                  '착공': RuntimeError('KOSIS err 20: 픽스처')})
    assert '착공' in failed and 'sido-h' in failed
    assert st['준공'] == j0 and st['착공'] == c0, '한쪽만 새 분기인 STATS 가 남았다'
    after = SZ.calc(st)
    assert after['H'] == after['lead'] and after['L'] == before['L']
    assert not any(t.startswith('준공') for t in changed)

    st = _stats()
    failed, changed = _basic_run(monkeypatch, st, {'준공': _new_quarter(st['준공']),
                                                  '착공': _new_quarter(st['착공'])})
    after = SZ.calc(st)
    assert 'sido-h' not in failed and after['H'] == after['lead'] and after['L'] > before['L'], \
        '둘 다 받은 회차는 새 분기로 가야 한다'


# ── #8 서울구 열이 한 회차 빠져도 이력을 지운다 ───────────────────────────────────────────
@pytest.mark.parametrize('kind,window', [('weekly', U.RECENT_WEEKS), ('monthly', U.RECENT_MONTHS)])
def test_gu_missing_for_one_run_keeps_its_history(kind, window):
    """최신 주(달)에 서울 구 하나가 빠진 부분 응답이 한 번 와도 그 구의 창 밖 이력이 남고, 다음 회차에 구가 돌아오면
    전 구간이 저장분 그대로다. 빠진 회차는 부분 실패로 기록된다.

    변이: _merge_hist 의 `if gone:` 합집합 블록을 지우면(예전처럼 새 응답의 열 목록만 쓰면) 첫 회차에 그 구 열이
          통째로 사라지고 다음 회차에 창 밖이 전부 None 이 되어 빨개진다(확인 — 주간 136주·월간 106달 영구 손실).
    픽스처: 저장 ADV 의 weekly/monthly.seoul(서울 25구 × 저장 구간)과, 그 끝 RECENT_WEEKS/RECENT_MONTHS 구간을 다시
            받은 응답. 첫 회차 응답은 열 목록 첫 구가 빠졌다(fetch_*_rone 이 최신 주 매매값에서 gus 를 다시 만들 때
            그 구 행이 페이지 경계에서 밀린 회차). 둘째 회차는 정상 응답.
    """
    cur = copy.deepcopy(U.read_current_adv()[3][kind]['seoul'])
    regs = cur['regions']
    gu = regs[0]
    keep = U.CONF[kind]['sgg_hist']
    full = {'regions': list(regs), 'rows': copy.deepcopy(cur['rows'][-window:])}
    part = {'regions': regs[1:], 'rows': [dict(r, **{k: v[1:] for k, v in r.items() if isinstance(v, list)})
                                          for r in copy.deepcopy(full['rows'])]}
    old = {r['p']: r['ma'][0] for r in cur['rows']}
    assert sum(v is not None for p, v in old.items() if p < full['rows'][0]['p']) > 0, '픽스처: 창 밖 이력이 없다'
    soft = []
    n1 = U._merge_hist(part, copy.deepcopy(cur), keep, '시험 서울구', soft)
    assert n1['regions'] == regs, '빠진 구의 열이 사라졌다'
    j = n1['regions'].index(gu)
    for r in n1['rows']:
        want = old[r['p']] if r['p'] < full['rows'][0]['p'] else None
        assert r['ma'][j] == want, r['p']
    assert soft == ['시험 서울구 열 빠짐(%s)' % gu]
    n2 = U._merge_hist(copy.deepcopy(full), n1, keep, '시험 서울구', soft)
    assert n2['regions'] == regs and [r['ma'][0] for r in n2['rows']] == [old[r['p']] for r in n2['rows']]
    assert len(soft) == 1, '정상 회차에 실패가 기록됐다'
