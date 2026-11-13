# -*- coding: utf-8 -*-
"""홈 진입·측정 — 블로그 링크 착지(A1), page_view 한 번(A3), GA 지연 로딩(C8). 2026-09-27 홈 마케팅 검수.

실제 상태(픽스처가 재현하는 것):
  - 09-11·09-17 발행한 주간 블로그 글의 '지도에서 직접 찾아보기'는
    `https://www.agongmap.co.kr/#stats-market?utm_source=naver_blog&utm_medium=social&utm_campaign=weekly_map` 이다.
    '#' 뒤라 쿼리가 비고, 홈 라우터 정규식(끝이 $)이 'stats-market?utm_…' 과 안 맞아 3년 공급 첫 화면에
    떨어졌다(브라우저 실측: 통계 뷰 안 열림). 발행 글은 고치지 않는다(대표 결정) — 사이트가 받아 준다.
  - 부팅 때 gtag config 의 자동 page_view 와 showView 의 수동 page_view 가 겹쳐 홈 한 번 방문에 page_view 가
    두 번 갔다(실측: '/' 2건, '/#stats-market-week' 2건, 홈 탭을 다시 누르면 또 1건).
  - 화면 전환 page_view 의 page_location 이 '/#stats'·'/#test' 였다. GA 는 페이지 경로·쿼리에 해시를 넣지 않아
    홈('/')과 통계·퀴즈가 페이지 경로 보고서에서 한 줄로 합쳐졌다(MEAS-1 권고: '/?view=stats' 처럼 쿼리로 가른다).
  - gtag.js 는 `<script async>` 로 머리에서 바로 받아 첫 화면 지도와 대역을 다퉜다(MOB-10).

방법: index.html <head> 의 인라인 스크립트 전부와 home-app.js 의 track·viewLoc·showView·applyHash(홈 스크립트는
tools/home_src.home_source() 로 읽는다)를 그대로 잘라 node vm 에서 돌린다. location·history·localStorage·
document 는 흉내 내고 DOM 을 만지는 이웃 함수(setStatsMode 등)는 호출 기록만 남긴다. 부팅 순서는 브라우저와
같게 둔다: 머리 스크립트 → (defer) boot 의 applyHash → DOMContentLoaded → requestIdleCallback.
CI 에서는 건너뜀도 실패다(conftest) — node 는 러너에 있다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인했다):
  - index.html 머리의 history.replaceState(해시 속 쿼리 옮기기) 줄을 지우면 → 주소 고치기 시험, 캠페인 시험
  - home-app.js applyHash 의 `.split('?')[0]` 을 지우면 → 머리 없이도 통계가 열리는지 보는 방어 시험
  - gtag('config', …) 의 {send_page_view:false} 를 지우면 → page_view 한 번 시험(2건)
  - showView 의 첫 호출 page_location 을 옛 `location.origin+'/#'+v` 로 되돌리면 → 캠페인 시험(쿼리를 잃는다)
  - 전환 page_location 을 옛 `location.origin+'/#'+v` 로 되돌리면 → 전환 시험·페이지 경로 보고서 시험(홈과 통계가
    한 줄로 합쳐진다). 첫 호출에 view= 를 달지 않고 착지 주소 그대로 보내면 → 부팅 한 번·캠페인·페이지 경로
    보고서 시험
  - viewLoc 의 홈 예외(`if(v!=='home')`)를 빼면 → 부팅 한 번·전환·로더 전 클릭·페이지 경로 보고서 시험('/' 가
    '/?view=home' 이 된다)
  - viewLoc 에서 있던 view= 를 걸러 내는 조건을 빼면 → 페이지 경로 보고서 시험(view= 가 두 번 붙는다)
  - 첫 호출의 착지 주소를 pushState 뒤의 location.href 로 잡으면 → 로더 전 클릭 시험(쿼리가 빠진 '/')
  - showView 의 `if(changed)` 를 빼면 → 같은 화면을 다시 누르는 시험
  - 머리 로더의 `if(!sent())gtag('event','page_view',…)` 를 지우면 → 부팅 실패·모르는 해시 시험(0건)
  - 로더를 DOMContentLoaded 전에 붙이거나(idle() 대신 load() 즉시 호출) 옛 `<script async src=…gtag/js>` 를
    머리에 되살리면 → 지연 로딩 시험
  - load() 의 ga-disable 확인을 지우면 → ga_off 기기 시험(로더를 붙인다)
"""
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402

