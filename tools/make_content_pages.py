# -*- coding: utf-8 -*-
"""콘텐츠 섹션 생성기 — `content/<섹션>/<slug>.md` → `/<섹션>/<slug>/` (백로그 50, 요청서 2026-10-26).

왜: 네이버 블로그 글이 색인에서 빠지는 일이 반복돼(10-24 이후 새 글 다수), 정보 가치가 있는 글의 정본을
사이트로 옮긴다. 목표는 AI 검색(네이버 AI 브리핑·구글·ChatGPT·Perplexity) 인용이라, 페이지마다 한 문단
요약·날짜·저자·출처·구조화 데이터를 생성기가 넣는다.

지키는 것
  - **손으로 고치는 출력물이 없다.** 모든 문구는 여기서 찍는다. 원고(content/*.md)만 사람이 쓴다.
  - **숫자는 자리표로.** 본문의 사이트 데이터 숫자는 `{{table:...}}`·`{{v:...}}`(content_tables)로 적고,
    생성기가 매 배치 채운다. 모르는 자리표·없는 지역은 실패다(빈 표를 내보내지 않는다).
  - 날짜는 프런트매터(date·updated)에서만 온다. 오늘 날짜를 읽지 않는다 — 같은 입력이면 같은 바이트.
  - 뼈대·머리·탭바·랜드마크는 make_indicator_pages.SHELL/fill 을 그대로 쓴다(/moveins/ 와 같은 집).

실행: python tools/make_content_pages.py   # 생성 + sitemap 갱신. 원고가 없으면 아무것도 바꾸지 않는다.
"""
import html
import io
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, 'tools'))

import content_md as CM            # noqa: E402  (프런트매터·원고 읽기)
import content_tables as CT        # noqa: E402  (자리표 → 사이트 데이터)
import make_indicator_pages as I   # noqa: E402  (뼈대 SHELL·fill·sitemap 갱신)
import make_sido_pages as SP       # noqa: E402  (keep_dates — 내용이 같으면 옛 날짜 유지)
import home_src as HS             # noqa: E402  (홈 파일 위치의 정본 — 백로그 10)
import site_nav as N              # noqa: E402  (탭바·뒤 단계 표식 구간 LATE_SLOTS 의 정본)

SITE = I.SITE
AUTHOR = '아공맵 운영팀'
# 면책은 공용 푸터(site_nav.site_footer)가 싣는다 — 글 끝에 같은 문장을 또 두면 두 번 연달아 나왔다(2026-10-31 디자인 리뷰 2차).
OG_IMAGE = '/og-brand.png'   # 어느 카드도 없을 때 떨어지는 자리


def card_rel(section, slug):
    """글별 공유 카드의 저장소 상대 경로. 카드를 굽는 쪽(make_content_cards)도 이 함수를 쓴다 —
    경로 규칙이 두 벌이면 한쪽만 고쳐져 og:image 가 없는 파일을 가리킨다."""
    return 'share/post-%s-%s.png' % (section, slug)


def thumb_rel(section, slug):
    """목록용 썸네일의 저장소 상대 경로. 굽는 쪽(make_content_cards)도 이 함수를 쓴다. 여기 두는 까닭: 이 생성기는 배치에서
    pillow 를 깔기 전에 돈다 — 경로 하나를 얻으려고 카드 생성기(모듈 맨 위에서 PIL 을 들인다)를 불러오면 그 단계가
    ModuleNotFoundError 로 멈춘다(test_test_deps_are_installed)."""
    return 'share/thumb-%s-%s.jpg' % (section, slug)


def section_card_rel(section):
    """섹션 공통 카드 — 글별 카드가 없을 때."""
    return 'share/section-%s.png' % section


def og_image(meta, root=ROOT):
    """글의 og:image 주소. 글별 카드 → 섹션 공통 카드 → 브랜드 카드 순으로 떨어진다.

    판(?v=)은 원고의 updated 다. 카드는 제목·분류·지역만 그리므로 **원고가 바뀔 때만** 달라진다 — 그래서
    카드 파일의 해시를 읽지 않아도 되고, 카드(게이트 뒤)와 페이지(게이트 앞)의 생성 순서가 서로 묶이지
    않는다. 숫자를 담은 카드였다면 데이터가 바뀐 날마다 둘을 같은 순서로 다시 구워야 했다.
    카드가 아직 없는 회차(새 글이 올라온 날)에도 미리보기가 비지 않게 두 단계로 떨어진다.
    """
    for rel in (card_rel(meta['section'], meta['slug']), section_card_rel(meta['section'])):
        if os.path.exists(os.path.join(root, rel)):
            return '%s/%s?v=%s' % (SITE, rel, meta['updated'])
    return SITE + OG_IMAGE

# 섹션 이름은 content_md.TOPICS 의 짧은 이름에서 온다(칩 = 빵부스러기 = <title> = og = 카드 = llms). 여기에는 소개 한 줄만 적는다.
_SECTION_DESC = {
    'city': '도시별 입주물량과 공급 흐름을 국가 통계로 읽습니다.',
    'gtx': 'GTX 노선과 역세권 아파트 공급을 국가 통계로 읽습니다.',
    'danji': '재건축·리모델링 단지를 공급 데이터와 함께 봅니다.',
    'column': '공직자·정치인 발언을 입주 물량과 시세로 따집니다.',
}
SECTION_META = {sec: (short, _SECTION_DESC[sec]) for _k, _q, short, sec in CM.TOPICS}
assert set(SECTION_META) == set(CM.SECTIONS), '섹션 목록이 content_md 와 다르다'


# 화면 날짜는 두 단계 정본(sido_zones.day_long·day_short — CLAUDE.md '날짜는 두 단계로 쓴다'). 글 머리의 작성·갱신일은 해를
# 넘겨 읽히는 자리라 '2026년 10월 30일', 목록·카드 메타는 좁은 자리라 '26.10.30'. JSON-LD·RSS·sitemap 은 ISO 그대로다.
# (2026-10-30 디자인 리뷰 — 목록·머리가 '2026-10-30 갱신' ISO 꼴이었다)
def _day_long(iso):
    import sido_zones as SZ
    return SZ.day_long(iso)


def _day_short(iso):
    import sido_zones as SZ
    return SZ.day_short(iso)


# ── 마크다운 (우리가 쓰는 부분집합) ─────────────────────────────────────────
def _inline(t):
    """인라인 서식. 먼저 이스케이프하고, 그 위에 굵게·코드·링크만 되살린다."""
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    # 속성에 들어가는 조각(주소·대체글)만 큰따옴표를 &quot; 로 바꾼다 — 본문 글자의 따옴표는 그대로 둔다(위에서 quote=False).
    # 안 바꾸면 `![그는 "오른다"고 했다](…)` 가 alt="그는 "오른다"고 했다" 로 나가 속성이 끊긴다(2026-11-13 전수 리뷰).
    q = lambda s: s.replace('"', '&quot;')      # noqa: E731
    t = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)',
               lambda m: '<img src="%s" alt="%s" loading="lazy">' % (q(m.group(2)), q(m.group(1))), t)
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', lambda m: '<a href="%s">%s</a>' % (q(m.group(2)), m.group(1)), t)
    return t


# ── 그림(인라인 SVG) ────────────────────────────────────────────────────────
# 이미지 파일이 아니라 인라인 SVG 다(요청 ①, 총괄 10-27). 그래야 배치가 페이지를 다시 구울 때 숫자가 따라
# 오고, 다크 모드도 CSS 변수로 따라온다. 색만으로 계열을 가르지 않는다 — 매매는 실선, 전세는 점선이다.
CH_W, CH_BAR_H, CH_LINE_H = 640, 210, 190       # viewBox 크기(폭은 CSS 로 100% 가 된다)
# 그림 글자 크기(viewBox 단위). 데스크톱 기본이 17, 휴대폰 가장 좁은 화면이 32(EXTRA_CSS 미디어 규칙과 같은 값 — 시험이 대조한다).
CH_UNIT, CH_UNIT_MAX = 17, 32
CH_EM = 0.6               # 숫자 한 글자 폭 ≈ 0.6em(Pretendard 숫자·쉼표 어림, 넉넉하게)


def _svg_open(spec, h, cls=''):
    # preserveAspectRatio 를 건드리지 않는다 — 'none' 으로 늘리면 좁은 화면에서 글자와 선 굵기가 함께
    # 늘어나 뭉갠다. 폭은 CSS(width:100%)가 맞추고 높이는 비율대로 따라온다.
    return ('<svg viewBox="0 0 %d %d" role="img" aria-label="%s" class="cchart-svg%s">'
            % (CH_W, h, html.escape(spec['alt']), cls))


def _anchor(cx, txt, lo, hi):
    """가운데 맞춤 글자가 그림 밖으로 나가면 끝 맞춤으로 — (x, 맞춤 클래스). 가장 큰 단위(휴대폰 32)로 잰다.

    마지막 막대 값 '15,287'이 375px 에서 오른쪽 끝이 잘려 '15,28'로 읽혔다(2026-11-07 디자인 검수, 치명). 맞춤은 클래스로
    준다(CSS 의 text-anchor 가 SVG 속성을 이긴다 — _lines_svg 주석)."""
    half = len(txt) * CH_EM * CH_UNIT_MAX / 2.0
    if cx + half > CH_W - 2:
        return hi, ' cx-e'
    if cx - half < 2:
        return lo, ' cx-s'
    return cx, ''


def _bars_svg(spec):
    pts = spec['series'][0]['points']
    rule = spec.get('rule')
    # 값이 None 인 해는 막대 없이 자리만 두고 '없음'을 적는다(CT.NO_MOVEIN — 공개 목록에 그 해 입주가 없다, 2026-11-12 대표 결정).
    top = max([v for _, v in pts if v is not None] + ([rule[0]] if rule and rule[0] else [0])) or 1
    # 위 여백은 휴대폰 글자(viewBox 단위 26, .cb-v)가 가장 높은 막대 위에서 잘리지 않을 만큼 둔다. 아래 여백은 휴대폰 x 축
    # 글자(26~32 단위) 윗선이 막대 밑단에 붙지 않을 만큼(2026-11-07 디자인 검수 — 26 이라 연도 글자 위로 막대가 덮였다).
    pad_l, pad_b, pad_t = 8, 40, 30
    plot_h = CH_BAR_H - pad_b - pad_t
    gap = 10
    # 막대가 두세 개뿐인 해(구미는 2027·2029 둘)에 폭을 다 나눠 가지면 화면을 꽉 메운 덩어리가 된다.
    # 폭에 상한을 두고 남는 자리는 가운데로 모은다.
    bw = min(72.0, max(14.0, (CH_W - pad_l * 2 - gap * (len(pts) - 1)) / float(len(pts))))
    used = bw * len(pts) + gap * (len(pts) - 1)
    pad_l = max(pad_l, (CH_W - used) / 2.0)
    # 막대가 많으면 값을 다 적을 자리가 없다(경기 13개에서 숫자가 서로 겹쳤다). 좁아지면 가장 큰 해와
    # 마지막 해만 적는다 — 나머지 숫자는 바로 아래 표와 대체 텍스트에 있다.
    tight = bw < 34
    keep = {max(range(len(pts)), key=lambda i: pts[i][1] or 0), len(pts) - 1}
    # 데스크톱 기본 단위(17)로도 값 글자가 막대 간격보다 넓으면 화면 폭과 상관없이 대표 둘만 적는다(cb-dense).
    widest = max(len(CT.num(v)) for _, v in pts if v is not None)
    dense = widest * CH_EM * CH_UNIT > bw + gap
    out = [_svg_open(spec, CH_BAR_H, ' cb-dense' if dense else '')]
    for i, (lab, v) in enumerate(pts):
        x = pad_l + i * (bw + gap)
        if v is None:
            tx, al = _anchor(x + bw / 2, '없음', x, x + bw)
            out.append('<text x="%.1f" y="%.1f" class="cb-v cb-k cb-none%s">없음</text>' % (tx, pad_t + plot_h - 4, al))
            odd = len(pts) > 6 and (len(pts) - 1 - i) % 2 == 1
            tx, al = _anchor(x + bw / 2, str(lab), x, x + bw)
            out.append('<text x="%.1f" y="%d" class="cb-x%s%s">%s</text>'
                       % (tx, CH_BAR_H - 8, ' cb-x2' if odd else '', al, html.escape(str(lab))))
            continue
        hh = max(1.0, v / float(top) * plot_h)
        y = pad_t + plot_h - hh
        over = rule and rule[0] and v >= rule[0]
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" class="cb%s"/>'
                   % (x, y, bw, hh, ' cb-over' if over else ''))
        # 휴대폰에서는 글자를 키우는 대신(.cb-* 미디어 규칙) 가장 큰 해·마지막 해(cb-k)만 값을 적고, 막대가 여섯 개를
        # 넘으면 x 축 이름을 하나 걸러 적는다(cb-x2) — 커진 글자끼리 겹치지 않게(2026-10-31 디자인 리뷰 2차).
        if not tight or i in keep:
            txt = CT.num(v)
            tx, al = _anchor(x + bw / 2, txt, x, x + bw)
            out.append('<text x="%.1f" y="%.1f" class="cb-v%s%s">%s</text>'
                       % (tx, y - 4, ' cb-k' if i in keep else '', al, html.escape(txt)))
        odd = len(pts) > 6 and (len(pts) - 1 - i) % 2 == 1
        tx, al = _anchor(x + bw / 2, str(lab), x, x + bw)
        out.append('<text x="%.1f" y="%d" class="cb-x%s%s">%s</text>'
                   % (tx, CH_BAR_H - 8, ' cb-x2' if odd else '', al, html.escape(str(lab))))
    if rule and rule[0]:
        ry = pad_t + plot_h - rule[0] / float(top) * plot_h
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="cb-rule"/>'
                   % (6, ry, CH_W - 6, ry))
        out.append('<text x="%d" y="%.1f" class="cb-rl cx-e">%s</text>'
                   % (CH_W - 8, max(26, ry - 5), html.escape(rule[1])))
    out.append('</svg>')
    return ''.join(out)


