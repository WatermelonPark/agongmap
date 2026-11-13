# -*- coding: utf-8 -*-
"""퀴즈 3종 제거(2026-11-14 대표 결정 '다 없애자')를 고정한다.

근거(11/2~11/8 한 주): /burini-test/ 조회 11회, 완료 7회가 모두 사람이 직접 보낸 초대 링크에서 나왔고 검색·홈에서 들어와
푼 경우는 0회였다. /redev-test/·/investor-test/ 는 주 1회 안팎이었다. 그래서 퀴즈 화면·생성기·진입점을 모두 걷었다.

고정하는 것:
  ① 세 퀴즈 주소(/burini-test/ 등)는 빈 페이지가 아니라 홈(/)으로 넘기는 최소 페이지다 — meta refresh 0초 → '/',
     canonical 은 정식 도메인 홈, robots 는 noindex. 점수별 하위 페이지(/0/~/10/)는 남지 않는다. 바깥에 퍼진 공유 링크·
     검색 색인이 404 대신 홈에 닿고, 검색 엔진은 이 주소를 색인에서 내린다.
  ② 홈(index.html·home-app.js·home-stats.js — home_src 로 읽는다)·sitemap.xml·llms.txt·llms-full.txt·feed.xml 에
     퀴즈 주소 링크가 0개다. 사이트의 다른 공개 HTML 에도 그 주소로 가는 href 가 없다(리다이렉트 페이지 자신은 뺀다).
  ③ 서비스워커 사전 캐시에 퀴즈 화면 파일(home-quiz.js)이 없고, 홈의 분할 파일 목록(home_src.PARTS)에도 없다.

무엇을 바꾸면 빨개지나(각각 실제로 깨뜨려 확인):
  - burini-test/index.html 의 meta refresh 를 지우거나 url 을 '/weekly/' 로 바꾸면, robots 를 'max-image-preview:large'
    로 되돌리면, canonical 을 '/burini-test/' 로 두면 → test_quiz_urls_redirect_home.
  - redev-test/0/index.html 같은 점수 페이지를 다시 두면 → test_quiz_urls_redirect_home.
  - 홈 푸터에 <a href="/burini-test/">부린이 테스트</a> 를 되살리면, sitemap.xml 에 /investor-test/ <url> 을 되살리면,
    llms.txt 에 /redev-test/ 링크를 적으면 → test_no_quiz_links_on_home_sitemap_llms.
  - faq/index.html 에 /burini-test/ 링크를 되살리면 → test_no_page_links_to_a_quiz.
  - sw.js PRECACHE 에 '/home-quiz.js?v=' + VERSION 을 되살리거나 home_src.PARTS 에 home-quiz.js 를 넣으면
    → test_service_worker_does_not_precache_the_quiz.
픽스처: 저장소의 실제 파일 그대로(데이터·날짜와 무관 — 배치가 데이터를 갈아도 같은 답).
"""
import io
import os
import re
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구)

SLUGS = ('burini-test', 'investor-test', 'redev-test')
SITE = 'https://' + io.open(os.path.join(ROOT, 'CNAME'), encoding='utf-8').read().strip()
QUIZ_HREF = re.compile(r'(?:href|src|content|<loc>)\s*=?\s*["\']?(?:https?://[^/"\'<>\s]+)?/(%s)/' % '|'.join(SLUGS))
QUIZ_PATH = re.compile(r'/(%s)/' % '|'.join(SLUGS))


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def test_quiz_urls_redirect_home():
    for slug in SLUGS:
        d = os.path.join(ROOT, slug)
        left = sorted(os.path.relpath(os.path.join(a, f), ROOT).replace(os.sep, '/')
                      for a, _, fs in os.walk(d) for f in fs)
        assert left == ['%s/index.html' % slug], '%s 아래에 리다이렉트 페이지 말고 다른 파일이 있다: %s' % (slug, left)
        html = _read('%s/index.html' % slug)
        assert re.search(r'<meta\s+http-equiv="refresh"\s+content="0;\s*url=/"\s*/?>', html), '%s 가 홈으로 넘기지 않는다' % slug
        canon = re.findall(r'<link\s+rel="canonical"\s+href="([^"]+)"', html)
        assert canon == [SITE + '/'], '%s canonical %s (정식 도메인 홈이어야 한다)' % (slug, canon)
        robots = re.findall(r'<meta\s+name="robots"\s+content="([^"]+)"', html)
        assert len(robots) == 1 and 'noindex' in [x.strip() for x in robots[0].split(',')], '%s robots %s' % (slug, robots)
        assert '<script' not in html and slug not in html, '%s 리다이렉트 페이지에 퀴즈 흔적이 남았다' % slug


def test_no_quiz_links_on_home_sitemap_llms():
    home = HS.home_source()
    HS.require(home, 'function applyHash', 'id="view-home"', what='홈 소스')
    bad = {'홈': QUIZ_PATH.findall(home)}
    for rel in ('sitemap.xml', 'llms.txt', 'llms-full.txt', 'feed.xml'):
        body = _read(rel)
        assert len(body) > 200, '%s 를 거의 못 읽었다' % rel
        bad[rel] = QUIZ_PATH.findall(body)
    assert '<loc>%s/</loc>' % SITE in _read('sitemap.xml'), 'sitemap 형식이 바뀌어 이 검사가 헛돈다'
    assert not any(bad.values()), '퀴즈 링크가 남았다: %s' % {k: v for k, v in bad.items() if v}
    # 홈 퀴즈 화면·구역도 남지 않는다
    for needle in ('id="view-test"', 'id="quiz-sample"', "to:'quiz_", 'shareTest(', 'startQuiz('):
        assert needle not in home, '홈에 퀴즈 화면 조각 %r 이 남았다' % needle


def _public_html():
    skip = {'docs', 'drafts', 'logs', 'tools', 'node_modules', '.git', '.github', '.claude'} | set(SLUGS)
    for top, dirs, files in os.walk(ROOT):
        rel = os.path.relpath(top, ROOT).replace(os.sep, '/')
        if rel.split('/')[0] in skip:
            dirs[:] = []
            continue
        for f in files:
            if f.endswith('.html'):
                yield (rel + '/' + f).lstrip('./') if rel != '.' else f


def test_no_page_links_to_a_quiz():
    seen, bad = 0, []
    for rel in _public_html():
        seen += 1
        hits = QUIZ_HREF.findall(_read(rel))
        if hits:
            bad.append('%s → %s' % (rel, sorted(set(hits))))
    assert seen > 50, '공개 HTML 을 거의 못 찾았다(%d)' % seen
    assert not bad, '퀴즈 주소로 가는 링크가 남았다: %s' % bad


def test_service_worker_does_not_precache_the_quiz():
    sw = _read('sw.js')
    pre = re.search(r'const PRECACHE = \[(.*?)\n\];', sw, re.S)
    assert pre and "'/home-app.js'" in pre.group(1), 'sw.js PRECACHE 를 못 읽었다'
    code = re.sub(r'//[^\n]*', '', pre.group(1))
    assert 'home-quiz.js' not in code, 'sw.js 사전 캐시에 퀴즈 화면 파일이 남았다'
    assert not [p for p in HS.PARTS if 'quiz' in p], 'home_src.PARTS 에 퀴즈 파일이 남았다: %s' % (HS.PARTS,)
    assert not os.path.exists(os.path.join(ROOT, 'home-quiz.js'))
