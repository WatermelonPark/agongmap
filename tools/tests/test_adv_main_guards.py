# -*- coding: utf-8 -*-
"""update_adv_data.main()의 방어선(역행·축소·전량 실패)과 기본통계 병합 규칙의 시나리오 시험.

2026-09-23 전체 점검 변이 시험에서 아래 방어선이 `if False` 로 꺼져도 전체 시험이 초록이었다 —
주간·월간 역행 가드, 인허가 행 수 축소 가드, 시도 지역 수 축소 가드, 전량 실패 rc=3 문턱,
월세 보존(_keep_wolse), merge_prov의 전월 기준·확정값 보호, merge_basic의 잠정(p) 꼬리표 제거.

원천 호출 없이 돈다. main()은 test_adv_update_fixes.test_main_records_soft_failures_without_changing_rc
와 같은 방식으로 돌린다 — 저장소 data.js를 tmp_path에 복사해 DATA·ROOT를 그쪽으로 돌리고, 각 fetch
함수를 **그 사본의 실제 ADV를 잘라 만든 응답**으로 바꿔 끼운다. 기대값도 같은 사본에서 뽑으므로 데이터가
매주 바뀌어도 시험은 낡지 않는다. 각 시험 독스트링에 ① 변이(실제로 적용해 빨개짐 확인)와 ② 픽스처가
재현하는 실제 상태를 적었다.
"""
import copy
import io
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import update_adv_data as U  # noqa: E402
import sido_zones            # noqa: E402

REPO_DATA = U.DATA


def _boom(*a, **k):
    raise RuntimeError('R-ONE err 99: 픽스처')


class _Run:
    """tmp 사본 위에서 main()을 돌리는 하네스. before = 실행 전 ADV(사본에서 읽은 실제 값)."""

    def __init__(self, monkeypatch, tmp_path):
        self.mp, self.tmp = monkeypatch, tmp_path
        data = tmp_path / 'data.js'
        data.write_text(io.open(REPO_DATA, encoding='utf-8').read(), encoding='utf-8')
        monkeypatch.setattr(U, 'DATA', str(data))
        monkeypatch.setattr(U, 'ROOT', str(tmp_path))
        monkeypatch.setattr(U, 'KEY', 'x')
        monkeypatch.setattr(U, 'ECOS_KEY', '')
        monkeypatch.setattr(U, 'SUPPLY_STALLED', [])
        monkeypatch.setattr(U.time, 'sleep', lambda s: None)
        for fn in ('fetch_weekly', 'fetch_monthly', 'fetch_permits', 'fetch_holidays', 'fetch_bubble'):
            monkeypatch.setattr(U, fn, _boom)
        monkeypatch.setattr(U, 'update_basic', lambda failed=None: [])
        monkeypatch.setattr(sys, 'argv', ['update_adv_data.py', '--update'])
        self.before = self.adv()
        # 시도 점수·입주물량은 STATS에서 다시 계산한다 — 기본은 '저장분과 같음'(변화 없음)
        sd, occ = self.before['sido'], self.before['occupancy']
        monkeypatch.setattr(sido_zones, 'calc', lambda st: copy.deepcopy(sd))
        monkeypatch.setattr(sido_zones, 'supply_rows', lambda st: {'rows': copy.deepcopy(occ.get('rows'))})

    def adv(self):
        return U.read_current_adv()[3]

    def set(self, fn, value):
        """fetch 함수가 매 호출 새 사본을 돌려주게 한다(main이 응답을 제자리에서 고친다)."""
        self.mp.setattr(U, fn, lambda *a, **k: copy.deepcopy(value))

    def quiet(self):
        """주간·월간·인허가·공휴일이 저장분과 같은 값을 돌려주는 조용한 회차(새 데이터 없음, 실패 없음)."""
        b = self.before
        self.set('fetch_weekly', b['weekly'])
        self.set('fetch_monthly', b['monthly'])
        self.set('fetch_permits', b['permits']['rows'])
        self.set('fetch_holidays', b['holidays'])

    def save(self, adv):
        U.write_adv(adv)
        self.before = self.adv()

    def main(self):
        U.main()
        return self.adv()

    def file(self, name):
        return (self.tmp / name).read_text(encoding='utf-8').split(',')


