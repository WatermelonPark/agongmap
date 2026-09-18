# -*- coding: utf-8 -*-
"""발행이 확인된 알림 이슈를 닫는다.

발행일 알림(.github/workflows/write-reminder.yml)이 만든 이슈는 사람이 닫아야
"발행했다"는 기록이 됐다. 주 2회 클릭이 쌓이면 결국 안 닫게 되고, 그러면
열린 이슈 목록이 신호가 아니라 잡음이 된다(2026-08-30에 4건이 밀려 있었다).

그래서 블로그 RSS로 실제 발행을 확인해 닫는다. **기록은 그대로 남긴다** —
닫기 전에 어떤 글이 그 이슈를 해소했는지 댓글로 적는다.

⚠️ 보수적으로 판단한다. 틀려서 안 쓴 글을 썼다고 닫으면 그 회차가 조용히
사라진다. 그래서:
  · 제목이 아니라 **카테고리**로 맞춘다(제목은 매주 바뀌고 손으로 고치기도 한다)
  · 이슈의 예정일 **이후에** 올라온 글만 인정한다
  · 글 하나는 이슈 하나만 닫는다(주간 이슈가 둘 밀려 있는데 글은 하나면 하나만)
  · RSS를 못 읽거나 gh가 없으면 아무것도 안 닫고 끝낸다

사용:
  python tools/close_published_issues.py            # 실제로 닫는다
  python tools/close_published_issues.py --dry-run  # 무엇을 닫을지만 보여준다
"""
import datetime
import json
import re
import subprocess
import sys
import urllib.request

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

# 2026-09-11 저장소 이름 변경(aptweather → agongmap). 깃헙이 옛 이름을 영구
# 리다이렉트해 줘서 당장은 옛 값으로도 돌지만, 리다이렉트에 기대면 다음 사람이
# 저장소를 못 찾는다. 정식 이름을 적는다.
REPO = 'WatermelonPark/agongmap'
RSS = 'https://rss.blog.naver.com/startupbd.xml'

# 알림 이슈의 '종류' → 블로그 카테고리. 카테고리로 맞추는 이유는 제목과 달리
# 발행할 때 바뀌지 않기 때문이다.
KIND_TO_CATEGORY = {
    '주간 시세': '주간 아파트 시세',
    '지역 공급': '지역별 아파트 공급',
    '사이클 이론': '부동산 사이클',
}

def norm(s):
    """눈에 보이는 글자만 남긴다.

    네이버 카테고리에는 줄바꿈 없는 공백(\xa0)이 섞여 들어온다. 화면에는
    보통 공백과 똑같이 보이는데 == 로는 다르다. 실제로 이것 때문에 발행한
    글을 '아직 발행 안 됨'으로 넘긴 적이 있다(2026-08-31).
    """
    return ' '.join((s or '').split())


MONTHS = {m: i for i, m in enumerate(
    'Jan Feb Mar Apr May Jun Jul Aug Sep Oct Nov Dec'.split(), 1)}


def fetch_posts():
    """RSS에서 (발행일, 카테고리, 제목, 주소)를 뽑는다. 실패하면 None."""
    try:
        req = urllib.request.Request(
            RSS, headers={'User-Agent': 'agongmap-publish-check/1.0'})
        raw = urllib.request.urlopen(req, timeout=25).read().decode('utf-8', 'replace')
    except Exception as e:
        print('RSS를 못 읽었다 — 아무것도 닫지 않는다: %s' % e)
        return None
    out = []
    for item in re.findall(r'<item>(.*?)</item>', raw, re.S):
        def pick(tag, cdata=True):
            pat = (r'<%s><!\[CDATA\[(.*?)\]\]></%s>' if cdata else r'<%s>(.*?)</%s>')
            m = re.search(pat % (tag, tag), item, re.S)
            return m.group(1).strip() if m else ''
        pub = re.search(r'<pubDate>(.*?)</pubDate>', item, re.S)
        d = None
        if pub:
            m = re.search(r'(\d{1,2})\s+(\w{3})\s+(\d{4})', pub.group(1))
            if m and m.group(2) in MONTHS:
                d = datetime.date(int(m.group(3)), MONTHS[m.group(2)], int(m.group(1)))
        url = re.search(r'<guid>(.*?)</guid>', item, re.S)
        if d:
            out.append(dict(date=d, cat=norm(pick('category')),
                            title=pick('title'),
                            url=url.group(1).strip() if url else ''))
    return out


# 알림 이슈 제목 → (예정일, 종류). 제목이 곧 메일 제목이라 2026-09-17 에 사람이 읽는
# 문장으로 바꿨다. 그 전에 만들어져 아직 열려 있는 이슈도 닫아야 하므로 옛 형식도 받는다.
PATTERNS = (
    re.compile(r'오늘 발행할 글:\s*(?P<kind>.+?)\s*\((?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})\)\s*$'),
    re.compile(r'\[발행\]\s+(?P<y>\d{4})-(?P<m>\d{2})-(?P<d>\d{2})\s+(?P<kind>.+?)\s*$'),
)


def parse_title(title):
    """알림 이슈 제목에서 (예정일, 종류)를 읽는다. 알림 이슈가 아니면 None."""
    for pat in PATTERNS:
        m = pat.search(title or '')
        if m:
            return (datetime.date(int(m.group('y')), int(m.group('m')), int(m.group('d'))),
                    m.group('kind'))
    return None


def done_title(kind, due):
    """닫을 때 바꿔 두는 제목 — '닫힘' 메일의 제목이 된다."""
    return '✅ 발행 확인됨: %s (%s) · 하실 일 없음' % (kind, due.isoformat())


