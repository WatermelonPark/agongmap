# -*- coding: utf-8 -*-
"""투자자 테스트 점수별 공유 카드 11장 (800x800).

문구는 home-quiz.js QUIZSETS.investor(home_src 로 읽는다)와 톤을 맞춘다. 둘 중 하나를 고치면 같이 볼 것.
티어 구간(점수 하한)은 QUIZSETS.investor.grade 에서, 점수 분모·미터 칸·장 수·꼬리말 'N문항'은 QUIZ_LEN 에서 읽는다(전수리뷰 P-9).
숫자 줄(점수 + '/N' + 이모지)이 카드 좌우 여백(SIDE) 안에 들지 않으면 숫자를 폭에 맞춰 줄이고 줄 전체를 가운데 둔다 —
예전엔 두 자리 '10'의 줄 폭이 790px 라 큰 숫자가 x=2 부터 찍혀 카드 왼쪽 끝에 붙었다(전수리뷰 P-5).
이모지는 폰트(OS)에 의존하지 않도록 art_raw/emoji/ 에 PNG로 번들해 합성한다.

사용:  python tools/make_investor_cards.py
"""
import os, sys
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from make_beginner_cards import noto  # noqa: E402  (번들 폰트 로더 공유)
import home_src as HS  # noqa: E402  (퀴즈 정본 — QUIZ_LEN·grade)

W = H = 800
BG = (255, 255, 255)
INK = (22, 32, 58)
MUTED = (139, 133, 118)
SLASH = (200, 195, 183)
METER_ON = (31, 138, 112)
METER_OFF = (228, 224, 214)
BRAND = (192, 57, 43)          # 상단 바 · 헤더 알약

# 점수별 숫자 색 (0~10) — beginner/calc 카드와 같은 팔레트
SCORE_COLORS = [
    (178, 59, 46), (178, 59, 46), (192, 57, 43), (192, 57, 43), (207, 91, 42),
    (217, 154, 0), (217, 154, 0), (61, 154, 99), (31, 138, 112), (184, 134, 47),
    (184, 134, 47),
]

SIDE = 50                      # 숫자 줄의 좌우 여백(다른 요소 — 독수리 x=49 — 와 같은 선)

# 티어별 (도장 문구, 도장 색, 문구 2줄, 이모지 파일) — 낮은 등급부터. 구간은 QUIZSETS.investor.grade 의 하한에서 나온다(tiers()).
TIER_ART = [
    ('거꾸로 독법', (197, 73, 60),   ['호재를 악재로', '읽고 계시네요'],       'compass'),
    ('재도전 요망', (197, 73, 60),   ['부동산 뉴스,', '헤드라인만 보셨죠?'],   'sweat'),
    ('반쯤 고수',   (220, 162, 20),  ['감은 있어요.', '계약은 아직 이르지만'], 'moon'),
    ('고수 인정',   (49, 146, 122),  ['머릿속엔 이미', '다주택자시네요'],      'cool'),
    ('업자 의심',   (197, 73, 60),   ['이걸 다 맞히네...', '혹시 업자세요?'],   'trophy'),
]


def tiers(src=None):
    """[(점수 구간 range, 도장, 색, 두 줄, 이모지)] — 구간은 QUIZSETS.investor.grade 하한, 끝은 QUIZ_LEN."""
    src = HS.home_source() if src is None else src
    los = [g[0] for g in HS.quiz_grades('investor', src)]
    if len(los) != len(TIER_ART):
        raise SystemExit('투자자 등급 %d개, 카드 티어 %d개 — TIER_ART 를 등급 수에 맞출 것' % (len(los), len(TIER_ART)))
    ends = los[1:] + [HS.quiz_len(src) + 1]
    return [(range(a, b),) + art for a, b, art in zip(los, ends, TIER_ART)]


TIERS = tiers()
QUIZ_N = HS.quiz_len()

ART = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'art_raw', 'emoji')


def tier_of(score):
    for rng, stamp, col, lines, emo in TIERS:
        if score in rng:
            return stamp, col, lines, emo
    raise ValueError(score)


def fit_h(text, target_h, weight='Bold', lo=8, hi=520):
    """글자 높이가 target_h가 되는 폰트 크기를 이분 탐색."""
    best = noto(lo, weight)
    while lo <= hi:
        mid = (lo + hi) // 2
        f = noto(mid, weight)
        b = f.getbbox(text)
        h = b[3] - b[1]
        if h <= target_h:
            best = f
            lo = mid + 1
        else:
            hi = mid - 1
    return best


def draw_centered(d, cx, cy, text, font, fill):
    b = d.textbbox((0, 0), text, font=font)
    d.text((cx - (b[2] - b[0]) / 2 - b[0], cy - (b[3] - b[1]) / 2 - b[1]), text, font=font, fill=fill)


