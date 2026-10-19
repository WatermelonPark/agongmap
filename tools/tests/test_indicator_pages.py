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
    hn, ln = I.SZ.disp(hi), I.SZ.disp(lo)   # 문장의 이름은 화면 이름(백로그 46)
    assert '가장 높은 곳은 <strong>%s %.1f%%</strong>' % (hn, sido[hi]) in html
    assert '가장 낮은 곳은 <strong>%s %.1f%%</strong>' % (ln, sido[lo]) in html
    assert '%s %.1f%%로 가장 높고 %s %.1f%%' % (I.ga(hn), sido[hi], I.neun(ln), sido[lo]) in html


def _shown_delta(cur, ago):
    """'변화' 칸의 계약(전수 리뷰 #16): **표시값(소수 첫째 자리)끼리의 차**. 정본 I.jeonse_delta 를 가져다 쓰지 않고 여기서
    따로 셈한다 — 같은 함수로 기대값을 만들면 그 함수의 회귀(원값 차로 되돌림)를 못 잡는다(전수리뷰 T2-7)."""
    return round(float('%.1f' % cur) - float('%.1f' % ago), 1) + 0.0


def test_jeonse_table_compares_with_twelve_months_ago():
    """표의 '1년 전'·'변화'와 머리 숫자·'1년 새 가장 크게 오른 곳'은 12개월 전 값과 견주고, 변화는 표시값끼리의 차다.

    변이(실제로 확인): build_jeonse 의 `SZ.month_back(dates, li, 12)` 를 11 로 바꾸면 모든 행의 '1년 전'이 틀려 빨개진다.
          jeonse_delta 를 원값 차 `round(cur - ago, 1) + 0.0` 으로 되돌리면 둘째 자리가 경계에 걸린 행에서 빨개진다
          (예전 기대식 round(cur - ago, 1) 은 cur 가 첫째 자리뿐인 픽스처라 그 변이에도 초록이었다 — 전수리뷰 T2-7).
    픽스처: 지역마다 1년 변화폭이 다른 14개월 계열(_jeonse_sts) — 11개월 전과 12개월 전이 다른 값이다. 기준월 값에는 둘째 자리
          (+0.04, 표시값은 그대로)를 얹어 전남광주 가중평균 계열 같은 실제 모양(78.72·77.16 → 표 +1.5, 원값 차 +1.6)을 만든다.
    """
    sts = _jeonse_sts()
    ser = sts['전세가율']['series']
    for r in ser:
        ser[r][-1] = round(ser[r][-1] + 0.04, 3)
    gap = [r for r in _JR if _shown_delta(ser[r][-1], ser[r][-13]) != round(ser[r][-1] - ser[r][-13], 1) + 0.0]
    assert gap, '픽스처에 표시값 차와 원값 차가 갈리는 행이 없다 — 이 시험이 원값 차 회귀를 못 잡는다'
    html, _ = I.build_jeonse(sts)
    for r in list(_JR):
        cur, ago = ser[r][-1], ser[r][-13]
        d = _shown_delta(cur, ago)
        cls = 'up' if d > 0 else 'dn' if d < 0 else 'mut'
        row = '<td>%s</td><td>%.1f%%</td><td>%.1f%%</td><td class="%s">%+.1f%%p</td></tr>' % (I.SZ.disp(r), cur, ago, cls, d)   # 행은 화면 이름(백로그 46)
        assert row in html, '%s 행이 12개월 전과 견주지 않았다' % r
    nat_d = _shown_delta(ser['전국'][-1], ser['전국'][-13])
    assert '1년 전 대비 %+.1f%%p' % nat_d in html
    ch = {r: _shown_delta(ser[r][-1], ser[r][-13]) for r in I.SIDO17}
    top = max(I.SIDO17, key=lambda r: ch[r])
    assert '1년 새 가장 크게 오른 곳은 <strong>%s(%+.1f%%p)</strong>' % (I.SZ.disp(top), ch[top]) in html   # 화면 이름(백로그 46)


