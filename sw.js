/* 아공맵(agongmap) service worker
   - HTML(navigation): network-first  → 배포 즉시 반영, 오프라인이면 캐시
   - 정적 자산: cache-first (+백그라운드 갱신)
   - 외부 도메인(GA·카카오 SDK)은 건드리지 않음
*/
// ⚠️ 올릴 때는 **현재 값을 읽어** +1 한다. 기억한 숫자를 박으면 그 사이 다른
// 세션이 올려둔 버전을 덮어 뒤로 돌아간다 — 2026-08-15에 v107을 v102로 되돌린
// 실사고가 그렇게 났다(sed로 패턴을 잡아 하드코딩 값으로 치환). 되돌아간 번호는
// 배포 이력을 못 읽게 만들고, 다음 사람이 이미 쓴 번호를 재사용하게 한다.
// 단조 증가는 test_sw_version_only_moves_forward가 지킨다.
// ⚠️ 이 값은 홈의 **판 표식**이기도 하다(C11·MOB-9). 올리면 index.html 의 <html data-build> 와
// home-app.js 의 HOME_BUILD, home-quiz.js 의 HOME_QUIZ_BUILD, home-stats.js 의 HOME_STATS_BUILD 도 같은 값으로 바꾼다
// — 하나라도 다르면 test_home_build 가 빨개진다.
const VERSION = 'v165'; // 홈 작은 글씨 정리(2026-09-28 대표 결정): 띠 둘째 줄·분포 한 줄·범례 뜻 한 줄·운영 주체 줄·출처 줄·블로그 이웃 안내·방향이 바뀐 곳 줄·격자 전세 값을 빼고, 남은 홈 글자를 13px 이상으로
const CACHE = `agongmap-${VERSION}`;

// 네트워크 우선 요청의 대기 한도(2026-09-15 점검 후속 ⑦). 느린 망에서 응답이 늦으면 캐시가
// 있는데도 빈 화면을 오래 본다. 이 시간을 넘기면 캐시로 먼저 응답하고, 늦게 온 네트워크 응답은
// 뒤에서 캐시만 갱신한다. ⚠️ 캐시가 없으면 네트워크를 끝까지 기다린다 — 빈 응답보다 늦은 응답이 낫다.
// ⚠️ res.ok 를 봐야 한다. 404/5xx 본문(에러 HTML)이 캐시에 들어가면 정상 프리캐시본을 덮고, 그 뒤
//    오프라인 폴백이 쓰레기를 준다(2026-08-07 감사에서 격리 재현).
// ⚠️ fallback(홈 '/' 캐시)은 **오프라인(fetch 거부)에서만** 쓴다. 타임아웃까지 fallback 으로 내리면
//    홈은 항상 프리캐시돼 있으므로, 캐시에 없는 문서(/weekly/·/zone/서울/)가 느린 망에서 3.5초 뒤
//    **홈 HTML 로 바꿔치기**된다(2026-09-16 리뷰에서 처리기를 돌려 재현). 타임아웃은 그 요청의
//    캐시만 쓰고, 없으면 네트워크를 끝까지 기다린다.
const NET_TIMEOUT_MS = 3500;
// 페이지(navigation)는 쿼리를 뺀 경로로 캐시한다. 쿼리를 키에 넣으면 ?utm_…·대결 링크(?c=&s=)·광고
// 클릭 파라미터마다 같은 페이지가 따로 쌓여 VERSION 을 올릴 때까지 캐시가 계속 커진다(2026-09-23
// 점검). 페이지 본문은 쿼리와 무관하고 쿼리는 스크립트가 location 에서 읽으므로 경로 키로 충분하다.
function cacheKey(req) {
  if (req.mode !== 'navigate') return req;
  const u = new URL(req.url);
  return u.origin + u.pathname;
}
function networkFirst(req, fallback) {
  const key = cacheKey(req);
  const net = fetch(req).then((res) => {
    if (res && res.ok) {
      const copy = res.clone();
      caches.open(CACHE).then((c) => c.put(key, copy)).catch(() => {});
    }
    return res;
  });
  const timer = new Promise((resolve) => setTimeout(resolve, NET_TIMEOUT_MS, 'timeout'));
  return Promise.race([net.catch(() => 'error'), timer]).then((first) => {
    if (first !== 'timeout' && first !== 'error') return first;
    return caches.match(key)
      .then((hit) => hit || (first === 'error' && fallback ? fallback() : undefined))
      .then((hit) => hit || net);
  });
}

// 프리캐시는 **오프라인에서 홈이 뜨는 데 필요한 것**만 둔다(2026-09-27 홈 마케팅 검수 A9·MOB-4).
// VERSION 을 올릴 때마다 설치가 이 목록 전체를 다시 받는다. 예전엔 차트 라이브러리(전송 70KB)·/cycle/·퀴즈
// 3종·512px 아이콘까지 17개(전송 약 294KB)를 받아, 재방문자가 배포마다 백그라운드에서 그만큼 모바일 데이터를
// 썼다 — 홈은 차트 라이브러리를 첫 로딩에서 받지도 않는다(home-app.js 머리 주석). 뺀 것은 처음 쓸 때 아래
// fetch 처리기가 런타임 캐시에 넣는다(페이지는 탐색 분기, 차트 라이브러리·아이콘은 정적 자산 분기).
// 오프라인에서 한 번도 안 연 /cycle/·퀴즈는 홈으로 폴백한다(탐색 분기의 fallback). 시험: test_speed_a11y 의 test_sw_precache_*.
const PRECACHE = [
  '/',
  '/data-core.js',   // 홈이 실제로 읽는 것
  '/sido-geo.js',    // 홈 지도 모드 경계(기본 모드라 프리캐시)
  '/app.css',
  '/home-app.js',   // 홈 본문 스크립트(2026-09-16 index.html 에서 분리) — HTML 과 한 몸이라 network-first
  // 퀴즈·통계 화면 코드(B11·MOB-8 코드 분할). 홈이 그 화면을 열 때 '?v=<HOME_BUILD>' 를 붙여 받으므로(home-app.js
  // loadPart) 같은 주소로 넣는다 — VERSION 과 HOME_BUILD 는 같은 값이다(test_home_build). 오프라인에서 #test-… 로 들어와도
  // 퀴즈가 뜬다. 주소에 판이 붙어 있어 VERSION 을 올리면 두 파일은 새로 받는다(전송 약 40KB, test_home_parts).
  // 두 파일 안의 판 표식(HOME_QUIZ_BUILD·HOME_STATS_BUILD)도 VERSION 과 같이 올린다(test_home_build).
  '/home-quiz.js?v=' + VERSION,
  '/home-stats.js?v=' + VERSION,
  '/404.html',
  '/favicon.svg',
  '/app_icon.png',
  '/icons/icon-192.png',
  '/icons/maskable-192.png',
];

