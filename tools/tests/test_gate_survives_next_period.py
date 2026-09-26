# -*- coding: utf-8 -*-
"""다음 분기 데이터가 들어온 회차를 미리 돌려 본다 — 생성기와 게이트가 그 데이터에서도 통과하는가
(2026-09-26 데이터 감사).

왜 필요한가: 배치 게이트(pytest)는 커밋 잡에서 **방금 받은 새 데이터**로 돈다. 그런데 그 데이터는 게이트를
통과해야 main 에 들어오므로, main 의 pytest 는 늘 옛 데이터로만 초록이다. 새 데이터에서만 빨개지는 시험은
미리 볼 길이 없다. 실제로 test_sido_pages_main 이 착공 자름을 '2026.03' 으로 박아 두어, 2026.09 준공·착공이
들어오는 날(L=2026Q3) H=10 이 되어 게이트가 빨개질 참이었다. 생성기 다섯 개는 모두 성공하고 게이트만
빨개져 그날 데이터 커밋 전체(주간 시세·월간·지역 페이지)가 막히고, 분기마다 되풀이된다(감사 #0 — 09-24~26
yaml 로 5회 막힌 사고와 같은 모양). 그래서 배치 한 회차를 한 분기 앞당겨 흉내 낸다.

무엇을 하나(저장소에는 쓰지 않는다 — 전부 tmp_path 사본에서 한다):
  1. 저장소 파일을 tmp 로 복사한다(git 이 추적하는 파일 + 무시되지 않은 새 파일, .git 은 뺀다).
  2. 사본 data.js 를 전진시킨다.
     - 준공·착공: 다음 분기(L+1)가 끝나는 달까지. 지역마다 12개월 전 값을 되풀이하므로 전국=Σ시도,
       수도권=서울+경기+인천 이 그대로다(원천이 새 분기를 낸 날의 모양).
     - 주간 시세: 한 주(시도·시군구·서울 구 모두). 월간 시세: 한 달. 보관 길이는 배치 상한(CONF) 그대로.
  3. 배치처럼 ADV.sido·occupancy 를 다시 굽고(update_adv_data --seed-sido — --update 와 같은 sido_zones.calc·
     supply_rows), split_data 를 돈다.
  4. 커밋 잡이 게이트 앞에서 돌리는 생성기(update-cloud.yml 에서 읽는다)를 사본에서 돌린다 — 전부 rc=0.
  5. 사본에서 pytest 게이트를 그대로 돈다(이 파일만 뺀다) — 전부 통과.

사본에는 .git 이 없어 git 이력을 읽는 시험(sw.js 버전)은 건너뛴다. 그래서 안쪽 게이트에만 AGONGMAP_ALLOW_SKIP=1 을
준다. 그 시험들은 바깥 게이트에서 제대로 돈다. 사본 안의 git 이 저장소를 찾아 올라가지 않게 GIT_CEILING_DIRECTORIES 를 둔다.

⚠️ 배치 커밋 잡(update-cloud.yml 의 commit 잡, GITHUB_JOB=commit) 안에서는 이 전진 시험을 돌리지 않는다.
   이건 **다음 분기** 문제를 미리 보는 시험이라, 배치 게이트에서 빨개지면 오늘 받은 멀쩡한 데이터까지 막는다 —
   미래의 정지를 오늘로 당기는 거짓 차단이 된다(이 감사가 없애려는 바로 그 모양). 개발 세션·로컬의 pytest 에서는
   돌고 빨개진다(시험·생성기를 고치는 사람이 먼저 본다). 배치 밖 CI 에서 매일 보고 싶으면 watchdog.yml 처럼
   데이터 커밋을 막지 않는 워크플로에서 이 파일만 따로 돌리면 된다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - test_sido_pages_main 의 착공 자름을 옛 '2026.03'·'H=11' 로 되돌리면 안쪽 게이트가
    'assert 10 == (12 - 1)' 로 빨개져 이 시험이 빨개진다(감사 #0 재현).
  - 전진 단계(_advance_supply)를 건너뛰면 픽스처 자기 확인('L 이 한 분기 나아가지 않았다')이 빨개진다.
  - commit_job_generators 가 빈 목록을 돌려주면 파서 자기 확인 시험이 빨개진다.
  - 배치 잡 가드(_in_batch_gate)를 지우면 test_forward_check_never_gates_the_batch_commit 이 빨개진다.
픽스처: 저장소의 실제 data.js 를 한 분기(준공·착공)·한 주·한 달 앞당긴 것. 실행 시간 약 30초(안쪽 게이트가 대부분).
"""
import datetime
import io
import json
import os
import re
import shutil
import subprocess
import sys
import warnings

