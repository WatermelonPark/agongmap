# -*- coding: utf-8 -*-
"""최신 주간 해설 글(네이버 블로그)을 RSS 에서 읽어 둔다 — 사이트에서 블로그로 가는 연결(홈 마케팅 검수 B5).

2026-09-27 대표 확인: 사이트 → 블로그 링크를 허용하고, 표기는 블로그 이름 없이 '네이버 블로그'만 쓴다.
사이트 방문자는 매주 나오는 해석 글의 존재를 몰랐고(RET-4), 사이트 어디에도 블로그 링크가 없었다(SEO-8·IA-9).

흐름
  1. 배치 fetch 잡이 데이터 갱신 뒤, split_data **앞에서** 이 도구를 돌린다(`python tools/blog_feed.py`).
     RSS 에서 '주간 아파트 시세' 카테고리의 가장 새 글 하나를 tools/data/blog_latest.json 에 적는다.
  2. split_data 가 그 글을 ADV.blog 로 data-core 에 싣고(홈 주간 구역이 읽는다), make_weekly_page 가 /weekly/ 하단에
     굽는다. 둘 다 pick() 하나로 '보여 줄지·어떤 말로'를 정한다 — 홈과 /weekly/ 가 다른 글을 가리키지 않게.

⚠️ 못 읽으면 칸이 빠지기만 한다. 이 도구는 **언제나 0 으로 끝난다**(RSS 장애로 데이터 갱신을 멈추지 않는다).
   못 읽은 회차에는 파일을 그대로 둔다 — 지난 회차에 읽은 글은 여전히 실제로 있는 글이다. 너무 오래된 글은
   pick() 이 걸러 칸을 뺀다(이번 주 발표일 7일 전보다 앞선 글).
⚠️ 알림을 약속하지 않는다. '매주 금요일' 같은 요일도 적지 않는다(RSS 상 8월 3·4주 글이 8/30 에 함께 올라갔다).
⚠️ 글 주소는 우리 블로그 주소(BLOG_HOME/…)만 받는다 — RSS 가 엉뚱한 주소를 주어도 사이트가 남의 곳을 가리키지 않게.

RSS 주소·카테고리 이름의 정본은 close_published_issues 다(발행 확인·블로그 초안 도구와 같은 값). 표준 라이브러리만 쓴다
(fetch 잡에는 pip 가 없다).

사용: python tools/blog_feed.py
"""
import datetime
import io
import threading
import json
import os
import re
import sys

try:
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
except Exception:
    pass

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import close_published_issues as CP  # noqa: E402  (RSS 주소·카테고리 이름·파서의 정본)
import weekly_release as WR  # noqa: E402  (주차 라벨 week_label·발표 간격 PUB_OFFSET 의 정본 — 표준 라이브러리만 쓴다)

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
FILE = os.path.join(ROOT, 'tools', 'data', 'blog_latest.json')

CATEGORY = CP.KIND_TO_CATEGORY['주간 시세']


def blog_home(rss):
    """RSS 주소 → 블로그 첫 화면 주소. 모양이 다르면 None — ⚠️ 예외를 던지지 않는다(검토 09-27). 이 모듈은 split_data·
    make_weekly_page 가 불러오는데, 예전 판은 여기서 SystemExit(= BaseException, split 의 `except Exception` 이 못 잡는다)을
    던져 RSS 주소 한 줄 때문에 수집 잡·생성기가 죽을 수 있었다. None 이면 글도 링크도 없이 칸만 빠진다."""
    m = re.match(r'^https://rss\.blog\.naver\.com/([A-Za-z0-9_-]+)\.xml$', rss or '')
    return ('https://blog.naver.com/' + m.group(1)) if m else None


