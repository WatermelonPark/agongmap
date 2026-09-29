# -*- coding: utf-8 -*-
"""주간 공유 카드의 '상승·하락' 상위 3은 /weekly/ 의 상위 3(make_weekly_page.top3)과 같은 곳이다(전수리뷰 #84).

예전 카드는 반올림한 표시값(pv2r)으로 정렬하고 동률은 주간 계열의 원천 순서, 하락은 그 역순으로 뽑았다. 두 지역이
같은 값으로 반올림되는 주에 원값으로 덜 움직인 곳이 카드에 오르고 더 움직인 곳이 빠져, 156주 가운데 43주에서
카드와 /weekly/·블로그의 3곳이 갈렸다(2026-09-14: 카드 '상승: 경기 +0.18 · 서울 +0.16 · 울산 +0.06',
원값 울산 0.0572·전북 0.0631 → /weekly/ 는 전북).

픽스처: 2026-09-14 의 실제 모양을 재현한 합성 한 주. 원천 순서(sido_zones.ORDER)에서 앞선 울산이 0.0572, 뒤의 전북이
0.0631 이라 둘 다 +0.06 으로 반올림된다. 하락 쪽은 원천 순서에서 앞선 대구 −0.0631, 뒤의 제주 −0.0572 로 같은
동률을 만든다(예전 코드는 역순이라 제주를 먼저 적었다). 나머지 시도는 0.

무엇을 깨뜨리면 빨개지나(실제로 적용해 확인):
  - summary_top3 를 예전 식(표시값 정렬 `sorted(regs, key=lambda r: pv2r(val[r]), reverse=True)`, 하락은 reversed)으로
    되돌리면 → 상승 3곳(울산)·하락 순서(제주 먼저)가 빨강
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
pytest.importorskip('PIL')
import make_weekly_page as MW  # noqa: E402
import make_weekly_share as WS  # noqa: E402
import sido_zones as SZ  # noqa: E402

VALS = {'경기': 0.18, '서울': 0.16, '울산': 0.0572, '전북': 0.0631,
        '부산': -0.12, '대구': -0.0631, '제주': -0.0572}


def _week():
    regs = list(SZ.ORDER)
    assert regs.index('울산') < regs.index('전북') and regs.index('대구') < regs.index('제주'), \
        '픽스처 전제(원천 순서) 가 바뀌었다'
    return regs, {'p': '2026-09-14', 'ma': [VALS.get(r, 0.0) for r in regs], 'je': [0.0] * len(regs)}


def test_card_top3_follows_raw_values_like_weekly_page():
    regs, row = _week()
    up, dn = WS.summary_top3(regs, row)
    assert [r for r, _ in up] == ['경기', '서울', '전북'], '반올림 동률에서 원값으로 덜 오른 곳을 실었다: %s' % up
    assert [r for r, _ in dn] == ['부산', '대구', '제주'], '반올림 동률에서 원값으로 덜 내린 곳을 앞에 실었다: %s' % dn


def test_card_top3_is_the_weekly_page_top3():
    regs, row = _week()
    val = dict(zip(regs, row['ma']))
    want = MW.top3([(z, val[z]) for z in MW.SIDO if val.get(z) is not None])
    assert WS.summary_top3(regs, row) == want
