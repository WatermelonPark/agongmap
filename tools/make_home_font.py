# -*- coding: utf-8 -*-
"""홈 첫 화면 글꼴 — 홈에서 실제로 쓰는 글자만 담은 Pretendard 가변 서브셋을 굽는다(홈 마케팅 검수 B11·MOB-2, 2026-09-27).

왜: 홈은 CDN 의 Pretendard 가변 글꼴(dynamic-subset, 한글을 92조각으로 나눈 것)을 쓰는데, 첫 화면 글자를 덮느라 17조각
(전송 약 436KB)을 받는다. Chromium 망 속도 모사(일반 4G·느린 4G, CPU 4배 감속, 375px)로 재 보니 글꼴을 막은 경우보다
지도 완성이 3초 넘게 늦었다(요청서 기준 0.5초의 여섯 배). 추적(trace)으로 보면 시간의 대부분은 전송이 아니라 본문
스레드의 레이아웃이었다 — 조각이 따로따로 도착할 때마다 페이지 전체를 다시 배치하고, 이 가변 글꼴에는 HVAR(가변 글자폭
표)이 없어 글자폭을 구할 때마다 윤곽선을 보간한다. 그래서 두 가지를 같이 한다.
  ① 홈이 쓰는 글자만 담은 파일 하나(약 115KB)를 자체 호스팅하고 preload 한다 — 조각 도착마다의 재배치가 사라진다.
     preload 는 fetchpriority="low" 다. 기본(높음)이면 느린 4G 에서 글꼴이 첫 배치 전에 도착하는 회차가 잦아(5회 중 3회)
     첫 화면(FCP·h1)이 약 1.5초 늦게 그려졌다 — 낮추면 본문 스크립트 뒤에 와 5회 중 1회로 줄었다. preload 를 아예 빼면
     글꼴을 CSS 배치 때에야 찾아 지도 완성이 느린 4G 5.4초로 되돌아갔다(측정은 요청서 B11 배포 기록).
  ② 서브셋에 HVAR 을 만들어 넣는다(fontTools.varLib.hvar) — 글자폭을 표에서 바로 읽는다.
  두 조치로 지도 완성이 글꼴을 막은 경우와 비슷해졌다(측정표는 요청서 B11 배포 기록).

무엇을 담나(glyph_text): 홈 마크업의 글자(통계·퀴즈 화면 제외 — 그 화면은 열 때 CDN 조각을 받는다), 홈 본문 스크립트
(home-app.js, 분할 파일 제외)의 문자열, data-core.js 의 문자열(지역 이름·판정 문구·주간 결론), ASCII. 원본 글꼴에 없는
글자(이모지 등)는 뺀다. 빠진 글자는 CSS 글꼴 목록의 다음 글꼴('Pretendard Variable', CDN)이 그린다 — 모양은 같고 조각
하나를 더 받을 뿐이다. 그래서 데이터 문구가 새 글자를 써도 화면은 깨지지 않는다(배치가 이 도구를 돌리지 않는 이유).

어디에 쓰나: webfonts/home-<내용 해시>.woff2(주소에 해시 — 서비스워커 cache-first 가 옛 파일을 붙들지 않게), 그리고
index.html 의 <!--HOME_FONT_START-->…<!--HOME_FONT_END--> 구간(preload + @font-face + 홈 body 글꼴 목록). 구간 밖은
건드리지 않는다. 옛 webfonts/home-*.woff2 는 지운다.

라이선스: Pretendard 는 SIL OFL 1.1 이고 'Pretendard' 가 예약 글꼴 이름이다. 서브셋은 수정본이므로 글꼴 안의 이름을
AgongHome 으로 바꾸고(저작권·라이선스 항목은 그대로), webfonts/LICENSE.txt 로 라이선스 전문을 함께 싣는다.

시험: test_home_font 가 구간 모양(preload 와 @font-face 가 같은 파일, 파일 존재), 홈 마크업의 한글·ASCII 가 unicode-range
안에 있는지(홈 문구를 고치고 이 도구를 안 돌리면 빨개진다), 글꼴 목록이 app.css body 목록 앞에 AgongHome 하나만 더한
것인지를 본다.

사용: python tools/make_home_font.py [--src PretendardVariable.woff2]
  --src 가 없으면 npm 레지스트리에서 pretendard@PRETENDARD 꾸러미를 tools/cache/ 로 받아 가변 woff2 를 꺼낸다.
의존: fonttools, brotli — 사람이 돌리는 도구라 배치·시험 설치 목록에 없다(함수 안에서만 가져온다).
"""
import argparse
import hashlib
import html.parser
import io
import os
import re
import sys
import tarfile
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import home_src as HS  # noqa: E402  홈 스크립트는 이 입구로만 읽는다(백로그 10)

