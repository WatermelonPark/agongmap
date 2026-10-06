# -*- coding: utf-8 -*-
"""지역 칸의 해마다 입주 신호등(2026-10-05 대표 요청 — '부족·균형 태그보다 동그라미 신호등 3개로 3년을 한눈에').

판정 태그(.sc-tier)를 칸에서 빼고(대표 결정: 태그 완전히 빼기 — 판정은 지도 색·리포트 본문에 남는다), 동그라미 하나가 한 해다.
색은 그해 입주 추정 ÷ 적정을 **입주물량 문턱 정본**(sido_zones.occ_level — OCC_LO_PCT·OCC_HI_PCT, 홈 입주물량 표·/moveins/ 와
같은 70%·130%)으로 가른다(대표 결정 — 70%·130% 안). 리포트 아래 해마다 막대도 같은 세 색이다(같은 대상을 재는 두 그림이
다른 색을 칠하면 73% 가 신호등은 노랑·막대는 빨강이 된다 — 2026-10-05 375px 실측에서 실제로 그랬다).

변이(각각 실제로 확인): light_of 가 occ_level 대신 `pct < 100` 으로 가르면 문턱 단정이, lights_legend_html 이 70 을 손으로
적고 OCC_LO_PCT 를 60 으로 바꾸면 범례 단정이, build_hub 가 칸에 sc-tier 를 되살리면 태그 단정이, outlook_cells 가 옛
'zo-lo/zo-hi'(100% 경계)로 돌아가면 막대 색 단정이 빨개진다.
픽스처: 경계 값(69·70·130·131)과 저장소 data.js 의 실제 판정·착공(색은 함수로 유도 — 데이터가 앞으로 가도 같은 판정).
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
    SZ.refresh_texts(s)
    return stats, s, SZ.qidx(int(s['L'][:4]), int(s['L'][-1]))


def test_colors_follow_the_move_in_thresholds():
    lo, hi = SZ.OCC_LO_PCT, SZ.OCC_HI_PCT
    assert [M.light_of(p)[0] for p in (lo - 1, lo, hi, hi + 1)] == ['lo', 'ok', 'ok', 'hi']
    leg = M.lights_legend_html(3)
    assert '%d%% 미만' % lo in leg and '%d~%d%%' % (lo, hi) in leg and '%d%% 초과' % hi in leg, leg
    assert '동그라미: ' + SZ.LIGHT_CAP % '1·2·3' in leg
    assert [lab for _, lab in (SZ.LIGHT[-1], SZ.LIGHT[0], SZ.LIGHT[1])] == ['적음', '보통', '많음'], '판정 낱말과 겹치지 않는 이름'


def test_hub_cards_show_lights_instead_of_grade_tags():
    stats, s, Lq = _ctx()
    h = M.build_hub(s, stats)
    cards = dict(re.findall(r'<a href="/zone/([^"]+)/"[^>]*>(.*?)</a>', h, re.S))
    import urllib.parse
    for z in s['zones']:
        c = cards[urllib.parse.quote(z['z'])]
        assert 'sc-tier' not in c, '칸에 판정 태그가 남았다: ' + z['z']
        ys = SZ.yearly_supply(stats, z['z'], Lq, s['H'])
        got = re.findall(r'<span class="zl-d (\w+)">(\d)</span>', c)
        assert got == [(M.light_of(y['pct'])[0], str(y['n'])) for y in ys], (z['z'], got)
    assert '<p class="zl-legend">' in h and 'class="z-hint"' in h
    # 2026-10-06 대표 요청: 칸이 먼저, 읽는 법(범례·막대 설명)은 목록 아래
    assert h.index('id="sido-list"') < h.index('class="zread"') and h.index('<p class="zl-legend">') > h.index('id="sido-list"')


def test_report_bars_share_the_light_colors_and_say_the_state():
    """시도 리포트는 머리에 큰 신호등을 두지 않고(2026-10-06 — 바로 아래 막대와 같은 값을 두 번 보였다) 해마다 막대 한 그림에
    동그라미와 같은 색 키·이름(적음·보통·많음)을 단다. '… 너머' 참고 칸은 회색(na)이다 — 바로 위 줄의 '필요량에 못 미칩니다'
    (PWARN_CUT 95%)와 신호등 문턱(70%)이 달라 82% 가 노랑으로 칠해졌다. 다른 지역 칸은 허브와 같은 동그라미다.

    변이(각각 실제로 확인): build_page 가 머리 신호등(zlights)을 되살리면, outlook_cells 가 참고 칸을 light_of 로 칠하면, 막대 아래
    상태 글자를 빼면 빨개진다. 픽스처: 저장소 data.js 의 경기 판정·착공(3년 너머 126% 인 실제 모양).
    """
    stats, s, Lq = _ctx()
    page = M.build_page('경기', s, stats, {}, s['zones'])
    ys = SZ.yearly_supply(stats, '경기', Lq, s['H'])
    assert 'class="zlights"' not in page, '리포트 머리에 큰 신호등이 되살아났다'
    keys = [M.light_of(y['pct'])[0] for y in ys]
    blk = re.search(r'<div class="zout">(.*?)</div></div>', page, re.S).group(1)
    bars = re.findall(r'<span class="zo-b (\w+)"', blk)
    assert bars == keys + ['na'], (bars, keys)
    labs = re.findall(r'<small>([^<]+)</small>', blk)
    assert labs[:len(ys)] == ['%d년 차 · %s' % (y['n'], M.light_of(y['pct'])[1]) for y in ys], labs
    others = re.search(r'<h2>다른 지역</h2><div class="zlinks">(.*?)</div>', page, re.S).group(1)
    assert 'sc-tier' not in others and others.count('class="zl"') == len(s['zones']) - 1


def test_home_payload_carries_the_same_lights():
    """홈 판정 카드(home-app.js aggLights)는 split_data 가 data-core.js 에 구워 실은 yl·ya·ylg 만 읽는다 — 허브·리포트와
    같은 sido_zones 함수 값이어야 하고, 홈 스크립트에 문턱(70·130)을 다시 적지 않는다.

    변이(각각 실제로 확인): split_data.main 에서 bake_lights 호출을 빼면 yl 단정이, aggLightKey 가 ylg 대신 '70% 미만'을
    손으로 적으면 문턱 단정이 빨개진다. 픽스처: 배치·CI 가 시험 앞에 split_data 로 굽는 저장소 data-core.js.
    """
    import io
    import json
    import home_src as HS
    stats, s, Lq = _ctx()
    src = io.open(os.path.join(os.path.dirname(M.__file__), '..', 'data-core.js'), encoding='utf-8').read()
    core = json.loads(re.search(r'const ADV=(\{.*?\});\n', src, re.S).group(1))['sido']
    assert core['ylg'] == [list(x) for x in SZ.light_legend()]
    for z in core['zones']:
        want = SZ.year_lights(stats, z['z'], Lq, s['H'])
        assert z.get('yl') == want, (z['z'], z.get('yl'), want)
        assert z.get('ya') == SZ.lights_aria([{'n': y['n'], 'pct': y['p']} for y in want])
    js = dict(HS.home_files())['home-app.js']
    for fn in ('aggLights', 'aggLightKey'):
        body = re.search(r'^function %s\(.*?^}' % fn, js, re.S | re.M).group(0)
        assert not re.search(r'\b(%d|%d)\b' % (SZ.OCC_LO_PCT, SZ.OCC_HI_PCT), body), '홈 스크립트가 문턱을 손으로 적었다: ' + fn
