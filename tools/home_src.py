# -*- coding: utf-8 -*-
"""홈(index.html) 스크립트를 읽는 단 하나의 입구 — 백로그 10 사전 작업(2026-09-16).

도구·시험 약 20곳이 홈 인라인 스크립트(QUIZSETS·SGG_QNAME·MATRIX_REGIONS 등)를 index.html 에서 직접
읽었다. 버리는 작업 트리에서 스크립트를 외부 파일로 옮겨 보니 두 가지가 동시에 났다.

  - 크게 실패: 주간 시세 생성기(배치 데이터 커밋 중단), 시험 46건.
  - **조용히 꺼짐**: 감시의 퀴즈 검토 기한 검사가 제도 문항 0개를 찾고 통과했고, '없어야 한다'류 단정
    다섯 곳이 대상 문자열을 못 읽은 채 초록불로 남았다.

두 번째가 더 위험하다. 그래서 이 입구는 **못 찾으면 빈 값을 돌려주지 않고 예외를 던진다.**

동결 창에서 스크립트를 옮길 때 할 일은 EXTERNAL 에 그 파일을 적는 한 줄뿐이다.
"""
import io
import os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
HOME = 'index.html'

# 동결 창에서 인라인 스크립트를 외부 파일로 옮기면 여기에 그 파일(저장소 루트 기준)을 적는다. 예: ('home-app.js',)
EXTERNAL = ()

# 읽는 쪽이 기대는 식별자. 하나라도 없으면 '스크립트를 못 읽었다'로 본다.
MARKERS = ('const QUIZSETS', 'const QUIZ_LEN', 'const QUIZ_SLUG', 'const SGG_QNAME',
           'const MATRIX_REGIONS', 'function nextStepHTML')

# 홈(마크업+스크립트) 크기 하한. 2026-09-16 기준 약 250KB 다. 스크립트가 빠지면 50KB 안팎으로 준다.
MIN_BYTES = 150000


class HomeSourceError(RuntimeError):
    """홈 스크립트를 찾지 못했거나 일부만 읽었다."""


def home_source(root=None, external=None):
    """index.html 과 EXTERNAL 파일을 이어 붙인 텍스트. 마크업과 스크립트를 함께 담는다.

    ⚠️ 빈 문자열·일부만 담긴 문자열을 돌려주지 않는다. 파일이 없거나, 크기가 하한보다 작거나, 표식 식별자가
       하나라도 없으면 HomeSourceError 를 던진다.
    """
    root = root or ROOT
    files = (HOME,) + tuple(EXTERNAL if external is None else external)
    parts = []
    for rel in files:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise HomeSourceError('홈 소스 파일이 없다: %s' % rel)
        parts.append(io.open(path, encoding='utf-8').read())
    text = '\n'.join(parts)
    size = len(text.encode('utf-8'))
    if size < MIN_BYTES:
        raise HomeSourceError('홈 소스가 %d바이트뿐이다(하한 %d) — 스크립트를 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL 에 그 파일을 적을 것' % (size, MIN_BYTES))
    missing = [m for m in MARKERS if m not in text]
    if missing:
        raise HomeSourceError('홈 스크립트에서 %s 를 찾지 못했다 — 스크립트를 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL 에 그 파일을 적을 것' % ', '.join(missing))
    return text


def is_home(*parts):
    """읽으려는 경로가 저장소 루트의 홈(index.html)인가."""
    return os.path.normpath(os.path.join(*parts)) == HOME


def require(text, *needles, **kw):
    """'없어야 한다' 단정 앞의 전제 — 검사 대상이 실제로 읽혔는지 먼저 확인한다.

    대상 문자열이 다른 파일로 옮겨지면 부정형 단정은 늘 참이 되어 초록불인 채 방어선이 꺼진다.
    """
    what = kw.get('what', '검사 대상')
    miss = [n for n in needles if n not in text]
    if miss:
        raise AssertionError('%s 을(를) 읽지 못했다(%s 없음) — 이 "없어야 한다" 검사가 헛돈다'
                             % (what, ', '.join(miss)))
