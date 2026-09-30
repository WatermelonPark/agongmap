# -*- coding: utf-8 -*-
"""블로그 초안 도구의 전수 리뷰(2026-09-30) 묶음 BL 결함을 고정한다 — 항목 72~84·24·114.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - make_naver_post._thumb_curve 의 `RC.index_breaks` 검사를 지우면 → test_thumb_skips_a_rebased_index (#72)
  - theory_link3.link3_numbers 첫머리 연속성 검사를 지우면 → test_link3_stops_on_a_rebased_index (#73)
  - make_theory_post.render 의 Link3DataError 분기를 지우면 → test_theory4_data_break_is_not_blamed_on_the_text
  - theory_link3 의 _se_pm·_ic_q assert 를 지우거나 except 를 AssertionError 만으로 되돌리면 → link3 가드 시험들 (#78)
  - _min2025 가 조사를 붙이지 않으면(옛 '는' 박기) → test_link3_min2025_carries_its_own_particle
  - make_naver_post._cut_weekly 에서 seoul·sgg 절단을 빼면 → test_week_back_cuts_the_district_series (#74)
  - make_theory_post.main 의 덮기 가드를 지우거나 인자 없는 기본값을 1로 되돌리면 → main 시험 둘 (#75)
  - 1·2편 본문에 '1.42%%' 를 되돌리거나 link1_values 의 가드·절 빼기를 지우면 → 고리① 시험들 (#76)
  - 3편 sync_topv 를 '%.1f' % CYCLE_SYNC[0]['corr'](1위 값)로 되돌리면 → test_theory3_sync_numbers_are_the_site_prose (#77)
  - series_links·naver_serp.track_keywords 의 카테고리를 손 문자열로 되돌리면 → test_category_names_follow_the_closer (#79)
  - pick_zone 의 seq 를 len(done)+1 로, _rot 의 바퀴 밀기나 title_arm 의 바퀴 뒤집기를 빼면 → 두 바퀴 시험 (#80)
  - track_keywords 가 RSS 실패에 [] 를 돌려주거나 main 의 failed += 1 을 빼면 → test_track_fails_when_rss_is_unreadable (#81)
  - WEEKLY_TABLE 에 모델에 없는 이름('광주')을 넣으면 → test_weekly_table_names_are_model_names (#82)
  - MORE_ROTATION[0] 의 path 를 '/weekly/' 로 되돌리면 → test_map_corner_links_to_the_map (#83)
  - draft_weekly 의 상·하위 3을 옛 sorted 사본으로 되돌리면 → test_weekly_top3_is_the_site_top3 (#84)
  - 전세가율 절(rot 0)을 _series_last 로 되돌리면 → test_jeonse_section_uses_the_site_reference_month (#24·#106)
  - 30년 넘은 아파트 절(rot 3)을 지역별 마지막 비결측 값으로 되돌리면 → test_aged_section_uses_one_complete_year (#114)

픽스처가 재현하는 실제 상태:
  - 지수 단절: 2026-09-28 데이터(3a823bc)처럼 계열 중간에서 여러 지역 값이 한꺼번에 절반으로 떨어진 합성 계열
    (판정 정본은 rebuild_cycle_analysis.index_breaks — 문턱 자체의 시험은 그쪽 묶음 C 시험에 있다).
  - link3 가드: 저장소 data.js 에서 매매지수 기준 단절을 시험 안에서만 이어 붙이고(단절이 없으면 그대로), 인허가를
    본문이 전제하는 반기(LATEST_H)까지, 매매지수를 그 반기 끝 달까지로 자르고, 수도권·지방 판정 칸(split·pbr)을
    2026-09-30 사이트 문장 그대로의 고정 값(FROZEN_SPLIT)으로 둔 상태 — 데이터가 앞으로 가도 같은 입력이 되게 고정한다
    (4편 '지금' 단정이 새 데이터로 뒤집히면 도구가 멈추지만 게이트는 막지 않는다 — 통합 검토). 여기에 리뷰가 재현한
    변이(서울 2021·22 인허가 ×0.8, 인천 ×1.5, 2025H2 행 이름 바꿈, 2026H2 행 추가, 받침으로 끝나는 시도가 2025년 최저
    목록의 끝에 오게 한 인허가)를 얹는다.
  - --week: 실제 주간 계열의 이번 주 서울 구 행 한 곳을 +9.99% 로 바꿔, 지난 회차 글에 그 값이 새면 드러나게 한다. 서울 구
    응답이 빈 회차(수집이 직전 블록을 둬 서울 구가 한 주 늦은 상태, #4)에는 이번 주 행을 붙여 같은 상태를 만든다.
  - 주간 표: 최신 주 매매값이 없는 지역(2026-04-27~07-06 전남광주 11주)은 기대값에서도 뺀다(도구의 규칙).
  - 노후주택 기준 해의 기대값은 저장 계열에서 '집계를 뺀 모든 시도가 찬 마지막 열'로 센다(끝 열이 일부만 찬 회차에도 초록).
  통합 검토(2026-09-30)에서 확인한 변이: _min2025 가 '는'을 박으면, _cut_weekly 가 seoul·sgg 를 자르지 않으면, WEEKLY_TABLE 에
  '광주'를 넣으면, 노후주택 절이 dates[-1] 열을 쓰면 각각 빨개진다. 서울 구가 한 주 늦은 상태·최신 주 전남광주 None·노후주택
  끝 열 일부만 참·서울 최신 확정치 −8%와 수도권 판정 반전은 고치기 전 시험에서 빨갛고 지금은 초록이다.
  - 전세가율·노후주택: 실제 계열 끝에 새 달·새 해 열을 붙이고 일부 지역만 채운 상태(merge 가 새 열을 전 지역 None 으로
    만들고 받은 지역만 채우는 구조, 2026.06·07 실제 사례).
네트워크·저장소 파일 쓰기 없음(초안은 tmp_path).
"""
import copy
import io
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import close_published_issues as CP  # noqa: E402
import make_indicator_pages as I  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_theory_post as T  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import naver_serp as NS  # noqa: E402
import rebuild_cycle_analysis as RC  # noqa: E402
import sido_zones as SZ  # noqa: E402
import theory_link3 as L3  # noqa: E402


