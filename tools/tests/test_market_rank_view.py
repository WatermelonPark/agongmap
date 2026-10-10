# -*- coding: utf-8 -*-
"""시세 탭 시장동향(주간·월간)의 보기 넷 — 순위·지도·그래프·표, 기본은 지도(2026-10-10 대표 결정).

재현하는 실제 상태: 10-09 까지 '지도' 보기 한 상자(#week-map)에 날짜 줄 → 상승 TOP 10 → 하락 TOP 10 → 시군구 지도가 함께
들어 있어, 375px 에서는 표 20줄을 지나야 지도가 나왔다(대표 지적 '탑텐이 너무 강하다'). 이제 같은 상자를 순위(gm-r)·지도(gm-m)
로 나눠 보이고, TOP 10 으로 가는 입구(홈 '시군구 상승·하락 TOP 10 보기', /weekly/ '전체 TOP 10 보기'·'TOP 10 →', 블로그 주간 초안의
TOP 10 캡처)는 '#stats-market-<주기>-rank' 로 순위 보기를 바로 연다.
픽스처: 저장소의 index.html·app.css·home-app.js(applyHash)·home-stats.js(gtSet)를 node 합성 DOM 에서 돌린다.

변이(각각 실제로 확인):
  · index.html 에서 기본 눌림(on)을 '순위' 단추로 옮기면, 순위 단추를 빼면 → 단추 시험 빨강.
  · app.css 에서 '.gsec.gm-m .map-rank' 를 지우면(지도 보기에 TOP 10 이 다시 나옴) → 상자 나눔 시험 빨강.
  · gtSet 에서 gm-r 토글을 지우면, 순위로 바꿀 때 trOpenDrop 을 부르지 않으면 → gtSet 시험 빨강.
  · applyHash 정규식에서 '(-rank)?' 를 빼면, 순위 갈래에서 openTrendRegion 에 'r' 을 넘기지 않으면, 그 갈래에서 gtSet 을 따로
    부르면(10-10 코드 리뷰 — 통계 파일을 못 받은 날 빈 화면, 받는 사이 누른 보기를 덮음) → 입구 시험 빨강.
  · openTrendRegion 닫기 갈래에서 view 'r' 을 무시하면, 받는 사이 사람이 고른 보기(GT_SEQ)를 보지 않으면, gtSet 이 사람이 누른
    전환을 세지 않으면, 라우터가 요청한 때의 GT_SEQ 를 넘기지 않으면(통계 파일은 왔는데 데이터가 늦을 때 openTrendRegion 이 늦게
    재면 그사이 누른 '그래프'를 덮는다 — 10-10 브라우저 재현) → 뒤로 가기·순위 입구·라우터 시험, gtSet 시험 빨강.
  · openTrendRegion 이 닫을 때 TR_BACK 대신 'm' 을 쓰면, 열 때 순위(gm-r)를 기억하지 않으면, 그래프가 열린 채 다른 지역으로
    갈 때 TR_BACK 을 덮으면 → 뒤로 가기 시험 빨강(순위에서 연 그래프를 닫으면 지도로 떨어지던 결함).
  · 홈 CTA·/weekly/ CTA·/weekly/ 머리 지도 아래 'TOP 10 →'·캡처 주소를 '#stats-market' 으로 되돌리면 → 입구 링크 시험 빨강.
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_weekly_page as MW  # noqa: E402

ROOT = HS.ROOT


def _files():
    return dict(HS.home_files())


def _fn(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, '%s 를 찾지 못했다' % name
    i, depth = src.index('{', m.end()), 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def _gt_seq_decl(f):
    """home-app.js 의 GT_SEQ 선언(사람이 누른 보기 전환 수 — 순위 입구가 요청한 때 읽는다)."""
    m = re.search(r'^const GT_SEQ=\{[^}]*\};', f['home-app.js'], re.M)
    assert m, 'home-app.js 에 GT_SEQ 선언이 없다'
    return m.group(0)


def _node(js):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8'))


def test_four_buttons_rank_map_graph_table_with_map_pressed():
    html = _files()[HS.HOME]
    for k in ('week', 'month'):
        sec = re.search(r'<section class="adv-sec gsec gm-m" id="sec-%s"[^>]*>(.*?)</section>' % k, html, re.S)
        assert sec, k
        btns = re.findall(r'<button([^>]*)data-v="([a-z])"[^>]*>([^<]+)</button>', sec.group(1))
        assert [(v, t) for _, v, t in btns] == [('r', '순위'), ('m', '지도'), ('g', '그래프'), ('t', '표')], btns
        on = [v for a, v, _ in btns if 'class="on"' in a]
        assert on == ['m'], on                                  # 기본은 지도(섹션 class 도 gm-m)
        assert "onclick=\"gtSet('%s','r')\"" % k in sec.group(1)


def test_rank_and_map_split_the_same_box():
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    rule = re.search(r'([^{}]*\.gsec\.gm-m \.map-rank[^{}]*)\{display:none\}', css)
    assert rule, '지도 보기에서 TOP 10 을 숨기는 규칙이 없다'
    for sel in ('.gsec.gm-r .map-scroll', '.gsec.gm-r .map-suplegend'):
        assert sel in rule.group(1), sel
    assert re.search(r'\.gsec\.gm-r \.gt-g,\.gsec\.gm-r \.gt-t\{display:none\}', css)
    assert re.search(r'\.gsec\.gm-r \.adv-regsel\{display:none\}', css)
    assert '.gsec.gm-r .map-datechip' not in css                # 날짜 줄은 순위·지도 둘 다에 남는다


GT = r'''
%(decl)s
%(fn)s
var drops=[], sent=[], swipe=[], TREND={week:{}};
function trOpenDrop(k){ drops.push(k); } function track(e,p){ sent.push([e,p]); } function syncSwipe(k){ swipe.push(k); }
function cl(){ var s={}; return {toggle:function(c,v){ if(v)s[c]=1; else delete s[c]; },has:function(c){return !!s[c]},list:function(){return Object.keys(s).sort()}}; }
var B=['r','m','g','t'].map(function(v){ var a={}; return {dataset:{v:v},classList:cl(),setAttribute:function(k,x){a[k]=x},get:function(k){return a[k]}}; });
var SEC={classList:cl(),querySelectorAll:function(){return B}};
var document={getElementById:function(id){ return id==='sec-week'?SEC:null; }};
var out=[];
['r','m','r','g'].forEach(function(v){ gtSet('week',v);
  out.push([v,SEC.classList.list(),B.filter(function(b){return b.get('aria-pressed')==='true'}).map(function(b){return b.dataset.v})]); });
gtSet('week','m',true);                               // openTrendRegion 이 바꾼 것(조용히) — 사람이 누른 수에 들지 않는다
process.stdout.write(JSON.stringify({out:out,drops:drops,sent:sent,swipe:swipe,seq:GT_SEQ.week}));
'''


def test_gtset_switches_to_rank_and_drops_an_open_region():
    f = _files()
    got = _node(GT % {'decl': _gt_seq_decl(f), 'fn': _fn(f['home-stats.js'], 'gtSet')})
    assert got['out'] == [['r', ['gm-r'], ['r']], ['m', ['gm-m'], ['m']], ['r', ['gm-r'], ['r']], ['g', ['gm-g'], ['g']]], got['out']
    assert got['drops'] == ['week', 'week', 'week'], got['drops']      # 순위·지도로 바꿀 때 연 지역 그래프를 닫는다
    assert got['swipe'] == ['week', 'week'], got['swipe']              # 밀기 안내는 지도 보기만(사람이 누른 것·조용한 것 하나씩)
    assert [p['view'] for e, p in got['sent'] if e == 'stats_gt'] == ['r', 'm', 'r', 'g']
    assert got['seq'] == 4, got['seq']                                 # 사람이 누른 넷만 센다(순위 입구가 덮지 않게)


BACK = r'''
%(decl)s
%(seq)s
%(fn)s
var TR_OPEN={week:null}, TRSHOW={week:12}, TREND={week:{sel:'wsel'}}, TREND_P=Promise.resolve(), SGG_HIST_READY=true, gts=[];
function trendData(){ return {regions:['서울']}; } function trendTarget(W,c){ return {zone:'',sgg:''}; }
function fillTrendReg(){} function fillSggSel(){} function renderWeekSec(){} function renderMonthSec(){} function afterLayout(){}
function loadFullData(){ return TREND_P; } function ensureSggHist(){ return Promise.resolve(); }
var cls='gm-m', SEL={value:''}, SEC={classList:{contains:function(c){ return c===cls; }},scrollIntoView:function(){}};
var document={getElementById:function(id){ return id==='sec-week'?SEC:SEL; }};
function gtSet(k,v){ gts.push(v); cls='gm-'+v; }
var res={};
(async function(){
  for(const [name,start,steps] of %(cases)s){
    TR_OPEN.week=null; cls=start; gts=[];
    for(const [c,v,race] of steps){
      const p=openTrendRegion('week',c,v,GT_SEQ.week);   // applyHash 처럼 요청한 때의 수를 넘긴다
      if(race)GT_SEQ.week++;                    // 데이터를 받는 사이 사람이 다른 보기를 눌렀다(gtSet 이 세는 수)
      await p;
    }
    res[name]=gts;
  }
  process.stdout.write(JSON.stringify(res));
})();
'''


def test_back_from_a_region_opened_on_the_rank_view_returns_to_rank():
    """순위 표에서 지역을 눌러 그래프를 열고(주소 '~코드') 뒤로 가면(코드 없는 주소 → openTrendRegion(k,null)) 순위로 돌아간다.
    지도에서 열었으면 지도로. 그래프가 열린 채 다른 지역으로 갔다가 닫아도 처음 연 곳으로.
    순위 입구(view 'r')는 데이터가 온 뒤 순위로 바꾸고(연 그래프가 있으면 먼저 닫는다), 받는 사이 사람이 다른 보기를 골랐으면
    덮지 않는다."""
    f = _files()
    src = f['home-stats.js']
    decl = re.search(r'^const TR_BACK=.*$', src, re.M)
    assert decl, 'home-stats.js 에 TR_BACK 선언이 없다'
    n = None
    cases = [['rank', 'gm-r', [['a7', n], [n, n]]], ['map', 'gm-m', [['a7', n], [n, n]]],
             ['rank2', 'gm-r', [['a7', n], ['b11', n], [n, n]]], ['idle', 'gm-r', [[n, n]]],
             ['entry', 'gm-m', [[n, 'r']]], ['entry_open', 'gm-m', [['a7', n], [n, 'r']]],
             ['entry_race', 'gm-g', [[n, 'r', True]]]]
    got = _node(BACK % {'decl': decl.group(0), 'seq': _gt_seq_decl(f), 'fn': _fn(src, 'openTrendRegion'),
                        'cases': json.dumps(cases)})
    assert got['rank'] == ['g', 'r'], got
    assert got['map'] == ['g', 'm'], got
    assert got['rank2'] == ['g', 'g', 'r'], got
    assert got['idle'] == [], got                       # 연 그래프가 없으면 보기를 건드리지 않는다
    assert got['entry'] == ['r'], got                   # 순위 입구
    assert got['entry_open'] == ['g', 'm', 'r'], got    # 연 지역 그래프를 닫고 순위로
    assert got['entry_race'] == [], got                 # 받는 사이 사람이 고른 보기는 덮지 않는다


ROUTER = r'''
%(fn)s
var calls=[], R2C=new Set();
function showView(v){ calls.push(['view',v]); } function setStatsMode(m){ calls.push(['mode',m]); }
function setMarketTab(t){ calls.push(['tab',t]); } function setAdvTab(t){ calls.push(['adv',t]); }
function openTrendRegion(t,c,v,s){ calls.push(['open',t,c,v||null].concat(s===undefined?[]:[s])); return Promise.resolve(); }
var GT_SEQ={week:3,month:5};
function gtSet(t,v,s){ calls.push(['gt',t,v,!!s]); }
function afterLayout(f){ f(); } function startQuiz(){} function backToPick(){}
var history={replaceState:function(a,b,u){ calls.push(['replace',u]); }};
var document={getElementById:function(){ return null; }};
var location={hash:''};
var res={};
(async function(){
  for(const h of %(hashes)s){ calls=[]; location.hash=h; applyHash(); await new Promise(r=>setTimeout(r,0)); res[h]=calls; }
  process.stdout.write(JSON.stringify(res));
})();
'''


def test_rank_entry_hash_opens_the_rank_view_and_keeps_the_old_shapes():
    hs = ['#stats-market-week-rank', '#stats-market-month-rank', '#stats-market-week~a7-t', '#stats-market', '#stats-adv-occ']
    got = _node(ROUTER % {'fn': _fn(_files()['home-app.js'], 'applyHash'), 'hashes': json.dumps(hs)})
    assert got['#stats-market-week-rank'] == [['view', 'stats'], ['mode', 'market'], ['tab', 'week'],
                                              ['open', 'week', None, 'r', 3], ['replace', '#stats-market-week']], \
        got['#stats-market-week-rank']      # 순위는 openTrendRegion 이 데이터가 온 뒤에(요청한 때의 GT_SEQ 와 함께) — gtSet 을 따로 부르지 않는다
    assert ['open', 'month', None, 'r', 5] in got['#stats-market-month-rank']
    assert not [c for h in got for c in got[h] if c[0] == 'gt'], got
    assert got['#stats-market-week~a7-t'][-1] == ['open', 'week', 'a7', 't']          # 옛 모양(지역·표)은 그대로
    assert not [c for c in got['#stats-market'] if c[0] == 'gt']                    # 맨 시장동향은 기본(지도)
    assert ['adv', 'occ'] in got['#stats-adv-occ']


def test_top10_entries_link_the_rank_view():
    html = _files()[HS.HOME]
    cta = re.search(r'<a class="home-cta" href="([^"]+)"[^>]*>시군구 상승·하락 TOP 10 보기</a>', html)
    assert cta and cta.group(1) == '#stats-market-week-rank', cta and cta.group(1)
    src = io.open(os.path.join(ROOT, 'tools', 'make_weekly_page.py'), encoding='utf-8').read()
    assert '<a class="cta" href="/#stats-market-week-rank">전체 TOP 10 보기</a>' in src
    assert '<a class="go" href="/#stats-market-week-rank">TOP 10 →</a>' in src          # 머리 지도 아래 입구
    assert not re.search(r'href="/#stats-market"[^>]*>[^<]*TOP 10', src)                # TOP 10 이라 쓰고 지도로 가는 입구가 없다
    assert set(P.WEEKLY_SHOT_HASH) == set(P.WEEKLY_SHOTS)
    assert P.WEEKLY_SHOT_HASH['top10'] == 'stats-market-week-rank' and P.WEEKLY_SHOT_HASH['map'] == 'stats-market'
    rx = re.search(r"const sm=h\.match\(/(.*?)/\);", _files()['home-app.js']).group(1)
    for h in P.WEEKLY_SHOT_HASH.values():
        assert re.match(rx.replace('\\/', '/'), h), h                              # 캡처 주소를 라우터가 받는다
    assert MW  # /weekly/ 생성기를 함께 불러 둔다(CTA 가 그 파일의 글자다)
