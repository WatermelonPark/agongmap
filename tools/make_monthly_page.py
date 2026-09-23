# -*- coding: utf-8 -*-
"""'이달의 공급 통계' 한 화면(/monthly/) — 매달 공개 통계를 훑는 순서 그대로.

왜 이 화면이 있나:
  같은 통계를 매달 보는 사람들이 정부 사이트 4~5군데를 돌며 확인한다. 값이
  없어서가 아니라 **화면에서 못 찾아서** 손으로 합산하는 일이 생긴다(광주 단독
  등). 우리는 그 값을 이미 갖고 있으므로, 원자료에 있는 것을 꺼내 한 화면에
  순서대로 놓는다. 새 지표는 없다 — 재배치다.

⚠️ 섹션 순서는 제품 그 자체다(PM 요청서 2026-08-26). 재량으로 바꾸지 말 것:
  시도별 매·전·월 → 인허가 → 입주물량 → 미분양 → 전세가율

⚠️ 광주·전남은 '전남광주' **한 행**으로 싣는다(2026-09-10 모델 통합, e2ba8eb).
  국토교통부가 2026.07 공표분부터 두 지역을 합쳐서만 내고 그 표에 시군구 계층이
  없어, 원자료 어디에도 분리된 값이 남아 있지 않다. 과거 시계열은 두 지역 합으로
  병합해 이어 붙였다(tools/merge_regions.py).
  ⚠️ 이 문구가 표와 어긋나면 화면이 스스로 거짓말한다. 2026-09-11에 실제로 그랬다 —
  모델은 통합됐는데 각주만 '분리해서 싣는다'로 남아 있었다. 모델을 바꿀 때 각주도
  같이 본다.

실행: python tools/make_monthly_page.py   (split_data 뒤 아무 때나)
"""
import io
import json
import os
import re
import sys
import urllib.parse

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, HERE)

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

import make_indicator_pages as I           # noqa: E402  SHELL·fill·ld_pack 공유
import sido_zones as SZ                    # noqa: E402  지역 정의 정본
import make_weekly_page as MW              # noqa: E402  변동률 반올림 정본(pv2r)

SITE = I.SITE
OUT = os.path.join(ROOT, 'monthly')
URL = SITE + '/monthly/'

# ⚠️ 이 페이지의 최초 공개일. make_indicator_pages.PUBLISHED(2026-07-29)를
# 물려쓰면 안 된다 — 그건 /moveins/·/jeonse-ratio/의 날짜다. 그대로 쓰면 이 URL이
# 존재하지도 않던 5주 전에 발행됐다고 선언하고, sitemap lastmod도 그 날로 나간다
# (2026-09-02 리뷰). 검색엔진에 거짓 신호를 보내는 쪽이라 반드시 자기 날짜를 쓴다.
PUBLISHED = '2026-09-01'


# 표에 싣는 지역 순서 — 집계 3을 앞에 두고 16시도가 따라온다(sido_zones 정본).
ORDER = list(SZ.ORDER)
AGG = set(SZ.AGG)


def esc(s):
    return (str(s).replace('&', '&amp;').replace('<', '&lt;')
            .replace('>', '&gt;').replace('"', '&quot;'))


def pv2(v):
    """표시 자릿수로 **먼저** 반올림하고 부호를 정한다.

    원값 부호를 쓰면 -0.0012가 '-0.00'이 된다 — 값은 0인데 부호가 붙는다.
    사이트(index.html pv2)·공유 카드(make_weekly_share.pv2r)와 같은 규칙이다.
    """
    if v is None:
        return '·'
    r = MW.pv2r(v)   # 반올림 정본(사이트 half-up). round()는 가운데 값에서 갈렸다(2026-09-23 점검)
    return ('%+.2f' % r) if r != 0 else '0.00'


def cls(v):
    """색도 표시값 기준 — 표시가 0.00인데 원값 부호로 칠하면 글자와 색이 갈린다."""
    if v is None:
        return ''
    r = MW.pv2r(v)
    return ' class="up"' if r > 0 else (' class="dn"' if r < 0 else '')


def num(v):
    return '·' if v is None else format(int(round(v)), ',')


