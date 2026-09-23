# -*- coding: utf-8 -*-
"""/monthly/ 인허가 표가 연내 누계를 풀어서 쓰는지, 시도 리포트와 같은 값을 내는지 고정한다.

인허가 계열 단위는 '호 (연내 누계)'다. 2026-09-13 까지 월간 페이지는 이 누계를 월별 값처럼
다뤘다 — '이 달'에 1~7월 누계를, '최근 12개월 합'에 누계 12개의 단순 합을 냈다. 경기
12개월 합이 544,783(실제 143,685), 전국은 실제의 약 3.8배였다. 같은 인허가를 시도 리포트는
sido_zones.permit_trail12 로 올바르게 내고 있어, 한 사이트 안에서 두 값이 나왔다.

CLAUDE.md 데이터 원칙: 같은 대상을 재는 코드가 둘 이상이면 같은 상수·함수를 쓰고 그 일치를
시험으로 고정한다. 이 파일이 그 고정이다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sido_zones as SZ  # noqa: E402
import make_monthly_page as MMP  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _stats():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    return json.loads(re.search(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', s, re.S).group(1))


def _permit_rows():
    """생성된 /monthly/ 인허가 표 → {지역: (이 달, 12개월 합)}. 값이 없으면 None."""
    h = io.open(os.path.join(ROOT, 'monthly', 'index.html'), encoding='utf-8').read()
    m = re.search(r'<section id="permits".*?</section>', h, re.S)
    assert m, '/monthly/ 에서 인허가 섹션을 찾지 못했다'
    out = {}
    # ⚠️ 집계 행은 <tr class="agg"> 로 나온다. <tr> 만 찾으면 전국·수도권·지방을 조용히 건너뛰어
    # 나머지 시험이 그 셋을 검사하지 않고 통과한다(처음 짰을 때 실제로 그랬다).
    for tr in re.findall(r'<tr[^>]*><th scope="row">(.*?)</th>(.*?)</tr>', m.group(0), re.S):
        tds = re.findall(r'<td>(.*?)</td>', tr[1])
        conv = [None if t.strip() in ('·', '') else int(t.replace(',', '')) for t in tds]
        out[tr[0].strip()] = tuple(conv[:2])
    assert out, '인허가 표에 행이 없다'
    for agg in ('전국', '수도권', '지방'):
        assert agg in out, '집계 행 %s 를 못 읽었다 — 파서가 마크업을 놓치고 있다' % agg
    return out


def test_unit_is_still_cumulative():
    """전제 확인 — 단위가 누계가 아니게 바뀌면 아래 기대값 산식도 바뀌어야 한다."""
    assert '누계' in (_stats()['인허가'].get('unit') or ''), '인허가 단위가 누계가 아니다 — 이 시험의 전제를 다시 볼 것'


def test_trailing_12_matches_the_zone_report_everywhere():
    st = _stats()
    label = st['인허가']['dates'][-1]
    rows = _permit_rows()
    bad = []
    for r, (_, yr) in rows.items():
        want, ym = SZ.permit_trail12(st, r)
        want = want if ym == label else None
        if yr != (None if want is None else int(round(want))):
            bad.append('%s 화면 %s vs permit_trail12 %s' % (r, yr, want))
    assert not bad, '12개월 합이 시도 리포트와 다르다: %s' % '; '.join(bad)


def test_this_month_is_the_cumulative_difference():
    st = _stats()
    d = st['인허가']
    dates = d['dates']
    i = len(dates) - 1
    y, m = (int(x) for x in re.match(r'^(\d{4})[.\-](\d{1,2})', dates[i]).groups())
    rows = _permit_rows()
    bad = []
    for r, (cur, _) in rows.items():
        v = d['series'].get(r) or []
        c = v[i] if i < len(v) else None
        if c is None:
            want = None
        elif m == 1:
            want = c
        else:
            p = v[i - 1] if i >= 1 else None
            want = (c - p) if p is not None else None
            if want is not None and want < 0:
                want = None   # 소급 정정분은 '이 달' 값으로 싣지 않는다(리뷰 13번)
        if cur != (None if want is None else int(round(want))):
            bad.append('%s 화면 %s vs 누계차분 %s' % (r, cur, want))
    assert not bad, "'이 달'이 누계 차분과 다르다: %s" % '; '.join(bad)


def test_this_month_is_not_the_raw_cumulative():
    """1월이 아니면 '이 달'이 그 달 누계와 같을 수 없다(전월 누계가 0이 아닌 한).

    위 시험은 산식이 같이 틀어지면 함께 통과할 수 있다. 이건 증상 자체를 잡는다.
    """
    st = _stats()
    d = st['인허가']
    i = len(d['dates']) - 1
    if re.match(r'^\d{4}[.\-]0?1$', d['dates'][i]):
        return
    rows = _permit_rows()
    raw = d['series']['전국'][i]
    prev = d['series']['전국'][i - 1]
    if raw is None or not prev:
        return
    assert rows['전국'][0] != int(round(raw)), "전국 '이 달'이 연내 누계 원값 그대로다"


def test_generator_does_not_sum_raw_cumulative():
    src = io.open(os.path.join(ROOT, 'tools', 'make_monthly_page.py'), encoding='utf-8').read()
    assert 'permit_trail12' in src, '12개월 합이 permit_trail12 를 쓰지 않는다 — 산식을 새로 쓰지 말 것'
    assert 'sum_last' not in src, '원값 12개 합산 함수가 되살아났다'


def test_negative_difference_is_blank_not_a_negative_permit():
    """누계가 소급 정정으로 줄어든 달은 '이 달'을 비운다 — 음수 인허가를 싣지 않는다.

    깨뜨리면 빨개지는 것: make_monthly_page.cum_month 의 음수 거르기를 지우면 −491 이 그대로 나온다(변이로 확인).
    픽스처: 실데이터에 있던 모양 — 서울 2011.07 누계 20,000 → 2011.08 19,509(−491), 경기는 정상 증가.
    """
    regions = list(MMP.ORDER)
    series = {r: [None, None] for r in regions}
    series['서울'] = [20000, 19509]
    series['경기'] = [10000, 10600]
    d = {'dates': ['2011.07', '2011.08'], 'series': series}
    got = MMP.cum_month(d, 1)
    assert got['서울'] is None, '소급 정정으로 줄어든 누계가 음수 인허가(%s)로 나간다' % got['서울']
    assert got['경기'] == 600, '정상 증가분까지 비웠다: %s' % got['경기']


def test_this_month_equals_permit_monthly_everywhere():
    """/monthly/ '이 달'(cum_month)이 sido_zones.permit_monthly 와 전 지역·전 기간에서 같다(음수만 비운다).

    같은 인허가 월 값을 사이트의 두 곳이 잰다 — permit_monthly 는 착공 전환율·3년 너머 신호·사이클
    고리3에, cum_month 는 /monthly/ 표와 '이 달 많은 곳' 요약에 쓰인다. 2026-09-23 전체 점검까지
    cum_month 는 연초 null(KOSIS 의 진짜 0)을 '전월 없음'으로 보고 다음 달을 비웠다.
    깨뜨리면 빨개지는 것: cum_month 를 옛 사본(전월 원값이 None 이면 그 달을 None 으로)으로 되돌리면
    실데이터 123칸(대구 2024.02 1,205 등 63칸 + 세종 출범 전 2007~2011년 60칸)에서 빨개진다(변이로 확인).
    픽스처: 저장소의 실제 data.js 인허가 계열 전부.
    """
    st = _stats()
    pm = st['인허가']
    ref = {r: SZ.permit_monthly(st, r) for r in MMP.ORDER}
    bad = []
    for i, d in enumerate(pm['dates']):
        got = MMP.cum_month(pm, i)
        for r in MMP.ORDER:
            want = ref[r].get(str(d)[:7])
            want = None if want is not None and want < 0 else want
            if got.get(r) != want:
                bad.append('%s %s: 표 %s · permit_monthly %s' % (d, r, got.get(r), want))
    assert not bad, '/monthly/ 이 달 값이 permit_monthly 와 %d칸 다르다: %s' % (len(bad), '; '.join(bad[:5]))


def test_month_after_a_null_january_is_not_blanked():
    """1월 누계가 null(진짜 0)이면 2월 '이 달'은 2월 누계 그대로다 — 비우지 않는다.

    깨뜨리면 빨개지는 것: 위와 같은 변이(옛 cum_month)로 대구가 None 이 되어 빨개진다(변이로 확인).
    픽스처: 실데이터 대구 2024.01 null → 2024.02 누계 1,205 를 그대로 옮겼다. 서울은 정상 증가.
    """
    series = {r: [None, None] for r in MMP.ORDER}
    series['대구'] = [None, 1205]
    series['서울'] = [800, 2100]
    d = {'dates': ['2024.01', '2024.02'], 'series': series}
    got = MMP.cum_month(d, 1)
    assert got['대구'] == 1205, '연초 null 뒤의 달을 비웠다: %s' % got['대구']
    assert got['서울'] == 1300
