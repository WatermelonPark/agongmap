# -*- coding: utf-8 -*-
"""conftest 의 'CI 에서는 skip = 실패' 훅이 실제로 동작하는지 본다.

무엇을 깨뜨리면 빨개지나: tools/tests/conftest.py 의 pytest_runtest_makereport 를 지우면 → ci_fails 단정.
훅이 call 단계만 보게 되돌리면 → 픽스처 skip 시험(test_ci_fixture_skips_are_failures)이 빨개진다(확인).
픽스처: 임시 폴더에 skip 하는 시험 하나를 만들고, 이 conftest 를 복사한 뒤 pytest 를 두 번 띄운다
(GITHUB_ACTIONS 없이 / 있이).
"""
import io
import os
import shutil
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))


CALL_SKIP = 'import pytest\ndef test_env():\n    pytest.skip("node 없음")\n'
# /monthly/ 파일이 없으면 픽스처에서 건너뛰는 test_monthly_page 의 실제 모양 — skip 이 setup 단계에서 난다.
FIXTURE_SKIP = ('import pytest\n@pytest.fixture\ndef html():\n    pytest.skip("생성 전")\n'
                'def test_env(html):\n    assert html\n')


def _run(tmp_path, env_extra, body=CALL_SKIP):
    d = tmp_path / 'p'
    d.mkdir(exist_ok=True)
    shutil.copy(os.path.join(HERE, 'conftest.py'), str(d / 'conftest.py'))
    io.open(str(d / 'test_x.py'), 'w', encoding='utf-8').write(body)
    env = {k: v for k, v in os.environ.items() if k not in ('GITHUB_ACTIONS', 'AGONGMAP_ALLOW_SKIP')}
    env.update(env_extra)
    p = subprocess.run([sys.executable, '-m', 'pytest', '-q', '-p', 'no:cacheprovider', str(d)],
                       capture_output=True, text=True, encoding='utf-8', errors='replace', env=env, timeout=120)
    return p.returncode, (p.stdout or '') + (p.stderr or '')


def test_ci_skips_are_failures(tmp_path):
    rc_local, out_local = _run(tmp_path, {})
    assert rc_local == 0 and '1 skipped' in out_local, '로컬에서는 skip 이 그대로여야 한다: %s' % out_local[-300:]
    rc_ci, out_ci = _run(tmp_path, {'GITHUB_ACTIONS': 'true'})
    assert rc_ci != 0 and '1 failed' in out_ci and '건너뜀이 실패' in out_ci, (
        'CI 에서 skip 이 실패로 바뀌지 않는다: %s' % out_ci[-400:])
    rc_allow, out_allow = _run(tmp_path, {'GITHUB_ACTIONS': 'true', 'AGONGMAP_ALLOW_SKIP': '1'})
    assert rc_allow == 0 and '1 skipped' in out_allow, 'AGONGMAP_ALLOW_SKIP 이 skip 을 되살리지 않는다'


def test_ci_fixture_skips_are_failures(tmp_path):
    rc_local, out_local = _run(tmp_path, {}, FIXTURE_SKIP)
    assert rc_local == 0 and '1 skipped' in out_local, out_local[-300:]
    rc_ci, out_ci = _run(tmp_path, {'GITHUB_ACTIONS': 'true'}, FIXTURE_SKIP)
    assert rc_ci != 0 and '건너뜀이 실패' in out_ci, '픽스처(setup) 단계 skip 이 CI 에서 초록으로 남는다: %s' % out_ci[-400:]
