# -*- coding: utf-8 -*-
"""한 해 적정 입주량의 산식 — 인구 ÷ 2.5 × 2% (2026-09-30 대표 결정).

왜 이 두 수만 따로 두나. 같은 산식을 도시 글 생성기(make_city_post)와 콘텐츠 자리표의 원천 수집기
(make_city_moveins)가 함께 쓴다. 뒤쪽은 **수집 잡**에서 도는데 그 자리에는 표준 라이브러리밖에 없고,
make_city_post 는 카드 생성기(make_zone_cards)를 타고 PIL 까지 닿는다. 상수를 가져오려고 그 묶음을
들여오면 수집 잡에서 ModuleNotFoundError 가 된다 — 2026-10-27 실제로 그랬고 배치 게이트의
test_test_deps_are_installed 가 잡아냈다. 값을 양쪽에 복사하면 한쪽만 고쳐지는 날이 오므로, 상수의
정본을 아무것도 들여오지 않는 이 파일에 둔다.
"""
PER_HH = 2.5      # 가구당 사람 수
RATE = 0.02       # 한 해 적정 입주량 = 추정 가구 수의 2%


def need(pop):
    """인구 → 한 해 적정 입주량(세대). 두 생성기가 이 함수로 같은 수를 낸다."""
    return int(round(pop / PER_HH * RATE))


def note():
    """표 각주에 적는 산식 한 줄 — '인구 ÷ 2.5 × 2%'."""
    return '인구 ÷ %s × %d%%' % (PER_HH, int(RATE * 100))
