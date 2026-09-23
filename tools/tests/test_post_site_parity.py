# -*- coding: utf-8 -*-
"""블로그 초안(make_naver_post·make_theory_post)이 사이트와 같은 숫자·같은 산식을 말하는지 본다.

2026-09-23 전체 점검에서 확인한 결함 넷을 고정한다(CLAUDE.md "사이트와 블로그가 다른 숫자·다른 산식을
말하면 안 된다"). 각 시험의 독스트링에 ① 무엇을 깨뜨리면 빨개지는지(실제로 변이를 넣어 확인했다),
② 픽스처가 어떤 실제 상태를 재현하는지 적었다.

홈 산식과의 대조는 홈 스크립트(tools/home_src.home_source)에서 해당 코드를 그대로 뽑아 node 로 돌린다.
CI 에서는 건너뜀도 실패이므로 node 가 없으면 건너뛰지 않고 실패한다(test_weekly_page 와 같은 사정 —
러너에 node 가 있다).
"""
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import home_src as HS  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_theory_post as T  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 산식과 대조할 수 없다'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _js_func(src, name):
    """홈 스크립트에서 `function name(...){...}` 하나를 중괄호 짝으로 잘라 온다."""
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError('%s 의 끝을 찾지 못했다' % name)


def _home_bubble_js():
    """홈 renderBubbleSec 의 '최신 전세가율' 함수와 월세수익률 식을 그대로 뽑는다."""
    f = _js_func(HS.home_source(), 'renderBubbleSec')
    lat = re.search(r'const latest=(r=>\{.*?return null;\});', f)
    lo = re.search(r'const lo=([^,;]+),hi=', f)
    assert lat and lo, '버블밴드의 latest()·월세수익률 식을 찾지 못했다 — 홈 코드 모양이 바뀌었는지 볼 것'
    return lat.group(1), lo.group(1)


def _site_bubble(adv, sts):
    """홈 코드로 계산한 {지역: [lo.toFixed(2), loan<=lo]}."""
    latest, expr = _home_bubble_js()
    js = ('const J=%s,B=%s;const latest=%s;const out={};'
          'for(const rg of (B.regions||Object.keys(B.conv))){const cv=B.conv[rg],jr=latest(rg);'
          'if(cv==null||jr==null)continue;const lo=%s;out[rg]=[lo.toFixed(2),B.loan.v<=lo];}'
          'process.stdout.write(JSON.stringify(out));'
          % (json.dumps(sts['전세가율'], ensure_ascii=False), json.dumps(adv['bubble'], ensure_ascii=False),
             latest, expr))
    return _node(js)


# ── ① 월세수익률 = 전세가율 × 전월세전환율 ──────────────────────────────────
# 2026-09-23 실데이터: 전국 전세가율 끝 세 칸 68.9·69.0·69.1, 전환율 5.37, 대출금리 4.48.
# 옛 블로그는 전환율 5.37%를 월세수익률로 찍고 '월세가 이자보다 비싸다'고 썼다. 홈은 3.71%다.
# 끝에 None 한 칸을 더 둔다 — 배치가 새 달 열을 전 지역 None 으로 먼저 만들고 받아온 지역만 채우므로
# (make_naver_post._series_last 주석) 전국이 아직 안 온 달에 실제로 이 모양이 된다.
FIX_ADV = {'bubble': {'prd': '2026.06', 'loan': {'v': 4.48, 'p': '2026.07'},
                      'regions': ['전국'], 'conv': {'전국': 5.37}}}
FIX_STS = {'전세가율': {'dates': ['2026.05', '2026.06', '2026.07', '2026.08'],
                        'series': {'전국': [68.9, 69.0, 69.1, None]}}}


def test_rent_yield_matches_the_home_formula_for_every_region():
    """블로그 rent_yield 가 홈 버블밴드와 모든 지역에서 같은 값(표시 두 자리)을 낸다.

    깨뜨리면 빨개지는 것: make_naver_post.rent_yield 의 `jr / 100 * cv` 를 `cv` 로 되돌리면(옛 결함)
    19개 지역 전부에서 빨개진다(변이로 확인). 끝 칸 결측 처리는 오늘 데이터에 결측 끝 칸이 없어
    여기서는 못 잡고, 아래 픽스처 시험이 잡는다.
    픽스처: 저장소의 실제 data.js(19개 지역) — 홈이 같은 파일을 읽어 버블밴드를 그린다.
    """
    adv, sts = M.load()
    site = _site_bubble(adv, sts)
    assert site, '홈 코드가 한 지역도 계산하지 못했다'
    bad = []
    for rg, (txt, _) in site.items():
        ours = P.rent_yield(adv, sts, rg)
        if ours is None or P.fixed2(ours) != txt:
            bad.append('%s: 사이트 %s · 블로그 %s' % (rg, txt, None if ours is None else P.fixed2(ours)))
    assert not bad, '월세수익률이 홈과 다르다: %s' % '; '.join(bad)


