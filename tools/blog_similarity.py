# -*- coding: utf-8 -*-
"""블로그 글끼리 겹치는 문장 비율(반복률) — 네이버 유사문서·자동 생성 문서로 읽힐 위험을 숫자로 본다(2026-10-15).

숫자와 지역 이름만 바뀐 문장은 같은 문장으로 센다('뼈대'). 같은 카테고리 직전 글과 뼈대가 같은 문장의 비율이
반복률이다. 2026-10-15 첫 측정: 주간 시세 42~46%, 지역 편 29~43%, 사이클 2~7%, 도시 편 1%. 목표는 카테고리마다
WARN(25%) 아래다.

    python tools/blog_similarity.py                 발행 글(8월 이후)을 블로그에서 받아 카테고리별 반복률과 반복 문장 상위
    python tools/blog_similarity.py --draft <초안>   초안 두 칸(b1 주간·b2 지역)을 같은 카테고리 최신 발행 글과 견준다

네트워크는 RSS(close_published_issues.fetch_posts)와 모바일 글 화면만 읽는다. 키가 필요 없다.
"""
import collections
import html
import io
import os
import re
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

WARN = 0.25


def _regions():
    """뼈대에서 '@'로 바꿀 이름 — 판정 단위(sido_zones.ORDER)와 생성기가 화면·태그에 쓰는 이름에서 파생한다.
    손으로 적은 목록은 판정 단위가 바뀌어도 따라오지 않는다(test_region_list_inventory)."""
    import make_naver_post as P
    import sido_zones as SZ
    names = set(SZ.ORDER) | set(P.SEARCH_NAME.values()) | set(P.TAG_NAME.values()) | set(P.CITY_TAG.values())
    return sorted(names, key=len, reverse=True)


_REGIONS = []
MIN_LEN = 12          # 이보다 짧은 줄(링크 글자·소제목 조각)은 세지 않는다


def sentences(paras):
    out = []
    for para in paras:
        for s in re.split(r'(?<=[.?!])\s+', para):
            s = s.strip()
            if len(s) >= MIN_LEN:
                out.append(s)
    return out


def skeleton(s):
    """숫자(단위 포함)는 '#', 지역 이름은 '@'로 바꾼 문장 뼈대."""
    s = re.sub(r'[+\-−]?\d[\d,.]*\s*(%p|%|세대|호|주|년|월|일|배|개|곳|분의)?', '#', s)
    if not _REGIONS:
        _REGIONS.extend(_regions())
    for z in _REGIONS:
        s = s.replace(z, '@')
    return re.sub(r'\s+', ' ', s).strip()


def overlap(prev, cur):
    """cur 문장 가운데 prev 와 뼈대가 같은 비율(0~1). 둘 다 문장 목록."""
    if not cur:
        return 0.0
    ks = set(skeleton(x) for x in prev)
    return sum(1 for x in cur if skeleton(x) in ks) / len(cur)


def html_paras(fragment):
    """초안 복사 상자 HTML → 문단 글자 목록(자리 표시자 [ … ] 줄은 뺀다 — 발행 전에 사람이 지우는 안내다)."""
    f = re.sub(r'<table.*?</table>', '', fragment, flags=re.S)
    f = re.sub(r'</(p|h3|li|tr)>', '\n', f)
    t = html.unescape(re.sub(r'<[^>]+>', '', f))
    return [x.strip() for x in t.split('\n') if x.strip() and not x.strip().startswith('[')]


def fetch_posts(since='2026-08-01'):
    import close_published_issues as C
    out = []
    for p in (C.fetch_posts() or []):
        if str(p['date']) < since:
            continue
        m = re.search(r'(\d{9,})', p['url'] or '')
        if not m:
            continue
        url = 'https://m.blog.naver.com/PostView.naver?blogId=startupbd&logNo=%s' % m.group(1)
        t = urllib.request.urlopen(urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0 (iPhone)'}),
                                   timeout=20).read().decode('utf-8', 'replace')
        paras = [html.unescape(re.sub(r'<[^>]+>', '', b)).strip()
                 for b in re.findall(r'<p class="se-text-paragraph[^"]*"[^>]*>(.*?)</p>', t, re.S)]
        out.append(dict(date=str(p['date']), cat=p['cat'], title=p['title'],
                        paras=[x for x in paras if x and x != '​']))
    return sorted(out, key=lambda x: x['date'])


def report(posts):
    bycat = collections.defaultdict(list)
    for p in posts:
        bycat[p['cat']].append(p)
    worst = 0.0
    print('== 같은 카테고리 직전 글과 뼈대가 같은 문장 비율 (경고 %d%%)' % (WARN * 100))
    for cat, L in bycat.items():
        for a, b in zip(L, L[1:]):
            r = overlap(sentences(a['paras']), sentences(b['paras']))
            worst = max(worst, r)
            print('%s %-10s %s %3d%%  %s' % ('⚠' if r > WARN else ' ', cat[:8], b['date'], round(r * 100), b['title'][:40]))
    cnt = collections.Counter()
    for p in posts:
        for k in set(skeleton(s) for s in sentences(p['paras'])):
            cnt[k] += 1
    print('\n== 3편 이상에 반복된 문장 뼈대 (#=숫자, @=지역)')
    for k, n in cnt.most_common(30):
        if n >= 3:
            print(n, k[:110])
    return worst


def check_draft(path, posts):
    s = io.open(path, encoding='utf-8').read()
    import close_published_issues as C
    cats = {'b1': C.KIND_TO_CATEGORY['주간 시세'], 'b2': C.KIND_TO_CATEGORY['지역 공급']}     # 카테고리 이름 정본(전수리뷰 BL2-11)
    rows = []
    for box, cat in cats.items():
        if 'id="%s"' % box not in s:
            continue
        i = s.index('id="%s"' % box)
        j = s.index('</div></div>', i)
        cur = sentences(html_paras(s[i:j]))
        prev = [p for p in posts if p['cat'] == cat and not C.is_city_post(p['title'])]
        if not prev:
            continue
        r = overlap(sentences(prev[-1]['paras']), cur)
        rows.append((box, cat, r, prev[-1]['title']))
        print('%s %s %3d%%  직전 발행: %s' % ('⚠' if r > WARN else ' ', cat, round(r * 100), prev[-1]['title'][:40]))
    return rows


def main(argv):
    posts = fetch_posts()
    if '--draft' in argv:
        rows = check_draft(argv[argv.index('--draft') + 1], posts)
        return 1 if any(r > WARN for _, _, r, _ in rows) else 0
    return 1 if report(posts) > WARN else 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
