# -*- coding: utf-8 -*-
"""/monthly/ 섹션 요약('변화가 큰 3곳')과 진입점을 고정한다(점검후속 개발 ④).

2026-09-15 고객 점검: 매달 정부 통계를 대조하는 사람에게 가장 맞는 화면인데 통계 탭·시도 허브·
주간 페이지 어디서도 가는 길이 없었고, 표 다섯 개를 다 읽어야 이번 달에 무엇이 움직였는지 보였다.

요약은 생성기가 값에서 뽑는다. 이 시험은 생성기 코드를 믿지 않고 **화면에 나간 표**에서 다시
계산해 대조한다 — 요약과 표가 서로 다른 달·다른 값을 말하면 화면이 스스로 모순된다.
표시 반올림 때문에 동률 순서는 갈릴 수 있어, 이름 순서가 아니라 '실린 값이 표와 같은가'와
'실리지 않은 시도 중 더 크게 움직인 곳이 없는가'를 본다.
"""
import io
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _read(*p):
    if HS.is_home(*p):
        return HS.home_source()
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def _val(t):
    t = t.strip()
    if t in ('·', ''):
        return None
    return float(t.replace(',', '').replace('+', ''))


def _section(h, sid):
    m = re.search(r'<section id="%s".*?</section>' % sid, h, re.S)
    assert m, '/monthly/ 에 %s 섹션이 없다' % sid
    return m.group(0)


def _rows(sec):
    out = {}
    for name, rest in re.findall(r'<tr[^>]*><th scope="row">(.*?)</th>(.*?)</tr>', sec, re.S):
        out[name.strip()] = [_val(re.sub(r'<[^>]+>', '', c)) for c in re.findall(r'<td[^>]*>(.*?)</td>', rest, re.S)]
    return out


def _top(sec):
    """요약 줄의 (링크, 이름, 값) 목록. 줄이 없으면 None, 비교 달이 없어 사유만 적힌 줄이면 []."""
    m = re.search(r'<p class="top3"><b>[^<]*</b>(.*?)</p>', sec, re.S)
    if not m:
        return None
    items = re.findall(r'<a href="/zone/([^/"]+)/">([^<]+)</a> ([^<·]+?)(?= · |$)', m.group(1).strip())
    return [(urllib.parse.unquote(href), name, _val(re.sub(r'[^\d.+\-,]', '', v))) for href, name, v in items]


# 섹션 → (표에서 '변화량'을 꺼내는 방법, 양수만 보는가)
PICK = {
    'price': (lambda c: c[0], False),            # 매매 변동률
    'permits': (lambda c: c[0], True),           # 이 달 인허가(물량)
    'moveins': (lambda c: None if None in c[:2] else c[1] - c[0], False),  # 예정 − 실적
    'unsold': (lambda c: c[1], False),           # 전월 대비
    'jeonse': (lambda c: c[1], False),           # 1년 전 대비
}


def test_every_section_has_a_summary_line_above_its_table():
    h = _read('monthly', 'index.html')
    for sid in PICK:
        sec = _section(h, sid)
        assert '<p class="top3">' in sec, '%s 섹션에 요약 줄이 없다' % sid
        assert sec.index('<p class="top3">') < sec.index('<table'), '%s 요약이 표 아래에 있다' % sid


def _assert_summary_matches_table(sid, sec):
    pick, positive = PICK[sid]
    rows = _rows(sec)
    top = _top(sec)
    assert top is not None, '%s 요약을 읽지 못했다' % sid
    assert len(top) <= 3
    change = {}
    for r, cells in rows.items():
        if r in SZ.AGG:
            continue
        v = pick(cells)
        if v is None or v == 0 or (positive and v < 0):
            continue
        change[r] = v
    if not top:
        # 사유만 적힌 줄(비교 달이 없는 회차 — 감사 #17)은 표의 증감 칸도 전부 비어 있을 때만 맞다.
        assert not change, '%s: 요약은 비교할 달이 없다는데 표에는 증감이 있다 %s' % (sid, sorted(change))
        return
    for href, name, v in top:
        assert href == name, '%s: 링크(%s)와 이름(%s)이 다르다' % (sid, href, name)
        assert name not in SZ.AGG, '%s: 집계 %s 가 요약에 끼었다' % (sid, name)
        assert name in change, '%s: 요약의 %s 가 표에서 변화가 없거나 없는 행이다' % (sid, name)
        assert abs(change[name] - v) < 0.006, '%s: %s 요약 %s ≠ 표 %s' % (sid, name, v, change[name])
    listed = {n for _, n, _ in top}
    floor = min(abs(v) for _, _, v in top)
    bigger = sorted(r for r, v in change.items() if r not in listed and abs(v) > floor + 0.006)
    assert not bigger, '%s: 요약에 없는데 더 크게 움직인 시도 %s' % (sid, bigger)
    if len(top) < 3:
        assert len(change) == len(top), '%s: 3곳을 채울 수 있는데 %d곳만 실었다' % (sid, len(top))


