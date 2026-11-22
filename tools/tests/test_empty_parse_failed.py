# -*- coding: utf-8 -*-
"""빈 파싱(원천은 응답했는데 읽은 값이 0건)은 실패다 — `.fetch_failed`로 올려 배치 기록에 남긴다(백로그 59).

예전엔 기본통계·금리·연간 계열에서 원천이 빈 응답을 주거나 파싱 규칙이 어긋나면 0건 병합으로 조용히 끝났다.
배치 기록은 ✅였고, 그 계열이 낡은 채로 남은 것을 알 길이 없었다(2026-11-13 전수 리뷰 잠복 결함).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402


def _min_stats():
    st = {name: {'dates': [], 'series': {}} for name in U.BASIC_CONF}
    st['금리'] = {'dates': [], 'series': {}}
    return st


def _basic_run(monkeypatch, st, fetch):
    """update_basic 만 돌린다 — 다른 갱신은 건너뛰고 원천은 fetch 로 바꿔 끼운다."""
    monkeypatch.setattr(U, 'read_current_stats', lambda: st)
    monkeypatch.setattr(U, 'write_stats', lambda s: None)
    for fn in ('update_size', 'update_supply', 'update_annual'):
        monkeypatch.setattr(U, fn, lambda *a, **k: [])
    monkeypatch.setattr(U, 'drop_raw_aggregates', lambda stats: {})
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    monkeypatch.setattr(U, '_fetch_basic_one', fetch)
    failed = []
    U.update_basic(failed)
    return failed


def test_empty_basic_parse_is_a_failure(monkeypatch):
    """기본통계 원천이 행은 줬는데 읽은 값이 0건이면(파싱 규칙 어긋남) 실패로 멈추고, update_basic 이 계열을 남긴다.

    변이(실제로 확인): _fetch_basic_one 끝의 `if data and not out and not rates: raise ...` 를 지우면 두 단정이 모두
          빨개진다.
    픽스처: KOSIS 가 행은 주는데 유형(C2_NM)이 표 설정과 달라 한 행도 채택되지 않는 회차 — 항목·열 이름이 바뀐 날의 모양.
    """
    rows = [{'C1_NM': '전국', 'C1': 'c1', 'C2_NM': '다른유형', 'PRD_DE': '202606', 'DT': '1'}]
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    monkeypatch.setattr(U, 'kosis', lambda *a, **k: rows)
    with pytest.raises(RuntimeError) as e:
        U._fetch_basic_one('인허가')
    assert '빈 파싱' in str(e.value)

    def boom(name, *a, **k):
        raise RuntimeError('빈 파싱 — 원천 행 3개에서 읽은 값이 없다')
    failed = _basic_run(monkeypatch, _min_stats(), boom)
    assert '인허가' in failed, failed


def test_empty_rate_parse_is_a_failure(monkeypatch):
    """ECOS 금리 응답이 빈 행이면 update_rate 가 실패로 멈추고, update_basic 이 'rate' 를 남긴다.

    변이(실제로 확인): update_rate 의 `if not fetched: raise ...` 를 지우면 두 단정이 모두 빨개진다.
    픽스처: ECOS StatisticSearch 응답의 row 가 빈 목록.
    """
    monkeypatch.setattr(U, 'ECOS_KEY', 'x')
    monkeypatch.setattr(U, 'http_json', lambda url: {'StatisticSearch': {'row': []}})
    with pytest.raises(RuntimeError) as e:
        U.update_rate({'금리': {'dates': [], 'series': {}}})
    assert '빈 응답' in str(e.value)

    def fetch(name, *a, **k):
        return {}, {}
    failed = _basic_run(monkeypatch, _min_stats(), fetch)
    assert 'rate' in failed, failed


def test_empty_annual_parse_is_a_failure(monkeypatch):
    """연간 원천이 빈 행 목록을 주면 _fetch_annual_raw 가 실패로 멈추고, update_annual 이 계열마다 남긴다.

    변이(실제로 확인): _fetch_annual_raw 끝의 `if not out: raise ...` 를 지우면 두 단정이 모두 빨개진다.
    픽스처: KOSIS 가 빈 행 목록을 주는 회차.
    """
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    monkeypatch.setattr(U, 'kosis', lambda *a, **k: [])
    name = next(iter(U.ANNUAL_CONF))
    with pytest.raises(RuntimeError) as e:
        U._fetch_annual_raw(name)
    assert '빈 응답' in str(e.value)
    st = {n: {'dates': [], 'series': {}} for n in U.ANNUAL_CONF}
    failed = []
    U.update_annual(st, failed)
    assert set(failed) == set(U.ANNUAL_CONF), failed
