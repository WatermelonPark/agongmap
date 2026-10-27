# -*- coding: utf-8 -*-
"""로컬 배치와 클라우드 배치가 같은 생성기를 같은 순서로 돌리고 같은 산출물을 커밋하는지 고정한다(백로그 11).

2026-09-16 리뷰 10번: 로컬 러너(run_weekly_update.bat)가 make_monthly_page 를 부르지 않았고 git add 목록에
cycle 이 없었다. 그래서 로컬 배치가 고친 cycle/index.html 이 공유 작업 트리에 미커밋으로 남아 다른 세션의
푸시를 막았고, 로컬이 돌 때 /monthly/ 는 갱신되지 않았다. 두 파일이 같은 대상을 따로 적어 두어 생긴 일이다.

무엇을 깨뜨리면 빨개지나:
  - bat 에서 생성기 한 줄을 지우거나(예: make_monthly_page) 순서를 바꾸면 → 순서 시험
  - bat 의 git add / git diff 목록에서 대상 하나를 빼면(예: cycle) → 대상 시험
  - pytest 게이트를 커밋 뒤로 옮기거나 지우면 → 순서 시험(게이트도 한 단계로 센다)
  - 파서가 망가져 빈 목록을 읽으면 → 파서 자기 확인 시험(빈 목록끼리는 같아서 조용히 통과한다)
픽스처: 저장소의 실제 두 파일을 읽는다.
"""
import io
import os
import re

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
BAT = os.path.join(ROOT, 'tools', 'run_weekly_update.bat')

# 클라우드에만 있는 보고용 도구 — 산출물을 만들지 않는다. 늘어나면 여기에 이유와 함께 적는다.
REPORT_ONLY = {'month_lag', 'batch_notes', 'format_batch_report'}


def _cloud_steps():
    out = []
    for line in io.open(YML, encoding='utf-8').read().splitlines():
        if line.strip().startswith('#'):
            continue
        if re.search(r'python3? -m pytest tools/tests', line):
            out.append('pytest')
            continue
        m = re.search(r'python3? tools/([a-z_]+)\.py', line)
        if m and m.group(1) not in REPORT_ONLY:
            out.append(m.group(1))
    return _dedupe(out)


def _bat_steps():
    out = []
    for line in io.open(BAT, encoding='utf-8').read().splitlines():
        t = line.strip()
        if t.lower().startswith('rem') or t.startswith('::'):
            continue
        if re.match(r'python -m pytest tools\\tests', t):
            out.append('pytest')
            continue
        m = re.match(r'python tools\\([a-z_]+)\.py', t)
        if m:
            out.append(m.group(1))
    return _dedupe(out)


def _dedupe(seq):
    seen, out = set(), []
    for x in seq:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out


def _cloud_targets():
    m = re.search(r'TARGETS="([^"]+)"', io.open(YML, encoding='utf-8').read())
    assert m, 'update-cloud.yml 에서 TARGETS 를 찾지 못했다'
    return set(m.group(1).split())


def _bat_list(cmd):
    lines = [l.strip() for l in io.open(BAT, encoding='utf-8').read().splitlines() if l.strip().startswith(cmd + ' ')]
    assert len(lines) == 1, 'bat 에서 "%s" 줄이 %d개다' % (cmd, len(lines))
    rest = lines[0][len(cmd):].split('>>')[0].split()   # 로그 리다이렉션은 대상이 아니다
    if rest and rest[0] == '--':
        rest = rest[1:]
    return {t.replace('\\', '/') for t in rest}


def test_parsers_actually_read_the_steps():
    for name, steps in (('클라우드', _cloud_steps()), ('로컬', _bat_steps())):
        for must in ('update_adv_data', 'blog_feed', 'split_data', 'make_sido_pages', 'make_monthly_page',
                     'make_home_summary', 'refresh_cycle_data', 'make_feed', 'make_llms_txt', 'pytest'):
            assert must in steps, '%s 배치에서 %s 를 읽지 못했다 — 파서가 깨졌거나 단계가 빠졌다: %s' % (name, must, steps)


def test_local_runs_the_same_generators_in_the_same_order():
    cloud, local = _cloud_steps(), _bat_steps()
    assert local == cloud, '로컬 배치 순서가 클라우드와 다르다\n  클라우드: %s\n  로컬:     %s' % (cloud, local)


def test_local_commits_the_same_targets():
    cloud = _cloud_targets()
    # index.html(홈 요약 표식 구간)·blog_latest.json(최신 주간 해설 글)은 2026-09-27 홈 마케팅 검수 B3·B5 에서 더했다.
    # feed.xml(새 소식 RSS)은 2026-09-27 홈 마케팅 검수 D1, llms.txt(AI 검색 요약)는 2026-09-28 D5 에서 더했다.
    assert {'monthly', 'cycle', 'weekly', 'index.html', 'tools/data/blog_latest.json', 'feed.xml', 'llms.txt'} <= cloud, \
        '클라우드 TARGETS 를 제대로 읽지 못했다: %s' % sorted(cloud)
    # 커밋은 경로 지정(남이 스테이징한 파일을 쓸어 담지 않게), 실패 복원도 같은 목록(리뷰 09-18 백로그 22).
    for cmd in ('git add', 'git diff --quiet',
                'git commit -m "stats: weekly auto-update (KOSIS, local)"',
                'git restore --staged --worktree'):
        local = _bat_list(cmd)
        assert local == cloud, '로컬 "%s" 대상이 클라우드 TARGETS 와 다르다 — 빠짐 %s, 더함 %s' % (
            cmd, sorted(cloud - local), sorted(local - cloud))


