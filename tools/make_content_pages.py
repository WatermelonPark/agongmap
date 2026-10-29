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

SITE = I.SITE
AUTHOR = '아공맵 운영팀'
DISCLAIMER = '공공 데이터를 가공한 참고 자료이며 투자자문이 아닙니다. 투자 판단과 책임은 이용자에게 있습니다.'
OG_IMAGE = '/og-brand.png'   # 어느 카드도 없을 때 떨어지는 자리


def card_rel(section, slug):
    """글별 공유 카드의 저장소 상대 경로. 카드를 굽는 쪽(make_content_cards)도 이 함수를 쓴다 —
    경로 규칙이 두 벌이면 한쪽만 고쳐져 og:image 가 없는 파일을 가리킨다."""
    return 'share/post-%s-%s.png' % (section, slug)


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

SECTION_META = {
    'city': ('도시 입주물량', '도시별 입주물량과 공급 흐름을 국가 통계로 읽습니다.'),
    'gtx': ('GTX 역세권', 'GTX 노선과 역세권 아파트 공급을 국가 통계로 읽습니다.'),
    'danji': ('단지 분석', '재건축·리모델링 단지를 공급 데이터와 함께 봅니다.'),
    'column': ('해설', '부동산 뉴스와 통념을 공개 데이터로 따져봅니다.'),
}
assert set(SECTION_META) == set(CM.SECTIONS), '섹션 목록이 content_md 와 다르다'


# ── 마크다운 (우리가 쓰는 부분집합) ─────────────────────────────────────────
def _inline(t):
    """인라인 서식. 먼저 이스케이프하고, 그 위에 굵게·코드·링크만 되살린다."""
    t = html.escape(t, quote=False)
    t = re.sub(r'`([^`]+)`', r'<code>\1</code>', t)
    t = re.sub(r'\*\*([^*]+)\*\*', r'<b>\1</b>', t)
    t = re.sub(r'!\[([^\]]*)\]\(([^)\s]+)\)', r'<img src="\2" alt="\1" loading="lazy">', t)
    t = re.sub(r'\[([^\]]+)\]\(([^)\s]+)\)', r'<a href="\2">\1</a>', t)
    return t


# ── 그림(인라인 SVG) ────────────────────────────────────────────────────────
# 이미지 파일이 아니라 인라인 SVG 다(요청 ①, 총괄 10-27). 그래야 배치가 페이지를 다시 구울 때 숫자가 따라
# 오고, 다크 모드도 CSS 변수로 따라온다. 색만으로 계열을 가르지 않는다 — 매매는 실선, 전세는 점선이다.
CH_W, CH_BAR_H, CH_LINE_H = 640, 210, 150       # viewBox 크기(폭은 CSS 로 100% 가 된다)


def _svg_open(spec, h):
    # preserveAspectRatio 를 건드리지 않는다 — 'none' 으로 늘리면 좁은 화면에서 글자와 선 굵기가 함께
    # 늘어나 뭉갠다. 폭은 CSS(width:100%)가 맞추고 높이는 비율대로 따라온다.
    return ('<svg viewBox="0 0 %d %d" role="img" aria-label="%s" class="cchart-svg">'
            % (CH_W, h, html.escape(spec['alt'])))


def _bars_svg(spec):
    pts = spec['series'][0]['points']
    rule = spec.get('rule')
    top = max([v for _, v in pts] + ([rule[0]] if rule and rule[0] else [0])) or 1
    pad_l, pad_b, pad_t = 8, 26, 16
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
    keep = {max(range(len(pts)), key=lambda i: pts[i][1]), len(pts) - 1}
    out = [_svg_open(spec, CH_BAR_H)]
    for i, (lab, v) in enumerate(pts):
        x = pad_l + i * (bw + gap)
        hh = max(1.0, v / float(top) * plot_h)
        y = pad_t + plot_h - hh
        over = rule and rule[0] and v >= rule[0]
        out.append('<rect x="%.1f" y="%.1f" width="%.1f" height="%.1f" class="cb%s"/>'
                   % (x, y, bw, hh, ' cb-over' if over else ''))
        if not tight or i in keep:
            out.append('<text x="%.1f" y="%.1f" class="cb-v">%s</text>'
                       % (x + bw / 2, y - 4, html.escape(CT.num(v))))
        out.append('<text x="%.1f" y="%d" class="cb-x">%s</text>'
                   % (x + bw / 2, CH_BAR_H - 8, html.escape(str(lab))))
    if rule and rule[0]:
        ry = pad_t + plot_h - rule[0] / float(top) * plot_h
        out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="cb-rule"/>'
                   % (6, ry, CH_W - 6, ry))
        out.append('<text x="%d" y="%.1f" class="cb-rl cx-e">%s</text>'
                   % (CH_W - 8, max(10, ry - 5), html.escape(rule[1])))
    out.append('</svg>')
    return ''.join(out)


