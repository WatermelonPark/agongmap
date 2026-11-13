# 아공맵 (aptweather) 작업 지침

아파트 공급 지도. 국가 통계(KOSIS·부동산원 R-ONE·한국은행 ECOS·공공데이터포털)를 그대로 가져와
시도·시군구 단위 공급 판정과 시세를 보여주고, 그 숫자로 쓴 글(`content/` 원고)을 싣는 정적 사이트다. 운영 배포는
**GitHub Pages**(`main`)이며 정식 도메인은 `CNAME`에 있는 것이다. PR에 붙는 Netlify(`aptweather`)는 병합 전 확인용
미리보기일 뿐 운영 사이트가 아니다. **이 저장소는 공개 저장소다.** 아래 "공개 저장소 규칙"을 먼저 읽는다.

## 공개 저장소 규칙 (하드 룰)

- 개인 인명을 적지 않는다. 타겟 사용자 집단은 "부동산 스터디 커뮤니티"처럼 집단명으로만 쓴다.
  예외는 하나다 — 공직자·정치인의 **공개 발언을 검증하는 `content/column/` 글**은 발언자 이름을 적는다(그 섹션의 설계,
  `make_content_pages` 의 '발언 검증'). 그 밖의 문서·코드·커밋 메시지에는 적지 않는다.
- 저장소 밖 로컬 경로(원고 폴더, 강의 아카이브, 키 파일 경로 등)를 문서·코드·커밋 메시지에 적지 않는다.
- 공인 IP, API 키, 개인 이메일을 적지 않는다. 키는 환경 변수로만 읽는다(`KOSIS_API_KEY`, `RONE_API_KEY`,
  `ECOS_API_KEY`, `DATA_GO_KR_KEY`). 키 파일 경로도 코드·문서에 적지 않는다(1회성 도구도 환경 변수로만 읽고, 비상용 bat 은
  `AGONGMAP_KEYS` 환경 변수로 경로를 받는다 — `test_no_local_paths`). 서비스 대표 주소 `agongmap@gmail.com`은 개인 이메일이
  아니라 공개 연락처이므로 소개·개인정보·푸터에 적어도 된다(2026-09-18 대표 결정).
- 특정 전문가·강의를 출처로 인용하지 않는다. 출처는 기관명(국토교통부, 한국부동산원, 기획재정부 등)만 쓴다.
  개념은 배우더라도 **우리 공개 데이터로 검증해 우리 근거로** 만든다.

## 구조

| 위치 | 내용 |
|---|---|
| `index.html`, `app.css`, `data.js`, `data-core.js`, `data-*.json` | 홈과 데이터 페이로드. 데이터는 `data.js`의 `ADV_DATA` 블록을 배치가 갈아끼우고 `tools/split_data.py`가 `data-core.js`·`data-*.json`으로 쪼갠다. `index.html`은 손으로 쓰는 파일이지만 표식 구간 셋과 설명 메타는 도구가 쓴다(손으로 고치지 않는다): `HOME_SUMMARY`와 description·og·twitter 설명 메타(`make_home_summary.py`, 매 회차), `CONTENT_RECENT`(최근 글 묶음, `make_content_pages.py`), `HOME_FONT`(글꼴 서브셋, `make_home_font.py` — 사람이 돌림) |
| `home-app.js`, `home-quiz.js`, `home-stats.js` | 홈 본문 스크립트. 퀴즈·통계 화면 코드는 `home-quiz.js`·`home-stats.js`로 떼어 필요할 때 받는다(`home-app.js`의 `PARTS` 대기열 — 입구 함수 이름은 `test_home_parts`가 맞물림을 본다). **도구·시험은 이 파일들을 직접 열지 말고 `tools/home_src.py`의 `home_source()`(이어 붙인 전체)·`home_files()`(파일별)로 읽는다**(`test_home_src`). 화면 동작 규칙은 아래 "홈·시세 탭 동작" |
| `webfonts/` | 홈 첫 화면 글꼴 서브셋(`make_home_font.py`, 사람이 돌림 — fonttools·brotli 필요). 홈 문구에 새 글자를 넣으면 다시 돌린다(`test_home_font`가 알린다). 루트 `fonts/`는 카드 도구 자리라 쓰지 않는다 |
| `desk.css` | 데스크톱 틀(1024px 이상). 모든 탭바 페이지가 `site_nav.desk_link()`(주소에 내용 해시)를 `media="(min-width:1024px)"`로 싣고 `<body data-desk="종류">`로 배치를 고른다 — read(글 단 그대로)·wide(표 단 넓힘)·doc(왼쪽 목차 `.dtoc`)·report(시도 리포트: 왼쪽 머리·오른쪽 표)·weekly(왼쪽 결론+지도·오른쪽 순위)·home. 규칙은 모두 `body[data-desk]` 아래라 1023px 이하와 표지 없는 페이지는 그대로다. **desk.css 를 고치면 해시가 바뀌어 손 페이지 링크의 `v=`도 고친다**(`test_desk`가 알린다). 위 내비 높이는 홈 `app.css`와 같은 52px. 시도 리포트 머리는 960px 이상 창에서만 붙고 화면보다 길면 머리 안에서 내려 읽으며, `/weekly/` 머리는 붙이지 않는다(`test_desk.test_sticky_heads_fit_the_window`). `audit_design.py`가 desk.css 를 따로 감사한다 |
| `sw.js` | 서비스워커. **홈 HTML·스크립트·app.css 를 바꾸는 배포는 판 표식 다섯 개를 같은 값으로 올린다**: `sw.js`의 `VERSION`, `index.html`의 `<html data-build>`, `home-app.js`의 `HOME_BUILD`, `home-quiz.js`의 `HOME_QUIZ_BUILD`, `home-stats.js`의 `HOME_STATS_BUILD`(`test_home_build`). 느린 망에서 새 HTML과 옛 스크립트가 섞이면 한 번 새로고침하는 표식이다. 분할 스크립트는 `?v=판` 주소로 받고 사전 캐시해 옛 판 파일이 새 홈에 섞이지 않고, 파일 안의 판 표식을 홈이 견줘 열어 둔 옛 판 탭이 새 판 파일을 받으면 한 번 새로고침한다(GitHub Pages 는 쿼리를 무시한다). GA 사용자 속성 `home_variant`(`HOME_VARIANT`)는 홈 구성을 크게 바꾸는 배포에서만 새 값으로 바꾼다 |
| `zone/`(시도별 리포트), `weekly/`, `monthly/`, `moveins/`, `jeonse-ratio/` | 생성 페이지(데이터). 손으로 고치지 말고 생성기를 고친다 |
| `content/` | **글 원고의 정본**(`content/<섹션>/<slug>.md`, 섹션은 `city`·`gtx`·`danji`·`column`). 규칙은 `content/README.md`, 아래 "콘텐츠 원고" |
| `city/`, `gtx/`, `danji/`, `column/`, `reports/` | 생성 페이지(글). 원고에서 `make_content_pages.py`가 굽는다. `/reports/`는 네 섹션을 모은 허브(하단 탭 '콘텐츠') |
| `cycle/` | 서술은 손으로 쓴 문서이고, `refresh_cycle_data.py`가 매 회차 차트 데이터(zones·rate_overlay·jratio_level·flow_chain·super.stock30)와 data-d 칸·`const ZN`·머리 메타의 'N개 시도 M년' 햇수(`RC.span_years` — RC 는 `rebuild_cycle_analysis`)를 다시 쓴다. D 에 싣는 하위 필드는 `rebuild_cycle_analysis.SHIP_FIELDS`가 정본이다. 고리 절 손 문장의 전제는 `RC.claim_breaks`가 보고, 재산정 `--write`는 전제가 깨지면 쓰지 않는다 — 문장을 고치면 claim_breaks 도 같이 고친다. 탭이 없고 입구는 `/reports/` 허브 '기본 개념' 줄이다 |
| `share/` | 공유 이미지. 주간·월간 카드(`weekly-map.png`·`monthly-card.png`)와 글 카드(`post-*`·`thumb-*`, `make_content_cards.py`)는 **CI 가 굽는다**(배치와 원고 발행 워크플로, 게이트 앞). 지역·퀴즈 카드(`make_zone_cards.py` 등)는 지역 구성이나 문항이 바뀔 때 사람이 돌린다 |
| 퀴즈 3종(`burini-test/`, `investor-test/`, `redev-test/`) | 랜딩은 손으로 쓴 파일, 점수별 하위 페이지(`/0/`~)는 `make_quiz_share_pages.py`가 만든다(사람이 돌리고 커밋한다). 퀴즈 정본 읽기는 `home_src.quiz_len()`·`quiz_grades()`·`quiz_grade_of()` 하나로 하고, 손으로 적은 'N문항'은 `test_every_quiz_count_follows_quiz_len`이 대조한다 |
| `about/`, `faq/`, `privacy/`, `404.html` | 손 페이지. GA 이벤트를 더하거나 보내는 값을 바꾸면 개인정보처리방침의 전송 목록 표(`#ga-events`)도 고친다(`test_privacy_ga_events`가 코드의 모든 GA 호출과 대조). 목록은 '사이트 코드가 보내는 이벤트'이고 GA 자동 수집은 `#ga-auto` 한 줄로 밝힌다. 목록을 고치면 변경 이력에 오늘 날짜 줄(`data-ga` 지문)을 더하고 '최근 개정'도 고친다(`test_privacy_history_follows_the_event_table`) |
| `tools/` | 배치·생성기·점검 도구 (아래 표) |
| `tools/tests/` | pytest. 배치가 커밋 직전에 게이트로 돌린다. 시험 중 블로그 초안 도구(make_naver_post·make_theory_post·make_city_post)의 쓰기 자리(OUT·STATE)는 conftest 의 autouse 픽스처 `_drafts_out_of_repo`가 임시 폴더로 돌리고, 저장소 쓰기 감시가 gitignore 폴더 `drafts/`도 파일마다 본다 — 초안 도구에 새 쓰기 자리 상수를 두면 conftest 의 `_DRAFT_TOOLS`에도 올린다(`test_repo_write_guard`) |
| `tools/data/` | 시딩 데이터·캐시·스탬프. 도시 입주물량 `city_moveins.json`·블로그 최신 글 `blog_latest.json`·`.home_stamp`는 배치가 커밋한다. `tools/cache/`와 벌크 원본은 gitignore |
| `docs/` | 요청서·결정 기록·백로그. 날짜 접두 파일명. 목록은 `docs/README.md`, 종결된 문서는 `docs/archive/`로 옮긴다 |
| `.github/workflows/` | 워크플로 열 개 (아래 "워크플로" 표) |
| `.claude/skills/`, `.claude/agents/` | 이 저장소 규칙에 맞춘 점검 스킬 다섯(`agongmap-seo-check`·`-a11y-check`·`-click-path-audit`·`-release-check`·`-design-polish`)과 리뷰 에이전트 둘(`agongmap-python-reviewer`·`agongmap-test-analyzer`). 공개 플러그인의 점검 항목을 참고해 우리 정본·시험 이름으로 새로 썼다(원문 복사는 저작권 고지에 개인 이름이 들어가 하지 않았다). 클라우드 세션은 플러그인을 불러오지 않지만 이 폴더는 읽는다. **정본 이름이 바뀌면 여기도 고친다** |
| `icons/`, `art_raw/` | 앱 아이콘 산출물과 그 원본 그림 |
| `drafts/`, `logs/` | **로컬 전용(gitignore)**. 블로그 초안과 배치 로그. 클라우드 세션에서는 보이지 않는다 |

