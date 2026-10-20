# -*- coding: utf-8 -*-
"""소개(/about/)·FAQ(/faq/)·홈 산출 방법에 글자로 박은 수치가 정본(모델 상수·데이터·사이클 분석)과 같은지 본다(전수리뷰 #112·#69).

두 페이지는 사람이 쓴 파일이라 배치가 고치지 않는다. 2026-09-30 전수 리뷰 때 아래 수치는 값은 맞았지만 대조하는
시험이 없어, 원천·분석·모델이 바뀌어도 아무것도 빨개지지 않았다(CLAUDE.md '사람이 센 수를 박지 않는다').

  ① '인허가는 같은 해 착공보다 15%쯤 많다'(about·faq·홈 index.html) — 정본은 시도 리포트가 같은 문장을 굽는
     sido_zones.permit_over_start_pct(전국 착공÷인허가의 역수, PERMIT_OVER_STEP=5 단위 반올림). 지금 0.867 → 15.3% → '15%쯤'.
     손 숫자는 리포트 값과 **같은 단위**(5의 배수)여야 하고, 게이트는 리포트 값에서 한 칸(PERMIT_OVER_STEP) 안까지 봐 준다 —
     합계 비율이라 한 해가 더 들어와도 크게 움직이지 않지만(가장 치우친 해 2023년 0.54 와 같은 해가 한 번 더 들어와도 15.3% → 18.1%),
     17.5% 를 넘는 날 리포트는 '20%쯤'이 된다. 그날 커밋을 막지 않고, 정확히 같은지는 배치 기록 ℹ️ 줄(batch_notes.hand_permit_lines)이
     알린다(전수리뷰 X1-11 — 예전엔 측정값 ±5%p 라 리포트 20% 와 손 페이지 15% 가 갈린 채 초록이었고 아무 데도 알리지 않았다).
  ② '착공부터 준공까지 2018년 전에는 약 28개월, 그 뒤로는 약 37개월'(faq 본문·JSON-LD) — 정본은 /cycle/ 의
     D.prose lead_old·lead_new(rebuild_cycle_analysis 가 사람 손으로 돌 때만 바뀐다 — 배치는 이 칸을 고치지 않으므로
     게이트를 막지 않는다. 재산정한 사람의 PR 에서 빨개진다).
  ③ FAQ 등급 문턱 '1.5배 미만은 균형, 1.5배·3배·4.5배 이상이면 부족·매우 부족·심각한 부족'(1년 적정물량의 N배, 2026-10-05) —
     정본은 sido_zones.GRADE_CUTS(× 연수 = cut_mult)·GRADE_LABS.
  ④ FAQ '부린이 테스트 10문항 … 무주택 달걀부터 부동산 봉황까지 11단계' — 정본은 home-quiz.js QUIZ_LEN 과
     home-app.js BLV(개수·처음·마지막 이름).
'16개 시도'는 test_handwritten_sido_count 가 이미 본다.

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · about/index.html(또는 홈 index.html)의 '15%쯤'을 '25%쯤'으로 바꾸면 ①이 실패한다. '17%쯤'(리포트와 다른 단위)으로 바꿔도 실패한다.
  · batch_notes.hand_permit_lines 의 정확 대조를 측정값 ±5 허용으로 바꾸면 ①의 배치 기록 시험이 실패한다.
  · faq/index.html 본문의 '약 37개월'을 '약 36개월'로 바꾸면 ②가 실패한다(JSON-LD 쪽만 바꿔도 실패).
  · sido_zones.GRADE_CUTS 의 1.5 를 1.6 으로 바꾸면 ③이 실패한다.
  · faq '11단계'를 '10단계'로 바꾸면 ④가 실패한다.
픽스처 없이 실제 파일과 데이터(data-rest.json — 배치가 split_data 로 먼저 굽는다)를 읽는다.
"""
import io
import json
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402  (홈 스크립트는 이 입구로만 읽는다)
import sido_zones as SZ  # noqa: E402

PERMIT_TOL = SZ.PERMIT_OVER_STEP   # %p — 리포트의 반올림 단위 한 칸. 근거는 위 독스트링 ①


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


import batch_notes as BN  # noqa: E402
HAND_PERMIT = BN.HAND_PERMIT_PAGES   # 배치 기록 줄(hand_permit_lines)과 같은 페이지 목록 — 한쪽에만 페이지를 더하면 게이트와 알림이 갈린다


def _hand_permit_numbers():
    out = {}
    for rel in HAND_PERMIT:
        text = HS.home_source() if HS.is_home(rel) else _read(rel)
        got = [int(x) for x in re.findall(r'착공보다 (\d+)%쯤 많', text)]
        assert got, "%s: '착공보다 N%%쯤 많' 문장을 못 찾았다 — 문구가 바뀌었으면 이 시험도 고칠 것" % rel
        out[rel] = got
    return out


