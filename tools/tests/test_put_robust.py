# -*- coding: utf-8 -*-
"""주간 페이지 뼈대를 고쳐 쓰는 put_* 의 두 가지 잠복 결함(백로그 59).

1) put_min_font 의 정규식이 선택자에 `>`·`<` 가 있으면 그 규칙을 통째로 건너뛰어 12px 이 남았다.
2) put_nav 의 '없으면 넣는다'가 anchor 글자가 바뀐 회차에 조용히 아무것도 안 넣었다(알 길이 없었다).
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_weekly_page as MW  # noqa: E402


def test_put_min_font_fixes_rules_inside_a_style_tag_with_attributes():
    """`<style type="text/css">` 처럼 속성이 붙은 블록도 고친다 — 예전 정규식은 `<style>` 글자 그대로만 찾아,
    속성이 붙는 날 소리 없이 12px 이 남았다.

    변이(실제로 확인): 블록 정규식을 옛 `(<style>.*?</style>)` 로 되돌리면 이 시험이 빨개진다.
    픽스처: 속성이 붙은 <style> 블록 하나.
    """
    s = '<style type="text/css">body>.x{font-size:12px}</style>'
    out = MW.put_min_font(s)
    assert 'font-size:13px' in out and 'font-size:12px' not in out, out


def test_put_after_is_loud_when_its_anchor_is_gone():
    """anchor 가 없거나 둘 이상이면 멈춘다 — 예전 `if X not in s: s.replace(anchor, …)` 는 조용히 아무것도 안 넣었다.

    변이(실제로 확인): _put_after 를 옛 `s.replace(anchor, anchor + nl + add, 1)` 한 줄로 되돌리면
          SystemExit 단정이 빨개진다.
    픽스처: anchor 가 없는 문자열, 그리고 하나뿐인 문자열.
    """
    with pytest.raises(SystemExit):
        MW._put_after('<style>a{}</style>', '.nav-btn svg{display:block}', 'X')
    with pytest.raises(SystemExit):
        MW._put_after('.a{}.a{}', '.a{}', 'X')
    assert MW._put_after('a\n.anchor{}', '.anchor{}', 'X') == 'a\n.anchor{}\nX'


def test_put_after_first_raises_when_there_is_no_style_tag():
    """`<style>` 는 여럿일 수 있어 첫 자리에 넣지만, 아예 없으면 멈춘다(예전엔 조용히 넘어갔다)."""
    assert MW._put_after_first('<style>a{}', '<style>', 'X') == '<style>X\na{}'
    with pytest.raises(SystemExit):
        MW._put_after_first('a{}', '<style>', 'X')