GA_ID = 'G-3FJNG6G1F3'
SITE = 'https://www.agongmap.co.kr'
# 09-11·09-17 발행본에 실제로 박혀 있는 링크(발행 글은 고치지 않는다)
BLOG_URL = (SITE + '/#stats-market?utm_source=naver_blog&utm_medium=social&utm_campaign=weekly_map')
FIXED_URL = (SITE + '/?utm_source=naver_blog&utm_medium=social&utm_campaign=weekly_map#stats-market')
# 그 착지의 첫 page_view 주소: 캠페인 쿼리는 그대로, 화면 표시 view= 를 해시 앞에 더한다(MEAS-1)
FIXED_PV = (SITE + '/?utm_source=naver_blog&utm_medium=social&utm_campaign=weekly_map&view=stats#stats-market')


def _head_scripts():
    """index.html 의 <head> 와 그 안의 인라인 스크립트(속성 없는 <script>) 전부 — 브라우저가 도는 순서대로.

    홈은 tools/home_src 입구로만 읽는다(index.html 이 맨 앞에 이어 붙어 온다)."""
    html = HS.home_source()
    head = html[:html.index('</head>')]
    return head, re.findall(r'<script>(.*?)</script>', head, re.S)


def _js_func(src, name):
    """홈 스크립트에서 `function name(...){...}` 하나를 중괄호 짝으로 잘라 온다."""
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError('%s 의 끝을 찾지 못했다' % name)


def _home_parts():
    src = HS.home_source()
    r2c = re.search(r'^const R2C=new Set\(\[.*?\]\);', src, re.M)
    assert r2c, 'R2C(리포트로 넘기는 옛 해시) 선언을 찾지 못했다'
    # PV_SENT(부팅 page_view 를 보냈는가)는 showView 가 쓴다(전수리뷰 #46). 대결 쿼리 걷기(chalInURL 등)는 2026-11-14
    # 퀴즈 제거로 홈에서 빠졌다.
    return '\n'.join(['var PV_SENT=false;', _js_func(src, 'track'), _js_func(src, 'viewLoc'), _js_func(src, 'showView'),
                      _js_func(src, 'applyHash'), r2c.group(0),
                      # 시장동향 주소 입구는 요청한 때의 GT_SEQ 를 넘긴다(2026-11-12 누름 경로 점검 B) — 그 선언도 같이 싣는다
                      re.search(r'^const GT_SEQ=\{[^}]*\};', src, re.M).group(0)])