def month_label(p):
    """'2026.06' → '2026년 6월'."""
    m = re.match(r'^(\d{4})[.\-](\d{1,2})', str(p))
    return '%s년 %d월' % (m.group(1), int(m.group(2))) if m else str(p)


def sort_key(p):
    """기준 시점을 비교 가능한 'YYYY-MM'으로.

    ⚠️ 한글 라벨('2026년 9월')을 그대로 max()에 넣으면 안 된다 — 자릿수를
    안 맞춘 어휘 비교라 '2026년 9월' > '2026년 10월'이 된다. 10월부터 dateModified와
    sitemap lastmod가 9월에 얼어붙는데, 표는 계속 바뀌므로 아무도 못 알아챈다
    (2026-09-02 리뷰). 분기('2026Q3')는 그 분기의 마지막 달로 환산한다.
    """
    s = str(p)
    m = re.match(r'^(\d{4})[.\-](\d{1,2})', s)
    if m:
        return '%s-%02d' % (m.group(1), int(m.group(2)))
    m = re.match(r'^(\d{4})Q([1-4])$', s)
    if m:
        return '%s-%02d' % (m.group(1), int(m.group(2)) * 3)
    return s


def last_idx(d):
    """계열의 마지막 시점 인덱스와 라벨."""
    dates = d['dates']
    return len(dates) - 1, dates[-1]


def series_at(d, i):
    """지역 → 그 시점 값. 없는 지역은 None."""
    ser = d.get('series') or {}
    out = {}
    for r in ORDER:
        v = ser.get(r)
        out[r] = (v[i] if v and i < len(v) else None)
    return out


def cum_month(d, i):
    """누계 계열의 '이 달' 값 — sido_zones.permit_monthly 를 그대로 쓴다.

    ⚠️ 인허가 단위는 '호 (연내 누계)'다. 원값을 그대로 쓰면 1~7월 누계가 '이 달'로
       나간다(2026-09-13 발견: 경기 38,240 → 실제 2,855). 1월은 누계가 곧 그 달이고 나머지
       달은 전월 누계와의 차다. 전월 값이 없으면 비워 둔다 — 추정해 채우지 않는다.
    ⚠️ 산식을 여기 새로 쓰지 않는다. 예전 사본은 연초 null(KOSIS 의 진짜 0)을 '전월 없음'으로
       보고 그 달을 비웠다. permit_monthly 는 그해 앞선 누계가 없을 때의 null 을 0 으로 보므로,
       2024.02 대구 1,205호가 사이트의 다른 화면(착공 전환율·사이클)에는 들어가고 이 표에서만
       '·'로 나갈 수 있었다(2026-09-23 전체 점검, 실데이터 63칸). 일치는 test_monthly_permits 가 본다.
    ⚠️ 차분이 음수면 비워 둔다(이 표의 표시 규칙 — permit_monthly 는 합계용이라 음수를 남긴다).
       원천이 과거 달 누계를 소급 정정하면 최신 달 누계가 전월보다 작아지는데, 그 차이는 '이 달에
       인허가가 줄었다'가 아니라 정정분이라 이 달 값으로 읽을 수 없다. 실데이터에 전남광주 2025.08 −1,
       서울 2011.08 −491, 대전 2011.10 −1,177 이 실재한다(리뷰 13번).
    """
    key = str(d['dates'][i])[:7]
    wrap = {'인허가': d}
    out = {}
    for r in ORDER:
        v = SZ.permit_monthly(wrap, r).get(key)
        out[r] = v if v is None or v >= 0 else None
    return out


def trail12(stats, label):
    """최근 12개월 인허가 합 — sido_zones.permit_trail12 를 그대로 쓴다.

    ⚠️ 산식을 여기 새로 쓰지 않는다. 같은 대상을 시도 리포트('인허가 1년')와 이 페이지가
       다른 방식으로 재면 한 사이트에서 두 값이 나온다 — 실제로 그랬다(누계 12개를 단순
       합산해 전국이 3.8배로 나갔다). permit_trail12 는 지역마다 자기 최신 월로 계산하므로,
       표의 기준 월(label)과 다른 지역은 섞지 않고 비운다.
    """
    out = {}
    for r in ORDER:
        v, ym = SZ.permit_trail12(stats, r)
        out[r] = v if ym == label else None
    return out


