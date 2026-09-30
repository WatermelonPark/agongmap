# -*- coding: utf-8 -*-
"""검색어 정렬(홈 마케팅 검수 B4·SEO-3①·SEO-4·SEO-7, 2026-09-27)을 고정한다.

재현하는 실제 상태:
  - /weekly/ title 이 생성기가 안 쓰는 고정 문구('이번 주 아파트 시세 지도…')라, 배치가 멈춘 주에도 검색 결과에 '이번 주'
    제목 아래 지난 발표가 보였다. 사람들이 치는 '주간아파트가격동향'·'9월 셋째 주'는 title·머리줄에 없었고 JSON-LD 에
    날짜가 없었다. 블로그 주간 글은 이미 '주간 아파트가격 동향(9월 셋째 주)'로 바꿨는데(09-17) 사이트는 다른 말을 썼다.
  - 시도 리포트 제목이 '서울 아파트 공급 분석 — 매우 부족'이라 팀이 확인한 검색 형태(연도 + 지역 + 아파트 공급물량 + 전망)와
    달랐다.
무엇을 깨뜨리면 빨개지나는 시험마다 적었다(각각 실제로 바꿔 확인).
"""
import io
import json
import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import make_sido_pages as M  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import sido_zones as SZ  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


@pytest.mark.parametrize('p,want', [
    ('2026-09-21', '9월 셋째 주'),      # 9/24 발표분 — 블로그 '주간 아파트가격 동향(9월 셋째 주)' 글과 같은 주
    ('2026-09-28', '9월 넷째 주'),
    ('2026-09-07', '9월 첫째 주'),
    ('2026-06-29', '6월 다섯째 주'),
    ('2026-12-28', '12월 넷째 주'),
])
def test_week_label_is_the_blog_ordinal(p, want):
    """주차 서수 = 조사기준일의 (일−1)//7 — 2026-09-12 블로그 제목 형식 그대로. 연도는 조사기준일의 해.

    변이: week_label 을 (일)//7 로 바꾸면 9/7 이 '둘째'가 되어 빨개진다(확인).
    """
    assert WR.week_label(p) == want
    assert WR.week_label(p, year=True) == '%s년 %s' % (p[:4], want)


def test_blog_title_uses_the_same_label_function_and_words():
    """블로그 주간 초안 제목이 /weekly/ 와 같은 함수(week_label)·같은 말(TITLE_KW)을 쓴다 — 사본 서수표가 남지 않는다.

    변이: make_naver_post 에 예전 `ORD = ('첫째', …)` 계산을 되살리거나 라벨을 문자열로 다시 적으면 빨개진다(확인).
    """
    src = io.open(os.path.join(ROOT, 'tools', 'make_naver_post.py'), encoding='utf-8').read()
    assert "'첫째'" not in src and 'ORD[' not in src
    assert "'[한국부동산원] %s(%s) | 서울 %s 전국 %s' % (\n        MW.TITLE_KW, MW.WR.week_label(p)" in src
    assert MW.TITLE_KW == '주간 아파트가격 동향'


def _week(p='2026-09-21'):
    regs = list(SZ.DISPLAY_ORDER)
    codes = ['C%02d' % i for i in range(12)]
    W = {'regions': regs, 'rows': [{'p': p, 'ma': [0.03] * len(regs)}], 'holidays': [],
         'sgg': {'codes': codes, 'rows': [{'p': p, 'ma': [0.02 * i - 0.1 for i in range(12)]}]},
         'seoul': {'regions': ['강남구', '마포구'], 'rows': [{'p': p, 'ma': [0.1, -0.1]}]}}
    return W, {c: '시군구%d' % i for i, c in enumerate(codes)}


def _skeleton():
    return io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()


