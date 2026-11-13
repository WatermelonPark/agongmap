# -*- coding: utf-8 -*-
"""홈의 '늦게 받는 데이터'와 history 항목 — 2026-11-13 전수 리뷰(홈 스크립트)에서 확인한 것.

① 통계 탭을 열 때 받는 data-trend.json 이 코어(data-core.js)보다 옛 판이면 홈의 이번 주·이번 달 값을 지난 것으로 덮었다.
② 대결 결과에서 다른 테스트로 가면 뒤로 가기가 헛돌았다(두 항목의 쿼리가 달라 hashchange 가 오지 않는다). 2026-11-14 퀴즈 3종을
   걷어 대상 코드(goQuiz)와 시험이 함께 빠졌다.
③ 같은 화면 탭을 다시 누르면 지금 항목의 state 를 지워, 지역 그래프를 닫은 뒤 첫 뒤로 가기가 헛돌았다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import home_src as HS  # noqa: E402
import _js as J  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _app():
    return dict(HS.home_files())['home-app.js']


def _core_adv():
    """저장소 data-core.js 의 ADV(홈이 부팅 때 갖는 것)."""
    t = io.open(os.path.join(ROOT, 'data-core.js'), encoding='utf-8').read()
    m = re.search(r'const ADV\s*=\s*', t)
    return json.JSONDecoder().raw_decode(t[m.end():])[0]


def _trend():
    return json.loads(io.open(os.path.join(ROOT, 'data-trend.json'), encoding='utf-8').read())


def _stale(trend):
    """한 회차 묵은 trend — 주간·월간 블록의 마지막 행(시군구 행 포함)을 하나씩 뺀다(서비스워커 캐시본의 모양)."""
    t = json.loads(json.dumps(trend))
    for k in ('weekly', 'monthly'):
        b = t['ADV'][k]
        b['rows'] = b['rows'][:-1]
        if b.get('sgg') and len(b['sgg']['rows']) > 1:
            b['sgg']['rows'] = b['sgg']['rows'][:-1]
    return t


def test_a_stale_trend_file_does_not_roll_the_home_back():
    """옛 주의 trend 를 받아도 ADV.weekly·monthly 의 마지막 행은 코어의 것이고, 이력은 trend 것에 코어의 새 행을 이어 붙인다.

    변이(실제로 확인): loadData 가 `lateBlock(ADV[k],A[k])` 대신 `A[k]` 를 그대로 싣게 되돌리면(예전 Object.assign) 마지막 주가
          지난주로 돌아가 빨개진다. lateBlock 이 이력을 잇지 않고 코어만 돌려주면 행 수 단정이 빨개진다.
    픽스처: 저장소의 실제 코어·trend 에서 trend 만 한 회차 묵힌 상태(홈만 자주 보던 사람이 느린 망에서 시세 탭을 연 경우).
    """
    core, fresh = _core_adv(), _trend()
    stale = _stale(fresh)
    js = ('var ADV=%s, STATS={}, PART_WAIT=0, PART_FAIL=false;\n' % json.dumps(core, ensure_ascii=False)
          + 'const document={getElementById(){return null;}};\n'
          + 'var __NEXT=null; function fetch(u){return Promise.resolve({ok:true,json(){return Promise.resolve(__NEXT);}});}\n'
          + 'let _loaded={};\n' + J.fns(_app(), 'lateBlock', 'loadData') + r"""
