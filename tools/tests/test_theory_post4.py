# -*- coding: utf-8 -*-
"""사이클 이론 4편(고리 ③) — 본문 숫자는 전부 theory_link3 가 데이터에서 세고, 단정이 깨지면 생성이 멈춘다.

⚠️ 실데이터로 4편을 렌더링해 단정("2024년 대구 인허가가 2007년 이후 가장 적다" 등)을 확인하는 시험은 두지
않는다. 데이터가 앞으로 가면(2026년 연간치가 들어오면) 단정이 깨질 수 있는데, 그걸 배치 게이트가 잡으면
그날 데이터 커밋 전체가 멈춘다(CLAUDE.md '게이트 시험은 데이터가 앞으로 가도 초록'). 단정은 초안을 만들 때
render 가 지킨다. 여기서는 구조만 고정한다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - theory_link3 에서 본문이 쓰는 값의 함수(def _<키>) 하나를 지우면 → 자리 표시자 시험
  - render 에서 Link3ClaimError 를 SystemExit 으로 바꾸는 try/except 를 지우면 → 가드 시험
  - 4편 본문에 숫자를 손으로 박으면(예: '2,996호') → 손 숫자 시험
픽스처: 실제 POSTS 4편 본문과 theory_link3 소스. 가드 시험은 link3_numbers 를 예외를 던지는 가짜로 바꾼다.
"""
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402
import theory_link3 as L3  # noqa: E402

POST = next(p for p in T.POSTS if p['n'] == 4)
RENDER_KEYS = {'link', 'cycle', 'zone', 'exp', 'nsido', 'moveins'}


def test_every_placeholder_has_a_counted_value():
    src = io.open(L3.__file__, encoding='utf-8').read()
    made = set(re.findall(r'^    def _(\w+)\(\):', src, re.M))
    used = set(re.findall(r'%\((\w+)\)', POST['body']))
    assert used - RENDER_KEYS <= made, sorted(used - RENDER_KEYS - made)


def test_claim_break_stops_the_draft(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)

    def broken(adv, sts):
        raise L3.Link3ClaimError('dg_24: 2024년이 더는 최저가 아니다')
    monkeypatch.setattr(L3, 'link3_numbers', broken)
    with pytest.raises(SystemExit) as e:
        T.render(POST)
    assert '4편을 만들 수 없다' in str(e.value)


def test_no_hand_written_counts_in_body():
    text = re.sub(r'%\(\w+\)s', '', POST['body']).replace('허가 100세대 가운데', '')   # 비율을 풀어 쓴 분모(단위 세대 — 백로그 36-2)
    # 연도(4자리)·편 번호·'1년' 같은 가정은 문장이다. 세대·호·퍼센트·배수는 전부 계산값이어야 한다.
    hand = re.findall(r'\d[\d,]*\s*(?:호|세대|%%|배)', text)
    assert not hand, hand


def test_no_ho_unit_left_in_any_post():
    """물량 단위는 '세대'(2026-10-06 대표 결정, 백로그 36-2). 자리 표시자 바로 뒤의 '호'(예: '%(se_demol_n)s호쯤')는 위 손 숫자 시험이
    자리를 지운 뒤 보므로 잡지 못했다 — 4편 '허가 100세대 가운데 17호쯤'이 그대로 남아 있었다(전수리뷰 BL2-13).
    변이(실제로 확인): 4편 본문을 '%(se_demol_n)s호쯤은'으로 되돌리면 빨개진다. 픽스처: 실제 POSTS 1~7편 본문."""
    bad = [(p['n'], m) for p in T.POSTS for m in re.findall(r'%\(\w+\)s\s*호|\d\s*호(?!선)', p['body'])]
    assert len(T.POSTS) >= 7 and not bad, bad


def test_tables_and_lists_show_blog_names(monkeypatch):
    """3편 동조성 표·4편 상승기 표·4편 '2025년 최저' 목록은 지역 키가 아니라 블로그 이름(P.SEARCH_NAME, '전남광주' → '광주·전남')을
    찍고, 조사는 보이는 이름의 받침으로 붙인다(전수리뷰 BL2-10·X1-5). 굵게(본문이 다루는 최저 지역) 판정은 키로 한다.
    픽스처: 2026-10-18 /cycle/ 동조성 표의 꼴(…, 충북 0.78, 전남광주 0.71, 서울 0.55)과 4편 표의 전남광주 행(+23%, 25,202→27,368).
    변이(실제로 확인): sync_table 의 P.SEARCH_NAME 을 빼거나, boom_table_html·names_eunneun 의 _nm 을 빼면 빨개진다."""
    key = '전남광주'
    shown = P.SEARCH_NAME[key]
    monkeypatch.setattr(T, 'CYCLE_SYNC', [dict(region='충북', corr=0.78), dict(region=key, corr=0.71), dict(region='서울', corr=0.55)])
    t3 = T.sync_table()
    assert shown in t3 and key not in t3 and '<b>서울</b>' in t3
    t4 = L3.boom_table_html([('수도권', 1, 60.0, 212431, 177796), (key, 0, 23.0, 25202, 27368)])
    assert '<td>%s</td>' % shown in t4 and key not in t4 and '<b>수도권</b>' in t4 and '1.09배' in t4
    assert L3.names_eunneun(['경남', '제주']) == '경남·제주는'
    assert L3.names_eunneun(['경남', key]) == '경남·%s%s' % (shown, P.eunneun(shown))
