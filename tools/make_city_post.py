# -*- coding: utf-8 -*-
"""도시 입주 예정 단지 편 초안 — drafts/city-<도시>.html, 반기 차트, 썸네일, 독자용 엑셀.

    python tools/make_city_post.py 대구 2026-10 [--thumb-msg "첫 줄|*둘째 줄*"] [--shortcut]
    python tools/make_city_post.py 청주 2026-10 충북

재료는 tools/city_movein.py 가 받아 둔 캐시(tools/cache/city/<시도>.json)다. 먼저 `city_movein.py <도시> <달> --fetch`.

지역(시도) 편과 **다른 콘텐츠**다(09-30 대표): 판정·적정 공급량·필요량 숫자를 싣지 않고, 소제목·유도문도 지역 편 문장을
재사용하지 않는다. 도시 편의 잣대는 '적정 입주량 = 인구 ÷ 2.5 × 2%'(09-30 대표 결정, 인구만으로 잡은 참고치)다.
제목에는 반드시 '입주물량'을 넣는다 — 지역 편과 같은 카테고리를 쓰고 이 말로 두 시리즈를 가른다(close_published_issues.CITY_MARK).

전망 문단은 생성기가 쓰지 않는다. drafts/city-<도시>-outlook.txt 에 사람이(Claude가) 쓰고, 숫자는 {자리}로 둬서 데이터로 채운다
(재생성해도 시세 절과 숫자가 갈리지 않게, 10-03 리뷰). 쓸 수 있는 자리 이름은 실행할 때 찍힌다.
"""
import base64
import json
import os
import statistics
import sys
from collections import Counter, defaultdict
from urllib.parse import quote

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import city_movein as CM  # noqa: E402
import make_naver_post as P  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import make_zone_cards as ZC  # noqa: E402

REPO = os.path.dirname(HERE)
OUT = os.path.join(REPO, 'drafts')
PER_HH, RATE = 2.5, 0.02          # 적정 입주량 = 인구 ÷ 2.5 × 2% (09-30 대표)
BIG = 1000                        # '큰 단지'로 따로 부르는 세대수
esc, num = P.esc, P.num


def ym_txt(ym):
    return '%s년 %d월' % (ym[:4], int(ym[5:7]))


def after(ym):
    y, mo = int(ym[:4]), int(ym[5:7]) + 1
    return '%d년 %d월' % (y + (mo > 12), (mo - 1) % 12 + 1)


def shown(name):
    """본문에 보일 단지 이름. 정비사업 공사명 뒤 괄호에 브랜드가 있으면 그것을 쓴다
    ('송현주공3단지 주택재건축정비사업공사(상인센트럴자이)' → '상인센트럴자이'). 엑셀에는 원래 이름을 둔다."""
    import re
    m = re.match(r'.*정비사업\S*\((.+)\)$', name or '')
    return m.group(1) if m else name


def half(ym):
    return ym[:4] + ('상' if ym[5:7] <= '06' else '하')


def city_codes(city, weekly_codes):
    """(도시 코드, [(구 이름, 코드)]) — 홈 시군구 이름표(SGG_QNAME)에서 센다. 손으로 적지 않는다.
    도시 코드는 구 코드들의 공통 앞부분을 주간 시세 코드에 있을 때까지 줄인 것(대구 b201~b208 → b2, 청주 c20101~ → c201)."""
    names = P._sgg_names()
    gus = sorted((v.split(' ', 1)[1], k) for k, v in names.items() if v.startswith(city + ' '))
    if not gus:
        return None, []
    pre = os.path.commonprefix([k for _, k in gus])
    while pre and (pre not in weekly_codes or pre in [k for _, k in gus]):
        pre = pre[:-1]
    return pre, gus