HARNESS = r'''
const vm = require('vm');
const CFG = %(cfg)s;
let url = new URL(CFG.start);
const rec = {replace: [], push: [], stats: [], market: [], trend: [], adv: [], quiz: [], appended: [], listeners: {},
             idle: [], locReplace: null};
const store = Object.assign({}, CFG.store || {});
const ids = new Set(CFG.ids || []);
const ctx = {URL, URLSearchParams, Date, Math, JSON, Object, Array, String, Set, Number, console};
ctx.window = ctx;
ctx.location = {
  get href() { return url.href; }, get hash() { return url.hash; }, get search() { return url.search; },
  get pathname() { return url.pathname; }, get origin() { return url.origin; },
  replace(u) { rec.locReplace = u; },
};
ctx.history = {
  replaceState(s, t, u) { url = new URL(u, url.href); rec.replace.push(u); },
  pushState(s, t, u) { url = new URL(u, url.href); rec.push.push(u); },
};
ctx.localStorage = {
  getItem(k) { return Object.prototype.hasOwnProperty.call(store, k) ? store[k] : null; },
  setItem(k, v) { store[k] = String(v); }, removeItem(k) { delete store[k]; },
};
ctx.matchMedia = () => ({matches: false});
ctx.navigator = {};
ctx.scrollTo = () => {};
ctx.requestIdleCallback = (fn, opt) => { rec.idle.push({fn, opt}); };
ctx.setTimeout = (fn) => { rec.idle.push({fn, opt: 'setTimeout'}); };
ctx.document = {
  readyState: 'loading',
  documentElement: {className: ''},
  addEventListener(ev, fn) { (rec.listeners[ev] = rec.listeners[ev] || []).push(fn); },
  createElement(tag) { return {tagName: tag}; },
  head: {appendChild(el) { rec.appended.push(el.src); }},
  querySelectorAll() { return []; },
  getElementById(id) { return ids.has(id) ? {id, scrollIntoView() {}} : null; },
  body: {classList: {toggle() {}}},
};
vm.createContext(ctx);
if (!CFG.noHead) for (const s of CFG.head) vm.runInContext(s, ctx);
const afterHead = url.href;
const flag = !!ctx['ga-disable-' + CFG.ga];
const queueAtHead = (ctx.dataLayer || []).map((a) => [a[0], typeof a[1] === 'string' ? a[1] : null, a[2] || null]);
const gtagAtHead = typeof ctx.gtag;
if (!CFG.noHome) {
  vm.runInContext(`
    var vHome={style:{}},vStats={style:{}};
    var statsInited=true,curView=null,statsMode='market';
    function setStatsMode(m,p){ __rec.stats.push([m,p]); }
    function setMarketTab(t,p){ __rec.market.push([t,p]); }
    function setAdvTab(t,p){ __rec.adv.push([t,p]); }
    function openTrendRegion(k,c,v){ __rec.trend.push([k,c,v]); }
    function afterLayout(fn){}
    function statsHashOf(m){ return '#stats-'+m+(m==='market'?'-week':''); }
  `, Object.assign(ctx, {__rec: rec}));
  vm.runInContext(CFG.home, ctx);
}
ctx.document.readyState = 'interactive';
if (!CFG.noHome && !CFG.bootFails) vm.runInContext('applyHash()', ctx);   // boot() 끝의 applyHash
for (const step of (CFG.beforeDCL || [])) vm.runInContext(step, ctx);      // 로더가 붙기 전의 클릭
const appendedBeforeDCL = rec.appended.length;
ctx.document.readyState = 'complete';
for (const f of (rec.listeners['DOMContentLoaded'] || [])) f();
const appendedBeforeIdle = rec.appended.length;
for (const it of rec.idle.splice(0)) it.fn();
for (const step of (CFG.after || [])) vm.runInContext(step, ctx);
function pageViews() {
  const out = [];
  for (const a of (ctx.dataLayer || [])) {
    if (!a) continue;
    if (a[0] === 'config' && !(a[2] && a[2].send_page_view === false)) out.push({auto: true, page_location: afterHead});
    if (a[0] === 'event' && a[1] === 'page_view') out.push(Object.assign({}, a[2] || {}));
  }
  return out;
}
process.stdout.write(JSON.stringify({afterHead, href: url.href, flag, store, queueAtHead, gtagAtHead, rec: {replace: rec.replace, push: rec.push,
  stats: rec.stats, market: rec.market, trend: rec.trend, adv: rec.adv, quiz: rec.quiz, appended: rec.appended, locReplace: rec.locReplace},
  appendedBeforeDCL, appendedBeforeIdle, pv: pageViews()}));
'''