# 홈 CDN 링크(index.html)와 같은 판이어야 서브셋 글자와 CDN 조각 글자가 같은 모양이다 — test_home_font 가 대조한다.
PRETENDARD = '1.3.9'
TARBALL = 'https://registry.npmjs.org/pretendard/-/pretendard-%s.tgz' % PRETENDARD
MEMBER = 'package/dist/web/variable/woff2/PretendardVariable.woff2'
FAMILY = 'AgongHome'
# ⚠️ 저장소 루트의 fonts/ 는 쓰지 않는다 — make_og_cards·make_zone_cards 가 그 폴더를 카드용 TTF 자리로 먼저 찾는다.
FONT_DIR = 'webfonts'
START, END = '<!--HOME_FONT_START-->', '<!--HOME_FONT_END-->'
_BLOCK = re.compile(re.escape(START) + r'(.*?)' + re.escape(END), re.S)
# CDN CSS(pretendardvariable-dynamic-subset.css)의 font-weight 와 같다.
WEIGHT = '45 920'
# 홈 마크업에서 글자를 모으지 않는 곳: 통계·퀴즈 화면(열 때 CDN 조각을 받는다)과 배치가 매 회차 고쳐 쓰는 요약 구간
# (make_home_summary — 데이터 문구라 data-core 글자로 덮는다).
SKIP_IDS = ('view-stats', 'view-test')
SUMMARY = re.compile(r'<!--HOME_SUMMARY_START-->.*?<!--HOME_SUMMARY_END-->', re.S)


class _Text(html.parser.HTMLParser):
    """<body> 의 글자(주석·script·style·통계/퀴즈 화면 밖). 속성 중 화면에 보이는 것(alt·title·placeholder·aria-label 은
    화면에 안 그려지거나 드물어 뺀다)은 모으지 않는다."""
    VOID = {'area', 'base', 'br', 'col', 'embed', 'hr', 'img', 'input', 'link', 'meta', 'source', 'track', 'wbr'}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.out, self.stack, self.skip_at, self.body = [], [], None, False

    def handle_starttag(self, tag, attrs):
        if tag == 'body':
            self.body = True
        if tag in self.VOID:
            return
        self.stack.append(tag)
        if self.skip_at is None and (tag in ('script', 'style', 'noscript', 'template', 'title')
                                     or dict(attrs).get('id') in SKIP_IDS):
            self.skip_at = len(self.stack)

    def handle_endtag(self, tag):
        if tag in self.VOID or tag not in self.stack:
            return
        while self.stack:
            t = self.stack.pop()
            if self.skip_at is not None and len(self.stack) < self.skip_at:
                self.skip_at = None
            if t == tag:
                break

    def handle_data(self, data):
        if self.body and self.skip_at is None:
            self.out.append(data)


def static_home_text(html_text):
    """홈 마크업에서 첫 로딩에 그려질 수 있는 글자(요약 구간·통계/퀴즈 화면 제외)."""
    p = _Text()
    p.feed(SUMMARY.sub('', html_text))
    return ''.join(p.out)


