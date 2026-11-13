---
name: agongmap-a11y-check
description: 아공맵 화면 접근성 점검(글자 하한 14·13px, 대비 4.5:1, 색만으로 뜻 전하기 금지, 키보드 초점, 누름 면, 그림 대체 텍스트). 새 화면 요소를 넣거나 디자인 검수·색 변경 뒤에 쓴다.
---

# 아공맵 접근성 점검

WCAG 2.2 AA 를 기준으로 하되, 이 저장소가 이미 정한 정본과 시험을 먼저 따른다.

## 정본

| 항목 | 정본 | 시험 |
|---|---|---|
| 글자 하한 | 읽는 문장 14px(`site_nav.READ_PX`), 라벨·칸·칩 13px(`LABEL_PX`). SVG 지도 라벨·축 눈금·표 보기 표·사이클 도식은 제외 | `test_home_min_font`·`test_view_min_font`·`test_page_min_font`·`test_hand_reading_font` |
| 틀 강조색 | `site_nav.BRAND_TOKENS`(남색·형광) — 데이터 그림에는 쓰지 않는다 | `test_brand_color` |
| 데이터 색 | 등락 글자 `UP_INK`·`DN_INK`, 그래프 계열 `SERIES_COL`(매매 빨강·전세 보라·공급 초록) | `test_brand_color`·`test_home_stats_design` |
| 대비 | 글자 4.5:1, 그래프 선 3:1. 시군구 지도의 진한 칸(알파 `make_weekly_page.MAP_INK_A` 이상, 홈 `INK_A` 가 거울) 숫자는 먹색, 계열색은 글자·선에만 진한 변형 | `test_a11y_1112`·`test_sgg_map` |
| 키보드 초점 | 탭바 `NAV_FOCUS_CSS`, 건너뛰기 링크 `.skip`, 초점이 하단 탭바 밑에 숨지 않게 `NAV_SCROLL_PAD_CSS`(1023px 이하) | `test_site_nav`·`test_speed_a11y` |
| 누름 면 | 단추·전환·접는 칸·따로 선 링크 40px 이상(`/weekly/` 는 `a.go40`). 표 칸·푸터·본문 안 글자 링크는 둘레 간격으로 24px 기준 | `test_speed_a11y` |

## 점검 순서

1. 대상 페이지를 375px·1280px 로 연다(Playwright, `deviceScaleFactor` 1).
2. **대비**: 보이는 글자마다 계산된 글자색과 실제 바탕(조상 배경을 따라 올라간다)의 대비를 잰다. 일반 글자 4.5:1, 18px 이상 굵은 글자 3:1. 칠한 칸 위 글자(지도 칸·칩)는 그 칸 바탕으로 잰다.
3. **색만으로 뜻을 전하지 않는다**: 등락은 부호(+/−)나 '▲▼'가, 판정은 '부족·균형·여유' 글자가, 신호등은 '적음·보통·많음' 글자가 함께 있어야 한다.
4. **키보드**: Tab 으로 탭바·모드 단추·보기 전환·접는 칸(`details`)을 차례로 돌며 초점이 보이는지, 초점이 숨은 요소에 들어가지 않는지.
5. **그림**: 콘텐츠 SVG 는 `role="img"`·`aria-label`, 이미지는 `alt`. 안에 링크가 있는 SVG(시군구 지도·`/cycle/` 순환 도식)는 `role="img"` 를 달지 않고 `role="group"` 이다(`test_no_links_inside_an_img_role_svg`). 지도 칸 링크는 지역 이름을 읽는다.
6. **움직임**: `prefers-reduced-motion` 에서 스크롤·전환 애니메이션이 멈추는지.
7. **넘침**: 375px 에서 가로 스크롤이 생기는 곳(넓은 표는 그림자 단서가 있는 스크롤 상자 안이어야 한다).

## 고칠 때

- 공용 클래스는 `#view-home` 으로 덮어 다른 페이지를 바꾸지 않는다. 데스크톱 배치는 `desk.css` 한 곳.
- 홈 HTML·스크립트·app.css 를 바꾸면 판 표식 다섯 개(sw.js `VERSION`·`index.html` data-build·`HOME_BUILD`·`HOME_QUIZ_BUILD`·`HOME_STATS_BUILD`)를 함께 올린다.
- desk.css 를 바꾸면 손 페이지의 `desk.css?v=` 해시를 고친다(`test_desk` 가 알린다).
- 새 규칙은 시험으로 잠그고, 무엇을 깨면 빨개지는지 실제로 깨뜨려 본 뒤 독스트링에 적는다.

## 보고 꼴

`페이지 · 요소 · 문제(잰 값) · 기준 · 고칠 곳` 표. 심각도는 '읽지 못함 > 헷갈림 > 다듬기' 순.