def _truncated(blk, lo, hi):
    """시도·서울구·시군구 블록의 rows를 같은 구간으로 자른 응답(열 목록·note는 저장분 그대로)."""
    out = copy.deepcopy(blk)
    out['rows'] = out['rows'][lo:hi]
    for part in ('seoul', 'sgg'):
        if out.get(part):
            out[part]['rows'] = out[part]['rows'][lo:hi]
    return out


def _bump(row, field='ma'):
    """소급 수정 한 칸 — 첫 지역 값을 0.01 올린다."""
    row[field] = list(row[field])
    row[field][0] = round((row[field][0] or 0) + 0.01, 4)
    return row


# ── 1. 주간·월간 역행 가드 ──────────────────────────────────────────────────
@pytest.mark.parametrize('kind,fn', [('weekly', 'fetch_weekly'), ('monthly', 'fetch_monthly')])
def test_partial_response_never_rolls_back_the_latest_period(monkeypatch, tmp_path, kind, fn):
    """R-ONE이 최근 몇 주(달)를 빠뜨린 부분 응답을 줘도 저장된 최신 주(달)와 서울구·시군구 상세를 지킨다.
    응답 안의 소급 수정은 받아들인다.

    변이: main()의 주간 역행 가드 `if weekly['rows'] and weekly['rows'][-1]['p'] < cur_last:` 를
          `if False:` 로 바꾸면 weekly 경우가, 월간 가드 `if monthly['rows'] and mo_last and ...` 를
          `if False:` 로 바꾸면 monthly 경우가 빨개진다(둘 다 확인 — 최신 3주·2달이 사라지고 상세가 옛 구간이 된다).
    픽스처: 실제 저장분에서 최근 20주(14달)를 받되 끝 3주(2달)가 빠진 R-ONE 부분 응답, 첫 행에 소급 수정 한 칸.
    """
    run = _Run(monkeypatch, tmp_path)
    cur = run.before[kind]
    tail = 3 if kind == 'weekly' else 2
    resp = _truncated(cur, -(20 if kind == 'weekly' else 14), -tail)
    _bump(resp['rows'][0])
    run.set(fn, resp)
    got = run.main()[kind]
    assert [r['p'] for r in got['rows']] == [r['p'] for r in cur['rows']], '최신 구간이 사라지거나 깊이가 줄었다'
    assert got['rows'][-tail:] == cur['rows'][-tail:]
    assert got['seoul'] == cur['seoul'] and got['sgg'] == cur['sgg'], '서울구·시군구 상세가 옛 구간으로 바뀌었다'
    revised = {r['p']: r for r in got['rows']}[resp['rows'][0]['p']]
    assert revised['ma'] == resp['rows'][0]['ma'], '응답의 소급 수정이 반영되지 않았다'
    assert any(t.startswith(('주간소급수정', '월간소급수정')) for t in run.file('.stats_changed'))


def test_rows_without_wolse_keep_the_saved_wolse(monkeypatch, tmp_path):
    """월간 응답 행에 월세(wo)가 없으면 저장분의 월세를 살린다 — 시도·서울구·시군구 모두.

    변이: `_keep_wolse` 본문을 `return` 한 줄로 바꾸면(no-op) 최근 14달 월세가 통째로 지워져, main()의
          `for _p in ('sgg', 'seoul'):` 를 `for _p in ():` 로 바꾸면 서울구·시군구 월세만 지워져 빨개진다(둘 다 확인).
    픽스처: 2026-07 KOSIS 폴백 사고와 같은 모양 — 최근 14달을 다 주되 매매·전세만 있고 월세가 없는 응답.
            매매 한 칸 소급 수정이 있어 저장 경로가 실제로 돈다.
    """
    run = _Run(monkeypatch, tmp_path)
    cur = run.before['monthly']
    resp = _truncated(cur, -14, None)
    for blk in (resp, resp['seoul'], resp['sgg']):
        for r in blk['rows']:
            r.pop('wo', None)
    _bump(resp['rows'][-1])
    run.set('fetch_monthly', resp)
    got = run.main()['monthly']
    assert got['rows'][-1]['ma'] == resp['rows'][-1]['ma'], '저장 경로가 돌지 않았다 — 시험이 비어 돈다'
    for part, g, c in (('시도', got, cur), ('서울구', got['seoul'], cur['seoul']), ('시군구', got['sgg'], cur['sgg'])):
        saved = {r['p']: r.get('wo') for r in c['rows']}
        assert all(isinstance(saved[r['p']], list) for r in g['rows'][-14:]), '픽스처 저장분에 월세가 없다'
        for r in g['rows']:
            assert r.get('wo') == saved[r['p']], '%s %s 월세가 사라졌다' % (part, r['p'])