def _lines_svg(spec):
    ser = spec['series']
    vals = [v for s in ser for _, v in s['points']]
    hi, lo = max(vals + [0.0]), min(vals + [0.0])
    span = (hi - lo) or 1.0
    pad_l, pad_t, pad_b = 8, 14, 24
    plot_h = CH_LINE_H - pad_t - pad_b
    n = max(len(s['points']) for s in ser)

    def xy(i, v, cnt):
        x = pad_l + (CH_W - pad_l * 2) * (i / float(max(1, cnt - 1)))
        return x, pad_t + plot_h - (v - lo) / span * plot_h
    out = [_svg_open(spec, CH_LINE_H)]
    zx, zy = xy(0, 0.0, n)
    out.append('<line x1="%d" y1="%.1f" x2="%d" y2="%.1f" class="cl-zero"/>'
               % (pad_l, zy, CH_W - pad_l, zy))      # 0선 척추
    for s in ser:
        d = ' '.join('%s%.1f %.1f' % ('M' if i == 0 else 'L', *xy(i, v, len(s['points'])))
                     for i, (_, v) in enumerate(s['points']))
        out.append('<path d="%s" class="cl cl-%s"/>' % (d, 'je' if s['name'] == '전세' else 'ma'))
        lx, ly = xy(len(s['points']) - 1, s['points'][-1][1], len(s['points']))
        out.append('<circle cx="%.1f" cy="%.1f" r="2.5" class="cl-dot"/>' % (lx, ly))
    # 양 끝 날짜는 '월-일' 로만 적는다(연도는 각주에 있다). 가장자리에 붙이면 잘려 보여 안쪽으로 넣는다.
    ends = (ser[0]['points'][0][0], ser[0]['points'][-1][0])
    # 맞춤은 클래스로 준다 — CSS 의 text-anchor 가 SVG 속성을 이겨서, 속성으로 적으면 가운데로 그려지고
    # 양 끝 글자가 그림 밖으로 밀려 잘린다(2026-10-27 브라우저에서 getBBox 로 확인했다).
    out.append('<text x="%d" y="%d" class="cb-x cx-s">%s</text>'
               % (pad_l + 2, CH_LINE_H - 7, html.escape(ends[0][5:])))
    out.append('<text x="%d" y="%d" class="cb-x cx-e">%s</text>'
               % (CH_W - pad_l - 2, CH_LINE_H - 7, html.escape(ends[1][5:])))
    out.append('</svg>')
    return ''.join(out)


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
    out.append('</figure>')
    return ''.join(out)


def _own_tab(page):
    """뼈대(make_indicator_pages.SHELL)는 '시세' 탭을 켜 둔다 — 콘텐츠 페이지는 제 탭('콘텐츠')을 켠다.

    탭바 마크업은 site_nav 가 정본이라 그 함수가 만든 두 덩어리를 맞바꾼다(문자열을 손으로 적지 않는다).
    """
    import site_nav as N
    return page.replace(N.bottomnav('stats'), N.bottomnav('reports'), 1)


def _table_html(head, body, note=''):
    h = ['<div class="ctab"><table><thead><tr>']
    h += ['<th scope="col">%s</th>' % html.escape(c) for c in head]
    h.append('</tr></thead><tbody>')
    for row in body:
        cells = ['<th scope="row">%s</th>' % html.escape(str(row[0]))]
        cells += ['<td>%s</td>' % html.escape(str(c)) for c in row[1:]]
        h.append('<tr>%s</tr>' % ''.join(cells))
    h.append('</tbody></table>')
    if note:
        h.append('<p class="cnote">%s</p>' % html.escape(note))
    h.append('</div>')
    return ''.join(h)


