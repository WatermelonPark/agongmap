# -*- coding: utf-8 -*-
"""사이트 → 네이버 블로그 연결(홈 마케팅 검수 B5·RET-4·SEO-8·IA-9, 2026-09-27)을 고정한다.

재현하는 실제 상태: 사이트 HTML 전체에서 blog.naver.com 링크가 0건이었다. 매주 나오는 해석 글(블로그)이 있어도
사이트 방문자는 몰랐다. 배치가 RSS 에서 최신 주간 글을 읽어(blog_feed) 홈 주간 구역(ADV.blog)과 /weekly/ 하단에
같은 글·같은 말로 굽는다. 못 읽으면 칸이 빠지기만 하고 배치는 멈추지 않는다.

픽스처: 네이버 블로그 RSS 모양의 글 네 개(주간 둘·가장 새 지역 편 하나·남의 주소 주간 글 하나). 카테고리에는 실제처럼
줄바꿈 없는 공백(\\xa0)이 섞여 있다(2026-08-31 발행 확인 도구가 이것 때문에 발행 글을 놓친 적이 있다 — 공백 정리는
close_published_issues.parse_posts 가 한다). 네트워크는 쓰지 않는다.
무엇을 깨뜨리면 빨개지나는 시험마다 적었다(각각 실제로 바꿔 확인).
"""
import datetime
import importlib
import io
import time
import json
import os
import re
import shutil
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import blog_feed as BF  # noqa: E402
import close_published_issues as CP  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import split_data as S  # noqa: E402
import weekly_release as WR  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
WF = os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml')
BAT = os.path.join(ROOT, 'tools', 'run_weekly_update.bat')

WEEKLY_CAT = CP.KIND_TO_CATEGORY['주간 시세'].replace(' ', '\xa0', 1)


def _item(cat, title, url, pub):
    return ('<item><author>x</author><category><![CDATA[%s]]></category><title><![CDATA[%s]]></title>'
            '<link><![CDATA[%s?fromRss=true&trackingCode=rss]]></link><guid>%s</guid>'
            '<description><![CDATA[본문]]></description><pubDate>%s</pubDate></item>' % (cat, title, url, url, pub))


RSS = ('<?xml version="1.0" encoding="UTF-8"?><rss version="2.0"><channel><title>블로그</title>'
       + _item(CP.KIND_TO_CATEGORY['지역 공급'], '2026년 부산 아파트 공급물량 전망, 지역 편',
               BF.BLOG_HOME + '/224000000003', 'Sun, 27 Sep 2026 09:00:00 +0900')
       + _item(WEEKLY_CAT, '[한국부동산원] 주간 아파트가격 동향(9월 셋째 주) | 서울 +0.13% 전국 +0.09%',
               BF.BLOG_HOME + '/224000000002', 'Fri, 25 Sep 2026 08:30:00 +0900')
       + _item(WEEKLY_CAT, '남의 주소로 온 주간 글', 'https://example.com/x/1', 'Sat, 26 Sep 2026 08:30:00 +0900')
       + _item(WEEKLY_CAT, '[한국부동산원] 주간 아파트가격 동향(9월 둘째 주) | 서울 +0.10% 전국 +0.07%',
               BF.BLOG_HOME + '/224000000001', 'Fri, 19 Sep 2026 08:30:00 +0900')
       + '</channel></rss>')


def test_latest_weekly_post_is_picked_from_the_feed():
    """주간 카테고리의 가장 새 글, 그중 우리 블로그 주소만.

    변이: latest_weekly 의 카테고리 조건을 지우면 가장 새 글인 9/27 지역 편이, ours() 조건을 지우면 남의 주소 글(9/26)이
          뽑혀 빨개진다(둘 다 확인).
    """
    got = BF.latest_weekly(CP.parse_posts(RSS))
    assert got == {'date': '2026-09-25', 'url': BF.BLOG_HOME + '/224000000002',
                   'title': '[한국부동산원] 주간 아파트가격 동향(9월 셋째 주) | 서울 +0.13% 전국 +0.09%'}, got
    assert BF.latest_weekly([]) is None


