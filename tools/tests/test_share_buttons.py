# -*- coding: utf-8 -*-
"""주간·월간 공유 버튼과 월간 공유 카드(홈 마케팅 검수 B8·VIRAL-1·VIRAL-2, 2026-09-27).

재현하는 실제 상태(09-26 라이브): 공유 코드가 있는 곳은 퀴즈와 시도 리포트뿐이었다. /weekly/·/monthly/·홈 주간 구역에는
공유 수단이 없었고, /monthly/ 의 og:image 는 범용 og-brand.png 라 링크를 붙이면 매달 같은 브랜드 카드가 떴다.
카카오톡은 페이지 주소 단위로 미리보기를 보관하므로(1차 A7 '남긴 한계') 매주 같은 /weekly/ 주소는 지난주 미리보기를 낼 수 있다.

정리한 모양:
  - 공유 내용은 파이썬 한 곳에서 만든다 — 주간 make_weekly_page.share_payload(→ /weekly/ 버튼, split_data → ADV.weekly.share →
    홈 격자 버튼), 월간 make_monthly_page.share_payload. 링크의 utm_campaign 이 회차(week_YYYYMMDD·month_YYYYMM)라 주소가
    회차마다 달라진다. 카카오 키·SDK 주소는 홈 스크립트에서 읽는다(page_share.kakao_consts).
  - 월간 카드는 make_monthly_share 가 make_monthly_page.SHARE_REL 에 굽고, 페이지 og:image 는 그 파일이 **있을 때만**
    ?v=기준월 을 붙여 가리킨다(없으면 브랜드 카드 — 병합 직후 첫 배치 전 상태).
각 시험의 독스트링에 ① 무엇을 깨뜨리면 빨개지는지(실제로 변이를 넣어 확인) ② 픽스처가 재현하는 상태를 적었다.
"""
import copy
import io
import json
import os
import re
import shutil
import subprocess
import sys
from urllib.parse import parse_qs, urlsplit

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
import home_src as HS  # noqa: E402
import make_monthly_page as MP  # noqa: E402
import make_weekly_page as MW  # noqa: E402
import page_share as PS  # noqa: E402
import split_data as S  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..'))
# 먼 미래 두 주(조사일 월 → 발표일 목). 날짜 셈은 여기 따로 적어 대조한다.
WEEKS = (('2030-01-07', '20300110', '2030-01-10'), ('2030-01-14', '20300117', '2030-01-17'))


def _node(js):
    node = shutil.which('node')
    assert node, 'node 가 없다 — 공유 스크립트를 돌려 볼 수 없다(CI 러너에는 있다)'
    p = subprocess.run([node, '-e', js], capture_output=True, timeout=60)
    assert p.returncode == 0, p.stderr.decode('utf-8', 'replace')
    return json.loads(p.stdout.decode('utf-8'))


def _week(p):
    """저장소 주간 계열 끝에 조사일 p 인 주를 덧붙인다(값은 직전 주 그대로)."""
    W, Q = MW.load()
    W = copy.deepcopy(W)
    W['rows'].append(dict(W['rows'][-1], p=p))
    for part in ('sgg', 'seoul'):
        W[part]['rows'].append(dict(W[part]['rows'][-1], p=p))
    return W, Q


def _page_share(html):
    """페이지에 구운 공유 스크립트의 내용(D)·키·SDK 주소."""
    m = re.search(r'<script>\(function\(\)\{var D=(\{.*?\}),KEY=("[^"]+"),SDK=("[^"]+")', html, re.S)
    assert m, '공유 스크립트를 찾지 못했다'
    return json.loads(m.group(1)), json.loads(m.group(2)), json.loads(m.group(3))


