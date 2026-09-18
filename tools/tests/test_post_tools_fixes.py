# -*- coding: utf-8 -*-
"""발행 도구·발행 확인 이슈의 리뷰 2026-09-18 결함(백로그 19·23)을 고정한다.

깨뜨리면 빨개지는 것(각각 확인):
  - thumb_message 의 '최근 3점' 조건을 빼면 → test_old_peak_is_not_called_all_time_high
  - _zone_of_title 을 '가장 앞' 대신 첫 매치로 되돌리거나 접미사 허용을 빼면 → title 시험 둘
  - ZONE_CAT 을 다시 손 문자열로 두면 → test_zone_category_comes_from_the_closer
  - _published_zone_posts 의 빈 목록 처리를 빼면 → test_empty_feed_is_unreadable_not_empty
  - _keep_existing_thumb 를 늘 False 로 → test_custom_thumbnail_is_kept_on_rerun
  - close_published_issues.match 의 예정일 조건·카테고리 조건을 빼면 → match 시험 둘
  - note_record 가 view 실패에도 --body 를 넘기면 → test_body_is_not_overwritten_when_view_fails
  - 닫기 실패 뒤 제목 복원을 빼면 → test_title_is_restored_when_close_fails
  - batch_notes.sync_claim_lines 가 SystemExit 을 삼키면 → test_sync_claim_mismatch_is_noted
픽스처: 합성 곡선·제목·RSS 항목·가짜 gh(subprocess.run 대체). 네트워크·저장소 파일 쓰기 없음.
"""
import datetime
import os
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import batch_notes as N  # noqa: E402
import close_published_issues as C  # noqa: E402
import make_naver_post as P  # noqa: E402


# ── 썸네일 문구 ──────────────────────────────────────────────────────────
def test_old_peak_is_not_called_all_time_high():
    vals = [100 + i for i in range(24)] + [123.5, 123.0, 122.0]   # 고점 24개월 전, 지금 −1.7%
    curve = (vals, 23, -1.7)
    first = P.thumb_message('전북', curve)[0]
    assert '역대 최고가' not in first and '고점에서' in first, first


def test_recent_peak_is_all_time_high():
    vals = list(range(100, 130))
    assert '역대 최고가' in P.thumb_message('전북', (vals, len(vals) - 1, 0.0))[0]
    assert '역대 최고가' in P.thumb_message('전북', (vals, len(vals) - 2, -0.5))[0]


# ── 제목에서 지역 읽기 ───────────────────────────────────────────────────
NAMES = {'서울', '부산', '세종', '경기', '전남광주'}


def test_two_regions_in_a_title_pick_the_first_one_every_time():
    t = '2026년 부산 아파트 공급물량 전망, 서울 아파트와 반대로 갑니다'
    assert P._zone_of_title(t, NAMES) == '부산'
    assert P._zone_of_title(t, sorted(NAMES, reverse=True)) == '부산', '순회 순서에 좌우되면 안 된다'


def test_suffixed_region_names_are_counted():
    assert P._zone_of_title('2026년 세종시 아파트 공급 전망', NAMES) == '세종'
    assert P._zone_of_title('2026년 경기도 아파트 공급 전망', NAMES) == '경기'
    assert P._zone_of_title('이번 주 아파트 시세 지도', NAMES) is None


def test_zone_category_comes_from_the_closer():
    assert P.ZONE_CAT == C.KIND_TO_CATEGORY['지역 공급']


def test_empty_feed_is_unreadable_not_empty(monkeypatch):
    monkeypatch.setattr(C, 'fetch_posts', lambda: [])
    assert P._published_zone_posts(NAMES) is None, '빈 피드로 1번 지역부터 다시 시작하면 안 된다'
    monkeypatch.setattr(C, 'fetch_posts', lambda: [
        {'cat': C.KIND_TO_CATEGORY['지역 공급'], 'url': 'u1', 'title': '2026년 서울 아파트 공급물량 전망'},
        {'cat': C.KIND_TO_CATEGORY['주간 시세'], 'url': 'u2', 'title': '이번 주 서울 아파트 시세'}])
    assert P._published_zone_posts(NAMES) == {'서울': {'u1'}}