def _run(start, **kw):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    _, head = _head_scripts()
    cfg = dict(start=start, head=head, home=_home_parts(), ga=GA_ID)
    cfg.update(kw)
    p = subprocess.run(['node', '-e', HARNESS % {'cfg': json.dumps(cfg, ensure_ascii=False)}],
                       capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _views(got):
    return [pv.get('page_title') for pv in got['pv']]


# ── A1 블로그 주간 링크 착지·UTM ──────────────────────────────────────────────
def test_head_moves_hash_query_before_the_hash():
    """발행본 주소 → 머리 스크립트가 '/?utm…#stats-market' 으로 고친다(GA 가 읽는 쿼리로)."""
    got = _run(BLOG_URL, noHome=True)
    assert got['afterHead'] == FIXED_URL
    assert len(got['rec']['replace']) == 1


def test_head_keeps_existing_query_and_leaves_normal_urls_alone():
    got = _run(SITE + '/?a=1#stats-market?utm_source=x', noHome=True)
    assert got['afterHead'] == SITE + '/?a=1&utm_source=x#stats-market'
    for u in (SITE + '/', SITE + '/?utm_source=x#stats-market', SITE + '/#score', SITE + '/?c=5&s=beginner'):
        got = _run(u, noHome=True)
        assert got['afterHead'] == u and got['rec']['replace'] == [], '정상 주소를 건드렸다: %s' % u


def test_ga_off_inside_the_hash_still_excludes_the_device():
    """해시 속 ?ga_off=1 도 먹는다 — 쿼리 옮기기가 ga_off 판정보다 앞이라야 한다."""
    got = _run(SITE + '/#stats?ga_off=1', noHome=True)
    assert got['store'].get('ga_off') == '1' and got['flag'] is True


def test_blog_link_opens_the_stats_market_view():
    """발행본 주소로 들어오면 통계 뷰의 시장동향(주간)이 열린다 — 머리 → 부팅 순서 그대로."""
    got = _run(BLOG_URL)
    assert got['href'] == FIXED_URL
    assert got['rec']['stats'] == [['market', False]] and got['rec']['market'] == [['week', False]]
    assert _views(got) == ['view_stats']


@pytest.mark.parametrize('frag,market,trend,view', [
    ('stats-market-week~a7020202', 'week', 'a7020202', 'g'),   # 홈 지도·통계 지도·/weekly/ 머리 지도의 시군구 칸(서울 강남구)
    ('stats-market-month~b304', 'month', 'b304', 'g'),         # 월간 TOP 10 지역명
    ('stats-market-week~a0', 'week', 'a0', 'g'),               # 전국 칸·홈 지도 주간 모드의 '그래프' 단추
    ('stats-market-month~a0-t', 'month', 'a0', 't'),           # 홈 지도 월간 모드의 '표' 단추(2026-10-04)
    ('stats-market-week', 'week', None, 'g'),                  # 코드 없는 주소 — 연 그래프를 지도로 되돌린다(뒤로 가기)
    ('stats-market', 'week', None, 'g'),
])
def test_region_hash_opens_that_region_graph(frag, market, trend, view):
    """지도 칸·TOP 10 지역명의 주소 '#stats-market-<주기>~<코드>' 가 그 주기 탭을 열고 openTrendRegion(주기, 코드)를 부른다
    (2026-10-02 대표 요청 — 새 화면이 아니라 시장동향 그래프). 코드 없는 시장동향 주소도 null 로 불러 그 함수가 연 그래프를
    되돌리게 한다. 픽스처: 실제 머리·홈 스크립트, 주소만 바꾼다.
    변이(실제로 확인): applyHash 정규식에서 '(?:~(…))?' 를 빼면 '~코드' 주소가 통계를 못 열어 빨개진다. 시장동향 분기에서
    openTrendRegion 호출을 빼면 trend 가 비어, '(-t)?' 를 빼면 표 주소가 통계를 못 열어 빨개진다."""
    got = _run('https://www.agongmap.co.kr/#' + frag)
    assert got['rec']['stats'] == [['market', False]]
    assert got['rec']['market'] == [[market, False]]
    assert got['rec']['trend'] == [[market, trend, view]]
    assert _views(got) == ['view_stats']


def test_region_hash_rejects_a_code_outside_the_tile_codes():
    """코드 모양(a~c + 숫자 1~8자리 — NATION_TILE 의 모든 코드)이 아니면 통계 주소로 받지 않는다(임의 글자를 select 에 넣지 않게).
    변이(실제로 확인): 정규식의 코드 모양을 '[^~]+' 로 넓히면 빨개진다."""
    got = _run('https://www.agongmap.co.kr/#stats-market-week~x<1>')
    assert got['rec']['stats'] == [] and got['rec']['trend'] == []


def test_router_survives_a_hash_query_without_the_head():
    """머리 스크립트가 못 돈 경우(옛 캐시 HTML 등)에도 applyHash 가 '?' 뒤를 잘라 통계를 연다."""
    got = _run(BLOG_URL, noHead=True)
    assert got['rec']['stats'] == [['market', False]] and got['rec']['market'] == [['week', False]]


def test_first_page_view_carries_the_blog_campaign():
    """부팅의 단 한 번 page_view 가 utm 쿼리를 '#' 앞에 둔 착지 주소를 싣는다 — 그래야 캠페인이 잡힌다.

    화면 표시 view=stats 는 그 쿼리 뒤에 붙고 utm 은 하나도 빠지지 않는다(MEAS-1)."""
    got = _run(BLOG_URL)
    assert len(got['pv']) == 1
    loc = got['pv'][0]['page_location']
    assert loc == FIXED_PV, loc


# ── A3 page_view 한 번 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize('start,view,loc', [
    (SITE + '/', 'view_home', SITE + '/'),
    (SITE + '/?utm_source=x&utm_medium=y', 'view_home', SITE + '/?utm_source=x&utm_medium=y'),
    (SITE + '/#stats-market-week', 'view_stats', SITE + '/?view=stats#stats-market-week'),
    (SITE + '/#stats-adv-occ', 'view_stats', SITE + '/?view=stats#stats-adv-occ'),
    (SITE + '/#score', 'view_home', SITE + '/#score'),
    (BLOG_URL, 'view_stats', FIXED_PV),
])
def test_boot_sends_exactly_one_page_view(start, view, loc):
    """부팅 page_view 는 한 번이고, 착지 주소(머리가 고친 뒤)에 화면 표시 view= 만 더한 주소를 싣는다.

    홈은 view 를 달지 않는다 — 착지 주소 그대로다."""
    got = _run(start)
    assert _views(got) == [view], '부팅 page_view 가 한 번이 아니다: %s' % got['pv']
    assert got['pv'][0]['page_location'] == loc, '첫 page_view 주소가 착지 주소+view 가 아니다: %s' % got['pv'][0]


