# -*- coding: utf-8 -*-
"""/cycle/의 차트가 모델의 지역을 다 담는가.

2026-09-12 실사고: `refresh_cycle_data.SIDO17`이 옛 손 목록(광주·전남)을 들고
있었고, 전세가율 차트를 만드는 `build_jratio`가 **모르는 지역을 조용히 건너뛰는**
구조였다. 통합 뒤 '전남광주'가 목록에 없으니 그대로 빠진 채 배포됐다 — 차트에
지역 하나가 통째로 없는데 아무도 빨개지지 않았다.

고리 검증(sync·link3_regional 등)도 같은 날 `tools/rebuild_cycle_analysis.py`로
다시 계산했다. 전에는 1회성 분석의 결과를 페이지에 적어두어 모델이 바뀌어도
따라오지 못했으므로, 이제는 옛 지역명이 남아 있으면 시험이 잡는다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import sido_zones as SZ  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
PAGE = os.path.join(ROOT, 'cycle', 'index.html')

# 지역 이름을 담고 있는 키. 값이 바뀌어도 이름만은 모델을 벗어나면 안 된다.
# 페이지에 싣지 않고 tools/data/cycle_analysis.json에만 남긴 것(supply_ratio)도
# 같이 본다. 화면에 안 나온다고 옛 이름을 품고 있어도 되는 것은 아니다.
REGION_KEYS = ('jratio_level', 'sync', 'link3_regional', 'link6_regional',
               'supply_ratio', 'cycle_strength')
ANALYSIS = os.path.join(ROOT, 'tools', 'data', 'cycle_analysis.json')


def _D():
    s = io.open(PAGE, encoding='utf-8').read()
    return json.loads(re.search(r'const D=(\{.*?\});', s, re.S).group(1)), s


def _model():
    return {z for z in SZ.ORDER if z not in SZ.AGG}


def test_regenerated_chart_covers_every_model_region():
    D, _ = _D()
    got = {r['region'] for r in D['jratio_level']}
    missing = _model() - got
    assert not missing, '전세가율 차트에 빠진 지역: %s' % ', '.join(sorted(missing))


def test_no_chart_names_a_region_outside_the_model():
    """모델에 없는 지역이 남아 있으면 통합 전 값이 그대로 배포된 것이다."""
    D, _ = _D()
    if os.path.exists(ANALYSIS):
        D = dict(json.load(io.open(ANALYSIS, encoding='utf-8')), **D)
    want = _model()
    for k in REGION_KEYS:
        if k not in D:
            continue
        stray = {r['region'] for r in D[k]} - want
        assert not stray, '%s에 모델 밖 지역: %s' % (k, ', '.join(sorted(stray)))


def test_generator_does_not_hardcode_regions():
    """손 목록이 다시 들어오면 같은 사고가 반복된다."""
    for name in ('refresh_cycle_data.py', 'rebuild_cycle_analysis.py'):
        src = io.open(os.path.join(ROOT, 'tools', name), encoding='utf-8').read()
        assert 'SZ.ORDER' in src, '%s의 지역 목록이 모델에서 오지 않는다' % name
        hard = re.findall(r"SIDO\w*\s*=\s*\[\s*'", src)
        assert not hard, '%s에 지역을 손으로 나열한 자리가 있다' % name


def test_headline_counts_match_the_model():
    """머리글이 말하는 지역 수는 실제로 분석한 수(sync 표본)여야 한다.

    2026-09-15 콘텐츠 세션이 머리글을 '16개 시도 · 지역 4곳'(모델 수)에서 '분석 14개
    시도'로 바꾸며 본문 칸(n_panel)을 썼다. 이 시험이 옛 문구 모양을 그대로 찾아
    원격 main이 빨개졌고, 그대로 두면 배치의 커밋 게이트가 데이터 갱신을 막았다.
    문구가 아니라 숫자의 출처를 본다 — 모델 지역 수와의 일치는 차트 시험이 맡는다."""
    D, s = _D()
    panel = len(D['sync'])
    assert (D.get('prose') or {}).get('n_panel') == str(panel), 'n_panel이 sync 표본 수와 다르다'
    assert '<span data-d="n_panel">%d</span>개 시도' % panel in s, '머리글·본문이 분석 지역 수를 칸으로 말하지 않는다'
    assert '%d개 시도 20년' % panel in s, '메타 설명의 지역 수가 분석 표본과 다르다'
    assert '합치기 전' not in s, '통합 이전 표본이라는 낡은 단서가 남아 있다'
