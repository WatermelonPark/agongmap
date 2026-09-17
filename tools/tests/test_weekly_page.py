# -*- coding: utf-8 -*-
"""/weekly/ 랜딩이 그 주의 답을 HTML 에 구워 싣는지 고정한다.

2026-09-15 고객 점검(점검후속 개발 ①):
  - 소개 블록("들어가면 더 보이는 것")이 답보다 먼저 나와 한 번 더 눌러야 답이 보였다.
  - 변동률이 스크립트로만 그려져 검색엔진·링크 미리보기에 결론이 없었다.
  - 타일이 광주·전남으로 따로 나왔다(판정 단위는 전남광주 하나).
  - 홈은 발표일, 통계 탭은 조사일만 적어 다른 데이터로 보였다.

생성기가 정본이다. 페이지가 data.js 와 어긋나면(누가 손으로 고쳤거나 배치가 생성기를 빠뜨리면)
첫 시험이 빨개진다. 나머지는 생성기 자체가 틀렸을 때를 잡도록 값을 따로 계산해 대조한다.
"""
import datetime
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _page():
    return io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()


def _block(name):
    m = re.search(r'<!--WK:%s-->(.*?)<!--/WK:%s-->' % (name, name), _page(), re.S)
    assert m, 'WK:%s 표식이 없다' % name
    return m.group(1)


# 반올림은 생성기 함수를 그대로 쓴다. 예전에는 Decimal half-up 으로 따로 구현했는데, 생성기·사이트는
# floor(|v|*100+0.5)(JS Math.round)라 0.145 같은 값에서 시험만 0.15 를 기대해 클라우드 게이트를 막을 수
# 있었다(리뷰 14번, 이력 38,783개 값 중 3개). 대신 그 함수가 사이트 pv2r 와 같은지는 아래 시험이 node 로 본다.
_r2 = MW.pv2r
_fmt = MW.pv2


def test_page_is_baked_from_current_data():
    W, Q = MW.load()
    s = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()
    assert MW.render(s, W, Q) == s, 'weekly/index.html 이 data.js 와 어긋난다 — python tools/make_weekly_page.py 를 돌릴 것'


def test_answer_comes_before_any_intro_block():
    s = _page()
    assert '들어가면 더 보이는 것' not in s, '소개 블록이 되살아났다 — 답을 먼저 싣는다'
    ans = _block('ANSWER')
    assert ans.count('<li>') >= 2, '시군구·서울 구 순위가 HTML 에 없다'
    assert '/#stats-market' in ans, '전체 TOP 10 으로 가는 버튼이 답 아래에 없다'


def test_no_live_render_script_overwrites_the_baked_answer():
    assert 'data-core.js' not in _page(), '라이브 렌더 스크립트가 남아 있다 — 구운 결론과 다른 값을 덮어쓸 수 있다'


def test_tiles_follow_the_zone_model():
    labels = re.findall(r'<div class="mm-tile"[^>]*><b[^>]*>([^<]+)</b>', _block('HEAD'))
    assert labels == list(SZ.DISPLAY_ORDER), '타일이 판정 단위 표시 순서와 다르다: %s' % labels
    assert '광주' not in labels and '전남' not in labels


def test_survey_and_release_dates_are_both_baked():
    W, _ = MW.load()
    p = W['rows'][-1]['p']
    y, m, d = (int(x) for x in p.split('-'))
    rel = datetime.date(y, m, d) + datetime.timedelta(days=3)
    want = '%d/%d 조사 · %d/%d 발표' % (m, d, rel.month, rel.day)
    assert want in _block('HEAD'), '제목 위에 "%s" 가 없다' % want
    desc = re.search(r'<meta name="description" content="([^"]*)"', _page()).group(1)
    assert want in desc, '검색 설명문에 기준일 병기가 없다'


def test_headline_names_the_biggest_mover_with_its_value():
    W, _ = MW.load()
    row = W['rows'][-1]
    val = {r: row['ma'][i] for i, r in enumerate(W['regions'])}
    sido = [(z, val[z]) for z in SZ.DISPLAY_ORDER if z not in SZ.AGG and val.get(z) is not None]
    best = max(sido, key=lambda x: abs(_r2(x[1])))
    h1 = re.search(r'<h1>(.*?)</h1>', _block('HEAD'), re.S).group(1)
    if _r2(best[1]) == 0:
        assert '보합' in h1
    else:
        assert '%s %s%%' % (best[0], _fmt(best[1])) in h1, '제목 결론이 데이터와 다르다: %s' % h1
    desc = re.search(r'<meta name="description" content="([^"]*)"', _page()).group(1)
    assert '%s %s%%' % (best[0], _fmt(best[1])) in desc, '검색 설명문에 결론이 없다'