# ── 2. 인허가 행 수 축소 가드 ────────────────────────────────────────────────
def test_permits_shorter_response_is_not_adopted(monkeypatch, tmp_path):
    """인허가 응답의 반기 행이 저장분보다 적으면 채택하지 않는다(소급 수정이 섞여 있어도).
    같은 길이면 채택한다(대조군).

    변이: main()의 `if rows and len(rows) >= len(adv['permits']['rows']) and differs(...)` 에서 길이 조건을
          지우면 옛 4개 반기가 잘린 표가 실려 빨개진다(확인).
    픽스처: KOSIS가 옛 연도 누계 조회에서 '데이터 없음'을 내 fetch_permits가 최근 반기만 돌려준 회차 —
            실제 저장분 rows에서 앞 4행이 빠지고 마지막 반기 값이 소급 수정된 응답.
    """
    run = _Run(monkeypatch, tmp_path)
    cur = run.before['permits']
    short = copy.deepcopy(cur['rows'][4:])
    short[-1]['v'][0] += 1
    run.set('fetch_permits', short)
    got = run.main()['permits']
    assert got['rows'] == cur['rows'] and got['ref'] == cur['ref']
    assert not any(t.startswith('permits') for t in run.file('.stats_changed') if t)

    same = copy.deepcopy(cur['rows'])
    same[-1]['v'][0] += 1
    run.set('fetch_permits', same)
    got = run.main()['permits']
    assert got['rows'] == same, '같은 길이의 소급 수정은 채택해야 한다'


# ── 3. 시도 지역 수 축소 가드 ────────────────────────────────────────────────
@pytest.mark.parametrize('first_seed', [False, True], ids=['saved', 'first-seed'])
def test_sido_result_missing_a_region_is_not_adopted(monkeypatch, tmp_path, first_seed):
    """시도 점수 결과에서 지역이 하나라도 빠지면 ADV.sido도 occupancy도 쓰지 않고 'sido-shrink'를 남긴다.
    저장분이 비어 있는 첫 시딩(직전 0곳)에서도 모델 지역 수(len(sido_zones.ORDER))로 막는다.

    변이: 가드 `if n_new < want or (n_old and n_new < n_old):` 를 `if False:` 로 바꾸면 두 경우가,
          `if n_old and n_new < n_old:` 로 바꾸면(절대 기준 제거) first-seed 경우가, 가드 뒤의
          `raise RuntimeError('sido 가드에 걸려 …')` 를 지우면 occupancy 단정이 빨개진다(셋 다 확인).
    픽스처: 새 주차·달이 없는 조용한 회차(주간·월간·인허가·공휴일이 저장분 그대로)에, 통계 부분 응답으로
            sido_zones.calc가 한 지역(모델의 마지막 시도)을 빼고 missing에 적은 결과. 입주물량 표는 이번
            회차에 달라진 값(마지막 행 제거)을 낸다.
    """
    run = _Run(monkeypatch, tmp_path)
    real = copy.deepcopy(run.before['sido'])
    if first_seed:
        adv = run.adv()
        adv['sido'] = dict(adv['sido'], zones=[])
        run.save(adv)
    base = run.before
    run.quiet()
    drop = [z for z in sido_zones.ORDER if z not in sido_zones.AGG][-1]
    shrunk = dict(copy.deepcopy(real), zones=[z for z in real['zones'] if z['z'] != drop], missing=[drop])
    assert len(shrunk['zones']) == len(sido_zones.ORDER) - 1
    monkeypatch.setattr(sido_zones, 'calc', lambda st: copy.deepcopy(shrunk))
    occ_rows = base['occupancy']['rows'][:-1]
    monkeypatch.setattr(sido_zones, 'supply_rows', lambda st: {'rows': copy.deepcopy(occ_rows)})
    got = run.main()
    assert got['sido'] == base['sido'], '빠진 결과가 채택됐다 — /zone/ 페이지가 지워진다'
    assert got['occupancy'] == base['occupancy'], '가드에 걸린 회차인데 입주물량을 썼다'
    assert 'sido-shrink' in run.file('.fetch_failed')