### 워크플로

| 파일 | 언제 돈다 | `main`에 커밋 | 실패하면 |
|---|---|---|---|
| `update-cloud.yml` | 예약(KST): 매일 13:00, 목요일 07·10·11·12·16시. GitHub 대기열 탓에 **실제 시작은 4~9시간 늦다**. 손으로도 돌린다 | 데이터·산출물(`stats-bot`) | 하루 넘게 멈추면 메일 한 통 |
| `update-cloud-retry.yml` | 러너 3개가 모두 프리플라이트에 실패하면 35분 뒤 배치를 다시 부른다 | — | — |
| `publish-content.yml` | `content/`나 생성기 경로가 바뀐 `main` 푸시 | 산출물(글 페이지·카드 등) | 메일 없음 — **병합한 세션이 실행 결과를 본다** |
| `rebake-outputs.yml` | 그 밖의 모든 `main` 푸시(발행 워크플로를 그대로 부른다) | 산출물 | 메일 없음 — 위와 같다 |
| `ci-tests.yml` | PR, `main` 푸시, 매일 22:17 예약 | — | PR 은 빨간 체크, 예약 실패는 `nightly-alert.yml` |
| `nightly-alert.yml` | 예약 시험이 실패로 끝났을 때(`workflow_run`) | — | 메일 한 통(경보 이슈 코멘트) |
| `watchdog.yml` | 매일 18:07 예약 — 라이브 데이터를 원천과 대조 | — | 판정 실패면 메일 한 통 |
| `runner-trial.yml` | 주 1회·수동 — 같은 시험을 다음 러너 판(26.04)에서 | — | 실행 화면에만 남는다 |
| `write-reminder.yml`, `publish-check.yml` | 휴면(블로그 발행 종료). 예약 없음, 손으로만 | — | — |

그래서 **PR 을 병합하면 몇 분 안에 `main`이 봇 커밋으로 전진한다**(산출물 재생성). 다음 작업은 `git fetch` 뒤 최신 `main`에서 시작한다.
`publish-content.yml`의 `paths`와 `rebake-outputs.yml`의 `paths-ignore`는 같은 목록이어야 하고, 발행 커밋 대상은 배치 커밋 대상(TARGETS)의 부분집합이어야 한다(`test_batch_parity`).

### 주요 도구

