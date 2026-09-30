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
    is_warm 으로 되돌리면 test_apply_keeps_what_audit_allows.
  - audit_design 의 radius 정규식에서 따옴표 제외를 빼면 test_audit_inline_style_stops_at_quote,
    violations 의 radius 문턱을 'nr > 2' 로 되돌리면 test_audit_flags_a_single_off_rule_radius.
  - cutout 에 `import numpy as np` 를 다시 넣으면 test_beginner_cutout_pillow_only(CI 는 numpy 가 없어
    ModuleNotFoundError, 로컬은 AST 검사), 가장 큰 성분 고르기를 빼면 같은 시험의 크기 검사가 빨개진다.
"""
import ast
import io
import os
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
            ' .box{border-radius:6px} button{border-radius:8px}</style></head><body></body></html>')
    p = _write(tmp_path, 't.html', html)
    a = audit_design.audit(p)
    assert a['radii'] == ['6px', '8px'] and a['warm'] == []   # 감사: 50%·틴트는 준수, 6/8px 는 위반
    apply_design.apply(p)
    out = io.open(p, encoding='utf-8').read()
    assert '.dot{width:8px;border-radius:50%}' in out, '감사가 허용한 원형을 적용 도구가 깨뜨렸다'
    assert '#' + tint in out, '감사가 예외로 둔 데이터 틴트를 적용 도구가 바꿨다'
    assert '.box{border-radius:0}' in out and 'button{border-radius:3px}' in out
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
