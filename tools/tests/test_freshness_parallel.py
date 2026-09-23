# -*- coding: utf-8 -*-
"""감시 원천 대조의 병렬 조회(백로그 25) — 빨라지되 판정은 직렬과 한 글자도 달라지면 안 된다.

원천 대조는 조회 19건(HTTP 25회)을 직렬로 돌아 광역 장애 밤의 최악이 30분 예산을 위협했다.
지금은 main()이 source_jobs()를 prefetch()로 한꺼번에 병렬로 받고, 판정·출력은 예전 순서대로
한 줄씩 한다. 여기서는 main()을 **통째로** 두 번 돌린다 — SOURCE_WORKERS=1(직렬)과 기본값(병렬).

픽스처가 재현하는 실제 상태:
  - 라이브 사이트 응답은 저장소의 실제 data.js·data-rest.json·data-size.json·data-core.js다
    (urlopen을 가짜로 바꿔 파일을 돌려준다. 네트워크에 나가면 시험이 실패한다).
  - 원천 함수(rone_latest·kosis_latest·rone_latest_complete·ecos_latest·rone_region_names)는
    잠깐 잠든 뒤 라이브와 같은 시점을 돌려준다 — 정상 날의 원천이다. 잠드는 시간을 호출마다
    다르게 해서 병렬일 때 끝나는 순서가 넣은 순서와 달라지게 한다.
  - 시나리오 A: 연간 '보급률'만 원천이 1년 앞서 있고(진짜 뒤처짐, grace 없음), 기본통계 '착공'은
    1차 조회에서 타임아웃이 났다가 재시도에 살아난다(2026-08-12 광역 타임아웃의 축소판).
    → 조회는 결국 다 성공했으니 결정론적 실패(rc=2, 재확인 없이 바로 경보)여야 한다.
  - 시나리오 B: 핵심 계열 '주간'의 원천이 재시도까지 계속 죽는다(R-ONE 장애의 날).
    → SKIPPED=['주간'], 새 IP로 다시 볼 값어치가 있는 실패(rc=1)여야 한다.
"""
import io
import os
import sys
import threading
import time

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import check_freshness as C  # noqa: E402

U = C.U
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SITE_FILES = ('data.js', 'data-rest.json', 'data-size.json', 'data-core.js')

# 호출 순서대로 돌려 가며 쓰는 잠 길이(초). 넣은 순서와 끝나는 순서를 어긋나게 한다.
DELAYS = (0.2, 0.1, 0.05)


class _Resp(io.BytesIO):
    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _site(unexpected):
    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        for f in SITE_FILES:
            if url == C.SITE + '/' + f:
                with open(os.path.join(ROOT, f), 'rb') as fh:
                    return _Resp(fh.read())
        unexpected.append(url)
        raise AssertionError('시험 중 네트워크 호출: %s' % url)
    return urlopen


def _live():
    """라이브 판본(저장소 파일)의 우리 시점 — 가짜 원천이 '같은 시점'을 돌려주는 기준."""
    import json
    import re
    t = open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'/\*ADV_DATA_START\*/const ADV=(\{.*?\});', t, re.S).group(1))
    stats = {}
    for f in ('data-rest.json', 'data-size.json'):
        stats.update(json.load(open(os.path.join(ROOT, f), encoding='utf-8'))['STATS'])
    last = {k: C.digits((v.get('dates') or [''])[-1]) for k, v in stats.items()}
    return adv, last


def _kosis_tables():
    """KOSIS 표 → 그 표를 보는 계열들. 주택멸실·아파트멸실처럼 **한 표를 두 계열이 본다**
    (실제 설정) — 그래서 원천 호출은 계열 수가 아니라 표 단위로 센다."""
    out = {}
    for n, c in list(U.BASIC_CONF.items()) + list(U.ANNUAL_CONF.items()):
        out.setdefault(c['tbl'], []).append(n)
    out.setdefault(U.SIZE_TBLS[0][1], []).append('규모별')
    return out


def _expected_calls():
    """정상이면 조회마다 한 번 — 한 표를 두 계열이 보면 그 표는 두 번."""
    exp = {'주간': 1, '월간': 1, '금리': 1, ('지역', 'WK'): 1, ('지역', 'MM'): 1}
    for tbl, names in _kosis_tables().items():
        exp[tbl] = len(names)
    for n in U.SUPPLY_CONF:
        exp[n] = 1
    return exp


