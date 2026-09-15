# -*- coding: utf-8 -*-
"""퀴즈 점수별 정적 공유 페이지 — /{세트 주소}/{점수}/ (2026-09-15 점검 후속 ⑧).

카카오 공유는 점수 카드를 직접 넘기지만, 링크 복사·밴드·문자로 보내면 미리보기 봇이 JS 를 실행하지
않아 랜딩의 일반 카드만 보였다. 점수마다 og:image(share/{세트}-{점수}.png)를 가진 정적 페이지를 두고
대결 링크를 그리로 보낸다. 사람은 곧바로 홈의 대결 화면으로 넘어간다.

⚠️ 세트·주소·문항 수를 여기 적지 않는다. index.html 의 QUIZ_SLUG·QUIZSETS·QUIZ_LEN 에서 읽는다.
   canonical 은 랜딩으로 건다 — 점수 페이지 33장이 따로 색인되면 얇은 중복 문서가 된다.

사용: python tools/make_quiz_share_pages.py   (퀴즈 세트나 공유 이미지를 바꿨을 때)
"""
import html
import io
import os
import re
import struct
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import home_src as HS  # noqa: E402  (홈 스크립트 읽기 입구 — 백로그 10)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.agongmap.co.kr'

PAGE = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>%(title)s %(sc)d점 · 같은 문제로 도전 | 아공맵</title>
<link rel="canonical" href="%(landing)s">
<meta name="description" content="친구가 %(title)s에서 %(sc)d/%(n)d점을 받았습니다. 같은 %(n)d문항으로 도전해 보세요.">
<meta property="og:type" content="website">
<meta property="og:title" content="%(emoji)s 친구의 %(title)s 점수는 %(sc)d/%(n)d점">
<meta property="og:description" content="같은 %(n)d문항으로 도전해 보세요. 2지선다, 즉시 채점·해설.">
<meta property="og:url" content="%(url)s">
<meta property="og:image" content="%(img)s">
<meta property="og:image:width" content="%(w)d">
<meta property="og:image:height" content="%(h)d">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="/app.css">
</head><body>
<main class="wrap" style="max-width:560px;margin:14vh auto;text-align:center;padding:0 20px">
<h1 style="font-size:22px">%(emoji)s %(title)s %(sc)d/%(n)d점</h1>
<p style="color:var(--muted);line-height:1.7">친구가 받은 점수입니다. 같은 문제로 도전하는 화면으로 이동합니다.</p>
<p style="margin-top:22px"><a href="%(landing)s" style="display:inline-block;background:var(--ink);color:var(--paper);padding:12px 22px;border-radius:3px;text-decoration:none">도전하기</a></p>
</main>
<script>
/* 대결 파라미터(?c=&s=&q=)가 있으면 홈의 대결 화면으로, 없으면 랜딩으로. 미리보기 봇은 JS 를 실행하지 않아 위 OG 를 읽는다. */
(function(){var q=location.search;
  if(/[?&]c=\\d/.test(q)&&/[?&]s=\\w/.test(q)){location.replace('/'+q);}
  else{location.replace('/%(slug)s/'+q);}
})();
</script>
</body></html>
'''


def load():
    s = HS.home_source()
    m = re.search(r'const QUIZ_SLUG=\{(.*?)\};', s)
    if not m:
        raise SystemExit('index.html 에서 QUIZ_SLUG 를 찾지 못했다')
    slug = dict(re.findall(r"(\w+):'([a-z-]+)'", m.group(1)))
    qs = s[s.find('const QUIZSETS'):s.find('const QUIZ_LEN')]
    sets = re.findall(r"\n  (\w+):\{\s*title:'([^']+)', emoji:'([^']+)'", qs)
    n = int(re.search(r'const QUIZ_LEN=(\d+);', s).group(1))
    if not sets or set(slug) != {k for k, _, _ in sets}:
        raise SystemExit('QUIZ_SLUG(%s) 와 QUIZSETS(%s) 의 세트가 다르다' % (sorted(slug), [k for k, _, _ in sets]))
    return slug, sets, n


def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('PNG 가 아니다: %s' % path)
    return struct.unpack('>II', head[16:24])


def pages():
    """[(경로, 내용)]"""
    slug, sets, n = load()
    out = []
    for key, title, emoji in sets:
        for sc in range(n + 1):
            img = os.path.join(ROOT, 'share', '%s-%d.png' % (key, sc))
            if not os.path.exists(img):
                raise SystemExit('공유 이미지가 없다: share/%s-%d.png' % (key, sc))
            w, h = png_size(img)
            body = PAGE % {
                'title': html.escape(title), 'emoji': emoji, 'sc': sc, 'n': n, 'slug': slug[key], 'w': w, 'h': h,
                'landing': '%s/%s/' % (SITE, slug[key]), 'url': '%s/%s/%d/' % (SITE, slug[key], sc),
                'img': '%s/share/%s-%d.png' % (SITE, key, sc)}
            out.append((os.path.join(ROOT, slug[key], str(sc), 'index.html'), body))
    return out


def main():
    wrote = 0
    for path, body in pages():
        old = io.open(path, encoding='utf-8').read() if os.path.exists(path) else None
        if old != body:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
            wrote += 1
    print('quiz share pages: %d개 중 %d개 갱신' % (len(pages()), wrote))


if __name__ == '__main__':
    main()
