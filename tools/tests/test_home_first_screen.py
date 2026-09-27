# -*- coding: utf-8 -*-
"""홈 첫 화면 — '이번 주' 띠·판정 카드·분포 한 줄·카드 ⓘ 식·지도 균형 중립색(홈 마케팅 검수 B1·B2·C4, 2026-09-27).

재현하는 실제 상태(09-26 라이브 375×812 첫 화면)
  - 첫 화면의 글자는 전부 분기 단위(히어로·카드 셋·'2026년 2분기 기준')라 한 분기 내내 같은 화면이었다. 매주 바뀌는
    이번 주 시군구 지도는 이름 없는 배경 무늬였고, 주간 구역 h2 는 매주 같은 질문이었다(HERO-2·RET-1·IA-4·IA-5·MOB-1).
  - 카드 셋이 모두 '부족'이고 지도는 균형 지역(충북 1%·세종 13%·경기 17%)까지 연한 빨강이라 16곳 중 13곳이 붉었다.
    '3년 필요량의 60%'는 '60%만 지어진다'로도 읽혔고, 686,396 = 1,140,000 − 714,127 + 260,523(지난 4년 쌓인 부족)을
    홈 재료로는 검산할 수 없었다(HERO-4·TRUST-2·TRUST-3). 375px 에서 수도권만 배지가 둘째 줄로 내려갔다(MOB-7).
원칙: 문장은 한 곳에서 만든다. 결론 한 줄은 make_weekly_page.conclusion(→ split_data 가 ADV.weekly.head 로 굽는다),
카드·식·분포·범례 문구는 sido_zones(→ refresh_texts), 발표 일정 문장은 weekly_release/weeklyRelease. 홈 JS 는 읽기만 한다.
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
FONTS = os.path.join(ROOT, 'tools', 'fonts')

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
    """띠·주간 h2 를 만드는 홈 함수들(순수 함수 + h2 적기)을 그대로 뽑는다."""
    h = _home()
    return '\n'.join([_wk_block()] + [_js_func(h, n) for n in
                                      ('pubDate', 'weeklyHead', 'heroBandLines', 'applyWeeklyStatus')])


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


def test_weekly_head_is_one_sentence_on_weekly_page_band_and_home_h2():
    """/weekly/ 제목 = '이번 주 아파트, ' + 결론, 홈 띠 첫 줄 = [발표일, 결론 →], 홈 주간 h2 = 결론(B1·IA-4).

    변이(각각 실제로 확인): make_weekly_page.h1_html 이 동사를 따로 적으면('가장 크게 올랐다') 첫 단정, head_payload 가
    text 를 빼면 둘째, 홈 heroBandLines 가 결론을 다시 만들면(hd.text 대신 자기 문장) 셋째, applyWeeklyStatus 가 hd 를
    무시하면(옛 고정 질문) 넷째 단정이 빨개진다.
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
              'const el={"wk-kicker":{textContent:""},"wk-h2":{textContent:"이번 주, 어디가 오르고 내렸을까?"}};\n'
              'globalThis.document={getElementById:id=>el[id]||null};\n'
              'applyWeeklyStatus(r,weeklyHead(W));\n'
              'process.stdout.write(JSON.stringify([heroBandLines(W,r),el["wk-h2"].textContent]));'
              % (json.dumps(H2026), json.dumps(WJ, ensure_ascii=False), _kst_ms(2026, 9, 11)))
        band, h2 = _node(js)
        assert band[0] == ['9/10 발표', want + ' →'], (key, band)
        assert h2 == want, (key, h2)


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


# ── B1: 띠 두 줄은 발표 상태를 따른다(주간 구역 머리줄과 같은 함수) ───────────────────────────────