self.addEventListener('install', (e) => {
  e.waitUntil(
    caches.open(CACHE)
      // 일부 자원이 실패해도 설치가 깨지지 않도록 개별 처리.
      // ⚠️ cache:'no-cache' — 기본 모드면 c.add()가 **브라우저 HTTP 캐시**를 그대로 탄다.
      //    GitHub Pages가 max-age=600을 주므로, 배포 직후 VERSION을 올려 설치되는
      //    회차가 옛 자산을 집어 새 캐시에 넣을 수 있다. 그러면 cache-first 자산은
      //    다음 VERSION 범프까지 스테일이 굳는다(2026-08-08 디자인 세션 제보).
      //    'no-cache' 는 HTTP 캐시에 있어도 서버에 한 번 묻는다(ETag 조건부 요청) — 스테일은 똑같이 막고,
      //    안 바뀐 파일은 304 로 끝난다. 예전 'reload' 는 매번 본문 전체를 다시 받아, 페이지가 방금 받은
      //    홈 파일 다섯 개까지 배포마다 두 번 받았다(2026-09-27 A9·MOB-4). 시험: test_sw_precache_*.
      .then((c) => Promise.all(PRECACHE.map(
        (u) => c.add(new Request(u, { cache: 'no-cache' })).catch(() => null))))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (e) => {
  e.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

// 서비스워커가 손대지 않는 같은 출처 경로(fetch 처리기 참조). 시험(test_feed)이 /feed.xml 이 여기 있는지 본다.
const NO_SW = new Set(['/feed.xml', '/sitemap.xml', '/robots.txt']);

self.addEventListener('fetch', (e) => {
  const req = e.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return; // GA·카카오 등은 통과
  // 새 소식 피드(/feed.xml, 배치가 굽는 RSS)·sitemap·robots 는 가로채지 않는다(홈 마케팅 검수 D1). 아래 cache-first 에
  // 떨어지면 옛 판을 주고, 탭에서 열면 navigate 폴백이 홈을 준다 — 늘 네트워크의 그 파일이어야 한다.
  if (NO_SW.has(url.pathname)) return;

  // data.js·app.css: HTML과 한 몸이라 network-first.
  //  - data.js를 cache-first로 두면 통계가 stale 된다.
  //  - app.css는 원래 HTML 인라인이라 마크업과 원자적으로 배포됐다. 외부화 후
  //    cache-first로 두면 새 마크업 + 옛 CSS가 한 박자 공존해 색 토큰을 바꿀 때
  //    깨진 중간 상태가 보인다. 그 원자성을 유지한다.
  //  - chart-4.4.1.umd.js는 파일명에 버전이 박혀 있어 cache-first로 안전하다.
  // 정적 자산 규칙보다 반드시 먼저 판정할 것.
  //  - sido-geo.js는 여기 넣지 않는다(2026-08-10 리뷰로 정정). 아래 정적 자산
  //    분기가 '캐시 즉시 응답 + 백그라운드 갱신'이라 재생성분은 다음 방문에
  //    따라온다 — 경계선이 한 방문 늦는 건 데이터 스테일과 달리 무해하고,
  //    network-first로 두면 파서 블로킹 스크립트가 매 방문 네트워크 왕복을 기다린다.
  // - home-app.js 는 index.html 에서 떼어낸 본문 스크립트다. app.css 와 같은 이유로 마크업과 함께 받는다.
  // - home-quiz.js·home-stats.js 는 home-app.js 에서 떼어 낸 화면 코드다(B11). 같은 이유로 함께 받는다 — 판(?v=)이 붙은
  //   주소째로 캐시하므로 네트워크가 늦어 캐시로 내려도 같은 판 파일만 나온다.
  if (url.pathname === '/data.js' || url.pathname === '/app.css' || url.pathname === '/home-app.js'
      || url.pathname === '/home-quiz.js' || url.pathname === '/home-stats.js'
      || url.pathname === '/data-core.js' || url.pathname === '/data-rest.json'
      || url.pathname === '/data-size.json'
      || url.pathname === '/data-trend.json' || url.pathname === '/data-sgg.json') {
    e.respondWith(networkFirst(req));
    return;
  }

  // HTML 문서: network-first
  if (req.mode === 'navigate') {
    e.respondWith(networkFirst(req, () => caches.match('/')));
    return;
  }

  // 정적 자산: cache-first + 백그라운드 갱신
  e.respondWith(
    caches.match(req).then((hit) => {
      const network = fetch(req)
        .then((res) => {
          if (res && res.status === 200 && res.type === 'basic') {
            const copy = res.clone();
            caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
          }
          return res;
        })
        .catch(() => hit);
      return hit || network;
    })
  );
});
