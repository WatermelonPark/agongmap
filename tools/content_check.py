# -*- coding: utf-8 -*-
"""원고 검사기 — `content/` 의 모든 원고를 훑어 어긋난 곳을 **파일과 줄 번호로** 알려 준다(백로그 50).

왜 따로 있나. 생성기(make_content_pages)는 깨진 글을 건너뛰고 나머지를 굽는다(배치를 세우지 않으려고).
그래서 작성 세션에게는 '무엇이 왜 걸렸는지'를 한 번에 보여 주는 쪽이 필요하다. 이 검사기는 고치는 사람을
위한 것이라 **모든 문제를 모아** 보여 주고, 하나라도 있으면 종료 코드 1 로 끝난다.

사용:
    python tools/content_check.py                 전부 검사
    python tools/content_check.py content/gtx     그 폴더만
    python tools/content_check.py --lenient       2026-11-05 양식(tldr·audience·key·city·topic)을 묻지 않는다 — 옛 원고를
                                                  고치는 동안만. 환경 변수 CONTENT_CHECK_LENIENT=1 도 같다. 커밋 기본은 엄격.
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


def _pages():
    """생성기 모듈 — 쓸 때 가져온다(뼈대·시도 생성기까지 따라 들어와 무겁다. 표준 라이브러리뿐이라 설치는 필요 없다)."""
    import make_content_pages as MC
    return MC


def _probe(data, m):
    """자리표 하나를 실제로 만들어 본다 — 종류마다 맞는 함수로. 오류는 그대로 올린다.

    생성기가 쓰는 함수를 그대로 부른다. 검사기가 따로 흉내내면 '검사는 통과했는데 생성기에서 걸리는'
    원고가 생긴다.
    """
    parts = [p.strip() for p in m.group(2).split(':')]
    return {'v': CT.value, 'table': CT.table, 'chart': CT.chart}[m.group(1)](data, parts[0], parts[1:])


def check_post(path, data, root=ROOT, lenient=False):
    """한 편 → [(줄, 문제)]"""
    rel = os.path.relpath(path, root).replace(os.sep, '/')
    text = io.open(path, encoding='utf-8').read()
    out, waits = [], []
    try:
        meta, body = CM.read(path, lenient=lenient)
    except CM.ContentError as e:
        msg = str(e).split(': ', 1)[-1]
        if CM.is_v2_miss(e):
            # 옛 양식 — 올려도 되지만(생성기가 옛 양식으로 굽는다) 카드에 지역·핵심 숫자가 빠진다. 기다림(…)으로 알린다.
            waits.append((1, msg + ' — 올라가지만 카드에 지역 칩·핵심 숫자가 빠진다'))
            meta, body = CM.read(path, lenient=True)
            lenient = True
        else:
            key = next((k for k in CM.REQUIRED + CM.REQUIRED_V2 + ('faq', 'sources', 'region') if k in msg), None)
            return ([(_front_line(text, key) if key else 1, msg)], [], rel)
    # 2026-11-05 양식의 지역·길이 — 이름표에 없는 city, 자리표를 채우면 넘치는 길이. 생성기(make_content_pages)와 같은 함수다.
    if not lenient:
        for name in meta.get('city') or []:
            try:
                CT.city_codes(data, name)
            except CT.TableError as e:
                out.append((_front_line(text, 'city'), str(e)))
        try:
            CT.check_lengths(CT.fill_meta(meta, data))
        except CT.Pending:
            pass                                   # 아직 안 받은 도시의 자리표 — 아래 본문 검사가 기다림으로 센다
        except CT.TableError as e:
            msg = str(e)
            key = next((k for k in ('tldr', 'audience', 'key', 'title') if msg.startswith(k)), 'title')
            out.append((_front_line(text, key), msg))
    # 본문은 프런트매터 뒤에서 시작한다 — 줄 번호를 파일 기준으로 되돌린다.
    offset = text.count('\n', 0, text.index(body)) if body and body in text else 0
    for m in PLACEHOLDER.finditer(body):
        try:
            _probe(data, m)
        except CT.Pending as e:
            waits.append((offset + _line_of(body, m.start()), '%s — %s' % (m.group(0), e)))
        except CT.TableError as e:
            out.append((offset + _line_of(body, m.start()), '%s — %s' % (m.group(0), e)))
    # 요약·FAQ 는 생성기와 **같은 함수**(fill_inline)로 본다. 한 줄 글에 못 들어가는 종류(표·그림)까지
    # 같은 눈으로 걸러야, 검사를 통과한 원고가 생성기에서 건너뛰어지는 일이 없다.
    for key in ('summary', 'title'):
        try:
            CT.fill_inline(meta.get(key) or '', data)
        except CT.Pending as e:
            # 아직 안 들어온 자료는 고칠 곳이 아니다 — 본문의 같은 자리표와 같은 눈으로 기다림(…)에 센다. 예전엔 Pending 이
            # TableError 의 아래 갈래라 여기서만 ✗ 가 됐다(2026-11-13 전수 리뷰).
            waits.append((_front_line(text, key), '%s: %s' % (key, e)))
        except CT.TableError as e:
            out.append((_front_line(text, key), '%s: %s' % (key, e)))
    for i, src in enumerate(meta.get('sources') or []):
        try:
            CT.fill_inline(src if isinstance(src, str) else '', data)
        except CT.TableError as e:
            out.append((_front_line(text, 'sources'), 'sources %d번: %s' % (i + 1, e)))
    for i, f in enumerate(meta.get('faq') or []):
        try:
            CT.fill_inline((f.get('q') or '') + ' ' + (f.get('a') or ''), data)
        except CT.TableError as e:
            out.append((_front_line(text, 'faq'), 'faq %d번: %s' % (i + 1, e)))
    # 표 줄(|)인데 표가 되지 못한 줄 — 생성기의 마크다운 걸음(MC.markdown)이 직접 알려 준다(검사기가 문법을 따로 흉내내지 않는다).
    stray = []
    _pages().markdown(body, stray)
    for n, s in stray:
        out.append((offset + n, "표 줄이 표가 되지 못했다 — 머리 줄 바로 아래 구분 줄(|---|---|)과 줄 끝 파이프(|)를 볼 것: %s" % s[:40]))
    # 끝으로 **생성기의 '한 편 굽기'를 그대로** 돌려 본다. 위 검사들이 못 본 탈(값의 꼴이 달라 굽다 예외로 끝나는 원고)이
    # 여기서 드러난다 — 검사를 통과한 원고가 배치의 생성기 단계에서 멈추는 일을 구조로 막는다(2026-11-13 전수 리뷰).
    if not out:
        try:
            _pages().build_page(CT.check_lengths(CT.fill_meta(meta, data)) if not lenient else CT.fill_meta(meta, data), body, data)
        except CT.Pending as e:
            if not waits:
                waits.append((1, str(e)))
        except (CT.TableError, CM.ContentError) as e:
            out.append((1, '생성기가 이 글을 건너뛴다 — %s' % e))
        except Exception as e:      # noqa: BLE001 — 예상 밖 예외를 고칠 곳으로 알리는 것이 이 줄의 일이다
            out.append((1, '생성기가 이 글을 굽다 예외로 멈춘다 — %s: %s' % (type(e).__name__, e)))
    return [(ln, '%s' % why) for ln, why in out], waits, rel


# 사이트 정본 낱말(CLAUDE.md '같은 개념은 한 이름, 물량은 한 단위' — 적정물량·세대). 원고 문장은 작성 세션의 몫이라
# 막지 않고 알림만 한다(2026-10-30 디자인 리뷰 — 콘텐츠 글에 '적정 입주량'·'적정 대비'·'2,056가구'가 섞였다).
TERM_NOTES = (
    (re.compile(r'적정\s+입주량'), "'적정 입주량' → '적정물량'"),
    (re.compile(r'적정\s+대비'), "'적정 대비' → '적정물량 대비'"),
    (re.compile(r'\d[\d,]*\s*가구'), "물량 단위 '가구' → '세대'"),
    # 화면 날짜 두 단계(CLAUDE.md) — 원고 문장 속 ISO 날짜. 프런트매터의 date·updated(기계가 읽는 값)는 세지 않는다.
    (re.compile(r'(?<![\d:/-])20\d\d-\d\d-\d\d(?!\d)'), "ISO 날짜 → 읽는 자리는 '10/26'·'2026년 10월 26일', 표 칸은 '26.10.26'"),
    (re.compile(r'\(20\d\d-\d\d-\d\d 조사\)'), "출처 조사일을 손으로 적지 않는다 → '{{v:asof:weekly}} 조사'"),
    # 2026-11-07 대표 승인 원고 규칙(docs/2026-11-07-콘텐츠-원고-규칙-안내.md) — 옛 양식으로 올라온 글이 같은 지적을 되풀이하지 않게.
    (re.compile(r'적정의\s*(?=\{\{|\d)'), "'적정의 N%' → '적정물량의 N%'"),
    (re.compile(r'^## 더 보기\s*$', re.M), "글 끝 '## 더 보기' 절은 쓰지 않는다 — 페이지 틀의 '이 지역 더 보기' 상자가 같은 링크를 단다"),
    (re.compile(r'!\[[^\]]*시세 (?:화면|추이)[^\]]*\]\('), "다른 서비스 앱의 시세 화면 캡처는 싣지 않는다 — 우리 표·그림(자리표)으로"),
)


def term_notes(text):
    """원고 글 → [(줄, 알림)]. 고칠 곳(종료 코드)에 세지 않는다."""
    out = []
    for pat, why in TERM_NOTES:
        for m in pat.finditer(text):
            line = text[text.rfind('\n', 0, m.start()) + 1:text.find('\n', m.start())]
            if re.match(r'^(date|updated)\s*:', line):
                continue                      # 프런트매터 날짜는 기계가 읽는 값이다
            out.append((_line_of(text, m.start()), '%s (%s)' % (why, m.group(0))))
    return out


# 글 배치 알림(2026-10-30 디자인 리뷰 3차) — 원고 구조는 작성 세션의 몫이라 고칠 곳에 세지 않고 알림만 한다.
OFF_TOPIC_CITY_CHART = ('gtx', 'danji')   # 도시 편은 도시 입주가 곧 주제라 앞에 와도 된다
METHOD_HEADS = ('고른 기준', '산식', '방법', '계산 방법', '이 글의 기준', '이렇게 셌', '세는 법')
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


# 카드 핵심 숫자 알림(2026-11-07 디자인 검수) — 카드에서 가장 큰 글자(22px)가 새 정보를 주지 않거나 다른 글과 같으면 글을 가르지
# 못한다(도시 편 11장 전부가 제목의 '적정물량의 N%'를 되풀이했고, 발언 검증 3장이 같은 '적정물량의 28%'였다). 원고의 몫이라 알림만.
_NUM = re.compile(r'\d[\d,]*(?:\.\d+)?')
WIDE_TABLE_COLS = 7         # 원고 표가 이보다 열이 많으면 휴대폰에서 핵심 열이 화면 밖으로 밀린다


def _key_value(meta):
    k = meta.get('key')
    if isinstance(k, list) and k and isinstance(k[0], dict):
        k = k[0]
    return (k.get('value') or '').strip() if isinstance(k, dict) else ''


def key_notes(entries):
    """[(rel, 원고 글, 자리표 채운 meta)] → {rel: [(줄, 알림)]}. 세 가지를 본다.

    ① key.value 의 숫자가 모두 제목에 이미 있다 — 카드 큰 숫자가 제목을 되풀이한다.
    ② 같은 섹션의 다른 글과 key.value 가 같다 — 카드끼리 숫자로 갈리지 않는다.
    ③ key.value 에 소수 둘째 자리 이상('105.95%') — 큰 숫자는 한눈에 읽히는 정밀도로.
    """
    out = {}
    by_val = {}
    for rel, text, meta in entries:
        v = _key_value(meta)
        if v:
            by_val.setdefault((meta.get('section'), v), []).append(rel)
    for rel, text, meta in entries:
        v = _key_value(meta)
        if not v:
            continue
        ln = _front_line(text, 'key')
        notes = []
        nums = _NUM.findall(v)
        title = meta.get('title') or ''
        if nums and all(re.search(r'(?<![\d,.])%s(?![\d,]|\.\d)' % re.escape(n), title) for n in nums):
            notes.append((ln, "카드 핵심 숫자 '%s' — 제목에 이미 있는 값이라 카드가 새 정보를 주지 않는다(제목에 없는 값: 절대량·기준 시점 등)" % v))
        same = [r for r in by_val.get((meta.get('section'), v), []) if r != rel]
        if same:
            notes.append((ln, "카드 핵심 숫자 '%s' — 같은 섹션 %s 와 같은 값이라 숫자로는 글이 갈리지 않는다" % (v, ', '.join(same))))
        if re.search(r'\d\.\d{2,}', v):
            notes.append((ln, "카드 핵심 숫자 '%s' — 소수 둘째 자리까지다. 큰 숫자는 정수·한 자리로(정확값은 본문에)" % v))
        if notes:
            out[rel] = notes
    return out


def table_notes(text):
    """원고 → [(줄, 알림)]. 열이 WIDE_TABLE_COLS 보다 많은 원고 표 — 휴대폰에서 첫 두세 열만 보이고 핵심 열(가격·현금)이 밀린다."""
    out = []
    lines = text.split('\n')
    for i, ln in enumerate(lines):
        s = ln.strip()
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()):
            n = len(s.strip('|').split('|'))
            if n > WIDE_TABLE_COLS:
                out.append((i + 1, '표가 %d열 — 휴대폰에서 앞 두세 열만 보인다. 핵심 열을 둘째 자리로 올리거나 나머지 열을 다른 표로' % n))
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    lenient = '--lenient' in argv or os.environ.get('CONTENT_CHECK_LENIENT') == '1'
    argv = [a for a in argv if a != '--lenient']
    only = argv[0].replace('\\', '/').rstrip('/').split('/')[-1] if argv else None
    data = CT.load()
    posts = CM.posts(ROOT, section=only if only in CM.SECTIONS else None)
    if not posts:
        print('검사할 원고가 없다')
        return 0
    bad, waiting = 0, 0
    entries = []
    for sec, slug, path in posts:
        try:
            try:
                m = CM.read(path, sec, slug)[0]          # 엄격 읽기가 key 를 dict 로 고른다 — 그래야 자리표가 채워진다
            except CM.ContentError:
                m = CM.read(path, sec, slug, lenient=True)[0]
            try:
                m = CT.fill_meta(m, data)
            except CT.TableError:
                pass                              # 자리표를 못 채운 글은 원고 글자 그대로 본다(그 오류는 아래에서 센다)
            entries.append((os.path.relpath(path, ROOT).replace(os.sep, '/'), io.open(path, encoding='utf-8').read(), m))
        except Exception:
            continue
    knotes = key_notes(entries)
    for sec, slug, path in posts:
        problems, waits, rel = check_post(path, data, lenient=lenient)
        text = io.open(path, encoding='utf-8').read()
        try:
            summary = CM.read(path, sec, slug, lenient=True)[0].get('summary') or ''
        except Exception:
            summary = ''
        for ln, why in sorted(term_notes(text) + layout_notes(text, summary, sec) + table_notes(text) + knotes.get(rel, [])):
            print('  ※    %s:%d  %s' % (rel, ln, why))
        for ln, why in sorted(waits):
            # 아직 자료가 없는 것은 고칠 곳이 아니다(안 받은 도시, 아직 분양 안 된 연도) —
            # 올리면 배치가 받아 넣고 다음 구움에서 나온다.
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
    print('\n원고 %d편 중 %d편에 고칠 곳이 있다.%s%s' % (
        len(posts), bad,
        ' %d편은 아직 안 들어온 자료를 기다린다(올려도 된다).' % waiting if waiting else '',
        ' (--lenient: 2026-11-05 양식은 묻지 않았다 — 커밋 전에 기본값으로 다시 돌릴 것)' if lenient else ''))
    if bad:
        print('쓸 수 있는 자리표는 content/README.md 에 있다.')
    return 1 if bad else 0


if __name__ == '__main__':
    sys.exit(main())
