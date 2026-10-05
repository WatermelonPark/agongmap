# -*- coding: utf-8 -*-
"""홈 첫 화면 — '이번 주' 띠·판정 카드·카드 ⓘ 식·지도 균형 중립색(홈 마케팅 검수 B1·B2·C4, 2026-09-27).

재현하는 실제 상태(09-26 라이브 375×812 첫 화면)
  - 첫 화면의 글자는 전부 분기 단위(히어로·카드 셋·'2026년 2분기 기준')라 한 분기 내내 같은 화면이었다. 매주 바뀌는
    이번 주 시군구 지도는 이름 없는 배경 무늬였고, 주간 구역 h2 는 매주 같은 질문이었다(HERO-2·RET-1·IA-4·IA-5·MOB-1).
  - 카드 셋이 모두 '부족'이고 지도는 균형 지역(충북 1%·세종 13%·경기 17%)까지 연한 빨강이라 16곳 중 13곳이 붉었다.
    '3년 필요량의 60%'는 '60%만 지어진다'로도 읽혔고, 686,396 = 1,140,000 − 714,127 + 260,523(지난 4년 쌓인 부족)을
    홈 재료로는 검산할 수 없었다(HERO-4·TRUST-2·TRUST-3). 375px 에서 수도권만 배지가 둘째 줄로 내려갔다(MOB-7).
원칙: 문장은 한 곳에서 만든다. 결론 한 줄은 make_weekly_page.conclusion(→ split_data 가 ADV.weekly.head 로 굽는다),
카드·식 문구는 sido_zones(→ refresh_texts), 발표 일정 문장은 weekly_release/weeklyRelease. 홈 JS 는 읽기만 한다.
2026-09-28 대표 결정(작은 글씨 정리)으로 띠 둘째 줄(배경 지도 캡션·다음 발표)·카드 아래 분포 한 줄·공급 범례 뜻 한 줄을 뺐다 —
그 셋은 '없다'를 단정한다.
2026-10-05 대표 요청으로 첫 화면 '이번 주' 띠와 '내 지역' 줄을 통째로 뺐다(첫 화면 위쪽을 너무 차지한다) — 히어로는 라벨·제목·
부제뿐이고(test_hero_is_the_title_block_only), 연휴 주 안내 문구도 발표 줄에서 뺐다.
각 시험의 독스트링에 ① 무엇을 깨뜨리면 빨개지는지(실제로 변이를 넣어 확인) ② 픽스처가 재현하는 상태를 적었다.
날짜는 고정 합성 주(2026 공휴일 표)로만 단정하고, 실데이터는 함수 결과와의 일치로만 본다(데이터가 앞으로 가도 초록).
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import urllib.parse

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import kst  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import split_data as S  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))

# 2026 법정공휴일(대체공휴일 포함) — test_weekly_release 와 같은 표. 추석 09-24(목)~26.
H2026 = ['2026-01-01', '2026-02-16', '2026-02-17', '2026-02-18', '2026-03-01', '2026-03-02', '2026-05-05',
         '2026-05-25', '2026-06-03', '2026-06-06', '2026-08-15', '2026-08-17', '2026-09-24', '2026-09-25',
         '2026-09-26', '2026-10-03', '2026-10-05', '2026-10-09', '2026-12-25']


def _src(rel):
    if HS.is_home(rel):
        return HS.home_source()   # 홈(index.html + home-app.js)은 입구로만 읽는다(test_home_src)
    return io.open(os.path.join(ROOT, rel), encoding='utf-8').read()


def _home():
    return HS.home_source()


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


def _wk_block():
    m = re.search(r'// <wk-release>[^\n]*\n(.*?)// </wk-release>', _home(), re.S)
    assert m, 'home-app.js 에서 <wk-release> 구간을 찾지 못했다'
    return m.group(1)


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 홈 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _band_js():
    """주간 h2 를 만드는 홈 함수들(순수 함수 + h2 적기)을 그대로 뽑는다(첫 화면 띠는 2026-10-05 대표 요청으로 뺐다)."""
    h = _home()
    return '\n'.join([_wk_block()] + [_js_func(h, n) for n in ('weeklyHead', 'applyWeeklyStatus')])


def _kst_ms(y, m, d, hh=12):
    t = datetime.datetime(y, m, d, hh, 0, tzinfo=kst.KST)
    return int(t.timestamp() * 1000)


def _week(val, p, sgg_p=None):
    """data.js ADV.weekly 와 같은 모양의 합성 주. val: {시도: 매매 변동}. 없는 시도는 +0.01."""
    regs = list(SZ.DISPLAY_ORDER)
    ma = [val.get(z, 0.01) for z in regs]
    sgg = [('가%d' % i, 0.01 * (i - 5)) for i in range(11)]
    codes = ['C%02d' % i for i in range(len(sgg))]
    W = {'regions': regs, 'rows': [{'p': p, 'ma': ma, 'je': ma}],
         'sgg': {'codes': codes, 'rows': [{'p': sgg_p or p, 'ma': [v for _, v in sgg]}]},
         'seoul': {'regions': ['강남구', '서초구', '송파구'], 'rows': [{'p': p, 'ma': [0.1, -0.1, 0.0]}]},
         'holidays': H2026}
    return W, {c: n for c, (n, _) in zip(codes, sgg)}


def _plain(h):
    return re.sub(r'<[^>]+>', '', h.replace('<br>', ' '))


# ── B1·IA-4: 결론 한 줄은 /weekly/ 제목·홈 띠·홈 주간 h2 에서 같은 문장 ─────────────────────────────

_WEEKS = {
    # 상승 주도(서울 +0.40), 하락 주도(대구 −0.31 이 서울 +0.12 보다 큼), 모두 보합
    'up': ({'서울': 0.40, '경기': 0.21, '대구': -0.10}, '서울 +0.40%, 가장 크게 올랐습니다'),
    'down': ({'서울': 0.12, '대구': -0.31, '부산': -0.18}, '대구 -0.31%, 가장 크게 내렸습니다'),
    'flat': ({z: 0.001 for z in SZ.DISPLAY_ORDER}, '시도 모두 보합입니다'),
}


def test_weekly_head_is_one_sentence_on_weekly_page_and_home_h2():
    """/weekly/ 제목 = '이번 주 아파트, ' + 결론, 홈 주간 h2 = 결론(B1·IA-4). 첫 화면 띠는 2026-10-05 대표 요청으로 뺐다.

    변이(각각 실제로 확인): make_weekly_page.h1_html 이 동사를 따로 적으면('가장 크게 올랐다') 첫 단정, head_payload 가
    text 를 빼면 둘째, applyWeeklyStatus 가 hd 를 무시하면(옛 고정 질문) 셋째 단정이 빨개진다.
    픽스처: 방향을 정한 합성 세 주(상승 주도·하락 주도·보합) — 조사일 2026-09-07(발표 9/10, 연휴 아님), 오늘 9/11 KST.
    """
    for key, (val, want) in _WEEKS.items():
        W, Q = _week(val, '2026-09-07')
        c = MW.conclusion(W)
        assert c['text'] == want, (key, c['text'])
        h1 = re.search(r'<h1>(.*?)</h1>', MW.build(W, Q)[0], re.S).group(1)
        assert _plain(h1) == '%s 아파트, %s' % (MW.H1_WEEK, want), (key, h1)
        hp = MW.head_payload(W)
        assert hp == {'p': '2026-09-07', 'text': want, 'dir': c['dir']}, hp
        WJ = dict(W, grace=WR.GRACE_WEEKLY, head=hp)
        js = (_band_js() + '\n_HOLIDAYS=new Set(%s);const W=%s;\n'
              'const r=weeklyRelease(W.rows[0].p,new Date(%d),W.grace);\n'
              'const el={"wk-h2":{textContent:"이번 주, 어디가 오르고 내렸을까?"}};\n'
              'globalThis.document={getElementById:id=>el[id]||null};\n'
              'applyWeeklyStatus(r,weeklyHead(W));\n'
              'process.stdout.write(JSON.stringify(el["wk-h2"].textContent));'
              % (json.dumps(H2026), json.dumps(WJ, ensure_ascii=False), _kst_ms(2026, 9, 11)))
        assert _node(js) == want, key


@pytest.fixture(scope='module')
def split(tmp_path_factory):
    """저장소 data.js 사본에 split 을 돌린다(저장소에는 쓰지 않는다 — test_split_semantics 와 같은 방식)."""
    d = tmp_path_factory.mktemp('split_fs')
    src = d / 'data.js'
    shutil.copyfile(os.path.join(ROOT, 'data.js'), src)
    paths = {'SRC': src, 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    trend = json.loads(paths['TREND'].read_text(encoding='utf-8'))
    return core_adv, trend['ADV']


def test_split_bakes_the_head_into_both_payloads_and_the_weekly_page_says_it(split):
    """배치가 ADV.weekly.head 를 data-core 와 data-trend(통계 탭이 ADV.weekly 를 통째로 바꾼다) 둘 다에 굽고,
    구운 /weekly/ 제목이 같은 문장을 말한다(실데이터 — 값은 함수에서 유도한다).

    변이: split_data 가 head 를 싣지 않거나(wk['head'] 줄 삭제) trend 쪽을 빼면 빨개진다(둘 다 확인). /weekly/ 를
          옛 생성기로 구운 채면(제목이 '올랐다') 마지막 단정이 빨개진다 — CI·배치는 생성기를 시험보다 먼저 돌린다.
    """
    core, trend = split
    W, _ = MW.load()
    want = MW.head_payload(W)
    assert want and want['p'] == W['rows'][-1]['p']
    assert core['weekly']['head'] == want and trend['weekly']['head'] == want
    assert core['weekly']['head']['p'] == core['weekly']['rows'][-1]['p']
    h1 = re.search(r'<h1>(.*?)</h1>', _src('weekly/index.html'), re.S).group(1)
    assert _plain(h1) == '%s 아파트, %s' % (MW.H1_WEEK, want['text']), h1


# ── 발표 줄(wkWhenText)은 발표 상태를 따르고 연휴 안내 문구는 없다 ─────────────────────────────────────────

def test_when_line_follows_the_release_state_without_a_holiday_notice():
    """발표 줄(wkWhenText — 지도 주간 모드 카드 아래 줄. 파이썬 정본 weekly_release.when_text 와 같은 문장)은 평상 주에
    '9/7 조사 · 9/10 발표 · 다음 발표 9/17(목)', 늦은 주에 '최근 반영: … · 반영 대기', 연휴 주에는 다음 발표를 적지 않고
    '9/14 조사 · 9/17 발표'로 끝난다 — '연휴로 발표 일정이 바뀔 수 있습니다'는 2026-10-05 대표 요청으로 뺐다(꼬리 ' · '도 없다).

    변이(각각 실제로 확인): wkNextText 의 연휴 갈래를 옛 안내 문구로 되돌리면 연휴 단정이, wkWhenText 가 빈 조각을 거르지
    않고 ' · '로 이어 붙이면(꼬리 ' · ') 연휴 단정이, 파이썬 when_text 만 옛 문장으로 두면 JS·파이썬 대조가 빨개진다.
    픽스처: 2026 공휴일 표. 평상(9/7 조사, 오늘 9/11), 추석 연휴 주(9/14 조사, 9/18 — 다음 발표 9/24 가 휴일),
            배치 정지(9/14 조사, 10/2 — 연휴 주라 한 주 늦춘 기준일 10/1 이 지남, 대표 결정 ④).
    """
    cases = [('2026-09-07', (2026, 9, 11)), ('2026-09-14', (2026, 9, 18)), ('2026-09-14', (2026, 10, 2))]
    js = (_wk_block() + '\n_HOLIDAYS=new Set(%s);const C=%s;\n'
          'process.stdout.write(JSON.stringify(C.map(([p,ms])=>{const r=weeklyRelease(p,new Date(ms),%d);'
          'return [r.hedge,wkWhenText(r)];})));'
          % (json.dumps(H2026), json.dumps([(p, _kst_ms(*d)) for p, d in cases]), WR.GRACE_WEEKLY))
    got = _node(js)
    for (p, d), (_, when) in zip(cases, got):
        assert when == WR.when_text(WR.status(p, datetime.date(*d), H2026)), (p, when)
    (h0, normal), (h1, hedge), (_, stale) = got
    assert not h0 and h1
    assert normal == '9/7 조사 · 9/10 발표 · 다음 발표 9/17(목)', normal
    assert hedge == '9/14 조사 · 9/17 발표', hedge
    assert stale == '최근 반영: 9/17 발표 · ' + WR.WAIT, stale
    assert not any('연휴' in w for _, w in got), got


def test_late_week_lead_is_one_phrase_on_h2_and_weekly_page():
    """늦은 주의 발표일 머리말('9/17 발표 기준')은 홈 주간 구역 h2·/weekly/ 제목이 같은 말이다(MOB-1, 2026-09-27 검토 지적).
    한 말은 WR.pub_lead / 홈 wkPubLead 이고 둘의 일치는 test_weekly_release 가 본다. 평상 주에는 h2 가 결론만 쓴다.

    변이(각각 실제로 확인): applyWeeklyStatus 가 머리말을 자기 문장(' 발표 · ')으로 적으면 h2 단정이, make_weekly_page.when_line
          이 '발표 기준' 대신 자기 말을 쓰면 /weekly/ 단정이 빨개진다.
    픽스처: 09-24~26 배치 정지를 옮긴 합성 주 — 9/14 조사(9/17 발표)가 최신인 채 오늘 10/2 KST(연휴 주라 한 주 늦춘
            기준일 10/1 이 지남, 대표 결정 ④), 그리고 같은 데이터의 평상 날(9/18). 공휴일 표는 2026.
    """
    text = '경기 +0.23%, 가장 크게 올랐습니다'
    W, Q = _week({}, '2026-09-14')
    W.pop('holidays')
    W.update(grace=WR.GRACE_WEEKLY, head={'p': '2026-09-14', 'text': text, 'dir': 'up'})
    out = []
    for mon, day in ((10, 2), (9, 18)):
        js = (_band_js() + '\n_HOLIDAYS=new Set(%s);const W=%s;\n'
              'const r=weeklyRelease(W.rows[0].p,new Date(%d),W.grace);\n'
              'const el={"wk-h2":{textContent:"이번 주, 어디가 오르고 내렸을까?"}};\n'
              'globalThis.document={getElementById:id=>el[id]||null};\n'
              'applyWeeklyStatus(r,weeklyHead(W));\n'
              'process.stdout.write(JSON.stringify([r.stale,el["wk-h2"].textContent]));'
              % (json.dumps(H2026), json.dumps(W, ensure_ascii=False), _kst_ms(2026, mon, day)))
        out.append(_node(js))
    (late, h2), (ok, h2_ok) = out
    st = WR.status('2026-09-14', datetime.date(2026, 10, 2), H2026)
    assert late and st['stale'] and not ok
    lead = WR.pub_lead(st)
    assert lead == '9/17 발표 기준'
    assert h2 == lead + ' · ' + text, h2
    assert h2_ok == text, h2_ok
    _, script = MW.when_line(dict(W, holidays=H2026), '2026-09-14')
    assert 'replace(%s,%s)' % (json.dumps(MW.H1_WEEK, ensure_ascii=False), json.dumps(lead, ensure_ascii=False)) in script


def _hero():
    m = re.search(r'<header class="home-hero">(.*?)</header>', _src('index.html'), re.S)
    assert m, '홈 히어로를 찾지 못했다'
    return m.group(1)


def test_hero_is_the_title_block_only():
    """첫 화면 히어로는 라벨·제목·부제뿐이다 — '내 지역' 줄(C5)과 '이번 주' 띠(B1)는 첫 화면 위쪽을 너무 차지해 2026-10-05
    대표 요청으로 뺐다. 띠가 말하던 발표일은 홈 주간 구역 머리말(평상 주 wkPubLead)이 잇는다. 고정해 둔 기기의 옛 저장값은
    부팅이 지운다(dropOldMyZone).

    변이(각각 실제로 확인): 히어로에 /weekly/ 띠 링크나 myz 줄을 되살리면 첫 단정이, boot 에서 renderHeroBand()·renderMyZone()
          을 다시 부르면 둘째 단정이, 주간 구역 머리말에서 wkPubLead 를 빼면 셋째, boot 에서 dropOldMyZone() 을 지우면 넷째
          단정이 빨개진다.
    """
    hero = _hero()
    assert '<a ' not in hero and 'myz' not in hero and 'hero-wk' not in hero, hero
    boot = _js_func(_home(), 'boot')
    assert not re.search(r'renderHeroBand|renderMyZone|initMyZonePick', boot), boot
    assert re.search(r"wg-when\">매매 전주 대비\(%\)'\+\(rel&&!rel\.stale\?' · '\+wkPubLead\(rel\)", _js_func(_home(), 'renderWeeklyGrid'))
    assert 'dropOldMyZone();' in boot
    css = _src('app.css')
    assert not re.search(r'\.(hero-wk|hw-\d|myz)', css), '뺀 히어로 줄의 CSS 규칙이 남아 있다'


def _css():
    return _src('app.css')


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])' + re.escape(sel) + r'\{([^}]*)\}', css)
    assert m, 'app.css 에서 %s 규칙을 찾지 못했다' % sel
    return m.group(1)


# ── B2·C4①: 식 한 줄은 홈 산출 방법·홈 카드 ⓘ·시도 리포트·블로그에서 같은 말 ──────────────────────────

def _check_formula(eq, need, fut, inow, tot, who):
    """식 문장(eq)을 읽는 사람처럼 검산한다: 적힌 세 항과 '+ 쌓인 부족 / − 남은 재고' 부호로 순부족(tot)이 나와야 하고,
    적힌 세 항은 화면 정수(display_ints)와 같아야 한다. 햇수('3년'·'4년')는 숫자 항이 아니다.
    한 자리 항(0~9)도 읽는다 — 옛 추출식 [\\d,]{2,} 는 지난 재고가 0 근처인 분기에 IndexError 로 게이트를 막았다(전수리뷰 #95)."""
    nums = [int(x.replace(',', '')) for x in re.findall(r'(?<![\d,])\d[\d,]*(?![\d,]|년)', eq)]
    assert len(nums) == 3, (who, eq, nums)
    sign = 1 if '쌓인 부족' in eq else -1
    assert nums == [need, fut, abs(inow)], (who, eq, (need, fut, inow))
    assert nums[0] - nums[1] + sign * nums[2] == tot == need - fut - inow, (who, eq, tot)


@pytest.mark.parametrize('inow', [-329, -5, 0, 7, 1434])
def test_formula_check_reads_single_digit_terms(inow):
    """식 검산이 지난 재고가 한 자리(0 포함)여도 게이트를 막지 않고 검산한다(전수리뷰 #95).
    픽스처: 세종 실데이터 모양(필요량 7,200·입주 추정 6,622)에 지난 재고만 실제 값(−329·1,434)과 0 근처 경계(−5·0·7)로 바꾼 행.
    변이(실제로 확인): _check_formula 의 추출식을 옛 [\\d,]{2,} 로 되돌리면 −5·0·7 칸이 빨개지고, sido_zones.formula_text 의
    갈래 조건을 뒤집어(inow > 0 이면 '쌓인 부족') 부호와 말이 어긋나게 하면 0 을 뺀 칸이 모두 빨개진다."""
    need, fut = 7200, 6622
    tot = need - fut - inow
    _check_formula(SZ.formula_text(SZ.LEAD_Q, SZ.BACKLOG_WINDOW, need, fut, inow), need, fut, inow, tot, inow)


def test_formula_is_one_text_on_home_zone_report_and_blog(monkeypatch):
    """'3년 필요량 − 착공 기반 입주 추정 + 지난 4년 쌓인 부족'(sido_zones.formula_text) 하나를 홈 산출 방법 첫 항목(손으로
    쓴 index.html)·홈 카드 ⓘ(구운 ftxt)·시도 리포트 '숫자로 보면'(생성기)·블로그 지역 편(초안 생성기)이 같이 쓴다.
    식의 숫자는 카드·리포트와 같은 정수이고 서로 검산된다(TRUST-2).

    변이(각각 확인): make_sido_pages 의 eq 를 옛 '= 적정 … − 공급 …'으로 되돌리면 리포트 단정이, draft_zone 이 식을 자기
          말('필요량 − 공급')로 적으면 블로그 단정이, index.html 첫 항목의 식을 바꾸면 홈 단정이, formula_text 가 모자란
          재고를 빼는 쪽(−)으로 적으면 검산 단정이 빨개진다. 산출 방법 첫 항목의 '4년'을 '3년'으로 적으면 햇수 단정.
    픽스처: 저장소 실데이터 판정 20곳(숫자는 함수에서 유도) + 생성기가 구운 /zone/전국/(CI·배치는 생성기를 먼저 돌린다).
    """
    gen = SZ.formula_text()
    assert gen == '3년 필요량 − 착공 기반 입주 추정 + 지난 4년 쌓인 부족'
    li = re.search(r'<li class="how-formula">(.*?)</li>', _src('index.html'), re.S)
    assert li, '홈 산출 방법 첫 항목(식)이 없다'
    assert '<b>%s</b>' % gen in li.group(1) and 'href="/zone/전국/#calc"' in li.group(1)
    years = {'%g' % (SZ.LEAD_Q / 4.0), '%g' % (SZ.BACKLOG_WINDOW / 4.0)}
    assert set(re.findall(r'(\d+)년', li.group(1))) <= years, '산출 방법 첫 항목에 모델과 다른 햇수가 있다'
    ul = re.search(r'<ul class="how-ls">\s*(<li[^>]*>)', _src('index.html'))
    assert ul and ul.group(1) == '<li class="how-formula">', '식 항목이 산출 방법의 첫 항목이 아니다'

    adv, sts = M.load()
    H = adv['sido']['H']
    for z in adv['sido']['zones']:
        need, fut, inow, tot = SZ.display_ints(z, H)
        eq, res = z['ftxt'].split(' = ')
        assert eq == SZ.formula_text(H, SZ.BACKLOG_WINDOW, need, fut, inow), z['z']
        _check_formula(eq, need, fut, inow, tot, z['z'])
        assert res == ('%s세대 %s' % (format(abs(tot), ','), '부족' if tot > 0 else '여유') if tot else '0세대'), res
    nat = next(z for z in adv['sido']['zones'] if z['z'] == '전국')
    page = _src(os.path.join('zone', '전국', 'index.html'))
    assert '<section id="calc">' in page, '/zone/전국/ 에 홈 산출 방법이 가리키는 식 블록 앵커가 없다'
    assert '= ' + M.esc(nat['ftxt'].split(' = ')[0]) in page, '시도 리포트의 식이 정본과 다르다'

    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(P, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(P, 'series_links', lambda *a, **k: '')
    for name in ('서울', '인천'):   # 모자란 재고(+) · 남은 재고(−) 두 갈래
        r = next(z for z in adv['sido']['zones'] if z['z'] == name)
        body = P.draft_zone(adv, sts, r, 1, 16)['body']
        assert '셈은 <b>%s</b>입니다.' % P.esc(r['ftxt'].split(' = ')[0]) in body, name


# ── C4②: 지도에서 균형(g1)은 중립색 ────────────────────────────────────────────────────────────────

def _hex(v):
    v = v.lstrip('#')
    return tuple(int(v[i:i + 2], 16) for i in (0, 2, 4))


def test_supply_map_colors_balance_as_neutral():
    """지도 채움: 균형(g1) 판정은 비율과 상관없이 중립 회색(--bal), 나머지는 예전 연속 농도(mapFill). 범례 램프 가운데 칸과
    시도 리포트·허브의 균형 배지(.sc-tier.g1)도 같은 무채색 계열이다(C4② — 09-13 결정 ② '지도 색 불변'을 바꾼다).

    변이(각각 확인): supplyFill 에서 g1 갈래를 지우면(비율 0.17 이 연한 빨강) 첫 단정, renderSidoMap 이 mapFill(z.ratio) 로
          돌아가면 둘째, --bal 을 붉은 기(#e8cfcb)로 바꾸면 무채색 단정, --bal 을 --paper2 와 같게 하면('자료 없음'과
          구별 안 됨) 거리 단정이 빨개진다.
    픽스처: 09-26 라이브의 균형 셋(충북 0.009·세종 0.126·경기 0.165)과 0·0.49(균형 끝), 부족(0.6)·여유(−0.19)·심각(1.79).
    """
    h = _home()
    fns = '\n'.join(_js_func(h, n) for n in ('tintA', 'mapFill', 'supplyFill'))
    consts = '\n'.join(re.search(r'^var %s=.*$' % n, h, re.M).group(0) for n in ('TB_MIN', 'TB_BAL'))
    consts += '\n' + re.search(r'^var TB_UP=.*$', h, re.M).group(0)
    js = (consts + '\n' + fns + '\nconst C=%s;process.stdout.write(JSON.stringify(C.map(([g,r])=>supplyFill({grade:g,ratio:r}))));'
          % json.dumps([['g1', 0.0], ['g1', 0.009], ['g1', 0.126], ['g1', 0.165], ['g1', 0.49],
                        ['g2', 0.6], ['g0', -0.19], ['g4', 1.79]]))
    got = _node(js)
    assert got[:5] == ['var(--bal)'] * 5, got[:5]
    rgb = [tuple(int(x) for x in re.findall(r'\d+', c)) for c in got[5:]]
    assert rgb[0][0] > rgb[0][2] and rgb[2][0] > rgb[2][2], '부족 쪽이 붉지 않다: %s' % got[5:]
    assert rgb[1][2] > rgb[1][0], '여유 쪽이 푸르지 않다: %s' % got[5:]
    # 공급 모드(M 없음)의 도형 채움은 supplyFill 이다 — 주간 모드(C3)의 wkFill 과 갈래로 나뉜다(test_home_map_mode 가 돌려 본다).
    assert "fill=\"'+(M?wkFill(M.v[key],M.ref):supplyFill(z))+'\"" in _js_func(h, 'renderSidoMap'), '지도 도형이 균형 중립색 규칙을 쓰지 않는다'

    css = _css()
    root = _rule(css, ':root')
    bal = _hex(re.search(r'--bal:(#[0-9a-fA-F]{6})', root).group(1))
    assert max(bal) - min(bal) <= 8, '균형 색이 무채색이 아니다: %s' % (bal,)
    for tok in ('--paper', '--paper2'):
        other = _hex(re.search(r'%s:(#[0-9a-fA-F]{6})' % tok, root).group(1))
        assert sum(abs(a - b) for a, b in zip(bal, other)) >= 30, '균형 색이 %s 와 구별되지 않는다' % tok
    assert 'background:var(--bal)' in _rule(css, '.map-key .mk-ramp .mk-b')
    assert '<i class="mk-b">%s</i>' % SZ.GRADE_LABS['g1'] in h, '범례 램프 가운데에 균형 표지가 없다'
    badge = _rule(css, '.sc-tier.g1')
    for c in re.findall(r'#[0-9a-fA-F]{6}', badge):
        v = _hex(c)
        assert max(v) - min(v) <= 30, '균형 배지 색이 무채색 계열이 아니다: %s' % c


# ── 2026-09-28 대표 결정(작은 글씨 정리): 카드 아래 분포 한 줄·공급 범례 뜻 한 줄은 없다 ─────────────────────────

def test_distribution_and_legend_lines_are_gone_with_their_data():
    """카드 아래 분포 한 줄('시도 16곳: 부족 이상 10 · 균형 3 · 여유 3(인천·대전·충남)')과 공급 범례 아래 뜻 한 줄('지난 4년 덜 지은
    몫까지 더해 3년 필요량을 채우는지 · 2026년 2분기 기준')을 뺐다. 읽는 곳이 홈뿐이던 재료(sido_zones.dist_text·dist_names·
    legend_text → ADV.sido.dist·dist_g0·ktxt)도 함께 지웠다 — 공급 판정 지도는 카드 셋·'지도에서 지역을 누르면' 안내·범례(여유·
    균형·부족)·지도만 그린다. 주간 모드의 발표 줄(wk-when)과 뜻 한 줄은 남는다(대표가 고르지 않음 — test_home_map_mode).
    기준 분기는 지도 아래 '앞으로 3년(2026년 3분기~2029년 2분기)' 구간 줄(supplySpan — test_home_small)이 말한다.

    변이(각각 실제로 확인): renderSidoMap 에 분포 줄(`'<p class="agg-dist">'+ADV.sido.dist+'</p>'`)을 되살리면 첫 단정이,
          mapKeyHtml 공급 갈래에 tk-n 뜻 한 줄을 되살리면 둘째 단정이, sido_zones 에 dist_text 를 되살리면 넷째 단정이 빨개진다.
    픽스처: 실제 좌표(sido-geo.js)·합성 판정 넷(집계 셋 + 서울, test_home_map_mode 와 같은 모양)에 옛 data.js 처럼 dist·dist_g0·
            ktxt 가 남은 판정으로 renderSidoMap 을 node 에서 한 번 그린다.
    """
    h = _home()
    geo = io.open(os.path.join(ROOT, 'sido-geo.js'), encoding='utf-8').read()
    zones = [dict(z='전국', agg=True, grade='g2', tot=686396, ratio=0.6), dict(z='수도권', agg=True, grade='g2', tot=1, ratio=0.5),
             dict(z='지방', agg=True, grade='g2', tot=1, ratio=0.6), dict(z='서울', grade='g3', tot=1, ratio=1.2)]
    for z in zones:
        z.update(SZ.zone_texts(dict(z, ref=1000, fut=1000, inow=-1, dtot=z['tot']), SZ.LEAD_Q))
    sido = {'L': '2026Q2', 'Ltxt': '2026년 2분기', 'H': SZ.LEAD_Q, 'zones': zones,
            'dist': '시도 16곳: 부족 이상 10', 'dist_g0': ['인천'], 'ktxt': '지난 4년 덜 지은 몫까지'}   # 옛 data.js 모양
    fns = '\n'.join(_js_func(h, n) for n in ('tintA', 'mapFill', 'supplyFill', 'aggLights', 'aggLightKey', 'aggCard', 'mapKeyHtml', 'mapAria', 'tbNum', 'tbSigned',
                                              'renderAggCards', 'renderSidoMap'))
    consts = '\n'.join(re.search(r'^var %s=.*$' % n, h, re.M).group(0)
                        for n in ('TB_MIN', 'TB_BAL', 'TB_UP', 'TB_GRADE', 'MAP_MODE'))
    js = (geo + '\n' + consts + '\n' + fns + '\nvar ADV={sido:%s,weekly:null};'
          'function priceModel(){return null;} function weeklyReleaseNow(){return null;}\n'
          'var EL={dataset:{},innerHTML:"",addEventListener:function(){}}, AG={innerHTML:""};'
          'var document={getElementById:function(id){return id==="map-wrap"?EL:(id==="agg-wrap"?AG:null)},'
          'querySelector:function(){return null}};\n'
          'renderAggCards();renderSidoMap();process.stdout.write(JSON.stringify([AG.innerHTML+EL.innerHTML,mapKeyHtml(null)]));'
          % json.dumps(sido, ensure_ascii=False))
    html, key = _node(js)
    top = _plain(html.split('<svg')[0])
    assert 'agg-dist' not in html and '시도 16곳' not in top and '인천' not in top, '분포 한 줄이 되살아났다: ' + top
    assert 'tk-n' not in key and '기준' not in _plain(key) and '지난 4년' not in key, key
    assert '<i class="mk-b">%s</i>' % SZ.GRADE_LABS['g1'] in key and '<p class="map-act">' in html
    for f in ('dist_text', 'dist_names', 'legend_text', 'DIST_GROUPS', 'DIST_LINK_KEYS'):
        assert not hasattr(SZ, f), 'sido_zones.%s 가 남아 있다 — 읽는 곳이 없다' % f
    for f in ('ADV.sido.dist', 'dist_g0', 'ADV.sido.ktxt', 'distLinks'):
        assert f not in h, '홈 스크립트가 %s 를 아직 읽는다' % f


# ── B2·C4①·MOB-7: 카드는 두 줄 링크, ⓘ 는 링크 밖 버튼 ─────────────────────────────────────────────

def test_cards_are_two_line_links_and_the_how_button_toggles():
    """카드 = '전국 [부족]' / '686,396세대 →' 두 줄 링크(넓은 화면만 '부족'·'3년 필요량의 60%'가 보인다), ⓘ 는 링크 밖의
    button(aria-expanded·aria-controls) — 누르면 식 한 줄이 펼쳐지고 다시 누르면 접힌다(기본은 접힘). 옛 캐시는 ⓘ 없음.

    변이(각각 확인): ⓘ 를 </a> 앞(링크 안)으로 옮기면 첫 단정, aggHow 가 hidden 을 안 바꾸면 토글 단정, 카드 둘째 줄이 ctxt
          통째를 쓰면(모바일 두 줄 고정이 깨짐) 세대수 단정이, aggCard 가 yl 이 있어도 배지를 그리면 신호등 단정이 빨개진다.
    픽스처: 09-26 라이브 수도권 카드(349,029세대 부족·58%, g2)와 같은 필드 모양, 옛 캐시 모양(ctxt 만).
    """
    h = _home()
    z = dict(z='수도권', grade='g2', tot=349029, **SZ.zone_texts(
        {'ref': 50000, 'fut': 408895, 'inow': -157924, 'dtot': 349029, 'ratio': 0.5817}, SZ.LEAD_Q))
    # 해마다 입주 신호등(2026-10-05 — 판정 배지 자리). 10-05 라이브 수도권 62·69·73% 모양, 값·키는 정본 함수로
    yrs = [{'n': i + 1, 'pct': p} for i, p in enumerate((62, 69, 73))]
    z['yl'] = [{'n': y['n'], 'p': y['pct'], 'k': SZ.light_of(y['pct'])[0]} for y in yrs]
    z['ya'] = SZ.lights_aria(yrs)
    js = ('var TB_GRADE=%s;function tbSigned(v){return String(v)}\n%s\n%s\n'
          'const z=%s, old={grade:"g2",tot:1,ctxt:"349,029세대 부족 · 3년 필요량의 58%%"};\n'
          'const p={hidden:true}, b={a:{"aria-expanded":"false","aria-controls":"agg-how-1"},'
          'getAttribute(k){return this.a[k]},setAttribute(k,v){this.a[k]=v}};\n'
          'globalThis.document={getElementById:id=>id==="agg-how-1"?p:null};\n'
          'const st=[];aggHow(b);st.push([b.a["aria-expanded"],p.hidden]);aggHow(b);st.push([b.a["aria-expanded"],p.hidden]);\n'
          'process.stdout.write(JSON.stringify([aggCard("수도권",z,1),aggCard("수도권",old,1),st]));'
          % (json.dumps(SZ.GRADE_LABS, ensure_ascii=False), _js_func(h, 'aggLights') + _js_func(h, 'aggCard'), _js_func(h, 'aggHow'),
             json.dumps(z, ensure_ascii=False)))
    card, old, toggles = _node(js)
    a = re.search(r'<a class="agg-a" href="/zone/[^"]+/">(.*?)</a>(.*)</div>$', card, re.S)
    assert a and '<button' not in a.group(1) and a.group(2).startswith('<button type="button" class="agg-i"'), card
    assert 'aria-expanded="false" aria-controls="agg-how-1"' in a.group(2)
    assert ('<span class="agg-l1"><b>수도권</b><span class="zl" role="img" aria-label="%s"><span class="zl-d lo">1</span>'
            '<span class="zl-d lo">2</span><span class="zl-d ok">3</span></span></span>' % z['ya']) in a.group(1), a.group(1)
    assert 'sc-tier' not in a.group(1), '신호등이 있는 카드에 판정 배지가 남았다'
    assert '<span class="sc-tier g2">부족</span>' in old, '옛 캐시(yl 없음)는 예전 배지를 그린다'
    assert re.search(r'<i class="agg-n">349,029세대<span class="agg-dir"> 부족</span><span class="agg-go"[^>]*> →</span></i>',
                     a.group(1)), a.group(1)
    assert '<i class="agg-p">%s</i>' % z['cpct'] in a.group(1) and z['cpct'] == '1년 적정물량의 1.7배', a.group(1)
    assert toggles == [['true', False], ['false', True]], toggles
    assert '<button' not in old and '349,029세대 부족' in old
    how = _js_func(h, 'renderAggCards')   # 카드·ⓘ 식은 2026-10-04 에 지도 상자 밖(#agg-wrap)으로 나갔다
    assert "'<p class=\"agg-how\" id=\"agg-how-'+i+'\" hidden>" in how and 'z.ftxt' in how
