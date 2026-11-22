# -*- coding: utf-8 -*-
"""광주·전남 주택보급률을 주택수·가구수로 다시 계산해 접는다(백로그 52, 대표 결정 2026-10-18 D3).

보급률은 비율이라 합도 가중평균(W_GJ)도 원천으로 검산되지 않는다. (주택수 합) ÷ (가구수 합) × 100 만이
원천 보급률을 재현한다(로컬 14 확인, 검산 30개 가운데 29개 일치. 원천도 시도 합으로 전국을 만든다).
원천이 통합 행('전남광주')을 직접 주면 그 값을 쓴다.
"""
import copy
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import merge_regions as MR  # noqa: E402
import update_adv_data as U  # noqa: E402

_PARTS = {'2024': {'광주': 106.4, '전남': 113.0}}


def test_ratio_is_housing_over_households_of_both_fragments():
    """(100+200) ÷ (80+160) × 100 = 125.0 — 더도 가중평균도 아니다.

    변이(실제로 확인): fold_housing_ratio 의 계산을 단순 합(주택수만)으로 바꾸면 300.0 이 나와 빨개진다.
    픽스처: 광주·전남 조각값과 그 둘을 합쳐 만든 통합 보급률.
    """
    out = copy.deepcopy(_PARTS)
    n = MR.fold_housing_ratio(out, {'2024': {'광주': 100.0, '전남': 200.0}},
                              {'2024': {'광주': 80.0, '전남': 160.0}})
    assert n == 1 and out['2024'] == {'전남광주': 125.0}, out
    assert '광주' not in out['2024'] and '전남' not in out['2024']


def test_no_value_when_a_fragment_or_a_part_is_missing():
    """주택수·가구수 한 조각이라도 없으면 통합 값을 만들지 않는다(없는 쪽 0 금지).

    변이(실제로 확인): all(...) 검사를 지우면 한 조각만으로도 125.0 이 만들어져 빨개진다.
    """
    out = copy.deepcopy(_PARTS)
    MR.fold_housing_ratio(out, {'2024': {'광주': 100.0}}, {'2024': {'광주': 80.0, '전남': 160.0}})
    assert out['2024'] == {}, out
    out = copy.deepcopy(_PARTS)
    MR.fold_housing_ratio(out, {'2024': {'광주': 100.0, '전남': 200.0}}, {'2024': {}})
    assert out['2024'] == {}, out


def test_source_total_row_wins():
    """원천이 통합 행을 직접 주면 그 값을 쓴다(우리 계산보다 우선)."""
    out = {'2024': {'전남광주': 110.1, '광주': 1.0, '전남': 2.0}}
    MR.fold_housing_ratio(out, {'2024': {'광주': 1.0, '전남': 2.0}}, {'2024': {'광주': 1.0, '전남': 2.0}})
    assert out['2024'] == {'전남광주': 110.1}, out


def test_update_annual_recomputes_the_ratio_and_does_not_store_the_parts(monkeypatch):
    """배치 update_annual 이 보급률을 비율로 접고, 주택수·가구수는 재료로만 받아 **저장 계열로 늘리지 않는다**.

    변이(실제로 확인): fold_annual_fetched 의 보급률 분기를 없애면(옛 _fold_gj) 전남광주가 219.4 로 나와 빨개진다.
    픽스처: 보급률 계열만 있는 저장분 + 세 항목 원자료(주택수·가구수 포함).
    """
    stats = {'보급률': {'dates': ['2024'], 'unit': '%',
                        'series': {'광주': [106.4], '전남': [113.0], '전남광주': [None], '서울': [90.0]}}}
    raw = {'보급률': {'2024': {'광주': 106.4, '전남': 113.0, '서울': 90.0}},
           '주택수': {'2024': {'광주': 100.0, '전남': 200.0, '서울': 900.0}},
           '가구수': {'2024': {'광주': 80.0, '전남': 160.0, '서울': 800.0}}}
    calls = []

    def fake(name, years=None, cfg=None):
        calls.append(name)
        return copy.deepcopy(raw[name])

    monkeypatch.setattr(U, '_fetch_annual_raw', fake)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    monkeypatch.setattr(U, 'ANNUAL_CONF', {k: U.ANNUAL_CONF[k] for k in ('보급률',)})
    failed = []
    U.update_annual(stats, failed=failed)
    assert not failed, failed
    i = stats['보급률']['dates'].index('2024')
    assert stats['보급률']['series']['전남광주'][i] == 125.0, stats['보급률']
    assert '주택수' not in stats and '가구수' not in stats, '재료 계열을 저장 STATS 에 늘렸다'
    assert set(calls) == {'보급률', '주택수', '가구수'}, calls


def test_fetch_annual_one_also_folds_the_ratio(monkeypatch):
    """`--heal-annual 보급률` 이 쓰는 _fetch_annual_one 도 같은 비율 계산을 한다 — 이력 재수집 경로(백로그 52).

    변이(실제로 확인): _fetch_annual_one 이 fold_annual 을 그대로 부르면 219.4 가 나와 빨개진다.
    """
    raw = {'보급률': {'2024': {'광주': 106.4, '전남': 113.0}},
           '주택수': {'2024': {'광주': 100.0, '전남': 200.0}},
           '가구수': {'2024': {'광주': 80.0, '전남': 160.0}}}

    def fake(name, years=None, cfg=None):
        return copy.deepcopy(raw[name])

    monkeypatch.setattr(U, '_fetch_annual_raw', fake)
    got = U._fetch_annual_one('보급률', 2)
    assert got == {'2024': {'전남광주': 125.0}}, got
