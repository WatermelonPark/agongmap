# -*- coding: utf-8 -*-
"""'짧은 코드(=상위 행정단위)가 이긴다'는 우선권은 값의 유무가 아니라 **행의 존재**로 정한다(백로그 59).

시도와 시군구가 같은 이름으로 오는 표(제주·제주시, 광주·경기 광주시)에서, 값이 빈 시도 행 뒤에 시군구 행이 오면
예전엔 시도 행이 값을 못 읽어 우선권을 못 잡고 시군구 값이 상위 자리에 앉았다(2026-11-13 전수 리뷰 잠복 결함).
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402


def test_basic_short_code_row_claims_the_slot_even_without_a_value(monkeypatch):
    """기본통계(_fetch_basic_one): 값이 빈 시도 행(제주, 코드 50)이 먼저 오면 그 달 그 지역은 비워 둔다.
    뒤따르는 시군구 행(제주시, 코드 50110) 값으로 대신 채우지 않는다.

    변이(실제로 확인): `_claim_code` 호출을 값 파싱 **뒤**로 되돌리면 시군구 값 3.14 가 실려 빨개진다.
    픽스처: 제주가 시도·시군구 두 행으로 오는 표의 모양(_fetch_basic_one 주석의 2026-08-07 감사 사례).
    """
    rows = [
        {'C1_NM': '제주', 'C1': '50', 'C2_NM': '아파트', 'PRD_DE': '202606', 'DT': '-'},
        {'C1_NM': '제주', 'C1': '50110', 'C2_NM': '아파트', 'PRD_DE': '202606', 'DT': '3.14'},
        {'C1_NM': '서울', 'C1': '11', 'C2_NM': '아파트', 'PRD_DE': '202606', 'DT': '10'},
    ]
    monkeypatch.setattr(U, 'kosis', lambda *a, **k: rows)
    monkeypatch.setattr(U.time, 'sleep', lambda s: None)
    got, _ = U._fetch_basic_one('인허가', months=1, upto=(2026, 6))
    assert got[(2026, 6)]['서울'] == 10
    assert '제주' not in got[(2026, 6)], '값이 빈 시도 행 대신 시군구 행 값을 썼다'


def test_bubble_conv_short_code_row_claims_the_slot_even_without_a_value():
    """버블밴드(bubble_conv_by_prd): 같은 규칙. 값이 빈 시도 행이 시군구 행보다 우선한다.

    변이(실제로 확인): `_claim_code` 호출을 값 파싱 뒤로 되돌리면 제주에 4.2 가 실려 빨개진다.
    픽스처: 2026-08-08 감사 사례(광주가 경기 광주시 값이었던 표)의 제주판.
    """
    rows = [
        {'C1_NM': '아파트', 'C2_NM': '제주', 'C2': '50', 'PRD_DE': '202606', 'DT': '-'},
        {'C1_NM': '아파트', 'C2_NM': '제주', 'C2': '50110', 'PRD_DE': '202606', 'DT': '4.2'},
        {'C1_NM': '아파트', 'C2_NM': '서울', 'C2': '11', 'PRD_DE': '202606', 'DT': '5.5'},
    ]
    got = U.bubble_conv_by_prd(rows)
    assert got['202606']['서울'] == 5.5
    assert '제주' not in got['202606'], '값이 빈 시도 행 대신 시군구 행 값을 썼다'


def test_size_short_code_row_claims_the_slot_even_without_a_value():
    """규모별(_size_levels): 같은 규칙. 값이 빈 시도 행이 시군구 행보다 우선한다.

    변이(실제로 확인): `_claim_code` 호출을 값 파싱 뒤로 되돌리면 제주 1구간에 3.0 이 실려 빨개진다.
    픽스처: 같은 이름이 시도·시군구로 겹치는 규모별 표의 모양.
    """
    rows = [
        {'C2_NM': '제주', 'C2': '50', 'C3': '1', 'PRD_DE': '202606', 'DT': '-'},
        {'C2_NM': '제주', 'C2': '50110', 'C3': '1', 'PRD_DE': '202606', 'DT': '3.0'},
        {'C2_NM': '서울', 'C2': '11', 'C3': '1', 'PRD_DE': '202606', 'DT': '7.0'},
    ]
    got = U._size_levels(rows)
    assert got['서울']['202606'][0] == 7.0
    assert not got.get('제주') or got['제주']['202606'][0] is None, '값이 빈 시도 행 대신 시군구 행 값을 썼다'