| 도구 | 역할 |
|---|---|
| `update_adv_data.py --update` | 원천 API에서 데이터를 받아 `data.js`를 갱신. 키가 필요하다(키 없이는 pytest로 검증한다). 매매·전세지수의 기준시점이 바뀌면 옛 계열에 이어 붙이지 않고 **스스로 전 기간을 다시 받는다**(`_basis_reason`·`refetch_basic_full`, 연결계수 금지 — 2026-09-30 대표 결정). 받지 못하면 그 계열만 보류하고 `.fetch_failed`에 '기준변경 보류'를 남긴다. 월간 응답에서 시도 값(매매·전세)이 전부 빈 달(원천이 시도 이름·계층을 바꾼 회차)은 싣지 않는다 — 저장분에 있던 달은 저장값을 지키고 새 달은 시도·서울구·시군구 세 블록 모두에서 보류한다(`_hold_sido_empty`, 'monthly:시도 결측 보류'). 지수 단절 판정의 정본은 `index_breaks`(`BREAK_JUMP`·`BREAK_REGIONS`)이고 사이클 재산정·`/cycle/` 보류·블로그 도구가 같은 함수를 부른다. 같은 원천 표를 두 경로로 받는 인허가(투자지표 반기 ADV.permits ↔ 기본통계 누계)는 `permit_half_mismatch`로 맞춰 보고, 어긋난 해는 `heal_permit_years`가 12달씩 다시 받는다(게이트 아님 — 커밋 잡이 'ℹ️ 원천 소급 정정 반영' 줄로 올린다). R-ONE 시도 행 찾기는 `rone_sido_key` 하나를 주간·월간 수집과 감시가 함께 쓰고, `--seed-sido`도 `sido_guard`를 거친다. 규모별 최신은 그 지표에 값이 있는 마지막 달(`size_last`)이고 감시·month_lag 가 같이 읽는다 |
| `make_city_moveins.py`, `city_movein.py`, `movein_need.py` | 도시(시군구) 입주물량 수집 → `tools/data/city_moveins.json`(배치 fetch 잡과 원고 발행이 돌린다). 적정 입주량 산식의 정본은 아무것도 들여오지 않는 `movein_need.py`(인구 ÷ 2.5 × 2%)다 |
| `split_data.py` | `data.js` → `data-core.js`, `data-*.json` 분리. 홈 통계용 `data-trend.json`은 허용목록 `TREND_ADV`만 싣는다(새 ADV 키를 홈 통계에 쓰려면 여기에 올린다). 분기·연 가격 합(`ADV.monthly.agg`, 원값 합·달이 덜 찬 칸은 비움)과 입주물량 문턱(`ADV.occupancy.band`)을 실어 홈이 계산하지 않고 읽게 한다. 주간 코어에는 최근 조사기준일 목록 `ADV.weekly.ps`를 실어 '지난 방문 이후 새 발표 N회'가 원천이 거른 주를 세지 않게 한다. 버블밴드 전세가율은 `make_indicator_pages.bubble_payload`(기준월 `jeonse_ref_index`)로 `ADV.bubble`에 싣고, 서울 구 블록과 코어에 이미 있는 키는 trend 에 싣지 않는다. 새 데이터가 처음 실린 날은 `fresh_marks`가 직전 `data-core.js`의 `ADV.fresh`에서 이어 받는다 |
| 생성기 아홉: `make_sido_pages.py` → `make_indicator_pages.py` → `make_monthly_page.py` → `make_weekly_page.py` → `make_home_summary.py` → `refresh_cycle_data.py` → `make_content_pages.py` → `make_feed.py` → `make_llms_txt.py` | 배치가 **이 순서로** 돌린다(그 앞에 `make_city_moveins.py`·`split_data.py`). 순서의 정본은 워크플로이고 `ci-tests.yml`·bat·`test_batch_parity`가 같은 목록이다. `/zone/`·`/monthly/`·`/jeonse-ratio/`·`/moveins/`·글 페이지의 dateModified·sitemap lastmod는 내용이 바뀐 날(`keep_dates`, KST)이다. 그래서 dateModified 는 데이터 시점을 말하지 않는다 — 감시는 화면의 시점 문구를 읽는다(`/moveins/`는 `make_indicator_pages.MOVEINS_BASIS`) |
| `make_sido_pages.py` | 시도 리포트와 `/zone/` 허브. 설명 메타와 `<main>` 첫 문단은 `summary_parts` 한 목록에서 나오고, h1 은 판정까지 말한다('서울 아파트 공급, 매우 부족'). 시세 구역 머리에는 홈 전국 시군구 지도를 그 지역 칸만 잘라(`zone_tile` — 상자 안 이웃 칸은 흐리게, 한 칸뿐인 세종은 생략) 주간·월간 두 장을 단추(`zone/zone.js`)로 바꿔 보인다(기본 주간, `test_zone_map`) |
| `make_indicator_pages.py`, `make_monthly_page.py` | `/jeonse-ratio/`·`/moveins/`·`/monthly/`. `make_indicator_pages.SHELL`은 글 페이지도 쓰는 공용 뼈대다. 전세가율 원천 표기는 `JR_SOURCE` 하나를 `/jeonse-ratio/`·`/monthly/`가 쓰고, `/monthly/` 입주물량 뒤 칸은 착공 기준 추정이라 열 머리·원천·주석(`moveins_est_note`)으로 밝힌다. `/monthly/`는 순위가 빈 절에도 사유 한 줄을 쓴다(`_why_empty`) |
| `make_weekly_page.py`, `weekly_moves.py`, `weekly_release.py` | `/weekly/`. 뼈대(`weekly/index.html`의 손 구간)는 PR 로 고치지 않고 생성기가 맞춘다(`put_nav`·`put_brand`·`put_desk`). '더 둘러보기'·Dataset temporalCoverage 도 생성기가 굽는다. `weekly_moves`는 주간 시세 움직임의 정본이다: 방향 표지·연속 주수(발표 기준 반올림 뒤 셈, 계열 첫 값까지 닿으면 '이상' — `opened`)·순위 이동·12주 누적(창은 조사일로)·시군구→시도 매핑(`sgg_sido`는 홈 `sidoOf`의 거울)·판정 단위 접기(`sgg_zone`은 홈 `sggZoneOf`의 거울). TOP 목록의 정본은 `top_split` — 상승에는 오른 곳만, 하락에는 내린 곳만(표시값 부호, 비면 '없다' 한 줄). `/weekly/` 표 앵커는 `TABLE_URL`(`#sgg-table`). `weekly_release`는 발표 일정(조사일·발표일·다음 발표·지연 판정)의 파이썬 정본으로 감시의 주간 유예(`GRACE_WEEKLY`), `/weekly/` 머리줄, `ADV.weekly.grace`가 여기서 나오고 홈 `weeklyRelease()`와 같은 답을 내는지 `test_weekly_release`가 node로 대조한다 |
| `make_content_pages.py`, `content_tables.py`, `content_md.py`, `content_check.py`, `make_content_cards.py` | 글 페이지·허브·자리표·원고 검사·글 카드. 아래 "콘텐츠 원고" |
| `make_home_summary.py`, `make_feed.py`, `make_llms_txt.py` | 홈 표식 구간·설명 메타(데이터가 그대로면 '페이지 수정' 날짜도 그대로), `/feed.xml` RSS, `/llms.txt`(AI 검색 요약 — 숫자 없이, 콘텐츠 글 목록 구역만 예외)·`/llms-full.txt`(글 전문) |
| `sido_zones.py` | 판정 단위·등급·정렬·화면 숫자·지역 이름·날짜 표기의 **정본**. 아래 "정본: sido_zones" |
| `site_nav.py` | 모든 페이지가 같이 쓰는 틀의 정본: 하단 탭바(홈·지역·시세·콘텐츠 — `TABS`, 생성기는 `bottomnav()`로 굽고 손 페이지는 손으로 맞추되 `test_site_nav`가 저장소의 모든 탭바를 대조한다. 탭 식별자는 GA 값이라 라벨을 바꿔도 그대로 둔다. 손 페이지가 켜는 탭은 `HAND_TAB_ON`), 글자 하한 `READ_PX`·`LABEL_PX`, 색 `BRAND_TOKENS`·`UP_INK`·`DN_INK`·`SERIES_COL`, 공용 조각 `NAV_FOCUS_CSS`·`NAV_ON_CSS`·`NAV_SCROLL_PAD_CSS`·`FONT_FALLBACK_CSS`·`FONT_STACK_HEAD`, 푸터 `HAND_FOOTER`·`FOOTER_DISC`·`FOOTER_CONTACT`·`site_footer()`, 데스크톱 틀 `desk_link`·`desk_body`·`dtoc`·`DTOC_JS`, 뒤 단계가 채우는 표식 구간 `LATE_SLOTS`(`keep_dates`가 이 구간을 비우고 견준다 — keep_dates 를 거치는 페이지에 새 표식 구간을 두면 여기에 올린다), 브라우저 머리 색 `THEME_COLOR`(= app.css `--ink`). **탭바나 글꼴 목록을 싣는 새 페이지는 이 글자를 그대로 싣는다** |
| `check_freshness.py` | 데이터 신선도·정합성 검사. 감시 워크플로가 부른다. 알려진 원천 정지는 `SOURCE_PAUSED`(기한 있음)로 경고로만 둔다 |
| `batch_notes.py`, `format_batch_report.py`, `post_alert.sh` | 배치 기록 줄(ℹ️·⚠️), 결과 보고, 경보 이슈 코멘트. 아래 "자동화"의 메일 |
| `gen_sgg_rone_map.py [--weekly] [--write]` | 시군구 매핑(월간 `SGG_RONE_CLS`·주간 `SGG_RONE_CLS_WK`) 재생성·대조. 키가 필요하다. 현재 매핑에만 있는 코드가 있으면 `--write`를 거부한다. 원천이 새 시군구를 내도 매핑은 저절로 붙지 않는다 — `batch_notes.sgg_map_gap_lines`가 '월간 시군구 매핑 없음' ℹ️ 줄로 알린다 |
| `refresh_cycle_data.py`, `rebuild_cycle_analysis.py` | `/cycle/` 데이터 갱신과 재산정. 칸 바로 뒤에는 값에 기대는 손 조사를 두지 않고, 지역 이름 뒤 조사는 화면 이름 받침(`RC._jong`)을 따른다. 고리⑥ 반응 시차 수는 `RC.link6_lag_prose` 한 함수가 정본이다. 홈 사이클 배너·FAQ 의 '20년'은 손 글자라 `test_span_years_come_from_the_data_span`이 자료 기간을 넘지 않는지만 본다 |
| `page_share.py`, `robots_meta.py`, `ga_tag.py`, `ping_indexnow.py`, `blog_feed.py` | 공유 버튼 조각(`/weekly/`·`/monthly/`). robots 메타(`max-image-preview:large`)의 정본 — 저장소의 모든 `.html`에 정확히 하나씩(`test_robots_meta`), 손 페이지를 새로 만들면 한 줄 넣는다. GA 내부 트래픽 표식(`?internal=on|off` → localStorage, 모든 `gtag('config', …)`는 `gaCfg(…)`를 거친다, `test_ga_internal`). 배치 커밋이 sitemap lastmod를 바꾼 주소만 IndexNow로 보냄(`--changed HEAD~1`, 도메인은 `CNAME`). 네이버 블로그 RSS에서 최신 글을 읽어 `tools/data/blog_latest.json`에 적음(실패하면 지난 값 유지) |
| `make_zone_cards.py`, `make_og_cards.py`, `make_weekly_share.py`, `make_monthly_share.py` | 공유용 이미지·OG 카드. 이미지 도구는 pillow 만 쓴다(numpy 등 금지). 디자인 감사·적용(`audit_design.py`·`apply_design.py`)은 `RADIUS_SHAPE`·`RADIUS_OK` 한 기준을 쓴다. 카드 글자는 `SZ.disp`·'적정물량'을 쓰고, 주간·월간 카드의 색 기준은 홈 지도 정본(`make_weekly_page.map_refs` = WK_MAP_REF·MO_MAP_REF), 주간 카드 범례는 `make_weekly_share.LEGEND`(하락 → 상승) 순서다 |
| `make_quiz_share_pages.py` | 퀴즈 점수별 정적 공유 페이지. 퀴즈 세트나 공유 이미지를 바꿨을 때 사람이 돌린다 |
| 블로그 초안 도구(휴면): `make_naver_post.py`, `make_theory_post.py`, `make_city_post.py`, `make_monthly_post.py`, `naver_serp.py`, `blog_similarity.py`, `blog_counter.py` | 블로그 발행은 2026-10-29 종료라 쓰지 않는다. 설명은 `docs/2026-11-13-블로그-도구-휴면-기록.md`. **살아 있는 코드가 읽는 것만 기억한다**: 배치 기록이 이론편 전제 가드(`make_theory_post.guard_values`)를 불러 편마다 ℹ️ 한 줄로 알린다(`batch_notes.theory_claim_lines` — 전제가 깨져도 게이트는 막지 않는다, 2026-10-18 대표 결정. 데이터 상태로 멈춘 편은 멈춤 문구에 `NOT_THE_TEXT`가 든다) |
| `run_weekly_update.bat` | 로컬 배치 러너(Windows 작업 스케줄러). 휴면 확정(2026-09-23), 비상용으로만 남긴다. 다시 켜면 두 배치의 순서·대상이 같아야 한다(`test_batch_parity`) |