def table(head, rows, note=''):
    """지역 행 표.

    ⚠️ 표두에 tabindex/role="button"/aria-sort를 **달지 않는다.** SHELL의 정렬
    스크립트는 `getElementById('utable')` 하나에만 붙는데 이 페이지엔 그 id가 없다.
    달아 두면 눌러도 아무 일이 없는 버튼 17개가 탭 순서에 끼고, 스크린리더에는
    '버튼'이라고 읽힌다. th에 role="button"을 얹는 것 자체가 SHELL 주석이 적어 둔
    2026-08-08 감사의 회귀이기도 하다(정렬이 필요해지면 그때 id와 함께 붙일 것).

    행 머리(지역명)는 여기서 <th scope="row">로 낸다 — 그것도 같은 스크립트가
    런타임에 승격시키던 일이라, 스크립트가 안 도는 이 페이지에서는 직접 해야
    20열 표에서 스크린리더가 '어느 지역'인지 말한다.
    """
    th = ''.join('<th scope="col">%s</th>' % esc(h) for h in head[1:])
    body = []
    for r in ORDER:
        tds = rows.get(r)
        if tds is None:
            continue
        body.append('<tr%s><th scope="row">%s</th>%s</tr>'
                    % (' class="agg"' if r in AGG else '', esc(r), tds))
    return ('<div class="tbl-wrap"><table><thead><tr>'
            '<th scope="col">%s</th>%s'
            '</tr></thead><tbody>%s</tbody></table></div>%s'
            % (esc(head[0]), th, ''.join(body),
               ('<p class="note">%s</p>' % note) if note else ''))


def ld_pack_here(headline, desc, url, modified):
    """구조화 데이터. I.ld_pack은 I.PUBLISHED를 박아 쓰므로 그대로 못 쓴다."""
    modified = max(modified, PUBLISHED)
    return json.dumps([{
        "@context": "https://schema.org", "@type": "Article",
        "headline": headline, "description": desc,
        "datePublished": PUBLISHED, "dateModified": modified,
        "author": {"@type": "Organization", "name": "아공맵"},
        "publisher": {"@type": "Organization", "name": "아공맵"},
        "mainEntityOfPage": url,
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "아공맵", "item": SITE + '/'},
            {"@type": "ListItem", "position": 2, "name": "이달의 공급 통계"},
        ],
    }], ensure_ascii=False, indent=2)


def sec(anchor, n, title, basis, source, body):
    """지표 한 덩어리. **기준월과 원천을 반드시 함께 적는다** — '지금 보는 게
    이번 달 발표분'이라는 확신이 이 화면의 존재 이유다(요청서 2번)."""
    body = body.replace('<table>', '<table aria-label="%s">' % esc(title), 1)   # 스크린리더용 표 이름(접근성 점검 2026-09-18)
    return ('<section id="%s"><div class="wrap">'
            '<div class="secno">%d</div><h2>%s</h2>'
            '<p class="basis"><b>%s</b> 기준 · %s</p>%s'
            '</div></section>' % (anchor, n, esc(title), esc(basis), esc(source), body))


