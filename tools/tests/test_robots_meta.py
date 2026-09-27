# -*- coding: utf-8 -*-
"""모든 페이지에 검색 로봇 메타 `max-image-preview:large` 가 정확히 하나 있다(홈 마케팅 검수 D2·DIST-4①, 2026-09-27).

구글 디스커버·이미지 검색이 큰 미리보기를 쓰는 조건이다. 2026-09-27 까지 robots 메타가 있는 페이지는 404(noindex)·
개인정보(index, follow) 두 장뿐이었다. 정본은 tools/robots_meta.py 이고, 생성기는 뼈대에 TAG 를 싣거나(ensure 로) 넣는다.

⚠️ 생성 페이지는 **생성기를 돌린 뒤** 기준이다 — 배치 게이트와 ci-tests 는 생성기 뒤에 이 시험을 돈다. /weekly/·/cycle/ 은
   뼈대가 배치 산출물이라 PR 로 고치지 않고 생성기가 첫 배치에서 한 줄을 넣는다(개발 트리에서 생성기 없이 돌리면 그 두 장이 빨갛다).

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - make_indicator_pages SHELL 에서 __ROBOTS__ 줄을 지우고 생성기를 다시 돌리면 → /moveins/·/jeonse-ratio/·/monthly/ 가 0개로 빨강
  - make_weekly_page.render 의 RM.ensure 줄을 지우면(뼈대에 아직 줄이 없는 상태에서 굽기) → /weekly/ 가 0개로 빨강
  - make_sido_pages 템플릿 dict 에서 'robots': RM.TAG 대신 '' 을 주면 → zone 20장이 0개로 빨강
  - about/index.html 에 robots 메타를 한 줄 더 적으면 → 2개로 빨강
  - robots_meta.CONTENT 를 'noindex' 로 바꾸면 → noindex 는 404 만 허용 시험이 빨강
  - 404.html 의 content 에서 noindex 를 빼면(합치다 잃으면) → 기존 뜻 유지 시험이 빨강
픽스처: 저장소의 실제 .html 전부(숨은 폴더·drafts·logs 제외). ensure() 단위 시험은 실제 뼈대 두 모양(줄마다 한 태그인
손 뼈대, 한 줄로 이어 쓴 통합 안내 페이지)과 기존 robots 메타 두 모양(noindex, index, follow)을 재현한다.
"""
import io
import os
import sys

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import robots_meta as RM  # noqa: E402

SKIP_DIRS = {'drafts', 'logs', 'node_modules'}


def html_files():
    out = []
    for d, dirs, files in os.walk(ROOT):
        dirs[:] = sorted(x for x in dirs if not x.startswith('.') and x not in SKIP_DIRS)
        out += [os.path.join(d, f) for f in sorted(files) if f.endswith('.html')]
    return out


def _rel(p):
    return os.path.relpath(p, ROOT).replace(os.sep, '/')


def test_walker_sees_every_kind_of_page():
    """파서 자기 확인 — 빈 목록이면 아래 시험이 헛돈다."""
    got = {_rel(p) for p in html_files()}
    for must in ('index.html', '404.html', 'about/index.html', 'weekly/index.html', 'monthly/index.html',
                 'cycle/index.html', 'zone/index.html', 'burini-test/index.html', 'burini-test/0/index.html'):
        assert must in got, '%s 를 찾지 못했다 — 걷는 범위가 깨졌다' % must
    assert len(got) >= 60


def test_every_page_has_exactly_one_robots_meta_with_large_preview():
    bad = []
    for p in html_files():
        s = io.open(p, encoding='utf-8').read()
        tags = RM.robots_metas(s)
        if len(tags) != 1:
            bad.append('%s: robots 메타 %d개' % (_rel(p), len(tags)))
            continue
        m = RM._ROBOTS.search(s)
        if not m or not RM.has_directive(m.group('c')):
            bad.append('%s: %s' % (_rel(p), tags[0]))
            continue
        head_end = s.lower().find('</head>')
        if not (0 <= m.start() < head_end):
            bad.append('%s: robots 메타가 <head> 밖에 있다' % _rel(p))
    assert not bad, ('max-image-preview:large 가 정확히 하나가 아닌 페이지(생성 페이지면 생성기를 먼저 돌릴 것):\n  '
                     + '\n  '.join(bad))


def test_noindex_stays_only_on_404_and_old_intent_is_kept():
    """robots 한 줄을 모든 페이지에 넣다가 noindex 가 퍼지면 사이트가 검색에서 빠진다. 404 의 noindex·개인정보의
    index, follow 는 합친 뒤에도 남아야 한다."""
    noindex = []
    for p in html_files():
        m = RM._ROBOTS.search(io.open(p, encoding='utf-8').read())
        if m and 'noindex' in m.group('c').lower():
            noindex.append(_rel(p))
    assert noindex == ['404.html'], 'noindex 가 404 밖으로 퍼졌거나 404 에서 빠졌다: %s' % noindex
    priv = RM._ROBOTS.search(io.open(os.path.join(ROOT, 'privacy', 'index.html'), encoding='utf-8').read())
    assert priv and 'index, follow' in priv.group('c')


HAND = ('<!DOCTYPE html>\n<html lang="ko">\n<head>\n<meta charset="UTF-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n<title>t</title>\n</head>')
STUB = ('<!doctype html><html lang="ko"><head><meta charset="utf-8">'
        '<meta name="viewport" content="width=device-width,initial-scale=1"><title>t</title></head>')


def test_ensure_inserts_once_on_its_own_line_and_is_idempotent():
    out = RM.ensure(HAND)
    assert '<meta name="viewport" content="width=device-width, initial-scale=1.0">\n%s\n<title>' % RM.TAG in out
    assert RM.ensure(out) == out
    out = RM.ensure(STUB)
    assert 'initial-scale=1">%s<title>' % RM.TAG in out and RM.ensure(out) == out
    crlf = RM.ensure(HAND.replace('\n', '\r\n'))
    assert '\r\n%s\r\n' % RM.TAG in crlf


def test_ensure_merges_into_an_existing_robots_meta():
    for old, want in (('noindex', 'noindex, max-image-preview:large'),
                      ('index, follow', 'index, follow, max-image-preview:large')):
        s = HAND.replace('<title>', '<meta name="robots" content="%s">\n<title>' % old)
        out = RM.ensure(s)
        assert len(RM.robots_metas(out)) == 1 and 'content="%s"' % want in out
        assert RM.ensure(out) == out


def test_ensure_refuses_two_robots_metas():
    s = HAND.replace('<title>', RM.TAG + '\n' + RM.TAG + '\n<title>')
    with pytest.raises(SystemExit):
        RM.ensure(s)
