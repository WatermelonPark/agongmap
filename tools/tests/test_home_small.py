# -*- coding: utf-8 -*-
"""홈 작은 장치 — 내 지역(C5 — 2026-10-05 에 뺐다, 옛 저장값 지우기만 남는다)·이달의 통계 입구(B6)·출처·구간(B9 — 운영 주체 줄은 2026-09-28 에 뺐다, 제보 메일은 푸터)·측정(B10)·설치 안내(C10①). 2026-09-27 홈 마케팅 검수 3차.

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
  ['map-span', 'home-weekly-grid', 'wk-h2'].forEach(el);
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


# ── C5 내 지역(2026-10-05 대표 요청으로 뺐다) ─────────────────────────────────────────────────────────────

def test_old_my_zone_value_is_dropped_and_the_feature_is_gone():
    """'내 지역'(C5)은 첫 화면 위쪽을 너무 차지해 2026-10-05 대표 요청으로 뺐다. 고정해 둔 기기에 남은 옛 저장값
    ('agongmap-myzone')은 부팅이 지우고(dropOldMyZone — 쓰지 않는 값을 브라우저에 남기지 않는다), 다른 저장값(방문 기록)은
    건드리지 않는다. 사생활 모드처럼 저장소가 던져도 부팅이 멈추지 않는다. 홈에는 고르기·고정 해제·myzone 이벤트가 없다.

    변이(각각 실제로 확인): dropOldMyZone 을 빈 함수로 두면 첫 단정이, lsGet·lsSet 대신 localStorage 를 맨손으로 부르면 던지는
          저장소 사례가(node 예외), 키를 'agong_myzone' 으로 바꾸면 첫 단정이, index.html 에 고르기 줄(myz-pick)을 되살리면
          마지막 단정이 빨개진다.
    픽스처: 고정해 둔 기기(서울 + 방문 기록), 고정한 적 없는 기기, 저장소가 던지는 기기.
    """
    js = 'dropOldMyZone(); OUT.ok = 1;'
    pinned, fresh, thrown = _run({'store': {'agongmap-myzone': '서울', 'agongmap-visit': '{"n":3}'}, 'js': js},
                                 {'store': {}, 'js': js}, {'storage': 'throw', 'js': js})
    assert pinned['store'] == {'agongmap-visit': '{"n":3}'}, pinned['store']
    assert fresh['store'] == {} and thrown['out'] == {'ok': 1}
    h = _home()
    assert not re.search(r'myz-pick|myZoneSet|renderMyZone|track\(\'myzone\'', h), '내 지역 고르기·고정이 남아 있다'


def test_grade_names_have_one_source():
    """홈의 등급 이름(TB_GRADE)은 sido_zones.GRADE_LABS 와 같다(공급 카드·지도 라벨이 쓴다).

    변이(실제로 확인): TB_GRADE 의 g2 를 '다소 부족'으로 바꾸면 빨개진다.
    """
    assert json.loads(_tb_grade().replace("'", '"').replace('g4:', '"g4":').replace('g3:', '"g3":')
                      .replace('g2:', '"g2":').replace('g1:', '"g1":').replace('g0:', '"g0":')) == SZ.GRADE_LABS


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


def test_source_line_sits_under_the_map_and_the_report_mail_is_in_the_footer():
    """공급 지도 구역(#sec-score) 안, 산출 방법 앞에 출처·구간 줄이 있다. 구간 자리의 정적 문구는 분기를 약속하지 않고(스크립트가
    못 돌면 그대로 보인다) 부팅이 구간을 채운다. 이달의 통계 입구(B6)는 '시도별로 자세히 보기' 바로 아래다(to 값은 test_home_cta).
    지도 아래 운영 주체 줄(B9·TRUST-6)과 '산출 방법' 옆 출처 줄은 뺐다(2026-09-28 대표 결정 — 작은 글씨 정리). 제보 경로는 홈
    푸터 '만든이' 메일이 mailto 링크로 남기고(같은 푸터 세 벌 모두), 출처 기관은 산출 방법을 펼치면 항목마다 있다.

    변이(각각 실제로 확인): 푸터 메일을 일반 텍스트로 되돌리면, 운영 주체 줄(map-who)이나 산출 방법 옆 출처(.src)를 되살리면,
          정적 구간 문구에 '2026년 3분기'를 적으면, boot 에서 renderSupplySpan() 을 지우면, 이달의 통계 줄을 산출 방법 뒤로
          옮기면 빨개진다.
    """
    h = _home()
    sec = re.search(r'<section class="home-sec vm-map" id="sec-score".*?</section>', h, re.S).group(0)
    how = sec.index('<details class="sc-how">')
    # 셋째 칸(#lt-key)은 신호등 범례 한 줄 — 부팅 때 채운다(2026-10-06, 카드 아래에서 옮겼다)
    src = re.search(r'<p class="map-src"><span id="map-span">([^<]*)</span><span>([^<]*)</span><span id="lt-key"></span></p>', sec)
    assert src and src.start() < how, '지도 아래 출처·구간 줄이 없다'
    assert not re.search(r'\d{4}|분기~', src.group(1)) and '국토교통부' in src.group(2), src.groups()
    assert 'map-who' not in h and '개인이 운영합니다' not in sec, '지도 아래 운영 주체 줄이 되살아났다'
    summ = re.search(r'<details class="sc-how"><summary>(.*?)</summary>(.*?)</details>', sec, re.S)
    assert summ and summ.group(1) == '<span class="t">산출 방법</span>', summ and summ.group(1)
    for org in ('국토교통부', '한국부동산원'):   # 출처 기관은 펼친 본문에 남는다
        assert org in summ.group(2), org
    metas = re.findall(r'<div class="ft-meta">(.*?)</div>', h)
    assert len(metas) == 3 and all('<a href="mailto:agongmap@gmail.com">' in m for m in metas), metas
    more, sub = sec.index('<p class="tb-more">'), sec.index('<p class="tb-sub"><a href="/monthly/"')
    assert more < sub < how and sec[more:sub].count('<p') == 1
    boot = _js_func(h, 'boot')
    for f in ('renderSupplySpan();', 'dropOldMyZone();', 'VISIT=countVisit();', 'watchSections();'):
        assert f in boot, f


def test_footer_mail_links_take_the_footer_color():
    """손 페이지 푸터의 '만든이' 메일(mailto)은 모두 링크이고 푸터 글자색을 따른다 — 브라우저 기본 파랑이 아니다.

    재현하는 실제 상태(2026-09-28 검토): /cycle/ 푸터 메일을 mailto 로 바꾸자 rgb(0,0,238) 파랑으로 보였다. 그 페이지는 공용
    시트(app.css)만 읽고 푸터 링크 색이 따로 없었다(옆 링크는 인라인 color:inherit). 퀴즈 랜딩·개인정보는 자기 <style> 의
    `footer a{color:…}` 가 칠한다. 공용 시트는 `footer a[href^="mailto:"]{color:inherit}` 로 칠한다(푸터 바로 옆 줄을 배치가
    고치는 /cycle/ 를 손대지 않으려고 CSS 쪽에서 풀었다).
    변이(각각 확인): app.css 의 mailto 규칙을 지우면 /cycle/ 가, 퀴즈 랜딩 하나의 메일을 일반 텍스트로 되돌리면 그 페이지가
          빨개진다. 픽스처: 저장소의 손 페이지(푸터에 메일이 있는 곳 전부를 찾는다 — 목록을 적지 않는다).
    """
    import glob
    import io
    root = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
    app = re.sub(r'/\*.*?\*/', '', io.open(os.path.join(root, 'app.css'), encoding='utf-8').read(), flags=re.S)
    shared = re.search(r'(?:^|[}\s])footer a\[href\^="mailto:"\]\{[^}]*color:inherit', app)
    pages = []
    for path in glob.glob(os.path.join(root, '**', 'index.html'), recursive=True):
        rel = os.path.relpath(path, root).replace(os.sep, '/')
        if rel.startswith(('tools/', 'docs/')) or HS.is_home(rel):
            continue
        s = io.open(path, encoding='utf-8').read()
        foot = re.search(r'<footer[^>]*>(.*?)</footer>', s, re.S)   # 손 페이지 공용 푸터는 class="sfoot"(백로그 36-4)
        if not foot or 'agongmap@gmail.com' not in foot.group(1):
            continue
        pages.append(rel)
        assert re.search(r'<a href="mailto:agongmap@gmail\.com">[^<]*agongmap@gmail\.com</a>', foot.group(1)), '%s 푸터 메일이 링크가 아니다' % rel
        own = re.search(r'(?:^|[}\s])footer a\{[^}]*color:', ''.join(re.findall(r'<style>(.*?)</style>', s, re.S)))
        uses_app = 'href="/app.css"' in s
        assert own or (uses_app and shared), '%s 푸터 메일 링크가 브라우저 기본색이다(푸터 링크 색 규칙 없음)' % rel
    assert 'cycle/index.html' in pages and len(pages) >= 5, pages


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
    assert names == ['home_visit', 'pwa_installed', 'pwa_prompt', 'section_view'], names
    assert all(re.match(r'^[a-z][a-z0-9_]*$', n) for n in names)
