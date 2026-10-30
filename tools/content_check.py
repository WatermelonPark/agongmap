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
    out, waits = [], []
    try:
        meta, body = CM.read(path)
    except CM.ContentError as e:
        msg = str(e).split(': ', 1)[-1]
        key = next((k for k in CM.REQUIRED + ('faq', 'sources', 'region') if k in msg), None)
        return ([(_front_line(text, key) if key else 1, msg)], [], rel)
    # 본문은 프런트매터 뒤에서 시작한다 — 줄 번호를 파일 기준으로 되돌린다.
    offset = text.count('\n', 0, text.index(body)) if body and body in text else 0
    for m in PLACEHOLDER.finditer(body):
        try:
            _probe(data, m)
        except CT.PendingCity as e:
            waits.append((offset + _line_of(body, m.start()), '%s — %s' % (m.group(0), e)))
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
    return [(ln, '%s' % why) for ln, why in out], waits, rel


# 사이트 정본 낱말(CLAUDE.md '같은 개념은 한 이름, 물량은 한 단위' — 적정물량·세대). 원고 문장은 작성 세션의 몫이라
# 막지 않고 알림만 한다(2026-10-30 디자인 리뷰 — 콘텐츠 글에 '적정 입주량'·'적정 대비'·'2,056가구'가 섞였다).
TERM_NOTES = (
    (re.compile(r'적정\s+입주량'), "'적정 입주량' → '적정물량'"),
    (re.compile(r'적정\s+대비'), "'적정 대비' → '적정물량 대비'"),
    (re.compile(r'\d[\d,]*\s*가구'), "물량 단위 '가구' → '세대'"),
)


def term_notes(text):
    """원고 글 → [(줄, 알림)]. 고칠 곳(종료 코드)에 세지 않는다."""
    out = []
    for pat, why in TERM_NOTES:
        for m in pat.finditer(text):
            out.append((_line_of(text, m.start()), '%s (%s)' % (why, m.group(0))))
    return out


# 글 배치 알림(2026-10-30 디자인 리뷰 3차) — 원고 구조는 작성 세션의 몫이라 고칠 곳에 세지 않고 알림만 한다.
OFF_TOPIC_CITY_CHART = ('gtx', 'danji')   # 도시 편은 도시 입주가 곧 주제라 앞에 와도 된다
METHOD_HEADS = ('고른 기준', '산식', '방법', '계산 방법', '이 글의 기준')
DUP_LIMIT = 0.5             # 결론 상자(summary)와 첫 문단 글자 2-gram 겹침이 이보다 크면 같은 말 두 번


def _bigrams(t):
    t = re.sub(r'\s+|\{\{[^}]*\}\}|[*`#>\[\]()]', '', t)
    return {t[i:i + 2] for i in range(len(t) - 1)}


def layout_notes(text, summary='', section=''):
    """원고 → [(줄, 알림)]. ① 결론 상자와 첫 문단이 거의 같은 말이면, ② 단지·GTX 글에서 도시 입주 그림({{chart:moveins:…}})이
    첫 소제목 앞에 와 글 주제를 끊으면, ③ 방법론 절(고른 기준·산식)이 본문 앞쪽 절반에 오면 알린다."""
    out = []
    try:
        _, body = CM.split_front(text)
    except Exception:
        return out
    off = text.find(body) if body else 0
    first_h = re.search(r'^## ', body, re.M)
    paras = [m for m in re.finditer(r'^(?![#{|!>\-*\d])(\S.+)$', body, re.M)]
    if summary and paras:
        a, b = _bigrams(summary), _bigrams(paras[0].group(1))
        if a and b and len(a & b) / float(len(a | b)) > DUP_LIMIT:
            out.append((_line_of(text, off + paras[0].start()), '첫 문단이 결론 상자(summary)와 거의 같은 말 — 첫 문단은 다음 이야기로'))
    m = re.search(r'\{\{chart:moveins:[^}]*\}\}', body)
    if m and first_h and m.start() < first_h.start() and section in OFF_TOPIC_CITY_CHART:
        out.append((_line_of(text, off + m.start()), "도시 입주 물량 그림이 첫 소제목 앞 — 글 끝 '○○ 공급' 절로 옮기면 글 주제가 끊기지 않는다"))
    for h in re.finditer(r'^## (.+)$', body, re.M):
        if any(k in h.group(1) for k in METHOD_HEADS) and h.start() < len(body) / 2:
            out.append((_line_of(text, off + h.start()), "방법론 절('%s')이 본문 앞쪽 — 글 끝으로 보내면 결론·근거가 먼저 읽힌다" % h.group(1).strip()))
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    only = argv[0].replace('\\', '/').rstrip('/').split('/')[-1] if argv else None
    data = CT.load()
    posts = CM.posts(ROOT, section=only if only in CM.SECTIONS else None)
    if not posts:
        print('검사할 원고가 없다')
        return 0
    bad, waiting = 0, 0
    for sec, slug, path in posts:
        problems, waits, rel = check_post(path, data)
        text = io.open(path, encoding='utf-8').read()
        try:
            summary = CM.read(path, sec, slug)[0].get('summary') or ''
        except Exception:
            summary = ''
        for ln, why in sorted(term_notes(text) + layout_notes(text, summary, sec)):
            print('  ※    %s:%d  %s' % (rel, ln, why))
        for ln, why in sorted(waits):
            # 아직 수집되지 않은 시군구는 고칠 곳이 아니다 — 올리면 배치가 받아 넣고 다음 구움에서 나온다.
            print('  …    %s:%d  %s' % (rel, ln, why))
        if waits and not problems:
            waiting += 1
        if not problems:
            if not waits:
                print('  OK   %s' % rel)
            continue
        bad += 1
        for ln, why in sorted(problems):
            print('  ✗    %s:%d  %s' % (rel, ln, why))
    print('\n원고 %d편 중 %d편에 고칠 곳이 있다.%s' % (
        len(posts), bad,
        ' %d편은 아직 안 받은 도시를 기다린다(올려도 된다).' % waiting if waiting else ''))
    if bad:
        print('쓸 수 있는 자리표는 content/README.md 에 있다.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
