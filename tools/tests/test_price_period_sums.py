# -*- coding: utf-8 -*-
"""가격 변동률의 분기·연 합 — 시도 리포트 분기 표와 홈 공급·가격 표가 같은 칸을 같게 쓴다(전수 리뷰 #15·#110, 대표 결정 ⑧).

재현하는 실제 상태:
  - #15: 전남광주 월간 계열은 2025-04·05 에만 값이 있고 06 부터 비었다. 시도 리포트(price_quarters)와 홈(tbAgg)이 값이 있는
    달만 더해 25Q2 에 두 달 합(-0.5%·-0.7%·-0.1%)을 분기 변동률처럼 찍고 색을 칠했다. 홈 연 보기의 2025년은 1~5월 합이었다.
  - #110: 홈은 소수 둘째 자리로 반올림한 월값(split_data._r2)을 더해, 원값을 더하는 리포트와 표시값이 칸의 5%(2,211칸 중 121칸)
    에서 갈렸다(대전 24Q1 매매 리포트 -2.7% · 홈 -2.6%).
정본은 sido_zones.price_periods(달이 다 찬 칸만, 원값으로 한 번)이고, split_data.price_agg 가 그 합을 화면 자리(소수 첫째,
half-up)로 ADV.monthly.agg 에 싣고, 홈 tbAgg 가 그 값을 읽는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - price_periods 의 `c == need` 조건을 빼면(값이 있는 달만 더함) → 부분 분기·부분 연 단정이 빨강
  - tbAgg 가 agg 대신 월값을 다시 더하게 되돌리면 → node 대조(agg 모드)가 빨강
  - tbAgg 의 옛 데이터 경로에서 달 수 검사를 빼면 → node 대조(agg 없음)가 빨강
  - split_data.price_agg 가 합을 2자리로 반올림해 실으면 → 실데이터 표시값 대조가 빨강
픽스처: 두 지역(A 는 2025-06 결측 = 전남광주 모양, B 는 다 참), 2025-01~2026-05(마지막 해가 5달뿐 = 연 보기의 올해).
실데이터 대조는 저장소 data.js 에서 그때그때 유도하므로 데이터가 앞으로 가도 초록이다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import sido_zones as SZ  # noqa: E402
import split_data as S  # noqa: E402
import make_sido_pages as P  # noqa: E402
import home_src as HS  # noqa: E402

REGS = ['A', 'B']


def _fixture():
    rows = []
    for y, last in ((2025, 12), (2026, 5)):
        for m in range(1, last + 1):
            k = (y - 2025) * 12 + m
            a = None if (y, m) == (2025, 6) else round(0.1 * k - 0.35, 4)
            b = round(-0.07 * k + 0.2, 4)
            rows.append({'p': '%d-%02d' % (y, m), 'ma': [a, b], 'je': [a, b], 'wo': [a, b]})
    return {'regions': REGS, 'rows': rows}


def test_partial_quarter_and_year_are_left_empty():
    mo = _fixture()
    q = SZ.price_periods(mo, 'q')
    assert 'A' not in q['2025Q2'], 'A 는 6월이 없는데 2025Q2 합이 나왔다: %s' % q['2025Q2'].get('A')
    b_q2 = sum(r['ma'][1] for r in mo['rows'] if r['p'] in ('2025-04', '2025-05', '2025-06'))
    assert abs(q['2025Q2']['B'][0] - b_q2) < 1e-9
    assert '2026Q2' not in q, '2026Q2 는 4·5월뿐이다'
    y = SZ.price_periods(mo, 'y')
    assert 'A' not in y['2025'] and '2026' not in y, '달이 덜 찬 해가 합으로 나왔다(대표 결정 ⑧)'
    assert abs(y['2025']['B'][0] - sum(r['ma'][1] for r in mo['rows'] if r['p'].startswith('2025'))) < 1e-9
    # 시도 리포트 분기 표도 같은 함수 — 부분 분기는 키 자체가 없다('–')
    pq = P.price_quarters({'monthly': mo})
    assert 'A' not in pq[SZ.qidx(2025, 2)] and pq[SZ.qidx(2025, 1)]['A'][0] is not None


def _tbagg_js():
    src = dict(HS.home_files())['home-app.js']
    parts = []
    for pat in (r'var TB_SIZE=\{[^}]*\};', r'var TB_PF=\{[^}]*\};'):
        m = re.search(pat, src)
        assert m, '%s 를 home-app.js 에서 못 찾았다' % pat
        parts.append(m.group(0))
    i = src.index('function tbAgg(rows,per){')
    depth, j = 0, src.index('{', i)
    while True:
        c = src[j]
        depth += (c == '{') - (c == '}')
        j += 1
        if depth == 0:
            break
    parts.append(src[i:j])
    return '\n'.join(parts)


def _node_tbagg(mo, per, with_agg):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    rows = []
    for r in mo['rows']:
        y, m = int(r['p'][:4]), int(r['p'][5:7])
        rows.append({'i': y * 12 + m - 1, 'fut': False, 's': [0, 0], 'm': r['ma'], 'j': r['je'], 'w': r['wo']})
    cache = {'pagg': S.price_agg(mo) if with_agg else None, 'pidx': [mo['regions'].index(z) for z in REGS]}
    js = ('var TB_BCACHE=%s;\n%s\nvar out=tbAgg(%s,%s).map(function(c){return [c.g,c.m];});\n'
          'process.stdout.write(JSON.stringify(out));'
          % (json.dumps(cache), _tbagg_js(), json.dumps(rows), json.dumps(per)))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _label(g, per):
    return ('%dQ%d' % (g // 4, g % 4 + 1)) if per == 'q' else str(g)


@pytest.mark.parametrize('per', ['q', 'y'])
@pytest.mark.parametrize('with_agg', [True, False])
def test_home_tbagg_empties_the_same_cells(per, with_agg):
    """홈 tbAgg 가 시도 리포트(price_periods)와 같은 칸을 비운다 — agg 를 읽을 때와, agg 가 없는 옛 데이터일 때 모두."""
    mo = _fixture()
    want = SZ.price_periods(mo, per)
    for g, m in _node_tbagg(mo, per, with_agg):
        lab = _label(g, per)
        for k, z in enumerate(REGS):
            exp = (want.get(lab) or {}).get(z)
            exp = None if exp is None else exp[0]
            got = m[k] if m else None
            if exp is None:
                assert got is None, '%s %s: 덜 찬 칸인데 홈이 %s 를 낸다' % (lab, z, got)
            elif with_agg:
                assert got == SZ.half_up(exp * 10) / 10.0, (lab, z, got, exp)
            else:
                assert abs(got - exp) < 1e-9, (lab, z, got, exp)


def _adv():
    src = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    return json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', src, re.S).group(1))


def test_home_quarter_values_are_the_report_values():
    """실데이터 전 칸: 홈이 읽는 분기 합(split_data.price_agg)의 표시값 = 시도 리포트 분기 표의 표시값(pct1)."""
    adv = _adv()
    mo = adv['monthly']
    agg = S.price_agg(mo)['q']
    pq = P.price_quarters(adv)
    regs = mo['regions']
    n = 0
    for i, byz in pq.items():
        lab = SZ.qkey(i)
        if lab[:4] < S.TABLE_FROM[:4]:
            continue
        for z, vals in byz.items():
            for f, v in zip(SZ.PRICE_FIELDS, vals):
                h = agg[lab][f][regs.index(z)]
                if v is None:
                    assert h is None, (lab, z, f, h)
                    continue
                assert P.pct1(v) == P.pct1(h), '%s %s %s: 리포트 %s · 홈 %s' % (lab, z, f, P.pct1(v), P.pct1(h))
                n += 1
    assert n > 1000, '대조한 칸이 너무 적다(%d) — 픽스처가 비었는지 볼 것' % n


def _split_to(tmp_path):
    """저장소 data.js 사본에 split_data 를 돌려 (코어 ADV, trend ADV)를 돌려준다 — 저장소 파일에는 쓰지 않는다
    (test_home_first_screen 의 split 픽스처와 같은 방식). 커밋된 산출물이 옛 판이어도 지금 코드의 페이로드를 본다."""
    import shutil as _sh
    src = tmp_path / 'data.js'
    _sh.copyfile(os.path.join(ROOT, 'data.js'), str(src))
    paths = {'SRC': src, 'OUT': tmp_path / 'data-core.js', 'REST': tmp_path / 'data-rest.json',
             'TREND': tmp_path / 'data-trend.json', 'SGG': tmp_path / 'data-sgg.json', 'SIZE': tmp_path / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    return core_adv, json.loads(paths['TREND'].read_text(encoding='utf-8'))['ADV']


def test_core_payload_ships_the_sums(tmp_path):
    """홈 코어(data-core.js)와 통계 탭 파일(data-trend.json) 둘 다 같은 합을 싣는다 — 통계 탭을 먼저 열면 loadFullData 가
    ADV.monthly 를 trend 것으로 통째로 바꾼다. 변이(실제로 확인): trend 쪽 w['agg'] 줄을 빼면 빨개진다."""
    want = S.price_agg(_adv()['monthly'])
    core, trend = _split_to(tmp_path)
    assert core['monthly'].get('agg') == want, '코어의 분기·연 합이 정본과 다르다'
    assert trend['monthly'].get('agg') == want, '통계 탭 파일의 분기·연 합이 정본과 다르다'
