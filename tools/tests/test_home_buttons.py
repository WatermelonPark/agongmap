# -*- coding: utf-8 -*-
"""홈 버튼 크기 한 규칙과 푸터 정돈(2026-10-05 대표 요청).

재현하는 실제 상태(2026-10-05 375px Chromium 실측): 홈의 큰 버튼 높이가 다섯 가지였다 — TOP 10·부린이·사이클 65.5px(18px 글자),
투자자·재건축 테스트 58px(16px), 시도별로 자세히 보기 53.4px(14.5px), 공유 46px(14px), '이달의 통계'는 글자 링크. 대표 결정:
큰 버튼은 52px·15px·600 한 규칙, 전환 버튼(.tb-seg)은 40px. 푸터는 가운데 정렬이라 '읽을거리'·'소개 · 개인정보 · 만든이' 줄이
가운데에서 꺾였고 줄 끝에 가운뎃점이 매달렸다 → 왼쪽 정렬·머리말 열 고정·가운뎃점(.ft-dot) 숨김.
브라우저 실측은 배치 게이트(pytest·pillow 만)에서 돌 수 없어, 크기를 정하는 규칙 한 곳과 그 규칙이 덮는 마크업을 대조한다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 마크업은 입구로만 읽는다 — test_home_src)

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _css():
    with open(os.path.join(ROOT, 'app.css'), encoding='utf-8') as f:
        return f.read()


def _index():
    return dict(HS.home_files())['index.html']


BIG = ('#view-home .home-cta', '#view-home .tb-more a', '#view-home .tb-sub a', '#view-home .wg-sh', '.shero .shero-link a')


def _plain_css():
    return re.sub(r'/\*.*?\*/', '', _css(), flags=re.S)   # 주석 안 글자가 선택자로 읽히지 않게


def _big_rule(css):
    for m in re.finditer(r'([^{}]+)\{([^}]*)\}', css):
        sels = [x.strip() for x in m.group(1).split(',')]
        if set(BIG) <= set(sels):
            return m.group(2)
    return None


def test_big_buttons_share_one_size_rule():
    """큰 버튼(구역 끝 동작·테스트·공유·시도별·이달의 통계, 시세 탭 '이달의 통계')은 한 규칙에서 높이 52px·글자 15px·굵기 600·
    border-box 를 받는다(테두리가 있는 보조 버튼도 높이가 같다). 그 뒤에 같은 대상의 높이·글자를 다시 정하는 규칙이 없어야 한다.

    변이(각각 실제로 확인): 규칙의 min-height 를 46px 로 바꾸면, 선택자에서 '#view-home .wg-sh' 를 빼면, 규칙 뒤에
          '#view-home .home-cta.alt{font-size:16px}' 를 더하면 빨개진다.
    """
    css = _plain_css()
    rule = _big_rule(css)
    assert rule, '큰 버튼 한 규칙(%s)이 없다' % ', '.join(BIG)
    for want in ('min-height:52px', 'font-size:15px', 'font-weight:600', 'box-sizing:border-box', 'border-radius:var(--r-touch)'):
        assert want in rule, (want, rule)
    after = css[css.index(rule) + len(rule):]
    for m in re.finditer(r'([^{}]+)\{([^}]*)\}', after):
        sels = m.group(1)
        if any(re.search(re.escape(b.replace('#view-home ', '').replace('.shero ', '')) + r'(?![\w-])', sels) for b in BIG) and \
                re.search(r'(?<![\w-])(font-size|min-height|height|padding):', m.group(2)) and '#view-home' in sels:
            raise AssertionError('큰 버튼 크기를 뒤에서 다시 정한다: %s{%s}' % (sels.strip(), m.group(2)))


def test_monthly_entry_is_a_button_on_home_and_stats():
    """'이달의 통계 한 화면으로 보기'는 홈(시도별 버튼 바로 아래)과 시세 탭 머리 두 곳 모두 버튼 규칙의 대상이다(글자 링크 아님).

    변이(실제로 확인): 홈 줄의 class 를 tb-sub 에서 다른 이름으로 바꾸면 빨개진다.
    """
    h = _index()
    assert re.search(r'<p class="tb-sub"><a href="/monthly/"[^>]*>이달의 통계 한 화면으로 보기 →</a></p>', h)
    assert re.search(r'<p class="shero-link"><a href="/monthly/">이달의 통계 한 화면으로 보기 →</a>', h)


def test_footer_links_are_split_by_hidden_dots_and_left_aligned():
    """홈·통계·퀴즈 푸터 세 벌 모두 링크 사이 가운뎃점이 .ft-dot 으로 감싸여 있고(CSS 가 숨기고 간격으로 가른다 — 줄 끝에 점이
    매달리지 않는다), 푸터는 왼쪽 정렬, 머리말 열(매주·매달·분기·읽을거리)은 padding 안에 고정된다.

    변이(각각 실제로 확인): 한 푸터의 '<i class="ft-dot"> · </i>' 를 맨 ' · ' 로 되돌리면 첫 단정이, .ft-dot 숨김 규칙을 지우면
          둘째, .home-foot 를 가운데 정렬로 되돌리면 셋째 단정이 빨개진다.
    """
    h = _index()
    blocks = re.findall(r'<nav class="ft-nav ft-grp".*?</nav>|<div class="ft-meta">.*?</div>', h, re.S)
    assert len(blocks) == 6, len(blocks)   # 푸터 세 벌 × (색인·메타)
    for b in blocks:
        assert '</a> · <a' not in b, '줄 끝에 매달리는 맨 가운뎃점이 남았다: ' + b[:80]
    css = _css()
    assert ':is(.home-foot,.minifooter) .ft-dot{display:none}' in css
    foot = re.search(r'\n  \.home-foot\{([^}]*)\}', css).group(1)
    assert 'text-align:left' in foot, foot
    assert ':is(.home-foot,.minifooter) .ft-grp .fg{padding-left:5em}' in css
