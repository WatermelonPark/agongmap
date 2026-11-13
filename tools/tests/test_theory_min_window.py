# -*- coding: utf-8 -*-
"""5편 가드의 '가장 적은 네 분기'(theory_link4.min_window)는 올해 1분기부터 훑는다(블로그 초안 도구 리뷰 2026-10-05 D5).

블로그 초안 도구는 2026-11-13 에 지웠고(가드만 남겼다) 그 도구의 리뷰 시험(D1·D2·D4·series_links)도 함께 지웠다. min_window 는 5편
가드(theory_guards.guard_values → theory_link4.link4_numbers)가 쓰므로 남긴다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - theory_link4.min_window 를 추정 분기만 훑게(start 를 첫 추정 분기로) 되돌리면 → test_min_window_includes_this_year
    (D5, 2026.08 데이터에서 231,328 > 215,877). min_window 가 시작 분기를 빼고 훑으면(`>= start` → `> start`) 실데이터 대조
    test_min4_window_is_not_above_any_full_year 도 빨갛다(2026.08 데이터에서 2026Q2~2027Q1 218,768 > 2026년 215,877)

픽스처가 재현하는 실제 상태: 2026Q1~Q2 실적이 낮고 2026Q3 부터 추정인 합성 분기 계열(2026.08 데이터의 모양), 그리고 저장소 data.js 그대로.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import theory_link4 as L4  # noqa: E402


def test_min_window_includes_this_year():
    v = {'2025Q4': 60, '2026Q1': 50, '2026Q2': 40, '2026Q3': 36, '2026Q4': 89,          # 2026Q1~Q2 실적
         '2027Q1': 53, '2027Q2': 54, '2027Q3': 54, '2027Q4': 98,
         '2028Q1': 26, '2028Q2': 58, '2028Q3': 57, '2028Q4': 91}
    rows = [{'p': p, 'v': [x]} for p, x in sorted(v.items())]
    a, b, s = L4.min_window(rows, '2026Q1')
    assert (a, b, s) == ('2026Q1', '2026Q4', 215), (a, b, s)
    year = {y: sum(x for p, x in v.items() if p.startswith(y)) for y in ('2026', '2027', '2028')}
    assert s <= min(year.values()), '가장 적은 네 분기가 어느 해 네 분기보다 많다 — 앞 문단 올해 입주와 어긋난다'


def test_min4_window_is_not_above_any_full_year():
    """실데이터 대조(D5). 5편 '가장 적은 네 분기'(min_window)는 같은 입주 계열(과거 실적 + 이후 추정)을 올해 1분기부터 훑으므로,
    그 범위의 어느 해 네 분기 합보다도 크지 않다 — 앞 문단 '올해 입주'(OY)와 어긋나지 않는다.

    link4_numbers 를 거치지 않는다(전수리뷰 T1-7): 그 함수는 5편 본문이 2026년 데이터를 전제해 2027년 자료부터 늘 Link4ClaimError 로
    빠지고, 예전 시험은 그때 조용히 return 해 이 대조가 영영 꺼졌다. 시작 분기는 데이터에서 유도한다(판정 L 분기의 해 1분기 = 실적이
    든 올해 — 5편의 '올해 1분기부터'). 늘 단정한다: 범위 안에 네 분기가 다 찬 해가 없으면 그것도 실패다.
    픽스처: 저장소 data.js 의 ADV.occupancy(전국 열)·ADV.sido.L 그대로."""
    import make_sido_pages as M
    adv, _ = M.load()
    rows = adv['occupancy']['rows']
    start = adv['sido']['L'][:4] + 'Q1'
    a, b, s = L4.min_window(rows, start)
    years = {}
    for r in rows:
        if r['p'] >= start:
            years.setdefault(r['p'][:4], []).append(r['v'][0])
    full = {y: sum(v) for y, v in years.items() if len(v) == 4}
    assert full, '훑은 범위에 네 분기가 다 찬 해가 없다 — 대조가 헛돈다: %s' % sorted(years)
    assert all(s <= v + 1e-6 for v in full.values()), (a, b, s, full)
