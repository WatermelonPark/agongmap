# -*- coding: utf-8 -*-
"""홈 블로그 카드 결론 뽑기(blog_feed.headline)가 주간 시세 글 제목의 두 꼴을 다 받는다(2026-10-17) — 세로줄 꼴
'[기관] 라벨(주차) | 결론절'과 연재형 괄호 부제 꼴 '[기관] 라벨 주차 (결론절)'.

제목을 만들던 블로그 초안 도구는 2026-11-13 에 지웠다(그 교대·경고 시험도 함께). 이미 발행된 글은 두 꼴이 섞여 있고 홈 카드는
RSS 최신 글(tools/data/blog_latest.json)을 읽으므로 이 시험은 남긴다.

무엇을 깨뜨리면 빨개지나(실제로 확인): blog_feed.headline 에서 괄호 가지를 빼면(옛 코드) 빨개진다.
픽스처: 요청서의 괄호 꼴 예제 제목과 세로줄 꼴·'[…]'만 있는 제목.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_feed as BF  # noqa: E402


def test_home_card_headline_takes_the_parenthesised_conclusion():
    assert BF.headline('[한국부동산원] 주간 아파트가격 동향 10월 둘째 주 (비강남이 끌어 서울 88주째 상승)') == '비강남이 끌어 서울 88주째 상승'
    # 세로줄 꼴과 '[…]'만 있는 제목은 전처럼
    assert BF.headline('[한국부동산원] 주간 아파트가격 동향(10월 둘째 주) | 경기는 가장 크게 올랐습니다') == '경기는 가장 크게 올랐습니다'
    assert BF.headline('[한국부동산원] 이번 주 시세 정리') == '이번 주 시세 정리'
