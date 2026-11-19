# -*- coding: utf-8 -*-
"""공유 이미지 도구 다섯이 같이 쓰는 카드 기본 — 캔버스 크기·색·글꼴·칩·푸터(백로그 61-C).

쓰는 곳: make_zone_cards(지역 카드)·make_og_cards(브랜드 카드)·make_content_cards(글 카드)는 쿨 계열 1200×630 카드를
여기 조각으로 그리고, make_weekly_share·make_monthly_share(주간·월간 카드)는 글꼴 폴더·글꼴 파일·폴백 로더(`noto`)만 쓴다.
예전엔 다섯 도구가 같은 값을 따로 적었다 — 한쪽만 바꾸면 카드끼리 계열이 조용히 갈린다.

여기 두지 않는 것(값이나 동작이 달라서 합치지 않았다):
  - 주간·월간 카드의 웜 계열 색(INK (22, 32, 58)·PAPER (246, 244, 238) 등)과 크기(make_weekly_page·make_monthly_page.SHARE_SIZE)
    — 쿨 계열과 값이 다르다. 웜 계열의 정본은 make_weekly_share 다.
  - 지역 카드의 fit_width, 글 카드의 wrap·save — 한 도구만 쓴다.

pillow 와 표준 라이브러리만 쓴다(CLAUDE.md '이미지 도구는 pillow 만'). PIL 을 맨 위에서 가져오므로 pip 앞에서 도는 생성기·감시는
이 모듈을 가져오지 않는다(test_test_deps_are_installed).
"""
import os

from PIL import Image, ImageDraw, ImageFont

TOOLS = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(TOOLS)

W, H = 1200, 630          # 쿨 계열 카드(지역·브랜드·글) 크기 — OG 권장 1.91:1

# 쿨 계열 — 랜딩 페이지 :root 토큰과 같다(make_og_cards 독스트링).
PAPER = (244, 246, 245)   # --paper #f4f6f5
INK   = (19, 30, 36)      # --ink   #131e24
RED   = (192, 57, 43)     # 상승/훅 라인 #c0392b
MUTED = (94, 111, 116)    # --muted #5e6f74
LINE  = (196, 206, 201)   # --line  #c4cec9
WHITE = (255, 255, 255)

# 글꼴 — 저장소에 번들한 Pretendard 서브셋(tools/fonts/, SIL OFL 1.1).
FONT_FILES = {'Bold': 'Pretendard-Bold.subset.ttf', 'Medium': 'Pretendard-Medium.subset.ttf'}
TOOLS_FONT_DIR = os.path.join(TOOLS, 'fonts')
# 쿨 계열 카드는 루트 fonts/ 가 있으면 그것을 먼저 본다(CLAUDE.md: 루트 fonts/ 는 카드 도구 자리). 지금 저장소에는 없어 두 폴더가
# 같은 곳(tools/fonts)을 가리키지만, 누가 루트 fonts/ 를 두면 쿨 카드만 따라가던 옛 동작을 그대로 지킨다 — 주간·월간 카드는
# 예전처럼 TOOLS_FONT_DIR 만 본다.
FONT_DIR = os.path.join(ROOT, 'fonts') if os.path.exists(os.path.join(ROOT, 'fonts')) else TOOLS_FONT_DIR
# 번들 글꼴이 없을 때만 noto() 가 쓰는 시스템 가변 글꼴(개발 PC 호환용)
FONT_FALLBACK = ['C:/Windows/Fonts/NotoSansKR-VF.ttf']

MX = 64                   # 쿨 계열 카드의 좌우 여백
DOMAIN = 'agongmap.co.kr' # 쿨 계열 카드 푸터 오른쪽 글자


def font(size, weight='Bold'):
    """쿨 계열 카드 글꼴(FONT_DIR). 파일이 없으면 그대로 실패한다 — 두부 카드를 만들지 않는다."""
    return ImageFont.truetype(os.path.join(FONT_DIR, FONT_FILES[weight]), size)


def noto(size, weight='Bold', font_dir=None):
    """주간·월간 카드 글꼴 — 번들 글꼴(TOOLS_FONT_DIR) 우선, 없으면 시스템 가변 글꼴로 폴백."""
    font_dir = font_dir or TOOLS_FONT_DIR
    path = os.path.join(font_dir, FONT_FILES.get(weight, FONT_FILES['Bold']))
    if os.path.exists(path):
        return ImageFont.truetype(path, size)
    for p in FONT_FALLBACK:
        if os.path.exists(p):
            f = ImageFont.truetype(p, size)
            try:
                f.set_variation_by_name(weight)
            except Exception:
                pass
            return f
    raise FileNotFoundError(
        '한글 폰트를 찾을 수 없습니다. %s 에 Pretendard 서브셋을 두세요.' % font_dir)


def canvas():
    """쿨 계열 빈 카드와 그리개 — PAPER 바탕(RGBA)에 위쪽 먹색 띠(13px)."""
    img = Image.new('RGBA', (W, H), PAPER + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 13], fill=INK)
    return img, d


def chip(d, text):
    """왼쪽 위 분류 칩(먹색 둥근 상자에 흰 글자). 칩 아래 끝 y 를 돌려준다."""
    cf = font(28, 'Bold')
    bb = d.textbbox((0, 0), text, font=cf)
    cw, ch = bb[2] - bb[0], bb[3] - bb[1]
    px, py = 22, 13
    d.rounded_rectangle([MX, 66, MX + cw + px * 2, 66 + ch + py * 2], radius=6, fill=INK)
    d.text((MX + px - bb[0], 66 + py - bb[1]), text, font=cf, fill=WHITE)
    return 66 + ch + py * 2


def footer(d, left_text):
    """아래 구분선(y=548)과 푸터 — 왼쪽 설명(없으면 생략)과 오른쪽 도메인(빨강)."""
    fy = 548
    d.line([MX, fy, W - MX, fy], fill=LINE, width=2)
    if left_text:
        d.text((MX, fy + 24), left_text, font=font(24, 'Medium'), fill=MUTED)
    df = font(26, 'Bold')
    bb = d.textbbox((0, 0), DOMAIN, font=df)
    d.text((W - MX - (bb[2] - bb[0]), fy + 22), DOMAIN, font=df, fill=RED)
