# -*- coding: utf-8 -*-
"""사람이 돌리는 이미지·디자인 도구 네 개가 CI 와 같은 환경(3.12, pytest·pillow 만)에서 돌고,
감사 도구와 적용 도구가 같은 기준을 쓰는지 본다(전수리뷰 #87·#88·#89·#90).

재현하는 실제 상태:
  - #87: 리눅스(클라우드 세션·CI 러너)에는 Windows 이모지 글꼴(seguiemj.ttf)이 없다. make_og_cards 는 그 경로
    하나를 박아 'OSError: cannot open resource' 로 죽었고, 퀴즈 카드를 먼저 굽느라 이모지가 필요 없는
    og-brand.png 까지 못 구웠다. 픽스처는 이모지 글꼴 후보가 하나도 없는 러너다.
  - #88: 감사(audit_design)는 원형 border-radius:50% 와 등급 '부족' 틴트 #faf3e7 을 준수로 보는데,
    적용(apply_design)은 50% 를 0 으로, #faf3e7 을 회색으로 바꿨다. 픽스처는 범례 점(.dot)과 등급 배지(.tag.g2).
  - #89: 감사가 세미콜론 없는 인라인 style(index.html 의 공유 버튼 `style="...border-radius:var(--r-touch)"
    onclick=...`)에서 마크업 꼬리를 radius 값으로 읽었고, 위반 문턱이 '>2' 라 /weekly/ 의 2px 같은 규칙 밖
    값 1~2종을 통과시켰다. 픽스처는 그 두 형태를 그대로 옮긴 것이다.
  - #90: make_beginner_cards.cutout 이 numpy 를 불러 pillow 만 깐 환경에서 11장 모두 실패했다. 픽스처는
    흰 배경에 큰 피사체 하나와 떨어진 작은 점(드롭섀도우·점선 조각 자리) 하나를 둔 원화다.

무엇을 깨뜨리면 빨개지나(실제로 확인):
  - make_og_cards.main 에서 make_brand() 를 퀴즈 카드 루프 뒤로 옮기면 test_og_brand_bakes_without_emoji_font.
  - emoji_font 를 EMOJI_FONTS 첫 경로만 여는 옛 코드로 되돌리면 test_emoji_font_names_candidates
    (OSError 이고 FileNotFoundError·후보 경로 안내가 아니다).
  - apply_design.rad 를 옛 코드(값 상관없이 0/3px)로 되돌리면, 또는 웜색 판정을 DATA_TINTS 예외 없는
    is_warm 으로 되돌리면 test_apply_keeps_what_audit_allows. rad 의 보존 판정을 RADIUS_OK 대신 RADIUS_SHAPE(원형만)로
    되돌려도 빨개진다 — 404 a.home·.skip 의 3px 가 0 이 된다(전수리뷰 P-6, 픽스처는 그 두 규칙을 그대로 옮겼다).
  - audit_design 의 radius 정규식에서 따옴표 제외를 빼면 test_audit_inline_style_stops_at_quote,
    violations 의 radius 문턱을 'nr > 2' 로 되돌리면 test_audit_flags_a_single_off_rule_radius.
  - cutout 에 `import numpy as np` 를 다시 넣으면 test_beginner_cutout_pillow_only(CI 는 numpy 가 없어
    ModuleNotFoundError, 로컬은 AST 검사), 가장 큰 성분 고르기를 빼면 같은 시험의 크기 검사가 빨개진다.
"""
import ast
import io
import os
import re
import sys

import pytest
from PIL import Image, ImageDraw

TOOLS = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if TOOLS not in sys.path:
    sys.path.insert(0, TOOLS)

import apply_design        # noqa: E402
import audit_design        # noqa: E402
import make_beginner_cards  # noqa: E402
import make_og_cards       # noqa: E402

MISSING = os.path.join(os.sep, 'nonexistent-agongmap', 'emoji.ttf')


def test_emoji_font_names_candidates(monkeypatch):
    monkeypatch.setattr(make_og_cards, 'EMOJI_FONTS', ((MISSING, 109),))
    with pytest.raises(FileNotFoundError) as e:
        make_og_cards.emoji_font()
    assert MISSING in str(e.value)


