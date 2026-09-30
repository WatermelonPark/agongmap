# -*- coding: utf-8 -*-
"""/monthly/ 전세가율 절의 기준월은 /jeonse-ratio/ 와 같은 정본 규칙(jeonse_ref_index)으로 고른다(전수리뷰 #24·#106).

merge_basic 은 새 달을 전 지역 None 열로 먼저 만들고 원천이 준 지역만 채운다. 원천 행 이름이 바뀌어 최신 열이
일부만 찬 일이 2026.06·07 에 실제로 있었다. 예전 /monthly/ 는 last_idx(dates[-1])를 읽어 그 부분 열을 '기준'으로
달고, 빈 지역 행을 조용히 뺐으며, 남은 두세 곳으로 '1년 새 변화가 큰 곳'을 뽑고, newest_basis 가 그 달을 골라
피드에 새 판(guid)까지 만들었다. 같은 날 /jeonse-ratio/·/cycle/·시도 리포트는 직전 완비 달을 말한다.

픽스처: test_month_gap_comparisons._jeonse(2025.01~2026.08, 달·지역마다 값이 다른 합성 계열) 끝에 다음 달 열을
붙이고 전국·서울·경기만 채운다 — 2026.06·07 에 최신 열이 일부만 찼던 실제 모양이다. 달 라벨은 픽스처에서 유도한다.

무엇을 깨뜨리면 빨개지나(실제로 적용해 확인):
  - make_monthly_page.jeonse_idx 를 `return len(jr['dates']) - 1, jr['dates'][-1]`(예전 last_idx)로 되돌리면
    → 기준월·행 수·newest_basis·요약 단정이 모두 빨강
  - top3_lines 의 전세가율 분기만 last_idx(jr) 로 되돌리면 → 요약 단정(서울·경기만 뽑힘) 빨강
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_monthly_page as MP  # noqa: E402
from test_month_gap_comparisons import _jeonse  # noqa: E402
from test_monthly_top3 import _assert_summary_matches_table, _rows, _section, _top  # noqa: E402


def _partial_latest():
    jr = _jeonse(skip=())
    last = jr['dates'][-1]
    y, m = (int(x) for x in last.split('.'))
    nxt = '%04d.%02d' % (y + (m == 12), m % 12 + 1)
    jr['dates'].append(nxt)
    for r, s in jr['series'].items():
        s.append(s[-1] + 0.3 if r in ('전국', '서울', '경기') else None)
    return jr, last, nxt


def test_monthly_jeonse_uses_the_same_basis_month_as_jeonse_ratio():
    jr, full, partial = _partial_latest()
    secs, basis = MP.build({}, {'전세가율': jr})
    sec = _section(''.join(secs), 'jeonse')
    lab = re.search(r'<p class="basis"><b>([^<]+)</b> 기준', sec).group(1)

    ref = jr['dates'][I.jeonse_ref_index(jr, I.JEONSE_NEED)]
    assert ref == full, '픽스처가 부분 최신 열을 재현하지 않는다'
    html, _ = I.build_jeonse({'전세가율': jr})
    ratio_month = re.search(r'전국 아파트 전세가율 · (\S+) 기준', html).group(1)
    assert ratio_month == ref
    assert lab == MP.month_label(ref), '/monthly/ 는 %s, /jeonse-ratio/ 는 %s 기준을 말한다' % (lab, ratio_month)

    rows = _rows(sec)
    missing = [r for r in I.JEONSE_NEED if r not in rows]
    assert not missing, '부분 최신 열을 기준으로 삼아 %s 행이 빠졌다' % missing
    i = jr['dates'].index(ref)
    assert rows['전국'][0] == jr['series']['전국'][i], '전국 전세가율이 /jeonse-ratio/ 와 다르다'

    assert MP.newest_basis(basis) != partial, '부분 최신 달(%s)이 피드 guid 기준월이 된다' % partial

    top = _top(sec)
    assert top and len(top) == 3 and {t[1] for t in top} - {'서울', '경기'}, \
        '요약 3곳을 부분 열에 남은 지역에서만 뽑았다: %s' % top
    _assert_summary_matches_table('jeonse', sec)


def test_monthly_jeonse_full_latest_month_is_still_the_basis():
    """최신 열이 다 차 있으면 예전처럼 그 달이 기준이다 — 고친 뒤에도 평소 달은 그대로."""
    jr = _jeonse(skip=())
    secs, _ = MP.build({}, {'전세가율': jr})
    sec = _section(''.join(secs), 'jeonse')
    assert '<b>%s</b> 기준' % MP.month_label(jr['dates'][-1]) in sec