const last=b=>b.rows[b.rows.length-1].p, OUT={};
(async function(){
  __NEXT=%s; await loadData('/data-trend.json');
  OUT.stale={w:last(ADV.weekly), m:last(ADV.monthly), wn:ADV.weekly.rows.length, mn:ADV.monthly.rows.length,
             head:ADV.weekly.head&&ADV.weekly.head.p, note:!!ADV.weekly.note, bubble:!!ADV.bubble,
             sgg:last(ADV.weekly.sgg), sggn:ADV.weekly.sgg.rows.length,
             sorted:ADV.weekly.rows.every((r,i,a)=>!i||a[i-1].p<r.p)};
  _loaded={}; __NEXT=%s; await loadData('/data-trend.json');
  OUT.fresh={w:last(ADV.weekly), wn:ADV.weekly.rows.length, mn:ADV.monthly.rows.length};
  process.stdout.write(JSON.stringify(OUT));
})().catch(e=>{console.error(e&&e.stack||e);process.exit(1);});
""" % (json.dumps(stale, ensure_ascii=False), json.dumps(fresh, ensure_ascii=False)))
    o = J.node(js)
    cw, cm = core['weekly']['rows'][-1]['p'], core['monthly']['rows'][-1]['p']
    fw, fm = fresh['ADV']['weekly'], fresh['ADV']['monthly']
    assert stale['ADV']['weekly']['rows'][-1]['p'] < cw, '픽스처가 묵은 trend 를 재현하지 못했다'
    assert (o['stale']['w'], o['stale']['m']) == (cw, cm), '묵은 trend 가 홈의 이번 주·이번 달을 덮었다: %r' % o['stale']
    assert o['stale']['wn'] == len(fw['rows']) and o['stale']['mn'] == len(fm['rows']), o['stale']   # 이력 + 코어의 새 행
    assert o['stale']['head'] == core['weekly']['head']['p'] and o['stale']['sorted'], o['stale']
    assert o['stale']['note'] and o['stale']['bubble'], 'trend 만 가진 것(주석·버블)이 빠졌다: %r' % o['stale']
    assert o['stale']['sgg'] == core['weekly']['sgg']['rows'][-1]['p'] and o['stale']['sggn'] == len(fw['sgg']['rows']), o['stale']
    assert o['fresh'] == {'w': fw['rows'][-1]['p'], 'wn': len(fw['rows']), 'mn': len(fm['rows'])}, o['fresh']


def test_late_block_keeps_the_core_when_regions_differ():
    """지역 목록이 다른 옛 trend(모델 개편 전 캐시본)는 행을 이을 수 없다 — 코어 블록을 그대로 둔다. 새 trend 는 그대로 받는다.

    변이(실제로 확인): lateBlock 의 지역 목록 비교 줄을 지우면 열이 어긋난 행이 이어져 빨개진다.
    픽스처: 지역이 둘인 코어와 지역 순서가 다른 옛 trend, 같은 주의 trend, 더 새 trend.
    """
    js = J.fns(_app(), 'lateBlock') + r"""
const cur={regions:['가','나'],rows:[{p:'2026-11-09',ma:[1,2]}],head:{p:'2026-11-09'}};
const old={regions:['나','가'],rows:[{p:'2026-11-02',ma:[9,8]}]};
const same={regions:['가','나'],rows:[{p:'2026-11-02',ma:[5,6]},{p:'2026-11-09',ma:[1,2]}],note:'n'};
const newer={regions:['가','나'],rows:[{p:'2026-11-16',ma:[3,4]}]};
process.stdout.write(JSON.stringify({old:lateBlock(cur,old)===cur, same:lateBlock(cur,same)===same,
  newer:lateBlock(cur,newer)===newer, none:lateBlock(undefined,same)===same}));
"""
    assert J.node(js) == {'old': True, 'same': True, 'newer': True, 'none': True}


def test_same_view_tab_press_keeps_the_entry_state():
    """같은 화면 탭을 다시 누를 때 지금 항목의 state 를 지우지 않는다(history.replaceState 에 history.state 를 넘긴다).

    왜: null 을 넘기면 지역 그래프가 연 항목의 표지(trBase)가 사라져, 그 뒤 '지도'로 닫을 때 trHashDrop 이 한 칸 접지 못하고
        같은 주소가 두 칸 쌓였다 — 첫 뒤로 가기가 헛돈다.
    변이(실제로 확인): showView 의 그 줄을 `history.replaceState(null,'',tgtUrl)` 로 되돌리면 빨개진다.
    픽스처: 저장소의 실제 showView 본문(같은 화면 갈래 한 줄).
    """
    body = J.fn(_app(), 'showView')
    m = re.search(r'if\(v===curView\)history\.replaceState\(([^,]+),', body)
    assert m, '같은 화면 갈래(v===curView)의 replaceState 를 찾지 못했다 — 코드가 바뀌었으면 이 시험도 고칠 것'
    assert m.group(1).strip() == 'history.state', '같은 화면 탭이 항목 state 를 %s 로 덮는다' % m.group(1)
