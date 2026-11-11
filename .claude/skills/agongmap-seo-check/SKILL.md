---
name: agongmap-seo-check
description: 아공맵 페이지의 검색·AI 검색 노출 점검(색인·canonical·제목/설명·구조화 데이터·sitemap·robots·llms.txt·내부 링크). 검색 유입 점검, 새 페이지 종류 추가, 제목·설명 메타·JSON-LD·sitemap 을 고칠 때 쓴다.
---

# 아공맵 검색 점검

검색 유입이 주 채널이다(네이버 블로그 종료 뒤 정보 글의 정본은 사이트, 2026-10-26). 점검은 **배치가 구운 페이지**를
대상으로 하고, 고칠 곳은 **생성기**다. 출력물을 손으로 고치면 다음 배치에서 되돌아간다.

## 대상과 고칠 자리

| 페이지 | 굽는 곳 | 제목·설명의 정본 |
|---|---|---|
| 홈 `index.html` | 손 파일 + `make_home_summary.py`(설명 메타·og·twitter) | 표식 구간은 손으로 고치지 않는다 |
| 시도 리포트 `zone/<키>/` | `make_sido_pages.py` | `page_title`·`summary_parts` |
| `/weekly/`·`/monthly/`·`/moveins/`·`/jeonse-ratio/` | `make_weekly_page.py`·`make_monthly_page.py`·`make_indicator_pages.py` | 각 생성기 |
| 콘텐츠 `city/`·`gtx/`·`danji/`·`column/`·`reports/` | `make_content_pages.py`(원고 `content/`) | 원고 머리 `title`·`summary` |
| 손 페이지(소개·FAQ·개인정보·퀴즈·404·`/cycle/` 서술) | 손으로 쓴 HTML | — |
| `sitemap.xml`·`feed.xml`·`llms.txt` | 생성기(lastmod 는 `keep_dates`, KST) | 손으로 고치지 않는다 |

## 점검 순서

1. **로컬에서 굽는다**: `python3 tools/make_sido_pages.py` 등 생성기 여덟 개(CLAUDE.md 순서). 점검이 끝나면 산출물은 되돌린다.
2. **페이지마다 본다**(375px·1280px, `python3 -m http.server 8321` + Playwright):
   - `<title>` 한 개, 30자 안쪽에 검색어가 앞, 결론이 뒤(블로그 제목 규칙과 같은 꼴). 지역 이름은 화면 이름(`SZ.disp` — '광주·전남').
   - `meta description` 한 개, 본문 첫 문단과 같은 사실(시도 리포트는 `summary_parts` 한 목록에서 나온다).
   - `link rel=canonical` 이 자기 자신(퀴즈 점수 페이지는 랜딩으로).
   - robots 메타 정확히 하나(`tools/robots_meta.py`, `test_robots_meta`).
   - JSON-LD: `@type` 이 페이지 종류에 맞는지(Article·Dataset·FAQPage·WebPage), `dateModified` 는 내용이 바뀐 날이지 데이터 시점이 아니다.
   - `h1` 한 개, 제목과 같은 답. 숫자는 화면 숫자 정본(`sido_zones`)과 같다.
3. **사이트 전체**: sitemap 의 모든 주소가 200 이고 noindex 가 아니다. 새 페이지 종류는 sitemap·`llms.txt`(숫자 없이)·RSS 에 들어갔는지. 바뀐 주소만 IndexNow(`ping_indexnow.py --changed`).
4. **내부 링크**: 시도 리포트 ↔ 그 지역 글('이 지역 글'), 글 끝 '이 지역 더 보기' 상자, 허브 칩. 고아 페이지가 없는지.
5. **속도**: 첫 화면 LCP·CLS 는 `agongmap-release-check` 의 측정 절차를 쓴다.

## 지키는 선

- 지역 수·시군구 수는 데이터에서 센다(박지 않는다). 제목에 숫자를 넣으면 생성기가 정본 함수로 만든다.
- 사이트와 블로그·피드가 같은 숫자를 말한다(블로그 도구는 재계산하지 않는다).
- 검색어용 문구를 본문에 억지로 반복하지 않는다. 한 페이지는 한 검색 의도.
- 고친 뒤에는 `test_search_titles`·`test_robots_meta`·`test_llms_txt`·`test_feed` 와 해당 생성기 시험을 돌리고, 새 규칙은 시험으로 잠근다(변이·픽스처를 독스트링에).

## 보고 꼴

페이지 종류별로 `문제 · 근거(실제 글자) · 고칠 생성기·함수 · 시험` 한 줄. 고칠 것이 없으면 없다고 적는다.
