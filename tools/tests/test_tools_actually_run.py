# -*- coding: utf-8 -*-
"""도구가 **실제로 실행되는지** 본다. import만으로는 부족하다.

2026-09-12 실사고. 리뷰가 `make_naver_post`에 `from make_theory_post import …`를
넣었는데, `make_theory_post`는 이미 `make_naver_post`를 import하고 있었다(CSS·복사
UI 재사용). 순환 참조가 생겨 `python tools/make_naver_post.py`가 ImportError로
죽었다 — 금요일 주간 글과 화요일 지역 편을 만드는 바로 그 도구다.

**테스트 209개가 전부 통과했다.** pytest는 모듈을 import만 하는데, 순환 참조는
한쪽이 `__main__`으로 먼저 올라올 때만 터진다. import 경로에서는 이미 올라온
모듈을 재사용해 우연히 넘어간다. 그래서 초록불이 도구의 고장을 덮었다.

여기서는 **별도 프로세스로** 각 도구의 최상단을 `__main__` 으로 실행한다.

이 시험 자체가 두 번 고장 났다.
  - 2026-09-17: runpy 로 본체까지 돌려 pytest 한 번마다 저장소 파일 28개를 다시 썼다(백로그 18).
  - 2026-09-18 리뷰 14번: `except Exception: pass` 가 ImportError 외의 최상단 실패를 전부 삼켰고
    (속성 접근으로 터지는 순환 참조는 AttributeError 다), 대상이 손으로 적은 12개라 배치가 부르는
    make_weekly_page·make_weekly_share·batch_notes·month_lag 등 8개가 빠져 있었다.

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - make_naver_post 최상단에 `from make_theory_post import CYCLE_SYNC_N` → ImportError 로 빨강
  - make_weekly_page 최상단에 `import month_lag as W` 뒤 없는 속성(`W.NOPE`) 접근 → AttributeError 로 빨강
  - 아무 도구 최상단에 없는 이름 참조 → NameError 로 빨강
  - _import_stage 를 runpy.run_path(..., run_name='__main__') 로 되돌리면 → 저장소 파일 시험이 빨강
  - 대상 목록 파생이 빈 목록을 돌려주면 → 목록 자기 확인 시험이 빨강
픽스처: 저장소의 tools/*.py 전부(가드가 있는 것). 네트워크·파일 쓰기 없이 최상단만 지난다(41개 약 8초).
"""
import ast
import glob
import io
import os
import subprocess
import sys

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
TOOLS = os.path.join(ROOT, 'tools')


def _has_main_guard(path):
    tree = ast.parse(io.open(path, encoding='utf-8').read(), path)
    return any(isinstance(n, ast.If) and isinstance(n.test, ast.Compare)
               and isinstance(n.test.left, ast.Name) and n.test.left.id == '__name__'
               for n in tree.body)


def scripts():
    """`__main__` 가드가 있는 tools/*.py 전부. 손으로 적지 않는다 — 새 도구가 생기면 저절로 들어온다.

    가드가 없는 파일은 뺀다: 라이브러리(home_src·quiz_review)이거나, 최상단이 곧 본체인 일회성
    분석 스크립트(rate_shock·study_grade_bands)라 최상단 실행이 실제 작업이 된다.
    """
    return sorted(os.path.basename(p) for p in glob.glob(os.path.join(TOOLS, '*.py'))
                  if _has_main_guard(p))


def _import_stage(name):
    """그 스크립트를 __main__ 으로 올려 **모듈 최상단까지만** 실행한다(가드 블록은 뗀다).

    종료 코드: 0 통과 · 9 ImportError(순환 참조 등) · 8 그 밖의 최상단 실패 · 7 최상단 SystemExit.
    저장소 밖 패키지(pillow 등)가 없어서 나는 ModuleNotFoundError 는 통과로 친다 — 배치는 pillow
    설치 실패를 인프라 경고로만 다루는데, 이 시험이 그걸 코드 회귀로 바꿔 데이터 커밋을 막으면 안 된다.
    """
    code = (
        'import ast, os, sys\n'
        'tools = %r\n'
        'sys.path.insert(0, tools)\n'
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
        '    top = (getattr(e, "name", None) or "").split(".")[0]\n'
        '    local = os.path.exists(os.path.join(tools, top + ".py"))\n'
        '    if isinstance(e, ModuleNotFoundError) and top and not local:\n'
        '        print("MISSINGDEP", top); sys.exit(0)\n'
        '    print("IMPORTERROR", e); sys.exit(9)\n'
        'except SystemExit as e:\n'
        '    print("SYSTEMEXIT", repr(e.code)[:120]); sys.exit(7)\n'
        'except BaseException as e:\n'
        '    print("TOPLEVEL", type(e).__name__, str(e)[:120]); sys.exit(8)\n'
        % (TOOLS, os.path.join(TOOLS, name))
    )
    return subprocess.run([sys.executable, '-c', code], capture_output=True,
                          text=True, encoding='utf-8', errors='replace', timeout=120)


def test_the_script_list_is_derived_and_covers_the_batch_tools():
    got = set(scripts())
    must = {'update_adv_data.py', 'split_data.py', 'make_sido_pages.py', 'make_indicator_pages.py',
            'make_monthly_page.py', 'make_weekly_page.py', 'refresh_cycle_data.py',
            'make_weekly_share.py', 'month_lag.py', 'batch_notes.py', 'format_batch_report.py',
            'make_naver_post.py', 'make_theory_post.py', 'check_freshness.py'}
    assert must <= got, '대상 목록 파생이 깨졌다 — 빠진 도구: %s' % sorted(must - got)


def test_running_the_tools_does_not_touch_the_repo():
    """이 시험 파일이 저장소 파일을 다시 쓰지 않는다(2026-09-17 정정의 재발 방지)."""
    watch = [os.path.join(ROOT, p) for p in ('data.js', 'sitemap.xml',
                                            os.path.join('zone', 'index.html'),
                                            os.path.join('weekly', 'index.html'),
                                            os.path.join('cycle', 'index.html'))]
    before = [os.path.getmtime(p) for p in watch]
    for name in ('make_sido_pages.py', 'split_data.py', 'make_naver_post.py',
                 'make_weekly_page.py', 'refresh_cycle_data.py'):
        _import_stage(name)
    assert [os.path.getmtime(p) for p in watch] == before


def test_no_tool_dies_at_top_level_when_run_as_a_script():
    broken = []
    for name in scripts():
        p = _import_stage(name)
        if p.returncode != 0:
            broken.append('%s (rc=%d): %s' % (name, p.returncode,
                                              ((p.stdout or '') + (p.stderr or '')).strip()[-200:]))
    assert not broken, (
        '스크립트로 띄우면 최상단에서 죽는 도구가 있다(순환 참조·없는 이름 등).\n  '
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
