# -*- coding: utf-8 -*-
"""홈 퀴즈·통계 코드 분할(홈 마케팅 검수 B11·MOB-8, 2026-09-27)을 고정한다.

지도 첫 화면이 쓰지 않는 퀴즈(home-quiz.js)·통계(home-stats.js) 코드를 home-app.js 에서 떼어, 그 화면을 열 때
loadPart 로 받는다. 파일이 오기 전에 불린 입구(PARTS.*.api)는 같은 이름의 대기 함수가 받아 두었다가 도착하면 부른
순서대로 진짜 함수를 부른다. 이 구조의 흔한 결함은 넷이다 — 모두 초록인 채 라이브에서만 드러난다.
  ① 홈 스크립트·onclick 이 부르는 분할 파일 함수가 입구 목록에 없어 ReferenceError(누름이 조용히 죽는다).
  ② 입구 이름과 분할 파일의 선언이 어긋나 파일이 와도 진짜 함수가 안 불린다.
  ③ 오프라인·배포 직후: 서비스워커 사전 캐시 주소와 홈이 부르는 주소(판 ?v=)가 달라 캐시가 헛돈다.
  ④ 코어에서 뺀 데이터(occupancy·permits·bubble·전세가율)를 홈 첫 화면 코드가 읽어 undefined 가 된다.
그래서 목록을 코드에서 뽑아 서로 대조하고, 로더와 서비스워커는 node 로 실제로 돌린다.
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
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import split_data as SD  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _files():
    return dict(HS.home_files())


def _core():
    return _files()['home-app.js']


def _parts_decl():
    """home-app.js 의 PARTS → {이름: (파일, [입구 함수])}."""
    core = _core()
    m = re.search(r'^const PARTS=\{(.*?)^\};', core, re.S | re.M)
    assert m, 'home-app.js 에서 PARTS 선언을 못 찾았다'
    out = {}
    for name, src, api in re.findall(r"(\w+):\{src:'/([\w.-]+)',api:\[([^\]]*)\]\}", m.group(1)):
        out[name] = (src, re.findall(r"'(\w+)'", api))
    assert out, 'PARTS 에서 분할 파일을 하나도 못 읽었다 — 모양이 바뀌었으면 이 시험도 고칠 것'
    return out


def _strip_js(js):
    """주석만 지운다(문자열·템플릿·정규식은 남긴다 — onclick 템플릿 속 호출도 호출이다)."""
    out, i, n, prev = [], 0, len(js), ''
    while i < n:
        c = js[i]
        if c in '\'"`':
            j = i + 1
            while j < n and js[j] != c:
                j += 2 if js[j] == '\\' else 1
            out.append(js[i:j + 1])
            i, prev = j + 1, c
        elif js.startswith('//', i):
            j = js.find('\n', i)
            i = n if j < 0 else j
        elif js.startswith('/*', i):
            j = js.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c == '/' and (prev == '' or prev in '(,=:[!&|?{};+-*%<>~^'):
            j, cls = i + 1, False                     # 정규식 리터럴
            while j < n and (js[j] != '/' or cls):
                if js[j] == '\\':
                    j += 1
                elif js[j] == '[':
                    cls = True
                elif js[j] == ']':
                    cls = False
                j += 1
            out.append(js[i:j + 1])
            i, prev = j + 1, '/'
        else:
            out.append(c)
            if not c.isspace():
                prev = c
            i += 1
    return ''.join(out)


def _top_names(js):
    """최상위 선언 이름 → 'function' | 'lexical'. 줄 첫머리의 function/const/let/var 만 본다(이 저장소의 모양)."""
    out = {}
    for m in re.finditer(r'^(?:async\s+)?function\s+([\w$]+)', js, re.M):
        out[m.group(1)] = 'function'
    for m in re.finditer(r'^(?:const|let|var)\s+', js, re.M):
        depth, cur, names, i = 0, '', [], m.end()
        while i < len(js):
            ch = js[i]
            if ch in '([{':
                depth += 1
            elif ch in ')]}':
                depth -= 1
            if depth == 0 and ch in ';\n':
                break
            if depth == 0 and ch == ',':
                names.append(cur)
                cur = ''
            else:
                cur += ch
            i += 1
        names.append(cur)
        for nm in names:
            mm = re.match(r'\s*([\w$]+)\s*(=|$)', nm)
            if mm:
                out[mm.group(1)] = 'lexical'
    return out


def test_home_source_carries_the_split_files():
    """도구·시험이 읽는 홈 소스(home_source)에 분할 파일이 이어 붙어 온다 — QUIZSETS·SGG_QNAME 을 읽는 생성기·감시가
    파일이 옮겨졌다고 조용히 꺼지지 않게(백로그 10 의 교훈).

    무엇을 깨뜨리면 빨개지나(실제로 확인): home_src.EXTERNAL 에서 분할 파일을 빼면(표식 QUIZSETS 가 없어 HomeSourceError),
    home-app.js 의 PARTS 에 새 파일을 더하고 home_src.PARTS 에 안 적으면.
    픽스처: 저장소의 home-app.js·home-quiz.js·home-stats.js.
    """
    decl = _parts_decl()
    assert sorted(src for src, _ in decl.values()) == sorted(HS.PARTS), (
        'home-app.js PARTS %s 와 tools/home_src.PARTS %s 가 다르다' % (sorted(s for s, _ in decl.values()), HS.PARTS))
    files = _files()
    assert list(files)[:2] == ['index.html', 'home-app.js'] and set(HS.PARTS) <= set(files)
    src = HS.home_source()
    for rel in HS.PARTS:
        assert files[rel].strip() and files[rel] in src, '%s 가 home_source 에 없다' % rel


def test_every_part_entry_is_declared_and_every_core_call_is_an_entry():
    """입구 목록(PARTS.*.api)과 분할 파일 선언·홈이 부르는 이름이 맞물린다.

    - 입구 이름은 그 분할 파일의 최상위 function 이어야 한다(아니면 파일이 와도 대기 함수가 진짜를 못 찾는다).
    - 홈 스크립트(주석 제외, onclick 템플릿 포함)와 index.html 의 on…="" 이 부르는 분할 파일 이름은 모두 입구여야 한다.
    - 홈이 분할 파일의 const/let 을 읽으면 안 된다(대기 함수로 받을 수 없다 — 파일이 오기 전엔 ReferenceError).
    - 같은 최상위 이름이 두 파일에 있으면 안 된다(나중에 도는 분할 파일이 홈 것을 덮는다).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): PARTS.stats.api 에서 'gtSet' 을 빼면(index.html onclick),
    home-app.js 에 renderAdvAll() 호출을 더하면(입구 아님), home-quiz.js 의 bootChallenge 를 bootChallenge2 로 바꾸면,
    home-stats.js 에 function pv2(){} 를 더하면(중복).
    픽스처: 저장소의 홈 파일 그대로.
    """
    files = _files()
    core = _strip_js(files['home-app.js'])
    core_names = _top_names(files['home-app.js'])
    handlers = ' '.join(re.findall(r'\son[a-z]+="([^"]*)"', files['index.html']))
    used = set(re.findall(r'[A-Za-z_$][\w$]*', core)) | set(re.findall(r'[A-Za-z_$][\w$]*', handlers))
    bad = []
    seen = dict((k, 'home-app.js') for k in core_names)
    for name, (rel, api) in _parts_decl().items():
        names = _top_names(files[rel])
        for fn in api:
            if names.get(fn) != 'function':
                bad.append('%s 입구 %s 가 %s 의 최상위 function 이 아니다' % (name, fn, rel))
            if fn in core_names:
                bad.append('%s 입구 %s 를 home-app.js 도 선언한다' % (name, fn))
        for nm, kind in names.items():
            if nm in seen:
                bad.append('%s 가 %s 와 %s 에 둘 다 있다' % (nm, seen[nm], rel))
            seen[nm] = rel
            if nm in used and nm not in api:
                bad.append('홈이 %s 의 %s(%s)를 입구 없이 부른다 — PARTS.%s.api 에 넣거나 홈에 남길 것'
                           % (rel, nm, kind, name))
    assert not bad, '\n  '.join(['분할 파일 입구가 어긋났다:'] + bad)


LOADER = r"""
const vm = require('vm');
const CFG = %(cfg)s;
const rec = {calls: [], appended: [], toast: [], box: []};
const scripts = [];
const els = {};
function el(id){ return els[id] || (els[id] = {id, style: {display: 'none'}, textContent: '', innerHTML: ''}); }
const ctx = {console, Promise, Object, Array, JSON, setTimeout, rec, __cfg: CFG};
ctx.window = ctx;
ctx.document = {
  createElement(t){ return {tag: t, remove(){}}; },
  head: {appendChild(s){ rec.appended.push(s.src); scripts.push(s); }},
  getElementById: el,
};
let trend = null;
ctx.fetch = (u) => new Promise((res, rej) => { trend = {res: () => res({ok: true, json: () => ({ADV: {}, STATS: {}})}), rej}; });
ctx.ADV = {}; ctx.STATS = {};
vm.createContext(ctx);
vm.runInContext(CFG.core + `
var statsInited=false, curView='stats', HOME_BUILD=__cfg.build;
function toast(m){ rec.toast.push(m); }
`, ctx);
process.on('unhandledRejection', () => {});   // 판정은 아래 기록으로 한다(변이가 거부를 흘려도 끝까지 돈다)
const tick = () => new Promise((r) => setImmediate(r));
function deliver(i, body){ vm.runInContext(body, ctx); scripts[i].onload(); }
(async () => {
  const out = {};
  // ① 통계: 파일이 오기 전 누름 둘(모드 → 모드)과 진입이 순서대로, 파일과 그래프 데이터가 **둘 다** 온 뒤에 돈다
  ctx.statsOpen(); ctx.setStatsMode('adv'); ctx.setStatsMode('basic');
  await tick();
  out.statsAppended = rec.appended.slice();
  out.boxWhileWaiting = els['stats-loading'] && els['stats-loading'].style.display;
  deliver(0, "function statsOpen(){rec.calls.push(['statsOpen'])} function setStatsMode(m){rec.calls.push(['setStatsMode',m])}");
  await tick();
  out.callsBeforeData = rec.calls.length;
  trend.res(); await tick(); await tick(); await tick();
  out.statsCalls = rec.calls.splice(0);
  // 도착 뒤에는 대기 함수가 아니라 진짜 함수가 바로 불린다
  ctx.setStatsMode('more'); out.direct = rec.calls.splice(0);
  // ② 퀴즈: 딥링크(#test-beginner) 경로 — applyHash 가 startQuiz 를 부르면 퀴즈 파일을 받고, 못 받으면 알리고 다시 받는다
  ctx.location = {hash: '#test-beginner'};
  ctx.showView = (v) => { rec.calls.push(['showView', v]); ctx.curView = v; };
  vm.runInContext('applyHash()', ctx);
  await tick();
  const qi = rec.appended.length - 1;
  out.quizAppended = rec.appended.slice(1);
  out.qcardWhileWaiting = els['qcard'] && els['qcard'].innerHTML;
  scripts[qi].onerror(); await tick(); await tick();
  out.afterFail = {toast: rec.toast.slice(), calls: rec.calls.splice(0)};
  ctx.startQuiz('calc');
  await tick();
  out.retryAppended = rec.appended.length - 1 > qi;
  ctx.curView = 'home';            // 파일이 오기 전에 뒤로 가기로 홈에 왔다
  deliver(rec.appended.length - 1, "function startQuiz(){rec.calls.push(['startQuiz'].concat([].slice.call(arguments)))}");
  await tick(); await tick();
  out.quizCallsAfterLeave = rec.calls.splice(0);
  ctx.curView = 'test'; ctx.startQuiz('investor');
  out.quizCalls = rec.calls.splice(0);
  process.stdout.write(JSON.stringify(out));
})().catch((e) => { console.error(e); process.exit(1); });
"""


def _loader_src():
    core = _core()
    a = core.index('function loadScript(src){')
    b = core.index('\n}', a) + 2
    pieces = [core[a:b]]
    s = core.index('const PARTS={')
    e = core.index('\n}));', s) + len('\n}));')
    pieces.append(core[s:e])
    for fn in ('loadFullData', 'loadData', 'applyHash'):
        m = re.search(r'^function %s\(' % fn, core, re.M)
        assert m, 'home-app.js 에서 %s 를 못 찾았다' % fn
        i, depth = core.index('{', m.end()), 0
        for j in range(i, len(core)):
            depth += {'{': 1, '}': -1}.get(core[j], 0)
            if depth == 0:
                pieces.append(core[m.start():j + 1])
                break
    pieces.append('let _loaded={}; const R2C=new Set(); function afterLayout(){}')
    return '\n'.join(pieces)


def _run_loader():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    build = re.search(r"const HOME_BUILD='(v\d+)'", _core()).group(1)
    cfg = {'core': _loader_src(), 'build': build}
    p = subprocess.run(['node', '-e', LOADER % {'cfg': json.dumps(cfg, ensure_ascii=False)}], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-2000:]
    return json.loads(p.stdout.decode('utf-8')), build


def test_calls_before_the_part_arrives_wait_and_replay_in_order():
    """분할 파일이 오기 전에 누른 것이 사라지지 않고, 파일(통계는 그래프 데이터까지)이 온 뒤 부른 순서대로 돈다.

    로더 코드(loadScript·PARTS 대기 함수·loadPart·partReady·partBusy·loadFullData·loadData·applyHash)를 꺼내 node 로
    돌린다. 재현하는 실제 상태: 느린 망에서 '시세' 탭 → 투자지표 → 기본통계를 파일 도착 전에 연달아 누름, 퀴즈 랜딩의
    '시작하기'(/#test-beginner)로 들어왔는데 퀴즈 파일을 못 받은 뒤 다시 시도, 다시 받는 사이 뒤로 가기로 홈에 옴.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): 대기 함수가 partReady 를 기다리지 않고 곧바로 window[fn] 을 부르게 하면
    (아직 대기 함수라 누름이 사라진다), partReady 가 통계에서 loadFullData 를 기다리지 않게 하면(callsBeforeData
    가 0 이 아니다), loadPart 실패에서 delete PART_P[n] 을 지우면(다시 받지 않는다), partURL 에서 '?v=' 를 빼면,
    대기 함수의 '떠난 화면이면 버린다'(curView 비교) 줄을 지우면.
    """
    o, build = _run_loader()
    assert o['statsAppended'] == ['/home-stats.js?v=' + build], o['statsAppended']
    assert o['boxWhileWaiting'] == '', '통계 파일을 기다리는 동안 불러오는 중 표시가 없다'
    assert o['callsBeforeData'] == 0, '그래프 데이터가 오기 전에 통계 함수가 돌았다(투자지표 입력이 아직 없다)'
    assert o['statsCalls'] == [['statsOpen'], ['setStatsMode', 'adv'], ['setStatsMode', 'basic']], o['statsCalls']
    assert o['direct'] == [['setStatsMode', 'more']]
    assert o['quizAppended'] == ['/home-quiz.js?v=' + build], o['quizAppended']
    assert '불러오는 중' in (o['qcardWhileWaiting'] or ''), '퀴즈 파일을 기다리는 동안 불러오는 중 표시가 없다'
    assert o['afterFail']['toast'] and not [c for c in o['afterFail']['calls'] if c[0] == 'startQuiz'], o['afterFail']
    assert o['retryAppended'], '못 받은 뒤 다시 눌러도 퀴즈 파일을 다시 받지 않는다'
    assert o['quizCallsAfterLeave'] == [], '기다리는 사이 떠난 화면의 누름을 도착 뒤에 부른다(화면과 주소가 갈린다)'
    assert o['quizCalls'] == [['startQuiz', 'investor']], o['quizCalls']


SW = r"""
const SRC = %(src)s;
const handlers = {};
const self = {addEventListener: (t, f) => { handlers[t] = f; }, location: {origin: 'https://example.test'},
              skipWaiting() {}, clients: {claim() {}}};
const store = new Map();
const keyOf = (r) => { const u = new URL(typeof r === 'string' ? r : r.url, 'https://example.test'); return u.pathname + u.search; };
const added = [];
const caches = {open: async () => ({put: async (r, v) => { store.set(keyOf(r), v); },
                                    add: async (r) => { added.push(typeof r === 'string' ? r : r.url); }}),
                match: async (r) => store.get(keyOf(r)), keys: async () => [], delete: async () => true};
class Request { constructor(u, o) { this.url = u; this.cache = (o && o.cache) || 'default'; } }
let NET = () => new Promise(() => {});
new Function('self', 'caches', 'fetch', 'Request', SRC)(self, caches, (r) => NET(r), Request);
const resp = (tag) => ({ok: true, status: 200, type: 'basic', tag, clone() { return this; }});
(async () => {
  let inst = null; handlers.install({waitUntil(p) { inst = p; }}); await inst;
  const out = {added, fresh: {}};
  for (const u of %(urls)s) {
    store.clear(); store.set(u, resp('cache'));
    NET = () => new Promise((r) => setTimeout(r, 5, resp('net')));
    let p = null;
    handlers.fetch({request: {url: 'https://example.test' + u, method: 'GET', mode: 'no-cors'}, respondWith(x) { p = x; }});
    out.fresh[u] = p ? (await p).tag : null;
  }
  process.stdout.write(JSON.stringify(out));
})();
"""


def test_sw_precaches_the_parts_at_the_address_home_asks_for():
    """서비스워커가 분할 파일을 홈이 부르는 바로 그 주소('/home-quiz.js?v=<판>')로 사전 캐시하고, 온라인이면 캐시보다
    네트워크를 먼저 쓴다(home-app.js 와 같은 규칙 — 새 판 배포 뒤 옛 캐시가 붙들지 않게).

    재현하는 실제 상태: 오프라인 재방문자가 퀴즈 랜딩의 '시작하기'(/#test-beginner)로 들어온다 — 사전 캐시 주소에 판이
    없거나 판이 다르면 caches.match 가 못 찾아 퀴즈가 안 뜬다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): sw.js PRECACHE 에서 home-quiz.js 줄을 빼면, "+ VERSION" 을 빼고 판 없는
    주소로 넣으면, network-first 목록에서 home-stats.js 를 빼면(정적 자산 분기의 cache-first 가 옛 캐시를 준다).
    픽스처: 저장소 sw.js 의 설치·fetch 처리기 그대로, 판은 home-app.js 의 HOME_BUILD.
    """
    if not shutil.which('node'):
        pytest.skip('node 없음')
    build = re.search(r"const HOME_BUILD='(v\d+)'", _core()).group(1)
    urls = ['/%s?v=%s' % (src, build) for src, _ in _parts_decl().values()]
    src = io.open(os.path.join(ROOT, 'sw.js'), encoding='utf-8').read()
    p = subprocess.run(['node', '-e', SW % {'src': json.dumps(src), 'urls': json.dumps(urls)}], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    o = json.loads(p.stdout.decode('utf-8'))
    miss = [u for u in urls if u not in o['added']]
    assert not miss, '사전 캐시에 홈이 부르는 분할 파일 주소가 없다: %s (사전 캐시 %s)' % (miss, o['added'])
    stale = [u for u, tag in o['fresh'].items() if tag != 'net']
    assert not stale, '온라인인데 분할 파일을 캐시에서 먼저 준다(network-first 가 아니다): %s' % stale


def test_head_preloads_the_part_for_deep_links():
    """퀴즈·통계로 바로 들어오는 주소는 머리에서 그 분할 파일을 같은 판 주소로 preload 한다 — 본문 스크립트가 돈 뒤에야
    받기 시작하면 첫 화면이 한 번 더 기다린다(퀴즈 랜딩 '시작하기', 대결 링크, 블로그 주간 링크).

    무엇을 깨뜨리면 빨개지나(실제로 확인): index.html ⑤ 의 '?v='+b 를 빼면(홈이 부르는 주소와 달라 preload 가 버려진다),
    #stats 분기에서 data-trend.json 을 빼면.
    픽스처: index.html 머리의 ⑤ 스크립트를 node 로 돌린다(주소 셋: #test-beginner, 대결 ?c=&s=, #stats-market).
    """
    if not shutil.which('node'):
        pytest.skip('node 없음')
    html = _files()['index.html']
    head = html[:html.index('</head>')]
    js = [s for s in re.findall(r'<script>(.*?)</script>', head, re.S) if 'home-quiz.js' in s]
    assert len(js) == 1, '머리에서 분할 파일 preload 스크립트를 못 찾았다'
    build = re.search(r'<html[^>]*\bdata-build="(v\d+)"', html).group(1)
    runner = r"""
const vm = require('vm'); const out = {};
for (const [href] of %(cases)s) {
  const u = new URL(href); const links = [];
  const ctx = {location: {hash: u.hash, search: u.search},
    document: {documentElement: {getAttribute: () => %(build)s}, createElement: () => ({}), head: {appendChild: (l) => links.push([l.href, l.as])}}};
  vm.createContext(ctx); vm.runInContext(%(js)s, ctx); out[href] = links;
}
process.stdout.write(JSON.stringify(out));
""" % {'cases': json.dumps([['https://x.test/#test-beginner'], ['https://x.test/?c=7&s=calc&q=1z'],
                             ['https://x.test/?utm_source=naver_blog#stats-market'], ['https://x.test/']]),
       'build': json.dumps(build), 'js': json.dumps(js[0])}
    p = subprocess.run(['node', '-e', runner], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    o = json.loads(p.stdout.decode('utf-8'))
    q, s = '/home-quiz.js?v=' + build, '/home-stats.js?v=' + build
    assert o['https://x.test/#test-beginner'] == [[q, 'script']], o
    assert o['https://x.test/?c=7&s=calc&q=1z'] == [[q, 'script']], o
    assert o['https://x.test/?utm_source=naver_blog#stats-market'] == [[s, 'script'], ['/data-trend.json', 'fetch']], o
    assert o['https://x.test/'] == [], '홈 첫 화면에서 분할 파일을 미리 받는다'
    # 홈이 부르는 주소와 같은가(loadPart 의 partURL, loadFullData 의 주소)
    core = _core()
    assert "function partURL(n){ return PARTS[n].src+'?v='+HOME_BUILD; }" in core
    assert "loadData('/data-trend.json')" in core


def test_home_first_screen_reads_only_core_data():
    """홈 본문 스크립트(home-app.js)가 읽는 ADV·STATS 키가 모두 data-core 에 실린다(B11 다이어트 뒤 ④ 결함 방지).

    투자지표·버블밴드 입력(occupancy·permits·bubble·STATS 전세가율)은 코어에서 빠져 data-trend·data-rest 로만 온다 —
    그 키를 홈 첫 화면 코드가 읽으면 undefined 로 그려진다. 통계 화면 코드(home-stats.js)는 데이터를 기다린 뒤에 돌므로
    검사하지 않는다. 코어 키는 split_data 의 목록에서 센다(홈에 따로 적지 않는다).
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): home-app.js 에 ADV.bubble 을 읽는 줄을 더하면, split_data.CORE_STATS 에서
    '준공' 을 빼면(홈 표가 읽는다).
    픽스처: 저장소의 home-app.js 와 split_data 의 코어 목록. 'weekly'·'monthly'·'blog' 는 split_data 가 따로 굽는 코어 키다.
    """
    core = _strip_js(_core())
    adv = set(re.findall(r'\bADV\.([A-Za-z_]\w*)', core))
    stats = set(re.findall(r"\bSTATS\[\s*'([^']+)'\s*\]", core))
    allowed = set(SD.CORE_ADV) | {'weekly', 'monthly', 'blog'}
    assert adv, 'home-app.js 에서 ADV 읽기를 하나도 못 찾았다 — 이 시험이 헛돈다'
    assert adv <= allowed, '홈 첫 화면 코드가 코어에 없는 ADV 키를 읽는다: %s' % sorted(adv - allowed)
    assert stats and stats <= set(SD.CORE_STATS), '홈 첫 화면 코드가 코어에 없는 STATS 계열을 읽는다: %s' % sorted(stats - set(SD.CORE_STATS))
    for gone in ('occupancy', 'permits', 'bubble'):
        assert gone not in SD.CORE_ADV
    assert '전세가율' not in SD.CORE_STATS
