# -*- coding: utf-8 -*-
"""'전월 대비'·'1년 전 대비'는 인덱스 차가 아니라 **달 라벨**로 비교 칸을 찾는다(2026-09-26 데이터 감사 #17).

배치는 불완비한 달을 보류한다(update_adv_data._drop_incomplete). 2026-09-26 배치 로그에 'supply 미분양: 2026-07
제외, 시도 1곳 결측(전남광주)'이 매 회차 찍혀 있다. R-ONE 이 07 을 끝내 안 채운 채 08 을 완비해 내면 merge_basic 은
08 을 06 바로 뒤에 붙이고, 07 칸은 없다. 예전엔 소비처가 모두 i-1·i-12 로 비교 칸을 잡아 /monthly/ 가 '08 − 06'
(두 달 치)을 '전월 대비'로 싣고, 요약 줄도 같은 값으로 3곳을 뽑았다. 감시는 dates[-1] 만 보므로 이 상태를
경보하지 않는다. 같은 인덱스 산식이 /jeonse-ratio/·시도 리포트 카드(li-12), 블로그 도구(_series_last 의 '결측을
건너뛴 앞 값'), 홈 통계표(k-lag)에도 있었다.

픽스처: 실제 상태를 재현한 합성 계열이다. 미분양은 [..., 2026.05, 2026.06, 2026.08](07 보류 후 08 완비 — 감사가
update_supply 전 경로로 재현한 모양), 전세가율은 12달 창 안에서 한 달이 빠진 계열이다. 값은 달마다 다르게 두어
어느 칸과 견줬는지가 숫자로 드러난다(실데이터 전세가율은 0.1씩 움직여 13달 전과 12달 전이 같을 수 있다).

무엇을 깨뜨리면 빨개지나(각각 실제로 적용해 확인):
  - sido_zones.month_back 을 인덱스 차(`return i - k if i >= k else None`)로 바꾸면 → 월간·전세가율·시도 카드·
    블로그 시험이 모두 빨강
  - make_monthly_page 의 미분양 비교를 `series_at(un, i - 1)` 로 되돌리면 → 월간 표 시험 빨강(08−06 = +30)
  - top3_lines 의 미분양 비교를 `i - 1` 로 되돌리면 → 요약 줄 시험 빨강(3곳이 실린다)
  - _with_top 의 사유 줄 분기를 지우면 → 요약 줄이 사라져 빨강
  - build_jeonse 의 `at(name, ya)` 를 `at(name, li - 12)` 로 되돌리면 → 13달 전 값이 실려 빨강
  - 시도 카드의 ya 를 `li - 12` 로, 블로그의 j 를 `idx[-2]`(결측 건너뛴 앞 값)로 되돌리면 → 각 시험 빨강
  - 홈 buildTable 의 비교를 `(k>=lag)?vals[k-lag]:null` 로 되돌리면 → 홈 시험 둘 다 빨강, 연 1점 구간 예외를
    지우면 → 미분양 2006.12 단정이 빨강
"""
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import make_indicator_pages as I  # noqa: E402
import make_monthly_page as MP  # noqa: E402
import make_naver_post as NP  # noqa: E402
import make_sido_pages as SP  # noqa: E402
import sido_zones as SZ  # noqa: E402
from test_monthly_top3 import _assert_summary_matches_table, _rows, _section, _top  # noqa: E402


def _months(a, b, skip=()):
    """'YYYY.MM' a 부터 b 까지(포함), skip 에 든 달은 뺀다."""
    y, m = (int(x) for x in a.split('.'))
    out = []
    while True:
        lab = '%04d.%02d' % (y, m)
        if lab not in skip:
            out.append(lab)
        if lab == b:
            return out
        y, m = y + (m == 12), m % 12 + 1


# ── 정본 함수 ────────────────────────────────────────────────────────────
def test_month_back_counts_months_by_label():
    d = ['2025.12', '2026.01', '2026.02 p)', '2026.04']
    assert SZ.month_back(d, 1, 1) == 0, '연 경계(1월 → 전년 12월)'
    assert SZ.month_back(d, 2, 1) == 1, "잠정 꼬리표('p)')가 붙은 라벨도 달로 읽는다"
    assert SZ.month_back(d, 3, 1) is None, '빠진 달(03)을 건너뛰고 02 를 전월로 잡았다'
    assert SZ.month_back(d, 3, 4) == 0
    assert SZ.month_back(d, 0, 1) is None
    assert SZ.month_back(d, 9, 1) is None