def build(adv, sts):
    out, basis_list = [], []

    # ── 1. 시도별 매·전·월 (월간 변동률) ─────────────────────────────
    mo = adv.get('monthly') or {}
    mrows = mo.get('rows') or []
    mregs = mo.get('regions') or []
    if mrows:
        row = mrows[-1]
        mi = {r: i for i, r in enumerate(mregs)}
        cells = {}
        for r in ORDER:
            i = mi.get(r)
            if i is None:
                continue
            ma = (row.get('ma') or [None] * len(mregs))[i]
            je = (row.get('je') or [None] * len(mregs))[i]
            wo = (row.get('wo') or [None] * len(mregs))[i]
            cells[r] = ('<td%s>%s</td><td%s>%s</td><td%s>%s</td>'
                        % (cls(ma), pv2(ma), cls(je), pv2(je), cls(wo), pv2(wo)))
        raw = row['p']
        lab = month_label(raw)
        basis_list.append(raw)
        out.append(sec('price', 1, '시도별 매매·전세·월세', lab,
                       '한국부동산원 전국주택가격동향조사',
                       table(['지역', '매매', '전세', '월세'], cells,
                             '전월 대비 변동률(%).')))

    # ── 2. 인허가 ────────────────────────────────────────────────
    pm = sts.get('인허가')
    if pm:
        i, p = last_idx(pm)
        # 인허가는 '호 (연내 누계)' — 원값이 아니라 누계를 풀어 쓴다(2026-09-13).
        cur, yr = cum_month(pm, i), trail12(sts, p)
        cells = {r: '<td>%s</td><td>%s</td>' % (num(cur.get(r)), num(yr.get(r)))
                 for r in ORDER if cur.get(r) is not None or yr.get(r) is not None}
        raw = p
        lab = month_label(raw)
        basis_list.append(raw)
        out.append(sec('permits', 2, '인허가', lab, esc(pm.get('source') or '국토교통부'),
                       table(['지역', '이 달', '최근 12개월 합'], cells,
                             '허가받은 단계의 물량(호). ' + SZ.PERMIT_NATURE + '습니다. '
                             '월별 편차가 커서 12개월 합을 함께 봅니다.')))

    # ── 3. 입주물량 ──────────────────────────────────────────────
    # ⚠️ 열 이름에 '이번/다음 분기'를 쓰지 않는다. act[-1]은 **끝난** 분기
    # (2026Q2)이고 fut[0]이 지금 **진행 중인** 분기(2026Q3)라, 상대 표현을 쓰면
    # 한 칸씩 밀린다 — 게다가 진행 중인 분기 번호가 화면에 아예 안 나왔다
    # (2026-09-02 리뷰). 분기를 그대로 적으면 어긋날 여지가 없다.
    occ = adv.get('occupancy') or {}
    orows, oregs = occ.get('rows') or [], occ.get('regions') or []
    if orows:
        oi = {r: i for i, r in enumerate(oregs)}
        act = [r for r in orows if not r.get('e')]
        fut = [r for r in orows if r.get('e')]
        last = act[-1] if act else orows[-1]
        nxt = fut[0] if fut else None
        cells = {}
        for r in ORDER:
            i = oi.get(r)
            if i is None:
                continue
            a = (last.get('v') or [])[i] if i < len(last.get('v') or []) else None
            b = (nxt.get('v') or [])[i] if nxt and i < len(nxt.get('v') or []) else None
            cells[r] = '<td>%s</td><td>%s</td>' % (num(a), num(b))
        raw = last.get('p', '')
        lab = raw
        basis_list.append(raw)
        out.append(sec('moveins', 3, '입주물량', lab, '국토교통부 준공 실적',
                       table(['지역', '%s(실적)' % lab, '%s(예정)' % (nxt.get('p', '') if nxt else '-')],
                             cells,
                             '실제로 집이 들어온 물량(세대). 분기 단위라 다른 지표와 '
                             '기준 시점이 다릅니다 — 표에 분기를 그대로 적었습니다. '
                             '<a href="/moveins/">입주물량 자세히 보기</a>')))

    # ── 4. 미분양 ────────────────────────────────────────────────
    un = sts.get('미분양')
    if un:
        i, p = last_idx(un)
        cur = series_at(un, i)
        prev = series_at(un, i - 1) if i > 0 else {}
        cells = {}
        for r in ORDER:
            c = cur.get(r)
            if c is None:
                continue
            d = None if prev.get(r) is None else c - prev[r]
            arrow = '' if d is None else (
                '<td class="up">+%s</td>' % format(int(d), ',') if d > 0
                else ('<td class="dn">%s</td>' % format(int(d), ',') if d < 0
                      else '<td>0</td>'))
            cells[r] = '<td>%s</td>%s' % (num(c), arrow or '<td>·</td>')
        raw = p
        lab = month_label(raw)
        basis_list.append(raw)
        out.append(sec('unsold', 4, '미분양', lab, esc(un.get('source') or '국토교통부'),
                       table(['지역', '미분양(호)', '전월 대비'], cells,
                             '다 짓고도 팔리지 않아 남은 집. 이미 지어진 재고라 '
                             '공급 순위 계산에는 넣지 않고 참고로만 봅니다.')))

    # ── 5. 전세가율 ──────────────────────────────────────────────
    jr = sts.get('전세가율')
    if jr:
        i, p = last_idx(jr)
        cur = series_at(jr, i)
        prev = series_at(jr, i - 12) if i >= 12 else {}
        cells = {}
        for r in ORDER:
            c = cur.get(r)
            if c is None:
                continue
            d = None if prev.get(r) is None else c - prev[r]
            cells[r] = ('<td>%s</td><td%s>%s</td>'
                        % ('·' if c is None else '%.1f' % c, cls(d), pv2(d)))
        raw = p
        lab = month_label(raw)
        basis_list.append(raw)
        out.append(sec('jeonse', 5, '전세가율', lab, esc(jr.get('source') or '한국부동산원'),
                       table(['지역', '전세가율(%)', '1년 전 대비(%p)'], cells,
                             '매매가 대비 전세가 비율. <a href="/jeonse-ratio/">전세가율 자세히 보기</a>')))

    tops = top3_lines(adv, sts)
    out = [_with_top(x, tops) for x in out]
    return out, basis_list