def test_blog_home_follows_the_rss_source_of_truth():
    """블로그 첫 화면 주소는 발행 확인 도구의 RSS 주소(정본)에서 만든다 — 사이트 푸터·/weekly/ 가 같은 값을 쓴다."""
    assert CP.RSS == 'https://rss.blog.naver.com/%s.xml' % BF.BLOG_HOME.rsplit('/', 1)[1]
    assert BF.LABEL == '네이버 블로그'


def test_pick_says_this_week_or_last_week_and_drops_older_posts():
    """발표일 당일·뒤 글은 '이번 주', 7일 안 앞선 글은 '지난주', 그보다 오래되면 칸을 뺀다.

    픽스처: 9/24(목) 발표 주. 9/25 금요일 글 · 9/19 지난주 금요일 글 · 9/16 두 주 전 글(블로그가 한 주 건너뛴 상태).
    변이: FRESH_DAYS 를 14 로 늘리면 9/16 글이 살아나고, `d >= p` 를 `d > p` 로 바꾸면 발표 당일(9/24) 글이 '지난주'가
          되어 빨개진다(둘 다 확인).
    """
    e = {'title': 't', 'url': BF.BLOG_HOME + '/1'}
    pub = '2026-09-24'
    assert BF.pick(dict(e, date='2026-09-25'), pub)['lead'] == BF.LEAD_NOW
    assert BF.pick(dict(e, date='2026-09-24'), pub)['lead'] == BF.LEAD_NOW
    b = BF.pick(dict(e, date='2026-09-19'), pub)
    assert b['lead'] == BF.LEAD_PREV and b['md'] == '9/19' and b['src'] == '네이버 블로그, 9/19'
    assert BF.pick(dict(e, date='2026-09-16'), pub) is None
    assert BF.pick(None, pub) is None
    now = BF.pick(dict(e, date='2026-09-25'), pub)
    assert (now['meta'], now['head']) == ('이번 주 해설 · 네이버 블로그 9/25', 't')
    assert 'note' not in b   # 이웃 안내 줄은 홈(2026-09-28)·/weekly/(2026-10-03) 모두 뺐다
    assert BF.pick(dict(e, date='2026-13-40'), pub) is None, '모양만 맞는 날짜가 예외로 새면 생성기가 죽는다'


@pytest.mark.parametrize('title,want', [
    ('[한국부동산원] 주간 아파트가격 동향(9월 셋째 주) | 강남 3구는 내리고 경기 남부가 올랐습니다', '강남 3구는 내리고 경기 남부가 올랐습니다'),
    ('주간 동향 | 앞 | 끝 결론', '끝 결론'),                 # '|' 가 여럿이면 마지막 뒤
    ('[한국부동산원] 이번 주 시세 정리', '이번 주 시세 정리'),   # '|' 가 없으면 '[…]' 머리말만 걷는다
    ('그냥 제목', '그냥 제목'),
    ('제목 |', '제목 |'),                                       # 결론이 비면 원래 제목
])
def test_headline_keeps_only_the_conclusion(title, want):
    """해설 카드의 굵은 줄은 제목의 결론만이다(2026-10-03 대표 요청 — 매주 같은 앞부분을 되풀이하지 않는다).
    변이(실제로 확인): rsplit 대신 split('|', 1) 로 첫 '|' 뒤를 쓰면 둘째 줄이, 빈 결론에 원래 제목으로 돌아가지 않으면 마지막 줄이 빨개진다.
    픽스처: 실제 발행 제목(9월 셋째 주)과 경계 모양."""
    assert BF.headline(title) == want