def facts(city, start, sido):
    raw = CM.load(sido)
    m = CM.merge(raw, city, start)
    rows, occ_max = m['rows'], m['occ_max']
    adv, sts = P.M.load()
    f = dict(city=city, sido=sido, start=start, occ_max=occ_max, rows=rows, adv=adv)
    f['total'] = sum(r['n'] for r in rows)
    by_year, by_half, by_year_gu = Counter(), Counter(), defaultdict(Counter)
    for r in rows:
        by_year[r['ym'][:4]] += r['n']
        by_half[half(r['ym'])] += r['n']
        by_year_gu[r['ym'][:4]][r['gu']] += r['n']
    f.update(by_year=by_year, by_half=by_half, by_year_gu=by_year_gu, years=sorted(by_year))
    f['last_ym'] = rows[-1]['ym']
    # 한 해를 다 세는 해: 시작 연도 다음 해부터 부동산원 목록이 끝나는 해 앞까지. 그 뒤는 '지금까지 공고된'.
    f['full_years'] = [y for y in f['years'] if start[:4] < y <= occ_max[:4] and not (y == occ_max[:4] and occ_max[5:] != '12')]
    f['part_years'] = [y for y in f['years'] if y not in f['full_years']]
    pop, prd = CM.population(raw, city)
    f.update(pop=pop, pop_txt='%s년 %d월' % (prd[:4], int(prd[4:])), need=int(round(pop / PER_HH * RATE)),
             hh_est=pop / PER_HH)
    f['share'] = lambda v: int(round(v / f['need'] * 100))
    # 시도 안 몫(도시 ≠ 시도일 때만)
    full_sido = next(k for k, v in __import__('update_adv_data').BUBBLE_SHORT.items() if v == sido and k in
                     {x.get('C1_NM') for x in raw['pop']})
    f['sido_full'] = full_sido
    if city != sido:
        sd = [x for x in raw['occ'] if (x['주소'] or '').startswith(full_sido) and x['입주예정월'] >= start]
        f['sido_all'] = sum(int(x['세대수']) for x in sd)
        f['sido_city'] = sum(int(x['세대수']) for x in sd if CM.in_city(x['주소'], city))
        f['pop_share'] = pop / CM.population(raw, full_sido)[0]
    # 과거 준공(국토교통부 준공 실적, 사이트 분기 공급표와 같은 값) — 도시가 곧 시도인 광역시만
    if city == sido:
        o = adv['occupancy']
        i = o['regions'].index(sido)
        done = Counter()
        for r in o['rows']:
            if not r.get('e'):
                done[r['p'][:4]] += r['v'][i]
        f['done'] = {y: int(round(v)) for y, v in done.items() if len([1 for r in o['rows'] if r['p'][:4] == y and not r.get('e')]) == 4}
    # 분양 공고 이력(청약홈, 2020년 이후 아파트 분양주택) — 공고→입주 기간과 해마다 공고 수(리뷰 F3)
    ann = [c for c in raw['ch'] if CM.in_city(c.get('HSSPLY_ADRES'), city) and c.get('RENT_SECD_NM') == '분양주택'
           and c.get('HOUSE_SECD_NM') == 'APT' and (c.get('RCRIT_PBLANC_DE') or '') >= '2020' and c.get('MVN_PREARNGE_YM')
           and CM.base_name(c.get('HOUSE_NM')) == (c.get('HOUSE_NM') or '').strip()]

    def lag(c):
        y, d = c['MVN_PREARNGE_YM'], c['RCRIT_PBLANC_DE']
        return (int(y[:4]) * 12 + int(y[4:6])) - (int(d[:4]) * 12 + int(d[5:7]))
    f['ann_med'] = int(statistics.median(lag(c) for c in ann))
    f['ann_cnt'], f['ann_hh'] = Counter(), Counter()
    for c in ann:
        f['ann_cnt'][c['RCRIT_PBLANC_DE'][:4]] += 1
        f['ann_hh'][c['RCRIT_PBLANC_DE'][:4]] += int(c['TOT_SUPLY_HSHLDCO'] or 0)
    f['ann_last'] = max(c.get('RCRIT_PBLANC_DE') or '' for c in raw['ch'])
    # 시세 — 발표 반올림(pv2) 기준으로 센다
    sg = adv['weekly']['sgg']
    code, gus = city_codes(city, sg['codes'])
    f['last_p'] = sg['rows'][-1]['p']

    def wk(cd):
        i = sg['codes'].index(cd)
        cur = sg['rows'][-1]

        def streak(key):
            sign = MW.pv2(cur[key][i])[0]
            n = 0
            for rr in reversed(sg['rows']):
                v = rr[key][i]
                if v is None or MW.pv2(v)[0] != sign or MW.pv2(v) == '0.00':
                    break
                n += 1
            return sign, n
        return dict(ma=MW.pv2(cur['ma'][i]), je=MW.pv2(cur['je'][i]), sma=streak('ma'), sje=streak('je'))
    f['city_w'] = wk(code)
    f['gus'] = [g for g, _ in gus]
    f['gu_w'] = {g: wk(c) for g, c in gus}
    f['now_y'] = int(f['last_p'][:4])
    return f


def stxt(s):
    return '%d주 연속 %s' % (s[1], '상승' if s[0] == '+' else '하락')


# ---------------------------------------------------------------- 그림
INK, SOFT = (19, 30, 36), (94, 111, 116)


def halves(f):
    rows = f['rows']
    return ['%d%s' % (y, h) for y in range(int(f['years'][0]), int(f['years'][-1]) + 1) for h in ('상', '하')
            if half(rows[0]['ym']) <= '%d%s' % (y, h) <= half(rows[-1]['ym'])]


