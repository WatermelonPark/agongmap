# -*- coding: utf-8 -*-
"""사이클 이론 4편(고리 ③) 가드 — 숫자는 theory_link3 가 데이터에서 세고, 단정이 깨지면 theory_guards.guard_values 가 멈춘다.

블로그 초안 도구는 2026-11-13 에 지웠다(가드만 남겼다). 배치 기록 줄(batch_notes.theory_claim_lines)이 이 가드를 불러, 단정이 깨진
날은 '전제가 어긋남'으로, 입력 계열이 끊긴 날(지수 기준 단절)은 '데이터 상태'로 알린다.

⚠️ 실데이터로 단정("2024년 대구 인허가가 2007년 이후 가장 적다" 등)을 확인하는 시험은 두지 않는다. 데이터가 앞으로 가면 단정이
깨질 수 있는데, 그걸 배치 게이트가 잡으면 그날 데이터 커밋 전체가 멈춘다(CLAUDE.md '게이트 시험은 데이터가 앞으로 가도 초록').

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - guard_values 4편 갈래에서 Link3ClaimError 를 SystemExit 으로 바꾸는 except 를 지우면 → test_claim_break_stops_the_guard
    (Link3ClaimError 가 그대로 샌다)
  - Link3DataError 갈래를 지우면 → test_data_break_is_not_blamed_on_the_text('문장을 먼저 고칠 것'으로 글쓴이 탓을 한다)
  - boom_table_html·names_eunneun 의 _nm 을 빼거나 _nm 이 SEARCH_NAME 대신 키를 돌려주면 → test_tables_and_lists_show_display_names
픽스처: 가드 시험은 link3_numbers 를 예외를 던지는 가짜로 바꾼다(저장소 데이터를 읽지 않는다). 이름 시험은 2026-10-18 4편 표의
전남광주 행(+23%, 25,202→27,368) 꼴이다.
"""
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import theory_guards as T  # noqa: E402
import theory_link3 as L3  # noqa: E402


def test_claim_break_stops_the_guard(monkeypatch):
    def broken(adv, sts, D=None):
        raise L3.Link3ClaimError('dg_24: 2024년이 더는 최저가 아니다')
    monkeypatch.setattr(L3, 'link3_numbers', broken)
    with pytest.raises(SystemExit) as e:
        T.guard_values(4, D={}, data=({}, {}))
    msg = str(e.value)
    assert msg == '4편을 만들 수 없다 — dg_24: 2024년이 더는 최저가 아니다. 문장을 먼저 고칠 것.', msg


def test_data_break_is_not_blamed_on_the_text(monkeypatch):
    def rebased(adv, sts, D=None):
        raise L3.Link3DataError('매매지수 기준 단절 — 매매지수 2026.01 (27개 지역, 예: 서울 189.83→94.62)')
    monkeypatch.setattr(L3, 'link3_numbers', rebased)
    with pytest.raises(SystemExit) as e:
        T.guard_values(4, D={}, data=({}, {}))
    msg = str(e.value)
    assert msg.startswith('4편을 만들 수 없다 — 매매지수 기준 단절') and T.NOT_THE_TEXT in msg, msg
    assert '문장을 먼저 고칠 것' not in msg and 'git pull' in msg, msg


def test_tables_and_lists_show_display_names():
    """4편 상승기 표·'2025년 최저' 목록은 지역 키가 아니라 보이는 이름(theory_link3.SEARCH_NAME — theory_guards 가 같은 표를 쓴다,
    '전남광주' → '광주·전남')을 찍고, 조사는 보이는 이름의 받침으로 붙인다(전수리뷰 BL2-10·X1-5). 굵게 판정은 키로 한다."""
    key = '전남광주'
    shown = T.SEARCH_NAME[key]
    assert shown != key
    t4 = L3.boom_table_html([('수도권', 1, 60.0, 212431, 177796), (key, 0, 23.0, 25202, 27368)])
    assert '<td>%s</td>' % shown in t4 and key not in t4 and '<b>수도권</b>' in t4 and '1.09배' in t4
    assert L3.names_eunneun(['경남', '제주']) == '경남·제주는'
    assert L3.names_eunneun(['경남', key]) == '경남·%s은' % shown
    assert L3.names_eunneun(['세종']) == '세종시는'