def test_jeonse_sentences_name_regions_by_their_display_name():
    """'가장 높은 곳'·'가장 낮은 곳'·'1년 새 가장 크게 오른 곳'과 설명 메타(og·JSON-LD 같은 글)는 판정 단위 키가 아니라 화면 이름을
    쓰고, 조사도 화면 이름 끝 글자로 센다('광주·전남이 …로 가장 높고', '광주·전남은 …'). 표 행만 화면 이름이던 때(10-17 백로그 46
    수정은 표 행만 바꿨다) 전남광주가 최고·최저·최대 상승인 달에 키가 그대로 나가 test_display_name 이 게이트에서 그날 데이터
    커밋을 막았다(전수리뷰 X2-1·Z1-1). 그 시험은 그날 데이터가 지나는 갈래만 보므로 여기서 세 자리를 합성 계열로 늘 본다.

    재현하는 실제 상태: 2026.05 전세가율 — 전남광주 78.72 가 경북 78.7 을 넘어 시도 최고였다(2012~2026 완비 165개월 중 59개월).
    픽스처: _jeonse_sts(2026.07 실측 모양)에서 DISPLAY_NAME 의 각 키(지금은 전남광주 하나)를 ① 최고이면서 1년 상승 1위인 값,
          ② 최저인 값으로 바꾼 두 계열.
    변이(각각 실제로 확인): build_jeonse 의 hi_n·lo_n·upm_p 가운데 하나에서 SZ.disp 를 빼면 빨개진다.
    """
    from test_display_name import _visible
    keys = [k for k in I.SZ.DISPLAY_NAME if k in I.SIDO17]
    assert keys, '화면 이름이 따로 있는 시도가 없다 — 이 시험이 아무것도 보지 않는다'
    for k in keys:
        name = I.SZ.disp(k)
        for case in ('high', 'low'):
            sts = _jeonse_sts()
            ser = sts['전세가율']['series']
            others = [ser[r][-1] for r in I.SIDO17 if r != k]
            ser[k][-1] = round(max(others) + 1.5 if case == 'high' else min(others) - 1.5, 3)
            html, _ = I.build_jeonse(sts)
            v = _visible(html)
            leak = [x for x in I.SZ.DISPLAY_NAME if x in v]
            assert not leak, '%s: 문장에 판정 단위 키 %s 가 보인다' % (case, leak)
            cur = ser[k][-1]
            if case == 'high':
                ch = {r: _shown_delta(ser[r][-1], ser[r][-13]) for r in I.SIDO17}
                assert max(ch, key=ch.get) == k, '픽스처 전제: %s 가 1년 상승 1위여야 한다' % k
                assert '가장 높은 곳은 <strong>%s %.1f%%</strong>' % (name, cur) in html
                assert '%s %.1f%%로 가장 높고' % (I.ga(name), cur) in html
                assert '1년 새 가장 크게 오른 곳은 <strong>%s(%+.1f%%p)</strong>' % (name, ch[k]) in html
            else:
                assert '가장 낮은 곳은 <strong>%s %.1f%%</strong>' % (name, cur) in html
                assert '%s %.1f%%.' % (I.neun(name), cur) in html


def test_jeonse_page_names_no_riser_when_nothing_rose():
    """모든 시도의 1년 변화가 0 이하인 해에는 '1년 새 가장 크게 오른 곳'을 말하지 않는다(전수리뷰 B2 — 예전엔 '-0.3%p'
    짜리 지역을 '가장 크게 오른 곳'이라 적었다). 하나라도 오르면 그곳을 적는다.

    변이(실제로 확인): build_jeonse 의 `or up_most[2] <= 0` 을 지우면 첫 단정이 빨개진다.
    픽스처: _jeonse_sts 를 1년 전보다 모든 지역이 0.3~2.0%p 내린 계열로 바꾼 것(전세가율이 전국적으로 내린 해), 그리고
          그 가운데 한 시도(경북)만 오르게 한 것.
    """
    sts = _jeonse_sts()
    ser = sts['전세가율']['series']
    for i, r in enumerate(sorted(ser)):
        d = 0.3 + 0.1 * i
        n = len(ser[r])
        ser[r] = [round(ser[r][-1] + d * (n - 1 - k) / 12.0, 3) for k in range(n)]
    assert all(round(ser[r][-1] - ser[r][-13], 1) < 0 for r in I.SIDO17), '픽스처가 모두 내린 해가 아니다'
    html, _ = I.build_jeonse(sts)
    assert '가장 크게 오른 곳' not in html
    n = len(ser['경북'])
    ser['경북'] = [round(ser['경북'][-1] - 0.5 * (n - 1 - k) / 12.0, 3) for k in range(n)]
    html, _ = I.build_jeonse(sts)
    assert '1년 새 가장 크게 오른 곳은 <strong>경북(+0.5%p)</strong>' in html
