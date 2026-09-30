# -*- coding: utf-8 -*-
"""퀴즈 결과 공유 — 카드 그림과 공유 문구·점수 분모·대결 판정을 실제 home-quiz.js 로 돌려 고정한다(전수리뷰 #86·#58·#57).

2026-09-30 전수 리뷰:
  - #86 재건축 퀴즈 공유 문구(shareTaunt)에 calc 분기가 없어, 카드 그림(share/calc-N.png)은 재건축 문구인데 카카오 설명·
        링크 복사 본문은 투자자 문구('호재를 악재로 읽고 계시네요')로 나갔다.
  - #58 공유 문구·카카오 제목이 분모를 '/10'으로 박아 결과 카드(QUIZ.length)·대결 상한(QUIZ_LEN)과 따로 놀았다.
  - #57 대결 결과 뒤 '다시 풀기'(새 난수 시험지)에도 도전 띠·VS 판정·challenge_result 를 다시 냈다.

home-quiz.js 전체와 home-app.js 의 BLV 를 node 에 올리고, DOM·저장소·측정은 작은 모형으로 둔다.
"""
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402

HARNESS = r"""
const STORE={};
const sessionStorage={getItem(k){return k in STORE?STORE[k]:null},setItem(k,v){STORE[k]=String(v)},removeItem(k){delete STORE[k]}};
const EV=[]; function track(e,p){EV.push([e,p]);}
const els={};
function mk(id){return {id,style:{},innerHTML:'',textContent:'',hidden:false,dataset:{},
  classList:{s:new Set(),add(c){this.s.add(c)},remove(c){this.s.delete(c)},contains(c){return this.s.has(c)},toggle(){}},
  setAttribute(){},scrollIntoView(){}};}
function el(id){return els[id]||(els[id]=mk(id));}
const document={getElementById:el,querySelectorAll(){return [];},querySelector(){return null;}};
const history={pushState(){},replaceState(){}};
const location={search:'',hash:'',pathname:'/'};
const window={scrollTo(){}};
function scrollBehavior(){return 'auto';}
function loadKakao(){return Promise.resolve();}
function setTimeout(){}
%(blv)s
%(quiz)s
;(function(){ %(body)s })();
process.stdout.write(JSON.stringify(OUT));
"""


def _blv(src):
    a = src.find('const BLV=[')
    b = src.find('\n];', a) + 3
    assert a >= 0 and b > a, 'home-app.js 에서 BLV 를 찾지 못했다'
    return src[a:b]


def _run(body, quiz_len=None):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    files = dict(HS.home_files())
    quiz = files['home-quiz.js']
    if quiz_len is not None:
        assert 'const QUIZ_LEN=10;' in quiz
        quiz = quiz.replace('const QUIZ_LEN=10;', 'const QUIZ_LEN=%d;' % quiz_len)
    js = HARNESS % {'blv': _blv(files['home-app.js']), 'quiz': 'var OUT;\n' + quiz, 'body': body}
    fd, path = tempfile.mkstemp(suffix='.js')
    with os.fdopen(fd, 'w', encoding='utf-8') as f:
        f.write(js)
    try:
        p = subprocess.run(['node', path], capture_output=True, timeout=60)
    finally:
        os.remove(path)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


def _norm(t):
    return re.sub(r'\s+', ' ', t.replace('...', '…')).strip()


