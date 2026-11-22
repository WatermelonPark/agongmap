# -*- coding: utf-8 -*-
"""시도 입주물량 연도 표·그림의 '창 경계 해'는 덜 찬 분기 합이다(백로그 59).

앞으로 3년 창은 달력 1월에서 시작하지 않는다(예: 2026Q3~2029Q2). 그래서 마지막 해(2029)는 두 분기만 들어오는데,
표는 그 해를 그냥 '예정'으로, 그림은 한 해 막대처럼 보여 줬다. 이제 표의 구분에 '(일부 분기)'를 달고,
그림에서는 그 해를 뺀 사실을 읽어 줄 글에 적는다. 값 자체는 원천 합 그대로 둔다(비율로 쪼개지 않는다).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import content_tables as CT  # noqa: E402


def _data():
    return CT.load()


def _quarters(data, key):
    """시도 키의 연도별 분기 수 — 창 경계 해를 데이터에서 찾는다(날짜를 박지 않는다)."""
    qn = {}
    for p, _v, _e in CT._series_rows(data['occupancy'], key):
        y = str(p)[:4]
        qn[y] = qn.get(y, 0) + 1
    return qn


def test_partial_boundary_year_is_marked_in_the_table():
    """분기가 4개 미만인 해만 '(일부 분기)'로 적고, 꽉 찬 해는 예전 표기 그대로 둔다.

    변이(실제로 확인): moveins 의 `if qn[y] < 4` 표시를 지우면 이 시험이 빨개진다.
    픽스처: 저장소 실데이터(앞으로 3년 창이 달력 연도를 걸쳐 끝나는 모양).
    """
    data = _data()
    qn = _quarters(data, '서울')
    _head, rows, note = CT.moveins(data, '서울')
    part = [r for r in rows if '일부 분기' in r[2]]
    assert part, '창 경계의 덜 찬 해가 표에 없다 — 이번 회차 자료가 창을 다 채웠는지 본다'
    for r in part:
        assert qn[r[0]] < 4, (r, qn[r[0]])
    full = [r for r in rows if '일부 분기' not in r[2]]
    assert full and all(qn[r[0]] == 4 for r in full), '꽉 찬 해를 일부로 표시했다'
    assert '들어온 분기만 합산' in note, note


def test_chart_drops_the_partial_year_and_says_so():
    """그림 막대에서는 덜 찬 해를 빼고, 뺐다는 사실을 읽어 줄 글에 적는다 — 반쪽 해를 한 해처럼 그리지 않는다.

    변이(실제로 확인): _chart_moveins 의 `if y not in part` 를 지우면 이 시험이 빨개진다.
    픽스처: 같은 실데이터의 시도 차트.
    """
    data = _data()
    qn = _quarters(data, '서울')
    ch = CT._chart_moveins(data, '서울')
    ys = [p[0] for p in ch['series'][0]['points']]
    assert ys and all(qn[y] == 4 for y in ys), ys
    part = [y for y, n in qn.items() if n < 4]
    assert part, '창 경계의 덜 찬 해가 데이터에 없다 — 시험이 헛돈다'
    assert all(y not in ys for y in part), (ys, part)
    assert '덜 찬 해' in ch['alt'] and all(y in ch['alt'] for y in part), ch['alt']
    assert ch['cards'], '카드가 비었다 — 그림 부품이 통째로 빠졌다'