@pytest.mark.parametrize('start,ids', [(SITE + '/#sec-week', ['sec-week']), (SITE + '/#no-such-view', [])])
def test_anchor_or_unknown_hash_still_counts_once(start, ids):
    """showView 를 부르지 않는 부팅 경로(요소 앵커·모르는 해시)도 머리 로더가 한 번 채운다."""
    got = _run(start, ids=ids)
    assert len(got['pv']) == 1 and got['pv'][0]['page_location'] == start


def test_click_before_the_loader_keeps_the_landing_address():
    """앵커로 들어와 로더가 붙기 전에 홈 탭을 누르면: page_view 는 그 클릭의 한 번뿐이고, 해시를 걷어 내기
    전의 착지 주소(utm 쿼리 포함)를 싣는다 — 세션의 첫 hit 라 캠페인이 여기서 정해진다. 홈으로 가는 pushState 는
    쿼리를 남긴다(뒤로 가기 때 hashchange 가 오게 — test_home_cta.test_in_page_entrances_keep_the_landing_query)."""
    start = SITE + '/?utm_source=x#sec-week'
    got = _run(start, ids=['sec-week'], beforeDCL=["showView('home')"])
    assert got['rec']['push'] == ['/?utm_source=x'], got['rec']['push']
    assert _views(got) == ['view_home'] and got['pv'][0]['page_location'] == start


def test_boot_failure_still_counts_the_visit_once():
    """home-app.js 가 못 오거나 부팅이 죽어도 방문은 한 번 잡힌다(예전 자동 page_view 가 하던 몫)."""
    got = _run(SITE + '/?utm_source=x', noHome=True)
    assert len(got['pv']) == 1 and got['pv'][0]['page_location'] == SITE + '/?utm_source=x'


def test_view_changes_send_one_each_and_repeats_send_none():
    """전환은 origin+'/' 에 view= 를 단 가상 주소 — 홈으로 돌아오면 view 없는 '/'(첫 화면과 같은 한 줄)."""
    got = _run(SITE + '/', after=["showView('stats')", "showView('stats')", "showView('home')", "showView('home')"])
    assert _views(got) == ['view_home', 'view_stats', 'view_home']
    assert [pv['page_location'] for pv in got['pv'][1:]] == [SITE + '/?view=stats', SITE + '/']


def _ga_path_query(u):
    """GA 의 '페이지 경로 + 쿼리 문자열' 측정기준 — 호스트 뒤부터 해시 앞까지(해시는 들어가지 않는다)."""
    s = urllib.parse.urlsplit(u)
    return s.path + ('?' + s.query if s.query else '')


