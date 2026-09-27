# -*- coding: utf-8 -*-
"""홈 요약 표식 구간·검색 설명·푸터·운영 주체(홈 마케팅 검수 B3·B5, 2026-09-27)를 고정한다.

재현하는 실제 상태(SEO-1·MOB-5): 홈 정적 HTML 에는 방법론 문단만 있고 판정·주간 숫자는 전부 스크립트가 그렸다.
스크립트를 돌리지 않는 검색 로봇·링크 미리보기에 숫자가 없었고, 느린 망에서 첫 화면이 빈 상자였다. 대표 확인(09-27)대로
배치(make_home_summary)가 index.html 의 **표식 구간 하나**와 설명 메타 셋만 data-core 값으로 고쳐 쓴다.

여기서 보는 것
  ① 표식 밖은 한 글자도 안 바뀐다(생성기의 자기 검사와 **따로** 이 파일이 잘라 비교한다)
  ② 구운 값 = data-core 값(배치 게이트는 생성기 뒤에 돌므로 커밋될 index.html 을 본다)
  ③ 화면 중복 없음: 구간이 #map-wrap 안에 있고, 지도가 그려지면 innerHTML 로 통째로 바뀌며, 자리 예약이 :empty 가 아니다
  ④ 배치 배선: 커밋 잡 생성기·ci-tests 두 잡·로컬 bat 이 make_home_summary 를 돌리고, TARGETS 에 index.html
  ⑤ 푸터 세 벌이 같고 매주·매달·분기·읽을거리로 묶였으며 블로그 링크가 정본 주소, Organization JSON-LD(sameAs 없음)
  ⑥ 홈 주간 구역의 해석 글 한 줄(스크립트)이 /weekly/ 와 같은 말
무엇을 깨뜨리면 빨개지나는 시험마다 적었다(각각 실제로 바꿔 확인).
"""
import html as H
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blog_feed as BF  # noqa: E402
import home_src as HS  # noqa: E402
import make_home_summary as MH  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
START, END = '<!--HOME_SUMMARY_START-->', '<!--HOME_SUMMARY_END-->'


def _index():
    return io.open(os.path.join(HS.ROOT, HS.HOME), encoding='utf-8', newline='').read()


def _strip(s):
    """이 시험 나름의 '표식 밖' — 생성기의 outside() 를 쓰지 않는다(검사기가 결함을 스스로 재현하지 않게)."""
    i, j = s.index(START) + len(START), s.index(END)
    s = s[:i] + s[j:]
    for attr in ('name="description"', 'property="og:description"', 'name="twitter:description"'):
        s = re.sub(r'(<meta %s content=")[^"]*(")' % re.escape(attr), r'\1\2', s)
    return s


def _adv(grade='g3', tot=412345, ratio=0.88, L='2027Q1', head=True, flat=False):
    """합성 data-core ADV — 실데이터와 다른 등급·분기·주(전진한 날을 흉내)."""
    zones = [{'z': z, 'agg': z in SZ.AGG, 'grade': 'g1', 'ratio': 0.1, 'dtot': 1000, 'H': 12} for z in SZ.ORDER]
    nat = next(z for z in zones if z['z'] == '전국')
    nat.update(grade=grade, ratio=ratio)
    for z in zones:
        num, d, pct = SZ.card_parts(tot if z is nat else 1000, z['ratio'])
        z.update(ctxt=SZ.card_text(tot if z is nat else 1000, z['ratio']), cnum=num, cdir=d, cpct=pct)
    regs = list(SZ.DISPLAY_ORDER)
    ma = [0.0 if flat else 0.01] * len(regs)
    if not flat:
        ma[regs.index('전국')] = 0.126
        ma[regs.index('부산')] = -0.33
    W = {'regions': regs, 'rows': [{'p': '2027-01-04', 'ma': ma}], 'grace': 9}
    if head:
        W['head'] = MW.head_payload(dict(W))
    return {'sido': {'L': L, 'Ltxt': SZ.quarter_text(L), 'H': 12, 'zones': zones},
            'weekly': W}