# ── 4. 전량 실패 rc=3 ────────────────────────────────────────────────────────
def test_all_main_sources_down_exits_3(monkeypatch, tmp_path):
    """주요 원천 다섯 갈래(주간·월간·인허가·공휴일·버블)가 모두 죽고 바뀐 것이 없으면 rc=3으로 멈춘다.
    같은 실패라도 기본통계에서 바뀐 것이 있으면 멈추지 않는다.

    변이: 문턱 `len(failed) >= 5` 를 `>= 6` 으로 바꾸면 첫 단정이(SystemExit 없음), `and not changed` 를
          지우면 둘째 단정이 빨개진다(둘 다 확인). 넷만 죽은 회차가 rc=0인 것은
          test_main_records_soft_failures_without_changing_rc 가 본다.
    픽스처: KOSIS·R-ONE·ECOS·공공데이터포털이 모두 예외를 낸 회차(ECOS 키는 있다), 시도 점수는 저장분과 같다.
    """
    run = _Run(monkeypatch, tmp_path)
    monkeypatch.setattr(U, 'ECOS_KEY', 'x')
    with pytest.raises(SystemExit) as e:
        run.main()
    assert e.value.code == 3
    assert set(run.file('.fetch_failed')) >= {'weekly', 'monthly', 'permits', 'holidays', 'bubble'}

    monkeypatch.setattr(U, 'update_basic', lambda failed=None: ['준공(3)'])
    run.main()   # SystemExit 없이 끝나야 한다


# ── 5. 기본통계 잠정치(merge_prov)·확정치(merge_basic) ───────────────────────
NAME = '매매지수'          # KOSIS가 확정 지수와 잠정 증감률을 따로 주는 계열
DEC = U.BASIC_CONF[NAME]['dec']
RATE = 0.37


def _slice(end_pred):
    """실제 저장분(STATS[NAME])에서 확정 라벨 3달을 잘라 온다. end_pred(ym)가 참인 마지막 확정 달로 끝난다."""
    D = U.read_current_stats()[NAME]
    idx = [i for i, d in enumerate(D['dates'])
           if 'p' not in d and i >= 2 and end_pred(U._label_ym(d))]
    e = idx[-1]
    return {'dates': D['dates'][e - 2:e + 1],
            'series': {r: v[e - 2:e + 1] for r, v in D['series'].items()}}


def _next(ym):
    return (ym[0] + 1, 1) if ym[1] == 12 else (ym[0], ym[1] + 1)


def _regions(D):
    return [r for r, v in D['series'].items() if v[-1] is not None and v[-2] is not None]


@pytest.mark.parametrize('case', ['mid-year', 'year-wrap'])
def test_prov_rate_applies_to_the_previous_month_index(case):
    """잠정 증감률은 **바로 전월** 지수에 곱한다. 12월 → 다음 해 1월도 같다.

    변이: merge_prov 의 `pi = key2idx[prev_ym]` 를 `pi = key2idx[prev_ym] - 1` 로 바꾸면 두 경우가,
          `prev = ym[0] - 1 if ym[1] == 1 else ym[0]` 를 `prev = ym[0]` 으로 바꾸면 year-wrap 경우가
          (전월을 못 찾아 잠정 달이 안 생김) 빨개진다(둘 다 확인).
    픽스처: 실제 저장분 매매지수의 마지막 확정 3달(mid-year) · 가장 최근 12월로 끝나는 확정 3달(year-wrap),
            그 다음 달의 KOSIS 잠정 증감률(모든 지역 +0.37%).
    """
    D = _slice((lambda ym: True) if case == 'mid-year' else (lambda ym: ym[1] == 12))
    nxt = _next(U._label_ym(D['dates'][-1]))
    regions = _regions(D)
    f = 1 + RATE / 100
    assert any(round(D['series'][r][-1] * f, DEC) != round(D['series'][r][-2] * f, DEC) for r in regions), \
        '픽스처의 전월·전전월이 같으면 기준 달 오류를 못 가린다'
    n = U.merge_prov(D, {nxt: {r: RATE for r in regions}}, DEC)
    assert D['dates'][-1] == '%d.%02d p)' % nxt
    assert n == len(regions)
    for r in regions:
        assert D['series'][r][-1] == round(D['series'][r][-2] * f, DEC), r