def test_weekly_share_link_and_card_change_every_week(tmp_path):
    """공유 링크는 /weekly/ 정식 주소 + utm_source=weekly_share·utm_medium=viral·utm_campaign=week_발표일, 그림은 카드?v=발표일 —
    새 주차가 들어오면 링크와 그림 주소가 같이 바뀐다(카카오가 새로 긁어 간다).

    변이(각각 실제로 확인): share_campaign 이 고정값('week')을 돌려주면, share_payload 의 img 에서 ?v= 를 빼면,
    utm_source 를 'weekly' 로 바꾸면 빨개진다.
    픽스처: 저장소 data.js 주간 계열에 먼 미래 주차를 하나씩 덧붙인 두 주. 그림 주소의 판은 구워진 카드에서 읽으므로
    (전수리뷰 #85) 주마다 그 주 카드(메타만 든 PNG)를 임시 폴더에 둔다.
    """
    from test_weekly_share_version import fake_card
    seen = set()
    for p, ymd, pub in WEEKS:
        W, _ = _week(p)
        fake_card(tmp_path.joinpath(*MW.SHARE_REL.split('/')), agongmap_basis=p, agongmap_pub=pub)
        d = MW.share_payload(W, root=str(tmp_path))
        u = urlsplit(d['url'])
        q = parse_qs(u.query)
        assert '%s://%s%s' % (u.scheme, u.netloc, u.path) == MW.SITE + '/weekly/'
        assert q == {'utm_source': ['weekly_share'], 'utm_medium': ['viral'], 'utm_campaign': ['week_' + ymd]}, q
        assert d['img'] == MW.SHARE_IMG + '?v=' + pub
        assert d['p'] == p and d['ct'] == 'weekly' and (d['w'], d['h']) == MW.SHARE_SIZE
        seen.add((d['url'], d['img']))
    assert len(seen) == len(WEEKS)


@pytest.fixture(scope='module')
def split(tmp_path_factory):
    d = tmp_path_factory.mktemp('split_share')
    src = d / 'data.js'
    shutil.copyfile(os.path.join(ROOT, 'data.js'), src)
    paths = {'SRC': src, 'OUT': d / 'data-core.js', 'REST': d / 'data-rest.json',
             'TREND': d / 'data-trend.json', 'SGG': d / 'data-sgg.json', 'SIZE': d / 'data-size.json'}
    with pytest.MonkeyPatch.context() as mp:
        for k, v in paths.items():
            mp.setattr(S, k, str(v))
        S.main()
    core = io.open(str(paths['OUT']), encoding='utf-8').read()
    core_adv = json.loads(re.search(r'const ADV=(\{.*?\});\nconst STATS', core, re.S).group(1))
    trend = json.loads(paths['TREND'].read_text(encoding='utf-8'))
    return core_adv, trend['ADV']


def test_home_and_weekly_page_share_the_same_payload(split):
    """홈 격자 버튼이 읽는 ADV.weekly.share(data-core·data-trend 둘 다)와 /weekly/ 버튼에 구운 내용이 같은 함수의 값이고,
    구운 스크립트의 카카오 키·SDK 주소가 홈 스크립트(KAKAO_KEY·loadKakao)의 것과 같다.

    변이(각각 실제로 확인): split_data 가 trend 쪽 share 를 빼면, share_html 이 제목을 따로 적으면, page_share.kakao_consts 를
    옛 SDK 주소(2.7.2) 상수로 바꾸면 빨개진다.
    픽스처: 저장소 data.js 사본에 split 을 돌린 결과와 저장소 weekly/index.html(CI·배치는 생성기를 시험보다 먼저 돌린다).
    """
    core, trend = split
    W, _ = MW.load()
    want = MW.share_payload(W)
    assert want and core['weekly']['share'] == want and trend['weekly']['share'] == want
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    d, key, sdk = _page_share(page)
    assert d == {k: v for k, v in want.items() if k != 'p'}
    h = HS.home_source()
    assert re.findall(r"^const KAKAO_KEY='([0-9a-f]+)';", h, re.M) == [key]
    assert sdk in re.findall(r"loadScript\('([^']+kakao\.min\.js)'\)", h), sdk


_STUB = r'''
const calls={kakao:[],share:[],clip:[],ev:[],loaded:0};
globalThis.window=globalThis;
globalThis.gtag=(a,b,c)=>calls.ev.push([a,b,c]);
globalThis.document={querySelector:()=>null,createElement:()=>({}),
  head:{appendChild:s=>{calls.loaded++;setTimeout(()=>MODE.sdk==='ok'?(globalThis.Kakao=KAKAO,s.onload()):s.onerror(),0);}}};
const KAKAO={_i:false,isInitialized(){return this._i;},init(k){calls.key=k;this._i=true;},
  Share:{sendDefault:o=>calls.kakao.push(o)}};
const nav={clipboard:{writeText:t=>{calls.clip.push(t);return Promise.resolve();}}};
if(MODE.os)nav.share=o=>{calls.share.push(o);return Promise.resolve();};
Object.defineProperty(globalThis,'navigator',{value:nav,configurable:true});
if(MODE.sdk==='ready')globalThis.Kakao=KAKAO;
'''