# ── ① 표식 밖은 그대로 ─────────────────────────────────────────────────────────────────────────────────
@pytest.mark.parametrize('kw', [{}, {'grade': 'g0', 'tot': -52000, 'ratio': -0.2}, {'head': False}, {'flat': True}])
def test_generator_touches_only_the_marker_block_and_three_metas(kw):
    """합성 데이터 네 벌(부족·여유·주간 결론 없음·전부 보합)로 구워도 표식 구간과 메타 셋 말고는 같다. 다시 구워도 같다.

    변이: make_home_summary.METAS 에 ('property', 'og:title') 을 더하면(생성기 자기 검사도 같이 눈감는다) 이 시험의
          따로 자른 비교가 빨개진다. render 가 끝 표식 뒤에 한 글자를 더 쓰면 생성기 자기 검사(SystemExit)로 빨개진다(둘 다 확인).
    """
    s = _index()
    out = MH.render(s, _adv(**kw))
    assert _strip(out) == _strip(s), '홈 요약 생성기가 표식 밖을 바꿨다'
    assert MH.render(out, _adv(**kw)) == out, '다시 구우면 달라진다(멱등 아님)'
    assert out.count(START) == 1 and out.count(END) == 1


def test_generator_refuses_a_page_without_exactly_one_marker_pair():
    s = _index()
    for bad in (s.replace(START, ''), s.replace(END, END + END), s.replace('<meta name="twitter:description"', '<meta name="x"')):
        with pytest.raises(SystemExit):
            MH.render(bad, _adv())


def test_baked_text_says_the_synthetic_numbers():
    """숫자는 data-core 필드 그대로(ctxt·Ltxt·ADV.weekly.head), 주간 값은 사이트 반올림(pv2), 발표일은 weekly_release.

    변이: facts() 에서 pv2 대신 '%.1f' 로 적거나, 발표일 대신 조사일(p)을 쓰면 빨개진다(둘 다 확인). 원값 0.126 은
          사이트 pv2 로 +0.13 이다(반올림 규칙이 다르면 끝자리가 갈린다).
    """
    a = _adv()
    out = MH.render(_index(), a)
    blk = out[out.index(START):out.index(END)]
    nat = next(z for z in a['sido']['zones'] if z['z'] == '전국')
    assert H.escape(nat['ctxt']) in blk and SZ.GRADE_LABS['g3'] in blk and a['sido']['Ltxt'] in blk
    assert '1/7 발표' in blk and '전국 +0.13%' in blk and a['weekly']['head']['text'] in blk
    assert 'href="/weekly/"' in blk and 'href="/zone/전국/"' in blk
    desc = re.search(r'<meta name="description" content="([^"]*)"', out).group(1)
    og = re.search(r'<meta property="og:description" content="([^"]*)"', out).group(1)
    tw = re.search(r'<meta name="twitter:description" content="([^"]*)"', out).group(1)
    assert nat['cnum'] in desc and '+0.13%' in desc and nat['cnum'] in og and '+0.13%' in og and og == tw
    n = len([z for z in SZ.ORDER if z not in SZ.AGG])
    assert ('%d개 시도' % n) in desc
    # 주간 결론이 없는 옛 data-core 면 결론만 빠진다 / 아무것도 없으면 표식만 남고 메타는 그대로
    blk2 = MH.render(_index(), _adv(head=False))
    assert '전국 +0.13%' in blk2 and a['weekly']['head']['text'] not in blk2[blk2.index(START):blk2.index(END)]
    empty = MH.render(_index(), {})
    assert START + END in empty and _strip(empty) == _strip(_index())
    assert re.search(r'<meta name="description" content="([^"]*)"', empty).group(1) == \
        re.search(r'<meta name="description" content="([^"]*)"', _index()).group(1)


# ── ② 구운 값 = data-core ──────────────────────────────────────────────────────────────────────────────
def _core():
    s = io.open(os.path.join(ROOT, 'data-core.js'), encoding='utf-8').read()
    return json.loads(re.search(r'^const ADV=(\{.*\});$', s, re.M).group(1))


def test_committed_home_says_what_data_core_says():
    """배치 게이트는 생성기 뒤에 돈다 — 그때의 index.html 요약·메타가 data-core.js 의 판정·주간 값과 같다.

    변이: 배치 커밋 잡에서 make_home_summary 를 빼면(ci-tests 도 같이) 표식 구간이 커밋된 빈 표식 그대로라 빨개진다
          (표식을 비운 index.html 로 확인).
    픽스처: 저장소의 index.html·data-core.js(배치가 방금 쓴 것). 기대값은 data-core 에서 따로 읽는다.
    """
    adv, s = _core(), _index()
    blk = s[s.index(START) + len(START):s.index(END)]
    nat = next(z for z in adv['sido']['zones'] if z['z'] == '전국')
    assert H.escape(nat['ctxt']) in blk, '홈 요약의 전국 판정이 data-core 와 다르다 — python tools/make_home_summary.py'
    assert (adv['sido'].get('Ltxt') or adv['sido']['L']) in blk
    w = adv['weekly']
    row = w['rows'][-1]
    nv = row['ma'][w['regions'].index('전국')]
    assert ('전국 %s%%' % MW.pv2(nv)) in blk and ('%s 발표' % WR.md(WR.status(row['p'])['pub'])) in blk
    if (w.get('head') or {}).get('p') == row['p']:
        assert w['head']['text'] in blk
    desc = re.search(r'<meta name="description" content="([^"]*)"', s).group(1)
    assert nat['cnum'] in desc and MW.pv2(nv) in desc