def _ld(s):
    return json.loads(re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', s, re.S).group(1))


def test_weekly_title_head_line_and_dates_carry_the_week():
    """/weekly/ 의 title·og:title·twitter:title·WebPage name 에 '주간 아파트가격 동향 2026년 9월 셋째 주', 머리줄 첫 조각에 같은
    주차, JSON-LD WebPage 에 발표일(datePublished·dateModified). 날짜가 없던 뼈대에는 넣고, 있던 판에서는 값만 바꾼다.

    픽스처: 9/21 조사(9/24 발표) 주와 그다음 주(9/28 조사). 뼈대는 저장소 weekly/index.html 에서 날짜 두 줄을 뗀 것(배포 전 모양).
    변이: render 에서 put_ld_dates 를 빼거나, titles() 가 연도 없는 week_label 을 쓰거나, eyebrow 의 wk-label 을 지우면 빨개진다
          (셋 다 확인).
    """
    base = re.sub(r'\s*"date(Published|Modified)": "[^"]*",', '', _skeleton())
    assert '"datePublished"' not in base
    W, Q = _week()
    out = MW.render(base, W, Q)
    lab = '주간 아파트가격 동향 2026년 9월 셋째 주'
    assert re.search(r'<title>([^<]*)</title>', out).group(1) == lab + ' | 아파트 시세 지도 | 아공맵'
    og = re.search(r'<meta property="og:title" content="([^"]*)"', out).group(1)
    assert og.startswith(lab) and og == re.search(r'<meta name="twitter:title" content="([^"]*)"', out).group(1)
    ld = _ld(out)
    assert ld['@type'] == 'WebPage' and ld['name'] == og
    assert ld['datePublished'] == ld['dateModified'] == '2026-09-24'
    assert ld['about']['@type'] == 'Dataset' and ld['about']['name'] != og, '중첩 Dataset 의 name 을 덮어썼다'
    assert '<p class="eyebrow"><span class="wk-label">2026년 9월 셋째 주</span> · <span id="wk-when">' in out
    assert len(re.search(r'<title>([^<]*)</title>', out).group(1).split(' | ')[0]) <= 30, '검색 결과에 보이는 30자 안쪽'
    W2, Q2 = _week('2026-09-28')
    out2 = MW.render(out, W2, Q2)
    ld2 = _ld(out2)
    assert ld2['datePublished'] == ld2['dateModified'] == '2026-10-01'
    assert out2.count('"datePublished"') == 1 and '2026년 9월 넷째 주' in re.search(r'<title>([^<]*)</title>', out2).group(1)
    assert MW.render(out2, W2, Q2) == out2


@pytest.mark.parametrize('grade', sorted(M.GRADE_TXT))
def test_zone_title_is_the_search_shape_for_every_grade(grade):
    """'2026년 서울 아파트 공급물량 전망, 3년 필요량 대비 매우 부족' — 연도는 전망하는 해, '3년'은 판정 창, 등급 말은 배지.

    연도는 주간 최신 조사일에서 sido_zones.outlook_year 로(10월부터 다음 해 — 2026-09-27 대표 결정, 블로그 지역 편과 한 함수).
    조사일이 없으면 연도를 뺀다(블로그와 같다).
    변이: page_title 의 연도를 '2026' 글자나 조사일의 해(p[:4])로 바꾸면 10월 픽스처에서, 기준 분기(calc['L'])에서 읽으면 9월
          픽스처에서, '대비'를 '보다'로 되돌리면 모양 단정에서 빨개진다(셋 다 확인).
    """
    lab = M.GRADE_TXT[grade][0]
    t = M.page_title('서울', {'L': '2026Q2', 'H': 12}, lab, '2026-10-05')
    assert t == '2027년 서울 아파트 공급물량 전망, 3년 필요량 대비 %s' % lab
    assert M.page_title('전국', {'L': '2026Q4', 'H': 8}, lab, '2027-09-28').startswith('2027년 전국 아파트 공급물량 전망, 2년 필요량 대비 ')
    assert M.page_title('서울', {'L': '2026Q2', 'H': 12}, lab, '') == '서울 아파트 공급물량 전망, 3년 필요량 대비 %s' % lab


def test_baked_zone_pages_share_one_title_across_title_og_and_headline():
    """배치가 구운 시도 리포트마다 <title>·og:title·JSON-LD headline 이 같은 값이고 그 값이 기준 분기의 연도로 시작한다.

    변이: head() 에서 og:title 이나 headline 에 옛 제목을 따로 넘기면 빨개진다(확인). 게이트는 생성기 뒤라 새 제목을 본다.
    픽스처: 저장소 data.js 의 ADV.sido 와 그걸로 구운 zone/<지역>/index.html(허브·통합 안내 페이지는 뺀다).
    """
    adv, _ = M.load()
    calc = adv['sido']
    for z in calc['zones']:
        path = os.path.join(ROOT, 'zone', z['z'], 'index.html')
        s = io.open(path, encoding='utf-8').read()
        title = re.search(r'<title>([^<]*)</title>', s).group(1)
        og = re.search(r'<meta property="og:title" content="([^"]*)"', s).group(1)
        head = [x for x in json.loads(re.search(r'<script type="application/ld\+json">(.*?)</script>', s, re.S).group(1))
                if x.get('@type') == 'Article'][0]['headline']
        want = M.page_title(z['z'], calc, M.GRADE_TXT[z['grade']][0], SZ.latest_survey(adv))
        assert title == M.esc(want) + ' | 아공맵' and og == M.esc(want) and head == want, (z['z'], title, og, head)
        assert want.startswith('%s년 %s 아파트 공급물량 전망, ' % (SZ.outlook_year(SZ.latest_survey(adv)), z['z']))


@pytest.mark.parametrize('p,want', [('2026-09-28', '2026'), ('2026-10-05', '2027'), ('2027-01-11', '2027'),
                                    ('2026-12-28', '2027'), ('', ''), (None, '')])
def test_outlook_year_is_the_year_being_forecast(p, want):
    """전망 연도 = 조사일의 해, 10월부터는 다음 해(2026-09-27 대표 결정). 변이: OUTLOOK_NEXT_FROM_MONTH 를 13 으로 두면 10·12월에서,
    기준 분기 규칙(L+1 의 해)으로 되돌리면 입력 모양이 달라 전부 빨개진다(확인)."""
    assert SZ.outlook_year(p) == want


@pytest.mark.parametrize('L,p,want', [('2026Q2', '2026-10-05', '2027'), ('2026Q3', '2027-01-11', '2027'), ('2026Q2', '2026-09-28', '2026')])
def test_site_and_blog_zone_titles_take_the_year_from_one_function(monkeypatch, L, p, want):
    """사이트 시도 리포트 제목과 블로그 지역 편 제목의 연도가 같은 함수(sido_zones.outlook_year)·같은 원천(주간 최신 조사일)에서
    나온다(요청서 B4, 2026-09-27 대표 결정 '전망하는 해 — 10월부터 다음 해').

    변이: make_naver_post 의 yr 줄을 조사일의 해(p[:4])로, make_sido_pages.page_title 을 기준 분기 규칙으로 되돌리거나 build_page 가
          조사일을 넘기지 않게 하면 빨개진다(확인).
    픽스처: 두 옛 원천이 갈리는 때. ① 2026년 10월 첫 주(조사일 10-05, 기준 분기 2026Q2): 전망하는 해 2027, 옛 사이트 원천(L+1 의 해)
            2026. ② 2027년 1월(조사일 01-11, 기준 분기 2026Q3 — 4분기 실적은 2월께): 2027, 옛 사이트 원천 2026. ③ 9월 말: 2026.
            draft_zone 을 끝까지 돌리지 않고, 그 안에서 제목을 만드는 zone_title 에 넘어가는 연도를 가로챈다.
    """
    import make_naver_post as P
    seen = {}

    class Stop(Exception):
        pass

    def grab(nm, yr, yrs, ask, seq, total=None):   # total: 바퀴 크기(전수리뷰 #80 제목 실험 팔)
        seen['yr'] = yr
        raise Stop()
    monkeypatch.setattr(P, 'zone_title', grab)
    adv = {'sido': {'L': L, 'H': 12, 'zones': []}, 'weekly': {'rows': [{'p': p}]}}
    row = {'z': '서울', 'dtot': 1000, 'ref': 1, 'fut': 1, 'inow': 1, 'ratio': 0.3, 'grade': 'g2'}
    with pytest.raises(Stop):
        P.draft_zone(adv, {}, row, 1, 1)
    site = M.page_title('서울', adv['sido'], '부족', SZ.latest_survey(adv))
    assert seen['yr'] == SZ.outlook_year(SZ.latest_survey(adv)) == site[:4] == want, (seen, site)