def stamp_img(text, color):
    """살짝 기울어진 테두리 도장."""
    f = fit_h(text, 43, 'Bold')
    tmp = Image.new('RGBA', (10, 10)); td = ImageDraw.Draw(tmp)
    b = td.textbbox((0, 0), text, font=f)
    tw, th = b[2] - b[0], b[3] - b[1]
    padx, pady = 37, 26
    bw, bh = tw + padx * 2, th + pady * 2
    im = Image.new('RGBA', (bw, bh), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.rounded_rectangle([2, 2, bw - 3, bh - 3], radius=16, outline=color + (255,), width=5)
    d.text((padx - b[0], pady - b[1]), text, font=f, fill=color + (255,))
    return im.rotate(7, expand=True, resample=Image.BICUBIC)


def make_card(score, out):
    stamp, scol, lines, emo = tier_of(score)
    im = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(im)

    # 상단 바
    d.rectangle([0, 0, W, 14], fill=BRAND)

    # 헤더: 독수리 + 알약
    eagle = os.path.join(ART, 'eagle.png')
    if os.path.exists(eagle):
        e = Image.open(eagle).convert('RGBA')
        im.paste(e, (49, 51), e)
    d.rounded_rectangle([114, 46, 347, 100], radius=27, fill=BRAND)
    draw_centered(d, (114 + 347) // 2, (46 + 100) // 2, '투자자 테스트', fit_h('투자자 테스트', 26, 'Bold'), (255, 255, 255))

    # 도장 (우상단)
    st = stamp_img(stamp, scol)
    im.paste(st, (int(608 - st.width / 2), int(104 - st.height / 2)), st)

    # 숫자 + /N  (아래 정렬, 그룹 중심 x≈265)
    num, frac = str(score), '/%d' % QUIZ_N
    fnum = fit_h(num, 256, 'Bold')
    fsl = fit_h(frac, 73, 'Bold')
    bn = d.textbbox((0, 0), num, font=fnum)
    bs = d.textbbox((0, 0), frac, font=fsl)
    nw, sw = bn[2] - bn[0], bs[2] - bs[0]
    gap, egap = 32, 70
    p = os.path.join(ART, '%s.png' % emo)
    e = Image.open(p).convert('RGBA') if os.path.exists(p) else None
    ew = e.width if e is not None else 0
    gx = 265 - (nw + gap + sw) / 2            # 그룹 왼쪽
    if gx < SIDE or gx + nw + gap + sw + egap + ew > W - SIDE:
        # 두 자리 점수: 줄(숫자·분모·이모지)이 여백 안에 들게 숫자를 폭으로 맞추고 줄 전체를 가운데 둔다
        room = W - 2 * SIDE - (gap + sw + egap + ew)
        lo, hi = 8, fnum.size
        while lo < hi:
            mid = (lo + hi + 1) // 2
            b = d.textbbox((0, 0), num, font=noto(mid, 'Bold'))
            lo, hi = (mid, hi) if b[2] - b[0] <= room else (lo, mid - 1)
        fnum = noto(lo, 'Bold')
        bn = d.textbbox((0, 0), num, font=fnum)
        nw = bn[2] - bn[0]
        gx = (W - (nw + gap + sw + egap + ew)) / 2
    d.text((gx - bn[0], 479 - bn[3]), num, font=fnum, fill=SCORE_COLORS[score])
    d.text((gx + nw + gap - bs[0], 448 - bs[3]), frac, font=fsl, fill=SLASH)

    # 이모지 (숫자 오른쪽)
    if e is not None:
        ex = int(gx + nw + gap + sw + egap)
        im.paste(e, (ex, int(310 - e.height / 2)), e)

    # 점 미터 (QUIZ_N 개)
    r, sp = 11, 40
    x0 = 400 - ((QUIZ_N - 1) * sp) / 2
    for i in range(QUIZ_N):
        cx = x0 + i * sp
        d.ellipse([cx - r, 525 - r, cx + r, 525 + r], fill=METER_ON if i < score else METER_OFF)

    # 문구 2줄
    f1 = fit_h(lines[0], 54, 'Bold')
    if d.textbbox((0, 0), lines[0], font=f1)[2] > 700:
        f1 = fit_h(lines[0], 44, 'Bold')
    draw_centered(d, 400, 609, lines[0], f1, INK)
    f2 = fit_h(lines[1], 54, 'Bold')
    if d.textbbox((0, 0), lines[1], font=f2)[2] > 700:
        f2 = fit_h(lines[1], 44, 'Bold')
    draw_centered(d, 400, 680, lines[1], f2, INK)

    # 푸터
    left, right = '%d문항 2지선다 · 5분 · ' % QUIZ_N, 'agongmap.co.kr'
    ffoot = fit_h(left + right, 25, 'Medium')
    fb = noto(ffoot.size, 'Bold')
    lw = d.textbbox((0, 0), left, font=ffoot)[2] - d.textbbox((0, 0), left, font=ffoot)[0]
    rw = d.textbbox((0, 0), right, font=fb)[2] - d.textbbox((0, 0), right, font=fb)[0]
    sx = 400 - (lw + rw) / 2
    bl = d.textbbox((0, 0), left, font=ffoot)
    d.text((sx - bl[0], 748 - (bl[3] - bl[1]) / 2 - bl[1]), left, font=ffoot, fill=MUTED)
    br = d.textbbox((0, 0), right, font=fb)
    d.text((sx + lw - br[0], 748 - (br[3] - br[1]) / 2 - br[1]), right, font=fb, fill=MUTED)

    im.save(out, 'PNG')
    return True


if __name__ == '__main__':
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    share = os.path.join(root, 'share')
    os.makedirs(share, exist_ok=True)
    for s in range(QUIZ_N + 1):
        make_card(s, os.path.join(share, 'investor-%d.png' % s))
    print('%d cards written -> %s' % (QUIZ_N + 1, share))
