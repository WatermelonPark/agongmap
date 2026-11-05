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
import shutil
import subprocess

import pytest

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
    카드 생성을 게이트 뒤로 되돌리면, content/** 트리거를 바꾸면. 발행은 사람 손을 거치지 않고 라이브로
    가므로 게이트가 유일한 방어선이다.
    픽스처: 저장소의 실제 워크플로 파일.

    ⚠️ 카드 생성(make_content_cards)이 게이트 **앞**이어야 하는 이유: 게이트의 시험 하나가 '모든 글이 제
       카드를 가진다'를 본다. 카드를 뒤에 구우면 새 글이 올라온 회차마다 그 시험이 아직 없는 카드를 보고
       빨개져 발행이 멈춘다(2026-10-29 세 런 연속). 산출물을 재는 시험은 그 산출물을 만드는 단계 뒤에 온다.
    """
    t = _pub_text()
    assert re.search(r'paths:\s*\n\s*-\s*[\'"]?content/\*\*', t), 'content/** 푸시에 반응하지 않는다'
    for gen in ('tools/make_content_pages.py', 'tools/content_tables.py', 'tools/content_md.py'):
        assert gen in t, '%s 를 고쳐도 페이지를 다시 굽지 않는다 — 옛 페이지가 라이브에 남는다' % gen
    # 순서는 **스텝 구간**에서만 센다. 트리거(paths)에도 생성기 파일 이름이 적혀 있어, 파일 전체에서
    # 처음 나오는 자리로 세면 트리거 줄이 먼저 걸려 순서를 오판한다(2026-10-27 이 시험이 그렇게 틀렸다).
    steps = t[t.index('    steps:'):]
    order = ['tools/make_city_moveins.py', 'tools/content_check.py', 'tools/make_content_pages.py',
             'tools/make_feed.py', 'tools/make_llms_txt.py', 'tools/make_content_cards.py',
             '-m pytest', 'git commit']
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


def _publish_commit_script():
    """발행 워크플로의 '변경 있으면 커밋·푸시' 스텝에서 `git commit` 까지의 셸 조각을 그대로 떼어 온다.

    글자로 베끼지 않고 **워크플로 파일에서 읽는다** — 그래야 워크플로를 고치면 시험도 같이 움직인다.
    push 루프는 네트워크를 타므로 커밋 줄에서 자른다.
    """
    t = _pub_text()
    i = t.index('- name: 변경 있으면 커밋·푸시')
    run = t.index('run: |', i) + len('run: |')
    lines = []
    for ln in t[run:].splitlines()[1:]:
        if ln.strip() and not ln.startswith('          '):
            break                                  # 스텝 밖으로 나갔다
        lines.append(ln[10:] if len(ln) > 10 else '')
        if ln.strip().startswith('git commit'):
            break
    assert any(l.strip().startswith('git commit') for l in lines), '커밋 줄을 찾지 못했다'
    return '\n'.join(lines) + '\n'


def test_publish_commit_keeps_the_lists_feed_and_sitemap(tmp_path):
    """원고가 하나 늘면 **목록·허브·피드·사이트맵까지** 한 커밋에 들어간다 — 새 글 파일만 가지 않는다.

    왜: 되돌리기(`git checkout -- .`)가 `git add` 보다 앞에 있던 판은, TARGETS 안팎을 가리지 않고 추적
    파일의 모든 변경을 되돌렸다. 그래서 새 글이 올라온 회차에 untracked 인 글 페이지·카드만 커밋되고
    /danji/ 목록과 /reports/ 허브에는 그 글이 없었다(2026-10-30 런 320be1e3, 총괄 지적). 주소로 직접
    가면 200 이라 더 늦게 드러난다.

    무엇을 바꾸면 빨개지나(둘 다 확인): `git add -- $HAVE` 를 다시 되돌리기 뒤로 옮기면, TARGETS 에서
      목록·피드·사이트맵을 빼면.
    ⚠️ LEFT 검사를 다시 넓혀도(`grep -v '^??'`) 이 시험은 통과한다 — add 가 앞서는 한 `git checkout` 은
       인덱스 기준 복원이라 스테이징된 변경을 지우지 못한다. 그 변이는 경고 문구만 틀리게 만든다.
    픽스처: 임시 git 저장소에 추적 파일(목록·허브·피드·사이트맵·홈)과 대상 밖 파일 하나를 커밋해 두고,
      그 전부를 고친 뒤 새 글 디렉터리를 untracked 로 둔다 — 발행 생성기가 한 회차에 만드는 상태 그대로다.
    """
    bash = shutil.which('bash')
    if not bash:
        pytest.skip('bash 가 없다 — 워크플로 조각을 돌려 볼 수 없다(CI 러너에는 있다)')
    d = tmp_path / 'repo'
    (d / 'danji' / 'new-post').mkdir(parents=True)
    (d / 'reports').mkdir()
    tracked = {'danji/index.html': '목록 옛 판', 'reports/index.html': '허브 옛 판',
               'feed.xml': '피드 옛 판', 'sitemap.xml': '사이트맵 옛 판', 'index.html': '홈 옛 판',
               'tools/keep_me.txt': '대상 밖 옛 판'}
    (d / 'tools').mkdir()
    for rel, text in tracked.items():
        (d / rel).write_text(text, encoding='utf-8')

    def git(*a):
        return subprocess.run(['git'] + list(a), cwd=str(d), capture_output=True, text=True,
                              encoding='utf-8', errors='replace')

    git('init', '-q', '-b', 'main')
    git('config', 'user.email', 't@t'), git('config', 'user.name', 't')
    git('add', '-A'), git('commit', '-qm', 'base')
    # 발행 생성기가 한 회차에 만드는 상태: 목록·허브·피드·사이트맵·홈이 바뀌고, 새 글은 untracked 다.
    for rel in tracked:
        (d / rel).write_text('새 판', encoding='utf-8')
    (d / 'danji' / 'new-post' / 'index.html').write_text('새 글', encoding='utf-8')

    p = subprocess.run([bash, '-c', _publish_commit_script()], cwd=str(d), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=120)
    assert p.returncode == 0, p.stdout + p.stderr
    files = set(git('show', '--name-only', '--format=', 'HEAD').stdout.split())
    for rel in ('danji/index.html', 'reports/index.html', 'feed.xml', 'sitemap.xml', 'index.html'):
        assert rel in files, '%s 가 발행 커밋에 없다 — 새 글이 목록·피드에 나타나지 않는다: %s' % (rel, sorted(files))
    assert 'danji/new-post/index.html' in files, '새 글 페이지가 커밋되지 않았다'
    # 대상 밖은 커밋하지도, 작업 트리에 남기지도 않는다(rebase 가 거부하지 않게).
    assert 'tools/keep_me.txt' not in files, '커밋 대상 밖 파일이 실렸다'
    assert (d / 'tools' / 'keep_me.txt').read_text(encoding='utf-8') == '대상 밖 옛 판', \
        '대상 밖 변경이 되돌려지지 않았다'


def _pub_steps():
    """발행 워크플로의 steps 구간에서 **게이트 앞까지** 도는 python 도구를 순서대로 읽는다.

    트리거(paths)에도 생성기 파일 이름이 적혀 있으므로 steps 구간으로 잘라서 센다.
    """
    t = _pub_text()
    steps = t[t.index('    steps:'):]
    out = []
    for line in steps[:steps.index('-m pytest')].splitlines():
        s = line.strip()
        if s.startswith('#'):
            continue
        m = re.search(r'python3? tools/([a-z_]+)\.py', s)
        if m:
            out.append(m.group(1))
    return _dedupe(out)


# 발행이 돌리지 않는 배치 생성기와 그 이유. 발행은 숫자를 수집하지 않는다(대표 결정 2026-10-26 ①) —
# 늘어나면 여기에 이유와 함께 적는다. 이유 없이 빼면 아래 시험이 빨개진다.
PUBLISH_SKIP = {
    'update_adv_data': 'API 키로 원천을 받는다 — 숫자 갱신은 매일 배치의 몫이다',
    'blog_feed': '네트워크 곁가지 — 발행에는 필요하지 않다',
    'make_weekly_share': '/weekly/ og 카드는 그 주 데이터로 그린다 — 원고가 올라와도 달라지지 않는다',
    'make_monthly_share': '/monthly/ og 카드는 그 달 데이터로 그린다 — 원고가 올라와도 달라지지 않는다',
}

# 생성기가 쓰는 산출물의 커밋 대상 이름(매일 배치 TARGETS 와 같은 이름). 굽는 것은 커밋해야 한다.
PUBLISH_OUTPUTS = {
    'split_data': ('data-core.js', 'data-rest.json', 'data-trend.json', 'data-sgg.json', 'data-size.json'),
    'make_sido_pages': ('zone',),
    'make_indicator_pages': ('moveins', 'jeonse-ratio'),
    'make_monthly_page': ('monthly',),
    'make_weekly_page': ('weekly',),
    'make_home_summary': ('index.html', 'tools/data/.home_stamp'),
    'refresh_cycle_data': ('cycle',),
    'make_content_pages': ('city', 'gtx', 'danji', 'column', 'reports'),
    'make_feed': ('feed.xml',),
    'make_llms_txt': ('llms.txt', 'llms-full.txt'),
    'make_city_moveins': ('tools/data/city_moveins.json',),
    'make_content_cards': ('share',),
}


def test_the_publish_step_parser_actually_reads_the_steps():
    """파서 자기 확인 — 빈 목록끼리는 같아서 아래 시험이 조용히 통과한다."""
    steps = _pub_steps()
    for must in ('make_city_moveins', 'make_content_pages', 'make_feed', 'make_llms_txt'):
        assert must in steps, '발행 워크플로에서 %s 를 읽지 못했다 — 파서가 깨졌다: %s' % (must, steps)
    assert 'make_content_cards' in steps, '카드 생성이 게이트 앞에서 사라졌다'


def test_publish_bakes_everything_the_gate_measures():
    """발행 워크플로는 게이트 앞에서 매일 배치와 **같은 생성기**를 돌리고, 구운 것을 커밋한다.

    왜: 발행의 게이트는 전체 시험이다. 그 시험 몇은 커밋된 생성 페이지를 읽는다. 그런데 발행이 글
    페이지만 구우면, 생성기만 고치고 산출물을 싣지 않은 병합(PR 은 산출물을 싣지 않는다 — CLAUDE.md)
    뒤에 커밋본이 묵은 채로 게이트에 걸려 **발행이 통째로 막힌다**. 2026-10-30 PR #113 이 공용 푸터·글자
    하한·날짜 정본을 생성기에 넣고 병합된 뒤, 발행 런 40990048414 가 그렇게 3 failed 로 섰다. 배치와 같은
    것을 다 구우면 그 회차는 막히는 대신 다시 구워 커밋한다.

    무엇을 바꾸면 빨개지나(셋 다 확인): 생성기 한 줄을 지우면, 이유 없이 PUBLISH_SKIP 에 넣으면,
      굽는 산출물을 TARGETS 에서 빼면.
    픽스처: 저장소의 실제 두 워크플로 파일. 배치 목록에서 가져오므로 배치에 생성기가 늘면 발행도 따라야 한다.
    """
    batch = _cloud_steps()
    batch_pre = batch[:batch.index('pytest')]
    want = [g for g in batch_pre if g not in PUBLISH_SKIP]
    pub = _pub_steps()
    missing = [g for g in want if g not in pub]
    assert not missing, (
        '발행이 게이트 앞에서 굽지 않는 배치 생성기가 있다 — 그 산출물이 묵으면 발행이 막힌다: %s'
        % missing)
    # 순서도 배치와 같아야 한다. 뒤 생성기가 앞 생성기의 산출물을 읽는다(예: make_content_pages 가
    # make_city_moveins 의 도시 자료를, make_feed 가 글 페이지를).
    order = [g for g in pub if g in want]
    assert order == want, '발행 생성기 순서가 배치와 다르다\n  배치: %s\n  발행: %s' % (want, order)

    m = re.search(r'^\s*TARGETS="([^"]+)"', _pub_text(), re.M)
    assert m, '발행 워크플로에서 커밋 대상 목록을 읽지 못했다'
    targets = set(m.group(1).split())
    for gen in pub:
        for out in PUBLISH_OUTPUTS.get(gen, ()):
            assert out in targets, (
                '%s 를 돌리는데 그 산출물 %r 이 커밋 대상에 없다 — 되돌려지고 다음 회차에 또 같은 일이 된다'
                % (gen, out))


def _publish_push_step():
    """'변경 있으면 커밋·푸시' 스텝을 **푸시 루프까지 통째로** 떼어 온다(위 함수는 커밋 줄에서 자른다)."""
    t = _pub_text()
    i = t.index('- name: 변경 있으면 커밋·푸시')
    run = t.index('run: |', i) + len('run: |')
    lines = []
    for ln in t[run:].splitlines()[1:]:
        if ln.strip() and not ln.startswith('          '):
            break
        lines.append(ln[10:] if len(ln) > 10 else '')
    assert any('push 재시도' in l for l in lines), '푸시 루프를 찾지 못했다'
    return '\n'.join(lines) + '\n'


def test_publish_forwards_to_the_remote_tip_before_baking():
    """발행은 **굽기 전에** 원격 끝으로 전진한다 — 옛 바탕에서 구워 생기는 충돌을 없앤다.

    왜: 런은 자기 트리거 커밋을 체크아웃한다. 앞 런이 그 뒤에 산출물을 커밋해 두면 이 런은 옛 바탕에서
    같은 생성 파일을 다시 써서 rebase 가 충돌한다. 2026-11-02 단지 11편(런 41459123576)과 같은 날
    도시 편(런 41457156426)이 그렇게 유실됐다 — 둘 다 앞 런의 커밋과 부딪혔다.

    무엇을 바꾸면 빨개지나: 전진 단계를 지우면, 생성기 뒤로 옮기면(그러면 옛 바탕에서 구운 것이 남는다).
    픽스처: 저장소의 실제 워크플로. 전진이 첫 생성기보다 앞인지 스텝 구간에서 센다.
    """
    t = _pub_text()
    steps = t[t.index('    steps:'):]
    fwd = steps.find('git reset --hard FETCH_HEAD')
    assert fwd >= 0, '굽기 전에 원격 끝으로 전진하지 않는다 — 옛 바탕에서 구워 rebase 가 충돌한다'
    assert 'git fetch origin main' in steps[:fwd], '전진 전에 원격을 받지 않는다'
    first_gen = min(i for i in (steps.find('python tools/make_city_moveins.py'),
                                steps.find('python tools/split_data.py')) if i >= 0)
    assert fwd < first_gen, '전진이 생성기보다 뒤다 — 옛 바탕에서 구운 산출물이 그대로 남는다'


def test_publish_stops_instead_of_repeating_the_same_rebase_conflict(tmp_path):
    """rebase 가 충돌하면 **한 번에 멈추고** 무엇이 걸렸는지 적는다 — 같은 충돌을 세 번 되풀이하지 않는다.

    왜: 충돌 파일은 전부 생성 산출물이다. 바탕이 그대로인 채 다시 걸면 같은 충돌이 그대로 나오므로
    재시도는 쓸모가 없다. 그런데도 세 번 되풀이한 끝에 "push 3회 모두 실패"로 끝나, 그 회차 발행이
    유실됐다(2026-11-02 단지 11편 런 41459123576). 지금은 충돌을 push 거부와 가려, 충돌 파일 이름과
    풀는 방법(수동 실행)을 적고 바로 멈춘다.

    무엇을 바꾸면 빨개지나(둘 다 확인): 충돌 가름을 지워 다시 세 번 되풀이하게 하면, 충돌 파일 이름을
      빼면.
    픽스처: 임시 bare 저장소를 원격으로 두고 **진짜 충돌을 만든다** — 다른 런이 같은 생성 파일을 먼저
      고쳐 올린 상태. 네트워크 없이 로컬 경로 원격으로 돈다.
    """
    bash = shutil.which('bash')
    if not bash:
        pytest.skip('bash 가 없다 — 워크플로 조각을 돌려 볼 수 없다(CI 러너에는 있다)')

    def git(cwd, *a):
        return subprocess.run(['git'] + list(a), cwd=str(cwd), capture_output=True, text=True,
                              encoding='utf-8', errors='replace')

    bare = tmp_path / 'remote.git'
    subprocess.run(['git', 'init', '-q', '--bare', '-b', 'main', str(bare)], check=True)

    # ① 원격에 바탕을 만든다.
    seed = tmp_path / 'seed'
    seed.mkdir()
    for rel in ('index.html', 'reports/index.html', 'feed.xml', 'sitemap.xml', 'danji/index.html'):
        (seed / rel).parent.mkdir(parents=True, exist_ok=True)
        (seed / rel).write_text('바탕\n', encoding='utf-8')
    git(seed, 'init', '-q', '-b', 'main')
    git(seed, 'config', 'user.email', 't@t'), git(seed, 'config', 'user.name', 't')
    git(seed, 'add', '-A'), git(seed, 'commit', '-qm', 'base')
    git(seed, 'remote', 'add', 'origin', str(bare)), git(seed, 'push', '-q', 'origin', 'main')

    # ② 다른 런이 같은 파일을 먼저 고쳐 올렸다.
    other = tmp_path / 'other'
    git(tmp_path, 'clone', '-q', str(bare), str(other))
    git(other, 'config', 'user.email', 'o@o'), git(other, 'config', 'user.name', 'stats-bot')
    for rel in ('index.html', 'reports/index.html'):
        (other / rel).write_text('앞 런이 쓴 판\n', encoding='utf-8')
    git(other, 'commit', '-qam', '원고 발행: 콘텐츠 페이지 재생성'), git(other, 'push', '-q')

    # ③ 이 런은 **옛 바탕**에서 같은 파일을 다르게 구웠다 — 전진 단계가 없을 때의 상태 그대로다.
    mine = tmp_path / 'mine'
    git(tmp_path, 'clone', '-q', str(bare), str(mine))
    git(mine, 'reset', '-q', '--hard', 'HEAD~1')
    git(mine, 'config', 'user.email', 'm@m'), git(mine, 'config', 'user.name', 't')
    for rel in ('index.html', 'reports/index.html'):
        (mine / rel).write_text('이 런이 쓴 판\n', encoding='utf-8')

    p = subprocess.run([bash, '-c', _publish_push_step()], cwd=str(mine), capture_output=True,
                       text=True, encoding='utf-8', errors='replace', timeout=180)
    out = p.stdout + p.stderr
    assert p.returncode != 0, '충돌인데 성공으로 끝났다:\n' + out
    errs = [l for l in out.splitlines() if '::error::' in l]
    assert errs, '무엇이 잘못됐는지 적지 않는다:\n' + out
    # ⚠️ 'index.html' 을 출력 전체에서 찾으면 안 된다 — git 이 찍는 'CONFLICT ... in index.html' 이 걸려,
    #    우리 알림에서 파일 이름을 빼도 통과한다(처음 쓴 판이 그랬다). ::error:: 줄에서만 센다.
    assert any('index.html' in l for l in errs), \
        '알림에 충돌 파일 이름이 없다 — 어느 산출물이 부딪혔는지 알 수 없다:\n' + '\n'.join(errs)
    assert any('수동 실행' in l for l in errs), '푸는 방법을 적지 않는다:\n' + '\n'.join(errs)
    assert 'push 재시도 2' not in out, \
        '같은 충돌을 되풀이한다 — 바탕이 그대로면 결과도 같다:\n' + out
    # rebase 를 물고 끝내지 않는다(다음 명령이 "rebase in progress" 로 막히지 않게).
    assert not (mine / '.git' / 'rebase-merge').exists() and not (mine / '.git' / 'rebase-apply').exists(), \
        'rebase 를 물고 끝났다'


def test_the_batch_draws_the_share_cards_before_the_gate():
    """배치(클라우드·로컬 둘 다)는 **게이트 앞**에서 공유 카드를 굽는다.

    왜: 게이트의 test_card_text_matches_the_manuscript_title 은 카드에 박힌 글자와 원고 제목을 맞댄다.
    제목에는 자리표가 들어갈 수 있어(예: '적정의 {{v:share:평택:2028}}') 새 데이터가 들어오면 제목의
    숫자가 바뀌고, 카드도 함께 다시 그려져야 한다. 카드를 게이트 뒤에 두었더니 **데이터가 움직인 날마다**
    옛 카드와 새 제목이 어긋나 커밋이 막혔다 — 2026-11-05 런 42053599155(카드 257% 대 제목 256%)로
    그날 데이터 갱신이 세 번 연속 멈췄다. 산출물을 재는 시험은 그 산출물을 만드는 단계 뒤에 와야 한다.

    무엇을 바꾸면 빨개지나: 어느 한쪽에서든 카드 생성을 pytest 뒤로 되돌리면.
    픽스처: 저장소의 실제 두 배치 파일. 파서가 읽은 단계 순서로 센다(글자 위치가 아니라 단계 목록).
    """
    for name, steps in (('클라우드', _cloud_steps()), ('로컬', _bat_steps())):
        assert 'pytest' in steps and 'make_content_cards' in steps, \
            '%s 배치에서 게이트나 카드 단계를 읽지 못했다: %s' % (name, steps)
        assert steps.index('make_content_cards') < steps.index('pytest'), \
            '%s 배치가 게이트 뒤에서 카드를 굽는다 — 데이터가 움직인 날 커밋이 막힌다: %s' % (name, steps)
        # 주간·월간 og 카드도 같은 자리에 둔다(그 둘은 데이터로만 그린다).
        for g in ('make_weekly_share', 'make_monthly_share'):
            assert steps.index(g) < steps.index('pytest'), '%s 배치의 %s 가 게이트 뒤다' % (name, g)
