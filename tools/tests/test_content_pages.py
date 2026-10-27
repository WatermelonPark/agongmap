# -*- coding: utf-8 -*-
"""콘텐츠 섹션 생성기(백로그 50) — 원고 검사·자리표·구조화 데이터·배치 연결을 고정한다.

왜 이 시험이 있나. 이 생성기는 사람이 쓴 원고를 받아 페이지를 굽는다. 조용히 틀리는 길이 셋이다.
  ① 프런트매터가 빠진 채 페이지가 구워져 AI 가 날짜·저자 없는 글을 읽는다.
  ② 자리표가 안 채워진 채(혹은 빈 표로) 나가 `{{table:...}}` 가 그대로 보인다.
  ③ 숫자가 사이트 데이터와 달라진다 — 원고에 손으로 적은 옛 숫자가 남는다.
그래서 시험은 생성기를 실제로 돌려(임시 저장소) 결과 HTML 을 읽고, 데이터와 따로 대조한다.

픽스처: tmp_path 에 content/city/*.md 를 쓰고 저장소의 실제 data-*.json 을 그대로 읽는다(값은 배치마다
바뀌므로 **기대값을 박지 않고** 같은 데이터에서 따로 계산해 비교한다).
"""
import io
import json
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import content_md as CM            # noqa: E402
import content_tables as CT        # noqa: E402
import home_src as HS              # noqa: E402  (홈 파일 위치의 정본 — 백로그 10)
import make_content_pages as MC    # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

FRONT = """---
title: 시험용 글 제목
summary: 시험이 쓰는 요약입니다. 마흔 자를 넘기도록 한 문단으로 적고, 답변 블록에 그대로 실립니다.
date: 2026-10-20
updated: 2026-10-27
section: city
region: 인천
sources:
  - 국토교통부 주택건설실적통계(인허가·착공·준공)
faq:
  - q: 질문입니다
    a: 답변입니다
---

## 머리글

문단입니다.

{{table:moveins:인천:2027}}

주간 변동률은 {{v:weekly:인천}} 입니다.
"""


def _write(tmp_path, body=FRONT, slug='test-post', section='city'):
    d = tmp_path / 'content' / section
    d.mkdir(parents=True, exist_ok=True)
    (d / (slug + '.md')).write_text(body, encoding='utf-8')
    return str(tmp_path / 'content' / section / (slug + '.md'))


# ── ① 프런트매터 ────────────────────────────────────────────────────────────
def test_missing_front_matter_fields_fail(tmp_path):
    """필수 항목이 빠지면 ContentError 로 멈춘다 — 날짜·저자 없는 페이지를 굽지 않는다.

    무엇을 바꾸면 빨개지나: content_md.REQUIRED 에서 항목을 빼거나 validate 의 검사를 지우면.
    픽스처: 올바른 원고에서 한 줄씩 지운 판(실제 작성 세션이 흔히 빠뜨리는 모양).
    """
    for key in CM.REQUIRED:
        body = '\n'.join(l for l in FRONT.split('\n') if not l.startswith(key + ':'))
        p = _write(tmp_path, body, slug='miss-' + key)
        with pytest.raises(CM.ContentError) as e:
            CM.read(p)
        assert key in str(e.value), '%s 가 빠졌는데 다른 오류가 났다: %s' % (key, e.value)


def test_bad_values_fail(tmp_path):
    """형식이 어긋난 값(날짜, 섹션 불일치, 짧은 요약, 잘못된 slug)도 멈춘다."""
    cases = [
        ('date: 2026-10-20', 'date: 20261020', 'date'),
        ('section: city', 'section: gtx', 'section'),
        ('summary: 시험이 쓰는 요약입니다. 마흔 자를 넘기도록 한 문단으로 적고, 답변 블록에 그대로 실립니다.', 'summary: 짧다', 'summary'),
        ('updated: 2026-10-27', 'updated: 2026-10-01', 'updated'),
    ]
    for old, new, word in cases:
        p = _write(tmp_path, FRONT.replace(old, new), slug='bad-' + word)
        with pytest.raises(CM.ContentError) as e:
            CM.read(p)
        assert word in str(e.value)
    p = _write(tmp_path, FRONT, slug='Bad_Slug')
    with pytest.raises(CM.ContentError):
        CM.read(p)


# ── ② 자리표 ────────────────────────────────────────────────────────────────
def test_unknown_placeholder_fails():
    """모르는 자리표·없는 지역은 실패한다 — 빈 표나 `{{...}}` 를 내보내지 않는다.

    무엇을 바꾸면 빨개지나: content_tables.table 의 마지막 raise 를 지우고 빈 값을 돌려주면.
    """
    data = CT.load()
    for kind, args in (('mystery', ['인천']), ('moveins', ['없는도시']), ('stats', ['없는계열', '인천'])):
        with pytest.raises(CT.TableError):
            CT.table(data, kind, args)