def chart(f, path, pal):
    from PIL import Image, ImageDraw, ImageFont
    K, Wd, Ht = 2, 1200, 1100
    img = Image.new('RGB', (Wd * K, Ht * K), (255, 255, 255))
    d = ImageDraw.Draw(img)
    F = lambda s, w='Bold': ImageFont.truetype(r'C:\Windows\Fonts\%s' % ('malgunbd.ttf' if w == 'Bold' else 'malgun.ttf'), s * K)
    d.text((50 * K, 46 * K), '%s 아파트 입주 예정 세대수 (반기별)' % f['city'], font=F(46), fill=INK)
    d.text((50 * K, 112 * K), '%s 이후 · %s부터는 청약 공고가 난 단지만 셈' % (ym_txt(f['start']), after(f['occ_max'])),
           font=F(30, 'Regular'), fill=SOFT)
    hs = halves(f)
    occ_h, ch_h = Counter(), Counter()
    for r in f['rows']:
        (ch_h if r['src'] == '청약홈' else occ_h)[half(r['ym'])] += r['n']
    hn = f['need'] / 2
    top = max(max(f['by_half'].values()), hn * 1.15)
    x0, x1, yb, yt = 40, Wd - 30, Ht - 210, 260
    bw = (x1 - x0) / len(hs)
    labels = []
    for i, h in enumerate(hs):
        cx = x0 + bw * (i + .5)
        a, b = occ_h[h], ch_h[h]
        ha, hb = (yb - yt) * a / top, (yb - yt) * b / top
        w = bw * .62
        if a:
            d.rectangle([(cx - w / 2) * K, (yb - ha) * K, (cx + w / 2) * K, yb * K], fill=pal[3])
        if b:
            d.rectangle([(cx - w / 2) * K, (yb - ha - hb) * K, (cx + w / 2) * K, (yb - ha) * K], fill=pal[2])
        v = a + b
        labels.append((cx, yb - ha - hb - 28, num(v) if v else ('공고 전' if h > half(f['occ_max']) else '0')))
        lab = '%s년 %s반기' % (h[:4], h[4])
        d.text((cx * K, (yb + 36) * K), lab[:5], font=F(32, 'Regular'), fill=SOFT, anchor='mm')
        d.text((cx * K, (yb + 76) * K), lab[6:], font=F(32, 'Regular'), fill=SOFT, anchor='mm')
    d.line([x0 * K, yb * K, x1 * K, yb * K], fill=(200, 200, 200), width=2 * K)
    yn = yb - (yb - yt) * hn / top
    xx = x0
    while xx < x1:
        d.line([xx * K, yn * K, min(xx + 14, x1) * K, yn * K], fill=(200, 60, 40), width=3 * K)
        xx += 24
    d.text(((x1 - 4) * K, (yn - 12) * K), '적정 입주량(반기) %s세대' % num(int(round(hn))), font=F(32), fill=(200, 60, 40), anchor='rb')
    for cx, cy, t in labels:
        d.text((cx * K, cy * K), t, font=F(38 if t[0].isdigit() else 30), fill=INK if t[0].isdigit() else SOFT,
               anchor='mm', stroke_width=6 * K, stroke_fill=(255, 255, 255))
    lx, ly = 50, 172
    d.rectangle([lx * K, ly * K, (lx + 30) * K, (ly + 30) * K], fill=pal[3])
    d.text(((lx + 42) * K, (ly + 15) * K), '입주예정물량정보', font=F(30, 'Regular'), fill=INK, anchor='lm')
    d.rectangle([(lx + 340) * K, ly * K, (lx + 370) * K, (ly + 30) * K], fill=pal[2])
    d.text(((lx + 382) * K, (ly + 15) * K), '청약홈 공고(청약 세대만)', font=F(30, 'Regular'), fill=INK, anchor='lm')
    d.text((50 * K, (Ht - 72) * K), '붉은 점선 = 연 적정 입주량(인구 ÷ 2.5 × 2%%) %s세대의 절반' % num(f['need']),
           font=F(30, 'Regular'), fill=(200, 60, 40), anchor='lm')
    d.text((50 * K, (Ht - 30) * K), '자료: 한국부동산원 입주예정물량정보·청약홈·KOSIS', font=F(30, 'Regular'), fill=SOFT, anchor='lm')
    d.text(((Wd - 30) * K, (Ht - 30) * K), '아공맵', font=F(30), fill=SOFT, anchor='rm')
    img.resize((Wd, Ht), Image.LANCZOS).save(path)


def thumb(f, path, lines, pal):
    from PIL import Image, ImageDraw
    K, Wd, Ht = 2, 1200, 900
    BG, FILL, DIM, ACC = pal
    img = Image.new('RGB', (Wd * K, Ht * K), BG)
    d = ImageDraw.Draw(img)
    hs = halves(f)
    top = max(max(f['by_half'].values()), f['need'] / 2)
    bw = Wd / len(hs)
    for i, h in enumerate(hs):
        hh = (Ht - 260) * f['by_half'][h] / top
        d.rectangle([(bw * i + bw * .12) * K, (Ht - 40 - hh) * K, (bw * (i + 1) - bw * .12) * K, (Ht - 40) * K], fill=FILL)
    d.text((Wd / 2 * K, 96 * K), '%s 아파트 입주물량 %s~%s' % (f['city'], f['start'][:4], f['last_ym'][:4]),
           font=ZC.font(38 * K, 'Bold'), fill=SOFT, anchor='mm')
    size = min([P.THUMB_FONT * K] + [ZC.fit_width(c.strip('*'), (Wd - 120) * K, hi=P.THUMB_FONT * K, lo=60 * K).size
                                     for c in lines])
    fnt = ZC.font(size, 'Bold')
    gap = int(size * 1.22)
    y = Ht / 2 * K - gap * (len(lines) - 1) / 2 + 10 * K
    for ln in lines:
        d.text((Wd / 2 * K, y), ln.strip('*'), font=fnt, anchor='mm', stroke_width=10 * K, stroke_fill=BG,
               fill=ACC if ln.startswith('*') else INK)
        y += gap
    d.text((Wd / 2 * K, (Ht - 78) * K), '아공맵', font=ZC.font(44 * K, 'Bold'), fill=INK, anchor='mm',
           stroke_width=6 * K, stroke_fill=BG)
    img.resize((Wd, Ht), Image.LANCZOS).save(path)


