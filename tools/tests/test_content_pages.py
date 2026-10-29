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
    """섹션 목록이 최신순이고, 맨 위에 카테고리 칩이 있으며, 글마다 썸네일을 단다(대표 결정 10-29).

    무엇을 바꾸면 빨개지나: 정렬을 뒤집거나, 칩을 빼거나(섹션 사이를 못 건너뛴다), 목록 부품에서
    썸네일을 떼면. 빵부스러기는 '아공맵 › 콘텐츠 › <섹션>' 이어야 한다.
    픽스처: 갱신일이 다른 글 셋.
    """
    metas = [{'section': 'city', 'slug': 'a', 'title': 'A', 'summary': '가' * 50,
              'date': '2026-10-01', 'updated': '2026-10-03'},
             {'section': 'city', 'slug': 'b', 'title': 'B', 'summary': '나' * 50,
              'date': '2026-10-02', 'updated': '2026-10-05'},
             {'section': 'city', 'slug': 'c', 'title': 'C', 'summary': '다' * 50,
              'date': '2026-10-03', 'updated': '2026-10-04'}]
    order = sorted(metas, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    page, lastmod = MC.build_index('city', order)
    slugs = re.findall(r'<a class="pcard[^"]*" href="/city/([^/]+)/"', page)
    assert slugs == [m['slug'] for m in order], '최신순이 아니다: %s' % slugs
    assert lastmod == '2026-10-05'
    assert 'class="rchips"' in page and 'href="/%s/"' % MC.REPORTS_DIR in page, '카테고리 칩이 없다'
    assert '› <a href="/%s/">콘텐츠</a> ›' % MC.REPORTS_DIR in page, '빵부스러기에 콘텐츠가 없다'


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
    CCBot(학습 말뭉치)도 목록에 있다 — 2026-10-27 대표가 전부 허용으로 결정했다.
    """
    r = io.open(os.path.join(ROOT, 'robots.txt'), encoding='utf-8').read()
    assert re.search(r'User-agent:\s*\*\s*\nAllow:\s*/', r), '전체 허용 줄이 없다'
    for bot in ('GPTBot', 'ChatGPT-User', 'OAI-SearchBot', 'PerplexityBot', 'ClaudeBot',
                'Google-Extended', 'CCBot', 'Googlebot', 'Bingbot', 'Yeti', 'Daum'):
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


def _posts_with_front_placeholder():
    """요약·FAQ 에 자리표를 쓰는 실제 원고 [(섹션, slug, meta)]."""
    out = []
    for sec, slug, path in CM.posts(ROOT):
        try:
            meta, _ = CM.read(path, sec, slug)
        except CM.ContentError:
            continue
        glued = (meta.get('summary') or '') + ' '.join(
            (f.get('q') or '') + (f.get('a') or '') for f in (meta.get('faq') or []))
        if CT.PH.search(glued):
            out.append((sec, slug, meta))
    return out


def test_front_matter_placeholders_are_filled_in_feed_and_llms():
    """요약·FAQ 의 자리표는 페이지뿐 아니라 feed·llms 에서도 채워진다.

    무엇을 바꾸면 빨개지나: make_feed.content_items 나 make_llms_txt.content_posts 에서 CT.fill_meta 를
    빼면. 2026-10-27 실제로 빠져 있어서 '{{v:moveins:…}}' 가 feed 19건·llms 9건에 그대로 실려 나갔다
    (구운 페이지에도 OG·JSON-LD·FAQ 까지 7곳씩 남았다).
    픽스처: 저장소의 실제 원고. 요약·FAQ 에 자리표를 쓰는 글이 없으면 검사할 것이 없으니 건너뛴다.
    """
    if not _posts_with_front_placeholder():
        pytest.skip('요약·FAQ 에 자리표를 쓰는 원고가 없다')
    import make_feed as MF
    import make_llms_txt as ML
    for it in MF.content_items():
        assert not CT.PH.search(it['title'] + it['desc']), 'feed 에 자리표가 남았다: %s' % it['guid']
    for sec, meta, body in ML.content_posts(ROOT):
        glued = meta['title'] + meta['summary'] + body
        assert not CT.PH.search(glued), 'llms 에 자리표가 남았다: %s/%s' % (sec, meta['slug'])


def test_published_files_carry_no_placeholder():
    """발행된 파일에 자리표가 하나도 남지 않는다 — 구운 콘텐츠 페이지·feed·llms 전부.

    무엇을 바꾸면 빨개지나: 자리표가 남은 산출물을 커밋하면. 위 시험이 생성기를 보는 것과 달리 이쪽은
    **저장소에 실제로 들어 있는 파일**을 본다(생성기를 고치고 다시 굽는 일을 잊은 회차를 잡는다).
    픽스처: 저장소의 구워진 파일. 아직 구운 글이 없으면 검사할 것이 없으니 건너뛴다.
    """
    files = [os.path.join(ROOT, sec, slug, 'index.html') for sec, slug, _ in CM.built(ROOT)]
    files += [os.path.join(ROOT, f) for f in ('feed.xml', 'llms.txt', 'llms-full.txt')]
    files = [f for f in files if os.path.exists(f)]
    if not files:
        pytest.skip('구워진 콘텐츠가 없다')
    for f in files:
        got = CT.PH.findall(io.open(f, encoding='utf-8').read())
        assert not got, '%s 에 자리표가 남았다: %s' % (os.path.relpath(f, ROOT), got[:3])


def test_inline_placeholder_rejects_a_table():
    """한 줄 글에 표 자리표를 쓰면 거부한다 — 요약 한가운데 표가 끼어드는 꼴을 막는다.

    무엇을 바꾸면 빨개지나: CT.fill_inline 이 table 자리표를 그냥 채우게 되면.
    """
    data = CT.load()
    with pytest.raises(CT.TableError):
        CT.fill_inline('요약 {{table:moveins:경기}} 끝', data)


def test_city_values_agree_with_the_city_tables():
    """도시 값 자리표(need·pop·peak·share)가 같은 도시의 표와 어긋나지 않는다.

    무엇을 바꾸면 빨개지나: need 가 moveins 표 각주의 적정 입주량과 다른 값을 내면, ratio 가 표의 두 행 비와 어긋나면, peak 가 단지 목록에서
    가장 많은 달이 아닌 달을 가리키면, share 가 moveins 표의 '적정 대비' 칸과 다르면. 값과 표가 한 글 안에
    나란히 실리므로, 둘이 갈리면 읽는 사람이 바로 본다.
    픽스처: tools/data/city_moveins.json 의 실제 도시 전부. 그 파일이 없으면 검사할 것이 없으니 건너뛴다.
    """
    data = CT.load()
    cities = sorted((data.get('cities') or {}).get('cities') or {})
    if not cities:
        pytest.skip('도시 자료가 없다')
    for name in cities:
        f = CT.city(data, name)
        # need: 연도별 표의 각주에 적힌 적정 입주량과 같은 수인가
        _, rows, note = CT.table(data, 'moveins', [name])
        assert CT.value(data, 'need', [name]).replace('세대', '') in note, \
            '%s: need 가 moveins 표 각주와 다르다 (%s / %s)' % (name, CT.value(data, 'need', [name]), note)
        # share: 그 해 행의 '적정 대비' 칸과 같은가
        year = rows[1][0] if len(rows) > 1 else rows[0][0]
        want = dict((r[0], r[2]) for r in rows)[year]
        assert CT.value(data, 'share', [name, year]) == want, \
            '%s %s: share(%s) 가 표의 적정 대비(%s)와 다르다' % (
                name, year, CT.value(data, 'share', [name, year]), want)
        # peak: 단지 목록에서 달마다 더해 가장 많은 달과 같은가
        agg = {}
        for r in f['rows']:
            agg[r['ym']] = agg.get(r['ym'], 0) + r['n']
        ym, n = max(sorted(agg.items()), key=lambda x: x[1])
        # ratio: 두 해 행의 세대 수 비와 같은가(콘텐츠-도시 요청으로 연 자리표)
        ys = [r[0] for r in rows]
        if len(ys) > 1:
            a, b = ys[-1], ys[-2]
            n_a = int(dict((r[0], r[1]) for r in rows)[a].replace(',', ''))
            n_b = int(dict((r[0], r[1]) for r in rows)[b].replace(',', ''))
            if n_b:
                assert CT.value(data, 'ratio', [name, a, b]) == '%d%%' % int(round(n_a / float(n_b) * 100)),                     '%s: ratio(%s÷%s) 가 표의 두 행과 다르다' % (name, a, b)
        got = CT.value(data, 'peak', [name])
        assert got == '%s년 %d월 %s세대' % (ym[:4], int(ym[5:7]), CT.num(n)), \
            '%s: peak(%s) 가 단지 목록의 최다 달(%s %d)과 다르다' % (name, got, ym, n)


def test_ratio_refuses_to_divide_by_a_zero_year():
    """견줄 해의 물량이 0이면 비를 내지 않고 거부한다.

    무엇을 바꾸면 빨개지나: city_ratio 의 0 검사를 지우면(ZeroDivisionError 가 나면서 생성기가 죽고,
    그 글만 건너뛰어지는 대신 메시지 없이 멈춘다).
    픽스처: 입주 예정이 0인 해를 가진 합성 도시 묶음 — 실데이터에는 아직 그런 해가 없어서 이 가드는
    저장소 데이터만으로는 영영 돌지 않는다.
    """
    f = {'by_year': {'2027': 0, '2028': 1200}, 'need': 1000, 'occ_max': '2028-06',
         'pop': 300000, 'pop_prd': '202609', 'rows': []}
    with pytest.raises(CT.TableError):
        CT.city_ratio({}, f, '2028', '2027')
    assert CT.city_ratio({}, f, '2028', '2028') == '100%', '같은 해끼리는 100% 여야 한다'


def test_year_table_splits_by_district_or_by_quarter():
    """그 해 표는 자치구가 있는 시는 구별로, 없는 시는 분기별로 나눈다 — '(구 없음)' 한 줄은 내지 않는다.

    구를 모르는 물량('구 미상')은 실제 구와 함께 실린다 — 합계가 맞아야 하므로 지우지 않는다(화성이 그렇다).
    무엇을 바꾸면 빨개지나: 자치구가 없는 시에 구별 표를 그대로 내면(2026-10-27 라이브에서 의정부 글이
    '(구 없음) 2,809 / 합계 2,809' 두 줄을 싣고 있었다), 구가 있는 시를 분기로 바꾸면, 한 줄짜리 표에 합계를 더하면.
    픽스처: tools/data/city_moveins.json 의 실제 도시들. 둘 중 한 쪽이 없으면 그 단정만 건너뛴다.
    """
    data = CT.load()
    cities = (data.get('cities') or {}).get('cities') or {}
    if not cities:
        pytest.skip('도시 자료가 없다')
    saw_gu = saw_q = False
    for name, f in sorted(cities.items()):
        for year in sorted(f.get('by_year') or {}):
            head, rows, _ = CT.table(data, 'moveins', [name, year])
            labels = [r[0] for r in rows]
            gu_rows = [x for x in labels if x != '합계']
            assert gu_rows != ['구 미상'], '%s %s: 구를 모르는 한 줄만 싣는다 — 분기로 나눠야 한다' % (name, year)
            if head[0] == '분기':
                saw_q = True
                assert all(re.match(r'^\d{4}Q[1-4]$', x) for x in labels if x != '합계'), \
                    '%s %s: 분기 이름이 아니다 — %s' % (name, year, labels)
            else:
                saw_gu = True
                assert head[0] == '지역' and any(x.endswith('구') for x in labels), \
                    '%s %s: 구별 표인데 구 이름이 없다 — %s' % (name, year, labels)
            if len(rows) > 1:
                assert labels[-1] == '합계', '%s %s: 두 줄 이상이면 합계가 있어야 한다' % (name, year)
            else:
                assert labels[-1] != '합계', '%s %s: 한 줄짜리 표에 합계를 더하면 같은 수를 두 번 적는다' % (name, year)
    assert saw_gu and saw_q, '구별·분기별 두 길을 다 밟지 못했다(자료에 한쪽만 있다): 구별 %s · 분기별 %s' % (saw_gu, saw_q)


def test_city_tables_drop_empty_columns_and_say_what_the_list_covers():
    """도시 표가 빈 열을 싣지 않고, 각주가 '어디까지 공개된 목록인지'와 받은 날을 말한다.

    무엇을 바꾸면 빨개지나: 구가 갈리지 않는 도시의 단지 목록에 '구' 열을 그대로 두면(구미 글이 '·' 로만
    찬 열을 싣고 있었다 — 총괄 제보 2026-10-27), 또는 각주를 '2028-06 목록 기준' 으로 되돌리면(읽는 사람이
    '2028년 6월에 만든 목록' 으로 오해한다).
    픽스처: 실제 도시 자료. 구가 갈리는 도시와 갈리지 않는 도시를 둘 다 밟는지 단정한다.
    """
    data = CT.load()
    cities = (data.get('cities') or {}).get('cities') or {}
    if not cities:
        pytest.skip('도시 자료가 없다')
    saw_gu = saw_flat = False
    for name, f in sorted(cities.items()):
        head, rows, note = CT.table(data, 'complexes', [name])
        gus = {(r.get('gu') or '') for r in f['rows']}
        if len(gus) < 2:
            saw_flat = True
            assert '구' not in head, '%s: 구가 갈리지 않는데 구 열을 싣는다 — %s' % (name, head)
            assert len(head) == len(rows[0]), '%s: 머리와 행의 칸 수가 다르다' % name
        else:
            saw_gu = True
            assert '구' in head, '%s: 구가 갈리는데 구 열이 없다 — %s' % (name, head)
        assert '입주분까지 공개된 목록' in note, '%s: 각주가 목록 범위를 말하지 않는다 — %s' % (name, note)
        assert re.search(r'\(\d{4}-\d{2}-\d{2} 조사\)', note), '%s: 각주에 조사일이 없다 — %s' % (name, note)
    assert saw_gu and saw_flat, '구가 갈리는 도시와 갈리지 않는 도시를 둘 다 밟지 못했다'


def test_chart_numbers_come_from_the_data_files():
    """그림의 숫자가 city_moveins.json·data-sgg.json 의 값과 **같은 수**다 — 그림만 옛 숫자를 들고 있지 않게.

    무엇을 바꾸면 빨개지나: chart 가 값을 깎거나 반올림하거나 다른 해를 집으면, 주간 꺾은선이 최신 주가
    아닌 곳에서 끝나면, 대체 텍스트가 그림과 다른 수를 말하면.
    픽스처: 저장소의 실제 자료. 도시 자료가 없으면 검사할 것이 없으니 건너뛴다.
    """
    data = CT.load()
    cities = (data.get('cities') or {}).get('cities') or {}
    if not cities:
        pytest.skip('도시 자료가 없다')
    for name, f in sorted(cities.items()):
        spec = CT.chart(data, 'moveins', [name])
        pts = dict(spec['series'][0]['points'])
        assert pts == {y: v for y, v in f['by_year'].items()}, '%s: 막대가 by_year 와 다르다' % name
        assert spec['rule'][0] == f['need'], '%s: 기준선이 적정 입주량과 다르다' % name
        for y, v in pts.items():
            assert CT.num(v) in spec['alt'], '%s: 대체 텍스트에 %s년 값이 없다' % (name, y)
    # 주간 꺾은선은 그 지역 계열의 마지막 주에서 끝난다(표의 최신 주와 같은 날).
    for name in ('서울', '분당구'):
        spec = CT.chart(data, 'weekly', [name])
        last = [s['points'][-1] for s in spec['series']]
        ser = [(p, v) for p, v in CT._weekly_series(data, name, 'ma') if v is not None]
        assert last[0] == ser[-1], '%s: 꺾은선이 최신 주에서 끝나지 않는다' % name
        assert len(spec['series'][0]['points']) <= CT.CHART_WEEKS, '%s: 26주보다 많다' % name


def test_chart_svg_is_accessible_and_scales():
    """구운 그림이 대체 텍스트를 달고, 색을 박지 않고, 폭에 맞춰 늘어난다.

    무엇을 바꾸면 빨개지나: aria-label 을 빼면(읽는 장치와 AI 가 그림을 못 읽는다), 색을 #rrggbb 로 박으면
    (나중에 다크 모드가 들어와도 그림만 밝은 색으로 남는다), viewBox 를 지우면(좁은 화면에서 잘린다).
    픽스처: 실제 자료로 구운 막대·꺾은선 한 장씩.
    """
    data = CT.load()
    if not ((data.get('cities') or {}).get('cities') or {}):
        pytest.skip('도시 자료가 없다')
    name = sorted((data['cities'])['cities'])[0]
    for kind, args in (('moveins', [name]), ('weekly', ['서울'])):
        spec = CT.chart(data, kind, args)
        svg = MC._chart_html(spec)
        assert 'role="img"' in svg and 'aria-label="' in svg, '%s: 대체 텍스트가 없다' % kind
        assert 'viewBox="0 0 ' in svg, '%s: viewBox 가 없다' % kind
        assert not re.search(r'(fill|stroke)="#', svg), '%s: 색을 박았다 — CSS 변수로 둘 것' % kind
        assert 'preserveAspectRatio' not in svg, '%s: 비율을 깨면 좁은 화면에서 글자가 뭉갠다' % kind
    # CSS 는 SVG 속성을 이긴다 — 맞춤을 속성으로 주면 가운데로 그려져 양 끝 글자가 잘린다(실제로 그랬다).
    assert 'text-anchor="' not in MC._chart_html(CT.chart(data, 'weekly', ['서울'])), \
        '맞춤을 속성으로 주었다 — .cx-s/.cx-e 클래스를 쓸 것'
    # 색은 스타일시트 쪽에도 박으면 안 된다. 마크업만 보면 CSS 에 박은 색을 놓친다.
    hard = re.findall(r'(?:fill|stroke|color|background)\s*:\s*(#[0-9a-fA-F]{3,8})', MC.EXTRA_CSS)
    assert not hard, '콘텐츠 CSS 가 색을 박았다 — var(--…) 로 둘 것: %s' % hard


def test_zone_posts_generator_sorts_posts_by_region(tmp_path):
    """글 묶음을 **만드는 쪽**을 돌려 본다 — 시군구 글이 그 시도로 가고, 남의 시도에는 안 간다(요청 ②).

    무엇을 바꾸면 빨개지나: zone_of 의 매핑을 끊거나(모두 한 시도로 묶는 등), 표식 구간을 못 찾게 하거나,
    글이 없는 시도의 구간을 비우지 않으면. 아래 '발행물' 시험과 달리 이쪽은 생성기를 실제로 돌리므로,
    페이지를 다시 굽지 않은 회차에도 회귀를 잡는다.
    픽스처: 표식만 담은 빈 zone 페이지 셋(서울·경기·경북)과 손으로 만든 글 메타 셋.
    """
    for z in ('서울', '경기', '경북'):
        d = tmp_path / 'zone' / z
        d.mkdir(parents=True)
        (d / 'index.html').write_text('<main>본문</main>%s%s<footer>' % (MC.ZONE_START, MC.ZONE_END),
                                      encoding='utf-8')
    metas = [{'section': 'city', 'slug': 'gumi-x', 'title': '구미 글', 'region': '구미',
              'date': '2026-10-01', 'updated': '2026-10-02'},
             {'section': 'danji', 'slug': 'bucheon-x', 'title': '부천 글', 'region': '부천',
              'date': '2026-10-01', 'updated': '2026-10-03'},
             {'section': 'gtx', 'slug': 'gg-x', 'title': '경기 글', 'region': '경기',
              'date': '2026-10-01', 'updated': '2026-10-04'}]
    assert MC.write_zone_posts(metas, root=str(tmp_path)) == 2, '글이 실린 시도는 경기·경북 둘이어야 한다'
    got = {}
    for z in ('서울', '경기', '경북'):
        s = (tmp_path / 'zone' / z / 'index.html').read_text(encoding='utf-8')
        got[z] = set(re.findall(r'href="(/[^"]+/)"', s))
    assert got['경북'] == {'/city/gumi-x/'}, '구미 글이 경북으로 가지 않았다: %s' % got['경북']
    assert got['경기'] == {'/danji/bucheon-x/', '/gtx/gg-x/'}, '경기 묶음이 다르다: %s' % got['경기']
    assert got['서울'] == set(), '글이 없는 시도에 묶음이 생겼다: %s' % got['서울']
    # 글이 빠지면 그 구간도 비워야 한다 — 지난 회차의 링크가 남으면 없는 글을 가리킨다.
    assert MC.write_zone_posts([], root=str(tmp_path)) == 0
    assert '/city/gumi-x/' not in (tmp_path / 'zone' / '경북' / 'index.html').read_text(encoding='utf-8'), \
        '글을 내렸는데 묶음이 그대로다'


def test_sido_generator_bakes_the_marker():
    """시도 생성기가 글 묶음 표식을 굽는다 — 표식이 없으면 채울 자리가 없다.

    무엇을 바꾸면 빨개지나: make_sido_pages 의 FOOT 에서 표식을 지우면.
    """
    import make_sido_pages as SP
    assert MC.ZONE_START in SP.FOOT and MC.ZONE_END in SP.FOOT, \
        '시도 페이지 바닥글에 글 묶음 표식이 없다'


def test_zone_reports_link_the_posts_about_that_region():
    """발행된 시도 리포트에 그 지역 글 묶음이 실제로 들어 있다(요청 ②).

    무엇을 바꾸면 빨개지나: 생성기를 고치고 페이지를 다시 굽지 않은 채 커밋하면. 위 생성기 시험과 짝이다.
    픽스처: 저장소에 구워져 있는 zone 페이지와 실제 원고.
    """
    import sido_zones as SZ
    posts, _ = MC.collect()
    if not posts:
        pytest.skip('원고가 없다')
    want = {}
    for sec, meta, _ in posts:
        z = MC.zone_of(meta)
        if z and os.path.exists(os.path.join(ROOT, sec, meta['slug'], 'index.html')):
            want.setdefault(z, set()).add('/%s/%s/' % (sec, meta['slug']))
    assert want, '어느 글도 시도에 묶이지 않았다 — region 매핑이 끊겼다'
    seen = 0
    for z in SZ.ORDER:
        p = os.path.join(ROOT, 'zone', z, 'index.html')
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding='utf-8').read()
        m = re.search(re.escape(MC.ZONE_START) + r'(.*?)' + re.escape(MC.ZONE_END), s, re.S)
        assert m, '%s 리포트에 글 묶음 표식이 없다' % z
        hrefs = set(re.findall(r'href="(/(?:city|gtx|danji|column)/[^"]+/)"', m.group(1)))
        assert hrefs == want.get(z, set()), '%s 리포트의 글 묶음이 그 지역 글과 다르다 — 빠짐 %s, 더함 %s' % (
            z, sorted(want.get(z, set()) - hrefs), sorted(hrefs - want.get(z, set())))
        seen += 1
    assert seen >= 10, '시도 리포트를 %d곳밖에 못 읽었다' % seen


def test_og_image_falls_back_in_three_steps(tmp_path):
    """글의 og:image 는 글별 카드 → 섹션 공통 카드 → 브랜드 카드 순으로 떨어진다.

    무엇을 바꾸면 빨개지나: 폴백 한 단계를 지우거나, 카드가 없는데도 그 주소를 가리키게 하면(미리보기가
    깨진 그림으로 뜬다), 판(?v=)을 updated 가 아닌 것으로 바꾸면.
    픽스처: 카드가 둘 다 없는 빈 뿌리, 섹션 카드만 있는 뿌리, 글별 카드까지 있는 뿌리 — 세 상태를 만든다.
    """
    meta = {'section': 'city', 'slug': 'x-2027', 'updated': '2026-10-27'}
    assert MC.og_image(meta, root=str(tmp_path)).endswith('/og-brand.png'), '카드가 없으면 브랜드 카드다'
    (tmp_path / 'share').mkdir()
    (tmp_path / MC.section_card_rel('city')).write_bytes(b'x')
    got = MC.og_image(meta, root=str(tmp_path))
    assert got.endswith('/share/section-city.png?v=2026-10-27'), '섹션 카드로 떨어지지 않는다: %s' % got
    (tmp_path / MC.card_rel('city', 'x-2027')).write_bytes(b'x')
    got = MC.og_image(meta, root=str(tmp_path))
    assert got.endswith('/share/post-city-x-2027.png?v=2026-10-27'), '글별 카드를 쓰지 않는다: %s' % got


def test_baked_pages_point_at_a_card_that_exists():
    """구운 글의 og:image 가 **저장소에 있는** 파일을 가리킨다.

    무엇을 바꾸면 빨개지나: 카드를 지우고 페이지를 다시 굽지 않거나, 카드 경로 규칙을 한쪽만 고치면.
    픽스처: 저장소에 구워져 있는 글 페이지 전부.
    """
    import urllib.parse
    built = CM.built(ROOT)
    if not built:
        pytest.skip('구워진 글이 없다')
    for sec, slug, _ in built:
        page = io.open(os.path.join(ROOT, sec, slug, 'index.html'), encoding='utf-8').read()
        m = re.search(r'<meta property="og:image" content="([^"]+)"', page)
        assert m, '%s/%s: og:image 가 없다' % (sec, slug)
        rel = urllib.parse.unquote(m.group(1).split('?')[0].split('/', 3)[-1])
        assert os.path.exists(os.path.join(ROOT, rel)), '%s/%s: 없는 카드를 가리킨다 — %s' % (sec, slug, rel)


def test_card_text_matches_the_manuscript_title():
    """커밋된 카드에 그려진 글자가 지금 원고의 제목과 같다(그림은 못 읽으므로 PNG 글 칸을 읽는다).

    무엇을 바꾸면 빨개지나: 제목을 고치고 카드를 다시 굽지 않으면. 지역 카드(test_zone_cards)와 같은 방법이다.
    픽스처: 저장소의 카드 파일과 원고. 카드가 아직 없는 글은 섹션 공통 카드로 떨어지므로 건너뛴다.
    """

    data = CT.load()
    seen = 0
    for sec, slug, path in CM.posts(ROOT):
        p = os.path.join(ROOT, MC.card_rel(sec, slug))
        if not os.path.exists(p):
            continue
        meta, _ = CM.read(path, sec, slug)
        want = CT.fill_inline(meta['title'], data)
        from PIL import Image
        # 글 칸은 iTXt 로 저장된다(한글이라 UTF-8). 직접 청크를 훑으면 tEXt 만 보다 놓친다.
        got = dict(Image.open(p).text)
        assert got.get('title') == want, '%s/%s: 카드 글자(%r)가 원고 제목(%r)과 다르다' % (
            sec, slug, got.get('title'), want)
        seen += 1
    assert seen >= 1, '카드가 하나도 없다 — make_content_cards 를 돌릴 것'


def test_sido_share_uses_the_zone_reference_not_the_city_formula():
    """시도의 need·share 는 기준표(sido_zones)에서 나오고, 그 해 입주물량 표와 맞는다(총괄 요청 10-29).

    무엇을 바꾸면 빨개지나: 분기 적정물량에 4를 곱하는 자리를 고치거나(한 해가 아닌 수가 된다), share 의
    분자를 그 해 입주물량 표가 아닌 값으로 바꾸거나, 도시 산식(인구 ÷ 2.5 × 2%)을 시도에 쓰면.
    픽스처: 저장소의 실제 시도 자료. 도시와 산식이 다르다는 것도 함께 단정한다 — 두 수가 같아지면
    어느 한쪽이 상대의 산식을 쓰고 있다는 뜻이다.
    """
    import sido_zones as SZ
    data = CT.load()
    zones = CT._zones(data)
    seen = 0
    for key in SZ.ORDER:
        z = zones.get(key)
        if not z or not z.get('ref'):
            continue
        want = CT.num(int(round(z['ref'] * 4))) + '호'
        assert CT.value(data, 'need', [key]) == want, '%s: need 가 기준표(ref×4)와 다르다' % key
        head, rows, _ = CT.moveins(data, key)
        by = {r[0]: r[1] for r in rows if r[0] != '합계'}
        year = sorted(by)[-2] if len(by) > 1 else sorted(by)[-1]
        v = int(by[year].replace(',', ''))
        got = CT.value(data, 'share', [key, year])
        assert got == '%d%%' % int(round(v / float(z['ref'] * 4) * 100)), \
            '%s %s: share 가 입주물량 표와 어긋난다 — %s' % (key, year, got)
        seen += 1
    assert seen >= 10, '시도를 %d곳밖에 못 봤다' % seen
    # 도시 전용 자리표는 시도에서 거부한다(인구·단지 목록은 도시 자료에만 있다).
    for kind in ('pop', 'peak'):
        with pytest.raises(CT.TableError):
            CT.value(data, kind, ['서울'])
    # 산식이 다르다 — 도시 need 는 '세대', 시도 need 는 '호'로 끝난다.
    cities = (data.get('cities') or {}).get('cities') or {}
    if cities:
        one = sorted(cities)[0]
        assert CT.value(data, 'need', [one]).endswith('세대'), '도시 need 의 단위가 바뀌었다'
        assert CT.value(data, 'need', ['서울']).endswith('호'), '시도 need 의 단위가 바뀌었다'


def test_hub_shows_six_category_cards_and_recent_posts():
    """허브 첫 화면이 카테고리 카드 6장이고, 그 아래 '최근 글' 이 최신순 %d편이다(대표 결정 10-29).

    무엇을 바꾸면 빨개지나: 카드를 빼거나 순서를 바꾸거나(발행 주기 순이다), 카드의 글 수가 실제와
    어긋나거나, 최근 글이 최신순이 아니거나 편수가 넘치면.
    픽스처: 저장소에 구워져 있는 /reports/ 와 실제 원고.
    """ % MC.RECENT_N
    p = os.path.join(ROOT, MC.REPORTS_DIR, 'index.html')
    if not os.path.exists(p):
        pytest.skip('/reports/ 가 아직 없다')
    page = io.open(p, encoding='utf-8').read()
    hrefs = re.findall(r'<a class="hcard" href="([^"]+)"', page)
    # 기대 순서를 **여기 적는다**. HUB_CARDS 에서 만들면 상수를 바꿀 때 기대값도 같이 바뀌어
    # 아무것도 지키지 못한다(2026-10-29 변이로 확인). 이 순서는 대표가 정한 발행 주기 순이다.
    want = ['/column/', '/weekly/', '/city/', '/gtx/', '/danji/', '/zone/']
    assert hrefs == want, '카드 순서·링크가 다르다(발행 주기 순이어야 한다): %s' % hrefs
    cads = re.findall(r'<a class="hcard"[^>]*>.*?<em>([^<]+)</em>', page, re.S)
    assert cads == ['당일', '매주', '연재', '연재', '연재', '분기'], '발행 주기 표시가 다르다: %s' % cads
    # 섹션 카드의 글 수는 실제 구워진 글과 같아야 한다.
    built = {}
    for sec, slug, _ in CM.built(ROOT):
        built[sec] = built.get(sec, 0) + 1
    for key, name, _d, _c in MC.HUB_CARDS:
        if key.startswith('/'):
            continue
        m = re.search(r'<a class="hcard" href="/%s/".*?<div class="hc-m">([^<]*)</div>' % key, page, re.S)
        assert m, '%s 카드를 못 찾았다' % key
        n = built.get(key, 0)
        assert ('글 %d편' % n) in m.group(1) or (n == 0 and '준비' in m.group(1)), \
            '%s 카드의 글 수(%s)가 실제(%d편)와 다르다' % (key, m.group(1), n)
    # 최근 글 — 편수와 정렬.
    # 최근 글 — 구워진 주소를 뽑아 **원고의 갱신일**과 맞댄다. 페이지에서 날짜를 긁으면 정규식이
    # 어긋났을 때 빈 목록이 되어 '정렬이 맞다' 로 통과한다(2026-10-29 변이로 확인).
    links = re.findall(r'<a class="pcard[^"]*" href="/([^/]+)/([^/]+)/"', page.split('최근 글')[1])
    assert 0 < len(links) <= MC.RECENT_N, '최근 글이 %d편이다' % len(links)
    upd = {}
    for sec, slug, path in CM.built(ROOT):
        meta, _ = CM.read(path, sec, slug)
        upd[(sec, slug)] = (meta['updated'], meta['date'], slug)
    keys = [upd[(s, g)] for s, g in links if (s, g) in upd]
    assert len(keys) == len(links), '목록에 자료에 없는 글이 있다'
    assert keys == sorted(keys, reverse=True), '최근 글이 최신순이 아니다: %s' % [k[0] for k in keys]
    assert keys[0] == max(upd.values()), '가장 최신 글이 맨 위가 아니다'


def test_every_listed_post_has_a_real_thumbnail():
    """목록의 글마다 썸네일 주소가 **실재하는 파일**을 가리키고, 공통 카드로 떨어진 글이 없다(요청 ⑤).

    무엇을 바꾸면 빨개지나: 썸네일을 굽지 않고 목록만 고치거나, 카드 생성이 조용히 실패해 그 글이
    섹션 공통 카드로 떨어지면(2026-10-29 fontTools 가 없어 그런 일이 있었다).
    픽스처: 저장소의 허브·섹션 목록·홈과 share/ 의 그림들.

    ⚠️ 이 시험은 **발행을 멈춘다**(배치·발행 게이트가 pytest 전체다). 그래서 카드를 굽는 단계는 게이트
       앞에 와야 한다 — 뒤에 두었더니 새 글이 올라온 회차마다 아직 없는 카드를 보고 빨개져 발행이
       세 런 연속 멈췄다(2026-10-29). 순서는 test_publish_workflow_runs_on_content_and_gates_before_commit 이 지킨다.
    """
    import urllib.parse
    pages = [os.path.join(ROOT, MC.REPORTS_DIR, 'index.html'), os.path.join(ROOT, HS.HOME)]
    pages += [os.path.join(ROOT, s, 'index.html') for s in CM.SECTIONS
              if os.path.exists(os.path.join(ROOT, s, 'index.html'))]
    seen = 0
    for p in pages:
        if not os.path.exists(p):
            continue
        page = io.open(p, encoding='utf-8').read()
        for src in re.findall(r'<img src="(/share/thumb-[^"]+)"', page):
            rel = urllib.parse.unquote(src.split('?')[0].lstrip('/'))
            assert os.path.exists(os.path.join(ROOT, rel)), '%s: 없는 썸네일 %s' % (os.path.basename(p), rel)
            seen += 1
    assert seen >= 5, '썸네일을 %d개밖에 못 봤다' % seen
    # '모든 글이 제 카드를 가진다'는 게이트가 보지 않는다. 카드는 발행·배치 모두 게이트 **뒤**에서 굽기 때문에, 새 글이
    # 올라온 회차의 게이트에는 그 글 카드가 아직 없다(2026-10-30 단지 6·7편 발행이 이 단정에 막혔고, 그 상태로는 매일
    # 배치 게이트도 데이터 커밋을 막는다). 카드가 빠진 글은 batch_notes.content_card_lines 가 ℹ️ 줄로 알린다.


def test_missing_post_cards_are_a_batch_note_not_a_gate(tmp_path):
    """제 카드·썸네일이 없는 구워진 글은 배치 기록 ℹ️ 줄이다 — 게이트가 아니다.

    무엇을 바꾸면 빨개지나: content_card_lines 가 카드만 보고 썸네일을 안 보거나(둘째 단정), 구워지지 않은 원고까지
    세거나(셋째 단정), 다 갖춘 글에도 줄을 쓰면(넷째 단정). 실제로 각각 깨뜨려 확인했다.
    픽스처: 원고 둘이 구워진 임시 저장소 — 하나는 카드·썸네일이 다 있고, 하나는 썸네일만 없다(단지 7편처럼 카드
    단계가 아직 돌지 않은 상태), 그리고 페이지가 아직 없는 원고 하나.
    """
    import batch_notes as BN
    root = tmp_path
    for sec, slug, page in (('danji', 'a', True), ('danji', 'b', True), ('danji', 'c', False)):
        d = root / 'content' / sec
        d.mkdir(parents=True, exist_ok=True)
        (d / (slug + '.md')).write_text('x', encoding='utf-8')
        if page:
            (root / sec / slug).mkdir(parents=True)
            (root / sec / slug / 'index.html').write_text('<html></html>', encoding='utf-8')
    (root / 'share').mkdir()
    for rel in (MC.card_rel('danji', 'a'), MC.thumb_rel('danji', 'a'), MC.card_rel('danji', 'b')):
        (root / rel).write_bytes(b'x')
    got = BN.content_card_lines(str(root))
    assert len(got) == 1 and got[0].startswith('ℹ️'), got
    assert 'danji/b' in got[0] and 'danji/a' not in got[0]
    assert 'danji/c' not in got[0]
    for rel in (MC.thumb_rel('danji', 'b'),):
        (root / rel).write_bytes(b'x')
    assert BN.content_card_lines(str(root)) == []


def test_content_has_an_entrance_in_tab_footer_and_home():
    """콘텐츠 글로 가는 입구가 탭·푸터·홈 세 곳에 있다(대표 요청 10-29 '네비에 메뉴 하나 추가되는거야?').

    무엇을 바꾸면 빨개지나: 탭에서 콘텐츠를 빼거나, 푸터의 섹션 링크를 지우거나, 홈 묶음의 '전체 보기'를
    없애면. 글이 늘어도 입구가 그대로인지는 위 시험이 본다.
    픽스처: 저장소의 탭바 정본과 구워진 홈.
    """
    import site_nav as N
    assert ('reports', '/%s/' % MC.REPORTS_DIR, '콘텐츠') in [(i, h, l) for i, h, l, _ in N.TABS], \
        '탭 정본에 콘텐츠가 없다: %s' % [(i, l) for i, _, l, _ in N.TABS]
    home = io.open(os.path.join(ROOT, HS.HOME), encoding='utf-8').read()
    assert 'href="/%s/"' % MC.REPORTS_DIR in home, '홈에 /reports/ 링크가 없다'
    assert '콘텐츠 전체 보기' in home, "홈 묶음에 '전체 보기' 가 없다"
    # 푸터는 세 벌(홈·통계·퀴즈)이다 — 한 벌에만 넣으면 어떤 화면에서는 입구가 없다.
    foots = re.findall(r'<nav class="ft-nav ft-grp".*?</nav>', home, re.S)
    assert len(foots) == 3, '홈 푸터가 %d벌이다' % len(foots)
    for i, f in enumerate(foots):
        for href in ('/reports/', '/city/', '/gtx/', '/danji/', '/column/'):
            assert 'href="%s"' % href in f, '%d번째 푸터에 %s 링크가 없다' % (i + 1, href)


def test_content_pages_light_their_own_tab():
    """콘텐츠 페이지는 '콘텐츠' 탭을 켠다 — 뼈대가 켜 두는 '시세' 를 그대로 두지 않는다.

    무엇을 바꾸면 빨개지나: _own_tab 을 빼면(모든 글에서 '시세' 탭이 켜진 채로 나간다).
    픽스처: 구워진 /reports/·섹션 목록·글 한 편.
    """
    import site_nav as N
    # 먼저 생성기를 직접 밟는다 — 구워진 페이지만 보면 생성기를 고치고 다시 굽기 전까지 초록이다.
    assert MC._own_tab(N.bottomnav('stats')) == N.bottomnav('reports'), '_own_tab 이 탭을 바꾸지 않는다'
    rel = [os.path.join(MC.REPORTS_DIR, 'index.html')]
    rel += [os.path.join(sec, 'index.html') for sec in CM.SECTIONS
            if os.path.exists(os.path.join(ROOT, sec, 'index.html'))]
    rel += [os.path.join(sec, slug, 'index.html') for sec, slug, _ in CM.built(ROOT)[:3]]
    seen = 0
    for r in rel:
        p = os.path.join(ROOT, r)
        if not os.path.exists(p):
            continue
        page = io.open(p, encoding='utf-8').read()
        on = re.search(r'class="nav-btn on"[^>]*href="([^"]+)"', page)
        assert on and on.group(1) == N.HREF['reports'], '%s: 켜진 탭이 %s 다' % (r, on and on.group(1))
        seen += 1
    assert seen >= 2, '검사한 페이지가 %d개뿐이다' % seen


def test_quotes_in_a_title_do_not_break_the_meta_attributes():
    """제목·요약의 큰따옴표가 <title>·og 속성을 끊지 않는다(반박 글은 발언을 그대로 옮긴다).

    무엇을 바꾸면 빨개지나: build_page 가 meta 값을 이스케이프하지 않으면. 2026-10-29 그 상태로 구운
    column 글이 게이트(test_no_glued_attributes)에 걸려 네 편이 발행되지 못했다.
    픽스처: 제목과 요약에 큰따옴표가 든 글 하나를 손으로 만들어 굽는다.
    """
    data = CT.load()
    meta = {'section': 'column', 'slug': 'quote-x', 'title': '그가 "급락" 이라 말했다',
            'summary': '"급락" 이라는 말이 무엇을 뜻하는지 입주 물량으로 따져 봅니다. 숫자는 국가 통계에서 옵니다.',
            'date': '2026-10-29', 'updated': '2026-10-29'}
    page, _ = MC.build_page(meta, '본문입니다.', data)
    for prop in ('og:title', 'og:description'):
        m = re.search(r'<meta property="%s" content="([^"]*)"\s*/?>' % prop, page)
        assert m, '%s 를 못 찾았다(속성이 끊겼을 수 있다)' % prop
        assert '"' not in m.group(1), '%s 안에 날것의 큰따옴표가 있다' % prop
    m = re.search(r'<title>([^<]*)</title>', page)
    assert m and '"' not in m.group(1), '<title> 에 날것의 큰따옴표가 있다'


def test_publish_commits_everything_the_generator_touches():
    """발행 워크플로의 커밋 대상이 콘텐츠 생성기가 고치는 곳을 모두 덮는다.

    무엇을 바꾸면 빨개지나: zone(지역 묶음)·share(글 카드) 같은 경로를 TARGETS 에서 빼면. 생성기가 고친
    파일이 대상 밖에 남으면 pull --rebase 가 "You have unstaged changes" 로 거부해 **그 회차 발행이 통째로
    사라진다**(2026-10-29 반박 4편). 되돌리는 안전장치도 함께 있어야 한다.
    픽스처: 저장소의 발행 워크플로.
    """
    t = io.open(os.path.join(ROOT, '.github', 'workflows', 'publish-content.yml'), encoding='utf-8').read()
    m = re.search(r'^\s*TARGETS="([^"]+)"', t, re.M)
    assert m, '커밋 대상을 읽지 못했다'
    targets = set(m.group(1).split())
    must = set(CM.SECTIONS) | {MC.REPORTS_DIR, 'zone', 'share', HS.HOME,   # 홈(최근 리포트 표식)
                               'feed.xml', 'llms.txt', 'llms-full.txt', 'sitemap.xml'}
    assert must <= targets, '발행이 생성기 산출물을 빠뜨린다: %s' % sorted(must - targets)
    assert 'git checkout -- .' in t, '커밋 대상 밖 변경을 되돌리는 안전장치가 없다'
    assert 'fonttools' in t, '카드 글꼴 검사에 쓰는 fonttools 를 깔지 않는다'


def test_a_city_not_collected_yet_is_a_wait_not_an_error(tmp_path):
    """자료에 아직 없는 **실재 시군구**는 오류가 아니라 '기다림'이다 — 그래야 원고를 올릴 수 있다.

    순환이 있었다: 수집기는 content/ 원고의 region 에서 도시를 읽는데, 원고는 그 도시 자리표가 검사에서
    실패해 올릴 수 없었다(2026-10-29 군포, 단지 4편). 이름표로 시도를 찾을 수 있으면 오타가 아니므로
    검사는 경고로 넘기고(종료 코드 0) 생성기는 그 글만 건너뛴다.
    무엇을 바꾸면 빨개지나: PendingCity 를 다시 TableError 로 되돌리거나, 모르는 이름까지 기다림으로
    넘기면(오타가 통과한다), 검사기가 기다림을 고칠 곳으로 세면.
    픽스처: 도시 자료에 없는 실재 시군구(군포)와 아예 없는 이름을 각각 자리표로 쓴다.
    """
    import make_city_moveins as MCM
    # 기다림은 TableError 의 하위여야 한다 — 생성기는 그것으로 '그 글만 건너뛰기' 를 한다.
    # 밖으로 빼면 배치가 그 글에서 죽는다(한 편 때문에 그날 발행 전체가 멈춘다).
    assert issubclass(CT.PendingCity, CT.TableError), 'PendingCity 가 TableError 의 하위가 아니다'
    data = CT.load()
    have = set((data.get('cities') or {}).get('cities') or {})
    pend = next((n for n in ('군포', '시흥', '광명', '구리') if n not in have and MCM.sido_of(n)), None)
    if not pend:
        pytest.skip('자료에 없는 실재 시군구를 찾지 못했다')
    for kind, args in (('moveins', [pend, '2027']), ('share', [pend, '2027']), ('need', [pend])):
        with pytest.raises(CT.PendingCity):
            CT.value(data, kind, args)
    # 모르는 이름은 그대로 오류다 — 오타를 통과시키지 않는다.
    with pytest.raises(CT.TableError) as e:
        CT.value(data, 'moveins', ['없는동네', '2027'])
    assert not isinstance(e.value, CT.PendingCity), '모르는 이름을 기다림으로 넘겼다'
    # 검사기는 그 글을 '고칠 곳'으로 세지 않는다(종료 코드 0).
    import content_check as CC
    d = tmp_path / 'content' / 'danji'
    d.mkdir(parents=True)
    (d / 'wait-x.md').write_text(
        '---\ntitle: "%s 모의 글"\n'
        'summary: "%s 의 사업 단계와 대지지분을 공급 데이터와 함께 봅니다. 숫자는 국가 통계에서 옵니다."\n'
        'date: "2026-10-29"\nupdated: "2026-10-29"\nsection: "danji"\nregion: "%s"\n---\n\n'
        '입주 물량은 {{v:moveins:%s:2027}} 입니다.\n' % (pend, pend, pend, pend), encoding='utf-8')
    problems, waits, _ = CC.check_post(str(d / 'wait-x.md'), data, root=str(tmp_path))
    assert not problems and len(waits) == 1, '기다림이 고칠 곳으로 잡혔다: %s' % (problems,)


def test_list_css_is_one_canon_in_both_places():
    """목록 부품 스타일이 app.css 와 생성기에서 같은 글자다 — 한쪽만 고치면 홈과 콘텐츠가 달라진다.

    콘텐츠 페이지는 app.css 를 링크하지 않고 뼈대의 인라인 style 을 쓰고, 홈은 app.css 를 읽는다.
    그래서 같은 글자가 두 곳에 있어야 한다(site_nav.NAV_FOCUS_CSS 와 같은 방식).
    무엇을 바꾸면 빨개지나: 둘 중 하나만 고치거나 app.css 의 표식 구간을 지우면.
    """
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    m = re.search(r'/\*LIST_CSS_START\*/(.*?)/\*LIST_CSS_END\*/', css, re.S)
    assert m, 'app.css 에 LIST_CSS 표식 구간이 없다'
    norm = lambda s: re.sub(r'^\s+', '', s.strip(), flags=re.M).replace('\r\n', '\n')
    assert norm(m.group(1)) == norm(MC.LIST_CSS), 'app.css 의 목록 부품이 생성기 정본과 다르다'
    assert '.pcard' in MC.EXTRA_CSS, '콘텐츠 페이지가 목록 부품을 싣지 않는다'


def test_collector_reads_every_city_placeholder_kind():
    """수집기가 **도시 자료가 필요한 모든 자리표 종류**에서 도시를 읽는다(table·v·chart 세 접두 다).

    무엇을 바꾸면 빨개지나: CITY_KINDS 에서 종류를 빼거나, 수집기가 그 목록을 쓰지 않고 제 목록을 들면.
    2026-10-29 chart·need 가 빠져 있었다 — 그 둘만 쓰는 글의 도시는 영영 수집되지 않는다(율곡 원고가
    moveins 도 써서 가려져 있었고, 단지 세션이 묻지 않았으면 몰랐다).
    주간 계열(streak·weekly)은 일부러 뺀다: 도시 자료가 필요 없고 인자가 '부천 소사구' 같은 구 이름이라
    수집 대상에 넣으면 시도를 못 찾는 경고만 쏟아진다.
    픽스처: 종류마다 자리표 한 줄씩을 지어 넣는다.
    """
    import make_city_moveins as MCM
    # 기대 종류를 **여기 적는다**. CT.CITY_KINDS 로 돌면 목록을 줄일 때 시험도 같이 줄어 아무것도
    # 지키지 못한다(2026-10-30 변이로 확인 — 허브 카드 순서에서 똑같은 실수를 했다).
    want = ('moveins', 'share', 'complexes', 'need', 'pop', 'peak', 'ratio')
    assert tuple(CT.CITY_KINDS) == want, '도시 자리표 종류가 바뀌었다: %s' % (CT.CITY_KINDS,)
    for kind in want:
        for pre in ('v', 'table', 'chart'):
            got = MCM.placeholder_cities('{{%s:%s:테스트시:2027}}' % (pre, kind))
            assert got == ['테스트시'], '%s:%s 에서 도시를 못 읽는다: %s' % (pre, kind, got)
    for kind in ('streak', 'weekly'):
        assert MCM.placeholder_cities('{{v:%s:분당구}}' % kind) == [], \
            '%s 는 도시 자료가 필요 없어 수집 대상이 아니다' % kind
    # 실제 원고에서도 읽힌다 — 자리표에만 도시가 있는 글(region 은 시도)이 섞여 있다.
    cities = MCM.cities_from_content(ROOT)
    assert len(cities) >= 10, '원고에서 도시를 %d곳밖에 못 읽었다' % len(cities)


def test_thumbnail_is_a_picture_not_the_title_card():
    """목록 썸네일은 **그림**이다 — OG 카드(제목 글자)를 줄인 판이 아니다(총괄 요청 2026-10-30).

    무엇을 바꾸면 빨개지나: 썸네일을 다시 카드 축소판으로 되돌리면. 그러면 목록에서 제목이 두 번 보인다
    (그림 속 제목과 바로 옆 제목). 반박 글은 발언 인용을 뽑아 쓴다.
    픽스처: 저장소의 카드·썸네일 한 쌍과 손으로 지은 제목들.
    """
    import make_content_cards as CC
    from PIL import Image
    built = CM.built(ROOT)
    if not built:
        pytest.skip('구워진 글이 없다')
    checked = 0
    for sec, slug, _ in built[:4]:
        cp = os.path.join(ROOT, MC.card_rel(sec, slug))
        tp = os.path.join(ROOT, CC.thumb_rel(sec, slug))
        if not (os.path.exists(cp) and os.path.exists(tp)):
            continue
        shrunk = Image.open(cp).convert('RGB').resize((CC.THUMB_W, CC.THUMB_H), Image.LANCZOS)
        actual = Image.open(tp).convert('RGB')
        # 카드를 그대로 줄인 것이면 두 그림이 거의 같다. 그림형이면 눈에 띄게 다르다.
        diff = sum(abs(a - b) for a, b in zip(shrunk.resize((48, 26)).tobytes(),
                                              actual.resize((48, 26)).tobytes()))
        assert diff > 20000, '%s/%s: 썸네일이 카드 축소판으로 보인다(차이 %d)' % (sec, slug, diff)
        checked += 1
    assert checked >= 2, '카드·썸네일 쌍을 %d개밖에 못 봤다' % checked
    # 반박 글의 인용 뽑기 — 작은따옴표·큰따옴표·둥근 따옴표를 모두 읽는다.
    for title, want in (("이성훈 LH 사장 '집값 급락할 가능성', 입주 물량은", '집값 급락할 가능성'),
                        ('그는 "공급 폭탄" 이라고 했다', '공급 폭탄'),
                        ('따옴표가 없는 제목입니다', None)):
        assert CC._quote(title) == want, '인용 뽑기가 틀렸다: %r → %r' % (title, CC._quote(title))


# ── /weekly/ 해설 칸(총괄 요청 2026-10-30) ──────────────────────────────────────────────────────────────
def _weekly_week():
    """주간 생성기에 넘길 최소한의 주 하나. 값은 쓰지 않는다 — 이 시험이 보는 것은 칸의 처리다."""
    import sido_zones as SZ
    regs = list(SZ.DISPLAY_ORDER)
    codes = ['C%02d' % i for i in range(12)]
    W = {'regions': regs, 'rows': [{'p': '2026-09-21', 'ma': [0.02] * len(regs)}], 'holidays': [],
         'sgg': {'codes': codes, 'rows': [{'p': '2026-09-21', 'ma': [0.01 * i - 0.05 for i in range(12)]}]},
         'seoul': {'regions': ['강남구', '서초구', '마포구'], 'rows': [{'p': '2026-09-21', 'ma': [0.1, -0.1, 0.0]}]}}
    return W, {c: '시군구%d' % i for i, c in enumerate(codes)}


def test_weekly_commentary_slot_points_to_the_latest_column_post(tmp_path):
    """/weekly/ 하단 해설 칸 = /column/ 최신 글 + 콘텐츠 허브. 네이버 블로그 링크는 더 굽지 않는다.

    왜: 2026-10-26·10-29 대표 결정으로 네이버 발행을 멈췄는데, 이 칸은 블로그 최신 주간 글을 가리켰다.
    발행이 끊긴 뒤로는 묵은 글만 걸렸다. 같은 일을 하는 글(/column/ 반박 편)이 사이트에 생겨 그쪽으로 돌렸다.

    무엇을 바꾸면 빨개지나: 칸에 블로그 링크를 되살리면, 최신 글 대신 옛 글을 고르면, 콘텐츠 허브 줄을
      빼면, 글이 없는데 칸을 채우면.
    픽스처: 저장소의 실제 weekly/index.html(표식이 붙은 지금 모양)과 손으로 지은 반박 글 메타 셋.
    """
    src = os.path.join(ROOT, 'weekly', 'index.html')
    d = tmp_path / 'weekly'
    d.mkdir(parents=True)
    shutil.copyfile(src, str(d / 'index.html'))

    def meta(slug, updated, title):
        return {'section': 'column', 'slug': slug, 'updated': updated, 'date': updated, 'title': title}

    metas = [meta('old-one', '2026-10-20', '옛 반박 글'),
             meta('new-one', '2026-10-29', '새 반박 글 "집값 급락" 을 따진다'),
             {'section': 'city', 'slug': 'x', 'updated': '2026-10-30', 'date': '2026-10-30', 'title': '도시 글'}]
    assert MC.write_weekly_column(metas, root=str(tmp_path)) is True
    s = io.open(str(d / 'index.html'), encoding='utf-8').read()
    blk = re.search(re.escape(MC.WEEKLY_START) + r'(.*?)' + re.escape(MC.WEEKLY_END), s, re.S).group(1)
    assert 'blog.naver' not in s, '/weekly/ 에 네이버 블로그 링크가 되살아났다'
    assert 'href="/column/new-one/"' in blk and 'old-one' not in blk, blk
    assert '도시 글' not in blk, '해설 칸은 반박 편만 싣는다'
    assert 'href="/%s/"' % MC.REPORTS_DIR in blk, '콘텐츠 허브 줄이 빠졌다'
    assert '&quot;' in blk or '&#x27;' in blk or '"' not in blk.split('<span>')[0], '제목을 그대로 넣었다'
    # 글이 없으면 허브 줄만 남는다(칸이 빈 글을 가리키지 않는다).
    assert MC.write_weekly_column([{'section': 'city', 'slug': 'x', 'updated': '2026-10-30',
                                    'date': '2026-10-30', 'title': '도시 글'}], root=str(tmp_path)) is True
    blk2 = re.search(re.escape(MC.WEEKLY_START) + r'(.*?)' + re.escape(MC.WEEKLY_END),
                     io.open(str(d / 'index.html'), encoding='utf-8').read(), re.S).group(1)
    assert '/column/' not in blk2 and 'href="/%s/"' % MC.REPORTS_DIR in blk2, blk2
    # 표식이 없는 페이지는 건너뛴다(주간 생성기가 아직 자리를 안 낸 회차).
    (d / 'index.html').write_text('<html></html>', encoding='utf-8')
    assert MC.write_weekly_column(metas, root=str(tmp_path)) is False


def test_weekly_generator_leaves_the_commentary_slot_alone():
    """주간 생성기는 해설 칸의 **자리만** 낸다 — 안은 콘텐츠 생성기의 것이라 다시 구워도 그대로다.

    왜 이게 중요한가: 주간 생성기는 뼈대의 'N개 시도'를 모델 수로 맞추는 치환을 한다. 옛 블로그 칸은 그
    치환에 제목이 걸려 '5개 시도만 올랐습니다'를 '16개 시도만'으로 고쳐 인용한 적이 있다(전수리뷰 #26).
    이제는 콘텐츠 생성기가 **뒤에** 쓰므로 구조적으로 안 생기는데, 그 순서를 이 시험이 지킨다.

    무엇을 바꾸면 빨개지나: put_column_slot 이 구간을 비우게 하면, 자리를 '더 둘러보기' 뒤로 옮기면,
      옛 블로그 표식을 걷지 않으면, render 에서 put_column_slot 호출을 지우면.
    픽스처: 저장소 weekly/index.html 에 ① 콘텐츠가 채운 것처럼 꾸민 칸(제목에 모델과 다른 시도 수가 든 글)
      ② 표식을 떼어 낸 판 ③ 옛 블로그 칸을 되살린 판.
    """
    import make_weekly_page as MW
    W, Q = _weekly_week()
    base = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    n = len(MW.SIDO) - 11
    mine = '<a href="/column/x/">%d개 시도만 올랐습니다</a>' % n
    filled = re.sub(re.escape(MC.WEEKLY_START) + r'.*?' + re.escape(MC.WEEKLY_END),
                    MC.WEEKLY_START + mine + MC.WEEKLY_END, base, flags=re.S)
    out = MW.render(filled, W, Q)
    assert mine in out, '주간 생성기가 해설 칸의 내용을 고쳤다'
    assert out.count(MC.WEEKLY_START) == 1
    rest = out.replace(mine, '')
    assert not [x for x in re.findall(r'(?<!\d)(\d+)개 시도', rest) if int(x) != len(MW.SIDO)], \
        '뼈대 시도 수 치환이 빠졌다'
    # 표식이 없으면 '더 둘러보기' 앞에 빈 자리를 낸다. 다시 구워도 자리가 늘지 않는다.
    stripped = re.sub(re.escape(MC.WEEKLY_START) + r'.*?' + re.escape(MC.WEEKLY_END) + r'\s*', '',
                      base, flags=re.S)
    o2 = MW.render(stripped, W, Q)
    assert o2.count(MC.WEEKLY_START) == 1 and MW.render(o2, W, Q) == o2
    assert o2.index(MC.WEEKLY_START) < o2.index('<h2>더 둘러보기</h2>'), '자리가 더 둘러보기 뒤로 갔다'
    assert re.search(re.escape(MC.WEEKLY_START) + r'\s*' + re.escape(MC.WEEKLY_END), o2), '자리가 비어 있지 않다'
    # 옛 블로그 칸(표식·내용)은 걷는다 — 묵은 글 링크가 남지 않게.
    old = stripped.replace('<h2>더 둘러보기</h2>',
                           '<!--WK:BLOG--><a href="https://blog.naver.com/x/1">옛 글</a><!--/WK:BLOG-->'
                           '<h2>더 둘러보기</h2>', 1)
    o3 = MW.render(old, W, Q)
    assert 'WK:BLOG' not in o3 and 'blog.naver' not in o3, '옛 블로그 칸이 남았다'


def _chart_region(meta, body):
    """그 글이 `chart:moveins` 로 고른 지역과 인자. 없으면 None — 썸네일 지역의 기대값이다."""
    for pre, inner in CT.PH.findall((body or '') + ' ' + (meta.get('summary') or '')):
        parts = [p.strip() for p in inner.split(':') if p.strip()]
        if pre == 'chart' and len(parts) >= 2 and parts[0] == 'moveins':
            return parts[1], parts[1:3]
    return None, None


def test_thumbnail_draws_the_region_the_post_itself_chose():
    """썸네일 막대는 **그 글이 `chart:moveins` 로 고른 지역**이다 — 프런트매터 region 이 아니다.

    왜: region 을 먼저 보던 판은 단지·GTX·반박 편에 모두 같은 막대를 달았다. 그 세 섹션의 region 은
    시도('경기')라, 수원 단지 글과 서울을 따지는 반박 글이 똑같은 숫자를 보였다(총괄 지적 2026-10-30).
    글이 가리키는 가장 좁은 지역은 글쓴이가 고른 chart 자리표에 있다.

    무엇을 바꾸면 빨개지나(둘 다 확인): thumb_args 가 region 을 먼저 보게 되돌리면, 자리표를 보지 않고
      region 만 쓰게 하면.
    ⚠️ 'chart 를 table·v 뒤로 미루기'와 'chart 의 해 인자 버리기'는 **지금 원고에서는 구분되지 않는다** —
       한 글의 chart 와 table·v 가 같은 지역을 쓰고, 그 해가 기본 연도와 같기 때문이다(변이로 확인).
       그래도 chart 를 먼저 보는 것이 옳다: 글이 여러 지역을 말할 때 대표 그림을 고른 자리표가 chart 다.
    픽스처: 저장소의 실제 원고와 데이터. 기대 지역은 자리표를 **따로 읽어** 만든다(썸네일 코드를 쓰지 않는다).
    """
    import make_content_cards as CC
    data = CT.load()
    checked = 0
    for sec, slug, path in CM.posts(ROOT):
        meta, body = CM.read(path, sec, slug)
        want, args = _chart_region(meta, body)
        if not want:
            continue
        try:
            CT.chart(data, 'moveins', args)     # 그 지역 자료가 아직 없는 글은 건너뛴다(군포 같은 새 도시)
        except CT.TableError:
            continue
        spec, _big = CC._thumb_source(meta, body, data)
        assert spec and spec['title'].split()[0] == want, \
            '%s/%s: 썸네일이 %r 를 그린다 — 글은 %r 를 고랐다' % (
                sec, slug, (spec or {}).get('title', '없음').split()[0], want)
        checked += 1
    assert checked >= 10, 'chart 자리표를 쓴 글을 %d편밖에 못 봤다' % checked


def test_thumbnail_number_is_that_regions_own_moveins_value():
    """썸네일의 큰 숫자는 그 지역·그 해의 `v:moveins` 와 **글자 그대로 같다**.

    무엇을 바꾸면 빨개지나(둘 다 확인): 큰 숫자를 입주 세대가 아닌 다른 카드에서 읽으면, 다른 해의
      값을 쓰면. 지역이 틀리는 경우는 윗 시험이 잡는다.
    픽스처: 저장소의 실제 원고와 데이터. 기대값은 자리표를 따로 채워 만든다.
    """
    import re as _re
    import make_content_cards as CC
    data = CT.load()
    seen, by_region = 0, {}
    for sec, slug, path in CM.posts(ROOT):
        meta, body = CM.read(path, sec, slug)
        spec, big = CC._thumb_source(meta, body, data)
        if not (spec and big):
            continue
        name = spec['title'].split()[0]
        year = _re.search(r'(\d{4})', big[1])
        assert year, '%s/%s: 큰 숫자 꼬리표에 연도가 없다 — %r' % (sec, slug, big)
        ph = '{{v:moveins:%s:%s}}' % (name, year.group(1))
        assert big[0] == CT.fill_inline(ph, data), \
            '%s/%s: 썸네일 숫자 %r 가 %s(%r) 와 다르다' % (sec, slug, big[0], ph, CT.fill_inline(ph, data))
        by_region.setdefault(big[0], set()).add(name)
        seen += 1
    assert seen >= 10, '썸네일 숫자를 %d개밖에 못 봤다' % seen
    # 같은 숫자를 서로 다른 지역이 나눠 쓰면 한쪽이 남의 값을 들고 있는 것이다.
    shared = {v: sorted(r) for v, r in by_region.items() if len(r) > 1}
    assert not shared, '한 숫자를 여러 지역이 쓴다 — 지역이 섞였다: %s' % shared
