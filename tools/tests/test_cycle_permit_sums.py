# -*- coding: utf-8 -*-
"""사이클 분석이 인허가 누계를 그대로 더하지 않는다 (2026-09-15 PM 요청 ①).

인허가 계열은 '호 (연내 누계)'다. rebuild_cycle_analysis의 q_sum·y_sum·_roll12가 그 원값을
더해 고리3(매매→이듬해 인허가)과 고리4(인허가→착공)가 부푼 합산 위에 있었다(/monthly/와
같은 함정). 이제 SZ.permit_monthly()로 푼 뒤 합한다. 되돌리면 여기서 걸린다.
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sido_zones as SZ  # noqa: E402
import rebuild_cycle_analysis as RC  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def test_yearly_permits_equal_december_cumulative():
    st = RC.load_stats()
    P = RC.prep(st)
    cum = st['인허가']
    checked = 0
    for r in RC.SIDO[:4]:
        by = {d[:7]: v for d, v in zip(cum['dates'], cum['series'][r])}
        for y, v in P[r]['ypermit'].items():
            dec = by.get('%s.12' % y)
            if dec is not None:
                assert abs(v - dec) < 1e-6, '%s %s년 인허가 %s ≠ 12월 누계 %s — 누계를 더했다' % (r, y, v, dec)
                checked += 1
    assert checked > 10, '비교한 연도가 너무 적다 — 시험이 헛돈다'


def test_quarterly_permits_come_from_monthly_flows():
    st = RC.load_stats()
    P = RC.prep(st)
    mon = SZ.permit_monthly(st, '서울')
    for k, v in list(P['서울']['qpermit'].items())[:12]:
        y, q = k
        want = sum(mon['%d.%02d' % (y, m)] for m in range(3 * q - 2, 3 * q + 1))
        assert abs(v - want) < 1e-6, k


def test_source_never_feeds_raw_permits_to_flow_sums():
    src = io.open(os.path.join(ROOT, 'tools', 'rebuild_cycle_analysis.py'), encoding='utf-8').read()
    for fn in ('q_sum', 'y_sum', '_roll12'):
        assert not re.search(r"%s\(\s*PM\[" % fn, src), '%s에 인허가 누계 원값을 넣는다' % fn


def test_q4_share_is_computed_not_written():
    st = RC.load_stats()
    q = RC.permit_q4_share(st)
    assert q['share'] is not None and 0.25 < q['share'] < 0.6
    assert q['from'] < q['to']