# ── /monthly/ ────────────────────────────────────────────────────────────
UN_DATES = ['2026.05', '2026.06', '2026.08']      # 07 보류 후 08 완비


def _unsold():
    regs = list(SZ.ORDER)
    return {'dates': list(UN_DATES),
            'series': {r: [1000.0 + i, 1100.0 + i, 1130.0 + i] for i, r in enumerate(regs)}}


def _jeonse(skip=('2025.12',)):
    """2025.01~2026.08 에서 skip 달이 빠진 전세가율. 값은 달마다 0.7 씩, 지역마다 1.0 씩 다르다."""
    dates = _months('2025.01', '2026.08', skip)
    regs = list(dict.fromkeys(list(SZ.ORDER) + ['전국', '수도권', '지방'] + list(I.SIDO17)))
    ser = {}
    for i, r in enumerate(regs):
        ser[r] = []
        for lab in dates:
            y, m = (int(x) for x in lab.split('.'))
            ser[r].append(round(50.0 + i + 0.7 * ((y - 2025) * 12 + m), 1))
    return {'dates': dates, 'series': ser}


def _val(block, r, lab):
    return block['series'][r][block['dates'].index(lab)]


def test_monthly_unsold_does_not_call_a_two_month_change_last_month():
    sts = {'미분양': _unsold()}
    secs, _ = MP.build({}, sts)
    sec = _section(''.join(secs), 'unsold')
    rows = _rows(sec)
    assert rows, '미분양 표가 비었다'
    for r, cells in rows.items():
        assert cells[0] == _val(sts['미분양'], r, '2026.08'), r
        assert cells[1] is None, '%s: 07 이 없는데 전월 대비 %s 를 실었다(08 − 06)' % (r, cells[1])
    top = _top(sec)
    assert top == [], '비교할 달이 없는데 요약에 3곳을 뽑았다: %s' % top
    line = re.search(r'<p class="top3">(.*?)</p>', sec, re.S).group(1)
    assert '2026년 7월' in line, '요약 줄이 어느 달이 비었는지 말하지 않는다: %s' % line
    _assert_summary_matches_table('unsold', sec)


def test_monthly_unsold_with_the_month_present_still_compares():
    """07 이 있으면 예전처럼 전월 대비와 3곳이 나온다 — 고친 뒤에도 평소 달은 그대로."""
    un = _unsold()
    un['dates'][-1] = '2026.07'
    secs, _ = MP.build({}, {'미분양': un})
    sec = _section(''.join(secs), 'unsold')
    for r, cells in _rows(sec).items():
        assert cells[1] == 30.0, (r, cells)
    assert len(_top(sec)) == 3
    _assert_summary_matches_table('unsold', sec)


def test_monthly_jeonse_compares_with_the_same_month_a_year_ago():
    jr = _jeonse()
    secs, _ = MP.build({}, {'전세가율': jr})
    sec = _section(''.join(secs), 'jeonse')
    for r, cells in _rows(sec).items():
        want = _val(jr, r, '2026.08') - _val(jr, r, '2025.08')
        assert cells[1] == float(MP.pv2(want)), '%s: 1년 전 대비 %s ≠ %s(2025.08 과 견줌)' % (r, cells[1], want)
    _assert_summary_matches_table('jeonse', sec)


def test_monthly_jeonse_without_the_year_ago_month_leaves_it_blank():
    jr = _jeonse(skip=('2025.08',))
    secs, _ = MP.build({}, {'전세가율': jr})
    sec = _section(''.join(secs), 'jeonse')
    assert all(c[1] is None for c in _rows(sec).values()), '1년 전 달이 없는데 다른 달과 견줬다'
    assert _top(sec) == [] and '2025년 8월' in sec
    _assert_summary_matches_table('jeonse', sec)


# ── /jeonse-ratio/ · 시도 리포트 카드 ────────────────────────────────────
def test_jeonse_page_compares_with_the_same_month_a_year_ago():
    jr = _jeonse()
    html, _ = I.build_jeonse({'전세가율': jr})
    nat = _val(jr, '전국', '2026.08')
    ago = _val(jr, '전국', '2025.08')
    assert '1년 전 대비 %+.1f%%p' % round(nat - ago, 1) in html
    row = re.search(r'<tr class="agg"><td>전국</td><td>[\d.]+%</td><td>([\d.]+)%</td>', html)
    assert row and float(row.group(1)) == ago, '전국 1년 전 칸이 2025.08 이 아니다: %s' % (row and row.group(1))