def test_og_brand_bakes_without_emoji_font(monkeypatch, tmp_path):
    monkeypatch.setattr(make_og_cards, 'EMOJI_FONTS', ((MISSING, 109),))
    monkeypatch.setattr(make_og_cards, 'ROOT', str(tmp_path))
    with pytest.raises(SystemExit) as e:
        make_og_cards.main()
    assert MISSING in str(e.value)
    brand = tmp_path / 'og-brand.png'
    assert brand.exists(), '이모지 글꼴이 없어도 og-brand.png 는 구워져야 한다'
    assert Image.open(str(brand)).size == (make_og_cards.W, make_og_cards.H)
    for c in make_og_cards.CARDS:          # 퀴즈 카드는 굽지 않고 멈춘다(반쪽 카드 없음)
        assert not (tmp_path / c[0]).exists()


def _write(tmp_path, name, html):
    p = tmp_path / name
    p.write_text(html, encoding='utf-8')
    return str(p)


def test_apply_keeps_what_audit_allows(tmp_path):
    tint = sorted(audit_design.DATA_TINTS)[0]
    html = ('<!doctype html><html><head><meta name="viewport" content="width=device-width">'
            '<style>.dot{width:8px;border-radius:50%} .tag.g2{background:#' + tint + ';color:#131e24}'
            ' .box{border-radius:6px} button{border-radius:8px}'
            ' a.home{display:inline-flex;min-height:48px;border-radius:3px}'
            ' .skip{position:absolute;left:8px;border-radius:3px}</style></head><body></body></html>')
    p = _write(tmp_path, 't.html', html)
    a = audit_design.audit(p)
    assert a['radii'] == ['6px', '8px'] and a['warm'] == []   # 감사: 50%·틴트는 준수, 6/8px 는 위반
    apply_design.apply(p)
    out = io.open(p, encoding='utf-8').read()
    assert '.dot{width:8px;border-radius:50%}' in out, '감사가 허용한 원형을 적용 도구가 깨뜨렸다'
    assert '#' + tint in out, '감사가 예외로 둔 데이터 틴트를 적용 도구가 바꿨다'
    assert '.box{border-radius:0}' in out and 'button{border-radius:3px}' in out
    assert 'a.home{display:inline-flex;min-height:48px;border-radius:3px}' in out, '감사가 허용한 3px(404 홈 단추)를 적용 도구가 깎았다'
    assert '.skip{position:absolute;left:8px;border-radius:3px}' in out, '감사가 허용한 3px(건너뛰기 링크)를 적용 도구가 깎았다'
    after = audit_design.audit(p)
    assert after['radii'] == [] and after['warm'] == []       # 적용 뒤에는 감사가 깨끗하다
    # 적용 도구가 남기거나 쓰는 radius 값은 전부 감사의 허용 값이다
    assert apply_design.RADIUS_SHAPE <= audit_design.RADIUS_OK
    assert {'0', '3px'} <= audit_design.RADIUS_OK


def test_audit_inline_style_stops_at_quote(tmp_path):
    html = ('<!doctype html><html><head><link rel="stylesheet" href="/app.css"></head><body>'
            '<button style="margin:22px auto 0;padding:13px 28px;border-radius:var(--r-touch)" '
            'onclick="shareTest()"><svg viewBox="0 0 24 24"></svg>보내기</button></body></html>')
    a = audit_design.audit(_write(tmp_path, 'i.html', html))
    assert a['shared'] and a['radii'] == [], a['radii']
    assert not any(f.startswith('radius') for f in audit_design.violations(a))


def test_audit_flags_a_single_off_rule_radius(tmp_path):
    html = ('<!doctype html><html><head><style>body{font-family:\'Pretendard Variable\'}'
            '.mm-cap i{display:inline-block;border-radius:2px}</style></head><body></body></html>')
    a = audit_design.audit(_write(tmp_path, 'w.html', html))
    assert a['radii'] == ['2px']
    assert any(f.startswith('radius') for f in audit_design.violations(a))


def test_beginner_cutout_pillow_only(tmp_path):
    tree = ast.parse(io.open(make_beginner_cards.__file__, encoding='utf-8').read())
    imported = {a.name.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.Import) for a in n.names}
    imported |= {n.module.split('.')[0] for n in ast.walk(tree) if isinstance(n, ast.ImportFrom) and n.module}
    assert 'numpy' not in imported, '이미지 도구는 pillow 만 깐 환경에서 돌아야 한다'

    im = Image.new('RGB', (120, 90), (255, 255, 255))
    d = ImageDraw.Draw(im)
    d.rectangle([20, 15, 69, 54], fill=(30, 90, 160))      # 피사체 50x40
    d.rectangle([95, 70, 97, 72], fill=(40, 40, 40))       # 떨어진 조각 3x3
    src = str(tmp_path / 'raw.png')
    im.save(src)
    out = make_beginner_cards.cutout(src)
    assert out.mode == 'RGBA' and out.size == (50, 40), out.size
    assert out.getpixel((0, 0)) == (30, 90, 160, 255)
    assert out.getchannel('A').getextrema() == (255, 255)


