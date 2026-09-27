# -*- coding: utf-8 -*-
"""네이버 블로그 공개 카운터를 하루 한 번 기록하고, 글마다 발행 뒤 방문자 증가를 표로 뽑는다(로컬 전용).

왜 필요한가(2026-09-27 조회수 조사): 블로그 통계(글별 조회수·유입 경로)는 로그인해야 보여서 대표만 볼 수
있다. 그래서 "목요일 밤에 올린 주간 글이 더 읽히나", "제목 앞머리를 바꾸면 달라지나" 같은 실험을 대표가
숫자를 붙여 주기 전에는 가를 수 없었다. 로그인 없이 공개되는 값은 블로그 전체의 오늘·누적 방문자,
이웃 수, 글마다 공감·댓글·공유 수다(글별 조회수 readCount 는 공개되지 않는다 — 응답에 null).
그래서 하루 끝(23:55)에 오늘 방문자를 남기고, 글이 올라간 날부터 사흘 동안 방문자가 평소보다 얼마나
늘었는지로 글의 효과를 가늠한다.

한계(표에도 적는다): 방문자는 조회수가 아니다. 같은 날 두 글을 올리면 효과를 가를 수 없다.

  python tools/blog_counter.py record   # 오늘 값을 logs/blog-counter.jsonl 에 한 줄 덧붙인다(예약 작업)
  python tools/blog_counter.py report   # 최근 발행 글의 D0~D3 초과 방문자 표

logs/ 는 gitignore 다. 표준 라이브러리만 쓴다.
"""
import datetime
import io
import json
import os
import statistics
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import kst  # noqa: E402  (KST '오늘'의 단일 출처)

BLOG = 'startupbd'
ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LOG = os.path.join(ROOT, 'logs', 'blog-counter.jsonl')
INFO_URL = 'https://m.blog.naver.com/rego/BlogInfo.naver?blogId=%s' % BLOG
POSTS_URL = ('https://m.blog.naver.com/api/blogs/%s/post-list?categoryNo=0&itemCount=24&page=1' % BLOG)
UA = ('Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 (KHTML, like Gecko) '
      'Chrome/120.0 Mobile Safari/537.36')
BASE_DAYS = 7      # 평소 방문자 = 발행 전 7일의 중앙값
AFTER_DAYS = 4     # D0~D3
RECENT_DAYS = 21   # 이 기간에 올라간 글만 표에 싣는다


def _get(url):
    req = urllib.request.Request(url, headers={
        'User-Agent': UA, 'Referer': 'https://m.blog.naver.com/%s' % BLOG})
    with urllib.request.urlopen(req, timeout=20) as r:
        return r.read().decode('utf-8')


def _json(text):
    """BlogInfo 응답은 JSON 앞에 `)]}',` 줄이 붙어 온다(JSON 가로채기 방지 접두어). 떼고 읽는다."""
    s = text.lstrip()
    if s.startswith(")]}'"):
        s = s.split('\n', 1)[1] if '\n' in s else s[s.index(',') + 1:]
    return json.loads(s)


def parse_info(text):
    r = _json(text).get('result') or {}
    return {'day': r.get('dayVisitorCount'), 'total': r.get('totalVisitorCount'),
            'subs': r.get('subscriberCount')}


def _kst_date(ms):
    return datetime.datetime.fromtimestamp(ms / 1000.0, kst.KST).date().isoformat()


def parse_posts(text):
    items = ((_json(text).get('result') or {}).get('items')) or []
    out = []
    for it in items:
        if not it.get('logNo') or not it.get('addDate'):
            continue
        out.append({'no': it['logNo'], 'title': it.get('titleWithInspectMessage') or '',
                    'date': _kst_date(it['addDate']), 'sym': it.get('sympathyCnt') or 0,
                    'cmt': it.get('commentCnt') or 0, 'share': it.get('shareCnt') or 0})
    return out


def record(path=LOG, now=None, get=None):
    get = get or _get
    now = now or datetime.datetime.now(datetime.timezone.utc)
    line = {'ts': now.astimezone(kst.KST).isoformat(timespec='seconds'),
            'date': kst.today_iso(now)}
    line.update(parse_info(get(INFO_URL)))
    line['posts'] = parse_posts(get(POSTS_URL))
    d = os.path.dirname(path)
    if d and not os.path.isdir(d):
        os.makedirs(d)
    with io.open(path, 'a', encoding='utf-8', newline='\n') as f:
        f.write(json.dumps(line, ensure_ascii=False) + '\n')
    return line


