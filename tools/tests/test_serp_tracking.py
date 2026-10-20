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


POSTS = [dict(date='2026-09-01', cat=ZONE, title='2026년 부산 아파트 공급물량 전망, 지금은 남는데 3년 뒤엔 모자랍니다'),
         dict(date='2026-09-29', cat=ZONE, title='2026 세종시 부동산 전망, 전세는 6주째 오르고 공급물량은 빠듯합니다'),
         dict(date='2026-10-17', cat=ZONE, title='2027년 광주·전남 아파트 공급물량 전망, 내년이 바닥입니다'),
         dict(date='2026-09-27', cat='주간 아파트 시세', title='[한국부동산원] 주간 아파트가격 동향')]


def test_track_adds_demand_and_own_terms():
    """'{지역} 적정 공급량'은 지역 편 소제목과 같은 검색 표기(SEARCH_NAME)로 잰다(전수리뷰 BL1-16). 키 표기('세종'·'전남광주')는
    도입일부터 8주(LEGACY_KEY_KW_UNTIL)까지만 함께 잰다 — 두 갈래를 today 로 고정해 본다(실제 오늘과 무관하게 초록).
    변이(확인): 적정 공급량 검색어를 nm(키)으로 되돌리면 검색 표기 단정이, legacy 조건을 지우면(늘 키 표기도 잼) 기한 뒤 단정이
    빨개진다.
    픽스처: 실제 발행 제목 형태(A안 부산, B안 세종시, 광주·전남 편)와 주간 글 하나."""
    until = NS.LEGACY_KEY_KW_UNTIL
    kws = NS.track_keywords(POSTS, today=until)
    assert '2026년 부산 아파트 공급물량' in kws               # 옛 추이를 잇는다
    for kw in ('부산 적정 공급량', '부산 부동산 전망', '세종시 적정 공급량', '세종시 부동산 전망', '광주·전남 적정 공급량',
               '세종 적정 공급량', '전남광주 적정 공급량'):
        assert kw in kws, kw
    assert not any('한국부동산원' in k for k in kws)
    after = NS.track_keywords(POSTS, today=until + __import__('datetime').timedelta(days=1))
    assert '세종시 적정 공급량' in after and '광주·전남 적정 공급량' in after and '부산 적정 공급량' in after
    assert '세종 적정 공급량' not in after and '전남광주 적정 공급량' not in after, after


def test_zone_posts_outside_the_rss_window_stay_tracked(tmp_path):
    """RSS 창 밖으로 밀린 지역 편도 캐시(gitignore)에서 이어 붙여 계속 잰다 — blog_feed.merge_city 와 같은 규칙(창 안인데
    RSS 에 없는 저장 글은 지워진 글이라 버린다)(전수리뷰 BL1-16).
    변이(확인): track_keywords 가 캐시를 읽지 않으면(merge_zone_posts 대신 posts 그대로) 둘째 실행에서 부산 검색어가 빠져
    빨개지고, merge_zone_posts 의 `< floor` 조건을 지우면 창 안에서 지워진 글이 남아 빨개진다.
    픽스처: 첫 실행 RSS 에 부산·세종 편, 둘째 실행 RSS 는 창이 밀려 세종(10-01 이후 글)만 — 부산 편은 창 밖(09-01).
    창 안(09-30)의 저장 글 '삭제된 글'은 둘째 RSS 에 없으니 버린다."""
    cache = str(tmp_path / 'zone.json')
    NS.track_keywords(POSTS[:2] + [dict(date='2026-09-30', cat=ZONE, title='2026년 대구 아파트 공급물량 전망, 지운 글',
                                        url='u-del')], today=NS.LEGACY_KEY_KW_UNTIL, cache=cache)
    rss2 = [dict(date='2026-09-29', cat=ZONE, title=POSTS[1]['title'], url=''),
            dict(date='2026-10-01', cat='주간 아파트 시세', title='[한국부동산원] 주간 아파트가격 동향', url='w')]
    kws = NS.track_keywords(rss2, today=NS.LEGACY_KEY_KW_UNTIL, cache=cache)
    assert '부산 적정 공급량' in kws and '2026년 부산 아파트 공급물량' in kws, kws
    assert '세종시 적정 공급량' in kws
    assert not any('대구' in k for k in kws), kws


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


def test_failed_date_rank_is_counted_not_recorded_as_absent(monkeypatch, tmp_path):
    """최신순 조회가 실패하면 실패로 세고(종료 코드 1) n_date 를 기록에서 뺀다 — '100 밖'(None)으로 적으면 최신순 추이가
    오염된다(2026-10 리뷰 C5: 예전엔 오류를 버리고 n_date=None 으로 적었다). 정확도순 자리는 받았으니 남긴다.

    변이(실제로 확인): main 의 `hd, derr = rank_on(...)` 뒤 실패 분기를 지우고 예전처럼 `rec['n_date'] = …` 만 두면
    rc 와 'n_date' 단정이 빨개진다.
    픽스처: 네이버 블로그 검색 API 를 흉내 낸 _get — 정확도순은 우리 글을 3번째로 내고, 최신순(sort=date)은 매번
    예외(재시도까지 실패한 상태). 이력 파일은 tmp.
    """
    def fake_get(kind, q, display=10, sort='sim'):
        if sort == 'date':
            raise OSError('timed out')
        items = [{'link': 'https://blog.example/x', 'title': 'a'}] * 2 + [
            {'link': 'https://blog.naver.com/startupbd/1', 'title': 't'}]
        return {'items': items, 'total': 3}
    monkeypatch.setattr(NS, '_get', fake_get)
    monkeypatch.setattr(NS, 'HIST', str(tmp_path / 'h.jsonl'))
    rc = NS.main(['--track', '세종시 부동산 전망'])
    import json
    rec = [json.loads(l) for l in open(NS.HIST, encoding='utf-8')][0]
    assert rc == 1, '최신순 조회 실패를 세지 않았다'
    assert rec['n'] == 3 and 'n_date' not in rec, rec