def _js_strings(js):
    """자바스크립트의 문자열·템플릿 글자(주석 제외). 넉넉히 모으는 것이 목적이라 템플릿 안의 식도 그대로 담긴다."""
    out, i, n = [], 0, len(js)
    while i < n:
        c = js[i]
        if js.startswith('//', i):
            j = js.find('\n', i)
            i = n if j < 0 else j
        elif js.startswith('/*', i):
            j = js.find('*/', i + 2)
            i = n if j < 0 else j + 2
        elif c in '\'"`':
            j = i + 1
            while j < n and js[j] != c:
                j += 2 if js[j] == '\\' else 1
            out.append(js[i + 1:j])
            i = j + 1
        else:
            i += 1
    return ''.join(out)


def glyph_text(root=ROOT):
    """서브셋에 담을 글자 후보(원본 글꼴에 없는 것은 build 가 뺀다)."""
    files = dict(HS.home_files(root))
    home, script = files[HS.HOME], files[HS.EXTERNAL[0]]   # 마크업, 홈 본문 스크립트(분할 파일 제외)
    core = io.open(os.path.join(root, 'data-core.js'), encoding='utf-8').read() \
        if os.path.isfile(os.path.join(root, 'data-core.js')) else ''
    css = io.open(os.path.join(root, 'app.css'), encoding='utf-8').read()
    pseudo = ''.join(re.findall(r'content:\s*"([^"]*)"', css))   # ::before·::after 글자(·, › 등)
    ascii_ = ''.join(chr(c) for c in range(0x20, 0x7f))
    return static_home_text(home) + _js_strings(script) + _js_strings(core) + pseudo + ascii_


def ranges(cps):
    """코드포인트 집합 → CSS unicode-range 문자열."""
    rs, s, e = [], None, None
    for c in sorted(cps):
        if s is None:
            s = e = c
        elif c == e + 1:
            e = c
        else:
            rs.append((s, e))
            s = e = c
    if s is not None:
        rs.append((s, e))
    return ','.join(('U+%X' % a if a == b else 'U+%X-%X' % (a, b)) for a, b in rs)


def parse_ranges(text):
    """CSS unicode-range 문자열 → 코드포인트 집합(시험이 쓴다)."""
    out = set()
    for part in text.split(','):
        m = re.match(r'\s*U\+([0-9A-Fa-f]+)(?:-([0-9A-Fa-f]+))?\s*$', part)
        if not m:
            raise ValueError('unicode-range 조각을 못 읽었다: %r' % part)
        a = int(m.group(1), 16)
        b = int(m.group(2), 16) if m.group(2) else a
        out.update(range(a, b + 1))
    return out


def body_stack(root=ROOT):
    """app.css body 의 글꼴 목록(홈 목록은 이 앞에 FAMILY 만 더한다)."""
    css = io.open(os.path.join(root, 'app.css'), encoding='utf-8').read()
    m = re.search(r'\bbody\{[^}]*?font-family:([^;}]+)', css)
    if not m:
        raise SystemExit('app.css body 규칙에서 font-family 를 못 찾았다')
    return m.group(1).strip()


def block_html(fname, urange, root=ROOT):
    url = '/%s/%s' % (FONT_DIR, fname)
    return (
        '\n<link rel="preload" href="%s" as="font" type="font/woff2" crossorigin fetchpriority="low">\n'
        "<style>@font-face{font-family:'%s';font-style:normal;font-weight:%s;font-display:swap;"
        "src:url(%s) format('woff2-variations'),url(%s) format('woff2');unicode-range:%s}\n"
        "body.home-app{font-family:'%s',%s}</style>\n"
        % (url, FAMILY, WEIGHT, url, url, urange, FAMILY, body_stack(root)))


