# -*- coding: utf-8 -*-
"""콘텐츠 글의 공유 카드(og:image) — `share/post-<섹션>-<slug>.png` (백로그 50, 대표 결정 ② 2026-10-26).

왜 생성기와 따로 도나. 카드는 pillow 로 그리는데 배치의 생성기 단계는 pip 앞에서 돌아 표준 라이브러리만
쓴다. 그래서 주간 공유 카드(make_weekly_share)처럼 **시험을 통과한 뒤** 이 도구가 따로 굽는다. 카드가 없는
글은 섹션 공통 카드로 떨어지고, 그것도 없으면 브랜드 카드로 떨어진다 — 미리보기가 비는 일은 없다.

카드에는 **숫자를 넣지 않는다.** 제목·분류·지역만 그린다. 그래야 카드가 원고가 바뀔 때만 달라지고,
페이지는 카드 파일을 읽지 않고도 `?v=<updated>` 로 판을 붙일 수 있다(카드와 페이지의 생성 순서가 서로
묶이지 않는다). 숫자를 담으면 데이터가 바뀐 날마다 카드와 페이지를 같은 순서로 다시 구워야 한다.

사용:
    python tools/make_content_cards.py          원고 전부(바뀐 것만 다시 그린다)
"""
import io
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

from PIL import Image, ImageDraw, PngImagePlugin  # noqa: E402

import content_md as CM            # noqa: E402  (원고 읽기)
import make_zone_cards as ZC       # noqa: E402  (카드 글꼴·색·크기의 정본 — 지역 카드와 한 계열로 보이게)
import make_content_pages as MC    # noqa: E402  (섹션 이름표 SECTION_META)

W, H = ZC.W, ZC.H
OUT_DIR = os.path.join(ROOT, 'share')
MX = 64                            # 좌우 여백(지역 카드와 같다)
FOOT = 'agongmap.co.kr'


def card_rel(section, slug):
    """카드의 저장소 상대 경로. 페이지 생성기도 이 함수로 같은 이름을 만든다."""
    return 'share/post-%s-%s.png' % (section, slug)


THUMB_W, THUMB_H = 480, 252      # 16:9에 가까운 목록용 판(원본 1200×630의 0.4배)


def thumb_rel(section, slug):
    """목록용 썸네일 경로 — 정본은 페이지 생성기(MC.thumb_rel, pillow 없이 도는 쪽)다."""
    return MC.thumb_rel(section, slug)


QUOTE_MAX = 16           # 인용 한 줄의 글자 수 상한(총괄: 10자 안팎)


def _quote(title):
    """제목에서 따옴표 안 발언을 뽑는다. 없으면 None — 그 글은 막대만 그린다."""
    import re
    for m in re.finditer(r"['\u2018\u2019\"\u201c\u201d]([^'\u2018\u2019\"\u201c\u201d]{3,%d})['\u2018\u2019\"\u201c\u201d]" % QUOTE_MAX, title):
        return m.group(1).strip()
    return None


def thumb_args(meta, body):
    """그 글의 썸네일에 그릴 moveins 자리표 인자를 **글이 쓴 순서대로**.

    `chart:moveins` 를 먼저 본다 — 글쓴이가 '이 글의 그림'으로 고른 자리표라, 글이 말하는 지역과 해가 거기
    들어 있다. 그다음이 table·v 의 moveins, 마지막이 프런트매터 region 이다.

    ⚠️ region 을 먼저 보면 안 된다. 단지·GTX·반박 편의 region 은 시도('경기')라, 수원 단지 글과 서울을
       따지는 반박 글이 **똑같은 경기 막대**를 달고 나갔다(총괄 지적 2026-10-30). 글이 가리키는 가장 좁은
       지역은 자리표에 있다.
    """
    import content_tables as CT
    text = (body or '') + ' ' + (meta.get('summary') or '')
    first, rest = [], []
    for pre, inner in CT.PH.findall(text):
        parts = [p.strip() for p in inner.split(':') if p.strip()]
        if len(parts) < 2 or parts[0] != 'moveins':
            continue
        (first if pre == 'chart' else rest).append(parts[1:])
    region = (meta.get('region') or '').strip()
    return first + rest + ([[region]] if region else [])