def test_card_meta_names_the_week_only_when_the_headline_is_numbers():
    """결론이 숫자(초안 기본 제목 make_naver_post — '서울 +0.10% 전국 +0.07%')면 머리줄에 주차를 붙여, 바로 위 이번 주 지도와 다른
    주의 값을 이번 주 값으로 읽지 않게 한다. 산문 결론(실제 발행 제목)에는 붙이지 않는다(2026-10-03 리뷰).
    변이(실제로 확인): 숫자 조건을 빼고 늘 붙이면 산문 단정이, 주차를 붙이지 않으면 숫자 단정이 빨개진다.
    픽스처: 9/24 발표 주의 지난주 글 두 모양(산문 결론·초안 기본 숫자 제목)."""
    pub = '2026-09-24'
    prose = BF.pick({'title': '[한국부동산원] 주간 아파트가격 동향(9월 둘째 주) | 강남 3구는 내리고 경기 남부가 올랐습니다',
                     'url': BF.BLOG_HOME + '/1', 'date': '2026-09-19'}, pub)
    nums = BF.pick({'title': '[한국부동산원] 주간 아파트가격 동향(9월 둘째 주) | 서울 +0.10% 전국 +0.07%',
                    'url': BF.BLOG_HOME + '/2', 'date': '2026-09-19'}, pub)
    assert prose['meta'] == '지난주 해설 · 네이버 블로그 9/19', prose
    assert nums['meta'] == '지난주 해설(9월 둘째 주) · 네이버 블로그 9/19' and nums['head'] == '서울 +0.10% 전국 +0.07%', nums


def test_feed_failure_never_stops_the_batch_and_keeps_the_last_value(tmp_path):
    """RSS 를 못 읽으면 0 으로 끝나고 파일을 그대로 둔다. 파일이 없으면 빈 값으로 만든다(배치의 git add 가 없는 경로에서
    죽지 않게). 읽으면 최신 글로 바꾼다.

    변이: main 의 실패 분기에서 `return 0` 을 `return 1` 로 바꾸거나, 빈 파일 만들기를 지우면 빨개진다(둘 다 확인).
    """
    f = str(tmp_path / 'blog.json')
    assert BF.main(path=f, fetch=lambda: None) == 0
    assert json.loads(io.open(f, encoding='utf-8').read()) == {'weekly': None}

    def boom():
        raise OSError('망 끊김')
    assert BF.main(path=f, fetch=lambda: CP.parse_posts(RSS)) == 0
    first = io.open(f, encoding='utf-8').read()
    assert BF.read(f)['date'] == '2026-09-25'
    assert BF.main(path=f, fetch=boom) == 0 and BF.main(path=f, fetch=lambda: []) == 0
    assert io.open(f, encoding='utf-8').read() == first, '못 읽은 회차에 지난 값을 지웠다'


def test_stored_value_is_validated_before_it_reaches_a_page(tmp_path):
    """저장 파일이 손상됐거나 남의 주소를 담으면 없는 것으로 본다(사이트가 엉뚱한 곳을 가리키지 않게).

    변이: read() 의 ours() 검사를 지우면 빨개진다(확인).
    """
    f = tmp_path / 'blog.json'
    f.write_text(json.dumps({'weekly': {'date': '2026-09-25', 'title': 't', 'url': 'https://evil.test/"x'}}), encoding='utf-8')
    assert BF.read(str(f)) is None
    f.write_text('{', encoding='utf-8')
    assert BF.read(str(f)) is None
    assert BF.read(str(tmp_path / 'none.json')) is None


def test_repo_file_exists_and_is_readable():
    """배치 커밋 대상(TARGETS)에 든 파일이라 저장소에 늘 있어야 한다 — 없으면 git add 가 경로를 못 찾아 커밋이 멈춘다."""
    raw = json.loads(io.open(BF.FILE, encoding='utf-8').read())
    assert 'weekly' in raw
    assert raw['weekly'] is None or BF.read() is not None


