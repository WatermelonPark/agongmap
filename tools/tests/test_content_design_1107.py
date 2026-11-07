# -*- coding: utf-8 -*-
"""콘텐츠 디자인 검수(2026-11-07)에서 고친 것들 — 섹션 이름, 칩 줄, 허브 접기, 글 끝 행동, 그림·표·각주, 원고 알림.

재현한 실제 상태(2026-11-07 main, Chromium 375px·1280px):
- 한 섹션을 '반박'(빵부스러기·<title>)·'발언 검증'(칩)·'해설'(홈 푸터) 세 이름으로 불렀다(도시·GTX·단지 편도 둘씩).
- 600px 이하에서 질문 칩·지역 칩 줄이 가로 밀기(nowrap)라 다섯째 질문 칩과 경기 지역 칩 대부분이 단서 없이 화면 밖이었다.
- 지역 칩 거르기가 정확 일치라 '부천'을 누르면 '부천 원미구'·'부천 오정구' 글이 숨었고, 칩은 글 수 순이라 같은 시가 흩어졌다.
- 허브 '최근 글'이 40장을 한 번에 쌓아 375px 에서 약 7,200px 였다.
- 글 끝 상자 넷이 같은 테두리라 첫 행동이 없었고, 도시 글에는 시도 리포트 상자가 빠졌다(region 이 시라 _zone_link 가 못 찾았다).
- 혼자 선 캡처 그림에 '눌러서 크게 보기' 표시가 없었고, 표 밑 '※' 방법론 15줄이 본문 크기로 결과 절을 막았다.
- 도시 편에서 같은 두 줄 각주가 표 셋·그림 하나 밑에 네 번, 핵심 숫자 띠와 그림 카드에 같은 '34%'가 두 번 섰다.
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import content_check as CC         # noqa: E402


# ── 원고 알림 ────────────────────────────────────────────────────────────
def test_content_check_notes_card_numbers_and_wide_tables():
    """원고 검사가 카드 핵심 숫자 셋(제목 되풀이·같은 섹션 중복·소수 둘째 자리)과 넓은 원고 표를 ※ 알림으로 낸다 — 고칠 곳(종료
    코드)에는 세지 않는다.

    변이(실제로 확인): key_notes 의 제목 비교를 지우면 첫 단정이, 중복 비교를 지우면 둘째가, table_notes 의 열 수 비교를 지우면
    마지막이 빨개진다.
    픽스처: 그날 원고 모양 — 도시 편(제목·key 모두 '적정물량의 24%'), 발언 검증 셋(같은 '적정물량의 28%'), 단지 편('105.95%').
    """
    front = 'title: %s\nsection: %s\nkey:\n  - label: l\n    value: v\n'
    e = [('c/a.md', front % ('진주 적정물량의 24%입니다', 'city'),
          {'section': 'city', 'title': '진주 2027년 입주는 적정물량의 24%입니다', 'key': {'label': 'l', 'value': '적정물량의 24%'}}),
         ('k/a.md', front % ('a', 'column'), {'section': 'column', 'title': 'a', 'key': {'value': '적정물량의 28%'}}),
         ('k/b.md', front % ('b', 'column'), {'section': 'column', 'title': 'b', 'key': {'value': '적정물량의 28%'}}),
         ('d/a.md', front % ('17평형 3억', 'danji'), {'section': 'danji', 'title': '17평형 3억', 'key': [{'value': '105.95%'}]}),
         ('d/b.md', front % ('24평형', 'danji'), {'section': 'danji', 'title': '24평형 2.9배 아닙니다', 'key': {'value': '29배'}})]
    got = CC.key_notes(e)
    assert any('제목에 이미 있는 값' in w for _l, w in got['c/a.md'])
    assert any('같은 섹션 k/b.md' in w for _l, w in got['k/a.md'])
    assert any('소수 둘째 자리' in w for _l, w in got['d/a.md'])
    assert 'd/b.md' not in got, '2.9 안의 9 를 29 로 잘못 잡았다'
    assert all(ln == 3 for notes in got.values() for ln, _w in notes), '알림 줄이 key 줄이 아니다'
    wide = CC.table_notes('a\n| ' + ' | '.join('h%d' % i for i in range(9)) + ' |\n|' + '---|' * 9 + '\n')
    assert wide and wide[0][0] == 2 and '9열' in wide[0][1]
    assert not CC.table_notes('| a | b |\n|---|---|\n')
