# -*- coding: utf-8 -*-
"""전세가율 최신 열이 일부만 찬 달에도 두 생성기가 죽지 않고 직전 완비 달로 굽는다(2026-09-26 데이터 감사).

merge_basic 은 새 달을 전 지역 None 열로 먼저 만들고 원천이 준 지역만 채운다. 원천이 행 이름을 바꾸면(2026.06
지방권, 2026.07 6대광역시·9개도가 실제로 그렇게 비었다) 최신 열에 필요한 지역이 빌 수 있다. 예전엔 두 생성기가
dates[-1] 을 그대로 읽어 build_jeonse 가 TypeError(전국 None), build_jratio 가 0 나누기·RuntimeError 로 죽었고,
둘 다 배치에서 `exit 1` 이라 그날 데이터 커밋 전체(주간 시세 포함)가 막혔다.

이 시험은 배치 게이트 안에서 돈다 — 즉 **생성기가 방금 보류한 바로 그 data.js** 를 읽는다. 그래서 기대하는 달을
실제 계열의 dates[-1] 에서 뽑으면 안 된다. 최신 열이 반쯤 찬 날(이 수정이 지키려는 바로 그날) 생성기는 직전 완비
달로 옳게 굽는데 시험이 dates[-1] 을 기대해 빨개지고, 막힘이 생성기 단계에서 게이트로 옮겨 갈 뿐 그날 데이터
커밋은 여전히 막힌다(2026-09-26 리뷰가 서울만 찬 2026.08 을 붙여 재현: 생성기 rc=0, 게이트 2 failed). 그래서
실제 계열을 **두 페이지가 쓰는 지역이 전부 찬 마지막 달까지 잘라** 기준 상태를 만들고, 그 뒤에 시험이 직접 만든
달을 붙인다. 기대하는 달은 그 구성에서 정해진다(자른 계열의 마지막 달, 또는 시험이 다 채워 붙인 달).

픽스처(모두 저장소의 실제 전세가율 계열 data-core.js·data.js 를 위처럼 자른 뒤):
  - 'fresh'         : 서울만 찬 새 달 하나 — 감사가 재현한 merge_basic 직후 모양.
  - 'batch_partial' : 서울만 찬 달이 이미 data.js 최신 열에 있고(리뷰가 게이트를 빨갛게 만든 배치 당일 상태),
                      시험이 서울만 찬 달을 하나 더 붙인다 — 보류가 두 달 연속.
  - 'no_jeonguk'    : 전국만 빈 달이 최신 열에 있고 서울만 찬 달이 그 뒤에 붙는다. /jeonse-ratio/ 는 전국 머리
                      숫자를 그리므로 전국까지 본다(JEONSE_NEED). /cycle/ 차트는 시도만 그리므로 시도만 본다
                      (refresh_cycle_data.SIDO). 이 경우 두 페이지의 기준월이 한 달 갈리는 것이 의도된 동작이다.

무엇을 깨뜨리면 빨개지나(각각 실제로 적용해 확인):
  - build_jeonse 의 `li = jeonse_ref_index(j, JEONSE_NEED)` 를 `li = len(dates) - 1` 로 되돌리면 → 세 픽스처 모두
    TypeError 로 빨강
  - build_jratio 의 `k = I.jeonse_ref_index(D, SIDO)` 를 `k = len(D['dates']) - 1` 로 되돌리면 → 세 픽스처 모두
    0 나누기로 빨강
  - jeonse_ref_index 가 완비 여부를 안 보고 마지막 열을 돌려주면 → 두 시험 모두 빨강
  - jeonse_ref_index 가 한 달만 보류하고(마지막 열이 비면 그 앞 열을 확인 없이) 돌려주면 → 'batch_partial'(두
    페이지)·'no_jeonguk'(/jeonse-ratio/)가 빨강('fresh' 만으로는 못 잡는다)
  - build_jratio 가 SIDO 대신 JEONSE_NEED(전국 포함)로 고르면 → /cycle/ 의 'no_jeonguk' 가 빨강
  - 완비 달이 없을 때 RuntimeError 대신 마지막 열로 넘어가면 → 마지막 시험이 빨강
시험 쪽 회귀도 확인했다: 기대하는 달을 다시 실제 계열의 dates[-1] 로 두면, 저장소 data.js 에 서울만 찬 달을
붙여 둔 상태(리뷰 재현)에서 게이트가 다시 빨개진다. 이 시험은 그 상태에서도 초록이다.
"""
import copy
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import refresh_cycle_data as RF  # noqa: E402

