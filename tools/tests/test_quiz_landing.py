# -*- coding: utf-8 -*-
"""퀴즈 랜딩 3종이 약속하는 점수별 레벨이 실제 결과와 같은지, 손 페이지가 본문 랜드마크를 갖는지 본다(전수리뷰 #70·#71).

① 레벨 표(#70). 랜딩의 '점수별 레벨' 표는 결과 화면·공유 문구가 읽는 정본을 손으로 옮긴 사본이다.
   부린이 테스트는 home-app.js 의 BLV(점수 0~10 → 이모지·이름), 투자자·재건축 테스트는 home-quiz.js 의
   grade 함수(if(s>=N)return{lv,g,emoji})가 정본이다. 2026-09-30 전수 리뷰 때 부린이 랜딩은 10·9·7점 이모지가
   BLV 와 달랐다(🐦‍🔥·🏰·🔑 ↔ 🦅·🏙️·🏠). 만점 🦅 는 투자자 테스트 아이콘과 같아서, 랜딩이 약속한 불사조와 다른
   그림을 받았다. 투자자 랜딩은 LV4·LV3 이름을 줄여 적었다.
② 랜드마크(#71). 09-18 접근성 2차가 '전 페이지'에 <main>·건너뛰기 링크를 넣었는데 퀴즈 랜딩 3종이 빠졌다.
   저장소 맨 위와 한 단계 아래의 모든 index.html(손 페이지와 생성 페이지 허브)이 <main id="main"> 하나와
   #main 건너뛰기 링크를 갖는지 본다. 404.html 도 대상이다(전수리뷰 P-11 — 예전엔 '아직 <main> 이 없다'며 뺐고, 본문
   랜드마크·건너뛰기 링크 없이 '공급 사이클 리포트는 아래에서'라는 낡은 안내가 홈 단추 위에 있었다).

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · burini-test/index.html 10점 행을 🐦‍🔥 로 되돌리면 test_burini_landing_levels_match_blv 가 실패한다.
  · home-app.js BLV[9].g 를 바꿔도 같은 시험이 실패한다.
  · investor-test/index.html LV4 행을 옛 줄임 이름('머릿속에선 이미 최소 다주택자')으로 되돌리면
    test_investor_redev_landing_levels_match_grade 가 실패한다.
  · burini-test/index.html 에서 <main id="main"> 을 빼거나 redev-test 건너뛰기 링크의 href 를 바꾸면
    test_pages_have_main_landmark_and_skip_link 가 실패한다. 404.html 을 옛 <div class="wrap"> 본문으로 되돌려도 실패한다.
픽스처 없이 저장소의 실제 파일을 읽는다. 날짜·데이터와 무관하다.
"""
import glob
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402  (홈 스크립트는 이 입구로만 읽는다)

VS = '\ufe0f'


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _unesc(s):
    """JS 의 \\u{1F985} 표기를 글자로 푼다. 이모지 비교에서는 변형 선택자(FE0F)를 뗀다."""
    return re.sub(r'\\u\{([0-9A-Fa-f]+)\}', lambda m: chr(int(m.group(1), 16)), s).replace(VS, '')


def _blv():
    src = HS.home_source()
    m = re.search(r'const BLV=\[(.*?)\n\];', src, re.S)
    assert m, 'home-app.js 에서 BLV 를 못 찾았다'
    rows = re.findall(r"\{lv:'(LV\d+)',emoji:'([^']+)',g:'([^']+)'", m.group(1))
    return [(_unesc(e), g) for _lv, e, g in rows]


def _landing_rows(rel):
    """'점수별 레벨' 표의 (점수 칸, 내용 칸) 목록."""
    s = _read(rel)
    i = s.find('<h2>점수별 레벨</h2>')
    assert i >= 0, '%s: 점수별 레벨 표를 못 찾았다 — 구조가 바뀌었으면 이 시험도 고칠 것' % rel
    table = s[i:s.index('</table>', i)]
    return re.findall(r'<tr><td>([\d~]+)</td><td>(.*?)</td></tr>', table)


def _scores(cell):
    a, _, b = cell.partition('~')
    return list(range(int(a), int(b or a) + 1))