### 실행

```bash
python -m pytest tools/tests -q          # 전체 테스트
python tools/make_sido_pages.py
```

Python 3.12. 별도 requirements 파일은 없고 표준 라이브러리 위주이며, 이미지 도구는 `pillow`를 쓴다.
배치 게이트는 `pytest`·`pillow`만 깐다 — 시험과 배치 도구는 그 밖의 서드파티(yaml 등)를 모듈 맨 위에서 가져오지 않는다
(`test_test_deps_are_installed`). 원고 발행 워크플로만 `fonttools`를 더 깐다(글 카드의 글자 검사). 개발 컨테이너엔 시스템 yaml 이
있어 로컬 pytest 로는 안 드러나므로, CI 와 같은 조건은 `python3 -m venv` 에 `pytest pillow` 만 깐 환경에서 확인한다
(2026-09-24~26 게이트 정지 사례). 클라우드 세션은 훅이 그 환경을 만들어 준다(아래 "자동화"). 생성기·감시·fetch 잡은 `pip` 앞이나
설치 없이 돌므로 표준 라이브러리만 쓴다. Windows 콘솔에서 한글이 깨지면 `PYTHONUTF8=1`을 준다.

**CI 와 같은 결과를 얻으려면 시험 앞에 산출물을 굽는다**: `ci-tests.yml`의 'split_data + 생성기' 단계 순서 그대로(앞단 둘 + 생성기 아홉).
PR 은 산출물을 싣지 않으므로 생성기를 고친 뒤 굽지 않고 시험하면 커밋된 옛 산출물과 견줘 빨개지는 시험이 있다. 작업 트리가 아니라
`git worktree` 사본에서 굽거나, 구운 뒤 산출물 변경을 되돌린다. 건너뜀까지 실패로 보려면 `GITHUB_ACTIONS=1 python3 -m pytest tools/tests -q`.
로컬 미리보기는 `.claude/launch.json`의 `agongmap`(정적 서버, 8321 포트)을 쓴다.

## 자동화

- **데이터 갱신**: 원천 수집 경로는 **클라우드 배치(`update-cloud.yml`) 하나**다. KOSIS가 해외 IP를 간헐 차단하므로
  러너 3개를 띄워 IP 프리플라이트를 통과한 것의 산출물만 쓰고, 0/3이면 35분 뒤 자동 재시도한다(`update-cloud-retry.yml`). fetch·commit
  잡은 `ref: main`으로 체크아웃해 대기한 런도 앞 런의 data.js 위에서 출발하고, commit 잡은 취소된 런에서 돌지 않는다(`!cancelled()`).
  결과 보고(`format_batch_report`)는 생성기·감시를 불러오지 않는다. 생성기를 돌린 **뒤, 커밋 직전에 pytest를 돌려 실패하면 데이터를
  커밋하지 않는다**(CI에서는 시험 건너뜀도 실패다). 테스트가 깨져 있으면 배치가 며칠째 멈춘 것으로 나타난다.
- **산출물 재생성**: `main`이 바뀔 때마다 `publish-content.yml`·`rebake-outputs.yml`이 생성기를 돌려 산출물을 커밋한다(위 "워크플로").
  그래서 생성기를 고친 PR 은 병합 직후 사이트에 반영되고, 데이터 값은 다음 배치에서 바뀐다.
- **시험**: `ci-tests.yml`이 PR·`main` 푸시·매일 예약(22:17 KST)에서 배치 게이트와 같은 조건(3.12, `pytest`·`pillow`만,
  depth 200, split_data·생성기 먼저)으로 pytest 를 돌리고, 설치 없이 도는 진입점을 따로 돌려 본다. 둘이 같은지는
  `test_ci_workflow_mirrors_gate`가 본다. 봇 데이터 커밋은 푸시로 이 워크플로를 부르지 못해 예약 실행을 둔다 —
  배치 게이트가 경고로만 넘기는 '다음 분기 전진 시험'(`test_gate_survives_next_period`)이 여기서 실패로 돈다. 전진 시험은
  준공·착공·주간·월간에 더해 매매·전세지수·금리도 새 분기 첫 달 모양(전세 한 달 늦음)으로 밀고, 안쪽 게이트도 건너뜀을 실패로 돈다
  (.git 없는 사본에서 판정 못 하는 sw.js 이력 시험 하나만 뺀다).
- **러너 판**: 모든 워크플로는 `ubuntu-24.04` 고정이다(ci-tests 의 `inputs.runner` 기본값이 정본, `test_runner_pin`). `runner-trial.yml`이
  같은 시험을 다음 판(26.04)에서 주 1회·수동으로 돌린다. 몇 주 초록이면 고정 판을 함께 올린다(2026-10-06 대표 결정).
- **감시**: `watchdog.yml`이 매일 `check_freshness.py`로 라이브 데이터를 원천과 대조한다. R-ONE 지역 목록 조회가 끊기면 재시도하고,
  그래도 끊기면 첫날은 경고, 이틀 연속이면 실패다(`region_fail_tolerated`, 상태는 actions/cache 의 `.watch_state` — 같은 회차·이웃 회차는
  KST 날짜가 아니라 실행 id 와 경과 시간으로 가른다). 감시 최악 소요는 `test_freshness_budget`이 줄인 시계로 main() 을 돌려 잡 상한과
  견준다 — 원천 호출·재시도를 늘리면 이 시험이 알린다. 배치 안의 알림 코드는 배치가 안 뜨면 실행되지 않으므로 감시자를 밖에 둔 것이다.
