# -*- coding: utf-8 -*-
"""등급 재현 구간표(`tools/grade_bands.py`)가 표본 전체를 덮는지(백로그 54).

예전 첫 구간 하한이 -9(-900%)라, 세종 초기처럼 순부족비가 그보다 아래인 표본 16개가 어느 구간에도 안 들어갔다.
그래서 표본 512개의 구간별 n 합이 496이었고, 문서의 '0 미만 n=211·실질 +0.25%'를 재현하지 못했다(n=195·−2.65%).
지금은 첫 구간과 마지막 구간이 열려 있어 어떤 값도 밖으로 새지 않는다.
"""
import io
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import grade_bands as GB  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))


def test_bands_cover_every_ratio_including_extremes():
    """-900% 아래, 그리고 아주 큰 값도 구간에 든다.

    변이(실제로 확인): BANDS 첫 하한을 -9로 되돌리면 -50.0 에서 ValueError 가 나 이 시험이 빨개진다.
    """
    for r in (-1e6, -900.5, -50.0, -9.0001, -0.0001, 0.0, 0.2499, 0.25, 0.4999, 1.0, 1e6):
        assert GB.band(r) in {name for name, _, _ in GB.BANDS}, r


def test_band_counts_add_up_to_the_sample_count():
    """구간 이름으로 센 n 합이 표본 수와 같다 — 빠지는 표본이 없다.

    변이(실제로 확인): 마지막 구간 상한을 99로 되돌리면 150.0 이 ValueError 로 새 이 시험이 빨개진다.
    """
    ratios = [-50.0, -3.0, -0.1, 0.0, 0.1, 0.3, 0.7, 2.0, 150.0]
    counts = {name: 0 for name, _, _ in GB.BANDS}
    for r in ratios:
        counts[GB.band(r)] += 1
    assert sum(counts.values()) == len(ratios)
    assert counts['<0'] == 3 and counts['≥1.0'] == 2, counts


def test_first_band_is_open_below_and_last_open_above():
    """열린 첫·마지막 구간이 이 고침의 핵심이다(구간표가 전체 실수를 덮는다)."""
    assert GB.BANDS[0][1] == float('-inf') and GB.BANDS[-1][2] == float('inf')


def test_reproduction_script_uses_the_module_and_checks_completeness():
    """재현 스크립트가 구간표 정본을 쓰고, 표본 누락을 스스로 멈춘다 — 사본을 다시 만들면 같은 사고가 반복된다."""
    src = io.open(os.path.join(HERE, '..', 'study_grade_bands.py'), encoding='utf-8').read()
    assert 'BANDS = GB.BANDS' in src, '재현 스크립트가 구간표 정본을 쓰지 않는다'
    assert '등급 구간표가 표본' in src, '표본 누락을 스크립트가 스스로 확인하지 않는다'
