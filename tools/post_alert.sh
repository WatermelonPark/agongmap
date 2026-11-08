#!/usr/bin/env bash
# 경보 이슈 하나를 찾고·만들고·코멘트를 단다 — 사람에게 가는 메일의 유일한 통로(2026-11-08 대표 결정).
#
# ⚠️ 이슈 코멘트가 곧 메일이다. 그래서 '꼭 보셔야 할 때'만 부른다:
#    데이터 갱신이 하루 넘게 멈춤(update-cloud.yml, format_batch_report.stall_decide) ·
#    라이브 데이터 점검 실패(watchdog.yml) · 매일 밤 예약 시험 실패(ci-tests.yml).
#    실행 실패 메일(Actions)은 대표가 GitHub 설정에서 껐다 — 위 셋이 그 자리를 대신한다.
# ⚠️ 메일 제목은 그 시점의 이슈 제목이다. 코멘트 직전에 제목을 그 경보의 결론으로 바꾼다(제목 변경은 메일이
#    아니다). 그래서 이슈는 제목이 아니라 라벨로 찾는다. 담당자 지정은 하지 않는다("Assigned" 메일이 한 통 더 간다).
#
# 사용:
#   post_alert.sh find                  열린 경보 이슈 번호(없으면 빈 줄)
#   post_alert.sh ensure "<제목>"        없으면 조용히 만들고 번호를 찍는다(코멘트 없음 = 메일 없음)
#   post_alert.sh post "<제목>" <본문>   제목을 바꾸고 본문 파일을 코멘트로 단다(= 메일 한 통)
# GH_TOKEN(issues: write)이 있어야 한다. 실패는 ::warning:: 으로 남기고 0 으로 끝난다 — 알림 실패가 배치를 막지 않게.
set -u
LABEL="batch-report"
OLD_TITLE="아공맵 배치 리포트"
DESC="꼭 보셔야 할 일이 있을 때만 코멘트(=메일)가 달립니다: 데이터 갱신이 하루 넘게 멈춤 · 라이브 데이터 점검 실패 · 매일 밤 예약 시험 실패. 메일 제목은 그 경보의 결론입니다. 닫아도 다음 경보 때 새로 만들어집니다."

find_issue() {
  local n
  n=$(gh issue list --state open --label "$LABEL" --limit 1 --json number --jq '.[0].number' 2>/dev/null || true)
  if [ -z "$n" ] || [ "$n" = "null" ]; then
    # 라벨을 붙이기 전에 만들어진 옛 이슈(제목 고정 시절)를 한 번 이어받는다.
    n=$(gh issue list --state open --search "$OLD_TITLE in:title" --limit 1 --json number --jq '.[0].number' 2>/dev/null || true)
    if [ -n "$n" ] && [ "$n" != "null" ]; then gh issue edit "$n" --add-label "$LABEL" >/dev/null || true; else n=""; fi
  fi
  echo "$n"
}

ensure_issue() {
  local n url
  n=$(find_issue)
  if [ -z "$n" ]; then
    gh label create "$LABEL" --color B60205 --description "경보(코멘트=메일)" >/dev/null 2>&1 || true
    # `gh issue create`는 --json 을 받지 않는다 — 출력 URL 끝의 숫자를 쓴다.
    url=$(gh issue create --title "$1" --label "$LABEL" --body "$DESC" || true)
    n=$(echo "$url" | grep -oE '[0-9]+$' || true)
  fi
  echo "$n"
}

case "${1:-}" in
  find)
    find_issue ;;
  ensure)
    ensure_issue "${2:-$OLD_TITLE}" ;;
  post)
    HEAD="${2:-$OLD_TITLE}"
    BODY="${3:-}"
    N=$(ensure_issue "$HEAD")
    if [ -z "$N" ]; then
      echo "::warning::경보 이슈를 찾지도 만들지도 못했다 — 실행 화면에는 남았다: $HEAD"
      exit 0
    fi
    gh issue edit "$N" --title "$HEAD" >/dev/null || echo "::warning::이슈 제목 변경 실패 — 메일 제목이 옛 문구로 간다"
    gh issue comment "$N" --body-file "$BODY" && echo "경보 이슈 #$N 에 남김: $HEAD" \
      || echo "::warning::이슈 코멘트 실패 — 실행 화면에는 남았다"
    ;;
  *)
    echo "사용: post_alert.sh find | ensure <제목> | post <제목> <본문 파일>" >&2
    exit 2 ;;
esac