def _run_page_share(html, mode, which='kakao'):
    m = re.search(r'<script>(\(function\(\)\{var D=.*?\}\)\(\);)</script>', html, re.S)
    assert m, '공유 스크립트를 찾지 못했다'
    js = ('const MODE=%s;' % json.dumps(mode)) + _STUB + m.group(1) + (
        '\nagShare(%s,{innerHTML:"",textContent:""});'
        'setTimeout(()=>process.stdout.write(JSON.stringify(calls)),50);' % json.dumps(which))
    return _node(js)


@pytest.mark.parametrize('page', ['weekly', 'monthly'])
def test_page_share_script_sends_the_feed_or_falls_back(page):
    """구운 공유 스크립트: 카카오 SDK 가 있으면 피드(제목·설명·그림·링크 = 구운 내용), 누를 때 받아 오면 받은 뒤 피드, 받기에
    실패하면 OS 공유, OS 공유가 없으면 '제목 + 링크' 복사. GA share 의 method 가 각 경로(kakao·os_share·copy)를 말한다.

    변이(각각 실제로 확인): 피드 링크를 D.url 대신 location.href 로 바꾸면, 받기 실패에서 FAIL 을 세우지 않으면(무한 재시도 —
    피드도 공유도 안 나간다), OS 공유 경로에서 ev 를 빼면 빨개진다.
    픽스처: node 에 Kakao·navigator·document 흉내를 두고 저장소 weekly/·monthly/index.html(생성기가 먼저 구운 것)의 스크립트를 돌린다.
    """
    html = io.open(os.path.join(ROOT, page, 'index.html'), encoding='utf-8').read()
    d, key, _ = _page_share(html)
    c = _run_page_share(html, {'sdk': 'ready', 'os': True})
    assert len(c['kakao']) == 1 and not c['share'] and c['key'] == key
    f = c['kakao'][0]
    assert f['content']['link'] == {'mobileWebUrl': d['url'], 'webUrl': d['url']}
    assert (f['content']['title'], f['content']['description'], f['content']['imageUrl']) == (d['title'], d['text'], d['img'])
    assert f['buttons'][0]['link']['webUrl'] == d['url']
    assert c['ev'] == [['event', 'share', {'content_type': page, 'method': 'kakao'}]]
    c = _run_page_share(html, {'sdk': 'ok', 'os': True})
    assert c['loaded'] == 1 and len(c['kakao']) == 1, '누른 뒤 SDK 를 받아 피드를 보내야 한다'
    c = _run_page_share(html, {'sdk': 'fail', 'os': True})
    assert not c['kakao'] and [s['url'] for s in c['share']] == [d['url']]
    assert c['ev'] == [['event', 'share', {'content_type': page, 'method': 'os_share'}]]
    c = _run_page_share(html, {'sdk': 'fail', 'os': False}, 'link')
    assert c['clip'] == [d['title'] + '\n' + d['url']] and c['loaded'] == 0
    assert c['ev'] == [['event', 'share', {'content_type': page, 'method': 'copy'}]]