- **메일**(2026-11-08 대표 결정 '꼭 봐야 하는 것만'): 사람에게 가는 메일은 경보 이슈(`batch-report` 라벨) 코멘트 하나뿐이고,
  코멘트·제목 바꾸기는 `tools/post_alert.sh` 한 곳이 한다. 보내는 경우는 셋이다 — 데이터 갱신이 하루 넘게 멈춤(배치, 같은 KST 날짜에
  한 통, 멈춘 시각은 이슈 본문의 숨은 표식 — `format_batch_report.stall_decide`), 감시 판정 실패(`watchdog.yml`의 `notify` 잡), 매일 밤
  예약 시험 실패(`nightly-alert.yml` — ci-tests 는 PR 코드를 돌려 쓰기 권한을 두지 않으므로 따로다). 알림 본문 생성이 죽은 회차는
  폴백 본문으로 한 통 더 간다. GitHub 실행 실패 메일(Actions)은 대표가 계정 설정에서 껐으니 그것에 기대지 않는다. 경보마다 제목에
  '하실 일: 세션에 알리기'를 적는다. 받는 주소는 GitHub 계정 설정이 정하고 저장소에는 적지 않는다(`test_mail_volume`).
- **메일이 아닌 것은 세션이 본다**: 하루 실패·확인 중(⚠️)·기준월 뒤처짐·배치 기록의 ℹ️·⚠️ 줄(원천 소급 정정, 시군구 매핑 없음, 이론편
  전제 등)·원고 발행 실패는 **실행 화면 요약에만 남는다**. 세션은 작업을 시작할 때와 PR 을 병합한 뒤에 최근 워크플로 실행을 본다.
- **발행 알림**: 휴면(2026-11-08, 블로그 발행 2026-10-29 종료). `write-reminder.yml`·`publish-check.yml`은 예약을 껐고 손으로만 돈다.
- 클라우드 세션에는 API 키가 없다. 데이터 갱신(`update_adv_data.py`)을 돌리지 말고 pytest로 검증한다.
  클라우드 세션은 컨테이너가 매번 새로 뜨므로 `.claude/hooks/session-start.sh`(SessionStart 훅)가 시작 때
  `python3.12` 격리 가상환경에 `pytest`·`pillow`만 깔아 PATH 앞에 둔다(배치 게이트와 같은 판·같은 패키지). 3.12 가
  없는 컨테이너면 시스템 파이썬에 깔고 경고를 남기니, 그때는 PR 의 `ci-tests.yml` 결과로 한 번 더 확인한다.
- 키·GA 화면처럼 클라우드 세션이 못 하는 일은 `docs/2026-09-23-로컬-전용-작업.md`에 있다.

## 데이터 원칙

- **숫자는 원천에서 그대로 가져온다.** 원천이 합쳐서 발표한 값을 비율로 쪼개 채우지 않는다. 검증 불가능한
  수가 되기 때문이다. 원천 분류가 바뀌면 판정 단위 자체를 바꾸거나 그 달을 보류한다.
- 사이트의 여러 화면과 글이 다른 숫자·다른 산식을 말하면 안 된다. 글·피드·블로그 도구는 배치가 구운 값을 읽고 재계산하지 않는다.
- **모델 밖 원천 집계 행(6대·5대광역시·9개도·8개도·기타광역시·기타지방)은 싣지 않는다** — 판정 모델 지역 축 계열(`MODEL_REGION_SERIES`)에서 `drop_raw_aggregates`가 매 회차 뺀다(2026-10-18 대표 결정 D2). 광주·전남 주택보급률은 두 조각으로 만들지 않고 비운다(`merge_regions.UNFOLDABLE`, D3 — 주택수·가구수 합 재계산은 백로그 52). 0 이 될 수 없는 연간 비율의 원천 0 은 '없음'이다(`ANNUAL_CONF`의 `zero_missing`).
- **사람이 센 수와 손으로 적은 목록을 코드에 박지 않는다.** 지역 수·시군구 수·검증 대상 곳 수
  같은 값은 모델이나 데이터에서 세어 쓴다(`len(SGG_QNAME)`, `CYCLE_SYNC_N`처럼). 박아 두면 모델이
  바뀌어도 따라오지 않고 **아무것도 빨개지지 않는다.** 2026-09-10 광주·전남 통합 한 번이 아홉
  자리에서 서로 다른 모습으로 터졌다(문장 속 수, 조건의 지역 목록, 완비 기준). 정본 상수를
  만들었으면 **같은 파일 안에서도 빠짐없이 그것을 쓴다** — 제목은 상수인데 본문은 하드코딩이면
  한 글 안에서 숫자가 갈린다.
- **같은 대상을 재는 코드가 둘 이상이면 같은 상수를 쓰고 그 일치를 시험으로 고정한다.** 서로 다른
  기준으로 재면 한쪽 방어선이 다른 쪽의 고장을 덮는다(2026-09-12 분양·미분양 수집 정지).
- **시험을 넣을 때 두 가지를 독스트링이나 커밋 메시지에 적는다.** ① 코드를 무엇으로 바꾸면 이 시험이
  빨개지는지(변이 1개 이상, 실제로 깨뜨려 확인), ② 픽스처가 어떤 실제 상태를 재현하는지. 초록인 채로
  결함이 배포되는 시험은 없는 것보다 나쁘다. 2026-09-16 리뷰 확정 15건 중 9건이 이 유형이었다(게이트가
  생성기 앞에서 돎, 평평한 픽스처, 검사기가 결함을 스스로 재현함).
