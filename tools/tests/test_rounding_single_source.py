# -*- coding: utf-8 -*-
"""변동률 표기 반올림은 한 곳(make_weekly_page.pv2r)만 쓴다.

사이트 JS 의 pv2r 는 절대값 half-up 이다. /weekly/ 는 백로그 15에서 그 규칙으로 맞췄고
(test_weekly_page 가 node 로 JS 와 대조), 블로그 초안도 2026-09-23 에 맞췄다. 그런데 공유 카드
(make_weekly_share)와 /monthly/ 가격표(make_monthly_page)는 파이썬 round() 를 따로 써서
-0.075 가 사이트 -0.08, 카드·월간 -0.07 로 갈렸다(같은 대상을 두 코드가 다른 기준으로 잰 경우).

무엇을 깨뜨리면 빨개지나: make_monthly_page.pv2·cls 나 make_weekly_share.pv2r 를 예전
round(v, 2) 로 되돌리면 -0.075·0.125·-0.045 에서 실패한다(실제로 확인).
픽스처: 이진 소수로 가운데에 걸리는 실제 주간 변동률 값들(-0.075 는 data.js 에 실재).
"""
import os
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_weekly_page as MW  # noqa: E402
import make_monthly_page as MP  # noqa: E402
import make_weekly_share as WS  # noqa: E402

HALFWAY = (-0.075, 0.125, -0.045, 0.015, 0.105, 0.0012, -0.0012, 0.0)


def test_monthly_page_rounds_like_the_site():
    for v in HALFWAY:
        r = MW.pv2r(v)
        assert MP.pv2(v) == (('%+.2f' % r) if r != 0 else '0.00'), v
        assert MP.cls(v) == (' class="up"' if r > 0 else (' class="dn"' if r < 0 else '')), v


def test_share_card_rounds_like_the_site():
    for v in HALFWAY:
        assert WS.pv2r(v) == MW.pv2r(v), v
