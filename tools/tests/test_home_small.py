# -*- coding: utf-8 -*-
"""홈 작은 장치 — 내 지역(C5)·이달의 통계 입구(B6)·출처·구간·운영 주체(B9)·측정(B10)·설치 안내(C10①). 2026-09-27 홈 마케팅 검수 3차.

재현하는 실제 상태
  - 재방문 장치(내 지역 저장 08-06)가 걷힌 뒤 대체가 없었다. 방문자는 매번 시도 격자에서 자기 지역을 찾았다(RET-6).
    되살린 형태는 순위·생활권이 아니라 '기기에 시도 한 곳' 최소안이다. 광주·전남이 09-10 '전남광주'로 합쳐진 것처럼 판정 단위가
    바뀌면 저장된 옛 이름은 없는 지역이 된다 — 그런 이름은 무시해야 한다. 사생활 모드 Safari 는 localStorage 에 접근만 해도 던진다.
  - 첫 화면 '3년'이 어느 분기부터 어느 분기까지인지 홈 어디에도 없었고(TRUST-5), 운영 주체·제보 메일은 퀴즈·사이클 뒤 푸터에만
    일반 텍스트로 있었다(TRUST-6). 매달 돌아오는 /monthly/ 는 홈 본문에 입구가 없었다(IA-8).
  - 주간 구역이 화면에 들어왔는지 재는 이벤트가 없어 클릭률의 분모가 없었고, 재방문을 가를 신호·배포 구분값이 없었다(MEAS-3).
  - 설치 유도가 없었다(PWA-1).
방법: home-app.js 의 <home-small> 구간을 통째로 node vm 에 올리고(발표 일정 <wk-release> 구간·pv2·tbSigned·TB_GRADE 와 함께 —
홈 스크립트는 tools/home_src 입구로만 읽는다), document·localStorage·window·gtag 는 흉내 낸다. 날짜는 고정 합성값이다.
각 시험 독스트링에 ① 무엇을 깨뜨리면 빨개지는지(실제로 변이를 넣어 확인) ② 픽스처가 재현하는 상태를 적었다.
"""
import inspect
import json
import os
import re
import shutil
import subprocess
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_sido_pages as M  # noqa: E402
import sido_zones as SZ  # noqa: E402


def _home():
    return HS.home_source()


def _js_func(src, name):
    m = re.search(r'^function %s\(' % re.escape(name), src, re.M)
    assert m, 'home-app.js 에서 %s 를 찾지 못했다' % name
    i = src.index('{', m.end())
    depth = 0
    for j in range(i, len(src)):
        depth += {'{': 1, '}': -1}.get(src[j], 0)
        if depth == 0:
            return src[m.start():j + 1]
    raise AssertionError('%s 의 끝을 찾지 못했다' % name)


def _block(tag):
    m = re.search(r'// <%s>[^\n]*\n(.*?)// </%s>' % (tag, tag), _home(), re.S)
    assert m, 'home-app.js 에서 <%s> 구간을 찾지 못했다' % tag
    return m.group(1)


def _tb_grade():
    m = re.search(r'^var TB_GRADE=(\{[^}]*\});', _home(), re.M)
    assert m, 'TB_GRADE 를 찾지 못했다'
    return m.group(1)