def test_burini_landing_levels_match_blv():
    blv = _blv()
    assert len(blv) >= 2, 'BLV 를 제대로 못 읽었다'
    rows = _landing_rows('burini-test/index.html')
    covered = []
    for cell, body in rows:
        pts = _scores(cell)
        covered += pts
        parts = [p.split(' — ')[0].strip() for p in body.split(' · ')]
        assert len(parts) == len(pts), '%s점 행: 점수마다 이모지·이름을 하나씩 적는다 — %r' % (cell, body)
        for n, part in zip(pts, parts):
            emoji, _, name = part.partition(' ')
            want = blv[n]
            assert (emoji.replace(VS, ''), name) == want, (
                '%d점: 랜딩은 %s %s, 결과(BLV)는 %s %s' % (n, emoji, name, want[0], want[1]))
    assert sorted(covered) == list(range(len(blv))), '랜딩 표가 0~%d점을 빠짐없이 한 번씩 덮지 않는다: %s' % (
        len(blv) - 1, sorted(covered))


def _grades(key):
    """정본 읽기는 home_src.quiz_grades 하나다(공유 카드 도구도 같은 함수를 읽는다 — 전수리뷰 P-14)."""
    # 랜딩 표는 높은 점수부터 적으므로 내림차순으로 돌려준다
    return [(lo, lv, g, e.replace(VS, '')) for lo, lv, g, e in reversed(HS.quiz_grades(key))]


def test_investor_redev_landing_levels_match_grade():
    for rel, key in (('investor-test/index.html', 'investor'), ('redev-test/index.html', 'calc')):
        grades = _grades(key)
        rows = _landing_rows(rel)
        assert len(rows) == len(grades), '%s: 랜딩 표 %d줄, 결과 등급 %d개' % (rel, len(rows), len(grades))
        for (cell, body), (lo, lv, g, e) in zip(rows, grades):
            assert _scores(cell)[0] == lo, '%s %s: 점수 하한이 결과(%d점 이상)와 다르다' % (rel, cell, lo)
            m = re.match(r'(\S+) (LV\d+) — (.+)$', body)
            assert m, '%s: 행 모양이 바뀌었다 — %r' % (rel, body)
            got = (m.group(1).replace(VS, ''), m.group(2), m.group(3))
            assert got == (e, lv, g), '%s %s점: 랜딩은 %s, 결과는 %s' % (rel, cell, got, (e, lv, g))


def _pages():
    out = ['index.html', '404.html']
    for p in sorted(glob.glob(os.path.join(ROOT, '*', 'index.html'))):
        out.append(os.path.relpath(p, ROOT).replace(os.sep, '/'))
    return out


def test_pages_have_main_landmark_and_skip_link():
    pages = _pages()
    for must in ('burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html',
                 'about/index.html', 'faq/index.html', 'privacy/index.html', 'cycle/index.html', '404.html'):
        assert must in pages, '%s 가 대상에 없다' % must
    bad = []
    for rel in pages:
        s = _read(rel)
        if s.count('<main id="main"') != 1 or '</main>' not in s or 'class="skip" href="#main"' not in s:
            bad.append(rel)
    assert not bad, '<main id="main"> 하나와 #main 건너뛰기 링크가 없는 페이지: %s' % bad


LANDINGS = ('burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html')


def _pool():
    """홈 퀴즈 문항 풀 — 질문(태그 뗀 글)과 보기 목록. 읽기 식은 test_quiz_regulation_items 의 ITEM 하나를 쓴다."""
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    import test_quiz_regulation_items as QRI
    return [(re.sub(r'<[^>]+>', '', x['q']).replace("\\'", "'"), x['opts']) for x in QRI._items()]


def _examples(rel):
    """'이런 걸 물어본다' 예시 [(질문, 보기 줄)] — 보기 줄은 ①② 로 보기를 적은 것만 보기 목록, 아니면 None."""
    s = _read(rel)
    out = []
    for qt, qo in re.findall(r'<div class="qt">Q\. (.*?)</div>\s*<div class="qo">(.*?)</div>', s, re.S):
        opts = None
        if '①' in qo:
            body = qo.split(' — ')[0].replace('&nbsp;', ' ')
            opts = [o.strip() for o in re.split(r'[①②③④]', body) if o.strip()]
        out.append((re.sub(r'<[^>]+>', '', qt).strip(), opts))
    return out