def markdown(body):
    """문단·제목·목록·인용·표만 있는 작은 마크다운. 모르는 줄은 문단으로 둔다."""
    lines = body.replace('\r\n', '\n').split('\n')
    out, i = [], 0
    while i < len(lines):
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
            h = ['<div class="ctab"><table><thead><tr>']
            h += ['<th scope="col">%s</th>' % _inline(c) for c in head]
            h.append('</tr></thead><tbody>')
            for r in rows:
                cells = ['<th scope="row">%s</th>' % _inline(r[0])] + ['<td>%s</td>' % _inline(c) for c in r[1:]]
                h.append('<tr>%s</tr>' % ''.join(cells))
            h.append('</tbody></table></div>')
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
        para = []
        while i < len(lines) and lines[i].strip() and not re.match(r'^(#{2,4}\s|[-*]\s|\d+\.\s|\||>)', lines[i].strip()):
            para.append(lines[i].strip())
            i += 1
        if para:
            out.append('<p>%s</p>' % _inline(' '.join(para)))
    return '\n'.join(out)


PLACEHOLDER = CT.PH      # 정규식은 content_tables 가 정본이다 — 종류가 늘면 한 곳만 고친다


def fill_placeholders(body, data):
    """자리표를 먼저 채운다. 표는 토큰으로 빼 두었다가 마크다운 변환 뒤 되돌린다."""
    blocks = []

    def sub(m):
        kind, rest = m.group(1), m.group(2)
        parts = [p.strip() for p in rest.split(':')]
        if not parts or not parts[0]:
            raise CT.TableError('자리표가 비었다: %s' % m.group(0))
        if kind == 'v':
            return CT.value(data, parts[0], parts[1:])
        if kind == 'chart':
            blocks.append(_chart_html(CT.chart(data, parts[0], parts[1:])))
        else:
            blocks.append(_table_html(*CT.table(data, parts[0], parts[1:])))
        return '\n\n\x00TABLE%d\x00\n\n' % (len(blocks) - 1)

    return PLACEHOLDER.sub(sub, body), blocks


def restore_tables(html_text, blocks):
    for i, b in enumerate(blocks):
        html_text = html_text.replace('<p>\x00TABLE%d\x00</p>' % i, b).replace('\x00TABLE%d\x00' % i, b)
    return html_text


