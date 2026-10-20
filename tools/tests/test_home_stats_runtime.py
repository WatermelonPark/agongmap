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
            'var ADV={}, STATS={}, statsInited=true, statsMode="market", curView="stats", TR_OPEN={week:null,month:null};\n'
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
    픽스처: 저장소 data-trend.json 의 ADV.bubble 에 data-rest.json 전세가율을 split_data 와 같은 함수(bubble_payload)로 실은 것,
    대출금리만 0.01%(모든 지역이 매수 신호권).
    """
    import make_indicator_pages as I
    trend, rest = _load('data-trend.json'), _load('data-rest.json')
    B = I.bubble_payload(trend['ADV']['bubble'], rest['STATS']['전세가율'])
    B['loan'] = dict(B['loan'], v=0.01)
    got = _node(_stats_js('ADV.bubble=%s;renderBubbleSec();'
                          'OUT.sum=document.getElementById("bubble-wrap").innerHTML.split("</p>")[0];'
                          % json.dumps(B, ensure_ascii=False)))
    n = int(re.search(r'(\d+)개 지역', got['sum']).group(1))
    regs = [r for r in (B.get('regions') or list(B['conv'])) if r not in SZ.AGG]
    assert n == len([r for r in regs if B['conv'].get(r) is not None and B['jr'].get(r) is not None]) and n <= len(SZ.ORDER), (n, got['sum'])


# ── H2-6·H2-7·H2-13 버블밴드: 정본 기준월·두 달 배지·범례 위치·여유 반올림 ──────────────────────
def _bubble_fixture(jr_last_partial=True):
    """시도 전부 + 집계 셋. 마지막 달(2026.09)은 서울·경기만 채워진 부분 달(merge_basic 이 새 달을 None 으로 만들고 받은 지역만
    채운 모양 — 전수리뷰 H2-6 재현), 그 앞 달(2026.08)은 모두 찼다."""
    import make_indicator_pages as I
    regs = ['전국', '수도권', '지방'] + list(SZ.ORDER)
    ser = {r: [60.0, 60.0] for r in regs}
    ser['서울'] = [50.0, 52.6]
    ser['경기'] = [60.0, 70.0]
    if jr_last_partial:
        for r in regs:
            if r not in ('서울', '경기'):
                ser[r][1] = None
    J = {'dates': ['2026.08', '2026.09'], 'series': ser}
    # 위험선까지 남은 폭: 서울 0.997(두 자리 1.00 → '1%p 미만' 아님), 경기 0.994(0.99 → 근접), 나머지는 넉넉
    conv = {r: 7.0 for r in regs}            # 그 밖: 60 × 7 = 4.2 ~ 8.4, 대출금리 6.0 은 밴드 안·여유 2.4
    conv['서울'] = (6.0 + 0.997) / 2 / 0.5      # 서울 jr 50.0(기준월) → lo=0.5*cv
    conv['경기'] = (6.0 + 0.994) / 2 / 0.6
    B = {'prd': '2026.07', 'loan': {'v': 6.0, 'p': '2026.08'}, 'regions': regs, 'conv': conv}
    return I.bubble_payload(B, J), J


def test_bubble_band_reads_the_site_reference_month_and_says_both_months():
    """버블밴드 전세가율은 사이트 기준월 정본(jeonse_ref_index — /jeonse-ratio/ 과 같은 달)의 값이고, 배지는 전세가율·전환율 달을
    함께 적는다. 범례는 막대 아래 한 줄, 위험선까지 남은 폭은 칩·상세·근접 셈이 같은 두 자리 값을 쓴다.
    재현한 실제 상태: 새 달이 일부 지역만 채워진 회차(전수리뷰 H2-6·#106)에 홈은 서울 52.6%(부분 달)로, /jeonse-ratio/ 은
    직전 완비 달 값으로 월세수익률을 말했고 배지는 '2026년 7월 기준'(전환율 달)만 적었다. 범례 네 줄이 막대 위에 섰다(H2-7).
    위험선까지 0.97%p 인 지역이 칩 '여유 1.0%p'인데 요약은 '1%p 미만'에 셌다(H2-13).
    픽스처: _bubble_fixture — 2026.09 는 서울·경기만 찬 부분 달, 대출금리 6.0, 서울 여유 0.997(→1.00)·경기 0.994(→0.99), 매수 신호권 0.

    변이(실제로 확인): bubble_jeonse 를 지역마다 마지막 비결측 값으로 바꾸면, 배지를 옛 `_ymT(B.prd)+' 기준'` 으로 되돌리면,
    범례를 막대 앞(h 머리)으로 되돌리면, 근접 셈을 원값 `hi-loan<1` 로 되돌리면 빨개진다.
    """
    B, J = _bubble_fixture()
    assert B['jp'] == '2026.08' and B['jr']['서울'] == 50.0, B['jp']
    got = _node(_stats_js('ADV.bubble=%s;renderBubbleSec();'
                          'OUT.html=document.getElementById("bubble-wrap").innerHTML;'
                          'OUT.badge=document.getElementById("bubble-prd").textContent;' % json.dumps(B, ensure_ascii=False)))
    assert got['badge'] == '전세가율 2026년 8월 · 전환율 2026년 7월 기준', got['badge']
    h = got['html']
    assert '전세가율 50% ×' in h and '52.6' not in h, '부분 달 값을 읽었다'
    first_row, legend = h.find('class="bb-row"'), h.find('class="bb-legend"')
    assert 0 <= first_row < legend, '범례가 막대 위에 있다'
    assert '<br>' not in h[legend:], '범례가 한 줄이 아니다'
    chips = dict(re.findall(r'data-r="([^"]+)".*?<span class="bb-chip[^"]*">([^<]*)</span>', h))
    assert chips['서울'] == '여유 1.00%p' and chips['경기'] == '여유 0.99%p', (chips['서울'], chips['경기'])
    assert '1개 지역이 위험선까지 1%p 미만' in h.split('</p>')[0], h.split('</p>')[0]
    # 완비 달이 마지막이면 배지는 전환율 달과 다를 때만 둘 — 같으면 한 달만 적는다
    B2, _ = _bubble_fixture(jr_last_partial=False)
    B2['prd'] = B2['jp']
    got2 = _node(_stats_js('ADV.bubble=%s;renderBubbleSec();OUT.badge=document.getElementById("bubble-prd").textContent;'
                           % json.dumps(B2, ensure_ascii=False)))
    assert got2['badge'] == '2026년 9월 기준', got2


def test_permit_and_occupancy_notes_sit_below_the_chart():
    """인허가·입주물량 설명 문단은 그래프·표 아래 한 문장(2026-10-06 '설명·범례는 콘텐츠 아래' — 전수리뷰 H2-7).
    재현한 실제 상태: 375px 에서 인허가 두 문장(62px)·입주물량 한 문장이 그래프 위에 있었다.
    변이(실제로 확인): index.html 에서 #sec-permit 의 .adv-note 를 옛 자리(.adv-regsel 앞)로 옮기면 빨개진다.
    픽스처: 저장소 index.html."""
    html = dict(HS.home_files())['index.html']
    for sec in ('sec-permit', 'sec-occ'):
        a = html.index('id="%s"' % sec)
        body = html[a:html.index('</section>', a)]
        note, chart = body.find('class="adv-note"'), body.find('class="gt-g"')
        assert 0 <= chart < note, sec
        txt = re.search(r'class="adv-note">([^<]*)<', body).group(1)
        assert txt.count('니다.') == 1, (sec, txt)
        if sec == 'sec-permit':
            assert SZ.PERMIT_NATURE in txt, '인허가 성격 문구가 정본(sido_zones.PERMIT_NATURE)과 갈렸다'


# ── H2-9 지역 선택 상자 순서 ─────────────────────────────────────────────────
def test_region_select_follows_the_display_order_then_other_rows():
    """통계 탭 지역 선택은 판정 단위를 목록 표시 정본(sido_zones.DISPLAY_ORDER — ADV.sido.zones 가 그 순서로 온다)으로 세우고,
    그 밖의 원천 권역 행(매매지수의 광역시·지방도·서울 권역)은 뒤에 화면 이름 가나다순으로 모은다.
    재현한 실제 상태(전수리뷰 H2-9): 키로 가나다순을 매겨 '광주·전남'(키 전남광주)이 '인천'과 '전북' 사이에 섰고, 매매지수
    목록은 '경북, 광역시, 대구, 대전, 도심권, …'처럼 시도와 권역 행이 섞였다.
    픽스처: 저장소 data-rest.json 매매지수의 지역 키 전부, ADV.sido.zones 는 DISPLAY_ORDER 순서, ADV.zname 은 DISPLAY_NAME.

    변이(실제로 확인): regSort 의 정렬 기준을 옛 '집계(REG_AGG)만 앞·나머지 키 가나다'로 되돌리면(ord=REG_AGG) 빨개진다.
    """
    keys = list(_load('data-rest.json')['STATS']['매매지수']['series'])
    model = [k for k in keys if k in SZ.DISPLAY_ORDER]
    other = [k for k in keys if k not in SZ.DISPLAY_ORDER]
    assert model and other, '매매지수에 판정 단위와 권역 행이 둘 다 있어야 이 시험이 뜻이 있다'
    zones = [{'z': z} for z in SZ.DISPLAY_ORDER]
    got = _node(_stats_js('ADV.sido={zones:%s};ADV.zname=%s;OUT.list=regSort(%s);'
                          % (json.dumps(zones), json.dumps(SZ.DISPLAY_NAME, ensure_ascii=False),
                             json.dumps(list(reversed(keys)), ensure_ascii=False)),
                          pre='function zn(r){return (ADV.zname||{})[r]||r;}'))
    want_head = [z for z in SZ.DISPLAY_ORDER if z in keys]
    assert got['list'][:len(want_head)] == want_head, got['list']
    tail = got['list'][len(want_head):]
    assert sorted(tail) == sorted(other) and len(tail) == len(other)
    collator = _node('process.stdout.write(JSON.stringify(%s.sort((a,b)=>a.localeCompare(b,"ko"))));'
                     % json.dumps(other, ensure_ascii=False))
    assert tail == collator, tail


# ── H2-15 규모별 진입·이탈의 보기 ───────────────────────────────────────────
def test_size_dataset_switches_view_quietly_and_restores_it():
    """기본통계에서 규모별(표 전용)을 고르면 표 보기로 **조용히** 바꾸고(stats_gt 를 보내지 않는다), 다른 계열로 나가면 들어오기 전
    보기로 되돌린다. 재현한 실제 상태(전수리뷰 H2-15, Playwright): 그래프(gm-g)로 보던 중 규모별 → 매매지수로 돌아오면 'gsec gm-t'
    (표)에 머물렀고, 규모별을 누를 때마다 stats_gt{section:basicmain, view:t} 가 사람 누름처럼 쌓였다.
    픽스처: 계열 단추 셋(매매지수·규모별·착공)의 클릭 처리기를 실제 initStats 로 단다. 그리기 함수는 모형이다.

    변이(실제로 확인): 규모별 진입을 옛 `gtSet('basicmain','t')`(silent 없음)로 되돌리면 stats_gt 가 쌓여, 이탈 때 되돌리기 줄을
    빼면 표에 머물러 빨개진다.
    """
    got = _node(_stats_js(r"""
STATS={'매매지수':{series:{}},'착공':{series:{}},'규모별':{series:{},regions:[]}};
const btns={};
const seg=document.getElementById('ds-seg');
seg.querySelectorAll=()=>Object.keys(STATS).map(k=>{const b=btns[k]||(btns[k]=__mk('b-'+k));b.dataset.ds=k;
  b.addEventListener=(e,f)=>{b.click=f;};return b;});
document.getElementById('reg-sel').parentElement=__mk('p');
fillRegions=()=>{};renderAux=()=>{};drawStat=()=>{};drawLeadtime=()=>{};
const sec=document.getElementById('sec-basicmain'); sec.classList.add('gm-g'); sec.classList.add('gsec');
initStats();
const view=()=>sec.classList.contains('gm-t')?'t':(sec.classList.contains('gm-g')?'g':'?');
__TR.length=0;
btns['규모별'].click(); OUT.inSize=view();
btns['규모별'].click(); OUT.again=view();
btns['매매지수'].click(); OUT.back=view();
OUT.gt=__TR.filter(t=>t[0]==='stats_gt').length;
// 표로 보던 사람은 표로 돌아온다
sec.classList.remove('gm-g'); sec.classList.add('gm-t');
btns['규모별'].click(); btns['착공'].click(); OUT.backT=view();
"""))
    assert got == {'inSize': 't', 'again': 't', 'back': 'g', 'gt': 0, 'backT': 't'}, got


# ── H2 overflow: 기간 단추 95% 규칙·입주 추정 분기의 '오늘'·옛 시군구 파일 ─────────────────────
def test_period_button_kst_quarter_and_stale_sgg_file():
    """① 시장동향 기간 단추: 행이 기간의 95~100% 면 단추가 보이고, 그 단추를 고른 채 그려도 '전체'로 바뀌지 않는다.
    ② 입주물량 추정 분기(occFut)는 한국 시간으로 센다 — UTC 12/31 15:30 은 한국 1/1 00:30 이라 새해 1분기는 '미래'가 아니다.
    ③ data-sgg.json 이 지금 것보다 옛 주(HTTP 캐시)면 시군구 행을 덮지 않는다.
    재현한 실제 상태(전수리뷰 H2 overflow 세 건): 보이는 '3년'을 눌러도 '전체'로 바뀜(have 150 < 156), 기기 시간대로 분기를 셈,
    옛 파일이 새 주 행을 되돌림. 픽스처: 주간 150행, 고정 시각 2030-12-31T15:30Z, 최신 2031-01-13 대 옛 파일 2031-01-06.

    변이(실제로 확인): renderTrPeriods 의 되돌림 조건을 옛 `cur[1]>have` 로, occFut 를 기기 시간대(getFullYear·getMonth)로,
    ensureSggHist 의 날짜 비교를 빼면 빨개진다(③은 node 가 TZ=UTC 일 때 ②와 함께).
    """
    got = _node(_stats_js(r"""
ADV.weekly={rows:Array.from({length:150},(_,i)=>({p:'w'+i}))};
TRP.week=2; renderTrPeriods('week'); OUT.kept=TRP.week;
OUT.has3y=document.getElementById('week-period').innerHTML.indexOf('3년')>=0;
const RD=Date; Date.now=()=>RD.UTC(2030,11,31,15,30);
OUT.fut=[occFut('2031Q1'), occFut('2031Q2'), occFut('2030Q4')];
ADV.weekly.sgg={codes:['a'],rows:[{p:'2031-01-13'}]}; ADV.monthly={sgg:{codes:['a'],rows:[{p:'2030-12'}]}};
globalThis.fetch=()=>Promise.resolve({ok:true,json:()=>({ADV:{weekly:{sgg:{codes:['a'],rows:[{p:'2031-01-06'}]}},
  monthly:{sgg:{codes:['a'],rows:[{p:'2030-11'},{p:'2030-12'}]}}}})});
await ensureSggHist();
OUT.wk=ADV.weekly.sgg.rows.map(r=>r.p); OUT.mo=ADV.monthly.sgg.rows.length;
"""))
    assert got['kept'] == 2 and got['has3y'], got
    assert got['fut'] == [False, True, False], got['fut']
    assert got['wk'] == ['2031-01-13'] and got['mo'] == 2, got


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


def test_apartment_build_aux_labels_come_from_the_data():
    """아파트건설 보조선 라벨의 수량·40년차 연도·정점 해는 그 칸의 원자료에서 만든다(전수리뷰 H2-14).
    재현한 실제 상태: '38만 돌파 · 40년차 2032'·'정점 43만 · 40년차 2035'를 글자로 박아, 원천이 옛 해 값을 고치거나 다른 해가
    1995년을 넘으면 선은 1995에 선 채 그래프와 다른 말을 했다. 픽스처: 저장소 data-rest.json 아파트건설(전국) 그대로 한 번,
    1997년 값을 정점보다 크게 바꾼 사본 한 번(정점이 옮겨 가는 경우).

    변이(실제로 확인): 정점 선을 옛 {y:1995,m:12,t:'정점 43만 · 40년차 2035'} 로 되돌리면 사본에서, fmt 의 +40 을 박은 연도로 바꾸면
    빨개진다.
    """
    D = _load('data-rest.json')['STATS']['아파트건설']
    reg = '전국'
    moved = json.loads(json.dumps(D))
    i97 = moved['dates'].index(next(d for d in moved['dates'] if d.startswith('1997')))
    moved['series'][reg][i97] = max(v for v in moved['series'][reg] if v is not None) + 20000
    for data in (D, moved):
        got = _node(_stats_js(r"""
const labels=S_.dates.map(d=>parseDate(d).label), vals=S_.series['전국'];
OUT.t=AUXLINES['아파트건설'].map(l=>{const p=auxPos(l,labels,vals);return p<0?null:[labels[p],auxText(l,labels[p],vals[p])];});
""", pre='const S_=%s;' % json.dumps(data, ensure_ascii=False)))
        pts = [(d[:4], v) for d, v in zip(data['dates'], data['series'][reg]) if v is not None and '1980' <= d[:4] <= '2005']
        py, pv = max(pts, key=lambda x: x[1])
        assert got['t'][-1] == [py, '정점 %d만 · 40년차 %d' % (round(pv / 1e4), int(py) + 40)], got['t']
        v92 = dict(pts)['1992']
        assert got['t'][1] == ['1992', '%d만 돌파 · 40년차 %d' % (v92 // 10000, 1992 + 40)], got['t']
    src = dict(HS.home_files())['home-stats.js']
    assert not re.search(r"t:'[^']*\d+만", src), '보조선 이름에 손으로 옮긴 수량이 있다'


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


# ── H2-4 시장동향·투자지표 그래프의 라이브러리 실패 ─────────────────────────────────
def test_market_and_investor_charts_say_when_the_library_fails():
    """차트 라이브러리를 못 받으면 시장동향(주간·월간)·인허가·입주물량 그래프도 그 그래프 상자 위에 안내와 '다시 시도'를 달고,
    시장동향은 기간 단추·범위 줄을 그린다. 다시 시도는 그 그래프를 다시 그린다(chartRedo).
    재현한 실제 상태(전수리뷰 H2-4, Playwright 로 /chart-4.4.1.umd.js 를 막음): '#stats-adv-occ' 는 빈 캔버스뿐, '#stats-market-week~a7' 은
    기간 단추가 없고 범위 줄이 '변동률(%)'뿐이었고, 유일한 안내는 숨은 기본통계 출처 줄에 있었다.
    픽스처: 저장소 data-trend.json(주간·월간·인허가·입주물량), needChart 는 늘 '기다림', loadChart 는 거부.

    변이(실제로 확인): drawTrendChart 의 needChart 를 옛 자리(함수 첫 줄, 안내 없음)로 되돌리면, drawPermitChart·drawOccChart 에서
    chartFailNote 를 빼면, CHART_FAIL 의 week 자리를 'src-note' 로 바꾸면 빨개진다.
    """
    trend = _load('data-trend.json')['ADV']
    got = _node(_stats_js(r"""
Object.assign(ADV, T_);
['adv-week-reg','adv-week-sgg','adv-month-reg','adv-month-sgg','adv-permit-reg','adv-occ-reg'].forEach(id=>{document.getElementById(id).options=[];});
let redo=[]; drawTrendChart=(k=>{const f=drawTrendChart; return k2=>{redo.push(k2); return f(k2);};})();
drawTrendChart('week'); drawTrendChart('month'); drawPermitChart(); drawOccChart();
await new Promise(r=>setTimeout(r,0));
const g=id=>document.getElementById(id).innerHTML;
OUT={box:['weekChartBox','monthChartBox','permitChartBox','occChartBox'].map(g), src:g('src-note'),
  period:g('week-period'), unit:document.getElementById('week-unit').textContent};
redo=[]; chartRedo('month'); OUT.redo=redo;
""", pre='const T_=%s;' % json.dumps({k: trend[k] for k in ('weekly', 'monthly', 'permits', 'occupancy')}, ensure_ascii=False)
    ).replace('function needChart(){return false;}', 'function needChart(){return true;}').replace(
        'function loadChart(){return Promise.resolve();}', 'function loadChart(){return Promise.reject(new Error("x"));}'))
    for i, b in enumerate(got['box']):
        assert '그래프를 불러오지 못했습니다' in b and 'retry-btn' in b and 'chartRedo(' in b, (i, b)
    assert got['src'] == '', got['src']
    assert '<button' in got['period'] and '~' in got['unit'], got
    assert got['redo'] == ['month'], got['redo']


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


# ── 전수리뷰 A3: 지역을 연 시장동향 주소 ─────────────────────────────────────────
def test_market_hash_keeps_the_opened_region():
    """지도 칸·TOP 10 으로 서울(a7) 그래프를 연 시장동향(#stats-market-week~a7)에서 같은 '주간' 탭을 다시 누르거나 하단
    '시세'를 다시 누르거나(showView 의 같은 화면 정규화 → statsHashOf), 주간 → 월간 → 주간으로 오가도 주소가 '~a7' 을
    잃지 않는다 — 화면은 서울 그래프인데 주소만 '#stats-market-week' 가 되면 새로고침·주소 복사가 다른 화면을 연다.
    표로 보고 있으면 '-t' 까지 싣는다(applyHash 가 같은 보기로 연다).

    변이(실제로 확인): statsHashOf 의 `(c?'~'+c+…:'')` 를 지우면 첫 단정이, setMarketTab 의 statsNav 인자를 옛
          '#stats-market-'+t 로 되돌리면 둘째 단정(월간 → 주간)이 빨개진다.
    픽스처: 실제 statsHashOf(home-app.js)와 setMarketTab(home-stats.js). 주간 탭이 켜져 있고 openTrendRegion 이 서울(a7)을
          연 상태(TR_OPEN.week='a7'), 월간은 연 지역 없음.
    """
    app = dict(HS.home_files())['home-app.js']
    got = _node(_stats_js(r"""
statsHashOf=(function(){ %s; return statsHashOf; })();
document.getElementById('mtab-week').classList.add('on'); TR_OPEN.week='a7';
OUT.same=statsHashOf('market');
setMarketTab('week'); setMarketTab('month'); setMarketTab('week');
OUT.nav=__NAV.slice();
document.getElementById('sec-week').classList.add('gm-t'); OUT.table=statsHashOf('market');
""" % _fn(app, 'statsHashOf')))
    assert got['same'] == '#stats-market-week~a7', got
    assert got['nav'] == [['#stats-market-week~a7', True], ['#stats-market-month', False], ['#stats-market-week~a7', False]], got
    assert got['table'] == '#stats-market-week~a7-t', got


# ── 전수리뷰 H2-10 규모별 표의 빈 끝 달 ─────────────────────────────────────────
def _size_payload():
    """data-size.json 2026-10 모양 — 축 2024.06~2026.07(26달), 매매·전세·월세는 2026.06 까지(2025.03 은 가운데 빈 달),
    전환율(3구간)은 2026.07 까지. 지역은 전국 하나."""
    dates, y, m = [], 2024, 6
    while (y, m) <= (2026, 7):
        dates.append('%d.%02d' % (y, m))
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    price = [None if d in ('2025.03', '2026.07') else [0.1] * 6 for d in dates]
    conv = [[5.0, 5.1, 5.2, None, None, None] for _ in dates]
    series = {'매매': {'전국': price}, '전세': {'전국': list(price)}, '월세': {'전국': list(price)}, '전환율': {'전국': conv}}
    return {'dates': dates, 'sizes': ['40㎡↓', '40~60㎡', '60~85㎡', '85~102㎡', '102~135㎡', '135㎡↑'],
            'conv_sizes': ['60㎡↓', '60~85㎡', '85㎡↑'], 'metrics': ['매매', '전세', '월세', '전환율'], 'regions': ['전국'],
            'unit': '전월 대비 % (전환율은 %)', 'source': '한국부동산원', 'note': '합성', 'series': series}


def test_size_pivot_drops_trailing_months_without_selected_values():
    """규모별 표는 고른 지표·규모 칸이 모두 빈 **끝** 달을 줄·기간 줄에서 뺀다 — 가운데 빈 달은 남긴다(전수리뷰 H2-10).
    기간 창(1년 보기)도 자른 끝에서 잰다.

    변이(각각 실제로 확인): drawSizePivot 의 끝 달 자르기(`while(end>=0&&…)end--;`)를 지우면 매매·전세 표 첫 줄이 빈 '26.7'이고
          기간 줄이 '2026년 7월'까지라 빨개진다. 1년 보기 창을 예전처럼 축 끝(`D.dates.length-ST.years*12`)에서 재면 11줄이 되어
          빨개진다.
    픽스처: 위 _size_payload(실제 상태 — 전환율만 2026.07 을 실은 축).
    """
    app = dict(HS.home_files())['home-app.js']
    pre = '\n'.join(_fn(app, n) for n in ('pv2r', 'pv2', 'pvSign')) + '\nconst SD_=%s;' % json.dumps(
        _size_payload(), ensure_ascii=False)
    got = _node(_stats_js(r"""
const T=document.getElementById('stat-tbl'), TH=document.getElementById('__th'), TB=document.getElementById('__tb');
T.querySelector=s=>s==='thead'?TH:TB;
document.getElementById('size-ctl').innerHTML='x';
STATS['규모별']=SD_; ST.ds='규모별'; ST.reg='전국';
function snap(){ const rows=TB.innerHTML.split('<tr>').slice(1);
  return {n:rows.length, first:(rows[0]||'').replace(/<[^>]+>/g,'|').split('|').filter(Boolean)[0],
    last:(rows[rows.length-1]||'').replace(/<[^>]+>/g,'|').split('|').filter(Boolean)[0],
    mid:rows.some(r=>r.indexOf('>25.3<')>=0),
    range:document.getElementById('prange').innerHTML.replace(/<[^>]+>/g,'')}; }
ST.years=0; SZ.met=new Set(['매매','전세']); SZ.siz=new Set([2]); SZ.desc=true; SZ.tr=false;
drawSizePivot(); OUT.price=snap();
SZ.met=new Set(['전환율']); drawSizePivot(); OUT.conv=snap();
SZ.met=new Set(['매매']); ST.years=1; drawSizePivot(); OUT.year=snap();
""", pre=pre))
    assert got['price']['n'] == 25 and got['price']['first'] == '26.6' and got['price']['mid'], got['price']
    assert got['price']['range'] == '2024년 6월 ~ 2026년 6월 · 25개월', got['price']
    assert got['conv']['n'] == 26 and got['conv']['first'] == '26.7', got['conv']
    assert got['year']['n'] == 12 and got['year']['first'] == '26.6' and got['year']['last'] == '25.7', got['year']


# ── 전수리뷰 A-8 · 대표 결정 2026-10-18 D3: 값이 없는 지역 열 ─────────────────────────────
def test_basic_matrix_skips_a_region_with_no_values():
    """기본통계 PC 표(buildMatrix)는 값이 하나도 없는 지역 열을 세우지 않는다 — 지역 선택(fillRegions)과 같은 규칙. 광주·전남
    주택보급률을 비운 뒤(D3) '·'뿐인 열이 서던 자리다.

    변이(실제로 확인): buildMatrix 의 `&&D.series[r].some(v=>v!=null)` 를 빼면 통합 지역 열이 서서 빨개진다.
    픽스처: data-rest.json 보급률 사본에서 통합 지역(merge_regions.DST)을 전부 비운 상태 — 배치가 이력을 지운 뒤의 모양.
    """
    from merge_regions import DST
    D = _load('data-rest.json')['STATS']['보급률']
    D['series'][DST] = [None] * len(D['dates'])
    got = _node(_stats_js(r"""
ST.ds='보급률'; STATS['보급률']=D_;
const parsed=D_.dates.map(parseDate);
buildMatrix(D_, parsed.map((p,i)=>i), parsed);
OUT.html=document.getElementById('stat-matrix').innerHTML;
""", pre='const D_=%s;' % json.dumps(D, ensure_ascii=False)))
    assert '<th>서울</th>' in got['html'], got['html'][:300]
    assert DST not in got['html'], '값이 없는 지역 열이 섰다'
