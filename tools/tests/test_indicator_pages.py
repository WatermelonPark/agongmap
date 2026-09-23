# -*- coding: utf-8 -*-
"""/jeonse-ratio/·/moveins/ 생성기의 방향어·최저 지역·1년 전 값을 고정한다(2026-09-23 전체 점검 시험 보강).

기존 시험은 이 두 페이지의 연도 머리(test_moveins_year)와 문구 몇 줄만 봤다. 그래서 다음 세 변이가
전부 초록이었다.
  - updown() 의 방향을 뒤집기 — 2026-08-01 실사고(105,950 → 115,411 인데 '줄어든다')의 재발
  - 전세가율 '가장 낮은 곳'을 max 로 뽑기
  - 전세가율 '1년 전' 값을 li-12 가 아니라 li-11 에서 읽기
생성기의 build_*() 를 직접 불러 HTML 문자열만 본다 — 저장소에 쓰지 않는다.
"""
import copy
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_indicator_pages as I  # noqa: E402
import make_sido_pages as P  # noqa: E402


def test_updown_follows_the_data_direction():
    """방향어는 데이터가 정한다. 2026-08-01 에 '줄어든다'를 본문에 박아 두었다가 105,950 → 115,411(증가)로
    바뀐 뒤 라이브에 정반대 문장이 걸렸다.

    변이: updown 의 `'늘어난다' if b > a else '줄어든다'` 를 `b < a` 로 뒤집으면 빨개진다(실제로 바꿔 확인).
    픽스처: 그 사고의 두 수(105,950 → 115,411)와 그 반대 방향, 3% 안쪽 변화, 값 없음.
    """
    assert I.updown(105950, 115411) == '늘어난다'
    assert I.updown(115411, 105950) == '줄어든다'
    assert I.updown(100000, 102900) == '거의 그대로다'
    assert I.updown(100000, 97100) == '거의 그대로다'
    assert I.updown(None, 5) == '이어진다'


def _moveins_with_capital(adv, factor):
    """수도권의 Y+1 예정 합이 Y 합의 factor 배가 되도록 Y+1 분기 값만 비례로 조정한다."""
    a = copy.deepcopy(adv)
    o = a['occupancy']
    i = o['regions'].index('수도권')
    y = int([r['p'] for r in o['rows'] if not r.get('e')][-1][:4])
    ty = sum(r['v'][i] or 0 for r in o['rows'] if r['p'].startswith(str(y)))
    rows1 = [r for r in o['rows'] if r['p'].startswith(str(y + 1))]
    t1 = sum(r['v'][i] or 0 for r in rows1)
    for r in rows1:
        r['v'][i] = r['v'][i] * ty * factor / t1
    return a, y


def test_moveins_sentence_says_increase_or_decrease_as_the_data_does():
    """/moveins/ 의 '수도권은 Y년 …에서 Y+1년 …로 ___' 문장이 두 방향 모두 데이터를 따른다.

    변이: 위 updown 방향 뒤집기로 두 단정이 함께 빨개진다(확인). 이번 데이터가 어느 쪽이든
          두 방향을 모두 만들어 보므로 그 주의 방향에 기대지 않는다.
    픽스처: 저장소의 실제 ADV.occupancy 에서 수도권 Y+1 예정만 Y 실적의 1.2배·0.8배로 맞춘 두 상태.
    """
    adv, _ = P.load()
    for factor, word in ((1.2, '늘어난다'), (0.8, '줄어든다')):
        a, y = _moveins_with_capital(adv, factor)
        html, _ = I.build_moveins(a)
        m = re.search(r'수도권은 %d년 ([\d,]+)세대에서 %d년 ([\d,]+)세대로 ([^.]+)\.' % (y, y + 1), html)
        assert m, '수도권 방향 문장을 찾지 못했다'
        a0, a1 = (int(x.replace(',', '')) for x in m.group(1, 2))
        assert (a1 > a0) == (factor > 1), '픽스처가 의도한 방향을 못 만들었다'
        assert m.group(3) == word, '%d→%d 인데 "%s"' % (a0, a1, m.group(3))