def _pct_tick(v):
    """눈금 글자 — 변동률 표기 정본(content_tables.pct, 소수 둘째 자리·표시값 부호)에 '%'. 0 은 '0'."""
    t = CT.pct(v)
    return '0' if t.strip('+-0.') == '' else t + '%'


def _lines_svg(spec):
    ser = spec['series']
    vals = [v for s in ser for _, v in s['points']]
    hi, lo = max(vals + [0.0]), min(vals + [0.0])
    span = (hi - lo) or 1.0
    # 위 여백은 최고 눈금 글자(휴대폰 26~32 단위)가 선 위에 설 자리, 아래 여백은 양 끝 날짜 줄(2026-11-07 디자인 검수 — 눈금 숫자가
    # 하나도 없어 변동 폭이 +0.1 인지 +1.0 인지 보이지 않았다).
    pad_l, pad_t, pad_b = 8, 34, 40
    plot_h = CH_LINE_H - pad_t - pad_b
    n = max(len(s['points']) for s in ser)

    def xy(i, v, cnt):
        x = pad_l + (CH_W - pad_l * 2) * (i / float(max(1, cnt - 1)))
        return x, pad_t + plot_h - (v - lo) / span * plot_h
    out = [_svg_open(spec, CH_LINE_H)]
    zx, zy = xy(0, 0.0, n)
    # 눈금: 최고·0·최저(같은 자리에 겹치면 0 을 남긴다). 최고·최저는 옅은 점선, 0 은 진한 척추. 글자는 왼쪽 안쪽에 선 위로.
    ticks = [(0.0, zy)]
    for v in (hi, lo):
        y = xy(0, v, n)[1]
        if abs(y - zy) >= 30:              # 26 단위 글자 한 줄보다 가까우면 0 눈금과 겹친다
            ticks.append((v, y))
            out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="cl-grid"/>' % (pad_l, y, CH_W - pad_l, y))
    out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="cl-zero"/>'
               % (pad_l, zy, CH_W - pad_l, zy))      # 0선 척추
    for s in ser:
        d = ' '.join('%s%.1f %.1f' % ('M' if i == 0 else 'L', *xy(i, v, len(s['points'])))
                     for i, (_, v) in enumerate(s['points']))
        out.append('<path d="%s" class="cl cl-%s"/>' % (d, 'je' if s['name'] == '전세' else 'ma'))
        lx, ly = xy(len(s['points']) - 1, s['points'][-1][1], len(s['points']))
        out.append('<circle cx="%.1f" cy="%.1f" r="2.5" class="cl-dot"/>' % (lx, ly))
    for v, y in ticks:
        out.append('<text x="%d" y="%.1f" class="cb-x cx-s cl-t">%s</text>' % (pad_l + 2, y - 5, html.escape(_pct_tick(v))))
    # 마지막 값은 첫 계열(매매 — 실선) 하나만, 점 왼쪽 위에 적는다. 두 계열 값을 나란히 적으면 휴대폰 글자에서 서로 겹친다 —
    # 전세 값은 대체 텍스트와 본문에 있다.
    s0 = ser[0]
    lx, ly = xy(len(s0['points']) - 1, s0['points'][-1][1], len(s0['points']))
    vy = ly - 8 if ly - 8 - 26 >= 0 else ly + 30
    out.append('<text x="%.1f" y="%.1f" class="cb-v cb-k cx-e cl-t">%s</text>'
               % (lx - 6, vy, html.escape(_pct_tick(s0['points'][-1][1]))))
    # 양 끝 날짜는 눈금 꼴 '9/28' 로만 적는다(연도는 각주에 있다, 날짜 두 단계 — sido_zones.day_text). 가장자리에 붙이면
    # 잘려 보여 안쪽으로 넣는다.
    ends = (ser[0]['points'][0][0], ser[0]['points'][-1][0])
    # 맞춤은 클래스로 준다 — CSS 의 text-anchor 가 SVG 속성을 이겨서, 속성으로 적으면 가운데로 그려지고
    # 양 끝 글자가 그림 밖으로 밀려 잘린다(2026-10-27 브라우저에서 getBBox 로 확인했다).
    out.append('<text x="%d" y="%d" class="cb-x cx-s">%s</text>'
               % (pad_l + 2, CH_LINE_H - 7, html.escape(_day_tick(ends[0]))))
    out.append('<text x="%d" y="%d" class="cb-x cx-e">%s</text>'
               % (CH_W - pad_l - 2, CH_LINE_H - 7, html.escape(_day_tick(ends[1]))))
    out.append('</svg>')
    return ''.join(out)


def _day_tick(iso):
    import sido_zones as SZ
    return SZ.day_text(iso)


def _chart_html(spec):
    """그림 한 덩이 — 숫자 카드(있으면) + SVG + 범례 + 각주."""
    out = ['<figure class="cchart">']
    if spec.get('cards'):
        out.append('<div class="ccards">')
        out += ['<div class="ccard"><b>%s</b><span>%s</span></div>'
                % (html.escape(v), html.escape(k)) for k, v in spec['cards']]
        out.append('</div>')
    out.append(_bars_svg(spec) if spec['kind'] == 'bars' else _lines_svg(spec))
    if spec['kind'] == 'lines' and len(spec['series']) > 1:
        out.append('<p class="clegend"><span class="lg-ma">매매</span><span class="lg-je">전세</span></p>')
    out.append('<figcaption>%s%s</figcaption>' % (
        html.escape(spec['title']), ' · ' + html.escape(spec['note']) if spec.get('note') else ''))
    # 3년 합계 한 줄(content_tables 가 짓는다). 각주와 같은 글자 크기로 두되 줄은 따로 — 각주에 이어
    # 붙이면 출처 문장 끝에 숫자가 매달려 읽기 어렵다.
    if spec.get('foot'):
        out.append('<p class="cfoot3">%s</p>' % html.escape(spec['foot']))
    out.append('</figure>')
    return ''.join(out)


def _own_tab(page):
    """뼈대(make_indicator_pages.SHELL)는 '시세' 탭을 켜 둔다 — 콘텐츠 페이지는 제 탭('콘텐츠')을 켠다.

    탭바 마크업은 site_nav 가 정본이라 그 함수가 만든 두 덩어리를 맞바꾼다(문자열을 손으로 적지 않는다).
    """
    return page.replace(N.bottomnav('stats'), N.bottomnav('reports'), 1)


_NUMLIKE = re.compile(r'^[+\-\u2212\u25b2\u25bc~(]?\s*\d')


def _text_cols(rows):
    """글자 열(첫 열 말고) — 칸 대부분이 숫자로 시작하지 않는 열. 글자 열은 머리·칸 모두 왼쪽, 숫자 열만 오른쪽에 붙인다
    (2026-10-30 디자인 리뷰 — GTX '출퇴근' 표의 '경로'처럼 글자 열이 오른쪽 정렬이고 머리는 가운데였다)."""
    out = set()
    n = max([len(r) for r in rows] or [0])
    for j in range(1, n):
        cells = [re.sub(r'<[^>]+>', '', str(r[j])).strip() for r in rows if j < len(r)]
        cells = [c for c in cells if c and c not in ('·', '-', '—')]
        if cells and sum(1 for c in cells if _NUMLIKE.match(c)) * 2 < len(cells):
            out.add(j)
    return out


# 숫자 열 안이라도 글자가 긴 칸(평형 목록·일정 설명)은 줄을 바꾼다 — 칸마다 한 줄로 묶으니 '핵심 숫자' 표의 값 열이
# 화면 밖으로 밀려 항목 이름만 보였다(2026-10-31 디자인 리뷰 2차). 짧은 숫자 칸은 한 줄 그대로 오른쪽에 붙인다.
LONG_CELL = 12


def _cls(j, tx, text=''):
    plain = re.sub(r'<[^>]+>', '', str(text)).strip()
    return ' class="tx"' if (j in tx or len(plain) > LONG_CELL) else ''


# 열이 이만큼 이상인 표는 휴대폰 단(331px)에 다 안 들어온다 — 표 밑에 '옆으로 밀어 N열 모두 보기' 한 줄(휴대폰에서만 보인다)을
# 단다. 그림자 단서만으로는 몇 열이 숨었는지 몰랐다(2026-11-07 디자인 검수 — GTX 11열 표의 '필요 현금' 열).
WIDE_COLS = 5


def _tab_hint(ncols):
    return ('<p class="ctab-hint">옆으로 밀어 %d열 모두 보기</p>' % ncols) if ncols >= WIDE_COLS else ''


def _table_html(head, body, note=''):
    tx = _text_cols(body)
    h = ['<div class="ctab"><table><thead><tr>']
    h += ['<th scope="col"%s>%s</th>' % (_cls(j, tx | {0}), html.escape(c)) for j, c in enumerate(head)]
    h.append('</tr></thead><tbody>')
    for row in body:
        cells = ['<th scope="row">%s</th>' % html.escape(str(row[0]))]
        cells += ['<td%s>%s</td>' % (_cls(j, tx, c), html.escape(str(c))) for j, c in enumerate(row[1:], 1)]
        h.append('<tr>%s</tr>' % ''.join(cells))
    h.append('</tbody></table>')
    if note:
        h.append('<p class="cnote">%s</p>' % html.escape(note))
    h.append('</div>')
    h.append(_tab_hint(len(head)))
    return ''.join(h)


def markdown(body, stray=None):
    """문단·제목·목록·인용·표만 있는 작은 마크다운. 모르는 줄은 문단으로 둔다.

    stray 에 목록을 주면 '표 줄(|)인데 표가 되지 못한 줄'의 (줄 번호, 글)을 담는다 — 구분 줄(|---|)이 없거나 끝 파이프가
    빠진 표다. 원고 검사기(content_check)가 이 목록으로 고칠 곳을 알린다(같은 걸음으로 봐야 검사와 굽기가 갈리지 않는다).
    """
    lines = body.replace('\r\n', '\n').split('\n')
    out, i, last = [], 0, -1
    while i < len(lines):
        if i == last:           # 걸음 감시 — 어느 갈래도 이 줄을 먹지 못했다면 넘긴다. 이 함수는 무슨 일이 있어도 끝난다
            i += 1
            continue
        last = i
        ln = lines[i]
        s = ln.strip()
        if not s:
            i += 1
            continue
        m = re.match(r'^(#{2,4})\s+(.*)$', s)
        if m:
            lvl = len(m.group(1))
            out.append('<h%d>%s</h%d>' % (lvl, _inline(m.group(2)), lvl))
            i += 1
            continue
        if s.startswith('|') and i + 1 < len(lines) and re.match(r'^\|[\s:|-]+\|$', lines[i + 1].strip()):
            head = [c.strip() for c in s.strip('|').split('|')]
            i += 2
            rows = []
            while i < len(lines) and lines[i].strip().startswith('|'):
                rows.append([c.strip() for c in lines[i].strip().strip('|').split('|')])
                i += 1
            tx = _text_cols(rows)
            h = ['<div class="ctab"><table><thead><tr>']
            h += ['<th scope="col"%s>%s</th>' % (_cls(j, tx | {0}), _inline(c)) for j, c in enumerate(head)]
            h.append('</tr></thead><tbody>')
            for r in rows:
                cells = (['<th scope="row">%s</th>' % _inline(r[0])]
                         + ['<td%s>%s</td>' % (_cls(j, tx, c), _inline(c)) for j, c in enumerate(r[1:], 1)])
                h.append('<tr>%s</tr>' % ''.join(cells))
            h.append('</tbody></table></div>')
            h.append(_tab_hint(len(head)))
            out.append(''.join(h))
            continue
        if re.match(r'^[-*]\s+', s) or re.match(r'^\d+\.\s+', s):
            ordered = bool(re.match(r'^\d+\.\s+', s))
            items = []
            while i < len(lines) and lines[i].strip() and (
                    re.match(r'^[-*]\s+', lines[i].strip()) or re.match(r'^\d+\.\s+', lines[i].strip())):
                items.append(re.sub(r'^([-*]|\d+\.)\s+', '', lines[i].strip()))
                i += 1
            tag = 'ol' if ordered else 'ul'
            out.append('<%s>%s</%s>' % (tag, ''.join('<li>%s</li>' % _inline(x) for x in items), tag))
            continue
        if s.startswith('>'):
            quote = []
            while i < len(lines) and lines[i].strip().startswith('>'):
                quote.append(lines[i].strip().lstrip('>').strip())
                i += 1
            out.append('<blockquote><p>%s</p></blockquote>' % _inline(' '.join(quote)))
            continue
        # 여기까지 온 줄은 위 어느 덩어리의 머리도 아니다 — **첫 줄은 무조건 먹는다**. 예전엔 표 머리가 아닌 '|' 줄(구분 줄 없는 표,
        # 끝 파이프가 빠진 구분 줄, 표 뒤 빈 줄 다음의 행)이 어느 갈래에도 먹히지 않아 i 가 그대로였고, 이 함수가 끝나지 않았다
        # (2026-11-13 전수 리뷰 — 검사기는 OK 를 내고 배치의 생성기 단계가 시간 상한까지 매달려 그날 데이터 커밋이 막힌다).
        if s.startswith('|') and stray is not None:
            stray.append((i + 1, s))
        para = [s]
        i += 1
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{2,4}\s|[-*]\s|\d+\.\s|\||>)', lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        out.append(_para(' '.join(para)))
    return '\n'.join(out)


