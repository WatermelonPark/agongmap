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


def test_head_map_links_every_tile_to_its_weekly_graph():
    """머리는 시도 타일 대신 전국 시군구 지도다(2026-10-02 대표 요청). 지도에 **선** 칸(NATION_TILE — 홈 소스에서 읽는다 — 가운데
    시도 머리 칸과 그 주 매매 값이 있는 칸. 값이 한 줄도 없는 칸은 세우지 않는다: sgg_map_svg·홈 sggMapSvg 의 2026-10-07 규칙,
    test_sgg_map 과 같은 셈)마다 홈 통계의 그 지역 주간 그래프 주소(/#stats-market-week~코드 — 홈 applyHash 가 받는 모양)로 가는
    링크이고, 칸 설명의 매매 값이 data.js 시군구 최신 주 값(pv2)과 같다. 시도 타일(mm-tile)은 없다.
    예전엔 NATION_TILE 전 칸을 기대해, 원천이 최신 주에 시군구 하나를 비운 회차에 생성기는 그 칸을 바르게 빼고 굽는데 이 시험만
    빨개져 게이트가 데이터 커밋을 막을 수 있었다(전수리뷰 Z2-2 — data.js 최신 주 a906 매매를 None 으로 두고 굽어 확인).

    변이(각각 실제로 확인): MAP_HREF 를 '/#stats-market' 으로 바꾸면 주소 단정이, week_map 이 전세(je) 줄을 읽으면 값 단정이,
    build 가 옛 tile() 격자를 되살리면 마지막 단정이 빨개진다. 빈 칸 거름은 아래 합성 시험이 늘 본다.
    픽스처: 저장소 data.js 최신 주와 그걸로 구운 weekly/index.html(게이트는 생성기 뒤에 돈다).
    """
    W, _ = MW.load()
    head = _block('HEAD')
    S = W['sgg']
    ma = S['rows'][-1]['ma']
    v = {c: ma[i] for i, c in enumerate(S['codes']) if i < len(ma)}
    tiles = MW.nation_tile()['t']
    drawn = [t[0] for t in tiles if t[4] or v.get(t[0]) is not None]
    links = re.findall(r'<a href="/#stats-market-week~([a-c][0-9]{1,8})" data-code="([^"]+)" aria-label="([^"]+)">', head)
    assert drawn and [c for c, _, _ in links] == drawn and all(c == d for c, d, _ in links), '지도 칸 링크가 배치와 다르다'
    bad = [(c, lab) for c, _, lab in links if not lab.endswith('매매 %s%%' % MW.pv2(v.get(c)))]
    assert not bad, '칸 설명의 매매 값이 data.js 와 다르다: %s' % bad[:5]
    assert 'mm-tile' not in head and 'mm-grid' not in head, '머리에 시도 타일이 되살아났다'


