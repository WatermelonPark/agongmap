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
const caches = {
  open: async () => ({ put: async (r, v) => { store.set(keyOf(r), v); }, add: async () => {} }),
  match: async (r) => store.get(keyOf(r)),
  keys: async () => [], delete: async () => true,
};
let NET = () => new Promise(() => {});
const fetch = (req) => NET(req);
new Function('self', 'caches', 'fetch', SRC.replace(/const NET_TIMEOUT_MS = \d+;/, 'const NET_TIMEOUT_MS = 60;'))(self, caches, fetch);

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


def test_sw_caches_pages_by_path_not_query():
    """페이지를 쿼리째 키로 넣으면 ?utm_…·대결 링크(?c=&s=)마다 캐시 항목이 쌓인다(2026-09-23 점검).
    무엇을 깨뜨리면 빨개지나: sw.js 의 cacheKey 가 req 를 그대로 돌려주게 하면 두 단정 모두 실패한다
    (실제로 확인). 픽스처: 블로그 유입 utm 주소와 퀴즈 대결 링크, 실제 쓰이는 두 형태다."""
    o = _sw_run()
    assert o['/zone/?utm hang+cache']['tag'] == 'cache', '쿼리 붙은 주소가 경로 캐시를 못 찾았다'
    assert o['query nav cache keys']['tag'] == '/burini-test/7/', o['query nav cache keys']
