# -*- coding: utf-8 -*-
"""월간 계열 기준월 뒤처짐 알림 (2026-09-16 PM 요청).

이 알림이 메우는 자리는 '방어선이 스스로를 못 보는 곳'이다. 미분양은 원천이 광주·전남
행을 주지 않아 그 달을 버리는데, 신선도 점검도 배치와 같은 완비 기준을 쓰므로 실패로
잡히지 않는다. 그래서 수치가 틀린 것이 아니라 **늙은 것**을 따로 본다.

⚠️ 픽스처에 지금의 계열 이름을 박지 않는다. 2026-09-11 에 모델 통합 직후 그런 시험이
   배치를 막았다. 여기서는 모양(월·분기·연간·일)과 셈만 잠근다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import month_lag as L  # noqa: E402


def _stats(**kw):
    return {name: {'dates': list(dates)} for name, dates in kw.items()}


def test_month_shapes_are_told_apart():
    assert L.month_of('2026.07') == (2026, 7)
    assert L.month_of('2026-07') == (2026, 7)
    assert L.month_of('2026.07 p)') == (2026, 7), '잠정치 표시가 붙어도 월로 읽어야 한다'
    for bad in ('2026Q2', '2024', '2026-09-07', '', None, '2026.13'):
        assert L.month_of(bad) is None, bad


def test_only_monthly_series_are_compared():
    """분기·연간·주간이 섞이면 '가장 최신 월'이 틀어진다 — 모양으로 걸러야 한다."""
    stats = _stats(a=['2026.06'], b=['2026.08'], c=['2024'], d=['2026Q3'])
    adv = {'w': {'rows': [{'p': '2026-09-07'}]}, 'm': {'rows': [{'p': '2026-08'}]}}
    got = L.monthly_months(adv, stats)
    assert got == {'a': (2026, 6), 'b': (2026, 8), 'm': (2026, 8)}


def test_lag_is_counted_in_months_across_a_year_end():
    assert L.gap((2025, 11), (2026, 2)) == 3
    assert L.gap((2026, 8), (2026, 8)) == 0


def test_only_series_behind_the_threshold_are_listed():
    months = {'ok': (2026, 8), 'one': (2026, 7), 'two': (2026, 6), 'four': (2026, 4)}
    newest, rows = L.behind(months)
    assert newest == (2026, 8)
    assert [r[0] for r in rows] == ['four', 'two'], '1개월 뒤처짐은 평상이라 싣지 않는다'
    assert rows[0][2] == 4 and rows[1][2] == 2


def test_line_names_the_series_and_the_newest_month():
    stats = _stats(느린계열=['2026.06'], 빠른계열=['2026.08'])
    s = L.line({}, stats)
    assert s.startswith(L.MARK), '실패·경고 표시를 쓰면 안 된다 — 알림이지 이상이 아니다'
    assert '월간 뒤처짐 2개월' in s and '느린계열 2026.06' in s and '최신 2026.08' in s
    assert '빠른계열' not in s


def test_no_line_when_everything_is_current():
    assert L.line({}, _stats(a=['2026.08'], b=['2026.08'])) is None
    assert L.line({}, {}) is None


def test_thresholds_are_ordered():
    assert 1 < L.MIN_MONTHS <= L.ESCALATE_MONTHS


def test_real_data_is_readable_and_agrees_with_the_stored_series():
    """저장된 data.js 로도 돌아야 한다. 값은 단정하지 않는다(배치가 매일 바꾼다)."""
    adv, sts = L.load()
    months = L.monthly_months(adv, sts)
    assert len(months) >= 5, '월간으로 잡힌 계열이 너무 적다 — 모양 판별이 헛돈다'
    for name, ym in months.items():
        assert ym == L.month_of((sts.get(name) or {}).get('dates', [None])[-1]
                                if name in sts else
                                adv[name]['rows'][-1]['p']), name


# ── 계열별 정상 시차(리뷰 2026-09-18 20번) ───────────────────────────────────
# 깨뜨리면 빨개지는 것: allowance() 가 늘 0 을 돌려주면 아래 둘 다 빨강.
# 픽스처: 감시가 GRACE_BASIC 으로 보는 계열(인허가) 하나와 기준 계열(금리) 하나.

def test_allowance_comes_from_the_watchdog_constants():
    import check_freshness as CF
    import update_adv_data as U
    assert L.SLOW_ALLOWANCE == int(round((CF.GRACE_BASIC - CF.GRACE_MONTHLY) / 30.0)) >= 1
    assert set(U.BASIC_CONF) <= L.SLOW_SERIES and '규모별' in L.SLOW_SERIES
    assert L.allowance('미분양') == 0 and L.allowance('금리') == 0, '공급·금리는 정상 시차 0 이어야 한다'


def test_normal_publication_lag_of_slow_series_is_not_a_lag():
    """인허가가 금리보다 2개월 늦은 것은 정상이다 — 매달 초 금리가 새 달로 넘어가도 알리지 않는다."""
    months = {'금리': (2026, 9), '인허가': (2026, 7), '미분양': (2026, 7)}
    _, rows = L.behind(months)
    assert [r[0] for r in rows] == ['미분양'], rows
    assert rows[0][2] == 2
    # 같은 계열이 정상보다 2개월 더 늦으면 그때 잡힌다(정상을 넘은 개월 수로 센다)
    _, rows = L.behind({'금리': (2026, 9), '인허가': (2026, 5)})
    assert rows and rows[0][0] == '인허가' and rows[0][2] == 2