def test_prov_rate_never_overwrites_a_confirmed_month():
    """확정 지수가 이미 있는 달에 잠정 증감률이 오면 건드리지 않는다. 잠정 달은 새 증감률로 고친다.

    변이: merge_prov 의 확정 라벨 분기에서 `continue` 를 `pass` 로 바꾸면 확정 값이 잠정 계산값으로 덮이고
          라벨에 ' p)' 가 붙어 빨개진다(확인).
    픽스처: KOSIS 잠정 표가 확정 표보다 늦게 내려가 이미 확정된 달(저장분 마지막 확정 달)의 잠정 증감률을
            다시 준 회차 — 실제 저장분 매매지수 마지막 확정 3달.
    """
    D = _slice(lambda ym: True)
    snap = copy.deepcopy(D)
    last = U._label_ym(D['dates'][-1])
    regions = _regions(D)
    assert U.merge_prov(D, {last: {r: RATE for r in regions}}, DEC) == 0
    assert D == snap, '확정 달이 잠정값으로 덮였다'
    # 잠정 달은 다음 회차 증감률로 고친다(같은 달이 두 번 붙지 않는다)
    nxt = _next(last)
    U.merge_prov(D, {nxt: {r: RATE for r in regions}}, DEC)
    U.merge_prov(D, {nxt: {r: 2 * RATE for r in regions}}, DEC)
    assert D['dates'].count('%d.%02d p)' % nxt) == 1 and len(D['dates']) == 4
    r0 = regions[0]
    assert D['series'][r0][-1] == round(D['series'][r0][-2] * (1 + 2 * RATE / 100), DEC)


def test_confirmed_value_replaces_the_provisional_label():
    """잠정 달('YYYY.MM p)')에 확정 지수가 도착하면 같은 칸에서 값을 바꾸고 꼬리표를 뗀다(칸이 늘지 않는다).

    변이: merge_basic 의 `D['dates'][i] = plain   # 잠정(p) 꼬리표 제거` 줄을 `pass` 로 바꾸면 라벨이 'p)' 로
          남아 빨개진다(확인) — 그러면 다음 회차 merge_prov 가 확정 달을 잠정값으로 다시 덮는다.
    픽스처: 실제 저장분 매매지수 마지막 확정 3달 + merge_prov 가 만든 다음 달 잠정 칸(저장분 끝의 '… p)' 칸과
            같은 상태), 그리고 다음 회차 KOSIS 확정 표가 그 달 값을 준 응답.
    """
    D = _slice(lambda ym: True)
    nxt = _next(U._label_ym(D['dates'][-1]))
    regions = _regions(D)
    U.merge_prov(D, {nxt: {r: RATE for r in regions}}, DEC)
    assert D['dates'][-1].endswith('p)')
    confirmed = {r: round(D['series'][r][-2] + 1.23, DEC) for r in regions}
    assert U.merge_basic(D, {nxt: confirmed}) == len(regions)
    assert D['dates'][-1] == '%d.%02d' % nxt and len(D['dates']) == 4
    for r in regions:
        assert D['series'][r][-1] == confirmed[r]
    # 꼬리표가 떨어졌으므로 늦게 온 잠정 증감률이 확정값을 덮지 않는다
    U.merge_prov(D, {nxt: {r: RATE for r in regions}}, DEC)
    assert D['dates'][-1] == '%d.%02d' % nxt and D['series'][regions[0]][-1] == confirmed[regions[0]]
