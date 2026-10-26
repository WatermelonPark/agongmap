# -*- coding: utf-8 -*-
"""홈(index.html·home-app.js)에 손으로 적힌 숫자·출처를 정본과 대조한다 — 2026-09-30 전수 리뷰 #68·#111·#21.

홈 산출 방법의 '착공보다 15%쯤 많고'(#112)는 소개·FAQ 의 같은 문장과 한 시험(test_hand_page_numbers)이 같은 허용 폭으로 본다.

홈은 정적 파일이라 생성기가 숫자를 주입하지 못한다. 그래서 문장 속 숫자를 모델 상수·데이터에서 센 값과 맞춘다
(CLAUDE.md '같은 대상을 재는 코드가 둘 이상이면 같은 상수 + 일치 시험'). 픽스처 없이 실제 파일과 저장소 데이터를 읽는다.
기대값은 모델 상수(sido_zones)나 데이터가 앞으로 가도 변하지 않는 사실(착공 계열의 첫 해)에서 유도한다.
"""
import io
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


def test_unsold_definition_on_home_is_the_canonical_one():
    """홈 산출 방법의 미분양 줄과 시도 리포트 '어떻게 계산했나'·참고 행 설명 칸이 미분양을 정본 정의(SZ.UNSOLD_NATURE)
    그대로 말하고, 옛 손글씨 정의('안 팔리고 남은')를 다시 적지 않는다(2026-10-24 업계 표현 — 10-23 대표 용어 지시).
    예전엔 정본이 '분양했지만 아직 팔리지 않은 집(공사 중 포함)'인데 홈 줄과 시도 리포트 두 곳은 '지금 안 팔리고 남은 집·재고'로
    손으로 따로 적혀 있어, 정본을 바꿔도 따라오지 않았다.

    변이(실제로 확인): index.html 미분양 줄을 옛 '지금 안 팔리고 남은 집'으로 되돌리면, 또는 make_sido_pages 의 설명 칸을
          옛 '지금 안 팔리고 남은 재고' 손글씨로 되돌리면 빨개진다. SZ.UNSOLD_NATURE 만 바꾸고 홈 줄을 그대로 두어도 빨개진다.
    픽스처: 실제 index.html 과 make_sido_pages 소스(생성기를 돌리지 않고 문구가 정본에서 오는지 본다).
    """
    li = re.search(r'<li><b>미분양</b>[^<]*', _html())
    assert li and SZ.UNSOLD_NATURE in li.group(0), (SZ.UNSOLD_NATURE, li and li.group(0))
    import make_sido_pages as M
    src = io.open(M.__file__, encoding='utf-8').read()
    assert '안 팔리고 남은' not in src, '시도 리포트에 미분양 손글씨 정의가 남았다'
    assert src.count('SZ.UNSOLD_NATURE') >= 3, '시도 리포트 미분양 정의가 정본 상수를 쓰지 않는다'


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


# 판정 창 햇수가 나오는 자리 — (정규식, 모델 상수). '1년 적정물량의 N배'(need_mult 의 고정 단위)는 모델 창이 아니라 넣지 않는다.
YEAR_SPOTS = (
    (r'지난 (\d+)년', 'BACKLOG_WINDOW'),
    (r'(\d+)년 뒤로 (?:밀|민)', 'LEAD_Q'),
    (r'(\d+)년 뒤 준공', 'LEAD_Q'),
    (r'시도별 (\d+)년 공급', 'LEAD_Q'),
    (r'공급은 (\d+)년', 'LEAD_Q'),
    (r'앞으로 (\d+)년', 'LEAD_Q'),
    (r'(\d+)년 적정물량 −', 'LEAD_Q'),
)


def _year_hits(text):
    out = {}
    for pat, const in YEAR_SPOTS:
        want = '%g' % (getattr(SZ, const) / 4.0)
        out[pat] = (want, re.findall(pat, text))
    return out


def test_window_years_sit_in_the_right_places():
    """홈·소개·FAQ 손 문장의 판정 창 햇수가 자리마다 모델 상수와 같다 — '지난 N년'은 BACKLOG_WINDOW/4, '앞으로 N년'·'N년 뒤로 밀어'·
    'N년 뒤 준공'·'시도별 N년 공급'·히어로 '공급은 N년'·식의 'N년 적정물량 −'은 LEAD_Q/4(전수리뷰 2차 T2-4).

    예전 시험(test_home_first_screen)은 산출 방법 첫 항목의 햇수가 {3, 4} 집합 안인지만 봐서 '지난 4년'을 '지난 3년'으로, '3년 뒤로
    밀어'를 '4년'으로 바꿔도 초록이었고(실제로 확인), 대표가 LEAD_Q·BACKLOG_WINDOW 를 바꾸면 굵은 식만 빨개지고 나머지 홈 문장은 옛
    햇수로 남았다. 홈은 생성 구간(HOME_SUMMARY·설명 메타 — make_home_summary 가 모델에서 굽는다)을 빼고 본다. 홈에서는 자리마다 1건
    이상이어야 한다(정규식이 아무것도 못 잡아 초록이 되지 않게).
    변이(각각 실제로 확인): index.html 산출 방법 산문의 '지난 4년'을 '지난 3년'으로, '착공 실적을 3년 뒤로 밀어'를 '4년'으로,
    투자지표 출처 줄의 '3년 뒤로 민 추정'을 '4년'으로 바꾸면 빨개진다.
    픽스처: 저장소 홈 소스(home_source — index.html + 홈 스크립트)·about·faq.
    """
    home = re.sub(r'<!--HOME_SUMMARY_START-->.*?<!--HOME_SUMMARY_END-->', '', HS.home_source(), flags=re.S)
    home = re.sub(r'<meta [^>]*description[^>]*>', '', home)
    bad = []
    for pat, (want, got) in _year_hits(home).items():
        assert got, '홈에서 %s 자리를 못 찾았다 — 문구를 바꿨으면 이 목록도 고칠 것' % pat
        bad += ['홈 %s: %s(모델 %s)' % (pat, g, want) for g in got if g != want]
    for rel in ('about/index.html', 'faq/index.html'):
        text = io.open(os.path.join(HS.ROOT, rel), encoding='utf-8').read()
        bad += ['%s %s: %s(모델 %s)' % (rel, pat, g, want) for pat, (want, got) in _year_hits(text).items() for g in got if g != want]
    assert not bad, '판정 창 햇수가 모델과 다른 자리: %s' % bad
