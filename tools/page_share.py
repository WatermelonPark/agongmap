# -*- coding: utf-8 -*-
"""생성 페이지(/weekly/·/monthly/)의 공유 버튼 — 홈 마케팅 검수 B8·VIRAL-1(2026-09-27).

매주·매달 바뀌어 단톡방에 퍼뜨리기 좋은 화면에 공유 수단이 없었다(공유 코드는 퀴즈와 시도 리포트뿐). 두 관례를
그대로 잇는다.
  - 퀴즈(home-app.js shareTest·shareResult): 카카오 SDK 를 **누를 때만** 받는다(loadKakao·needKakao). SDK 가 있으면
    Kakao.Share.sendDefault 피드(제목·설명·그림을 우리가 정해 보낸다), 못 받으면 OS 공유 → 링크 복사로 넘어간다.
    GA 는 share {content_type, method: kakao|os_share|copy}.
  - 시도 리포트(make_sido_pages.share_section): 랜딩 페이지라 첫 로딩에 SDK 를 싣지 않는다. 그래서 여기서도
    누르려는 순간(버튼에 손가락·포인터가 닿거나 초점이 갈 때) 받기 시작하고, 첫 화면 무게는 0 바이트다.
두 버튼을 둔다. '카카오톡 공유'는 피드, '링크 공유'는 OS 공유 시트(모바일 — 카톡·문자·밴드 등) 또는 복사(데스크톱).

카카오 키와 SDK 주소는 홈 스크립트(home-app.js)에 있는 것을 **읽어서** 쓴다 — 여기 따로 적으면 SDK 판을 올릴 때
한쪽만 바뀐다(같은 대상을 두 곳에서 재지 않는다, test_page_share).

■ 미리보기 보관(VIRAL-2·1차 A7 '남긴 한계'): 카카오톡은 한 번 긁어 간 **페이지 주소**의 미리보기를 보관한다. 그래서
  보내는 링크에 회차 값(utm_campaign=week_YYYYMMDD·month_YYYYMM)을 붙여 주마다·달마다 다른 주소로 만든다. 같은 값이
  GA 캠페인이 되어 어느 회차 카드가 퍼졌는지도 보인다. 피드는 그림 주소를 우리가 넘기므로 그림 주소의 ?v= 판이
  곧 새 그림이다.
"""
import html
import json
import re

import home_src as HS

MEDIUM = 'viral'   # GA 어트리뷰션 규약(home-app.js SHARE_URL_UTM·zone_share): utm_medium=viral 고정


def kakao_consts(src=None):
    """홈 스크립트의 (카카오 JS 키, SDK 주소). 못 찾으면 SystemExit — 빈 값으로 굽지 않는다."""
    src = src if src is not None else HS.home_source()
    key = re.findall(r"^const KAKAO_KEY='([0-9a-f]+)';", src, re.M)
    sdk = re.findall(r"loadScript\('(https://t1\.kakaocdn\.net/kakao_js_sdk/[^']+/kakao\.min\.js)'\)", src)
    if len(key) != 1 or len(set(sdk)) != 1:
        raise SystemExit('home-app.js 에서 KAKAO_KEY(%d)·카카오 SDK 주소(%d)를 하나씩 찾지 못했다' % (len(key), len(set(sdk))))
    return key[0], sdk[0]


def link(page_url, source, campaign):
    """공유 링크. utm_source = 유입 장치(weekly_share·monthly_share), utm_campaign = 회차."""
    return '%s?utm_source=%s&utm_medium=%s&utm_campaign=%s' % (page_url, source, MEDIUM, campaign)


CSS = ('.pshare{padding:6px 0 26px}'
       '.pshare-lead{font-size:13px;color:var(--muted);text-align:center;margin:0 0 10px}'
       '.pshare-row{display:flex;gap:8px;max-width:400px;margin:0 auto}'
       '.pshare-btn{flex:1 1 0;min-width:0;min-height:46px;display:flex;align-items:center;justify-content:center;gap:5px;'
       'background:#fff;color:var(--ink);border:1.5px solid var(--ink);border-radius:3px;cursor:pointer;'
       'font-family:inherit;font-size:14px;font-weight:600;padding:10px 6px;line-height:1.3;white-space:nowrap}'
       '.pshare-btn.pshare-k{background:#FEE500;border-color:#FEE500;color:#191919}'   # 퀴즈 카카오 버튼(.qshare-btn.primary)과 같은 색
       '.pshare-btn svg{flex:none}')