def test_permit_excess_percent_follows_measured_conversion():
    st = SZ._load_stats()
    report = SZ.permit_over_start_pct(st)          # 시도 리포트가 같은 문장에 굽는 값
    assert report is not None, '전국 착공÷인허가를 재지 못했다'
    for rel, got in _hand_permit_numbers().items():
        for n in got:
            assert n % SZ.PERMIT_OVER_STEP == 0, '%s: %d%%쯤 — 리포트와 같은 %d 단위로 적는다' % (rel, n, SZ.PERMIT_OVER_STEP)
            assert abs(n - report) <= PERMIT_TOL, (
                '%s: 인허가가 착공보다 %d%%쯤 많다고 적었는데 리포트는 %d%%쯤 — 문장을 고친다' % (rel, n, report))


def test_hand_permit_mismatch_reaches_the_batch_record():
    """손 페이지의 'N%쯤'이 리포트 값(permit_over_start_pct)과 **정확히** 다르면 배치 기록에 ℹ️ 한 줄이 실린다 — 게이트는 한 칸까지 봐
    주므로 갈린 날 사람에게 닿는 통로다(전수리뷰 X1-11). 실데이터는 두 갈래 모두 의미 있게 본다(같으면 줄 없음, 다르면 그 페이지 이름이
    줄에 있다). 합성은 리포트가 '20%쯤'이 되는 상태(착공÷인허가 0.8461 → 18.2%)에서 손 문장 15%·20% 두 갈래.
    변이(실제로 확인): hand_permit_lines 의 정확 대조(`int(n) != want`)를 측정값 ±5 허용으로 바꾸면 합성 15% 갈래가 빨개진다.
    """
    import batch_notes as N
    st = SZ._load_stats()
    want = SZ.permit_over_start_pct(st)
    off = sorted(rel for rel, got in _hand_permit_numbers().items() if any(n != want for n in got))
    real = N.hand_permit_lines(st)
    if off:
        assert len(real) == 1 and all(rel in real[0] for rel in off) and '%d%%쯤' % want in real[0], real
    else:
        assert real == [], real
    dates = ['%d.%02d' % (y, m) for y in (2012, 2013) for m in range(1, 13)]
    syn = {'인허가': {'dates': dates, 'series': {'전국': [100.0 * m for m in range(1, 13)] * 2}},
           '착공': {'dates': dates, 'series': {'전국': [84.61] * 24}}}
    assert SZ.permit_over_start_pct(syn) == 20
    line = N.hand_permit_lines(syn, {'about/index.html': '인허가는 같은 해 착공보다 15%쯤 많고'})
    assert len(line) == 1 and 'about/index.html' in line[0] and '20%쯤' in line[0] and line[0].startswith(N.ML.MARK), line
    assert N.hand_permit_lines(syn, {'about/index.html': '인허가는 같은 해 착공보다 20%쯤 많고'}) == []
    assert N.hand_permit_lines({}, {'about/index.html': '착공보다 15%쯤 많'}) == [], '리포트가 구절을 빼는 상태(잴 수 없음)에는 줄이 없다'


def _cycle_prose():
    s = _read('cycle/index.html')
    m = re.search(r'const D=(\{.*?\});\n', s, re.S)
    assert m, 'cycle 페이지에서 const D 를 찾지 못했다'
    return json.loads(m.group(1))['prose']


def _faq_parts():
    """FAQ 의 두 벌 — 검색용 FAQPage JSON-LD 와 사람이 읽는 <main> 본문. 같은 문턱 문장을 각각 정확히 한 번씩 대조한다(전수리뷰 P-4)."""
    s = _read('faq/index.html')
    m = re.search(r'<script type="application/ld\+json">\s*(\{.*?"FAQPage".*?\})\s*</script>', s, re.S)
    assert m, 'FAQPage JSON-LD 를 못 찾았다'
    i, j = s.find('<main'), s.find('</main>')
    assert 0 <= i < j, 'FAQ <main> 을 못 찾았다'
    return (('JSON-LD', m.group(1)), ('본문', s[i:j]))


def test_faq_lead_months_follow_cycle_analysis():
    prose = _cycle_prose()
    want = (int(prose['lead_old']), int(prose['lead_new']))
    got = [(int(a), int(b)) for a, b in
           re.findall(r'2018년 전에는 약 (\d+)개월, 그 뒤로는 약 (\d+)개월', _read('faq/index.html'))]
    assert len(got) == 2, 'FAQ 본문과 JSON-LD 두 곳에서 착공→준공 개월 수를 찾아야 한다: %s' % got
    assert all(g == want for g in got), 'FAQ 는 %s, 사이클 분석(D.prose)은 %s' % (got, want)


