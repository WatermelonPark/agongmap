# -*- coding: utf-8 -*-
"""IndexNow 핑 — 네이버·빙에 변경된 URL의 재크롤을 즉시 요청한다.

키 파일: 저장소 루트의 {key}.txt (사이트에도 배포됨), 키 값은 .indexnow_key(비커밋).
사용: python tools/ping_indexnow.py --changed [REF]   (배치: 이번 커밋에서 sitemap lastmod 가 바뀐 주소만. REF 기본 HEAD~1)
      python tools/ping_indexnow.py --sitemap         (sitemap.xml의 전체 URL 제출 — 사람이 손으로)
      python tools/ping_indexnow.py [url ...]         (인자 없으면 기본 URL 몇 개)

--changed (홈 마케팅 검수 D1, 2026-09-27): 배치는 성공한 회차마다 sitemap 32개 주소를 전부 보냈는데(--sitemap) 네이버
색인은 08월 사본에 머물러 있었다. 안 바뀐 주소까지 매일 보내면 '매일 전부 갱신'이라는 틀린 신호가 되고 정작 바뀐 주소가
묻힌다. 그래서 배치 커밋(HEAD)과 그 부모(REF)의 sitemap.xml 을 비교해 lastmod 가 바뀐 loc·새로 생긴 loc·빠진 loc 만 보낸다
(IndexNow 규격은 추가·갱신·삭제된 URL 을 모두 제출하라고 한다 — 빠진 주소를 알려야 검색엔진이 404·이전을 빨리 본다).
바뀐 주소가 없으면 보내지 않는다. 비교 기준을 커밋 이력(REF)으로 잡는 까닭: 배치 커밋은 pull --rebase 뒤에 푸시되므로
HEAD~1 은 곧 '이 커밋 전의 라이브 사이트'다. 생성 전에 사본을 떠 두는 방식은 셸 단계가 하나 더 늘고 러너가 바뀌면 사본이 없다.

손으로 관리하는 페이지(/about/·/faq/ 등, 요청서 SEO-3 권고 ②)도 같은 길로 간다: 그 파일을 고친 커밋이 main 에 들어가면
다음 배치의 make_indicator_pages.hand_lastmods() 가 sitemap lastmod 를 그 커밋 날짜로 옮기고, 그 배치 커밋에서 이 모드가
그 주소를 보낸다(하루 안쪽 지연, 배치가 멈춘 동안은 함께 멈춘다).

결과는 **한 줄**로 표준 출력에 찍는다(배치가 rep 으로 배치 리포트에 그대로 싣는다). 보낸 주소 목록은 표준 오류로.
  ✅ IndexNow 제출 HTTP 200 · 바뀐 주소 3개
  ✅ IndexNow 보낼 주소 없음 — sitemap lastmod 변화 없음
  ⚠️ IndexNow 실패 — HTTP 403 · 바뀐 주소 3개 · 색인 지연만 발생(데이터는 정상)
실패 줄은 늘 'IndexNow 실패'를 담는다 — format_batch_report 가 이 말로 사람의 문장을 고른다. 실패면 종료 코드 1.
표준 라이브러리만 쓴다(설치 없이 돈다).
"""
import glob
import io
import json
import os
import re
import subprocess
import sys
import urllib.error
import urllib.request

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ENDPOINT = 'https://api.indexnow.org/indexnow'
DEFAULT = ['/', '/weekly/', '/faq/', '/burini-test/', '/cycle/']
OK_CODES = (200, 202)   # 202 = 받았고 키 확인은 나중에(IndexNow 규격)
TAIL = '색인 지연만 발생(데이터는 정상)'


def host(root=ROOT):
    """정식 도메인(CNAME). /feed.xml(make_feed)과 같은 출처."""
    return io.open(os.path.join(root, 'CNAME'), encoding='utf-8').read().strip().split()[0]


def site(root=ROOT):
    return 'https://' + host(root)


_URL = re.compile(r'<url>(.*?)</url>', re.S)
_LOC = re.compile(r'<loc>\s*(.*?)\s*</loc>', re.S)
_LASTMOD = re.compile(r'<lastmod>\s*(.*?)\s*</lastmod>', re.S)


def sitemap_entries(xml):
    """sitemap 문자열 → [(loc, lastmod)] (문서 순서). lastmod 가 없는 항목은 ''."""
    out = []
    for block in _URL.findall(xml or ''):
        m = _LOC.search(block)
        if not m:
            continue
        lm = _LASTMOD.search(block)
        out.append((m.group(1), lm.group(1) if lm else ''))
    return out


def changed_locs(old_xml, new_xml):
    """이번에 알릴 주소 — 새 sitemap 순서로 (lastmod 가 바뀐 loc, 새 loc), 그 뒤에 빠진 loc(옛 순서).

    그대로인 loc 는 보내지 않는다. old_xml 이 비어 있으면(첫 sitemap) 새 sitemap 의 모든 loc 가 새 주소다.
    """
    old = dict(sitemap_entries(old_xml))
    new = sitemap_entries(new_xml)
    seen = {loc for loc, _ in new}
    out = [loc for loc, lm in new if loc not in old or old[loc] != lm]
    out += [loc for loc in old if loc not in seen]
    return out