def _rank(vals, n=3):
    """{지역: 변화량} → 절대값이 큰 순서로 n곳.

    집계(전국·수도권·지방)는 뺀다 — 시도와 같은 층위가 아니라 그 합이라, 섞으면 순위가
    자기 자신과 겨룬다. 동률이면 표 순서(ORDER)가 앞선 곳. 0 은 변화가 아니므로 싣지 않는다.
    """
    items = [(r, v) for r, v in vals.items() if v is not None and r not in AGG and r in ORDER]
    items.sort(key=lambda x: (-abs(x[1]), ORDER.index(x[0])))
    return [x for x in items if x[1] != 0][:n]


def _signed(v):
    r = int(round(v))
    return ('+' if r > 0 else '') + format(r, ',')


def top3_lines(adv, sts):
    """섹션마다 '이번 달 변화가 큰 3곳' — 표와 같은 값에서 뽑는다(2026-09-15 점검 후속 ④).

    ⚠️ 문장을 박지 않는다. 지역·수치는 매달 바뀌고, 박아 두면 표와 요약이 서로 다른 달을
       말한다. 표를 만드는 도우미(cum_month·series_at·last_idx)를 그대로 써서 같은 값을 본다.
    반환: {섹션 id: (머리말, [(지역, 표시값)])}
    """
    tops = {}
    mo = adv.get('monthly') or {}
    mrows, mregs = mo.get('rows') or [], mo.get('regions') or []
    if mrows:
        ma = mrows[-1].get('ma') or []
        vals = {r: ma[i] for i, r in enumerate(mregs) if i < len(ma)}
        tops['price'] = ('매매 변동이 큰 곳',
                         [(r, pv2(v) + '%') for r, v in _rank(vals) if pv2(v) != '0.00'])
    pm = sts.get('인허가')
    if pm:
        i, _ = last_idx(pm)
        vals = {r: v for r, v in cum_month(pm, i).items() if v is not None and v > 0}
        tops['permits'] = ('이 달 인허가가 많은 곳', [(r, num(v) + '호') for r, v in _rank(vals)])
    occ = adv.get('occupancy') or {}
    orows, oregs = occ.get('rows') or [], occ.get('regions') or []
    act = [r for r in orows if not r.get('e')]
    fut = [r for r in orows if r.get('e')]
    if orows and fut:
        last, nxt = (act[-1] if act else orows[-1]), fut[0]
        lv, nv = last.get('v') or [], nxt.get('v') or []
        vals = {r: nv[i] - lv[i] for i, r in enumerate(oregs)
                if i < len(lv) and i < len(nv) and lv[i] is not None and nv[i] is not None}
        tops['moveins'] = ('%s 실적 대비 %s 예정, 증감이 큰 곳' % (last.get('p', ''), nxt.get('p', '')),
                           [(r, _signed(v) + '세대') for r, v in _rank(vals)])
    un = sts.get('미분양')
    if un:
        i, _ = last_idx(un)
        if i > 0:
            cur, prev = series_at(un, i), series_at(un, i - 1)
            vals = {r: cur[r] - prev[r] for r in ORDER
                    if cur.get(r) is not None and prev.get(r) is not None}
            tops['unsold'] = ('전월 대비 미분양 증감이 큰 곳', [(r, _signed(v) + '호') for r, v in _rank(vals)])
    jr = sts.get('전세가율')
    if jr:
        i, _ = last_idx(jr)
        if i >= 12:
            cur, prev = series_at(jr, i), series_at(jr, i - 12)
            vals = {r: cur[r] - prev[r] for r in ORDER
                    if cur.get(r) is not None and prev.get(r) is not None}
            tops['jeonse'] = ('1년 새 전세가율 변화가 큰 곳',
                              [(r, pv2(v) + '%p') for r, v in _rank(vals) if pv2(v) != '0.00'])
    return tops


