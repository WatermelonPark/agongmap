# -*- coding: utf-8 -*-
"""split_data.py가 쪼갠 파일들이 **원천 data.js와 같은 값**을 싣는지(크기·허용 키가 아니라 내용).

test_split_payload는 저장소에 커밋된 data-core.js의 크기·허용 키만 본다. 그래서 홈 주간 배너가
2023년 첫 주를 보여 주거나(rows[:1]), 전세 칸에 매매 값이 실리거나, 기본통계에서 미분양이 빠지거나,
trend가 가장 오래된 12행을 싣거나, 지연 파일 data-size.json이 비어도 모두 초록이었다
(2026-09-23 전체 점검 변이 시험).

픽스처: 저장소의 실제 data.js를 tmp_path에 복사해 split_data.main()을 그 사본에 돌린다(저장소에는
쓰지 않는다). 기대값은 모두 같은 사본의 ADV·STATS에서 뽑는다 — 숫자 리터럴을 두지 않으므로
데이터가 매주 바뀌어도 시험은 낡지 않는다.
"""
import io
import json
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import split_data as S  # noqa: E402

REPO_DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'data.js')


def _read_src(path):
    src = io.open(path, encoding='utf-8').read()
    adv = json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', src, re.S).group(1))
    stats = json.loads(re.search(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', src, re.S).group(1))
    return adv, stats


@pytest.fixture(scope='module')
def split(tmp_path_factory):
    """실제 data.js 사본에 split을 돌리고 (원천 ADV, 원천 STATS, 산출물 dict)를 돌려준다."""
    d = tmp_path_factory.mktemp('split')
    src = d / 'data.js'
    shutil.copyfile(REPO_DATA, src)
    paths = {'SRC': src, 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(paths['OUT'], encoding='utf-8').read()
    out = {
        'core_adv': json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1)),
        'core_stats': json.loads(re.search(r'const STATS=(\{.*?\});\nwindow', core, re.S).group(1)),
    }
    for k in ('REST', 'TREND', 'SGG', 'SIZE'):
        out[k.lower()] = json.loads(paths[k].read_text(encoding='utf-8'))
    adv, stats = _read_src(str(src))
    return adv, stats, out


def test_home_weekly_carries_the_newest_week(split):
    """홈 주간 배너·히어로 지도는 '가장 최근 주' 한 행만 받는다.

    변이: split_data의 `w['rows'][-1:]` 를 `w['rows'][:1]` 로 바꾸면 156주 전(2023년) 행이 실려
          빨개진다(확인). 시군구 `sgg['rows'][-1:]` 를 `[:1]` 로 바꿔도 빨개진다(확인).
    픽스처: 실제 data.js — ADV.weekly.rows 가 오래된 주 → 최신 주 순으로 156행, sgg 도 같은 순서.
    """
    adv, _, out = split
    wk = out['core_adv']['weekly']
    src_rows = adv['weekly']['rows']
    newest = max(src_rows, key=lambda r: r['p'])
    assert len(src_rows) > 1 and src_rows[0]['p'] != newest['p'], '픽스처가 한 주뿐이면 변이를 못 가린다'
    assert wk['rows'] == [newest]
    src_sgg = adv['weekly']['sgg']['rows']
    assert wk['sgg']['rows'] == [max(src_sgg, key=lambda r: r['p'])]
    assert wk['sgg']['codes'] == adv['weekly']['sgg']['codes']


def test_home_monthly_fields_map_to_their_own_series(split):
    """홈 통합표의 매매·전세·월세 칸(ma·je·wo)은 원천의 같은 이름 계열을 소수 2자리로 싣는다.

    변이: core monthly 행을 만드는 곳에서 `'je': _r2(r.get('je'))` 를 `_r2(r.get('ma'))` 로 바꾸면
          전세 칸이 매매 값이 되어 빨개진다(확인).
    픽스처: 실제 data.js ADV.monthly — 매매·전세·월세 변동률이 지역마다 서로 다르다(아래 전제 단정으로 확인).
    """
    adv, _, out = split
    mo = out['core_adv']['monthly']
    src = {r['p']: r for r in adv['monthly']['rows']}
    assert mo['regions'] == adv['monthly']['regions']
    want_ps = [r['p'] for r in adv['monthly']['rows'] if r['p'].replace('-', '.') >= S.TABLE_FROM]
    assert [r['p'] for r in mo['rows']] == want_ps, '표 구간(TABLE_FROM~)의 달이 빠지거나 더 실렸다'
    last = src[want_ps[-1]]
    assert S._r2(last['ma']) != S._r2(last['je']), '픽스처의 매매·전세가 같으면 뒤바뀜을 못 가린다'
    for r in mo['rows']:
        for f in ('ma', 'je', 'wo'):
            assert r[f] == S._r2(src[r['p']].get(f)), '%s %s가 원천 %s와 다르다' % (r['p'], f, f)


def test_rest_carries_every_basic_series_except_lazy_ones(split):
    """기본통계 화면은 data-rest.json의 STATS를 쓴다 — 지연 파일로 뺀 규모별만 빼고 전부, 원천 그대로.

    변이: rest_stats 에서 '미분양' 을 빼면(예: `if k not in lazy_stats and k != '미분양'`) 빨개진다(확인).
    픽스처: 실제 data.js STATS(매매지수~아파트멸실, 규모별 포함).
    """
    _, stats, out = split
    rest = out['rest']['STATS']
    want = {k: v for k, v in stats.items() if k not in S.LAZY_STATS}
    assert set(rest) == set(want), '빠진 계열 %s · 더 실린 계열 %s' % (
        sorted(set(want) - set(rest)), sorted(set(rest) - set(want)))
    for k, v in want.items():
        assert rest[k] == v, '%s 값이 원천과 다르다' % k
    assert set(rest) & set(S.LAZY_STATS) == set(), '지연 계열이 rest에도 실렸다(중복 전송)'


def test_size_file_carries_the_lazy_series(split):
    """data-size.json은 규모별 피벗 전체를 싣는다(기본통계에서 '규모별'을 누른 사람이 받는다).

    변이: SIZE 파일을 `dump({'STATS': {}})` 로 쓰면 빨개진다(확인).
    픽스처: 실제 data.js STATS['규모별'](지표4×규모6 피벗).
    """
    _, stats, out = split
    size = out['size']['STATS']
    lazy = [k for k in S.LAZY_STATS if k in stats]
    assert lazy, '픽스처에 지연 계열이 없다 — 시험이 비어 돈다'
    assert size == {k: stats[k] for k in lazy}
    assert set(S.LAZY_FILES[os.path.basename(S.SIZE)]) == set(S.LAZY_STATS)


def test_trend_keeps_the_newest_district_rows_and_sgg_keeps_all(split):
    """통계 탭 그래프(trend)는 시군구·서울구의 **최근** TREND_SGG_KEEP행만, data-sgg.json은 전체를 싣는다.

    변이: trend 자르기를 `sec['rows'][:TREND_SGG_KEEP]` 로 바꾸면 가장 오래된 12행이 실려 빨개진다(확인).
    픽스처: 실제 data.js — weekly 156행·monthly 120행씩 쌓인 sgg·seoul 블록(모두 12행보다 길다).
    """
    adv, _, out = split
    trend, sgg = out['trend']['ADV'], out['sgg']['ADV']
    n = S.TREND_SGG_KEEP
    checked = 0
    for k in ('weekly', 'monthly'):
        for part in ('sgg', 'seoul'):
            rows = adv[k][part]['rows']
            assert len(rows) > n, '픽스처가 짧으면 자르기를 못 본다'
            assert trend[k][part]['rows'] == rows[-n:], '%s.%s trend가 최근 %d행이 아니다' % (k, part, n)
            assert trend[k][part]['rows'][-1]['p'] == max(r['p'] for r in rows)
            assert sgg[k][part]['rows'] == rows, '%s.%s 전체가 data-sgg.json에 없다' % (k, part)
            checked += 1
        # 시도 행은 자르지 않는다(그래프 3년 탭)
        assert trend[k]['rows'] == adv[k]['rows']
    assert checked == 4
