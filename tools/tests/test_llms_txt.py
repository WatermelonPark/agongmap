# -*- coding: utf-8 -*-
"""/llms.txt — AI 검색이 읽는 사이트 요약(홈 마케팅 검수 D5, 2026-09-28 대표 승인).

지키는 것
  ① 배치가 구웠다: 디스크의 llms.txt = 생성기(make_llms_txt.build)가 지금 저장소로 구운 것.
  ② 방금 구운 sitemap.xml 의 /zone/<이름>/ 주소가 **전부** 실린다(퍼센트 디코딩해 비교). 순서는 집계(AGG) 먼저, 그다음
     DISPLAY_ORDER. sitemap 에 있는데 sido_zones 에 없는 이름은 버리지 않고 맨 뒤에 싣는다(배포된 페이지를 빠뜨리지 않는다).
  ③ 숫자가 없다: 세대·%·호·날짜(YYYY-MM, M/D)·분기(YYYYQn)·쉼표 숫자를 포함해 **링크 주소 밖의 모든 숫자**를 막는다.
     허용은 창 길이 'N년' 가운데 N 이 LEAD_Q/4·BACKLOG_WINDOW/4 인 것뿐이다(산식의 정의이지 데이터 값이 아니다). 발표 요일은
     글자('목요일')라 숫자 규칙에 걸리지 않는다.
  ④ 사이트 링크는 모두 sitemap 에 있는 주소이거나(피드처럼 sitemap 밖 파일이면) 저장소에 실제로 있는 파일이다. 핵심 페이지
     (허브·주간·월간·입주·전세가율·사이클·FAQ·소개·피드)가 모두 있다. 바깥 링크는 데이터 출처 기관(SOURCES)뿐이다.
  ⑤ llmstxt.org 형식: 첫 줄 `# 이름`, 그다음 `> 요약`, `## 섹션` 아래 `- [제목](절대 URL): 설명`.
  ⑥ 오늘 날짜를 읽지 않는다: datetime·time·kst 를 먼 과거·먼 미래로 바꿔도 같은 바이트.
  그 밖에: 식 이름은 sido_zones.formula_text() 그대로, 발표 요일은 weekly_release 에서, 출처 기관 이름·순서는 /about/ 과 같고,
  서비스워커가 /llms.txt 를 가로채지 않는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - make_llms_txt 의 문장 한 글자를 바꾸고 llms.txt 를 다시 굽지 않으면 → ① 빨강(배치·ci 에서 생성기를 빼면 같은 모양)
  - build 에서 zones 를 zones[:-1] 로 자르면 → ② 빨강. zone_order 가 모르는 이름을 버리게(key 대신 filter) 바꾸면 → ② 픽스처 빨강
  - build 의 식을 SZ.formula_text(need=SZ.REF_Q['전국']) 로(숫자를 넣은 식) 바꾸면 → ③ 빨강. 요약에 기준 분기를 넣어도 → ③ 빨강
  - /moveins/ 링크를 /movein/ 으로 바꾸면 → ④ 빨강(sitemap 에 없음). SOURCES 밖 바깥 주소를 넣어도 → ④ 빨강
  - 요약 줄의 '> ' 를 지우면 → ⑤ 빨강
  - build 끝에 KST.today_iso() 를 붙이면 → ⑥ 빨강
  - SOURCES 순서를 바꾸면(/about/ 과 다르게) → 출처 시험 빨강
  - weekly_release.SURVEY_WEEKDAY 를 1 로 바꾸면 → 요일 시험 빨강(status() 의 발표일 요일과 다름)
  - sw.js NO_SW 에서 '/llms.txt' 를 지우면 → 서비스워커 시험 빨강
픽스처: 저장소의 실제 sitemap.xml(생성기가 방금 구운 것)·faq/about 손 페이지·생성기가 방금 구운 llms.txt. ② 의 두 번째 시험은
실제 sitemap 에서 시도 하나를 빼고 sido_zones 에 없는 이름 하나(퍼센트 인코딩)를 더한 sitemap — 지역 개편 뒤 모델과 sitemap 이
한 회차 어긋난 모양이다. ③ 의 검사기 자기 확인은 실제 llms.txt 에 숫자 조각을 하나씩 끼운 문자열로 한다. 요일 시험의
월요일(2026-09-21)은 날짜 계산 픽스처일 뿐 데이터 값이 아니다(데이터가 앞으로 가도 그대로 초록).
"""
import datetime
import io
import os
import re
import sys
import urllib.parse
import xml.etree.ElementTree as ET


ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_llms_txt as L  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_release as WR  # noqa: E402
import kst as KST  # noqa: E402
from test_feed import _fake_clock  # noqa: E402  (datetime·time·kst 를 한꺼번에 돌리는 가짜 시계)