def _thumb_source(meta, body, data):
    """썸네일에 그릴 (막대 묶음, 큰 숫자). 어느 지역인지는 thumb_args 가 고른다."""
    import content_tables as CT
    for args in thumb_args(meta, body):
        try:
            spec = CT.chart(data, 'moveins', args[:2])
        except CT.TableError:
            continue
        big = None
        for lab, val in spec.get('cards') or []:
            if '입주' in lab or '적정' in lab:
                big = (val, lab)
                break
        return spec, big
    return None, None


def draw_thumb(spec, big=None, quote=None):
    """목록 그림 한 장(480×252). 제목은 넣지 않는다 — 목록에서 바로 옆에 있다.

    위쪽에 큰 숫자 하나(또는 발언 인용), 아래쪽에 연도별 입주 막대와 적정 기준선. 막대는 OG 카드·본문
    그림과 같은 데이터(content_tables.chart)라 세 곳이 어긋나지 않는다.
    """
    W, H = THUMB_W, THUMB_H
    img = Image.new('RGB', (W, H), ZC.PAPER)
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 6], fill=ZC.INK)
    pad = 18
    top_h = 86
    if quote:
        f = ZC.fit_width('\u201c%s\u201d' % quote, W - pad * 2, hi=40, lo=20)
        bb = d.textbbox((0, 0), '\u201c%s\u201d' % quote, font=f)
        d.text((pad - bb[0], 30 - bb[1]), '\u201c%s\u201d' % quote, font=f, fill=ZC.INK)
    elif big:
        val, lab = big
        f = ZC.fit_width(val, W - pad * 2, hi=52, lo=24)
        bb = d.textbbox((0, 0), val, font=f)
        d.text((pad - bb[0], 24 - bb[1]), val, font=f, fill=ZC.INK)
        lf = ZC.font(18, 'Medium')
        d.text((pad, 24 + (bb[3] - bb[1]) + 8), lab, font=lf, fill=ZC.MUTED)
    if not spec:
        return img
    pts = spec['series'][0]['points']
    rule = spec.get('rule')
    top = max([v for _, v in pts] + ([rule[0]] if rule and rule[0] else [0])) or 1
    plot_t, plot_b = top_h + 18, H - 26
    plot_h = plot_b - plot_t
    gap = 6
    bw = min(46.0, max(8.0, (W - pad * 2 - gap * (len(pts) - 1)) / float(len(pts))))
    x0 = max(pad, W - pad - (bw * len(pts) + gap * (len(pts) - 1)))
    for i, (lab, v) in enumerate(pts):
        x = x0 + i * (bw + gap)
        hh = max(2.0, v / float(top) * plot_h)
        over = rule and rule[0] and v >= rule[0]
        d.rectangle([x, plot_b - hh, x + bw, plot_b], fill=ZC.INK if over else ZC.LINE)
        if bw >= 22:
            yf = ZC.font(13, 'Medium')
            yb = d.textbbox((0, 0), str(lab)[2:], font=yf)
            d.text((x + bw / 2 - (yb[2] - yb[0]) / 2, plot_b + 5), str(lab)[2:], font=yf, fill=ZC.MUTED)
    if rule and rule[0]:
        ry = plot_b - rule[0] / float(top) * plot_h
        for sx in range(int(pad), W - pad, 8):
            d.line([sx, ry, sx + 4, ry], fill=ZC.MUTED, width=1)
    return img


def save_thumb(card_img, rel):
    """카드를 줄여 JPEG 로. webp 가 아니라 jpg 인 까닭: 오래된 카톡 미리보기·메일 클라이언트까지 연다."""
    out = os.path.join(ROOT, rel)
    im = card_img.convert('RGB').resize((THUMB_W, THUMB_H), Image.LANCZOS)
    body = io.BytesIO()
    im.save(body, 'JPEG', quality=82, optimize=True, progressive=True)
    data = body.getvalue()
    if os.path.exists(out) and io.open(out, 'rb').read() == data:
        return False
    io.open(out, 'wb').write(data)
    return True


