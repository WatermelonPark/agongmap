# -*- coding: utf-8 -*-
"""사이클 이론 5편(고리 ④ 착공 → 입주) — 본문 숫자는 전부 theory_link4 가 데이터에서 세고, 단정이 깨지면 생성이 멈춘다.

⚠️ 실데이터로 5편을 렌더링해 단정("옛 시차라면 2025년에 드러났어야" 등)을 확인하는 시험은 두지
않는다. 데이터가 앞으로 가면(2026년 연간치가 들어오면) 단정이 깨질 수 있는데, 그걸 배치 게이트가 잡으면
그날 데이터 커밋 전체가 멈춘다(CLAUDE.md '게이트 시험은 데이터가 앞으로 가도 초록'). 단정은 초안을 만들 때
render 가 지킨다. 여기서는 구조만 고정한다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - theory_link4 에서 본문이 쓰는 값의 함수(def _<키>) 하나를 지우면 → 자리 표시자 시험
  - render 에서 Link4ClaimError 를 SystemExit 으로 바꾸는 try/except 를 지우면 → 가드 시험
  - 5편 본문에 숫자를 손으로 박으면(예: '312,088호') → 손 숫자 시험
픽스처: 실제 POSTS 5편 본문과 theory_link4 소스. 가드 시험은 link4_numbers 를 예외를 던지는 가짜로 바꾼다.
"""
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import make_theory_post as T  # noqa: E402
import theory_link4 as L3  # noqa: E402

POST = next(p for p in T.POSTS if p["n"] == 5)
RENDER_KEYS = {'link', 'cycle', 'zone', 'exp', 'nsido', 'moveins'}


def test_every_placeholder_has_a_counted_value():
    src = io.open(L3.__file__, encoding='utf-8').read()
    made = set(re.findall(r'^    def _(\w+)\(\):', src, re.M))
    used = set(re.findall(r'%\((\w+)\)', POST['body']))
    assert used - RENDER_KEYS <= made, sorted(used - RENDER_KEYS - made)


def test_claim_break_stops_the_draft(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)

    def broken(adv, sts):
        raise L3.Link4ClaimError('dn25: 옛 시차 반례가 더는 성립하지 않는다')
    monkeypatch.setattr(L3, 'link4_numbers', broken)
    with pytest.raises(SystemExit) as e:
        T.render(POST)
    assert '5편을 만들 수 없다' in str(e.value)


def test_no_hand_written_counts_in_body():
    text = re.sub(r'%\(\w+\)s', '', POST['body']).replace('허가 100호 가운데', '')   # 비율을 풀어 쓴 분모
    # 연도(4자리)·편 번호·'1년' 같은 가정은 문장이다. 세대·호·퍼센트·배수는 전부 계산값이어야 한다.
    hand = re.findall(r'\d[\d,]*\s*(?:호|세대|%%|배)', text)
    assert not hand, hand
