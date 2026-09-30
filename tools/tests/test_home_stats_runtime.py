# -*- coding: utf-8 -*-
"""홈 통계 화면(home-stats.js)과 부팅 가드(home-app.js)를 실제 코드로 node 에 올려 고정한다 — 2026-09-30 전수 리뷰.

home-stats.js 는 최상위에 선언만 있어(실행문 없음) 파일 전체를 vm 에 올리고, 쓰는 홈 전역(loadFullData·track·statsNav·
<wk-release> 구간 등)은 모형이나 home-app.js 에서 꺼낸 실제 함수로 둔다. DOM 은 아무 id 나 받는 작은 모형이다.
각 시험 독스트링에 변이(실제로 깨뜨려 빨개지는 것을 확인)와 픽스처가 재현하는 실제 상태를 적었다.
"""
import datetime
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
import sido_zones as SZ  # noqa: E402
import weekly_moves as WM  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

DOM = r"""
const __els={};
function __mk(id){
  const attrs={};
  const e={id,style:{},innerHTML:'',textContent:'',hidden:false,disabled:false,title:'',dataset:{},value:'',
    classList:{s:new Set(),add(c){this.s.add(c)},remove(c){this.s.delete(c)},contains(c){return this.s.has(c)},
      toggle(c,on){if(on===undefined)on=!this.s.has(c);if(on)this.s.add(c);else this.s.delete(c);return on;}},
    setAttribute(k,v){attrs[k]=String(v)},getAttribute(k){return k in attrs?attrs[k]:null},removeAttribute(k){delete attrs[k]},
    hasAttribute(k){return k in attrs},insertAdjacentHTML(p,h){this.innerHTML+=h},querySelector(){return null},
    querySelectorAll(){return []},scrollIntoView(){},addEventListener(){}};
  return e;
}
const document={getElementById(id){return __els[id]||(__els[id]=__mk(id));},querySelector(){return null},
  querySelectorAll(){return []},createElement(){return __mk('x')},head:{appendChild(){}},documentElement:{}};
const window=globalThis; window.scrollTo=()=>{};
const __TR=[]; function track(e,p){__TR.push([e,p]);}
"""


def _fn(src, name):
    """src 에서 function name(…){…} 를 중괄호 짝으로 떼어 낸다."""
    a = src.find('function %s(' % name)
    assert a >= 0, '%s 를 찾지 못했다' % name
    i, depth = src.index('{', a), 0
    for j in range(i, len(src)):
        if src[j] == '{':
            depth += 1
        elif src[j] == '}':
            depth -= 1
            if depth == 0:
                return src[a:j + 1]
    raise AssertionError(name)


def _wk_block(app):
    m = re.search(r'// <wk-release>[^\n]*\n(.*?)// </wk-release>', app, re.S)
    assert m
    return m.group(1)


def _node(js):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        p = subprocess.run(['node', path], capture_output=True, timeout=60)
    finally:
        os.remove(path)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def _stats_js(body, pre=''):
    """DOM 모형 + 홈 전역 모형 + home-stats.js 전체 + body. body 는 OUT 을 채운다(약속을 기다리면 await 를 써도 된다)."""
    files = dict(HS.home_files())
    app = files['home-app.js']
    return (DOM + _wk_block(app) + '\n'
            'var ADV={}, STATS={}, statsInited=true, statsMode="market", curView="stats";\n'
            'const __NAV=[]; function statsNav(h,r){__NAV.push([h,!!r]);}\n'
            'function statsHashOf(m){return "#stats-"+m;}\n'
            'function afterLayout(){}\n'
            'function needChart(){return false;}\n'
            'function loadChart(){return Promise.resolve();}\n'
            + pre + '\n' + files['home-stats.js'] + '\n'
            ';(async function(){ let OUT={};\n' + body + '\n process.stdout.write(JSON.stringify(OUT)); })()'
            '.catch(e=>{console.error(e&&e.stack||e);process.exit(1);});\n')


def _load(name):
    return json.loads(io.open(os.path.join(ROOT, name), encoding='utf-8').read())