def _source(path):
    if path:
        return path
    cache = os.path.join(ROOT, 'tools', 'cache')
    os.makedirs(cache, exist_ok=True)
    out = os.path.join(cache, 'PretendardVariable-%s.woff2' % PRETENDARD)
    if not os.path.isfile(out):
        tgz = os.path.join(cache, 'pretendard-%s.tgz' % PRETENDARD)
        if not os.path.isfile(tgz):
            print('받는 중:', TARBALL)
            urllib.request.urlretrieve(TARBALL, tgz)
        with tarfile.open(tgz) as t:
            io.open(out, 'wb').write(t.extractfile(MEMBER).read())
    return out


def _rename(font):
    """예약 글꼴 이름(OFL)을 쓰지 않도록 글꼴 안 이름을 바꾼다. 저작권(0)·상표(7)·라이선스(13·14) 항목은 그대로 둔다."""
    keep = {0, 7, 8, 9, 11, 12, 13, 14}
    for rec in font['name'].names:
        if rec.nameID in keep:
            continue
        s = rec.toUnicode()
        t = s.replace('Pretendard Variable', FAMILY).replace('PretendardVariable', FAMILY).replace('Pretendard', FAMILY)
        if t != s:
            rec.string = t
    font['name'].setName('Subset of Pretendard %s for the agongmap home page (SIL OFL 1.1). Generated by '
                         'tools/make_home_font.py.' % PRETENDARD, 10, 3, 1, 0x409)


def build(src, root=ROOT):
    from fontTools import subset                  # noqa: 사람이 돌리는 도구 — 설치: pip install fonttools brotli
    from fontTools.ttLib import TTFont
    from fontTools.varLib.hvar import add_HVAR

    font = TTFont(src)
    cmap = font.getBestCmap()
    want = {ord(c) for c in glyph_text(root)} & set(cmap)
    opts = subset.Options()
    opts.flavor = 'woff2'
    opts.layout_features = ['*']
    opts.name_IDs = ['*']
    opts.name_languages = ['*']
    opts.notdef_outline = True
    s = subset.Subsetter(opts)
    s.populate(unicodes=sorted(want))
    s.subset(font)
    _rename(font)
    if 'HVAR' not in font:
        add_HVAR(font)
    font.flavor = 'woff2'
    font.recalcTimestamp = False   # 같은 입력이면 같은 파일(같은 해시) — 다시 돌려도 주소가 바뀌지 않게
    buf = io.BytesIO()
    font.save(buf)
    data = buf.getvalue()
    got = set(TTFont(io.BytesIO(data)).getBestCmap())
    return data, got


def write(data, cps, root=ROOT):
    d = os.path.join(root, FONT_DIR)
    os.makedirs(d, exist_ok=True)
    fname = 'home-%s.woff2' % hashlib.sha1(data).hexdigest()[:10]
    for f in os.listdir(d):
        if re.match(r'home-[0-9a-f]+\.woff2$', f) and f != fname:
            os.remove(os.path.join(d, f))
    io.open(os.path.join(d, fname), 'wb').write(data)
    lic = os.path.join(root, 'tools', 'fonts', 'LICENSE.txt')
    if os.path.isfile(lic):
        io.open(os.path.join(d, 'LICENSE.txt'), 'wb').write(io.open(lic, 'rb').read())
    path = os.path.join(root, HS.HOME)
    h = io.open(path, encoding='utf-8').read()
    if h.count(START) != 1 or h.count(END) != 1:
        raise SystemExit('index.html 에 %s … %s 구간이 하나씩 있어야 한다' % (START, END))
    out = _BLOCK.sub(lambda m: START + block_html(fname, ranges(cps), root) + END, h)
    io.open(path, 'w', encoding='utf-8', newline='\n').write(out)
    return fname


def main():
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--src', help='Pretendard Variable woff2(없으면 npm 에서 받는다)')
    a = ap.parse_args()
    data, cps = build(_source(a.src))
    fname = write(data, cps)
    hangul = sum(1 for c in cps if 0xAC00 <= c <= 0xD7A3)
    print('%s/%s  %d바이트 · 글자 %d개(한글 %d)' % (FONT_DIR, fname, len(data), len(cps), hangul))


if __name__ == '__main__':
    main()
