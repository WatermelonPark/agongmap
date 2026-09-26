#!/bin/bash
# 클라우드 세션(Claude Code on the web) 시작 시 **배치 게이트와 같은** 시험 환경을 만든다.
#
# 배치 커밋 잡은 setup-python 3.12 위에 pytest·pillow 만 깐다(update-cloud.yml). 컨테이너의 python3 는 3.11 이고
# 시스템 패키지(yaml·requests 등)가 보여서, 세션에서 초록인 시험이 배치에서 ModuleNotFoundError 로 빨개졌다
# (2026-09-24~26 데이터 갱신 다섯 회 정지). 그래서 /usr/bin/python3.12 로 격리 가상환경(시스템 site-packages
# 없음)을 만들어 pytest·pillow 만 깔고, PATH 맨 앞에 둬서 세션의 `python3 -m pytest` 가 그 환경을 쓰게 한다
# (2026-09-26 데이터 감사). CI 처럼 건너뜀까지 실패로 보려면: GITHUB_ACTIONS=1 python3 -m pytest tools/tests -q
# 시스템 파이썬(yaml 등이 필요한 임시 확인용)은 /usr/local/bin/python3 로 그대로 부를 수 있다.
#
# 컨테이너 안에서 다시 돌면(재개·/clear) 이미 만든 환경을 그대로 쓴다. 로컬 세션에서는 아무것도 하지 않는다.
# 설치 목록과 파이썬 판이 배치와 같은지는 tools/tests/test_session_hook.py 가 본다.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

ENV_FILE="${CLAUDE_ENV_FILE:-/dev/null}"
PKGS="pytest pillow"                                   # = update-cloud.yml 커밋 잡의 pip 줄
PY312="${AGONGMAP_PY312:-/usr/bin/python3.12}"         # = setup-python 의 python-version
VENV="${XDG_CACHE_HOME:-$HOME/.cache}/agongmap-ci312"

echo 'export PYTHONUTF8=1' >> "$ENV_FILE"

venv_ok() {
  [ -x "$VENV/bin/python" ] &&
    "$VENV/bin/python" -c 'import sys, pytest, PIL; sys.exit(sys.version_info[:2] != (3, 12) or sys.prefix == sys.base_prefix)' 2>/dev/null
}

make_venv() {
  [ -x "$PY312" ] || return 1
  rm -rf "$VENV"
  "$PY312" -m venv "$VENV" || return 1
  "$VENV/bin/python" -m pip install --quiet --disable-pip-version-check --root-user-action=ignore $PKGS || return 1
  venv_ok
}

if venv_ok || make_venv; then
  echo "export PATH=\"$VENV/bin:\$PATH\"" >> "$ENV_FILE"
else
  # 3.12 나 venv 가 없는 컨테이너 — 예전처럼 시스템 python3 에 깐다. 시험은 돌지만 배치와 판·패키지가 다를 수
  # 있으니(시스템 yaml 등) 의존성·3.12 전용 문제는 PR 의 ci-tests.yml 결과로 확인한다.
  echo "session-start: $PY312 로 격리 환경을 못 만들었다 — 시스템 python3 에 설치한다(배치와 조건이 다르다)" >&2
  rm -rf "$VENV"
  python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore $PKGS
fi