def test_rent_yield_section_prints_the_site_value_and_verdict():
    """④ 로테이션 2번(월세수익률 vs 대출금리) 문단이 홈과 같은 수치·같은 판정을 쓴다.

    깨뜨리면 빨개지는 것: extra_section 에서 `lo = rent_yield(...)` 를 옛 `conv`(전환율 그대로)로 되돌리면
    5.37%가 찍히고 판정이 뒤집혀 빨개진다(변이로 확인). rent_yield 가 최신 비결측 대신 계열
    끝 칸(`s[-1]`)을 읽게 바꾸면 값이 사라져 문단이 비고 빨개진다(변이로 확인).
    픽스처: 2026-09-23 실값(69.1 × 5.37 = 3.71 < 대출금리 4.48) + 새 달 열이 먼저 None 으로 생긴 상태.
    """
    site = _site_bubble(FIX_ADV, FIX_STS)['전국']
    assert site[0] == '3.71', site
    html = P.extra_section(FIX_ADV, FIX_STS, 2)
    assert '<b>%s%%</b>' % site[0] in html, html
    assert '5.37' not in html, '전월세전환율을 월세수익률로 찍었다'
    want = '월세로 사는 비용이 대출 이자보다 비싼 상태' if site[1] else '대출 이자가 월세보다 비싼 상태'
    assert want in html, '판정이 홈(loan<=lo → 매수 신호권)과 반대다: %s' % html


def test_fixed2_matches_js_tofixed_on_ties():
    """fixed2 가 JS toFixed(2) 와 같은 문자열을 낸다 — 정확히 가운데인 값에서 '%.2f'와 갈린다.

    깨뜨리면 빨개지는 것: fixed2 를 `'%.2f' % v` 로 바꾸면 3.125·0.625 에서 빨개진다(변이로 확인).
    픽스처: 이진수로 정확히 표현되는 가운데 값(62.5% × 5.0 = 3.125 같은 월세수익률이 실제로 나올 수 있다)과
    그렇지 않은 흔한 값.
    """
    cases = [3.125, 0.625, 1.005, 3.7106699999999996, 4.48, 2.675, 0.0, 12.345]
    site = _node('process.stdout.write(JSON.stringify(%s.map(v=>v.toFixed(2))));' % json.dumps(cases))
    assert [P.fixed2(v) for v in cases] == site


# ── ② 주간 변동률 반올림 ─────────────────────────────────────────────────────
def _weekly_values(adv):
    W = adv['weekly']
    vals = set()
    for blk in (W, W.get('seoul') or {}):
        for r in blk.get('rows') or []:
            for f in ('ma', 'je'):
                vals.update(v for v in (r.get(f) or []) if v is not None)
    return sorted(vals)


def test_weekly_pct_matches_site_pv2_on_every_cell():
    """블로그 pct 가 홈 pv2(+'%')와 data.js 주간 칸 전부에서 같다.

    깨뜨리면 빨개지는 것: make_naver_post.pct 를 옛 `'0.00%' if abs(v) < 0.005 else '%+.2f%%' % v` 로
    되돌리면 -0.075(사이트 -0.08, 옛 블로그 -0.07) 등 고유값 23개에서 빨개진다(변이로 확인 — 칸으로는
    주간 13,706칸 중 58칸이 갈려 있었다).
    픽스처: 저장소의 실제 data.js 주간 시도·서울 구 매매·전세 값 전부(고유값) + 경계값.
    """
    adv, _ = M.load()
    vals = _weekly_values(adv) + [-0.075, -0.015, 0.105, 0.145, -0.085, 0.125, -0.001, 0.004]
    h = HS.home_source()
    site = _node('%s\n%s\nprocess.stdout.write(JSON.stringify(%s.map(pv2)));'
                 % (_js_func(h, 'pv2r'), _js_func(h, 'pv2'), json.dumps(vals)))
    bad = ['%r: 사이트 %s%% · 블로그 %s' % (v, s, P.pct(v)) for v, s in zip(vals, site) if P.pct(v) != s + '%']
    assert not bad, '블로그 변동률 표기가 사이트와 %d칸 다르다: %s' % (len(bad), '; '.join(bad[:5]))