import pytest

TOOLS = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
ROOT = os.path.dirname(TOOLS)
sys.path.insert(0, TOOLS)

import sido_zones as SZ  # noqa: E402
import update_adv_data as U  # noqa: E402  data.js 읽기·쓰기와 보관 상한(CONF)의 정본

YML = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
GATE = 'python3 -m pytest tools/tests'
BATCH_JOB = 'commit'      # update-cloud.yml 의 커밋 잡 키 = 그 잡의 GITHUB_JOB. 파서와 가드가 같이 쓴다
SELF = os.path.basename(os.path.abspath(__file__))


def _in_batch_gate():
    """배치 커밋 잡의 게이트 안에서 도는가 — 거기서는 전진 시험이 오늘 데이터를 막지 않게 빠진다."""
    return bool(os.environ.get('GITHUB_ACTIONS')) and os.environ.get('GITHUB_JOB') == BATCH_JOB


def commit_job_generators():
    """update-cloud.yml 커밋 잡이 게이트 **앞**에서 부르는 tools/*.py — 손으로 적지 않는다."""
    text = io.open(YML, encoding='utf-8').read()
    job = text[text.index('\n  %s:\n' % BATCH_JOB):]
    out = []
    for line in job.splitlines():
        s = line.strip()
        if s.startswith('#'):
            continue
        if GATE in s:
            return out
        m = re.search(r'python3? tools/([a-z_]+)\.py', s)
        if m and m.group(1) not in out:
            out.append(m.group(1))
    raise AssertionError('update-cloud.yml 커밋 잡에서 pytest 게이트를 찾지 못했다')


def _copy_repo(dst):
    """추적 파일 + 무시되지 않은 새 파일만 복사한다(.gitignore 된 벌크 원본·캐시·다른 워크트리는 뺀다)."""
    try:
        out = subprocess.run(['git', 'ls-files', '-z', '--cached', '--others', '--exclude-standard'],
                             cwd=ROOT, capture_output=True, timeout=60)
        files = [f for f in out.stdout.decode('utf-8', 'replace').split('\0') if f] if out.returncode == 0 else []
    except Exception:
        files = []
    if not files:   # git 이 없는 환경 — 무거운 로컬 전용 폴더만 빼고 통째로
        shutil.copytree(ROOT, dst, ignore=shutil.ignore_patterns(
            '.git', '.claude', '__pycache__', 'drafts', 'logs', 'cache', '.pytest_cache'))
        return
    for f in files:
        src = os.path.join(ROOT, f)
        if not os.path.isfile(src):
            continue   # 작업 트리에서 지운 추적 파일
        d = os.path.join(dst, f)
        os.makedirs(os.path.dirname(d), exist_ok=True)
        shutil.copy2(src, d)


def _next_month(ym):
    y, m = int(ym[:4]), int(ym[5:7])
    y, m = (y + 1, 1) if m == 12 else (y, m + 1)
    return y, m