# '※' 문단(표 밑 기준·읽는 법)이 이보다 길면 접는다 — 표 바로 밑 15줄 방법론이 결과 절을 막았다(2026-11-07 디자인 검수).
NOTE_FOLD = 110
NOTE_SUMMARY = '※ 이 표의 기준과 읽는 법'


def _para(text):
    """문단 하나. '※' 로 여는 문단은 기준·읽는 법이다 — 짧으면 각주 문단(.cnotep), 길면 접는 칸(.cfold). 원고 글자는 그대로 싣는다."""
    if not text.startswith('※'):
        return '<p>%s</p>' % _inline(text)
    if len(text) <= NOTE_FOLD:
        return '<p class="cnotep">%s</p>' % _inline(text)
    return '<details class="cfold"><summary>%s</summary><p>%s</p></details>' % (
        html.escape(NOTE_SUMMARY), _inline(text.lstrip('※').strip()))


PLACEHOLDER = CT.PH      # 정규식은 content_tables 가 정본이다 — 종류가 늘면 한 곳만 고친다


SAME_NOTE = '출처는 위와 같습니다'


def _card_in_key(v, key):
    """카드 값('34%')이 글 머리 핵심 숫자 띠('적정물량의 34%')에 이미 있나 — 숫자 앞뒤가 다른 숫자에 붙지 않은 자리에서만."""
    kv = (key or {}).get('value') or ''
    v = (v or '').strip()
    return bool(v and kv and re.search(r'(?<![\d.,])%s(?![\d.,])' % re.escape(v), kv))


def fill_placeholders(body, data, key=None):
    """자리표를 먼저 채운다. 표는 토큰으로 빼 두었다가 마크다운 변환 뒤 되돌린다.

    key(글 머리 핵심 숫자 띠)를 주면 그림 숫자 카드 가운데 띠와 같은 값은 뺀다 — 같은 수가 띠·카드에 166px 사이로 두 번
    섰다(2026-11-07 디자인 검수). 바로 앞 표·그림과 같은 각주는 '출처는 위와 같습니다' 한 줄로 줄인다 — 도시 편에서 같은
    두 줄 각주가 표 셋·그림 하나 밑에 네 번 나왔다.
    """
    blocks = []
    last = {'note': None}

    def note_of(n):
        if n and n == last['note']:
            return SAME_NOTE
        last['note'] = n or last['note']
        return n

    def sub(m):
        kind, rest = m.group(1), m.group(2)
        parts = [p.strip() for p in rest.split(':')]
        if not parts or not parts[0]:
            raise CT.TableError('자리표가 비었다: %s' % m.group(0))
        if kind == 'v':
            return CT.value(data, parts[0], parts[1:])
        if kind == 'chart':
            spec = dict(CT.chart(data, parts[0], parts[1:]))
            spec['cards'] = [(k, v) for k, v in (spec.get('cards') or []) if not _card_in_key(v, key)]
            spec['note'] = note_of(spec.get('note'))
            blocks.append(_chart_html(spec))
        else:
            head, rows, note = CT.table(data, parts[0], parts[1:])
            blocks.append(_table_html(head, rows, note_of(note)))
        return '\n\n\x00TABLE%d\x00\n\n' % (len(blocks) - 1)

    return CT.no_leftover(PLACEHOLDER.sub(sub, body)), blocks      # 꼴이 어긋나 안 채워진 '{{' 는 발행하지 않는다


def restore_tables(html_text, blocks):
    for i, b in enumerate(blocks):
        html_text = html_text.replace('<p>\x00TABLE%d\x00</p>' % i, b).replace('\x00TABLE%d\x00' % i, b)
    return html_text


# ── 페이지 ──────────────────────────────────────────────────────────────────
LIST_CSS = """/* 콘텐츠 카드 부품(2026-11-05 콘텐츠 구조 개편) — 허브·섹션 목록·홈 "최근 리포트"·시도 리포트 '이 지역 글'이 카드 하나를 쓴다.
   카드 = 칩(지역·질문) → 결론 제목(두 줄) → 핵심 숫자(큰 값 + 작은 이름) → 날짜. 그림 썸네일은 없다(112×63 안 글자가 4~6px 라
   읽히지 않았고, 제목이 글 내용을 말하지 못해 '무엇이 내 관심사인지' 알 수 없었다 — 대표 지적 11-05). 모바일은 한 단, 768px
   이상은 3열 같은 높이. 간격은 4의 배수(2026-11-07 디자인 검수 — 5·6·10·14·22px 가 섞여 있었다). */
/* 칩 줄은 휴대폰에서도 접어 내린다 — 가로 밀기였을 때 다섯째 질문 칩과 경기 지역 칩 대부분이 화면 밖에 단서 없이 숨었다
   (2026-11-07 디자인 검수). 칩 높이 35px(손가락 목표에 가깝게). */
.rchips{display:flex;gap:8px;flex-wrap:wrap;margin:0 0 16px}
.rchip{display:inline-block;text-decoration:none;font:inherit;font-size:13px;line-height:1;padding:10px 12px;
 border:1px solid var(--line);border-radius:3px;background:var(--paper);color:var(--ink2);cursor:pointer}
.rchip.on{background:var(--brand);border-color:var(--brand);color:var(--paper)}
/* 지금 보는 섹션은 테두리로만 — 지역 칩의 '켜짐'(먹색 채움)과 다른 꼴이라야 어느 쪽이 페이지이고 어느 쪽이 거름인지 갈린다. */
.rchip[aria-current=page]{border-color:var(--brand);color:var(--brand);background:var(--brand-bg);font-weight:600}
.rchip:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.kgrid{display:grid;gap:12px}
.kcard{display:flex;flex-direction:column;gap:8px;padding:16px;border:1px solid var(--line);border-radius:3px;
 background:var(--paper);color:var(--ink);text-decoration:none;min-width:0}
.kcard:hover{border-color:var(--ink2)}
.kcard:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.kcard[hidden]{display:none}
/* 허브 '최근 글'은 첫 묶음만 보이고 '더 보기'로 편다(.kfold — 허브 JS 가 거를 때·펼 때 푼다, JS 가 없으면 noscript 가 푼다). */
.kfold .kcard:nth-child(n+13){display:none}
.kmore{display:block;width:100%;margin:12px 0 0;padding:14px 12px;text-align:center}
.kc-chips{display:flex;gap:4px;flex-wrap:wrap}
.kc-chip{font-size:13px;line-height:1;padding:4px 8px;border-radius:3px;background:var(--paper2);color:var(--ink2)}
.kc-chip.kc-t{background:var(--mark-bg);color:var(--mark-ink);font-weight:600}
/* 결론 제목은 세 줄까지 — 두 줄에서 자르니 3열 칸(약 300px)에서 결론 동사('…올랐습니다')가 잘렸다(2026-11-07 디자인 검수). */
.kc-hook{display:-webkit-box;-webkit-line-clamp:3;-webkit-box-orient:vertical;overflow:hidden;
 font-size:16px;font-weight:600;line-height:1.45}
.kc-key{display:flex;align-items:baseline;gap:8px;flex-wrap:wrap;margin-top:auto}
.kc-key strong{font-size:22px;font-weight:700;line-height:1.2;letter-spacing:-.01em;background:linear-gradient(transparent 58%,var(--mark) 58%);padding:0 2px}
.kc-key small{font-size:13px;color:var(--muted)}
.kc-date{font-style:normal;font-size:13px;color:var(--muted)}
/* 질문 카드 — 허브 '질문으로 찾기'. 질문 오른쪽에 글 수, 아래에 최신 결론(휴대폰 한 줄, 768px 이상 두 줄). 결론은 읽는 글이라
   14px(2026-11-06 하한 — 13px 였다). */
.qgrid{display:grid;gap:8px;margin:0 0 24px}
.qcard{display:grid;grid-template-columns:1fr auto;align-items:baseline;gap:4px 12px;padding:12px 16px;
 border:1px solid var(--line);border-radius:3px;background:var(--paper);color:var(--ink);text-decoration:none}
.qcard:hover{border-color:var(--ink2)}
.qcard b{font-size:16px;font-weight:600;line-height:1.4}
.qc-n{font-size:13px;color:var(--muted);white-space:nowrap}
.qcard ul{grid-column:1/-1;list-style:none;margin:2px 0 0;padding:0;font-size:14px;line-height:1.55;color:var(--ink2)}
.qcard li{display:-webkit-box;-webkit-line-clamp:1;-webkit-box-orient:vertical;overflow:hidden}
.qcard li+li{display:none}
/* 지역 칩 — 시도별 한 줄(넘치면 접는다). 허브 JS 가 data-city 로 카드를 거른다. JS 가 없으면 전부 보인다. */
.cityf{margin:0 0 24px}
.cf-g{display:flex;gap:8px;align-items:flex-start;margin:0 0 8px}
.cf-g em{flex:none;font-style:normal;font-size:13px;line-height:35px;font-weight:600;color:var(--ink2);min-width:3.2em}
.cf-c{display:flex;gap:8px;flex-wrap:wrap;min-width:0}
.cf-n{font-size:13px;color:var(--muted);margin:0 0 12px}
/* 절 제목은 뼈대 h2 와 같은 급(20px/700) — 16px/600 이라 카드 제목과 같은 급이었다(2026-11-07 디자인 검수). */
.rh2{font-size:20px;font-weight:700;letter-spacing:-.02em;line-height:1.35;margin:0 0 12px}
@media (min-width:768px){
  .kgrid{grid-template-columns:repeat(3,1fr);gap:16px}
  .qgrid{grid-template-columns:repeat(2,1fr)}
  .qcard li+li{display:-webkit-box}
}"""
# 콘텐츠 페이지는 app.css 를 링크하지 않고 뼈대의 인라인 style 을 쓴다. 홈은 app.css 를 읽는다.
# 그래서 같은 글자가 두 곳에 있고, test_content_pages 가 app.css 의 LIST_CSS 구간과 대조한다.