def test_hero_band_lines_follow_the_release_state():
    """띠 둘째 줄의 뒤 조각은 wkNextText(주간 머리줄·통계 탭과 같은 함수)이고, 파이썬 정본(weekly_release.next_text)과 같다.
    늦은 주에는 '반영 대기', 연휴 주에는 날짜 대신 안내, 캡션은 늦거나 시군구 주가 다르면 '이번 주' 대신 발표일.
    옛 캐시(결론·유예 없음)와 섞인 판(head.p ≠ 최신 조사일)은 null — 정적 문구가 남는다.

    변이(각각 실제로 확인): heroBandLines 의 `W.grace==null` 검사를 빼면 옛 캐시 사례가, 캡션 조건에서 `!r.stale` 을 빼면
    늦은 주 사례가, wkNextText(r) 대신 '다음 발표 '+_md(r.next) 를 쓰면 연휴·늦은 주 사례가, weeklyHead 의 조사일 비교를
    빼면 섞인 판 사례가 빨개진다.
    픽스처: 2026 공휴일 표. 평상(9/7 조사, 오늘 9/11), 추석 연휴 주(9/14 조사, 9/18 — 다음 발표 9/24 가 휴일),
            배치 정지(9/14 조사, 9/29 — 기준일 9/28 이 지남), 시군구만 한 주 늦음(시도 9/21·시군구 9/14, 9/25).
    """
    base = {'p': None, 'text': '경기 +0.23%, 가장 크게 올랐습니다', 'dir': 'up'}
    cases = []

    def case(p, when, sgg_p=None, head=True, grace=WR.GRACE_WEEKLY, head_p=None, sgg=True):
        W, _ = _week({}, p, sgg_p)
        W.pop('holidays')
        if head:
            W['head'] = dict(base, p=head_p or p)
        if grace is not None:
            W['grace'] = grace
        if not sgg:
            W.pop('sgg')
        cases.append((W, _kst_ms(*when)))
        return len(cases) - 1

    normal = case('2026-09-07', (2026, 9, 11))
    hedge = case('2026-09-14', (2026, 9, 18))
    stale = case('2026-09-14', (2026, 9, 29))
    lag = case('2026-09-21', (2026, 9, 25), sgg_p='2026-09-14')
    no_head = case('2026-09-07', (2026, 9, 11), head=False)
    no_grace = case('2026-09-07', (2026, 9, 11), grace=None)
    mixed = case('2026-09-07', (2026, 9, 11), head_p='2026-08-31')
    no_sgg = case('2026-09-07', (2026, 9, 11), sgg=False)
    js = (_band_js() + '\n_HOLIDAYS=new Set(%s);const C=%s;\n'
          'process.stdout.write(JSON.stringify(C.map(([W,ms])=>heroBandLines(W,weeklyRelease(W.rows[0].p,new Date(ms),W.grace)))));'
          % (json.dumps(H2026), json.dumps(cases, ensure_ascii=False)))
    got = _node(js)
    T = base['text'] + ' →'

    def nxt(p, d):
        return WR.next_text(WR.status(p, d, H2026))
    assert got[normal] == [['9/10 발표', T], ['배경 지도: 이번 주 시군구 매매 변동', nxt('2026-09-07', datetime.date(2026, 9, 11))]]
    assert got[normal][1][1] == '다음 발표 9/17(목)'
    assert got[hedge][1] == ['배경 지도: 이번 주 시군구 매매 변동', WR.HOLD]
    assert got[stale] == [['9/17 발표', T], ['배경 지도: 9/17 발표 시군구 매매 변동', WR.WAIT]]
    assert nxt('2026-09-14', datetime.date(2026, 9, 29)) == WR.WAIT
    assert got[lag][1][0] == '배경 지도: 9/17 발표 시군구 매매 변동', got[lag]
    assert got[no_head] is None and got[no_grace] is None and got[mixed] is None
    assert got[no_sgg][1] == ['한국부동산원 주간 통계', '다음 발표 9/17(목)']


def _hero():
    m = re.search(r'<header class="home-hero">(.*?)</header>', _src('index.html'), re.S)
    assert m, '홈 히어로를 찾지 못했다'
    return m.group(1)


