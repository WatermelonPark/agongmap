# -*- coding: utf-8 -*-
"""화면에 보이는 지역 이름은 판정 단위 키가 아니라 화면 이름이다(백로그 46, 2026-10-17 대표 승인).

재현하는 실제 상태: 2026-09-10 광주·전남 통합 뒤 판정 단위 키 '전남광주'(국토교통부·KOSIS 가 발표하는 통합 단위 이름)가
지도 라벨·표 머리·선택 상자·리포트 제목·/monthly/ 표·/cycle/ 차트에 그대로 나갔다. 사람들은 '광주·전남'으로 찾고 읽는다.
그래서 화면 이름 표 하나(sido_zones.DISPLAY_NAME)를 두고, 생성기는 SZ.disp, 홈은 split_data 가 실은 ADV.zname 을 읽는 zn(),
/cycle/ 차트는 refresh_cycle_data 가 다시 쓰는 const ZN, 블로그 검색어는 make_naver_post.SEARCH_NAME 이 같은 표를 읽는다.
주소(/zone/전남광주/)·데이터 키·GA 값·sessionStorage 값은 키 그대로다.
픽스처: 배치 게이트처럼 split_data·생성기를 먼저 돌린 저장소 산출물(생성 페이지·data-core.js·cycle/index.html·llms.txt·feed.xml)과
홈 스크립트(home_src).

변이(각각 실제로 확인): make_monthly_page 표 행 머리의 SZ.disp 를 빼면·make_sido_pages page_title 의 SZ.disp 를 빼면 첫 시험이,
통합 안내 페이지의 조사를 '로'로 고정하면 둘째가, split_data 의 zname 줄을 빼면 셋째가, /cycle/ 차트 한 곳의 zname() 을 빼거나
refresh_cycle_data 의 fill_zname 호출을 빼고 ZN 표를 손으로 고치면 넷째가, home-stats 의 시도 선택 상자에서 value 를 빼면 다섯째가,
버블 GA 를 이름표 글자로 되돌리면 여섯째가, SEARCH_NAME 을 손 표로 되돌리면 일곱째가 빨개진다.
"""
import glob
import io
import json
import os
import re
import sys
import urllib.parse

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import sido_zones as SZ  # noqa: E402
import home_src as HS  # noqa: E402
import make_sido_pages as P  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
SKIP_DIRS = ('drafts', 'logs', 'node_modules', 'tools', 'docs', '.git', '.github', '.claude')


def _read(rel):
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _visible(s):
    """사람이 읽는 글자 — 스크립트·스타일과 주소(href·src·data-*)는 뺀다. meta description·title·aria-label 은 남긴다."""
    s = re.sub(r'<script\b.*?</script>|<style\b.*?</style>|<!--.*?-->', '', s, flags=re.S)
    s = re.sub(r'\b(?:href|src|action|data-[\w-]+)="[^"]*"', '', s)
    return re.sub(r'https?://\S+', '', s)


def _pages():
    out = []
    for f in glob.glob(os.path.join(ROOT, '**', '*.html'), recursive=True):
        rel = os.path.relpath(f, ROOT)
        if rel.split(os.sep)[0] in SKIP_DIRS:
            continue
        out.append(rel)
    out += [x for x in ('llms.txt', 'feed.xml') if os.path.exists(os.path.join(ROOT, x))]
    return sorted(out)


def test_canon_table_is_a_two_way_map_of_model_keys():
    assert SZ.DISPLAY_NAME, '화면 이름 표가 비었다'
    assert set(SZ.DISPLAY_NAME) <= set(SZ.ORDER)
    shown = set(SZ.disp(z) for z in SZ.ORDER)
    assert len(shown) == len(SZ.ORDER), '화면 이름이 겹친다 — 두 지역이 같은 이름으로 보인다'
    assert not (set(SZ.DISPLAY_NAME.values()) & set(SZ.ORDER)), '화면 이름이 다른 지역 키와 같다'
    for z in SZ.ORDER:
        assert SZ.key_of(SZ.disp(z)) == z


def test_no_page_shows_a_renamed_key():
    pages = _pages()
    assert len(pages) > 30 and 'monthly/index.html' in pages and 'cycle/index.html' in pages, pages[:5]
    bad = []
    for rel in pages:
        v = _visible(_read(rel))
        for k in SZ.DISPLAY_NAME:
            for m in re.finditer(re.escape(k), v):
                bad.append('%s: …%s…' % (rel, v[max(0, m.start() - 30):m.end() + 15].replace('\n', ' ')))
    assert not bad, '화면에 판정 단위 키가 보인다(SZ.disp·zn 을 거치지 않았다):\n' + '\n'.join(bad[:12])
    # 바뀐 이름은 실제로 보여야 한다 — 위 단정이 '아무 이름도 안 찍힌' 페이지로 통과하지 않게
    for k, name in SZ.DISPLAY_NAME.items():
        assert name in _visible(_read(os.path.join('zone', k, 'index.html'))), k
        assert name in _visible(_read('monthly/index.html')), k


