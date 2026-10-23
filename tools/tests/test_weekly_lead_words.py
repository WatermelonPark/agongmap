"""주간 초안 첫 문단의 방향 낱말(10-23 업계 용어 점검) — '+0.08% 움직였다' 대신 '0.08% 올랐다·내렸다·보합'."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import make_naver_post as P   # noqa: E402


def test_moved_names_the_direction_by_display_value():
    """부호는 표시값으로 가른다. 재현: 10/19 조사 전국 +0.08%(오름), 부산 -0.02%(내림), 원값 0.001(표시 0.00 = 보합).
    변이(확인): moved 가 원값 부호로 가르게(v > 0) 바꾸면 0.001 이 '올랐고요'가 되어, 문자열 '움직였'을 되돌리면 둘째 검사가 빨개진다."""
    w = ('올랐고요', '내렸고요', '보합이었고요')
    assert P.moved(0.08, *w) == '<b>0.08%</b> 올랐고요'
    assert P.moved(-0.02, *w) == '<b>0.02%</b> 내렸고요'
    assert P.moved(0.001, *w) == '<b>0.00%</b>로 보합이었고요'
    src = open(P.__file__, encoding='utf-8').read()
    i = src.index('def draft_weekly'); j = src.index('def draft_zone')
    assert '움직였고요' not in src[i:j] and '움직였는데요' not in src[i:j]