# ---------------------------------------------------------------- 엑셀
def excel(f, path):
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
    from openpyxl.utils import get_column_letter
    rows, city = f['rows'], f['city']
    wb = Workbook()
    head_fill = PatternFill('solid', fgColor='E9E0F4')
    thin = Side(style='thin', color='CCCCCC')
    box = Border(left=thin, right=thin, top=thin, bottom=thin)

    def table(ws, head, data, widths):
        for j, h in enumerate(head, 1):
            c = ws.cell(1, j, h)
            c.font, c.fill, c.border = Font(bold=True), head_fill, box
            c.alignment = Alignment(horizontal='center', vertical='center', wrap_text=True)
        for i, row in enumerate(data, 2):
            for j, v in enumerate(row, 1):
                c = ws.cell(i, j, v)
                c.border = box
                if isinstance(v, int):
                    c.number_format = '#,##0'
        for j, w in enumerate(widths, 1):
            ws.column_dimensions[get_column_letter(j)].width = w

    ws = wb.active
    ws.title = '단지 목록'
    table(ws, ['입주 예정월', '단지명', '구·군', '주소', '세대수', '구분', '출처', '청약 공고일', '청약홈 공급 세대', '비고'],
          [[r['ym'], r['name'], r['gu'], r['addr'], r['n'], r['kind'], r['src'], r.get('ch_date') or '',
            r.get('ch_n') if r.get('ch_n') is not None else '', r['note']] for r in rows],
          [11, 46, 9, 40, 9, 8, 28, 12, 11, 40])
    last = len(rows) + 1
    ws.cell(last + 2, 4, '합계').font = Font(bold=True)
    c = ws.cell(last + 2, 5, f['total'])
    c.font, c.number_format = Font(bold=True), '#,##0'
    ws.freeze_panes = 'C2'
    ws.auto_filter.ref = 'A1:J%d' % last

    ws2 = wb.create_sheet('연도별·구별 합계')
    gus = [g for g in f['gus'] if any(f['by_year_gu'][y].get(g) for y in f['years'])]
    data2 = [[int(y)] + [f['by_year_gu'][y].get(g, 0) for g in gus] + [f['by_year'][y]] for y in f['years']]
    table(ws2, ['입주 연도'] + gus + ['합계'], data2, [11] + [10] * len(gus) + [11])
    k = len(data2) + 2
    ws2.cell(k, 1, '합계').font = Font(bold=True)
    for j in range(2, len(gus) + 3):
        c = ws2.cell(k, j, sum(row[j - 1] for row in data2))
        c.font, c.number_format = Font(bold=True), '#,##0'
    ws2.cell(k + 2, 1, '%s 이후 입주만 셉니다. %s부터는 청약홈 공고 기준이라 조합원·임대 몫이 빠집니다.'
             % (ym_txt(f['start']), after(f['occ_max'])))

    ws4 = wb.create_sheet('적정 대비')
    data4 = []
    for y in f['years']:
        part = y in f['part_years']
        note = ('%s부터만 셈' % ym_txt(f['start'])) if y == f['start'][:4] else \
            ('지금까지 공고분 포함(청약 공급 세대, 조합원·임대 몫 제외)' if part else '')
        data4.append([int(y), f['by_year'][y], f['need'], '' if part else f['by_year'][y] / f['need'], note])
    table(ws4, ['입주 연도', '입주 예정 세대', '연간 적정 입주량', '적정 대비', '비고'], data4, [11, 14, 16, 11, 40])
    for i in range(2, len(data4) + 2):
        ws4.cell(i, 4).number_format = '0%'
    k = len(data4) + 3
    for j, t in enumerate(['적정 입주량 = 인구 ÷ 2.5(가구당 인원) × 2%',
                           '%s 인구 %s명(KOSIS 주민등록인구, %s) ÷ 2.5 = %s세대, 그 2%% = 연 %s세대'
                           % (city, num(f['pop']), f['pop_txt'], num(int(round(f['hh_est']))), num(f['need'])),
                           '인구만으로 잡은 참고치입니다. 도시의 성격이나 주변 도시로 오가는 수요는 반영하지 않습니다.']):
        ws4.cell(k + j, 1, t)

    ws3 = wb.create_sheet('읽는 법')
    matched = [r for r in rows if '+' in r['src']]
    notes = [
        ('자료', '한국부동산원 주택공급정보 「입주예정물량정보」(공공데이터포털 15111714, 30세대 이상 단지별)와 '
               '청약홈 「APT 분양정보」(공공데이터포털)를 합쳤습니다.'),
        ('기간', '%s부터 %s까지 입주 예정인 단지입니다.' % (ym_txt(f['start']), ym_txt(f['last_ym']))),
        ('합치는 규칙', '%s까지는 입주예정물량정보를 씁니다. 청약홈에도 있는 단지(%d곳)는 한 번만 세고 세대수는 입주예정물량정보 '
                     '값을 씁니다. 그 기간에 청약홈에만 있는 단지는 입주예정물량정보 갱신 뒤에 나온 공고라서 더했습니다. %s부터는 '
                     '입주예정물량정보가 아직 없어 청약홈 공고의 입주 예정월로 채웁니다.' % (ym_txt(f['occ_max']), len(matched),
                                                                         after(f['occ_max']))),
        ('청약홈 세대수', '청약으로 공급한 세대(일반·특별공급)만 셉니다. 조합원 몫과 단지 안의 임대 몫이 빠지고, 청약홈 분양 공고에 '
                     '나오지 않는 임대 단지는 잡히지 않습니다.'),
        ('적정 입주량', '인구 ÷ 2.5(가구당 인원)로 세대수를 잡고 그 2%%를 연간 적정 입주량으로 봅니다. %s 인구 %s명(%s 주민등록) '
                    '기준 연 %s세대입니다. 인구만으로 잡은 참고치입니다.' % (city, num(f['pop']), f['pop_txt'], num(f['need']))),
        ('입주 예정월', '공고 시점의 예정월입니다. 공사 일정에 따라 앞뒤로 바뀔 수 있습니다.'),
        ('기준일', '청약홈은 %s 공고까지 받았습니다. 입주예정물량정보는 반기마다 갱신됩니다.' % f['ann_last']),
        ('만든 곳', '아공맵(아파트 공급 지도) https://www.agongmap.co.kr'),
        ('면책', '숫자는 공개 데이터를 정리한 것입니다. 투자 판단과 그 결과는 이용하는 분의 몫입니다.'),
    ]
    for i, (a, b) in enumerate(notes, 1):
        ws3.cell(i, 1, a).font = Font(bold=True)
        c = ws3.cell(i, 2, b)
        c.alignment = Alignment(wrap_text=True, vertical='top')
        ws3.cell(i, 1).alignment = Alignment(vertical='top')
    ws3.column_dimensions['A'].width = 14
    ws3.column_dimensions['B'].width = 100
    wb.save(path)
    return ws2.title, ws4.title


