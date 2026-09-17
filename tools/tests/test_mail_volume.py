# -*- coding: utf-8 -*-
"""알림 메일의 양과 제목 (2026-09-17 대표 요청).

받은편지함을 실제로 세어 보니 2주에 43통, 하루 3통꼴이었다. 원인은 코드가 아니라 전제였다:
'멘션이 메일 스위치'라고 믿고 정상 회차의 멘션만 뗐는데, 한 번이라도 멘션되거나 담당자로
지정된 사람은 그 이슈의 구독자가 되어 **이후 코멘트를 전부 메일로 받는다.** 그래서 메일을
줄이는 길은 코멘트를 줄이는 것뿐이다. 여기서 잠그는 것은 세 가지다.

  1. 정상 회차는 이슈에 쓰지 않는다(코멘트 = 메일).
  2. 메일 제목만 보고 판단할 수 있다 — 무슨 일인가 · 사이트는 괜찮은가 · 할 일이 있는가.
  3. 담당자 지정과 '코멘트 달고 닫기'를 되살리지 않는다(한 통씩 더 간다).

⚠️ 워크플로는 실행해 볼 수 없어 원문을 본다. 문구가 아니라 **구조**(무엇 뒤에 무엇이 오는가)를
   단정해, 주석을 고쳤다고 깨지지 않게 한다.
"""
import datetime
import io
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import close_published_issues as C  # noqa: E402
import format_batch_report as F  # noqa: E402

ROOT = os.path.join(os.path.dirname(__file__), '..', '..')
KST = '2026-09-17 18:33'
OK = ('✅ 러너 3/3 clean · 채택 주간 2026-09-14 / 월간 2026-08 / 공급 2026Q2\n'
      '✅ 커밋·푸시 (5개 파일)\n')


def _wf(name):
    return io.open(os.path.join(ROOT, '.github', 'workflows', name), encoding='utf-8').read()


def _code(text):
    """주석을 뺀 실행 줄만. 주석에 적은 경고문이 단정을 통과시키면 안 된다."""
    return '\n'.join(ln for ln in text.splitlines() if not ln.lstrip().startswith('#'))


# ── 1. 정상 회차는 메일이 없다 ─────────────────────────────────────────────

def test_meta_tells_the_workflow_whether_to_write(tmp_path):
    rep = tmp_path / 'r.txt'
    meta = tmp_path / 'm.txt'
    for raw, weekday, want in ((OK, 2, '0'), (OK, 0, '1'),
                               (OK + '❌ 테스트 실패 — 배포 중단\n', 2, '1')):
        rep.write_text(raw, encoding='utf-8')
        F.main([str(rep), '--kst', KST, '--run-url', 'u', '--owner', 'O',
                '--weekday', str(weekday), '--meta', str(meta)])
        lines = meta.read_text(encoding='utf-8').splitlines()
        assert lines[0] == want, (weekday, raw[-20:])
        assert len(lines) == 2 and lines[1].strip(), '둘째 줄에 제목이 있어야 한다'


def test_workflow_comments_only_after_checking_the_send_flag():
    code = _code(_wf('update-cloud.yml'))
    i_flag = code.find('if [ "$SEND" != "1" ]')
    i_comment = code.find('gh issue comment')
    assert i_flag >= 0, '메일 여부를 보지 않고 이슈에 쓴다'
    assert 0 <= i_flag < i_comment, '코멘트가 메일 여부 검사보다 앞에 있다'
    assert code.count('gh issue comment') == 1, '검사를 거치지 않는 코멘트 경로가 생겼다'
    gate = code[i_flag:i_comment]
    assert re.search(r'\bexit 0\b', gate), '정상 회차에서 빠져나가지 않는다'


def test_fallback_report_still_sends_mail():
    """본문 생성이 죽은 회차는 그 자체가 이상이다 — 조용히 넘어가면 안 된다."""
    code = _code(_wf('update-cloud.yml'))
    assert re.search(r"printf '1\\n[^']+' > _report\.meta", code)


