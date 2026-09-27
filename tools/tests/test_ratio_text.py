# -*- coding: utf-8 -*-
"""판정 옆 비율 문구 (2026-09-13 PM 요청 ①).

경기 리포트가 판정은 '균형'인데 바로 아래 '누적 순부족 50,579세대'라 반대로 읽혔다.
등급은 '앞으로 H분기 필요량 대비 누적 순부족의 비율'로 자르는데 화면에 그 비율이
없었다. 비율을 판정 옆에 보여줘서 푼다. 이 시험이 지키는 것은 셋이다.

① 문구의 숫자는 ratio에서만 나온다.
② 문구는 한 곳(sido_zones)에서만 만든다 — 홈 JS가 다시 만들지 않는다.
③ 판정 규칙 문장의 숫자는 GRADE_CUTS에서 나온다.

⚠️ 생성된 페이지 내용을 라이브 데이터로 단정하지 않는다. 배치는 pytest를 페이지 생성보다
먼저 돌리므로 그 시점의 페이지는 지난 회차 것이다. 그렇게 짜면 비율이 바뀌는 주마다
배치가 멈춘다.
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)
import sido_zones as SZ  # noqa: E402
import make_sido_pages as P  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')


def _adv():
    src = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    return json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', src, re.S).group(1))


def test_percent_is_the_ratio_itself():
    for r in (0.02, 0.165, 0.49, 0.6, 0.97, 1.01, 1.79):
        t = SZ.ratio_text(r)
        assert ('%d%%' % int(round(r * 100))) in t, '%s → %s: 비율과 다른 숫자' % (r, t)
        assert '부족' in t


def test_shortfall_beyond_need_stays_in_percent():
    """'1.0배'는 '딱 같다'로 읽힌다(울산 1.012). 규칙 문장과 단위도 맞춘다."""
    assert '139%' in SZ.ratio_text(1.389) and '배' not in SZ.ratio_text(1.389)
    assert '101%' in SZ.ratio_text(1.012)


def test_surplus_reads_as_surplus():
    t = SZ.ratio_text(-0.19)
    assert '19%' in t and '여유' in t and '부족' not in t


def test_near_zero_does_not_invent_a_direction():
    t = SZ.ratio_text(0.004)
    assert '거의 같' in t and '부족' not in t and '여유' not in t


def test_sign_word_matches_sign_everywhere():
    for i in range(-150, 250):
        r = i / 100.0
        t = SZ.ratio_text(r)
        pct = int(round(r * 100))
        assert ('부족' in t) == (pct >= 1), '%s → %s' % (r, t)
        assert ('여유' in t) == (pct <= -1), '%s → %s' % (r, t)


def test_horizon_follows_H_instead_of_saying_three_years():
    """착공표가 한 달 늦으면 H가 11이 된다. 그때 '3년'이라고 쓰면 거짓이다."""
    assert '3년' in SZ.ratio_text(0.2, SZ.LEAD_Q)
    assert '3년' not in SZ.ratio_text(0.2, SZ.LEAD_Q - 1)


def test_stored_rows_carry_the_text_for_their_own_ratio():
    adv = _adv()
    H = adv['sido']['H']
    for z in adv['sido']['zones']:
        assert z.get('rtxt') == SZ.ratio_text(z['ratio'], H), \
            '%s: 저장된 문구가 저장된 비율과 다르다 — --seed-sido를 다시 돌릴 것' % z['z']


def _mid(lo, hi):
    return (lo + hi) / 2.0


def test_rule_sentence_numbers_come_from_the_cuts(monkeypatch):
    c = SZ.GRADE_CUTS
    for r in (c[0] + 0.3, _mid(c[1], c[0]), _mid(c[2], c[1]), _mid(c[3], c[2]), c[3] - 0.3):
        row = {'ratio': r, 'grade': SZ.grade(r)}
        line = P.verdict_line(row, SZ.LEAD_Q)
        assert SZ.ratio_text(r, SZ.LEAD_Q, full=True) in line
        assert P.GRADE_TXT[row['grade']][0] in line, '판정 문장에 등급 이름이 없다'
    # 컷을 옮기면 문장이 따라 바뀌어야 한다 — 숫자가 박혀 있지 않다는 증거
    monkeypatch.setattr(SZ, 'GRADE_CUTS', (2.0, 1.2, 0.6, 0.0))
    assert '60%' in P.verdict_line({'ratio': 0.3, 'grade': 'g1'}, SZ.LEAD_Q)


def test_balance_line_no_longer_says_enough_is_coming():
    """모순의 원문. g1에 '필요한 만큼 들어오고 있습니다'가 붙어 있었다."""
    r = 0.165
    line = P.verdict_line({'ratio': r, 'grade': SZ.grade(r)}, SZ.LEAD_Q)
    assert '필요한 만큼' not in line
    assert '%d%%' % int(round(r * 100)) in line and '균형' in line


def test_home_reads_the_baked_text_instead_of_rebuilding_it():
    src = HS.home_source()
    assert 'z.ctxt' in src, '홈 요약 카드가 구워 둔 카드 문구를 읽지 않는다'
    assert not re.search(r'z\.ratio\s*\*', src), '홈이 비율 문구를 따로 계산한다 — 이중 구현'


def test_inner_spread_exemptions_are_real_regions():
    for z in P.NO_INNER_UNITS:
        assert z in SZ.ORDER and z not in SZ.AGG, '%s는 모델에 없는 지역이다' % z


# ── 판정 설명(full)은 판정의 정의대로 지난 4년 재고까지 셈한다(홈 마케팅 검수 B2·C4·TRUST-2④, 2026-09-27 검토 지적) ──
# 인천 실측 모양: 3년 필요량 69,600 · 착공 기반 입주 추정 66,579(필요량보다 적다) · 지난 4년 남은 재고 16,258 → 13,237세대
# 여유(19%). 옛 문장 '앞으로 3년 필요량보다 19% 더 들어옵니다'는 바로 옆의 식(formula_text)과 숫자로 부딪쳤다.
INCHEON = {'z': '인천', 'ref': 5800, 'fut': 66579, 'inow': 16258, 'dtot': -13237,
           'ratio': round(-13237 / 69600.0, 4), 'grade': 'g0'}


def test_full_sentence_counts_the_past_window_on_the_formula_branch():
    """full 문장은 앞으로 3년만의 주장('더 들어옵니다', '앞으로 3년')을 하지 않고, 지난 4년 재고의 갈래가 식(formula_text)의
    갈래와 같다 — 모자랐으면 '덜 지은 몫', 남았으면 '남은 재고'. 퍼센트는 비율 그대로이고 방향말은 비율 부호를 따른다.

    변이(각각 실제로 확인): ratio_text(full=True) 를 옛 문장('앞으로 3년 필요량보다 N% 더 들어옵니다' / '누적 순부족이 …')으로
          되돌리면 첫 단정이, inow 갈래를 뒤집으면('덜 지은 몫' ↔ '남은 재고') 식 갈래 단정이 빨개진다.
    픽스처: 비율 부호(부족·여유·거의 0) × 지난 재고 부호(모자람·남음·모름) 아홉 칸 — 여유 × 남음이 인천, 부족 × 남음이 충북
            (앞으로 3년 78% 인데 과거 여유 덕에 균형), 부족 × 모자람이 전국 모양이다.
    """
    past = '지난 %g년' % (SZ.BACKLOG_WINDOW / 4.0)
    for r in (0.6, 0.009, -0.19, 0.004):
        pct = int(round(r * 100))
        for inow in (-260523, 16258, None):
            t = SZ.ratio_text(r, SZ.LEAD_Q, full=True, inow=inow)
            assert '더 들어옵니다' not in t and '앞으로' not in t and '누적 순부족' not in t, t
            assert t.startswith(past), '판정 설명이 지난 창 재고를 말하지 않는다: %s' % t
            if abs(pct) >= 1:
                assert '%d%%만큼' % abs(pct) in t, t
            assert ('부족합니다' in t) == (pct >= 1) and ('남습니다' in t) == (pct <= -1), t
            if inow is not None and abs(pct) >= 1:   # 거의 0 이면 방향이 없어 갈래도 없다
                tail = SZ.formula_text(SZ.LEAD_Q, SZ.BACKLOG_WINDOW, 1, 1, inow)
                assert ('덜 지은 몫' in t) == ('쌓인 부족' in tail) and ('남은 재고' in t) == ('남은 재고' in tail), \
                    (t, tail)


def test_surplus_report_and_blog_do_not_say_more_is_coming_than_needed(monkeypatch):
    """여유 지역(입주 추정 < 필요량, 남은 재고 > 0)의 시도 리포트 판정 문장과 블로그 지역 편 판정 문단은 '지난 4년 남은 재고까지
    더하면 3년 필요량의 19%만큼 남습니다'이고, 바로 다음 식 한 줄과 숫자·갈래가 맞는다(TRUST-2④).

    변이(각각 실제로 확인): verdict_line 이 inow 를 넘기지 않으면(갈래 없는 '재고까지 셈하면') 리포트 단정이, draft_zone 이
          inow 를 넘기지 않으면 블로그 단정이, ratio_text 를 옛 여유 문장으로 되돌리면 둘 다 빨개진다.
    픽스처: 인천 실측 모양의 합성 행(INCHEON). 블로그는 저장소 판정 행을 복사해 숫자만 이 모양으로 덮는다(데이터가 앞으로
            가도 같은 숫자).
    """
    want = '지난 4년 남은 재고까지 더하면 3년 필요량의 19%만큼 남습니다'
    line = P.verdict_line(INCHEON, SZ.LEAD_Q)
    assert line.startswith(want + '. '), line
    assert '더 들어옵니다' not in line

    import make_naver_post as N
    monkeypatch.setattr(sys, 'argv', ['make_naver_post.py', '--no-shot'])
    monkeypatch.setattr(N, 'thumb_zone', lambda *a, **k: None)
    monkeypatch.setattr(N, 'series_links', lambda *a, **k: '')
    adv, sts = P.load()
    r = dict(next(z for z in adv['sido']['zones'] if z['z'] == '인천'), **INCHEON)
    body = N.draft_zone(adv, sts, r, 1, 16)['body']
    m = re.search(r'판정은 <b>[^<]+</b>입니다\. ([^<]+)\.</p>\s*<p>셈은 <b>([^<]+)</b>입니다\.</p>', body)
    assert m, body[:600]
    assert m.group(1) == want, m.group(1)
    assert m.group(2) == SZ.formula_text(SZ.LEAD_Q, SZ.BACKLOG_WINDOW, 69600, 66579, 16258)
    assert '더 들어옵니다' not in body


def test_faq_quotes_the_report_sentence_it_explains():
    """FAQ '판정이 균형인데 왜 부족 세대수가 나오나요?'가 인용하는 지역 리포트 문장 틀이 지금 ratio_text 가 굽는 문장과 같다.

    재현하는 실제 상태(2차 배포 검토, 2026-09-27): 판정 설명을 '지난 4년 덜 지은 몫까지 더하면 3년 필요량의 N%만큼
    부족합니다'로 바꾼 뒤에도 손으로 쓴 faq/index.html 은 사라진 옛 문장('누적 순부족이 앞으로 3년 필요량의 N%입니다')을
    따옴표로 인용하며 '지역 페이지 머리의 … 문장이 바로 그 기준'이라고 말했다. 어느 시험도 이 인용을 보지 않았다.
    변이: ratio_text 의 모자람 갈래 문구를 바꾸거나 FAQ 인용을 옛 문장으로 되돌리면 빨개진다(실제로 확인).
    """
    faq = io.open(os.path.join(ROOT, 'faq', 'index.html'), encoding='utf-8').read()
    m = re.search(r'지역 페이지</a> 머리의 "([^"]+)" 문장', faq)
    assert m, 'FAQ 에서 지역 리포트 문장 인용을 찾지 못했다'
    want = re.sub(r'\d+%', 'N%', SZ.ratio_text(0.6, full=True, inow=-1))
    assert m.group(1) == want, 'FAQ 인용 "%s" ≠ 리포트 문장 틀 "%s"' % (m.group(1), want)
