"""넓은 표 상자에는 가로로 밀 것이 남았다는 그림자가 있다(2026-10-30 디자인 리뷰 — 휴대폰에서 표 열이 잘리는데 표시가 없었다).

규칙은 지표 페이지 .tbl-wrap(백로그 36-5)과 같은 순수 CSS 다: 바탕색 덮개(background-attachment local)가 끝에 닿으면
그림자(scroll)를 가린다. 콘텐츠 글 표(.ctab), 개인정보처리방침 표(.scroll), 시도 리포트 분기표(.ztb-scroll)에 같은 규칙을 둔다.

무엇을 바꾸면 빨개지나(실제로 확인): .ctab 규칙에서 그림자 background 를 지우면, 개인정보 body 에서 word-break:keep-all 을
지우면('수집합/니다'처럼 단어 중간에서 줄이 바뀌던 상태), 휴대폰 .ztb-scroll 의 max-height:none 을 지우면(가로·세로 이중
스크롤 상자로 되돌아감).
픽스처: 저장소의 app.css·privacy/index.html 과 생성기 make_content_pages·make_indicator_pages 의 CSS 상수 그대로.
"""
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_content_pages as MC  # noqa: E402
import make_indicator_pages as I  # noqa: E402


def _read(*p):
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])' + re.escape(sel) + r'\{([^}]*)\}', css)
    assert m, '%s 규칙을 찾지 못했다' % sel
    return m.group(1)


def _has_cue(body):
    return body.count('no-repeat local') == 2 and body.count('no-repeat scroll') == 2


def test_wide_table_boxes_show_a_scroll_shadow():
    privacy = _read('privacy', 'index.html')
    for where, css, sel in (('콘텐츠 글', MC.EXTRA_CSS, '.ctab'),
                            ('지표 페이지', I.SHELL, '.tbl-wrap'),
                            ('개인정보처리방침', privacy, '.scroll'),
                            ('시도 리포트 분기표', _read('app.css'), '.ztb-scroll')):
        assert _has_cue(_rule(css, sel)), '%s %s 에 넘침 그림자가 없다' % (where, sel)


def test_privacy_breaks_lines_between_words():
    assert 'word-break:keep-all' in _rule(_read('privacy', 'index.html'), 'body')


def test_zone_quarter_table_is_not_a_double_scroll_box_on_phones():
    css = _read('app.css')
    assert re.search(r'@media \(max-width:600px\)\{\.ztb-scroll\{max-height:none\}\}', css)
