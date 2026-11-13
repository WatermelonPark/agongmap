# -*- coding: utf-8 -*-
"""GitHub Pages(Jekyll) 배포 설정 `_config.yml` — 원고는 내보내지 않고, 사이트가 불러오는 파일은 뺀 적이 없다.

2026-11-13 전수 리뷰: `content/` 원고(md)에 YAML 프런트매터가 있어 Jekyll 이 변환 대상으로 보고
/content/city/<slug>.html 을 내보냈다. 자리표({{v:…}})는 Liquid 가 빈칸으로 지워 "상록구가 , 단원구가 입니다" 같은
숫자 빠진 문장이 됐고, canonical 이 자기 자신이라 정식 글(/city/<slug>/)의 중복 페이지가 색인 가능한 상태였다.
"""
import fnmatch
import io
import os
import re
import subprocess

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))


def excludes(text=None):
    """_config.yml 의 exclude 목록. yaml 을 들이지 않고 읽는다(게이트는 pytest·pillow 만 깐다)."""
    if text is None:
        text = io.open(os.path.join(ROOT, '_config.yml'), encoding='utf-8').read()
    out, on = [], False
    for ln in text.splitlines():
        if re.match(r'^exclude:\s*$', ln):
            on = True
            continue
        if on:
            m = re.match(r'^\s+-\s+(\S.*?)\s*$', ln)
            if m:
                out.append(m.group(1).strip('\'"'))
            elif ln.strip() and not ln.lstrip().startswith('#'):
                on = False
    return out


def excluded(path, pats):
    """Jekyll 3 EntryFilter 가 보는 눈: 폴더 항목('docs/')은 그 아래 전부, 그 밖은 fnmatch(별표가 '/' 도 넘는다)나 앞말 일치."""
    for p in pats:
        if p.endswith('/'):
            if path.startswith(p):
                return True
        elif fnmatch.fnmatchcase(path, p) or path == p or path.startswith(p + '/'):
            return True
    return False


def tracked(prefix=''):
    """저장소가 추적하는 파일(루트 기준 '/' 경로). .git 이 없는 사본(다음 분기 전진 시험의 안쪽 게이트)에서는 폴더를 걷는다."""
    try:
        out = subprocess.run(['git', '-c', 'core.quotepath=off', 'ls-files', '--', prefix or '.'], cwd=ROOT,
                             stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, universal_newlines=True, check=True).stdout
        got = [f for f in out.splitlines() if f]
        if got:
            return got
    except (OSError, subprocess.CalledProcessError):
        pass
    got = []
    for d, ds, fs in os.walk(os.path.join(ROOT, prefix) if prefix else ROOT):
        ds[:] = [x for x in ds if not x.startswith('.') and x not in ('drafts', 'logs', 'node_modules', '__pycache__')]
        for f in fs:
            got.append(os.path.relpath(os.path.join(d, f), ROOT).replace(os.sep, '/'))
    return got


def test_manuscripts_are_not_deployed():
    """content/ 아래의 모든 md(원고와 README)는 배포에서 빠진다.

    변이(실제로 확인): _config.yml 에서 `content/*/*.md` 줄을 지우면 원고 전부가, `content/README.md` 줄을 지우면 README 가
          잡혀 빨개진다. 새 섹션 폴더를 한 단계 더 깊게 두어도(content/a/b/c.md) 빨개져 설정을 고치게 한다.
    픽스처: 저장소가 추적하는 실제 content/ 파일 목록과 실제 _config.yml.
    """
    pats = excludes()
    mds = [f for f in tracked('content') if f.endswith('.md')]
    assert mds, 'content/ 에 원고가 없다 — 픽스처가 비었다'
    left = [f for f in mds if not excluded(f, pats)]
    assert not left, '배포에 실리는 원고(Jekyll 이 HTML 로 변환한다): %s' % left[:5]


def test_exclude_never_hides_a_file_the_site_loads():
    """exclude 는 사이트가 실제로 불러오는 파일을 빼지 않는다 — 글 그림(content/<섹션>/img/), 루트 스크립트·데이터, 생성 페이지.

    변이(실제로 확인): exclude 에 `content/` 를 통째로 넣으면 글 그림이, `*.json` 을 넣으면 데이터 조각이 잡혀 빨개진다.
    픽스처: 저장소가 추적하는 실제 파일 가운데 사이트 주소로 읽히는 것(md·저장소 전용 폴더 밖).
    """
    pats = excludes()
    repo_only = ('docs/', 'tools/', 'art_raw/', '.claude/', '.github/')
    served = [f for f in tracked() if not f.startswith(repo_only) and not f.endswith('.md')
              and f not in ('_config.yml', '.gitignore')]
    imgs = [f for f in served if f.startswith('content/')]
    assert imgs, '글 그림이 하나도 없다 — 픽스처가 비었다'
    hidden = [f for f in served if excluded(f, pats)]
    assert not hidden, '사이트가 불러오는 파일이 배포에서 빠진다: %s' % hidden[:5]


def test_exclude_reader_follows_the_file_shape():
    """이 시험의 읽기 함수가 주석·빈 줄·따옴표를 지나 목록만 읽는다(검사기가 조용히 빈 목록을 읽으면 위 시험이 뜻을 잃는다).

    변이(실제로 확인): excludes 가 주석 줄에서 멈추게 하면(`elif ln.strip():`) 주석 뒤 항목을 놓쳐 빨개진다.
    픽스처: 주석이 항목 사이에 낀 합성 설정.
    """
    got = excludes('a: 1\nexclude:\n  - docs/\n  # 설명\n\n  - "content/*/*.md"\nother:\n  - x\n')
    assert got == ['docs/', 'content/*/*.md']
    assert excluded('content/city/a.md', got) and not excluded('content/city/img/a.png', got)
    assert excluded('docs/x/y.md', got) and not excluded('docsx/y.md', got)
