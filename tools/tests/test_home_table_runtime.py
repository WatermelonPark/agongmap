# -*- coding: utf-8 -*-
"""홈 공급·가격 표(home-app.js tbBuild·tbAgg·tbDraw)를 실데이터로 node 에 올려 시도 리포트 분기 표와 대조한다
(전수리뷰 2차 H1-4·X2-5·X2-6·X2-7).

같은 대상(분기별 준공 실적·착공 기반 추정 세대수와 적정 대비 %)을 홈 JS(월 단위로 짓고 위로 합침)와 파이썬
(make_sido_pages.series, 분기 full_only)이 따로 잰다. 2026-08-07·08 감사에서 이 쌍이 실제로 갈렸는데(미래 240칸 중 51칸 ±1,
1,000칸 중 1칸 %) 회귀 시험은 가격 합(test_price_period_sums)뿐이었다. 기대값은 모두 데이터에서 유도하므로 분기가
넘어가도 초록이다.

픽스처: 저장소 data.js 사본에 split_data 를 돌려(저장소 파일에는 쓰지 않는다) 지금 코드가 내는 data-core.js 를 그대로
node 에 싣는다 — 배치가 구운 홈 페이로드와 같은 상태다.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_sido_pages as P  # noqa: E402
import sido_zones as SZ  # noqa: E402
import split_data as S  # noqa: E402

DOM = r"""
const __els={};
function __mk(id){
  return {id,style:{},innerHTML:'',textContent:'',hidden:true,checked:false,dataset:{},
    setAttribute(){},getAttribute(){return null},scrollIntoView(){},addEventListener(){}};
}
const window=globalThis;
const document={getElementById(id){return __els[id]||(__els[id]=__mk(id));},querySelector(){return null},
  querySelectorAll(){return []}};
"""

SYN = '시험용이름'   # 표시 이름이 키와 다른 열을 데이터와 무관하게 하나 더 만든다(아래 시험 독스트링)


def _fn(src, name):
    a = src.find('function %s(' % name)
    assert a >= 0, '%s 를 찾지 못했다' % name
    i, depth = src.index('{', a), 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[a:j + 1]
    raise AssertionError(name)


def _tb_vars(app):
    """home-app.js 의 한 줄짜리 `var TB_…` 선언(여러 줄인 TB_REFNOTE 는 표 그리기에 쓰지 않아 뺀다)."""
    out = [ln for ln in re.findall(r'^var TB_.*$', app, re.M) if not ln.rstrip().endswith('{')]
    assert any(ln.startswith('var TB_FROM=') for ln in out), out
    return '\n'.join(out)


@pytest.fixture(scope='module')
def home_table(tmp_path_factory):
    tmp = tmp_path_factory.mktemp('split')
    src = tmp / 'data.js'
    shutil.copyfile(os.path.join(P.ROOT, 'data.js'), str(src))
    paths = {'SRC': src, 'OUT': tmp / 'data-core.js', 'REST': tmp / 'data-rest.json',
             'TREND': tmp / 'data-trend.json', 'SGG': tmp / 'data-sgg.json', 'SIZE': tmp / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    app = dict(HS.home_files())['home-app.js']
    fns = ('_ymP', '_ymT', 'zn', 'tintA', 'tbTint', 'tbPv', 'tbNum', 'tbMi', 'tbQLast', 'tbLabel',
           'tbBuild', 'tbAgg', 'refBtn', 'tbRefSync', 'tbDraw')
    js = (DOM + core + '\n' + _tb_vars(app) + '\n' + '\n'.join(_fn(app, n) for n in fns) + r"""