def test_jeonse_page_survives_a_missing_year_ago_month():
    """1년 전 달이 없으면 비교 문구만 빠진다. 예전엔 None 빼기로 생성기가 죽어 그날 배치 커밋이 막혔다."""
    html, _ = I.build_jeonse({'전세가율': _jeonse(skip=('2025.08',))})
    assert '2026.08 기준' in html
    assert '1년 전 대비' not in html and '1년 새 가장 크게 오른 곳' not in html


def test_zone_card_compares_with_the_same_month_a_year_ago():
    jr = _jeonse()
    z = next(r for r in SZ.ORDER if r not in SZ.AGG)
    html = SP.next_links(z, None, {'전세가율': jr})
    want = round(_val(jr, z, '2026.08') - _val(jr, z, '2025.08'), 1) + 0.0
    assert '1년 전 대비 %+.1f%%p' % want in html, html


# ── 블로그 도구 ──────────────────────────────────────────────────────────
def test_blog_last_month_is_the_calendar_month_before():
    sts = {'미분양': {'dates': list(UN_DATES), 'series': {'전국': [65000, 67464, 68000]}}}
    assert NP._series_last(sts, '미분양') == (None, None, None), '두 달 전 값을 전월로 적었다'
    assert NP.extra_section({}, sts, 1) == '', '전월이 없는데 미분양 절을 썼다'
    sts['미분양']['dates'][-1] = '2026.07'
    assert NP._series_last(sts, '미분양') == (68000, 67464, '2026.07')


# ── 홈 통계표 ────────────────────────────────────────────────────────────
def _fn(src, head):
    a = src.find(head)
    assert a >= 0, '홈 스크립트에서 %s 를 찾지 못했다 — 구조가 바뀌었으면 이 시험도 고칠 것' % head
    b = src.find('\n}\n', a)
    return src[a:b + 2]


def _home_table(ds, dates, vals):
    """홈 drawStat 이 buildTable 을 부르는 모양 그대로 돌려 {라벨: 증감 문자열} 을 받는다."""
    if not shutil.which('node'):
        pytest.skip('node 없음')
    s = HS.home_source()
    cum = re.search(r'const DS_CUM=new Set\([^)]*\);', s)
    assert cum, '홈 스크립트에서 DS_CUM 을 찾지 못했다'
    js = ('const T={thead:{innerHTML:""},tbody:{innerHTML:""}};'
          'const document={querySelector:q=>q.endsWith("thead")?T.thead:T.tbody};'
          'const DS_LABEL=new Proxy({},{get:()=>"값"});function fmtN(v,d){return d==null?String(v):v.toFixed(d)}'
          '%s\nconst ST={ds:%s};\n%s\n%s\n'
          'const D={dates:%s};const parsed=D.dates.map(parseDate);const idx=parsed.map((p,i)=>i);'
          'buildTable(D,idx.map(i=>parsed[i].label),%s,idx,parsed);'
          'const out={},re=/<tr><td>([^<]*)<\\/td><td>[^<]*<\\/td><td>(.*?)<\\/td><\\/tr>/g;let m;'
          'while((m=re.exec(T.tbody.innerHTML)))out[m[1]]=m[2].replace(/<[^>]+>/g,"").split(" ")[0];'
          'process.stdout.write(JSON.stringify(out));'
          % (cum.group(0), json.dumps(ds, ensure_ascii=False), _fn(s, 'function parseDate('),
             _fn(s, 'function buildTable('), json.dumps(dates), json.dumps(vals)))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def test_home_table_compares_calendar_neighbours():
    got = _home_table('미분양', ['2005.12', '2006.12', '2007.01', '2026.05', '2026.06', '2026.08'],
                      [10, 30, 35, 100, 120, 150])
    assert got['2026.08'] == '', '07 이 없는데 08 − 06 을 전기 대비로 실었다: %s' % got['2026.08']
    assert got['2026.06'] == '+20'
    assert got['2007.01'] == '+5'
    assert got['2006.12'] == '+20', '연 1점(12월) 구간은 전년 12월과 견준다 — 미분양 2000~2006년'


def test_home_cumulative_table_compares_the_same_month_last_year():
    dates = _months('2025.01', '2026.08', skip=('2025.07',))
    vals = list(range(len(dates)))
    got = _home_table('인허가', dates, vals)
    assert got['2026.07'] == '', '2025.07 이 없는데 다른 달과 전년 동월 대비를 냈다: %s' % got['2026.07']
    i8, j8 = dates.index('2026.08'), dates.index('2025.08')
    assert got['2026.08'] == '+%d' % (vals[i8] - vals[j8])
