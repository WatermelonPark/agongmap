# -*- coding: utf-8 -*-
"""도구가 **실제로 실행되는지** 본다. import만으로는 부족하다.

2026-09-12 실사고. 리뷰가 `make_naver_post`에 `from make_theory_post import …`를
넣었는데, `make_theory_post`는 이미 `make_naver_post`를 import하고 있었다(CSS·복사
UI 재사용). 순환 참조가 생겨 `python tools/make_naver_post.py`가 ImportError로
죽었다 — 금요일 주간 글과 화요일 지역 편을 만드는 바로 그 도구다.

**테스트 209개가 전부 통과했다.** pytest는 모듈을 import만 하는데, 순환 참조는
한쪽이 `__main__`으로 먼저 올라올 때만 터진다. import 경로에서는 이미 올라온
모듈을 재사용해 우연히 넘어간다. 그래서 초록불이 도구의 고장을 덮었다.

이 저장소가 반복해서 당한 '안 도는 방어선'의 새 변종이다. 여기서는 **별도
프로세스로 스크립트를 띄워** 그 경로를 실제로 지난다. 원천 호출이 필요한 도구는
`--help`처럼 부작용 없는 경로로 띄운다.
"""
import os
import subprocess
import sys

ROOT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
TOOLS = os.path.join(ROOT, 'tools')

# 스크립트로 직접 띄웠을 때 import 단계를 지나야 하는 도구들.
# 실제 작업까지 시키지 않는다 — 없는 인자를 줘서 argparse/사용법에서 멈추게 하거나,
# 모듈 최상단만 지나면 되는 것은 그대로 둔다.
SCRIPTS = ['make_naver_post.py', 'make_theory_post.py', 'make_sido_pages.py',
           'make_indicator_pages.py', 'make_monthly_page.py', 'split_data.py',
           'check_freshness.py', 'update_adv_data.py', 'format_batch_report.py',
           'refresh_cycle_data.py', 'merge_regions.py', 'naver_serp.py']


def _import_stage(name):
    """그 스크립트를 __main__ 으로 올려 **모듈 최상단까지만** 실행한다.

    ⚠️ 2026-09-17 정정. 예전엔 runpy로 스크립트를 통째로 돌렸다. "최상단까지만"이라고
    적어 놓고 실제로는 `if __name__ == '__main__':` 아래 본체까지 돌아서, pytest를 한 번
    돌릴 때마다 make_sido_pages·split_data 등이 **진짜 저장소에** zone/*·data.js·sitemap
    등 28개 파일을 다시 썼다(내용은 같고 줄바꿈만 달라 매번 미커밋 28건). 공유 작업
    트리가 늘 더러워 rebase가 막히고, PM이 "주인 없는 미커밋 28개"로 추적해야 했다.
    make_naver_post는 초안까지 만들었다.

    이제 소스를 읽어 `__main__` 가드 블록만 떼고 나머지 최상단을 `__name__ == '__main__'`
    으로 실행한다. 순환 참조는 최상단 import에서 터지므로 잡으려던 것은 그대로 잡는다
    (변이: make_naver_post 최상단에 `import make_theory_post`를 넣으면 빨개진다 — 확인함).
    """
    code = (
        'import ast, sys\n'
        'sys.path.insert(0, %r)\n'
        'path = %r\n'
        'tree = ast.parse(open(path, encoding="utf-8").read(), path)\n'
        'def is_guard(n):\n'
        '    return (isinstance(n, ast.If) and isinstance(n.test, ast.Compare)\n'
        '            and isinstance(n.test.left, ast.Name) and n.test.left.id == "__name__")\n'
        'tree.body = [n for n in tree.body if not is_guard(n)]\n'
        'sys.argv = [path]\n'
        'try:\n'
        '    exec(compile(tree, path, "exec"), {"__name__": "__main__", "__file__": path})\n'
        'except ImportError as e:\n'
        '    print("IMPORTERROR", e); sys.exit(9)\n'
        'except SystemExit:\n'
        '    pass\n'
        'except Exception:\n'
        '    pass\n'
        % (TOOLS, os.path.join(TOOLS, name))
    )
    return subprocess.run([sys.executable, '-c', code], capture_output=True,
                          text=True, encoding='utf-8', errors='replace', timeout=120)


def test_running_the_tools_does_not_touch_the_repo():
    """이 시험 파일이 저장소 파일을 다시 쓰지 않는다(위 정정의 재발 방지).
    변이: _import_stage를 runpy.run_path(..., run_name='__main__')로 되돌리면 빨개진다."""
    watch = [os.path.join(ROOT, p) for p in ('data.js', 'sitemap.xml',
                                            os.path.join('zone', 'index.html'))]
    before = [os.path.getmtime(p) for p in watch]
    for name in ('make_sido_pages.py', 'split_data.py', 'make_naver_post.py'):
        _import_stage(name)
    assert [os.path.getmtime(p) for p in watch] == before


def test_no_tool_dies_on_import_when_run_as_a_script():
    broken = []
    for name in SCRIPTS:
        if not os.path.exists(os.path.join(TOOLS, name)):
            continue
        p = _import_stage(name)
        if p.returncode == 9 or 'IMPORTERROR' in (p.stdout or ''):
            broken.append('%s: %s' % (name, (p.stdout or '').strip()[:120]))
    assert not broken, (
        '스크립트로 띄우면 import 단계에서 죽는 도구가 있다(순환 참조 등).\n  '
        + '\n  '.join(broken))


def test_the_two_publishing_tools_have_one_way_dependency():
    """의존 방향이 한 쪽만 남아야 한다. 양방향이면 위 시험이 터지기 전에 여기서 걸린다."""
    a = open(os.path.join(TOOLS, 'make_naver_post.py'), encoding='utf-8').read()
    b = open(os.path.join(TOOLS, 'make_theory_post.py'), encoding='utf-8').read()
    a_uses_b = 'import make_theory_post' in a
    b_uses_a = 'import make_naver_post' in b
    assert not (a_uses_b and b_uses_a), (
        '두 발행 도구가 서로를 import한다 — 스크립트로 띄우면 ImportError로 죽는다. '
        '정본은 make_naver_post 에 두고 make_theory_post 가 받아 쓴다.')
