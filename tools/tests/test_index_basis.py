# -*- coding: utf-8 -*-
"""지수 계열 기준시점 변경(리베이스)을 이어 붙이지 않는다 — 전수리뷰 #61(+72·73의 수집 쪽).

2026-09-28 배치(3a823bc): 한국부동산원 실거래가격지수(KOSIS DT_KAB_11672_S1·S23)가 기준시점을 2017.11=100 에서
2026.06=100 으로 바꿨는데, update_basic 은 최근 8개월만 다시 받아 옛 계열 끝에 덮어써서 매매지수는 2026.01, 전세지수는
2025.12 에서 한 달에 −25~−54% 짜리 가짜 절벽이 생겼다(서울 매매 189.83 → 94.62). unit 도 옛 기준을 적은 채였다.
대표 결정(2026-09-30): 전 기간을 새 기준으로 다시 받아 원천 그대로 둔다(연결계수 금지). 못 받으면 그 계열 갱신 보류.

이 파일은 두 가지를 본다.
  1. 게이트: 저장 data.js 의 지수 계열에 기준 단절이 있으면 **다음 배치가 전 기간 재수집을 하게 돼 있어야** 한다
     (update_basic 이 쓰는 판정 `_basis_reason` 이 그 단절을 잡는다). 단절이 없으면 unit 의 기준시점이 데이터의 기준시점
     표지(모든 지역 100.0 인 달)와 같아야 한다. 병합 직후 data.js 는 단절 상태이므로 게이트는 단절 자체로 빨개지지 않는다 —
     그러면 배치가 복구하기도 전에 멈춘다. 배치가 재수집에 성공하면 단절이 사라져 unit 검사가 엄격해진다. 재수집이 실패한
     회차는 '<계열>:기준변경 보류'가 .fetch_failed(배치 알림 ℹ️ 줄)에 남는다.
  2. 합성 응답으로 기준 변경 감지 → 전 기간 재수집, 저장 단절 → 재수집, 재수집 실패·불완전 → 보류를 재현한다.
원천 호출 없이 돈다(kosis 를 픽스처로 바꾼다). 각 시험 독스트링에 ① 변이(실제로 적용해 빨개짐 확인) ② 픽스처를 적었다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402

NAME = '매매지수'
BASE = (2026, 6)          # 픽스처의 새 기준 달(원천 실제 새 기준과 같게 둔다 — 값은 픽스처 안에서만 쓴다)
FIRST = (2024, 1)
LAST = (2026, 7)          # 마지막 확정 달. 그 다음 달은 잠정 증감률로만 온다


# ── 1. 게이트 ─────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('name', U.BASIS_SERIES)
def test_stored_index_break_is_scheduled_for_full_refetch(name):
    """저장 지수 계열에 지역 전반의 인접 월 단절(±JUMP_TOL 을 넘은 지역이 BROAD_SHARE 이상)이 있으면 update_basic 이
    다음 회차에 전 기간을 다시 받게 돼 있다. 단절이 없으면 unit 의 기준시점이 데이터의 기준시점 표지와 같다.

    변이: _basis_reason 에서 `br = basis_breaks(D); if br: return …` 를 지우면(저장 단절을 못 보면) 지금 data.js(단절 상태)
          에서 두 계열 모두 빨개진다(확인). 배치가 재수집으로 복구한 뒤에는 basis_unit 을 거치지 않고 옛 unit 을 두면
          unit 단정이 빨개진다(test_rebase_in_overlap_refetches_the_whole_series 의 합성 복구본으로 확인).
    픽스처: 저장소 data.js 의 STATS 실제 값. 날짜·지역을 박지 않는다 — 데이터가 앞으로 가도 같은 판정을 한다.
    """
    D = U.read_current_stats()[name]
    breaks = U.basis_breaks(D)
    if breaks:
        assert U._basis_reason(D, {}), '%s 에 기준 단절(%s)이 있는데 배치가 재수집하지 않는다' % (name, breaks)
    else:
        assert D.get('unit') == U.basis_unit(D, D.get('unit')), \
            '%s unit(%s)이 데이터의 기준시점(%s)과 다르다' % (name, D.get('unit'), U.basis_months(D)[-1:])


def test_thresholds_have_room_over_real_moves():
    """문턱이 실제 움직임보다 넉넉한지 — 저장 계열의 단절 달을 뺀 모든 인접 월에서 JUMP_TOL 을 넘은 지역 비율이
    BROAD_SHARE 에 한참 못 미친다(실제 월간 최대는 13%대 한 지역). 문턱을 낮추다 실제 급등락을 단절로 오인하면 배치가
    매 회차 전 기간을 다시 받게 된다.

    변이: JUMP_TOL 을 0.05 로 낮추면 빨개진다(확인 — 세종·제주의 실제 급등 달이 단절로 잡힌다).
    픽스처: 저장소 data.js 의 두 지수 계열 실제 값.
    """
    for name in U.BASIS_SERIES:
        D = U.read_current_stats()[name]
        br = set(U.basis_breaks(D))
        regs = list(D['series'].values())
        for i in range(1, len(D['dates'])):
            if D['dates'][i] in br:
                continue
            both = [(a[i - 1], a[i]) for a in regs if a[i - 1] and a[i] is not None]
            if not both:
                continue
            big = sum(1 for p, c in both if abs(c / p - 1) > U.JUMP_TOL)
            assert big < U.BROAD_SHARE * len(both) / 2, (name, D['dates'][i], big, len(both))


# ── 2. 합성 원천 ───────────────────────────────────────────────────────────────
def _months(a, b):
    out = []
    while a <= b:
        out.append(a)
        a = (a[0] + 1, 1) if a[1] == 12 else (a[0], a[1] + 1)
    return out


MONTHS = _months(FIRST, LAST)


def _regions():
    return list(U.read_current_stats()[NAME]['series'])


def _old_level(j, t):
    """옛 기준 계열. 지역마다 수준이 다르다(60~190) — 기준 달 값이 100 근처인 지역은 기준 변경에도 거의 안 움직인다."""
    return (60 + 5 * j) * (1.003 ** t) * (1 + 0.002 * ((t * (j + 3)) % 5))


def _series(new_base):
    regs = _regions()
    b = MONTHS.index(BASE)
    out = {}
    for j, r in enumerate(regs):
        vals = [_old_level(j, t) for t in range(len(MONTHS))]
        if new_base:
            vals = [v / vals[b] * 100 for v in vals]
        out[r] = [round(v, 2) for v in vals]
    return out


OLD, NEW = _series(False), _series(True)


def _stored(kind):
    """저장 계열. 'old' = 옛 기준만(기준 변경 직전 회차), 'spliced' = 끝 8달만 새 기준으로 덮인 지금 data.js 모양."""
    k = len(MONTHS) - U.BASIC_MONTHS
    series = {}
    for r in OLD:
        series[r] = list(OLD[r]) if kind == 'old' else OLD[r][:k] + NEW[r][k:]
    return {'dates': ['%d.%02d' % ym for ym in MONTHS], 'unit': '지수(2017.11=100)',
            'series': series, 'source': '한국부동산원 아파트 실거래가격지수'}


def _rows(months, rate=None):
    rows = []
    for ym in months:
        i = MONTHS.index(ym)
        for j, r in enumerate(NEW):
            rows.append({'ITM_NM': '지수', 'C1_NM': r, 'C1': 'k%02d' % j, 'PRD_DE': '%d%02d' % ym, 'DT': str(NEW[r][i])})
    if rate is not None:
        nxt = (LAST[0], LAST[1] + 1) if LAST[1] < 12 else (LAST[0] + 1, 1)
        for j, r in enumerate(NEW):
            rows.append({'ITM_NM': '잠정 증감률', 'C1_NM': r, 'C1': 'k%02d' % j,
                         'PRD_DE': '%d%02d' % nxt, 'DT': str(rate)})
    return rows


def _run(monkeypatch, stored, range_ok=True, gap=None):
    """update_basic 을 합성 STATS({NAME: stored}) 위에서 돈다. kosis 는 새 기준 원천을 흉내 낸다:
    newEstPrdCnt 는 최근 n 확정 달(+잠정 증감률), startPrdDe~endPrdDe 는 그 구간(range_ok=False 면 KOSIS 오류)."""
    st = {NAME: copy.deepcopy(stored)}
    monkeypatch.setattr(U, 'BASIC_CONF', {NAME: U.BASIC_CONF[NAME]})
    monkeypatch.setattr(U, 'read_current_stats', lambda: st)
    monkeypatch.setattr(U, 'write_stats', lambda s: None)
    for fn in ('update_rate', 'update_size', 'update_supply', 'update_annual'):
        monkeypatch.setattr(U, fn, lambda *a, **k: [])
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    calls = []

    def kosis(p):
        calls.append(p)
        if 'newEstPrdCnt' in p:
            return _rows(MONTHS[-int(p['newEstPrdCnt']):], rate=0.3)
        if not range_ok:
            raise RuntimeError('KOSIS err 21: 픽스처(조회 한도)')
        lo, hi = p['startPrdDe'], p['endPrdDe']
        ms = [ym for ym in MONTHS if lo <= '%d%02d' % ym <= hi and ym != gap]
        return _rows(ms, rate=0.3 if hi >= '%d%02d' % LAST else None)
    monkeypatch.setattr(U, 'kosis', kosis)
    failed = []
    changed = U.update_basic(failed)
    return st[NAME], failed, changed, calls


def _assert_rebuilt(D, changed):
    assert D['dates'][:len(MONTHS)] == ['%d.%02d' % ym for ym in MONTHS]
    for r, arr in NEW.items():
        assert D['series'][r][:len(MONTHS)] == arr, '%s 에 옛 기준 값이 남았다' % r
    assert D['dates'][-1].endswith('p)'), '잠정 달이 안 붙었다'
    assert U.basis_breaks(D) == []
    assert D['unit'] == '지수(%d.%02d=100)' % BASE
    assert D['unit'] == U.basis_unit(D, D['unit'])
    assert any(t.startswith(NAME + '(기준변경 전기간 재수집') for t in changed)


def test_rebase_in_overlap_refetches_the_whole_series(monkeypatch):
    """원천이 기준시점을 바꾼 첫 회차: 최근 8달 응답이 저장분과 지역 전반에서 어긋나면 이어 붙이지 않고 저장분 첫 달부터
    다시 받아, 저장 계열 전체가 새 기준 원천 값이 되고 unit 이 새 기준을 말한다.

    변이: _basis_reason 의 `if fetched and rebase_in_overlap(D, fetched): return …` 를 지우면 끝 8달만 덮여 절벽이 생기고
          빨개진다(확인 — 3a823bc 회차의 모양). refetch_basic_full 끝의 `new['unit'] = basis_unit(…)` 을 지우면 unit 단정이
          빨개진다(확인).
    픽스처: 옛 기준(지역마다 수준 60~190)으로 2024.01~2026.07 을 저장한 계열, 원천은 같은 움직임을 2026.06=100 으로 다시
            낸 값 + 2026.08 잠정 증감률. 기준 달 값이 100 근처인 지역이 섞여 있어 '모든 지역' 기준이면 못 잡는다.
    """
    D, failed, changed, calls = _run(monkeypatch, _stored('old'))
    assert not failed
    _assert_rebuilt(D, changed)
    assert any('startPrdDe' in p and p['startPrdDe'] <= '%d%02d' % FIRST for p in calls), '첫 달까지 다시 받지 않았다'


def test_spliced_store_heals_itself_on_the_next_run(monkeypatch):
    """이미 이어 붙은 저장 계열(지금 data.js 모양 — 끝 8달만 새 기준)은 최근 8달 응답이 저장분과 같아도(겹치는 달 비 1)
    저장 계열 안의 단절로 알아보고 전 기간을 다시 받는다. 다음 클라우드 배치가 스스로 복구하는 경로다.

    변이: _basis_reason 의 `br = basis_breaks(D); if br: return …` 를 지우면 단절이 그대로 남아 빨개진다(확인).
    픽스처: 옛 기준 앞부분 + 새 기준 끝 8달로 이어 붙은 저장 계열, 원천은 새 기준 전 기간.
    """
    stored = _stored('spliced')
    assert U.basis_breaks(stored), '픽스처: 단절이 없다'
    assert not U.rebase_in_overlap(stored, {ym: {r: NEW[r][MONTHS.index(ym)] for r in NEW}
                                            for ym in MONTHS[-U.BASIC_MONTHS:]}), '픽스처: 겹치는 달이 어긋난다'
    D, failed, changed, _ = _run(monkeypatch, stored)
    assert not failed
    _assert_rebuilt(D, changed)


@pytest.mark.parametrize('mode', ['kosis-error', 'gap'])
def test_failed_refetch_holds_the_series_and_is_recorded(monkeypatch, mode):
    """전 기간 재수집이 실패하거나(KOSIS 오류) 받은 것이 온전하지 않으면(중간 달 빠짐) 그 계열은 보류한다 — 저장분
    그대로이고 이번 회차의 새 달도 붙이지 않으며, '<계열>:기준변경 보류'가 부분 실패로 남는다(.fetch_failed → ℹ️ 줄).

    변이: update_basic 의 재수집 except 블록에서 `continue` 를 지우면 평소 병합으로 넘어가 잠정 달이 붙어 빨개진다(확인).
          refetch_basic_full 의 연속성 검사 `if seq != got: raise` 를 지우면 gap 경우가 빠진 달 없이 저장돼 빨개진다(확인).
    픽스처: 이어 붙은 저장 계열(지금 data.js 모양). kosis-error 는 기간 조회가 KOSIS 오류, gap 은 2025.03 한 달이 빠진 응답
            (조회 한 조각이 비어 돌아온 회차).
    """
    stored = _stored('spliced')
    D, failed, changed, _ = _run(monkeypatch, stored, range_ok=(mode != 'kosis-error'),
                                 gap=(2025, 3) if mode == 'gap' else None)
    assert D == stored, '보류해야 할 계열이 바뀌었다'
    assert failed == ['%s:기준변경 보류' % NAME]
    assert changed == []
