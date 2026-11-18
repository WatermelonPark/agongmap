# -*- coding: utf-8 -*-
"""브랜드 OG 카드 og-brand.png (1200x630) — 카카오톡·트위터 공유 미리보기(홈·about·faq·cycle·zone 허브 등).

톤은 사이트 쿨 토큰과 1:1로 맞춘다:
  ink #131e24 / paper #f4f6f5 / green #1a6b54 / red #c0392b / muted #5e6f74 / line #c4cec9

퀴즈 3종 OG 카드(og-test.png·og-investor.png·og-redev.png)와 그 이모지 렌더링은 2026-11-14 퀴즈 제거로 걷었다.
브랜드 카드 푸터의 '부동산 테스트'도 같은 날 뺐다.

사용:  python tools/make_og_cards.py
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import card_kit as CK  # noqa: E402

# 크기·쿨 계열 색·글꼴은 card_kit 이 정본이다(백로그 61-C — 지역·글 카드와 한 벌). 이름은 그대로 남긴다.
W, H = CK.W, CK.H
PAPER, INK, RED, MUTED, LINE, WHITE = CK.PAPER, CK.INK, CK.RED, CK.MUTED, CK.LINE, CK.WHITE
ROOT = CK.ROOT
FONT_DIR, FONT_FILES = CK.FONT_DIR, CK.FONT_FILES
font = CK.font


def make_brand():
    """og-brand.png(홈 공유 카드) — 옛 병아리·웜톤 카드를 현 브랜드로 교체.
    모래시계 아이콘(make_app_icon.draw_icon 재사용) + 훅 + 아공맵 + 슬로건."""
    from make_app_icon import draw_icon
    img, d = CK.canvas()                          # 상단 바: 브랜드는 먹색
    MX = CK.MX

    # 우측: 사이클 모래시계 (배경색 동일해 그대로 붙는다)
    glass = draw_icon(380, 0.94)
    img.paste(glass, (770, 130))

    # 훅 (빨강) → 아공맵 (거대 먹색) → 슬로건 (뮤트)
    d.text((MX, 104), '공급을 보면 집값이 보인다', font=font(40, 'Bold'), fill=RED)
    nf = font(150, 'Bold')
    d.text((MX, 180), '아공맵', font=nf, fill=INK)
    d.text((MX, 400), '아파트 공급 지도', font=font(42, 'Medium'), fill=MUTED)

    # 하단 구분선 + 푸터
    CK.footer(d, '주간 시세 지도 · 시도별 공급 진단 · 국가기관 데이터 기반')

    img.convert('RGB').save(os.path.join(ROOT, 'og-brand.png'), 'PNG', optimize=True)
    return 'og-brand.png'


def main():
    print('written ->', make_brand())


if __name__ == '__main__':
    main()