def test_home_weekly_share_uses_the_baked_payload():
    """홈 주간 격자의 '카카오톡 공유'는 ADV.weekly.share 를 그대로 피드로 보내고, 조사일이 다른 옛 내용이면 보내지 않는다.

    변이(각각 실제로 확인): weeklyShare 의 조사일 검사(`s.p===row.p`)를 빼면 둘째 단정, shareWeekly 가 피드 링크로
    location.href 를 쓰면 첫 단정이 빨개진다.
    픽스처: 저장소 data.js 주간 계열로 만든 공유 내용과 그 조사일을 하루 비튼 옛 내용.
    """
    h = HS.home_source()
    W, _ = MW.load()
    sh = MW.share_payload(W)
    fn = lambda n: re.search(r'^function %s\(.*?^\}' % n, h, re.M | re.S).group(0)
    base = '\n'.join(['const calls={kakao:[],ev:[]};',
                      'globalThis.Kakao={isInitialized:()=>true,Share:{sendDefault:o=>calls.kakao.push(o)}};',
                      'function needKakao(){return false;} function kakaoReady(){return true;}',
                      'function track(a,b){calls.ev.push([a,b]);} function copyText(){}',
                      fn('weeklyShare'), fn('shareWeekly')])
    for shp, n in ((sh, 1), (dict(sh, p='1999-01-04'), 0)):
        adv = {'weekly': {'rows': [{'p': W['rows'][-1]['p']}], 'share': shp}}
        c = _node(base + '\nglobalThis.ADV=%s;shareWeekly("kakao");process.stdout.write(JSON.stringify(calls));'
                  % json.dumps(adv, ensure_ascii=False))
        assert len(c['kakao']) == n, shp['p']
        if n:
            f = c['kakao'][0]['content']
            assert (f['link']['webUrl'], f['imageUrl'], f['title']) == (sh['url'], sh['img'], sh['title'])
            assert c['ev'] == [['share', {'content_type': 'weekly', 'method': 'kakao'}]]


def test_weekly_card_size_is_one_constant(tmp_path, monkeypatch):
    """/weekly/ 뼈대의 og:image 크기, 카드 생성기가 굽는 크기, 피드에 싣는 크기가 make_weekly_page.SHARE_SIZE 하나다.

    변이(각각 실제로 확인): make_weekly_share 의 크기를 `900, 1100` 으로 따로 적으면, SHARE_SIZE 를 (900, 1100) 으로 바꾸면
    (뼈대와 갈린다) 빨개진다.
    픽스처: 저장소 weekly/index.html 과 임시 폴더에 구운 카드(저장소 share/ 는 건드리지 않는다).
    """
    pytest.importorskip('PIL')
    import make_weekly_share as WS
    from PIL import Image
    page = io.open(os.path.join(ROOT, 'weekly', 'index.html'), encoding='utf-8').read()
    w = re.findall(r'<meta property="og:image:width" content="(\d+)">', page)
    h = re.findall(r'<meta property="og:image:height" content="(\d+)">', page)
    assert (w, h) == ([str(MW.SHARE_SIZE[0])], [str(MW.SHARE_SIZE[1])])
    tmp_path.joinpath('share').mkdir()
    W = WS.load_weekly()
    monkeypatch.setattr(WS, 'load_weekly', lambda: W)
    monkeypatch.setattr(WS, 'ROOT', str(tmp_path))
    monkeypatch.setattr(sys, 'argv', ['make_weekly_share.py'])
    WS.main()
    assert Image.open(str(tmp_path.joinpath(*MW.SHARE_REL.split('/')))).size == MW.SHARE_SIZE


# ── 월간 ────────────────────────────────────────────────────────────────────────────────────────

