# -*- coding: utf-8 -*-
"""발행 확인 이슈 도구와 이론편 점검의 리뷰 2026-09-18 결함(백로그 19·23)을 고정한다.

블로그 초안 도구(썸네일 문구·제목에서 지역 읽기·썸네일 덮기)의 시험은 2026-11-13 도구와 함께 지웠다. close_published_issues 는
살아 있는 blog_feed 가 RSS 읽기·카테고리 이름의 정본으로 가져오므로 남는다.

깨뜨리면 빨개지는 것(각각 확인):
  - close_published_issues.match 의 예정일 조건·카테고리 조건을 빼면 → match 시험 둘
  - note_record 가 view 실패에도 --body 를 넘기면 → test_body_is_not_overwritten_when_view_fails
  - 닫기 실패 뒤 제목 복원을 빼면 → test_title_is_restored_when_close_fails
  - batch_notes.theory_claim_lines 가 SystemExit 을 삼키면 → test_sync_claim_mismatch_is_noted
픽스처: 합성 곡선·제목·RSS 항목·가짜 gh(subprocess.run 대체). 네트워크·저장소 파일 쓰기 없음.
"""
import datetime
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import batch_notes as N  # noqa: E402
import close_published_issues as C  # noqa: E402


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
    """본문을 못 읽으면 본문을 덮지 않고(점검 체크리스트 보존), 기록을 못 남겼으니 닫지도 않는다(전수리뷰 F overflow — 예전엔
    제목만 바꿔 닫아, 글 주소 기록이 없는 닫힌 이슈가 생겼고 다음 날 같은 글이 다른 알림 이슈를 또 닫을 수 있었다).

    변이(실제로 확인): main 의 `if not note_record(...): continue` 를 지우면(옛 '실패해도 닫는다') 둘째 단정(close 없음)이 빨강.
    note_record 가 view 실패에도 --body 로 덮으면 첫 단정이 빨강.
    픽스처: gh issue view 가 실패하는 가짜 gh, 열린 지역 공급 알림 이슈 하나와 그 창 안의 글 하나.
    """
    gh = _Gh(fail_view=True)
    monkeypatch.setattr(C.subprocess, 'run', gh)
    assert C.note_record(7, '기록', '제목') is False
    assert not [a for a in gh.calls if a[2] == 'edit' and '--body' in a], gh.calls
    gh = _Gh(fail_view=True)
    monkeypatch.setattr(C.subprocess, 'run', gh)
    iss = _iss(9, ZONE, D(2026, 9, 15))
    monkeypatch.setattr(C, 'fetch_posts', lambda: [dict(date=D(2026, 9, 16), cat=ZONE, title='z', url='z')])
    monkeypatch.setattr(C, 'open_issues', lambda: [iss])
    C.main([])
    assert any(a[2] == 'view' for a in gh.calls), gh.calls          # 닫으려고 했다
    assert not [a for a in gh.calls if a[2] == 'close'], '기록을 못 남겼는데 닫았다: %s' % gh.calls
    gh = _Gh()
    monkeypatch.setattr(C.subprocess, 'run', gh)
    assert C.note_record(7, '기록', '제목') is True     # 읽고 덧붙였으면 닫는다


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
    픽스처: 옛 발행 알림 워크플로(2026-11-13 삭제)가 만들던 제목의 열린 알림 이슈 둘(9/18·9/25 주간 시세)과 RSS 글 하나(9/25, 주간 카테고리).
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
    import theory_guards as T
    rows = [{'region': '대구', 'corr': 0.3, 'sudo': False}, {'region': '서울', 'corr': 0.55, 'sudo': True}]
    monkeypatch.setattr(T, 'CYCLE_SYNC', sorted(rows, key=lambda x: -x['corr']))
    out = N.theory_claim_lines()      # 3편도 이론편 점검(theory_claim_lines — 옛 sync_claim_lines 를 접었다)이 본다
    line = next((ln for ln in out if ' 사이클 3편 ' in ln), None)   # 다른 편 줄은 실데이터 상태에 따라 있을 수도 없을 수도
    assert line and line.startswith(N.ML.MARK) and '대구' in line and '검사 불가' not in line, out
    # 알림 줄은 main() 이 붙인다 — lines(adv) 는 인자만 보고 실데이터 점검을 싣지 않는다(전수리뷰 #32·#94,
    # main 쪽은 test_batch_notes.test_main_appends_theory_claim_lines 가 본다)
    assert N.lines({'sido': {'zones': [{'z': '서울', 'pbr': 1.0}]}}) == []
