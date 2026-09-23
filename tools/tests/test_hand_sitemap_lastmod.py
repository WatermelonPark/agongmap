# -*- coding: utf-8 -*-
"""손으로 관리하는 페이지의 sitemap lastmod 가 파일의 마지막 커밋을 따라가는지 본다(백로그 29).

/faq/ 는 08-06 모델 개편으로 본문이 바뀌었는데 lastmod 가 07-16 에 멈춰 있었고, /privacy/ 는 lastmod
자체가 없었다. 생성기가 없는 페이지라 아무도 고치지 않았다. make_indicator_pages 가 배치마다
hand_lastmods() → bump_sitemap() 으로 따라가게 했다.

무엇을 깨뜨리면 빨개지나(모두 실제로 확인):
  · bump_sitemap 의 '앞으로만' 비교(`m.group(1) < lm`)를 지우면 → 날짜가 뒤로 가는 단정이 실패
  · lastmod 없는 항목에 넣는 분기를 지우면 → /privacy/ 단정이 실패
  · hand_lastmods 의 얕은 경계 커밋 제외를 지우면 → 얕은 클론 단정이 실패
픽스처: 실제 sitemap.xml 의 두 모양(여러 줄 항목, 한 줄로 적힌 /privacy/ 항목)과, 파일을 마지막으로
바꾼 커밋이 얕은 클론 창 밖에 있는 배치 커밋 잡(fetch-depth 200)의 상태를 임시 git 저장소로 재현한다.
"""
import io
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import make_indicator_pages as I  # noqa: E402

SITE = I.SITE
SITEMAP = ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset>\n'
           '  <url>\n    <loc>%s/faq/</loc>\n    <lastmod>2026-07-16</lastmod>\n  </url>\n'
           '  <url><loc>%s/privacy/</loc><changefreq>yearly</changefreq></url>\n'
           '</urlset>\n') % (SITE, SITE)


def test_bump_moves_forward_only_and_fills_missing(tmp_path):
    io.open(str(tmp_path / 'sitemap.xml'), 'w', encoding='utf-8').write(SITEMAP)
    I.bump_sitemap([('/faq/', '2026-09-18'), ('/privacy/', '2026-09-18')], root=str(tmp_path))
    x = io.open(str(tmp_path / 'sitemap.xml'), encoding='utf-8').read()
    assert '<loc>%s/faq/</loc>\n    <lastmod>2026-09-18</lastmod>' % SITE in x
    assert '<loc>%s/privacy/</loc><lastmod>2026-09-18</lastmod>' % SITE in x
    I.bump_sitemap([('/faq/', '2026-08-01')], root=str(tmp_path))
    x = io.open(str(tmp_path / 'sitemap.xml'), encoding='utf-8').read()
    assert '<lastmod>2026-09-18</lastmod>' in x and '2026-08-01' not in x, '날짜가 뒤로 갔다'


def _git(cwd, *a):
    env = dict(os.environ, GIT_AUTHOR_NAME='t', GIT_AUTHOR_EMAIL='t@t', GIT_COMMITTER_NAME='t',
               GIT_COMMITTER_EMAIL='t@t')
    subprocess.run(['git'] + list(a), cwd=cwd, check=True, capture_output=True, env=env)


def test_shallow_boundary_commit_is_not_trusted(tmp_path):
    src = tmp_path / 'src'
    src.mkdir()
    _git(str(src), 'init', '-q')
    (src / 'faq').mkdir()
    (src / 'faq' / 'index.html').write_text('faq', encoding='utf-8')
    _git(str(src), 'add', '.')
    _git(str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'faq', '--date', '2026-07-16T00:00:00')
    (src / 'other.txt').write_text('x', encoding='utf-8')
    _git(str(src), 'add', '.')
    _git(str(src), '-c', 'commit.gpgsign=false', 'commit', '-q', '-m', 'other')
    full = dict(I.hand_lastmods(str(src)))
    assert '/faq/' in full, '전체 이력이면 마지막 커밋 날짜를 써야 한다'
    shallow = tmp_path / 'shallow'
    _git(str(tmp_path), 'clone', '-q', '--depth', '1', 'file://' + str(src), str(shallow))
    got = dict(I.hand_lastmods(str(shallow)))
    assert '/faq/' not in got, '얕은 클론의 경계 커밋 날짜를 faq 의 수정일로 믿었다: %s' % got