def section_rel(section):
    """섹션 공통 카드 — 글별 카드가 없을 때 떨어지는 자리."""
    return 'share/section-%s.png' % section


def _font_misses(text):
    """카드 글꼴에 없는 글자. 두부(□)가 박힌 카드를 퍼뜨리지 않으려고 먼저 본다.

    fontTools 가 없으면 **검사를 건너뛴다**(빈 목록). 그 묶음은 배치에 깔려 있지 않을 수 있는데, 글자 검사
    하나 때문에 카드 전체가 안 그려지면 손해가 더 크다 — 2026-10-29 발행이 그렇게 죽어 반박 4편이 묶였다.
    워크플로에는 fonttools 를 함께 깔아 두었으므로 평소에는 검사가 돈다.
    """
    try:
        from fontTools.ttLib import TTFont
    except ImportError:
        sys.stderr.write('⚠️ fontTools 가 없어 글꼴 글자 검사를 건너뛴다(카드는 그린다)\n')
        return []
    cmap = set(TTFont(os.path.join(ZC.FONT_DIR, ZC.FONT_FILES['Bold'])).getBestCmap())
    return sorted({c for c in text if ord(c) > 0x20 and ord(c) not in cmap})


def wrap(draw, text, fnt, width, max_lines):
    """어절 단위로 줄을 나눈다. 한 어절이 폭을 넘으면 글자 단위로 자른다(긴 괄호 묶음·주소가 그렇다).

    max_lines 를 넘으면 마지막 줄 끝에 '…' 를 붙인다 — 제목이 잘렸다는 것을 읽는 사람이 알게.
    """
    def w(s):
        bb = draw.textbbox((0, 0), s, font=fnt)
        return bb[2] - bb[0]
    lines, cur = [], ''
    for word in text.split(' '):
        while w(word) > width:                 # 한 어절이 한 줄보다 길다
            cut = len(word)
            while cut > 1 and w(word[:cut]) > width:
                cut -= 1
            if cur:
                lines.append(cur)
                cur = ''
            lines.append(word[:cut])
            word = word[cut:]
        trial = (cur + ' ' + word).strip()
        if cur and w(trial) > width:
            lines.append(cur)
            cur = word
        else:
            cur = trial
    if cur:
        lines.append(cur)
    if len(lines) > max_lines:
        lines = lines[:max_lines]
        last = lines[-1]
        while last and w(last + '…') > width:
            last = last[:-1]
        lines[-1] = last + '…'
    return lines


def _chip(d, text):
    """왼쪽 위 분류 칩(지역 카드와 같은 모양)."""
    cf = ZC.font(28, 'Bold')
    bb = d.textbbox((0, 0), text, font=cf)
    cw, ch = bb[2] - bb[0], bb[3] - bb[1]
    px, py = 22, 13
    d.rounded_rectangle([MX, 66, MX + cw + px * 2, 66 + ch + py * 2], radius=6, fill=ZC.INK)
    d.text((MX + px - bb[0], 66 + py - bb[1]), text, font=cf, fill=ZC.WHITE)
    return 66 + ch + py * 2


def _foot(d, left_text):
    fy = 548
    d.line([MX, fy, W - MX, fy], fill=ZC.LINE, width=2)
    if left_text:
        d.text((MX, fy + 24), left_text, font=ZC.font(24, 'Medium'), fill=ZC.MUTED)
    df = ZC.font(26, 'Bold')
    bb = d.textbbox((0, 0), FOOT, font=df)
    d.text((W - MX - (bb[2] - bb[0]), fy + 22), FOOT, font=df, fill=ZC.RED)


