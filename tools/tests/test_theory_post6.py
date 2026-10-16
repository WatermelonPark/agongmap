# -*- coding: utf-8 -*-
"""사이클 6편(입주 → 전세, 역전세)의 문장 전제 가드 — link6_values (2026-10-16).

본문은 다섯 가지를 문장으로 못 박는다: 서울은 효과가 확인되지 않는다, 수도권으로 묶으면 서울보다 강하다, 광역시가
도보다 강하다, 확인된 수도권 시도는 한 분기 뒤에 반응한다, 가장 강한 시도(대전)가 앞으로 입주가 적정물량을 넘는 곳이다.
재산정으로 하나라도 뒤집히면 초안을 만들지 않아야 한다(3편 check_sync_claims 와 같은 원칙).

픽스처: 저장소의 실제 /cycle/ 정본(P.cycle_d())과 ADV. 그대로 두면 통과하고, 한 항목씩 뒤집은 사본은 멈춰야 한다.
무엇을 깨뜨리면 빨개지나(실제로 확인): link6_values 에서 서울 유의 검사를 지우면 첫째 뒤집기 시험이, 가장 강한 시도 검사를
지우면 둘째가 빨개진다.
"""
import copy
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_theory_post as T  # noqa: E402


@pytest.fixture(scope='module')
def real():
    adv, sts = T.M.load()
    return T.P.cycle_d(), adv, sts


def test_real_data_passes_and_fills_every_slot(real):
    D, adv, sts = real
    v = T.link6_values(D, adv, sts)
    post = next(p for p in T.POSTS if p['n'] == 6)
    import re
    for k in set(re.findall(r'%\((\w+)\)s', post['body'])) - {'exp', 'zone', 'cycle', 'link'}:
        assert k in v, k


def test_seoul_turning_significant_stops_the_draft(real):
    D, adv, sts = real
    D2 = copy.deepcopy(D)
    next(x for x in D2['link6_regional'] if x['region'] == '서울')['sig'] = True
    with pytest.raises(SystemExit):
        T.link6_values(D2, adv, sts)


def test_strongest_region_outside_the_oversupply_list_stops_the_draft(real):
    D, adv, sts = real
    D2 = copy.deepcopy(D)
    x = next(x for x in D2['link6_regional'] if x['region'] == '서울')
    x['r'] = -0.9                      # 서울이 가장 강해진 가상 재산정(서울은 입주 과잉 지역이 아니다)
    with pytest.raises(SystemExit):
        T.link6_values(D2, adv, sts)