def test_page_path_report_tells_views_apart():
    """MEAS-1 권고: GA 페이지 경로 보고서에서 홈·통계가 서로 다른 한 줄씩이어야 한다(퀴즈 화면은 2026-11-14 제거).

    픽스처: 캠페인 없는 두 착지('/', 통계 해시)에서 부팅한 뒤 탭을 오가는 실제 순서, 그리고
    요소 앵커(#sec-week — 홈 화면이 뜬 채 머리 로더가 채운 한 건, page_title 없음). 화면 하나는 부팅이든
    전환이든 같은 한 줄로, 화면끼리는 다른 줄로 모여야 한다. 옛 '/#'+v 는 셋 다 '/' 한 줄이었다.
    주소창에 GA 보고서의 가상 주소를 붙여 넣고 다른 화면 해시로 들어와도 view= 가 두 번 붙지 않는다.
    """
    seen = {}
    runs = [(SITE + '/', ["showView('stats')", "showView('home')"], []),
            (SITE + '/#stats-market-week', ["showView('home')", "showView('stats')"], []),
            (SITE + '/#sec-week', ["showView('stats')"], ['sec-week'])]
    for start, after, ids in runs:
        got = _run(start, after=after, ids=ids)
        assert len(got['pv']) == len(after) + 1, got['pv']
        for pv in got['pv']:
            seen.setdefault(pv.get('page_title') or 'view_home', set()).add(_ga_path_query(pv['page_location']))
    assert set(seen) == {'view_home', 'view_stats'}, seen
    for title, rows in seen.items():
        assert len(rows) == 1, '%s 가 부팅·전환에서 다른 주소로 갈라진다: %s' % (title, sorted(rows))
    rows = {title: next(iter(r)) for title, r in seen.items()}
    assert len(set(rows.values())) == len(rows), '화면끼리 페이지 경로 한 줄로 합쳐진다: %s' % rows
    assert rows['view_home'] == '/', rows
    got = _run(SITE + '/?view=home#stats-market-week')
    assert got['pv'][0]['page_location'] == SITE + '/?view=stats#stats-market-week', got['pv']


# ── C8 GA 지연 로딩 ───────────────────────────────────────────────────────────
def test_ga_loader_waits_for_the_first_screen():
    """gtag.js 는 DOMContentLoaded(부팅이 지도를 그린 뒤) 다음 한가할 때 붙는다. 머리에 정적 로더가 없다."""
    head, _ = _head_scripts()
    assert not re.search(r'<script[^>]*\bsrc="[^"]*googletagmanager\.com/gtag/js', head), \
        '머리에 정적 gtag.js 로더가 있다 — 첫 화면 지도와 대역을 다툰다(MOB-10)'
    got = _run(SITE + '/')
    assert got['appendedBeforeDCL'] == 0 and got['appendedBeforeIdle'] == 0
    assert got['rec']['appended'] == ['https://www.googletagmanager.com/gtag/js?id=' + GA_ID]


def test_ga_queue_is_ready_before_boot():
    """큐(dataLayer·gtag)는 머리에서 곧바로 서야 부팅 중 이벤트(page_view 등)를 잃지 않는다.

    config 는 자동 page_view 를 끈 채로 js 다음에 온다 — 로더가 늦게 와도 이 순서대로 처리한다.
    """
    got = _run(SITE + '/', noHome=True)
    assert got['gtagAtHead'] == 'function'
    assert [q[0] for q in got['queueAtHead']] == ['js', 'config']
    assert got['queueAtHead'][1][1] == GA_ID and got['queueAtHead'][1][2] == {'send_page_view': False}


def test_ga_off_device_is_still_excluded():
    got = _run(SITE + '/?ga_off=1')
    assert got['flag'] is True and got['rec']['appended'] == [], 'ga_off 기기에 GA 를 붙였다'
    got = _run(SITE + '/', store={'ga_off': '1'})
    assert got['flag'] is True and got['rec']['appended'] == []
    got = _run(SITE + '/?ga_off=0', store={'ga_off': '1'})
    assert got['flag'] is False and got['store'].get('ga_off') is None and got['rec']['appended']


