# -*- coding: utf-8 -*-
"""퀴즈 점수별 정적 공유 페이지 — /{세트 주소}/{점수}/ (2026-09-15 점검 후속 ⑧).

카카오 공유는 점수 카드를 직접 넘기지만, 링크 복사·밴드·문자로 보내면 미리보기 봇이 JS 를 실행하지
않아 랜딩의 일반 카드만 보였다. 점수마다 og:image(share/{세트}-{점수}.png)를 가진 정적 페이지를 두고
대결 링크를 그리로 보낸다. 사람은 곧바로 홈의 대결 화면으로 넘어간다.
스크립트가 늦게 도는 느린 망에서 잠깐 보이는 폴백 화면도 다른 손 페이지와 같은 틀(먹색 칩·문서 h1 토큰·공용 푸터
site_nav.HAND_FOOTER)이다(2026-11-07 디자인 검수 hand-11 — 예전엔 22px 제목과 단추뿐이었다). 탭바는 되돌리는 화면이라 싣지 않는다.

⚠️ 세트·주소·문항 수를 여기 적지 않는다. home-quiz.js 의 QUIZ_SLUG·QUIZSETS·QUIZ_LEN 에서(home_src 경유) 읽는다.
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
import robots_meta as RM  # noqa: E402  (검색 로봇 메타 정본 — 홈 마케팅 검수 D2)
import site_nav as N  # noqa: E402  (손 페이지 공용 푸터 정본 — 2026-11-07 디자인 검수 hand-11)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.agongmap.co.kr'

PAGE = '''<!doctype html>
<html lang="ko"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
%(robots)s
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
<meta name="twitter:card" content="%(tw)s">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="stylesheet" href="/app.css">
<style>.chip{display:inline-block;font-size:13px;font-weight:600;color:#fff;background:var(--brand);padding:6px 16px;margin-bottom:18px}
.sfoot{text-align:center}</style>
</head><body>
<main class="wrap" style="max-width:560px;margin:14vh auto 0;text-align:center;padding:0 20px">
<div class="chip">%(title)s</div>
<h1 style="font-size:var(--h1-doc);line-height:1.3">친구의 점수 %(sc)d/%(n)d점</h1>
<p style="color:var(--ink2);line-height:1.7;margin-top:12px">친구가 받은 점수입니다. 같은 문제로 도전하는 화면으로 이동합니다.</p>
<p style="margin-top:22px"><a href="%(landing)s" style="display:inline-block;background:var(--brand);color:#fff;font-size:17px;font-weight:600;padding:14px 26px;border-radius:3px;text-decoration:none">같은 문제로 도전하기</a></p>
</main>
%(footer)s
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
        raise SystemExit('홈 스크립트(home-quiz.js, home_src 경유)에서 QUIZ_SLUG 를 찾지 못했다')
    slug = dict(re.findall(r"(\w+):'([a-z-]+)'", m.group(1)))
    qs = s[s.find('const QUIZSETS'):s.find('const QUIZ_LEN')]
    sets = re.findall(r"\n  (\w+):\{\s*title:'([^']+)', emoji:'([^']+)'", qs)
    n = HS.quiz_len(s)        # 문항 수 정본 읽기는 home_src 한 곳(전수리뷰 P-9)
    if not sets or set(slug) != {k for k, _, _ in sets}:
        raise SystemExit('QUIZ_SLUG(%s) 와 QUIZSETS(%s) 의 세트가 다르다' % (sorted(slug), [k for k, _, _ in sets]))
    return slug, sets, n


def png_size(path):
    with open(path, 'rb') as f:
        head = f.read(24)
    if head[:8] != b'\x89PNG\r\n\x1a\n':
        raise SystemExit('PNG 가 아니다: %s' % path)
    return struct.unpack('>II', head[16:24])


def twitter_card(w, h):
    """트위터(X) 카드 종류 — 큰 그림(summary_large_image)은 2:1 로 잘려 보이므로, 정사각형에 가까운 점수 카드(800x800)는 작은 정사각형
    카드(summary)로 둔다(전수리뷰 P 묶음 overflow — 예전엔 800x800 카드에 summary_large_image 를 달아 가운데 띠만 보였다)."""
    return 'summary_large_image' if w >= 1.5 * h else 'summary'


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
                'footer': N.HAND_FOOTER, 'tw': twitter_card(w, h), 'robots': RM.TAG, 'title': html.escape(title), 'emoji': emoji, 'sc': sc, 'n': n, 'slug': slug[key], 'w': w, 'h': h,
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
