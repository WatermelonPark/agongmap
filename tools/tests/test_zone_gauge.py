# -*- coding: utf-8 -*-
"""지역 허브(/zone/) 부족률 막대와 범례(2026-10-05 대표 요청 — 퍼센트가 클수록 나쁜지, 부족 17%와 여유 19%가 어떻게 다른지가
숫자만으로는 안 보였다). 막대는 한 축(왼쪽 남음 ↔ 오른쪽 모자람)이고 구간 경계·이름은 등급 컷·등급 이름(sido_zones)에서 만든다.

변이(각각 실제로 확인): gauge_bg 의 구간 경계를 손 숫자(예: 40%)로 바꾸면 경계 단정이, _gx 의 끝 붙이기(min/max)를 빼면 막대 밖
단정이, gauge_legend_html 이 GRADE_LABS 대신 손 이름을 쓰거나 cut_mult 대신 퍼센트를 쓰면 범례 단정이, build_hub 가 막대를 빼면 허브 단정이 빨개진다.
픽스처: 실제 칸의 비율 모양(서울 1.389·경기 0.17·인천 −0.19·충남 −0.74·제주 1.79)과 축 밖 값(−1.5·2.6), 저장소 판정(허브).
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _left(r):
    return float(re.search(r'left:([\d.]+)%', M.gauge_html({'ratio': r})).group(1))


def test_marker_moves_left_as_the_shortfall_grows_and_stays_inside():
    """왼쪽이 부족, 오른쪽이 여유다(2026-10-06 대표 결정 — '부족할수록 오른쪽'은 같은 칸 신호등(적음 → 많음)과 방향이 반대라
    헷갈렸다). 막대·범례·홈 지도 범례가 같은 방향이다.
    변이(각각 실제로 확인): _gx 를 옛 방향(부족 = 오른쪽)으로 되돌리면 위치 단정이, gauge_legend_html 이 옛 순서(공급 여유부터)로
    돌아가면 범례 순서 단정이, 홈 mapKeyHtml 공급 범례를 '공급 여유 … 공급 부족'으로 되돌리면 홈 단정이 빨개진다."""
    xs = [_left(r) for r in (-1.5, -0.74, -0.19, 0.0, 0.17, 1.389, 1.79, 2.6)]
    assert xs == sorted(xs, reverse=True) and xs[0] == 100.0 and xs[-1] == 0.0, xs
    assert _left(-0.19) > _left(0.0) > _left(0.17), '여유(−)와 부족(+)이 0 을 사이에 두고 갈리지 않는다'
    legend = re.sub(r'<[^>]+>', ' ', M.gauge_legend_html())
    names = [SZ.GRADE_LABS[k] for k in SZ.GRADE_KEYS]           # g4(심각한 부족) … g0(공급 여유)
    assert legend.index(names[0]) < legend.index(names[-1]), legend
    import home_src as HS
    key = re.search(r"if\(!M\) return (.*?);", dict(HS.home_files())['home-app.js'], re.S).group(1)
    assert key.index('공급 부족') < key.index('공급 여유'), '홈 지도 공급 범례가 막대와 반대 방향이다'


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
    # 전국·수도권·지방 칸도 시도 칸과 같은 정본 ctxt(세대수 + 괄호 배수)다(2026-10-30 디자인 리뷰 3차 — 같은 허브 안 칸 양식 통일).
    for z in zones:
        t = SZ.card_text(z['dtot'], z['ratio'], adv['sido']['H'])
        frag = t.split('(')[-1].rstrip(')') if '(' in t else t
        assert frag in h, (z['z'], frag)
        assert ('<i>%s' % t.split('(')[0]) in h, (z['z'], t)


def test_home_table_legend_is_one_price_ramp():
    """홈 표 보기 범례는 한 줄이고, 색 띠는 가격만(왼쪽 하락 → 오른쪽 상승) 말한 뒤 '미래 칸은 붉을수록 공급 부족'을 글로 붙인다
    (2026-10-18 대표 결정 D4, 전수리뷰 2차 H1-6). 예전 범례 '하락 · 공급 과잉 [띠] 상승 · 공급 부족'은 한 띠가 가격과 공급을 함께
    말해 공급 방향이 지도 범례(왼쪽 부족 → 오른쪽 여유)와 반대였고, 판정 이름 '공급 여유'와 다른 '과잉'을 썼다.
    변이(실제로 확인): index.html .tb-key 를 옛 '하락 · 공급 과잉 … 상승 · 공급 부족'으로 되돌리면 빨개진다.
    픽스처: 저장소 index.html(손으로 쓰는 홈 마크업)."""
    html = io.open(os.path.join(M.ROOT, 'index.html'), encoding='utf-8').read()
    m = re.search(r'<div class="tb-key">(.*?)</div>', html, re.S)
    assert m, '홈 표 보기 범례(.tb-key)를 못 찾았다'
    key = re.sub(r'<[^>]+>', '|', m.group(1))
    words = [w.strip() for w in key.split('|') if w.strip()]
    assert words[:3] == ['하락', '상승', '미래 칸은 붉을수록 공급 부족'], words
    assert '과잉' not in m.group(1) and '여유' not in m.group(1), words
    assert m.group(1).index('tk-d') < m.group(1).index('tk-ramp') < m.group(1).index('tk-u')