- **게이트 시험은 날짜·데이터가 앞으로 가도 초록이어야 한다.** 실데이터의 달·분기·등급을 숫자로 박으면 새 분기가
  들어오는 날 게이트가 그날 데이터 커밋을 막는다(2026-09-26 데이터 감사: 20건 중 7건이 '데이터가 앞으로 가면 그날
  커밋이 막히는' 유형이었다 — 시험 5건, 생성기 중단 2건). 기대값은 데이터에서
  유도하고, 날짜가 지나서 생기는 일(검토 기한 등)은 게이트가 아니라 감시 경고·배치 기록 줄로 알린다. '오늘'은
  `tools/kst.py`, '전월'·'1년 전' 칸은 인덱스 차가 아니라 `sido_zones.month_back`으로 찾는다. 실데이터 게이트 시험에는 시장값 문턱(지역 사이 순서, '5 미만' 같은 상한)도 두지 않는다 — 상한은 역대 최고를 크게 넘는 단위 사고 막이로만 둔다(2026-10-18 전수리뷰: 인허가 신호 순서는 165개월 중 77개월 뒤집혔다).
- 계산법 공개가 핵심 가치다. 산식을 바꾸면 사이트 설명문과 그 숫자를 쓰는 글·생성기를 같이 고친다.
- 생성 페이지의 문구는 생성기(`make_*.py`)를 고친다. 출력물을 직접 고치면 다음 배치에서 되돌아간다.
- **글 카드·썸네일(`share/`)은 CI 만 그린다.** 로컬에서 `make_content_cards.py` 를 돌려도 그 결과는
  커밋하지 않는다 — 같은 데이터·같은 코드인데도 환경에 따라 그림이 달라진다(2026-10-30: 로컬 Windows 와
  발행 워크플로 Linux 가 쉰아홉 장을 서로 다르게 그려 커밋이 서로를 되돌렸다). 한 환경 안에서는
  결정적이라 두 번 돌리면 0 장이다. 카드가 묵었으면 원고 발행 워크플로(`publish-content.yml`)를 수동 실행한다.

## 콘텐츠 원고

- **글의 정본은 `content/<섹션>/<slug>.md`다**(섹션 `city`·`gtx`·`danji`·`column`). `/city/`·`/gtx/`·`/danji/`·`/column/`·`/reports/`는
  `make_content_pages.py`가 굽는 산출물이다. 원고는 클라우드 세션이 PR 로 올리고, 병합되면 `publish-content.yml`이 굽는다.
- **숫자는 자리표로만 적는다**(`{{v:…}}`·`{{table:…}}`·`{{chart:…}}`, `content_tables.py`). 손으로 적은 숫자는 데이터가 바뀌어도 따라오지
  않는다. 자리표 종류·프런트매터·글자 상한(`content_md.TITLE_MAX` 등)은 `content/README.md`가 정본이고, 원고 규칙 여섯 가지는
  `docs/2026-11-07-콘텐츠-원고-규칙-안내.md`에 있다.
- **원고(md)는 배포하지 않는다.** `_config.yml`의 exclude 가 `content/`의 md 만 뺀다(`test_pages_config`). 빼지 않으면 Jekyll 이
  자리표가 지워진 중복 페이지를 `/content/…html`로 내보낸다. `content/`를 통째로 빼면 글 페이지가 부르는 그림(`content/<섹션>/img/`)이 깨진다.
- **원고 한 편의 탈은 그 글만 건너뛴다.** 생성기는 한 편을 굽다 난 예외를 그 글에 가두고(`_crash_note`) 나머지를 굽는다. 검사기는
  생성기의 `build_page`·`markdown`을 그대로 돌려 같은 탈을 `✗`로 미리 알린다(`test_content_robust`).
- **올리기 전에 `python tools/content_check.py`를 돌려 `※` 줄을 0 으로 만든다.** 아직 원천에 없는 자료(새 도시, 공개 전인 해)는
  '기다림(…)'으로 떨어진다 — 원고는 올려도 되고, 자료가 들어온 회차에 저절로 구워진다. 그동안 그 글은 건너뛰고,
  건너뛴 글로 가는 링크(이전·다음 글, 목록, 지역 묶음)는 만들지 않는다.
- 화면 단위는 '세대' 하나다(시도 `v:need` 포함 — `sido_zones.unit_text`). 도시 연도별 표·그림에서 입주가 없는 해는 건너뛰지 않고
  '입주 예정 없음'으로 자리를 둔다(0 으로 적지 않는다 — `content_tables.NO_MOVEIN`·`year_span`).
- 도시 숫자의 원천은 `tools/data/city_moveins.json`(`make_city_moveins.py`)이다. 도시 적정물량(인구 ÷ 2.5 × 2%, `movein_need.py`)과
  시도 적정물량(기준표 분기 값 × 4)은 산식이 다르다 — 한 글에서 나란히 견주면 그 차이를 글이 밝힌다.
- 허브 페이지 제목·h1 은 `make_content_pages.REPORTS_NAME`('부동산 공급 리포트'), 탭·빵부스러기 이름은 `REPORTS_TITLE`('콘텐츠')이다.
  목록 페이지의 JSON-LD 는 `CollectionPage`, 글은 `Article`이다.
- `make_content_pages.py`는 다른 페이지의 표식 구간도 쓴다: 홈 `CONTENT_RECENT`, 시도 리포트 `ZONE_POSTS`('이 지역 글'),
  `/weekly/` 해설 칸, `/moveins/` 도시 글 칸. 그 구간은 손으로 고치지 않는다.

## 화면 설계 원칙 (대표 지적이 반복된 것)

- **설명·범례는 짧게, 콘텐츠 아래에 둔다.** 머리나 카드·칸 위에 설명 문단·범례를 쌓지 않는다. 범례는 한 줄, 설명은 한 문장이
  기본이고 긴 풀이는 목록 아래 '읽는 법'·접는 칸·FAQ 로 보낸다(2026-10-06 대표 지적 — 홈 카드 밑 두 줄 범례, 지역 허브 머리의
  설명·범례 네 덩어리, 리포트 막대 아래 다섯 줄 설명이 같은 날 연달아 지적됐다). 새 화면 요소를 넣을 때 첫 화면(375px)에서
  콘텐츠가 설명보다 먼저 보이는지 본다.
- **같은 개념은 한 이름, 물량은 한 단위.** 기준 물량은 '적정물량'(옛 '필요량'·'수요 기준선'·'적정수요'는 쓰지 않는다), 물량 단위는
  '세대'(원천 표의 '호'는 화면에서 `sido_zones.unit_text`·홈 `unitT`로 바꾼다 — 아파트는 1호가 1세대라 숫자는 같다), 해마다 입주 수준은
  신호등 낱말 '적음·보통·많음'(`/moveins/` 포함). 신호등은 판정과 다른 값이라 판정 낱말(부족·균형·여유)과 겹치지 않게 하고,
  모양은 어두운 틀 안에 채운 등이다(2026-10-06 대표 결정).
- **날짜는 두 단계로 쓴다.** 해를 넘겨 보이는 읽는 자리(퀴즈 제도 기준일, 글 머리 작성·갱신일, '페이지 수정')는 '2026년 9월 15일'
  (`sido_zones.day_long`, 홈 거울 `_dL`). 읽는 자리(기준 줄·문장·배너)는 '9/28'·'2026년 8월'·'2026년 2분기', 좁은 자리(표 칸·축 눈금·툴팁)는
  '26.9.28'(눈금 '9/28')·'26.8'·'26Q2'. 기준 줄은 '시점 기준 · 출처' 한 양식, 범위는 '~'. 기계가 읽는 값(JSON-LD 날짜·RSS·utm·PNG 메타)은
  그대로 둔다. 정본은 `sido_zones.month_text`·`month_short`·`day_text`·`day_short`·`quarter_text`·`quarter_short`, 홈 거울은
  `_ymT`·`_ymS`·`_md`·`_dS`·`_qT`(`test_date_format`). 감시는 화면 시점을 `basis_month`로 읽는다(옛 꼴 'YYYY.MM'도 받는다).
- **가로 축은 '오른쪽 = 많음'이다.** 공급은 왼쪽 부족 → 오른쪽 여유, 시세는 왼쪽 하락 → 오른쪽 상승, 신호등은 적음 → 많음
  (2026-10-06 대표 결정, `test_zone_gauge`가 막대·범례·홈 지도 범례 방향을 본다).
- **글자 하한은 두 단계다**(2026-11-06 대표 결정 '읽는 글 14px'): 읽는 문장(마침표로 끝나는 설명·주석·단락·카드 결론 줄·보기 줄·푸터
  면책)은 14px 이상, 라벨·축 눈금·표 칸·칩·날짜·캡션 한 줄은 13px 이상이고, SVG 지도 라벨·그래프 축·표 보기 표·사이클 도식은 제외한다.
  정본 상수는 `site_nav.READ_PX`(14)·`LABEL_PX`(13)다. 홈(`test_home_min_font`)·시세 탭·퀴즈 화면·모든 푸터(`test_view_min_font`)·생성
  페이지(`test_page_min_font`)의 시험은 아직 13px 한 단계로 보고, 손 페이지와 공용 푸터 면책은 `test_hand_reading_font`가 두 단계로 본다.
  홈에서 공용 클래스를 고칠 때는 `#view-home`으로 덮어 다른 페이지를 바꾸지 않는다.
- **색은 쓰임마다 정본이 하나다**(2026-11-11 대표 결정 '남색 + 형광 표시', 11-12 접근성 결정). 틀(내비·선택된 단추·주요 단추·링크·요약
  표지)은 남색 `--brand`, 결론 숫자 강조와 분류 태그는 형광 `--mark` 계열(`site_nav.BRAND_TOKENS`) — **데이터 그림(지도·표·그래프)에는
  쓰지 않는다**. 흰 바탕 등락 글자는 `UP_INK`·`DN_INK` 한 벌, 그래프 계열은 `SERIES_COL`(매매 빨강·전세 보라·공급 초록)이고 글자·가는
  선에는 같은 색의 진한 변형을 쓴다. 시군구 지도의 진한 칸(알파 `make_weekly_page.MAP_INK_A` 이상, 홈 `INK_A`가 거울) 숫자는 먹색이다.
  머리 표지(.chip)에는 이모지를 쓰지 않는다. 시험은 `test_brand_color`·`test_a11y_1112`.
- **접근성 하한**: 글자 대비 4.5:1, 그래프 선 3:1, 누름 면 40px(단추·전환·접는 칸·따로 선 링크 — `test_speed_a11y`). 키보드 초점이
  하단 탭바 밑에 숨지 않게 `NAV_SCROLL_PAD_CSS`를 싣는다. 링크가 든 SVG 는 `role="img"`가 아니라 `role="group"`이다.
- **넓은 화면(1024px 이상)은 `desk.css` 한 곳에서 짠다.** 위 내비·'아공맵' 이름표·화면별 배치를 페이지마다 따로 만들지 않는다. 새 페이지는
  `desk_link()`와 `data-desk` 종류 하나를 고르고, 긴 문서면 `dtoc`을 단다. 1023px 이하 화면은 이 파일과 무관하다(2026-10-06).

## 홈·시세 탭 동작

- **전국 시군구 지도는 하나다.** 홈 지도 구역의 주간·월간 시세 지도, 시세 탭 시장동향 지도, `/weekly/` 머리, 시도 리포트의 잘라 낸 지도가
  같은 지도다(홈 `sggMapSvg`, 파이썬 거울 `make_weekly_page.sgg_map_svg` — `test_sgg_map`이 한 글자까지 대조). 한쪽을 고치면 거울도 고친다.
- **홈 지도는 단추 하나에 지도 하나다**(2026-10-29 대표 결정). 모드는 공급 현황·주간 시세·월간 시세 셋(`mapMode`·`priceModel`)이고,
  공급 현황은 시도 지도, 주간·월간 시세는 같은 카드 안에 전국 시군구 지도(`priceTilesHtml`, 주간 매매·전세 2줄·월간 매매·전세·월세 3줄 —
  코어에는 `split_data`가 두 주기의 시군구 마지막 행만 싣는다)를 그린다. 시세 모드의 그래프·표 단추는 시세 탭을 연다. 그래서 주간
  구역(`renderWeeklyGrid`)에는 지도가 없고 홈은 모든 폭에서 한 단이다(`test_home_desktop`). 홈 첫 화면 히어로는 라벨·제목·부제뿐이다.
- **N 배지**: 세 모드 단추는 새 데이터가 이 사이트에 처음 실린 날부터 주간 4일·월간 7일·공급 14일 동안 글자 바로 왼쪽에 N 배지를 달고,
  그날과 다음 날은 무조건, 그 뒤는 누르면 그 기기에서 지운다(날은 `split_data.fresh_marks`, `test_home_fresh`).
- 카드 아래 공급 기준 줄(`.map-src`)은 칸이 470px 이하면 구간과 출처를 처음부터 제 줄로 나눠 부팅 전후 줄 수가 같다 — 문구 길이를 바꾸면
  단추 위치를 다시 잰다.
- **시세 탭 시장동향의 보기는 순위·지도·그래프·표 넷이고 기본은 지도다.** 순위·지도는 한 상자(`drawNationMap`)를 나눠 보인다(`gm-r`·`gm-m`).
  지도 칸·TOP 10 지역명은 `#stats-market-<week|month>~코드`로 그 지역 그래프를 연다(`openTrendRegion` — `~코드-t`는 표). TOP 10 입구(홈
  CTA·`/weekly/`의 TOP 10 링크 둘)는 `#stats-market-<주기>-rank`로 순위를 연다. 순위에서 연 지역 그래프는 뒤로 가면 순위로 돌아간다
  (`TR_BACK`, `test_market_rank_view`).
- **주소가 화면을 말하고, 늦게 온 데이터가 사람이 고른 보기를 덮지 않는다**: 주소 입구는 요청한 때의 `GT_SEQ`를 넘기고(그사이 사람이 다른
  보기를 고르면 버린다), 주소 입구가 대기열에 넣은 부름은 그사이 화면이 옮겨졌으면 버리며(`NAV_N`), 지역 그래프에서 그래프↔표를 바꾸면
  주소의 `-t`도 맞추고, 그래프를 닫을 때는 들어온 항목을 한 칸 뒤로 접는다(`trHashDrop`). '다시 시도'는 들어온 입구를 다시 연다(`statsRetry`).
- 시세 탭 지역 선택 상자는 판정 단위를 `DISPLAY_ORDER`로, 그 밖의 원천 권역 행은 뒤에 둔다. 시군구 이름표는 다른 이름의 앞말과 같으면
  안 된다(경기 광주시는 '경기 광주'). 구를 가진 시(성남·수원·청주 등)의 시 전체 행은 공용 이름표(`SGG_QNAME`)에 올리지 않고 시세 탭
  그래프·표 지역 선택에서만 '성남 전체'로 고른다(`sggPickOf`·`sggCityName` — 시 코드는 데이터에서 센다. TOP 10·`/weekly/` 표·시도 리포트
  표에는 넣지 않는다, 2026-10-29 대표 결정).

## 정본: sido_zones

`tools/sido_zones.py`가 판정 단위(시도) 목록·등급·화면 숫자·이름·날짜 표기의 정본이다. 손 페이지(홈·소개·FAQ)에 적힌 같은 숫자는
`test_home_hand_numbers`·`test_hand_page_numbers`가 대조한다.

- **순서는 셋을 가려 쓴다.** 순위는 반드시 `zone_order()`(등급군 → 절대량 — 절대 세대수로 순위를 매기면 판정과 모순이 난다). 시도
  **목록을 보여줄 때**는 `DISPLAY_ORDER`(관심 지역 고정 순서). `/monthly/`처럼 정부 표와 대조하는 화면은 `ORDER`(발표 원천 순서).
- **화면 숫자**: 분기·연 가격 칸 `price_periods`(달이 다 찬 칸만·원값 합), 쌓인 부족·여유의 크기 `need_mult`('1년 적정물량의 N배' —
  반올림이 등급 컷을 넘지 않게, 컷 글은 `cut_mult`), '3년 너머' 퍼센트는 원값 pbr 을 `pbr_pct`로 한 번만 반올림, 인허가 '1년'·'3년 너머'
  창은 계열 전체의 마지막 달 `permit_ref_month`에서 끝난다(그 지역에 빈 달이 있으면 값을 내지 않고 배치 기록 ⚠️), '인허가가 착공보다
  N%쯤 많다'의 `permit_over_start_pct`(손 페이지의 그 숫자는 게이트가 한 칸 안인지만 보고 정확히 다르면 `batch_notes.hand_permit_lines`가
  ℹ️ 줄로 알린다), 미분양 배수 표기와 경고는 `um_times` 한 규칙, 표 시작 연도는 `TABLE_FROM_YEAR`.
