# -*- coding: utf-8 -*-
"""해마다의 입주 전망(sido_zones.yearly_supply, 2026-10-05 대표 요청 — '지금보다 1년·2년·3년 뒤가 중요하다').

판정은 3년 합계(calc 의 fut)로 그대로 두고, 같은 식을 네 분기씩 나눈 해마다의 '입주 추정 ÷ 적정'을 지역 허브 칸과 시도 리포트에
보조로 보여 준다(경기: 3년 합계 88%로 균형인데 1년 차는 73%). 같은 대상을 재는 두 코드라 세 해의 입주 추정 합이 판정의 fut 와
같아야 한다(CLAUDE.md '같은 대상을 재는 코드는 같은 상수·같은 식').

변이(각각 실제로 확인): yearly_supply 가 LEAD_Q 대신 LEAD_Q−1 로 착공을 당겨 오면 합 대조가, CONV 를 빼면 합 대조가, 마지막
묶음의 적정을 4분기로 고정하면(H=11 사례) 부분 묶음 단정이, build_hub 가 신호등 칸을 빼면 허브 단정이, build_page 가 블록을
빼면 리포트 단정이 빨개진다.
픽스처: 저장소 data.js 의 실제 판정·착공(값은 함수로 유도 — 데이터가 앞으로 가도 같은 판정), H=11 합성 시야.
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _ctx():
    adv, stats = M.load()
    s = adv['sido']
    return adv, stats, s, SZ.qidx(int(s['L'][:4]), int(s['L'][-1]))


def test_three_years_add_up_to_the_verdict_supply():
    adv, stats, s, Lq = _ctx()
    for z in s['zones']:
        ys = SZ.yearly_supply(stats, z['z'], Lq, s['H'])
        assert len(ys) == -(-s['H'] // 4) and [y['n'] for y in ys] == list(range(1, len(ys) + 1)), z['z']
        ref = SZ.REF_Q[z['z']]
        total = sum(y['pct'] / 100.0 * ref * (4 if i < len(ys) - 1 or s['H'] % 4 == 0 else s['H'] % 4)
                    for i, y in enumerate(ys))
        # 퍼센트 반올림(해마다 ±0.5%p × 적정)만큼만 어긋날 수 있다
        assert abs(total - z['fut']) <= 0.005 * ref * 4 * len(ys) + 1, (z['z'], total, z['fut'])


def test_partial_last_year_uses_only_its_quarters():
    adv, stats, s, Lq = _ctx()
    ys = SZ.yearly_supply(stats, '서울', Lq, 11)
    assert len(ys) == 3 and ys[-1]['from'] == SZ.qkey(Lq + 9) and ys[-1]['to'] == SZ.qkey(Lq + 11), ys
    st = SZ.quarterly(stats, '착공', '서울')
    f = sum(st.get(i - SZ.LEAD_Q, 0) * SZ.CONV for i in range(Lq + 9, Lq + 12))
    assert ys[-1]['pct'] == SZ.half_up(100.0 * f / (SZ.REF_Q['서울'] * 3)), ys[-1]


def test_move_in_percents_round_half_up_like_moveins():
    """해마다 입주 %·'… 너머' %는 /moveins/(pct_shown)·occ_level 계약과 같은 half_up 으로 찍는다 — 파이썬 round 는 짝수 쪽으로
    반올림해 정확히 .5 인 값(12.5 → 12)이 /moveins/ 와 1%p 갈리고, 130.5 면 색이 보통·많음 사이에서 뒤집힌다(2026-10-06 리뷰).
    변이(실제로 확인): pbr_pct 를 int(round(...)) 로 되돌리면 빨개진다. 픽스처: 이진수로 정확한 0.125(= 12.5%)."""
    assert SZ.pbr_pct(0.125) == 13 and SZ.half_up(12.5) == 13


def _split_pct(row):
    return int(re.search(r'적정물량의 (\d+)%입니다', row['split']['ref'][1]).group(1))


def _ref_cell_pct(block):
    return int(re.search(r'<span class="zo-p">(\d+)%</span><small>[^<]*너머', block).group(1))


def test_beyond_cell_and_split_line_print_one_integer(monkeypatch):
    """'… 너머' 회색 칸(outlook_block)과 바로 위 split 줄('…적정물량의 N%입니다'), 경고(pwarn)가 한 정수를 쓴다 — 화면 정수는 원값에서
    한 번만 반올림한다(sido_zones.pbr_pct, 전수리뷰 Z1-3·X1-2).

    재현한 실제 상태(2026-10-18): calc 가 pbr 을 셋째 자리로 굳혀 저장해(원값 0.424576 → 0.425) 경북 리포트가 줄에는 42%, 그 아래
    회색 칸에는 43%(저장값 42.5 를 다시 반올림)를 찍었다. 100×원값의 소수부가 [0.45, 0.5) 인 지역마다(지역당 약 5%) 생긴다. 원값이
    [0.9445, 0.945) 이면 pwarn(원값 94%)과 저장값 경고(0.945 → 95%)도 갈려 test_split_permit 의 경고 대조가 빨개진다.
    변이(실제로 확인): calc 의 'pbr' 저장을 round(sig['pbr'], 3) 로 되돌리면 합성 갈래 둘(42·94)과 실데이터 경북이 빨개진다.
    픽스처: ① 저장소 STATS 로 지금 코드의 SZ.calc 를 새로 돌린 행(배치가 다음 회차에 싣는 값 — 저장된 data.js 의 옛 행은 다음 배치 전까지
    셋째 자리일 수 있다), ② permit_signal 을 원값 0.424576(경북 10-18 모양)·0.94475(문턱 경계)·1.240479(경고 없는 갈래, 경기 모양)로
    바꾼 합성 행 — 실데이터가 그 창에 없어도 늘 돌고, 경고 있음·없음 두 갈래를 다 지난다.
    """
    adv, stats, s, _ = _ctx()
    fresh = SZ.calc(stats)
    Lq, H = SZ.qidx(int(fresh['L'][:4]), int(fresh['L'][-1])), fresh['H']
    rows = [z for z in fresh['zones'] if z.get('pbr') is not None]
    assert rows, '인허가 신호가 있는 지역이 없다 — 시험이 헛돈다'
    for z in rows:
        want = SZ.pbr_pct(z['pbr'])
        block = M.outlook_block(SZ.yearly_supply(stats, z['z'], Lq, H), z['pbr'], H)
        assert _split_pct(z) == want == _ref_cell_pct(block), (z['z'], z['pbr'], _split_pct(z), _ref_cell_pct(block))
        assert z['pwarn'] == SZ.pbr_thin(z['pbr']) == z['split']['ref'][3], z['z']
    for raw, pct in ((0.424576, 42), (0.94475, 94), (1.240479, 124)):
        monkeypatch.setattr(SZ, 'permit_signal', lambda st, zz, ref, _r=raw: {'pbr': _r, 'pdec': 0.2, 'pconv': 0.8})
        row = [z for z in SZ.calc(stats)['zones'] if z['z'] == '경북'][0]
        block = M.outlook_block(SZ.yearly_supply(stats, '경북', Lq, H), row['pbr'], H)
        assert _split_pct(row) == SZ.pbr_pct(row['pbr']) == _ref_cell_pct(block) == pct, (raw, row['pbr'])
        assert row['pwarn'] == SZ.pbr_thin(row['pbr']) == row['split']['ref'][3] == (pct < SZ.PWARN_CUT * 100), raw


def test_hub_and_report_show_the_years():
    adv, stats, s, Lq = _ctx()
    h = M.build_hub(s, stats)
    cards = re.findall(r'<a href="/zone/[^"]+/"[^>]*>(.*?)</a>', h, re.S)
    # 허브 칸은 2026-10-05 대표 결정으로 막대 대신 신호등(make_sido_pages.lights_html)을 싣는다 — test_zone_lights
    with_out = [c for c in cards if 'class="zl"' in c]
    assert len(with_out) == len(s['zones']), (len(with_out), len(s['zones']))
    gy = SZ.yearly_supply(stats, '경기', Lq, s['H'])
    assert M.lights_aria(gy) in h
    calc = s
    pq = {}
    others = s['zones']
    page = M.build_page('경기', calc, stats, pq, others)
    assert '<div class="zout">' in page and '3년 너머' in page


def test_outlook_picture_reads_out_the_states_and_the_reference():
    """해마다 입주 그림(role=img)의 읽어 줄 글(aria-label)이 그림 칸이 보이는 것을 다 말한다 — 해마다의 퍼센트와 막대 아래 상태 낱말
    (적음·보통·많음), '… 너머' 참고 칸이 있으면 그 퍼센트(전수리뷰 Z1-11). img 의 자식 글자는 보조기술에 읽히지 않는다.
    재현한 실제 상태(10-18 zone/전남광주): aria-label '적정 대비 입주 1년 차 96%, 2년 차 23%, 3년 차 48%' — 화면의 '1년 차 · 보통'·
    '2년 차 · 적음'과 회색 '48% 3년 너머'가 이름에 없었다.
    변이(실제로 확인): outlook_aria 를 옛 '적정 대비 입주 …'(상태·참고값 없음)로 되돌리면 빨개진다.
    픽스처: 저장소 판정·착공으로 센 경기 해마다 칸에 참고값 1.26(126%)을 준 블록과 주지 않은 블록 — 신호등 세 낱말이 다 나오도록
    합성 칸(61·96·140%)도 하나.
    """
    adv, stats, s, Lq = _ctx()
    real = SZ.yearly_supply(stats, '경기', Lq, s['H'])
    synth = [{'n': 1, 'from': '2026Q3', 'to': '2027Q2', 'pct': 61}, {'n': 2, 'from': '2027Q3', 'to': '2028Q2', 'pct': 96},
             {'n': 3, 'from': '2028Q3', 'to': '2029Q2', 'pct': 140}]
    for ys in (real, synth):
        for pbr in (1.26, None):
            block = M.outlook_block(ys, pbr, s['H'])
            aria = re.search(r'<div class="zo zo-lg" role="img" aria-label="([^"]*)">', block).group(1)
            shown = re.findall(r'<span class="zo-p">(\d+)%</span><small>([^<]*)</small>', block)
            assert len(shown) == len(ys) + (pbr is not None), shown
            for (pct, lab), y in zip(shown, ys):
                n, word = re.match(r'(\d+)년 차 · (\S+)', lab).groups()
                assert '%s년 차 %s%% %s' % (n, pct, word) in aria, (aria, lab)
            if pbr is not None:
                pct, lab = shown[-1]
                assert '%s(참고) %s%%' % (lab, pct) in aria, aria
            else:
                assert '참고' not in aria
    assert {w for w in ('적음', '보통', '많음') if w in M.outlook_aria(synth)} == {'적음', '보통', '많음'}