def test_monthly_share_link_and_og_follow_the_month(tmp_path):
    """월간 공유 링크의 회차는 month_기준월, og:image 는 카드 파일이 있을 때만 카드?v=기준월(없으면 브랜드 카드).

    변이(각각 실제로 확인): share_payload 의 회차를 고정값('month')으로 바꾸면, share_image 가 파일 유무를 보지 않으면
    (없는 파일을 가리킨다), share_image 가 판을 카드 메타가 아니라 데이터(share_version)에서 셈하면(#85) 빨개진다.
    픽스처: 저장소 data.js 의 월간 계열에 먼 미래 달(2030-02)을 하나 덧붙인 것, 카드 파일은 임시 폴더에 두고 빼 본다.
    """
    adv, sts = MP.load()
    adv = copy.deepcopy(adv)
    adv['monthly']['rows'].append(dict(adv['monthly']['rows'][-1], p='2030-02'))
    from test_weekly_share_version import fake_card
    assert MP.share_version(adv) == '2030-02'
    assert MP.share_image(adv, root=str(tmp_path)) == MP.BRAND_IMG
    card = tmp_path.joinpath(*MP.SHARE_REL.split('/'))
    card.parent.mkdir(parents=True)
    card.write_bytes(b'png')
    assert MP.share_image(adv, root=str(tmp_path)) == MP.BRAND_IMG, '판 메타가 없는 카드를 새 판 주소로 가리켰다'
    # 카드 생성이 실패해 지난달 카드가 남은 회차(#85): 주소의 판은 그림의 판(2030-01)이지 데이터의 달(2030-02)이 아니다.
    fake_card(card, agongmap_basis='2030-01')
    assert MP.share_image(adv, root=str(tmp_path)) == (
        '%s/%s?v=2030-01' % (MP.SITE, MP.SHARE_REL), MP.SHARE_SIZE[0], MP.SHARE_SIZE[1])
    fake_card(card, agongmap_basis='2030-02')
    assert MP.share_image(adv, root=str(tmp_path)) == (
        '%s/%s?v=2030-02' % (MP.SITE, MP.SHARE_REL), MP.SHARE_SIZE[0], MP.SHARE_SIZE[1])
    d = MP.share_payload(adv, sts, root=str(tmp_path))
    q = parse_qs(urlsplit(d['url']).query)
    assert q == {'utm_source': ['monthly_share'], 'utm_medium': ['viral'], 'utm_campaign': ['month_203002']}, q
    assert d['img'].endswith('?v=2030-02') and '2030년 2월' in d['title']


def test_monthly_page_og_image_is_the_card_only_when_it_exists():
    """저장소 /monthly/ 의 og:image·twitter:image 가 같은 주소이고, 저장소에 카드 파일이 있으면 카드?v=기준월, 없으면 브랜드 카드다
    (병합 직후 첫 배치 전에도 없는 파일을 미리보기로 가리키지 않는다). 공유 버튼의 그림도 같은 주소다.

    변이(각각 실제로 확인): share_image 가 파일 유무를 보지 않으면(카드가 없는 저장소에서) 빨개진다. put_share_meta 가
    twitter:image 를 빼면 빨개진다.
    픽스처: 저장소 monthly/index.html(생성기가 시험보다 먼저 굽는다)과 저장소 share/ 폴더.
    """
    adv, _ = MP.load()
    html = io.open(os.path.join(ROOT, 'monthly', 'index.html'), encoding='utf-8').read()
    og = re.findall(r'<meta property="og:image" content="([^"]*)">', html)
    tw = re.findall(r'<meta name="twitter:image" content="([^"]*)">', html)
    want = MP.share_image(adv)
    assert og == [want[0]] and tw == og, (og, tw, want)
    if MP.card_version():
        # 판은 구워진 카드의 기준월이다(#85). 게이트는 카드보다 먼저 돌므로 새 달이 들어온 회차엔 데이터의 달보다 한 달
        # 앞선 카드 판이 정상이다 — 데이터의 달(share_version)과 견주면 새 달이 오는 날 게이트가 커밋을 막는다.
        assert og[0].endswith('?v=' + MP.card_version())
    else:
        assert og[0] == MP.BRAND_IMG[0]
    d, _, _ = _page_share(html)
    assert d['img'] == og[0] and d['ct'] == 'monthly'


def test_monthly_card_is_baked_where_the_page_points_with_its_month(tmp_path, monkeypatch):
    """월간 카드 생성기는 페이지가 가리키는 바로 그 파일(SHARE_REL)에 16:9·폭 1200 이상으로 굽고, 카드 메타의 기준월이
    월간 시세 최신 달이며 og:image 판(?v=)과 같다.

    변이(각각 실제로 확인): make_monthly_share 의 출력 경로를 'share/monthly.png' 로 따로 적으면, share_version 이 첫 달
    (rows[0])을 돌려주면 빨개진다.
    픽스처: 저장소 data.js 월간 계열, 카드는 임시 폴더에 굽는다(저장소 share/ 는 건드리지 않는다).
    """
    pytest.importorskip('PIL')
    import make_monthly_share as MS
    from PIL import Image
    monkeypatch.setattr(MS, 'ROOT', str(tmp_path))
    MS.main()
    adv, _ = MP.load()
    card = tmp_path.joinpath(*MP.SHARE_REL.split('/'))
    assert card.is_file(), sorted(p.relative_to(tmp_path).as_posix() for p in tmp_path.rglob('*.png'))
    im = Image.open(str(card))
    w, h = im.size
    assert (w, h) == MP.SHARE_SIZE and w >= 1200 and abs(w / h - 16 / 9) < 0.01
    newest = str(adv['monthly']['rows'][-1]['p'])[:7]
    assert im.text.get('agongmap-basis') == newest
    assert MP.share_image(adv, root=str(tmp_path))[0].endswith('?v=' + im.text['agongmap-basis'])


