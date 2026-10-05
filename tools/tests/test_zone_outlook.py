# -*- coding: utf-8 -*-
"""해마다의 입주 전망(sido_zones.yearly_supply, 2026-10-05 대표 요청 — '지금보다 1년·2년·3년 뒤가 중요하다').

판정은 3년 합계(calc 의 fut)로 그대로 두고, 같은 식을 네 분기씩 나눈 해마다의 '입주 추정 ÷ 적정'을 지역 허브 칸과 시도 리포트에
보조로 보여 준다(경기: 3년 합계 88%로 균형인데 1년 차는 73%). 같은 대상을 재는 두 코드라 세 해의 입주 추정 합이 판정의 fut 와
같아야 한다(CLAUDE.md '같은 대상을 재는 코드는 같은 상수·같은 식').

변이(각각 실제로 확인): yearly_supply 가 LEAD_Q 대신 LEAD_Q−1 로 착공을 당겨 오면 합 대조가, CONV 를 빼면 합 대조가, 마지막
묶음의 적정을 4분기로 고정하면(H=11 사례) 부분 묶음 단정이, build_hub 가 전망 칸을 빼면 허브 단정이, build_page 가 블록을
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
    assert ys[-1]['pct'] == int(round(100.0 * f / (SZ.REF_Q['서울'] * 3))), ys[-1]


def test_hub_and_report_show_the_years():
    adv, stats, s, Lq = _ctx()
    h = M.build_hub(s, stats)
    cards = re.findall(r'<a href="/zone/[^"]+/"[^>]*>(.*?)</a>', h, re.S)
    with_out = [c for c in cards if 'class="zo"' in c]
    assert len(with_out) == len(s['zones']), (len(with_out), len(s['zones']))
    gy = SZ.yearly_supply(stats, '경기', Lq, s['H'])
    assert ('적정 대비 입주 ' + ', '.join('%d년 차 %d%%' % (y['n'], y['pct']) for y in gy)) in h
    calc = s
    pq = {}
    others = s['zones']
    page = M.build_page('경기', calc, stats, pq, others)
    assert '<div class="zout">' in page and '3년 너머' in page
