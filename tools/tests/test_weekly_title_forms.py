# -*- coding: utf-8 -*-
"""주간 시세 글 제목의 두 꼴 A/B(2026-10-17) — 세로줄 꼴 '[기관] 라벨(주차) | 결론절'과 연재형 괄호 부제 꼴
'[기관] 라벨 주차 (결론절)'이 조사일 주 번호(_wk)로 2주씩 번갈아 나오고, 결론절 검사·홈 카드 결론 뽑기가 두 꼴을 다 받는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - weekly_title_form 이 늘 'bar' 를 돌려주면(또는 WEEKLY_TITLE_RUN 을 1 로 바꾸면) 교대 시험이 빨개진다.
  - title_tail 에서 끝 괄호 부제를 보는 가지를 빼면(옛 title_warnings 처럼 ' | '와 쉼표만 보면) 괄호 경고 시험이 빨개진다.
  - blog_feed.headline 에서 괄호 가지를 빼면(옛 코드) 홈 카드 결론 시험이 빨개진다.
픽스처: 2026-10-05 부터 8주 연속 조사일(월요일), 블덱스가 실제로 대표 키워드로 잡았던 일반어 세 개('2분기'·'2027년'·'모자',
2026-10-15 광주·전남·청주·부산 편 사례)를 괄호 부제 안에 넣은 제목, 그리고 요청서의 괄호 꼴 예제 제목.
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_feed as BF  # noqa: E402
import make_naver_post as P  # noqa: E402

WEEKS = [(datetime.date(2026, 10, 5) + datetime.timedelta(days=7 * i)).isoformat() for i in range(8)]


def test_weekly_title_forms_alternate_every_two_weeks():
    forms = [P.weekly_title_form(p) for p in WEEKS]
    assert set(forms) == set(P.WEEKLY_TITLE_FORMS), forms          # 두 꼴이 다 나온다
    # 2주씩 이어 쓴다(요청 사양의 숫자 그대로 — 상수에 맞추면 상수를 1 로 바꿔도 초록이다). 창의 첫·끝 묶음은 잘려
    # 있을 수 있으니 안쪽 묶음만 재고, 안쪽 묶음이 하나는 있어야 한다.
    runs, cur = [], 1
    for a, b in zip(forms, forms[1:]):
        if a == b:
            cur += 1
        else:
            runs.append(cur)
            cur = 1
    runs.append(cur)
    inner = runs[1:-1]
    assert inner and all(r == 2 for r in inner), (forms, runs)
    assert P.WEEKLY_TITLE_RUN == 2


def test_weekly_title_text_matches_its_form():
    tail = '서울 +0.16% 전국 +0.10%'
    for p in WEEKS:
        t = P.weekly_title(p, tail)
        assert t.startswith('[한국부동산원] %s' % P.MW.TITLE_KW), t     # 라벨(데이터랩 실측 검색어)은 두 꼴 모두 그대로
        assert P.MW.WR.week_label(p) in t, t
        if P.weekly_title_form(p) == 'paren':
            assert t.endswith(' (%s)' % tail) and ' | ' not in t, t
        else:
            assert t.endswith(' | %s' % tail) and '(%s)' % P.MW.WR.week_label(p) in t, t
        assert P.title_tail(t) == tail, t                            # 결론절 검사가 두 꼴에서 같은 결론절을 본다


@pytest.mark.parametrize('word', ['2분기', '2027년', '모자'])
def test_title_warnings_look_inside_the_parenthesised_subtitle(word):
    tail = {'2분기': '내년 2분기부터 입주가 줄어듭니다', '2027년': '2027년까지 공급이 끊깁니다', '모자': '수도권 공급이 모자랍니다'}[word]
    paren = '[한국부동산원] 주간 아파트가격 동향 10월 둘째 주 (%s)' % tail
    bar = '[한국부동산원] 주간 아파트가격 동향(10월 둘째 주) | %s' % tail
    assert any(word in w for w in P.title_warnings(paren)), P.title_warnings(paren)
    assert len(P.title_warnings(paren)) == len(P.title_warnings(bar))   # 두 꼴이 같은 결론절에 같은 경고를 낸다


def test_title_warnings_still_ignore_the_head_in_the_parenthesised_form():
    # 앞머리의 주차('10월 둘째 주')는 규칙상 들어가는 말이라 '\d+월' 패턴에 걸리면 안 된다
    assert not P.title_warnings('[한국부동산원] 주간 아파트가격 동향 10월 둘째 주 (비강남이 끌어 서울 88주째 상승)')


def test_home_card_headline_takes_the_parenthesised_conclusion():
    assert BF.headline('[한국부동산원] 주간 아파트가격 동향 10월 둘째 주 (비강남이 끌어 서울 88주째 상승)') == '비강남이 끌어 서울 88주째 상승'
    # 세로줄 꼴과 '[…]'만 있는 제목은 전처럼
    assert BF.headline('[한국부동산원] 주간 아파트가격 동향(10월 둘째 주) | 경기는 가장 크게 올랐습니다') == '경기는 가장 크게 올랐습니다'
    assert BF.headline('[한국부동산원] 이번 주 시세 정리') == '이번 주 시세 정리'