def read_key(root=ROOT):
    keyfile = os.path.join(root, '.indexnow_key')
    if os.path.exists(keyfile):
        return io.open(keyfile).read().strip()
    # ⚠️ IndexNow 키는 설계상 공개값이다 — 사이트 루트의 {key}.txt를 검색엔진이
    # 직접 받아 소유권을 확인한다. 그래서 비커밋 .indexnow_key가 없으면 커밋된
    # 키 파일에서 읽는다. 이게 없어서 클라우드 배치에는 핑이 아예 없었고,
    # 2026-08-06 URL 전면 교체(생활권 31곳 → 시도 20곳)가 색인 요청 없이 나갔다.
    cand = sorted(f for f in glob.glob(os.path.join(root, '*.txt'))
                  if len(os.path.basename(f)) == 36 and
                  all(ch in '0123456789abcdef' for ch in os.path.basename(f)[:32]))
    return os.path.basename(cand[0])[:32] if cand else None


def git_show(ref, path, root=ROOT):
    """REF:path 의 내용. REF 가 없으면 None, REF 는 있는데 그 파일이 없으면 ''(첫 sitemap)."""
    def run(*args):
        return subprocess.run(['git'] + list(args), cwd=root, capture_output=True, timeout=30,
                              encoding='utf-8', errors='replace')
    try:
        if run('rev-parse', '--verify', '--quiet', ref + '^{commit}').returncode != 0:
            return None
        r = run('show', '%s:%s' % (ref, path))
    except Exception:
        return None
    return r.stdout if r.returncode == 0 else ''


def submit(urls, key, root=ROOT, opener=urllib.request.urlopen):
    """IndexNow 에 보낸다 → (성공, 한 줄). opener 는 시험용."""
    h = host(root)
    payload = json.dumps({'host': h, 'key': key, 'keyLocation': 'https://%s/%s.txt' % (h, key),
                          'urlList': urls}).encode('utf-8')
    req = urllib.request.Request(ENDPOINT, data=payload,
                                 headers={'Content-Type': 'application/json; charset=utf-8'})
    try:
        with opener(req, timeout=30) as r:
            code = r.status
    except urllib.error.HTTPError as e:
        code = e.code
    except Exception as e:  # noqa: BLE001 — 연결 오류·시간 초과. 데이터 배포를 막지 않는다
        return False, '⚠️ IndexNow 실패 — 연결 오류(%s) · 주소 %d개 · %s' % (type(e).__name__, len(urls), TAIL)
    if code in OK_CODES:
        return True, '✅ IndexNow 제출 HTTP %d · 주소 %d개' % (code, len(urls))
    return False, '⚠️ IndexNow 실패 — HTTP %d · 주소 %d개 · %s' % (code, len(urls), TAIL)


def changed_mode(ref, root=ROOT, opener=urllib.request.urlopen):
    """--changed 의 본체 → (성공, 한 줄, 보낸 주소)."""
    old = git_show(ref, 'sitemap.xml', root)
    if old is None:
        return False, '⚠️ IndexNow 실패 — 비교 기준 %s 를 찾지 못함 · %s' % (ref, TAIL), []
    p = os.path.join(root, 'sitemap.xml')
    new = io.open(p, encoding='utf-8').read() if os.path.exists(p) else ''
    if not sitemap_entries(new):
        return False, '⚠️ IndexNow 실패 — sitemap.xml 에 주소가 없음 · %s' % TAIL, []
    pre = site(root) + '/'
    changed = changed_locs(old, new)
    urls = [u for u in changed if u.startswith(pre) or u == site(root)]
    # 정식 도메인(CNAME) 밖의 loc 은 IndexNow 가 통째로 거절한다(host 불일치 422). 생성기의 SITE 상수와 CNAME 이 갈린 것이라
    # '보낼 주소 없음'으로 조용히 넘기면 안 된다 — 나머지는 보내되 결과 줄을 ⚠️ 로 남긴다(D1 검토).
    foreign = len(changed) - len(urls)
    warn = ('sitemap 주소 %d개가 정식 도메인 %s 밖이라 빼고' % (foreign, host(root))) if foreign else ''
    if not urls:
        if warn:
            return False, '⚠️ IndexNow 실패 — %s 보낼 주소가 없음 · %s' % (warn, TAIL), []
        return True, '✅ IndexNow 보낼 주소 없음 — sitemap lastmod 변화 없음', []
    key = read_key(root)
    if not key:
        return False, '⚠️ IndexNow 실패 — 키 파일 없음 · 바뀐 주소 %d개 · %s' % (len(urls), TAIL), urls
    ok, line = submit(urls, key, root, opener)
    line = line.replace('주소 %d개' % len(urls), '바뀐 주소 %d개' % len(urls))
    if warn:
        return False, '⚠️ IndexNow 실패 — %s 나머지를 보냄(%s) · %s' % (
            warn, line.split(' ', 1)[1].replace(' · ' + TAIL, ''), TAIL), urls
    return ok, line, urls


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if args and args[0] == '--changed':
        ok, line, urls = changed_mode(args[1] if len(args) > 1 else 'HEAD~1')
        for u in urls:
            sys.stderr.write('  %s\n' % u)
        print(line)
        return 0 if ok else 1
    key = read_key()
    if not key:
        print('indexnow skip: 키 파일 없음')
        return 0
    if args and args[0] == '--sitemap':
        sm = os.path.join(ROOT, 'sitemap.xml')
        if not os.path.exists(sm):
            print('indexnow skip: sitemap.xml 없음')
            return 0
        urls = [loc for loc, _ in sitemap_entries(io.open(sm, encoding='utf-8').read())]
        if not urls:
            print('indexnow skip: sitemap.xml에 URL이 없음')
            return 0
    else:
        urls = [site() + u for u in (args or DEFAULT)]
    ok, line = submit(urls, key)
    print(line)
    return 0 if ok else 1


if __name__ == '__main__':
    try:
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    except Exception:
        pass
    sys.exit(main())