BLOG_HOME = blog_home(CP.RSS)   # 푸터·/weekly/ 의 '매주 해설 글' 링크도 이 값이다(None 이면 링크를 굽지 않는다)
LABEL = '네이버 블로그'                                   # 대표 확인(09-27): 블로그 이름 없이 이 말만
FRESH_DAYS = 7          # 이번 주 발표일보다 이만큼 앞선 글까지 보여 준다(= 지난주 글). 그보다 오래되면 칸을 뺀다
LEAD_NOW, LEAD_PREV = '이번 주 해석 읽기', '지난주 해석 읽기'
HOME_TEXT = '매주 해설 글'   # 블로그 첫 화면 링크 이름(홈 푸터·/weekly/). '매주 금요일'처럼 요일을 약속하지 않는다
# 해석 글 칸 옆 한 줄(RET-4 A안). 알림을 약속하지 않는다 — 네이버 이웃 기능이 하는 일을 적을 뿐이다. /weekly/(blog_html)만 쓴다 —
# 홈 주간 구역의 같은 줄(ADV.blog.note)은 뺐다(2026-09-28 대표 결정 — 작은 글씨 정리).
NEIGHBOR = '블로그 이웃이 되면 새 글이 이웃 새 글 목록에 올라옵니다.'
WALL_SECONDS = 60   # RSS 읽기 벽시계 상한(소켓 타임아웃은 읽기마다 25초라 느린 응답이 이어지면 끝이 없다). 워크플로 timeout 90 이 바깥 상한


def ours(url):
    return bool(BLOG_HOME) and isinstance(url, str) and url.startswith(BLOG_HOME + '/') and '"' not in url and '<' not in url


def latest_weekly(posts):
    """[{date, cat, title, url}] → 주간 카테고리의 가장 새 글 {'date': 'YYYY-MM-DD', 'title', 'url'}. 없으면 None."""
    cat = CP.norm(CATEGORY)
    cand = [p for p in posts or () if CP.norm(p.get('cat')) == cat and ours(p.get('url'))
            and (p.get('title') or '').strip() and p.get('date')]
    if not cand:
        return None
    p = max(cand, key=lambda x: x['date'])
    d = p['date']
    return {'date': d.isoformat() if hasattr(d, 'isoformat') else str(d),
            'title': ' '.join(p['title'].split()), 'url': p['url'].strip()}


def read(path=None):
    """저장해 둔 최신 주간 글. 파일이 없거나 모양이 다르면 None."""
    path = path or FILE
    try:
        w = json.loads(io.open(path, encoding='utf-8').read()).get('weekly')
    except Exception:
        return None
    if not isinstance(w, dict) or not ours(w.get('url')) or not w.get('title') \
            or not re.match(r'^\d{4}-\d{2}-\d{2}$', str(w.get('date') or '')):
        return None
    return w


def _d(iso):
    return datetime.date(*(int(x) for x in iso.split('-')))


_WEEK_LABEL = re.compile(r'(\d{1,2})월\s*(%s)\s*주' % '|'.join(WR.ORDINALS))


def title_week(title):
    """글 제목 속 주차 라벨('9월 셋째 주') — 공백을 한 칸으로 맞춘 모양. 없으면 None."""
    m = _WEEK_LABEL.search(title or '')
    return ('%d월 %s 주' % (int(m.group(1)), m.group(2))) if m else None


