# -*- coding: utf-8 -*-
"""속도·접근성 1차(점검후속 개발 ⑦)를 고정한다.

2026-09-15 고객 점검:
  - 페이지 이동이 <button onclick="location.href=…"> 라 인앱 브라우저에서 길게 눌러 열 수 없었다.
  - 지도/그래프/표 전환(약 32px)·세그먼트(약 26~27px)가 손가락 대상으로 작았다.
  - 서비스 워커가 HTML·데이터를 네트워크 우선으로 받되 대기 한도가 없어, 느린 망에서 캐시가 있어도
    빈 화면을 오래 봤다.
  - /monthly/·/moveins/·/jeonse-ratio/ 면책 문구(.disc #8a9599)의 대비가 2.83:1 이었다.

서비스 워커는 문자열이 아니라 **실제 fetch 처리기를 node 로 돌려** 본다. 타임아웃 코드가 있어도
분기에서 안 쓰이면 방어선이 안 돈다 — 이 저장소가 가장 자주 당한 결함 유형이다.
"""
import io
import json
import os
import re
import shutil
import subprocess

import pytest

import sys as _hs_sys  # noqa: E402
_hs_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _read(*p):
    if HS.is_home(*p):
        return HS.home_source()
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def test_no_page_navigation_through_buttons():
    s = _read('index.html')
    HS.require(s, 'function nextStepHTML', 'class="qpick', what='이동 버튼이 있던 퀴즈 템플릿·카드')
    left = re.findall(r'<button[^>]*onclick="[^"]*location\.href[^"]*"', s)
    assert not left, '버튼으로 페이지를 옮기는 곳이 남았다 — <a href> 로: %s' % left


def test_tab_buttons_have_a_40px_minimum():
    css = _read('app.css')
    # 09-15 엔 두 선택자만 잡아 통계 토글(.gt 26px)·심화 탭(34px)·기간(36px)·주석 칩(28px)이 빠졌다(2026-09-18 오딧 2번).
    for sel in (r'\.tb-seg button', r'\.seg button', r'\.gt button', r'\.adv-tabs button', r'\.period button', r'\.aux button'):
        hs = [int(x) for x in re.findall(sel + r'\{[^}]*min-height:(\d+)px', css)]
        assert hs and max(hs) >= 40, '%s 최소 높이가 40px 미만이다' % sel.replace('\\', '')


def test_disclaimer_contrast_uses_the_muted_token():
    assert '#8a9599' not in _read('tools', 'make_indicator_pages.py'), '생성기에 대비 낮은 .disc 색이 남았다'
    for page in (('monthly', 'index.html'), ('moveins', 'index.html'), ('jeonse-ratio', 'index.html')):
        assert '#8a9599' not in _read(*page), '%s 에 대비 낮은 .disc 색이 남았다' % '/'.join(page)