# ── ③ 화면 중복 없음·자리 예약 ─────────────────────────────────────────────────────────────────────────
def test_summary_lives_in_the_map_slot_and_the_map_replaces_it():
    """요약은 #map-wrap 안에 있고, renderSidoMap 이 그 칸을 innerHTML 로 통째로 갈아 끼우며 data-done 을 단다. 자리 예약은
    :not([data-done]) 에 건다 — :empty 면 요약이 든 순간 예약이 풀려 CLS 0.62(2026-09-18)가 되돌아온다.

    변이: 표식을 #map-wrap 밖(앞)으로 옮기거나, renderSidoMap 의 `el.innerHTML=h` 를 insertAdjacentHTML 로 바꾸거나,
          app.css 예약을 #map-wrap:empty 로 되돌리면 빨개진다(셋 다 확인).
    """
    s = _index()
    m = re.search(r'<div id="map-wrap">(.*?)</div>\s*\n\s*<div id="graph-wrap">', s, re.S)
    assert m and m.group(1).startswith(START) and m.group(1).rstrip().endswith(END), '표식 구간이 #map-wrap 바로 안에 있지 않다'
    js = HS.home_source()
    i = js.index('function renderSidoMap(')
    body = js[i:js.index('\nfunction ', i + 10)]
    assert "getElementById('map-wrap')" in body and re.search(r'\bel\.innerHTML=h;', body) and "el.dataset.done='1'" in body
    css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    code = re.sub(r'/\*.*?\*/', '', css, flags=re.S)
    assert '#map-wrap:empty' not in code, '지도 자리 예약이 :empty 다 — 요약이 들면 예약이 풀린다'
    assert len(re.findall(r'#map-wrap:not\(\[data-done\]\)\{min-height:\d+px\}', code)) >= 3


# ── ④ 배치 배선 ─────────────────────────────────────────────────────────────────────────────────────────
def test_every_batch_path_runs_the_home_generator_and_commits_index():
    """클라우드 커밋 잡(게이트 앞)·ci-tests 두 잡·로컬 bat 이 make_home_summary 를 돌리고, 두 배치가 index.html 을 커밋한다.

    변이: ci-tests.yml bare-runtime 잡에서 make_home_summary 줄을 지우면, bat 의 git add 에서 index.html 을 빼면 빨개진다
          (둘 다 확인 — 순서·대상 일치 자체는 test_batch_parity·test_ci_workflow_mirrors_gate 도 본다).
    """
    wf = os.path.join(ROOT, '.github', 'workflows')
    up = io.open(os.path.join(wf, 'update-cloud.yml'), encoding='utf-8').read()
    ci = io.open(os.path.join(wf, 'ci-tests.yml'), encoding='utf-8').read()
    bat = io.open(os.path.join(ROOT, 'tools', 'run_weekly_update.bat'), encoding='utf-8').read()
    gate = up.index('python3 -m pytest tools/tests/')
    assert -1 < up.find('if ! python3 tools/make_home_summary.py') < gate
    assert ci.count('python3 tools/make_home_summary.py') == 2
    assert re.search(r'^python tools\\make_home_summary\.py$', bat, re.M)
    assert 'index.html' in re.search(r'TARGETS="([^"]+)"', up).group(1).split()
    assert 'index.html' in re.search(r'^\s*git add (.+)$', bat, re.M).group(1).split()


# ── ⑤ 푸터·운영 주체 ────────────────────────────────────────────────────────────────────────────────────
def _footers(s):
    return re.findall(r'<nav class="ft-nav ft-grp"[^>]*>(.*?)</nav>', s, re.S)


