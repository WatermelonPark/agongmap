# -*- coding: utf-8 -*-
"""같은 개념은 한 이름 — 기준 물량은 '적정물량', 판정 방향은 '부족·여유'(등급 정본 sido_zones.GRADE_LABS 의 '공급 여유')다
(2026-10-06 대표 결정, CLAUDE.md '화면 설계 원칙'). 옛 이름('필요량'·'수요 기준선'·'적정수요')과 정본에서 벗어난 말('과잉'·'적정선'·
'적정 물량'·'필요한 집')이 화면에 다시 들어오지 않게 본다(전수리뷰 Z1-8·X1-9).

재현한 실제 상태(2026-10-18): /jeonse-ratio/ 더 보기 '16개 시도를 부족·과잉 등급으로'(같은 생성기의 /moveins/ 는 '부족·여유를 등급으로'),
/moveins/ 해설 '공급이 적정선의 70%를 밑돌면'(같은 문단 앞 두 번은 '적정물량'), 시도 리포트 공유 문구 '…에 필요한 집과 앞으로 들어올 집',
퀴즈 랜딩 3종 '16개 시도의 부족·과잉을 등급으로', FAQ 검색용 JSON-LD '적정 물량과 비교해 공급 과잉·부족'(화면 답은 '적정물량과 견줘'),
소개 '적정 물량과 견줘보고'. 36-2 용어 통일 뒤에도 막는 시험이 없어 남아 있었다.

범위: 이 시험이 보는 것은 손 페이지(소개·FAQ·퀴즈 랜딩 3종)와 시도 리포트·지표 두 쪽·/llms.txt 의 생성 결과, 그 생성기들과 지역 카드 도구
(make_zone_cards — 그림 글자는 test_zone_cards 가 본다)의 문자열(독스트링·주석 제외 — 옛 이름의 이력을 적는 자리다). 홈(index.html — 표 보기 범례는 대표 결정 2026-10-18 D4 로 고쳤다, 변이: 옛 '하락 · 공급 과잉' 범례로 되돌리면 빨개진다)도 본다.
/weekly/ '더 둘러보기'(생성기가 맡게 바꾸는 별건)는 그 수정과 함께 이 목록에 더한다.
/llms.txt 입주물량 줄도 '적정물량과 견준 부족·과잉'이었다(검토 보강 — 입주물량은 판정이 아니라 신호등 낱말 적음·보통·많음으로 쓴다).
변이(실제로 확인): make_llms_txt 의 입주물량 설명을 옛 '부족·과잉'으로 되돌리면 생성기 단정이 빨개진다. make_indicator_pages 의 /jeonse-ratio/ 링크를 '부족·과잉 등급으로'로 되돌리면 생성기 단정이, faq JSON-LD 를 옛 '적정 물량과
비교해 공급 과잉·부족'으로 되돌리면 페이지 단정이 빨개진다.
픽스처: 배치 게이트처럼 split_data·생성기를 먼저 돌린 저장소 산출물과 손 페이지, 생성기 소스.
"""
import ast
import glob
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
FORBIDDEN = ('과잉', '적정선', '적정 물량', '적정수요', '필요한 집', '필요량', '수요 기준선')
HAND = ('index.html', 'about/index.html', 'faq/index.html', 'burini-test/index.html', 'investor-test/index.html', 'redev-test/index.html')
GENERATED = ('jeonse-ratio/index.html', 'moveins/index.html', 'llms.txt')
GENERATORS = ('tools/make_indicator_pages.py', 'tools/make_sido_pages.py', 'tools/make_zone_cards.py', 'tools/make_llms_txt.py')


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _pages():
    zone = sorted(os.path.relpath(p, ROOT) for p in glob.glob(os.path.join(ROOT, 'zone', '*', 'index.html')))
    return list(HAND) + list(GENERATED) + zone


def _hits(text):
    return [t for t in FORBIDDEN if t in text]


def test_pages_use_the_canon_terms():
    pages = _pages()
    assert len(pages) > len(HAND) + len(GENERATED) + 10, '시도 리포트를 거의 못 찾았다 — 생성기를 먼저 돌렸는지 확인'
    bad = []
    for rel in pages:
        s = re.sub(r'<!--.*?-->', '', _read(rel), flags=re.S)   # 주석은 사람이 읽지 않는다 — JSON-LD·스크립트 문구는 본다
        for t in _hits(s):
            i = s.index(t)
            bad.append('%s: %s …%s…' % (rel, t, s[max(0, i - 30):i + 20].replace('\n', ' ')))
    assert not bad, '정본 용어(적정물량·부족·여유)를 벗어난 말:\n' + '\n'.join(bad)


def _literals(rel):
    tree = ast.parse(_read(rel))
    docs = {id(n.body[0].value) for n in ast.walk(tree)
            if isinstance(n, (ast.Module, ast.FunctionDef, ast.ClassDef)) and n.body and isinstance(n.body[0], ast.Expr)}
    return [n.value for n in ast.walk(tree)
            if isinstance(n, ast.Constant) and isinstance(n.value, str) and id(n) not in docs]


def test_generators_write_the_canon_terms():
    bad = []
    for rel in GENERATORS:
        lits = _literals(rel)
        assert lits, rel
        bad += ['%s: %s' % (rel, t) for v in lits for t in _hits(v)]
    assert not bad, '생성기 문자열에 정본 밖 용어가 있다: %s' % bad
