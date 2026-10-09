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
# 퀴즈·통계 화면 코드는 2026-09-27 홈 마케팅 검수 B11 에 home-app.js 에서 떼어 냈다(홈이 그 화면을 열 때 받는다).
# 이어 붙이는 순서는 브라우저가 실행하는 순서와 같다 — 본문 스크립트가 먼저고, 분할 파일은 그 전역 위에서 돈다.
# 분할 파일을 늘리면 여기와 home-app.js 의 PARTS·sw.js 사전 캐시를 같이 고친다(test_home_parts 가 셋을 대조한다).
PARTS = ('home-quiz.js', 'home-stats.js')
EXTERNAL = ('home-app.js',) + PARTS

# 읽는 쪽이 기대는 식별자. 하나라도 없으면 '스크립트를 못 읽었다'로 본다.
MARKERS = ('const QUIZSETS', 'const QUIZ_LEN', 'const QUIZ_SLUG', 'const SGG_QNAME',
           'const MATRIX_REGIONS', 'function nextStepHTML')

# 홈(마크업+스크립트) 크기 하한. 2026-09-16 기준 약 250KB 다. 스크립트가 빠지면 50KB 안팎으로 준다.
MIN_BYTES = 150000

# 파일마다 제 안에 있어야 하는 표식과 크기 하한(전수리뷰 #13). 위 MARKERS 는 모두 분할 파일에 있고 합계 하한은
# index.html 과 분할 두 파일만으로도 넘어서, 본문 스크립트(home-app.js)가 비거나 EXTERNAL 에 없는 파일로 옮겨져도
# 이어 붙인 텍스트 기준 검사는 통과했다(주석 한 줄짜리 home-app.js 로 실제로 확인). 그래서 읽는 파일 가운데 여기
# 적힌 파일은 **그 파일 안에서** 표식과 하한을 따로 본다. 본문을 다른 파일로 옮기면 여기 표식도 같이 옮긴다.
FILE_MARKERS = {
    'home-app.js': ('const PARTS', 'function showView', 'function applyHash', 'function weeklyRelease',
                    'function tbBuild', 'function boot'),
    'home-quiz.js': ('const QUIZSETS', 'const QUIZ_LEN', 'const QUIZ_SLUG', 'function nextStepHTML'),
    'home-stats.js': ('const SGG_QNAME', 'const MATRIX_REGIONS', 'function statsOpen'),
}
# 2026-09-30 기준 home-app.js 약 130KB, home-quiz.js 약 59KB, home-stats.js 약 81KB. 하한은 그 절반 남짓.
FILE_MIN_BYTES = {'home-app.js': 60000, 'home-quiz.js': 25000, 'home-stats.js': 35000}


class HomeSourceError(RuntimeError):
    """홈 스크립트를 찾지 못했거나 일부만 읽었다."""


def home_source(root=None, external=None):
    """index.html 과 EXTERNAL 파일을 이어 붙인 텍스트. 마크업과 스크립트를 함께 담는다.

    ⚠️ 빈 문자열·일부만 담긴 문자열을 돌려주지 않는다. 파일이 없거나, 크기가 하한보다 작거나, 표식 식별자가
       하나라도 없으면 HomeSourceError 를 던진다. FILE_MARKERS 에 적힌 파일은 파일마다 따로 본다.
    """
    return '\n'.join(body for _, body in _read_checked(root, external))


def _read_checked(root=None, external=None):
    """[(경로, 텍스트)] — 파일마다 한 번만 읽고 home_source 의 모든 검사(파일별·합친 크기·표식)를 거친다. home_source·home_files 공용."""
    root = root or ROOT
    files = (HOME,) + tuple(EXTERNAL if external is None else external)
    parts = []
    for rel in files:
        path = os.path.join(root, rel)
        if not os.path.isfile(path):
            raise HomeSourceError('홈 소스 파일이 없다: %s' % rel)
        body = io.open(path, encoding='utf-8').read()
        _check_file(rel, body)
        parts.append((rel, body))
    text = '\n'.join(b for _, b in parts)
    size = len(text.encode('utf-8'))
    if size < MIN_BYTES:
        raise HomeSourceError('홈 소스가 %d바이트뿐이다(하한 %d) — 스크립트를 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL 에 그 파일을 적을 것' % (size, MIN_BYTES))
    missing = [m for m in MARKERS if m not in text]
    if missing:
        raise HomeSourceError('홈 스크립트에서 %s 를 찾지 못했다 — 스크립트를 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL 에 그 파일을 적을 것' % ', '.join(missing))
    return parts


def _check_file(rel, body):
    """FILE_MARKERS·FILE_MIN_BYTES 에 적힌 파일이면 그 파일 안에서 표식과 크기 하한을 본다."""
    size = len(body.encode('utf-8'))
    low = FILE_MIN_BYTES.get(rel)
    if low and size < low:
        raise HomeSourceError('%s 가 %d바이트뿐이다(하한 %d) — 본문을 다른 파일로 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL·FILE_MARKERS 를 같이 고칠 것' % (rel, size, low))
    missing = [m for m in FILE_MARKERS.get(rel, ()) if m not in body]
    if missing:
        raise HomeSourceError('%s 에서 %s 를 찾지 못했다 — 본문을 다른 파일로 옮겼다면 tools/home_src.py 의 '
                              'EXTERNAL·FILE_MARKERS 를 같이 고칠 것' % (rel, ', '.join(missing)))


def home_files(root=None):
    """home_source() 와 같은 검사를 거친 뒤 파일별로 나눈 [(경로, 텍스트)] — index.html, home-app.js, 분할 파일 순.

    마크업만·본문 스크립트만 따로 봐야 하는 도구(make_home_font 의 글자 모으기)가 쓴다. 검사를 통과하지 못하면
    home_source 처럼 HomeSourceError 를 던진다.
    """
    return _read_checked(root)   # 한 번 읽고 같은 검사(예전엔 home_source 로 한 번, 파일별로 또 한 번 — 10-09 리뷰)


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