# 카카오 말풍선 — 퀴즈 결과 화면의 카카오 공유 버튼(home-app.js .qshare-btn.primary)과 같은 그림
_ICON_K = ('<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" '
           'd="M12 3C6.48 3 2 6.54 2 10.9c0 2.8 1.86 5.26 4.66 6.66-.15.52-.97 3.36-1 3.58 0 0-.02.17.09.24.11.07.24.02.24.02'
           '.32-.04 3.66-2.4 4.24-2.81.57.08 1.16.13 1.77.13 5.52 0 10-3.54 10-7.9S17.52 3 12 3z"/></svg>')
_ICON_S = ('<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="none" stroke="currentColor" '
           'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" '
           'd="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M12 3v13M8 7l4-4 4 4"/></svg>')

# 누르는 쪽의 스크립트. ES5 — 생성 페이지는 빌드 도구 없이 나간다. D 는 페이지마다 굽는 공유 내용.
# say(): 버튼의 원래 모양(아이콘+라벨)은 **한 번만** 저장하고 앞선 되돌림 타이머를 지운다. 누를 때마다 저장하면 2초 안에
# 두 번 누른 경우 안내 문구를 '원래 모양'으로 저장해 버튼이 새로고침 전까지 안내 문구로 굳었다(전수리뷰 #28).
_JS = r"""(function(){var D=%(d)s,KEY=%(key)s,SDK=%(sdk)s,P=null,FAIL=false;
function load(){if(window.Kakao)return Promise.resolve();if(P)return P;
P=new Promise(function(ok,no){var s=document.createElement('script');s.src=SDK;s.async=true;s.onload=function(){ok();};
s.onerror=function(){s.parentNode&&s.parentNode.removeChild(s);P=null;FAIL=true;no();};document.head.appendChild(s);});return P;}
function ready(){if(!window.Kakao)return false;try{if(!Kakao.isInitialized())Kakao.init(KEY);return Kakao.isInitialized();}catch(e){return false;}}
function ev(m){try{gtag('event','share',{content_type:D.ct,method:m});}catch(e){}}
function say(b,m){if(!b)return;if(b._o==null)b._o=b.innerHTML;clearTimeout(b._t);b.textContent=m;
b._t=setTimeout(function(){b.innerHTML=b._o;b._o=null;},2000);}
function copy(b){var t=D.title+'\n'+D.url;if(navigator.clipboard&&navigator.clipboard.writeText){
navigator.clipboard.writeText(t).then(function(){say(b,'링크를 복사했어요');},function(){say(b,'주소창을 복사해 주세요');});}
else say(b,'주소창을 복사해 주세요');}
function share(b){ev(navigator.share?'os_share':'copy');if(navigator.share){
navigator.share({title:D.title,text:D.text,url:D.url}).catch(function(e){if(e&&e.name!=='AbortError')copy(b);});return;}copy(b);}
function kakao(b){if(!window.Kakao&&!FAIL){load().then(function(){kakao(b);},function(){kakao(b);});return;}
if(ready()){try{Kakao.Share.sendDefault({objectType:'feed',content:{title:D.title,description:D.text,imageUrl:D.img,
imageWidth:D.w,imageHeight:D.h,link:{mobileWebUrl:D.url,webUrl:D.url}},
buttons:[{title:D.btn,link:{mobileWebUrl:D.url,webUrl:D.url}}]});ev('kakao');return;}catch(e){}}
share(b);}
window.agShare=function(m,b){if(m==='kakao')kakao(b);else share(b);};
var k=document.querySelector('#%(id)s .pshare-k');
if(k)['pointerenter','touchstart','focus'].forEach(function(t){k.addEventListener(t,function(){load().catch(function(){});},{once:true,passive:true});});
})();"""


def block(d, lead, src=None):
    """공유 구역 HTML(스타일·스크립트 포함). d: ct·url·title·text·img·w·h·btn."""
    key, sdk = kakao_consts(src)
    sid = 'share-' + d['ct']
    js = _JS % {'d': json.dumps({k: d[k] for k in ('ct', 'url', 'title', 'text', 'img', 'w', 'h', 'btn')},
                                ensure_ascii=False).replace('</', '<\\/'),
                'key': json.dumps(key), 'sdk': json.dumps(sdk), 'id': sid}
    return ('<section class="pshare" id="%s" aria-label="공유"><div class="wrap">'
            '<p class="pshare-lead">%s</p><div class="pshare-row">'
            '<button type="button" class="pshare-btn pshare-k" onclick="agShare(\'kakao\',this)">%s카카오톡 공유</button>'
            '<button type="button" class="pshare-btn" onclick="agShare(\'link\',this)">%s링크 공유</button>'
            '</div></div></section>\n<style>%s</style>\n<script>%s</script>'
            % (sid, html.escape(lead), _ICON_K, _ICON_S, CSS, js))