HARNESS = r'''
const vm = require('vm');
const CFG = %(cfg)s;
function run(o) {
  const rec = {track: [], gtag: [], listeners: {}, removed: [], timers: [], appended: [], boxRemoved: 0};
  const data = Object.assign({}, o.store || {});
  const els = {};
  function el(id) {
    return els[id] = {id, hidden: true, textContent: '', innerHTML: '', href: '', value: '', style: {}, opts: [],
      rect: {top: 0, bottom: 0}, appendChild(c) { this.opts.push(c.value); },
      getBoundingClientRect() { return this.rect; }, addEventListener() {}};
  }
  ['myz', 'myz-n', 'myz-a', 'myz-v', 'myz-pick', 'myz-sel', 'myz-msg', 'map-span', 'home-weekly-grid', 'wk-h2'].forEach(el);
  const bad = () => { throw new Error('SecurityError: storage is disabled'); };
  const store = o.storage === 'throw' ? {getItem: bad, setItem: bad, removeItem: bad}
    : {getItem: (k) => Object.prototype.hasOwnProperty.call(data, k) ? data[k] : null,
       setItem: (k, v) => { data[k] = String(v); }, removeItem: (k) => { delete data[k]; }};
  const ctx = {JSON, Math, Date, Object, Array, String, Number, Set, Error, Promise, console, encodeURIComponent};
  ctx.track = (e, p) => rec.track.push([e, p]);
  if (!o.noGtag) ctx.gtag = function () { rec.gtag.push([].slice.call(arguments)); };
  ctx.localStorage = store;
  ctx.navigator = {userAgent: o.ua || '', maxTouchPoints: o.touch || 0};
  ctx.window = {innerHeight: o.vh || 800,
    addEventListener(ev, fn) { (rec.listeners[ev] = rec.listeners[ev] || []).push(fn); },
    removeEventListener(ev) { rec.removed.push(ev); }};
  ctx.setTimeout = (fn, ms) => { rec.timers.push({fn, ms}); return rec.timers.length; };
  ctx.document = {
    getElementById: (id) => els[id] || null,
    querySelectorAll: () => [],
    documentElement: {clientHeight: o.vh || 800, classList: {contains: (c) => (o.htmlClass || []).includes(c)}},
    createElement: () => {
      const b = {id: '', className: '', attrs: {}, innerHTML: '', h: {},
        setAttribute(k, v) { this.attrs[k] = v; },
        querySelector(sel) { const self = this; return this.innerHTML.includes('class="' + sel.slice(1) + '"')
          ? {addEventListener(ev, fn) { self.h[sel] = fn; }} : null; },
        remove() { rec.boxRemoved++; delete els[this.id]; }};
      return b;
    },
    body: {appendChild(b) { rec.appended.push(b.innerHTML); els[b.id] = b; }},
  };
  vm.createContext(ctx);
  vm.runInContext('var curView=' + JSON.stringify(o.view || 'home') + ';\n' + CFG.prelude, ctx);
  vm.runInContext(CFG.block, ctx);
  const OUT = {};
  ctx.OUT = OUT; ctx.__els = els; ctx.__rec = rec; ctx.__data = data;
  ctx.__timers = () => { const t = rec.timers.splice(0); t.forEach((x) => x.fn()); return t.length; };
  vm.runInContext(o.js, ctx);
  return {out: OUT, track: rec.track, gtag: rec.gtag, store: data, removed: rec.removed, appended: rec.appended,
          boxRemoved: rec.boxRemoved, listen: Object.keys(rec.listeners)};
}
process.stdout.write(JSON.stringify(CFG.cases.map(run)));
'''