# ---------------------------------------------------------------- 본문
def body(f, sheets, xlsx_name, outlook):
    city, sido, rows = f['city'], f['sido'], f['rows']
    by_year, years, share = f['by_year'], f['years'], f['share']
    yN = str(f['now_y'] + 1)
    B = ['<p>[여기에 썸네일 이미지를 넣어 주세요 — 첫 이미지가 대표 이미지가 됩니다]</p>']
    B.append('<h3>%s 아파트 입주물량, %s년까지 %d개 단지</h3>' % (city, f['last_ym'][:4], len(rows)))
    per_year = ', '.join(('%s년 <b>%s세대</b>' if y in f['full_years'] else '%s년 %s세대') % (y, num(by_year[y]))
                         for y in years)
    B.append('<p>%s부터 %s까지 %s에 입주가 잡힌 아파트는 <b>%d개 단지, %s세대</b>입니다. 연도별로는 %s입니다. %s</p>'
             % (ym_txt(f['start']), ym_txt(f['last_ym']), city, len(rows), num(f['total']), per_year,
                '%s년은 %d월부터 센 것이고, %s 이후는 지금까지 분양 공고가 난 물량만 들어 있습니다.'
                % (f['start'][:4], int(f['start'][5:]), after(f['occ_max']))
                if len(years) > 1 else ''))
    if f.get('done'):
        ys = sorted(f['done'])[-3:]
        B.append('<p>얼마 전까지는 사정이 달랐습니다. 국토교통부 준공 실적으로 보면 %s에는 %s의 아파트가 지어졌습니다. '
                 '%s년 입주 예정 %s세대는 그 시기와 견줄 수 없을 만큼 적습니다.</p>'
                 % (sido, ', '.join('%s년 %s호' % (y, num(f['done'][y])) for y in ys), yN, num(by_year.get(yN, 0))))
    if city != sido:
        B.append('<p>한국부동산원 자료가 있는 %s까지로 좁혀 보면, %s부터 %s에 입주할 %s세대 가운데 <b>%d%%</b>(%s세대)가 %s 단지입니다. '
                 '%s에는 %s 인구의 %d%%가 살고 있으므로, %s 새 아파트 가운데 %s가 받는 몫은 인구 비중의 %.1f배입니다.</p>'
                 % (ym_txt(f['occ_max']), ym_txt(f['start']), sido, num(f['sido_all']),
                    round(f['sido_city'] / f['sido_all'] * 100), num(f['sido_city']), city, city, sido,
                    round(f['pop_share'] * 100), sido, city, f['sido_city'] / f['sido_all'] / f['pop_share']))
    B.append('<p>[여기에 반기별 입주 차트 이미지를 넣어 주세요]</p>')

    B.append('<h3>%s 적정 입주량과 견주면</h3>' % city)
    fy = f['full_years']
    B.append('<p>%s %s 아파트 입주물량은 한 해 적정 입주량의 %s입니다.%s 적정 입주량은 %s 인구 %s명(%s 주민등록)을 가구당 2.5명으로 '
             '나눈 약 %s세대의 2%%인 <b>연 %s세대</b>입니다. 인구만으로 잡은 참고치이므로 도시의 성격이나 주변 도시로 오가는 수요는 '
             '반영하지 않습니다.</p>'
             % ('·'.join('%s년' % y for y in fy), city, '·'.join('<b>%d%%</b>' % share(by_year[y]) for y in fy),
                ''.join(' %s년은 지금까지 잡힌 물량만으로 %d%%입니다.' % (y, share(by_year[y]))
                        for y in f['part_years'] if y > f['start'][:4]),
                city, num(f['pop']), f['pop_txt'], num(int(round(f['hh_est'], -3))), num(f['need'])))

    big = sorted([r for r in rows if r['n'] >= BIG], key=lambda r: r['ym'])
    rent = [r for r in rows if r['kind'] == '임대']
    B.append('<h3>%s 입주 예정 단지</h3>' % city)
    txt = []
    if big:
        txt.append('1,000세대가 넘는 단지는 %s%s입니다.' % (
            ', '.join('%s %s %s %s세대' % (ym_txt(r['ym']), r['gu'], esc(shown(r['name'])), num(r['n'])) for r in big),
            ' 두 곳' if len(big) == 2 else (' %d곳' % len(big) if len(big) > 2 else '')))
        txt.append('두 단지를 빼면 남는 물량은 %s세대입니다.' % num(f['total'] - sum(r['n'] for r in big)) if len(big) == 2 else '')
    if rent:
        txt.append('%d곳 %s세대는 공공임대·행복주택 같은 임대 단지입니다.' % (len(rent), num(sum(r['n'] for r in rent))))
    B.append('<p>%s 전체 단지는 아래 표와 같습니다. 주소와 출처까지 담은 엑셀 파일을 글 끝에 첨부했습니다.</p>'
             % ' '.join(t for t in txt if t))
    tr = []
    for r in rows:
        mark = ' ※' if r['src'] == '청약홈' else ''
        extra = '' if '임대' in r['name'] or '행복' in r['name'] else {'임대': '(임대)', '분양임대': '(분양·임대)'}.get(r['kind'], '')
        tr.append('<tr><td>%s.%s</td><td>%s%s · %s</td><td style="text-align:right">%s%s</td></tr>'
                  % (r['ym'][:4], r['ym'][5:7], esc(shown(r['name'])), extra, r['gu'], num(r['n']), mark))
    B.append('<table border="1" cellspacing="0" cellpadding="6"><thead><tr><th>입주</th><th>단지 · 구</th><th>세대수</th></tr></thead>'
             '<tbody>%s<tr><th colspan="2">합계</th><th style="text-align:right">%s</th></tr></tbody></table>'
             % (''.join(tr), num(f['total'])))
    if any(r['src'] == '청약홈' for r in rows):
        B.append('<p>※ 표시는 한국부동산원 입주예정물량정보에 아직 없어 청약홈 분양 공고로 채운 단지입니다. 청약으로 공급한 세대만 '
                 '세므로 조합원·임대 몫이 있는 단지는 실제 입주 세대보다 적게 잡힙니다.</p>')

    ac, ah = f['ann_cnt'], f['ann_hh']
    ny = str(f['now_y'])
    prev = [str(f['now_y'] - k) for k in (3, 2, 1)]
    peak_y = max((y for y in ac if y < ny), key=lambda y: ac[y])
    few = ac[ny] * 4 <= ac[peak_y]                 # 가장 많던 해의 4분의 1 이하
    land = f['now_y'] * 12 + int(f['last_p'][5:7]) - 1 + f['ann_med']
    B.append(('<h3>%s 분양 공고, 올해는 %d건뿐입니다</h3>' if few else '<h3>%s 분양 공고, 올해 %d건</h3>') % (city, ac[ny]))
    B.append('<p>2020년 이후 %s 분양 단지는 청약 공고부터 입주 예정월까지 중간값이 <b>%d개월</b>입니다. 지금 공고가 나와도 입주는 '
             '%d년 %d월 무렵이라서, 그 전까지 들어올 새 아파트는 이 표가 사실상 전부입니다. %s 분양 공고는 %s년 %d건(%s세대)이 가장 많았고, '
             '%s이었다가 올해는 %d월까지 %d건(%s세대)입니다.%s</p>'
             % (city, f['ann_med'], land // 12, land % 12 + 1, city, peak_y, ac[peak_y], num(ah[peak_y]),
                ', '.join('%s년 %d건(%s세대)' % (y, ac[y], num(ah[y])) for y in prev),
                int(f['ann_last'][5:7]), ac[ny], num(ah[ny]),
                ' <b>입주 공백을 메울 공고가 나오지 않고 있습니다.</b>' if few else ''))

    cw, gw = f['city_w'], f['gu_w']
    lead = cw['sje'] if cw['sje'][1] >= cw['sma'][1] else cw['sma']
    B.append('<h3>%s 아파트 시세, %s %s</h3>' % (city, '전세' if lead is cw['sje'] else '매매', stxt(lead)))
    up = sorted((g for g in gw if gw[g]['sma'][0] == '+'), key=lambda g: -gw[g]['sma'][1])
    dn = sorted((g for g in gw if gw[g]['sma'][0] == '-' and gw[g]['sma'][1] >= 8), key=lambda g: -gw[g]['sma'][1])
    je_up = [g for g in gw if gw[g]['sje'][0] == '+']
    s = ['한국부동산원 %s 기준 %s 아파트값은 매매 <b>%s%%</b>, 전세 <b>%s%%</b>입니다.' % (P.kdate(f['last_p']), city, cw['ma'], cw['je'])]
    if len(je_up) == len(gw):
        s.append('주간 시세가 나오는 %s %d개 구·군의 전세가 모두 오르고 있습니다.' % (city, len(gw)))
    if up:
        g = up[0]
        s.append('매매는 %s가 %s%%로 %d주째 가장 오래 오르고 있습니다.' % (g, gw[g]['ma'], gw[g]['sma'][1]))
    for g in dn:
        s.append('%s 매매는 %s%%로 %d주 연속 내렸습니다.' % (g, gw[g]['ma'], gw[g]['sma'][1]))
    B.append('<p>%s</p>' % ' '.join(s))

    B.append('<h3>%s년 입주 공백 뒤 %s 전세와 매매</h3>' % (yN, city))
    B.append('<p>%s</p>' % outlook)

    B.append('<h3>단지 목록 엑셀 파일</h3>')
    B.append('<p>%d개 단지의 입주 예정월, 주소, 세대수, 출처를 엑셀 파일로 정리했습니다. 「%s」와 「%s」 시트도 함께 넣었습니다. '
             '관심 단지의 입주 시기를 확인하거나 전세 만기와 맞춰 볼 때 쓰시면 됩니다.</p>' % (len(rows), sheets[0], sheets[1]))
    B.append('<p>[여기에 엑셀 파일을 첨부해 주세요: %s]</p>' % esc(xlsx_name))
    B.append('<p>자료: 한국부동산원 입주예정물량정보(%s까지), 청약홈 분양 공고, KOSIS 주민등록인구%s. 두 자료에 모두 있는 단지는 한 번만 '
             '셌습니다. 자세한 기준은 첨부 엑셀의 「읽는 법」 시트에 적었습니다.</p>'
             % (ym_txt(f['occ_max']), ', 국토교통부 준공 실적' if f.get('done') else ''))
    link = P.site_link('/zone/%s/' % quote(sido), 'city_%s' % quote(city))
    B.append('<p>%s 전체 공급은 이 글과 다른 시도 단위 기준으로 리포트에서 따로 다룹니다.<br>👉 <a href="%s">%s 공급 리포트</a></p>'
             % (P.SEARCH_NAME.get(sido, sido), link, P.SEARCH_NAME.get(sido, sido)))
    B.append('<p>이 목록에 빠진 단지나 입주 시기가 바뀐 단지를 아시면 댓글로 알려 주세요. 확인한 내용은 다른 분들도 보실 수 있게 '
             '답글로 남기겠습니다.</p>')
    B.append(P.disclaimer(f['now_y'] + len(rows)))
    return '\n'.join(B)


