# -*- coding: utf-8 -*-
"""IndexNow 는 이번 배치 커밋에서 sitemap lastmod 가 바뀐 주소만 보낸다(홈 마케팅 검수 D1, 2026-09-27).

배치는 성공한 회차마다 sitemap 32개 주소를 전부 보냈다(--sitemap). 안 바뀐 주소를 매일 보내면 '매일 전부 갱신'이라는
틀린 신호가 되고 바뀐 주소가 묻힌다. 이제 배치 커밋(HEAD)과 부모(HEAD~1)의 sitemap 을 비교해 바뀐 loc·새 loc·빠진 loc 만
보내고, 응답 코드와 보낸 개수를 배치 리포트 한 줄로 남긴다. 바뀐 것이 없으면 보내지 않는다.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - changed_locs 가 새 loc 를 빼면(`loc not in old or` 를 지우면) → 새 loc 시험 빨강(KeyError)
  - changed_locs 가 lastmod 를 보지 않고 loc 만 비교하면 → 바뀐 loc 시험 빨강
  - 빠진 loc 을 더하는 줄을 지우면 → 삭제 시험 빨강
  - changed_mode 가 바뀐 것이 없을 때도 보내면(if not urls 분기를 지우면) → 보내지 않음 시험 빨강(가짜 전송기가 불린다)
  - submit 이 HTTPError 를 성공으로 치면 → 실패 줄 시험 빨강
  - 배치가 다시 --sitemap 으로 보내거나, bat 이 커밋 블록 밖에서 보내면 → 배선 시험 빨강
  - 생성기 하나의 SITE 상수를 다른 도메인으로 바꾸면(CNAME 과 갈리면) → 도메인 일치 시험 빨강
  - 바뀐 loc 이 전부 도메인 밖일 때 '✅ 보낼 주소 없음'으로 넘기면(foreign 분기를 지우면) → 도메인 밖 시험 빨강
픽스처: 실제 sitemap 모양(여러 줄 <url> 블록과 lastmod 없이 한 줄로 적힌 /privacy/ 항목, 퍼센트 인코딩된 /zone/ 주소)을
작게 줄인 것. changed_mode 는 임시 git 저장소에 두 커밋(이전 라이브·배치 커밋)을 만들어 실제 `git show HEAD~1:sitemap.xml`
경로로 돈다. 네트워크는 가짜 전송기로 바꾼다.
"""
import io
import os
import subprocess
import sys
import urllib.error

import pytest

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'tools'))
import ping_indexnow as P  # noqa: E402
import format_batch_report as FR  # noqa: E402

S = 'https://www.agongmap.co.kr'
ZONE = S + '/zone/%EC%84%9C%EC%9A%B8/'


def sm(entries, privacy=True):
    body = ''.join('\n  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n    <changefreq>weekly</changefreq>\n  </url>'
                   % e for e in entries)
    if privacy:
        body += '\n  <url><loc>%s/privacy/</loc><changefreq>yearly</changefreq></url>' % S
    return ('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
            + body + '\n</urlset>\n')


OLD = sm([(S + '/', '2026-09-19'), (S + '/weekly/', '2026-09-19'), (ZONE, '2026-08-06'), (S + '/faq/', '2026-07-16')])


def test_reader_sees_every_entry_including_the_one_line_privacy():
    got = P.sitemap_entries(OLD)
    assert [u for u, _ in got] == [S + '/', S + '/weekly/', ZONE, S + '/faq/', S + '/privacy/']
    assert dict(got)[S + '/privacy/'] == ''


def test_unchanged_sitemap_changes_nothing():
    assert P.changed_locs(OLD, OLD) == []


def test_changed_lastmod_is_sent_and_the_rest_is_not():
    new = OLD.replace('<loc>%s/weekly/</loc>\n    <lastmod>2026-09-19' % S, '<loc>%s/weekly/</loc>\n    <lastmod>2026-09-27' % S)
    assert new != OLD
    assert P.changed_locs(OLD, new) == [S + '/weekly/']


