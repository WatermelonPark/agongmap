# -*- coding: utf-8 -*-
"""'착공한 것의 N%가 3년 뒤 준공'의 N과 기준 연도가 모델 상수(sido_zones.CONV·CONV_START_FROM)와 같은지 본다.

시도 페이지 생성기는 2026-09-23부터 이 값을 상수에서 읽는다. 홈 산출 방법(index.html)은 손으로
쓴 문장이라 셀 수 없어, 전환율을 다시 재면 홈만 옛 숫자로 남는다('96%·15년치'가 두 곳에 박혀
있던 것을 이날 점검에서 찾았다). CLAUDE.md "같은 대상을 재는 코드가 둘 이상이면 같은 상수를 쓰고
그 일치를 시험으로 고정한다".

무엇을 깨뜨리면 빨개지나: index.html 의 '96%'를 '95%'로 바꾸거나 sido_zones.CONV 를 0.94 로
바꾸면 실패한다(앞의 것은 실제로 확인). 생성기 쪽은 문장에 숫자가 다시 박히면 두 번째 시험이
실패한다. 픽스처 없이 실제 파일을 읽는다. CONV 를 데이터로 다시 잰 값과의 대조는 게이트가 아니라 배치 기록 ℹ️ 줄이다
(batch_notes.conv_model_lines — 원천 소급 정정이 그날 커밋을 막지 않게, 2026-10-21 대표 결정).
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
    # 기준 연도는 CONV 를 잰 첫 착공 연도(CONV_START_FROM, 2011)이지 CONV_FROM(착공÷인허가의 첫 해, 2012)이 아니다(전수리뷰 #111).
    assert int(m.group(2)) == SZ.CONV_START_FROM, (m.group(2), SZ.CONV_START_FROM)


def test_zone_generator_does_not_hardcode_conversion():
    s = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    assert '착공한 것의 %(convp)d%%가 %(lead)s 뒤 준공되는 게 %(conv_from)d년 이후 실측' in s
    assert not re.search(r"착공한 것의 \d+%%가", s), '생성기 문장에 전환율이 숫자로 박혔다'
    assert "'conv_from': SZ.CONV_START_FROM" in s, '시도 리포트의 측정 연도가 CONV 를 잰 첫 착공 연도가 아니다'


def _conv_stats(done_per_month, last_year=None):
    """합성 STATS: 착공은 해마다 달 100, 준공은 달 done_per_month — 연도별 비(준공 ÷ 착공)가 모두 done_per_month/100 이다."""
    last_year = last_year or SZ.CONV_START_FROM + SZ.CONV_YEARS - 1 + SZ.LEAD_Q // 4
    dates = ['%d.%02d' % (y, m) for y in range(SZ.CONV_START_FROM, last_year + 1) for m in range(1, 13)]
    return {'착공': {'dates': dates, 'series': {'전국': [100.0] * len(dates)}},
            '준공': {'dates': dates, 'series': {'전국': [float(done_per_month)] * len(dates)}}}


def test_conversion_drift_is_a_batch_note_not_a_gate():
    """모델 전환율 CONV 를 그 구간(착공 CONV_START_FROM 년부터 CONV_YEARS 쌍)의 데이터로 다시 잰 값이 화면 정수로 다르면 배치 기록에
    ℹ️ 한 줄(batch_notes.conv_model_lines)이 남고, 게이트는 막지 않는다(2026-10-21 대표 결정).

    재현하는 실제 상태: 2026-10-21 배치에서 원천이 2025년 착공·준공 240칸을 소급 정정해(투자지표 인허가와 기본통계 누계가 갈린 해를 다시
    받음) 같은 구간의 재측정이 95.8% → 94.7% 가 되었다. 예전 시험(test_conversion_start_year_is_where_conv_was_measured)이 이것을 게이트에서
    단정해 그날 데이터 커밋이 막혔다 — 상수를 바꾸는 일은 판정·문구가 함께 움직이는 사람의 결정이라 게이트가 아니라 알림으로 올린다.
    측정 연도 문구(CONV_START_FROM)가 모델과 같은지는 위 두 시험과 아래 시도 리포트 시험이 계속 게이트로 본다.
    변이(각각 실제로 확인): conv_model_lines 가 늘 [] 를 돌려주면 합성 95% 갈래가, 비교를 ±1%p 허용으로 바꾸면 같은 갈래가, None 갈래를
          [] 로 바꾸면 '재측정 불가' 갈래가 빨개진다.
    픽스처: 합성 STATS 세 벌(재측정 96%·95%·구간 미달)과 저장소 data-rest.json(두 갈래 모두 의미 있게 본다 — 같으면 줄 없음, 다르면 그 값).
    """
    import batch_notes as N
    want = round(SZ.CONV * 100)
    assert N.conv_model_lines(_conv_stats(want)) == []
    line = N.conv_model_lines(_conv_stats(want - 1))
    assert len(line) == 1 and line[0].startswith(N.ML.MARK) and '%d%%' % (want - 1) in line[0] and '%d%%' % want in line[0], line
    short = N.conv_model_lines(_conv_stats(want, last_year=SZ.CONV_START_FROM + 3))
    assert len(short) == 1 and '재측정 불가' in short[0], short
    assert N.conv_model_lines({}) == [], '착공·준공 계열이 통째로 없는 데이터(축소 픽스처)에는 줄이 없다'
    st = SZ._load_stats(os.path.join(ROOT, 'data-rest.json'))
    got = SZ.conv_measured(st)
    real = N.conv_model_lines(st)
    if got is not None and round(got * 100) == want:
        assert real == [], real
    else:
        assert len(real) == 1, real


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