def test_audit_reads_the_desktop_sheet(tmp_path, capsys, monkeypatch):
    """감사가 데스크톱 틀 desk.css 를 시트 한 줄로 따로 읽는다(전수리뷰 P-7).

    재현한 상태(2026-10-18): audit() 는 페이지 <style> 과 app.css 만 봐, 모든 탭바 페이지가 싣는 desk.css 의 이름표
    `body[data-desk] .bottomnav::before{…font-weight:800}` 가 감사 표에 드러나지 않았다(전 페이지 800 칸 0).
    픽스처: 그 규칙과 주석 속 'app.css' 글자(지금 desk.css 에 실제로 있다 — 공유 판정이 켜지면 app.css 그림자까지 합산된다)를
    옮긴 시트. 실제 desk.css 는 위반이 없어야 한다.
    변이(실제로 확인): main() 의 pages.append('desk.css') 를 지우면, audit 의 is_css 갈래를 지우면(공유 판정이 켜져
    그림자를 합산) 빨개진다. desk.css 이름표를 font-weight:800 으로 되돌려도 빨개진다.
    """
    p = _write(tmp_path, 'desk.css', '/* 홈 app.css 와 같은 52px */\n'
               "body[data-desk] .bottomnav::before{content:'x';font-weight:800}\n"
               'body[data-desk] .dtoc{box-shadow:0 2px 8px rgba(0,0,0,.2)}\n')   # 떠 있는 탭바 그림자는 기능이라 세지 않는다(11-12)
    a = audit_design.audit(p)
    assert a['shared'] is False and a['w800'] == 1 and a['shadow'] == 1, a
    assert any(f.startswith('800') for f in audit_design.violations(a))
    root = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..')
    real = audit_design.audit(os.path.join(root, 'desk.css'))
    assert audit_design.violations(real) == [], audit_design.violations(real)
    monkeypatch.chdir(root)        # main() 이 작업 디렉터리를 바꾸므로 시험 뒤 되돌린다
    audit_design.main()
    out = capsys.readouterr().out
    assert re.search(r'^desk\.css\s', out, re.M), 'audit_design.main() 표에 desk.css 줄이 없다'


def test_audit_counts_only_decorative_shadows(tmp_path):
    """감사의 '그림자'는 장식 그림자만 센다 — inset(정렬 열 밑줄·속 빈 고리)과 떠 있는 고정 요소(.bottomnav·.inst)는 기능이라 뺀다.
    실제 상태(2026-11-12 디자인 마감 점검): 홈·/cycle/·리포트의 '그림자×4' 가 탭바·데스크톱 위 내비·설치 알림·정렬 열 밑줄 넷이었다.
    변이(실제로 확인): 'inset' not in x 조건이나 FLOATING 거르기를 빼면 빨개진다. 카드에 장식 그림자 둘을 더하면 여전히 위반이다.
    픽스처: 탭바·설치 알림·inset 밑줄과 장식 카드 그림자 둘을 담은 합성 시트."""
    p = tmp_path / 'x.css'
    p.write_text('.bottomnav{position:fixed;box-shadow:0 -4px 18px rgba(0,0,0,.2)}\n'
                 '.inst{position:fixed;\n  box-shadow:0 6px 22px rgba(0,0,0,.2)}\n'
                 '.rank-tbl th.on{box-shadow:inset 0 -2px 0 #000}\n', encoding='utf-8')
    assert audit_design.audit(str(p))['shadow'] == 0
    p.write_text(p.read_text(encoding='utf-8') + '.card{box-shadow:0 2px 8px #0002}.tile{box-shadow:0 4px 12px #0003}\n',
                 encoding='utf-8')
    a = audit_design.audit(str(p))
    assert a['shadow'] == 2 and any(f.startswith('그림자') for f in audit_design.violations(a)), a