EXTRA_CSS = LIST_CSS + """
/* 본문 그림은 단 폭을 넘지 않는다 — 그림 주소를 고친 뒤(2026-10-30) 지도·표 그림이 원본 폭(1,900~2,500px)으로 그려져
   375px·1280px 모두 페이지가 옆으로 넘쳤다. */
.cbody img{display:block;max-width:100%;height:auto;margin:0 0 16px}
.cchart{margin:0 0 20px;padding:0}
.cchart-svg{display:block;width:100%;max-width:640px;height:auto;margin:2px 0 0;overflow:visible}
.ccards{display:flex;gap:8px;margin:0 0 10px;flex-wrap:wrap}
.ccard{flex:1 1 30%;min-width:96px;background:var(--paper2);border:1px solid var(--line);
 border-radius:3px;padding:8px 10px}
.ccard b{display:block;font-size:18px;font-weight:600;line-height:1.25;letter-spacing:-.01em}
/* 회색 종이(paper2) 위 라벨은 ink2 — muted 는 4.44:1 로 4.5 에 못 미쳤다(2026-11-07 디자인 검수). */
.ccard span{display:block;font-size:13px;color:var(--ink2);margin-top:2px}
.cchart figcaption,.clegend{font-size:13px;color:var(--muted);margin:6px 0 0;line-height:1.55}
.cfoot3{font-size:14px;font-weight:600;color:var(--ink);margin:4px 0 0;line-height:1.55}
.clegend{display:flex;gap:14px}
.clegend span{display:inline-flex;align-items:center;gap:5px}
.clegend span::before{content:"";width:16px;height:0;border-top:2px solid var(--maemae)}
.clegend .lg-je::before{border-top:2px dashed var(--jeonse)}
.cb{fill:var(--stock);opacity:.5}
.cb-over{opacity:.85}
.cb-v{fill:var(--ink);font-size:11px;text-anchor:middle}
.cb-none{fill:var(--muted)}   /* 입주 예정이 없는 해(CT.NO_MOVEIN) — 막대 없이 자리만 */
.cb-x{fill:var(--muted);font-size:11px;text-anchor:middle}
.cx-s{text-anchor:start}
.cx-e{text-anchor:end}
.cb-rule{stroke:var(--ink);stroke-width:1;stroke-dasharray:4 3;opacity:.65}
.cb-rl{fill:var(--muted);font-size:11px}
/* 그림 글자는 viewBox(640) 단위라 단이 좁아지면 함께 줄어든다 — 375px 에서 11 단위가 5.7px 로 그려졌다(2026-10-31 디자인
   리뷰 2차). 글 단(.wrap 560 - 좌우 22)은 600px 이상 화면에서 516px 이라 13 단위는 10.5px 였다(2026-11-07 디자인 검수) —
   기본을 17 단위(516px 에서 13.7px)로 두고 단이 좁아지면 단위를 올린다. 커진 글자가 겹치지 않게 휴대폰은 값을 대표 둘(cb-k)만,
   막대가 많으면 x 축 이름은 하나 걸러(cb-x2) 적는다. 17 단위 값이 막대 간격에 안 들어가는 그림(cb-dense)은 화면 폭과
   상관없이 대표 둘만 적는다. 크기 계산은 test_content_review2.test_chart_labels_hold_13px_on_a_phone 이 본다. */
.cb-v,.cb-x,.cb-rl{font-size:17px}
@media (max-width:687px){.cb-v:not(.cb-k),.cb-x2{display:none}}
@media (max-width:580px){.cb-v,.cb-x,.cb-rl{font-size:19px}}
@media (max-width:500px){.cb-v,.cb-x,.cb-rl{font-size:22px}}
@media (max-width:440px){.cb-v,.cb-x,.cb-rl{font-size:24px}}
@media (max-width:400px){.cb-v,.cb-x,.cb-rl{font-size:26px}}
@media (max-width:368px){.cb-v,.cb-x,.cb-rl{font-size:29px}}
@media (max-width:335px){.cb-v,.cb-x,.cb-rl{font-size:32px}}
.cb-dense .cb-v:not(.cb-k){display:none}
/* 끝 맞춤한 값이 옆 막대에 걸쳐도 읽히게 종이색 테두리(마지막 막대 값이 한 칸 왼쪽으로 들어온다). */
.cb-v{paint-order:stroke;stroke:var(--paper);stroke-width:4px;stroke-linejoin:round}
/* 꺾은선 눈금(최고·0·최저)과 마지막 값 — 선 위에 놓여도 읽히게 종이색 테두리를 두른다. */
.cl-t{paint-order:stroke;stroke:var(--paper);stroke-width:5px;stroke-linejoin:round}
.cl-grid{stroke:var(--line);stroke-width:1;stroke-dasharray:2 3}
.cl{fill:none;stroke:var(--maemae);stroke-width:1.8;stroke-linejoin:round}
.cl-je{stroke:var(--jeonse);stroke-dasharray:4 3}
.cl-zero{stroke:var(--muted);stroke-width:1}
.cl-dot{fill:var(--maemae)}
.cmeta{font-size:13px;color:var(--muted);margin:0 0 14px}
.cmeta a{white-space:nowrap}
/* 허브·섹션 목록·글의 머리는 왼쪽 정렬 — 뼈대 header 는 가운데라 머리만 가운데, 그 아래 칩·카드·본문은 왼쪽이라 정렬선이
   두 개였다(2026-11-07 디자인 검수). 허브 제목은 리포트 급(--h1-report), 글 제목은 데스크톱에서 38px(본문 15px 의 2.5배). */
.hub-head,.post-head{text-align:left;padding:32px 0 8px}
.hub-q .qgrid,.hub-city .cityf{margin-bottom:0}
.hub-head h1{font-size:var(--h1-report);line-height:1.2}
@media (min-width:1024px){.post-head h1{font-size:38px}}
/* 글 머리(2026-11-05 콘텐츠 구조 개편): 질문·지역 눈썹 → 제목 → 메타 → 3줄 요약 → 이 글이 맞는 분 → 핵심 숫자 띠 → 본문. */
.eyebrow{font-size:13px;color:var(--ink2);margin:0 0 8px}
.eyebrow a{color:var(--ink2);font-weight:600;text-decoration-color:var(--line)}
.ctldr{background:var(--mark-soft);border-left:3px solid var(--brand);padding:12px 16px;margin:0 0 14px}
.ctldr b{display:block;font-size:13px;color:var(--brand);margin:0 0 6px}
.ctldr ol{margin:0;padding:0 0 0 1.3em}
.ctldr li{font-size:15.5px;line-height:1.7}
.caud{font-size:14px;line-height:1.7;color:var(--ink2);margin:0 0 14px}
.caud b{color:var(--ink);margin-right:6px}
.ckey{display:flex;align-items:baseline;gap:10px;flex-wrap:wrap;border:1px solid var(--line);border-radius:3px;padding:12px 16px;margin:0 0 22px}
.ckey strong{font-size:26px;font-weight:700;line-height:1.2;letter-spacing:-.01em;background:linear-gradient(transparent 58%,var(--mark) 58%);padding:0 2px}
.ckey span{font-size:13px;color:var(--muted)}
.cmore{margin-top:8px}
.cmore h2{font-size:20px;margin:0 0 12px}
.cmore-l{display:flex;gap:8px;flex-wrap:wrap}
.cmore-l a{flex:1;min-width:200px;border:1px solid var(--line);border-radius:3px;padding:12px 14px;text-decoration:none;color:var(--ink);font-size:14px}
.cmore-l a span{display:block;font-size:13px;color:var(--muted);margin-bottom:2px}
/* 글 끝의 첫 행동은 하나만 채운다(.cgo) — 꼬리 상자 넷이 같은 테두리라 무엇을 먼저 누를지 신호가 없었다(2026-11-07 디자인 검수). */
.cmore-l a.cgo{background:var(--brand);border-color:var(--brand);color:var(--paper);font-size:15px;font-weight:600}
.cmore-l a.cgo span{color:var(--paper);opacity:.85;font-weight:400}
.cbody h2{font-size:22px;letter-spacing:-.01em;margin:28px 0 10px}
.cbody h3{font-size:18px;margin:22px 0 8px}
/* 본문 링크가 브라우저 기본 파랑이었다(도시 편 '더 보기' 목록 — 뼈대 규칙은 p 안 링크만 잡는다). */
.cbody a:not([class]){color:var(--ink);text-decoration-color:var(--line);text-decoration-thickness:1px;text-underline-offset:3px}
.cbody a:not([class]):hover{text-decoration-color:var(--ink)}
/* '※' 로 여는 문단은 표 밑 기준·읽는 법이다. 짧으면 한 줄 각주(14px — 문장이다), 길면 접는다(.cfold): 표 바로 밑에
   방법론 15줄이 본문 크기로 서서 결과 절을 막았다(2026-11-07 디자인 검수). 원고 글자는 그대로다. */
.cbody p.cnotep{font-size:14px;line-height:1.7;color:var(--ink2)}
.cfold{margin:0 0 14px;border-left:2px solid var(--line);padding:0 0 0 12px}
.cfold summary{font-size:13px;color:var(--ink2);cursor:pointer;padding:6px 0}
.cfold summary:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.cbody .cfold p{font-size:14px;line-height:1.7;color:var(--ink2);margin:4px 0 8px}
.cbody p{font-size:15px;line-height:1.8;margin:0 0 14px}
.cbody li{font-size:15px;line-height:1.8}
.cbody blockquote{margin:0 0 14px;padding:10px 14px;background:var(--paper2);border-radius:3px}
.ctab{overflow-x:auto;margin:0 0 16px;background:linear-gradient(to right,var(--paper) 30%,rgba(255,255,255,0)) left center/24px 100% no-repeat local,linear-gradient(to left,var(--paper) 30%,rgba(255,255,255,0)) right center/24px 100% no-repeat local,radial-gradient(farthest-side at 0 50%,rgba(0,0,0,.28),transparent) left center/16px 100% no-repeat scroll,radial-gradient(farthest-side at 100% 50%,rgba(0,0,0,.28),transparent) right center/16px 100% no-repeat scroll}
/* ↑ 넘침 표시 — 가로로 밀 것이 남은 쪽 가장자리에 그림자(지표 페이지 .tbl-wrap 과 같은 규칙, 2026-10-30 디자인 리뷰). 2026-11-07 디자인
   검수: 10px 그림자가 눈에 안 띄어 16px 로 키우고, 첫 열(단지·항목 이름)은 데스크톱에서도 붙여 둔다 — 열이 많은 표(GTX 11열)는
   960px 로 펴도 넘쳐, 밀면 어느 행인지 놓쳤다. 열이 많은 표(.ctab-wide)는 휴대폰에서 표 밑에 '옆으로 밀기' 한 줄을 단다. */
.ctab th[scope=row]{position:sticky;left:0;background:var(--paper);z-index:1}
.ctab-hint{display:none;font-size:13px;color:var(--muted);margin:-10px 0 16px}
@media (max-width:600px){.ctab-hint{display:block}}
.ctab table{width:100%;border-collapse:collapse;font-size:14px}
.ctab th,.ctab td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.ctab th[scope=row]{text-align:left;font-weight:500}
.ctab .tx{text-align:left;white-space:normal;min-width:6em}
/* 데스크톱은 글을 읽는 단(read, 516px)에 두되 표만 단 밖으로 넓힌다 — 단에 갇혀 11열 표가 한 화면에 안 들어오고 행이
   88px 로 접혔다(2026-10-31 디자인 리뷰 2차). 표가 좁으면 단 폭 그대로다(min-width:100%), 넓으면 960px 까지 가운데로 편다. */
@media (min-width:1024px){
  .ctab{width:fit-content;min-width:100%;max-width:min(960px,calc(100vw - 96px));position:relative;left:50%;transform:translateX(-50%)}
}
.ctab thead th{border-bottom:1.5px solid var(--ink);font-size:13px;color:var(--muted)}
.cnote{font-size:13px;color:var(--muted);margin:6px 0 0}
.csrc{font-size:14px;color:var(--ink2);line-height:1.7}
/* 목록 글머리표가 단 여백 밖(화면 끝)에 걸렸다 — 뼈대가 padding 을 0 으로 지운다(2026-10-31 디자인 리뷰 2차). */
.cbody ul,.cbody ol,.csrc{padding-left:1.3em;margin:0 0 14px}
/* 빵부스러기 링크가 브라우저 기본 파랑이었다(사이트에서 남은 유일한 자리). */
.crumb a{color:var(--ink2);text-decoration-color:var(--line)}
/* 본문 그림은 원본으로 열린다 — 표·지도 캡처가 휴대폰 단 폭으로 줄어 그림 속 글자가 3~4px 가 됐다. 혼자 선 그림은 figure 로
   굽고 밑에 그림 이름과 '눌러서 크게 보기'를 단다 — 눌러지는 줄 아무 표시가 없었다(2026-11-07 디자인 검수). */
.cimg{display:block;margin:0 0 16px}
.cimg img{margin:0}
.cfig{margin:0 0 16px}
.cfig .cimg{margin:0;border:1px solid var(--line);border-radius:3px;overflow:hidden}
.cfig figcaption{font-size:13px;color:var(--ink2);margin:6px 0 0;line-height:1.55}
.cbody .cfig figcaption a{color:var(--ink2);text-decoration-color:var(--line);white-space:nowrap}
.csrc li{margin-bottom:3px}
/* 꼬리 절 사이 간격은 뼈대 section 여백 하나만 — 출처 절과 FAQ 사이가 80px 비어 글이 끝난 것처럼 보였다(2026-11-07 디자인 검수). */
.csrc-s{padding-bottom:0}
.cfaq{margin-top:0}
.cfaq dt{font-weight:600;font-size:15px;margin-top:14px}
.cfaq dd{margin:6px 0 0;font-size:14.5px;line-height:1.75;color:var(--ink2)}
/* 이전·다음 글과 섹션 목록은 2급 — 테두리 없이 위아래 선만. 휴대폰은 이전·다음을 한 줄에. */
.cnav{display:grid;grid-template-columns:1fr 1fr;gap:8px;margin-top:24px}
.cnav a{min-width:0;border-top:1px solid var(--line);border-bottom:1px solid var(--line);padding:12px 2px;
 text-decoration:none;color:var(--ink2);font-size:14px;line-height:1.5}
.cnav a span{display:block;font-size:13px;color:var(--muted);margin-bottom:2px}
.cnav a.cnav-n{text-align:right}
.cnav a.cnav-hub{grid-column:1/-1;color:var(--ink);font-weight:600}
.clist{display:flex;flex-direction:column;gap:10px;margin-top:18px}
.clist a{border:1px solid var(--line);border-radius:3px;padding:13px 15px;text-decoration:none;color:var(--ink)}
.clist b{display:block;font-size:15.5px;font-weight:600;margin-bottom:4px}
.clist span{display:block;font-size:13.5px;color:var(--ink2);line-height:1.6}
.clist i{display:block;font-style:normal;font-size:13px;color:var(--muted);margin-top:5px}
"""


def _ld(meta, url, body_html):
    """Article + (faq 가 있으면) FAQPage + BreadcrumbList."""
    sec = meta['section']
    out = [{
        "@context": "https://schema.org", "@type": "Article",
        "headline": meta['title'],
        "description": meta['summary'],
        "datePublished": meta['date'], "dateModified": meta['updated'],
        "author": {"@type": "Organization", "name": "아공맵"},
        "publisher": {"@type": "Organization", "name": "아공맵"},
        "mainEntityOfPage": url,
        "inLanguage": "ko-KR",
    }]
    faq = meta.get('faq') or []
    if faq:
        out.append({
            "@context": "https://schema.org", "@type": "FAQPage",
            "mainEntity": [{"@type": "Question", "name": f['q'],
                            "acceptedAnswer": {"@type": "Answer", "text": f['a']}} for f in faq],
        })
    out.append({
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "아공맵", "item": SITE + '/'},
            {"@type": "ListItem", "position": 2, "name": SECTION_META[sec][0], "item": '%s/%s/' % (SITE, sec)},
            {"@type": "ListItem", "position": 3, "name": meta['title']},
        ],
    })
    return json.dumps(out, ensure_ascii=False, indent=2)