# ── #42·#48 통계 데이터 재요청 ────────────────────────────────────────────────
def test_reentry_after_trend_failure_requests_the_trend_again():
    """home-stats.js 는 받고 data-trend.json 만 실패한 뒤 다시 들어오면(statsOpen 재호출) trend 를 다시 요청하고 그린다.
    투자지표도 입력이 오기 전엔 그리지 않고 온 뒤에 그린다(TypeError 로 setStatsMode 가 끊기지 않는다).

    변이(실제로 확인): statsOpen 첫머리의 loadFullData() 대기를 빼면(옛 코드) 두 번째 진입의 요청 수가 1 로 남아 빨개진다.
          setStatsMode 의 advReady 가드를 빼면 permits 없는 renderAdvPermits 가 던져 빨개진다.
    픽스처: 첫 trend 요청만 실패(망이 흔들린 경우)하고 두 번째는 성공 — 리뷰 재현(t1_trend_fail.js)과 같은 순서.
    """
    o = _node(_stats_js(r"""
let calls=0; const R=[];
loadFullData=function(){ calls++; if(calls===1)return Promise.reject(new Error('trend'));
  ADV.permits={regions:[]}; ADV.occupancy={regions:[]}; return Promise.resolve(); };
ensureBasicStats=()=>Promise.resolve();
renderReleaseInfo=()=>R.push('rel'); renderWeekSec=()=>R.push('week'); renderMonthSec=()=>R.push('month');
renderBubbleSec=()=>R.push('bubble'); initStats=()=>R.push('init');
renderAdvPermits=()=>{ if(!ADV.permits)throw new TypeError('regions'); R.push('permits'); };
renderAdvOcc=()=>R.push('occ');
await statsOpen(); OUT.first={calls, inited:statsInited, drawn:R.slice()};
statsInited=true; await statsOpen(); OUT.second={calls, drawn:R.slice()};
""", pre='function loadFullData(){} function ensureBasicStats(){}'))
    assert o['first'] == {'calls': 1, 'inited': False, 'drawn': []}, o['first']
    assert o['second']['calls'] == 2 and o['second']['drawn'][:3] == ['rel', 'week', 'month'], o['second']
    o = _node(_stats_js(r"""
let calls=0; const R=[]; let resolve;
loadFullData=function(){ calls++; return new Promise(r=>{resolve=()=>{ADV.permits={regions:[]};ADV.occupancy={regions:[]};r();};}); };
renderAdvPermits=()=>{ if(!ADV.permits)throw new TypeError('regions'); R.push('permits'); };
renderAdvOcc=()=>R.push('occ'); drawPermitChart=()=>R.push('pchart'); drawOccChart=()=>R.push('ochart');
setStatsMode('adv'); OUT.before={calls, drawn:R.slice(), nav:__NAV.slice()};
resolve(); await new Promise(r=>setTimeout(r,0)); OUT.after={drawn:R.slice()};
""", pre='function loadFullData(){}'))
    assert o['before'] == {'calls': 1, 'drawn': [], 'nav': [['#stats-adv', False]]}, o['before']
    assert o['after']['drawn'][:2] == ['permits', 'occ'], o['after']


# ── #52 누르지 않은 전환은 세지 않는다 ────────────────────────────────────────
def test_tab_events_count_clicks_only():
    """stats_mode·market_tab·adv_tab 은 사람이 누른 전환(push!==false)만 보낸다 — 착지·뒤로 가기(applyHash 가 false 로
    부른다)·renderAdvAll 안의 setAdvTab('occ',false) 는 세지 않는다.

    변이(실제로 확인): setStatsMode 의 track 을 push 검사 밖으로 되돌리면(옛 코드) 해시 복원 호출에서 stats_mode 가 나가
          빨개진다. setMarketTab·setAdvTab 도 같다.
    픽스처: 블로그 링크 착지(/#stats-market) → applyHash 가 부르는 모양(false) 세 번, 그다음 사람이 누른 세 번.
    """
    o = _node(_stats_js(r"""
setStatsMode('market',false); setMarketTab('week',false); setAdvTab('permit',false);
OUT.hash=__TR.map(x=>x[0]);
setStatsMode('basic'); setMarketTab('month'); setAdvTab('permit');
OUT.click=__TR.map(x=>x[0]);
"""))
    assert o['hash'] == [], o['hash']
    assert o['click'] == ['stats_mode', 'market_tab', 'adv_tab'], o['click']