def test_head_map_drops_a_tile_whose_week_is_empty():
    """그 주 매매 값이 빈 시군구 칸(시도 머리 칸이 아닌 칸)은 머리 지도에 서지 않고 링크도 없다 — 나머지 칸은 같은 순서로 다 남는다.

    재현하는 실제 상태: R-ONE 이 최신 주에 시군구 하나를 내지 않은 회차(fetch_weekly_rone 은 응답에 없는 칸을 None 으로 싣는다)나
    행정구역 개편으로 옛 코드가 끊긴 회차. 이력 156주 중 142주에 값 없는 칸이 있었다(인천 신설 4구·화성 분구 — 코드가 데이터보다
    먼저 들어간 기간). 전수리뷰 Z2-2.
    변이(실제로 확인): sgg_map_svg 의 칸 거름(T)을 N['t'] 로 되돌려 빈 칸도 세우면 빨개진다(실데이터 시험은 오늘 빈 칸이 없으면
          그 변이에 초록이라 이 합성 시험이 맡는다).
    픽스처: 저장소 data.js 주간 계열의 깊은 복사에서 최신 주 비머리 칸 하나(값이 있는 첫 칸)의 매매만 None 으로 둔 주.
    """
    import copy
    W, Q = MW.load()
    W = copy.deepcopy(W)
    S = W['sgg']
    row = S['rows'][-1]
    idx = {c: i for i, c in enumerate(S['codes'])}
    tiles = MW.nation_tile()['t']
    gone = next((t[0] for t in tiles if not t[4] and t[0] in idx and idx[t[0]] < len(row['ma'])
                 and row['ma'][idx[t[0]]] is not None), None)
    assert gone, '픽스처 전제: 최신 주에 값이 있는 비머리 칸이 하나는 있어야 한다'

    def drawn():
        v = {c: row['ma'][i] for i, c in enumerate(S['codes']) if i < len(row['ma'])}
        return [t[0] for t in tiles if t[4] or v.get(t[0]) is not None]
    before = drawn()
    row['ma'][idx[gone]] = None
    links = re.findall(r'<a href="/#stats-market-week~([a-c][0-9]{1,8})" data-code="', MW.build(W, Q)[0])
    assert gone not in links, '값이 빈 칸 %s 가 지도에 섰다' % gone
    assert links == drawn() == [c for c in before if c != gone], '빈 칸 하나만 빠져야 한다: %s' % links[:5]


