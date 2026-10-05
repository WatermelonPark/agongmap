# -*- coding: utf-8 -*-
"""지역 허브(/zone/) 부족률 막대와 범례(2026-10-05 대표 요청 — 퍼센트가 클수록 나쁜지, 부족 17%와 여유 19%가 어떻게 다른지가
숫자만으로는 안 보였다). 막대는 한 축(왼쪽 남음 ↔ 오른쪽 모자람)이고 구간 경계·이름은 등급 컷·등급 이름(sido_zones)에서 만든다.

변이(각각 실제로 확인): gauge_bg 의 구간 경계를 손 숫자(예: 40%)로 바꾸면 경계 단정이, _gx 의 끝 붙이기(min/max)를 빼면 막대 밖
단정이, gauge_legend_html 이 GRADE_LABS 대신 손 이름을 쓰거나 cut_mult 대신 퍼센트를 쓰면 범례 단정이, build_hub 가 막대를 빼면 허브 단정이 빨개진다.
픽스처: 실제 칸의 비율 모양(서울 1.389·경기 0.17·인천 −0.19·충남 −0.74·제주 1.79)과 축 밖 값(−1.5·2.6), 저장소 판정(허브).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _left(r):
    return float(re.search(r'left:([\d.]+)%', M.gauge_html({'ratio': r})).group(1))


def test_marker_moves_right_as_the_shortfall_grows_and_stays_inside():
    xs = [_left(r) for r in (-1.5, -0.74, -0.19, 0.0, 0.17, 1.389, 1.79, 2.6)]
    assert xs == sorted(xs) and xs[0] == 0.0 and xs[-1] == 100.0, xs
    assert _left(-0.19) < _left(0.0) < _left(0.17), '여유(−)와 부족(+)이 0 을 사이에 두고 갈리지 않는다'


def test_band_edges_and_legend_come_from_the_grade_cuts():
    bg = M.gauge_bg()
    edges = sorted(set(float(x) for x in re.findall(r'([\d.]+)%', bg)))
    want = sorted({0.0, 100.0} | {round(M._gx(c), 2) for c in SZ.GRADE_CUTS})
    assert edges == want, (edges, want)
    legend = M.gauge_legend_html()
    for k in SZ.GRADE_KEYS:
        assert SZ.GRADE_LABS[k] in legend and M.GRADE_COLOR[k] in legend, k
    for c in SZ.GRADE_CUTS[:3]:
        assert SZ.cut_mult(c) in legend, c          # 단위는 판정 문구와 같은 '1년 적정물량의 N배'(2026-10-05 안 A′)
    assert '%' not in legend


def test_hub_cards_carry_the_gauge_and_the_multiple():
    adv, _ = M.load()
    SZ.refresh_texts(adv['sido'])
    h = M.build_hub(adv['sido'])
    cards = re.findall(r'<a href="/zone/[^"]+/"[^>]*>(.*?)</a>', h, re.S)
    zones = [z for z in adv['sido']['zones']]
    with_gauge = [c for c in cards if 'class="zg"' in c]
    assert len(with_gauge) == len(zones), (len(with_gauge), len(zones))
    assert '<p class="zg-note">' in h and '<p class="zg-legend">' in h
    for z in zones:
        t = SZ.ratio_text(z['ratio'], adv['sido']['H']) if z['agg'] else SZ.card_text(z['dtot'], z['ratio'], adv['sido']['H'])
        frag = t.split('(')[-1].rstrip(')') if '(' in t else t
        assert frag in h, (z['z'], frag)