HARNESS = r"""
const SRC = %(src)s;
const handlers = {};
const self = { addEventListener: (t, f) => { handlers[t] = f; }, location: { origin: 'https://example.test' },
               skipWaiting() {}, clients: { claim() {} } };
const store = new Map();
// 실제 Cache API 처럼 문자열·Request 를 같은 URL 로 정규화하고, 쿼리까지 키에 넣는다(쿼리를 떼는 건 sw.js 의 몫).
const keyOf = (r) => { const u = new URL(typeof r === 'string' ? r : r.url, 'https://example.test'); return u.pathname + u.search; };
const added = [];   // 설치(install)가 c.add 에 넘긴 요청 — 주소와 캐시 모드(A9·MOB-4)
const caches = {
  open: async () => ({ put: async (r, v) => { store.set(keyOf(r), v); },
                       add: async (r) => { added.push(typeof r === 'string' ? { url: r, cache: 'default' }
                                                                             : { url: r.url, cache: r.cache }); } }),
  match: async (r) => store.get(keyOf(r)),
  keys: async () => [], delete: async () => true,
};
// 브라우저 Request 처럼 주소·캐시 모드만 담는다. node 의 Request 는 상대 주소('/')를 받지 못한다.
class Request { constructor(u, o) { this.url = u; this.cache = (o && o.cache) || 'default'; } }
let NET = () => new Promise(() => {});
const fetch = (req) => NET(req);
new Function('self', 'caches', 'fetch', 'Request',
             SRC.replace(/const NET_TIMEOUT_MS = \d+;/, 'const NET_TIMEOUT_MS = 60;'))(self, caches, fetch, Request);

const resp = (tag) => ({ ok: true, status: 200, type: 'basic', tag, clone() { return this; } });
const later = (ms, v) => new Promise((r) => setTimeout(r, ms, v));
async function run(path, mode) {
  let p = null;
  const req = { url: 'https://example.test' + path, method: 'GET', mode };
  handlers.fetch({ request: req, respondWith(x) { p = Promise.resolve(x); } });
  if (!p) return { handled: false };
  const t0 = Date.now();
  const r = await Promise.race([p, later(2000, { tag: 'STUCK' })]);
  return { handled: true, tag: r && r.tag, ms: Date.now() - t0 };
}
(async () => {
  const out = {};
  let installing = null;
  handlers.install({ waitUntil(p) { installing = p; } });
  await installing;
  out.install = added;
  for (const [path, mode] of [['/data-core.js', 'no-cors'], ['/zone/', 'navigate']]) {
    store.clear(); store.set(path, resp('cache'));
    NET = () => new Promise(() => {});                       // 응답이 오지 않는 망
    out[path + ' hang+cache'] = await run(path, mode);
    NET = () => later(5, resp('net'));                        // 빠른 망
    out[path + ' fast'] = await run(path, mode);
    store.clear();
    NET = () => later(150, resp('net'));                      // 느린 망, 캐시 없음
    out[path + ' slow+nocache'] = await run(path, mode);
  }
  // 쿼리가 붙은 주소(utm·대결 링크)도 경로 캐시로 응답한다 — 쿼리마다 따로 쌓지 않는다(2026-09-23).
  store.clear(); store.set('/zone/', resp('cache'));
  NET = () => new Promise(() => {});
  out['/zone/?utm hang+cache'] = await run('/zone/?utm_source=blog', 'navigate');
  store.clear();
  NET = () => later(5, resp('net'));
  await run('/burini-test/7/?c=7&s=beginner', 'navigate');
  await later(20);
  out['query nav cache keys'] = { handled: true, tag: [...store.keys()].join(','), ms: 0 };
  store.clear(); store.set('/', resp('home'));
  NET = () => Promise.reject(new Error('offline'));           // 오프라인, 그 문서 캐시 없음 → 홈
  out['/zone/ offline'] = await run('/zone/', 'navigate');
  // ⚠️ 배포 직후의 실제 상태: 홈은 프리캐시돼 있고 그 문서는 없다. 느린 망(한도 초과)이라도
  //    홈으로 바꿔치기하면 안 되고 네트워크를 기다려야 한다(2026-09-16 리뷰에서 잡힌 결함).
  store.clear(); store.set('/', resp('home'));
  NET = () => later(150, resp('net'));
  out['/zone/ slow+home-cached'] = await run('/zone/', 'navigate');
  // 한도를 넘겨 매달렸다가 끝내 끊기는 망, 그 문서 캐시 없음 → 그때는 홈(전수리뷰 #67). 예전엔 거부(브라우저 오류 화면).
  store.clear(); store.set('/', resp('home'));
  NET = () => later(150).then(() => { throw new TypeError('Failed to fetch'); });
  out['/zone/ slow-fail'] = await run('/zone/', 'navigate').catch((e) => ({ handled: true, tag: 'REJECTED ' + e, ms: 0 }));
  process.stdout.write(JSON.stringify(out));
})();
"""


def _sw_run():
    if not shutil.which('node'):
        pytest.skip('node 없음')
    js = HARNESS % {'src': json.dumps(_read('sw.js'))}
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def test_sw_timeout_is_3_to_4_seconds():
    m = re.search(r'const NET_TIMEOUT_MS = (\d+);', _read('sw.js'))
    assert m and 3000 <= int(m.group(1)) <= 4000, '네트워크 대기 한도가 3~4초가 아니다'


def test_sw_serves_cache_when_network_hangs_and_network_when_fast():
    o = _sw_run()
    for path in ('/data-core.js', '/zone/'):
        hang = o[path + ' hang+cache']
        assert hang['tag'] == 'cache', '%s: 망이 멈췄는데 캐시로 응답하지 않았다 — %s' % (path, hang)
        assert o[path + ' fast']['tag'] == 'net', '%s: 빠른 망인데 네트워크 응답을 쓰지 않았다' % path
        assert o[path + ' slow+nocache']['tag'] == 'net', '%s: 캐시가 없는데 네트워크를 기다리지 않았다' % path
    assert o['/zone/ offline']['tag'] == 'home', '오프라인 문서 요청이 홈 캐시로 폴백하지 않았다'
    slow = o['/zone/ slow+home-cached']
    assert slow['tag'] == 'net', '느린 망에서 캐시에 없는 문서를 홈으로 바꿔치기했다 — %s' % slow
    # 전수리뷰 #67: 한도를 넘긴 뒤 끝내 실패한 탐색은 홈으로 폴백한다. 변이: sw.js 의 net.catch(…fallback…) 를 옛
    # `hit || net` 으로 되돌리면 respondWith 가 거부돼 빨개진다(실제로 확인). 픽스처: 홈만 캐시된 배포 직후, 150ms
    # 매달렸다가 끊기는 망(한도 60ms).
    assert o['/zone/ slow-fail']['tag'] == 'home', o['/zone/ slow-fail']