def test_landing_examples_with_options_are_real_quiz_items():
    """랜딩이 '①②' 보기까지 내건 예시는 홈 퀴즈 풀에 같은 질문·같은 보기 문항이 있어야 한다(전수리뷰 P-1).

    2026-09-13 대표 판단으로 투자자 규제 문항을 '호재일까 악재일까?'에서 '시장에 남기는 효과로 가까운 것은?'으로
    바꿨는데, 투자자 랜딩만 옛 질문·보기('① 공급 줄여 호재 ② 거래 막혀 악재 — 정답과 해설은 테스트에서')를 계속
    내걸었다. 그 문항은 풀에 없어 '정답과 해설은 테스트에서'라는 약속이 어느 회차에서도 지켜지지 않았다.
    보기 없이 주제만 소개하는 예시(요약문)는 풀 문구와 달라도 된다 — 보기를 적은 예시만 대조한다.
    변이(실제로 확인): investor-test/index.html 의 첫 예시를 옛 질문·보기로 되돌리면 빨개진다(풀에 없음, 호재·악재 이분법
    둘 다). 픽스처 없이 저장소의 실제 랜딩 3종과 home-quiz.js 문항 풀을 읽는다.
    """
    pool = _pool()
    assert pool, '퀴즈 풀을 못 읽었다'
    checked = 0
    bad = []
    for rel in LANDINGS:
        ex = _examples(rel)
        assert ex, '%s: 예시를 하나도 못 읽었다 — 구조가 바뀌었으면 이 시험도 고칠 것' % rel
        for q, opts in ex:
            if opts is None:
                continue
            checked += 1
            if '호재' in ' '.join(opts) and '악재' in ' '.join(opts):
                bad.append('%s: 호재·악재 이분법 예시 — %s' % (rel, q))
            if not any(pq == q and po == opts for pq, po in pool):
                bad.append('%s: 풀에 같은 질문·보기 문항이 없다 — %s %s' % (rel, q, opts))
    assert checked >= len(LANDINGS), '보기를 내건 예시가 %d개뿐이다 — 대조가 헛돈다' % checked
    assert not bad, bad


def _px(rule, prop):
    m = re.search(r'(?:^|[;{\s])%s:(\d+)px' % prop, rule)
    return int(m.group(1)) if m else None


def test_landing_toast_sits_above_the_bottom_nav():
    """퀴즈 랜딩의 안내 토스트(#toast — '링크가 복사됐어요!', '공유 링크: …')가 하단 탭바 위에 뜬다(전수리뷰 P-12).

    재현한 상태(2026-10-18): #toast 는 bottom:34px·z-index:60, 탭바는 높이 62px·z-index:100 이라 토스트 아래 28px 가 늘 탭바 뒤였다.
    375px 에서 두 줄로 접히면 둘째 줄이, 768~1023px 에서는 한 줄 전체가 탭바에 가려 읽히지 않았다(카카오 SDK·Web Share 가 없는
    폴백 경로). 홈 .qtoast 는 bottom:80px 라 같은 문제가 없다.
    변이(실제로 확인): 한 랜딩의 #toast 를 bottom:34px 로 되돌리면 빨개진다.
    픽스처 없이 저장소의 실제 랜딩 3종의 <style> 규칙을 읽는다.
    """
    bad = []
    for rel in LANDINGS:
        s = _read(rel)
        toast = re.search(r'#toast\{([^}]*)\}', s)
        nav = re.search(r'\.bottomnav\{([^}]*)\}', s)
        assert toast and nav, '%s: #toast 나 .bottomnav 규칙을 못 찾았다' % rel
        b, h = _px(toast.group(1), 'bottom'), _px(nav.group(1), 'height')
        assert b is not None and h, '%s: bottom·height 를 못 읽었다' % rel
        if b <= h:
            bad.append('%s: 토스트 bottom %dpx ≤ 탭바 높이 %dpx' % (rel, b, h))
    assert not bad, bad
