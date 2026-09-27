# -*- coding: utf-8 -*-
"""블로그 공개 카운터 기록·발행 효과 표(tools/blog_counter.py).

무엇을 깨뜨리면 빨개지나(각각 실제로 확인):
  - _json 에서 `)]}',` 접두어 떼기를 지우면 → 방문자 읽기 시험
  - 평소 방문자를 중앙값 대신 평균(statistics.mean)으로 바꾸면 → 피드에 걸린 날 시험
  - 기록 없는 날을 None 대신 0 으로 채우면 → 빈 날 시험
  - 같은 날 여러 번 기록했을 때 늦은 기록 대신 첫 기록을 쓰면 → 하루 끝 값 시험
픽스처: 2026-09-27 실제 응답의 모양(BlogInfo 는 `)]}',` 줄 + JSON, post-list 는 addDate 밀리초·readCount null)을
줄여 재현한다. 네트워크는 쓰지 않는다.
"""
import datetime
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import blog_counter as B  # noqa: E402
import kst  # noqa: E402

INFO = (")]}',\n" + json.dumps({'result': {'blogId': 'startupbd', 'dayVisitorCount': 3,
                                           'totalVisitorCount': 72792, 'subscriberCount': 199}}))


def _ms(iso):
    d = datetime.datetime.fromisoformat(iso + 'T21:00:00').replace(tzinfo=kst.KST)
    return int(d.timestamp() * 1000)


def _posts(*rows):
    return json.dumps({'result': {'items': [
        {'logNo': no, 'titleWithInspectMessage': t, 'addDate': _ms(d), 'sympathyCnt': 0,
         'commentCnt': 0, 'shareCnt': s, 'readCount': None} for no, t, d, s in rows]}})


def _line(date, day, posts=(), hh='23:55:00'):
    return {'ts': '%sT%s+09:00' % (date, hh), 'date': date, 'day': day, 'total': 0, 'subs': 0,
            'posts': [{'no': no, 'title': t, 'date': d, 'sym': 0, 'cmt': 0, 'share': s}
                      for no, t, d, s in posts]}


def test_reads_visitors_behind_the_guard_prefix():
    assert B.parse_info(INFO) == {'day': 3, 'total': 72792, 'subs': 199}


def test_record_appends_one_line(tmp_path):
    now = datetime.datetime(2026, 9, 27, 14, 55, tzinfo=datetime.timezone.utc)   # 23:55 KST
    got = {B.INFO_URL: INFO, B.POSTS_URL: _posts((224423460593, '주간', '2026-09-27', 0))}
    p = tmp_path / 'logs' / 'c.jsonl'
    B.record(str(p), now=now, get=got.__getitem__)
    ln = B.load(str(p))
    assert len(ln) == 1 and ln[0]['date'] == '2026-09-27' and ln[0]['day'] == 3
    assert ln[0]['posts'][0]['date'] == '2026-09-27'


def test_feed_spike_in_baseline_does_not_sink_next_post():
    """대구 편처럼 하루 100명대가 기준 기간에 섞여도 평소 값은 3 이어야 한다."""
    days = ['2026-09-%02d' % d for d in range(10, 21)]
    vis = [3, 3, 3, 120, 3, 3, 3, 13, 8, 5, 3]    # 13일에 피드, 17일 발행
    post = (1, '세종 편', '2026-09-17', 2)
    lines = [_line(d, v, [post]) for d, v in zip(days, vis)]
    r = B.post_effects(lines, today='2026-09-20')[0]
    assert r['base'] == 3
    assert r['excess'] == [10, 5, 2, 0]


def test_missing_day_is_unknown_not_zero():
    lines = [_line('2026-09-%02d' % d, 3, [(1, '글', '2026-09-17', 0)]) for d in range(10, 18)]
    lines.append(_line('2026-09-19', 9, [(1, '글', '2026-09-17', 0)]))     # 18일 기록 없음
    r = B.post_effects(lines, today='2026-09-20')[0]
    assert r['excess'][1] is None and r['excess'][2] == 6


def test_latest_record_of_the_day_wins():
    lines = [_line('2026-09-17', 2, hh='09:00:00'), _line('2026-09-17', 11, hh='23:55:00')]
    assert B.daily_visitors(lines) == {'2026-09-17': 11}