- **전환율**: 잰 첫 착공 연도는 `CONV_START_FROM`. 그 구간을 데이터로 다시 잰 값이 `CONV`와 화면 정수로 갈리면 게이트가 아니라
  `batch_notes.conv_model_lines` ℹ️ 줄이다 — 원천 소급 정정이 그날 커밋을 막지 않게(2026-10-21 대표 결정). 상수를 바꿀지는 사람이 정한다.
- **입주 신호등 문턱**: `OCC_LO_PCT`·`OCC_HI_PCT`(70·130%, 홈과 `/moveins/` 공통 — 2026-09-30 대표 결정). 지역 칸·시도 리포트·홈 판정 카드의
  해마다 입주 신호등·막대 색도 이 문턱이다(`light_of`·`year_lights`).
- **지역 이름**: 화면에 보이는 이름은 `DISPLAY_NAME`(키 '전남광주' → '광주·전남')이 정본이다. 생성기는 `disp`로, 홈은 `split_data`가 실은
  `ADV.zname`을 `zn()`으로, `/cycle/` 차트는 `refresh_cycle_data`가 다시 쓰는 `const ZN`으로 읽는다. **주소·데이터 키·GA 값·선택 상자
  `value`는 키 그대로**이고, 페이지 글자를 읽어 대조하는 시험은 `key_of`로 되돌린다(`test_display_name`). 데이터에 따라 바뀌는 이름
  자리(가장 높은·낮은 곳 같은 결론 문장과 그것을 옮기는 설명 메타·og·RSS)도 `disp`를 거치고 조사는 화면 이름 끝 글자로 센다 — 그런
  자리는 그 키가 1위가 되는 합성 픽스처 시험으로 늘 본다. 지역을 꼽는 문장은 표시값이 같은 지역을 모두 적는다.