def test_monthly_card_generator_restamps_the_page(tmp_path, monkeypatch):
    """배치 순서(페이지 → 게이트 → 카드) 그대로: /monthly/ 는 카드보다 먼저 구워져 지난달 카드 판(?v=)을 가리키고, 월간 카드
    생성기가 새 카드를 구운 직후 restamp_share 로 같은 회차 안에서 og:image·twitter:image·공유 버튼 그림 주소를 새 판으로
    고친다(전수리뷰 #85). 카드 생성이 실패하면 이 단계에 닿지 않아 주소는 남은 그림의 판에 머문다(위 시험).

    변이(실제로 확인): make_monthly_share.main 에서 restamp_share 호출을 지우면 빨개진다.
    픽스처: 임시 저장소 뿌리에 지난달 카드(메타만 든 PNG, 기준월 = 데이터 최신 달의 한 달 앞 라벨)와 그 판으로 구운
    monthly/index.html 을 두고, 저장소 data.js 로 카드 생성기를 돌린다.
    """
    pytest.importorskip('PIL')
    import make_monthly_share as MS
    from test_weekly_share_version import fake_card
    adv, sts = MP.load()
    new = MP.share_version(adv)
    y, m = (int(x) for x in new.split('-'))
    old = '%04d-%02d' % (y - (m == 1), (m - 2) % 12 + 1)
    fake_card(tmp_path.joinpath(*MP.SHARE_REL.split('/')), agongmap_basis=old)
    page = MP.put_share_meta('<meta property="og:image" content="%s">' % MP.BRAND_IMG[0],
                             *MP.share_image(adv, root=str(tmp_path)))
    d = MP.share_payload(adv, sts, root=str(tmp_path))
    page += PS.block(d, MP.SHARE_LEAD)
    (tmp_path / 'monthly').mkdir()
    (tmp_path / 'monthly' / 'index.html').write_text(page, encoding='utf-8')
    assert page.count('?v=' + old) >= 3, '픽스처가 지난 판 주소 셋(og·twitter·버튼)을 담지 않는다'

    monkeypatch.setattr(MS, 'ROOT', str(tmp_path))
    MS.main()
    html = (tmp_path / 'monthly' / 'index.html').read_text(encoding='utf-8')
    want = '%s/%s?v=%s' % (MP.SITE, MP.SHARE_REL, new)
    assert re.findall(r'<meta property="og:image" content="([^"]*)">', html) == [want]
    assert re.findall(r'<meta name="twitter:image" content="([^"]*)">', html) == [want]
    assert '?v=' + old not in html, '카드를 새로 구웠는데 지난 판 주소가 남았다'


def test_batch_bakes_the_monthly_card_after_the_gate():
    """배치(update-cloud.yml)가 월간 카드를 pytest 게이트 **뒤**, pillow 가 있을 때 주간 카드 다음에 굽는다(로컬 bat 순서는
    test_batch_parity 가 본다). 게이트 앞에 두면 pillow 가 없는 자리라 매 회차 죽는다(test_test_deps_are_installed).

    변이(각각 실제로 확인): 월간 카드 줄을 지우거나 pytest 줄 앞으로 옮기면 빨개진다.
    픽스처: 저장소 워크플로 파일.
    """
    y = io.open(os.path.join(ROOT, '.github', 'workflows', 'update-cloud.yml'), encoding='utf-8').read()
    lines = [l.strip() for l in y.splitlines() if not l.strip().startswith('#')]
    at = lambda pat: next(i for i, l in enumerate(lines) if re.search(pat, l))
    gate, wk, mo = at(r'python3 -m pytest tools/tests'), at(r'python3 tools/make_weekly_share\.py'), \
        at(r'python3 tools/make_monthly_share\.py')
    assert gate < wk < mo
