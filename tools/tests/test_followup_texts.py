# -*- coding: utf-8 -*-
"""점검후속 ③④⑤⑥⑦ (2026-09-15) — 기간 정본·갱신 주기·카드 부호·입주물량 해설·병합 안내.

⚠️ 생성된 페이지를 라이브 데이터로 단정하지 않는다(배치는 pytest를 페이지 생성보다 먼저
돌린다). 함수와 원본(생성기·손으로 쓴 홈)과 저장된 값끼리의 일치로 본다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sido_zones as SZ  # noqa: E402
import make_sido_pages as P  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def _src(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _adv():
    return json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/',
                                _src('data.js'), re.S).group(1))


# ---- ③ 기간 정본 ----

def test_period_constants_follow_the_analysis():
    """정본 상수는 재산정한 리드타임과 같아야 한다. 재측정으로 값이 바뀌면 여기서 걸린다."""
    a = json.load(io.open(os.path.join(ROOT, 'tools', 'data', 'cycle_analysis.json'), encoding='utf-8'))
    assert a['leadtime']['old_months'] == SZ.START_DONE_MONTHS_OLD
    assert a['leadtime']['new_months'] == SZ.START_DONE_MONTHS_NEW


def test_permit_text_describes_nature_not_an_unmeasured_period():
    """인허가→입주 기간은 측정된 적이 없다(전국 집계 시차 0은 사업 단위 시차가 아니다).

    2026-09-15에 '약 3년'으로 박았다가 PM 반대 의견으로 되돌렸다. 기간 대신 성격을 쓴다.
    """
    assert not hasattr(SZ, 'PERMIT_TO_MOVEIN'), '인허가→입주 기간 상수가 되살아났다'
    assert SZ.PERMIT_NATURE in P.REFNOTE['pm']
    period = re.compile(r'\d+\s*(?:~\s*\d+)?\s*년 뒤 입주')
    for rel in ('tools/make_sido_pages.py', 'tools/make_monthly_page.py'):
        assert not period.search(_src(rel)), '%s가 인허가→입주 기간을 단정한다' % rel
    home = _src('index.html')
    pm = re.search(r"pm:'([^']*)'", home).group(1)
    assert SZ.PERMIT_NATURE in pm, '홈 인허가 안내문 사본이 정본 서술과 다르다'
    assert '약 3년 뒤 입주' not in home


# ---- ④ 갱신 주기 ----

def test_quarterly_verdict_is_not_described_as_weekly():
    s = _src('tools/make_sido_pages.py')
    assert '매주 자동 갱신' not in s
    assert '분기마다 갱신' in s
    assert SZ.quarter_text('2026Q2') == '2026년 2분기'
    assert _adv()['sido'].get('Ltxt') == SZ.quarter_text(_adv()['sido']['L'])


def test_home_supply_captions_say_quarterly():
    home = _src('index.html')
    for bad in ('분기 합산 · 홈 공급표와 같은 값 · 매주 자동 갱신', '지수 전월비 환산) · 매주 자동 갱신'):
        assert bad not in home, bad


# ---- ⑤ 카드 부호와 용어 ----

def test_card_text_never_pairs_a_minus_sign_with_shortfall():
    for dtot, ratio in ((686396, 0.60), (-13237, -0.19), (907, 0.126), (281, 0.009)):
        t = SZ.card_text(dtot, ratio)
        assert '−' not in t and '-' not in t, t
        assert ('부족' in t) == (dtot > 0) and ('여유' in t) == (dtot < 0), t


def test_stored_cards_match_the_function_and_the_display_integer():
    adv = _adv()
    H = adv['sido']['H']
    for z in adv['sido']['zones']:
        want = P.rnd(z['ref']) * H - P.rnd(z['fut']) - P.rnd(z['inow'])
        assert z['dtot'] == want, z['z']
        assert z['ctxt'] == SZ.card_text(z['dtot'], z['ratio'], H), z['z']


def test_home_and_hub_read_the_baked_card_text():
    home = _src('index.html')
    assert "z.ctxt" in home
    assert "tbSigned(z.tot)+'세대'+(z.rtxt" not in home, '홈 카드가 옛 부호 문구를 만든다'
    hub = _src('tools/make_sido_pages.py')
    assert "esc(o['ctxt'])" in hub
    assert '모자란 재고' not in hub and "'지난 4년 재고'" not in hub


def test_unsold_multiple_reads_as_percent_below_one():
    assert P.umx(0.05) == '5%' and P.umx(0.53) == '53%' and P.umx(2.4) == '2.4배'


def test_home_legend_says_what_the_color_means_and_when():
    home = _src('index.html')
    assert '앞으로 3년 필요한 만큼 지어지는지' in home and 'ADV.sido.Ltxt' in home
    assert '적정물량 대비 누적 순부족 · 기준' not in home


# ---- ⑥ 입주물량 ----

def test_moveins_page_explains_the_gap_to_the_verdict():
    s = _src('tools/make_indicator_pages.py')
    assert '지역 판정' in s and '/zone/' in s
    assert '착공한 물량의 약' in s
    assert '매주 갱신.</div>' not in s


# ---- ⑦ 병합 안내 (2026-09-15 사용자 결정으로 제거) ----

# 전남광주를 한 곳으로 보는 건 당연해 본문에 설명을 두지 않는다. 옛 주소 안내 페이지
# (/zone/광주/, /zone/전남/)만 예외다 — 그 페이지는 옮겨졌다는 사실 자체가 내용이다.
MERGE_EXPLAINER = re.compile(r'통합 발표|통합에 따라|한 곳으로 본|한 지역으로 봅니다|'
                             r'한 행으로 싣|두 지역(의)? 합으로 병합|왜 합쳐졌')


def test_no_merge_explainer():
    assert not hasattr(P, 'merge_note'), '통합 리포트 병합 안내가 되살아났다'
    srcs = ['tools/make_sido_pages.py', 'tools/make_monthly_page.py',
            'faq/index.html', 'cycle/index.html']
    for rel in srcs:
        text = _src(rel)
        if rel.endswith('.py'):
            # 주석·독스트링의 개발 기록은 화면에 안 나온다 — 따옴표 문자열 줄만 본다
            text = '\n'.join(l for l in text.splitlines()
                             if l.strip().startswith(("'", '"', "('", '("'))
                             or re.search(r"\bh\.append|return \(", l))
        m = MERGE_EXPLAINER.search(text)
        assert not m, '%s에 병합 설명 문구가 있다: %r' % (rel, m.group(0))