def test_hero_band_is_one_link_to_weekly_under_the_title_and_boot_fills_it():
    """띠는 h1·부제 바로 아래 한 줄 전체 /weekly/ 링크이고 home_cta to='weekly_hero' 로 잰다(B1). 정적 문구는 날짜·'이번 주'를
    약속하지 않는다(스크립트가 못 돌거나 옛 캐시일 때 보이는 문구 — TRUST-1). 부팅이 renderHeroBand 를 부른다.

    변이: 정적 문구를 '이번 주 시세 · 9/24 발표'로 바꾸면, boot 에서 renderHeroBand() 를 지우면, 띠를 h1 위로 옮기면
          빨개진다(확인).
    """
    hero = _hero()
    m = re.search(r'<a class="hero-wk" id="hero-wk" href="/weekly/" '
                  r"""onclick="track\('home_cta',\{to:'weekly_hero'\}\)">(.*?)</a>""", hero, re.S)
    assert m, '히어로에 /weekly/ 띠 링크가 없다'
    assert hero.index('<h1 class="hero-msg">') < hero.index('<p class="hero-sub">') < m.start()
    static = _plain(m.group(1))
    assert not re.search(r'\d|이번 주|매주 갱신', static), static
    for line in ('hw-1', 'hw-2'):
        inner = re.search(r'<span class="%s" id="%s">(.*?)</span></span>' % (line, line), m.group(1), re.S)
        assert inner and re.fullmatch(r'<span class="hw-a">[^<]+</span><span class="hw-s"> · </span>'
                                      r'<span class="hw-b">[^<]+', inner.group(1)), line
    assert 'renderHeroBand();' in _js_func(_home(), 'boot')


def _css():
    return _src('app.css')


def _rule(css, sel):
    m = re.search(r'(?:^|[}\s])' + re.escape(sel) + r'\{([^}]*)\}', css)
    assert m, 'app.css 에서 %s 규칙을 찾지 못했다' % sel
    return m.group(1)


def test_home_hero_band_fits():
    """띠의 줄 수는 폭으로 고정된다 — 조각(날짜·결론 / 캡션·다음 발표)이 정해진 폭에서만 줄을 바꾸므로, 가장 긴 문구도 조각
    하나가 한 줄 안에 들어가야 정적 문구 → 데이터 문구로 바뀔 때 높이가 같다(CLS 0). 운영 글꼴(Pretendard 서브셋)로 잰다.

    Chromium 실측(2026-09-27, playwright): 띠 높이가 정적·평상·연휴·반영 대기·옛 캐시·전남광주 하락에서 모두 같았다
    (320px 91.3 · 360px 73.8 · 375px 74.2 · 414px 76.0 · 480px 이상 60).
    변이(각각 확인): 둘째 줄을 조각마다 바꾸는 폭을 479→399px 로 줄이면 400~479px 에서, 첫 줄 글자를 clamp(…,3.6vw,…)
    로 키우면 360px 에서, 첫 줄을 조각마다 바꾸는 규칙(359px)을 지우면 320px 에서 빨개진다.
    픽스처: 가장 긴 경우를 함수로 만든다 — 이름이 가장 긴 시도의 하락 결론(conclusion), 두 자리 달·날짜(12/28),
            가장 긴 다음 발표 문장(연휴 안내·반영 대기·'다음 발표 12/31(목)' 중), 시군구 주가 다른 캡션.
    """
    ImageFont = pytest.importorskip('PIL.ImageFont')
    css = _css()
    pad = int(re.search(r'padding:0 (\d+)px', _rule(css, '.wrap')).group(1))
    band = _rule(css, '.hero-wk')
    maxw = int(re.search(r'max-width:(\d+)px', band).group(1))
    bpad = int(re.search(r'padding:\d+px (\d+)px', band).group(1))
    bord = int(re.search(r'border:(\d+)px', band).group(1))
    lo, mid, hi = (float(x) for x in re.search(r'font-size:clamp\(([\d.]+)px,([\d.]+)vw,([\d.]+)px\)',
                                               _rule(css, '.hero-wk .hw-1')).groups())
    f2 = float(re.search(r'font-size:([\d.]+)px', _rule(css, '.hero-wk .hw-2')).group(1))
    split1 = int(re.search(r'@media\(max-width:(\d+)px\)\{\.hero-wk \.hw-1 \.hw-s\{display:none\}', css).group(1))
    split2 = int(re.search(r'@media\(max-width:(\d+)px\)\{\.hero-wk \.hw-2 \.hw-s\{display:none\}', css).group(1))
    bold = os.path.join(FONTS, 'Pretendard-Bold.subset.ttf')
    med = os.path.join(FONTS, 'Pretendard-Medium.subset.ttf')
    longest = max((z for z in MW.SIDO), key=lambda z: ImageFont.truetype(bold, 13).getlength(z))
    W, _ = _week({longest: -1.23}, '2026-12-21')
    concl = MW.conclusion(W)['text'] + ' →'
    date = '12/28 발표'
    cap = '배경 지도: 12/28 발표 시군구 매매 변동'
    nxts = [WR.HOLD, WR.WAIT, '다음 발표 12/31(목)']
    bad = []
    for vw in (320, 340, 359, 360, 375, 390, 399, 400, 414, 430, 460, 479, 480, 560, 768, 1280):
        inner = min(vw - 2 * pad, maxw) - 2 * bpad - 2 * bord - 2   # 2px: 글꼴 래스터 차이 여유
        s1 = min(max(lo, mid * vw / 100), hi)
        g1 = ImageFont.truetype(bold, round(s1 * 2) / 2)
        g2 = ImageFont.truetype(med, f2)
        l1 = [date, concl] if vw <= split1 else [date + ' · ' + concl]
        l2 = [cap] + nxts if vw <= split2 else [cap + ' · ' + n for n in nxts]
        for t in l1:
            if g1.getlength(t) > inner:
                bad.append('%dpx 첫 줄 %.0f > %d: %s' % (vw, g1.getlength(t), inner, t))
        for t in l2:
            if g2.getlength(t) > inner:
                bad.append('%dpx 둘째 줄 %.0f > %d: %s' % (vw, g2.getlength(t), inner, t))
    assert not bad, '띠 조각이 한 줄을 넘는다 — 데이터 문구가 들어오면 높이가 달라져 아래가 밀린다:\n' + '\n'.join(bad)