# ── #50·#105 리드타임 곡선 ────────────────────────────────────────────────────
def test_leadtime_curve_peaks_are_the_canonical_analysis():
    """리드타임 화면의 봉우리(최강 시차)는 곡선에서 찾고, 그 값이 정본 분석(cycle_analysis.json leadtime)·
    sido_zones.START_DONE_MONTHS_* 와 같다. 설명문에 개월 수를 손으로 적지 않는다.

    변이(실제로 확인): LEADTIME 을 옛 곡선(과거 봉우리 27개월 0.959)으로 되돌리면 빨개진다. src-note 에 '과거 약 28개월'을
          손으로 다시 적으면 마지막 단정이 빨개진다.
    픽스처: 저장소의 home-stats.js 와 tools/data/cycle_analysis.json(사이클 재산정 때만 바뀐다 — 매 배치가 아니므로 게이트가
            데이터에 묶이지 않는다).
    """
    src = dict(HS.home_files())['home-stats.js']
    L = json.loads(re.search(r'^const LEADTIME=(\{.*?\});$', src, re.M).group(1))
    lt = _load(os.path.join('tools', 'data', 'cycle_analysis.json'))['leadtime']

    def peak(a):
        i = max((i for i, v in enumerate(a) if v is not None), key=lambda i: a[i])
        return L['lags'][i], a[i]
    assert peak(L['old']) == (lt['old_months'], lt['old_r']) and lt['old_months'] == SZ.START_DONE_MONTHS_OLD
    assert peak(L['new']) == (lt['new_months'], lt['new_r']) and lt['new_months'] == SZ.START_DONE_MONTHS_NEW
    assert 'peak_old' not in L and 'peak_new' not in L, '봉우리를 곡선과 따로 박았다'
    body = _fn(src, 'drawLeadtime')
    assert not re.search(r'약 \d+개월', body), '리드타임 설명문에 개월 수가 박혀 있다'


# ── #104 시도 → 시군구 ────────────────────────────────────────────────────────
def test_sgg_choices_fold_into_judgement_units():
    """통계 탭 추이의 시도 목록(판정 단위) 각 지역에서 고를 수 있는 시군구가 파이썬 정본(weekly_moves.zone_names —
    시도 리포트 표)과 같다. 전남광주를 고르면 광주 5구·전남 6시가 나온다.

    변이(실제로 확인): sggOfSido 를 옛 `sidoOf(c)===sido` 로 되돌리면 전남광주가 0곳이 되어 빨개진다.
    픽스처: 저장소 data-trend.json 의 주간·월간(목록에 '전남광주'만 있고 '광주'·'전남'은 없다 — 2026-09-10 통합 이후 실제 모양).
            값이 하나도 없는 시군구는 홈이 세우지 않으므로(has) 파이썬 쪽도 같은 기준으로 거른다.
    """
    trend = _load('data-trend.json')['ADV']
    got = _node(_stats_js('OUT={};for(const k of ["weekly","monthly"]){const W=ADV_T[k];OUT[k]={};'
                          'for(const z of W.regions)OUT[k][z]=sggOfSido(W,z);}\nOUT.names=Object.keys(SGG_QNAME);',
                          pre='const ADV_T=%s;' % json.dumps({k: trend[k] for k in ('weekly', 'monthly')},
                                                             ensure_ascii=False)))
    names = {c: c for c in got['names']}
    merged = [z for z in trend['weekly']['regions'] if z not in SZ.AGG and z not in WM.SGG_PREFIX.values()]
    assert merged, '통합 판정 단위가 없는 데이터 — 이 시험이 헛돈다'
    for k in ('weekly', 'monthly'):
        W = trend[k]
        S = W['sgg']

        def has(c):
            i = S['codes'].index(c)
            return any((r.get(f) or [None] * (i + 1))[i] is not None for r in S['rows'] for f in ('ma', 'je', 'wo')
                       if len(r.get(f) or []) > i)
        for z in W['regions']:
            if z in SZ.AGG:
                continue
            want = [c for c in S['codes'] if c in WM.zone_names(S['codes'], names, z) and has(c)]
            assert got[k][z] == want, (k, z, got[k][z][:5], want[:5])
        for z in merged:
            assert got[k][z], '%s %s 의 시군구가 0곳이다' % (k, z)


# ── #55 월간 다음 발표 ────────────────────────────────────────────────────────
H2026 = ['2026-01-01', '2026-02-16', '2026-02-17', '2026-02-18', '2026-03-01', '2026-03-02', '2026-05-05',
         '2026-05-25', '2026-06-03', '2026-06-06', '2026-08-15', '2026-08-17', '2026-09-24', '2026-09-25',
         '2026-09-26', '2026-10-03', '2026-10-05', '2026-10-09', '2026-12-25']


