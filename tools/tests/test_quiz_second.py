# -*- coding: utf-8 -*-
"""퀴즈 2차(점검후속 개발 ⑧)를 고정한다.

2026-09-15 고객 점검:
  - 링크 복사·밴드·문자 공유에는 점수가 안 보였다 → 점수별 정적 공유 페이지.
  - 대결 중 '다시 도전'이 시드를 넘기지 않아 다른 시험지를 풀었다.
  - 보기 순서가 고정이라 정답이 첫 보기에 몰려 위치로 답이 보였다 → 시드로 섞기.
  - 틀린 문항을 되짚을 길이 없었다 → 결과 점을 누르면 해설.
  - 제도 문항이 시간이 지나면 틀린 답이 된다 → 기준일·검토 기한, 감시가 기한 경과를 알린다.
  - 인허가→입주 기간을 문항마다 다르게 말했다 → 데이터 세션 정본(sido_zones)을 따른다.

보기 섞기·해설은 실제 퀴즈 코드를 node 로 돌려 본다. 특히 '문항 선택이 옛 시드와 같은가'를 옛 알고리즘을
다시 구현해 대조한다 — 섞기 난수를 문항 선택 난수에 이어 쓰면 이미 보낸 대결 링크가 다른 문제를 뽑는다.
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import make_quiz_share_pages as MQ  # noqa: E402
import quiz_review as QR  # noqa: E402
import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _read(*p):
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def _quizsets():
    s = _read('index.html')
    return s[s.find('const QUIZSETS'):s.find('const QUIZ_LEN')]


# ── 기간 정본 ──────────────────────────────────────────────────────────────
def test_quiz_period_wording_follows_the_canon():
    qs = _quizsets()
    for bad in ('4~6년', '3~4년 뒤', '3~3.5년', '3년~3년 반', '인허가에서 입주까지', '인허가에서 착공까지'):
        assert bad not in qs, "퀴즈에 정본과 다른 기간 표현 '%s' 이 남았다" % bad
    pairs = re.findall(r'과거 (\d+)개월에서 최근 (\d+)개월', qs)
    assert pairs, '착공→준공 기간을 정본 값으로 말하는 문항이 없다'
    for old, new in pairs:
        assert (int(old), int(new)) == (SZ.START_DONE_MONTHS_OLD, SZ.START_DONE_MONTHS_NEW), (
            '퀴즈의 착공→준공 %s→%s개월이 정본 %d→%d와 다르다' % (old, new, SZ.START_DONE_MONTHS_OLD, SZ.START_DONE_MONTHS_NEW))
    for m in re.finditer(r'(최근 )(\d+)개월\)', qs):
        assert int(m.group(2)) == SZ.START_DONE_MONTHS_NEW


# ── 제도 문항 기준일·검토 기한 ─────────────────────────────────────────────
def test_dated_policy_items_carry_asof_and_review():
    qs = _quizsets()
    tagged = {q for q, _, _ in QR.items(qs)}
    for m in re.finditer(r"\{q:'((?:[^'\\]|\\.)*)',(.*?)exp:'((?:[^'\\]|\\.)*)'\}", qs, re.S):
        text = m.group(1) + m.group(3)
        if re.search(r'\d·\d+ ?대책|추진 ?중|20\d\d년 ?\d{1,2}월', text):
            q = re.sub(r'<[^>]+>', '', m.group(1))
            assert q in tagged, '날짜가 박힌 제도 문항에 asof·review 가 없다: %s' % q[:40]
    for q, asof, review in QR.items(qs):
        assert datetime.date.fromisoformat(review) > datetime.date.fromisoformat(asof), '%s: 검토 기한이 기준일보다 앞선다' % q[:30]


def test_review_check_flags_only_overdue_items():
    qs = _quizsets()
    n = len(QR.items(qs))
    assert n >= 4, '제도 문항 태그를 %d개밖에 못 읽었다' % n
    assert QR.overdue(qs, datetime.date(2026, 9, 15)) == []
    late = QR.overdue(qs, datetime.date(2030, 1, 1))
    assert len(late) == n and all('검토 기한' in x for x in late)
    assert 'QR.overdue' in _read('tools', 'check_freshness.py'), '감시가 검토 기한을 보지 않는다'


def test_asof_is_shown_with_the_explanation():
    assert 'item.asof?' in _read('index.html'), '해설에 제도 기준일을 보여주지 않는다'


# ── 대결 재도전 ────────────────────────────────────────────────────────────
def test_challenge_retry_keeps_the_same_sheet():
    s = _read('index.html')
    m = re.search(r"track\('challenge_retry'[^\"]*\"", s)
    assert m and 'startQuiz(curSet,CHALLENGE.seed)' in m.group(0), '대결 재도전이 시드를 넘기지 않는다'


# ── node 로 퀴즈 코드 돌리기 ───────────────────────────────────────────────
HARNESS = r"""
const sessionStorage={getItem(){return null},setItem(){},removeItem(){}};
function track(){} function confirm(){return true}
const document={getElementById(){return {style:{},classList:{add(){},contains(){return false}},innerHTML:'',textContent:'',scrollIntoView(){}}},querySelectorAll(){return []}};
const history={pushState(){}}; const location={hash:''}; const window={scrollTo(){}};
function scrollBehavior(){return 'auto'} function renderChalBar(){} let CHALLENGE=null;
var OUT;
%(src)s
;(function(){ %(body)s })();
process.stdout.write(JSON.stringify(OUT));
"""


def _run(body):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    s = _read('index.html')
    a, b = s.find('const QUIZSETS'), s.find('function showResult(')
    assert a >= 0 and b > a
    p = subprocess.run(['node', '-e', HARNESS % {'src': s[a:b], 'body': body}], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')[-1500:]
    return json.loads(p.stdout.decode('utf-8'))


SHUFFLE = r"""
const orig={}; for(const k in QUIZSETS){ QUIZSETS[k].Q.forEach(it=>{ orig[it.q]=it; }); }
const sets=Object.keys(QUIZSETS);
let same=true, keep=true; const first={}, total={};
sets.forEach(k=>{first[k]=0;total[k]=0;});
for(let s=1;s<=300;s++){
  for(const k of sets){
    const a=drawQuiz(k,s*7919), b=drawQuiz(k,s*7919);
    if(JSON.stringify(a)!==JSON.stringify(b)) same=false;
    a.forEach(it=>{
      const o=orig[it.q];
      if(it.opts[it.answer]!==o.opts[o.answer] || it.opts.slice().sort().join('|')!==o.opts.slice().sort().join('|')) keep=false;
      total[k]++; if(it.answer===0) first[k]++;
    });
  }
}
/* 옛 문항 선택 알고리즘(보기 섞기 이전) — 이미 보낸 대결 링크가 같은 문항을 뽑는지 대조 */
function oldDraw(setKey,seed){
  const rnd=mulberry32(seed>>>0);
  const shuf=a=>{for(let i=a.length-1;i>0;i--){const j=Math.floor(rnd()*(i+1));const t=a[i];a[i]=a[j];a[j]=t;}return a;};
  const pool=shuf(QUIZSETS[setKey].Q.slice());
  const n=Math.min(QUIZ_LEN,pool.length);
  const key=pool.find(x=>x.k), mkt=pool.filter(x=>x.m&&!x.k), rest=pool.filter(x=>!x.m);
  if(!key||mkt.length<2||rest.length<n-3) return pool.slice(0,n);
  const pick=shuf(rest.slice(0,n-3).concat(mkt.slice(0,2)));
  pick.splice(Math.floor(rnd()*3),0,key);
  return pick;
}
let sel=true;
for(let s=1;s<=80;s++){ for(const k of sets){ if(drawQuiz(k,s).map(x=>x.q).join('|')!==oldDraw(k,s).map(x=>x.q).join('|')) sel=false; } }
OUT={same,keep,first,total,sel};
"""


def test_options_are_shuffled_by_seed_without_changing_the_questions():
    o = _run(SHUFFLE)
    assert o['same'], '같은 시드인데 시험지(보기 순서)가 달라진다 — 이어 풀기·대결이 깨진다'
    assert o['keep'], '보기를 섞으며 정답 텍스트나 보기 구성이 바뀌었다'
    assert o['sel'], '문항 선택이 옛 시드와 달라졌다 — 이미 보낸 대결 링크가 다른 문제를 뽑는다'
    for k, t in o['total'].items():
        share = o['first'][k] / float(t)
        assert 0.35 <= share <= 0.65, '%s: 정답이 첫 보기인 비율 %.2f — 위치로 답이 보인다' % (k, share)


def test_result_dot_opens_that_question():
    o = _run(r"""