class _Sources:
    """정상 날의 원천. fault[계열]가 'flaky'면 첫 호출만, 'dead'면 매번 타임아웃이 난다.
    KOSIS 계열의 fault·bump·호출 수는 그 계열의 표 이름으로 센다."""

    def __init__(self, fault=None, bump=None):
        self.adv, self.last = _live()
        self.tables = _kosis_tables()
        byname = {n: t for t, ns in self.tables.items() for n in ns}
        self.fault = {byname.get(k, k): v for k, v in (fault or {}).items()}
        self.bump = {byname.get(k, k): v for k, v in (bump or {}).items()}
        self.calls = {}
        self.slept = 0.0
        self._lock = threading.Lock()
        self._n = 0
        self.supply = {c['tbl']: n for n, c in U.SUPPLY_CONF.items()}

    def _hit(self, key):
        with self._lock:
            self.calls[key] = self.calls.get(key, 0) + 1
            nth = self.calls[key]
            d = DELAYS[self._n % len(DELAYS)]
            self._n += 1
            self.slept += d
        time.sleep(d)
        f = self.fault.get(key)
        if f == 'dead' or (f == 'flaky' and nth == 1):
            raise OSError('timed out')

    def _val(self, key, v):
        if key in self.bump:
            return str(int(v) + self.bump[key])
        return v

    def rone_latest(self, tbl, cycle, since=None):
        key = '주간' if cycle == 'WK' else '월간'
        self._hit(key)
        if cycle == 'WK':
            return self.adv['weekly']['rows'][-1]['p']
        return C.digits(self.adv['monthly']['rows'][-1]['p'])

    def kosis_latest(self, org, tbl, objn, prd, extra=None):
        self._hit(tbl)
        return self._val(tbl, max(self.last[n] for n in self.tables[tbl]))

    def rone_latest_complete(self, tbl, since=None, want_total=False):
        key = self.supply[tbl]
        self._hit(key)
        return self._val(key, self.last[key])

    def ecos_latest(self):
        self._hit('금리')
        return self.last['금리']

    def rone_region_names(self, tbl, cycle):
        self._hit(('지역', cycle))
        return {{'지방': '지방권'}.get(z, z) for z in U.WEEKLY_REGIONS}


def _run(monkeypatch, capsys, workers, **src_kw):
    src = _Sources(**src_kw)
    unexpected = []
    for k in ('KOSIS_API_KEY', 'RONE_API_KEY', 'ECOS_API_KEY'):
        monkeypatch.setenv(k, 'test')
    monkeypatch.setattr(C.urllib.request, 'urlopen', _site(unexpected))
    for fn in ('rone_latest', 'kosis_latest', 'rone_latest_complete', 'ecos_latest',
               'rone_region_names'):
        monkeypatch.setattr(C, fn, getattr(src, fn))
    wk = src.adv['weekly']['rows'][-1]['p']
    monkeypatch.setattr(C, 'live_card_basis', lambda: wk)          # 카드는 라이브 주간과 같다
    monkeypatch.setattr(C, 'check_derived_pages', lambda adv, stats: [])  # 따로 시험한다
    monkeypatch.setattr(C, 'RETRY_WAIT', 0)
    monkeypatch.setattr(C, 'FETCH_TIMEOUT', 25)                   # retry_failed가 20으로 바꾼다
    monkeypatch.setattr(C, 'SOURCE_WORKERS', workers)
    for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
        lst.clear()
    C._COMPLETE_CACHE.clear()
    capsys.readouterr()
    t0 = time.perf_counter()
    rc = 0
    try:
        C.main()
    except SystemExit as e:
        rc = e.code
    wall = time.perf_counter() - t0
    out = capsys.readouterr().out
    skipped = list(C.SKIPPED)
    for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
        lst.clear()
    assert not unexpected, unexpected
    return dict(rc=rc, out=out, wall=wall, skipped=skipped, src=src)