def load(path=LOG):
    if not os.path.exists(path):
        return []
    out = []
    with io.open(path, encoding='utf-8') as f:
        for ln in f:
            ln = ln.strip()
            if ln:
                try:
                    out.append(json.loads(ln))
                except ValueError:
                    continue     # 쓰다 끊긴 줄은 건너뛴다
    return out


def daily_visitors(lines):
    """날짜별 방문자. 같은 날 여러 번 기록했으면 가장 늦은 기록(하루 끝에 가까운 값)을 쓴다."""
    last = {}
    for ln in lines:
        if ln.get('day') is None:
            continue
        if ln['date'] not in last or ln['ts'] > last[ln['date']]['ts']:
            last[ln['date']] = ln
    return {d: v['day'] for d, v in last.items()}


def _shift(iso, n):
    return (datetime.date.fromisoformat(iso) + datetime.timedelta(days=n)).isoformat()


def post_effects(lines, today=None):
    """최근 글마다 D0~D3 초과 방문자(그날 방문자 − 발행 전 7일 중앙값)와 공유 증가.

    평균이 아니라 중앙값을 쓰는 이유: 대구 편처럼 피드에 한 번 걸린 날(하루 100명대)이 기준 기간에
    섞이면 평균이 크게 올라, 다음 글의 효과가 음수로 보인다.
    기록이 없는 날은 None 이다(모르는 값을 0 으로 채우지 않는다).
    """
    if not lines:
        return []
    today = today or kst.today_iso()
    vis = daily_visitors(lines)
    latest = max(lines, key=lambda x: x['ts'])
    first_seen = {}
    for ln in sorted(lines, key=lambda x: x['ts']):
        for p in ln.get('posts') or []:
            first_seen.setdefault(p['no'], p)
    rows = []
    for p in latest.get('posts') or []:
        if p['date'] < _shift(today, -RECENT_DAYS):
            continue
        base = [vis[_shift(p['date'], -k)] for k in range(1, BASE_DAYS + 1)
                if _shift(p['date'], -k) in vis]
        med = statistics.median(base) if base else None
        ex = []
        for k in range(AFTER_DAYS):
            d = _shift(p['date'], k)
            ex.append(None if (med is None or d not in vis) else vis[d] - med)
        rows.append({'no': p['no'], 'title': p['title'], 'date': p['date'], 'base': med,
                     'excess': ex, 'share': p['share'],
                     'share_gain': p['share'] - first_seen[p['no']]['share'],
                     'same_day': sum(1 for q in latest['posts']
                                     if q['date'] == p['date'] and q['no'] != p['no'])})
    rows.sort(key=lambda r: r['date'])
    return rows


def report(lines, today=None):
    rows = post_effects(lines, today)
    if not rows:
        return '기록이 없다. 먼저 `python tools/blog_counter.py record` 가 며칠 돌아야 한다.'
    f = lambda v: '—' if v is None else ('%+d' % v if isinstance(v, int) else '%+.1f' % v)
    out = ['| 발행일 | 글 | 평소(7일 중앙값) | D0 | D1 | D2 | D3 | 공유(증가) | 같은 날 다른 글 |',
           '|---|---|---|---|---|---|---|---|---|']
    for r in rows:
        out.append('| %s | %s | %s | %s | %s(+%d) | %s |' % (
            r['date'], r['title'][:40], '—' if r['base'] is None else '%g' % r['base'],
            ' | '.join(f(v) for v in r['excess']), r['share'], r['share_gain'],
            r['same_day'] or ''))
    out.append('')
    out.append('※ 방문자는 조회수가 아니다. 같은 날 다른 글이 있으면 그 날 증가는 나눠 가진 것이다. '
               '— 는 기록이 없는 날이다.')
    return '\n'.join(out)


def main(argv):
    cmd = argv[0] if argv else 'report'
    if cmd == 'record':
        ln = record()
        print('%s 방문자 %s · 누적 %s · 이웃 %s · 글 %d건 기록' % (
            ln['date'], ln['day'], ln['total'], ln['subs'], len(ln['posts'])))
        return 0
    if cmd == 'report':
        print(report(load()))
        return 0
    raise SystemExit('record 또는 report')


if __name__ == '__main__':
    sys.exit(main(sys.argv[1:]))