OUT = os.path.join(ROOT, 'llms.txt')
LINK = re.compile(r'\[([^\]]+)\]\(([^)\s]+)\)')
ITEM = re.compile(r'^- \[[^\]]+\]\((https?://[^)\s]+)\)(: .+)?$')
NS = '{http://www.sitemaps.org/schemas/sitemap/0.9}'


def _read(*p):
    return io.open(os.path.join(ROOT, *p), encoding='utf-8').read()


def _llms():
    assert os.path.exists(OUT), 'llms.txt 가 없다 — python tools/make_llms_txt.py (배치는 생성기 단계에서 굽는다)'
    return _read('llms.txt')


def _base():
    return 'https://' + _read('CNAME').strip()


def _sitemap_locs(xml=None):
    """sitemap 의 loc 전부(생성기와 다른 눈 — ElementTree 로 읽는다)."""
    root = ET.fromstring((xml if xml is not None else _read('sitemap.xml')).encode('utf-8'))
    return [(u.findtext(NS + 'loc') or u.findtext('loc') or '').strip() for u in root.iter()
            if u.tag in (NS + 'url', 'url')]


def _zone_names(urls, base):
    out = []
    for u in urls:
        path = urllib.parse.unquote(u[len(base):]) if u.startswith(base + '/') else ''
        m = re.match(r'^/zone/([^/]+)/$', path)
        if m:
            out.append(m.group(1))
    return out


def _links(text):
    return [u for _, u in LINK.findall(text)]


# ── ① 배치가 구웠다 ────────────────────────────────────────────────────────────
def test_llms_on_disk_is_what_the_generator_makes():
    assert _llms() == L.build(), 'llms.txt 가 지금 저장소로 구운 판과 다르다 — python tools/make_llms_txt.py'


# ── ② sitemap 의 시도 리포트 전부 ──────────────────────────────────────────────
def test_every_zone_page_in_the_sitemap_is_listed_in_order():
    base = _base()
    want = _zone_names(_sitemap_locs(), base)
    got = _zone_names(_links(_llms()), base)
    assert want, 'sitemap 에서 /zone/<이름>/ 주소를 하나도 못 읽었다 — 검사기가 헛돈다'
    assert set(want) <= set(got), 'llms.txt 에 빠진 시도 리포트: %s' % sorted(set(want) - set(got))
    assert len(got) == len(set(got)), '같은 시도 리포트가 두 번 실렸다: %s' % got
    known = [n for n in got if n in SZ.DISPLAY_ORDER]
    order = [n for n in SZ.AGG] + [n for n in SZ.DISPLAY_ORDER if n not in SZ.AGG]
    assert known == [n for n in order if n in known], '시도 순서가 집계 → DISPLAY_ORDER 가 아니다: %s' % known