# 두 페이지가 기준월에 값이 있어야 하는 지역의 합집합(순서 보존). 모델 상수에서 세고 손으로 적지 않는다.
NEED_BOTH = tuple(dict.fromkeys(tuple(I.JEONSE_NEED) + tuple(RF.SIDO)))


def _next_month(lab):
    y, m = (int(x) for x in re.match(r'^(\d{4})\.(\d{2})', lab).groups())
    return '%04d.%02d' % (y + (m == 12), m % 12 + 1)


def _has(block, r, k):
    s = block['series'].get(r) or []
    return k < len(s) and s[k] is not None


def _cut_to_complete(block):
    """실제 계열을 NEED_BOTH 가 전부 찬 마지막 달까지 자른다 — 배치 당일 최신 열이 반쯤 차 있어도 기준이 흔들리지 않게.

    생성기의 jeonse_ref_index 를 부르지 않고 시험이 따로 센다(생성기 규칙으로 기대값을 만들면 같이 틀린다).
    """
    full = [k for k in range(len(block['dates'])) if all(_has(block, r, k) for r in NEED_BOTH)]
    assert full, '실제 전세가율 계열에 %s 이(가) 전부 찬 달이 없다' % ', '.join(NEED_BOTH)
    k = full[-1]
    b = copy.deepcopy(block)
    b['dates'] = b['dates'][:k + 1]
    b['series'] = {r: s[:k + 1] for r, s in b['series'].items()}
    return b


def _append_month(b, keep):
    """merge_basic 이 새 달을 만든 모양 — 새 열은 전부 None 으로 두고 keep(r) 인 지역만 채운다. 새 달 이름을 돌려준다."""
    new = _next_month(b['dates'][-1])
    b['dates'].append(new)
    for r, s in b['series'].items():
        s.append(s[-1] if keep(r) else None)
    return new


def _only_seoul(r):
    return r == '서울'


def _all_but_jeonguk(r):
    return r != '전국'


CASES = ('fresh', 'batch_partial', 'no_jeonguk')


def _fixture(block, case):
    """(계열, 완비 달, /cycle/ 가 골라야 할 달, 보류돼야 하는 달들)."""
    b = _cut_to_complete(block)
    complete = b['dates'][-1]
    cycle_pick = complete
    held = []
    if case == 'batch_partial':
        held.append(_append_month(b, _only_seoul))
    elif case == 'no_jeonguk':
        cycle_pick = _append_month(b, _all_but_jeonguk)   # 시도는 다 찼다 — /cycle/ 는 이 달을 쓴다
        held.append(cycle_pick)                           # /jeonse-ratio/ 는 전국이 비어 보류한다
    held.append(_append_month(b, _only_seoul))
    return b, complete, cycle_pick, held


@pytest.mark.parametrize('case', CASES)
def test_jeonse_page_holds_a_partially_filled_month(case):
    _, sts = I.load()
    part, complete, _, held = _fixture(sts['전세가율'], case)
    html, _ = I.build_jeonse(dict(sts, 전세가율=part))
    assert '%s 기준' % complete in html, '직전 완비 달(%s)로 굽지 않았다' % complete
    for m in held:
        assert '%s 기준' % m not in html, '반쯤 찬 달(%s)을 기준월로 찍었다' % m


@pytest.mark.parametrize('case', CASES)
def test_cycle_chart_holds_a_partially_filled_month(case):
    S = RF.load_stats()
    part, _, want, _ = _fixture(S['전세가율'], case)
    lvl, sudo, jib, prd = RF.build_jratio(dict(S, 전세가율=part))
    assert prd == want, (prd, want)
    assert {x['region'] for x in lvl} == set(RF.SIDO), '보류한 달 대신 읽은 달에서 시도가 빠졌다'
    assert RF.jratio_prose(lvl, prd)['jr_prd'] == want


def test_no_complete_month_stops_with_a_clear_error():
    _, sts = I.load()
    b = copy.deepcopy(sts['전세가율'])
    b['series']['서울'] = [None] * len(b['dates'])
    with pytest.raises(RuntimeError, match='전부 채워진 달이 없다'):
        I.jeonse_ref_index(b, I.JEONSE_NEED)
