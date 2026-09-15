# -*- coding: utf-8 -*-
"""시도 리포트 하단의 '다음 행선지'(점검후속 개발 ⑤)와 FAQ 면책(⑥)을 고정한다.

2026-09-15 고객 점검: 리포트 끝이 방법론 → 다른 지역 → 공유 순이라 '이 지역 이번 주 시세는?'으로
가는 길이 없었다. 그 지역의 최신 주간 매매·전세 변동률과 전세가율을 한 줄씩 붙이고 /weekly/·
/jeonse-ratio/ 로 잇는다. FAQ 에만 투자 면책이 없었다.

값은 생성기를 믿지 않고 data.js 에서 따로 계산해 대조한다. 반올림은 사이트 규칙(절대값 half-up,
소수 둘째)을 Decimal 로 다시 구현한다 — 생성기가 파이썬 round()(은행가 반올림)로 바뀌면 끝자리가
홈·/weekly/ 와 갈리는데, 같은 함수를 import 해 비교하면 그 변화를 못 잡는다.
"""
import datetime
import io
import json
import os
import re
import sys
from decimal import ROUND_HALF_UP, Decimal

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import sido_zones as SZ  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def _data():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', s, re.S).group(1))
    sts = json.loads(re.search(r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', s, re.S).group(1))
    return adv, sts


def _page(z):
    return io.open(os.path.join(ROOT, 'zone', z, 'index.html'), encoding='utf-8').read()


def _pv2(v):
    r = float(Decimal(repr(abs(v))).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)) * (-1 if v < 0 else 1) + 0.0
    return ('+' if r > 0 else '') + '%.2f' % r


def _md(p, plus=0):
    d = datetime.date(*(int(x) for x in p.split('-'))) + datetime.timedelta(days=plus)
    return '%d/%d' % (d.month, d.day)


def _block(z):
    s = _page(z)
    m = re.search(r'<section><div class="wrap"><h2>%s 시세도 함께</h2>(.*?)</section>' % re.escape(z), s, re.S)
    return s, (m.group(1) if m else None), (m.start() if m else -1)


def test_every_report_has_the_block_between_method_and_other_regions():
    for z in SZ.ORDER:
        s, blk, at = _block(z)
        assert blk, '%s 리포트에 시세 블록이 없다' % z
        assert s.index('<h2>어떻게 계산했나</h2>') < at < s.index('<h2>다른 지역</h2>'), (
            '%s: 시세 블록이 방법론과 다른 지역 사이에 있지 않다' % z)


def test_weekly_line_matches_saved_data():
    adv, _ = _data()
    w = adv['weekly']
    row = w['rows'][-1]
    for z in SZ.ORDER:
        _, blk, _ = _block(z)
        m = re.search(r'<a href="/weekly/"><b>이번 주 시세</b><i>(.*?)</i></a>', blk or '')
        i = w['regions'].index(z) if z in w['regions'] else None
        ma = row['ma'][i] if i is not None else None
        je = row['je'][i] if i is not None else None
        if ma is None and je is None:
            assert not m, '%s: 주간 값이 없는데 칸을 인쇄했다' % z
            continue
        assert m, '%s: 주간 시세 칸이 없다' % z
        want = ' · '.join('%s %s%%' % (k, _pv2(v)) for k, v in (('매매', ma), ('전세', je)) if v is not None)
        want += ' · %s 조사 · %s 발표' % (_md(row['p']), _md(row['p'], 3))
        assert m.group(1) == want, '%s: %r ≠ %r' % (z, m.group(1), want)


def test_jeonse_line_matches_saved_data():
    _, sts = _data()
    j = sts['전세가율']
    li = len(j['dates']) - 1
    for z in SZ.ORDER:
        _, blk, _ = _block(z)
        m = re.search(r'<a href="/jeonse-ratio/"><b>전세가율</b><i>(.*?)</i></a>', blk or '')
        ser = j['series'].get(z) or []
        cur = ser[li] if li < len(ser) else None
        if cur is None:
            assert not m, '%s: 전세가율 값이 없는데 칸을 인쇄했다' % z
            continue
        ago = ser[li - 12] if li >= 12 and li - 12 < len(ser) else None
        want = '%.1f%%' % cur
        if ago is not None:
            want += ' · 1년 전 대비 %+.1f%%p' % (round(cur - ago, 1) + 0.0)
        want += ' · %s 기준' % j['dates'][li]
        assert m and m.group(1) == want, '%s: %r ≠ %r' % (z, m and m.group(1), want)


def test_generator_reads_saved_values_not_literals():
    src = io.open(os.path.join(ROOT, 'tools', 'make_sido_pages.py'), encoding='utf-8').read()
    body = src[src.index('def next_links'):src.index('def build_page')]
    assert 'MW.pv2' in body and "'전세가율'" in body, '시세 블록이 저장분·공용 표기를 쓰지 않는다'
    assert not re.search(r'\d+\.\d+%', body.split('"""', 2)[-1]), '시세 블록에 수치를 박았다'


def test_faq_has_the_common_disclaimer():
    s = io.open(os.path.join(ROOT, 'faq', 'index.html'), encoding='utf-8').read()
    foot = re.search(r'<footer>.*?</footer>', s, re.S)
    assert foot and '투자자문이 아닙니다' in foot.group(0), 'FAQ 푸터에 투자 면책이 없다'