def test_tables_match_the_site_data():
    """자리표 표의 숫자가 data-*.json 과 같다.

    무엇을 바꾸면 빨개지나: content_tables 가 다른 열·다른 기간을 읽거나 단위를 바꾸면.
    픽스처: 저장소의 실제 데이터. 기대값은 여기서 따로 계산한다(배치마다 값이 바뀌므로 박지 않는다).
    """
    data = CT.load()
    occ = data['occupancy']
    i = occ['regions'].index('인천')
    want = {r['p']: (r.get('v') or [])[i] for r in occ['rows'] if str(r['p']).startswith('2027')}
    head, body, _ = CT.table(data, 'moveins', ['인천', '2027'])
    got = {r[0]: int(r[1].replace(',', '')) for r in body if r[0] != '합계'}
    assert got == {p: int(round(v)) for p, v in want.items() if v is not None}, '분기별 입주물량이 데이터와 다르다'
    total = [r for r in body if r[0] == '합계'][0]
    assert int(total[1].replace(',', '')) == int(round(sum(v for v in want.values() if v is not None)))

    W = data['weekly']
    j = W['regions'].index('인천')
    last = W['rows'][-1]
    assert CT.value(data, 'weekly', ['인천']) == CT.pct(last['ma'][j]) + '%', '주간 값이 최신 주와 다르다'


def test_region_display_name_is_accepted():
    """화면 이름(광주·전남)으로 써도 내부 키로 찾는다 — 작성 세션이 화면에 보이는 이름을 쓴다."""
    import sido_zones as SZ
    data = CT.load()
    merged = [k for k, v in SZ.DISPLAY_NAME.items() if v]
    if not merged:
        pytest.skip('화면 이름이 다른 지역이 없다')
    key = merged[0]
    assert CT.region_key(data, SZ.DISPLAY_NAME[key]) == key


# ── ③ 페이지와 구조화 데이터 ────────────────────────────────────────────────
def _build_page(tmp_path):
    p = _write(tmp_path)
    meta, body = CM.read(p)
    page, lm = MC.build_page(meta, body, CT.load())
    return meta, page, lm


def test_page_has_summary_dates_author_sources_and_no_placeholder(tmp_path):
    """요약·날짜·저자·출처·면책이 모두 페이지에 있고, 자리표는 하나도 남지 않는다."""
    meta, page, _ = _build_page(tmp_path)
    assert meta['summary'] in page and 'csum' in page, '요약 답변 블록이 없다'
    assert meta['date'] in page and meta['updated'] in page, '작성일·갱신일이 없다'
    assert MC.AUTHOR in page and '/about/' in page, '저자 표기가 없다'
    assert '국토교통부 주택건설실적통계' in page, '출처 목록이 없다'
    assert '투자자문이 아닙니다' in page, '면책 한 줄이 없다'
    assert '{{' not in page, '자리표가 남았다'
    assert '<table>' in page, '자리표 표가 그려지지 않았다'


def test_json_ld_is_valid_and_dates_match(tmp_path):
    """JSON-LD 가 유효한 JSON 이고 dateModified 가 updated 와 같다. faq 가 있으면 FAQPage 가 나간다.

    무엇을 바꾸면 빨개지나: _ld 가 datePublished 를 dateModified 에 넣거나 FAQPage 를 빼면.
    """
    meta, page, _ = _build_page(tmp_path)
    blocks = re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
    assert blocks, 'JSON-LD 가 없다'
    types = {}
    for b in blocks:
        d = json.loads(b)                      # 깨진 JSON 이면 여기서 실패한다
        for item in (d if isinstance(d, list) else [d]):
            types[item['@type']] = item
    assert {'Article', 'FAQPage', 'BreadcrumbList'} <= set(types), '빠진 구조화 데이터: %s' % sorted(types)
    art = types['Article']
    assert art['dateModified'] == meta['updated'] and art['datePublished'] == meta['date']
    assert art['headline'] == meta['title'] and art['description'] == meta['summary']
    qs = [q['name'] for q in types['FAQPage']['mainEntity']]
    assert qs == [f['q'] for f in meta['faq']], 'FAQ 질문이 원고와 다르다'