# ── 페이지 ──────────────────────────────────────────────────────────────────
EXTRA_CSS = """
.rchips{display:flex;gap:6px;flex-wrap:wrap;margin:0 0 16px}
.rchip{font:inherit;font-size:13px;line-height:1;padding:8px 12px;border:1px solid var(--line);
 border-radius:3px;background:var(--paper);color:var(--ink2);cursor:pointer}
.rchip.on{background:var(--ink);border-color:var(--ink);color:var(--paper)}
.rchip:focus-visible{outline:2px solid var(--ink);outline-offset:2px}
.clist a[hidden]{display:none}
.cchart{margin:0 0 20px;padding:0}
.cchart-svg{display:block;width:100%;height:auto;margin:2px 0 0}
.ccards{display:flex;gap:8px;margin:0 0 10px;flex-wrap:wrap}
.ccard{flex:1 1 30%;min-width:96px;background:var(--paper2);border:1px solid var(--line);
 border-radius:3px;padding:8px 10px}
.ccard b{display:block;font-size:18px;font-weight:600;line-height:1.25;letter-spacing:-.01em}
.ccard span{display:block;font-size:13px;color:var(--muted);margin-top:2px}
.cchart figcaption,.clegend{font-size:13px;color:var(--muted);margin:6px 0 0;line-height:1.55}
.clegend{display:flex;gap:14px}
.clegend span{display:inline-flex;align-items:center;gap:5px}
.clegend span::before{content:"";width:16px;height:0;border-top:2px solid var(--ink)}
.clegend .lg-je::before{border-top-style:dashed;opacity:.75}
.cb{fill:var(--ink);opacity:.45}
.cb-over{opacity:.78}
.cb-v{fill:var(--ink);font-size:11px;text-anchor:middle}
.cb-x{fill:var(--muted);font-size:11px;text-anchor:middle}
.cx-s{text-anchor:start}
.cx-e{text-anchor:end}
.cb-rule{stroke:var(--ink);stroke-width:1;stroke-dasharray:4 3;opacity:.65}
.cb-rl{fill:var(--muted);font-size:11px}
.cl{fill:none;stroke:var(--ink);stroke-width:1.6;stroke-linejoin:round}
.cl-je{stroke-dasharray:4 3;opacity:.75}
.cl-zero{stroke:var(--line);stroke-width:1}
.cl-dot{fill:var(--ink)}
.cmeta{font-size:13px;color:var(--muted);margin:0 0 14px}
.csum{font-size:16px;line-height:1.75;color:var(--ink);background:var(--paper2);
 border-left:3px solid var(--ink);padding:14px 16px;margin:0 0 20px}
.cbody h2{font-size:20px;margin:28px 0 10px}
.cbody h3{font-size:16.5px;margin:22px 0 8px}
.cbody p{font-size:15px;line-height:1.8;margin:0 0 14px}
.cbody li{font-size:15px;line-height:1.8}
.cbody blockquote{margin:0 0 14px;padding:10px 14px;background:var(--paper2);border-radius:3px}
.ctab{overflow-x:auto;margin:0 0 16px}
.ctab table{width:100%;border-collapse:collapse;font-size:14px}
.ctab th,.ctab td{padding:7px 9px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
.ctab th[scope=row]{text-align:left;font-weight:500}
.ctab thead th{border-bottom:1.5px solid var(--ink);font-size:12.5px;color:var(--muted)}
.cnote{font-size:12px;color:var(--muted);margin:6px 0 0}
.csrc{font-size:13px;color:var(--ink2);line-height:1.7}
.csrc li{margin-bottom:3px}
.cfaq{margin-top:26px}
.cfaq dt{font-weight:600;font-size:15px;margin-top:14px}
.cfaq dd{margin:6px 0 0;font-size:14.5px;line-height:1.75;color:var(--ink2)}
.cnav{display:flex;gap:10px;flex-wrap:wrap;margin-top:26px}
.cnav a{flex:1;min-width:200px;border:1px solid var(--line);border-radius:3px;padding:11px 13px;
 text-decoration:none;color:var(--ink);font-size:14px}
.cnav a span{display:block;font-size:12px;color:var(--muted);margin-bottom:2px}
.clist{display:flex;flex-direction:column;gap:10px;margin-top:18px}
.clist a{border:1px solid var(--line);border-radius:3px;padding:13px 15px;text-decoration:none;color:var(--ink)}
.clist b{display:block;font-size:15.5px;font-weight:600;margin-bottom:4px}
.clist span{display:block;font-size:13.5px;color:var(--ink2);line-height:1.6}
.clist i{display:block;font-style:normal;font-size:12px;color:var(--muted);margin-top:5px}
.cdisc{font-size:12px;color:var(--muted);margin-top:22px;line-height:1.6}
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


def build_page(meta, body_md, data, prev=None, nxt=None):
    filled, blocks = fill_placeholders(body_md, data)
    body_html = restore_tables(markdown(filled), blocks)
    sec = meta['section']
    url = '%s/%s/%s/' % (SITE, sec, meta['slug'])
    srcs = meta.get('sources') or []
    nav = []
    if prev:
        nav.append('<a href="/%s/%s/"><span>이전 글</span>%s</a>' % (sec, prev['slug'], html.escape(prev['title'])))
    if nxt:
        nav.append('<a href="/%s/%s/"><span>다음 글</span>%s</a>' % (sec, nxt['slug'], html.escape(nxt['title'])))
    if meta.get('region'):
        z = _zone_link(meta['region'])
        if z:
            nav.append(z)
    faq_html = ''
    if meta.get('faq'):
        items = ''.join('<dt>%s</dt><dd>%s</dd>' % (html.escape(f['q']), html.escape(f['a']))
                        for f in meta['faq'])
        faq_html = '<section class="cfaq"><h2>자주 묻는 질문</h2><dl>%s</dl></section>' % items
    src_html = ''
    if srcs:
        src_html = ('<section><h2>숫자의 출처</h2><ul class="csrc">%s</ul></section>'
                    % ''.join('<li>%s</li>' % html.escape(s) for s in srcs))
    body = (
        '<header><div class="wrap">'
        '<nav class="crumb"><a href="/">아공맵</a> › <a href="/%s/">%s</a></nav>'
        '<h1>%s</h1>'
        '<p class="cmeta">%s 작성 · %s 갱신 · <a href="/about/">%s</a></p>'
        '</div></header>'
        '<section><div class="wrap">'
        '<p class="csum">%s</p>'
        '<div class="cbody">%s</div>'
        '%s%s'
        '<div class="cnav">%s</div>'
        '<p class="cdisc">%s</p>'
        '</div></section>'
        % (sec, html.escape(SECTION_META[sec][0]), html.escape(meta['title']),
           meta['date'], meta['updated'], AUTHOR,
           html.escape(meta['summary']), body_html, src_html, faq_html,
           ''.join(nav), DISCLAIMER))
    page = I.fill(I.SHELL, title='%s | 아공맵' % meta['title'],
                  ogtitle=meta['title'], desc=meta['summary'], url=url, body=body,
                  ld=_ld(meta, url, body_html), src=' · '.join(srcs) if srcs else '아공맵',
                  nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    page = re.sub(r'<meta property="og:image" content="[^"]*">',
                  '<meta property="og:image" content="%s">' % html.escape(og_image(meta)), page, count=1)
    return page, meta['updated']


def build_index(sec, posts_meta):
    """섹션 목록 페이지. 최신순(updated 내림차순, 같으면 date·slug)."""
    name, desc = SECTION_META[sec]
    url = '%s/%s/' % (SITE, sec)
    items = ''.join(
        '<a href="/%s/%s/"><b>%s</b><span>%s</span><i>%s 갱신</i></a>'
        % (sec, m['slug'], html.escape(m['title']), html.escape(m['summary']), m['updated'])
        for m in posts_meta)
    if not items:
        items = '<p>아직 글이 없습니다.</p>'
    body = ('<header><div class="wrap">'
            '<nav class="crumb"><a href="/">아공맵</a> › <b>%s</b></nav>'
            '<h1>%s</h1><p class="cmeta">%s</p></div></header>'
            '<section><div class="wrap"><div class="clist">%s</div></div></section>'
            % (html.escape(name), html.escape(name), html.escape(desc), items))
    lastmod = max([m['updated'] for m in posts_meta], default=None)
    page = I.fill(I.SHELL, title='%s | 아공맵' % name, ogtitle=name, desc=desc, url=url, body=body,
                  ld=I.ld_pack(name, desc, url, name, lastmod or I.PUBLISHED),
                  src='아공맵', nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    return page, lastmod


REPORTS_DIR = 'reports'
REPORTS_TITLE = '콘텐츠'
REPORTS_DESC = '도시 입주물량·GTX 역세권·단지 분석·해설을 한자리에서 봅니다. 숫자는 국가 통계에서 옵니다.'


def build_reports(all_metas):
    """네 섹션 글을 최신순 한 목록으로. 위에 섹션 거르개를 둔다(탭 '콘텐츠'가 여기로 온다).

    거르개는 자바스크립트 없이도 **전부 보이는** 상태가 기본이다(점진적 향상). 스크립트가 돌면 누른 섹션만
    남긴다 — 목록이 서버에서 이미 완성돼 있으므로 검색·AI 수집기는 거르개와 무관하게 전부 읽는다.
    """
    newest = sorted(all_metas, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    secs = [s for s in CM.SECTIONS if any(m['section'] == s for m in newest)]
    chips = ['<button type="button" class="rchip on" data-sec="">전체</button>']
    chips += ['<button type="button" class="rchip" data-sec="%s">%s</button>' % (s, html.escape(SECTION_META[s][0]))
              for s in secs]
    items = ''.join(
        '<a href="/%s/%s/" data-sec="%s"><b>%s</b><span>%s</span><i>%s · %s 갱신</i></a>'
        % (m['section'], m['slug'], m['section'], html.escape(m['title']), html.escape(m['summary']),
           html.escape(SECTION_META[m['section']][0]), m['updated'])
        for m in newest)
    if not items:
        items = '<p>아직 글이 없습니다.</p>'
    body = ('<header><div class="wrap">'
            '<nav class="crumb"><a href="/">아공맵</a> › <b>%s</b></nav>'
            '<h1>%s</h1><p class="cmeta">%s</p></div></header>'
            '<section><div class="wrap">'
            '<div class="rchips" role="group" aria-label="섹션 거르개">%s</div>'
            '<div class="clist" id="rlist">%s</div>'
            '</div></section>'
            '<script>(function(){var w=document.querySelector(".rchips");if(!w)return;'
            'w.addEventListener("click",function(e){var b=e.target.closest(".rchip");if(!b)return;'
            '[].forEach.call(w.querySelectorAll(".rchip"),function(x){x.classList.toggle("on",x===b);});'
            'var s=b.getAttribute("data-sec");'
            '[].forEach.call(document.querySelectorAll("#rlist a"),function(a){'
            'a.hidden=!!s&&a.getAttribute("data-sec")!==s;});});})();</script>'
            % (html.escape(REPORTS_TITLE), html.escape(REPORTS_TITLE), html.escape(REPORTS_DESC),
               ''.join(chips), items))
    url = '%s/%s/' % (SITE, REPORTS_DIR)
    lastmod = max([m['updated'] for m in newest], default=None)
    page = I.fill(I.SHELL, title='%s | 아공맵' % REPORTS_TITLE, ogtitle=REPORTS_TITLE, desc=REPORTS_DESC,
                  url=url, body=body, ld=I.ld_pack(REPORTS_TITLE, REPORTS_DESC, url, REPORTS_TITLE,
                                                   lastmod or I.PUBLISHED),
                  src='아공맵', nsido=str(len(I.SIDO17)))
    page = _own_tab(page.replace('</style>', EXTRA_CSS + '</style>', 1))
    return page, lastmod


HOME_START, HOME_END = '<!--CONTENT_RECENT_START-->', '<!--CONTENT_RECENT_END-->'
HOME_RECENT = 6
_HOME_RE = re.compile(re.escape(HOME_START) + r'(.*?)' + re.escape(HOME_END), re.S)


def home_recent_html(metas):
    """홈 '최근 리포트' 묶음. 섹션을 가리지 않고 갱신일 최신 HOME_RECENT 편."""
    if not metas:
        return ''
    newest = sorted(metas, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)[:HOME_RECENT]
    items = ''.join(
        '<li><a href="/%s/%s/"><b>%s</b><i>%s · %s 갱신</i></a></li>'
        % (m['section'], m['slug'], html.escape(m['title']),
           html.escape(SECTION_META[m['section']][0]), m['updated'])
        for m in newest)
    # '전체 보기'는 탭 '콘텐츠'와 같은 자리로 보낸다 — 홈에서 여섯 편만 보고 더 읽고 싶은 사람의 길이다.
    return ('<div class="crecent"><h2>최근 리포트</h2><ul>%s</ul>'
            '<p class="crecent-all"><a href="/%s/">콘텐츠 전체 보기 →</a></p></div>' % (items, REPORTS_DIR))


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


ZONE_START, ZONE_END = '<!--ZONE_POSTS_START-->', '<!--ZONE_POSTS_END-->'
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


def zone_posts_html(metas):
    """시도 리포트 아래에 붙는 '이 지역 글' 묶음. 갱신일 최신 순."""
    if not metas:
        return ''
    newest = sorted(metas, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
    items = ''.join(
        '<li><a href="/%s/%s/"><b>%s</b><i>%s · %s 갱신</i></a></li>'
        % (m['section'], m['slug'], html.escape(m['title']),
           html.escape(SECTION_META[m['section']][0]), m['updated'])
        for m in newest)
    return '<section class="crecent zposts"><h2>이 지역 글</h2><ul>%s</ul></section>' % items


def write_zone_posts(metas, root=ROOT):
    """시도 리포트(zone/<시도>/index.html)의 표식 구간만 고쳐 쓴다 — 홈 묶음과 같은 규칙이다.

    ⚠️ 구간 밖은 건드리지 않는다. 글이 없는 시도는 구간을 비운다(지난 회차의 글이 남지 않게).
       표식이 없는 페이지는 건너뛴다 — make_sido_pages 가 아직 그 판을 굽지 않은 회차다.
    """
    import sido_zones as SZ
    by = {}
    for m in metas:
        z = zone_of(m)
        if z:
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


def collect(root=ROOT, strict=False):
    """[(섹션, meta, 본문)], [건너뛴 사유] — 원고를 읽고 검사한다.

    ⚠️ 규약을 어긴 원고 하나 때문에 배치를 세우지 않는다. 그 글만 건너뛰고 경고를 남긴 뒤 나머지를 굽는다 —
       콘텐츠 원고는 여러 세션이 수시로 올리는데, 한 편의 오타가 그날의 데이터 갱신까지 막으면 손해가 크다
       (2026-10-27: 첫 19편이 들어오자마자 시군구 자리표에서 걸렸다). 건너뛴 글은 배치 보고에 뜬다.
       strict=True 는 사람이 손으로 돌려 원고를 고칠 때 쓴다 — 첫 오류에서 멈춘다.
    """
    out, skipped = [], []
    for sec, slug, path in CM.posts(root):
        try:
            meta, body = CM.read(path, sec, slug)
        except CM.ContentError as e:
            if strict:
                raise
            skipped.append(str(e))
            continue
        out.append((sec, meta, body))
    return out, skipped


def _warn(msg):
    """배치 로그에 경고를 남긴다(GitHub Actions 에서는 실행 화면 주석으로도 뜬다) — 다른 생성기와 같은 방식."""
    print(('::warning::' if os.environ.get('GITHUB_ACTIONS') else '  ⚠️ ') + msg)


def main(strict=False):
    posts, skipped = collect(strict=strict)
    for why in skipped:
        _warn('콘텐츠 원고를 건너뛴다 — ' + why)
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
            filled.append((sec, CT.fill_meta(meta, data), body))
        except CT.TableError as e:
            if strict:
                raise
            dropped.append('%s/%s.md 프런트매터: %s' % (sec, meta['slug'], e))
    for why in dropped:
        _warn('콘텐츠 원고를 건너뛴다 — ' + why)
    posts = filled
    if not posts:
        emptied = write_home_recent([])
        print('content pages: 쓸 수 있는 원고가 없다 — 페이지를 만들지 않는다%s'
              % (' · 홈 묶음 비움' if emptied else ''))
        return 0
    by_sec = {}
    for sec, meta, body in posts:
        by_sec.setdefault(sec, []).append((meta, body))
    entries, wrote = [], 0
    for sec, items in by_sec.items():
        items.sort(key=lambda x: (x[0]['date'], x[0]['slug']))
        metas = [m for m, _ in items]
        for i, (meta, body) in enumerate(items):
            prev = metas[i - 1] if i else None
            nxt = metas[i + 1] if i + 1 < len(metas) else None
            try:
                page, lm = build_page(meta, body, data, prev, nxt)
            except (CT.TableError, CM.ContentError) as e:
                # 자리표를 못 채운 글도 건너뛴다(collect 와 같은 이유). 반쯤 채운 페이지는 내보내지 않는다.
                if strict:
                    raise
                skipped.append('%s/%s.md: %s' % (sec, meta['slug'], e))
                _warn('콘텐츠 자리표를 채우지 못해 건너뛴다 — %s/%s.md: %s' % (sec, meta['slug'], e))
                continue
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
        newest = sorted(done, key=lambda m: (m['updated'], m['date'], m['slug']), reverse=True)
        page, lm = build_index(sec, newest)
        fp = os.path.join(ROOT, sec, 'index.html')
        os.makedirs(os.path.dirname(fp), exist_ok=True)
        page, lm, _ = SP.keep_dates(page, SP.read_old(fp), lm or I.PUBLISHED)
        io.open(fp, 'w', encoding='utf-8', newline='\n').write(page)
        entries.append(('/%s/' % sec, lm))
    I.update_sitemap(entries)
    all_metas = [m for items in by_sec.values() for m, _ in items
                 if os.path.exists(os.path.join(ROOT, m['section'], m['slug'], 'index.html'))]
    # 네 섹션을 한자리에 모은 /reports/ — 상단·하단 탭 '콘텐츠'가 여기로 온다.
    rp, rlm = build_reports(all_metas)
    rpath = os.path.join(ROOT, REPORTS_DIR, 'index.html')
    rp, rlm, _ = SP.keep_dates(rp, SP.read_old(rpath), rlm or I.PUBLISHED)
    if not os.path.isdir(os.path.dirname(rpath)):
        os.makedirs(os.path.dirname(rpath))
    io.open(rpath, 'w', encoding='utf-8', newline='\n').write(rp)
    entries.append(('/%s/' % REPORTS_DIR, rlm))
    I.update_sitemap(entries)
    home = write_home_recent(all_metas)
    zones = write_zone_posts(all_metas)
    print('content pages: %d편%s · 섹션 %s%s%s' % (
        wrote, (' · 건너뜀 %d편' % len(skipped)) if skipped else '',
        ', '.join(sorted(by_sec)), ' · 홈 최근 리포트 갱신' if home else '',
        ' · 지역 리포트 %d곳에 글 묶음' % zones if zones else ''))
    return 0


if __name__ == '__main__':
    # --strict: 첫 오류에서 멈춘다(원고를 고칠 때). 배치는 기본값으로 돌려 한 편의 오타가 그날 갱신을 막지 않게 한다.
    sys.exit(main(strict='--strict' in sys.argv))