def test_faq_grade_thresholds_follow_model_cuts():
    """FAQ 등급 문턱 문장의 배수·이름이 모델(GRADE_CUTS × 연수 = cut_mult, GRADE_LABS)과 같다.
    2026-10-05 안 A′로 단위가 '1년 적정물량의 N배'(1.5·3·4.5배)로 바뀌었다. 변이(실제로 확인): GRADE_CUTS 의 1.5 를 1.6 으로
    바꾸면 빨개진다(4.5배 → 4.8배). 화면 본문(q7)만 '2배 미만은 균형, 2배 이상이면 부족'으로 바꿔도 빨개진다(전수리뷰 P-4 —
    예전엔 re.search 가 앞에 있는 JSON-LD 사본만 맞춰 보고 사람이 읽는 본문은 대조하지 않았다)."""
    pat = re.compile(r'모자람 없이 남으면 (\S+ \S+), ([\d.]+배) 미만은 (\S+), ([\d.]+배) 이상이면 (\S+), ([\d.]+배) 이상이면 (.+?), '
                     r'([\d.]+배) 이상이면 (.+?)이다')
    c4, c3, c2 = (SZ.cut_mult(x) for x in SZ.GRADE_CUTS[:3])
    L = SZ.GRADE_LABS
    want = (L['g0'], c2, L['g1'], c2, L['g2'], c3, L['g3'], c4, L['g4'])
    for part, text in _faq_parts():
        got = [m.groups() for m in pat.finditer(text)]
        assert len(got) == 1, 'FAQ %s 에서 등급 문턱 문장을 %d번 찾았다(정확히 한 번이어야 한다) — 문구가 바뀌었으면 이 시험도 고칠 것' % (
            part, len(got))
        assert got[0] == want, 'FAQ %s 는 %s, 모델은 %s' % (part, got[0], want)


def test_faq_burini_quiz_counts_follow_quiz_code():
    src = HS.home_source()
    qlen = int(re.search(r'const QUIZ_LEN=(\d+);', src).group(1))
    blv = re.findall(r"\{lv:'LV\d+',emoji:'[^']+',g:'([^']+)'", re.search(r'const BLV=\[(.*?)\n\];', src, re.S).group(1))
    assert len(blv) >= 2, 'BLV 를 못 읽었다'
    s = _read('faq/index.html')
    n = [int(x) for x in re.findall(r'(\d+)문항', s)]
    assert len(n) == 2 and all(x == qlen for x in n), 'FAQ 부린이 테스트 문항 수 %s, QUIZ_LEN %d' % (n, qlen)
    m = re.search(r'(\S+ \S+)부터 (\S+ \S+)까지 (\d+)단계', s)
    assert m, 'FAQ 부린이 단계 문장을 못 찾았다'
    assert (m.group(1), m.group(2), int(m.group(3))) == (blv[0], blv[-1], len(blv)), (m.groups(), blv[0], blv[-1], len(blv))


def test_faq_structured_data_asks_what_the_page_asks():
    """FAQ 검색용 구조화 데이터(FAQPage JSON-LD)의 질문이 화면의 질문과 같은 순서·같은 글이다. 재현한 실제 상태(2026-10-06 리뷰):
    화면 11문항 중 8문항만 실려 '판정이 균형인데…'(그날 기준이 바뀐 문항)·'인허가는 왜 참고로만…'·'데이터는 얼마나 자주…'가 빠졌고,
    'LTV와 DSR의 차이는?'은 JSON-LD 에서만 '…무엇인가요?'였다. 손으로 고치는 두 벌이라 한쪽만 고치면 갈린다.
    변이(실제로 확인): JSON-LD 에서 한 문항을 지우면, 화면 질문 하나의 글을 바꾸면 빨개진다."""
    s = _read('faq/index.html')
    ld = json.loads(re.search(r'<script type="application/ld\+json">\s*(\{.*?"FAQPage".*?\})\s*</script>', s, re.S).group(1))
    vis = re.findall(r'<details[^>]*>\s*<summary>([^<]+)</summary>', s)
    assert len(vis) >= 10, '화면 질문을 거의 못 읽었다 — 이 시험이 헛돈다'
    assert [q['name'] for q in ld['mainEntity']] == vis


def test_faq_light_thresholds_follow_the_move_in_band():
    """FAQ 의 신호등 문턱('70% 미만이면 적음, 70~130%는 보통, 130%를 넘으면 많음')이 정본 OCC_LO_PCT·OCC_HI_PCT·LIGHT 와 같다.
    변이(실제로 확인): sido_zones.OCC_HI_PCT 를 140 으로 바꾸면 빨개진다. 화면 본문(q7)만 '60% 미만이면 적음, 60~140%는 보통,
    140%를 넘으면 많음'으로 바꿔도 빨개진다(전수리뷰 P-4 — 예전엔 JSON-LD 사본만 대조했다)."""
    pat = re.compile(r'1년 적정물량의 (\d+)% 미만이면 (\S+), (\d+)~(\d+)%는 (\S+), (\d+)%를 넘으면 (\S+)이다')
    lo, hi = SZ.OCC_LO_PCT, SZ.OCC_HI_PCT
    want = (str(lo), SZ.LIGHT[-1][1], str(lo), str(hi), SZ.LIGHT[0][1], str(hi), SZ.LIGHT[1][1])
    for part, text in _faq_parts():
        got = [m.groups() for m in pat.finditer(text)]
        assert len(got) == 1, 'FAQ %s 에서 신호등 문턱 문장을 %d번 찾았다(정확히 한 번)' % (part, len(got))
        assert got[0] == want, (part, got[0], want)
