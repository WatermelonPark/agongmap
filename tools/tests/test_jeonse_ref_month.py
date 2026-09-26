# -*- coding: utf-8 -*-
"""전세가율 최신 열이 일부만 찬 달에도 두 생성기가 죽지 않고 직전 완비 달로 굽는다(2026-09-26 데이터 감사).

merge_basic 은 새 달을 전 지역 None 열로 먼저 만들고 원천이 준 지역만 채운다. 원천이 행 이름을 바꾸면(2026.06
지방권, 2026.07 6대광역시·9개도가 실제로 그렇게 비었다) 최신 열에 필요한 지역이 빌 수 있다. 예전엔 두 생성기가
dates[-1] 을 그대로 읽어 build_jeonse 가 TypeError(전국 None), build_jratio 가 0 나누기·RuntimeError 로 죽었고,
둘 다 배치에서 `exit 1` 이라 그날 데이터 커밋 전체(주간 시세 포함)가 막혔다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - build_jeonse 의 `li = jeonse_ref_index(j, JEONSE_NEED)` 를 `li = len(dates) - 1` 로 되돌리면 → TypeError 로 빨강
  - build_jratio 의 `k = I.jeonse_ref_index(D, SIDO)` 를 `k = len(D['dates']) - 1` 로 되돌리면 → 0 나누기로 빨강
  - jeonse_ref_index 가 완비 여부를 안 보고 마지막 열을 돌려주면 → 두 단정이 함께 빨강
  - 완비 달이 없을 때 RuntimeError 대신 마지막 열로 넘어가면 → 마지막 시험이 빨강
픽스처: 저장소의 실제 전세가율 계열(data-core.js·data.js) 뒤에, 감사가 재현한 모양 그대로 서울만 찬 새 달을
하나 붙인 상태. 기대하는 달은 하드코딩하지 않고 실제 계열의 마지막 달에서 뽑는다.
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import refresh_cycle_data as RF  # noqa: E402


def _next_month(lab):
    y, m = (int(x) for x in re.match(r'^(\d{4})\.(\d{2})', lab).groups())
    return '%04d.%02d' % (y + (m == 12), m % 12 + 1)


def _with_partial_month(block, filled=('서울',)):
    """merge_basic 이 새 달을 만든 직후의 모양 — 새 열은 전부 None, 원천이 준 지역만 채운다."""
    b = copy.deepcopy(block)
    new = _next_month(b['dates'][-1])
    b['dates'].append(new)
    for r, s in b['series'].items():
        s.append(s[-1] if r in filled else None)
    return b, new


def test_jeonse_page_holds_a_partially_filled_month():
    _, sts = I.load()
    real_last = sts['전세가율']['dates'][-1]
    part, new = _with_partial_month(sts['전세가율'])
    html, _ = I.build_jeonse(dict(sts, 전세가율=part))
    assert '%s 기준' % real_last in html, '직전 완비 달(%s)로 굽지 않았다' % real_last
    assert '%s 기준' % new not in html, '반쯤 찬 달(%s)을 기준월로 찍었다' % new


def test_cycle_chart_holds_the_same_month_as_the_jeonse_page():
    S = RF.load_stats()
    real_last = S['전세가율']['dates'][-1]
    part, _ = _with_partial_month(S['전세가율'])
    lvl, sudo, jib, prd = RF.build_jratio(dict(S, 전세가율=part))
    assert prd == real_last, (prd, real_last)
    assert {x['region'] for x in lvl} == set(RF.SIDO), '보류한 달 대신 읽은 달에서 시도가 빠졌다'
    assert RF.jratio_prose(lvl, prd)['jr_prd'] == real_last
    # 두 페이지가 같은 규칙으로 같은 달을 고른다(전국까지 본 /jeonse-ratio/ 와 시도만 본 /cycle/).
    _, sts = I.load()
    pj, _ = _with_partial_month(sts['전세가율'])
    assert pj['dates'][I.jeonse_ref_index(pj, I.JEONSE_NEED)] == prd


def test_no_complete_month_stops_with_a_clear_error():
    _, sts = I.load()
    b = copy.deepcopy(sts['전세가율'])
    b['series']['서울'] = [None] * len(b['dates'])
    with pytest.raises(RuntimeError, match='전부 채워진 달이 없다'):
        I.jeonse_ref_index(b, I.JEONSE_NEED)