def test_parallel_source_phase_is_faster_and_judges_like_serial(monkeypatch, capsys):
    """시나리오 A. 병렬이 직렬보다 실제로 빠르고(잠든 시간 합의 40% 이상을 덜어냄), 출력 전문·
    종료 코드·SKIPPED가 직렬과 똑같아야 한다.

    무엇을 깨뜨리면 빨개지나(실제로 확인):
      - prefetch()의 ThreadPoolExecutor를 직렬 `[run(g) for g in getters]`로 바꾸면 → 시간 단정.
      - prefetch()가 결과를 끝난 순서(as_completed)로 모으면 → 계열과 값이 엇갈려 출력이 달라진다.
      - check()가 RETRYQ에 `getter`(받아 둔 _Fetched)를 그대로 넣으면 → '착공'이 재시도에서도
        같은 예외를 되풀이해 SKIPPED에 남고 rc가 1이 된다(재시도 층이 꺼짐).
      - main()이 받아 둔 pre[...] 대신 원천 함수를 다시 부르면 → 호출 횟수 단정(계열당 1회).
    """
    kw = dict(fault={'착공': 'flaky'}, bump={'보급률': 1})
    ser = _run(monkeypatch, capsys, 1, **kw)
    par = _run(monkeypatch, capsys, 4, **kw)

    # 판정은 직렬과 한 글자도 다르지 않다.
    assert par['out'] == ser['out']
    assert (par['rc'], par['skipped']) == (ser['rc'], ser['skipped'])
    # 조회는 결국 다 성공했고 진짜 뒤처짐이 있다 → 결정론적 실패.
    assert par['rc'] == C.EXIT_DETERMINISTIC, par['out'][-800:]
    want = int(par['src'].last['보급률']) + 1
    assert '보급률(라이브' in par['out'] and '< 원천 %d' % want in par['out']
    assert '착공' not in par['skipped'], '재시도에 살아난 계열이 건너뜀으로 남았다'
    # 조회마다 한 번씩만 부른다(재시도한 '착공'만 한 번 더).
    exp = _expected_calls()
    exp[U.BASIC_CONF['착공']['tbl']] += 1
    for s in (ser, par):
        assert s['src'].calls == exp
    # 실제로 겹쳐 돌았다 — 직렬은 잠든 시간을 다 쓰고, 병렬은 그중 40% 이상을 덜어낸다.
    assert ser['wall'] >= ser['src'].slept
    # 실측(2026-09-23): 잠 2.4초, 직렬 2.52초, 병렬 0.88초. 병렬 4면 이상적으로 75%를 덜어낸다.
    assert par['wall'] + 0.4 * par['src'].slept < ser['wall'], (par['wall'], ser['wall'])


def test_parallel_keeps_the_retryable_classification(monkeypatch, capsys):
    """시나리오 B. 핵심 계열이 재시도까지 죽으면 병렬이어도 SKIPPED=['주간']이고 rc=1(새 IP로 재확인)
    이어야 한다 — 직렬과 출력·종료 코드가 같아야 한다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): prefetch()의 run()이 예외를 None 값으로 바꿔 삼키면
    ('조회 실패'가 '값 없음'으로 둔갑) → '주간'이 SKIPPED에 들어가지 않아 rc가 달라진다.
    """
    kw = dict(fault={'주간': 'dead'})
    ser = _run(monkeypatch, capsys, 1, **kw)
    par = _run(monkeypatch, capsys, 4, **kw)
    assert par['out'] == ser['out']
    assert par['rc'] == ser['rc'] == C.EXIT_RETRYABLE, par['out'][-800:]
    assert par['skipped'] == ser['skipped'] == ['주간']
    assert par['src'].calls['주간'] == 2, '1차와 재시도에서 한 번씩 불러야 한다'


def test_prefetch_preserves_order_and_exceptions():
    """prefetch()만 따로 — 끝나는 순서를 뒤집어도 결과는 넣은 순서이고, 예외는 부를 때 그대로
    다시 난다. `fresh`는 원래 getter여야 재시도가 새로 부를 수 있다.

    무엇을 깨뜨리면 빨개지나(실제로 확인): run()을 `except Exception: return _Fetched(g, True, None)`
    으로 바꾸면 pytest.raises가 빨개진다.
    """
    def slow(v, d):
        return lambda: (time.sleep(d), v)[1]

    def boom():
        raise OSError('timed out')
    gs = [slow('a', 0.15), slow('b', 0.0), boom, slow('d', 0.05)]
    got = C.prefetch(gs, workers=4)
    assert [g.fresh for g in got] == gs
    assert got[0]() == 'a' and got[1]() == 'b' and got[3]() == 'd'
    with pytest.raises(OSError):
        got[2]()
    assert C.prefetch([]) == []