def outlook_text(f):
    path = os.path.join(OUT, 'city-%s-outlook.txt' % f['city'])
    cw = f['city_w']
    yN = str(f['now_y'] + 1)
    keys = dict(city=f['city'], y_next=yN, n_next=num(f['by_year'].get(yN, 0)), share_next=f['share'](f['by_year'].get(yN, 0)),
                need=num(f['need']), ann_med=f['ann_med'], ann_now=f['ann_cnt'][str(f['now_y'])],
                je_streak=cw['sje'][1], ma_streak=cw['sma'][1], je=cw['je'], ma=cw['ma'],
                ma_down='·'.join(g for g in f['gu_w'] if f['gu_w'][g]['sma'][0] == '-'))
    if f.get('done'):
        for y, v in f['done'].items():
            keys['done_%s' % y] = num(v)
    if not os.path.exists(path):
        print('  ⚠ 전망 문단 파일이 없다: %s — 자리 이름: %s' % (path, ', '.join('{%s}' % k for k in keys)))
        return '[여기에 전망을 3~5문장으로. 첫 문장에 "제 판단으로는"으로 방향을 못 박고, 시점 유보는 마지막 한 문장]'
    with open(path, encoding='utf-8') as fh:
        return fh.read().strip().format(**keys)


def main(argv):
    args = [a for a in argv if not a.startswith('--') and not (argv.index(a) > 0 and argv[argv.index(a) - 1] == '--thumb-msg')]
    city, start = args[0], args[1]
    sido = args[2] if len(args) > 2 else city
    f = facts(city, start, sido)
    pal = P.THUMB_PALETTES[P.THUMB_GROUP[sido]]
    os.makedirs(OUT, exist_ok=True)
    chart_path = os.path.join(OUT, 'city-%s-입주.png' % city)
    thumb_path = os.path.join(OUT, 'thumb-city-%s.png' % city)
    chart(f, chart_path, pal)
    yN = str(f['now_y'] + 1)
    lines = P._thumb_msg_arg(argv) or ['%s년 입주 %s세대' % (yN, num(f['by_year'].get(yN, 0))), '*적정의 %d%%*' % f['share'](f['by_year'].get(yN, 0))]
    if not P._thumb_msg_arg(argv):
        print('  ⚠ 썸네일 문구가 기본값이다. 결론에 맞춰 --thumb-msg "첫 줄|*둘째 줄*" 로 바꿀 것')
    thumb(f, thumb_path, lines, pal)
    xlsx_name = '%s-아파트-입주예정-단지-%s-%s.xlsx' % (city, start[:4], f['last_ym'][:4])
    xlsx_path = os.path.join(OUT, xlsx_name)
    sheets = excel(f, xlsx_path)
    html_body = body(f, sheets, xlsx_name, outlook_text(f))
    share_n = f['share'](f['by_year'].get(yN, 0))
    # 제목에는 반드시 '입주물량'. 결론절에 연도·월을 넣지 않는다(title_warnings, 블덱스 '#2027년' 사례).
    titles = ['%s년 %s 아파트 입주물량, 적정의 %d%%에 그쳐 전세가 먼저 오릅니다' % (yN, city, share_n),
              '%s년 %s 입주 예정 아파트 %d곳, 입주물량은 적정의 %d%%입니다' % (yN, city, len(f['rows']), share_n)]
    assert all(CM_MARK in t for t in titles)
    warn = [w for t in titles for w in P.title_warnings(t)]
    tags = ['%s아파트' % city, '%s입주물량' % city, '%s부동산전망' % city, '%s입주예정아파트' % city, '아공맵']
    S = ['<!doctype html><html lang="ko"><meta charset="utf-8">',
         '<title>네이버 블로그 초안 — %s 입주 예정 단지</title>' % city,
         '<style>%s</style>' % P.CSS,
         '<h1>네이버 블로그 초안 — %s 입주 예정 단지 (%s 기준)</h1>' % (city, f['last_p']),
         '<p class="hint">[복사] → 스마트에디터에 붙여넣기 → 이미지 붙여넣기 → 엑셀 파일 첨부 → 발행.</p>',
         '<section class="draft"><h2>도시 입주 예정 단지 편 · %s</h2>' % city,
         P.field('제목', 't1', esc(titles[0]), 't'),
         '<p class="note">제목 후보 2: <code>%s</code>%s</p>' % (esc(titles[1]), ''.join('<br>⚠ ' + esc(w) for w in warn)),
         P.field('본문', 'b1', html_body),
         '<p class="note">📎 이미지 두 장과 엑셀 파일 하나입니다.<br><b>%s</b> → [썸네일] (글 맨 위, 대표 이미지로 지정)<br>'
         '<b>%s</b> → [반기별 입주 차트]<br><b>%s</b> → 본문 [엑셀 파일] 자리. 스마트에디터 위쪽 도구 막대의 '
         '<b>파일</b> 버튼 → 내 PC → 이 파일을 고르면 글 안에 내려받기 칸이 생깁니다.</p>'
         % (os.path.relpath(thumb_path, REPO), os.path.relpath(chart_path, REPO), 'drafts\\' + xlsx_name),
         P.img_gallery([(os.path.relpath(thumb_path, REPO), '썸네일 · 글 맨 위, 대표 이미지'),
                        (os.path.relpath(chart_path, REPO), '반기별 입주 차트')]),
         # 첨부 엑셀은 태그 바로 앞(10-09 대표). 초안 안에 싣는다.
         '<p class="note">📎 <a download="%s" href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,%s" '
         'style="font-weight:700">⬇ 첨부 엑셀 내려받기 (%s)</a> · 받은 파일을 스마트에디터 <b>파일</b> 버튼으로 본문 [엑셀 파일] 자리에 첨부하세요.</p>'
         % (esc(xlsx_name), base64.b64encode(open(xlsx_path, 'rb').read()).decode('ascii'), esc(xlsx_name)),
         P.tagfield(tags),   # 태그는 맨 아래(10-09 대표)
         '</section>',
         '<p class="hint">⚠️ 지역(시도) 편이나 다른 도시 편과 같은 문장을 쓰면 유사문서로 묶일 수 있습니다. 도시 이름과 숫자만 바뀌는 '
         '뼈대 문장은 회차마다 고쳐 쓰세요.</p>', P.SOURCE_CHECK, '<script>%s</script></html>' % P.JS]
    html_path = os.path.join(OUT, 'city-%s.html' % city)
    P.write_draft(html_path, '\n'.join(S))
    print('저장', html_path, xlsx_path)
    if '--shortcut' in argv:
        print(P.desktop_shortcut(html_path, '아공맵 블로그 초안 (도시)'))
    return f


import close_published_issues as _CPI  # noqa: E402
CM_MARK = _CPI.CITY_MARK

if __name__ == '__main__':
    main(sys.argv[1:])