# ── B2·C4①: 식 한 줄은 홈 산출 방법·홈 카드 ⓘ·시도 리포트·블로그에서 같은 말 ──────────────────────────

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
        nums = [int(x.replace(',', '')) for x in re.findall(r'[\d,]{2,}', eq.replace('%s년' % (H // 4), '')
                                                                             .replace('%d년' % (SZ.BACKLOG_WINDOW // 4), ''))]
        sign = 1 if '쌓인 부족' in eq else -1
        assert nums[0] - nums[1] + sign * nums[2] == tot, (z['z'], eq, tot)
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
    assert "fill=\"'+supplyFill(z)+'\"" in _js_func(h, 'renderSidoMap'), '지도 도형이 균형 중립색 규칙을 쓰지 않는다'

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


# ── B2: 분포 한 줄 ─────────────────────────────────────────────────────────────────────────────

def test_distribution_line_counts_the_zones():
    """'시도 N곳: 부족 이상 a · 균형 b · 여유 c' — 곳 수와 N 은 판정에서 센다(HERO-4·TRUST-3). 묶음은 등급 키를 한 번씩 덮는다.

    변이: dist_text 에 '시도 16곳'을 박으면 15곳 픽스처에서, DIST_GROUPS 의 '부족 이상'에서 g3 를 빼면(모듈 머리의 검사가
          SystemExit) 불러오기부터 빨개진다(둘 다 확인). 홈이 ADV.sido.dist 를 안 그리면 마지막 단정.
    픽스처: 집계 셋 + 시도 15곳(심각 1·매우 2·부족 4·균형 5·여유 3) — 등급마다 수를 다르게 두어 자리가 바뀌면 드러난다.
    """
    grades = ['g4'] + ['g3'] * 2 + ['g2'] * 4 + ['g1'] * 5 + ['g0'] * 3
    zones = [{'z': a, 'agg': True, 'grade': 'g2'} for a in SZ.AGG] + \
            [{'z': 'X%d' % i, 'agg': False, 'grade': g} for i, g in enumerate(grades)]
    assert SZ.dist_text(zones) == '시도 15곳: 부족 이상 7 · 균형 5 · 여유 3'
    keys = [k for _, ks in SZ.DIST_GROUPS for k in ks]
    assert sorted(keys) == sorted(SZ.GRADE_KEYS) and len(keys) == len(set(keys))
    assert [n for n, _ in SZ.DIST_GROUPS] == ['부족 이상', '균형', '여유']
    assert "'<p class=\"agg-dist\">'+ADV.sido.dist+'</p>'" in _js_func(_home(), 'renderSidoMap')


# ── B2·C4①·MOB-7: 카드는 두 줄 링크, ⓘ 는 링크 밖 버튼 ─────────────────────────────────────────────

def test_cards_are_two_line_links_and_the_how_button_toggles():
    """카드 = '전국 [부족]' / '686,396세대 →' 두 줄 링크(넓은 화면만 '부족'·'3년 필요량의 60%만큼'이 보인다), ⓘ 는 링크 밖의
    button(aria-expanded·aria-controls) — 누르면 식 한 줄이 펼쳐지고 다시 누르면 접힌다(기본은 접힘). 옛 캐시는 ⓘ 없음.

    변이(각각 확인): ⓘ 를 </a> 앞(링크 안)으로 옮기면 첫 단정, aggHow 가 hidden 을 안 바꾸면 토글 단정, 카드 둘째 줄이 ctxt
          통째를 쓰면(모바일 두 줄 고정이 깨짐) 세대수 단정이 빨개진다.
    픽스처: 09-26 라이브 수도권 카드(349,029세대 부족·58%, g2)와 같은 필드 모양, 옛 캐시 모양(ctxt 만).
    """
    h = _home()
    z = dict(z='수도권', grade='g2', tot=349029, **SZ.zone_texts(
        {'ref': 50000, 'fut': 408895, 'inow': -157924, 'dtot': 349029, 'ratio': 0.5817}, SZ.LEAD_Q))
    js = ('var TB_GRADE=%s;function tbSigned(v){return String(v)}\n%s\n%s\n'
          'const z=%s, old={grade:"g2",tot:1,ctxt:"349,029세대 부족 · 3년 필요량의 58%%"};\n'
          'const p={hidden:true}, b={a:{"aria-expanded":"false","aria-controls":"agg-how-1"},'
          'getAttribute(k){return this.a[k]},setAttribute(k,v){this.a[k]=v}};\n'
          'globalThis.document={getElementById:id=>id==="agg-how-1"?p:null};\n'
          'const st=[];aggHow(b);st.push([b.a["aria-expanded"],p.hidden]);aggHow(b);st.push([b.a["aria-expanded"],p.hidden]);\n'
          'process.stdout.write(JSON.stringify([aggCard("수도권",z,1),aggCard("수도권",old,1),st]));'
          % (json.dumps(SZ.GRADE_LABS, ensure_ascii=False), _js_func(h, 'aggCard'), _js_func(h, 'aggHow'),
             json.dumps(z, ensure_ascii=False)))
    card, old, toggles = _node(js)
    a = re.search(r'<a class="agg-a" href="/zone/[^"]+/">(.*?)</a>(.*)</div>$', card, re.S)
    assert a and '<button' not in a.group(1) and a.group(2).startswith('<button type="button" class="agg-i"'), card
    assert 'aria-expanded="false" aria-controls="agg-how-1"' in a.group(2)
    assert '<span class="agg-l1"><b>수도권</b><span class="sc-tier g2">부족</span></span>' in a.group(1)
    assert re.search(r'<i class="agg-n">349,029세대<span class="agg-dir"> 부족</span><span class="agg-go"[^>]*> →</span></i>',
                     a.group(1)), a.group(1)
    assert '<i class="agg-p">3년 필요량의 58%만큼</i>' in a.group(1)
    assert toggles == [['true', False], ['false', True]], toggles
    assert '<button' not in old and '349,029세대 부족' in old
    how = _js_func(h, 'renderSidoMap')
    assert "'<p class=\"agg-how\" id=\"agg-how-'+i+'\" hidden>" in how and 'z.ftxt' in how
