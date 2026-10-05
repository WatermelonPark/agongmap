# -*- coding: utf-8 -*-
"""/monthly/ 공유 카드(og:image) — 그 달 시도별 아파트 매매가격 변동률(홈 마케팅 검수 B8·VIRAL-1, 2026-09-27).

예전 /monthly/ 의 og:image 는 범용 og-brand.png 라, 단톡방에 링크를 붙이면 그 달의 숫자가 아니라 매달 같은 브랜드
카드가 떴다. 주간 카드(make_weekly_share)와 같은 방식으로 굽는다.
  - 크기 1200×675(16:9, 폭 1200 이상 — 요청서 D2 조건). 글자는 제목·기준월·가장 크게 오르고 내린 곳 두 줄뿐.
  - 타일 배치는 주간 카드(make_weekly_share.TILE)를 그대로 쓴다 — 두 카드의 지도가 매체마다 달라 보이지 않게.
  - 반올림·색은 사이트 표시값 기준(make_weekly_page.pv2r) — '0.00' 칸에 부호·색이 붙지 않는다.
  - 출력 경로와 기준월 판은 make_monthly_page(SHARE_REL·share_version)가 정본이다. 페이지 og:image 가 그 경로에
    ?v=기준월 을 붙여 가리킨다. PNG 메타 agongmap-basis 에 기준월을 심어 시험이 그림과 주소의 판을 맞춰 본다.
배치가 pytest 뒤 pillow 구역에서 돌린다(update-cloud.yml — make_weekly_share 다음). 출력은 매달 같은 이름으로 덮어쓴다.

사용: python tools/make_monthly_share.py
"""
import os
import sys

from PIL import Image, ImageDraw, PngImagePlugin

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import make_monthly_page as MP  # noqa: E402  (경로·기준월·표의 '변화가 큰 곳' 정본)
import make_weekly_page as MW   # noqa: E402  (반올림 정본)
import make_weekly_share as WS  # noqa: E402  (타일 배치·색·폰트)
import sido_zones as SZ         # noqa: E402

INK, PAPER, MUTED, LINE = WS.INK, WS.PAPER, WS.MUTED, WS.LINE
UP_INK, DN_INK = (143, 35, 24), (18, 60, 92)
REF = 1.0   # 색 진하기 상한(%p). 월간 변동은 주간(0.4)보다 크다


def load():
    return MP.load()


def _fmt(v):
    r = MW.pv2r(v)
    return '·' if r is None else (('%+.2f' % r) if r != 0 else '0.00')


def _ink(v):
    r = MW.pv2r(v) or 0
    return UP_INK if r > 0 else (DN_INK if r < 0 else MUTED)


def pick_top(val):
    """{지역: 그 달 매매 변동률} → ([가장 많이 오른 곳], [가장 많이 내린 곳]) — 각 한 곳(없으면 빈 목록).

    주간 카드(make_weekly_share.summary_top3, 전수리뷰 #84)와 같이 /weekly/ 정본 top3(MW.top3 — **원값** 정렬, 시도 목록
    MW.SIDO)를 쓴다(전수리뷰 B4). 예전엔 반올림한 표시값으로 정렬하고 동률은 원천 순서(ORDER)로 갈라, 두 시도가 같은 값으로
    반올림되는 달에 원값으로 덜 움직인 곳을 '가장 많이 오른 곳'으로 적었다.
    """
    up, dn = MW.top3([(z, val[z]) for z in MW.SIDO if val.get(z) is not None])
    return up[:1], dn[:1]