def test_custom_thumbnail_is_kept_on_rerun(tmp_path):
    path = str(tmp_path / 'thumb-서울.png')
    open(path, 'wb').write(b'x')
    assert P._keep_existing_thumb(path, None, argv=['x'])
    assert not P._keep_existing_thumb(path, ['a', '*b*'], argv=['x']), '문구를 주면 새로 만든다'
    assert not P._keep_existing_thumb(path, None, argv=['x', '--force'])
    assert not P._keep_existing_thumb(str(tmp_path / 'none.png'), None, argv=['x'])


# ── 발행 확인 이슈 ───────────────────────────────────────────────────────
D = datetime.date
ZONE, WEEK = C.KIND_TO_CATEGORY['지역 공급'], C.KIND_TO_CATEGORY['주간 시세']


def _iss(n, cat, due, kind='지역 공급'):
    return dict(n=n, kind=kind, cat=cat, due=due, title='✍️ 오늘 발행할 글: %s (%s)' % (kind, due.isoformat()))


def test_match_needs_the_post_on_or_after_the_due_date():
    posts = [dict(date=D(2026, 9, 12), cat=WEEK, title='w1', url='w1')]
    issues = [_iss(1, WEEK, D(2026, 9, 19), '주간 시세')]
    assert C.match(posts, issues) == [], '지난주 글이 이번 주 이슈를 닫는다'
    posts.append(dict(date=D(2026, 9, 19), cat=WEEK, title='w2', url='w2'))
    assert [(i['n'], p['url']) for i, p in C.match(posts, issues)] == [(1, 'w2')]


def test_match_needs_the_same_category_and_uses_each_post_once():
    posts = [dict(date=D(2026, 9, 16), cat=WEEK, title='w', url='w'),
             dict(date=D(2026, 9, 16), cat=ZONE, title='z', url='z')]
    issues = [_iss(1, ZONE, D(2026, 9, 15)), _iss(2, ZONE, D(2026, 9, 16))]
    got = [(i['n'], p['url']) for i, p in C.match(posts, issues)]
    assert got == [(1, 'z')], got   # 주간 글은 지역 이슈를 닫지 않고, 지역 글 하나는 이슈 하나만 닫는다


class _Gh:
    def __init__(self, fail_view=False, fail_close=False):
        self.calls, self.fail_view, self.fail_close = [], fail_view, fail_close

    def __call__(self, args, **kw):
        self.calls.append(args)
        sub = args[2] if len(args) > 2 else ''
        class R:
            returncode, stdout, stderr = 0, '', ''
        r = R()
        if sub == 'view':
            if self.fail_view:
                r.returncode = 1
            else:
                r.stdout = '{"body": "체크리스트"}'
        if sub == 'close' and self.fail_close:
            r.returncode = 1
        if sub == 'list':
            r.stdout = '[]'
        return r


def test_body_is_not_overwritten_when_view_fails(monkeypatch):
    gh = _Gh(fail_view=True)
    monkeypatch.setattr(C.subprocess, 'run', gh)
    C.note_record(7, '기록', '제목')
    edits = [a for a in gh.calls if a[2] == 'edit']
    assert edits and '--body' not in edits[0] and '--title' in edits[0], edits


def test_title_is_restored_when_close_fails(monkeypatch):
    gh = _Gh(fail_close=True)
    monkeypatch.setattr(C.subprocess, 'run', gh)
    iss = _iss(9, ZONE, D(2026, 9, 15))
    post = dict(date=D(2026, 9, 16), cat=ZONE, title='z', url='z')
    monkeypatch.setattr(C, 'fetch_posts', lambda: [post])
    monkeypatch.setattr(C, 'open_issues', lambda: [iss])
    C.main([])
    titles = [a[a.index('--title') + 1] for a in gh.calls if a[2] == 'edit' and '--title' in a]
    assert titles and titles[-1] == iss['title'], '닫기 실패 뒤 제목이 원래대로 돌아오지 않는다: %s' % titles


# ── 3편 주장 점검은 게이트가 아니라 알림 ──────────────────────────────────
def test_sync_claim_mismatch_is_noted(monkeypatch):
    import make_theory_post as T
    rows = [{'region': '대구', 'corr': 0.3, 'sudo': False}, {'region': '서울', 'corr': 0.55, 'sudo': True}]
    monkeypatch.setattr(T, 'CYCLE_SYNC', sorted(rows, key=lambda x: -x['corr']))
    out = N.sync_claim_lines()
    assert out and out[0].startswith(N.ML.MARK) and '3편' in out[0], out
    assert N.lines({'sido': {'zones': [{'z': '서울', 'pbr': 1.0}]}}) == out, '알림 줄에 실려야 한다'
