# -*- coding: utf-8 -*-
"""순위 추적 검색어 교체와 네이버 사본 신선도 표시(2026-09-27 조회수 조사 SRCH-7).

추적하던 '2026년 {지역} 아파트 공급물량'은 월 검색량이 집계 하한에도 못 미쳐, 순위가 올라도 사람이 오지
않는다. 그래서 지역마다 '{지역} 적정 공급량'(고유어, 경쟁 적음)과 '{검색 표기} 부동산 전망'(수요 있음)을
더하고, 전국 질의는 블로그와 웹문서를 함께 잰다. 웹문서에서 잡힌 우리 페이지의 제목이 저장소의 지금
<title> 과 다르면 네이버 사본이 옛것이라고 표시한다(09-27 실측: 시도 리포트 사본이 6주 넘게 옛 제목).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - track_keywords 에서 적정 공급량·부동산 전망 추가를 빼면 → 검색어 시험
  - make_naver_post._zone_of_title 의 정규식에서 '부동산'을 빼면 → B안 제목 시험 둘(제목 교대 실험
    B안으로 발행한 세종 편을 못 세면 다음 회차에 세종을 또 고른다)
  - stale_copy 가 늘 False 를 돌려주면 → 사본 시험
픽스처: 실제 발행 제목 형태(A안 '2026년 부산 아파트 공급물량 전망, …', B안 '2026 세종시 부동산 전망, …')와
저장소의 실제 /zone/서울/ 페이지. 네트워크는 쓰지 않는다.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import make_naver_post as P  # noqa: E402
import naver_serp as NS  # noqa: E402
import sido_zones as SZ  # noqa: E402

ZONE = '지역별 아파트 공급'
NAMES = [z for z in SZ.ORDER if z not in SZ.AGG]


def test_track_adds_demand_and_own_terms():
    posts = [dict(date='2026-09-01', cat=ZONE, title='2026년 부산 아파트 공급물량 전망, 지금은 남는데 3년 뒤엔 모자랍니다'),
             dict(date='2026-09-29', cat=ZONE, title='2026 세종시 부동산 전망, 전세는 6주째 오르고 공급물량은 빠듯합니다'),
             dict(date='2026-09-27', cat='주간 아파트 시세', title='[한국부동산원] 주간 아파트가격 동향')]
    kws = NS.track_keywords(posts)
    assert '2026년 부산 아파트 공급물량' in kws               # 옛 추이를 잇는다
    for kw in ('부산 적정 공급량', '부산 부동산 전망', '세종 적정 공급량', '세종시 부동산 전망'):
        assert kw in kws, kw
    assert not any('한국부동산원' in k for k in kws)


def test_b_arm_title_is_counted_as_that_zone():
    assert P._zone_of_title('2026 세종시 부동산 전망, 전세는 6주째 오르고 공급물량은 빠듯합니다', NAMES) == '세종'
    assert P._zone_of_title('2026년 부산 아파트 공급물량 전망, 서울 아파트와 반대로 갑니다', NAMES) == '부산'


def test_stale_naver_copy_is_flagged():
    cur = NS.site_title('https://www.agongmap.co.kr/zone/%EC%84%9C%EC%9A%B8/')
    assert cur and '서울' in cur
    assert NS.stale_copy('<b>서울</b> 생활권 공급 분석 — 다소 부족 | 아공맵', cur) is True
    assert NS.stale_copy('<b>%s</b>...' % cur[:20], cur) is False
    assert NS.stale_copy(None, cur) is None


def test_track_records_date_rank_too(monkeypatch, tmp_path):
    """--track 은 정확도순과 함께 최신순 자리(n_date)를 기록한다(2026-09-29). 변이: 최신순 조회를 빼면 빨개진다."""
    calls = []

    def fake_get(kind, q, display=10, sort='sim'):
        calls.append(sort)
        items = [{'link': 'https://blog.naver.com/startupbd/1', 'title': 't'}] if sort == 'date' else []
        return {'items': items, 'total': 1}
    monkeypatch.setattr(NS, '_get', fake_get)
    monkeypatch.setattr(NS, 'HIST', str(tmp_path / 'h.jsonl'))
    NS.main(['--track', '세종시 부동산 전망'])
    import json
    rec = [json.loads(l) for l in open(NS.HIST, encoding='utf-8')][0]
    assert 'date' in calls and rec['n'] is None and rec['n_date'] == 1