def test_monthly_next_release_waits_for_this_months_moved_date():
    """이번 달 15일이 주말·휴일로 밀린 달에는, 밀린 발표일 12시(KST)가 지나야 다음 달로 넘어간다.

    변이(실제로 확인): _next15 를 옛 판정(달력상 15일 12시)으로 되돌리면 8/16·8/18 오전·11/16 오전 사례가 빨개진다.
    픽스처: 2026 공휴일 — 8/15(토·광복절)·8/17(대체공휴일) → 8월 발표 8/18(화), 11/15(일) → 11/16(월).
            기대값은 파이썬 weekly_release.biz_day 로 센다.
    """
    cases = [(8, 15, 10), (8, 16, 10), (8, 18, 10), (8, 18, 13), (11, 16, 10), (11, 16, 13), (12, 31, 23)]
    ms = [int(datetime.datetime(2026, m, d, h, tzinfo=datetime.timezone(datetime.timedelta(hours=9))).timestamp() * 1000)
          for m, d, h in cases]
    got = _node(_stats_js('_HOLIDAYS=new Set(%s);OUT.r=%s.map(t=>_iso(_next15(new Date(t))));' % (json.dumps(H2026), json.dumps(ms))))
    want = []
    for m, d, h in cases:
        r = WR.biz_day(datetime.date(2026, m, 15), H2026)
        today = datetime.date(2026, m, d)
        if today > r or (today == r and h >= 12):
            y2, m2 = (2027, 1) if m == 12 else (2026, m + 1)
            r = WR.biz_day(datetime.date(y2, m2, 15), H2026)
        want.append(r.isoformat())
    assert got['r'] == want, list(zip(cases, got['r'], want))
    assert got['r'][1] == '2026-08-18' and got['r'][4] == '2026-11-16'


# ── #56 버블 요약 개수 ────────────────────────────────────────────────────────
def test_bubble_summary_counts_provinces_only():
    """버블밴드 요약 'N개 지역'은 집계(전국·수도권·지방)를 빼고 센다 — 시도 수를 넘지 않는다.

    변이(실제로 확인): 루프의 `one`(집계면 0)을 1 로 되돌리면 금리를 아주 낮춘 사례가 시도 수보다 커져 빨개진다.
    픽스처: 저장소 data-trend.json 의 ADV.bubble 과 data-rest.json 의 전세가율, 대출금리만 0.01%(모든 지역이 매수 신호권).
    """
    trend, rest = _load('data-trend.json'), _load('data-rest.json')
    B = trend['ADV']['bubble']
    B['loan'] = dict(B['loan'], v=0.01)
    got = _node(_stats_js('ADV.bubble=%s;STATS["전세가율"]=%s;renderBubbleSec();'
                          'OUT.sum=document.getElementById("bubble-wrap").innerHTML.split("</p>")[0];'
                          % (json.dumps(B, ensure_ascii=False), json.dumps(rest['STATS']['전세가율'], ensure_ascii=False))))
    n = int(re.search(r'(\d+)개 지역', got['sum']).group(1))
    regs = [r for r in (B.get('regions') or list(B['conv'])) if r not in SZ.AGG]
    assert n == len([r for r in regs if B['conv'].get(r) is not None]) and n <= len(SZ.ORDER), (n, got['sum'])


# ── #59 보조선 정점·바닥 ─────────────────────────────────────────────────────
def test_aux_peak_lines_sit_on_the_data_peak():
    """'정점'·'바닥' 보조선은 그리는 계열·지역 원자료의 그 구간 최댓값·최솟값 달에 선다.

    변이(실제로 확인): AUXLINES 의 매매지수 정점을 옛 손 날짜({y:2021,m:9})로 되돌리면 빨개진다(원자료 정점은 2021.10).
    픽스처: 저장소 data-rest.json 의 매매지수·전세지수·금리 — 전국·서울, 각 보조선 구간.
    """
    rest = _load('data-rest.json')['STATS']
    src = dict(HS.home_files())['home-stats.js']
    got = _node(_stats_js(r"""
OUT={};
for(const ds of ['매매지수','전세지수','금리']){
  const D=S_[ds]; const labels=D.dates.map(d=>parseDate(d).label);
  for(const reg of Object.keys(D.series).filter(r=>['전국','서울','CD(91일)'].includes(r))){
    const vals=D.series[reg];
    OUT[ds+'|'+reg]=(AUXLINES[ds]||[]).filter(l=>l.find).map(l=>[l.find,l.from,l.to,labels[auxPos(l,labels,vals)]]);
  }
}
""", pre='const S_=%s;' % json.dumps({k: rest[k] for k in ('매매지수', '전세지수', '금리')}, ensure_ascii=False)))
    assert got and all(got.values()), got
    lab = {}
    for key, lines in got.items():
        ds, reg = key.split('|')
        D = rest[ds]
        for find, lo, hi, at in lines:
            pts = [(d, v) for d, v in zip(D['dates'], D['series'][reg]) if v is not None and lo <= d[:7] <= hi]
            pick = (max if find == 'max' else min)(pts, key=lambda x: x[1])
            assert at == pick[0][:7], (key, find, at, pick)
            lab[key] = at
    assert '{y:2021,m:9,t:\'2021 정점\'' not in src


