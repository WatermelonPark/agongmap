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
  - make_naver_post.site_link 를 거치지 않고 옛 `'%s/#stats-market?utm_…'` 줄로 되돌리면 → 초안 링크 시험
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
    # PV_SENT(부팅 page_view 를 보냈는가)와 대결 쿼리 걷기(chalInURL·chalSearch)는 showView 가 쓴다(전수리뷰 #44·#46)
    return '\n'.join(['var PV_SENT=false, PV_AFTER=null;', _js_func(src, 'track'), _js_func(src, 'viewLoc'), _js_func(src, 'showView'),
                      _js_func(src, 'chalInURL'), _js_func(src, 'chalSearch'), _js_func(src, 'chalBootable'),
                      _js_func(src, 'applyHash'), r2c.group(0)])


HARNESS = r'''
const vm = require('vm');
const CFG = %(cfg)s;
let url = new URL(CFG.start);
const rec = {replace: [], push: [], stats: [], market: [], adv: [], quiz: [], appended: [], listeners: {},
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
    var vHome={style:{}},vStats={style:{}},vTest={style:{}};
    var statsInited=true,curView=null,statsMode='market';
    function setStatsMode(m,p){ __rec.stats.push([m,p]); }
    function setMarketTab(t,p){ __rec.market.push([t,p]); }
    function setAdvTab(t,p){ __rec.adv.push([t,p]); }
    function startQuiz(){ __rec.quiz.push([].slice.call(arguments)); }
    function backToPick(){}
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
  stats: rec.stats, market: rec.market, adv: rec.adv, quiz: rec.quiz, appended: rec.appended, locReplace: rec.locReplace},
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


def _site_links(html):
    return re.findall(r'https?://(?:www\.)?agongmap\.co\.kr[^\s"\'<>)]*', html)


def _all_drafts(monkeypatch):
    """초안 생성기가 만드는 본문 전부 — 주간 4주 로테이션, 지역 편 유도문 전 회차, 이론 편 전부."""
    import make_naver_post as P
    import make_theory_post as T
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = P.M.load()
    out = {}
    n_rot = len(P.MORE_ROTATION)
    for rot in range(n_rot):
        monkeypatch.setattr(P, 'rot_index', lambda p, _r=rot: _r)
        out['weekly-%d' % rot] = P.draft_weekly(adv, sts)['body']
    zones = [z for z in adv['sido']['zones'] if not z.get('agg')]
    for seq in range(1, len(P.ZONE_CTA) + 1):
        out['zone-%d' % seq] = P.draft_zone(adv, sts, zones[0], seq, len(zones))['body']
    for post in T.POSTS:
        try:
            out['theory-%d' % post['n']] = T.render(post)
        except SystemExit:
            continue      # 생성 가드가 걸린 편(데이터 조건)은 링크를 낼 본문이 없다
    return out


def test_every_draft_site_link_puts_the_query_before_the_hash(monkeypatch):
    drafts = _all_drafts(monkeypatch)
    links = [(k, u) for k, html in drafts.items() for u in _site_links(html)]
    assert len(links) >= len(drafts), '초안에서 사이트 링크를 거의 못 찾았다 — 검사가 헛돈다'
    bad = sorted({'%s: %s' % (k, u) for k, u in links if '#' in u and '?' in u[u.index('#'):]})
    assert not bad, "'?'가 '#' 뒤에 있는 사이트 링크 — GA 가 캠페인을 못 읽고 홈이 화면을 못 찾는다: %s" % bad[:5]


def test_weekly_map_link_lands_on_stats_with_campaign(monkeypatch):
    drafts = _all_drafts(monkeypatch)
    want = FIXED_URL.replace('&', '&amp;')
    for k, html in drafts.items():
        if k.startswith('weekly-'):
            assert want in _site_links(html), '%s: 주간 지도 링크가 %s 가 아니다' % (k, want)


# ── A3 page_view 한 번 ─────────────────────────────────────────────────────────
@pytest.mark.parametrize('start,view,loc', [
    (SITE + '/', 'view_home', SITE + '/'),
    (SITE + '/?utm_source=x&utm_medium=y', 'view_home', SITE + '/?utm_source=x&utm_medium=y'),
    (SITE + '/#stats-market-week', 'view_stats', SITE + '/?view=stats#stats-market-week'),
    (SITE + '/#stats-adv-occ', 'view_stats', SITE + '/?view=stats#stats-adv-occ'),
    (SITE + '/#score', 'view_home', SITE + '/#score'),
    (SITE + '/#test', 'view_test', SITE + '/?view=test#test'),
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
    """MEAS-1 권고: GA 페이지 경로 보고서에서 홈·통계·퀴즈가 서로 다른 한 줄씩이어야 한다.

    픽스처: 캠페인 없는 세 착지('/', 통계 해시, 퀴즈 해시)에서 부팅한 뒤 탭을 오가는 실제 순서, 그리고
    요소 앵커(#sec-week — 홈 화면이 뜬 채 머리 로더가 채운 한 건, page_title 없음). 화면 하나는 부팅이든
    전환이든 같은 한 줄로, 화면끼리는 다른 줄로 모여야 한다. 옛 '/#'+v 는 셋 다 '/' 한 줄이었다.
    주소창에 GA 보고서의 가상 주소를 붙여 넣고 다른 화면 해시로 들어와도 view= 가 두 번 붙지 않는다.
    """
    seen = {}
    runs = [(SITE + '/', ["showView('stats')", "showView('test')", "showView('home')"], []),
            (SITE + '/#stats-market-week', ["showView('home')", "showView('stats')"], []),
            (SITE + '/#test', ["showView('stats')", "showView('home')", "showView('test')"], []),
            (SITE + '/#sec-week', ["showView('stats')"], ['sec-week'])]
    for start, after, ids in runs:
        got = _run(start, after=after, ids=ids)
        assert len(got['pv']) == len(after) + 1, got['pv']
        for pv in got['pv']:
            seen.setdefault(pv.get('page_title') or 'view_home', set()).add(_ga_path_query(pv['page_location']))
    assert set(seen) == {'view_home', 'view_stats', 'view_test'}, seen
    for title, rows in seen.items():
        assert len(rows) == 1, '%s 가 부팅·전환에서 다른 주소로 갈라진다: %s' % (title, sorted(rows))
    rows = {title: next(iter(r)) for title, r in seen.items()}
    assert len(set(rows.values())) == len(rows), '화면끼리 페이지 경로 한 줄로 합쳐진다: %s' % rows
    assert rows['view_home'] == '/', rows
    got = _run(SITE + '/?view=test#stats-market-week')
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


def test_bad_challenge_link_sends_one_boot_page_view():
    """값이 틀린 대결 링크(점수 상한 초과)는 부팅 page_view 가 한 번(view_home, 착지 주소)이다(전수리뷰 #46).
    맞는 대결 링크도 한 번(view_test).

    변이: showView 의 quiet 인자를 무시하면(`if(changed&&!quiet)` → `if(changed)`) view_test·view_home 두 건이 나가
          빨개진다(실제로 확인).
    픽스처: boot 의 실제 순서 — showView('test',false,true) 뒤 bootChallenge 가 readChallenge 실패로 applyHash, 또는
            성공해 showView('test',false). 착지 주소 '/?c=11&s=beginner'(QUIZ_LEN 10 초과)와 '/?c=7&s=beginner&q=abc'.
    """
    bad = _run(SITE + '/?c=11&s=beginner', bootFails=True, beforeDCL=["showView('test',false,true)", 'applyHash()'])
    assert _views(bad) == ['view_home'], bad['pv']
    assert bad['pv'][0]['page_location'] == SITE + '/?c=11&s=beginner', bad['pv']
    assert bad['href'] == SITE + '/', '값이 틀린 대결 쿼리가 홈 주소에 남았다: %s' % bad['href']
    ok = _run(SITE + '/?c=7&s=beginner&q=abc', bootFails=True,
              beforeDCL=["showView('test',false,true)", "showView('test',false)"])
    assert _views(ok) == ['view_test'], ok['pv']


def test_challenge_query_leaves_with_the_quiz_and_other_hashes_win():
    """대결 쿼리(c·s·q)는 퀴즈 화면에서만 남는다 — 시세·홈으로 옮기면 걷고 utm 은 둔다. 부팅은 그 대결 세트 퀴즈 해시
    (또는 해시 없음)일 때만 대결로 간다(전수리뷰 #44·#49).

    변이(실제로 확인): showView 의 `q` 를 location.search 로 되돌리면 옮긴 주소에 c·s·q 가 남아, chalBootable 이 늘 참을
          내면 '#stats-…' 부팅 단정이 빨개진다.
    픽스처: 대결 링크로 들어와 퀴즈(#test-beginner)를 보다가 하단 '시세' → '홈'을 누른 실제 순서, 그리고 옛 탭에 남은
            '?c=7&s=beginner#stats-market-week' 주소.
    """
    start = SITE + '/?c=7&s=beginner&q=abc&utm_source=quiz_challenge#test-beginner'
    got = _run(start, bootFails=True, beforeDCL=["__rec.quiz.push(['boot', chalBootable()])",
                                                  "showView('test',false,true)", "showView('test',false)"],
               after=["showView('stats')", "__rec.quiz.push(['stats', location.href])",
                      "showView('home')", "__rec.quiz.push(['home', location.href])"])
    q = dict((k, v) for k, v in got['rec']['quiz'])
    assert q['boot'] is True
    assert q['stats'] == SITE + '/?utm_source=quiz_challenge#stats-market-week', q['stats']
    assert q['home'] == SITE + '/?utm_source=quiz_challenge', q['home']
    old = _run(SITE + '/?c=7&s=beginner#stats-market-week', bootFails=True,
               beforeDCL=["__rec.quiz.push(['boot', chalBootable()])"])
    assert old['rec']['quiz'] == [['boot', False]], '다른 화면 해시가 붙은 대결 주소를 대결로 부팅한다'



def test_leaving_the_challenge_quiz_strips_the_query_from_both_entries():
    """대결 퀴즈(/?c=&s=&q=#test-…)에서 시세로 옮기면, 새 항목만이 아니라 떠나는 퀴즈 항목의 주소에서도 대결 쿼리를 먼저
    걷는다(replaceState). 두 항목의 쿼리가 다르면 뒤로 가기에 hashchange 가 오지 않아(popstate 만) 주소는 퀴즈인데 화면은
    시세에 머물렀다(통합 검토, Chromium 재현: 새 판 view=stats hc=0 · 기준 커밋 view=test hc=1).

    변이(실제로 확인): showView 의 `if(curView==='test'&&v!=='test'&&chalInURL(location.search))history.replaceState(…)` 줄을
          지우면 퀴즈 항목을 걷는 replace 가 없어 빨개진다.
    픽스처: 퀴즈 랜딩이 넘기는 대결 링크 모양과 utm 한 개(걷지 않고 남아야 한다).
    """
    got = _run('https://www.agongmap.co.kr/?utm_source=kakao&c=6&s=investor&q=abc12#test-investor',
               after=["showView('stats')"])
    rep = [u for u in got['rec']['replace'] if u.endswith('#test-investor')]
    assert rep and all('c=' not in u and 'q=' not in u for u in rep) and 'utm_source=kakao' in rep[-1], got['rec']
    pushed = got['rec']['push'][-1]
    assert pushed.endswith('#stats-market-week'), pushed
    left = rep[-1].split('#')[0]
    assert (pushed.split('#')[0] or left) == left, '두 항목의 쿼리가 다르다 — 뒤로 가기에 hashchange 가 오지 않는다: %s · %s' % (left, pushed)


def test_head_fallback_leaves_the_boot_page_view_to_a_deferred_challenge_boot():
    """머리 스크립트의 idle 폴백은 dataLayer 에 page_view 가 없으면 보낸다. 대결 부팅은 page_view 를 home-quiz.js 도착 뒤로
    미루므로(#46) 그 파일만 늦으면 폴백과 bootChallenge 가 한 건씩 두 건을 보냈다(통합 검토 — home-quiz.js 800ms 지연 재현).
    부팅이 window.__pvDefer 를 세우면 폴백은 보내지 않는다. 표지가 없으면 예전처럼 한 건을 보낸다.

    변이(실제로 확인): index.html 머리 load() 의 `&&!window.__pvDefer` 를 지우면 첫 단정이 빨개진다.
    픽스처: 홈 스크립트 없이 머리만 돈 상태(home-quiz.js 가 아직 안 온 대결 부팅과 같다).
    """
    got = _run('https://www.agongmap.co.kr/?c=6&s=investor&q=abc12', noHome=True, beforeDCL=['window.__pvDefer=true'])
    assert got['pv'] == [], got['pv']
    got = _run('https://www.agongmap.co.kr/', noHome=True)
    assert len(got['pv']) == 1, got['pv']


def test_deferred_boot_runs_the_visit_after_the_first_page_view():
    """대결 부팅의 home_visit 은 부팅 page_view 뒤에 간다 — boot 가 countVisit 를 PV_AFTER 로 걸어 두고, showView 가 첫
    page_view 를 보낸 직후 한 번 부른다. 예전엔 page_view 가 bootChallenge 로 미뤄진 뒤에도 boot 가 곧바로 home_visit 을
    보내 순서가 늘 뒤집혔다(통합 검토).

    변이(실제로 확인): showView 의 `if(first&&PV_AFTER){…}` 를 지우면 기록이 비어 빨개지고, boot 의 대결 분기에서
          `PV_AFTER=()=>{VISIT=countVisit();};` 를 지우면 정적 단정이 빨개진다.
    픽스처: 부팅 applyHash 없이(bootFails), 부팅처럼 __pvDefer 를 세우고 quiet 로 퀴즈를 띄운 뒤 대결 확정
            (showView('test',false))을 흉내 낸다.
    """
    got = _run('https://www.agongmap.co.kr/?c=6&s=investor&q=abc12', bootFails=True, beforeDCL=['window.__pvDefer=true'], after=[
        "PV_AFTER=()=>{__rec.quiz.push(['visit',(dataLayer||[]).filter(a=>a&&a[1]==='page_view').length]);}",
        "showView('test',false,true)", "showView('test',false)", "showView('home')"])
    assert got['rec']['quiz'] == [['visit', 1]], got['rec']['quiz']
    boot = _js_func(HS.home_source(), 'boot')
    assert 'PV_AFTER=()=>{VISIT=countVisit();};' in boot and 'if(!PV_AFTER)VISIT=countVisit();' in boot