def test_sw_caches_pages_by_path_not_query():
    """페이지를 쿼리째 키로 넣으면 ?utm_…·대결 링크(?c=&s=)마다 캐시 항목이 쌓인다(2026-09-23 점검).
    무엇을 깨뜨리면 빨개지나: sw.js 의 cacheKey 가 req 를 그대로 돌려주게 하면 두 단정 모두 실패한다
    (실제로 확인). 픽스처: 블로그 유입 utm 주소와 퀴즈 대결 링크, 실제 쓰이는 두 형태다."""
    o = _sw_run()
    assert o['/zone/?utm hang+cache']['tag'] == 'cache', '쿼리 붙은 주소가 경로 캐시를 못 찾았다'
    assert o['query nav cache keys']['tag'] == '/burini-test/7/', o['query nav cache keys']


def test_zone_reference_row_buttons_are_40px():
    """시도 리포트 표의 참고 행(미분양·인허가 1년) ⓘ 버튼이 첫 칸 전체·40px 인지 본다.
    재현하는 실제 상태: 2026-09-18 오딧 12번 실측 49×20·70×20px(버튼이 글자 폭만큼만 있었다). 2026-09-23 수정 뒤
    Chromium 375px 에서 88×40px(칸 폭 89px)로 쟀다. 홈 표(#tb-main)는 tfoot 붙박이 설계라 25px 줄높이를 유지한다.
    무엇을 깨뜨리면 빨개지나: app.css 의 `.ztb tfoot .rbtn` 에서 min-height:40px 를 빼거나 width:100% 를 빼면
    빨개진다(실제로 확인). 지역 페이지 생성기가 이 버튼을 tfoot 첫 칸에 두는지도 함께 본다."""
    css = _read('app.css')
    m = re.search(r'\.ztb tfoot \.rbtn\{([^}]*)\}', css)
    assert m, '.ztb tfoot .rbtn 규칙이 없다'
    assert re.search(r'min-height:(4\d|[5-9]\d)px', m.group(1)), '참고 행 버튼의 최소 높이가 40px 미만이다'
    assert 'width:100%' in m.group(1), '참고 행 버튼이 칸 전체를 차지하지 않는다'
    gen = _read('tools', 'make_sido_pages.py')
    assert re.search(r'<tr class="zref"[^>]*><td>%s</td>', gen), '생성기의 참고 행 첫 칸 구조가 바뀌었다 — 이 시험도 고칠 것'
    assert 'refbtn(' in gen


def test_skip_link_has_its_hiding_rule():
    """건너뛰기 링크(<a class="skip">)가 있는 페이지는 그 링크를 평소에 감추는 .skip 규칙을 가져야 한다.
    재현하는 실제 상태: 2026-09-18 2차 작업이 링크를 모든 페이지에 넣었는데 공용 시트를 안 읽는 /weekly/·/faq/·
    /about/·/privacy/ 에는 규칙이 없어, 링크가 늘 왼쪽 위에 밑줄 글자로 떠 있었다(2026-09-23 375·1280px 스크린샷).
    무엇을 깨뜨리면 빨개지나: faq/index.html 에서 .skip{…} 규칙을 지우면 빨개진다(실제로 확인)."""
    import glob
    pages = ['index.html', '404.html'] + sorted(glob.glob(os.path.join(ROOT, '*', 'index.html')))
    bad = []
    for p in pages:
        rel = os.path.relpath(p if os.path.isabs(p) else os.path.join(ROOT, p), ROOT)
        s = io.open(os.path.join(ROOT, rel), encoding='utf-8').read()
        if 'class="skip"' not in s:
            continue
        shared = re.search(r'<link[^>]+href="/app\.css', s)
        if not (shared or re.search(r'\.skip\{[^}]*top:-\d+px', s)):
            bad.append(rel)
    assert re.search(r'\.skip\{[^}]*top:-\d+px', _read('app.css')), '공용 시트에 .skip 규칙이 없다'
    shell = __import__('make_indicator_pages').SHELL
    assert re.search(r'\.skip\{[^}]*top:-\d+px', shell), '지표 생성기 껍데기에 .skip 규칙이 없다'
    assert not bad, '건너뛰기 링크가 늘 보이는 페이지: %s' % bad


def _site_file(url):
    """사이트 주소 → 저장소 파일('/' 는 index.html, '/x/' 는 x/index.html). 쿼리('?v=판', B11 분할 파일)는 뗀다 —
    GitHub Pages 는 쿼리와 무관하게 같은 파일을 준다."""
    rel = url.split('?')[0].lstrip('/')
    if not rel or rel.endswith('/'):
        rel += 'index.html'
    return os.path.join(ROOT, *rel.split('/'))