def _advance_supply(stats):
    """준공·착공을 다음 분기(L+1) 끝 달까지 채운다. 새 L 인덱스를 돌려준다."""
    L = SZ.last_full_quarter(stats, '준공')
    y, q = SZ.qparts(L + 1)
    target = '%d.%02d' % (y, q * 3)
    for key in ('준공', '착공'):
        s = stats[key]
        n = len(s['dates'])
        for v in s['series'].values():
            v.extend([None] * (n - len(v)))      # 계열 길이를 날짜에 맞춘 뒤 붙인다
        while s['dates'][-1][:7] < target:
            s['dates'].append('%d.%02d' % _next_month(s['dates'][-1]))
            for v in s['series'].values():
                v.append(v[-12])                 # 같은 달 작년 값 — 지역 합 항등식이 그대로다
    return L + 1


def _advance_rows(block, step, keep):
    rows = block['rows']
    new = json.loads(json.dumps(rows[-1]))
    new['p'] = step(rows[-1]['p'])
    block['rows'] = (rows + [new])[-keep:]


def _next_week(p):
    return (datetime.date(*(int(x) for x in p.split('-'))) + datetime.timedelta(days=7)).isoformat()


def _next_month_dash(p):
    return '%d-%02d' % _next_month(p)


def _advance_prices(adv):
    for key, step, hist in (('weekly', _next_week, 'weeks_hist'), ('monthly', _next_month_dash, 'months_hist')):
        blk = adv[key]
        _advance_rows(blk, step, U.CONF[key][hist])
        for sub in ('sgg', 'seoul'):
            if (blk.get(sub) or {}).get('rows'):
                _advance_rows(blk[sub], step, U.CONF[key]['sgg_hist'])
    return adv['weekly']['rows'][-1]['p'], adv['monthly']['rows'][-1]['p']


def _run(args, cwd, env, timeout=300):
    p = subprocess.run([sys.executable, '-B'] + args, cwd=cwd, env=env, capture_output=True,
                       timeout=timeout, encoding='utf-8', errors='replace')
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def _tail(out, n=40):
    lines = out.splitlines()
    keep = [ln for ln in lines if ln.startswith(('FAILED', 'ERROR', 'E   '))][:30]
    return '\n'.join(keep + ['...'] + lines[-n:])


def test_parser_reads_the_commit_job_generators():
    """목록 파생이 헛돌면 아래 시험이 생성기를 하나도 안 돌리고 초록이 된다 — 빈 목록을 막는다.

    변이: commit_job_generators 가 [] 를 돌려주면 빨개진다(확인). 커밋 잡 키가 바뀌어 BATCH_JOB 과
          어긋나면 index 에서 ValueError 로 빨개진다 — 그때는 배치 가드도 함께 고쳐야 한다.
    픽스처: 저장소의 실제 update-cloud.yml.
    """
    gens = commit_job_generators()
    assert len(gens) >= 5 and 'make_sido_pages' in gens and 'refresh_cycle_data' in gens, gens
    assert 'split_data' not in gens and 'update_adv_data' not in gens, '수집 잡의 도구가 섞였다: %s' % gens


def test_forward_check_never_gates_the_batch_commit(tmp_path, monkeypatch):
    """배치 커밋 잡(GITHUB_JOB=commit)에서는 전진 시험이 아무것도 하지 않고 경고만 남긴다.

    변이: test_generators_and_gate_pass_on_next_quarter_data 첫머리의 `if _in_batch_gate():` 가드를 지우면
          사본 복사(_copy_repo)가 불려 빨개진다(실제로 확인).
    픽스처: 커밋 잡의 환경 변수 두 개(GITHUB_ACTIONS·GITHUB_JOB). 사본 복사는 불리면 바로 실패하게 바꿔 둔다.
    """
    monkeypatch.setenv('GITHUB_ACTIONS', 'true')
    monkeypatch.setenv('GITHUB_JOB', BATCH_JOB)

    def boom(dst):
        raise AssertionError('배치 게이트 안에서 전진 시험이 돌았다 — 다음 분기 문제로 오늘 데이터 커밋을 막는다')
    monkeypatch.setattr(sys.modules[__name__], '_copy_repo', boom)
    with pytest.warns(UserWarning):
        test_generators_and_gate_pass_on_next_quarter_data(tmp_path, monkeypatch)


