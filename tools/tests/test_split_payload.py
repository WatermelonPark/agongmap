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


# 홈 페이로드(data-core.js) 예산 — 자라지 않는 몫엔 고정 상한, 시간에 따라 자라는 몫엔 칸당 상한(전수리뷰 T3-13).
FIXED_CAP = 45_000   # 자라지 않는 몫: 시도 판정 카드·주간 마지막 회차·블로그·N 배지·화면 이름·휴일·껍데기 — 2026-10 실측 31,919B
ROW_CAP = 600        # monthly.rows 한 행 평균(조사월 + 매매·전세·월세 × 시도) — 실측 평균 455B·최대 487B
AGG_CAP = 400        # monthly.agg 한 칸 평균(분기·연 하나의 매매·전세·월세 × 시도) — 실측 평균 286B·최대 316B
CELL_CAP = 12        # STATS 준공·착공 한 칸(한 달 × 한 지역, 날짜 몫 포함) — 실측 7.0B
ROW_KEYS, AGG_KEYS = {'p', 'ma', 'je', 'wo'}, {'ma', 'je', 'wo'}   # 홈 표(tbAgg·가격 3등분)가 읽는 칸 모양


def _bytes(o):
    """data-core.js 가 싣는 모양(split_data.main 의 dump — 빈칸 없는 JSON)의 바이트 수."""
    return len(json.dumps(o, ensure_ascii=False, separators=(',', ':')).encode('utf-8'))


def test_home_payload_stays_small(out):
    """분리 구조의 존재 이유가 홈 전송량이다. 상한을 두 갈래로 잰다 — 시간에 따라 자라는 몫(가격 행 monthly.rows, 분기·연 합
    monthly.agg, 표의 STATS 준공·착공)은 칸 수에 비례한 칸당 상한, 나머지(자라지 않는 몫)는 고정 상한 FIXED_CAP. 빌드 전용 키가
    새면 고정 몫이 넘쳐 빨개지고, 데이터가 앞으로 가는 것만으로는 빨개지지 않는다.

    2026-10 실측(저장소 data.js 사본에 split_data): data-core.js 129,862B = 고정 몫 31,919 + monthly.rows 53,192(117행, 행당 455B)
    + monthly.agg 13,740(분기 39·연 9 = 48칸, 칸당 286B) + STATS 준공·착공 31,011(2 × 116달 × 19곳 = 4,408칸, 칸당 7.0B). 한 달에
    약 800B 씩 자라지만 가격 행은 배치가 120개월 창(update_adv_data CONF months_hist)으로 자르고, 준공·착공은 TABLE_FROM 부터 끝없이
    자란다. 예전 상한(45,000 + 750 × 가격 행 수)은 가격 행이 120에서 멈춘 뒤 135,000B 로 굳어, 누출 없이 데이터 전진만으로 2028년
    봄(+18개월)에 게이트가 데이터 커밋을 막을 참이었고(그때 여유 2.9KB — 독스트링은 '여유 40KB'로 낡아 있었다), 정당한 3KB 키
    하나도 '빌드 전용 데이터가 샜다'로 오진했다.

    칸에 값이 새로 붙는 누출(가격 행마다 시도 값 한 줄)은 칸 모양(ROW_KEYS·AGG_KEYS)이 먼저 잡고, 칸당 상한은 값 모양이 바뀌는
    것(반올림을 빼 꼬리가 길어짐 등)을 잡는다.

    변이(각각 실제로 확인): 2026-08-05 사고 모양 — CORE_ADV 에 'permits' 를 넣고 core 쪽 strip_units 를 빼면 고정 몫 단정이 빨개진다
          (자라지 않는 몫 486,474B). core 의 주간 시군구를 마지막 한 줄이 아니라 통째로 실으면 고정 몫이(511,265B), core 가격 행마다
          시도 값 한 줄(19칸)을 더 실으면 칸 모양 단정이, 가격 행 값을 소수 넷째 자리 대신 길게(_r4 를 v + 1e-9 로) 실으면 행당
          상한이 빨개진다. 가격·준공·착공을 12·17·18·60·120개월 앞당긴 data.js 로는 이 시험이 모두 초록이다(옛 상한은 +18개월
          135,182B > 135,000B 에서 빨강).
    픽스처: 저장소의 실제 data.js 사본에 split_data.main() 을 tmp 경로로 돌린 data-core.js(모듈 픽스처 out).
    """
    adv, stats = _core(out)
    mo = adv.get('monthly') or {}
    rows, agg = mo.get('rows') or [], mo.get('agg') or {}
    agg_cells = sum(len(v) for v in agg.values())
    tbl = [stats[k] for k in S.TABLE_STATS if k in stats]
    cells = sum(len(s['dates']) * len(s['series']) for s in tbl)
    assert rows and agg_cells and cells, '자라는 몫이 비었다 — 칸당 상한이 아무것도 재지 않는다'
    shape = sorted({tuple(sorted(r)) for r in rows if set(r) != ROW_KEYS}
                   | {tuple(sorted(c)) for v in agg.values() for c in v.values() if set(c) != AGG_KEYS})
    assert not shape, '가격 행·합 칸에 홈이 읽지 않는 값이 실렸다: %s' % shape[:3]
    grow = {'monthly.rows': (_bytes(rows), ROW_CAP * len(rows)),
            'monthly.agg': (_bytes(agg), AGG_CAP * agg_cells),
            'STATS 준공·착공': (sum(_bytes(s) for s in tbl), CELL_CAP * cells)}
    over = ['%s %dB > %dB' % (k, n, cap) for k, (n, cap) in grow.items() if n > cap]
    assert not over, '칸마다 싣는 양이 늘었다 — 값 모양(자릿수)이 바뀌었거나 칸에 빌드 전용 값이 붙었는지 확인할 것: %s' % over
    fixed = out['core_bytes'] - sum(n for n, _ in grow.values())
    assert 0 < fixed < FIXED_CAP, ('data-core.js 의 자라지 않는 몫 %dB > %dB — 빌드 전용 데이터가 샜는지 확인할 것'
                                   % (fixed, FIXED_CAP))


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
