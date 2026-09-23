# -*- coding: utf-8 -*-
"""'착공한 것의 N%가 3년 뒤 준공'의 N과 기준 연도가 모델 상수(sido_zones.CONV·CONV_FROM)와 같은지 본다.

시도 페이지 생성기는 2026-09-23부터 이 값을 상수에서 읽는다. 홈 산출 방법(index.html)은 손으로
쓴 문장이라 셀 수 없어, 전환율을 다시 재면 홈만 옛 숫자로 남는다('96%·15년치'가 두 곳에 박혀
있던 것을 이날 점검에서 찾았다). CLAUDE.md "같은 대상을 재는 코드가 둘 이상이면 같은 상수를 쓰고
그 일치를 시험으로 고정한다".

무엇을 깨뜨리면 빨개지나: index.html 의 '96%'를 '95%'로 바꾸거나 sido_zones.CONV 를 0.94 로
바꾸면 실패한다(앞의 것은 실제로 확인). 생성기 쪽은 문장에 숫자가 다시 박히면 두 번째 시험이
실패한다. 픽스처 없이 실제 파일을 읽는다.
"""
import io
import os
import re
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sido_zones as SZ  # noqa: E402

PAT = re.compile(r'착공한 것의 (\d+)%가 3년 뒤 준공되는 게 (\d{4})년 이후 실측')


def test_home_how_text_matches_model_conversion():
    s = io.open(os.path.join(ROOT, 'index.html'), encoding='utf-8').read()
    m = PAT.search(s)
    assert m, '홈 산출 방법 문장을 못 찾았다 — 문구가 바뀌었으면 이 시험도 고칠 것'
    assert int(m.group(1)) == round(SZ.CONV * 100), (m.group(1), SZ.CONV)
    assert int(m.group(2)) == SZ.CONV_FROM, (m.group(2), SZ.CONV_FROM)


def test_zone_generator_does_not_hardcode_conversion():
    s = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    assert '착공한 것의 %d%%가 3년 뒤 준공되는 게 %d년 이후 실측' in s
    assert not re.search(r"착공한 것의 \d+%%가", s), '생성기 문장에 전환율이 숫자로 박혔다'
