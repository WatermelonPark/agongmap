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
OG_IMAGE = '/og-brand.png'   # 글별 카드는 후속(요청서 덧붙임) — 그때까지 공용 카드

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


PLACEHOLDER = re.compile(r'\{\{(table|v):([^}]+)\}\}')


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
        head, rows, note = CT.table(data, parts[0], parts[1:])
        blocks.append(_table_html(head, rows, note))
        return '\n\n\x00TABLE%d\x00\n\n' % (len(blocks) - 1)

    return PLACEHOLDER.sub(sub, body), blocks


def restore_tables(html_text, blocks):
    for i, b in enumerate(blocks):
        html_text = html_text.replace('<p>\x00TABLE%d\x00</p>' % i, b).replace('\x00TABLE%d\x00' % i, b)
    return html_text


# ── 페이지 ──────────────────────────────────────────────────────────────────
EXTRA_CSS = """
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
    page = page.replace('</style>', EXTRA_CSS + '</style>', 1)
    page = page.replace('<meta property="og:image" content="%s' % SITE,
                        '<meta property="og:image" content="%s' % SITE)   # 공용 카드 유지(후속에서 글별 카드)
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
    page = page.replace('</style>', EXTRA_CSS + '</style>', 1)
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
    return '<div class="crecent"><h2>최근 리포트</h2><ul>%s</ul></div>' % items


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
    home = write_home_recent(all_metas)
    print('content pages: %d편%s · 섹션 %s%s' % (
        wrote, (' · 건너뜀 %d편' % len(skipped)) if skipped else '',
        ', '.join(sorted(by_sec)), ' · 홈 최근 리포트 갱신' if home else ''))
    return 0


if __name__ == '__main__':
    # --strict: 첫 오류에서 멈춘다(원고를 고칠 때). 배치는 기본값으로 돌려 한 편의 오타가 그날 갱신을 막지 않게 한다.
    sys.exit(main(strict='--strict' in sys.argv))
