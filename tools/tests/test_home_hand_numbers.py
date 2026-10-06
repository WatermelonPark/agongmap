# -*- coding: utf-8 -*-
"""홈(index.html·home-app.js)에 손으로 적힌 숫자·출처를 정본과 대조한다 — 2026-09-30 전수 리뷰 #68·#111·#21.

홈 산출 방법의 '착공보다 15%쯤 많고'(#112)는 소개·FAQ 의 같은 문장과 한 시험(test_hand_page_numbers)이 같은 허용 폭으로 본다.

홈은 정적 파일이라 생성기가 숫자를 주입하지 못한다. 그래서 문장 속 숫자를 모델 상수·데이터에서 센 값과 맞춘다
(CLAUDE.md '같은 대상을 재는 코드가 둘 이상이면 같은 상수 + 일치 시험'). 픽스처 없이 실제 파일과 저장소 데이터를 읽는다.
기대값은 모델 상수(sido_zones)나 데이터가 앞으로 가도 변하지 않는 사실(착공 계열의 첫 해)에서 유도한다.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _html():
    return dict(HS.home_files())['index.html']


def test_occupancy_source_line_conversion_is_the_model_constant():
    """투자지표 입주물량 출처 줄의 '전환율 0.958' 은 sido_zones.CONV 와 같다(전수리뷰 #68).

    변이(실제로 확인): SZ.CONV 를 0.962(반올림하면 여전히 96%라 산출 방법 문장 시험은 초록)로 바꾸면 빨개진다.
    픽스처: 실제 index.html 의 출처 줄.
    """
    m = re.findall(r'전환율 (0\.\d+)\)', _html())
    assert len(m) == 1, '입주물량 출처 줄의 전환율을 찾지 못했다(또는 여러 곳이다): %s' % m
    assert float(m[0]) == SZ.CONV, (m[0], SZ.CONV)


def test_conversion_measurement_start_year_is_the_start_series_first_full_year():
    """'착공한 것의 96%가 3년 뒤 준공되는 게 N년 이후 실측'의 N 은 CONV 를 잰 첫 착공 연도 — 전국 착공 계열이 12개월
    온전한 첫 해다(전수리뷰 #111). 예전엔 다른 측정(착공÷인허가)의 첫 해 CONV_FROM(2012)을 붙여, 2012년부터 재면 94%라
    문장이 성립하지 않았다.

    변이(실제로 확인): index.html 의 연도를 옛 2012 로 되돌리면 빨개진다.
    픽스처: 저장소 data-rest.json 의 착공 전국 계열(2011.01 부터 — 이 첫 해는 데이터가 앞으로 가도 바뀌지 않는다).
    정본 상수 SZ.CONV_START_FROM(시도 리포트 문장이 같은 상수를 쓴다)과도 같아야 한다.
    """
    m = re.search(r'착공한 것의 (\d+)%가 3년 뒤 준공되는 게 (\d{4})년 이후 실측', _html())
    assert m
    st = SZ._load_stats()['착공']
    years = {}
    for d, v in zip(st['dates'], st['series']['전국']):
        years.setdefault(d[:4], []).append(v)
    first = min(y for y, xs in years.items() if len(xs) == 12 and all(x is not None for x in xs))
    assert int(m.group(2)) == int(first), (m.group(2), first)
    assert int(m.group(2)) == SZ.CONV_START_FROM, (m.group(2), SZ.CONV_START_FROM)


def test_unsold_source_on_home_agrees_with_the_reference_note():
    """홈 산출 방법의 미분양 출처와 공급표 참고 행 안내(TB_REFNOTE.un — 시도 리포트 REFNOTE 의 거울)가 같은 기관을
    말한다(전수리뷰 #21). 예전엔 한 화면에서 '한국부동산원'과 '국토교통부 월간 집계'로 갈렸다.

    변이(실제로 확인): index.html 미분양 줄을 옛 '(한국부동산원)'으로 되돌리면 빨개진다.
    픽스처: 실제 index.html·home-app.js. 기관 이름은 참고 안내의 괄호 속에서 읽는다(통합 때 REFNOTE 문구가 바뀌어도 따라간다).
    """
    files = dict(HS.home_files())
    body = re.search(r'var TB_REFNOTE=\{(.*?)\n\};', files['home-app.js'], re.S).group(1)
    un = dict(re.findall(r"(\w+):'((?:[^'\\]|\\.)*)'", body))['un']
    orgs = [o for o in ('국토교통부', '한국부동산원') if o in un]
    assert orgs, '참고 안내에서 미분양 출처 기관을 찾지 못했다: %s' % un
    li = re.search(r'<li><b>미분양</b>[^<]*', files['index.html'])
    assert li, '홈 산출 방법의 미분양 줄을 찾지 못했다'
    for o in orgs:
        assert o in li.group(0), '홈 산출 방법 미분양 줄에 %s 가 없다: %s' % (o, li.group(0))
    import make_sido_pages as M   # 정본 UN_SOURCE(시도 리포트 참고 안내·방법론 문단이 같은 상수를 쓴다)
    assert '(%s)' % M.UN_SOURCE in li.group(0), (M.UN_SOURCE, li.group(0))


def test_occupancy_legend_uses_the_canonical_thresholds():
    """투자지표 입주물량 범례의 문턱(적정물량의 N% 초과 / M% 미만)은 대표 결정 ③ 정본(/moveins/ 와 한 값, 70%·130%)이다.
    예전 범례는 '분기 적정물량 이상'·'적정물량의 60% 미만'으로 /moveins/ 와 달랐다(전수리뷰 #60·#113 홈 쪽 문구).

    변이(실제로 확인): 범례를 옛 '적정물량의 60% 미만'으로 되돌리면 빨개진다.
    픽스처: 실제 index.html 범례를 SZ.OCC_LO_PCT·OCC_HI_PCT 와 대조한다(home-stats.js occCls 는 같은 상수를 split_data 가
            ADV.occupancy.band 로 실어 준 값으로 칠한다 — test_occ_band 가 본다).
    """
    lo, hi = SZ.OCC_LO_PCT, SZ.OCC_HI_PCT
    # 범례 낱말은 신호등과 같은 적음·보통·많음이다(백로그 36-2·10, 2026-10-06 — 막대 색과 같은 색, 왼쪽 적음 → 오른쪽 많음).
    legs = [x for x in re.findall(r'<div class="adv-legend">(.*?)</div>', _html(), re.S) if '적음(' in x]
    assert len(legs) == 1, '입주물량 범례를 찾지 못했다'
    assert re.findall(r'많음\((\d+)% 초과\)', legs[0]) == [str(hi)], legs[0]
    assert re.findall(r'적음\((\d+)% 미만\)', legs[0]) == [str(lo)], legs[0]
    assert legs[0].index('적음') < legs[0].index('보통') < legs[0].index('많음'), '범례는 적음 → 많음 순서(가로 축 오른쪽 = 많음)'
