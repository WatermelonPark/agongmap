# -*- coding: utf-8 -*-
"""홈 페이로드(data-core.js)·통계 탭 파일(data-trend.json)에 빌드 전용 데이터가 새지 않는지.

픽스처: 저장소의 실제 data.js 사본에 split_data.main() 을 tmp 경로로 돌린 산출물(생성기를 직접 시험한다 — 커밋된
data-*.json 을 읽으면 생성기를 바꿔도 다음 배치 전까지 초록이다). 실제 data.js 의 permits 에는 빌드 전용 키
city·units·done·sched·demol 이 들어 있다.
"""
import io, json, os, re, shutil, sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import split_data as S

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


@pytest.fixture(scope='module')
def out(tmp_path_factory):
    """실제 data.js 사본에 split 을 돌린 산출물 {'core_adv','core_stats','trend','core_bytes','src_adv'}."""
    d = tmp_path_factory.mktemp('split_payload')
    src = d / 'data.js'
    shutil.copyfile(os.path.join(ROOT, 'data.js'), src)
    paths = {'SRC': src, 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(paths['OUT'], encoding='utf-8').read()
    raw = io.open(src, encoding='utf-8').read()
    return {
        'core_adv': json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1)),
        'core_stats': json.loads(re.search(r'const STATS=(\{.*?\});\nwindow', core, re.S).group(1)),
        'trend': json.loads(paths['TREND'].read_text(encoding='utf-8')),
        'core_bytes': os.path.getsize(paths['OUT']),
        'src_adv': json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/',
                                        raw, re.S).group(1)),
    }


def _core(out):
    return out['core_adv'], out['core_stats']


def test_build_only_keys_are_not_shipped_to_browser(out):
    """permits 에 새 하위 키를 넣으면 아무도 안 막아준 채 브라우저 페이로드가 커진다 — permits.city(150KB)가 실제로
    그렇게 새어 data-core가 131KB -> 311KB가 됐다(2026-08-05). 거부목록이던 시절엔 생활권 잔재 meas·fwd_far가 계속
    실려 나갔고, 테스트도 같은 목록을 돌아 통과했다(2026-08-07 감사) — 이제 허용목록이라 '없어야 할 키'를 열거하지 않는다.

    2026-09-27 B11 로 permits 는 data-core 에서 빠졌고 허용목록이 실제로 걸리는 곳은 통계 탭 파일 data-trend.json 이다.
    예전 시험은 data-core 의 (늘 빈) permits 를 봐서 늘 참이었다(전수리뷰 #99).
    변이(실제로 확인): split_data.main 의 `trend_adv = strip_units(adv)` 를 `trend_adv = dict(adv)` 로 바꾸면 trend 단정이
    빨개지고(data-trend.json 250KB → 699KB), CORE_ADV 에 'permits' 를 되돌려 넣으면 core 단정이 빨개진다."""
    core_adv, _ = _core(out)
    assert 'permits' not in core_adv, 'permits 는 통계 탭 전용이다(B11) — 홈 첫 화면 페이로드에 실렸다'
    assert set(core_adv) <= set(S.CORE_ADV) | {'weekly', 'monthly'} | set(S.CORE_ONLY_ADV), sorted(core_adv)
    src_p = out['src_adv'].get('permits') or {}
    assert set(src_p) - set(S.KEEP_PERMITS), '픽스처가 평평하다 — 원천 permits 에 빌드 전용 키가 없어 허용목록을 못 잰다'
    p = (out['trend'].get('ADV') or {}).get('permits')
    assert p, '통계 탭 파일에 permits 가 없다 — 투자지표 화면이 빈다'
    extra = set(p) - set(S.KEEP_PERMITS)
    assert not extra, 'permits에 허용목록 밖 키가 통계 탭 페이로드(data-trend.json)에 있다: %s' % sorted(extra)
    assert set(p) == set(S.KEEP_PERMITS) & set(src_p), '허용목록 키가 빠졌다'
    assert 'livezone' not in core_adv, '생활권 31곳 체제 잔재 — ADV.sido로 대체됐다'
    assert 'aged30' not in core_adv, 'aged30은 폐기된 지표다'