def test_share_text_says_what_the_card_says_for_every_set():
    """세 세트 모두, 점수별 공유 문구 = 그 점수 카드(share/<세트>-N.png)의 도발 문구 두 줄.

    변이(실제로 확인): shareTaunt 에서 calc 분기(QUIZSETS[curSet].taunt)를 빼면 calc 0점이 투자자 문구가 되어
          빨개진다. make_calc_cards 가 표를 읽지 않고 옛 손 사본으로 돌아가 한 칸만 바꿔도 빨개진다.
    픽스처: 실제 카드 생성기 세 개(make_beginner_cards.LEVELS · make_investor_cards.tier_of · make_calc_cards.levels())
            와 실제 home-quiz.js. 투자자 카드는 폰트 때문에 '...'을 쓰고 사이트는 '…'이라 그 한 가지만 같게 본다.
    """
    import make_beginner_cards as MB
    import make_calc_cards as MC
    import make_investor_cards as MI
    o = _run("OUT={};for(const k of ['beginner','investor','calc']){curSet=k;"
             "OUT[k]=[...Array(11).keys()].map(s=>shareTaunt(s));}")
    want = {'beginner': [' '.join(t) for _, _, t in MB.LEVELS],
            'investor': [' '.join(MI.tier_of(s)[2]) for s in range(11)],
            'calc': [' '.join(t) for _, _, t in MC.levels()]}
    for k in want:
        got = [_norm(x) for x in o[k]]
        assert got == [_norm(x) for x in want[k]], (k, [(i, a, b) for i, (a, b) in enumerate(zip(got, want[k]))
                                                       if a != _norm(b)][:3])


def test_share_denominator_follows_the_quiz_length():
    """공유 문구·카카오 제목의 점수 분모는 결과 카드와 같은 QUIZ.length 다(문항 수를 12로 바꾼 상태로 돈다).

    변이: shareTxt 의 `/${QUIZ.length}` 를 옛 '/10' 으로 되돌리면 빨개진다(실제로 확인).
    픽스처: QUIZ_LEN 만 12로 바꾼 실제 home-quiz.js, 투자자 세트(문항 풀 20개라 12문항이 뽑힌다), 11점.
    """
    o = _run("curSet='investor';QUIZ=drawQuiz('investor',123);qScore=11;OUT={n:QUIZ.length,txt:shareTxt()};",
             quiz_len=12)
    assert o['n'] == 12
    assert '11/12' in o['txt'] and '/10' not in o['txt'], o['txt']
    src = dict(HS.home_files())['home-quiz.js']
    assert not re.search(r'\$\{qScore\}/10', src), '공유 문구 어딘가에 분모 /10 이 남았다'


def test_retry_after_a_challenge_is_not_scored_as_the_challenge():
    """친구와 같은 시험지(시드)일 때만 대결이다 — 결과 뒤 '다시 풀기'(새 시드)는 도전 띠·VS·challenge_result 를 내지 않는다.

    변이(실제로 확인): chalActive 를 옛 조건(`CHALLENGE&&CHALLENGE.set===curSet`)으로 되돌리면 두 번째 판에
          challenge_result 가 또 나가 빨개진다. '다시 도전하기'(같은 시드) 경로는 여전히 대결로 센다.
    픽스처: /?c=7&s=calc&q=1z 대결 링크(시드 71)로 푼 뒤 결과 화면의 '다시 풀기'(startQuiz()), 이어 같은 시드 재도전.
    """
    o = _run(r"""
CHALLENGE={score:7,set:'calc',seed:71};
const play=()=>{for(let i=0;i<QUIZ.length;i++){qAnswered=false;qIdx=i;answerQ(0);} showResult();};
startQuiz('calc',71); const bar1=els['chal-bar'].style.display; play();
const vs1=/class="versus/.test(els['quiz-result'].innerHTML);
startQuiz(); const bar2=els['chal-bar'].style.display; const seed2=curSeed; play();
const vs2=/class="versus/.test(els['quiz-result'].innerHTML);
startQuiz('calc',CHALLENGE.seed); play();
const vs3=/class="versus/.test(els['quiz-result'].innerHTML);
OUT={bar1,bar2,vs1,vs2,vs3,seed2,cr:EV.filter(e=>e[0]==='challenge_result').length};
""")
    assert o['bar1'] == '' and o['vs1'], '대결 첫 판에 도전 띠·VS 가 없다'
    assert o['seed2'] != 71
    assert o['bar2'] == 'none' and not o['vs2'], '다른 시험지인데 대결로 판정했다'
    assert o['vs3'] and o['cr'] == 2, o   # 첫 판 + 같은 시드 재도전