- **낱말**: 미분양의 정의와 순위에서 빼는 이유는 `UNSOLD_NATURE`·`UNSOLD_RANK_WHY`.

## 세션 운영

**개발·원고는 클라우드 세션 하나로 한다(2026-11-05 대표 결정).** 코드·생성기·시험·문서·콘텐츠 원고(`content/`)는 모두 클라우드
세션이 PR 로 올린다. 로컬 세션은 API 키가 있어야 하는 조회(시군구 매핑 재생성, 원천 1회성 확인)에만 켠다 — 클라우드 환경
설정에 키 네 개를 넣으면 그 일도 클라우드가 한다. 개발·데이터·디자인·마케팅·콘텐츠·PM·리뷰 같은 역할은 세션이 아니라
백로그의 "담당" 칸으로 나눈다. 여기에 `stats-bot`(데이터 배치·산출물 재생성)이 `main`에 커밋한다.

| 세션 | 하는 일 | 커밋 방식 |
|---|---|---|
| 클라우드 세션 | 코드·생성기·시험·문서·원고 수정, pytest 검증 | 자기 컨테이너 클론에서 `claude/...` 브랜치 → PR → 병합 |
| 로컬 세션 | 키가 필요한 조회만(`docs/2026-09-23-로컬-전용-작업.md` 6번) | 키로 받은 데이터만 `main`에 직접. 코드·원고는 올리지 않는다 |

공통 규칙:

- 세션 간 연락은 `docs/` 요청서와 `docs/2026-09-09-유지보수-백로그.md`로 한다. 항목을 집을 때 세션명·시각을
  적고 `🔨 진행중` 커밋을 남기며, 끝내면 `✅ 완료`와 커밋 해시를 적는다.
- **완성한 작업은 바로 커밋한다.** 다른 세션은 내 검증 기록을 못 보므로 미커밋 상태는 "중간 상태"로 오해된다.
- 푸시 직전에 `git fetch`로 원격 상태를 확인한다. 로컬 세션은 작업을 시작할 때 `git pull`부터 한다.
- 커밋 메시지는 한국어 한 줄 요약(무엇을, 왜). 요청서 번호나 백로그 번호가 있으면 함께 적는다.
- `git add -A`, `git stash`, `--autostash`를 쓰지 않는다. 남의 미커밋 작업을 쓸어 담거나 숨긴다.

클라우드 세션(PR 브랜치):

- **생성 산출물을 PR에 싣지 않는다.** 정본 목록은 배치의 커밋 대상(`update-cloud.yml`의 TARGETS)이다: `data.js`·`data-core.js`·`data-*.json`,
  생성 페이지(`zone/`·`weekly/`·`monthly/`·`moveins/`·`jeonse-ratio/`·`cycle/`·`city/`·`gtx/`·`danji/`·`column/`·`reports/`), `feed.xml`·`llms.txt`·
  `llms-full.txt`·`sitemap.xml`, `index.html`의 표식 구간·설명 메타, `share/` 이미지, `tools/data/`의 배치 산출물. 봇이 `main` 푸시마다와
  매일 배치에서 다시 쓰므로 PR 브랜치에서 고치면 병합 때 충돌하고 덮인다. 생성기(`make_*.py`)와 시험만 고치고 산출물은 CI 가 굽게 둔다.
  생성기를 돌려 확인만 했다면 산출물 변경은 커밋 전에 되돌린다. (사람이 돌리는 산출물 — 퀴즈 점수 페이지, 지역·퀴즈 카드, 글꼴 서브셋 —
  은 그 도구를 돌린 PR 에 싣는다.)
- 병합 전 CI(`ci-tests.yml` 시험·Netlify 미리보기)가 초록인지 본다. 운영 반영은 `main` 병합 뒤 GitHub Pages 배포로 이뤄진다. 병합이
  늦어져 `main`과 충돌하면 `main`을 병합해 푼다. 병합 뒤에는 산출물 재생성 런(원고·생성기면 원고 발행 런)이 초록인지 본다.

로컬 세션(공유 작업 트리):

- **코드·생성기·워크플로·시험은 로컬에서 `main`에 직접 올리지 않는다.** 그 일은 클라우드 세션이 PR로 하고, 로컬은
  요청서나 백로그 항목으로 넘긴다. 꼭 고쳐야 하면 `claude/...` 브랜치로 푸시하고 PR 을 열어 `ci-tests.yml`이 초록인 것을 본 뒤
  병합한다. `main` 직접 커밋은 시험이 커밋 뒤에 돌아 고장을 그날 밤 배치가 먼저 맞는다(2026-10-27~29 배치 커밋 정지, 2026-10-29 대표 결정).
- **작업 트리와 인덱스를 로컬의 모든 작업이 같이 쓴다.** 스테이징해 두고 다른 일을 하면 남의 커밋에 실린다.
  - `git add`와 `git commit`은 한 명령으로 붙여 실행한다.
  - 커밋 전 `git status` 전체(잘라 보지 않는다)에서 충돌 파일(U)·`MERGE_HEAD`·남의 미커밋 변경을 본다. 있으면
    그 트리에서 커밋하지 말고 `git worktree add --detach <임시 경로> origin/main`에서 커밋·푸시한 뒤 워크트리를 지운다.

## 글 쓰는 법 (사이트 콘텐츠)

글의 정본은 사이트의 `content/` 원고다(네이버 블로그 발행은 2026-10-29 종료 — 블로그 전용 규칙과 도구 설명은
`docs/2026-11-13-블로그-도구-휴면-기록.md`). 숫자는 자리표가 채우고, Claude가 그 데이터의 해석을 쓰고, 대표가 PR 로 본다.

- **우리는 공급론자다.** 방어적으로 쓰지 않는다. 부정형으로 문단을 열지 않고, "다만/대신"으로 강한 사실을
  감싸지 않는다. 한계는 근거 옆에 짧게 둔다.
- **사실 나열로 끝내지 않는다.** 숫자 다음에는 "그래서 어떻게 되는가"를 쓴다. 두 갈래인데 결론이 같은 논증을
  우선 찾는다.
- **구조**: 결론 → 그 주제의 내용 → 전망·해석 → (링크) → 산식·방법론 → 면책. 방법론은 맨 뒤에 짧게.
  도구 설명서가 아니라 그 주제의 리포트로 쓴다. 소제목에 브랜드를 붙이지 않는다. 제목은 결론형 한 문장이다(앞에 검색어, 뒤에 결론).
- **글끼리 반복 금지.** 같은 설명(산식, 서비스 소개, 사이클 고리)을 글마다 다시 쓰지 않는다. 숫자가 지역마다
  다른 문장만 리포트 본체다.
- **지키는 선**: 투자자문 아님 면책, 시점 한계("방향은 되고 시점·폭은 안 된다"), 데이터와 견해를 가르는
  "제 판단으로는", 사이트의 다른 화면과 다른 말 금지.
- 결론은 절대 공급 부족으로 다시 묶는다. 세제·금리 같은 외부 요인을 다룬 글일수록 그렇다.

## 응답 언어

사용자에게는 한국어로 답한다. 문장은 조사·어미를 생략하지 않은 완결된 형태로 쓰고, 명사구나 연결어미로
끝내지 않는다. 비유적 어휘 대신 일반 어휘를 쓰고, 엠대시(—)는 쓰지 않는다. 코드·주석·커밋 메시지는 프로젝트
관례를 따른다. (사용자 전역 지침 "fluent-korean"의 요약이다. 전문은 사용자 로컬 `~/.claude/CLAUDE.md`에 있다.)

**시각은 항상 한국 시간(KST)으로 말한다.** 사용자에게 시각·일정·예약을 알릴 때는 UTC 등 다른 시간대를 쓰지 않고
KST로 바꿔 적는다(예: "22:28", 필요하면 "(KST)"). GitHub Actions cron·API 응답처럼 원본이 UTC인 값도 사용자에게는
KST로 환산해 전한다. 워크플로 파일 안의 cron 식은 UTC 그대로 두되 주석에 KST를 함께 적는 기존 관례를 따른다(2026-09-26 대표 요청).