def _zone_link(region):
    import sido_zones as SZ
    try:
        key = CT.region_key(None, region) if False else SZ.key_of(region)
    except Exception:
        return ''
    if key not in SZ.ORDER:
        return ''
    import urllib.parse
    return ('<a href="/zone/%s/"><span>지역 공급 리포트</span>%s 아파트 공급 분석</a>'
            % (urllib.parse.quote(key), html.escape(SZ.DISPLAY_NAME.get(key, key))))


# ── 질문(주제)·카드 부품(2026-11-05 콘텐츠 구조 개편) ─────────────────────────────────────────────────
# 정본은 content_md.TOPICS(원고 검사가 같은 목록으로 topic 을 본다). 여기 이름으로 생성기·시험이 읽는다.
TOPICS = CM.TOPICS
TOPIC_BY = {k: (q, short, sec) for k, q, short, sec in TOPICS}
SECTION_TOPIC = {sec: k for k, _q, _s, sec in TOPICS}


def topic_of(meta):
    """글의 질문 키. 없으면 섹션의 기본 질문(옛 양식 글을 lenient 로 읽은 경우)."""
    t = meta.get('topic')
    return t if t in TOPIC_BY else SECTION_TOPIC[meta['section']]


def _region_disp(name):
    import sido_zones as SZ
    key = SZ.key_of(name) if SZ.key_of(name) in SZ.ORDER else name
    return SZ.DISPLAY_NAME.get(key, key)


def post_cities(meta):
    """카드·칩에 쓰는 지역 이름 목록. city 가 비면 '시도 전체'(region) 한 칸 — 서울 집값 발언 반박 같은 시도 글."""
    cities = [c for c in (meta.get('city') or []) if c]
    if cities:
        return cities
    return [_region_disp(meta['region']) + ' 전체'] if meta.get('region') else []


def _key_of(meta):
    k = meta.get('key')
    if isinstance(k, list) and k and isinstance(k[0], dict):
        k = k[0]
    return k if isinstance(k, dict) and k.get('value') else None


def card(meta):
    """카드 하나 — 허브·섹션 목록·홈·시도 리포트가 같은 마크업을 쓴다(CSS 는 LIST_CSS .kcard).

    칩은 지역(첫 도시, 둘 이상이면 '외 N')과 질문의 짧은 이름, 제목은 결론형 한 문장, 핵심 숫자는 큰 값과
    작은 이름, 날짜는 **작성일**의 좁은 자리 꼴('26.11.5', card_order). data-city 는 허브 지역 칩이 거르는 값(모든 도시, '|' 로 이어서).
    """
    cities = post_cities(meta)
    tkey = topic_of(meta)
    chips = ''
    if cities:
        chips += '<span class="kc-chip">%s</span>' % html.escape(cities[0] + (' 외 %d' % (len(cities) - 1) if len(cities) > 1 else ''))
    chips += '<span class="kc-chip kc-t">%s</span>' % html.escape(TOPIC_BY[tkey][1])
    key = _key_of(meta)
    key_html = ('<span class="kc-key"><strong>%s</strong><small>%s</small></span>'
                % (html.escape(key['value']), html.escape(key.get('label') or ''))) if key else ''
    return ('<a class="kcard" href="/%s/%s/" data-sec="%s" data-topic="%s" data-city="%s">'
            '<span class="kc-chips">%s</span><b class="kc-hook">%s</b>%s<i class="kc-date">%s</i></a>'
            % (meta['section'], meta['slug'], meta['section'], tkey, html.escape('|'.join(cities)),
               chips, html.escape(meta['title']), key_html, _day_short(meta['date'])))


def card_order(m):
    """카드 목록의 정렬 열쇠 — 작성일(처음 올린 날)이 먼저, 같은 날이면 갱신일·slug.

    카드 날짜도 작성일이다(2026-11-07 대표 승인). 갱신일은 원고를 한꺼번에 고친 날 모든 글이 같은 날이 되어 카드에서 정보가
    없었다(11-05 일괄 개편 뒤 46장 중 41장이 26.11.5). 갱신일은 글 머리 메타 줄('… 작성 · … 갱신')과 JSON-LD·sitemap 에 남는다.
    """
    return (m['date'], m['updated'], m['slug'])


def _newest(metas, n=None):
    out = sorted(metas, key=card_order, reverse=True)
    return out[:n] if n else out


def cards_grid(metas, n=None, fold=None):
    """카드 격자. fold 를 주면 그 수 뒤 카드는 접어 두고(.kfold) '글 N편 더 보기' 단추를 단다 — 허브 '최근 글'이 40장을 한 번에
    쌓아 휴대폰에서 7,000px 카드 벽이었다(2026-11-07 디자인 검수). 카드는 모두 마크업에 있다(거르기·검색·JS 없는 독자)."""
    got = _newest(metas, n)
    if not fold or len(got) <= fold:
        return '<div class="kgrid">%s</div>' % ''.join(card(m) for m in got)
    assert fold == HUB_FIRST, 'LIST_CSS 의 .kfold nth-child(n+%d) 와 수가 다르다' % (HUB_FIRST + 1)
    return ('<div class="kgrid kfold">%s</div>'
            '<button type="button" class="rchip kmore">글 %d편 더 보기</button>'
            '<noscript><style>.kfold .kcard:nth-child(n){display:flex}.kmore{display:none}</style></noscript>'
            % (''.join(card(m) for m in got), len(got) - fold))


HUB_FIRST = 12      # 허브 '최근 글'이 처음 보이는 카드 수(3열 네 줄). LIST_CSS 의 .kfold nth-child(n+13) 과 짝이다


def city_sido(name):
    """지역 칩 이름 → 시도 키. '서울 전체' 꼴(시도 글)은 그 시도, 시군구는 코드 접두에서(손 표 없음). 모르면 None."""
    import sido_zones as SZ
    if name.endswith(' 전체'):
        k = SZ.key_of(name[:-3])
        return k if k in SZ.ORDER else None
    try:
        import make_city_moveins as MCM
        return MCM.sido_of(name)
    except Exception:
        return None


def city_groups(metas):
    """[(시도 화면 이름, [지역 칩 이름…])] — 글의 city 에서 모아 시도 표시 순서(DISPLAY_ORDER)로.

    한 시도 안에서는 이름 순이라 시와 그 구가 붙어 선다('부천' 다음 '부천 오정구'·'부천 원미구' — 글 수 순일 때는 '부천'이
    13번째, '부천 원미구'가 2번째로 떨어져 섰다, 2026-11-07 디자인 검수). 구 칩만 둘 이상인 시('고양 덕양구'·'고양 일산동구')는
    시 칩('고양')을 앞에 하나 더 세운다 — 시 칩은 앞말로 걸러(FILTER_JS) 그 시의 구 글을 모두 남긴다. 시도 이름('서울')은
    시 칩으로 세우지 않는다('서울 전체'가 따로 있다).
    """
    import sido_zones as SZ
    by = {}
    for m in metas:
        for c in post_cities(m):
            by.setdefault(city_sido(c) or '', set()).add(c)
    sido_names = set(SZ.ORDER) | set(SZ.DISPLAY_NAME.values())
    for z, names in by.items():
        heads = {}
        for c in names:
            if ' ' in c:
                heads.setdefault(c.split(' ')[0], set()).add(c)
        for h, kids in heads.items():
            if h not in names and h not in sido_names and len(kids) >= 2:
                names.add(h)
    order = [z for z in SZ.DISPLAY_ORDER if z in by] + sorted(k for k in by if k not in SZ.DISPLAY_ORDER)
    key = lambda c: (c.split(' ')[0], ' ' in c and not c.endswith(' 전체'), c)     # 시·'○○ 전체'가 그 구들 앞
    return [(SZ.DISPLAY_NAME.get(z, z) if z else '그 밖', sorted(by[z], key=key)) for z in order]


def _chip_label(c, names):
    """지역 칩 글자 — 바로 앞에 그 시의 칩이 있는 구는 구 이름만('부천' 다음의 '원미구'). 거르는 값(data-city)은 이름 그대로다."""
    head, _, rest = c.partition(' ')
    return rest if rest and head in names and not rest.endswith('전체') else c


def city_chips(metas, total_label='글'):
    """'지역으로 찾기' — 시도별 칩 줄. 칩은 button(JS 가 거른다). JS 없이는 모두 보이는 목록이라 입구 구실은 그대로다.

    첫 줄의 '전체' 칩은 거름을 푸는 단추라 글자도 '전체 N편'이다('글 N편'은 편수 이름표로 읽혀 눌리는 줄 몰랐다).
    """
    groups = city_groups(metas)
    if not groups:
        return ''
    rows = ['<div class="cf-g"><em></em><span class="cf-c"><button type="button" class="rchip on" data-city="">전체 %d편</button></span></div>'
            % len(metas)]
    for sido, cities in groups:
        names = set(cities)
        rows.append('<div class="cf-g"><em>%s</em><span class="cf-c">%s</span></div>' % (html.escape(sido), ''.join(
            '<button type="button" class="rchip" data-city="%s">%s</button>'
            % (html.escape(c), html.escape(_chip_label(c, names))) for c in cities)))
    # 거른 수 줄은 거를 때만 보인다(hidden) — 전체일 때는 '전체' 칩이 이미 편수를 말한다.
    return '<nav class="cityf" aria-label="지역으로 찾기">%s</nav><p class="cf-n" hidden>%s %d편</p>' % (''.join(rows), html.escape(total_label), len(metas))


# 지역 칩이 카드를 거르는 스크립트. 칩을 다시 누르면 푼다. 거른 수는 .cf-n 에 적는다.
# 거르기는 이름 그대로이거나 **앞말 + 빈칸**이 같으면 남긴다 — '부천' 칩이 '부천 원미구'·'부천 오정구' 글까지 남긴다(정확 일치일
# 때는 '수원'을 누르면 영통구 글 4편이 숨었다, 2026-11-07 디자인 검수). 빈칸까지 보므로 '광주'가 '광주시' 꼴을 잘못 잡지 않는다.
# 허브 '최근 글'의 접힘(.kfold)은 거르는 동안 풀고(맞는 글이 모두 보인다), '더 보기'를 누르면 아주 푼다.
FILTER_JS = ("<script>(function(){var g=document.querySelector('.kgrid.kfold'),mb=document.querySelector('.kmore'),open=false;"
             "if(mb)mb.addEventListener('click',function(){open=true;if(g)g.classList.remove('kfold');mb.hidden=true});"
             "var f=document.querySelector('.cityf');if(!f)return;"
             "var cards=document.querySelectorAll('.kgrid .kcard[data-city]'),n=document.querySelector('.cf-n');"
             "f.addEventListener('click',function(e){var b=e.target.closest('.rchip');if(!b)return;e.preventDefault();"
             "var c=b.getAttribute('data-city')||'',on=!!c&&!b.classList.contains('on'),k=0;"
             "f.querySelectorAll('.rchip.on').forEach(function(x){x.classList.remove('on')});"
             "cards.forEach(function(x){var d='|'+x.getAttribute('data-city')+'|',"
             "s=!on||d.indexOf('|'+c+'|')>=0||d.indexOf('|'+c+' ')>=0;x.hidden=!s;if(s)k++});"
             "(on?b:f.querySelector('.rchip[data-city=\\\"\\\"]')).classList.add('on');"
             "if(g)g.classList.toggle('kfold',!on&&!open);if(mb)mb.hidden=on||open;"
             "if(n){n.textContent=(on?c+' ':'')+'글 '+k+'편';n.hidden=!on}});})();</script>")


def questions_block(metas):
    """'질문으로 찾기' — 질문 넷. 글 수와 최신 결론 둘은 글에서 센다. 글이 없는 질문도 입구는 둔다(준비 중)."""
    out = []
    for k, q, _short, sec in TOPICS:
        posts = _newest([m for m in metas if topic_of(m) == k])
        hooks = ''.join('<li>%s</li>' % html.escape(m['title']) for m in posts[:2])
        out.append('<a class="qcard" href="/%s/"><b>%s</b><span class="qc-n">%s</span>%s</a>'
                   % (sec, html.escape(q), ('글 %d편' % len(posts)) if posts else '준비 중',
                      ('<ul>%s</ul>' % hooks) if hooks else ''))
    return '<div class="qgrid">%s</div>' % ''.join(out)


def section_chips(cur=None):
    """섹션(질문) 사이를 건너뛰는 칩. 첫 칩은 '전체'(허브). 이름은 TOPICS 의 짧은 이름 — 허브 질문 카드와 같은 넷이다."""
    out = ['<a class="rchip" href="/%s/">전체</a>' % REPORTS_DIR]
    for k, _q, short, sec in TOPICS:
        # 지금 섹션은 aria-current(테두리 꼴) — 지역 칩의 '켜짐'(채움)과 같은 꼴이면 어느 것이 페이지인지 갈리지 않았다.
        out.append('<a class="rchip" href="/%s/"%s>%s</a>' % (sec, ' aria-current="page"' if sec == cur else '', html.escape(short)))
    return '<nav class="rchips" aria-label="질문으로 찾기">%s</nav>' % ''.join(out)