QUIZ=drawQuiz('calc',12345);
qChoices=QUIZ.map((it,i)=> i%2 ? it.answer : 1-it.answer);
OUT={no:dotExpHTML(0), ok:dotExpHTML(1), exp0:QUIZ[0].exp, ans0:QUIZ[0].opts[QUIZ[0].answer],
     mine0:QUIZ[0].opts[qChoices[0]], ans1:QUIZ[1].opts[QUIZ[1].answer]};
""")
    assert o['exp0'] in o['no'] and ('정답: ' + o['ans0']) in o['no'], '틀린 문항 해설에 정답·해설이 없다'
    assert ('내 답: ' + o['mine0']) in o['no'], '틀린 문항에 내 답이 없다'
    assert '내 답' not in o['ok'] and ('정답: ' + o['ans1']) in o['ok']
    s = _read('index.html')
    assert 'onclick="showDotExp(${i})"' in s and 'id="rc-exp"' in s, '결과 점이 해설을 열지 않는다'


# ── 점수별 공유 페이지 ─────────────────────────────────────────────────────
def test_score_share_pages_exist_and_match_the_quiz():
    slug, sets, n = MQ.load()
    for path, body in MQ.pages():
        assert os.path.exists(path), '점수 공유 페이지가 없다: %s — python tools/make_quiz_share_pages.py' % path
        assert io.open(path, encoding='utf-8').read() == body, '점수 공유 페이지가 퀴즈 세트와 어긋난다: %s' % path
    assert len(MQ.pages()) == len(sets) * (n + 1)
    for key, _, _ in sets:
        p = _read(slug[key], '7', 'index.html')
        assert 'share/%s-7.png' % key in p and 'rel="canonical" href="https://www.agongmap.co.kr/%s/"' % slug[key] in p


def test_challenge_link_points_to_the_score_page():
    s = _read('index.html')
    assert 'https://www.agongmap.co.kr/${slug}/${qScore}/?c=' in s, '대결 링크가 점수 공유 페이지로 가지 않는다'
    assert 'const slug=QUIZ_SLUG[curSet]' in s