def test_a_region_without_a_value_still_bakes_the_head():
    """한 지역(시도) 값이 빈 주에도 머리(결론·시군구 지도)를 굽는다 — 생성기와 게이트가 같은 계약을 쓴다. 시도 값이 반 넘게 비면
    반쯤 빈 결론을 굽지 않고, 모델 지역 열이 통째로 없으면 조용히 빠지지 않고 멈춘다(SystemExit). 머리에는 시도 집계 리드
    문장이 없다(2026-10-03 대표 요청 — 광역 단위를 걷음).

    변이(각각 실제로 확인): build 의 `if val.get(z) is not None` 거름을 빼면 반쯤 빈 주에도 굽어 둘째 단정이, 모델 대조(miss)를
          빼면 셋째 단정이, 리드 문장(class="lead")을 되살리면 첫 단정이 빨개진다.
    픽스처: 전남광주 값이 빈 주(2026-04-27~07-06 실데이터에 11주 있었다), 시도 값이 반 넘게 빈 주, 전남광주 열이 없는 계열.
    """
    import pytest
    W, Q = _week(dict(_base(0.05), 전남광주=None), _DOWN_SGG, _DOWN_GU)
    head = MW.build(W, Q)[0]
    assert '<h1>' in head and '<div class="mm-scroll"><svg' in head and 'class="lead"' not in head, head[:300]
    half = dict(_base(0.05), **{z: None for z in MW.SIDO[:len(MW.SIDO) // 2 + 1]})
    W1, Q1 = _week(half, _DOWN_SGG, _DOWN_GU)
    with pytest.raises(SystemExit):
        MW.build(W1, Q1)
    W2, Q2 = _week(_base(0.05), _DOWN_SGG, _DOWN_GU)
    i = W2['regions'].index('전남광주')
    W2['regions'] = W2['regions'][:i] + W2['regions'][i + 1:]
    W2['rows'][-1]['ma'] = W2['rows'][-1]['ma'][:i] + W2['rows'][-1]['ma'][i + 1:]
    with pytest.raises(SystemExit):
        MW.build(W2, Q2)


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
    """제목·검색 설명문의 결론이 데이터의 가장 크게 움직인 시도와 그 값이다. 시도 모두 보합인 주에는 둘 다 '보합'을 말한다.

    예전엔 설명문 단정이 분기 밖에 있어, 시도 모두 보합인 주에 생성기가 쓰는 '시도 모두 보합이다.' 대신 '서울 0.00%'를
    기대해 게이트가 그날 데이터 커밋을 막을 수 있었다(2026-10-05 리뷰 E2 — data.js 최신 주 시도 ma 를 모두 ±0.002 로 바꾸고
    생성기를 돌려 재현, 고친 뒤 초록 확인).
    변이(실제로 확인): 보합 분기의 설명문 단정을 옛 모양('%s %s%%' % best)으로 되돌리면 위 보합 재현에서 빨갛고, 생성기
    설명문이 보합 주에도 'X 0.00%'를 쓰게 바꾸면 보합 분기가 빨갛다(make_weekly_page 의 '시도 모두 보합이다.' 를 다른 말로 바꿈).
    픽스처: 저장소 data.js 최신 주와 그걸로 구운 weekly/index.html(게이트는 생성기 뒤에 돈다).
    지역 이름은 화면 이름(SZ.disp — 백로그 46)으로 대조한다. 예전엔 키(best[0])를 h1 에서 찾아, 전남광주가 가장 크게 움직인 주에
    h1 '광주·전남 …'과 어긋나 게이트가 그 주 데이터 커밋을 막았다(전수리뷰 T3-7 — data.js 최신 주 전남광주 ma 를 0.9 로 두고
    구워 재현). 그 갈래는 실데이터가 지나지 않으므로 아래 test_desc_og_and_feed_name_the_mover_by_its_display_name 이 합성 주로 본다.
    """
    W, _ = MW.load()
    row = W['rows'][-1]
    val = {r: row['ma'][i] for i, r in enumerate(W['regions'])}
    sido = [(z, val[z]) for z in SZ.DISPLAY_ORDER if z not in SZ.AGG and val.get(z) is not None]
    best = max(sido, key=lambda x: abs(_r2(x[1])))
    h1 = re.search(r'<h1>(.*?)</h1>', _block('HEAD'), re.S).group(1)
    desc = re.search(r'<meta name="description" content="([^"]*)"', _page()).group(1)
    if _r2(best[1]) == 0:
        assert '보합' in h1
        assert '시도 모두 보합' in desc, '보합 주의 검색 설명문에 결론이 없다: %s' % desc
    else:
        want = '%s %s%%' % (SZ.disp(best[0]), _fmt(best[1]))
        assert want in h1, '제목 결론이 데이터와 다르다: %s' % h1
        assert want in desc, '검색 설명문에 결론이 없다'


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
    # 하락 쪽도 본다 — 예전엔 상승 목록만 zip 해서 하락 TOP 3 정렬을 뒤집어도 초록이었다(2026-09-23 점검).
    # 값 순서만 대조한다(동률의 이름 순서는 안정 정렬 방향에 따라 갈릴 수 있다). 정렬 자체의 변이는
    # 아래 합성 픽스처 시험이 잡는다.
    dn = sorted((x for x in arr if _r2(x[1]) < 0), key=lambda x: x[1])[:3]
    sec = re.search(r'<h3 class="dn">[^<]*</h3><ol>(.*?)</ol>', _block('ANSWER'), re.S).group(1)
    got_dn = re.findall(r'<b class="[^"]*">([^<]+)%</b>', sec)
    assert got_dn == [_fmt(v) for _, v in dn], '시군구 하락 순위가 다르다: %s vs %s' % (got_dn, [_fmt(v) for _, v in dn])


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


# ---------------------------------------------------------------------------
# 합성 주간 픽스처(2026-09-23 전체 점검 시험 보강)
# 위 시험들은 이번 주 실데이터로만 돌아, 그 주의 방향에 기대어 초록이었다 — 가장 크게 움직인 시도가
# 마침 오른 주라 결론 문장의 abs 를 빼도 통과했고, 하락 TOP 3 정렬을 뒤집어도 통과했다.
# 여기서는 방향을 정해 둔 두 주를 만들어 build() 를 직접 부른다. 모양은 data.js 의 ADV.weekly 와 같다
# (regions·rows[-1].ma, sgg.codes·rows, seoul.regions·rows, 조사일은 월요일).
# ---------------------------------------------------------------------------
_GU = ['강남구', '서초구', '송파구', '용산구', '마포구', '노원구', '도봉구', '강북구', '성동구', '광진구']


def _week(sido, sgg, gu):
    regs = list(SZ.DISPLAY_ORDER)
    val = dict(sido)
    val.setdefault('전국', 0.01)
    ma = [val.get(z, 0.01) for z in regs]
    codes = ['C%02d' % i for i in range(len(sgg))]
    W = {'regions': regs, 'rows': [{'p': '2026-09-14', 'ma': ma}],
         'sgg': {'codes': codes, 'rows': [{'p': '2026-09-14', 'ma': [v for _, v in sgg]}]},
         'seoul': {'regions': [g for g, _ in gu], 'rows': [{'p': '2026-09-14', 'ma': [v for _, v in gu]}]}}
    Q = {c: n for c, (n, _) in zip(codes, sgg)}
    return W, Q


def _base(v):
    return {z: v for z in MW.SIDO}


# 하락이 주도한 주: 대구가 −0.31 로 가장 크게 내렸고 오른 곳은 서울 +0.12 가 최고다.
# 시군구는 하락폭이 표시 순서와 섞여 있다(정렬이 실제로 일해야 맞는다).
_DOWN_SIDO = dict(_base(-0.03), 서울=0.12, 경기=0.05, 대구=-0.31, 부산=-0.18, 제주=-0.22)
_DOWN_SGG = [('가군', -0.05), ('나구', -0.44), ('다시', 0.08), ('라군', -0.21), ('마시', -0.62),
             ('바구', 0.02), ('사시', -0.30), ('아군', -0.01), ('자구', 0.15), ('차시', -0.12), ('카군', 0.0)]
_DOWN_GU = [(g, v) for g, v in zip(_GU, (-0.02, 0.06, -0.09, -0.01, -0.15, -0.07, 0.03, -0.04, -0.11, 0.0))]
# 상승이 주도한 주: 서울이 +0.40 으로 가장 크게 올랐고 내린 곳은 대구 −0.10 이 최대다.
_UP_SIDO = dict(_base(0.02), 서울=0.40, 경기=0.21, 대구=-0.10, 부산=-0.04)


def _rank(answer, cls, nth=0):
    secs = re.findall(r'<h3 class="%s">[^<]*</h3><ol>(.*?)</ol>' % cls, answer, re.S)
    return re.findall(r'<li><span class="nm">([^<]+)</span><b class="[^"]*">([^<]+)%</b></li>', secs[nth])


def test_down_week_headline_names_the_biggest_fall():
    """하락이 주도한 주에는 제목이 '대구 −0.31%, 가장 크게 내렸습니다'여야 한다(결론 문장은 make_weekly_page.conclusion —
    홈 띠·홈 주간 h2 와 같은 문장이라 2026-09-27 B1 부터 습니다체다. 설명문(description)은 그대로 다체).

    변이: build() 의 `max(sido, key=lambda x: abs(pv2r(x[1])))` 에서 abs 를 빼면 서울 +0.12 가
          제목에 올라 빨개진다(실제로 바꿔 확인). 실데이터 시험은 그 주가 상승 주도여서 초록이었다.
    픽스처: 대구 −0.31·제주 −0.22·부산 −0.18, 서울 +0.12 — 지방 하락이 수도권 상승보다 큰 주.
    """
    head, _, desc, og = MW.build(*_week(_DOWN_SIDO, _DOWN_SGG, _DOWN_GU))
    h1 = re.search(r'<h1>(.*?)</h1>', head, re.S).group(1)
    assert '대구 -0.31%' in h1 and '가장 크게 내렸습니다' in h1, h1
    assert '대구 -0.31%로 가장 크게 내렸다' in desc and '대구 -0.31%' in og


def test_up_week_headline_names_the_biggest_rise():
    """같은 규칙이 상승 주에는 반대 방향으로 선다 — 두 방향을 모두 고정한다.

    변이: 방향어를 뒤집어(`'올랐다' if pv2r(best[1]) < 0`) 쓰면 빨개진다(확인). 시도 집계 리드 문장('가장 많이 내린 곳은 …')을
    되살려도 빨개진다.
    픽스처: 서울 +0.40·경기 +0.21, 대구 −0.10 — 수도권 상승이 주도한 주.
    """
    head, _, desc, _ = MW.build(*_week(_UP_SIDO, _DOWN_SGG, _DOWN_GU))
    h1 = re.search(r'<h1>(.*?)</h1>', head, re.S).group(1)
    assert '서울 +0.40%' in h1 and '가장 크게 올랐습니다' in h1, h1
    assert '가장 많이' not in head, '시도 집계 리드 문장이 되살아났다(2026-10-03 대표 요청으로 뺐다)'


def test_desc_og_and_feed_name_the_mover_by_its_display_name():
    """가장 크게 움직인 시도가 화면 이름이 따로 있는 지역(DISPLAY_NAME 키 — 지금은 전남광주 하나)인 주에도 h1·검색 설명문(description)·
    og:description·RSS 설명(make_feed.weekly_item — 이 description 을 옮긴다)이 모두 화면 이름('광주·전남 -0.55%')을 쓰고 키는 보이는
    글자 어디에도 없다. 시도 모두 보합인 주에는 og 도 h1·설명문처럼 '시도 모두 보합'이다.

    재현하는 실제 상태: 10-17 백로그 46 수정이 conclusion() 의 who 만 SZ.disp 로 바꾸고 build() 의 desc·og 는 키를 남겨, 전남광주가
    가장 크게 움직인 주(156주 중 아직 없고, 2위 3주·3위 5주 — 2023-10-30 은 경기와 |0.08| 동률)에 test_display_name 이 게이트에서
    weekly/index.html·feed.xml 을 빨갛게 했다(전수리뷰 X2-2·Z2-1·T3-8). 실데이터 시험은 그 갈래를 지나지 않아 합성 주로 늘 본다.
    픽스처: _week — 시도 모두 +0.02 에 그 키만 -0.55 인 주, 시도 모두 +0.001(표시 0.00) 인 보합 주.
    변이(각각 실제로 확인): build 의 desc 에서 who 를 best[0] 으로 되돌리면 desc·feed 단정이, og 에서 되돌리면 og 단정이 빨개진다.
          og 의 보합 갈래를 지우면 마지막 단정이 빨개진다.
    """
    import make_feed as F
    from test_display_name import _visible
    keys = [k for k in SZ.DISPLAY_NAME if k in MW.SIDO]
    assert keys, '화면 이름이 따로 있는 시도가 없다 — 이 시험이 아무것도 보지 않는다'
    for k in keys:
        W, Q = _week(dict(_base(0.02), **{k: -0.55}), _DOWN_SGG, _DOWN_GU)
        head, _, desc, og = MW.build(W, Q)
        h1 = re.search(r'<h1>(.*?)</h1>', head, re.S).group(1)
        feed = F.weekly_item(W, Q)['desc']
        want = '%s -0.55%%' % SZ.disp(k)
        for where, s in (('h1', h1), ('description', desc), ('og:description', og), ('RSS', feed)):
            assert want in s, '%s 에 화면 이름 결론(%s)이 없다: %s' % (where, want, s)
            leak = [x for x in SZ.DISPLAY_NAME if x in _visible(s)]
            assert not leak, '%s 에 판정 단위 키 %s 가 보인다: %s' % (where, leak, s)
    W, Q = _week(_base(0.001), _DOWN_SGG, _DOWN_GU)
    head, _, desc, og = MW.build(W, Q)
    assert '시도 모두 보합' in head and '시도 모두 보합이다.' in desc, (head[:200], desc)
    named = [z for z in MW.SIDO if '%s 0.00%%' % SZ.disp(z) in og]
    assert '시도 모두 보합.' in og and not named, '보합 주 og 가 한 지역을 결론처럼 적는다: %s' % og


def test_down_top3_lists_the_largest_falls_first():
    """하락 TOP 3 은 가장 많이 내린 곳부터다(마시 −0.62 → 나구 −0.44 → 사시 −0.30).

    변이: top3() 의 `reversed(arr)` 를 `arr` 로 바꾸면 덜 내린 곳부터(아군 −0.01 …) 나와 빨개진다
          (실제로 바꿔 확인). 예전 시험은 상승 목록만 대조해 초록이었다.
    픽스처: 하락폭이 표시 순서와 섞인 시군구 11곳(보합 1곳 포함)과 서울 10개 구.
    """
    _, answer, desc, _ = MW.build(*_week(_DOWN_SIDO, _DOWN_SGG, _DOWN_GU))
    assert _rank(answer, 'dn', 0) == [('마시', '-0.62'), ('나구', '-0.44'), ('사시', '-0.30')]
    assert _rank(answer, 'up', 0) == [('자구', '+0.15'), ('다시', '+0.08'), ('바구', '+0.02')]
    assert _rank(answer, 'dn', 1) == [('마포구', '-0.15'), ('성동구', '-0.11'), ('송파구', '-0.09')]
    assert '하락 1위 마시 -0.62%' in desc


def test_og_description_drops_the_nation_part_when_it_is_missing():
    """전국 값이 없는 주(R-ONE 부분 응답 — update_adv_data 의 chg 는 원천이 없으면 None)에 og:description 이 '전국 ·%'를
    굽지 않는다. desc·리드·공유 문구처럼 전국 조각을 뺀다(전수리뷰 #29).

    픽스처: 저장소 data.js 주간 계열의 최신 행에서 '전국' 칸만 None 으로 바꾼 것(값·날짜는 데이터에서), 그 사본에서 시도를 모두
          보합(±0.001)으로 둔 주와 한 시도만 크게(+0.5) 움직인 주 — og 의 두 갈래(지역 결론·'시도 모두 보합')를 실데이터 방향과
          상관없이 늘 지난다. 마지막은 전국 칸에 값(+0.07)을 넣은 사본.
    변이(실제로 확인): build 의 og 를 예전 식('%s · 전국 %s%%, %s %s%%.' % (datestr, pv2(nation), …))으로 되돌리면 빨개진다.
          og 의 보합 갈래를 지우고 늘 '%s %s%%' % (who, …) 를 쓰면 보합 사본에서 빨개진다(전수리뷰 Z2-1 — 예전 og 는 보합 주에
          'X 0.00%' 로 한 지역을 결론처럼 적어 h1 '시도 모두 보합'과 갈렸다).
    """
    import copy
    W, Q = MW.load()
    W = copy.deepcopy(W)
    ma = W['rows'][-1]['ma']
    ma[W['regions'].index('전국')] = None
    flat, moved = copy.deepcopy(W), copy.deepcopy(W)
    for z in MW.SIDO:
        flat['rows'][-1]['ma'][W['regions'].index(z)] = 0.001
        moved['rows'][-1]['ma'][W['regions'].index(z)] = 0.001
    moved['rows'][-1]['ma'][W['regions'].index(MW.SIDO[-1])] = 0.5
    seen = set()
    for w in (W, flat, moved):
        _, _, desc, og = MW.build(w, Q)
        for name, s in (('og', og), ('desc', desc)):
            assert '·%' not in s and '전국 ·' not in s, '%s: %s' % (name, s)
        who = MW.conclusion(w)['who']   # 화면 이름(SZ.disp) — 보합 주에는 None
        after = og.split('발표', 1)[1]
        if who is None:
            assert after.startswith(' · 시도 모두 보합.'), og
        else:
            assert who in og and '전국' not in after.split(who)[0], og
        seen.add(who is None)
    assert seen == {True, False}, '두 갈래(보합·지역 결론)를 다 지나지 않았다'
    # 전국 값이 있으면 예전처럼 싣는다
    W2 = copy.deepcopy(W)
    W2['rows'][-1]['ma'][W2['regions'].index('전국')] = 0.07
    assert '전국 +0.07%' in MW.build(W2, Q)[3]