def test_summaries_match_the_tables_they_sit_on():
    h = _read('monthly', 'index.html')
    for sid in PICK:
        _assert_summary_matches_table(sid, _section(h, sid))


def test_moveins_estimate_on_a_half_rounds_like_the_site_and_the_summary_follows_the_table():
    """입주물량 추정치가 x.5 에 걸린 분기 — 표 칸은 사이트 규칙(half-up)으로, 요약 증감은 표의 두 정수 차로.

    추정치는 착공 × 0.958 을 소수 셋째 자리로 싣는다. 착공이 500 으로 나눠 250 이 남는 분기(250·750세대
    단지 하나로도 된다)면 x.5 가 되는데, 예전엔 표가 round()(은행가)로, 요약이 '원값 차의 반올림'으로 따로
    반올림해 '대구 -3,042세대' 위에 표가 3,281 → 240(차 -3,041)을 보였다. 그 분기 내내 요약 대조 시험이
    빨개져 게이트가 데이터 커밋 전체를 막는다(2026-09-26 데이터 감사 #18). 홈(occFmt, Math.round)과 지역
    페이지(make_sido_pages.rnd)는 718.5 를 719 로 보이는데 이 표만 718 이었다.

    변이: top3_lines 의 증감을 원값 차(`nv[i] - lv[i]`)로 되돌리고 _signed 를 `int(round(v))` 로 되돌리면
          대구 요약이 -3,042 가 되어 빨개진다(실제로 바꿔 확인). num() 을 `int(round(v))` 로 되돌리면
          서울 718.5 칸이 718 이 되어 빨개진다(확인).
    픽스처: 감사가 재현한 모양 — 2026Q2 실적 대구 3,281(홀수)·2026Q3 추정 239.5(= 250 × 0.958),
            서울 실적 5,001·추정 718.5(= 750 × 0.958). 다른 지역은 실적과 추정이 같아(변화 0) 요약에 오르지 않는다.
    """
    import make_sido_pages as SP
    regs = list(SZ.ORDER)
    act = {r: 1000.0 for r in regs}
    est = {r: 1000.0 for r in regs}
    act['대구'], est['대구'] = 3281.0, round(250 * SZ.CONV, 3)
    act['서울'], est['서울'] = 5001.0, round(750 * SZ.CONV, 3)
    assert (est['대구'], est['서울']) == (239.5, 718.5), '픽스처 전제(착공 250·750 → x.5)가 깨졌다'
    adv = {'occupancy': {'regions': regs, 'rows': [
        {'p': '2026Q2', 'v': [act[r] for r in regs]},
        {'p': '2026Q3', 'v': [est[r] for r in regs], 'e': 1}]}}
    secs, _ = MP.build(adv, {})
    sec = _section(''.join(secs), 'moveins')
    rows = _rows(sec)
    assert rows['서울'] == [5001.0, float(SP.rnd(718.5))] == [5001.0, 719.0], '표 반올림이 사이트와 다르다: %s' % rows['서울']
    assert rows['대구'] == [3281.0, 240.0], rows['대구']
    _assert_summary_matches_table('moveins', sec)
    assert {n: v for _, n, v in _top(sec)} == {'서울': 719.0 - 5001.0, '대구': 240.0 - 3281.0}


def test_summary_links_point_to_existing_zone_reports():
    h = _read('monthly', 'index.html')
    for sid in PICK:
        for href, _, _ in _top(_section(h, sid)) or []:
            assert os.path.exists(os.path.join(ROOT, 'zone', href, 'index.html')), '없는 리포트로 링크: %s' % href


def test_generator_does_not_hardcode_region_names_in_summaries():
    src = _read('tools', 'make_monthly_page.py')
    body = src[src.index('def top3_lines'):src.index('def _with_top')]
    names = [z for z in SZ.ORDER if z not in SZ.AGG and ("'%s'" % z) in body]
    assert not names, '요약 생성기에 지역 이름을 박았다: %s' % names


def test_entry_points_exist():
    idx = _read('index.html')
    m = re.search(r'<div id="view-stats".*?</header>', idx, re.S)
    assert m and 'href="/monthly/"' in m.group(0), '통계 탭 첫 화면에 이달의 통계 진입점이 없다'
    assert 'href="/monthly/"' in _read('zone', 'index.html'), '시도 허브에 이달의 통계 진입점이 없다'
    assert "/monthly/" in _read('tools', 'make_sido_pages.py'), '허브 진입점이 생성기가 아니라 출력물에만 있다'
    assert 'href="/monthly/"' in _read('weekly', 'index.html'), '주간 페이지에 이달의 통계 진입점이 없다'


# ---------------------------------------------------------------------------
# 표가 원천 계열의 올바른 칸을 싣는가(2026-09-23 전체 점검 시험 보강)
# 위 시험은 요약과 표를 서로 대조할 뿐이라, 표의 '전세' 칸에 매매 값을 넣어도(요약은 매매 칸만 읽는다)
# 초록이었다. 여기서는 build() 의 표를 **원천 계열**과 칸마다 대조한다.
# ---------------------------------------------------------------------------
import make_monthly_page as MP  # noqa: E402
import make_weekly_page as MW  # noqa: E402


