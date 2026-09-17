# -*- coding: utf-8 -*-
"""퀴즈 진행 저장·나가기 확인·측정을 실제 함수로 돌려 고정한다(점검후속 개발 ③).

2026-09-15 고객 점검:
  - "← 테스트 선택"이 확인 없이 진행을 지웠다.
  - 새로고침·뒤로 가기에서 처음부터 다시 풀어야 했다(인앱 브라우저에서 잦다).
  - quiz_start 가 새로고침·다시 풀기까지 시작으로 잡아 이탈률이 부풀었고, 문항별 응답 측정이 없었다.

문자열 검사로는 '저장은 하는데 복원이 다른 시험지를 뽑는' 결함을 못 잡는다. 그래서 index.html 에서
퀴즈 코드를 꺼내 node 로 돌리고, 페이지를 새로 연 것처럼 한 번 더 평가해 이어 풀기를 확인한다.
"""
import io
import json
import os
import shutil
import subprocess
import tempfile

import pytest

import sys as _hs_sys  # noqa: E402
_hs_sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _quiz_src():
    """QUIZSETS 부터 showResult 함수 끝까지. 결과 화면을 실제로 거쳐야 '다시 풀기' 경로를 볼 수 있다.

    ⚠️ 예전에는 gradeOf 앞에서 잘라 showResult 가 없었고, 그래서 재시작 시험이 qClear() 를 직접 불러
       결함을 스스로 재현했다(리뷰 11번). 경계는 showResult 의 닫는 중괄호(줄 첫머리의 '}')다 —
       다음 함수까지 잡으면 사이의 전역 선언(let CHALLENGE 등)이 딸려 와 하네스 선언과 부딪힌다.
    """
    s = HS.home_source()
    a = s.find('const QUIZSETS')
    r = s.find('function showResult(')
    b = s.find('\n}', r) + 2
    assert a >= 0 and r > a and b > r, '퀴즈 코드 경계를 찾지 못했다 — 구조가 바뀌었으면 이 시험도 고칠 것'
    return s[a:b]


HARNESS = r"""
const STORE = %(store)s;
const THROW = %(throw)s;
const sessionStorage = {
  getItem(k){ if(THROW) throw new Error('blocked'); return k in STORE ? STORE[k] : null; },
  setItem(k,v){ if(THROW) throw new Error('blocked'); STORE[k] = String(v); },
  removeItem(k){ if(THROW) throw new Error('blocked'); delete STORE[k]; },
};
const EV = [];
function track(ev,p){ EV.push([ev,p]); }
let CONFIRM = true, ASKED = 0;
function confirm(){ ASKED++; return CONFIRM; }
const els = {};
function el(id){ return els[id] || (els[id] = {id, style:{display:id==='quiz-play'?'none':''}, innerHTML:'',
  textContent:'', classList:{set:new Set(), add(c){this.set.add(c)}, contains(c){return this.set.has(c)}},
  scrollIntoView(){} }); }
const document = { getElementById: el, querySelectorAll(){ return [0,1].map(()=>({style:{}, innerHTML:'',
  classList:{add(){}}})); } };
const history = { pushState(){} };
const location = { hash:'' };
const window = { scrollTo(){} };
function scrollBehavior(){ return 'auto'; }
function renderChalBar(){}
function versusHTML(){ return ''; }
function loadKakao(){ return Promise.resolve(); }
let CHALLENGE = null;
%(src)s
;(function(){ %(body)s })();
process.stdout.write(JSON.stringify(OUT));
"""


def _run(body, store=None, throw=False):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    js = HARNESS % {'store': json.dumps(store or {}), 'throw': 'true' if throw else 'false',
                    'src': 'var OUT;\n' + _quiz_src(), 'body': body}
    # ⚠️ 명령줄로 넘기지 않는다. showResult 까지 담으면 Windows 명령줄 한도(약 32KB)를 넘어
    #    WinError 206 으로 시험 전체가 실행조차 안 된다(2026-09-17 백로그 12 작업 중 실제로 그랬다).
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        p = subprocess.run(['node', path], capture_output=True, timeout=60)
    finally:
        os.remove(path)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


FIRST = """
startQuiz('investor');
answerQ(0); nextQ(); answerQ(1);
OUT = {ev:EV, store:STORE, qs:QUIZ.map(x=>x.q), idx:qIdx, score:qScore, results:qResults};
"""


def test_answers_are_measured_and_progress_is_saved():
    o = _run(FIRST)
    starts = [p for e, p in o['ev'] if e == 'quiz_start']
    assert starts == [{'quiz_type': 'investor', 'start_type': 'new'}], starts
    ans = [p for e, p in o['ev'] if e == 'quiz_answer']
    assert [a['idx'] for a in ans] == [1, 2], ans
    assert [a['correct'] for a in ans] == o['results'], 'quiz_answer.correct 가 채점과 다르다'
    sv = json.loads(o['store']['agong_quiz'])
    assert sv['set'] == 'investor' and sv['idx'] == 1 and sv['ch'] == [0, 1], sv


