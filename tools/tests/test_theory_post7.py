# -*- coding: utf-8 -*-
"""사이클 7편(금리와 집값)의 문장 전제 가드 — link7_values (2026-10-16).

본문이 못 박는 것: 금리 바닥 뒤 1년 매매 상승이 전세의 3배를 넘는다, 고금리 국면에서 매매가 전세보다 먼저·크게 꺾였다,
최근 금리가 오르는 동안 매매·전세가 함께 올랐다. 재산정·데이터 갱신으로 하나라도 뒤집히면 초안을 만들지 않아야 한다.

픽스처: 저장소의 실제 /cycle/ 정본(D.rate_overlay). 그대로 두면 통과하고, 한 항목씩 뒤집은 사본은 멈춰야 한다.
무엇을 깨뜨리면 빨개지나(실제로 확인): 첫 검사(3배)를 지우면 첫째 뒤집기가, 셋째 검사(최근 동반 상승)를 지우면 둘째 뒤집기가
빨개진다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_theory_post as T  # noqa: E402


@pytest.fixture(scope='module')
def D():
    return T.P.cycle_d()


def test_real_data_passes_and_fills_every_slot(D):
    import re
    v = T.link7_values(D)
    post = next(p for p in T.POSTS if p['n'] == 7)
    for k in set(re.findall(r'%\((\w+)\)s', post['body'])) - {'exp', 'zone', 'cycle', 'link'}:
        assert k in v, k


def test_sales_not_three_times_jeonse_in_the_low_rate_year_stops_the_draft(D):
    D2 = copy.deepcopy(D)
    r = D2['rate_overlay']
    lo = r['rate'].index(min(r['rate']))
    r['maemae'][lo + 4] = r['maemae'][lo] * 1.2           # 매매가 20%만 올랐다면(전세 8%) '세 배 넘게'가 거짓이 된다
    with pytest.raises(SystemExit):
        T.link7_values(D2)


def test_prices_falling_while_rates_rise_stops_the_draft(D):
    D2 = copy.deepcopy(D)
    r = D2['rate_overlay']
    r['maemae'][-1] = min(r['maemae'][-8:]) - 1             # 최근 금리 상승 중 매매가 내렸다면 '지금은 공급'이 거짓이 된다
    with pytest.raises(SystemExit):
        T.link7_values(D2)
