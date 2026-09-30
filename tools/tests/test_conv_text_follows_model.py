# -*- coding: utf-8 -*-
"""'착공한 것의 N%가 3년 뒤 준공'의 N과 기준 연도가 모델 상수(sido_zones.CONV·CONV_START_FROM)와 같은지 본다.

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
import home_src as HS  # noqa: E402  (홈은 이 입구로만 읽는다 — 백로그 10)

PAT = re.compile(r'착공한 것의 (\d+)%가 3년 뒤 준공되는 게 (\d{4})년 이후 실측')


def test_home_how_text_matches_model_conversion():
    m = PAT.search(HS.home_source())
    assert m, '홈 산출 방법 문장을 못 찾았다 — 문구가 바뀌었으면 이 시험도 고칠 것'
    assert int(m.group(1)) == round(SZ.CONV * 100), (m.group(1), SZ.CONV)
    # ⚠️ 연도는 아직 CONV_FROM(착공÷인허가를 재는 첫 해 2012)과 대조한다 — 홈 index.html 은 H 묶음이 '2011년'으로 고친다.
    # 그때 이 줄을 SZ.CONV_START_FROM 으로 바꾼다(전수 리뷰 #111). 시도 리포트 쪽은 아래 시험이 이미 CONV_START_FROM 을 본다.
    assert int(m.group(2)) == SZ.CONV_FROM, (m.group(2), SZ.CONV_FROM)


def test_zone_generator_does_not_hardcode_conversion():
    s = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    assert '착공한 것의 %(convp)d%%가 %(lead)s 뒤 준공되는 게 %(conv_from)d년 이후 실측' in s
    assert not re.search(r"착공한 것의 \d+%%가", s), '생성기 문장에 전환율이 숫자로 박혔다'
    assert "'conv_from': SZ.CONV_START_FROM" in s, '시도 리포트의 측정 연도가 CONV 를 잰 첫 착공 연도가 아니다'


def test_conversion_start_year_is_where_conv_was_measured():
    """'착공한 것의 96%가 … 2011년 이후 실측'의 연도(CONV_START_FROM)부터 CONV_YEARS 쌍을 데이터로 다시 재면 CONV 다(전수 리뷰 #111).

    재현하는 실제 상태: 2026-09-23 점검이 문장의 연도를 CONV_FROM(2012 — 착공÷인허가를 재는 첫 해)에 묶어, 시도 리포트 19장이
    96% 의 측정 구간을 '2012년 이후'로 공개했다. 2012년부터 재면 94%다(착공 2012~2022, 11쌍).
    변이(실제로 확인): CONV_START_FROM 을 2012 로 바꾸면 재측정이 94% 라 빨개진다.
    픽스처: 저장소의 data-rest.json STATS(전국 착공·준공). 쌍 수를 CONV_YEARS 로 묶어 두어 새 완비 연도가 들어와도 값이 안 움직인다.
    """
    st = SZ._load_stats(os.path.join(ROOT, 'data-rest.json'))
    got = SZ.conv_measured(st)
    assert got is not None, '착공 %d년부터 %d쌍을 채우지 못했다' % (SZ.CONV_START_FROM, SZ.CONV_YEARS)
    assert round(got * 100) == round(SZ.CONV * 100), (got, SZ.CONV)


def test_zone_page_says_the_measured_start_year():
    """생성된 시도 리포트 문장 자체가 CONV_START_FROM 과 CONV 를 말한다(생성기 한 장을 메모리에서 굽는다).
    변이: build_page 의 'conv_from' 을 SZ.CONV_FROM 으로 되돌리면 빨개진다(실제로 확인)."""
    import make_sido_pages as P
    adv, stats = P.load()
    calc = adv['sido']
    html = P.build_page('서울', calc, stats, P.price_quarters(adv), calc['zones'])
    m = re.search(r'착공한 것의 (\d+)%가 (\d+)년 뒤 준공되는 게 (\d{4})년 이후 실측', html)
    assert m, '시도 리포트에서 전환율 문장을 못 찾았다'
    assert (int(m.group(1)), int(m.group(3))) == (round(calc['conv'] * 100), SZ.CONV_START_FROM)
    assert int(m.group(2)) == SZ.LEAD_Q // 4
