# -*- coding: utf-8 -*-
"""퀴즈 랜딩 3종이 약속하는 점수별 레벨이 실제 결과와 같은지, 손 페이지가 본문 랜드마크를 갖는지 본다(전수리뷰 #70·#71).

① 레벨 표(#70). 랜딩의 '점수별 레벨' 표는 결과 화면·공유 문구가 읽는 정본을 손으로 옮긴 사본이다.
   부린이 테스트는 home-app.js 의 BLV(점수 0~10 → 이모지·이름), 투자자·재건축 테스트는 home-quiz.js 의
   grade 함수(if(s>=N)return{lv,g,emoji})가 정본이다. 2026-09-30 전수 리뷰 때 부린이 랜딩은 10·9·7점 이모지가
   BLV 와 달랐다(🐦‍🔥·🏰·🔑 ↔ 🦅·🏙️·🏠). 만점 🦅 는 투자자 테스트 아이콘과 같아서, 랜딩이 약속한 불사조와 다른
   그림을 받았다. 투자자 랜딩은 LV4·LV3 이름을 줄여 적었다.
② 랜드마크(#71). 09-18 접근성 2차가 '전 페이지'에 <main>·건너뛰기 링크를 넣었는데 퀴즈 랜딩 3종이 빠졌다.
   저장소 맨 위와 한 단계 아래의 모든 index.html(손 페이지와 생성 페이지 허브)이 <main id="main"> 하나와
   #main 건너뛰기 링크를 갖는지 본다. 404.html 은 index.html 이 아니라 대상 밖이다(아직 <main> 이 없다).

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · burini-test/index.html 10점 행을 🐦‍🔥 로 되돌리면 test_burini_landing_levels_match_blv 가 실패한다.
  · home-app.js BLV[9].g 를 바꿔도 같은 시험이 실패한다.
  · investor-test/index.html LV4 행을 옛 줄임 이름('머릿속에선 이미 최소 다주택자')으로 되돌리면
    test_investor_redev_landing_levels_match_grade 가 실패한다.
  · burini-test/index.html 에서 <main id="main"> 을 빼거나 redev-test 건너뛰기 링크의 href 를 바꾸면
    test_pages_have_main_landmark_and_skip_link 가 실패한다.
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
    src = HS.home_source()
    i = src.find('\n  %s:{' % key)
    assert i >= 0, 'QUIZSETS 에서 %s 세트를 못 찾았다' % key
    j = src.index('grade:s=>{', i)
    body = src[j:src.index('\n    }', j)]
    out = []
    for lo, lv, g, e in re.findall(r"(?:if\(s>=(\d+)\))?return\{lv:'(LV\d+)',g:'([^']+)',d:'[^']*',emoji:'([^']+)'\}",
                                   body):
        out.append((int(lo) if lo else 0, lv, g, e.replace(VS, '')))
    assert len(out) >= 2, '%s grade 함수를 못 읽었다' % key
    return out


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
    out = ['index.html']
    for p in sorted(glob.glob(os.path.join(ROOT, '*', 'index.html'))):
        out.append(os.path.relpath(p, ROOT).replace(os.sep, '/'))
    return out


def test_pages_have_main_landmark_and_skip_link():
    pages = _pages()
    for must in ('burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html',
                 'about/index.html', 'faq/index.html', 'privacy/index.html', 'cycle/index.html'):
        assert must in pages, '%s 가 대상에 없다' % must
    bad = []
    for rel in pages:
        s = _read(rel)
        if s.count('<main id="main"') != 1 or '</main>' not in s or 'class="skip" href="#main"' not in s:
            bad.append(rel)
    assert not bad, '<main id="main"> 하나와 #main 건너뛰기 링크가 없는 페이지: %s' % bad