def test_zone_list_follows_the_sitemap_not_the_model():
    """sitemap 에서 시도 하나를 빼고 모델에 없는 이름을 더하면 llms.txt 도 그대로 따라간다(모르는 이름은 맨 뒤)."""
    xml = _read('sitemap.xml')
    base = _base()
    names = _zone_names(_sitemap_locs(xml), base)
    drop = next(n for n in names if n not in SZ.AGG)
    drop_loc = '%s/zone/%s/' % (base, urllib.parse.quote(drop))
    assert drop_loc in xml, '빼려는 주소가 sitemap 모양과 다르다: %s' % drop_loc
    new = '새시도'
    assert new not in SZ.DISPLAY_ORDER
    extra = '<url><loc>%s/zone/%s/</loc><lastmod>2026-01-01</lastmod></url>' % (base, urllib.parse.quote(new))
    blk = re.search(r'<url>\s*<loc>%s</loc>.*?</url>' % re.escape(drop_loc), xml, re.S)
    assert blk, '빼려는 url 블록을 못 찾았다'
    fake = xml.replace(blk.group(0), '').replace('</urlset>', extra + '</urlset>')
    got = _zone_names(_links(L.build(sitemap_xml=fake)), base)
    assert drop not in got, 'sitemap 에 없는 시도가 실렸다(모델에서 목록을 만든다)'
    assert got and got[-1] == new, 'sitemap 에만 있는 이름을 버렸거나 맨 뒤가 아니다: %s' % got


# ── ③ 숫자 금지 ───────────────────────────────────────────────────────────────
ALLOWED_YEARS = {'%g년' % (SZ.LEAD_Q / 4.0), '%g년' % (SZ.BACKLOG_WINDOW / 4.0)}
# 이름 붙은 유형(보고용). 아래 '모든 숫자' 규칙이 이 전부를 덮는다 — 이 목록은 무엇이 걸렸는지 말해 주려고 둔다.
KINDS = (('날짜', r'\d{4}-\d{2}(-\d{2})?|\d{1,2}/\d{1,2}|\d{4}\.\d{2}'), ('분기', r'\d{4}\s*Q\s*[1-4]|\d분기'),
         ('쉼표 숫자', r'\d{1,3}(,\d{3})+'), ('세대·호', r'\d\s*(세대|호)'), ('%', r'\d\s*%p?|%'))


def number_problems(text):
    """링크 주소를 뺀 본문에서 허용되지 않은 숫자·% 조각 목록. 비어 있으면 통과."""
    body = LINK.sub(lambda m: '[' + m.group(1) + ']', text)
    bad = []
    for m in re.finditer(r'\d[\d,.]*\s*(년)?', body):
        tok = m.group(0).replace(' ', '')
        if tok in ALLOWED_YEARS:
            continue
        kind = next((k for k, pat in KINDS if re.search(pat, body[max(0, m.start() - 4):m.end() + 3])), '숫자')
        bad.append('%s:%s' % (kind, body[max(0, m.start() - 8):m.end() + 4].strip()))
    if '%' in body:
        bad.append('%: ' + body[max(0, body.index('%') - 8):body.index('%') + 2])
    return bad


def test_no_numbers_outside_window_lengths():
    bad = number_problems(_llms())
    assert not bad, 'llms.txt 에 숫자가 있다(배치마다 묵는다): %s' % bad


def test_number_checker_catches_each_kind():
    """검사기 자기 확인 — 실제 llms.txt 에 숫자 조각을 하나씩 끼워 모두 잡는지, 창 길이는 통과시키는지."""
    text = _llms()
    assert not number_problems(text + '\n지난 %s와 앞으로 %s\n' % tuple(sorted(ALLOWED_YEARS)))
    for frag in ('686,396세대', '18,700호', '60%', '+0.9%p', '2026-09', '2026-09-24', '9/24', '2026Q2', '2026년',
                 '16개 시도', '2026.08', '3분기'):
        assert number_problems(text + '\n' + frag + '\n'), '검사기가 %r 를 놓친다' % frag


def test_formula_and_release_weekday_come_from_the_canon():
    t = _llms()
    assert SZ.formula_text() in t, '식 이름이 sido_zones.formula_text() 와 다르다'
    assert '(%s요일)' % WR.pub_weekday() in t, '발표 요일이 weekly_release 와 다르다'
    for y in ALLOWED_YEARS:
        assert y in t