PUB = os.path.join(ROOT, '.github', 'workflows', 'publish-content.yml')


def _pub_text():
    return io.open(PUB, encoding='utf-8').read()


def test_publish_workflow_runs_on_content_and_gates_before_commit():
    """원고 발행 워크플로(대표 결정 10-26 ①)가 검사 → 생성 → 게이트 → 커밋 순서를 지킨다.

    무엇을 바꾸면 빨개지나: pytest 게이트를 커밋 뒤로 옮기거나 지우면, 생성기 하나를 빼면,
    content/** 트리거를 바꾸면. 발행은 사람 손을 거치지 않고 라이브로 가므로 게이트가 유일한 방어선이다.
    픽스처: 저장소의 실제 워크플로 파일.
    """
    t = _pub_text()
    assert re.search(r'paths:\s*\n\s*-\s*[\'"]?content/\*\*', t), 'content/** 푸시에 반응하지 않는다'
    for gen in ('tools/make_content_pages.py', 'tools/content_tables.py', 'tools/content_md.py'):
        assert gen in t, '%s 를 고쳐도 페이지를 다시 굽지 않는다 — 옛 페이지가 라이브에 남는다' % gen
    # 순서는 **스텝 구간**에서만 센다. 트리거(paths)에도 생성기 파일 이름이 적혀 있어, 파일 전체에서
    # 처음 나오는 자리로 세면 트리거 줄이 먼저 걸려 순서를 오판한다(2026-10-27 이 시험이 그렇게 틀렸다).
    steps = t[t.index('    steps:'):]
    order = ['tools/make_city_moveins.py', 'tools/content_check.py', 'tools/make_content_pages.py',
             'tools/make_feed.py', 'tools/make_llms_txt.py', '-m pytest', 'git commit']
    at = [steps.find(s) for s in order]
    for s, i in zip(order, at):
        assert i >= 0, '발행 워크플로에 %r 가 없다' % s
    assert at == sorted(at), '발행 순서가 어긋났다 — 검사·생성·게이트가 모두 커밋 앞이어야 한다: %s' % (
        [s for _, s in sorted(zip(at, order))])


def test_publish_workflow_does_not_commit_the_manuscripts():
    """발행 워크플로는 content/ 를 커밋하지 않는다 — 자기 커밋이 자기를 다시 부르지 않게.

    무엇을 바꾸면 빨개지나: 커밋 대상 목록에 content 를 넣으면(푸시 → 발행 → 푸시로 런이 계속 돈다).
    """
    t = _pub_text()
    m = re.search(r'^\s*TARGETS="([^"]+)"', t, re.M)
    assert m, '발행 워크플로에서 커밋 대상 목록을 읽지 못했다'
    targets = set(m.group(1).split())
    assert 'content' not in targets and not any(x.startswith('content/') for x in targets), \
        '발행 워크플로가 원고를 커밋한다 — 런이 스스로를 다시 부른다: %s' % sorted(targets)
    # 글 페이지와 그 글을 가리키는 목록·피드·색인은 함께 나가야 한다. 하나라도 빠지면 발행된 글이
    # 사이트맵이나 피드에 없는 상태로 라이브가 된다.
    assert {'city', 'gtx', 'danji', 'column', 'feed.xml', 'llms.txt', 'llms-full.txt',
            'sitemap.xml', 'index.html'} <= targets, '발행 대상이 빠졌다: %s' % sorted(targets)
    # 그 대상은 매일 배치도 같은 이름으로 커밋한다 — 두 배치가 다른 경로에 같은 산출물을 두면
    # 한쪽이 커밋한 파일이 다른 쪽에서 미커밋으로 남는다(백로그 11 과 같은 사고).
    assert targets <= _cloud_targets(), '발행 대상이 매일 배치 TARGETS 밖이다: %s' % sorted(
        targets - _cloud_targets())


def test_publish_workflow_commits_nothing_that_triggers_itself():
    """발행이 커밋하는 파일은 발행을 부르는 경로에 없다 — 런이 자기를 영원히 다시 부르지 않게.

    무엇을 바꾸면 빨개지나: 커밋 대상과 트리거 경로가 겹치게 하면. 2026-10-27 새 도시를 받아 넣는 스텝을
    더하면서 tools/data/city_moveins.json 이 양쪽에 들어갈 참이었다 — 그러면 발행이 그 파일을 커밋하고,
    그 커밋이 다시 발행을 불러 런이 끝없이 돈다(GitHub 은 봇 커밋도 push 로 센다).
    픽스처: 저장소의 발행 워크플로. 트리거 목록과 TARGETS 를 글자로 읽어 맞댄다.
    """
    t = _pub_text()
    on = t[t.index('on:'):t.index('concurrency:')]
    paths = re.findall(r"^\s*-\s*'([^']+)'", on, re.M)
    assert paths, '트리거 경로를 읽지 못했다'
    m = re.search(r'^\s*TARGETS="([^"]+)"', t, re.M)
    assert m, '커밋 대상을 읽지 못했다'
    for tgt in m.group(1).split():
        for p in paths:
            pre = p[:-3] if p.endswith('/**') else p
            assert not (tgt == pre or tgt.startswith(pre + '/') or pre.startswith(tgt + '/') or pre == tgt), \
                '커밋 대상 %r 이 트리거 경로 %r 과 겹친다 — 발행이 자기를 다시 부른다' % (tgt, p)
