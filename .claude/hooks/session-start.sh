#!/bin/bash
# 클라우드 세션(Claude Code on the web) 시작 시 시험 의존성을 깐다.
# 컨테이너가 세션마다 새로 만들어져 pytest·pillow가 없으면 tools/tests 가 돌지 않는다.
# 로컬 세션에서는 아무것도 하지 않는다.
set -euo pipefail

if [ "${CLAUDE_CODE_REMOTE:-}" != "true" ]; then
  exit 0
fi

python3 -m pip install --quiet --disable-pip-version-check --root-user-action=ignore pytest pillow
echo 'export PYTHONUTF8=1' >> "${CLAUDE_ENV_FILE:-/dev/null}"
