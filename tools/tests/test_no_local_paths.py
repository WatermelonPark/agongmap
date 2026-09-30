# -*- coding: utf-8 -*-
"""추적 파일에 저장소 밖 로컬 경로(개인 홈 폴더·키 파일 경로)를 적지 않는다(공개 저장소 규칙, 전수리뷰 #7·#116).

CLAUDE.md 하드 룰: '저장소 밖 로컬 경로(원고 폴더, 강의 아카이브, 키 파일 경로 등)를 문서·코드·커밋 메시지에 적지 않는다',
'키는 환경 변수로만 읽는다'. 2026-09-30 까지 R-ONE 일회성 도구 두 개(fetch_index_levels·gen_sgg_rone_map)가 홈 폴더의 키
파일 경로를 코드·오류 문구에 적고 그 파일을 정규식으로 읽었고, 로컬 러너 bat 도 같은 경로를 세 곳에 적었다. 지금은 두 도구가
환경 변수 RONE_API_KEY 만 읽고, bat 은 키 파일 경로를 환경 변수 AGONGMAP_KEYS 로 받는다.

검사 대상: `git ls-files` 의 추적 파일 전부(이진 파일은 건너뜀, 이 시험 파일 자신은 패턴 원문을 담으므로 제외).
git 이 없으면 숨은 폴더·drafts·logs·cache 를 뺀 저장소 전체를 걷는다. 허용: GitHub 러너의 공개 경로(/home/runner/),
컨테이너 기본 경로(/home/user/), 셸 변수 `$HOME` 을 쓰는 캐시 경로처럼 특정 사람·파일을 가리키지 않는 것.

무엇을 깨뜨리면 빨개지나(각각 실제로 깨뜨려 확인):
  - fetch_index_levels._key() 에 홈 폴더 키 파일 폴백(expanduser 로 '~/.' 로 시작하는 키 파일 경로)을 되살리면 → 빨강
  - gen_sgg_rone_map 의 오류 문구에 '~/.' 로 시작하는 '..._keys.bat' 파일명을 다시 적으면 → 빨강
  - run_weekly_update.bat 의 `call "%AGONGMAP_KEYS%"` 를 `%USERPROFILE%\\<키 파일>` 로 되돌리면 → 빨강
  - docs 요청서에 Windows 사용자 폴더(`C:` + `\\Users\\이름\\`) 나 macOS 홈(`/Users/이름/`)을 적으면 → 빨강
픽스처: 저장소의 실제 추적 파일 전부(기준 커밋 0649df8 에서는 위 세 파일 6곳이 걸렸다). 패턴 단위 시험은 되살아나기 쉬운
실제 모양(옛 코드·옛 bat 줄)을 문자열로 재현해 걸리는지, 허용 경로가 걸리지 않는지 본다.
"""
import os
import re
import subprocess

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
SELF = os.path.relpath(os.path.abspath(__file__), ROOT).replace(os.sep, '/')

# (이름, 정규식) — 대소문자 무시
FORBIDDEN = [
    ('Windows 사용자 폴더', r'\b[A-Z]:[\\/]+Users[\\/]+[^\\/\s"\']+'),
    ('macOS 홈 폴더', r'(?<![\w.:/])/Users/[^/\s"\']+/'),
    ('리눅스 개인 홈 폴더', r'(?<![\w.:/])/home/(?!runner/|user/)[a-z_][\w.-]*/'),
    ('Windows 사용자 환경 변수 경로', r'%(USERPROFILE|HOMEPATH|APPDATA|LOCALAPPDATA|ONEDRIVE)%[\\/]'),
    ('코드에서 홈 폴더 파일 직접 열기', r'expanduser\(\s*[\'"]~[\\/]'),
    ('홈 폴더의 키·비밀 파일', r'~[\\/]\.?[\w.-]*(key|secret|token|cred)'),
    ('키 파일 이름', r'[\w.-]*_keys?\.(bat|cmd|ps1|env|txt|sh|json)\b'),
]
_RX = [(name, re.compile(rx, re.I)) for name, rx in FORBIDDEN]


def _tracked():
    try:
        out = subprocess.run(['git', 'ls-files', '-z'], cwd=ROOT, capture_output=True, timeout=60)
        files = [f for f in out.stdout.decode('utf-8', 'replace').split('\0') if f] if out.returncode == 0 else []
    except Exception:
        files = []
    if files:
        return files
    found = []
    for dp, dns, fns in os.walk(ROOT):
        dns[:] = [d for d in dns if not d.startswith('.') and d not in ('drafts', 'logs', 'cache', '__pycache__')]
        for fn in fns:
            found.append(os.path.relpath(os.path.join(dp, fn), ROOT).replace(os.sep, '/'))
    return found


def _hits(text):
    out = []
    for name, rx in _RX:
        for m in rx.finditer(text):
            out.append((name, m.group(0)))
    return out


def test_no_local_paths_in_tracked_files():
    files = _tracked()
    assert len(files) > 100, '추적 파일 목록을 못 읽었다: %d개' % len(files)
    bad = []
    for f in files:
        if f == SELF:
            continue
        p = os.path.join(ROOT, f)
        if not os.path.isfile(p):
            continue
        with open(p, 'rb') as fh:
            raw = fh.read()
        if b'\0' in raw[:8192]:
            continue   # 이진 파일(이미지·글꼴)
        text = raw.decode('utf-8', 'replace')
        for ln_no, ln in enumerate(text.splitlines(), 1):
            for name, hit in _hits(ln):
                bad.append('%s:%d [%s] %s' % (f, ln_no, name, hit))
    assert not bad, ('저장소 밖 로컬 경로가 추적 파일에 있다(공개 저장소 규칙 — 경로는 환경 변수로 받는다):\n  '
                     + '\n  '.join(bad[:40]))


def test_patterns_catch_the_old_shapes_and_spare_public_paths():
    # 기준 커밋의 옛 모양(이 시험이 막으려는 것) — 문자열을 쪼개 적어 이 파일이 스스로 걸리지 않게 한다
    # 파일 이름은 합성('example')이다 — 실제 로컬 키 파일 이름을 여기서 다시 조립하지 않는다(공개 저장소 규칙).
    home_key = '~/.' + 'example' + '_keys.bat'
    old = [
        "    p = os.path.expanduser('" + home_key + "')",
        "raise SystemExit('RONE_API_KEY 필요 (환경변수 또는 " + home_key + ")')",
        'call "%USER' + 'PROFILE%\\.' + 'example' + '_keys.bat"',
        'C:' + '\\Users\\someone\\Documents\\manuscripts',
        '/Us' + 'ers/someone/Desktop/lectures',
        '/ho' + 'me/someone/keys',
    ]
    for s in old:
        assert _hits(s), '옛 모양을 못 잡는다: %r' % s
    ok = [
        'call "%AGONGMAP_KEYS%"',
        "k = os.environ.get('RONE_API_KEY', '')",
        '`/home/runner/work/agongmap/agongmap`',
        'VENV="${XDG_CACHE_HOME:-$HOME/.cache}/agongmap-ci312"',
        'https://m.stock.naver.com/marketindex/home/major/exchange/bond',
        '사용자 로컬 `~/.claude/CLAUDE.md`에 있다',
    ]
    for s in ok:
        assert not _hits(s), '허용 경로를 잘못 잡는다: %r → %r' % (s, _hits(s))