def test_audit_and_apply_see_the_same_tracking_and_uppercase(tmp_path):
    r"""자간·대문자 변환을 감사가 세면 적용 도구가 고치고, 둘 다 같은 꼴을 본다 — '0.08em'·'1em'·'.045em'·쌍점 뒤 빈칸.

    왜: 두 도구가 정규식을 따로 적어, 자간은 둘 다 '.05em' 꼴만 잡았고('0.08em'·'1em'·'.045em' 은 위반 없음으로 나왔다),
        `text-transform: uppercase`(쌍점 뒤 빈칸)는 감사가 세는데 적용은 그대로 남겼다(2026-11-13 전수 리뷰).
    변이(실제로 확인): audit_design.TRACK_RE 를 예전 식(`\.(?:0[5-9]|[1-9]\d*)em`)으로 되돌리면 첫 단정이, apply_design 의
          uppercase 판정을 `'text-transform:uppercase' in s` 로 되돌리면 적용 뒤 단정이 빨개진다.
    픽스처: 위반 꼴 넷과 허용 꼴 둘(.04em — 문턱 그대로, 음수 자간)이 든 합성 페이지.
    """
    html = ('<!doctype html><html><head><meta name="viewport" content="width=device-width">'
            '<style>.a{letter-spacing:0.08em}.b{letter-spacing: 1em}.c{letter-spacing:.045em}.d{letter-spacing:.05em}'
            '.ok{letter-spacing:.04em}.neg{letter-spacing:-.01em}.u{text-transform: uppercase;color:#131e24}</style>'
            '</head><body></body></html>')
    p = _write(tmp_path, 'k.html', html)
    a = audit_design.audit(p)
    assert (a['track'], a['upper']) == (4, 1), a
    apply_design.apply(p)
    out = io.open(p, encoding='utf-8').read()
    after = audit_design.audit(p)
    assert (after['track'], after['upper']) == (0, 0), (after, out)
    assert '.ok{letter-spacing:.04em}' in out and '.neg{letter-spacing:-.01em}' in out, '허용한 자간을 적용 도구가 지웠다'
    assert 'uppercase' not in out and '.u{color:#131e24}' in out.replace('.u{ ', '.u{'), out


def test_shadow_scan_is_linear_and_agrees_with_the_rule_grammar():
    r"""그림자 훑기는 문서 길이에 비례하고, 예전 정규식과 같은 답을 낸다.

    왜: 예전 식은 그림자가 없는 규칙마다 선택자 자리의 모든 시작점에서 다시 훑어 제곱으로 느렸다 — 시도 리포트 한 장에 13초,
        /cycle/ 에 7초, 이 감사를 부르는 시험 하나가 24초로 게이트에서 셋째로 느렸다(2026-11-13 전수 리뷰).
    변이(실제로 확인): _rules 를 `re.finditer(r'([^{}]*)\{([^{}]*)\}', css)` 로 되돌리면 아래 긴 입력이 20초 안에 끝나지 않아
          빨개진다(딴 프로세스에서 상한을 두고 본다 — 이 시험이 게이트를 매달지 않는다).
    픽스처: 저장소의 실제 app.css(답 대조), 그리고 닫는 중괄호 뒤에 중괄호 없는 긴 글이 오고 다시 '}' 로 끝나는 합성 입력
            (`a{b{c:1} …긴 글… }` — 스크립트·JSON 이 든 페이지의 모양. 여는 중괄호 없이 '}' 를 만나는 자리가 느린 자리다).
    """
    import subprocess
    css = io.open(os.path.join(os.path.dirname(TOOLS), 'app.css'), encoding='utf-8').read()
    old = re.findall(r'([^{}]*)\{[^{}]*?box-shadow:\s*([^;}\n]+)', css)
    new = audit_design._shadows(css)
    assert old and [(s.strip(), x) for s, x in old] == [(s.strip(), x) for s, x in new]
    assert list(audit_design._rules('a{b{c:1}d}e{f:2}')) == [('b', 'c:1'), ('e', 'f:2')]
    code = ('import sys; sys.path.insert(0, %r)\nimport audit_design as A\n'
            's = "a{b{c:1}" + ("가나다라 " * 60000) + "}" + ".k{box-shadow:0 1px 2px #000}"\n'
            'print(len(A._shadows(s * 3)))\n') % TOOLS
    try:
        r = subprocess.run([sys.executable, '-c', code], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                           universal_newlines=True, timeout=20)
    except subprocess.TimeoutExpired:
        pytest.fail('그림자 훑기가 긴 글에서 끝나지 않는다(제곱 시간)')
    assert r.returncode == 0 and r.stdout.strip() == '3', r.stderr[-400:]