def _with_top(section_html, tops):
    """섹션의 기준월 줄 바로 아래(표 위)에 요약 한 줄을 넣는다. 지역 이름은 그 지역 리포트로 잇는다."""
    m = re.match(r'<section id="([a-z]+)"', section_html)
    t = tops.get(m.group(1)) if m else None
    if not t or not t[1]:
        return section_html
    line = ('<p class="top3"><b>%s</b> %s</p>'
            % (esc(t[0]), ' · '.join('<a href="/zone/%s/">%s</a> %s'
                                     % (urllib.parse.quote(r), esc(r), esc(v)) for r, v in t[1])))
    i = section_html.find('</p>') + len('</p>')
    return section_html[:i] + line + section_html[i:]


EXTRA_CSS = """
.secno{display:inline-block;font-size:11.5px;font-weight:600;color:var(--muted);
 border:1px solid var(--line);border-radius:0;padding:1px 7px;margin-bottom:6px}
.basis{font-size:13px;color:var(--muted);margin-bottom:8px}
.basis b{color:var(--ink);font-weight:600}
.up{color:var(--up)} .dn{color:var(--dn)}
.toc{display:flex;flex-wrap:wrap;gap:6px;margin:10px 0 4px}
.toc a{font-size:12.5px;color:var(--ink2);text-decoration:none;border:1px solid var(--line);
 border-radius:3px;padding:0 11px;min-height:40px;display:inline-flex;align-items:center;white-space:nowrap}   /* 31px·2px 였다(2026-09-18 오딧 11번) */
.toc a:hover{background:var(--paper2)}
table td:first-child,table th[scope=row]{white-space:nowrap}
tbody tr.agg{background:var(--paper2)}
.top3{font-size:13.5px;color:var(--ink2);margin:2px 0 10px;line-height:1.7}
.top3 b{color:var(--ink);font-weight:600;margin-right:4px}
.top3 a{color:var(--ink)}
"""