def draw(adv):
    """그 달 카드 그림과 기준월. 월간 시세가 없으면 SystemExit."""
    mo = adv.get('monthly') or {}
    rows, regs = mo.get('rows') or [], mo.get('regions') or []
    ver = MP.share_version(adv)
    if not rows or not ver:
        raise SystemExit('monthly share: 월간 시세가 없다 — 카드를 굽지 않는다')
    row = rows[-1]
    ma = row.get('ma') or []
    val = {r: ma[i] for i, r in enumerate(regs) if i < len(ma)}
    missing = [z for z in SZ.ORDER if z not in val]
    if missing:
        raise SystemExit('monthly share: 월간 계열에 없는 지역 %s — 그 칸이 조용히 빈다' % ', '.join(missing))

    IW, IH = MP.SHARE_SIZE
    img = Image.new('RGB', (IW, IH), PAPER)
    d = ImageDraw.Draw(img)
    noto = WS.noto

    # 왼쪽: 제목·기준월·가장 크게 오르고 내린 곳
    x0 = 64
    d.text((x0, 78), '이달의 아파트 시세', font=noto(48), fill=INK, anchor='ls')
    d.text((x0, 124), '%s · 매매가격 전월 대비(%%)' % MP.month_label(ver), font=noto(24, 'Medium'), fill=MUTED, anchor='ls')
    nat = val.get('전국')
    d.text((x0, 200), '전국', font=noto(26, 'Medium'), fill=MUTED, anchor='ls')
    d.text((x0, 272), '%s%%' % _fmt(nat), font=noto(64), fill=_ink(nat), anchor='ls')
    up, dn = pick_top(val)
    y = 350
    for lab, items, col in (('가장 많이 오른 곳', up, UP_INK), ('가장 많이 내린 곳', dn, DN_INK)):
        if not items:
            continue
        d.text((x0, y), lab, font=noto(22, 'Medium'), fill=MUTED, anchor='ls')
        d.text((x0, y + 42), '%s %s%%' % (items[0][0], _fmt(items[0][1])), font=noto(34), fill=col, anchor='ls')
        y += 100
    d.line((x0, IH - 96, 470, IH - 96), fill=LINE, width=2)
    d.text((x0, IH - 58), 'agongmap.co.kr/monthly', font=noto(26), fill=INK, anchor='ls')
    d.text((x0, IH - 26), '자료: 한국부동산원 전국주택가격동향조사(월간)', font=noto(17, 'Medium'), fill=MUTED, anchor='ls')

    # 오른쪽: 시도 타일 지도(주간 카드와 같은 배치)
    TW, TH, G = 150, 110, 10
    ox, oy = IW - 56 - (4 * TW + 3 * G), (IH - (5 * TH + 4 * G)) // 2
    for name, cx, cy in WS.TILE:
        px, py = ox + cx * (TW + G), oy + cy * (TH + G)
        v = val.get(name)
        d.rounded_rectangle((px, py, px + TW, py + TH), 14, fill=WS.cell_bg(v, REF), outline=LINE, width=2)
        d.text((px + TW // 2, py + 36), name, font=noto(26 if len(name) < 4 else 22), fill=INK, anchor='mm')
        d.text((px + TW // 2, py + 76), _fmt(v), font=noto(30), fill=_ink(v), anchor='mm')
    return img, ver


def main():
    adv, _ = load()
    img, ver = draw(adv)
    out = os.path.join(ROOT, *MP.SHARE_REL.split('/'))
    os.makedirs(os.path.dirname(out), exist_ok=True)
    meta = PngImagePlugin.PngInfo()
    meta.add_text('agongmap-basis', ver)   # og:image 주소의 판(?v=)과 같아야 한다 — 시험이 그림 대신 메타로 본다
    img.save(out, 'PNG', pnginfo=meta, optimize=True)
    print('wrote %s (%s)' % (os.path.relpath(out, ROOT), ver))
    # 페이지는 카드보다 먼저 구워져 지난 판(?v=)을 가리킨다 — 카드가 구워진 지금 판을 맞춘다(전수리뷰 #85).
    for rel in MP.restamp_share(ROOT):
        print('restamped %s (?v=%s)' % (rel, ver))


if __name__ == '__main__':
    main()
