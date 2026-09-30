# -*- coding: utf-8 -*-
"""개인정보처리방침(/privacy/)이 적은 GA 전송 목록이 코드가 실제로 보내는 것과 같은지 본다(전수리뷰 #65).

재현하는 실제 상태: 2026-09-30 전수 리뷰 때 방침 1항은 '퀴즈 결과 등은 이용자 브라우저에만 저장되며 서버로
전송·수집되지 않습니다'라고 적었다. 그러나 home-quiz.js 는 문항마다 quiz_answer{correct}, 끝나면
quiz_complete{score}, 대결에서 challenge_result{score, friend_score} 를 gtag 로 보낸다. 공개 문서가 실제 처리와
반대였고 이를 보는 시험이 없었다. 대표 결정(2026-09-30 ②)으로 방침을 사실대로 고치고, 1항에 전송 목록 표
(id="ga-events", 행마다 data-ev)를 두었다. 이 시험은 그 표와 코드를 양방향으로 대조한다.

코드 쪽은 저장소에서 GA 로 값을 보내는 곳을 모두 훑는다: 홈 전체(home_src.home_source() — index.html 과
home-*.js), 저장소 맨 위·한 단계 아래 HTML(퀴즈 랜딩·사이클·생성 페이지 허브), tools/*.py 생성기(시도 리포트·
공유 조각·주간·월간). 호출 모양은 track('이벤트',{키:…}) 과 gtag('event'|'set','이름',{키:…}) 두 가지다.
이름을 변수로 넘기는 호출은 이 훑기가 못 보므로, 그런 호출이 생기면 따로 실패한다.

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · home-quiz.js 의 quiz_answer 에 매개변수 하나(예: pick)를 더하면 → 방침에 없는 전송으로 실패.
  · privacy/index.html 표에서 quiz_complete 행을 지우면 → 같은 시험이 실패.
  · 표에 코드에 없는 행이나 값(예: quiz_complete 에 answer)을 더하면 → 코드에 없는 항목으로 실패.
  · 1항 문구를 옛 '서버로 전송·수집되지 않습니다'로 되돌리면 → test_privacy_does_not_deny_quiz_transfer 가 실패.
  · home-app.js 에 track(ev2,{}) 처럼 이름을 변수로 보내는 호출을 더하면 → test_every_call_names_its_event 가 실패.
픽스처 없이 실제 파일을 읽는다. 날짜·데이터와 무관하다.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402  (홈 스크립트는 이 입구로만 읽는다)

Q = r"""\\?['"]"""   # HTML 속성 안의 \' 와 파이썬 문자열 안의 따옴표까지
CALL = re.compile(r'\btrack\(\s*' + Q + r'(\w+)' + Q
                  + r'|\bgtag\(\s*' + Q + r'(?:event|set)' + Q + r'\s*,\s*' + Q + r'(\w+)' + Q)
ANY_CALL = re.compile(r'\btrack\((?!\))|\bgtag\(\s*' + Q + r'(?:event|set)' + Q)
# 감싸는 함수 정의 한 줄(function track(ev,params){…gtag('event',ev,…)…}) — 이름을 변수로 넘기는 유일한 자리다
DEF = re.compile(r'function track\(ev,params\)\{[^\n]*')
KEY = re.compile(r'[{,]\s*(\w+)\s*:')


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _sources():
    out = [('home', HS.home_source())]
    rels = ['404.html'] + [os.path.relpath(p, ROOT).replace(os.sep, '/')
                          for p in sorted(glob.glob(os.path.join(ROOT, '*', 'index.html')))]
    rels += [os.path.relpath(p, ROOT).replace(os.sep, '/')
             for p in sorted(glob.glob(os.path.join(ROOT, 'tools', '*.py')))]
    for rel in rels:
        if rel == 'privacy/index.html':
            continue
        s = _read(rel)
        if rel.endswith('.py'):
            # 여러 줄로 이어 붙인 파이썬 문자열('…'\n  '…')을 한 덩이로 — 매개변수 이름이 줄 경계에 걸린다
            s = re.sub(r"""(['"])\s*\n\s*\1""", '', s)
        out.append((rel, s))
    return out


def _args(src, i):
    depth = 0
    for j in range(i, len(src)):
        c = src[j]
        if c == '(':
            depth += 1
        elif c == ')':
            depth -= 1
            if depth == 0:
                return src[i:j]
    raise AssertionError('괄호가 닫히지 않는 호출: %r' % src[i:i + 80])


def code_events():
    ev = {}
    for _rel, src in _sources():
        for m in CALL.finditer(src):
            name = m.group(1) or m.group(2)
            ev.setdefault(name, set()).update(KEY.findall(_args(src, src.index('(', m.start()))))
    return ev


def page_events():
    s = _read('privacy/index.html')
    i = s.find('id="ga-events"')
    assert i >= 0, '방침에 GA 전송 목록(id="ga-events")이 없다'
    block = s[i:s.index('</table>', i)]
    ev = {}
    for name, body in re.findall(r'<tr data-ev="(\w+)">(.*?)</tr>', block, re.S):
        cells = re.findall(r'<td>(.*?)</td>', body, re.S)
        assert re.findall(r'<code>(\w+)</code>', cells[0]) == [name], '%s 행의 첫 칸이 이벤트 이름이 아니다' % name
        assert name not in ev, '%s 행이 두 번 있다' % name
        ev[name] = set(re.findall(r'<code>(\w+)</code>', cells[1]))
    return ev


def test_scanner_sees_the_quiz_events():
    """훑기가 조용히 0개를 찾고 통과하지 않게 — 리뷰가 짚은 퀴즈 전송이 보여야 한다."""
    ev = code_events()
    assert {'correct'} <= ev.get('quiz_answer', set())
    assert {'score'} <= ev.get('quiz_complete', set())
    assert {'score', 'friend_score'} <= ev.get('challenge_result', set())
    assert len(ev) >= 20, '이벤트가 너무 적게 잡혔다 — 훑는 파일이나 호출 모양이 바뀌었는지 볼 것: %s' % sorted(ev)


def test_privacy_lists_exactly_what_code_sends():
    code, page = code_events(), page_events()
    missing = sorted('%s%s' % (e, '' if e not in page else sorted(ps - page[e]))
                     for e, ps in code.items() if e not in page or ps - page[e])
    extra = sorted('%s%s' % (e, '' if e not in code else sorted(ps - code[e]))
                   for e, ps in page.items() if e not in code or ps - code[e])
    assert not missing, '코드가 보내는데 방침 목록에 없는 이벤트·값: %s — privacy/index.html 1항 표에 적는다' % missing
    assert not extra, '방침 목록에 있는데 코드가 보내지 않는 이벤트·값: %s — 표에서 뺀다' % extra


def test_every_call_names_its_event():
    """이름을 변수로 넘기는 호출은 위 대조가 못 본다 — 정의(function track)만 빼고 모두 글자 이름이어야 한다."""
    bad = []
    for rel, src in _sources():
        src = DEF.sub('', src)
        n_any = len(ANY_CALL.findall(src))
        n_lit = len(CALL.findall(src))
        if n_any != n_lit:
            bad.append('%s(%d/%d)' % (rel, n_lit, n_any))
    assert not bad, '이벤트 이름을 글자로 쓰지 않은 track/gtag 호출이 있다: %s' % bad


def test_privacy_does_not_deny_quiz_transfer():
    s = _read('privacy/index.html')
    assert not re.search(r'퀴즈[^<]{0,40}서버로 전송·수집되지 않', s), '방침이 퀴즈 결과를 보내지 않는다고 적었다'
    assert '퀴즈 점수' in s and 'Google Analytics에 전송' in s
    # 방침을 고쳤으면 변경 이력에 날짜를 남긴다 — 머리의 '최근 개정'과 6항 이력의 마지막 날짜가 같아야 한다
    head = re.search(r'최근 개정 (\d{4}년 \d+월 \d+일)', s)
    hist = re.findall(r'<li>(\d{4}년 \d+월 \d+일) — ', s)
    assert head and hist and hist[-1] == head.group(1), '머리의 개정일과 변경 이력의 마지막 날짜가 다르다'