def main():
    src = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/',
        src, re.S).group(1))
    sts = json.loads(re.search(
        r'const STATS\s*=\s*(\{.*?\});?\s*(?:/\*|const |$)', src, re.S).group(1))

    secs, basis = build(adv, sts)
    # ⚠️ 계열 하나가 비면 그 섹션만 조용히 빠진 4섹션 페이지가 커밋된다.
    # 그 자체도 문제지만 더 나쁜 건 **다음 회차**다 — 배치는 pytest를 생성보다
    # 먼저 돌리므로, 4섹션 페이지를 본 test_five_indicators_in_fixed_order가
    # 실패해 **데이터 커밋 전체가 막힌다**(주간 시세·지역 20장까지 함께).
    # 원인은 이 화면인데 증상은 파이프라인 전체 정지라 진단이 오래 걸린다.
    # 그래서 여기서 먼저 죽는다: 커밋되지 않으니 라이브는 직전 판을 유지하고,
    # 배치 로그가 '어느 지표가 비었는지'를 그 자리에서 말한다(2026-09-02 리뷰).
    want = ['price', 'permits', 'moveins', 'unsold', 'jeonse']
    got = [re.search(r'<section id="([a-z]+)"', s).group(1) for s in secs]
    if got != want:
        print('monthly: 지표가 빠졌다 — 생성하지 않음 (기대 %s / 실제 %s)'
              % (want, got))
        print('  원자료에 해당 계열이 없다. data.js와 update_adv_data 쪽을 볼 것.')
        return 1

    # dateModified는 가장 최신 기준 시점에서 유도한다. 데이터가 안 바뀌면 안 움직여야
    # sitemap lastmod가 매일 흔들리지 않는다(/moveins/와 같은 규칙).
    # 비교는 반드시 sort_key로 — 한글 라벨 어휘 비교는 10월을 9월보다 작다고 본다.
    newest_raw = max(basis, key=sort_key) if basis else ''
    newest = month_label(newest_raw)
    key = sort_key(newest_raw)                       # 'YYYY-MM'
    mod_iso = (key + '-01') if re.match(r'^\d{4}-\d{2}$', key) else PUBLISHED

    toc = ('<div class="wrap"><nav class="toc" aria-label="지표 목록">'
           '<a href="#price">1 매매·전세·월세</a><a href="#permits">2 인허가</a>'
           '<a href="#moveins">3 입주물량</a><a href="#unsold">4 미분양</a>'
           '<a href="#jeonse">5 전세가율</a></nav></div>')

    title = '이달의 공급 통계 — 시도별 매매·전세·인허가·입주물량·미분양 | 아공맵'
    desc = ('매달 발표되는 공개 통계를 한 화면에서 순서대로. 시도별 매매·전세·월세 '
            '변동률, 인허가, 입주물량, 미분양, 전세가율 — 기준월과 원천을 함께 표시합니다.')
    body = ('<header><div class="wrap"><div class="chip">이달의 공급 통계</div>'
            '<h1>이번 달 통계, 한 화면에서</h1>'
            '<p class="lead">매달 흩어져 발표되는 공개 통계를 보는 순서 그대로 모았습니다. '
            '지표마다 <b>기준월과 발표 원천</b>을 함께 적었습니다.</p></div></header>'
            + toc + ''.join(secs)
            + '<section><div class="wrap"><p class="note">'
            '모든 값은 공개 통계 원자료에서 그대로 가져옵니다. 가공은 단위 환산과 '
            '합계뿐이며, 없는 값을 추정해 채우지 않습니다.'
            '</p></div></section>')

    html = I.fill(
        I.SHELL,
        title=esc(title), ogtitle=esc('이달의 공급 통계 — 한 화면 정리'),
        desc=esc(desc), url=URL,
        ld=ld_pack_here('이달의 공급 통계', desc, URL, mod_iso),
        src='한국부동산원 · 국토교통부 · KOSIS',
        body=body)
    # 이 페이지 전용 CSS를 SHELL 스타일 끝에 얹는다(SHELL을 건드리지 않는다).
    html = html.replace('</style>', EXTRA_CSS + '</style>', 1)
    # 진입 측정 — 기존 view/to 패턴과 같은 이름을 쓴다.
    html = html.replace('</body>',
                        "<script>try{gtag('event','view',{screen_name:'monthly'});}"
                        "catch(e){}</script>\n</body>", 1)

    os.makedirs(OUT, exist_ok=True)
    p = os.path.join(OUT, 'index.html')
    old = None
    try:
        old = io.open(p, encoding='utf-8').read()
    except IOError:
        pass
    # 날짜만 다른 재생성은 커밋하지 않는다(/zone/과 같은 규칙).
    DATE = re.compile(r'\d{4}-\d{2}-\d{2}')
    if old and DATE.sub('@', old) == DATE.sub('@', html):
        I.update_sitemap([('/monthly/', max(mod_iso, PUBLISHED))])
        print('monthly: 내용 변경 없음 — 그대로 둠 (기준 %s)' % newest)
        return 0
    io.open(p, 'w', encoding='utf-8', newline='\n').write(html)
    I.update_sitemap([('/monthly/', max(mod_iso, PUBLISHED))])
    print('monthly: /monthly/ 생성 (기준 %s, %d개 지표, %.1f KB)'
          % (newest, len(secs), len(html.encode('utf-8')) / 1024))
    return 0


if __name__ == '__main__':
    sys.exit(main())
