# -*- coding: utf-8 -*-
"""원고 값 자리표 v:cum(최근 N주 누적 변동률, content_tables.cum — 2026-11-19).

왜 이 시험이 있나. 단지·GTX 글이 '최근 4주 +1.8%'·'12주 +3.85%' 를 손으로 적어, 다음 주 배치부터 글만 옛 숫자를 말했다(CLAUDE.md
'숫자는 자리표로만'). v:cum 은 주간 정본(weekly_moves.cum_window·cum_change)으로 세므로 시도 리포트 12주 누적 칸과 같은 값이어야
하고, 최신 회차의 창을 잡지 못하면(원천이 기준 주를 거른 회차) 값을 지어내지 않고 앞 회차로 물러서며 그 조사일을 밝혀야 한다.

무엇을 바꾸면 빨개지나(실제로 넣어 확인했다):
  - cum 이 WM.cum_change 대신 주간 값을 단순히 더하면 → test_matches_compounded_weekly_changes
  - cum_window 대신 rows[-weeks:] 로 창을 잡으면(거른 주가 있으면 N+1 주가 된다) → test_skipped_base_week_steps_back
  - 물러선 값에 '(… 조사까지)' 를 붙이지 않으면 → test_skipped_base_week_steps_back
  - value() 가 '전세' 인자를 버리고 늘 매매로 세면 → test_metric_and_shape
픽스처: 합성 주간 자료(시군구 하나, 매주 +1%·전세 +2% — 4주 누적은 복리 4.06%·8.24%), 기준 주 한 회차를 뺀 같은 자료(원천처럼
다음 회차가 두 주 치 변동을 싣는다),
그리고 저장소 실데이터의 서울 노원구 12주(시도 리포트 weekly_moves.zone_table 의 ma12 와 대조 — 값은 데이터에서 유도).
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import content_tables as CT   # noqa: E402
import weekly_moves as WM     # noqa: E402


def _data(n=20, drop=None):
    start = datetime.date(2026, 6, 1)
    rows = []
    for k in range(n):
        if drop is not None and k == drop:
            continue
        two = drop is not None and k == drop + 1      # 거른 주 다음 회차는 전 회차 대비라 두 주 치(1.01² − 1)를 싣는다
        rows.append({'p': (start + datetime.timedelta(days=7 * k)).isoformat(),
                     'ma': [2.01 if two else 1.0], 'je': [4.04 if two else 2.0]})
    return {'weekly': {'regions': [], 'rows': []},
            'sgg': {'codes': ['X1'], 'rows': rows}}


@pytest.fixture
def one_sgg(monkeypatch):
    monkeypatch.setattr(CT, 'sgg_codes', lambda data, name: [('X1', '가상 시험구')] if name == '가상 시험구' else [])


def test_matches_compounded_weekly_changes(one_sgg):
    assert CT.value(_data(), 'cum', ['가상 시험구', '4']) == '+4.06%', '주간 변동률을 이어 곱해야 한다(더하면 +4.00%)'


def test_metric_and_shape(one_sgg):
    assert CT.value(_data(), 'cum', ['가상 시험구', '전세', '4']) == '+8.24%'
    for bad in (['가상 시험구'], ['가상 시험구', '전세'], ['가상 시험구', '월세', '4'], ['가상 시험구', '0']):
        with pytest.raises(CT.TableError):
            CT.value(_data(), 'cum', bad)
    with pytest.raises(CT.TableError):
        CT.table(_data(), 'cum', ['가상 시험구', '4'])


def test_skipped_base_week_steps_back(one_sgg):
    """마지막 행이 k=19 일 때 4주 창의 기준 주는 k=15 — 그 회차를 원천이 걸렀으면 최신 회차로 셀 수 없다(5주 치가 실린다)."""
    got = CT.value(_data(drop=15), 'cum', ['가상 시험구', '4'])
    last_ok = datetime.date(2026, 6, 1) + datetime.timedelta(days=7 * 18)
    assert got.startswith('+4.06%(') and got.endswith('조사까지)'), got
    assert CT._kdate(last_ok.isoformat()) in got, '물러선 회차의 조사일을 밝혀야 한다: %s' % got


def test_real_data_matches_zone_report():
    data = CT.load()
    S = data.get('sgg') or {}
    got = CT.sgg_codes(data, '서울 노원구')
    if not got or got[0][0] not in (S.get('codes') or []):
        pytest.skip('노원구 주간 자료가 없다')
    rows = S['rows']
    i = S['codes'].index(got[0][0])
    want = WM.cum_change(rows, WM.cum_window(rows, WM.CUM_WEEKS), i, 'ma')
    if want is None:
        pytest.skip('최신 회차의 12주 창이 비었다(원천이 기준 주를 거른 회차)')
    assert CT.value(data, 'cum', ['서울 노원구', str(WM.CUM_WEEKS)]) == CT.pct(want, 2) + '%'