def test_three_footers_are_the_same_grouped_by_cadence_with_the_blog_link():
    """홈·통계·퀴즈 푸터 세 벌이 같고(측정 onclick 만 다름), 매주·매달·분기·읽을거리 순서로 묶이며, 블로그 링크는 정본 주소·
    '네이버 블로그' 표기·새 창이다. 요일·알림 약속이 없다. 투자자·재건축 테스트 링크가 있다(IA-9).

    변이: 셋 중 하나에서 링크 하나를 지우거나, 블로그 주소를 손으로 다른 값으로 적거나, 묶음 순서를 바꾸면 빨개진다(셋 다 확인).
    """
    s = _index()
    fs = [re.sub(r' onclick="[^"]*"', '', f) for f in _footers(s)]
    assert len(fs) == 3 and fs[0] == fs[1] == fs[2], '푸터 세 벌이 다르다'
    f = fs[0]
    assert re.findall(r'<span class="fg"><b>([^<]+)</b>', f) == ['매주', '매달', '분기', '읽을거리']
    blog = re.search(r'<a href="([^"]+)"([^>]*)>([^<]+)</a>', f[f.index(BF.BLOG_HOME) - 9:])
    assert blog.group(1) == BF.BLOG_HOME and 'target="_blank"' in blog.group(2) and 'rel="noopener"' in blog.group(2)
    assert blog.group(3) == '%s(%s)' % (BF.HOME_TEXT, BF.LABEL)
    for href in ('/weekly/', '/monthly/', '/jeonse-ratio/', '/zone/', '/moveins/', '/cycle/', '/faq/',
                 '/burini-test/', '/investor-test/', '/redev-test/'):
        assert f.count('href="%s"' % href) == 1, href
    assert not re.search(r'금요일|알림|구독', f)


def test_home_has_an_organization_without_same_as_yet():
    """홈 JSON-LD 에 Organization(name·url·logo). sameAs 는 서치어드바이저 원문 확인 뒤라 아직 없다. logo 파일이 실제로 있다.

    변이: logo 를 없는 파일(/icons/logo.png)로 바꾸거나 sameAs 를 넣으면 빨개진다(둘 다 확인).
    """
    s = _index()
    head = s[:s.index('</head>')]
    lds = [json.loads(b) for b in re.findall(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', head, re.S)]
    org = [x for x in lds if x.get('@type') == 'Organization']
    assert len(org) == 1, lds
    o = org[0]
    assert o['name'] == '아공맵' and o['url'] == 'https://www.agongmap.co.kr/' and 'sameAs' not in o
    assert o['logo'].startswith('https://www.agongmap.co.kr/')
    assert os.path.isfile(os.path.join(ROOT, *o['logo'][len('https://www.agongmap.co.kr/'):].split('/')))


# ── ⑥ 홈 주간 구역의 해석 글 한 줄 ──────────────────────────────────────────────────────────────────────
def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i, depth = src.index('{', m.end()), 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError(name)


def test_home_blog_line_says_what_the_weekly_page_says():
    """홈 blogLine 이 ADV.blog 로 만드는 한 줄 = blog_feed.text(같은 글·같은 말). 남의 주소·빈 값은 칸을 안 연다. 부팅이 부르고,
    자리(#wk-blog)는 주간 구역에 숨은 채 있으며, 누르면 home_cta blog_weekly 로 잡힌다.

    변이: blogLine 에서 src 를 빼거나 주소 검사를 지우거나, boot 에서 renderBlogLine() 줄을 지우면 빨개진다(셋 다 확인).
    """
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    js = HS.home_source()
    b = BF.pick({'date': '2026-09-25', 'title': '주간 <글>', 'url': BF.BLOG_HOME + '/7'}, '2026-09-24')
    prog = (_js_func(js, 'blogLine') + ';const B=%s;const L=blogLine(B);'
            'console.log(JSON.stringify([L.text+L.src,blogLine(Object.assign({},B,{url:"https://evil.test/x"})),'
            'blogLine(null),blogLine({})]));' % json.dumps(b, ensure_ascii=False))
    p = subprocess.run([node, '-e', prog], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    got = json.loads(p.stdout.decode('utf-8'))
    assert got == [BF.text(b), None, None, None], got
    boot = _js_func(js, 'boot')
    assert re.search(r'^\s*renderBlogLine\(\);', boot, re.M), '부팅이 renderBlogLine 을 부르지 않는다'
    assert "track('home_cta',{to:'blog_weekly'})" in _js_func(js, 'renderBlogLine')
    s = _index()
    sec = s[s.index('id="wk-h2"'):s.index('<!-- ===== 통계보기 대시보드 ===== -->')]
    assert re.search(r'<p class="wk-blog" id="wk-blog" hidden></p>', sec[:sec.index('</section>')])