def _fixture():
    """data.js 와 같은 모양의 한 달치. 칸마다 값의 크기·부호가 달라 칸이 섞이면 바로 드러난다.

    매매는 오르고(+), 전세는 내리고(−), 월세는 작게 오른다 — 매매·전세 방향이 갈린 달.
    전세가율은 14개월, 달마다 0.3%p 씩 올라 '1년 전'(12개월 전)과 '11개월 전'이 다른 값이다.
    """
    regs = list(SZ.ORDER)
    n = len(regs)
    ma = [round(0.11 * (i + 1), 2) for i in range(n)]
    je = [round(-0.07 * (i + 1), 2) for i in range(n)]
    wo = [round(0.013 * (i + 1), 3) for i in range(n)]
    adv = {'monthly': {'regions': regs, 'rows': [{'p': '2026.07', 'ma': ma, 'je': je, 'wo': wo}]}}
    dates = ['2025.%02d' % m for m in range(6, 13)] + ['2026.%02d' % m for m in range(1, 8)]   # 14개월
    jr = {r: [60.0 + i + 0.3 * k for k in range(len(dates))] for i, r in enumerate(regs)}
    un = {r: [1000.0 * (i + 1), 1000.0 * (i + 1) + 37 * (i + 1)] for i, r in enumerate(regs)}
    sts = {'전세가율': {'dates': dates, 'series': jr},
           '미분양': {'dates': ['2026.06', '2026.07'], 'series': un}}
    return adv, sts, dict(ma=ma, je=je, wo=wo)


def _cells(adv, sts, sid):
    secs, _ = MP.build(adv, sts)
    return _rows(_section(''.join(secs), sid))


def test_price_table_puts_each_series_in_its_own_column():
    """'시도별 매매·전세·월세' 표의 세 칸이 ADV.monthly 의 ma·je·wo 와 지역마다 같아야 한다.

    변이: build() 의 전세 칸 `pv2(je)` 를 `pv2(ma)` 로 바꾸면 빨개진다(실제로 바꿔 확인 — 옛 요약 대조
          시험은 초록이었다). 매매·월세 칸을 서로 바꿔도 빨개진다.
    픽스처: 매매 상승·전세 하락으로 방향이 갈린 한 달(_fixture 독스트링).
    """
    adv, sts, src = _fixture()
    rows = _cells(adv, sts, 'price')
    regs = adv['monthly']['regions']
    assert set(rows) == set(regs)
    for i, r in enumerate(regs):
        want = [MW.pv2r(src[k][i]) for k in ('ma', 'je', 'wo')]
        assert rows[r] == want, '%s: 표 %s ≠ 원천(매매·전세·월세) %s' % (r, rows[r], want)


def test_jeonse_and_unsold_tables_use_the_right_reference_month():
    """전세가율 표는 '최신값, 12개월 전 대비', 미분양 표는 '최신값, 전월 대비'다.

    변이: 전세가율의 `series_at(jr, i - 12)` 를 `i - 11` 로 바꾸면 변화가 +3.60 이 아니라 +3.30 이 되어
          빨개진다. 미분양의 전월 대비를 `prev[r] - c` 로 뒤집어도 빨개진다(둘 다 확인).
    픽스처: 전세가율이 달마다 0.3%p 오르는 14개월, 미분양이 한 달 새 늘어난 두 달.
    """
    adv, sts, _ = _fixture()
    jr = _cells(adv, sts, 'jeonse')
    for r, ser in sts['전세가율']['series'].items():
        assert jr[r][0] == float('%.1f' % ser[-1]), r
        assert abs(jr[r][1] - MW.pv2r(ser[-1] - ser[-13])) < 1e-9, '%s: 1년 전 대비 %s' % (r, jr[r][1])
    un = _cells(adv, sts, 'unsold')
    for r, ser in sts['미분양']['series'].items():
        assert un[r] == [ser[-1], ser[-1] - ser[-2]], '%s: %s' % (r, un[r])


def test_price_table_matches_the_stored_monthly_row():
    """실데이터에서도 표의 세 칸이 저장된 ADV.monthly 마지막 행과 같다(값이 아니라 **대응**을 본다).

    변이: 위와 같은 칸 바꿔치기(전세 칸에 매매)로 빨개진다(확인).
    픽스처: 저장소의 data.js 그대로.
    """
    import make_sido_pages as P
    adv, sts = P.load()
    rows = _cells(adv, sts, 'price')
    mo = adv['monthly']
    last = mo['rows'][-1]
    n = len(mo['regions'])
    checked = 0
    for i, r in enumerate(mo['regions']):
        if r not in rows:
            continue
        want = []
        for k in ('ma', 'je', 'wo'):
            v = (last.get(k) or [None] * n)[i]
            want.append(None if v is None else MW.pv2r(v))
        assert rows[r] == want, '%s: 표 %s ≠ 저장값 %s' % (r, rows[r], want)
        checked += 1
    assert checked == len(SZ.ORDER), '표에 실린 지역이 %d곳뿐이다' % checked