def test_markdown_subset_renders(tmp_path):
    """제목·목록·인용·링크·굵게·표가 HTML 로 나오고, 원고의 꺾쇠는 이스케이프된다."""
    body = FRONT + '\n### 소제목\n\n- 하나\n- 둘\n\n1. 첫째\n\n> 인용\n\n**굵게** 와 [링크](/faq/) 와 <script>알림</script>\n'
    p = _write(tmp_path, body, slug='md-post')
    meta, md = CM.read(p)
    page, _ = MC.build_page(meta, md, CT.load())
    for frag in ('<h3>소제목</h3>', '<ul><li>하나</li>', '<ol><li>첫째</li>', '<blockquote>',
                 '<b>굵게</b>', '<a href="/faq/">링크</a>'):
        assert frag in page, '%s 가 렌더되지 않았다' % frag
    assert '<script>알림</script>' not in page and '&lt;script&gt;' in page, '원고의 태그가 그대로 나갔다'


def test_section_index_lists_posts_newest_first(tmp_path):
    """섹션 목록이 최신순으로 글을 싣는다."""
    older = FRONT.replace('updated: 2026-10-27', 'updated: 2026-10-21').replace('시험용 글 제목', '오래된 글')
    metas = []
    for body, slug in ((FRONT, 'new-post'), (older, 'old-post')):
        p = _write(tmp_path, body, slug=slug)
        metas.append(CM.read(p)[0])
    newest = sorted(metas, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    page, lm = MC.build_index('city', newest)
    assert lm == max(m['updated'] for m in metas)
    lst = re.search(r'<div class="clist">(.*?)</div></div>', page, re.S)
    assert lst, '목록 묶음을 찾지 못했다'
    titles = re.findall(r'<b>([^<]+)</b>', lst.group(1))
    assert titles[:2] == [newest[0]['title'], newest[1]['title']], '목록이 최신순이 아니다: %s' % titles


# ── ④ 배치·사이트맵·llms ────────────────────────────────────────────────────
def test_both_batches_run_the_generator_and_commit_the_sections():
    """두 배치가 생성기를 부르고 섹션 폴더를 커밋한다 — 구워도 배포되지 않는 일을 막는다.

    무엇을 바꾸면 빨개지나: yml/bat 에서 make_content_pages 줄을 지우거나 TARGETS 에서 섹션을 빼면.
    """
    yml = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    bat = io.open(os.path.join(ROOT, 'tools', 'run_weekly_update.bat'), encoding='utf-8').read()
    assert 'make_content_pages.py' in yml and 'make_content_pages.py' in bat, '배치가 생성기를 부르지 않는다'
    targets = re.search(r'TARGETS="([^"]*)"', yml).group(1).split()
    for sec in CM.SECTIONS:
        assert sec in targets, '클라우드 TARGETS 에 %s 가 없다' % sec
        assert re.search(r'(?<![\w/\\])%s(?![\w\-/\\.])' % sec, bat), '로컬 배치 커밋 목록에 %s 가 없다' % sec


def test_generated_pages_are_in_sitemap_and_llms():
    """**구워진** 글은 sitemap 과 llms.txt 에 들어 있다.

    ⚠️ 기준은 원고가 아니라 페이지다. 원고만 먼저 올라오고 생성기가 아직 안 돈 상태(작성 세션이 .md 를
       커밋한 직후)는 정상이다 — 그걸 빨간불로 만들면 데이터 배치의 pytest 게이트가 막힌다
       (2026-10-27 실제로 그랬다. 저장소 규칙: 생성물 대 원고 정합은 생성기 뒤에서만 본다).
    무엇을 바꾸면 빨개지나: 생성기가 sitemap 에 글을 안 넣거나, llms.txt 가 섹션 목록을 빠뜨리면.
    """
    built = [(sec, slug) for sec, slug, _ in CM.posts(ROOT)
             if os.path.exists(os.path.join(ROOT, sec, slug, 'index.html'))]
    if not built:
        pytest.skip('아직 구워진 콘텐츠 페이지가 없다')
    sm = io.open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read()
    llms = io.open(os.path.join(ROOT, 'llms.txt'), encoding='utf-8').read()
    for sec, slug in built:
        assert '/%s/%s/' % (sec, slug) in sm, '%s/%s 가 sitemap 에 없다' % (sec, slug)
    for sec, slug in built[:10]:
        assert '/%s/%s/' % (sec, slug) in llms, '%s/%s 가 llms.txt 에 없다' % (sec, slug)


# ── ⑤ 홈 묶음·robots·수정일 (요청 2) ────────────────────────────────────────
def test_home_recent_block_is_scoped_to_its_markers(tmp_path):
    """홈 '최근 리포트'는 표식 구간 안만 바꾼다 — 홈은 손으로 관리하고 여러 세션이 같이 고치는 파일이다.

    무엇을 바꾸면 빨개지나: write_home_recent 가 표식 밖을 건드리거나(구간 밖 비교), 표식이 index.html 에서
    사라지면. 픽스처: 저장소 홈을 복사해 표식만 비운 판.
    """
    src = io.open(os.path.join(ROOT, HS.HOME), encoding='utf-8', newline='').read()
    assert src.count(MC.HOME_START) == 1 and src.count(MC.HOME_END) == 1, 'index.html 에 표식 쌍이 하나가 아니다'
    home = tmp_path / 'index.html'
    empty = re.sub(re.escape(MC.HOME_START) + r'.*?' + re.escape(MC.HOME_END),
                   MC.HOME_START + MC.HOME_END, src, flags=re.S)
    home.write_text(empty, encoding='utf-8', newline='')
    meta = CM.read(_write(tmp_path))[0]
    assert MC.write_home_recent([meta], root=str(tmp_path)) is True
    got = io.open(str(home), encoding='utf-8', newline='').read()   # 줄바꿈 변환 없이 — 구간 밖 비교가 흔들리지 않게
    assert '/city/%s/' % meta['slug'] in got and meta['title'] in got, '최근 리포트에 글이 없다'
    outside_before = re.sub(re.escape(MC.HOME_START) + r'.*?' + re.escape(MC.HOME_END), '@', empty, flags=re.S)
    outside_after = re.sub(re.escape(MC.HOME_START) + r'.*?' + re.escape(MC.HOME_END), '@', got, flags=re.S)
    assert outside_before == outside_after, '표식 밖을 바꿨다'


def test_robots_names_the_ai_crawlers_and_stays_open():
    """robots.txt 가 AI 검색·검색엔진 크롤러를 이름으로 허용하고, 전체 허용과 사이트맵 줄을 지킨다.

    무엇을 바꾸면 빨개지나: 크롤러 줄을 지우거나 Disallow 로 바꾸면(대표 결정 없이 막는 것을 막는다).
    """
    r = io.open(os.path.join(ROOT, 'robots.txt'), encoding='utf-8').read()
    assert re.search(r'User-agent:\s*\*\s*\nAllow:\s*/', r), '전체 허용 줄이 없다'
    for bot in ('GPTBot', 'ChatGPT-User', 'OAI-SearchBot', 'PerplexityBot', 'ClaudeBot',
                'Google-Extended', 'Googlebot', 'Bingbot', 'Yeti'):
        m = re.search(r'User-agent:\s*%s\s*\n(Allow|Disallow):\s*(\S+)' % re.escape(bot), r)
        assert m, '%s 줄이 없다' % bot
        assert m.group(1) == 'Allow' and m.group(2) == '/', '%s 를 막고 있다(대표 결정 사항)' % bot
    assert 'Disallow: /' not in r, '전체 차단 줄이 들어왔다'
    assert re.search(r'^Sitemap:\s*https://\S+/sitemap\.xml$', r, re.M), '사이트맵 줄이 없다'


def test_home_and_zone_show_the_modified_date_on_screen_and_in_json_ld():
    """홈·시도 리포트가 수정일을 화면과 JSON-LD 에 **같은 값**으로 싣는다(요청 2.4).

    무엇을 바꾸면 빨개지나: 화면 줄만 지우거나, 두 곳이 다른 날짜를 쓰게 되면.
    픽스처: 저장소에 구워져 있는 실제 홈과 시도 리포트 한 장.
    """
    home = io.open(os.path.join(ROOT, HS.HOME), encoding='utf-8').read()
    m = re.search(r'<p class="hsum-u">페이지 수정 (\d{4}-\d{2}-\d{2})</p>', home)
    assert m, '홈 화면에 페이지 수정일이 없다'
    ld = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', home, re.S)]
    mods = {x.get('dateModified') for d in ld for x in (d if isinstance(d, list) else [d]) if x.get('dateModified')}
    assert m.group(1) in mods, '홈 화면 수정일(%s)이 JSON-LD(%s)와 다르다' % (m.group(1), sorted(mods))

    import sido_zones as SZ
    z = [x for x in SZ.ORDER if os.path.exists(os.path.join(ROOT, 'zone', x, 'index.html'))][0]
    page = io.open(os.path.join(ROOT, 'zone', z, 'index.html'), encoding='utf-8').read()
    mz = re.search(r'페이지 수정 (\d{4}-\d{2}-\d{2})', page)
    assert mz, '%s 리포트 화면에 페이지 수정일이 없다' % z
    art = [x for b in re.findall(r'<script type="application/ld\+json">(.*?)</script>', page, re.S)
           for x in (lambda d: d if isinstance(d, list) else [d])(json.loads(b)) if x.get('@type') == 'Article']
    assert art and art[0]['dateModified'] == mz.group(1), '%s 화면 수정일이 JSON-LD 와 다르다' % z