# 2026.07 실측 전세가율(시도 16곳 + 집계). 가장 높은 곳 경북 78.8, 가장 낮은 곳 세종 52.1 이다.
_JR = {'전국': 69.1, '수도권': 62.9, '지방': 74.9,
       '서울': 52.4, '경기': 66.8, '인천': 69.6, '부산': 69.3, '대구': 70.8, '대전': 71.8,
       '울산': 74.7, '세종': 52.1, '강원': 76.8, '충북': 78.6, '충남': 77.6, '전북': 78.3,
       '경북': 78.8, '경남': 78.3, '제주': 65.9, '전남광주': 78.6}


def _jeonse_sts():
    """14개월(2025.06~2026.07). 지역마다 1년 변화폭 d 가 달라(음수 포함) 12개월 전과 11개월 전이 다르다."""
    dates = ['2025.%02d' % m for m in range(6, 13)] + ['2026.%02d' % m for m in range(1, 8)]
    n = len(dates)
    ser = {}
    for i, (r, cur) in enumerate(sorted(_JR.items())):
        d = 0.37 * ((i % 7) - 3) + 0.05 * i            # −1.11 ~ +1.9, 지역마다 다름
        ser[r] = [round(cur - d * (n - 1 - k) / 12.0, 3) for k in range(n)]
    return {'전세가율': {'dates': dates, 'series': ser}}


def test_jeonse_page_names_the_true_lowest_and_highest():
    """'가장 높은 곳'·'가장 낮은 곳'과 설명문의 두 지역이 실제 최고·최저여야 한다.

    변이: build_jeonse 의 `lo = min(vals, ...)` 를 `max` 로 바꾸면 최저 자리에 경북이 올라 빨개진다
          (실제로 바꿔 확인). hi 를 min 으로 바꿔도 빨개진다.
    픽스처: 2026.07 실측 값(_JR) — 최고 경북 78.8, 최저 세종 52.1 로 동률이 없다.
    """
    sts = _jeonse_sts()
    html, _ = I.build_jeonse(sts)
    sido = {r: v for r, v in _JR.items() if r in I.SIDO17}
    lo = min(sido, key=sido.get)
    hi = max(sido, key=sido.get)
    assert '가장 높은 곳은 <strong>%s %.1f%%</strong>' % (hi, sido[hi]) in html
    assert '가장 낮은 곳은 <strong>%s %.1f%%</strong>' % (lo, sido[lo]) in html
    assert '%s %.1f%%로 가장 높고 %s %.1f%%' % (I.ga(hi), sido[hi], I.neun(lo), sido[lo]) in html


def test_jeonse_table_compares_with_twelve_months_ago():
    """표의 '1년 전'·'변화'와 머리 숫자·'1년 새 가장 크게 오른 곳'은 12개월 전(li−12) 값과 견준다.

    변이: build_jeonse 의 `at(name, li - 12)` 를 `li - 11` 로 바꾸면 모든 행의 '1년 전'이 틀려 빨개진다
          (실제로 바꿔 확인). 머리의 전국 변화(`nat_d`)만 li−11 로 바꿔도 빨개진다.
    픽스처: 지역마다 1년 변화폭이 다른 14개월 계열(_jeonse_sts) — 11개월 전과 12개월 전이 다른 값이다.
    """
    sts = _jeonse_sts()
    ser = sts['전세가율']['series']
    html, _ = I.build_jeonse(sts)
    for r in list(_JR):
        cur, ago = ser[r][-1], ser[r][-13]
        d = round(cur - ago, 1)
        cls = 'up' if d > 0 else 'dn' if d < 0 else 'mut'
        row = '<td>%s</td><td>%.1f%%</td><td>%.1f%%</td><td class="%s">%+.1f%%p</td></tr>' % (r, cur, ago, cls, d)
        assert row in html, '%s 행이 12개월 전과 견주지 않았다' % r
    nat_d = round(ser['전국'][-1] - ser['전국'][-13], 1)
    assert '1년 전 대비 %+.1f%%p' % nat_d in html
    ch = {r: round(ser[r][-1] - ser[r][-13], 1) for r in I.SIDO17}
    top = max(I.SIDO17, key=lambda r: ch[r])
    assert '1년 새 가장 크게 오른 곳은 <strong>%s(%+.1f%%p)</strong>' % (top, ch[top]) in html
