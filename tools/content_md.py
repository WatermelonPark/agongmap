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
# 2026-11-05 콘텐츠 구조 개편(대표 지시 "어떤 글이 내 관심사인지 모르겠다") — 독자가 카드 하나로 글을 고르게 하는 다섯 항목.
# 이것도 필수다. 없으면 생성기는 그 글을 건너뛰고(경고), 원고 검사는 고칠 곳으로 센다. 일할 때는 content_check --lenient.
REQUIRED_V2 = ('tldr', 'audience', 'key', 'city', 'topic')
# 글의 질문(주제) — 허브 '질문으로 찾기'의 네 입구. (키, 질문, 칩에 쓰는 짧은 이름, 그 질문이 사는 섹션).
# make_content_pages.TOPICS 가 같은 튜플이다(생성기가 content_md 를 들여오므로 정본은 여기 두고 거기서 다시 내보낸다).
# 짧은 이름은 **섹션 이름의 정본**이기도 하다 — 칩·빵부스러기·<title>·og·카드·llms·홈 푸터가 모두 이 이름을 쓴다
# (2026-11-07 디자인 검수: 한 섹션을 '반박'·'발언 검증'·'해설' 세 이름으로 불렀다). 도시 편은 /moveins/ '입주물량'과
# 겹치지 않게 '도시 입주물량'이다.
TOPICS = (
    ('moveins', '내 동네, 앞으로 입주 얼마나?', '도시 입주물량', 'city'),
    ('first-home', '역세권 첫 집, 얼마면 되나?', '역세권 첫 집', 'gtx'),
    ('redevelop', '재건축·리모델링, 어디까지 왔나?', '재건축·리모델링', 'danji'),
    ('claim', '그 발언, 숫자로 맞나?', '발언 검증', 'column'),
)
TOPIC_KEYS = tuple(t[0] for t in TOPICS)
# 글자 수 상한(카드·글 머리가 한 화면에 들어오는 길이). 자리표 {{…}} 는 빼고 센다 — 채운 길이는 content_check·생성기가
# content_tables.check_lengths 로 한 번 더 본다.
TITLE_MAX, TLDR_N, TLDR_MAX, AUDIENCE_MAX, KEY_MAX, CITY_MAX = 45, 3, 60, 50, 12, 3
_PH = re.compile(r'\{\{[^}]*\}\}')
# 요약은 AI 답변 블록의 첫 문단이다. 요청서는 40~60자였는데 실제 원고는 숫자와 출처를 담아 100자를 넘는다
# (2026-10-27 첫 19편 가운데 gtx-a-changneung 이 121자). 한 문단을 넘기지만 않으면 되므로 상한을 180자로 둔다.
SUMMARY_MIN, SUMMARY_MAX = 40, 180
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


V2_MISS = '프런트매터에 %s 가 없다(2026-11-05 양식 — content/README.md)'


def is_v2_miss(err):
    """ContentError 가 '2026-11-05 양식 다섯 항목 없음'인가 — 생성기는 그 글을 옛 양식으로 굽고(경고), 검사기는 기다림으로 센다."""
    return '2026-11-05 양식' in str(err)


def vis_len(text):
    """자리표를 뺀 글자 수 — 상한을 잴 때 쓴다."""
    return len(_PH.sub('', text or '').strip())


