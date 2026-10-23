"""월간 시세 블로그 초안 생성기(make_monthly_post) — 숫자가 /monthly/ 페이지와 같은 함수·같은 반올림에서 나오는지."""
import copy
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import make_monthly_page as MP   # noqa: E402
import make_monthly_post as MO   # noqa: E402


def test_draft_says_the_site_numbers(tmp_path):
    """실데이터로 초안을 굽고, 글의 숫자를 /monthly/ 쪽 함수로 따로 다시 세어 대조한다(기대값은 데이터에서 유도 — 달이 바뀌어도 초록).
    ① 서울 매매 표시값(MP.pv2) ② 서울 구 오른 곳·내린 곳 수(표시값 부호) ③ 인허가 이 달·12개월 합(MP.cum_month·trail12, MP.num 꼴)
    ④ 제목 꼴('[한국부동산원] N월 월간 아파트가격 동향 | 결론절') ⑤ 해석 자리 표시자 하나·엠대시 0·UTM 링크.
    변이(확인): 인허가를 '{:,}'.format 으로 되돌리면('44,773.0세대') ③이, 제목 구분자를 '|' 대신 괄호로 바꾸면 ④가,
    해석 자리 표시자를 지우면 ⑤가 빨개진다. 픽스처: 저장소 data.js 그대로(배치가 구운 그 달)."""
    adv, sts = MP.load()
    f, title, out = MO.build(str(tmp_path), adv_sts=(adv, sts), draw=False)
    body = (tmp_path / 'body.html').read_text(encoding='utf-8')
    mo = adv['monthly']; regs = mo['regions']; last = mo['rows'][-1]
    assert MP.pv2(last['ma'][regs.index('서울')]) + '%' in body
    se = mo['seoul']; vals = [MP.MW.pv2r(v) for v in se['rows'][-1]['ma'] if v is not None]
    up, down = sum(v > 0 for v in vals), sum(v < 0 for v in vals)
    if down:
        assert '%d곳이 오르고' % up in body, body
    if sts.get('인허가'):
        i, p = MP.last_idx(sts['인허가'])
        cur, yr = MP.cum_month(sts['인허가'], i), MP.trail12(sts, p)
        if cur.get('서울') is not None and yr.get('서울'):
            assert '%s세대, 최근 12개월 합은 %s세대' % (MP.num(cur['서울']), MP.num(yr['서울'])) in body
    assert not re.search(r'\d\.0세대', body)
    assert re.match(r'^\[한국부동산원\] \d{1,2}월 월간 아파트가격 동향 \| \S', title), title
    assert body.count('[여기에 이번 달 해석') == 1
    assert '—' not in re.sub(r'\[[^\]]*\]', '', body)
    links = re.findall(r'href="([^"]+)"', body)
    assert links and all('utm_campaign=monthly_' in u and '#' not in u for u in links), links


def test_counts_use_display_rounding():
    """구 하나가 -0.004%(화면 '0.00')면 내린 곳으로 세지 않는다 — 사이트 표가 '0.00'이라 쓰는 칸을 글이 '내렸다'고 하면 안 된다.
    픽스처: 실데이터 사본에서 오른 구 하나의 9월 값을 -0.004 로 바꾼 상태(원값 부호와 표시 부호가 갈리는 실제 꼴, pv2 독스트링의 -0.0012 사례).
    변이(확인): facts 의 rv(v) 를 원값 v 로 되돌리면 빨개진다."""
    adv, sts = MP.load()
    adv = copy.deepcopy(adv)
    row = adv['monthly']['seoul']['rows'][-1]
    k = next(i for i, v in enumerate(row['ma']) if v is not None and v > 0)
    name = adv['monthly']['seoul']['regions'][k]
    row['ma'][k] = -0.004
    f = MO.facts(adv, sts)
    assert name not in [n for n, _ in f['down']] and name not in [n for n, _ in f['up']], (name, f['down'])


def test_trend_and_streak_words():
    """추세 문장과 '넉 달째' 낱말. 재현: 2026년 7~9월 서울 +1.27·+1.05·+0.74(두 달째 줄었다 — 처음 손 초안은 '석 달째'로 잘못 셌다),
    지방 6~9월 +0.01·+0.02·+0.05·+0.03(넉 달째 0.1% 아래). 변이(확인): trend_text 가 첫 달부터 세게 바꾸면, KDAL 의 4 → '넉' 을 지우면 빨개진다."""
    s = [('2026-06', 1.21), ('2026-07', 1.27), ('2026-08', 1.05), ('2026-09', 0.74)]
    assert MO.trend_text(s[-3:]) == '두 달째 상승폭이 줄었어요.'
    assert MO.trend_text(s) == '두 달째 상승폭이 줄었어요.'
    assert MO.trend_text([('a', 0.1), ('b', 0.2), ('c', 0.3)]) == '두 달째 상승폭이 커졌어요.'
    assert MO.trend_text([('a', 0.2), ('b', 0.2)]) == '상승폭은 지난달과 같았어요.'
    local = [('2026-05', 0.12), ('2026-06', 0.01), ('2026-07', 0.02), ('2026-08', 0.05), ('2026-09', 0.03)]
    assert MO.local_streak(local) == 4 and MO.KDAL(4) == '넉 달째'
