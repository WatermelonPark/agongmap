# -*- coding: utf-8 -*-
"""원고 검사기 — `content/` 의 모든 원고를 훑어 어긋난 곳을 **파일과 줄 번호로** 알려 준다(백로그 50).

왜 따로 있나. 생성기(make_content_pages)는 깨진 글을 건너뛰고 나머지를 굽는다(배치를 세우지 않으려고).
그래서 작성 세션에게는 '무엇이 왜 걸렸는지'를 한 번에 보여 주는 쪽이 필요하다. 이 검사기는 고치는 사람을
위한 것이라 **모든 문제를 모아** 보여 주고, 하나라도 있으면 종료 코드 1 로 끝난다.

사용:
    python tools/content_check.py                 전부 검사
    python tools/content_check.py content/gtx     그 폴더만
"""
import io
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import content_md as CM        # noqa: E402
import content_tables as CT    # noqa: E402

PLACEHOLDER = CT.PH      # 정규식은 content_tables 가 정본이다 — 종류가 늘면 한 곳만 고친다


def _line_of(text, pos):
    return text.count('\n', 0, pos) + 1


def _front_line(text, key):
    """프런트매터에서 그 키가 적힌 줄. 없으면 1(파일 첫 줄)."""
    m = re.search(r'^%s\s*:' % re.escape(key), text, re.M)
    return _line_of(text, m.start()) if m else 1


def _probe(data, m):
    """자리표 하나를 실제로 만들어 본다 — 종류마다 맞는 함수로. 오류는 그대로 올린다.

    생성기가 쓰는 함수를 그대로 부른다. 검사기가 따로 흉내내면 '검사는 통과했는데 생성기에서 걸리는'
    원고가 생긴다.
    """
    parts = [p.strip() for p in m.group(2).split(':')]
    return {'v': CT.value, 'table': CT.table, 'chart': CT.chart}[m.group(1)](data, parts[0], parts[1:])


def check_post(path, data, root=ROOT):
    """한 편 → [(줄, 문제)]"""
    rel = os.path.relpath(path, root).replace(os.sep, '/')
    text = io.open(path, encoding='utf-8').read()
    out = []
    try:
        meta, body = CM.read(path)
    except CM.ContentError as e:
        msg = str(e).split(': ', 1)[-1]
        key = next((k for k in CM.REQUIRED + ('faq', 'sources', 'region') if k in msg), None)
        return [(_front_line(text, key) if key else 1, msg)]
    # 본문은 프런트매터 뒤에서 시작한다 — 줄 번호를 파일 기준으로 되돌린다.
    offset = text.count('\n', 0, text.index(body)) if body and body in text else 0
    for m in PLACEHOLDER.finditer(body):
        try:
            _probe(data, m)
        except CT.TableError as e:
            out.append((offset + _line_of(body, m.start()), '%s — %s' % (m.group(0), e)))
    # 요약·FAQ 는 생성기와 **같은 함수**(fill_inline)로 본다. 한 줄 글에 못 들어가는 종류(표·그림)까지
    # 같은 눈으로 걸러야, 검사를 통과한 원고가 생성기에서 건너뛰어지는 일이 없다.
    for key in ('summary', 'title'):
        try:
            CT.fill_inline(meta.get(key) or '', data)
        except CT.TableError as e:
            out.append((_front_line(text, key), '%s: %s' % (key, e)))
    for i, f in enumerate(meta.get('faq') or []):
        try:
            CT.fill_inline((f.get('q') or '') + ' ' + (f.get('a') or ''), data)
        except CT.TableError as e:
            out.append((_front_line(text, 'faq'), 'faq %d번: %s' % (i + 1, e)))
    return [(ln, '%s' % why) for ln, why in out], rel


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    only = argv[0].replace('\\', '/').rstrip('/').split('/')[-1] if argv else None
    data = CT.load()
    posts = CM.posts(ROOT, section=only if only in CM.SECTIONS else None)
    if not posts:
        print('검사할 원고가 없다')
        return 0
    bad = 0
    for sec, slug, path in posts:
        problems, rel = check_post(path, data)
        if not problems:
            print('  OK   %s' % rel)
            continue
        bad += 1
        for ln, why in sorted(problems):
            print('  ✗    %s:%d  %s' % (rel, ln, why))
    print('\n원고 %d편 중 %d편에 고칠 곳이 있다.' % (len(posts), bad))
    if bad:
        print('쓸 수 있는 자리표는 content/README.md 에 있다.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
