# -*- coding: utf-8 -*-
"""감시 최악 소요가 잡 시간 상한(watchdog.yml freshness 잡 timeout-minutes) 안에 드는가 — 손셈 주석 대신 실제로 잰다.

check_freshness.py 의 예산 주석('최악 N분')은 세 번 낡았다(2026-08-15 '~15분'이 실제 30분 초과, 09-30 13.7분 뒤로 쪽 재시도
3회·지역 목록 재시도 10·30초가 붙었는데 주석은 그대로 — 전수리뷰 F-9). 넘기면 잡이 판정 없이 죽고 재확인 잡이 같은 30분을
또 쓴다. 그래서 main() 을 통째로 '원천 전부 타임아웃' 상태로 돌려, 잠(time.sleep)과 응답 대기를 같은 비율로 줄인 실제
시계로 재고 원래 시간으로 되돌려 견준다.
"""
import io
import json
import os
import re
import socket
import sys
import time
import urllib.error

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import check_freshness as C  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
SCALE = 0.005         # 1초 → 5ms
MEASURE_TRIES = 3     # 바쁜 러너에서 부푼 측정을 다시 잴 횟수(아래 시험)
JOB_SETUP_S = 300     # 체크아웃·파이썬 설치·프리플라이트·상태 복원에 남겨 둘 몫(실측 1~2분의 넉넉한 위)
_REAL_SLEEP = time.sleep   # 아래에서 time.sleep 을 줄인 것으로 바꾸므로 진짜를 먼저 잡아 둔다


def _job_limit_s():
    y = io.open(os.path.join(ROOT, '.github', 'workflows', 'watchdog.yml'), encoding='utf-8').read()
    blk = y[y.index('\n  freshness:\n'):y.index('\n  recheck:\n')]
    return int(re.search(r'timeout-minutes:\s*(\d+)', blk).group(1)) * 60


class _Resp:
    def __init__(self, b):
        self.b = b

    def read(self):
        return self.b


def _run(monkeypatch, scale, heads):
    real_sleep = _REAL_SLEEP
    monkeypatch.setattr(C.time, 'sleep', lambda s: real_sleep(s * scale))

    def urlopen(req, timeout=None):
        url = req.full_url if hasattr(req, 'full_url') else str(req)
        if url.startswith(C.SITE):
            path = url[len(C.SITE) + 1:].split('?')[0]
            if path == '' or path.endswith('/'):
                path += 'index.html'
            real_sleep(timeout * 0.95 * scale)      # 우리 사이트는 타임아웃 직전에 겨우 온다
            try:
                with open(os.path.join(ROOT, path), 'rb') as f:
                    return _Resp(f.read())
            except OSError:
                raise urllib.error.HTTPError(url, 404, 'not found', {}, None)
        if heads and 'reb.or.kr' in url and 'pSize=1&' in url + '&':
            return _Resp(json.dumps({'SttsApiTblData': [{'head': [{'list_total_count': 2500}]}]}).encode())
        real_sleep(timeout * scale)                # 원천은 끝까지 기다렸다가 끊긴다
        raise socket.timeout('timed out')
    monkeypatch.setattr(C.urllib.request, 'urlopen', urlopen)
    for k in ('KOSIS_API_KEY', 'RONE_API_KEY', 'ECOS_API_KEY'):
        monkeypatch.setenv(k, 'test')
    monkeypatch.delenv(C.REGION_STATE_ENV, raising=False)
    monkeypatch.setattr(C, 'FETCH_TIMEOUT', 25)    # retry_failed 가 20 으로 바꾼다
    for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
        lst.clear()
    C._COMPLETE_CACHE.clear()
    t0 = time.perf_counter()
    try:
        C.main()
    except SystemExit:
        pass
    took = time.perf_counter() - t0
    for lst in (C.SKIPPED, C.RETRYQ, C.FETCH_FAIL):
        lst.clear()
    return took


def test_worst_case_watchdog_fits_the_job_timeout(monkeypatch, capsys):
    """광역 장애(원천 전부 타임아웃·우리 사이트는 타임아웃 직전 응답)와 R-ONE 머리만 받히고 본문 쪽이 끊기는 경우, 둘 다
    감시 1차 잡 전체(대조·지역 목록 재시도·75초 대기·재시도)가 잡 시간 상한에서 준비 몫을 뺀 시간 안에 끝난다.
    2026-10-19 잰 값은 둘 다 약 1,040초(17.4분) — 상한 1,800초에서 준비 몫 300초를 빼면 455초가 남는다.

    잠(time.sleep)·응답 대기를 SCALE 배로 줄여 실제로 돌리고, 같은 코드를 잠 0 배로 돌린 계산 시간을 빼서 되돌린다.
    변이(실제로 확인): RONE_TRIES 를 3 → 6 으로 올리면(쪽마다 여섯 번) 빨강. REGION_RETRY_WAITS 에 300초를 하나 더 붙여도 빨강.
    측정은 실제 시계라 러너가 바쁘면 위로만 부푼다 — 넘으면 MEASURE_TRIES 번까지 다시 재 가장 작은 값으로 견준다(위 변이는
    세 번 모두 넘어 그대로 빨강).
    픽스처: 저장소의 실제 data.js·data-rest.json·생성 페이지를 우리 사이트로 내주고, 원천(R-ONE·KOSIS·ECOS)은 모두 FETCH_TIMEOUT
    을 꽉 채운 뒤 끊긴다 — 2026-08-12 광역 타임아웃(14/18 실패)과 10-01·03·04 R-ONE 끊김을 한데 모은 최악.
    """
    limit = _job_limit_s() - JOB_SETUP_S
    for heads in (False, True):
        # 실제 시계라 러너가 바쁘면 잰 값이 **위로만** 부푼다(잠이 늦게 깨는 쪽). 상한을 넘으면 MEASURE_TRIES 번까지 다시 재고
        # 가장 작은 값으로 견준다 — 코드가 정말 느려진 변이는 몇 번을 재도 넘는다(게이트가 바쁜 러너 탓에 데이터 커밋을 막지 않게).
        seen = []
        for _ in range(MEASURE_TRIES):
            base = _run(monkeypatch, 0.0, heads)            # 잠 없이 도는 계산 시간
            took = _run(monkeypatch, SCALE, heads)
            seen.append((took - base) / SCALE)
            out = capsys.readouterr().out
            assert 'VERDICT=retry' in out, out[-600:]      # 실제로 조회 실패 경로를 탔다
            if seen[-1] < limit:
                break
        virtual = min(seen)
        assert virtual > 600, seen                       # 측정이 깨져 0 근처로 통과하지 않게
        assert virtual < limit, ('감시 최악 소요 %s초 ≥ 잡 상한 %d초 − 준비 %d초 — 판정 없이 죽는다(heads=%s)'
                                 % ('/'.join('%.0f' % v for v in seen), limit + JOB_SETUP_S, JOB_SETUP_S, heads))
