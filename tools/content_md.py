# -*- coding: utf-8 -*-
"""콘텐츠 원고(`content/<섹션>/<slug>.md`)의 프런트매터·마크다운 읽기(백로그 50).

생성기(make_content_pages)와 시험이 같은 파서를 쓴다. 표준 라이브러리만 쓴다 — 배치의 생성기 단계는
pip 설치 전에 돌기 때문이다(다른 생성기와 같은 제약).

프런트매터는 YAML 전체가 아니라 **우리가 쓰는 부분집합**만 읽는다: `키: 값`, `키:` 뒤의 `- 항목` 목록,
`- q:`/`  a:` 짝 목록. 모르는 모양을 만나면 조용히 넘기지 않고 ContentError 를 던진다 — 원고가 의도한
항목이 빠진 채 페이지가 구워지는 쪽이 더 나쁘다.
"""
import io
import os
import re

SECTIONS = ('city', 'gtx', 'danji', 'column')
REQUIRED = ('title', 'summary', 'date', 'updated', 'section')
SUMMARY_MIN, SUMMARY_MAX = 40, 120   # 요약은 AI 답변 블록의 첫 문단 — 한 문단을 넘기지 않는다
SLUG_RE = re.compile(r'^[a-z0-9][a-z0-9-]*$')
DATE_RE = re.compile(r'^\d{4}-\d{2}-\d{2}$')


class ContentError(Exception):
    """원고가 규약을 벗어났다. 생성기는 이걸 받아 배치를 세운다(반쯤 만든 페이지를 내보내지 않는다)."""


def split_front(text):
    """'---' 로 감싼 프런트매터와 본문을 가른다."""
    t = text.replace('\r\n', '\n').replace('\r', '\n')
    if not t.startswith('---\n'):
        raise ContentError("프런트매터가 없다 — 첫 줄이 '---' 여야 한다")
    end = t.find('\n---', 3)
    if end < 0:
        raise ContentError("프런트매터가 닫히지 않았다 — '---' 한 줄로 끝낼 것")
    nl = t.find('\n', end + 1)
    return t[4:end + 1], (t[nl + 1:] if nl >= 0 else '')


def _scalar(v):
    v = v.strip()
    if len(v) >= 2 and v[0] == v[-1] and v[0] in '"\'':
        v = v[1:-1]
    return v.strip()


def parse_front(block):
    """프런트매터 → dict. 값은 문자열, 목록, 또는 {'q','a'} 목록."""
    out, key, lines = {}, None, block.split('\n')
    i = 0
    while i < len(lines):
        raw = lines[i]
        i += 1
        if not raw.strip() or raw.lstrip().startswith('#'):
            continue
        if not raw[0].isspace() and not raw.lstrip().startswith('-'):
            m = re.match(r'^([A-Za-z_][\w-]*)\s*:(.*)$', raw)
            if not m:
                raise ContentError('프런트매터 줄을 읽지 못했다: %r' % raw)
            key, val = m.group(1), _scalar(m.group(2))
            out[key] = val if val else []
            continue
        if key is None:
            raise ContentError('프런트매터가 키 없이 시작한다: %r' % raw)
        item = raw.strip()
        if not item.startswith('- '):
            raise ContentError('프런트매터 목록 항목이 아니다: %r' % raw)
        item = item[2:].strip()
        if not isinstance(out.get(key), list):
            raise ContentError("'%s' 에 값과 목록이 함께 있다" % key)
        m = re.match(r'^([A-Za-z_][\w-]*)\s*:(.*)$', item)
        if m:                                     # - q: ... / a: ... 짝
            d = {m.group(1): _scalar(m.group(2))}
            while i < len(lines) and lines[i].strip() and lines[i][0].isspace() and not lines[i].strip().startswith('- '):
                m2 = re.match(r'^([A-Za-z_][\w-]*)\s*:(.*)$', lines[i].strip())
                if not m2:
                    raise ContentError('프런트매터 짝 항목을 읽지 못했다: %r' % lines[i])
                d[m2.group(1)] = _scalar(m2.group(2))
                i += 1
            out[key].append(d)
        else:
            out[key].append(_scalar(item))
    return out


def validate(meta, slug, section):
    """필수 항목·형식 검사. 어기면 ContentError — 빠진 채로 굽지 않는다."""
    miss = [k for k in REQUIRED if not meta.get(k)]
    if miss:
        raise ContentError('프런트매터에 %s 가 없다' % ', '.join(miss))
    for k in REQUIRED:
        if not isinstance(meta[k], str):
            raise ContentError("'%s' 는 한 줄 값이어야 한다" % k)
    if not SLUG_RE.match(slug):
        raise ContentError('파일 이름(slug)은 영소문자·숫자·붙임표만 쓴다: %r' % slug)
    if meta['section'] != section:
        raise ContentError("section(%r)이 폴더(%r)와 다르다" % (meta['section'], section))
    if section not in SECTIONS:
        raise ContentError('모르는 섹션이다: %r (쓸 수 있는 것: %s)' % (section, ', '.join(SECTIONS)))
    for k in ('date', 'updated'):
        if not DATE_RE.match(meta[k]):
            raise ContentError("'%s' 는 YYYY-MM-DD 여야 한다: %r" % (k, meta[k]))
    if meta['updated'] < meta['date']:
        raise ContentError('updated(%s)가 date(%s)보다 앞선다' % (meta['updated'], meta['date']))
    n = len(meta['summary'])
    if not (SUMMARY_MIN <= n <= SUMMARY_MAX):
        raise ContentError('summary 가 %d자다 — %d~%d자로 쓸 것(AI 답변 블록의 첫 문단)'
                           % (n, SUMMARY_MIN, SUMMARY_MAX))
    for f in meta.get('faq') or []:
        if not isinstance(f, dict) or not f.get('q') or not f.get('a'):
            raise ContentError('faq 항목은 q 와 a 가 모두 있어야 한다: %r' % (f,))
    if isinstance(meta.get('sources'), str):
        raise ContentError('sources 는 목록으로 쓴다(- 로 시작하는 줄)')
    return meta


def read(path, section=None, slug=None):
    """원고 한 편 → (meta, 본문 마크다운). 경로에서 섹션·slug 를 읽어 프런트매터와 대조한다."""
    section = section or os.path.basename(os.path.dirname(path))
    slug = slug or os.path.splitext(os.path.basename(path))[0]
    front, body = split_front(io.open(path, encoding='utf-8').read())
    meta = validate(parse_front(front), slug, section)
    meta['slug'] = slug
    return meta, body


def posts(root, section=None):
    """[(섹션, slug, 경로)] — 섹션 폴더 순서, 그 안은 파일 이름 순서."""
    base = os.path.join(root, 'content')
    out = []
    for sec in SECTIONS:
        if section and sec != section:
            continue
        d = os.path.join(base, sec)
        if not os.path.isdir(d):
            continue
        for fn in sorted(os.listdir(d)):
            if fn.endswith('.md'):
                out.append((sec, fn[:-3], os.path.join(d, fn)))
    return out