def _run(*cases):
    node = shutil.which('node')
    if not node:
        pytest.skip('node 없음')   # CI 에서는 conftest 가 실패로 바꾼다
    h = _home()
    prelude = '\n'.join([_block('wk-release'), _js_func(h, 'pv2r'), _js_func(h, 'pv2'), _js_func(h, 'tbSigned'),
                         'var TB_GRADE=%s;' % _tb_grade()])
    cfg = {'prelude': prelude, 'block': _block('home-small'), 'cases': list(cases)}
    p = subprocess.run([node, '-e', HARNESS % {'cfg': json.dumps(cfg, ensure_ascii=False)}],
                       capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _sido():
    """합성 판정 — 모양은 ADV.sido(sido_zones.calc → refresh_texts)와 같다. 문구는 정본 함수(zone_texts)로 굽는다."""
    def z(name, grade, tot, ratio, agg=False):
        row = {'z': name, 'agg': agg, 'grade': grade, 'tot': tot, 'dtot': tot, 'ratio': ratio, 'ref': 10000, 'fut': 60000}
        row['inow'] = row['ref'] * SZ.LEAD_Q - row['fut'] - tot    # 필요량 − 입주 추정 − 지난 재고 = 순부족(검산되게)
        row.update(SZ.zone_texts(row, SZ.LEAD_Q))
        return row
    zones = [z('전국', 'g2', 686396, 0.6, True), z('수도권', 'g2', 349029, 0.58, True), z('지방', 'g2', 337367, 0.62, True),
             z('서울', 'g3', 311689, 1.389), z('인천', 'g0', -12000, -0.2), z('전남광주', 'g4', 98765, 2.1)]
    return {'L': '2026Q2', 'H': SZ.LEAD_Q, 'zones': zones}


def _weekly():
    regs = list(SZ.DISPLAY_ORDER)
    ma = [0.01] * len(regs)
    ma[regs.index('서울')] = 0.1342
    ma[regs.index('전남광주')] = -0.0012     # 반올림하면 0.00 — 부호가 붙으면 안 된다(격자와 같은 pv2)
    return {'regions': regs, 'rows': [{'p': '2026-09-14', 'ma': [0.0] * len(regs)}, {'p': '2026-09-21', 'ma': ma}]}


def _data_js():
    return 'var ADV={sido:%s,weekly:%s};' % (json.dumps(_sido(), ensure_ascii=False), json.dumps(_weekly(), ensure_ascii=False))


# ── C5 내 지역 ────────────────────────────────────────────────────────────────────────────────

def test_my_zone_line_shows_this_week_and_the_verdict_from_the_baked_strings():
    """고정한 시도의 이번 주 매매 변동(최신 행, pv2 반올림)과 판정(등급 이름 + 카드와 같은 cnum·cdir)이 띠 앞 줄에 선다.
    줄은 그 시도 리포트로 가고, 고르기 목록은 판정 단위(집계 3종 제외)다.

    변이(각각 실제로 확인): myZoneOf 가 최신 행 대신 rows[0] 을 읽으면 매매 단정이, cnum 대신 ctxt 통째를 쓰면 세대수 단정이,
          myZoneLine 이 pv2 대신 toFixed(2) 를 쓰면 전남광주 '−0.00' 단정이, initMyZonePick 이 agg 를 거르지 않으면 목록 단정이
          빨개진다.
    픽스처: 09-26 라이브 서울 행 모양(311,689세대 부족·139%·g3)과 반올림하면 0 인 하락(−0.0012, 08-18 부산 실측 유형).
    """
    js = _data_js() + '''
      renderMyZone(); OUT.seoul = [__els.myz.hidden, __els['myz-n'].textContent, __els['myz-a'].href, __els['myz-v'].innerHTML];
      initMyZonePick(); OUT.pick = [__els['myz-pick'].hidden, __els['myz-sel'].opts, __els['myz-sel'].value];
      localStorage.setItem(MYZ_KEY, '전남광주'); renderMyZone(); OUT.jn = __els['myz-v'].innerHTML;
    '''
    got = _run({'store': {'agongmap-myzone': '서울'}, 'js': js})[0]['out']
    hidden, name, href, line = got['seoul']
    seoul = next(z for z in _sido()['zones'] if z['z'] == '서울')
    assert (hidden, name, href) == (False, '서울', '/zone/%EC%84%9C%EC%9A%B8/')
    assert line == '매매 +0.13%% · <span class="sc-tier g3">%s</span> %s<span class="myz-dir"> %s</span> →' % (
        SZ.GRADE_LABS['g3'], seoul['cnum'], seoul['cdir']), line
    assert got['pick'] == [False, ['서울', '인천', '전남광주'], '서울'], got['pick']
    assert got['jn'].startswith('매매 0.00% · <span class="sc-tier g4">'), got['jn']


def test_my_zone_ignores_unknown_names_and_survives_a_throwing_storage():
    """없는 시도 이름(판정 단위 개편으로 사라진 '광주'), 집계 이름('전국'), 빈 값은 무시한다 — 줄을 닫는다. 판정 데이터가 실린
    부팅이면 없는 이름의 저장값을 지운다(남겨 두면 인라인 스크립트가 방문마다 자리를 열었다 닫아 CLS — Chromium 375px 0.07 실측).
    데이터가 안 온 부팅(옛 캐시·조각 실패)에서는 지우지 않는다.
    저장소가 던지는 기기(사생활 모드)는 조용히 빠진다: 줄은 닫히고, 고르기 줄은 열리지 않고, 고정 시도는 예외 없이 아무 일도
    안 하며 이벤트도 가지 않는다.

    변이(각각 실제로 확인): lsGet 의 try/catch 를 벗기면 던지는 저장소 사례가(node 예외), myZoneOf 의 `&&!x.agg` 를 빼면 '전국'
          사례가, initMyZonePick 의 lsOk() 검사를 빼면 고르기 줄 단정이, myZoneSet 이 lsSet 실패를 무시하고 track 하면 이벤트 단정이
          빨개진다. renderMyZone 의 저장값 지우기를 빼면 지우기 단정이, 데이터 확인(S.zones.length) 없이 지우면 데이터 없는 부팅
          단정이 빨개진다.
    픽스처: 09-10 광주·전남 통합 전에 저장했을 법한 '광주', 집계 '전국', data-core 가 안 온 부팅, 사생활 모드(모든 접근이 SecurityError).
    """
    base = _data_js() + 'renderMyZone(); OUT.hidden = __els.myz.hidden;'
    cases = [{'store': {'agongmap-myzone': n}, 'js': base} for n in ('광주', '전국', '')]
    cases.append({'store': {'agongmap-myzone': '광주'}, 'js': 'var ADV={}; renderMyZone(); OUT.hidden = __els.myz.hidden;'})
    cases.append({'storage': 'throw', 'js': _data_js() + '''
      __els.myz.hidden = false;            // 인라인 스크립트가 열었다고 치고(실제로는 거기서도 던져 닫혀 있다)
      renderMyZone(); initMyZonePick(); myZoneSet('서울'); myZoneSet('');
      OUT.hidden = __els.myz.hidden; OUT.pick = __els['myz-pick'].hidden;'''})
    got = _run(*cases)
    for g, n, kept in zip(got[:4], ('광주', '전국', '', '광주'), (False, False, True, True)):
        assert g['out']['hidden'] is True, n
        assert ('agongmap-myzone' in g['store']) is kept, (n, g['store'])
    t = got[4]
    assert t['out'] == {'hidden': True, 'pick': True} and t['track'] == [], t


def test_pin_and_unpin_restore_the_myzone_event():
    """고정·해제는 myzone{action} 이벤트로 잰다(08-14 에 죽은 이벤트로 해제했던 이름을 기능과 함께 복원 — RET-6 권고). 고른 시도
    이름은 싣지 않는다(개인정보처리방침: 선택 지역은 브라우저에만 저장, 서버로 전송·수집하지 않음). 없는 이름으로 고정하려 하면
    아무 일도 없다. 해제는 저장값을 지운다.

    변이(각각 실제로 확인): myZoneSet 의 unpin track 을 지우면, `if(name&&!o)return` 을 지우면(없는 이름이 저장된다),
          해제 때 removeItem 대신 빈 문자열을 저장하면(lsSet(MYZ_KEY,'')) 빨개진다.
    픽스처: 아무것도 고정하지 않은 기기에서 서울 고정 → 없는 이름 '광주' 고정 시도 → 해제.
    """
    js = _data_js() + '''
      myZoneSet('서울'); OUT.a = [__data[MYZ_KEY], __els.myz.hidden, __els['myz-msg'].textContent];
      myZoneSet('광주'); OUT.b = __data[MYZ_KEY];
      myZoneSet(''); OUT.c = [Object.prototype.hasOwnProperty.call(__data, MYZ_KEY), __els.myz.hidden];'''
    g = _run({'js': js})[0]
    assert g['out']['a'] == ['서울', False, '첫 화면 맨 위에 고정했습니다']
    assert g['out']['b'] == '서울'
    assert g['out']['c'] == [False, True]
    assert [t for t in g['track'] if t[0] == 'myzone'] == [['myzone', {'action': 'pin'}], ['myzone', {'action': 'unpin'}]]


def test_grade_names_and_storage_key_have_one_source():
    """홈의 등급 이름(TB_GRADE)은 sido_zones.GRADE_LABS 와 같고, 첫 페인트 전에 자리를 여는 index.html 인라인 스크립트는
    home-app.js 의 MYZ_KEY 와 같은 키를 읽는다. 그 인라인 스크립트는 '내 지역' 줄 바로 뒤, '이번 주' 띠 앞에 있다(C5 '띠 앞').

    변이(각각 실제로 확인): 인라인 스크립트의 키를 'agong_myzone' 으로 바꾸면, TB_GRADE 의 g2 를 '다소 부족'으로 바꾸면,
          '내 지역' 줄을 띠 뒤로 옮기면 빨개진다.
    """
    assert json.loads(_tb_grade().replace("'", '"').replace('g4:', '"g4":').replace('g3:', '"g3":')
                      .replace('g2:', '"g2":').replace('g1:', '"g1":').replace('g0:', '"g0":')) == SZ.GRADE_LABS
    key = re.search(r"^const MYZ_KEY='([^']+)';", _home(), re.M)
    assert key, 'MYZ_KEY 가 없다'
    hero = re.search(r'<header class="home-hero">(.*?)</header>', _home(), re.S).group(1)
    m = re.search(r'<div class="myz" id="myz" hidden>.*?</div>\s*<script>(.*?)</script>', hero, re.S)
    assert m, "히어로에 '내 지역' 줄과 바로 뒤의 인라인 스크립트가 없다"
    assert "localStorage.getItem('%s')" % key.group(1) in m.group(1), m.group(1)
    assert hero.index('<p class="hero-sub">') < m.start() < hero.index('<a class="hero-wk"')
    assert "onclick=\"myZoneSet('')\"" in hero and 'track(\'home_cta\',{to:\'my_zone\'})' in hero


# ── B9 출처·구간·운영 주체 ─────────────────────────────────────────────────────────────────────────

def test_supply_span_is_the_model_window_from_L_and_H():
    """'앞으로 3년(2026년 3분기~2029년 2분기)'의 구간은 ADV.sido.L·H 에서 계산한다 — 판정 모델(sido_zones.calc)이 미래 공급을
    더하는 창 range(L+1, L+H+1)의 첫·끝 분기이고, 햇수도 H/4 다. 연도를 넘는 경우·H 가 13인 부분 수집 회차·옛 캐시(L 없음)를 본다.
    실데이터 판정(data.js)의 L·H 로도 같은 답이다(값은 함수에서 유도 — 데이터가 앞으로 가도 초록).

    변이(각각 실제로 확인): supplySpan 이 qShift(S.L,0) 에서 시작하면, 끝을 qShift(S.L,S.H-1) 로 잡으면, 햇수를 '3' 으로 적으면
          (H=13 사례) 빨개진다. calc 의 미래 창을 range(L, L+H) 로 바꾸면 모델 대조 단정이 빨개진다.
    """
    src = inspect.getsource(SZ.calc)
    assert 'range(L + 1, L + H + 1)' in src, '판정 모델의 미래 창이 바뀌었다 — 홈 구간 계산(supplySpan)도 같이 고칠 것'
    adv, _ = M.load()
    live = (adv['sido']['L'], adv['sido']['H'])
    samples = [('2026Q2', 12), ('2026Q4', 12), ('2027Q1', 13), live]

    def want(L, H):
        y, q = re.match(r'(\d{4})Q([1-4])$', L).groups()
        i = SZ.qidx(int(y), int(q))
        return '앞으로 %g년(%s~%s)' % (H / 4.0, SZ.quarter_text(SZ.qkey(i + 1)), SZ.quarter_text(SZ.qkey(i + H)))
    js = 'OUT.s = %s.map(([L,H]) => supplySpan({L, H})); OUT.none = [supplySpan(null), supplySpan({H: 12}), supplySpan({L: "2026Q2"})];' \
        % json.dumps(samples)
    got = _run({'js': js})[0]['out']
    assert got['s'] == [want(L, H) for L, H in samples], got
    assert got['s'][0] == '앞으로 3년(2026년 3분기~2029년 2분기)'
    assert got['none'] == [None, None, None]


def test_source_and_operator_lines_sit_under_the_map_without_promising_dates():
    """공급 지도 구역(#sec-score) 안, 산출 방법 앞에 출처·구간 줄과 운영 주체 줄이 있다. 구간 자리의 정적 문구는 분기를 약속하지
    않고(스크립트가 못 돌면 그대로 보인다), 운영 주체 줄은 대표 메일 mailto 링크와 /about/ 링크를 단다(TRUST-6). 부팅이 구간을 채운다.
    이달의 통계 입구(B6)는 '시도별로 자세히 보기' 바로 아래다(to 값은 test_home_cta).

    변이(각각 실제로 확인): mailto 를 일반 텍스트로 되돌리면, 정적 구간 문구에 '2026년 3분기'를 적으면, boot 에서
          renderSupplySpan() 을 지우면, 이달의 통계 줄을 산출 방법 뒤로 옮기면 빨개진다.
    """
    h = _home()
    sec = re.search(r'<section class="home-sec vm-map" id="sec-score".*?</section>', h, re.S).group(0)
    how = sec.index('<details class="sc-how">')
    src = re.search(r'<p class="map-src"><span id="map-span">([^<]*)</span><span>([^<]*)</span></p>', sec)
    assert src and src.start() < how, '지도 아래 출처·구간 줄이 없다'
    assert not re.search(r'\d{4}|분기~', src.group(1)) and '국토교통부' in src.group(2), src.groups()
    who = re.search(r'<p class="map-who">(.*?)</p>', sec, re.S)
    assert who and who.start() < how
    assert '<a href="mailto:agongmap@gmail.com">agongmap@gmail.com</a>' in who.group(1)
    assert '<a href="/about/">' in who.group(1)
    more, sub = sec.index('<p class="tb-more">'), sec.index('<p class="tb-sub"><a href="/monthly/"')
    assert more < sub < how and sec[more:sub].count('<p') == 1
    boot = _js_func(h, 'boot')
    for f in ('renderMyZone();', 'renderSupplySpan();', 'initMyZonePick();', 'VISIT=countVisit();', 'watchSections();'):
        assert f in boot, f


# ── B10 측정 ────────────────────────────────────────────────────────────────────────────────────

def test_visit_counter_counts_days_and_sends_home_visit_once_a_day():
    """방문한 날 수를 KST 날짜로 센다 — 같은 날 다시 부팅하면 세지 않고, 다음 날이면 n+1·gap_days, 망가진 저장값은 첫 방문으로
    되돌린다. first_week 는 첫 방문 주의 월요일(코호트 열쇠). home_visit 은 그날 첫 부팅에만 간다. 저장 못 하는 기기는 세지 않는다
    (null — 매번 '첫 방문'으로 부풀지 않게).

    변이(각각 실제로 확인): visitNext 의 `day<=prev.l` 을 `day<prev.l` 로 바꾸면 같은 날 단정이, weekOf 의 +6 을 빼면(일요일
          시작) 주 단정이, countVisit 이 lsSet 실패를 무시하면 던지는 저장소 단정이, fresh 검사 없이 track 하면 이벤트 수 단정이
          빨개진다.
    픽스처: 2026-09-27(일)·09-28(월)·10-05(월) KST 합성 날짜.
    """
    day = '(Date.UTC(%s)/864e5)'
    js = ('''const d27=%s, d28=%s, o05=%s;
      let v=visitNext(null,d27); const a=[v]; v=visitNext(v,d27); a.push(v); v=visitNext(v,d28); a.push(v);
      v=visitNext(v,o05); a.push(v); a.push(visitNext(v,d28)); a.push(visitNext({n:'x'},d28)); a.push(visitNext({n:2,f:1.5,l:3},d28));
      OUT.seq=a.map(x=>[x.n,x.gap,x.fresh]); OUT.first=a[0].f===d27&&a[3].f===d27;
      OUT.weeks=[weekOf(d27),weekOf(d28),weekOf(o05)];
      const r1=countVisit(), r2=countVisit(); OUT.cv=[r1&&r1.n, r2&&r2.fresh];''' % (
        day % '2026,8,27', day % '2026,8,28', day % '2026,9,5'))
    ok, bad = _run({'js': js}, {'storage': 'throw', 'js': 'OUT.cv=countVisit();'})
    assert ok['out']['seq'] == [[1, 0, True], [1, 0, False], [2, 1, True], [3, 7, True], [3, 0, False],
                                [1, 0, True], [1, 0, True]], ok['out']['seq']
    assert ok['out']['first'] is True
    assert ok['out']['weeks'] == ['2026-09-21', '2026-09-28', '2026-10-05']
    assert ok['out']['cv'] == [1, False]
    hv = [t for t in ok['track'] if t[0] == 'home_visit']
    assert len(hv) == 1 and set(hv[0][1]) == {'visit_n', 'gap_days', 'first_week'} and hv[0][1]['visit_n'] == 1, hv
    assert json.loads(ok['store']['agongmap-visit'])['n'] == 1
    assert bad['out']['cv'] is None and bad['track'] == []


def test_section_view_is_sent_once_when_the_weekly_grid_scrolls_into_view():
    """주간 격자가 화면에 들어올 때 section_view{section:'week'} 을 한 번 보낸다 — 스크롤 위치 계산(IntersectionObserver 아님).
    숨은 뷰(높이 0)·화면 아래에 있을 때는 안 보내고, 들어온 뒤에는 더 보내지 않으며 스크롤 감시를 뗀다.

    변이(각각 실제로 확인): inView 의 `/2` 를 빼면(요소가 다 들어와야 인정) 반쯤 들어온 사례가, checkSections 의 `if(SEEN[name])
          return` 을 지우면 한 번 단정이, 감시 떼기를 지우면 removed 단정이 빨개진다.
    픽스처: 375×812 화면에서 격자(높이 560)가 top 1133(09-26 실측 위치) → 스크롤 뒤 top 500(반 이상 보임).
    """
    js = '''
      OUT.iv=[inView(0,0,800), inView(900,1400,800), inView(500,1060,812), inView(700,1260,812), inView(-2000,-100,800),
              inView(-100,3000,800)];
      watchSections(); __timers(); OUT.n0=__rec.track.length;
      __els['home-weekly-grid'].rect={top:1133,bottom:1693}; checkSections(); OUT.n1=__rec.track.length;
      __els['home-weekly-grid'].rect={top:500,bottom:1060}; checkSections(); checkSections(); OUT.n2=__rec.track.length;'''
    g = _run({'vh': 812, 'js': js})[0]
    assert g['out']['iv'] == [False, False, True, False, False, True], g['out']['iv']
    assert (g['out']['n0'], g['out']['n1'], g['out']['n2']) == (0, 0, 1)
    assert g['track'] == [['section_view', {'section': 'week'}]]
    assert set(g['listen']) >= {'scroll', 'resize'} and set(g['removed']) >= {'scroll', 'resize'}


def test_home_variant_is_one_constant_set_before_the_first_page_view():
    """home_variant 사용자 속성은 한 상수(HOME_VARIANT)에서 나오고, 부팅(showView 의 첫 page_view)보다 먼저 큐에 들어간다 — 스크립트
    맨 위 수준 문장이라 defer 스크립트가 실행되는 순간(DOMContentLoaded 의 boot 보다 앞) 돈다. gtag 가 없으면 조용히 넘어간다.

    변이(각각 실제로 확인): 'set' 문장을 boot() 안 applyHash() 뒤로 옮기면 맨 위 수준 단정이, 값을 문자열로 직접 적으면 상수 단정이
          빨개진다.
    """
    h = _home()
    const = re.findall(r"^const HOME_VARIANT='([a-z0-9_]+)';", h, re.M)
    assert len(const) == 1, const
    assert h.count("'%s'" % const[0]) == 1, 'home_variant 값이 상수 밖에도 적혀 있다'
    m = re.search(r"^try\{if\(typeof gtag==='function'\)gtag\('set','user_properties',\{home_variant:HOME_VARIANT\}\);\}catch\(e\)\{\}$",
                  h, re.M)
    assert m and m.start() < h.index('\nfunction boot(')
    g, quiet = _run({'js': ''}, {'noGtag': True, 'js': 'OUT.ok=1;'})
    assert g['gtag'] == [['set', 'user_properties', {'home_variant': const[0]}]]
    assert quiet['out'] == {'ok': 1}


# ── C10① 설치 안내 ───────────────────────────────────────────────────────────────────────────────

ANDROID = 'Mozilla/5.0 (Linux; Android 14; SM-S918N) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Mobile Safari/537.36'
IPHONE = 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Mobile/15E148 Safari/604.1'
IPAD_DESK = 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.6 Safari/605.1.15'
KAKAO = IPHONE + ' KAKAOTALK 10.8.5'
WIN = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0 Safari/537.36'


def test_install_plan_rules():
    """안드로이드는 설치 프롬프트를 받았고 두 번째 방문이거나 주간 구역을 봤을 때만, iOS 는 같은 조건에서 인앱 브라우저가 아닐 때만.
    이미 설치(standalone)·이미 한 번 띄움·저장소 불가·데스크톱은 띄우지 않는다.

    변이(각각 실제로 확인): installPlan 의 standalone 검사를 지우면, `o.visitN>=2` 를 `>=1` 로 바꾸면(첫 방문에 뜬다), 안드로이드의
          hasPrompt 검사를 지우면, iOS 의 inapp 검사를 지우면, installPlatform 의 iPad(Macintosh+터치) 분기를 지우면 빨개진다.
    """
    base = dict(standalone=False, storageOk=True, stored=False, platform='android', inapp=False, hasPrompt=True,
                visitN=2, weekSeen=False)
    rows = [({}, 'android'), ({'visitN': 1}, None), ({'visitN': 1, 'weekSeen': True}, 'android'),
            ({'hasPrompt': False}, None), ({'standalone': True}, None), ({'stored': True}, None),
            ({'storageOk': False}, None), ({'platform': None}, None),
            ({'platform': 'ios', 'hasPrompt': False}, 'ios'), ({'platform': 'ios', 'inapp': True}, None),
            ({'platform': 'ios', 'visitN': 1}, None)]
    uas = [[ANDROID, 0], [IPHONE, 5], [IPAD_DESK, 5], [IPAD_DESK, 0], [WIN, 0]]
    js = ('OUT.plan=%s.map(o=>installPlan(o)); OUT.pf=%s.map(([u,t])=>installPlatform(u,t)); OUT.inapp=[INAPP.test(%s),INAPP.test(%s)];'
          % (json.dumps([dict(base, **r) for r, _ in rows]), json.dumps(uas), json.dumps(KAKAO), json.dumps(IPHONE)))
    got = _run({'js': js})[0]['out']
    assert got['plan'] == [w for _, w in rows], got['plan']
    assert got['pf'] == ['android', 'ios', 'ios', None, None]
    assert got['inapp'] == [True, False]


def test_install_prompt_shows_once_and_closing_keeps_it_closed():
    """두 번째 방문 날의 iPhone Safari: 부팅 뒤 지연 시간이 지나야 '공유 → 홈 화면에 추가' 안내가 한 번 뜨고(pwa_prompt shown),
    닫으면 기기에 적혀 다음 부팅에서 다시 뜨지 않는다. 안드로이드는 beforeinstallprompt 를 받아(기본 미니바는 막고) 주간 구역을 본 뒤
    뜨고, '홈 화면에 추가'를 누르면 브라우저 프롬프트를 부르고 결과를 잰다. standalone 이나 저장소 불가 기기에서는 뜨지 않는다.

    변이(각각 실제로 확인): installMaybe 의 `!_instReady` 검사를 지우면 지연 단정이, lsSet(INSTALL_KEY,'shown') 을 지우면 두 번째
          부팅 단정이, beforeinstallprompt 처리에서 preventDefault 를 지우면 안드로이드 단정이 빨개진다.
    픽스처: 어제 처음 온 기기(visit n=1, 어제 날짜)가 오늘 다시 온 상태 — 저장값 {n:1,f:어제,l:어제}.
    """
    boot = '''VISIT=countVisit(); watchSections(); _instReady=false; installMaybe(); OUT.before=__rec.appended.length;
      _instReady=true; installMaybe(); OUT.after=__rec.appended.length; OUT.html=__rec.appended[0]||'';'''
    close = boot + " const b=__els.inst; b&&b.h['.inst-x'](); OUT.stored=__data[INSTALL_KEY]; OUT.gone=!__els.inst;"
    yday = {'agongmap-visit': json.dumps({'n': 1, 'f': 1, 'l': 1})}
    android = '''VISIT=countVisit(); watchSections(); _instReady=true;
      let prevented=false, prompted=false;
      const ev={preventDefault(){prevented=true;}, prompt(){prompted=true;}, userChoice:Promise.resolve({outcome:'accepted'})};
      for(const f of (__rec.listeners.beforeinstallprompt||[])) f(ev);
      OUT.early=__rec.appended.length;                                   // 첫 방문·주간 구역 아직 — 안 뜬다
      __els['home-weekly-grid'].rect={top:100,bottom:600}; checkSections();
      OUT.shown=__rec.appended.length; OUT.prevented=prevented;
      __els.inst.h['.inst-go'](); OUT.prompted=prompted;'''
    ios2, ios3, andr, stand, nostore = _run(
        {'ua': IPHONE, 'touch': 5, 'store': dict(yday), 'js': close},
        {'ua': IPHONE, 'touch': 5, 'store': dict(yday, **{'agongmap-install': 'closed'}), 'js': boot},
        {'ua': ANDROID, 'js': android},
        {'ua': IPHONE, 'touch': 5, 'store': dict(yday), 'htmlClass': ['pwa'], 'js': boot},
        {'ua': IPHONE, 'touch': 5, 'storage': 'throw', 'js': boot})
    o = ios2['out']
    assert (o['before'], o['after']) == (0, 1), o
    assert '매주 시세를 홈 화면에서 바로 보기' in o['html'] and '공유' in o['html'] and '홈 화면에 추가' in o['html']
    assert o['stored'] == 'closed' and o['gone'] is True
    steps = [t[1]['step'] for t in ios2['track'] if t[0] == 'pwa_prompt']
    assert steps == ['shown', 'close'] and all(t[1]['platform'] == 'ios' for t in ios2['track'] if t[0] == 'pwa_prompt')
    assert ios3['out']['after'] == 0, '닫은 기기에서 다시 떴다'
    a = andr['out']
    assert (a['early'], a['shown'], a['prevented'], a['prompted']) == (0, 1, True, True), a
    assert ['pwa_prompt', {'step': 'shown', 'platform': 'android'}] in andr['track']
    assert andr['store'].get('agongmap-install') == 'shown'
    assert stand['out']['after'] == 0 and nostore['out']['after'] == 0


def test_install_prompt_leaves_the_browser_default_alone_where_it_will_not_show():
    """띄우지 않을 기기에서는 beforeinstallprompt 를 막지 않는다 — 막으면 브라우저 기본 설치 안내(미니바·주소창 설치 아이콘)까지
    사라지는데 우리 안내도 뜨지 않아 설치 입구가 아예 없어진다. 이미 한 번 띄운 안드로이드, 앱으로 연(standalone) 안드로이드,
    데스크톱 크롬(installPlatform 이 null), 저장소를 못 쓰는 안드로이드가 그 경우다.

    변이(각각 실제로 확인): 처리기의 `s.platform!=='android'` 검사를 지우면 데스크톱 단정이, `s.stored` 검사를 지우면 띄운 기기 단정이,
          `s.standalone` 검사를 지우면 standalone 단정이 빨개진다(셋 다 preventDefault 가 불린다).
    픽스처: 주간 구역을 본 두 번째 방문 — 조건만으로는 띄울 날이어서, 막지 않는 이유가 기기 상태뿐이다.
    """
    js = '''VISIT=countVisit(); _instReady=true; SEEN.week=true;
      let prevented=false; const ev={preventDefault(){prevented=true;}, prompt(){}, userChoice:Promise.resolve({})};
      for(const f of (__rec.listeners.beforeinstallprompt||[])) f(ev);
      OUT.prevented=prevented; OUT.shown=__rec.appended.length;'''
    yday = {'agongmap-visit': json.dumps({'n': 1, 'f': 1, 'l': 1})}
    stored, stand, desk, nostore, fresh = _run(
        {'ua': ANDROID, 'store': dict(yday, **{'agongmap-install': 'shown'}), 'js': js},
        {'ua': ANDROID, 'store': dict(yday), 'htmlClass': ['pwa'], 'js': js},
        {'ua': WIN, 'store': dict(yday), 'js': js},
        {'ua': ANDROID, 'storage': 'throw', 'js': js},
        {'ua': ANDROID, 'store': dict(yday), 'js': js})
    for name, r in (('띄운 기기', stored), ('standalone', stand), ('데스크톱', desk), ('저장소 불가', nostore)):
        assert r['out'] == {'prevented': False, 'shown': 0}, (name, r['out'])
    assert fresh['out'] == {'prevented': True, 'shown': 1}, '대조군(띄울 안드로이드)이 막지 않았다 — 하네스가 처리기를 못 부른다'


def test_new_event_names_are_snake_case_and_listed():
    """이번에 넣은 이벤트·사용자 속성 이름 — GA 주석·맞춤 측정기준 등록에 그대로 옮기는 목록이다(보고서 notes 와 같다).
    이름이 바뀌면 여기서 빨개져 목록을 같이 고치게 한다.

    변이: pwa_installed 를 'appInstalled' 로 바꾸면 빨개진다(확인).
    """
    blk = _block('home-small')
    names = sorted(set(re.findall(r"track\('([^']+)'", blk)))
    assert names == ['home_visit', 'myzone', 'pwa_installed', 'pwa_prompt', 'section_view'], names
    assert all(re.match(r'^[a-z][a-z0-9_]*$', n) for n in names)
