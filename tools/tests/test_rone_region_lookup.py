# -*- coding: utf-8 -*-
"""R-ONE 계층에서 우리 지역을 집는 규칙 하나(update_adv_data.rone_sido_key)를 주간·월간 수집과 감시가 함께 쓰는지, 그리고
계층이 바뀐 응답에서도 지역마다 **맞는 행의 값**이 열에 실리는지 행동으로 본다(전수리뷰 A-7).

재현하는 실제 상태: 2026-08-07 감사 — R-ONE 월간표가 2025-05 부터 '광주'·'전남'을 '전남광주>광주'·'전남광주>전남'으로 옮겼는데
월간 수집이 평평한 이름만 찾아 두 지역이 15개월 결측이었다. 그 뒤 규칙을 '평평한 이름, 없으면 가장 얕은 >이름'으로 고쳤지만
주간·월간 클로저 둘과 감시의 거울 하나, 세 벌로 흩어졌고 일치 시험은 원문 문자열 포함만 봐서 월간 쪽 별칭 하나만
{'지방': '지방'} 으로 바뀌어도(월간 '지방' 열 통째 None) 관련 시험 151개가 초록이었다.
픽스처: R-ONE 응답 모양(CLS_FULLNM·CLS_ID·시점·DTA_VAL) — '지방'은 원천 이름 '지방권', 시도 둘은 '수도권>' 밑으로 옮겨진 계층,
한 시도는 '지방권>X' 와 같은 이름의 더 깊은 시군구 행 '지방권>X>X'(값이 다르다)를 함께 둔다, 통합 지역(전남광주)은 평평한 행과
옛 두 조각(광주·전남) 하위 행을 함께 준다. 지역 이름은 모델(WEEKLY_REGIONS·sido_zones)과 merge_regions 정본에서 가져온다.

변이(각각 실제로 확인):
  - rone_sido_key 의 min(..) 을 max(..) 로 바꾸면 깊은 시군구 행을 집어 주간·월간 시험과 규칙 시험이 빨개진다.
  - fetch_monthly_rone 의 sido() 를 별칭 {'지방': '지방'} 을 쓰는 옛 클로저로 되돌리면 월간 시험만 빨개진다('지방' 열 None).
  - fetch_weekly_rone 의 sido() 를 평평한 이름만 찾게 바꾸면 주간 시험이 빨개진다(옮겨진 두 시도·'지방' None).
  - check_freshness 의 `_sido_lookup = U.rone_sido_key` 를 따로 적은 함수로 바꾸면 감시 동일성 시험이 빨개진다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U   # noqa: E402
import check_freshness as C   # noqa: E402
import sido_zones as SZ       # noqa: E402
from merge_regions import SRC, DST  # noqa: E402

SIDO = [z for z in SZ.ORDER if z not in SZ.AGG and z != DST]
MOVED = SIDO[1:3]          # '수도권>' 밑으로 옮겨진 시도 둘(R-ONE 이 상위 묶음을 새로 만든 회차의 모양)
DEEP = SIDO[3]             # 같은 이름의 더 깊은 시군구 행이 있는 시도


def _paths():
    """{우리 지역: 원천에서 그 지역 값이 실린 행 이름}, 그리고 응답에만 있는 다른 행들(미끼)."""
    want, extra = {}, []
    for r in U.WEEKLY_REGIONS:
        if r in U.RONE_ALIAS:
            want[r] = U.RONE_ALIAS[r]
        elif r in MOVED:
            want[r] = '수도권>' + r
        elif r == DEEP:
            want[r] = '지방권>' + r
            extra.append('지방권>%s>%s' % (r, r))          # 깊은 쪽 미끼 — 얕은 것을 집어야 한다
        else:
            want[r] = r
    extra += ['%s>%s' % (DST, p) for p in SRC]                 # 통합 지역의 옛 두 조각(하위 행)
    extra += ['서울>강북지역>도심권>종로구', '서울>강남지역>동남권>강남구']
    return want, extra


def test_rule_picks_flat_then_shallowest_and_the_watchdog_uses_the_same_function():
    want, extra = _paths()
    names = list(want.values()) + extra
    for r, path in want.items():
        assert U.rone_sido_key(names, r) == path, r
        assert U.rone_sido_key({n: 0 for n in names}, r) == path, '사전(한 시점 값)으로 받아도 같아야 한다 — %s' % r
    assert U.rone_sido_key(names, '없는지역') is None
    assert C._sido_lookup is U.rone_sido_key, '감시가 배치와 다른 함수로 지역을 찾는다(거울을 다시 두지 말 것)'


def _rows(periods, field, tables):
    """tables 의 표마다 R-ONE 응답 행 — 행 이름마다 값이 달라 어느 행을 집었는지 드러난다."""
    want, extra = _paths()
    names = sorted(set(want.values()) | set(extra))
    book = {}
    for t, tbl in enumerate(tables):
        rows = []
        for k, p in enumerate(periods):
            for j, n in enumerate(names):
                rows.append({'CLS_FULLNM': n, 'CLS_ID': 70000 + j, field: p,
                             'DTA_VAL': str(100 + k * (j + 1) * (t + 1) / 10.0)})
        book[tbl] = rows
    return book, names


def _chg(names, path, t):
    j = names.index(path)
    a, b = 100.0, 100 + (j + 1) * (t + 1) / 10.0
    return round((b / a - 1) * 100, 4)


def _fake(monkeypatch, book):
    monkeypatch.setattr(U, '_rone_recent_rows',
                        lambda tbl, need, cycle='WK', since=None: [dict(r) for r in book[tbl]])
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)


def test_weekly_fetch_puts_each_region_from_its_own_row(monkeypatch):
    tables = [U.RONE_TBL['maega'], U.RONE_TBL['jeonse']]
    book, names = _rows(['2026-10-05', '2026-10-12'], 'WRTTIME_DESC', tables)
    _fake(monkeypatch, book)
    got = U.fetch_weekly_rone(1)
    want, _ = _paths()
    row = got['rows'][-1]
    assert got['regions'] == U.WEEKLY_REGIONS and row['p'] == '2026-10-12'
    for i, r in enumerate(U.WEEKLY_REGIONS):
        assert row['ma'][i] == _chg(names, want[r], 0), '주간 매매 %s 가 다른 행(또는 None)' % r
        assert row['je'][i] == _chg(names, want[r], 1), '주간 전세 %s 가 다른 행(또는 None)' % r
    assert got['seoul']['regions'] == ['강남구', '종로구']


def test_monthly_fetch_puts_each_region_from_its_own_row(monkeypatch):
    tables = [U.RONE_MONTHLY_TBL[k] for k in ('maega', 'jeonse', 'wolse')]
    book, names = _rows(['202608', '202609'], 'WRTTIME_IDTFR_ID', tables)
    _fake(monkeypatch, book)
    got = U.fetch_monthly_rone(1)
    want, _ = _paths()
    row = got['rows'][-1]
    assert got['regions'] == U.WEEKLY_REGIONS and row['p'] == '2026-09'
    for i, r in enumerate(U.WEEKLY_REGIONS):
        for f, t in (('ma', 0), ('je', 1), ('wo', 2)):
            assert row[f][i] == _chg(names, want[r], t), '월간 %s %s 가 다른 행(또는 None)' % (f, r)
    assert got['seoul']['regions'] == ['강남구', '종로구']
