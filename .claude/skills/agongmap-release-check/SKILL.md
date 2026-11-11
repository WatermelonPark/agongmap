---
name: agongmap-release-check
description: 아공맵 PR 병합 전후 점검 — 병합 뒤 워크플로·GitHub Pages 배포·판 표식·서비스워커 캐시·운영 페이지 응답과 첫 화면 속도(LCP·CLS)를 본다. 큰 PR 병합 뒤나 '배포됐는데 안 바뀐다'는 제보에 쓴다.
---

# 아공맵 배포 점검

운영은 GitHub Pages(`main`), 정식 도메인은 `CNAME`. Netlify 는 미리보기일 뿐이다.

## 병합 전

1. CI 와 같은 조건으로 전체 시험: `python3 -m venv` 에 `pytest pillow` 만 깔고 생성기 여덟 개를 먼저 돌린 뒤
   `GITHUB_ACTIONS=1 python3 -m pytest tools/tests -q`(건너뜀도 실패). 끝나면 생성 산출물을 되돌린다.
2. PR 에 생성 산출물(`data*.js(on)`·`zone/`·`weekly/`·`monthly/`·`city/` 등·sitemap·feed·llms·`share/` 이미지)이 섞이지 않았는지 `git diff --stat` 으로 본다.
3. 홈 HTML·스크립트·app.css 를 바꿨으면 판 표식 다섯 개가 같은 값인지(`test_home_build`), desk.css 를 바꿨으면 손 페이지 `desk.css?v=` 해시(`test_desk`).

## 병합 뒤

1. `main` 의 워크플로: `ci-tests.yml`(시험), `publish-content.yml`(원고), `rebake-outputs.yml`(산출물 재생성)이 초록인지.
   취소는 동시성 때문일 수 있다 — 이 커밋을 포함한 뒤 런이 초록이면 된다.
2. `pages build and deployment` 가 끝났는지.
3. 운영 주소에서 바뀐 것이 보이는지: 홈은 `data-build` 판, 생성 페이지는 다음 배치(예약 13:00 KST, 실제 17시께) 뒤에 바뀐다.
   서비스워커가 옛 판을 들고 있으면 한 번 새로고침해야 한다(판 표식 보호가 작동하는지 확인).
4. 배치가 하루 넘게 멈추면 경보 이슈에 한 통이 간다(`tools/post_alert.sh`) — 그 전에 실행 화면 요약을 본다.

## 첫 화면 속도 측정

Playwright 로 375px(4G 수준으로 `page.route` 지연을 줄 수 있다)과 1280px 에서 잰다:

```js
const lcp = await page.evaluate(() => new Promise(r => {
  new PerformanceObserver(l => { const e = l.getEntries(); r(e[e.length - 1].startTime); })
    .observe({ type: 'largest-contentful-paint', buffered: true });
}));
const cls = await page.evaluate(() => new Promise(r => { let v = 0;
  new PerformanceObserver(l => { for (const e of l.getEntries()) if (!e.hadRecentInput) v += e.value; })
    .observe({ type: 'layout-shift', buffered: true }); setTimeout(() => r(v), 3000); }));
```

기준: LCP 2.5초 이하, CLS 0.1 이하. 홈은 부팅 전후 줄 수가 같아야 한다(`.map-src` 470px 규칙). 같은 조건으로 병합 전후를 견줘 나빠졌으면 원인 커밋을 찾는다.

## 보고 꼴

`항목 · 결과(초록/빨강·잰 값) · 근거 링크` 표, 마지막 줄에 '남은 일'(없으면 없다고).