def test_pub_weekday_matches_the_release_schedule():
    monday = '2026-09-21'   # 날짜 계산 픽스처(조사기준일 모양 — 월요일)
    assert datetime.date(2026, 9, 21).weekday() == WR.SURVEY_WEEKDAY
    pub = WR.status(monday)['pub']
    assert WR.WEEKDAYS[datetime.date(*map(int, pub.split('-'))).weekday()] == WR.pub_weekday()


# ── ④ 링크 ────────────────────────────────────────────────────────────────────
CORE = ('/zone/', '/weekly/', '/monthly/', '/moveins/', '/jeonse-ratio/', '/cycle/', '/faq/', '/about/', '/feed.xml')


def test_site_links_are_published_pages_or_real_files():
    base = _base()
    locs = set(_sitemap_locs())
    links = _links(_llms())
    paths = [u[len(base):] for u in links if u.startswith(base + '/')]
    for p in CORE:
        assert p in paths, '핵심 페이지 %s 가 없다' % p
    for u in links:
        if not u.startswith(base + '/'):
            continue
        if u in locs:
            continue
        rel = urllib.parse.unquote(u[len(base) + 1:])
        assert rel and not rel.endswith('/') and os.path.isfile(os.path.join(ROOT, rel)), \
            '%s 는 sitemap 에도 없고 저장소 파일도 아니다' % u
    outside = [u for u in links if not u.startswith(base + '/')]
    assert outside == [u for _, u, _ in L.SOURCES], '바깥 링크가 데이터 출처 목록과 다르다: %s' % outside


# ── ⑤ 형식 ────────────────────────────────────────────────────────────────────
def test_llmstxt_shape():
    lines = _llms().split('\n')
    assert lines[0].startswith('# ') and lines[0][2:].strip(), '첫 줄이 `# 이름` 이 아니다'
    first = next(l for l in lines[1:] if l.strip())
    assert first.startswith('> ') and first[2:].strip(), '이름 다음 줄이 `> 요약` 이 아니다'
    assert sum(1 for l in lines if l.startswith('# ')) == 1, 'H1 은 하나다'
    h2 = [i for i, l in enumerate(lines) if l.startswith('## ')]
    assert h2, '`## 섹션` 이 없다'
    for l in lines[h2[0]:]:
        if l.startswith('## ') or not l.strip():
            continue
        assert ITEM.match(l), '섹션 안 줄이 `- [제목](절대 URL): 설명` 이 아니다: %r' % l


# ── ⑥ 오늘을 읽지 않는다 ──────────────────────────────────────────────────────
def test_output_does_not_depend_on_today(monkeypatch):
    outs = []
    for day in (datetime.date(2001, 1, 1), datetime.date(2039, 12, 31)):
        with monkeypatch.context() as m:
            _fake_clock(m, day)
            assert datetime.date.today().year == day.year and KST.today() == day   # 가짜 시계가 먹었는지
            outs.append(L.build())
    assert outs[0] == outs[1] == L.build()


# ── 출처·서비스워커 ───────────────────────────────────────────────────────────
def test_source_names_match_the_about_page():
    about = _read('about', 'index.html')
    names = '·'.join(n for n, _, _ in L.SOURCES)
    dd = re.search(r'<dt>출처를 전부 밝힙니다</dt>\s*<dd>([^<]*)', about)
    assert dd, '/about/ 의 출처 줄을 못 찾았다'
    assert dd.group(1).startswith(names + ' '), '/about/ 출처(%s)와 llms.txt 출처(%s)가 다르다' % (dd.group(1), names)
    assert ('자료: ' + names) in about, '/about/ 푸터 출처가 llms.txt 출처와 다르다'
    assert names in _llms()


def test_service_worker_leaves_llms_txt_alone():
    sw = _read('sw.js')
    m = re.search(r'const NO_SW = new Set\(\[([^\]]*)\]\)', sw)
    assert m and "'%s'" % L.PATH in m.group(1), 'sw.js NO_SW 에 /llms.txt 가 없다'
    rb = _read('robots.txt')
    assert not re.search(r'(?im)^Disallow:\s*/(llms\.txt)?\s*$', rb), 'robots.txt 가 /llms.txt 를 막는다'