# ── 2. 제목만 보고 판단한다 ────────────────────────────────────────────────

def test_every_headline_answers_what_site_and_todo():
    cases = ((OK, 0), (OK, 2), (OK + '❌ 테스트 실패 — x\n', 3),
             (OK + '⚠️ 공유카드 실패 — x\n', 3),
             (OK + 'ℹ️ 월간 뒤처짐 4개월 · 가 2026.04 · 최신 2026.08\n', 3))
    for raw, wd in cases:
        h = F.headline(raw, KST, wd)
        assert h[0] in '🔴🟡🟢', h
        assert '하실 일' in h, '할 일이 있는지가 제목에 없다: %s' % h
        assert '9/17' in h
        assert len(h) <= 60, '제목이 길면 받은편지함 목록에서 잘린다: %s' % h
        for jargon in ('clean', '러너', 'rc=', '배치', 'KOSIS'):
            assert jargon not in h, '내부 용어가 제목에 샜다: %s' % h


def test_failure_headline_says_the_site_is_fine():
    h = F.headline(OK + '❌ 테스트 실패 — x\n', KST, 3)
    assert h.startswith('🔴') and '사이트는 정상' in h


def test_headline_severity_follows_the_body():
    """제목과 본문이 서로 다른 말을 하면 안 된다."""
    for raw, wd in ((OK + '❌ x\n', 3), (OK + '⚠️ x\n', 3), (OK, 0)):
        body, _ = F.build(raw, KST, 'u', 'O', wd)
        h = F.headline(raw, KST, wd)
        assert ('### ✅' in body) == h.startswith('🟢'), (h, body[:40])


def test_workflow_renames_the_issue_before_commenting():
    code = _code(_wf('update-cloud.yml'))
    i_title = code.find('gh issue edit "$N" --title "$HEAD"')
    assert 0 <= i_title < code.find('gh issue comment'), '제목을 바꾸기 전에 코멘트를 단다'
    assert '--label "$LABEL"' in code, '제목이 바뀌므로 이슈는 라벨로 찾아야 한다'


def test_failure_mail_subjects_are_readable():
    """'Run failed: <워크플로 이름>' 메일 — 이름이 곧 제목이다."""
    for name in ('update-cloud.yml', 'watchdog.yml'):
        first = _wf(name).splitlines()[0]
        assert first.startswith('name: ') and '하실 일' in first, first


# ── 3. 한 통씩 더 가는 것들을 되살리지 않는다 ──────────────────────────────

def test_no_workflow_assigns_the_owner():
    for name in ('update-cloud.yml', 'write-reminder.yml'):
        code = _code(_wf(name))
        assert '--assignee' not in code and '--add-assignee' not in code, name


def test_closer_closes_without_a_comment():
    src = _code(io.open(os.path.join(ROOT, 'tools', 'close_published_issues.py'),
                        encoding='utf-8').read())
    assert "'--comment'" not in src, '코멘트를 달고 닫으면 메일이 두 통 간다'
    assert src.find('note_record(') < src.find("'issue', 'close'"), '제목을 바꾸기 전에 닫는다'


def test_reminder_title_round_trips_through_the_closer():
    wf = _wf('write-reminder.yml')
    m = re.search(r'--title "([^"]+)"', wf)
    title = (m.group(1).replace('${{ steps.plan.outputs.kind }}', '지역 공급')
             .replace('${{ steps.plan.outputs.date }}', '2026-09-15'))
    assert C.parse_title(title) == (datetime.date(2026, 9, 15), '지역 공급'), title
    assert '오늘 발행할 글' in title


def test_closer_still_reads_titles_made_before_the_change():
    assert C.parse_title('[발행] 2026-09-15 지역 공급') == (datetime.date(2026, 9, 15), '지역 공급')
    for other in ('🟢 주간 확인 · 데이터 정상 · 하실 일 없음 (9/21)',
                  C.done_title('지역 공급', datetime.date(2026, 9, 15)), ''):
        assert C.parse_title(other) is None, other
