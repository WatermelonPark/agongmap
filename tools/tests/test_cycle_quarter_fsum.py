# -*- coding: utf-8 -*-
"""/cycle/ 분기 평균이 파이썬 판에 따라 갈리지 않는다(2026-09-26 데이터 감사).

파이썬 3.12 부터 내장 sum() 이 실수에 보정 합산을 한다. 3.11 은 왼쪽부터 그냥 더한다. 분기 평균이 .x5
경계에 걸리면 반올림이 뒤집혀, 같은 data.js 로 개발 컨테이너(3.11)와 배치(3.12)가 다른 값을 구웠다 —
수도권 2011Q1 매매 87.8↔87.9, 2011Q4 85.6↔85.5, CD 금리 2016Q3 1.3↔1.4. 2026-08-08~09-18 사이 봇 커밋과
사람 커밋이 이 세 칸을 번갈아 뒤집었다. refresh_cycle_data 는 math.fsum 을 써서 판과 무관하게
배치(3.12)가 굽던 값과 같은 값을 낸다.

시험은 모듈 전역에 '왼쪽부터 더하는 sum'(3.11 의 동작)을 끼워 넣고 분기 평균을 구한다. 전역 이름이 내장보다
먼저 찾아지므로, 코드가 내장 sum() 으로 돌아가면 3.12 에서도 3.11 의 답이 나온다.

무엇을 깨뜨리면 빨개지나(실제로 확인): quarterly() 의 `math.fsum(a)` 를 `sum(a)` 로 되돌리면 87.9 자리에
87.8, 1.4 자리에 1.3 이 나와 빨개진다(3.12 가상환경에서 확인).
픽스처: 감사가 찾은 실제 월별 값 — 수도권 매매지수 2011.01~03(87.21, 88.19, 88.15)과 CD(91일) 금리
2016.07~09(1.36, 1.35, 1.34). 저장소에 굽혀 있는 값(배치 3.12 산출)이 87.9 와 1.4 다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import refresh_cycle_data as RF  # noqa: E402


def _left_to_right_sum(xs, start=0):
    """파이썬 3.11 까지의 내장 sum() — 보정 없이 왼쪽부터 더한다."""
    t = start
    for x in xs:
        t = t + x
    return t


def test_quarter_mean_does_not_depend_on_the_python_version(monkeypatch):
    # 픽스처가 정말 경계에 걸려 있는지 먼저 본다 — 아니면 시험이 아무것도 못 가른다.
    assert round(_left_to_right_sum([87.21, 88.19, 88.15]) / 3, 1) == 87.8
    monkeypatch.setattr(RF, 'sum', _left_to_right_sum, raising=False)
    ma = {'dates': ['2011.01', '2011.02', '2011.03'], 'series': {'수도권': [87.21, 88.19, 88.15]}}
    assert RF.quarterly(ma, '수도권', RF.ZONES_FROM) == {2011.0: 87.9}
    cd = {'dates': ['2016.07', '2016.08', '2016.09'], 'series': {'CD(91일)': [1.36, 1.35, 1.34]}}
    assert RF.quarterly(cd, 'CD(91일)', RF.OVERLAY_FROM) == {2016.5: 1.4}


def test_capital_and_rest_means_use_the_same_sum(monkeypatch):
    """build_jratio 의 수도권·지방 평균도 같은 합산을 쓴다. 코드에 내장 sum() 이 남아 있으면 끼워 넣은
    가짜가 불려 빨개진다(변이: 두 평균 중 하나를 `sum(` 으로 되돌리면 빨강, 실제로 확인).
    픽스처: 모델의 모든 시도에 값이 있는 한 달짜리 전세가율."""
    called = []

    def spy(xs, start=0):
        called.append(1)
        return _left_to_right_sum(xs, start)
    monkeypatch.setattr(RF, 'sum', spy, raising=False)
    S = {'전세가율': {'dates': ['2026.07'], 'series': {r: [60.0 + i] for i, r in enumerate(RF.SIDO)}}}
    RF.build_jratio(S)
    assert not called, 'build_jratio 가 내장 sum() 으로 평균을 낸다 — 판에 따라 값이 갈린다'