def test_home_payload_stays_small(out):
    """분리 구조의 존재 이유가 홈 전송량이다. 상한은 고정 몫 + 월 수에 비례한 몫이다 — 월별 행(가격·준공·착공)은
    한 달에 약 600B 씩 자라므로 고정 상한을 박으면 몇 해 뒤 데이터가 앞으로 간 날 게이트가 막힌다. 달마다 750B 를 주면
    시간이 지나도 초록이고, 빌드 전용 키가 40KB 넘게 새면 빨개진다(2026-09 새로 구운 크기 약 90KB, 상한 약 132KB).
    변이(실제로 확인): 2026-08-05 사고 모양 — CORE_ADV 에 'permits' 를 넣고 core 쪽 strip_units 를 빼면 554KB 로 빨개진다."""
    months = len(((out['core_adv'].get('monthly') or {}).get('rows')) or [])
    assert months, '월별 가격 행이 없다'
    limit = 45_000 + 750 * months
    n = out['core_bytes']
    assert n < limit, 'data-core.js %d bytes > %d — 빌드 전용 데이터가 샜는지 확인할 것' % (n, limit)


def test_table_stats_are_trimmed_to_the_table_window(out):
    """준공·착공은 표가 그리는 구간·지역만 실어야 한다. 전 구간 22개 지역이면
    65KB인데 잘라 쓰면 절반 아래다. 점수(ADV.sido)는 이미 계산돼 있으므로 홈이
    옛 구간을 다시 읽을 일이 없다."""
    _, stats = _core(out)
    for k in S.TABLE_STATS:
        s = stats.get(k)
        assert s, '홈 표가 쓰는 %s가 core에 없다' % k
        assert s['dates'][0] >= S.TABLE_FROM, '%s가 %s 이전까지 실렸다' % (k, S.TABLE_FROM)
        extra = set(s['series']) - S.TABLE_REGIONS
        assert not extra, '%s에 표에 없는 지역이 실렸다: %s' % (k, sorted(extra))


def test_core_carries_price_rows_for_the_table(out):
    """표의 과거 칸 3등분(매매·전세·월세)이 이 데이터로 칠해진다.
    통계 탭이 열리면 loadFullData가 전체 monthly로 덮어쓴다(상위 키 통째 교체)."""
    adv, _ = _core(out)
    mo = adv.get('monthly') or {}
    assert mo.get('rows'), 'monthly가 core에 없다 — 표의 가격 색이 전부 빠진다'
    # 표가 그리는 지역(TABLE_REGIONS = sido_zones.ORDER)과 가격 행의 지역이 같아야 칸이 빠짐없이
    # 칠해진다. 예전엔 `== 19` 리터럴이라 모델이 원천 통합을 반영해 바뀌면 이 줄이 배치를 막았다.
    # 변이: 모델에서 지역 하나를 빼거나(ORDER) 가격 행 지역에서 하나를 빼면 빨개진다.
    regions = mo.get('regions') or []
    assert len(regions) == len(set(regions)), '가격 행 지역이 중복됐다'
    assert set(regions) == set(S.TABLE_REGIONS), (
        '표 지역과 가격 지역이 다르다 — 빠짐 %s · 남음 %s'
        % (sorted(set(S.TABLE_REGIONS) - set(regions)), sorted(set(regions) - set(S.TABLE_REGIONS))))
    for f in ('ma', 'je', 'wo'):
        assert f in mo['rows'][0], 'monthly.rows에 %s가 없다' % f
    for heavy in ('seoul', 'sgg'):
        assert heavy not in mo, 'monthly.%s는 홈이 안 쓴다(합쳐 694KB)' % heavy
    # ⚠️ monthly는 '2017-01', STATS는 '2017.01'로 구분자가 다르다. 그대로 비교하면
    # '-'(0x2D) < '.'(0x2E)라 2017년이 통째로 잘린다(2026-08-06 실제로 그랬다).
    assert mo['rows'][0]['p'].replace('-', '.') >= S.TABLE_FROM