def test_sgg_top_matches_home_ranking_rule():
    """홈 TOP 10 과 같은 대상·정렬: SGG_QNAME 에 이름이 있고 값이 있는 곳, 값 내림차순."""
    W, Q = MW.load()
    S = W['sgg']
    row = S['rows'][-1]
    arr = sorted(((Q[c], row['ma'][i]) for i, c in enumerate(S['codes'])
                  if c in Q and row['ma'][i] is not None), key=lambda x: -x[1])
    up = [x for x in arr if _r2(x[1]) > 0][:3]
    got = re.findall(r'<li><span class="nm">([^<]+)</span><b class="[^"]*">([^<]+)%</b></li>', _block('ANSWER'))
    for (n, v), (gn, gv) in zip(up, got[:3]):
        assert (n, _fmt(v)) == (gn, gv), '시군구 상승 순위가 다르다: %s vs %s' % ((n, _fmt(v)), (gn, gv))


def test_region_count_phrases_are_derived():
    n = len([z for z in SZ.ORDER if z not in SZ.AGG])
    for x in re.findall(r'(?<!\d)(\d+)개 시도', _page()):
        assert int(x) == n, "'%s개 시도' 가 모델(%d곳)과 다르다" % (x, n)


def test_both_batches_run_the_generator_and_commit_the_page():
    yml = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    assert 'python3 tools/make_weekly_page.py' in yml, '클라우드 배치가 생성기를 부르지 않는다'
    t = re.search(r'TARGETS="([^"]*)"', yml).group(1).split()
    assert 'weekly' in t, '클라우드 배치 커밋 대상에 weekly 가 없다 — 구워도 배포되지 않는다'
    bat = io.open(os.path.join(ROOT, 'tools', 'run_weekly_update.bat'), encoding='utf-8').read()
    assert 'make_weekly_page.py' in bat, '로컬 배치가 생성기를 부르지 않는다'
    add = [ln for ln in bat.splitlines() if ln.strip().startswith('git add ')]
    assert add and all(re.search(r'(?<![\w/\\])weekly(?![\w\-/\\.])', ln) for ln in add), '로컬 배치 git add 에 weekly 가 없다'


PV2R_CASES = (0.145, -0.145, 0.125, -0.085, 2.675, 0.005, 1.005, 0.0049, -0.0012, 0.2, 0.0)


def test_generator_rounding_matches_the_site_js():
    """생성기 pv2r 가 사이트(home-app.js) pv2r 와 같은 값을 낸다 — 같은 주 같은 지역의 끝자리가 갈리지 않게.

    깨뜨리면 빨개지는 것: make_weekly_page.pv2r 를 round(v, 2)(은행가 반올림)나 Decimal half-up 으로 바꾸면
    0.125·0.145 에서 사이트와 갈린다(변이로 확인).
    픽스처: 경계값 모음 — 리뷰가 찾은 0.145, 부호 대칭 −0.085, 은행가 반올림이 갈리는 0.125·2.675.
    """
    import json
    import shutil
    import subprocess
    import home_src as HS
    if not shutil.which('node'):
        import pytest
        pytest.skip('node 없음')
    m = re.search(r'^function pv2r\(v\)\{[^\n]*\}', HS.home_source(), re.M)
    assert m, 'home-app.js 에서 pv2r 를 찾지 못했다'
    js = m.group(0) + ';process.stdout.write(JSON.stringify(%s.map(pv2r)));' % json.dumps(list(PV2R_CASES))
    p = subprocess.run(['node', '-e', js], capture_output=True, timeout=30)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    site = json.loads(p.stdout.decode('utf-8'))
    ours = [MW.pv2r(v) for v in PV2R_CASES]
    bad = ['%s: 사이트 %s · 생성기 %s' % (v, a, b) for v, a, b in zip(PV2R_CASES, site, ours) if abs(a - b) > 1e-9]
    assert not bad, '생성기 반올림이 사이트와 다르다: %s' % '; '.join(bad)