def _sgg_anchor(data, name):
    """지역 이름 → 홈 시세 지도 주소. 시군구 하나로 풀리면 그 칸의 그래프(#stats-market-week~코드), 구가 여럿이거나 모르면 지도 자체."""
    try:
        got = CT.sgg_codes(data, name) if data else []
    except Exception:
        got = []
    if len(got) == 1:
        return '/#stats-market-week~%s' % got[0][0], got[0][1]
    return '/#stats-market-week', name        # 구가 여럿인 시('수원')는 첫 구가 아니라 지도 자체로


def region_box(meta, data, others=None):
    """글 끝 '이 지역 더 보기' — 시도 리포트, 홈 시세 지도(첫 도시 칸), 같은 도시의 입주물량 글(있으면). 양방향 연결의 글 쪽."""
    rows = []
    zone = zone_of(meta) if meta.get('region') else None
    if zone:
        # 시도 키로 찾는다 — 도시 글(region '수원')은 region 이 시도가 아니라 리포트 카드가 빠졌다(2026-11-07 디자인 검수).
        z = _zone_link(zone)
        if z:
            rows.append(z)
    cities = [c for c in (meta.get('city') or []) if c]
    if cities:
        href, label = _sgg_anchor(data, cities[0])
        rows.append('<a href="%s"><span>시세 지도</span>%s 주간 시세</a>' % (href, html.escape(label)))
    elif meta.get('region'):
        rows.append('<a href="/#stats-market-week"><span>시세 지도</span>%s 주간 시세</a>' % html.escape(_region_disp(meta['region'])))
    heads = {c.split(' ')[0] for c in cities}
    for o in _newest(others or []):
        if o['section'] == 'city' and o['slug'] != meta['slug'] and heads & {c.split(' ')[0] for c in (o.get('city') or [])}:
            rows.append('<a href="/city/%s/"><span>%s</span>%s</a>' % (o['slug'], html.escape(TOPIC_BY['moveins'][1]), html.escape(o['title'])))
            break
    if not rows:
        return ''
    rows[0] = rows[0].replace('<a ', '<a class="cgo" ', 1)     # 첫 행동 하나만 채운다(LIST 밖 EXTRA_CSS .cgo)
    return '<section class="cmore"><h2>이 지역 더 보기</h2><div class="cmore-l">%s</div></section>' % ''.join(rows)


_LEAD_THUMB = re.compile(r'^\s*!\[[^\]]*\]\([^)]*-thumb\.png\)[ \t]*\n+')


def strip_lead_thumb(body_md):
    """본문 첫 줄의 제목 카드 그림(img/<slug>-thumb.png)을 뺀다 — 제목이 글 머리와 그림에서 두 번 보였다(11-05 개편)."""
    return _LEAD_THUMB.sub('', body_md, count=1)


IMG_HINT = '눌러서 크게 보기'


def content_img_src(body_html, sec):
    """원고의 상대 그림 주소(img/x.png)를 원고 폴더의 절대 주소(/content/<섹션>/img/x.png)로.

    원고는 content/<섹션>/ 옆에 그림을 두고 상대 경로로 쓰는데, 페이지는 /<섹션>/<글>/ 에 구워져
    상대 경로가 /<섹션>/<글>/img/… 를 가리켰다 — 그런 파일은 없어 단지 글 그림이 모두 깨졌다(2026-10-30
    디자인 리뷰). 그림은 복사하지 않고 원고 폴더 한 곳에 둔다(content/ 는 Pages 배포에 포함된다)."""
    out = re.sub(r'(<img src=")(?![a-z]+:|/|#)([^"]+)"',
                  lambda m: '%s/content/%s/%s"' % (m.group(1), sec, m.group(2)), body_html)

    # 원본으로 여는 링크로 감싼다 — 단 폭으로 줄인 표 그림을 휴대폰에서 크게 볼 길(2026-10-31 디자인 리뷰 2차).
    def wrap(m):
        return '<a class="cimg" href="%s" target="_blank" rel="noopener">%s</a>' % (m.group(1), m.group(0))

    # 혼자 선 그림(문단 하나가 그림 하나)은 figure 로 굽고 밑에 그림 이름·'눌러서 크게 보기'를 단다 — 지도·표 캡처가 단 폭으로
    # 줄어 글자가 3~4px 인데 눌러지는 표시가 없었다(2026-11-07 디자인 검수). 문장 속 그림은 링크만 둔다.
    def fig(m):
        img = m.group(1)
        src = re.search(r'src="([^"]+)"', img).group(1)
        alt = re.search(r'alt="([^"]*)"', img)
        cap = (alt.group(1) + ' · ') if alt and alt.group(1) else ''      # alt 는 이미 이스케이프된 글자다(_inline)
        return ('<figure class="cfig">%s<figcaption>%s<a href="%s" target="_blank" rel="noopener">%s</a></figcaption></figure>'
                % (re.sub(r'<img src="([^"]+)"([^>]*)>', wrap, img), cap, src, IMG_HINT))
    alone = re.compile(r'^<p>\s*(<img [^>]*>)\s*</p>$')
    parts = re.split(r'(<p>\s*<img [^>]*>\s*</p>)', out)
    return ''.join(alone.sub(fig, p) if alone.match(p) else re.sub(r'<img src="([^"]+)"([^>]*)>', wrap, p) for p in parts)