def test_merged_stub_particles_follow_the_display_name():
    for old, new in P.MERGED_INTO.items():
        path = os.path.join('zone', old, 'index.html')
        if not os.path.exists(os.path.join(ROOT, path)):
            continue
        s = _read(path)
        nd = SZ.disp(new)
        assert '%s %s%s 합쳐졌습니다' % (old + P._topic(old), nd, P._euro(nd)) in s, (path, re.search(r'<h1[^>]*>(.*?)</h1>', s).group(1))
        assert '/zone/' + urllib.parse.quote(new) + '/' in s, '안내 페이지의 주소는 키 그대로다'


def test_merged_stub_says_what_the_source_did(tmp_path):
    """통합 안내 페이지는 원천이 한 일을 사실대로 쓴다 — '광주와 전남의 공급 통계를 한 단위로 묶어 발표'(묶인 지역은 MERGED_INTO 에서,
    조사 와/과는 받침으로). 화면 이름('광주·전남')을 원천이 쓰는 이름처럼 '<b>광주·전남</b> 하나로 발표'라 쓰지 않는다 — 원천 표의 통합
    단위 이름은 키 '전남광주'다(전수리뷰 Z1-9). 키도 화면에 내지 않는다(test_no_page_shows_a_renamed_key).
    변이(실제로 확인): 문장을 옛 '공급 통계를 <b>%s</b> 하나로'(화면 이름)로 되돌리면 빨개진다.
    픽스처: MERGED_INTO 의 옛 지역마다 임시 폴더에 안내 페이지를 굽는다."""
    assert P.MERGED_INTO
    for old, new in P.MERGED_INTO.items():
        d = tmp_path / old
        d.mkdir()
        P._write_merged_stub(str(d), old, new)
        s = (d / 'index.html').read_text(encoding='utf-8')
        parts = [o for o, n in P.MERGED_INTO.items() if n == new]
        want = '·'.join(parts[:-1]) + P._wa(parts[-2]) + ' ' + parts[-1]
        assert '<b>%s</b>의 공급 통계를 한 단위로 묶어 발표' % want in s, s
        assert '<b>%s</b> 하나로' % SZ.disp(new) not in s
        assert new not in _visible(s), '안내 페이지 글자에 판정 단위 키가 보인다'
    assert P._wa('광주') == '와' and P._wa('전남') == '과'


def test_core_payload_carries_the_canon_table():
    s = _read('data-core.js')
    m = re.search(r'"zname":(\{[^}]*\})', s)
    assert m, 'data-core.js 에 ADV.zname 이 없다 — 홈 zn() 이 키를 그대로 찍는다'
    assert json.loads(m.group(1)) == SZ.DISPLAY_NAME


def test_cycle_chart_labels_go_through_the_canon_table():
    s = _read('cycle/index.html')
    m = re.search(r'const ZN=(\{[^\n]*?\}),zname=', s)
    assert m and json.loads(m.group(1)) == SZ.DISPLAY_NAME, 'cycle 의 ZN 표가 정본과 다르다'
    labels = [x for x in re.findall(r'labels:D\.\w+\.map\(\w=>[^,]*', s) if '.region' in x]
    assert len(labels) >= 3, '지역 차트 이름표를 못 찾았다: %s' % labels
    raw = [x for x in labels if 'zname(' not in x]
    assert not raw, '키를 그대로 찍는 차트 이름표: %s' % raw


def test_home_region_selects_keep_the_key_as_value():
    """<option> 은 value 가 없으면 글자가 값이 된다 — 화면 이름이 데이터 키 자리에 들어가 그 지역 자료를 못 찾는다."""
    src = HS.home_source()
    opts = re.findall(r"""<option(?!\s+value=)[^>]*>""", src)
    bad = [o for o in opts if '${' in o or "'+" in o or o == '<option>']
    assert not bad, 'value 없는 <option>: %s' % bad
    assert re.search(r'<option value="\$\{r\}"\$\{r===ST\.reg', src), '통계 탭 지역 선택 상자가 키를 value 로 싣지 않는다'
    # 지역 글자를 바로 찍는 표 머리가 남지 않았는지(통계 탭 표·인허가·입주물량·시장동향)
    assert not re.search(r'<th>\$\{(?:r|reg)\}</th>|<th>\'\+reg\+\'</th>', src)


def test_home_ga_region_values_stay_keys():
    src = HS.home_source()
    m = re.search(r"track\('bubble_detail',\{region:([^}]*)\}\)", src)
    assert m and 'textContent' not in m.group(1), '버블 GA 지역 값이 이름표 글자(화면 이름)다'
    assert re.search(r'class="bb-row" data-r="\'\+rg\+\'"', src), '버블 행에 키가 없다'


def test_blog_search_names_read_the_canon_table():
    import make_naver_post as NP
    for k, v in SZ.DISPLAY_NAME.items():
        assert NP.SEARCH_NAME.get(k) == v, k
    src = _read('tools/make_naver_post.py')
    assert re.search(r'SEARCH_NAME = dict\(SZ\.DISPLAY_NAME', src), 'SEARCH_NAME 이 정본 표를 읽지 않는다'