def test_sw_precache_revalidates_instead_of_reloading():
    """설치가 프리캐시를 'no-cache'(조건부 요청)로 받는지 — 설치 처리기를 node 로 돌려 c.add 에 넘긴 요청을 본다.

    재현하는 실제 상태(홈 마케팅 검수 A9·MOB-4, 2026-09-26): 'reload' 는 HTTP 캐시를 건너뛰고 본문 전체를 다시 받아,
    VERSION 을 올릴 때마다 재방문자가 목록 전체(전송 약 294KB, 그중 158.5KB 는 페이지가 방금 받은 홈 파일)를 또 받았다.
    'no-cache' 는 ETag 로 한 번 묻고 안 바뀐 파일은 304 로 끝나며, 기본 모드와 달리 max-age=600 동안의 옛 자산을
    새 캐시에 집어넣지도 않는다(2026-08-08 제보). 두 가지를 다 만족하는 모드는 'no-cache' 하나다.
    무엇을 깨뜨리면 빨개지나: sw.js 설치의 { cache: 'no-cache' } 를 'reload' 로 되돌리거나 옵션을 빼면(기본 모드)
    빨개진다(둘 다 실제로 확인). 픽스처: 저장소 sw.js 의 설치 처리기 그대로.
    """
    adds = _sw_run()['install']
    assert adds, '설치가 아무것도 프리캐시하지 않았다 — 하네스가 설치 처리기를 못 찾았는지 볼 것'
    bad = ['%s(%s)' % (a['url'], a['cache']) for a in adds if a['cache'] != 'no-cache']
    assert not bad, '프리캐시 요청이 no-cache 가 아니다 — reload 는 배포마다 전부 다시 받고, 기본 모드는 옛 자산을 굳힌다: %s' % bad


def test_sw_precache_is_the_offline_home_only():
    """프리캐시 목록이 '오프라인에서 홈이 뜨는 데 필요한 것'과 같은지 본다(A9·MOB-4).

    ① 홈 HTML 이 부르는 같은 출처 스크립트·스타일시트는 모두 있다 — index.html 에서 세고 손으로 적지 않는다.
    ② 홈이 첫 로딩에서 받지 않는 차트 라이브러리(home-app.js loadChart 의 주소), '/'·404 밖의 페이지(/cycle/·퀴즈),
       512px 아이콘은 없다 — 처음 쓸 때 런타임 캐시가 맡는다.
    ③ 목록의 파일은 저장소에 실제로 있다 — 설치는 실패를 삼키므로(.catch) 이름이 바뀐 파일은 조용히 빠진다.
    재현하는 실제 상태: 2026-09-26 까지 17개(차트 70KB·/cycle/·퀴즈 3종·512px 아이콘 포함)였다.
    무엇을 깨뜨리면 빨개지나(각각 실제로 확인): PRECACHE 에 '/chart-4.4.1.umd.js' 나 '/cycle/' 나
    '/icons/icon-512.png' 를 되살리면 ②, '/app.css' 를 빼거나 '/app2.css' 로 바꾸면 ①, 저장소에 없는
    '/icons/nope.png' 를 넣으면 ③ 이 빨개진다.
    픽스처: 저장소 sw.js 설치 처리기가 실제로 넘긴 요청, index.html·home-app.js(home_source).
    """
    urls = [a['url'] for a in _sw_run()['install']]
    home = _read('index.html')   # 홈 마크업+스크립트(home_source)
    need = set(re.findall(r'<script\b[^>]*\bsrc="(/(?!/)[^"?#]+)"', home))
    need |= set(re.findall(r'<link\b[^>]*rel="stylesheet"[^>]*href="(/(?!/)[^"?#]+)"', home))
    assert {'/home-app.js', '/app.css'} <= need, '홈 HTML 에서 본문 스크립트·스타일시트를 못 읽었다 — 이 시험이 헛돈다: %s' % need
    miss = sorted((need | {'/'}) - set(urls))
    assert not miss, '오프라인 홈에 필요한 파일이 프리캐시에 없다: %s' % miss
    chart = re.search(r"function loadChart\(\)\{.*?loadScript\('(/[^']+)'\)", home, re.S)
    assert chart, 'home-app.js 에서 차트 라이브러리 주소를 못 읽었다'
    extra = [u for u in urls if u == chart.group(1) or (u.endswith('/') and u != '/') or '512' in u]
    assert not extra, '홈 첫 화면이 쓰지 않는 것을 배포마다 다시 받는다: %s' % extra
    ghost = [u for u in urls if not os.path.isfile(_site_file(u))]
    assert not ghost, '프리캐시에 저장소에 없는 파일이 있다(설치가 조용히 건너뛴다): %s' % ghost
