# -*- coding: utf-8 -*-
"""규모별(STATS['규모별'])의 '우리 최신'은 축 끝이 아니라 지표마다 값이 있는 마지막 달이다(전수리뷰 A-2·H2-10).

재현하는 실제 상태: 규모별 축(dates)은 표 넷(매매 B014·전세 B015·월세 B005·전환율 N0009) 시점의 합집합이다. 2026-09-28 전환율이
2026.07 을 실어 축 끝이 2026.07 이 됐는데 매매·전세·월세는 2026.06 에서 석 달째 멈춰 있었다. 감시는 매매 표 하나만 원천과 견주고
우리 최신을 축 끝으로 읽어 초록이었고(나이 상한도 12월에야 돈다), 월간 뒤처짐 알림(month_lag)도 축 끝을 읽었다.
픽스처: 그 모양의 합성 페이로드 — 축 2026.05~07, 매매·월세는 06 까지, 전세는 05 의 한 지역 한 칸만, 전환율은 07 까지.
지역 이름은 모델(WEEKLY_REGIONS)에서 가져온다. 달은 합성이라 실데이터가 앞으로 가도 판정이 같다.

변이(각각 실제로 확인):
  - update_adv_data.size_last 가 지표와 상관없이 dates[-1] 을 돌려주면 첫 시험이 빨개진다.
  - check_freshness.size_checks 가 우리 최신을 D['dates'][-1] 로 읽으면 둘째 시험이 빨개진다(매매가 원천과 같은 달로 보인다).
  - month_lag.monthly_months 의 피벗 분기를 지워 dates[-1] 을 읽으면 셋째 시험이 빨개진다.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U   # noqa: E402
import check_freshness as C   # noqa: E402
import month_lag as L         # noqa: E402

DATES = ['2026.05', '2026.06', '2026.07']
LAST = {'매매': '2026.06', '전세': '2026.05', '월세': '2026.06', '전환율': '2026.07'}


def _payload():
    """지표마다 LAST 달까지 6구간 값이 찬 페이로드. 전세는 첫 지역 한 곳만 값이 있다(한 칸이라도 있으면 그 달이 최신)."""
    regs = U.WEEKLY_REGIONS

    def ser(last, only_first=False):
        k = DATES.index(last)
        return {r: [([0.1] * 6 if i <= k and (j == 0 or not only_first) else None) for i in range(len(DATES))]
                for j, r in enumerate(regs)}
    series = {m: ser(LAST[m], only_first=(m == '전세')) for m, _, _ in U.SIZE_TBLS}
    return {'dates': list(DATES), 'metrics': [m for m, _, _ in U.SIZE_TBLS], 'regions': list(regs), 'series': series}


def test_size_last_reads_each_metric_own_last_month():
    D = _payload()
    assert U.size_last(D) == LAST
    D['series']['월세'] = {r: [None] * len(DATES) for r in D['regions']}     # 값이 하나도 없는 지표는 빠진다
    assert '월세' not in U.size_last(D) and U.size_last({}) == {}


def test_watchdog_compares_each_size_table_with_its_own_last_month(monkeypatch):
    """원천 넷이 모두 축 끝 달(2026.07)을 낼 때 — 값이 멈춘 매매·전세·월세는 뒤처짐 실패, 전환율만 통과다. 오늘은 매매 최신
    달 시작 + GRACE_BASIC + 1일(유예 밖)이고 나이 상한(끝날 + MAX_AGE_BASIC)은 아직 안 넘는다."""
    D = _payload()
    src = DATES[-1].replace('.', '')
    pre = {('규모별', m): (lambda: src) for m, _, _ in U.SIZE_TBLS}
    monkeypatch.setattr(C, 'TODAY', datetime.date(2026, 6, 1) + datetime.timedelta(days=C.GRACE_BASIC + 1))
    got = dict(zip([m for m, _, _ in U.SIZE_TBLS], C.size_checks(D, pre)))
    for m in ('매매', '월세'):
        assert got[m] and (C.SIZE_LABEL % m) in got[m] and '라이브 2026.06 < 원천 %s' % src in got[m], got
    assert got['전세'] and '라이브 2026.05' in got['전세'], got
    assert got['전환율'] is None, got


def test_month_lag_reads_the_most_lagging_size_metric():
    stats = {'규모별': _payload(), '금리': {'dates': ['2026.10']}}
    assert L.monthly_months({}, stats) == {'규모별': (2026, 5), '금리': (2026, 10)}
    s = L.line({}, stats)
    assert s and '규모별 2026.05' in s, s
