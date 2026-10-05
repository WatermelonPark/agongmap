# -*- coding: utf-8 -*-
"""주간 발표 일정(조사일·발표일·다음 발표·반영 대기) — 홈 마케팅 검수 A2(2026-09-27).

같은 규칙이 세 곳에 있다: 홈 주간 격자 머리줄·통계 탭 rel-week(home-app.js weeklyRelease), /weekly/ 머리줄
(make_weekly_page → tools/weekly_release.py), 감시(check_freshness 의 GRACE_WEEKLY). 여기서 셋이 같은 날짜·같은
문장·같은 유예를 쓰는지 고정한다.

재현하는 실제 상태
  - 09-24~26 배치 정지: 홈은 '매주 갱신' 고정 문구 아래 9/17 발표값을 9일 동안 보였다(지연을 스스로 알리지 않음).
  - rel-week 는 데이터가 아니라 오늘 날짜로 다음 목요일을 세어, 밀린 회차를 건너뛴 날짜를 냈다.
  - 2026 추석: 9/21 조사분은 휴일인 9/24(목) 당일 R-ONE 에 올라왔다(9/24 09:10 KST 배치에는 없고 18:12 KST 배치에
    'updated: weekly(~2026-09-21)'). 옛 규칙(_bizDay)은 9/28(월)을 말했다.
픽스처: 날짜를 박은 합성 주차(2026 공휴일 표 H2026)와, 저장소 data.js 의 실제 ADV.holidays 로 그 목록의 연도 전체
모든 월요일. 실데이터의 '최신 주'나 공휴일 목록의 연도에 기대는 단정은 두지 않는다(데이터가 앞으로 가도 초록).
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import check_freshness as CF  # noqa: E402
import home_src as HS  # noqa: E402
import kst  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import split_data as S  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 2026 법정공휴일(대체공휴일 포함) — 특일정보 API 가 준 값과 같은 모양. 추석 09-24(목)~26.
H2026 = ['2026-01-01', '2026-02-16', '2026-02-17', '2026-02-18', '2026-03-01', '2026-03-02', '2026-05-05',
         '2026-05-25', '2026-06-03', '2026-06-06', '2026-08-15', '2026-08-17', '2026-09-24', '2026-09-25',
         '2026-09-26', '2026-10-03', '2026-10-05', '2026-10-09', '2026-12-25']


def _adv():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    return json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', s, re.S).group(1))


def _d(iso):
    return datetime.date(*(int(x) for x in iso.split('-')))


# ---- 파이썬 정본: 추석 주·평상 주 ----

def test_chuseok_week_hedges_instead_of_guessing_a_date():
    """다음 발표 목요일이 휴일(9/24)이면 날짜를 단정하지 않고(안내 문구도 없이 '… 발표'로 끝난다 — 2026-10-05 대표 요청으로
    '연휴로 발표 일정이 바뀔 수 있습니다'를 뺐다), 지연 판정은 한 주 늦춘 날(10/1)까지 참는다.

    연휴 주는 원천이 조사를 거르기도 해서 기준일을 한 주(WEEK) 늦춘다(전수리뷰 #10, 대표 결정 ④ — 아래
    test_skipped_survey_week_does_not_raise_a_false_wait 가 실제 거른 주를 본다).
    변이: status 에서 hedge 의 한 주 늦춤을 빼면(due 9/28) 9/29 에 '반영 대기'가 떠 빨개진다(확인).
          hedge 창을 목요일 하루(range(1))로 좁혀도 설 연휴(2/16~18 월~수) 주에서 빨개진다(확인). next_text 의 연휴 갈래를 옛
          안내 문구로 되돌리거나 when_text 가 빈 조각까지 ' · '로 이으면 when_text 단정이 빨개진다(확인).
    픽스처: 9/14 조사분(9/17 발표) — 09-24~26 배치가 멈췄던 바로 그 주.
    """
    st = WR.status('2026-09-14', _d('2026-09-29'), H2026)
    assert st['next'] == '2026-09-24' and st['hedge'] and st['due'] == '2026-10-01' and not st['stale']
    assert WR.next_text(st) == '' and WR.when_text(st) == '9/14 조사 · 9/17 발표'
    late = WR.status('2026-09-14', _d('2026-10-02'), H2026)
    assert late['stale'] and WR.when_text(late) == '최근 반영: 9/17 발표 · 이번 주 발표분 반영 대기'
    # 설 연휴가 월~수에 걸린 주 — 목요일은 평일이어도 그 주 일정은 단정하지 않는다
    assert WR.status('2026-02-09', None, H2026)['hedge']


def test_normal_week_names_the_next_thursday_and_waits_one_day():
    """평상 주: 다음 발표 목요일을 적고, 그 목요일이 다 지나야(금요일부터) '반영 대기'.

    감시(GRACE_WEEKLY 9)는 목요일 배치 뒤에 돌아 목요일부터 실패로 보지만, 화면은 발표 당일 아침에도 보이므로
    하루를 더 준다. 변이: status 의 `today > due` 를 `>=` 로 바꾸면 발표 당일(10/1)에 빨개진다(확인).
    픽스처: 9/21 조사분(9/24 발표) — 추석 뒤 첫 평상 주.
    """
    ok = WR.status('2026-09-21', _d('2026-10-01'), H2026)
    assert (ok['pub'], ok['next'], ok['hedge'], ok['stale']) == ('2026-09-24', '2026-10-01', False, False)
    assert WR.when_text(ok) == '9/21 조사 · 9/24 발표 · 다음 발표 10/1(목)'
    assert WR.status('2026-09-21', _d('2026-10-02'), H2026)['stale']
    # 정적 페이지(오늘 없음)는 지연을 판정하지 않는다
    assert not WR.status('2026-09-21', None, H2026)['stale']



# 2025 법정공휴일(대체·임시 포함) — 원천이 조사를 거른 두 번(설·추석)을 재현하는 데 쓴다.
H2025 = ['2025-01-01', '2025-01-27', '2025-01-28', '2025-01-29', '2025-01-30', '2025-03-01', '2025-03-03',
         '2025-05-05', '2025-05-06', '2025-06-03', '2025-06-06', '2025-08-15', '2025-10-03', '2025-10-05',
         '2025-10-06', '2025-10-07', '2025-10-08', '2025-10-09', '2025-12-25']


@pytest.mark.parametrize('p, nxt_real', [('2025-01-20', '2025-02-03'), ('2025-09-29', '2025-10-13')])
def test_skipped_survey_week_does_not_raise_a_false_wait(p, nxt_real):
    """원천이 연휴로 조사를 한 주 거른 주에는, 다음 실제 발표일까지 '반영 대기'를 띄우지 않는다(전수리뷰 #10).

    변이: status 의 `(WEEK if hedge else 0)` 를 빼면 2025-02-01~05·10-11~15 에 '반영 대기'가 떠 빨개진다(실제로 확인).
          JS 거울만 빼면 test_js_and_python_* 가 빨개진다(확인).
    픽스처: 저장소 data.js 의 실제 주간 행에서 거른 두 번 — 2025-01-20 다음 조사분이 2025-02-03(설),
            2025-09-29 다음이 2025-10-13(추석). 공휴일은 2025 달력(H2025). 다음 실제 발표 = 그 조사분 목요일.
    """
    real_pub = _d(nxt_real) + datetime.timedelta(days=WR.PUB_OFFSET)
    day = _d(p) + datetime.timedelta(days=WR.PUB_OFFSET + 1)
    while day <= real_pub:
        st = WR.status(p, day, H2025)
        assert st['hedge'] and not st['stale'], (p, day.isoformat(), WR.when_text(st))
        day += datetime.timedelta(days=1)
    # 그 발표일이 지나도 새 주차가 없으면 그때는 알린다
    assert WR.status(p, real_pub + datetime.timedelta(days=1), H2025)['stale']


# ---- 같은 상수: 감시 ↔ split_data ↔ 홈 ----

@pytest.fixture(scope='module')
def split(tmp_path_factory):
    """저장소 data.js 사본에 split 을 돌린다(저장소에는 쓰지 않는다 — test_split_semantics 와 같은 방식)."""
    d = tmp_path_factory.mktemp('split_wr')
    src = d / 'data.js'
    shutil.copyfile(os.path.join(ROOT, 'data.js'), src)
    paths = {'SRC': src, 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(paths['OUT'], encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    trend = json.loads(paths['TREND'].read_text(encoding='utf-8'))
    return core_adv, trend


def test_grace_is_the_watchdog_constant_in_both_payloads(split):
    """홈이 읽는 유예(ADV.weekly.grace)는 감시가 쓰는 GRACE_WEEKLY 와 같다 — data-core 와, 통계 탭을 열면
    ADV.weekly 를 통째로 갈아끼우는 data-trend 둘 다.

    변이: check_freshness 에 `GRACE_WEEKLY = 10` 을 따로 적거나, split_data 가 trend 쪽에 grace 를 빼면
          빨개진다(둘 다 실제로 확인).
    """
    core_adv, trend = split
    assert CF.GRACE_WEEKLY == WR.GRACE_WEEKLY
    assert core_adv['weekly']['grace'] == CF.GRACE_WEEKLY
    assert trend['ADV']['weekly']['grace'] == CF.GRACE_WEEKLY


def _home():
    return HS.home_source()


def _fn(src, name):
    m = re.search(r'\nfunction %s\([^)]*\)\{.*?\n\}' % name, src, re.S)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    return m.group(0)


def test_home_reads_grace_from_data_and_both_views_share_one_function():
    """홈 격자 머리줄과 통계 탭 rel-week 가 같은 함수(weeklyReleaseNow → weeklyRelease)를 쓰고, 유예는 데이터에서 읽는다.

    변이: renderReleaseInfo 를 옛 `_nextThu(now)` 계산으로 되돌리거나, weeklyReleaseNow 의 `W.grace` 를 9 로
          바꾸면 빨개진다(확인). 격자 머리줄이 wkWhenText 를 안 쓰면(정적 '매주 갱신' 복귀) 빨개진다.
          (머리줄·h2 를 적는 줄은 1차 배포 검토 뒤 applyWeeklyStatus 로 옮겼고, 그 동작은 아래
          test_home_kicker_and_h2_follow_the_release_state 가 node 로 돌려 본다.)
    """
    src = _home()
    assert '_nextThu(' not in src, '오늘 기준 다음 목요일 계산이 되살아났다 — 데이터 기준(weeklyRelease)으로 센다'
    now = _fn(src, 'weeklyReleaseNow')
    assert 'weeklyRelease(row.p,new Date(),W.grace)' in now, '유예를 데이터(ADV.weekly.grace)가 아닌 곳에서 읽는다'
    rel, grid = _fn(src, 'renderReleaseInfo'), _fn(src, 'renderWeeklyGrid')
    assert 'weeklyReleaseNow()' in rel and 'wkNextText(r)' in rel
    apply = _fn(src, 'applyWeeklyStatus')
    assert 'applyWeeklyStatus(weeklyReleaseNow(),weeklyHead(ADV.weekly))' in grid
    # 주간 구역 머리줄(wk-kicker)은 뺐다(2026-10-03 대표 요청 — 군더더기). 정적 '매주 갱신'도 되살아나지 않는다.
    assert "getElementById('wk-kicker')" not in apply and 'id="wk-kicker"' not in src and '매주 갱신 · 한국부동산원' not in src


# ---- JS ↔ 파이썬 대조 ----

def _js_block():
    m = re.search(r'// <wk-release>[^\n]*\n(.*?)// </wk-release>', _home(), re.S)
    assert m, 'home-app.js 에서 <wk-release> 구간을 찾지 못했다'
    return m.group(1)


def _years(holidays):
    return sorted({int(str(h)[:4]) for h in holidays})


def _cases(years):
    """years 의 모든 월요일 × 발표 전후 여러 날 × KST 자정 전후·정오 전후 시각.

    범위는 첫 해 1/1 이 든 주의 **한 주 앞** 월요일(다음 발표가 1월 첫 주에 걸리는 조사분)부터 마지막 해
    12/31 이 든 주의 월요일까지다. 범위를 날짜로 박지 않고 공휴일 목록의 연도에서 잡는다 — 배치
    (update_adv_data.fetch_holidays)는 ADV.holidays 를 '올해+내년'으로 통째로 바꾸므로, 박아 둔 범위는 해가
    바뀌면 공휴일이 하나도 없는 구간이 된다.
    """
    first, last = datetime.date(years[0], 1, 1), datetime.date(years[-1], 12, 31)
    p = first - datetime.timedelta(days=first.weekday() + 7)
    end = last - datetime.timedelta(days=last.weekday())
    out = []
    while p <= end:
        for dd in (3, 9, 10, 11, 12, 13, 17):
            for hh, mm in ((0, 30), (11, 59), (23, 30)):
                t = datetime.datetime.combine(p + datetime.timedelta(days=dd), datetime.time(hh, mm), tzinfo=kst.KST)
                out.append((p.isoformat(), int(t.timestamp() * 1000), t))
        p += datetime.timedelta(days=7)
    return out


def _js_matches_python(holidays, cases):
    """같은 공휴일·같은 사례로 JS(weeklyRelease·wkNextText·wkWhenText·wkPubLead)와 파이썬 정본을 돌려 전부 같은지 본다.
    wkPubLead(늦은 주 '발표 기준' 머리말)는 2026-09-27 추가 — '기준'을 한쪽에서만 빼면 늦은 주 사례가 빨개진다(확인).
    유예는 감시 상수·10·없음(옛 캐시) 세 가지. 파이썬 쪽 결과를 돌려준다(갈래 확인용)."""
    if not shutil.which('node'):
        pytest.skip('node 없음')
    graces = (WR.GRACE_WEEKLY, 10, None)
    js = (_js_block() + '\n_HOLIDAYS=new Set(%s);\nconst C=%s, G=%s, out=[];\n'
          'for(const [p,ms] of C)for(const g of G){const r=weeklyRelease(p,new Date(ms),g);'
          'out.push([r.survey,r.pub,r.next,r.hedge,r.due,r.stale,wkNextText(r),wkWhenText(r),wkPubLead(r)]);}\n'
          'process.stdout.write(JSON.stringify(out));'
          % (json.dumps(list(holidays)), json.dumps([[p, ms] for p, ms, _ in cases]), json.dumps(list(graces))))
    proc = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode('utf-8', 'replace')
    got = json.loads(proc.stdout.decode('utf-8'))
    want = []
    for p, _, t in cases:
        for g in graces:
            st = WR.status(p, kst.today(t), holidays, g)
            want.append([st['survey'], st['pub'], st['next'], st['hedge'], st['due'], st['stale'],
                         WR.next_text(st), WR.when_text(st), WR.pub_lead(st)])
    assert len(got) == len(want)
    bad = [(c[0], c[2].isoformat(), g, a, b) for (c, g), a, b in
           zip(((c, g) for c in cases for g in graces), got, want) if a != b]
    assert not bad, '홈 JS 와 파이썬 정본이 %d건 다르다. 예: %s' % (len(bad), bad[:3])
    return want


def test_js_and_python_give_the_same_dates_and_sentences():
    """홈(JS)과 /weekly/(파이썬)가 2026 한 해의 모든 주에 같은 발표일·다음 발표·연휴 여부·반영 대기·문장을 낸다.

    변이(각각 실제로 확인): JS 의 연휴 창 `k<=3` → `k<3`, 유예 `b+grace+1` → `b+grace`, KST 보정(+9h) 제거
    (23:30 KST 가 전날로 셈), JS _bizDay 가 공휴일을 보지 않음(추석 주 지연 판정이 갈림), 파이썬 WEEKDAYS 순서
    어긋남 — 모두 빨개진다. 공휴일을 빈 목록으로 돌리면(평평한 픽스처) 마지막 갈래 단정이 빨개진다.
    픽스처: 고정 표 H2026(추석 9/24~26 목~토, 설 2/16~18 월~수)과 유예 9·10·없음. 갈래(평상·연휴·반영 대기)가
    모두 나오는지는 **이 고정 픽스처에만** 건다 — 실데이터 공휴일은 해마다 바뀌므로 갈래 단정을 걸면 게이트가
    날짜에 묶인다(아래 실데이터 대조 시험의 독스트링).
    """
    want = _js_matches_python(H2026, _cases(_years(H2026)))
    # 픽스처가 실제로 세 갈래(평상·연휴·반영 대기)를 모두 지났는지 — 평평한 픽스처로 초록이 되지 않게
    kinds = {(w[3], w[5]) for w in want}
    assert {(False, False), (True, False)} <= kinds and any(w[5] for w in want), kinds


def test_js_and_python_agree_on_the_live_holiday_list():
    """저장소 data.js 의 ADV.holidays(배치가 특일정보 API 로 매 회차 '올해+내년'을 채운다)로도 JS 와 파이썬이 같다.

    범위는 그 목록의 연도에서 잡는다(_cases). 예전엔 2025-12-22~2027-12-27 로 박고 갈래 단정까지 여기 걸어,
    data.js 의 holidays 를 2028·2029 목록(2028-01-01, 설 01-26~28, 추석 10-02~05 … 2029-12-25)으로 바꾸면
    박힌 범위에 공휴일이 하나도 없어 `(True, False)` 갈래가 사라지고 빨개졌다(실제로 확인) — 2028 첫 배치부터
    데이터 커밋이 막혔을 것이다. 지금은 같은 치환에서 초록이다(확인).
    변이: 위 시험의 변이 다섯(연휴 창·유예·KST·_bizDay·WEEKDAYS)이 여기서도 모두 빨개진다(확인). 갈래 확인은
    데이터에서 유도한다 — 목록에 월~목 공휴일이 하나라도 있으면 연휴 주가 한 번은 나와야 한다(양쪽에 빈 목록을
    주면 빨개짐, 확인).
    픽스처: data.js 의 실제 ADV.holidays. 비어 있으면(키 없는 회차) 올해 한 해를 빈 공휴일로 대조만 한다.
    """
    holidays = _adv().get('holidays') or []
    want = _js_matches_python(holidays, _cases(_years(holidays) or [kst.today().year]))
    if any(_d(h).weekday() <= 3 for h in holidays):
        assert any(w[3] for w in want), '월~목 공휴일이 있는데 연휴 주가 한 번도 나오지 않았다'


# ---- /weekly/ ----

def _week(p, holidays):
    """data.js ADV.weekly 와 같은 모양의 합성 주(모든 시도 +0.05, 시군구 11곳, 서울 3개 구)."""
    import sido_zones as SZ
    regs = list(SZ.DISPLAY_ORDER)
    sgg = [('가%d' % i, 0.01 * (i - 5)) for i in range(11)]
    codes = ['C%02d' % i for i in range(len(sgg))]
    W = {'regions': regs, 'rows': [{'p': p, 'ma': [0.05] * len(regs)}],
         'sgg': {'codes': codes, 'rows': [{'p': p, 'ma': [v for _, v in sgg]}]},
         'seoul': {'regions': ['강남구', '서초구', '송파구'], 'rows': [{'p': p, 'ma': [0.1, -0.1, 0.0]}]},
         'holidays': holidays}
    return W, {c: n for c, (n, _) in zip(codes, sgg)}


def test_weekly_page_bakes_the_shared_when_line():
    """/weekly/ 머리줄은 weekly_release 문장을 그대로 굽고, 배치가 멈추면 같은 '반영 대기' 문장으로 스스로 바꾼다.

    변이: build() 가 옛 datestr('9/21 조사 · 9/24 발표')만 굽거나, 스크립트의 비교 날짜를 due 가 아닌 next 로 쓰거나,
          스크립트를 h1 앞(eyebrow 바로 뒤)에 두면 추석 주 픽스처에서 빨개진다(확인).
    픽스처: 합성 주(9/14 조사, 2026 공휴일) — 다음 발표 9/24 가 추석이라 다음 발표를 적지 않는다, 비교 날짜는 한 주
            늦춘 10/1(대표 결정 ④).
    """
    W, Q = _week('2026-09-14', H2026)
    head = MW.build(W, Q)[0]
    assert '<span id="wk-when">9/14 조사 · 9/17 발표</span>' in head
    assert '>"2026-10-01"){' in head and '"최근 반영: 9/17 발표 · 이번 주 발표분 반영 대기"' in head
    # 제목의 '이번 주'도 발표일로 — 스크립트가 h1 보다 뒤에 있어야 h1 을 찾는다(TRUST-1③)
    assert '.replace("이번 주","9/17 발표 기준")' in head and head.index('<h1>') < head.index('<script>')
    # 실데이터: 구운 페이지의 머리줄이 정본 함수 결과와 같다(날짜는 데이터에서 유도)
    W2, _ = MW.load()
    st = WR.status(W2['rows'][-1]['p'], None, W2['holidays'])
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    assert '<span id="wk-when">%s</span>' % WR.when_text(st) in page


def test_weekly_page_dataset_points_at_itself_and_source_claim_is_checkable():
    """Dataset url 은 /weekly/ 자신(canonical), 출처 문단은 확인 가능한 사실만(A4·A6, SEO-2①·TRUST-8).

    변이: render() 에서 put_dataset_url 이나 put_source 호출을 빼면 옛 뼈대 값('/#stats-market', '뉴스 기사보다
          하루 빠르다')이 남아 빨개진다(확인).
    픽스처: 옛 뼈대 조각 — 생성기가 손으로 적힌 값을 덮어쓰는지 본다.
    """
    old = ('<link rel="canonical" href="https://www.agongmap.co.kr/weekly/">\n'
           '{"@type": "WebPage", "url": "https://www.agongmap.co.kr/weekly/", "about": {\n'
           '  "@type": "Dataset", "name": "x", "url": "https://www.agongmap.co.kr/#stats-market", "k": 1}}\n'
           '<h2>숫자의 출처</h2>\n  <p>… 국가 통계라, 뉴스 기사보다 하루 빠르다.</p>')
    new = MW.put_source(MW.put_dataset_url(old))
    assert '"@type": "Dataset", "name": "x", "url": "https://www.agongmap.co.kr/weekly/"' in new
    assert '뉴스 기사보다' not in new and MW.SOURCE_TEXT in new
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    ds = re.search(r'"@type":\s*"Dataset",.*?"url":\s*"([^"]*)"', page, re.S).group(1)
    assert ds == re.search(r'<link rel="canonical" href="([^"]+)">', page).group(1), ds
    assert '뉴스 기사보다' not in page and MW.SOURCE_TEXT in page


# ---- 화면에 적는 줄(1차 배포 검토에서 시험이 비어 있던 두 곳) ----

def _node(js):
    if not shutil.which('node'):
        pytest.skip('node 없음')
    proc = subprocess.run(['node', '-e', js], capture_output=True, timeout=60)
    assert proc.returncode == 0, proc.stderr.decode('utf-8', 'replace')
    return json.loads(proc.stdout.decode('utf-8'))


def test_home_h2_follows_the_release_state_and_no_kicker_is_written():
    """홈 주간 구역: h2 는 늦은 주에만 '이번 주' 대신 발표일로 바뀐다(TRUST-1②). 구역 머리줄은 2026-10-03 에 뺐다 —
    늦은 주를 알리는 곳은 이 h2 와 첫 화면 띠뿐이라, 머리줄 자리에 아무것도 적지 않는지도 본다.

    변이: applyWeeklyStatus 에서 h2 줄을 지우거나, 조건을 `r.stale` 없이 늘 바꾸게 하면 빨개진다(실제로 확인).
          renderWeeklyGrid 가 applyWeeklyStatus 를 부르지 않으면 마지막 단정이 빨개진다(확인).
    픽스처: 합성 조사일 2026-09-14(발표 9/17), 유예는 감시 상수. '늦은 날'은 9/27(KST), '제때'는 9/18(KST).
    """
    src = _home()
    h2_default = '이번 주, 어디가 오르고 내렸을까?'
    js = (_js_block() + '\n' + _fn(src, 'applyWeeklyStatus') + '\n'
          '_HOLIDAYS=new Set([]);const out=[];\n'
          'for(const iso of %s){const el={"wk-kicker":{textContent:""},"wk-h2":{textContent:%s}};\n'
          '  globalThis.document={getElementById:id=>el[id]||null};\n'
          '  applyWeeklyStatus(weeklyRelease("2026-09-14",new Date(iso),%d));\n'
          '  out.push([el["wk-kicker"].textContent,el["wk-h2"].textContent]);}\n'
          'process.stdout.write(JSON.stringify(out));'
          % (json.dumps(['2026-09-18T03:00:00Z', '2026-09-27T03:00:00Z']), json.dumps(h2_default), WR.GRACE_WEEKLY))
    (k_ok, h_ok), (k_late, h_late) = _node(js)
    st = WR.status('2026-09-14', datetime.date(2026, 9, 18))
    assert k_ok == '' and h_ok == h2_default, (k_ok, h_ok)
    st = WR.status('2026-09-14', datetime.date(2026, 9, 27))
    assert st['stale'] and k_late == '', k_late
    assert h_late == '9/17 발표, 어디가 오르고 내렸을까?', h_late
    assert 'applyWeeklyStatus(weeklyReleaseNow(),weeklyHead(ADV.weekly))' in _fn(src, 'renderWeeklyGrid')


def test_weekly_page_script_compares_the_kst_date():
    """/weekly/ 의 스스로 고치는 스크립트는 오늘을 **KST** 날짜로 센다 — UTC 로 세면 KST 새벽 9시간 동안 하루 늦는다.

    변이: 스크립트의 `Date.now()+324e5` 를 `Date.now()` 로 바꾸면 'KST 는 다음 날, UTC 는 아직 그날'인 순간에 바꾸지
          않아 빨개진다(실제로 확인). 비교를 `>` 에서 `>=` 로 바꾸면 기준일 당일에 바꿔 빨개진다(확인).
    픽스처: 합성 주 2026-09-14(2026 공휴일 — 연휴 주라 비교 날짜 due 는 한 주 늦춘 10/1). 두 순간: KST 10/1 23:00
            (= UTC 14:00, 아직 제때)과 KST 10/2 05:00(= UTC 10/1 20:00, 늦음).
    """
    W, Q = _week('2026-09-14', H2026)
    head = MW.build(W, Q)[0]
    script = re.search(r'<script>(\(function\(\)\{try\{if\(new Date.*?)</script>', head, re.S).group(1)
    js = ('const out=[];\n'
          'for(const ms of %s){const e={textContent:"x"},t={nodeType:3,nodeValue:"이번 주 아파트"};\n'
          '  globalThis.document={getElementById:()=>e,querySelector:()=>({firstChild:t})};\n'
          '  Date.now=()=>ms;\n%s\n  out.push([e.textContent,t.nodeValue]);}\n'
          'process.stdout.write(JSON.stringify(out));'
          % (json.dumps([int(datetime.datetime(2026, 10, 1, 14, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000),
                         int(datetime.datetime(2026, 10, 1, 20, 0, tzinfo=datetime.timezone.utc).timestamp() * 1000)]),
             script))
    (k1, h1), (k2, h2) = _node(js)
    assert (k1, h1) == ('x', '이번 주 아파트'), '기준일(KST 10/1) 당일에 벌써 바꿨다'
    assert k2 == '최근 반영: 9/17 발표 · 이번 주 발표분 반영 대기' and h2 == '9/17 발표 기준 아파트', (k2, h2)


def test_dataset_url_rewrite_stays_inside_the_dataset_object():
    """Dataset 자신의 url 줄이 없으면 중첩 객체(creator)의 url 을 덮어쓰지 않고 멈춘다.

    변이: put_dataset_url 의 `[^{}]*?` 를 옛 `.*?` 로 되돌리면 creator 의 url 을 조용히 바꿔 빨개진다(실제로 확인).
    픽스처: url 줄이 빠진 Dataset 뒤에 url 을 가진 creator 가 오는 모양(뼈대를 손으로 고치다 줄을 지운 경우).
    """
    broken = ('<link rel="canonical" href="https://www.agongmap.co.kr/weekly/">\n'
              '{"@type": "Dataset", "name": "x",\n'
              ' "creator": {"@type": "Organization", "url": "https://www.agongmap.co.kr/"}}')
    with pytest.raises(SystemExit):
        MW.put_dataset_url(broken)