def draw_card(title, chip, foot_left):
    """제목 카드 한 장. 제목 크기는 줄 수에 맞춰 줄인다(긴 제목도 세 줄 안에 들어오게)."""
    img = Image.new('RGBA', (W, H), ZC.PAPER + (255,))
    d = ImageDraw.Draw(img)
    d.rectangle([0, 0, W, 13], fill=ZC.INK)
    top = _chip(d, chip)
    avail = W - MX * 2
    for size, max_lines in ((64, 3), (56, 3), (50, 4), (44, 4)):
        fnt = ZC.font(size, 'Bold')
        lines = wrap(d, title, fnt, avail, max_lines)
        if len(lines) <= max_lines - (1 if size > 50 else 0) or size == 44:
            break
    # 제목 블록을 칩과 바닥 선 사이 가운데에 둔다. 위에 붙이면 두 줄짜리 제목에서 아래가 휑하다.
    step = int(size * 1.42)
    block = step * len(lines)
    y = max(top + 40, top + 40 + ((548 - 40) - (top + 40) - block) // 2)
    for ln in lines:
        bb = d.textbbox((0, 0), ln, font=fnt)
        d.text((MX - bb[0], y - bb[1]), ln, font=fnt, fill=ZC.INK)
        y += step
    _foot(d, foot_left)
    return img, lines


def save(img, rel, texts):
    """PNG 글 칸에 그린 글자를 함께 싣는다 — 시험이 커밋된 카드와 지금 원고를 맞댄다(그림은 못 읽는다)."""
    out = os.path.join(ROOT, rel)
    meta = PngImagePlugin.PngInfo()
    for k, v in texts.items():
        meta.add_text(k, v)
    body = io.BytesIO()
    img.convert('RGB').save(body, 'PNG', optimize=True, pnginfo=meta)
    data = body.getvalue()
    if os.path.exists(out) and io.open(out, 'rb').read() == data:
        return False
    if not os.path.isdir(os.path.dirname(out)):
        os.makedirs(os.path.dirname(out))
    io.open(out, 'wb').write(data)
    return True


def main(argv=None):
    posts = CM.posts(ROOT)
    if not posts:
        print('content cards: 원고가 없다 — 아무것도 바꾸지 않는다')
        return 0
    import content_tables as CT
    data = CT.load()          # 썸네일 막대가 쓰는 자료 — 글마다 다시 읽지 않는다
    wrote, skipped, secs = 0, [], set()
    for sec, slug, path in posts:
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError as e:
            skipped.append(str(e))
            continue
        try:
            title = CT.fill_inline(meta['title'], data)
        except Exception:
            title = meta['title']
        miss = _font_misses(title)
        if miss:
            # 두부가 박힌 카드를 퍼뜨리지 않는다. 그 글은 섹션 공통 카드로 떨어진다.
            skipped.append('%s/%s: 카드 글꼴에 없는 글자 %s' % (sec, slug, ''.join(miss)))
            continue
        chip = MC.SECTION_META[sec][0]
        img, lines = draw_card(title, chip, (meta.get('region') or '').strip())
        if save(img, card_rel(sec, slug), {'title': title, 'chip': chip, 'lines': '\n'.join(lines)}):
            wrote += 1
        spec, big = _thumb_source(meta, body, data)
        th = draw_thumb(spec, big, _quote(title) if sec == 'column' else None)
        if save_thumb(th, thumb_rel(sec, slug)):
            wrote += 1
        secs.add(sec)
    for sec in sorted(secs):
        name, desc = MC.SECTION_META[sec][0], MC.SECTION_META[sec][1]
        img, lines = draw_card(desc, name, '')
        if save(img, section_rel(sec), {'title': desc, 'chip': name, 'lines': '\n'.join(lines)}):
            wrote += 1
    for why in skipped:
        sys.stderr.write('⚠️ 카드를 건너뛴다 — %s\n' % why)
    print('content cards: %d장 새로 그림 · 글 %d편 · 섹션 %d개%s'
          % (wrote, len(posts) - len(skipped), len(secs),
             (' · 건너뜀 %d' % len(skipped)) if skipped else ''))
    return 0


if __name__ == '__main__':
    sys.exit(main())
