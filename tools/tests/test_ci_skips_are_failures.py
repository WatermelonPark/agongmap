# -*- coding: utf-8 -*-
"""conftest 의 'CI 에서는 skip = 실패' 훅이 실제로 동작하는지 본다.

무엇을 깨뜨리면 빨개지나: tools/tests/conftest.py 의 pytest_runtest_makereport 를 지우면 → ci_fails 단정.
훅이 call 단계만 보게 되돌리면 → 픽스처 skip 시험(test_ci_fixture_skips_are_failures)이 빨개진다(확인).
pytest_collectreport(모듈 수준 건너뜀 훅)를 지우면 → test_ci_module_skips_are_failures 가 빨개진다(확인 — 기준 커밋
0649df8 에서는 두 모양 모두 CI 에서 rc=0 '1 passed, 1 skipped' 였다).
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

# 모듈 맨 위의 importorskip — 2026-09-24~26 yaml 사고를 '없으면 건너뛰기'로 고쳤다면 생겼을 모양. 수집 단계에서 끝난다.
MODULE_IMPORTORSKIP = ('import pytest\nyaml = pytest.importorskip("yaml_not_installed_xyz")\n'
                       'def test_env():\n    assert False\n')
MODULE_SKIP = 'import pytest\npytest.skip("x", allow_module_level=True)\ndef test_env():\n    assert False\n'
OK_BODY = 'def test_ok():\n    assert True\n'


def _run(tmp_path, env_extra, body=CALL_SKIP, extra=None):
    d = tmp_path / 'p'
    d.mkdir(exist_ok=True)
    shutil.copy(os.path.join(HERE, 'conftest.py'), str(d / 'conftest.py'))
    io.open(str(d / 'test_x.py'), 'w', encoding='utf-8').write(body)
    for name, text in (extra or {}).items():
        io.open(str(d / name), 'w', encoding='utf-8').write(text)
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


def test_ci_module_skips_are_failures(tmp_path):
    """모듈 수준 건너뜀(importorskip·allow_module_level)도 CI 에서는 실패다 — 나머지 시험은 그대로 돈다."""
    for body in (MODULE_IMPORTORSKIP, MODULE_SKIP):
        extra = {'test_ok.py': OK_BODY}
        rc_local, out_local = _run(tmp_path, {}, body, extra)
        assert rc_local == 0 and '1 skipped' in out_local and '1 passed' in out_local, out_local[-300:]
        rc_ci, out_ci = _run(tmp_path, {'GITHUB_ACTIONS': 'true'}, body, extra)
        assert rc_ci != 0 and '건너뜀이 실패' in out_ci and '1 passed' in out_ci, (
            '모듈 수준 skip 이 CI 에서 초록으로 남는다: %s' % out_ci[-400:])
        rc_allow, out_allow = _run(tmp_path, {'GITHUB_ACTIONS': 'true', 'AGONGMAP_ALLOW_SKIP': '1'}, body, extra)
        assert rc_allow == 0, out_allow[-300:]