def test_reload_resumes_the_same_sheet_without_double_counting():
    first = _run(FIRST)
    o = _run("""
startQuiz('investor', undefined, true);
OUT = {ev:EV, qs:QUIZ.map(x=>x.q), idx:qIdx, score:qScore, answered:qAnswered, results:qResults};
""", store=first['store'])
    assert o['qs'] == first['qs'], '이어 풀기가 다른 시험지를 뽑았다 — 시드 복원이 깨졌다'
    assert (o['idx'], o['score'], o['results']) == (first['idx'], first['score'], first['results'])
    assert o['answered'] is True, '답한 문항의 해설 상태가 복원되지 않았다'
    starts = [p for e, p in o['ev'] if e == 'quiz_start']
    assert starts == [{'quiz_type': 'investor', 'start_type': 'resume'}], starts
    assert not [e for e, _ in o['ev'] if e == 'quiz_answer'], '복원하면서 quiz_answer 를 다시 보냈다'


def test_opening_without_answering_is_not_a_resume():
    """해시로 열기만 해도 빈 저장이 생긴다. 그걸 resume 으로 세면 수치가 다시 부푼다(브라우저 확인에서 발견)."""
    o = _run("""
startQuiz('investor', undefined, true);
startQuiz('investor');
OUT = {ev:EV};
""")
    starts = [p['start_type'] for e, p in o['ev'] if e == 'quiz_start']
    assert starts == ['new', 'new'], starts


def test_other_set_or_other_seed_does_not_resume():
    first = _run(FIRST)
    o = _run("""
startQuiz('beginner', undefined, true); const a = qIdx;
startQuiz('investor', 12345); const b = qIdx;
OUT = {a, b, ev:EV};
""", store=first['store'])
    assert o['a'] == 0 and o['b'] == 0, '다른 세트·다른 시드인데 이어 풀었다'


def test_exit_asks_while_playing_and_clears_only_when_confirmed():
    first = _run(FIRST)
    o = _run("""
startQuiz('investor', undefined, true);
CONFIRM = false; backToPick();
const kept = {play: document.getElementById('quiz-play').style.display, saved: 'agong_quiz' in STORE, asked: ASKED};
CONFIRM = true; backToPick();
const gone = {play: document.getElementById('quiz-play').style.display, saved: 'agong_quiz' in STORE, asked: ASKED};
startQuiz('investor', undefined, true); backToPick(true);
const back = {saved: 'agong_quiz' in STORE, asked: ASKED};
OUT = {kept, gone, back};
""", store=first['store'])
    assert o['kept'] == {'play': '', 'saved': True, 'asked': 1}, '취소했는데 나가졌거나 저장이 지워졌다: %s' % o['kept']
    assert o['gone'] == {'play': 'none', 'saved': False, 'asked': 2}, '확인했는데 남았다: %s' % o['gone']
    assert o['back']['asked'] == 2, '뒤로 가기에서도 확인창을 띄웠다'
    assert o['back']['saved'] is True, '뒤로 가기가 저장을 지웠다 — 앞으로 가기로 이어 풀 수 없다'


def test_retry_after_finishing_is_marked_retry():
    """10문항을 끝까지 풀어 실제 결과 화면(nextQ → showResult)을 거친 뒤 '다시 풀기'는 retry 로 새로 시작한다.

    깨뜨리면 빨개지는 것: home-app.js 의 showResult 에서 qClear() 나 qMarkDone() 을 빼면 — 저장이 남아
    다시 풀기가 같은 시험지 10번 문항으로 되돌아가고 start_type 이 resume 이 된다(리뷰 11번, 변이로 확인).
    픽스처: 빈 sessionStorage 에서 투자자 세트를 처음부터 끝까지 푼 실제 흐름. 시험 본문은 저장을 직접 지우지 않는다.
    """
    o = _run("""
startQuiz('investor');
for (let i=0;i<QUIZ.length;i++){ answerQ(0); nextQ(); }
const afterResult = {saved:'agong_quiz' in STORE};
startQuiz();
OUT = {ev:EV, afterResult, idx:qIdx, answered:qAnswered};
""")
    assert [p for e, p in o['ev'] if e == 'quiz_complete'], '결과 화면(showResult)을 거치지 않았다 — 시험이 헛돈다'
    assert o['afterResult']['saved'] is False, '결과 화면 뒤에도 진행 저장이 남았다'
    starts = [p['start_type'] for e, p in o['ev'] if e == 'quiz_start']
    assert starts == ['new', 'retry'], starts
    assert o['idx'] == 0 and o['answered'] is False, '다시 풀기가 처음 문항에서 시작하지 않는다'


def test_blocked_storage_does_not_break_the_quiz():
    o = _run(FIRST, throw=True)
    assert o['idx'] == 1 and len(o['results']) == 2, '저장소가 막히면 퀴즈가 멈춘다'


def test_time_copy_matches_real_duration():
    """해설 포함 실제 4~6분(요청서 실측) — '3분'으로 약속하지 않는다."""
    files = ['index.html', 'weekly/index.html', 'faq/index.html', 'cycle/index.html', 'burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html',
             'tools/make_og_cards.py', 'tools/make_investor_cards.py', 'tools/make_naver_post.py']
    import re
    bad = []
    for f in files:
        s = HS.home_source() if HS.is_home(f) else io.open(os.path.join(ROOT, f), encoding='utf-8').read()
        HS.require(s, '5분', what=f)   # 고친 표기를 실제로 읽었는가 — 못 읽으면 '3분 없음'이 헛돈다
        bad += ['%s: %s' % (f, m.group(0)) for m in re.finditer(r'.{0,12}3분(?![기위]).{0,6}', s)]
    assert not bad, "퀴즈 시간 표기에 '3분'이 남았다: %s" % bad