# ── ③ 지역 편 순부족 ─────────────────────────────────────────────────────────
def test_zone_post_net_shortage_is_the_site_card_number(monkeypatch):
    """지역 편 '결론부터'의 순부족 세대수가 사이트 카드 문구(ctxt, 배치가 구운 값)와 같다.

    깨뜨리면 빨개지는 것: draft_zone 의 `t = M.disp_tot(r, SZ.LEAD_Q)` 를 옛 `t = r['tot']` 로 되돌리면
    경기(50,578 vs 50,579)·대구·울산·강원에서 빨개진다(변이로 확인).
    픽스처: 저장소의 실제 ADV.sido 시도 16곳 전부. 캡처·썸네일·RSS 는 끈다(네트워크·파일 쓰기 없음).
    """
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    adv, sts = M.load()
    zones = [z for z in adv['sido']['zones'] if not z.get('agg')]
    assert len(zones) == len([z for z in SZ.ORDER if z not in SZ.AGG])
    bad = []
    for z in zones:
        m = re.match(r'([\d,]+)세대 (부족|여유)', z['ctxt'])
        if not m:
            continue                      # 0세대(비율만 있는 문구)는 대조할 수가 없다
        body = P.draft_zone(adv, sts, z, 1, len(zones))['body']
        g = re.search(r'현재 <b>([\d,]+)세대가 (모자란|남아도는)</b>', body)
        want = (m.group(1), '모자란' if m.group(2) == '부족' else '남아도는')
        if not g or g.groups() != want:
            bad.append('%s: 사이트 %s · 블로그 %s' % (z['z'], want, g and g.groups()))
    assert not bad, '지역 편 순부족이 사이트 카드와 다르다: %s' % '; '.join(bad)


# ── ⑥ 이론 편의 시도 수 ──────────────────────────────────────────────────────
def test_theory_posts_say_the_model_sido_count():
    """이론 1·2편의 'N개 시도를 같은 기준으로'가 모델의 시도 수(= /zone/ 허브의 N_SIDO)와 같다.

    깨뜨리면 빨개지는 것: 1·2편 템플릿의 `%(nsido)d` 를 모델과 다른 수('17개')로 박으면 빨개진다(변이로 확인).
    오늘 모델(16곳)과 같은 '16개'를 박은 옛 코드는 여기서는 초록이다 — 그건 아래 시험이 잡는다.
    픽스처: 실제 POSTS 1·2편 본문. 3편은 발행본이라 고치지 않고(대표 결정), 곳 수도 다른 대상(sync_n)이다.
    """
    n = len([z for z in SZ.ORDER if z not in SZ.AGG])
    assert M.N_SIDO == n
    for no in (1, 2):
        post = next(p for p in T.POSTS if p['n'] == no)
        html = T.render(post)
        got = [int(x) for x in re.findall(r'(\d+)개 시도를 같은 기준으로', html)]
        assert got, '%d편에서 시도 수 문장을 찾지 못했다' % no
        assert set(got) == {n}, '%d편이 %s개 시도라고 쓴다(모델 %d)' % (no, got, n)


def test_theory_render_follows_a_changed_model(monkeypatch):
    """모델 시도 수가 바뀌면 이론 편 문장도 따라 바뀐다 — 숫자를 박으면 여기가 빨개진다.

    깨뜨리면 빨개지는 것: make_theory_post 1·2편 템플릿의 `%(nsido)d` 를 옛 '16'(또는 어떤 수로든) 박으면
    빨개진다(변이로 확인). 픽스처: 모델이 바뀐 상태를 흉내 내 N_SIDO 를 실재할 수 없는 99로 바꾼다 —
    17처럼 그럴듯한 수를 쓰면 그 수를 박은 코드가 우연히 통과한다.
    """
    monkeypatch.setattr(M, 'N_SIDO', 99)
    for no in (1, 2):
        html = T.render(next(p for p in T.POSTS if p['n'] == no))
        got = re.findall(r'(\d+)개 시도를 같은 기준으로', html)
        assert got and set(got) == {'99'}, '%d편이 모델을 따라오지 않는다: %s' % (no, got)
