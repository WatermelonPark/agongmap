# -*- coding: utf-8 -*-
"""데이터 리포트의 배치 — 설명은 콘텐츠 아래(CLAUDE.md 화면 설계 원칙, 2026-10-30 디자인 리뷰 3차).

재현한 실제 상태(2026-10-30 main, 375px): 시도 리포트 머리에서 판정 막대보다 '3년 너머' 참고 줄·허수 안내·추정 주석이 먼저
보였고, /moveins/·/jeonse-ratio/ 는 '…이란' 정의 두 문단이 표보다 먼저 나왔다. '이 지역 글' 묶음은 본문 틀(.wrap) 밖이었고,
/monthly/ 의 3~4열 표는 데스크톱에서 836px 로 늘어났다.
픽스처: 생성기를 먼저 돌린 저장소의 구워진 페이지(게이트와 같은 순서). 페이지가 없으면 건너뛴다(CI 에서는 건너뜀도 실패).
"""
import io
import os
import re
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_content_pages as MC  # noqa: E402
import make_sido_pages as M  # noqa: E402


def _page(*p):
    f = os.path.join(ROOT, *p)
    if not os.path.exists(f):
        pytest.skip('구워진 페이지가 없다: %s' % '/'.join(p))
    return io.open(f, encoding='utf-8').read()


def test_zone_reference_notes_fold_below_the_bars():
    """시도 리포트의 3년 너머·추정 줄은 해마다 입주 막대 **뒤** 접는 칸에 있다.

    변이(실제로 확인): make_sido_pages 에서 split_ref_block 을 outlook_block 앞으로 옮기거나, split_block 이 다시 참고 줄을
    그리면 빨개진다.
    """
    seen = 0
    for z in os.listdir(os.path.join(ROOT, 'zone')):
        f = os.path.join(ROOT, 'zone', z, 'index.html')
        if not os.path.exists(f):
            continue
        s = io.open(f, encoding='utf-8').read()
        head = s[s.find('<header class="zhead"'):s.find('<main')]
        if 'zs-ref' not in head and 'zs-est' not in head:
            continue
        seen += 1
        assert head.find('class="zout"') < head.find('<details class="zmore"'), '%s: 참고 줄이 막대보다 앞이다' % z
        rest = re.sub(r'<details class="zmore">.*?</details>', '', head, flags=re.S)
        assert 'class="zs-row zs-ref' not in rest and 'class="zs-est"' not in rest, '%s: 참고 줄이 접는 칸 밖에 남았다' % z
    assert seen >= 3, '참고 줄이 있는 시도 리포트를 %d곳밖에 못 봤다' % seen
    assert M.split_ref_block(None) == '' and M.split_ref_block({'rows': []}) == ''


def test_zone_posts_sit_inside_the_body_column():
    """'이 지역 글' 묶음이 다른 절처럼 .wrap 안에 있다. 변이: zone_posts_html 을 옛 '<section class="crecent zposts">' 로
    되돌리면 빨개진다(확인)."""
    out = MC.zone_posts_html([{'section': 'city', 'slug': 'x', 'title': 't', 'updated': '2026-10-30', 'date': '2026-10-30'}])
    assert out.startswith('<section class="zposts"><div class="wrap">'), out[:80]


@pytest.mark.parametrize('rel,word', [('moveins', '입주물량이란'), ('jeonse-ratio', '전세가율이란')])
def test_indicator_definitions_come_after_the_table(rel, word):
    """지표 페이지의 '…이란' 정의 절은 표(#utable)와 '지금 표에서 읽히는 것' 뒤에 있다.
    변이: make_indicator_pages 에서 정의 절을 머리 바로 뒤로 되돌리면 빨개진다(확인)."""
    s = _page(rel, 'index.html')
    assert s.find('id="utable"') < s.find('<h2>%s</h2>' % word), '%s: 정의가 표보다 앞이다' % rel
    assert s.find('지금 표에서 읽히는 것') < s.find('<h2>%s</h2>' % word)


def test_monthly_small_tables_are_capped_on_desktop():
    """/monthly/ 의 열이 적은 표는 tbl-narrow 로 넓은 화면 폭을 묶는다. 변이: table() 의 narrow 를 빼면 빨개진다(확인)."""
    s = _page('monthly', 'index.html')
    assert '.tbl-wrap.tbl-narrow{max-width:560px}' in s
    assert len(re.findall(r'<div class="tbl-wrap tbl-narrow"><table', s)) >= 4
