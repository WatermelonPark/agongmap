# -*- coding: utf-8 -*-
"""/cycle/이 싣고 다니는 값이 실제로 쓰이는가, 본문과 어긋나지 않는가.

2026-09-12: `const D`의 키 22개 중 12개를 페이지 어디서도 읽지 않았다. 한때
차트가 있었다가 사라진 자리, 분석만 하고 싣기만 한 값, 배치가 매일 갱신하는데
아무도 보지 않는 평균이 뒤섞여 있었다. 눈에 띄지 않은 이유는 간단하다. 쓰이지
않는 데이터는 틀려도 화면이 멀쩡하기 때문이다. 실제로 그중 하나는 광주·전남
통합 뒤에도 옛 지역명을 안고 있었다.

그래서 두 가지를 지킨다.

1. D에 들어간 키는 페이지 코드가 읽어야 한다. 안 읽을 값이면 싣지 말고
   `tools/data/cycle_analysis.json`에 남긴다.
2. 본문에 글자로 박은 수치는 그 분석 결과와 같아야 한다. 재산정한 뒤 본문을
   고치지 않으면 여기서 걸린다.
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
PAGE = os.path.join(ROOT, 'cycle', 'index.html')
ANALYSIS = os.path.join(ROOT, 'tools', 'data', 'cycle_analysis.json')


def _page():
    s = io.open(PAGE, encoding='utf-8').read()
    m = re.search(r'const D=(\{.*?\});\n', s, re.S)
    assert m, 'cycle 페이지에서 const D를 찾지 못했다'
    return json.loads(m.group(1)), s[:m.start()] + s[m.end():], s


def _analysis():
    if not os.path.exists(ANALYSIS):
        pytest.skip('분석 결과 파일이 없다(rebuild_cycle_analysis.py --write로 만든다)')
    return json.load(io.open(ANALYSIS, encoding='utf-8'))


def test_every_payload_key_is_read_by_the_page():
    D, code, _ = _page()
    dead = [k for k in D
            if not re.search(r'D\.%s\b|D\[.%s.\]' % (re.escape(k), re.escape(k)), code)]
    assert not dead, ('페이지가 읽지 않는 키를 싣고 있다: %s — 차트가 쓰지 않을 값이면 '
                      'tools/data/cycle_analysis.json에 남긴다' % ', '.join(sorted(dead)))


def test_archived_analysis_is_not_also_shipped():
    """같은 숫자를 두 곳에 두면 한쪽만 고쳐질 때 둘이 어긋난다."""
    D, _, _ = _page()
    A = _analysis()
    both = sorted(set(D) & set(A) - {'_extra'})
    shipped = {'sync', 'link1_new', 'link3_regional', 'link6_regional', 'cycle_strength', 'prose'}
    stray = [k for k in both if k not in shipped]
    assert not stray, '보관용 값이 페이지에도 실려 있다: %s' % ', '.join(stray)


def test_prose_spans_carry_exactly_the_payload_values():
    """본문 수치는 D.prose에서 온다(2026-09-15). 칸의 글자와 D.prose가 같아야 하고,
    쓰지 않는 prose 값이나 값 없는 칸이 없어야 한다."""
    D, _, s = _page()
    prose = D.get('prose') or {}
    spans = re.findall(r'<span data-d="([a-z0-9_]+)">([^<]*)</span>', s)
    assert spans, '본문 칸이 하나도 없다'
    wrong = [(k, v, prose.get(k)) for k, v in spans if prose.get(k) != v]
    assert not wrong, '칸과 D.prose가 다르다: %s' % wrong[:5]
    unused = sorted(set(prose) - {k for k, _ in spans})
    assert not unused, '어느 칸도 쓰지 않는 prose 값: %s' % unused


def test_prose_is_what_the_analysis_computed():
    """보관한 분석 결과와 페이지의 prose가 같은 회차의 것이어야 한다."""
    D, _, _ = _page()
    A = _analysis()
    # 전세가율 풀이 칸(jr_)은 매일 배치가 차트와 함께 채워 보관 분석에 없다 — 비교에서 뺀다.
    # 빼지 않으면 전세가율이 바뀌는 날마다 이 시험이 배치의 커밋 게이트를 막는다.
    mine = {k: v for k, v in (D.get('prose') or {}).items() if not k.startswith('jr_')}
    assert mine == A.get('prose'), '페이지와 보관 분석의 prose가 다르다 — --write를 다시 돌릴 것'


def test_jeonse_ratio_spans_follow_the_chart_on_the_same_page():
    """전세가율 풀이 칸은 같은 페이지의 전세가율 차트(jratio_level)와 같은 값이어야 한다."""
    import refresh_cycle_data as RF
    D, _, _ = _page()
    prose = D.get('prose') or {}
    # 기준월은 D 안에 다른 출처가 없다. 배치가 넣은 값을 그대로 넘겨 나머지 칸을 대조한다.
    # ⚠️ 여기서 data.js 의 최신 달과 맞추지 말 것 — 실데이터 값을 배포 게이트에 단정하지
    #    않는다는 규칙이다. (게이트는 2026-09-16 c23c7dd4 부터 생성기 뒤·커밋 앞에서 돈다.)
    want = RF.jratio_prose(D['jratio_level'], prose.get('jr_prd'))
    got = {k: prose.get(k) for k in RF.JR_KEYS}
    assert got == want, '전세가율 풀이 칸이 차트와 다르다 — refresh_cycle_data를 다시 돌릴 것: %s vs %s' % (got, want)


def test_jratio_mid_band_is_only_a_decade_when_both_share_it():
    import refresh_cycle_data as RF
    base = [{'region': '서울', 'val': 52.4}, {'region': '전남광주', 'val': 78.6}]
    assert RF.jratio_prose(base + [{'region': '대구', 'val': 70.8}, {'region': '대전', 'val': 71.8}], '2026.07')['jr_mid'] == '70%대'
    assert RF.jratio_prose(base + [{'region': '대구', 'val': 69.4}, {'region': '대전', 'val': 71.8}], '2026.07')['jr_mid'] == '69~72%'


def test_jratio_caption_month_comes_with_the_values():
    """차트 캡션의 기준월은 값을 읽은 그 달이어야 한다(백로그 17).

    캡션에 손으로 적은 '2026.06 기준'이 값이 07로 넘어간 뒤에도 남아 있었다.
    """
    import pytest
    import refresh_cycle_data as RF
    lvl = [{'region': r, 'val': 60.0} for r in ('서울', '전남광주', '대구', '대전')]
    assert RF.jratio_prose(lvl, '2026.07')['jr_prd'] == '2026.07'
    for bad in (None, '', '2026-07-01', '2026Q2'):
        with pytest.raises(RuntimeError):
            RF.jratio_prose(lvl, bad)
    _, _, s = _page()
    assert re.search(r'<span data-d="jr_prd">\d{4}\.\d{2}</span> 기준', s), '캡션 기준월이 칸이 아니다'
    assert not re.search(r'<b>\d{4}\.\d{2} 기준</b>', s), '캡션에 손으로 적은 기준월이 남았다'


def test_page_script_fills_from_the_payload():
    _, code, _ = _page()
    assert "querySelectorAll('[data-d]')" in code and 'D.prose' in code


def test_old_hand_written_figures_are_gone():
    """계산되지 않던 수(4분기 43%)와 옛 요약 수치가 돌아오지 않는다."""
    _, _, s = _page()
    for old in ('4분기 43%', '0.6% vs 적은 분기 1.4%', '최근 3년 반으로'):
        assert old not in s, old