def pick(entry, pub):
    """보여 줄 글과 그 말. pub = 최신 주간 발표일('YYYY-MM-DD', weekly_release.status(p)['pub']).

    돌려주는 것 {'lead': '이번 주 해석 읽기', 'title', 'url', 'date', 'md': '9/25', 'src': '네이버 블로그, 9/25'}
    또는 None.
    이번 주 발표일보다 FRESH_DAYS 일 넘게 앞선 글이나 없는 글은 None(칸을 뺀다). 그 밖에는:
      - 제목에 주차 라벨('(9월 셋째 주)')이 있으면 **그 라벨로** 정한다 — 이번 조사일의 라벨(weekly_release.week_label)이면
        '이번 주', 한 주 앞 조사일의 라벨이면 '지난주', 둘 다 아니면(더 옛 회차 글) None. 예전엔 게시일로만 정해, 지난 회차
        글이 이번 발표일 뒤에 올라오면(8월 3·4주 글이 8/30 에 함께 올라간 실제 사례) '이번 주 해석 읽기: …(8월 셋째 주)'를
        '8월 넷째 주' 페이지에 붙였다(전수리뷰 #27). 조사일은 발표일 − weekly_release.PUB_OFFSET 이다(status 가 그렇게 셈한다) —
        그래서 부르는 쪽(split_data·make_weekly_page)은 발표일만 넘기면 된다.
      - 라벨이 없는 제목은 게시일로 정한다: 발표일 당일·뒤면 '이번 주', 그 전이면 '지난주'.
    """
    if not entry or not pub:
        return None
    try:
        d, p = _d(entry['date']), _d(pub)
    except (ValueError, TypeError, AttributeError, KeyError):   # '2026-13-40' 처럼 모양만 맞는 날짜 — 칸만 뺀다
        return None
    if d < p - datetime.timedelta(days=FRESH_DAYS):
        return None
    tw = title_week(entry.get('title'))
    if tw:
        survey = p - datetime.timedelta(days=WR.PUB_OFFSET)
        now = WR.week_label(survey.isoformat())
        prev = WR.week_label((survey - datetime.timedelta(days=WR.WEEK)).isoformat())
        if tw == now:
            lead = LEAD_NOW
        elif tw == prev:
            lead = LEAD_PREV
        else:
            return None
    else:
        lead = LEAD_NOW if d >= p else LEAD_PREV
    md = '%d/%d' % (d.month, d.day)
    return {'lead': lead, 'title': entry['title'], 'url': entry['url'],
            'date': entry['date'], 'md': md, 'src': '%s, %s' % (LABEL, md)}


def text(b):
    """홈 주간 구역과 같은 한 줄 — '이번 주 해석 읽기: {제목} (네이버 블로그, 9/25)'. 홈 JS renderBlogLine 과 같은 모양."""
    return '%s: %s (%s)' % (b['lead'], b['title'], b['src'])


def write(entry, path=None):
    path = path or FILE
    body = json.dumps({'weekly': entry}, ensure_ascii=False, indent=1) + '\n'
    try:
        old = io.open(path, encoding='utf-8').read()
    except Exception:
        old = None
    if old != body:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        io.open(path, 'w', encoding='utf-8', newline='\n').write(body)
        return True
    return False


def _fetch_with_wall(fetch):
    """fetch() 를 WALL_SECONDS 안에서만 기다린다. 넘기거나 실패하면 None — 데몬 스레드라 남아도 프로세스는 끝난다.
    (로컬 bat 에는 셸 timeout 이 없어 도구 안에 벽시계를 둔다.)"""
    box = {}

    def run():
        try:
            box['v'] = fetch()
        except BaseException as e:   # noqa: BLE001 — 블로그 칸 때문에 데이터 갱신을 멈추지 않는다
            box['e'] = e
    t = threading.Thread(target=run, daemon=True)
    t.start()
    t.join(WALL_SECONDS)
    if t.is_alive():
        print('블로그 RSS 읽기가 %d초를 넘겨 그만둔다' % WALL_SECONDS)
        return None
    if 'e' in box:
        print('블로그 RSS 읽기 실패: %s' % box['e'])
        return None
    return box.get('v')


def main(path=None, fetch=None):
    """RSS 를 읽어 최신 주간 글을 적는다. 언제나 0 — 못 읽으면 파일을 그대로 둔다(없으면 빈 값으로 만든다)."""
    path = path or FILE
    posts = _fetch_with_wall(fetch or CP.fetch_posts)
    new = latest_weekly(posts) if posts else None
    if new is None:
        print('블로그 주간 글을 못 읽었다 — 지난 값을 그대로 둔다(칸은 오래되면 빠진다)')
        if not os.path.exists(path):
            write(None, path)        # 배치 커밋 대상 목록(git add)이 없는 파일에 걸려 죽지 않게
        return 0
    changed = write(new, path)
    print('블로그 주간 글 %s: %s (%s)' % ('갱신' if changed else '그대로', new['title'][:40], new['date']))
    return 0


if __name__ == '__main__':
    sys.exit(main())
