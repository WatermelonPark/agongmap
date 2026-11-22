# -*- coding: utf-8 -*-
"""5·6편이 같이 쓰는 '앞으로 3년' 목록(fut_lists)의 문턱은 화면 정수 퍼센트로 가른다(백로그 59).

원값으로 가르면 화면이 '100%'인 지역이 '적정물량을 넘는 곳'에도, '못 미치는 곳'에도 들어가 같은 문장이 화면 숫자와 모순된다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import theory_link4 as L4  # noqa: E402


def _zone(z, fut, need, shown):
    return {'z': z, 'fut': fut, 'need': need,
            'split': {'rows': [[], ['앞으로 3년', '%d%%' % shown]]}}


def _adv(zones):
    return {'sido': {'H': 12, 'zones': zones}}


def test_thresholds_follow_the_shown_percent_not_the_raw_ratio():
    """화면 정수 100%인 지역은 '넘는 곳'도 '못 미치는 곳'도 아니다 — 원값 100.04%·99.96%가 그랬다.

    변이(실제로 확인): fut_lists 의 문턱을 옛 원값(`fut_ratio > 1`·`< LOW`·`< 1`)으로 되돌리면 A 가 hi 에, B 가 below 에
          들어가 빨개진다.
    픽스처: 경계 바로 안쪽·바깥의 원값과 그 화면 정수 넷(A 100.04→100%, B 99.96→100%, C 33.4→33%, D 101→101%).
    """
    adv = _adv([_zone('A', 10004, 10000, 100), _zone('B', 9996, 10000, 100),
                _zone('C', 3334, 10000, 33), _zone('D', 10100, 10000, 101)])
    got = L4.fut_lists(adv, name=lambda k: k)
    assert got['hi'] == ['D'], got
    assert got['lo'] == ['C'], got
    assert got['below'] == 1, got
    assert got['fut_high'] == 'D 101%' and got['fut_low'] == 'C 33%', got
    assert got['fut_high_names'] == 'D', got