# ── #54 밀기 안내 ────────────────────────────────────────────────────────────
def test_swipe_hint_is_judged_when_visible():
    """지도 '옆으로 밀어 전체 보기' 안내는 숨은 상태(폭 0)에서 판정하지 않고, 월간 탭을 열 때 다시 판정한다.

    변이(실제로 확인): setMarketTab 의 syncSwipe(t) 호출을 빼면 월간 탭을 연 뒤에도 안내가 숨은 채라 빨개진다.
    픽스처: 375px 실측 모양 — 월간 지도 상자 clientWidth 0(숨김)으로 그려진 뒤, 탭을 열면 scrollWidth 472 > clientWidth 339.
    """
    got = _node(_stats_js(r"""
const box={clientWidth:0,scrollWidth:0}, sw={hidden:true};
const m=document.getElementById(TREND.month.map); m.querySelector=q=>q==='.map-scroll'?box:(q==='.map-swipe'?sw:null);
syncSwipe('month'); OUT.hiddenWhileHidden=sw.hidden;
box.clientWidth=339; box.scrollWidth=472; setMarketTab('month',false); OUT.afterOpen=sw.hidden;
box.clientWidth=900; syncSwipe('month'); OUT.wide=sw.hidden;
"""))
    assert got == {'hiddenWhileHidden': True, 'afterOpen': False, 'wide': True}, got


# ── #53 차트 라이브러리 실패 ──────────────────────────────────────────────────
def test_basic_stats_table_draws_without_the_chart_library():
    """차트 라이브러리를 못 받아도 기본통계 표·메타·출처는 그리고, 출처 줄에 그래프 실패 안내를 단다.

    변이(실제로 확인): drawStat 을 옛 모양(첫 줄 `if(needChart(()=>drawStat()))return;`)으로 되돌리면 표가 비어 빨개진다.
    픽스처: /chart-4.4.1.umd.js 요청이 실패한 첫 방문(리뷰 t5_nochart.js) — needChart 는 늘 '기다림', loadChart 는 거부.
    """
    rest = _load('data-rest.json')['STATS']
    got = _node(_stats_js(r"""
ST.ds='매매지수'; ST.reg='전국'; STATS['매매지수']=S_;
let tbl=0; buildTable=()=>{tbl++;}; buildMatrix=()=>{};
drawStat(); await new Promise(r=>setTimeout(r,0));
OUT={tbl, meta:document.getElementById('meta-bar').innerHTML.length>0,
  note:document.getElementById('src-note').innerHTML};
""", pre='const S_=%s;' % json.dumps(rest['매매지수'], ensure_ascii=False)).replace(
        'function needChart(){return false;}', 'function needChart(){return true;}').replace(
        'function loadChart(){return Promise.resolve();}', 'function loadChart(){return Promise.reject(new Error("x"));}'))
    assert got['tbl'] == 1 and got['meta'], got
    assert '그래프를 불러오지 못했습니다' in got['note'], got['note']