def validate_v2(meta):
    """2026-11-05 양식의 다섯 항목. 모양을 고쳐 넣는다: key 는 dict, city 는 목록. 어기면 ContentError.

    오류 글은 그대로 작성 세션에게 간다 — 무엇을 몇 자로 고칠지 한 줄에 다 적는다.
    """
    # city 는 비어도 된다 — 시도 전체를 말하는 글(서울 집값 발언 반박 등)은 region 이 지역이다. 그때 허브 지역 칩은 '서울 전체'.
    miss = [k for k in REQUIRED_V2 if not meta.get(k) and not (k == 'city' and meta.get('region') and k in meta)]
    if miss:
        raise ContentError(V2_MISS % ', '.join(miss))
    n = vis_len(meta['title'])
    if n > TITLE_MAX:
        raise ContentError('title 이 %d자다 — %d자 이하 결론형 한 문장으로' % (n, TITLE_MAX))
    tl = meta['tldr']
    if not isinstance(tl, list) or len(tl) != TLDR_N or not all(isinstance(x, str) and x.strip() for x in tl):
        raise ContentError('tldr 는 "- " 줄 %d개여야 한다(지금 %s)' % (
            TLDR_N, '%d줄' % len(tl) if isinstance(tl, list) else '한 줄 값'))
    for i, x in enumerate(tl):
        if vis_len(x) > TLDR_MAX:
            raise ContentError('tldr %d번째 줄이 %d자다 — %d자 이하' % (i + 1, vis_len(x), TLDR_MAX))
    if not isinstance(meta['audience'], str):
        raise ContentError('audience 는 한 줄 값이어야 한다')
    if vis_len(meta['audience']) > AUDIENCE_MAX:
        raise ContentError('audience 가 %d자다 — %d자 이하' % (vis_len(meta['audience']), AUDIENCE_MAX))
    key = meta['key']
    if isinstance(key, list) and len(key) == 1 and isinstance(key[0], dict):
        key = key[0]                       # '- label: …' 한 짝 목록(작성 세션의 꼴)
    if not isinstance(key, dict) or not key.get('label') or not key.get('value'):
        raise ContentError('key 는 label 과 value 한 짝이다(key: 아래 "- label: 2027년 입주" 줄과 "value: 적정의 141%" 줄)')
    for k in ('label', 'value'):
        if vis_len(key[k]) > KEY_MAX:
            raise ContentError('key.%s 가 %d자다 — %d자 이하' % (k, vis_len(key[k]), KEY_MAX))
    meta['key'] = {'label': key['label'], 'value': key['value']}
    city = meta['city']
    if isinstance(city, str):
        city = [city]
    lo = 0 if meta.get('region') else 1
    if not isinstance(city, list) or not (lo <= len(city) <= CITY_MAX) or not all(isinstance(c, str) and c.strip() for c in city):
        raise ContentError('city 는 시군구 이름 1~%d곳 목록이다(지금 %s)%s' % (
            CITY_MAX, '%d곳' % len(city) if isinstance(city, list) else '목록이 아님',
            '' if lo else ' — 시도 전체 글이면 region 을 적고 city 를 비운다'))
    meta['city'] = [c.strip() for c in city]
    if meta['topic'] not in TOPIC_KEYS:
        raise ContentError('topic 은 %s 가운데 하나다: %r' % (', '.join(TOPIC_KEYS), meta['topic']))
    return meta


def validate(meta, slug, section, lenient=False):
    """필수 항목·형식 검사. 어기면 ContentError — 빠진 채로 굽지 않는다. lenient=True 는 2026-11-05 양식(REQUIRED_V2)을
    묻지 않는다 — 옛 원고를 고치는 동안 검사기·생성기를 돌릴 때만 쓴다."""
    miss = [k for k in REQUIRED if not meta.get(k)]
    if miss:
        raise ContentError('프런트매터에 %s 가 없다' % ', '.join(miss))
    for k in REQUIRED:
        if not isinstance(meta[k], str):
            raise ContentError("'%s' 는 한 줄 값이어야 한다" % k)
    if not lenient:
        validate_v2(meta)
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


def read(path, section=None, slug=None, lenient=False):
    """원고 한 편 → (meta, 본문 마크다운). 경로에서 섹션·slug 를 읽어 프런트매터와 대조한다."""
    section = section or os.path.basename(os.path.dirname(path))
    slug = slug or os.path.splitext(os.path.basename(path))[0]
    try:
        front, body = split_front(io.open(path, encoding='utf-8').read())
        meta = validate(parse_front(front), slug, section, lenient=lenient)
    except ContentError as e:
        # 어느 원고인지 먼저 말한다 — 여러 편을 한꺼번에 굽다 멈추면 파일 이름 없이는 찾는 데만 시간이 든다.
        raise ContentError('%s/%s.md: %s' % (section, slug, e))
    meta['slug'] = slug
    return meta, body


def built(root, section=None):
    """[(섹션, slug, 경로)] — **페이지가 구워져 있는** 원고만. 피드·llms 가 쓰는 기준이다.

    ⚠️ 원고만 올라오고 생성기가 아직 안 돈 상태(작성 세션이 .md 를 먼저 커밋)는 정상이다. 그 글을 피드나
       llms.txt 에 실으면 없는 주소를 광고하게 된다 — 구워진 뒤부터 싣는다.
    """
    return [(sec, slug, path) for sec, slug, path in posts(root, section)
            if os.path.exists(os.path.join(root, sec, slug, 'index.html'))]


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