# ── 전수리뷰(2026-09-30) #45·#46·#44 ──────────────────────────────────────────
def test_bare_stats_hash_sets_the_default_screen_and_normalizes_the_address():
    """모든 페이지 탭바의 '시세'(/#stats)로 들어오면 #stats-market 과 같게 모드·하위 탭을 기본값으로 맞추고 주소를
    #stats-market-week 로 바꿔 둔다 — 뒤로 가기로 #stats 에 돌아와도 같은 화면을 재현한다(전수리뷰 #45).

    변이: applyHash 의 `if(h==='stats'){…}` 분기를 빼면(옛 `h==='stats'` 는 showView 만) 빨개진다(실제로 확인).
    픽스처: /zone/ 등 다른 페이지 탭바의 '/#stats' 착지, 그 뒤 투자지표로 옮겼다가 뒤로 가기로 '/#stats' 에 돌아온 순간.
    """
    got = _run(SITE + '/#stats', after=["history.pushState(null,'','/#stats-adv-occ')",
                                         "history.pushState(null,'','/#stats'); applyHash()"])
    assert got['rec']['stats'] == [['market', False], ['market', False]], got['rec']['stats']
    assert got['rec']['market'] == [['week', False], ['week', False]], got['rec']['market']
    assert got['href'] == SITE + '/#stats-market-week', got['href']
    assert _views(got) == ['view_stats']


def test_old_quiz_hash_opens_home_and_drops_the_hash():
    """옛 퀴즈 주소(/#test·/#test-<세트>, 발행한 글·북마크·공유 링크에 남아 있다)는 홈을 열고 주소에서 해시를 걷는다 — 퀴즈 3종은
    2026-11-14 대표 결정으로 걷었다. 부팅 page_view 는 홈(view_home) 한 번이고 착지 쿼리(utm)를 그대로 싣는다.

    변이(실제로 확인): applyHash 의 옛 퀴즈 주소 갈래를 지우면 해시가 남고(모르는 해시라 요소 앵커로 빠진다) 빨개진다.
    픽스처: 퀴즈 랜딩 '시작하기'가 보내던 주소 모양(/?utm_source=kakao#test-investor)과 맨 #test.
    """
    for frag in ('#test-investor', '#test'):
        got = _run(SITE + '/?utm_source=kakao' + frag)
        assert got['href'] == SITE + '/?utm_source=kakao', got['href']
        assert _views(got) == ['view_home'], got['pv']
        assert got['pv'][0]['page_location'] == SITE + '/?utm_source=kakao', got['pv']   # utm 은 남는다


def test_head_scripts_leave_no_globals():
    """머리 인라인 스크립트(쿼리 옮기기·ga_off)는 전역에 이름을 남기지 않는다 — 뒤 스크립트가 같은 이름(_h·_p 등)을 최상위
    let/const 로 두면 그 파일 전체가 SyntaxError 로 죽는다(전수리뷰 2차 overflow, 지금은 충돌 없음).

    변이(실제로 확인): index.html 머리 스크립트의 (function(){ … })() 감싸기를 지우면 빨개진다.
    픽스처: 저장소 홈 머리 스크립트를 해시 속 쿼리·ga_off 가 있는 주소로 node vm 에서 돌린다(두 갈래를 다 탄다).
    """
    if not shutil.which('node'):
        pytest.skip('node 없음')
    _, head = _head_scripts()
    assert head, '머리 인라인 스크립트를 못 찾았다'
    js = r"""
const vm = require('vm');
const S = %s;
const url = new URL('https://example.test/?a=1#stats?ga_off=1');
const store = {};
const ctx = {URLSearchParams, location: url,
  history: {replaceState(_, __, u) { const n = new URL(u, url.href); url.search = n.search; url.hash = n.hash; }},
  localStorage: {getItem: (k) => store[k] || null, setItem: (k, v) => { store[k] = String(v); }, removeItem: (k) => { delete store[k]; }},
  setTimeout() {}, document: {readyState: 'loading', addEventListener() {}, createElement() { return {}; }, head: {appendChild() {}}}, addEventListener() {}};
ctx.window = ctx;
vm.createContext(ctx);
const before = new Set(Object.keys(ctx));
for (const s of S) vm.runInContext(s, ctx);
process.stdout.write(JSON.stringify({leaked: Object.keys(ctx).filter((k) => !before.has(k) && /^_[a-z]$/.test(k)), ga: store.ga_off || null}));
""" % json.dumps(head, ensure_ascii=False)
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    o = json.loads(p.stdout.decode('utf-8'))
    assert o['ga'] == '1', '머리 스크립트가 돌지 않았다(헛통과 방지): %s' % o
    assert o['leaked'] == [], '머리 스크립트가 전역 이름을 남긴다: %s' % o['leaked']