# ── #43 data-core 없이 부팅 ──────────────────────────────────────────────────
def test_boot_renders_survive_a_missing_data_core():
    """data-core.js 가 오지 않아(ADV 없음) 지도 그리기 두 함수가 불려도 던지지 않는다 — 부팅의 라우팅(대결·해시)이 돈다.

    변이(실제로 확인): renderHeroMap 의 try 가드를 옛 `const S=ADV.weekly&&…` 로 되돌리거나 renderSidoMap 의
          `typeof ADV==='undefined'` 분기를 빼면 ReferenceError 로 빨개진다.
    픽스처: data-core.js 요청이 실패한 착지(리뷰 t2_core_fail.js) — ADV 는 선언조차 없다. sido-geo.js 도 없다.
    """
    app = dict(HS.home_files())['home-app.js']
    js = (DOM + 'const NATION_TILE={};function mapColor(){}\nvar TB_VIEW="map";\n'
          + _fn(app, 'renderHeroMap') + '\n' + _fn(app, 'renderSidoMap') + '\n'
          'let OUT={};try{renderHeroMap();renderSidoMap();OUT.ok=true;}catch(e){OUT.err=String(e);}\n'
          'process.stdout.write(JSON.stringify(OUT));')
    assert _node(js) == {'ok': True}


# ── #47 홈 탭바 aria-current ─────────────────────────────────────────────────
def test_home_tabbar_marks_the_current_view():
    """홈 탭바도 켠 탭에 aria-current="page" 를 단다(다른 페이지 탭바 site_nav.bottomnav 와 같은 의미).
    처음 마크업의 홈 버튼에도 있고, 버튼 아이콘 svg 는 aria-hidden 이다.

    변이(실제로 확인): showView 의 setAttribute('aria-current','page') 줄을 옛 classList.toggle 만으로 되돌리면 빨개진다.
    픽스처: 실제 showView·viewLoc·chalInURL·chalSearch 와 탭 버튼 네 개(홈·시세 버튼, 지역·사이클 링크) 모형.
    """
    files = dict(HS.home_files())
    app = files['home-app.js']
    js = (DOM + 'var PV_SENT=false,PV_AFTER=null,statsInited=true,curView=null,statsMode="market";\n'
          'const vHome={style:{}},vStats={style:{}},vTest={style:{}};document.body={classList:{toggle(){}}};\n'
          'const location={href:"https://x/",search:"",hash:"",pathname:"/",origin:"https://x"};\n'
          'const history={pushState(){},replaceState(){}};function statsHashOf(){return "#stats-market-week";}\n'
          'const btns=[["home"],[null],["stats"],[null]].map(([v],i)=>{const b=__mk("b"+i);if(v)b.dataset.view=v;return b;});\n'
          'document.querySelectorAll=q=>q===".nav-btn"?btns:[];\n'
          + '\n'.join(_fn(app, n) for n in ('viewLoc', 'showView', 'chalInURL', 'chalSearch')) + '\n'
          'const OUT={};showView("stats");OUT.stats=btns.map(b=>b.getAttribute("aria-current"));\n'
          'showView("test");OUT.test=btns.map(b=>b.getAttribute("aria-current"));\n'
          'process.stdout.write(JSON.stringify(OUT));')
    got = _node(js)
    assert got['stats'] == [None, None, 'page', None], got
    assert got['test'] == ['page', None, None, None], got
    nav = re.search(r'<nav class="bottomnav">(.*?)</nav>', files['index.html'], re.S).group(1)
    assert re.search(r'<button class="nav-btn on" data-view="home" aria-current="page">', nav)
    for b in re.findall(r'<button[^>]*>\s*<svg[^>]*>', nav):
        assert 'aria-hidden="true"' in b, b



# ── 통합 검토: 재진입 없이 모드 탭으로 다시 열기(#42 잔여) ─────────────────────────
def test_mode_tab_reopens_stats_after_a_failed_first_open():
    """첫 진입(statsOpen)이 data-trend 를 못 받아 statsInited 가 풀린 뒤, 화면을 떠나지 않고 모드 탭(투자지표)을 누르면
    statsOpen 을 다시 돌려 시장동향(주간·월간)까지 그린다. 예전엔 투자지표 분기만 데이터를 다시 받아 그 화면만 그리고,
    loadData 성공이 '불러오지 못했습니다' 안내를 숨겨 시장동향·기본통계가 안내 없이 빈 채로 남았다(통합 검토 재현:
    L3 시장동향 {weekMap:0, weekTbl:0, monthTbl:0}).

    변이(실제로 확인): setStatsMode 의 `if(curView==='stats'&&!statsInited){…statsOpen();}` 줄을 지우면 둘째 기록에
          week·month 가 없어 빨개진다.
    픽스처: 첫 trend 요청만 실패하고 다음은 성공(망이 흔들린 경우) — test_reentry_after_trend_failure 와 같은 순서.
    """
    o = _node(_stats_js(r"""
let calls=0; const R=[];
loadFullData=function(){ calls++; if(calls===1)return Promise.reject(new Error('trend'));
  ADV.permits={regions:[]}; ADV.occupancy={regions:[]}; return Promise.resolve(); };
ensureBasicStats=()=>Promise.resolve();
renderReleaseInfo=()=>R.push('rel'); renderWeekSec=()=>R.push('week'); renderMonthSec=()=>R.push('month');
renderBubbleSec=()=>R.push('bubble'); initStats=()=>R.push('init');
renderAdvPermits=()=>R.push('permits'); renderAdvOcc=()=>R.push('occ'); drawPermitChart=()=>{}; drawOccChart=()=>{};
await statsOpen(); OUT.first={inited:statsInited};
setStatsMode('adv');
for(let i=0;i<5;i++) await new Promise(r=>setTimeout(r,0));
OUT.second={inited:statsInited, drawn:R.slice()};
""", pre='function loadFullData(){} function ensureBasicStats(){}'))
    assert o['first'] == {'inited': False}, o
    assert o['second']['inited'] is True and {'week', 'month'} <= set(o['second']['drawn']), o['second']