TB_ANCHOR=false; document.getElementById('tb-main').dataset.refbound='1';
const B=tbBuild();
const OUT={regs:B.regs, from:TB_FROM, cells:[]};
tbAgg(B.rows,'q').forEach(function(c){
  const lab=Math.floor(c.g/4)+'Q'+(c.g%4+1);
  B.regs.forEach(function(r,k){
    const ref=B.refs[r]*c.n/3, v=c.s[k];
    OUT.cells.push([lab,r,Math.round(v),ref?Math.round(v/ref*100):null,c.fut,c.n]);
  });
});
// 표시 이름이 키와 다른 열 — 실데이터의 이름표(ADV.zname)에 합성 이름 하나를 더한다
ADV.zname=Object.assign({},ADV.zname||{},{[B.regs[1]]:'""" + SYN + r"""'});
OUT.zname=ADV.zname; OUT.html={};
['q','y'].forEach(function(p){ TB_PER=p; tbDraw(); OUT.html[p]=document.getElementById('tb-main').innerHTML; });
process.stdout.write(JSON.stringify(OUT));
""")
    if not shutil.which('node'):
        pytest.skip('node 없음')
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        p = subprocess.run(['node', path], capture_output=True, timeout=120)
    finally:
        os.remove(path)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def test_home_table_supply_cells_are_the_zone_report_cells(home_table):
    """홈 표 분기 칸(세대수·적정 대비 %)이 시도 리포트 분기 표(make_sido_pages.series·rnd)와 모든 지역·분기에서 같고,
    두 표의 분기 집합도 같다(X2-7·X2-6).

    변이(각각 실제로 확인): tbBuild 의 미래 칸을 월마다 Math.round(…*S.conv) 로 반올림하면(2026-08-07 감사 때의 결함)
    세대수 칸이, 홈 TB_FROM 을 2018*12 로 바꾸면 분기 집합 단정이, split_data.TABLE_FROM 을 '2018.01' 로 바꾸면(홈 표 2017년
    행이 진짜 0처럼 찍힌다) 세대수 칸이 빨개진다.
    """
    adv, stats = P.load()
    calc = adv['sido']
    want = {}
    for z in home_table['regs']:
        row = [x for x in calc['zones'] if x['z'] == z][0]
        for i, v, fut in P.series(stats, z, calc):
            want[(SZ.qkey(i), z)] = (P.rnd(v), P.rnd(v / float(row['ref']) * 100) if row['ref'] else None, fut)
    got = {(lab, z): (n, pct, fut) for lab, z, n, pct, fut, _ in home_table['cells']}
    assert {k[0] for k in got} == {k[0] for k in want}, '홈 표와 시도 리포트 표의 분기 집합이 다르다: 홈만 %s · 리포트만 %s' % (
        sorted({k[0] for k in got} - {k[0] for k in want}), sorted({k[0] for k in want} - {k[0] for k in got}))
    diff = [(k, got[k], want.get(k)) for k in got if got[k] != want.get(k)]
    assert not diff, '홈 표와 시도 리포트 표가 %d칸에서 갈린다(앞 5칸: %s)' % (len(diff), diff[:5])
    futs = [k for k, v in got.items() if v[2]]
    assert futs and len(futs) < len(got), '실적·추정 두 구간이 모두 대조되지 않았다'
    assert len(got) >= 19 * 40, '대조한 칸이 너무 적다(%d)' % len(got)


def test_home_table_starts_where_the_canon_starts(home_table):
    """홈 TB_FROM(월 인덱스)이 정본 sido_zones.TABLE_FROM_YEAR·split_data.TABLE_FROM·make_sido_pages.TABLE_FROM 과 같은 첫 달이다.

    변이(실제로 확인): home-app.js 의 TB_FROM 을 2018*12 로 바꾸면 빨개진다."""
    assert home_table['from'] == SZ.TABLE_FROM_YEAR * 12
    assert S.TABLE_FROM == '%d.01' % SZ.TABLE_FROM_YEAR
    assert P.TABLE_FROM == SZ.qidx(SZ.TABLE_FROM_YEAR, 1)


def test_home_table_titles_use_display_names(home_table):
    """표 칸 설명(title)과 열 머리가 판정 단위 키가 아니라 화면 이름(zn)을 쓴다(백로그 46 잔여, H1-4·X2-5).

    실데이터 이름표(ADV.zname — 지금은 '전남광주'→'광주·전남')에 둘째 열의 합성 이름을 더해, 이름표가 데이터에서 비어도
    키와 이름이 다른 열이 늘 하나 이상 있게 한다. 변이(실제로 확인): tbDraw 의 칸 title 을 옛 `B.regs[k]` 로 되돌리면
    빨개진다."""
    zname = home_table['zname']
    assert SYN in zname.values()
    for real_key in SZ.DISPLAY_NAME:
        if real_key in home_table['regs']:
            assert zname.get(real_key) == SZ.DISPLAY_NAME[real_key], '코어 이름표가 정본(DISPLAY_NAME)과 다르다'
    for per, html in home_table['html'].items():
        titles = re.findall(r'<td title="([^"]*)"', html)
        assert titles, per
        for k, name in zname.items():
            if k not in home_table['regs']:
                continue
            assert not [t for t in titles if t.startswith(k + ' ')], '%s 표 칸 title 이 키 %s 를 찍는다' % (per, k)
            assert [t for t in titles if t.startswith(name + ' ')], '%s 표에 %s 칸 title 이 없다' % (per, name)
            assert '>%s</a></th>' % k not in html and '>%s</a></th>' % name in html, per