def _idx_sts(vals, others=None, name='세종'):
    """세종 계열 vals + 다른 두 지역(기본은 RISE). 기준 단절은 여러 지역이 같은 달에 함께 끊기는 모양이다."""
    dates = ['%d.%02d' % (2016 + i // 12, i % 12 + 1) for i in range(len(vals))]
    dates[-1] += ' p)'
    o = others if others is not None else RISE
    return {'매매지수': {'dates': dates, 'series': {name: vals, '대구': list(o), '부산': list(o)}}}


RISE = [100.0 + i for i in range(60)]
REBASED = RISE[:48] + [v / 2 for v in RISE[48:]]        # 2020.01 부터 새 기준 — 한 달에 −50%


# ── #72·#73 지수 기준 단절 ────────────────────────────────────────────────
def test_thumb_skips_a_rebased_index():
    assert P._thumb_curve(_idx_sts(RISE), '세종') is not None, '정상 계열에서는 곡선을 그린다'
    assert P._thumb_curve(_idx_sts(REBASED, REBASED), '세종') is None
    # 단절은 계열 전체의 일이다 — 세종 자신은 끊기지 않았어도(대구 +4% 처럼 폭이 작은 지역) 쓰지 않는다
    assert P._thumb_curve(_idx_sts(RISE, REBASED), '세종') is None
    assert '고점에서' not in P.thumb_message('세종', P._thumb_curve(_idx_sts(REBASED, REBASED), '세종'))[0]


def test_link3_stops_on_a_rebased_index():
    with pytest.raises(L3.Link3DataError) as e:
        L3.link3_numbers({}, _idx_sts(REBASED, REBASED))
    assert '기준 단절' in str(e.value)


def test_theory4_data_break_is_not_blamed_on_the_text(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)

    def broken(adv, sts):
        raise L3.Link3DataError('매매지수 기준 단절 — 매매지수 2026.01 (27개 지역, 예: 서울 189.83→94.62)')
    monkeypatch.setattr(L3, 'link3_numbers', broken)
    with pytest.raises(SystemExit) as e:
        T.render(next(p for p in T.POSTS if p['n'] == 4))
    # 복구는 클라우드 배치의 전 기간 재수집이다(대표 결정 ①) — 로컬 세션에 git pull 뒤 다시 돌리라고 말한다
    assert 'git pull' in str(e.value) and '문장을 먼저 고칠 것' not in str(e.value)


# ── #78 4편 단정 가드 ────────────────────────────────────────────────────
def _link3_fixture():
    adv, sts = M.load()
    adv, sts = copy.deepcopy(adv), copy.deepcopy(sts)
    mm = sts['매매지수']
    for _ in range(5):                       # 시험 안에서만 이어 붙인다(데이터에는 연결계수를 쓰지 않는다 — 대표 결정 ①)
        br = RC.index_breaks(sts, ('매매지수',))
        if not br:
            break
        i = mm['dates'].index(br[0][1])
        for ser in mm['series'].values():
            prev = next((v for v in reversed(ser[:i]) if v is not None), None)
            if i < len(ser) and prev and ser[i]:
                f = prev / ser[i]
                for k in range(i, len(ser)):
                    if ser[k] is not None:
                        ser[k] *= f
    assert not RC.index_breaks(sts, ('매매지수',))
    rows = adv['permits']['rows']
    adv['permits']['rows'] = rows[:next(i for i, r in enumerate(rows) if r['p'] == L3.LATEST_H) + 1]
    # 배치가 매 회차 움직이는 입력은 LATEST_H 끝 달에서 멈춘다 — 4편의 '지금' 단정(_se_pk: 최신 확정치 > 지난 정점,
    # _boom_n 의 30개월 창)이 데이터 전진으로 뒤집히면 도구가 멈추는 것이 맞지만(로컬 세션이 돌릴 때 드러난다), 그날 배치의
    # 데이터 커밋까지 막으면 안 된다(CLAUDE.md '게이트 시험은 데이터가 앞으로 가도 초록'). 이 시험들은 가드의 동작을 본다.
    end = '%s.%s' % (L3.LATEST_H[:4], '06' if L3.LATEST_H.endswith('H1') else '12')
    k = [d.split()[0] for d in mm['dates']].index(end) + 1
    mm['dates'] = mm['dates'][:k]
    mm['series'] = {r: v[:k] for r, v in mm['series'].items()}
    # 판정 칸(adv['sido'] zones 의 split·pbr)도 분기마다 바뀐다 — 사이트 판정 문장과 같은 모양의 고정 값으로 둔다.
    for x in adv['sido']['zones']:
        if x['z'] in FROZEN_SPLIT:
            rows_, pbr = FROZEN_SPLIT[x['z']]
            x['split'] = dict(x['split'], rows=[list(r) for r in rows_])
            x['pbr'] = pbr
    return adv, sts


# 2026-09-30 사이트 판정 문장(make_sido_pages 가 굽는 split 두 줄·pbr) 그대로 — 판정이 분기마다 바뀌어도 가드 시험 입력은 고정
FROZEN_SPLIT = {
    '수도권': ((('지난 4년', '필요량보다 20% 덜 지었습니다'), ('앞으로 3년', '필요량의 68%가 들어옵니다')), 0.968),
    '지방': ((('지난 4년', '필요량보다 14% 덜 지었습니다'), ('앞으로 3년', '필요량의 57%가 들어옵니다')), 0.663),
}


def _scale(adv, region, years, f):
    R = adv['permits']['regions']
    for r in adv['permits']['rows']:
        if r['p'][:4] in years and r['v'][R.index(region)] is not None:
            r['v'][R.index(region)] *= f


def test_link3_baseline_passes_on_a_continuous_index():
    adv, sts = _link3_fixture()
    out = L3.link3_numbers(adv, sts)
    assert out['ic_q'] == '0.5배'


@pytest.mark.parametrize('region,f,key', [('서울', 0.8, 'se_pm'), ('인천', 1.5, 'ic_q')])
def test_link3_direction_claims_are_guarded(region, f, key):
    adv, sts = _link3_fixture()
    _scale(adv, region, ('2021', '2022'), f)
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert (' %s:' % key) in str(e.value), str(e.value)


def test_link3_missing_half_year_is_a_claim_error_not_a_traceback():
    adv, sts = _link3_fixture()
    for r in adv['permits']['rows']:
        if r['p'] == '2025H2':
            r['p'] = '2025H9'                # 연간 합은 그대로, 반기 한 칸만 못 찾게
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert 'StopIteration' in str(e.value)


def test_link3_new_half_year_stops_the_now_sentences():
    adv, sts = _link3_fixture()
    last = adv['permits']['rows'][-1]
    adv['permits']['rows'].append(dict(last, p='2026H2', v=list(last['v'])))
    with pytest.raises(L3.Link3ClaimError) as e:
        L3.link3_numbers(adv, sts)
    assert 'jb_h1' in str(e.value)


def test_link3_min2025_carries_its_own_particle():
    adv, sts = _link3_fixture()
    v = L3.link3_numbers(adv, sts)['min2025']
    names, part = v[:-1], v[-1]
    assert part == P.eunneun(names.split('·')[-1])
    assert '%(min2025)s 2025년' in next(p for p in T.POSTS if p['n'] == 4)['body']
    # 실데이터의 끝 지역(제주)은 받침이 없어 '는'을 박아도 초록이다 — 받침으로 끝나는 시도가 끝에 오는 상태를 만든다.
    # 그 시도의 2025년을 2007년 이후 최저로 낮추고(0 은 아니게), 모델 순서상 그 뒤 시도는 2025년을 올려 목록에서 뺀다.
    R = adv['permits']['regions']
    sido = [rg for rg in R if rg not in SZ.AGG]
    tgt = [rg for rg in sido if P.eunneun(rg) == '은'][-1]
    for r in adv['permits']['rows']:
        if r['p'][:4] == '2025':
            for rg in sido[sido.index(tgt):]:
                i = R.index(rg)
                if r['v'][i]:
                    r['v'][i] = r['v'][i] * (0.01 if rg == tgt else 100)
    v = L3.link3_numbers(adv, sts)['min2025']
    assert v.split('·')[-1] == tgt + '은', v


# ── #74 --week N ─────────────────────────────────────────────────────────
def test_week_back_cuts_the_district_series(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    adv, sts = M.load()
    adv = copy.deepcopy(adv)
    se = adv['weekly']['seoul']
    # 이번 주(잘려야 할 주)의 서울 구 행에만 있는 값. 서울 구 응답이 빈 회차엔 수집이 직전 블록을 그대로 두어(#4) 서울 구가
    # 시도 계열보다 한 주 늦다 — 그때는 이번 주 행을 붙여 같은 상태를 만든다(마지막 행을 이번 주라 가정하지 않는다).
    wk = adv['weekly']['rows'][-1]['p']
    row = next((r for r in se['rows'] if r['p'] == wk), None)
    if row is None:
        row = dict(copy.deepcopy(se['rows'][-1]), p=wk)
        se['rows'].append(row)
    row['ma'][0] = 9.99
    cut = P._cut_weekly(adv, 1)
    W = cut['weekly']
    p = W['rows'][-1]['p']
    assert W['seoul']['rows'][-1]['p'] <= p and W['sgg']['rows'][-1]['p'] <= p
    body = P.draft_weekly(cut, sts, shot=False)['body']
    assert '+9.99%' not in body, '지난 회차 글에 이번 주 서울 구 값이 실렸다'
    assert P._cut_weekly(adv, 0) is adv


# ── #75 이론 초안 덮기 ────────────────────────────────────────────────────
def test_theory_main_keeps_a_filled_experience_paragraph(tmp_path, monkeypatch):
    monkeypatch.setattr(T, 'OUT', str(tmp_path))
    monkeypatch.setattr(T, 'render', lambda post: '<p>%s</p>' % T.EXP_PLACEHOLDER)
    path = tmp_path / 'theory-05.html'
    assert T.main(['5']) == 0
    path.write_text('<p>사람이 쓴 경험 문단</p>', encoding='utf-8')
    T.main(['5'])
    assert '사람이 쓴 경험 문단' in path.read_text(encoding='utf-8')
    assert (tmp_path / 'theory-05.new.html').exists()
    T.main(['5', '--force'])
    assert '사람이 쓴' not in path.read_text(encoding='utf-8')


def test_theory_main_needs_a_post_number(tmp_path, monkeypatch):
    monkeypatch.setattr(T, 'OUT', str(tmp_path))
    with pytest.raises(SystemExit):
        T.main([])
    assert not list(tmp_path.iterdir()), '인자 없이 돌렸는데 초안을 썼다'


# ── #76 1·2편 고리① ───────────────────────────────────────────────────────
def _d(rise, lo, hi):
    return {'link1_new': {'jeonse_rise': rise}, 'prose': {'l1_lo': lo, 'l1_hi': hi}}


def test_link1_values_follow_the_site_numbers():
    v = T.link1_values(_d([2.66, 1.74, -0.36], '2.7', '−0.4'))       # 2026-09 /cycle/ 정본
    assert (v['l1_lo'], v['l1_hi'], v['l1_dir'], v['l1_mid']) == ('2.7', '−0.4', '하락으로 돌아섭니다.', '')
    v = T.link1_values(_d([1.42, 1.9, 0.63], '1.4', '0.6'))                # 초안을 처음 쓸 때의 모양
    assert v['l1_dir'] == '절반 이하로 떨어집니다.' and '가운데가 가장 높은 이유' in v['l1_mid']
    with pytest.raises(SystemExit):
        T.link1_values(_d([0.5, 1.0, 1.2], '0.5', '1.2'))


def test_theory1_2_print_the_site_link1_numbers(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    pr = P.cycle_d()['prose']
    for n in (1, 2):
        post = next(p for p in T.POSTS if p['n'] == n)
        assert not re.findall(r'\d+\.\d+%%', post['body']), '%d편 본문에 손 숫자' % n
        html = T.render(post)
        assert '<b>%s%%</b>' % pr['l1_lo'] in html and '<b>%s%%</b>' % pr['l1_hi'] in html, n


def test_theory2_drops_the_middle_section_when_the_site_says_otherwise(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    D = P.cycle_d()
    D['link1_new']['jeonse_rise'] = [2.66, 1.74, -0.36]
    monkeypatch.setattr(P, 'cycle_d', lambda: D)
    assert '가운데가 가장 높은 이유' not in T.render(next(p for p in T.POSTS if p['n'] == 2))


# ── #77 3편 동조성 값 ────────────────────────────────────────────────────
def test_theory3_sync_numbers_are_the_site_prose(monkeypatch):
    monkeypatch.setattr(P, 'rivals', lambda *a, **k: None)
    monkeypatch.setattr(T, 'check_sync_claims', lambda rows=None: None)
    D = P.cycle_d()
    D['prose'] = dict(D['prose'], sync_top_v='0.1', sync_mean='0.22', seoul_sync='0.33', sync_top2='가·나')
    monkeypatch.setattr(P, 'cycle_d', lambda: D)
    html = T.render(next(p for p in T.POSTS if p['n'] == 3))
    assert '가·나은 0.1으로' in html and '평균 0.22' in html and '동조성 0.33로' in html


# ── #79 카테고리 이름 ────────────────────────────────────────────────────
def test_category_names_follow_the_closer(monkeypatch):
    cats = {'주간 시세': '새 주간 이름', '지역 공급': '새 지역 이름'}
    monkeypatch.setattr(CP, 'KIND_TO_CATEGORY', dict(CP.KIND_TO_CATEGORY, **cats))
    monkeypatch.setattr(P, 'ZONE_CAT', cats['지역 공급'])
    posts = [dict(date='2026-09-01', cat=cats['지역 공급'], url='u1', title='2026년 부산 아파트 공급물량 전망, 모자랍니다'),
             dict(date='2026-09-05', cat=cats['주간 시세'], url='u2', title='[한국부동산원] 주간 아파트가격 동향')]
    monkeypatch.setattr(CP, 'fetch_posts', lambda: posts)
    html = P.series_links('서울', 1)
    assert 'u1' in html and 'u2' in html
    assert '부산 적정 공급량' in NS.track_keywords(posts)


# ── #80 두 바퀴째 ────────────────────────────────────────────────────────
def test_second_lap_gets_new_campaign_arm_and_sentences():
    total = 16
    for k in range(1, total + 1):
        a, b = k, k + total
        assert P.title_arm(a, total) != P.title_arm(b, total), k
        assert P.title_arm(a, total) == P.title_arm(a), '한 바퀴째 팔은 이미 나간 글과 같아야 한다'
        assert 'zone_deep_%d"' % b in P.cta('세종', b, total)
        assert P.cta('세종', a, total).split('<br>')[0] != P.cta('세종', b, total).split('<br>')[0], k
        assert P.ask_cta('세종', a, total) != P.ask_cta('세종', b, total), k
        assert P.ask_cta('세종', a, total) == P.ask_cta('세종', a), '한 바퀴째 문장은 예전과 같다'


# ── #81 --track RSS 실패 ─────────────────────────────────────────────────
def test_track_fails_when_rss_is_unreadable(monkeypatch, tmp_path, capsys):
    monkeypatch.setattr(CP, 'fetch_posts', lambda: None)
    monkeypatch.setattr(NS, '_get', lambda *a, **k: {'items': [], 'total': 0})
    monkeypatch.setattr(NS, 'HIST', str(tmp_path / 'h.jsonl'))
    assert NS.track_keywords() is None
    assert NS.track_keywords([]) == []
    assert NS.main(['--track']) == 1
    assert '발행 목록(RSS)을 못 읽어' in capsys.readouterr().out


# ── #82 주간 표 지역 ─────────────────────────────────────────────────────
def test_weekly_table_names_are_model_names(monkeypatch):
    assert set(P.WEEKLY_TABLE) <= set(SZ.DISPLAY_ORDER), sorted(set(P.WEEKLY_TABLE) - set(SZ.DISPLAY_ORDER))
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    adv, sts = M.load()
    body = P.draft_weekly(adv, sts, shot=False)['body']
    table = body.split('<tbody>', 1)[1].split('</tbody>', 1)[0]
    got = re.findall(r'<tr><td>([^<]+)</td>', table)
    W = adv['weekly']
    last = W['rows'][-1]
    # 최신 주 매매값이 없는 지역(2026-04-27~07-06 전남광주 11주처럼)은 표에서 빠지는 것이 도구의 규칙이다
    assert got == [z for z in SZ.DISPLAY_ORDER if z in P.WEEKLY_TABLE and z in W['regions']
                   and last['ma'][W['regions'].index(z)] is not None]


# ── #83 더 보기 지도 칸 ──────────────────────────────────────────────────
def test_map_corner_links_to_the_map():
    maps = [m for m in P.MORE_ROTATION if '지도' in m['desc'] and str(P.SGG_N) in m['desc']]
    assert maps and all('#stats-market' in m['path'] for m in maps)


# ── #84 상·하위 3 ────────────────────────────────────────────────────────
def test_weekly_top3_is_the_site_top3(monkeypatch):
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    sido = list(MW.SIDO)
    vals = {z: 0.01 for z in sido}
    vals[sido[0]], vals[sido[1]], vals[sido[2]] = 0.3, 0.2, 0.1
    a, b, c = sido[3], sido[4], sido[5]
    vals[a] = vals[b] = -0.05                 # 원값까지 같은 하락 동률 — 순서는 /weekly/(MW.top3)를 따라야 한다
    vals[c] = -0.02
    regs = ['전국'] + sido
    row = {'p': '2026-09-21', 'ma': [0.01] + [vals[z] for z in sido], 'je': [0.0] * len(regs)}
    adv = {'weekly': {'regions': regs, 'rows': [dict(row, p='2026-09-14'), row]}}
    body = P.draft_weekly(adv, {}, shot=False)['body']
    up, dn = MW.top3([(z, vals[z]) for z in sido])
    assert '가장 많이 오른 곳은 %s입니다' % ' · '.join('<b>%s %s</b>' % (k, P.pct(v)) for k, v in up) in body
    assert '%s는 내렸습니다' % ' · '.join('%s %s' % (k, P.pct(v)) for k, v in dn) in body, body


# ── #24·#106 전세가율 기준월, #114 노후주택 기준 해 ──────────────────────────
def test_jeonse_section_uses_the_site_reference_month():
    adv, sts = M.load()
    sts = copy.deepcopy(sts)
    j = sts['전세가율']
    j['dates'].append('2099.01')
    for rg, s in j['series'].items():
        s.append(99.9 if rg == '전국' else None)   # 전국만 먼저 온 새 달
    i = I.jeonse_ref_index(j, I.JEONSE_NEED)
    html = P.extra_section(adv, sts, 0)
    assert '(%s 기준' % j['dates'][i] in html and '2099.01' not in html and '99.9%' not in html
    assert '<b>%.1f%%</b>' % j['series']['전국'][i] in html


def test_aged_section_uses_one_complete_year():
    adv, sts = M.load()
    sts = copy.deepcopy(sts)
    N = sts['노후주택30년']
    # 기준 해는 집계를 뺀 모든 시도가 찬 마지막 열이다 — 실데이터 끝 열이 일부만 찬 회차에도 이 시험이 게이트를 막지 않게
    # 기대값을 저장 계열에서 센다(dates[-1] 을 박지 않는다)
    full = [j for j in range(len(N['dates']))
            if all(j < len(v) and v[j] is not None for k, v in N['series'].items() if k not in SZ.AGG)]
    last = N['dates'][full[-1]]
    N['dates'].append('2099')
    for rg, s in N['series'].items():
        s.append(9999999 if rg == '서울' else None)
    html = P.extra_section(adv, sts, 3)
    assert '(%s년 기준)' % last in html and '9,999,999' not in html, html


# ── 월세수익률 절의 대출금리 기준월(묶음 F 제안) ──────────────────────────────
def test_loan_rate_carries_its_month():
    """변이: extra_section rot 2 에서 '(%s 기준)' 을 빼면 빨개진다. 픽스처: 2026-09-23 실값(전국 69.1 × 5.37, 대출 4.48 2026.07)."""
    adv = {'bubble': {'loan': {'v': 4.48, 'p': '2026.07'}, 'regions': ['전국'], 'conv': {'전국': 5.37}}}
    sts = {'전세가율': {'dates': ['2026.06', '2026.07'], 'series': {'전국': [69.0, 69.1]}}}
    assert '주택담보대출 금리는 <b>4.48%</b>(2026.07 기준)입니다' in P.extra_section(adv, sts, 2)