# ── 통합 검토: 리드타임도 표 먼저(#53 잔여) ─────────────────────────────────────
def test_leadtime_table_draws_without_the_chart_library():
    """차트 라이브러리를 못 받아도 '착공·준공 리드타임'을 고르면 그 표·메타·출처를 그리고 그래프 실패 안내를 단다.
    예전엔 drawLeadtime 첫 줄에서 돌아가, 단추는 리드타임인데 표·메타는 앞 데이터셋(매매 실거래지수 248행)이 남았다
    (통합 검토 재현: chart-4.4.1.umd.js abort).

    변이(실제로 확인): drawLeadtime 첫 줄을 옛 `if(needChart(()=>drawLeadtime()))return;` 로 되돌리면 표 머리가 비어 빨개진다.
    픽스처: needChart 는 늘 '기다림', loadChart 는 거부(첫 방문에서 라이브러리 요청 실패). 앞 데이터셋 표가 남아 있는 상태.
    """
    got = _node(_stats_js(r"""
document.querySelector=(q)=>document.getElementById(q);
document.getElementById('#stat-tbl thead').innerHTML='<tr><th>연월</th><th>매매 실거래지수</th></tr>';
document.getElementById('meta-bar').innerHTML='<span>단위 <b>지수(2017.11=100)</b></span>';
drawLeadtime(); await new Promise(r=>setTimeout(r,0));
OUT={th:document.getElementById('#stat-tbl thead').innerHTML, rows:document.getElementById('#stat-tbl tbody').innerHTML,
  meta:document.getElementById('meta-bar').innerHTML, note:document.getElementById('src-note').innerHTML};
""").replace('function needChart(){return false;}', 'function needChart(){return true;}').replace(
        'function loadChart(){return Promise.resolve();}', 'function loadChart(){return Promise.reject(new Error("x"));}'))
    assert '시차(개월)' in got['th'] and '<tr>' in got['rows'], got
    assert '상관계수' in got['meta'] and '매매 실거래지수' not in got['th'], got
    assert '그래프를 불러오지 못했습니다' in got['note'], got['note']


# ── 통합 검토: data-core 없이 공급 표 단추(#43 잔여) ───────────────────────────
def test_supply_table_buttons_survive_a_missing_data_core():
    """data-core.js 가 오지 않아 ADV·STATS 가 선언조차 없어도, 공급 구역의 '표'·기간 단추가 부르는 tbBuild 는 던지지 않고
    null 을 돌려준다(tbDraw 가 구역을 숨긴다). 예전엔 renderSidoMap 이 지도 단추만 잠가 '표'를 누르면 ReferenceError 였다.

    변이(실제로 확인): tbBuild 의 `typeof ADV==='undefined'` 가드를 지우면 ReferenceError 로 빨개진다.
    픽스처: data-core.js 요청이 실패한 착지(통합 검토 fr_s15) — ADV·STATS 선언 없음.
    """
    app = dict(HS.home_files())['home-app.js']
    js = ('var TB_BCACHE=null;\n' + _fn(app, 'tbBuild') + '\n'
          'let OUT={};try{OUT.b=tbBuild();}catch(e){OUT.err=String(e);}\n'
          'process.stdout.write(JSON.stringify(OUT));')
    assert _node(js) == {'b': None}