def open_issues():
    try:
        r = subprocess.run(
            ['gh', 'issue', 'list', '--repo', REPO, '--state', 'open',
             '--limit', '50', '--json', 'number,title'],
            capture_output=True, text=True, timeout=60, encoding='utf-8')
    except Exception as e:
        print('gh 실행 실패: %s' % e)
        return None
    if r.returncode != 0:
        print('gh 오류: %s' % (r.stderr or '').strip()[:200])
        return None
    out = []
    for it in json.loads(r.stdout or '[]'):
        got = parse_title(it['title'])
        if not got:
            continue                      # 알림 이슈가 아니면 건드리지 않는다
        due, kind = got[0], norm(got[1])
        cat = norm(KIND_TO_CATEGORY.get(kind, ''))
        if not cat:
            continue
        out.append(dict(n=it['number'], kind=kind, cat=cat, due=due, title=it['title']))
    out.sort(key=lambda x: x['due'])      # 오래된 것부터 — 글 하나에 이슈 하나
    return out


def match(posts, issues):
    """[(이슈, 글)] — 같은 카테고리이고 발행일이 예정일 이후인 가장 이른 글 하나. 글 하나에 이슈 하나.

    예정일 조건을 빼면 지난주 주간 글이 이번 주 이슈를 닫고, 카테고리 조건을 빼면 주간 글이 지역 이슈를
    닫는다 — 둘 다 시험으로 고정한다(리뷰 09-18 23번).
    """
    used, out = set(), []
    for iss in issues:
        cand = [p for p in posts
                if p['cat'] == iss['cat'] and p['date'] >= iss['due'] and p['url'] not in used]
        if not cand:
            continue
        cand.sort(key=lambda p: p['date'])
        used.add(cand[0]['url'])
        out.append((iss, cand[0]))
    return out


def note_record(n, record, title):
    """발행 기록을 이슈 본문 끝에 덧붙이고 제목을 바꾼다. 실패해도 닫기는 계속한다."""
    try:
        r = subprocess.run(['gh', 'issue', 'view', str(n), '--repo', REPO, '--json', 'body'],
                           capture_output=True, text=True, timeout=60, encoding='utf-8')
        if r.returncode != 0:
            # 본문을 못 읽었으면 본문은 건드리지 않는다 — 빈 값 위에 기록을 쓰면 점검 체크리스트가
            # 지워진다(리뷰 09-18 23번). 제목만 바꾼다.
            args = ['gh', 'issue', 'edit', str(n), '--repo', REPO, '--title', title]
        else:
            old = json.loads(r.stdout or '{}').get('body') or ''
            new = (old.rstrip() + '\n\n---\n' + record) if old else record
            args = ['gh', 'issue', 'edit', str(n), '--repo', REPO, '--title', title, '--body', new]
        r = subprocess.run(args, capture_output=True, text=True, timeout=60, encoding='utf-8')
        if r.returncode != 0:
            print('   ! 기록·제목 수정 실패: %s' % (r.stderr or '').strip()[:160])
    except Exception as e:
        print('   ! 기록·제목 수정 실패: %s' % e)


def main(argv):
    dry = '--dry-run' in argv
    posts = fetch_posts()
    if posts is None:
        return 0
    issues = open_issues()
    if issues is None:
        return 0
    if not issues:
        print('열린 알림 이슈가 없다.')
        return 0

    closed = 0
    pairs = dict((iss['n'], p) for iss, p in match(posts, issues))
    for iss in issues:
        p = pairs.get(iss['n'])
        if p is None:
            print('· #%d %s %s — 아직 발행 안 됨' % (iss['n'], iss['due'], iss['kind']))
            continue
        body = ('✅ 발행 확인 — %s\n\n**%s**\n%s\n\n'
                '이 이슈는 블로그 RSS에서 발행이 확인되어 자동으로 닫혔습니다'
                '(`tools/close_published_issues.py`). 카테고리와 발행일로 맞춘 것이라,'
                ' 다른 글이 잘못 잡혔다면 다시 열어 주세요.'
                % (p['date'], p['title'], p['url']))
        print('%s #%d %s %s → %s' % ('[dry]' if dry else '닫음', iss['n'],
                                     iss['due'], iss['kind'], p['title'][:40]))
        if dry:
            continue
        # ⚠️ 코멘트를 달고 닫으면 메일이 두 통 간다(코멘트 + 닫힘). 기록은 본문 끝에
        #    덧붙이고(본문·제목 수정은 알림을 만들지 않는다) 닫기만 한다 — 메일은 '닫힘'
        #    한 통이고, 그 제목이 '발행 확인됨'이 되도록 제목을 먼저 바꾼다.
        note_record(iss['n'], body, done_title(iss['kind'], iss['due']))
        r = subprocess.run(['gh', 'issue', 'close', str(iss['n']), '--repo', REPO],
                           capture_output=True, text=True, timeout=60, encoding='utf-8')
        if r.returncode != 0:
            print('   ! 닫기 실패: %s' % (r.stderr or '').strip()[:160])
            # 제목을 먼저 바꿔 둔 상태라, 되돌리지 않으면 다음 회차에 알림 이슈로 인식되지 않아
            # '발행 확인됨' 제목으로 영원히 열려 있다(리뷰 09-18 23번).
            subprocess.run(['gh', 'issue', 'edit', str(iss['n']), '--repo', REPO, '--title', iss['title']],
                           capture_output=True, text=True, timeout=60, encoding='utf-8')
        else:
            closed += 1
    print('\n%d건 닫음.' % closed if not dry else '\n(dry-run — 아무것도 닫지 않았다)')
    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