# ── /weekly/ 하단 칸 ─────────────────────────────────────────────────────────────────────────────────
def _week():
    regs = list(__import__('sido_zones').DISPLAY_ORDER)
    ma = [0.02] * len(regs)
    codes = ['C%02d' % i for i in range(12)]
    W = {'regions': regs, 'rows': [{'p': '2026-09-21', 'ma': ma}], 'holidays': [],
         'sgg': {'codes': codes, 'rows': [{'p': '2026-09-21', 'ma': [0.01 * i - 0.05 for i in range(12)]}]},
         'seoul': {'regions': ['강남구', '서초구', '마포구'], 'rows': [{'p': '2026-09-21', 'ma': [0.1, -0.1, 0.0]}]}}
    return W, {c: '시군구%d' % i for i, c in enumerate(codes)}


def _skeleton():
    return io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8', newline='').read()


def test_weekly_page_bakes_the_same_post_once_before_more_links(tmp_path, monkeypatch):
    """/weekly/ 하단 칸 = 홈과 같은 pick 결과 + 블로그 첫 화면 링크. 표식은 '더 둘러보기' 앞에 하나만 생기고, 다시 구워도 같다.
    글이 없으면 글 줄만 빠진다.

    픽스처: 9/21 조사(9/24 발표) 주, 저장 파일에 9/25 주간 글. 뼈대는 저장소 weekly/index.html 에서 표식을 뗀 것(표식 이전
    모양)과 붙은 것 둘 다.
    변이: put_blog 의 표식 삽입을 '</main>' 앞으로만 하게 바꾸면 순서 단정이, blog_html 에서 글 줄·이웃 안내 줄·onclick 을
          지우면 각 단정이 빨개진다(넷 다 확인).
    """
    f = tmp_path / 'blog.json'
    f.write_text(json.dumps({'weekly': {'date': '2026-09-25', 'title': '제목 <b>&', 'url': BF.BLOG_HOME + '/9'}},
                            ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(BF, 'FILE', str(f))
    W, Q = _week()
    base = re.sub(r'<!--WK:BLOG-->.*?<!--/WK:BLOG-->\s*', '', _skeleton(), flags=re.S)
    out = MW.render(base, W, Q)
    assert out.count('<!--WK:BLOG-->') == 1 and MW.render(out, W, Q) == out
    blk = re.search(r'<!--WK:BLOG-->(.*?)<!--/WK:BLOG-->', out, re.S).group(1)
    assert out.index('<!--WK:BLOG-->') < out.index('<h2>더 둘러보기</h2>')
    b = BF.pick(BF.read(), WR.status('2026-09-21')['pub'])
    assert b['lead'] == BF.LEAD_NOW
    assert '>제목 &lt;b&gt;&amp;<span>%s</span></a>' % b['meta'] in blk, blk
    assert 'href="%s"' % BF.BLOG_HOME in blk and '금요일' not in blk and '알림' not in blk
    # 이웃 안내 줄(RET-4 A안)은 뺐다(2026-10-03 대표 요청 — 군더더기). 클릭은 gtag blog_link 이벤트(이 페이지엔 홈 track 이 없다)
    assert 'blog-note' not in blk and '이웃' not in blk, '해설 글 칸에 이웃 안내 줄이 되살아났다'
    assert "gtag('event','blog_link',{to:'weekly_post'})" in blk and "gtag('event','blog_link',{to:'weekly_home'})" in blk
    f.write_text(json.dumps({'weekly': None}), encoding='utf-8')
    blk2 = re.search(r'<!--WK:BLOG-->(.*?)<!--/WK:BLOG-->', MW.render(out, W, Q), re.S).group(1)
    assert BF.LEAD_NOW not in blk2 and 'href="%s"' % BF.BLOG_HOME in blk2


def test_pick_labels_by_the_week_in_the_title_not_the_post_date():
    """제목에 주차 라벨이 있으면 '이번 주/지난주'를 그 라벨로 정한다(전수리뷰 #27). 게시일로만 정하면 지난 회차 글이
    이번 발표일 뒤에 올라왔을 때 '이번 주 해설: …(8월 셋째 주)'가 '8월 넷째 주' 페이지에 붙는다.

    픽스처: 8/30 에 8월 3·4주 글이 함께 올라간 실제 사례. 조사일 2026-08-24(발표일은 weekly_release.status 에서) 회차에
    발표일 뒤 게시된 세 글 — 제목 라벨이 이번 조사일·한 주 앞·두 주 앞(라벨은 WR.week_label 로 유도). 라벨 없는 제목은
    예전처럼 게시일로 정한다.
    변이(실제로 확인): pick 에서 제목 라벨 분기를 지워 게시일 규칙만 남기면 '지난주'·None 단정이 빨개진다. 조사일을
          발표일 − PUB_OFFSET 대신 발표일 그대로 쓰면 9/7 조사(9/10 발표 — 서수가 갈리는 주) 단정이 빨개진다.
    """
    d = datetime.date.fromisoformat
    # 두 번째 조사일(9/7)은 발표일(9/10)과 서수가 다른 주다 — 조사일을 발표일에서 거꾸로 세는 셈이 틀리면 드러난다.
    for s in ('2026-08-24', '2026-09-07'):
        pub = WR.status(s)['pub']
        after = (d(pub) + datetime.timedelta(days=3)).isoformat()

        def lab(k):
            return WR.week_label((d(s) - datetime.timedelta(days=7 * k)).isoformat())

        def post(k):
            return {'date': after, 'url': BF.BLOG_HOME + '/%d' % k,
                    'title': '[한국부동산원] 주간 아파트가격 동향(%s) | 서울이 올랐습니다' % lab(k)}
        assert len({lab(0), lab(1), lab(2)}) == 3
        assert BF.pick(post(0), pub)['lead'] == BF.LEAD_NOW, s
        assert BF.pick(post(1), pub)['lead'] == BF.LEAD_PREV, '지난 회차 글을 게시일만 보고 이번 주 해석으로 붙였다(%s)' % s
        assert BF.pick(post(2), pub) is None, '두 회차 전 글을 이번 주 페이지에 붙였다(%s)' % s
    plain = {'date': after, 'url': BF.BLOG_HOME + '/9', 'title': '주간 시세 해설'}
    assert BF.pick(plain, pub)['lead'] == BF.LEAD_NOW
    assert BF.title_week('동향(8월  셋째 주)') == '8월 셋째 주'


def test_weekly_page_keeps_the_blog_title_as_written(tmp_path, monkeypatch):
    """/weekly/ 의 해설 글 칸은 RSS 제목을 그대로 인용한다 — 뼈대의 'N개 시도'를 모델 수로 맞추는 치환이 남의 글 제목까지
    고치면 안 된다(전수리뷰 #26: '5개 시도만 올랐습니다' → '16개 시도만'). 뼈대 문구의 치환은 그대로 된다.

    픽스처: 9/21 조사 주(_week), 저장 파일에 이번 주 라벨·발표일 뒤 게시의 주간 글, 제목 결론절에 시도 수(모델 수와 다른
    수 — 모델에서 유도)가 든 실제 제목 모양.
    변이(실제로 확인): render 에서 시도 수 치환을 put_blog 뒤로 되돌리면 빨개진다.
    """
    W, Q = _week()
    n = len(MW.SIDO) - 11
    title = '[한국부동산원] 주간 아파트가격 동향(%s) | %d개 시도만 올랐습니다' % (WR.week_label(W['rows'][-1]['p']), n)
    f = tmp_path / 'blog.json'
    f.write_text(json.dumps({'weekly': {'date': WR.status(W['rows'][-1]['p'])['pub'], 'title': title,
                                        'url': BF.BLOG_HOME + '/7'}}, ensure_ascii=False), encoding='utf-8')
    monkeypatch.setattr(BF, 'FILE', str(f))
    out = MW.render(_skeleton(), W, Q)
    blk = re.search(r'<!--WK:BLOG-->(.*?)<!--/WK:BLOG-->', out, re.S).group(1)
    assert '%d개 시도만 올랐습니다' % n in blk, '해설 글 제목을 고쳐 인용했다: %s' % blk
    assert '%d개 시도만' % len(MW.SIDO) not in blk
    rest = out.replace(blk, '')
    assert not [x for x in re.findall(r'(?<!\d)(\d+)개 시도', rest) if int(x) != len(MW.SIDO)], '뼈대 시도 수 치환이 빠졌다'


# ── 홈 쪽(ADV.blog) ──────────────────────────────────────────────────────────────────────────────────
def test_split_carries_the_picked_post_as_a_top_level_key(tmp_path, monkeypatch):
    """split_data 가 /weekly/ 와 같은 pick 결과를 data-core 최상위 ADV.blog 로 싣는다. 최상위 키라 통계 탭을 열어도
    (loadFullData 의 Object.assign 은 trend 에 있는 키만 바꾼다) 남는다. 고를 글이 없으면 키를 싣지 않는다.

    변이: split_data 에서 `core_adv['blog'] = blog` 줄을 지우거나, 발표일 대신 조사일(p, 발표 3일 전)을 pick 에 넘기면
          발표 8일 전 글이 살아나 빨개진다(둘 다 확인).
    픽스처: 저장소 data.js 사본 + 그 최신 주 발표일 다음 날 글 / 발표 8일 전 글(블로그가 한 주 건너뛴 상태).
    """
    d = tmp_path
    src = d / 'data.js'
    shutil.copyfile(os.path.join(ROOT, 'data.js'), str(src))
    for k, name in (('SRC', 'data.js'), ('OUT', 'data-core.js'), ('REST', 'r.json'), ('TREND', 't.json'),
                    ('SGG', 's.json'), ('SIZE', 'z.json')):
        monkeypatch.setattr(S, k, str(d / name))
    W, _ = MW.load()
    pub = WR.status(W['rows'][-1]['p'])['pub']
    y, m, dd = (int(x) for x in pub.split('-'))
    f = d / 'blog.json'
    monkeypatch.setattr(BF, 'FILE', str(f))

    def core(post_date):
        f.write_text(json.dumps({'weekly': {'date': post_date, 'title': '글', 'url': BF.BLOG_HOME + '/5'}}), encoding='utf-8')
        S.main()
        s = (d / 'data-core.js').read_text(encoding='utf-8')
        adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', s, re.S).group(1))
        trend = json.loads((d / 't.json').read_text(encoding='utf-8'))['ADV']
        return adv, trend
    nxt = (datetime.date(y, m, dd) + datetime.timedelta(days=1)).isoformat()
    adv, trend = core(nxt)
    assert adv['blog'] == BF.pick(BF.read(), pub) and adv['blog']['lead'] == BF.LEAD_NOW
    assert 'blog' not in trend, 'trend 에 blog 키가 있으면 통계 탭을 열 때 덮어쓸 수 있다'
    old = (datetime.date(y, m, dd) - datetime.timedelta(days=BF.FRESH_DAYS + 1)).isoformat()
    adv, _ = core(old)
    assert 'blog' not in adv


# ── 배치 배선 ──────────────────────────────────────────────────────────────────────────────────────────
def _code_lines(path):
    return [l for l in io.open(path, encoding='utf-8').read().splitlines()
            if l.strip() and not l.strip().startswith(('#', 'rem', 'REM'))]


def test_batch_reads_the_feed_before_split_and_ships_the_file():
    """수집 잡이 split_data **앞**에서 RSS 를 읽고(홈 data-core 에 실리려면), 그 파일을 아티팩트로 올려 커밋 잡이 옮기고,
    커밋 대상에 넣는다. 실패가 데이터 갱신을 막지 않는다(`||` 로 흡수 — 도구도 언제나 0).

    변이: blog_feed 줄을 split_data 뒤로 옮기거나, `timeout 90` 을 빼거나, 업로드 경로·커밋 잡 cp·TARGETS 에서 파일을 빼면
          빨개진다(다섯 다 확인).
    픽스처: 저장소의 update-cloud.yml·run_weekly_update.bat.
    """
    lines = _code_lines(WF)
    feed = [i for i, l in enumerate(lines) if 'tools/blog_feed.py' in l]
    split = [i for i, l in enumerate(lines) if re.search(r'python3? tools/split_data\.py', l)]
    assert len(feed) == 1 and split and feed[0] < split[0], (feed, split)
    assert lines[feed[0]].strip().startswith('timeout 90 python tools/blog_feed.py'), '벽시계 상한(timeout 90)이 없다'
    assert '||' in lines[feed[0]], 'blog_feed 실패가 수집 잡을 죽일 수 있다'
    y = io.open(WF, encoding='utf-8').read()
    up = re.search(r'name: data-\$\{\{ matrix\.n \}\}\s*\n\s*path: \|\n((?:\s+\S.*\n)+?)\s+retention-days', y)
    assert up and 'tools/data/blog_latest.json' in up.group(1).split(), '아티팩트에 blog_latest.json 이 없다'
    assert 'cp "$SRC/tools/data/blog_latest.json" tools/data/blog_latest.json' in y
    t = re.search(r'TARGETS="([^"]+)"', y).group(1).split()
    assert 'tools/data/blog_latest.json' in t and 'index.html' in t
    bl = _code_lines(BAT)
    bf = [i for i, l in enumerate(bl) if l.strip().startswith('python tools\\blog_feed.py')]
    bs = [i for i, l in enumerate(bl) if l.strip().startswith('python tools\\split_data.py')]
    assert len(bf) == 1 and bs and bf[0] < bs[0]


def test_a_malformed_rss_address_empties_the_line_instead_of_killing_split(tmp_path, monkeypatch):
    """RSS 정본 주소 모양이 바뀌어도 blog_feed 를 불러오는 split_data·make_weekly_page 가 죽지 않는다 — 칸만 빈다.
    예전 판은 모듈 맨 위에서 SystemExit(BaseException)을 던져 split 의 `except Exception` 을 뚫고 수집 잡을 죽일 수 있었다.

    변이: blog_home 을 옛 `raise SystemExit(...)` 로 되돌리면 reload 에서 빨개진다(확인).
    픽스처: close_published_issues.RSS 가 다른 모양('https://example.com/feed')인 상태.
    """
    import make_weekly_page as MWP
    try:
        monkeypatch.setattr(CP, 'RSS', 'https://example.com/feed')
        importlib.reload(BF)
        assert BF.BLOG_HOME is None and not BF.ours('https://blog.naver.com/x/1')
        assert BF.latest_weekly(CP.parse_posts(RSS)) is None
        assert MWP.blog_html(None) == ''
        f = str(tmp_path / 'b.json')
        assert BF.main(path=f, fetch=lambda: CP.parse_posts(RSS)) == 0 and BF.read(f) is None
    finally:
        monkeypatch.undo()
        importlib.reload(BF)
    assert BF.BLOG_HOME and BF.BLOG_HOME.startswith('https://blog.naver.com/')


def test_rss_read_has_a_wall_clock_cap(tmp_path, monkeypatch):
    """RSS 읽기가 느리게 새도 도구가 WALL_SECONDS 에서 그만두고 0 으로 끝나며 지난 값을 둔다(로컬 bat 엔 셸 timeout 이 없다).

    변이: _fetch_with_wall 의 `t.join(WALL_SECONDS)` 를 `t.join()` 으로 바꾸면 3초를 다 기다려 빨개진다(확인).
    픽스처: 3초 걸리는 fetch, 상한 0.3초.
    """
    f = str(tmp_path / 'b.json')
    BF.write({'date': '2026-09-19', 'title': '지난 글', 'url': BF.BLOG_HOME + '/1'}, f)
    before = io.open(f, encoding='utf-8').read()
    monkeypatch.setattr(BF, 'WALL_SECONDS', 0.3)

    def slow():
        time.sleep(3)
        return CP.parse_posts(RSS)
    t0 = time.time()
    assert BF.main(path=f, fetch=slow) == 0
    assert time.time() - t0 < 2, '벽시계 상한이 걸리지 않았다'
    assert io.open(f, encoding='utf-8').read() == before