def test_new_loc_counts_as_changed():
    new = OLD.replace('\n</urlset>', '\n  <url>\n    <loc>%s/monthly/</loc>\n    <lastmod>2026-09-01</lastmod>\n  </url>\n</urlset>' % S)
    assert P.changed_locs(OLD, new) == [S + '/monthly/']
    assert P.changed_locs('', OLD) == [u for u, _ in P.sitemap_entries(OLD)], '첫 sitemap 이면 전부 새 주소다'


def test_removed_loc_is_sent_so_engines_see_it_gone():
    new = sm([(S + '/', '2026-09-19'), (S + '/weekly/', '2026-09-19'), (S + '/faq/', '2026-07-16')])
    assert P.changed_locs(OLD, new) == [ZONE]


def _git(root, *args):
    subprocess.run(['git', '-c', 'user.name=t', '-c', 'user.email=t@example.invalid', '-c', 'commit.gpgsign=false']
                   + list(args), cwd=root, check=True, capture_output=True)


@pytest.fixture
def repo(tmp_path):
    """이전 라이브(HEAD~1)와 배치 커밋(HEAD) 두 커밋. 키 파일·CNAME 은 저장소 모양 그대로."""
    r = str(tmp_path)
    io.open(os.path.join(r, 'CNAME'), 'w', encoding='utf-8').write('www.agongmap.co.kr\n')
    io.open(os.path.join(r, '0123456789abcdef0123456789abcdef.txt'), 'w').write('0123456789abcdef0123456789abcdef')
    _git(r, 'init', '-q')
    io.open(os.path.join(r, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write(OLD)
    _git(r, 'add', '.')
    _git(r, 'commit', '-q', '-m', 'live')
    return r


def _commit(r, xml):
    io.open(os.path.join(r, 'sitemap.xml'), 'w', encoding='utf-8', newline='\n').write(xml)
    _git(r, 'commit', '-q', '--allow-empty', '-am', 'batch')


class _Resp(object):
    def __init__(self, status):
        self.status = status

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


def _opener(calls, status=200, error=None):
    def op(req, timeout=None):
        import json
        calls.append(json.loads(req.data.decode('utf-8')))
        if error is not None:
            raise error
        return _Resp(status)
    return op


def test_nothing_changed_sends_nothing(repo):
    _commit(repo, OLD)
    calls = []
    ok, line, urls = P.changed_mode('HEAD~1', root=repo, opener=_opener(calls))
    assert ok and urls == [] and calls == [], '바뀐 주소가 없는데 보냈다'
    assert line.startswith('✅') and '보낼 주소 없음' in line


def test_changed_urls_only_and_the_report_line(repo):
    new = OLD.replace('<lastmod>2026-09-19</lastmod>', '<lastmod>2026-09-27</lastmod>')
    _commit(repo, new)
    calls = []
    ok, line, urls = P.changed_mode('HEAD~1', root=repo, opener=_opener(calls, 200))
    assert urls == [S + '/', S + '/weekly/']
    assert len(calls) == 1 and calls[0]['urlList'] == urls
    assert calls[0]['host'] == 'www.agongmap.co.kr'
    assert calls[0]['keyLocation'] == 'https://www.agongmap.co.kr/0123456789abcdef0123456789abcdef.txt'
    assert ok and line == '✅ IndexNow 제출 HTTP 200 · 바뀐 주소 2개'


def test_http_failure_is_a_warning_line_with_the_code(repo):
    _commit(repo, OLD.replace('2026-07-16', '2026-09-27'))
    err = urllib.error.HTTPError(P.ENDPOINT, 403, 'Forbidden', {}, None)
    ok, line, urls = P.changed_mode('HEAD~1', root=repo, opener=_opener([], error=err))
    assert not ok and line.startswith('⚠️ IndexNow 실패') and 'HTTP 403' in line and '바뀐 주소 1개' in line
    # 받는 사람의 말로 바뀐다(내부 용어 없이)
    assert 'IndexNow' not in FR.plain(line) and '검색엔진' in FR.plain(line)


def test_accepted_202_is_success(repo):
    _commit(repo, OLD.replace('2026-07-16', '2026-09-27'))
    ok, line, _ = P.changed_mode('HEAD~1', root=repo, opener=_opener([], 202))
    assert ok and 'HTTP 202' in line


def test_missing_base_is_a_failure_not_a_full_resend(repo):
    calls = []
    ok, line, _ = P.changed_mode('HEAD~5', root=repo, opener=_opener(calls))
    assert not ok and calls == [] and 'IndexNow 실패' in line


def test_quiet_run_line_does_not_read_as_no_update():
    """'보낼 주소 없음'이 ➖ 로 시작하면 메일 제목이 '갱신 없음'으로 바뀐다 — ✅ 로 남아야 한다."""
    raw = '✅ 커밋·푸시 (3개 파일)\n✅ IndexNow 보낼 주소 없음 — sitemap lastmod 변화 없음\n'
    assert FR.headline(raw, '2026-09-27 18:00', 2).startswith('🟢')


def test_batches_send_only_changed_urls():
    y = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    code = '\n'.join(l for l in y.splitlines() if not l.strip().startswith('#'))
    assert 'ping_indexnow.py --sitemap' not in code
    push = code.index('if git pull --rebase origin main && git push; then')
    ping = code.index('python3 tools/ping_indexnow.py --changed HEAD~1')
    assert push < ping < code.index('break', ping), 'IndexNow 는 푸시가 성공한 뒤, 그 회차 안에서 보낸다'
    assert 'rep "$IXN"' in code
    bat = io.open(os.path.join(ROOT, 'tools', 'run_weekly_update.bat'), encoding='utf-8').read()
    lines = [l.strip() for l in bat.splitlines()]
    i = lines.index(r'python tools\ping_indexnow.py --changed HEAD~1')
    assert lines.index('git push origin main') < i < lines.index(') else (', i), \
        'bat 은 커밋·푸시한 블록 안에서만 보낸다 — 커밋이 없으면 HEAD~1 은 남의 변경이다'


def test_every_site_constant_and_sitemap_loc_is_the_cname_domain():
    """sitemap 을 굽는 생성기들의 SITE 상수·피드·IndexNow(CNAME)·감시가 한 도메인이다. 갈리면 IndexNow 는 host 불일치로
    전부 거절하고, 피드와 페이지가 다른 주소를 가리킨다(D1 검토)."""
    import make_sido_pages, make_indicator_pages, make_monthly_page, make_weekly_page, make_quiz_share_pages
    import check_freshness, make_feed
    want = 'https://' + io.open(os.path.join(ROOT, 'CNAME'), encoding='utf-8').read().strip()
    got = {m.__name__: m.SITE for m in (make_sido_pages, make_indicator_pages, make_monthly_page, make_weekly_page,
                                        make_quiz_share_pages, check_freshness, make_feed)}
    got['ping_indexnow'] = P.site()
    assert all(v == want for v in got.values()), '도메인이 CNAME(%s)과 다르다: %s' % (want, got)
    locs = [u for u, _ in P.sitemap_entries(io.open(os.path.join(ROOT, 'sitemap.xml'), encoding='utf-8').read())]
    assert locs and all(u.startswith(want + '/') for u in locs), [u for u in locs if not u.startswith(want + '/')]


def test_changed_locs_outside_the_domain_are_a_warning(repo):
    other = OLD.replace(S, 'https://agongmap.example')   # 생성기 SITE 상수가 CNAME 과 갈린 채 두 회차가 돈 모양
    _commit(repo, other)
    _commit(repo, other.replace('2026-07-16', '2026-09-27'))
    calls = []
    ok, line, urls = P.changed_mode('HEAD~1', root=repo, opener=_opener(calls))
    assert not ok and calls == [] and line.startswith('⚠️ IndexNow 실패') and '정식 도메인' in line, line