def build_page(meta, body_md, data, prev=None, nxt=None, others=None):
    data = CT.for_post(data, meta)     # 도시 3년 창·그림 기본 연도는 이 글의 작성 연도가 정한다
    filled, blocks = fill_placeholders(strip_lead_thumb(body_md), data, key=_key_of(meta))
    sec = meta['section']
    body_html = content_img_src(restore_tables(markdown(filled), blocks), sec)
    url = '%s/%s/%s/' % (SITE, sec, meta['slug'])
    srcs = meta.get('sources') or []
    nav = []
    if prev:
        nav.append('<a class="cnav-p" href="/%s/%s/"><span>이전 글</span>%s</a>' % (sec, prev['slug'], html.escape(prev['title'])))
    if nxt:
        nav.append('<a class="cnav-n" href="/%s/%s/"><span>다음 글</span>%s</a>' % (sec, nxt['slug'], html.escape(nxt['title'])))
    more = region_box(meta, data, others)
    if meta.get('region') and not more:
        z = _zone_link(zone_of(meta) or meta['region'])
        if z:
            nav.append(z.replace('<a ', '<a class="cnav-hub" ', 1))
    # 글 끝에서 섹션 목록으로 돌아가는 길(2026-11-07 디자인 검수 — 머리 눈썹·빵부스러기에만 있었다).
    tk = topic_of(meta)
    nav.append('<a class="cnav-hub" href="/%s/"><span>이 질문의 글 모두</span>%s</a>'
               % (TOPIC_BY[tk][2], html.escape(TOPIC_BY[tk][0])))
    faq_html = ''
    if meta.get('faq'):
        items = ''.join('<dt>%s</dt><dd>%s</dd>' % (html.escape(f['q']), html.escape(f['a']))
                        for f in meta['faq'])
        faq_html = '<section class="cfaq"><h2>자주 묻는 질문</h2><dl>%s</dl></section>' % items
    src_html = ''
    if srcs:
        src_html = ('<section class="csrc-s"><h2>숫자의 출처</h2><ul class="csrc">%s</ul></section>'
                    % ''.join('<li>%s</li>' % html.escape(s) for s in srcs))
    # 글 머리(11-05 개편): 눈썹(질문 · 지역) → 제목 → 메타 → 3줄 요약 → 이 글이 맞는 분 → 핵심 숫자 띠 → 본문.
    # summary 는 설명 메타·og·JSON-LD·피드에 남고 화면에서는 3줄 요약이 그 자리다(둘 다 두면 같은 말이 두 번).
    tkey = topic_of(meta)
    cities = post_cities(meta)
    eyebrow = '<p class="eyebrow"><a href="/%s/">%s</a>%s</p>' % (
        TOPIC_BY[tkey][2], html.escape(TOPIC_BY[tkey][0]),
        (' · ' + html.escape(' · '.join(cities))) if cities else '')
    head = ''
    if meta.get('tldr'):
        head += '<div class="ctldr"><b>3줄 요약</b><ol>%s</ol></div>' % ''.join('<li>%s</li>' % html.escape(x) for x in meta['tldr'])
    if meta.get('audience'):
        head += '<p class="caud"><b>이 글이 맞는 분</b>%s</p>' % html.escape(meta['audience'])
    key = _key_of(meta)
    if key:
        head += '<div class="ckey"><strong>%s</strong><span>%s</span></div>' % (html.escape(key['value']), html.escape(key.get('label') or ''))
    if not head:
        head = '<p class="csum">%s</p>' % html.escape(meta['summary'])   # 옛 양식 글(lenient) — 결론 상자로 되돌아간다
    body = (
        '<header class="post-head"><div class="wrap">'
        '<nav class="crumb"><a href="/">아공맵</a> › <a href="/%s/">%s</a> › <a href="/%s/">%s</a></nav>'
        '%s<h1>%s</h1>'
        '<p class="cmeta">%s 작성 · %s 갱신 · <a href="/about/">%s</a></p>'
        '</div></header>'
        '<section><div class="wrap">'
        '%s'
        '<div class="cbody">%s</div>'
        '%s%s%s'
        '<div class="cnav">%s</div>'
        '</div></section>'
        % (REPORTS_DIR, html.escape(REPORTS_TITLE), sec, html.escape(SECTION_META[sec][0]), eyebrow, html.escape(meta['title']),
           _day_long(meta['date']), _day_long(meta['updated']), AUTHOR,
           head, body_html, src_html, faq_html, more,
           ''.join(nav)))
    # 제목·요약은 <title> 과 og 속성 값에 들어간다. 반박 글 제목에는 발언을 그대로 옮긴 큰따옴표가 있어
    # 이스케이프하지 않으면 속성이 그 자리에서 끊긴다(2026-10-29 게이트가 잡았다).
    # 글은 읽는 단(desk 'read') — 넓은 단(wide)이면 1280px 에서 본문 한 줄이 70자를 넘고 결론 상자와 본문 폭이 달랐다
    # (2026-10-30 디자인 리뷰). 넓은 표는 .ctab 상자 안에서 옆으로 민다.
    page = I.fill(I.SHELL, desk='read', title=html.escape('%s | 아공맵' % meta['title']),
                  ogtitle=html.escape(meta['title']), desc=html.escape(meta['summary']), url=url, body=body,
                  ld=_ld(meta, url, body_html), src='',   # 출처는 본문 '숫자의 출처'(src_html)에 있다 — 푸터에 되풀이하지 않는다
                  nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    page = re.sub(r'<meta property="og:image" content="[^"]*">',
                  '<meta property="og:image" content="%s">' % html.escape(og_image(meta)), page, count=1)
    return page, meta['updated']


def build_index(sec, posts_meta):
    """섹션 목록 페이지 — 질문을 머리로, 한 줄 소개, 질문 칩(섹션 사이 건너뛰기), 그 섹션 글의 지역 칩, 카드 목록(허브와 같은 부품)."""
    name, desc = SECTION_META[sec]
    url = '%s/%s/' % (SITE, sec)
    q = TOPIC_BY[SECTION_TOPIC[sec]][0]
    items = cards_grid(posts_meta) if posts_meta else '<p>아직 글이 없습니다.</p>'
    body = ('<header class="hub-head"><div class="wrap">'
            '<nav class="crumb"><a href="/">아공맵</a> › <a href="/%s/">%s</a> › <b>%s</b></nav>'
            '<h1>%s</h1><p class="cmeta">%s</p></div></header>'
            '<section><div class="wrap">%s%s%s</div></section>%s'
            % (REPORTS_DIR, html.escape(REPORTS_TITLE), html.escape(name), html.escape(q), html.escape(desc),
               section_chips(sec), city_chips(posts_meta), items, FILTER_JS if posts_meta else ''))
    lastmod = max([m['updated'] for m in posts_meta], default=None)
    page = I.fill(I.SHELL, title=html.escape('%s | 아공맵' % name), ogtitle=html.escape(name),
                  desc=html.escape(desc), url=url, body=body,
                  ld=I.ld_pack(name, desc, url, name, lastmod or I.PUBLISHED, kind='CollectionPage'),
                  src='', nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    return page, lastmod


REPORTS_DIR = 'reports'
REPORTS_TITLE = '콘텐츠'          # 탭·빵부스러기 이름(site_nav 탭 '콘텐츠'와 같다)
# 허브 페이지 제목·h1·JSON-LD — '콘텐츠'는 검색어가 없다(2026-11-12 SEO 점검·대표 결정). 탭 이름은 그대로 REPORTS_TITLE.
REPORTS_NAME = '부동산 공급 리포트'
REPORTS_DESC = '질문이나 내 동네로 들어와 결론부터 읽는 글. 숫자는 국가 통계에서 옵니다.'

# ── '기본 개념' 줄(대표 승인 2026-10-30) ──────────────────────────────────────────────────────────────
# 상단 탭에서 '사이클'을 빼면서(site_nav.TABS) 그 입구를 여기로 옮겼다. 발행 주기가 없는 상시 글이라
# 카테고리 카드(발행 주기 순) **아래**에 둔다. 사이클이 첫째다 — 탭이 주된 통로였으니 허브에서 눈에
# 띄어야 한다(GA 10/2~10/29: /cycle/ 세션 26 중 19가 사이트 안 이동).
#
# ⚠️ 이름과 곁말을 여기에 손으로 적지 않는다. 각 페이지의 <title> 에서 읽는다('이름 — 곁말 | 아공맵').
#    손 페이지의 제목을 고치면 이 줄도 따라 바뀐다. 파일이 없으면 그 카드만 빠진다.
BASIC_H2 = '기본 개념'
BASIC_PAGES = ('cycle', 'faq', 'burini-test', 'investor-test', 'redev-test')
_TITLE_RE = re.compile(r'<title>([^<]*)</title>')


def _page_title(slug, root=ROOT):
    """손 페이지 <title> → (이름, 곁말). 못 읽으면 (None, None) — 그 카드는 싣지 않는다."""
    p = os.path.join(root, slug, 'index.html')
    try:
        m = _TITLE_RE.search(io.open(p, encoding='utf-8').read())
    except (IOError, OSError):
        return None, None
    if not m:
        return None, None
    head = m.group(1).split('|')[0].strip()          # '… | 아공맵' 의 앞부분
    name, _, sub = head.partition('—')               # 엠대시 앞이 이름, 뒤가 곁말
    return (name.strip() or None), sub.strip()


def basic_row(root=ROOT):
    """'기본 개념' 칩 줄 — 허브 '지역으로 찾기' 바로 아래. 이름은 각 페이지 <title> 에서 읽는다.

    11-05 개편 때 카드 다섯 장을 맨 아래 13px 한 줄(중점 다섯 개)로 줄였더니 40장 카드 뒤 푸터와 같은 꼴이라 입구 구실을
    못 했다(2026-11-07 디자인 검수). 절 제목(.rh2)과 칩(.rchip)으로 질문·지역 입구와 같은 급에 둔다."""
    out = []
    for slug in BASIC_PAGES:
        name, _sub = _page_title(slug, root)
        if name:
            out.append('<a class="rchip" href="/%s/">%s</a>' % (slug, html.escape(name)))
    if not out:
        return ''
    return ('<section class="hub-basic"><div class="wrap"><h2 class="rh2">%s</h2><nav class="rchips" aria-label="%s">%s</nav>'
            '</div></section>' % (html.escape(BASIC_H2), html.escape(BASIC_H2), ''.join(out)))


def build_reports(all_metas, data=None):
    """콘텐츠 허브(2026-11-05 개편) — '질문으로 찾기' 넷, '지역으로 찾기' 시도별 칩, '기본 개념' 칩, 최근 글(첫 HUB_FIRST 장 + 더 보기).

    옛 허브(카테고리 카드 여섯 장, 10-29·10-30 결정)는 '무엇이 내 관심사인지' 말하지 못했다(대표 11-05). 독자는 질문이나 내
    동네로 들어와 결론 카드로 글을 고른다.
    """
    newest = _newest(all_metas)
    body = ('<header class="hub-head"><div class="wrap">'
            '<nav class="crumb"><a href="/">아공맵</a> › <b>%s</b></nav>'
            '<h1>%s</h1><p class="cmeta">%s</p></div></header>'
            '<section class="hub-q"><div class="wrap"><h2 class="rh2">질문으로 찾기</h2>%s</div></section>'
            '<section class="hub-city"><div class="wrap"><h2 class="rh2">지역으로 찾기</h2>%s</div></section>%s'
            '<section class="hub-recent"><div class="wrap"><h2 class="rh2">최근 글</h2>%s</div></section>%s'
            % (html.escape(REPORTS_TITLE), html.escape(REPORTS_NAME), html.escape(REPORTS_DESC),
               questions_block(all_metas), city_chips(all_metas), basic_row(),
               cards_grid(newest, fold=HUB_FIRST) if newest else '<p>아직 글이 없습니다.</p>', FILTER_JS))
    url = '%s/%s/' % (SITE, REPORTS_DIR)
    lastmod = max([m['updated'] for m in all_metas], default=None)
    page = I.fill(I.SHELL, title=html.escape('%s | 아공맵' % REPORTS_NAME),
                  ogtitle=html.escape(REPORTS_NAME), desc=html.escape(REPORTS_DESC),
                  url=url, body=body, ld=I.ld_pack(REPORTS_NAME, REPORTS_DESC, url, REPORTS_TITLE,
                                                   lastmod or I.PUBLISHED, kind='CollectionPage'),
                  src='', nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    return page, lastmod


HOME_START, HOME_END = '<!--CONTENT_RECENT_START-->', '<!--CONTENT_RECENT_END-->'
HOME_RECENT = 6
_HOME_RE = re.compile(re.escape(HOME_START) + r'(.*?)' + re.escape(HOME_END), re.S)


def home_recent_html(metas):
    """홈 '최근 리포트' 묶음. 콘텐츠 목록과 **같은 부품**을 쓴다(요청 ④) — 썸네일·꼬리표가 한 벌로 간다."""
    if not metas:
        return ''
    return ('<div class="crecent"><h2>최근 리포트</h2>%s'
            '<p class="crecent-all"><a href="/%s/">콘텐츠 전체 보기 →</a></p></div>' % (cards_grid(metas, HOME_RECENT), REPORTS_DIR))


def write_home_recent(metas, root=ROOT):
    """홈(index.html)의 표식 구간만 고쳐 쓴다. 표식이 없으면 조용히 건너뛰지 않고 알린다.

    ⚠️ 구간 **밖**은 건드리지 않는다. 홈은 손으로 관리하는 파일이고 여러 세션이 같이 고친다
       (make_home_summary 와 같은 규칙 — 대표 확인 2026-09-27).
    """
    p = os.path.join(root, HS.HOME)
    s = io.open(p, encoding='utf-8', newline='').read()
    if len(_HOME_RE.findall(s)) != 1:
        print('  ⚠️ index.html 에 CONTENT_RECENT 표식 쌍이 하나가 아니다 — 홈 묶음은 건너뛴다')
        return False
    nl = '\r\n' if '\r\n' in s else '\n'
    body = home_recent_html(metas)
    inner = nl + ((body + nl) if body else '')
    out = _HOME_RE.sub(lambda m: HOME_START + inner + HOME_END, s)
    if out == s:
        return False
    io.open(p, 'w', encoding='utf-8', newline='').write(out)
    return True


ZONE_START, ZONE_END = N.SLOT_ZONE_POSTS      # 정본은 site_nav(keep_dates 가 이 구간을 가리고 견준다)
_ZONE_RE = re.compile(re.escape(ZONE_START) + r'(.*?)' + re.escape(ZONE_END), re.S)


def zone_of(meta):
    """글의 region → 시도 키. 시군구면 홈 이름표와 시군구 코드 접두에서 읽는다(손 표를 두지 않는다).

    region 이 비었거나 어느 시도인지 알 수 없으면 None — 그 글은 지역 묶음에 싣지 않는다.
    """
    import sido_zones as SZ
    name = (meta.get('region') or '').strip()
    if not name:
        return None
    if name in SZ.ORDER:
        return name
    if SZ.key_of(name) in SZ.ORDER:
        return SZ.key_of(name)
    try:
        import make_city_moveins as MCM
        return MCM.sido_of(name)
    except Exception:
        return None


def zones_of(meta):
    """글이 묶이는 시도들 — region 의 시도와 city 마다의 시도(11-05 개편: 분당 글은 city '성남 분당구'로도 경기에 묶인다)."""
    out = set()
    z = zone_of(meta)
    if z:
        out.add(z)
    for c in meta.get('city') or []:
        z = city_sido(c)
        if z:
            out.add(z)
    return out


def zone_posts_html(metas):
    """시도 리포트 아래에 붙는 '이 지역 글' 묶음 — 허브와 같은 카드(11-05 개편). 갱신일 최신 순."""
    if not metas:
        return ''
    # 리포트의 다른 절과 같은 본문 틀(.wrap) 안에 둔다 — 예전엔 틀 밖이라 375px 에서 좌우 여백이 0, 1280px 에서는
    # 오른쪽 본문 단과 어긋났다(2026-10-30 디자인 리뷰).
    return ('<section class="zposts"><div class="wrap"><div class="crecent"><h2>이 지역 글</h2>%s</div></div></section>'
            % cards_grid(metas))


def write_zone_posts(metas, root=ROOT):
    """시도 리포트(zone/<시도>/index.html)의 표식 구간만 고쳐 쓴다 — 홈 묶음과 같은 규칙이다.

    ⚠️ 구간 밖은 건드리지 않는다. 글이 없는 시도는 구간을 비운다(지난 회차의 글이 남지 않게).
       표식이 없는 페이지는 건너뛴다 — make_sido_pages 가 아직 그 판을 굽지 않은 회차다.
    """
    import sido_zones as SZ
    by = {}
    for m in metas:
        for z in zones_of(m):
            by.setdefault(z, []).append(m)
    done = 0
    for z in SZ.ORDER:
        p = os.path.join(root, 'zone', z, 'index.html')
        if not os.path.exists(p):
            continue
        s = io.open(p, encoding='utf-8', newline='').read()
        if len(_ZONE_RE.findall(s)) != 1:
            continue
        nl = '\r\n' if '\r\n' in s else '\n'
        body = zone_posts_html(by.get(z) or [])
        out = _ZONE_RE.sub(lambda m: ZONE_START + nl + ((body + nl) if body else '') + ZONE_END, s)
        if out != s:
            io.open(p, 'w', encoding='utf-8', newline='').write(out)
        if body:
            done += 1                 # 글이 실린 시도만 센다(빈 구간을 비운 것도 변경이라 따로 센다)
    return done


#  ── /weekly/ 아래 '이 수치로 따져 본 글' 칸(총괄 요청 2026-10-30) ─────────────────────────────────────────
# 주간 시세 페이지를 끝까지 읽은 사람에게 다음에 읽을 글을 준다. 2026-10-26까지는 네이버 블로그의 주간 해설
# 글을 가리켰는데, 그 발행을 멈추기로 하면서(10-26·10-29 대표 결정) 묵은 글만 걸렸다. 같은 일을 하는 글이
# 사이트에 생겼으니(/column/ 반박 편 — 공직자 발언을 주간 시세와 입주 물량으로 따진다) 그 최신 글을 싣는다.
#
# ⚠️ 자리(표식)는 make_weekly_page.put_column_slot 이 내고, 내용은 여기서 채운다. 주간 생성기는 그 구간을
#    읽지도 쓰지도 않는다(제 'N개 시도' 치환조차 구간을 비껴간다). 발행 워크플로는 이 생성기만 돌리므로,
#    column 글이 올라온 날 바로 이 칸이 바뀐다 — 주간 배치(주 1회)를 기다리지 않는다.
WEEKLY_PAGE = os.path.join('weekly', 'index.html')
WEEKLY_START, WEEKLY_END = '<!--WK:COLUMN-->', '<!--/WK:COLUMN-->'
WEEKLY_H2 = '이 수치로 따져 본 글'
WEEKLY_SEC = 'column'          # 이 칸에 싣는 섹션. 주간 시세를 근거로 쓰는 글이 반박 편이다
_WEEKLY_RE = re.compile(re.escape(WEEKLY_START) + r'(.*?)' + re.escape(WEEKLY_END), re.S)


def weekly_column_html(metas):
    """/weekly/ 칸의 안쪽. 최신 반박 글 한 편과 콘텐츠 허브 링크. 글이 없으면 허브 링크만 남는다.

    뼈대의 `.links` 스타일(주간 페이지 '더 둘러보기'와 같은 부품)을 그대로 쓴다 — 이 칸만의 CSS 가 없다.
    """
    rows = []
    posts = sorted([m for m in metas if m['section'] == WEEKLY_SEC],
                   key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    if posts:
        m = posts[0]
        rows.append('    <a href="/%s/%s/">%s<span>%s · %s 갱신</span></a>'
                    % (m['section'], m['slug'], html.escape(m['title']),
                       html.escape(SECTION_META[m['section']][0]), _day_short(m['updated'])))
    # 섹션 이름은 SECTION_META 에서 읽는다 — 섹션이 늘거나 이름이 바뀌면 이 곁말도 따라온다.
    names = ' · '.join(SECTION_META[k][0] for k in CM.SECTIONS)
    rows.append('    <a href="/%s/">%s<span>%s</span></a>'
                % (REPORTS_DIR, html.escape('%s 전체 보기' % REPORTS_TITLE), html.escape(names)))
    return '\n'.join(['<section><div class="wrap">', '  <h2>%s</h2>' % html.escape(WEEKLY_H2),
                      '  <div class="links">'] + rows + ['  </div>', '</div></section>'])


def write_weekly_column(metas, root=ROOT):
    """/weekly/index.html 의 표식 구간만 고쳐 쓴다 — 홈·지역 묶음과 같은 규칙이다.

    표식이 없으면 건너뛴다(주간 생성기가 아직 자리를 안 낸 회차). 구간 밖은 건드리지 않는다.
    """
    p = os.path.join(root, WEEKLY_PAGE)
    if not os.path.exists(p):
        return False
    s = io.open(p, encoding='utf-8', newline='').read()
    if len(_WEEKLY_RE.findall(s)) != 1:
        return False
    nl = '\r\n' if '\r\n' in s else '\n'
    body = weekly_column_html(metas)
    out = _WEEKLY_RE.sub(lambda m: WEEKLY_START + nl + body.replace('\n', nl) + nl + WEEKLY_END, s)
    if out == s:
        return False
    io.open(p, 'w', encoding='utf-8', newline='').write(out)
    return True


#  ── /moveins/ 의 '도시별 입주 예정 단지' 칸(총괄 결정 2026-10-30) ─────────────────────────────────────────
# 2026-10-07부터 네이버 블로그의 도시 입주물량 편을 가리켰다(백로그 37). 네이버 발행이 끝나 묵은 글만
# 남았고, 같은 주제의 글이 사이트에 생겼다(/city/ 도시 입주물량 편). 자리(표식)는 make_indicator_pages 가
# 내고 내용은 여기서 채운다 — /weekly/ 해설 칸과 같은 나눔이고, 이유도 같다(그쪽 주석 참조).
MOVEINS_PAGE = os.path.join('moveins', 'index.html')
MOVEINS_START, MOVEINS_END = N.SLOT_MOVEINS_CITY
MOVEINS_H2 = '도시별 입주 예정 단지'
MOVEINS_SEC = 'city'
MOVEINS_MAX = 6                 # 칸에 싣는 글 수. 더 많아지면 '전체 보기'로 보낸다
_MOVEINS_RE = re.compile(re.escape(MOVEINS_START) + r'(.*?)' + re.escape(MOVEINS_END), re.S)


def moveins_cities_html(metas):
    """/moveins/ 칸의 안쪽. 도시 입주물량 편 최신 몇 편과 섹션 전체 링크. 글이 없으면 칸을 비운다.

    /moveins/ 뼈대의 `.links` 스타일을 그대로 쓴다(옛 블로그 칸과 같은 부품) — 이 칸만의 CSS 가 없다.
    """
    posts = sorted([m for m in metas if m['section'] == MOVEINS_SEC],
                   key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    if not posts:
        return ''                      # 빈 약속을 굽지 않는다 — 칸째 사라진다
    rows = ['    <a href="/%s/%s/">%s<span>%s 갱신</span></a>'
            % (m['section'], m['slug'], html.escape(m['title']), _day_short(m['updated']))
            for m in posts[:MOVEINS_MAX]]
    note = '도시마다 입주 예정 단지를 이름·입주 월·세대수까지 적고, 한 해 적정물량과 견줍니다.'
    if len(posts) > MOVEINS_MAX:
        note += ' 글 %d편 전체는 <a href="/%s/">%s</a> 에 있습니다.' % (
            len(posts), MOVEINS_SEC, html.escape(SECTION_META[MOVEINS_SEC][0]))
    return ('<section class="wrap">\n  <h2>%s</h2>\n  <div class="links">\n%s\n  </div>\n'
            '  <div class="note">%s</div>\n</section>' % (html.escape(MOVEINS_H2), '\n'.join(rows), note))


def write_moveins_cities(metas, root=ROOT):
    """/moveins/index.html 의 표식 구간만 고쳐 쓴다. 표식이 없으면 건너뛴다(지표 생성기가 아직 안 돈 회차)."""
    p = os.path.join(root, MOVEINS_PAGE)
    if not os.path.exists(p):
        return False
    s = io.open(p, encoding='utf-8', newline='').read()
    if len(_MOVEINS_RE.findall(s)) != 1:
        return False
    nl = '\r\n' if '\r\n' in s else '\n'
    body = moveins_cities_html(metas)
    inner = nl + ((body.replace('\n', nl) + nl) if body else '')
    out = _MOVEINS_RE.sub(lambda m: MOVEINS_START + inner + MOVEINS_END, s)
    if out == s:
        return False
    io.open(p, 'w', encoding='utf-8', newline='').write(out)
    return True


def collect(root=ROOT, strict=False, old_format=None):
    """[(섹션, meta, 본문)], [건너뛴 사유] — 원고를 읽고 검사한다. old_format 목록을 주면 옛 양식으로 구운 글을 거기 적는다.

    ⚠️ 규약을 어긴 원고 하나 때문에 배치를 세우지 않는다. 그 글만 건너뛰고 경고를 남긴 뒤 나머지를 굽는다 —
       콘텐츠 원고는 여러 세션이 수시로 올리는데, 한 편의 오타가 그날의 데이터 갱신까지 막으면 손해가 크다
       (2026-10-27: 첫 19편이 들어오자마자 시군구 자리표에서 걸렸다). 건너뛴 글은 배치 보고에 뜬다.
       strict=True 는 사람이 손으로 돌려 원고를 고칠 때 쓴다 — 첫 오류에서 멈춘다.
    """
    out, skipped = [], []
    old_format = old_format if old_format is not None else []
    for sec, slug, path in CM.posts(root):
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError as e:
            if CM.is_v2_miss(e):
                # 2026-11-05 양식(다섯 항목)이 없는 옛 원고는 굽되 경고한다 — 카드에 지역 칩·핵심 숫자가 빠지고 글 머리는
                # 결론 상자로 돌아간다. 다른 세션이 옛 양식으로 올린 글 한 편이 그날 발행 전체를 막지 않게(11-06).
                meta, body = CM.read(path, sec, slug, lenient=True)
                old_format.append('%s/%s' % (sec, slug))
                out.append((sec, meta, body))
                continue
            if strict:
                raise
            skipped.append(str(e))
            continue
        out.append((sec, meta, body))
    return out, skipped


def _warn(msg):
    """배치 로그에 경고를 남긴다(GitHub Actions 에서는 실행 화면 주석으로도 뜬다) — 다른 생성기와 같은 방식."""
    print(('::warning::' if os.environ.get('GITHUB_ACTIONS') else '  ⚠️ ') + msg)


def _crash_note(sec, meta, err, where):
    """원고 한 편을 굽다 난 **예상 밖 예외**의 한 줄. 배치는 그 글만 건너뛰고 나머지를 굽는다.

    왜 넓게 잡나: 자리표·프런트매터 오류(TableError·ContentError)만 받으면, 검사를 통과한 원고 한 편의 모양 탈(목록이어야 할
    값이 짝으로 읽힘 등)이 생성기 전체를 예외로 끝내고 배치가 '생성기 실패 — 커밋하지 않는다'로 그날 데이터를 올리지 못한다
    (2026-11-13 전수 리뷰). 생성기 버그도 이 줄로 드러난다 — 예외 이름을 그대로 적는다. --strict 는 예전처럼 멈춘다.
    """
    return '%s/%s.md %s: 굽다가 예외(%s: %s) — 원고 꼴이나 생성기를 고칠 것' % (
        sec, meta.get('slug'), where, type(err).__name__, err)


def main(strict=False):
    old_format = []
    posts, skipped = collect(strict=strict, old_format=old_format)
    for why in skipped:
        _warn('콘텐츠 원고를 건너뛴다 — ' + why)
    for what in old_format:
        _warn('옛 양식 원고 — %s: 2026-11-05 양식 다섯 항목(tldr·audience·key·city·topic)이 없어 카드에 지역·핵심 숫자가 빠진다'
              '(content/README.md)' % what)
    if not posts:
        # 원고가 없으면 페이지는 만들지 않는다. 다만 홈 묶음은 비운다 — 글을 전부 내린 회차에 홈만 옛 목록을
        # 들고 있으면 없는 글로 가는 링크가 남는다.
        emptied = write_home_recent([])
        print('content pages: 원고 없음 — 페이지를 만들지 않는다%s' % (' · 홈 묶음 비움' if emptied else ''))
        return 0
    data = CT.load()
    # 프런트매터의 글(제목·요약·FAQ)도 자리표를 쓴다. 본문보다 먼저, 여기서 한 번만 채운다 — 페이지와
    # OG·JSON-LD·섹션 목록·홈 묶음·feed·llms 가 모두 이 결과를 돌려쓴다(CT.fill_meta 의 주석 참조).
    filled, dropped = [], []
    for sec, meta, body in posts:
        try:
            for name in meta.get('city') or []:
                CT.city_codes(data, name)                  # 이름표에 없는 도시는 건너뛴다(허브 칩·시세 링크가 그 이름으로 만들어진다)
            filled.append((sec, CT.check_lengths(CT.fill_meta(meta, data)), body))
        except CT.TableError as e:
            if strict:
                raise
            dropped.append('%s/%s.md 프런트매터: %s' % (sec, meta['slug'], e))
        except Exception as e:      # noqa: BLE001 — 한 편의 탈이 나머지 글과 그날 데이터 커밋을 막지 않게 가둔다(_crash_note)
            if strict:
                raise
            dropped.append(_crash_note(sec, meta, e, '프런트매터'))
    for why in dropped:
        _warn('콘텐츠 원고를 건너뛴다 — ' + why)
    posts = filled
    if not posts:
        emptied = write_home_recent([])
        print('content pages: 쓸 수 있는 원고가 없다 — 페이지를 만들지 않는다%s'
              % (' · 홈 묶음 비움' if emptied else ''))
        return 0
    # 본문 자리표를 못 채우는 글을 **먼저** 거른다 — 이전·다음 글과 '이 지역 더 보기'는 구워지는 글만 가리켜야 한다.
    # 예전엔 거르기 전 목록에서 이웃을 골라, 건너뛴 단지 글(광명 철산13, 11-06~)로 가는 '이전·다음 글'이 404 였다
    # (2026-11-12 SEO 점검). 한 바퀴 더 구워도 52편에 2초 남짓이다.
    ok = []
    for sec, meta, body in posts:
        try:
            build_page(meta, body, data)
        except (CT.TableError, CM.ContentError) as e:
            # 자리표를 못 채운 글도 건너뛴다(collect 와 같은 이유). 반쯤 채운 페이지는 내보내지 않는다.
            if strict:
                raise
            skipped.append('%s/%s.md: %s' % (sec, meta['slug'], e))
            _warn('콘텐츠 자리표를 채우지 못해 건너뛴다 — %s/%s.md: %s' % (sec, meta['slug'], e))
            continue
        except Exception as e:      # noqa: BLE001 — 위와 같다
            if strict:
                raise
            why = _crash_note(sec, meta, e, '본문')
            skipped.append(why)
            _warn('콘텐츠 원고를 건너뛴다 — ' + why)
            continue
        ok.append((sec, meta, body))
    posts = ok
    by_sec = {}
    for sec, meta, body in posts:
        by_sec.setdefault(sec, []).append((meta, body))
    everyone = [m for _s, m, _b in posts]       # 글 끝 '이 지역 더 보기'가 같은 도시의 입주물량 글을 찾는 범위
    entries, wrote = [], 0
    for sec, items in by_sec.items():
        items.sort(key=lambda x: (x[0]['date'], x[0]['slug']))
        metas = [m for m, _ in items]
        for i, (meta, body) in enumerate(items):
            prev = metas[i - 1] if i else None
            nxt = metas[i + 1] if i + 1 < len(metas) else None
            page, lm = build_page(meta, body, data, prev, nxt, everyone)
            d = os.path.join(ROOT, sec, meta['slug'])
            os.makedirs(d, exist_ok=True)
            fp = os.path.join(d, 'index.html')
            page, lm, changed = SP.keep_dates(page, SP.read_old(fp), lm)
            io.open(fp, 'w', encoding='utf-8', newline='\n').write(page)
            wrote += 1
            entries.append(('/%s/%s/' % (sec, meta['slug']), lm))
        # 목록에는 **실제로 구워진 글만** 싣는다 — 건너뛴 글로 가는 링크를 만들지 않는다.
        done = [m for m in metas if os.path.exists(os.path.join(ROOT, sec, m['slug'], 'index.html'))]
        if not done:
            continue
        page, lm = build_index(sec, _newest(done))
        fp = os.path.join(ROOT, sec, 'index.html')
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        page, lm, _ = SP.keep_dates(page, SP.read_old(fp), lm or I.PUBLISHED)
        io.open(fp, 'w', encoding='utf-8', newline='\n').write(page)
        entries.append(('/%s/' % sec, lm))
    I.update_sitemap(entries)
    all_metas = [m for items in by_sec.values() for m, _ in items
                 if os.path.exists(os.path.join(ROOT, m['section'], m['slug'], 'index.html'))]
    # 네 섹션을 한자리에 모은 /reports/ — 상단·하단 탭 '콘텐츠'가 여기로 온다.
    rp, rlm = build_reports(all_metas, data)
    rpath = os.path.join(ROOT, REPORTS_DIR, 'index.html')
    rp, rlm, _ = SP.keep_dates(rp, SP.read_old(rpath), rlm or I.PUBLISHED)
    if not os.path.isdir(os.path.dirname(rpath)):
        os.makedirs(os.path.dirname(rpath))
    io.open(rpath, 'w', encoding='utf-8', newline='\n').write(rp)
    entries.append(('/%s/' % REPORTS_DIR, rlm))
    I.update_sitemap(entries)
    home = write_home_recent(all_metas)
    zones = write_zone_posts(all_metas)
    wk = write_weekly_column(all_metas)
    mv = write_moveins_cities(all_metas)
    print('content pages: %d편%s · 섹션 %s%s%s%s%s' % (
        wrote, (' · 건너뜀 %d편' % (len(skipped) + len(dropped))) if (skipped or dropped) else '',
        ', '.join(sorted(by_sec)), ' · 홈 최근 리포트 갱신' if home else '',
        ' · 지역 리포트 %d곳에 글 묶음' % zones if zones else '',
        ' · 주간 리포트 해설 칸 갱신' if wk else '',
        ' · 입주물량 도시 칸 갱신' if mv else ''))
    return 0


if __name__ == '__main__':
    # --strict: 첫 오류에서 멈춘다(원고를 고칠 때). 배치는 기본값으로 돌려 한 편의 오타가 그날 갱신을 막지 않게 한다.
    sys.exit(main(strict='--strict' in sys.argv))
