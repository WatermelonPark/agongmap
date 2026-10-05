# -*- coding: utf-8 -*-
"""발행 도구·발행 확인 이슈의 리뷰 2026-09-18 결함(백로그 19·23)을 고정한다.

깨뜨리면 빨개지는 것(각각 확인):
  - thumb_message 를 옛 규칙('하락 3% 미만이면 역대 최고가')으로 되돌리면 → test_old_peak_is_not_called_all_time_high,
    test_recent_peak_is_all_time_high(-0.5% 는 고점이 아니다 — 2026-10-05 리뷰 D4)
  - _zone_of_title 을 '가장 앞' 대신 첫 매치로 되돌리거나 접미사 허용을 빼면 → title 시험 둘
  - ZONE_CAT 을 다시 손 문자열로 두면 → test_zone_category_comes_from_the_closer
  - _published_zone_posts 의 빈 목록 처리를 빼면 → test_empty_feed_is_unreadable_not_empty
  - _keep_existing_thumb 를 늘 False 로, 또는 '--force' 로도 다시 만들게 되돌리면 → test_custom_thumbnail_is_kept_on_rerun
    (초안 덮기 --force 와 썸네일 --force-thumb 는 따로다 — 2026-10-05 리뷰 D1)
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
    assert '역대 최고가' in P.thumb_message('전북', (vals, len(vals) - 2, -0.04))[0], '표시 자릿수로 0 이면 고점이다'
    assert P.thumb_message('전북', (vals, len(vals) - 2, -0.5))[0] == '전북, 고점에서 -0.5%'


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
    assert P._keep_existing_thumb(path, None, argv=['x', '--force']), '초안 --force 가 맞춤 썸네일을 덮는다'
    assert not P._keep_existing_thumb(path, None, argv=['x', '--force-thumb'])
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


def test_post_published_a_day_early_closes_that_issue():
    """주간 시세를 예정일(금) 전날 밤에 올린 실제 운영 패턴이다. 예전 조건(발행일 >= 예정일)이면
    이 글은 어느 이슈도 닫지 못해 이슈가 한 주씩 밀렸다.
    무엇을 깨뜨리면 빨개지나: EARLY_DAYS 를 0으로 두면 첫 단정이 실패한다(실제로 확인).
    사흘 이른 글은 여전히 닫지 못한다 — 여유를 넓혀 지난 회차 글을 끌어오지 않는지 함께 본다."""
    issues = [_iss(1, WEEK, D(2026, 9, 25), '주간 시세')]
    posts = [dict(date=D(2026, 9, 24), cat=WEEK, title='w', url='w')]
    assert [(i['n'], p['url']) for i, p in C.match(posts, issues)] == [(1, 'w')]
    posts = [dict(date=D(2026, 9, 22), cat=WEEK, title='w0', url='w0')]
    assert C.match(posts, issues) == []


def test_match_needs_the_same_category_and_uses_each_post_once():
    posts = [dict(date=D(2026, 9, 16), cat=WEEK, title='w', url='w'),
             dict(date=D(2026, 9, 16), cat=ZONE, title='z', url='z')]
    issues = [_iss(1, ZONE, D(2026, 9, 15)), _iss(2, ZONE, D(2026, 9, 16))]
    got = [(i['n'], p['url']) for i, p in C.match(posts, issues)]
    # 주간 글은 지역 이슈를 닫지 않고, 지역 글 하나는 이슈 하나만 닫는다. 두 창에 걸친 글은 늦은 이슈가 가진다(리뷰 C3).
    assert got == [(2, 'z')], got


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


class _GhRepo:
    """gh 이슈 명령을 상태가 있는 가짜 저장소로 흉내 낸다 — list(--state open|closed)·view·edit·close.
    실행을 건너 닫힌 이슈와 그 본문(발행 기록)이 남는다."""

    def __init__(self, issues):
        self.iss = {n: dict(title=t, body='체크리스트', state='open') for n, t in issues}

    def __call__(self, args, **kw):
        import json

        class R:
            returncode, stdout, stderr = 0, '', ''
        r, sub = R(), args[2]
        if sub == 'list':
            st = args[args.index('--state') + 1]
            r.stdout = json.dumps([dict(number=n, title=v['title'], body=v['body'])
                                   for n, v in self.iss.items() if v['state'] == st])
        elif sub == 'view':
            r.stdout = json.dumps({'body': self.iss[int(args[3])]['body']})
        elif sub == 'edit':
            v = self.iss[int(args[3])]
            if '--title' in args:
                v['title'] = args[args.index('--title') + 1]
            if '--body' in args:
                v['body'] = args[args.index('--body') + 1]
        elif sub == 'close':
            self.iss[int(args[3])]['state'] = 'closed'
        return r


def test_one_post_never_closes_two_issues_across_runs(monkeypatch, capsys):
    """주간 시세 9/18 회차를 거르고 9/25 에 글 하나를 올렸다. 그 글은 9/25 이슈만 닫고, 거른 9/18 이슈는 열린 채 남는다 —
    오늘 실행에서도, 다음 날 실행에서도(2026-10 리뷰 C3).

    예전 match 는 열린 이슈를 오래된 것부터 돌며 '예정일 − 2일 이후의 가장 이른 글'을 줬고, '글 하나에 이슈 하나'는 한
    실행 안에서만 지켰다. 그래서 첫 실행에서 9/25 글이 9/18 이슈를 닫고, 다음 날 실행에서 같은 글이 9/25 이슈까지 닫았다
    — 거른 회차가 조용히 사라지고 글 하나가 이슈 둘을 닫는다.
    변이(실제로 확인): match 의 창 조건 `start <= p['date'] < end` 를 예전 `p['date'] >= start` 로 되돌리고 이슈를
    오래된 것부터 돌면(예전 match) 첫 실행이 9/18 을 닫아 빨개진다.
    픽스처: write-reminder 가 만드는 제목의 열린 알림 이슈 둘(9/18·9/25 주간 시세)과 RSS 글 하나(9/25, 주간 카테고리).
    gh 는 상태가 있는 가짜 저장소라 첫 실행에서 닫힌 이슈와 본문 기록이 다음 실행에 그대로 보인다.
    """
    t18 = '✍️ 오늘 발행할 글: 주간 시세 (2026-09-18)'
    t25 = '✍️ 오늘 발행할 글: 주간 시세 (2026-09-25)'
    gh = _GhRepo([(18, t18), (25, t25)])
    monkeypatch.setattr(C.subprocess, 'run', gh)
    post = dict(date=D(2026, 9, 25), cat=WEEK, title='주간 시세 9/25', url='https://blog.example/w925')
    monkeypatch.setattr(C, 'fetch_posts', lambda: [post])
    for _ in range(2):                       # 오늘 실행, 다음 날 실행
        assert C.main([]) == 0
        assert gh.iss[25]['state'] == 'closed' and post['url'] in gh.iss[25]['body']
        assert gh.iss[18]['state'] == 'open' and gh.iss[18]['title'] == t18, '거른 회차의 이슈를 다음 회차 글이 닫았다'
    assert C.closed_post_urls([dict(post, url='https://blog.example/w92')]) == set(), '주소 앞부분만 같은 글을 같은 글로 쳤다'


def test_post_recorded_in_a_closed_issue_is_not_reused(monkeypatch, capsys):
    """창이 겹치는 자리: 9/18 회차 글을 닷새 늦게 9/23(수)에 올려 9/18 이슈가 닫혔다. 9/25(금) 이슈가 생긴 날, 그 글은
    9/25 이슈의 창 [9/23, 10/2) 에도 들지만 이미 9/18 이슈를 닫은 글이라 다시 쓰지 않는다 — 9/25 이슈는 그 회차 글을
    기다린다(2026-10 리뷰 C3: 닫힌 이슈의 기록으로 실행을 건너 '글 하나에 이슈 하나'를 지킨다).

    변이(실제로 확인): main 의 `used = closed_post_urls(posts)` 를 `used = set()` 으로 바꾸면 두 번째 실행이 9/25 이슈를
    지난 회차 글로 닫아 빨개진다.
    픽스처: 첫 실행엔 9/18 이슈만 열려 있고(9/25 이슈는 금요일 아침에 생긴다), 둘째 실행 전에 9/25 이슈가 생긴다.
    RSS 글은 9/23 주간 글 하나.
    """
    t18 = '✍️ 오늘 발행할 글: 주간 시세 (2026-09-18)'
    t25 = '✍️ 오늘 발행할 글: 주간 시세 (2026-09-25)'
    gh = _GhRepo([(18, t18)])
    monkeypatch.setattr(C.subprocess, 'run', gh)
    late = dict(date=D(2026, 9, 23), cat=WEEK, title='주간 시세 9/18 (늦음)', url='https://blog.example/w918')
    monkeypatch.setattr(C, 'fetch_posts', lambda: [late])
    C.main([])
    assert gh.iss[18]['state'] == 'closed'
    gh.iss[25] = dict(title=t25, body='체크리스트', state='open')
    C.main([])
    assert gh.iss[25]['state'] == 'open' and gh.iss[25]['title'] == t25, '이미 다른 이슈를 닫은 글로 다음 회차 이슈를 닫았다'
    iss25 = [_iss(25, WEEK, D(2026, 9, 25), '주간 시세')]
    assert [(i['n'], p['url']) for i, p in C.match([late], iss25)] == [(25, late['url'])], '픽스처: 글이 9/25 창 안이어야 한다'


# ── 3편 주장 점검은 게이트가 아니라 알림 ──────────────────────────────────
def test_sync_claim_mismatch_is_noted(monkeypatch):
    import make_theory_post as T
    rows = [{'region': '대구', 'corr': 0.3, 'sudo': False}, {'region': '서울', 'corr': 0.55, 'sudo': True}]
    monkeypatch.setattr(T, 'CYCLE_SYNC', sorted(rows, key=lambda x: -x['corr']))
    out = N.sync_claim_lines()
    assert out and out[0].startswith(N.ML.MARK) and '3편' in out[0], out
    # 알림 줄은 main() 이 붙인다 — lines(adv) 는 인자만 보고 실데이터 점검을 싣지 않는다(전수리뷰 #32·#94,
    # main 쪽은 test_batch_notes.test_main_appends_sync_claim_lines 가 본다)
    assert N.lines({'sido': {'zones': [{'z': '서울', 'pbr': 1.0}]}}) == []
