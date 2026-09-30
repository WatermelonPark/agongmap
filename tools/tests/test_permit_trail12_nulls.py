# -*- coding: utf-8 -*-
"""'인허가 1년'(permit_trail12)이 연초 인허가 누계 null 을 permit_monthly 와 같은 규칙(진짜 0)으로 센다(전수 리뷰 #11).

재현하는 실제 상태: KOSIS 인허가 누계의 연초 null 은 전부 진짜 0 이다(2026-09-15 전수 99/99). permit_monthly 는 그렇게
셌는데 permit_trail12 는 결측으로 봐서 (1) 전년 같은 달이 null 이면 None — 2025.01 에 대구·충북·세종의 '인허가 1년' 참고 행이
사라졌고, (2) 최신 달이 null 이면 그 지역만 전년 12월로 물러나 — 2024.01 에 대구만 '2023.12'(전년 1~12월 합 13,962, 최근 12개월
합은 12,174)를 실어 다른 지역과 기간이 섞였다.
픽스처: 2023.01~2025.01 월별 누계. A 는 2024.01·2025.01 이 null(연초 0), B 는 null 없음(대조군), C 는 연중(7월) 결측.
변이(실제로 확인): permit_trail12 를 옛 구현(최신 비null 달로 물러남 + 전년 같은 달 null 이면 None)으로 되돌리면
A 의 기준 달·값 단정이 빨개진다. 기준 달을 지역마다 정하게 바꿔도 빨개진다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sido_zones as SZ  # noqa: E402


def _stats(until):
    dates = ['%d.%02d' % (y, m) for y in (2023, 2024, 2025) for m in range(1, 13)]
    dates = dates[:dates.index(until) + 1]

    def cum(null_jan, gap=None):
        out = []
        for d in dates:
            y, m = int(d[:4]), int(d[5:])
            if (null_jan and m == 1) or d == gap:
                out.append(None)
            else:
                out.append(100.0 * m + (y - 2023))     # 누계: 매달 약 100호씩 쌓인다
        return out
    return {'인허가': {'dates': dates, 'series': {'A': cum(True), 'B': cum(False), 'C': cum(False, gap='2024.07')}}}


def test_new_year_null_is_zero_not_missing():
    for until in ('2025.01', '2024.01'):
        st = _stats(until)
        mon_a = SZ.permit_monthly(st, 'A')
        keys = sorted(mon_a)[-12:]
        v, ym = SZ.permit_trail12(st, 'A')
        assert ym == until, '%s: A 의 기준 달이 %s 로 물러났다' % (until, ym)
        assert v == sum(mon_a[k] for k in keys), (until, v)
        vb, ymb = SZ.permit_trail12(st, 'B')
        assert ymb == ym, '지역마다 기준 달이 갈렸다'
        mon_b = SZ.permit_monthly(st, 'B')
        assert vb == sum(mon_b[k] for k in sorted(mon_b)[-12:])


def test_mid_year_gap_still_folds_the_line():
    """연중 결측(누계가 쌓인 뒤의 null)은 0 이 아니다 — 그 달이 창 안이면 반쪽 계산 대신 접는다."""
    assert SZ.permit_trail12(_stats('2025.01'), 'C') == (None, None)
    v, ym = SZ.permit_trail12(_stats('2025.12'), 'C')
    assert ym == '2025.12' and v is not None