def test_generators_and_gate_pass_on_next_quarter_data(tmp_path, monkeypatch):
    if _in_batch_gate():
        warnings.warn('배치 커밋 잡에서는 다음 분기 전진 시험을 돌리지 않는다(오늘 데이터 커밋을 막지 않게) — '
                      '개발 세션의 pytest 에서 돈다')
        return
    repo = tmp_path / 'repo'
    _copy_repo(str(repo))
    data = str(repo / 'data.js')
    monkeypatch.setattr(U, 'DATA', data)          # U 의 읽기·쓰기를 사본으로 돌린다

    stats = U.read_current_stats()
    old_L = SZ.last_full_quarter(stats, '준공')
    new_L = _advance_supply(stats)
    U.write_stats(stats)
    _, _, _, adv = U.read_current_adv()
    old_w, old_m = adv['weekly']['rows'][-1]['p'], adv['monthly']['rows'][-1]['p']
    new_w, new_m = _advance_prices(adv)
    U.write_adv(adv)

    env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1', GIT_CEILING_DIRECTORIES=str(tmp_path))
    for step in (['tools/update_adv_data.py', '--seed-sido'], ['tools/split_data.py']):
        rc, out = _run(step, str(repo), env)
        assert rc == 0, '%s 실패(rc=%d)\n%s' % (' '.join(step), rc, out[-3000:])

    # 픽스처 자기 확인 — 전진이 실제로 일어났고 점수가 그 데이터로 다시 구워졌다.
    _, _, _, adv2 = U.read_current_adv()
    assert adv2['sido']['L'] == SZ.qkey(new_L) and new_L == old_L + 1, \
        'L 이 한 분기 나아가지 않았다: %s → %s' % (SZ.qkey(old_L), adv2['sido']['L'])
    assert adv2['sido']['H'] == SZ.LEAD_Q, '전진한 사본이 H≠lead 다 — 준공·착공을 같은 달까지 채우지 못했다'
    assert new_w > old_w and new_m > old_m

    bad = []
    for g in commit_job_generators():
        rc, out = _run(['tools/%s.py' % g], str(repo), env)
        if rc != 0:
            bad.append('%s rc=%d\n%s' % (g, rc, out[-2000:]))
    assert not bad, '다음 분기 데이터에서 생성기가 실패한다 — 그날 배치가 커밋을 멈춘다:\n' + '\n'.join(bad)

    # 생성기가 사본을 구웠는지(저장소가 아니라) — 새 분기·새 주차가 페이지에 실렸다.
    def page(*p):
        return io.open(os.path.join(str(repo), *p), encoding='utf-8').read()
    assert '%s(실적)' % SZ.qkey(new_L) in page('monthly', 'index.html'), '/monthly/ 가 새 분기로 구워지지 않았다'
    y, m, d = (int(x) for x in new_w.split('-'))
    assert '%d/%d 조사' % (m, d) in page('weekly', 'index.html'), '/weekly/ 가 새 주차로 구워지지 않았다'
    stale = [z['z'] for z in adv2['sido']['zones']
             if SZ.quarter_text(SZ.qkey(new_L)) not in page('zone', z['z'], 'index.html')]
    assert not stale, '/zone/ 이 새 분기로 구워지지 않았다: %s' % stale

    genv = dict(env, AGONGMAP_ALLOW_SKIP='1')
    rc, out = _run(['-m', 'pytest', 'tools/tests', '-q', '-p', 'no:cacheprovider',
                    '--ignore', 'tools/tests/' + SELF, '--basetemp', str(tmp_path / 'inner')],
                   str(repo), genv, timeout=600)
    assert rc == 0, ('다음 분기(준공·착공 %s, 주간 %s, 월간 %s) 데이터에서 게이트가 빨개진다 — 그날 배치가 '
                     '데이터 커밋 전체를 멈춘다. 실데이터의 날짜·값을 박은 시험인지 볼 것:\n%s'
                     % (SZ.qkey(new_L), new_w, new_m, _tail(out)))
