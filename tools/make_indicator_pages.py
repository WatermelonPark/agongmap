# -*- coding: utf-8 -*-
"""지표별 정적 랜딩 페이지 생성기 — /jeonse-ratio/(전세가율), /moveins/(입주물량).

zone 페이지와 같은 모델: 배치가 실데이터를 표·요약 문장으로 구워 넣은 완결
페이지를 재생성한다. 빈 차트 껍데기(thin content)가 아니라 JS 없이도 내용이
온전해야 검색엔진이 지표 페이지로 인정한다. 대상 지표는 검색 수요가 실재하는
것만 — 기본통계 전 계열을 페이지로 찍으면 얇은 유사 페이지 무더기가 된다
(2026-07-29 사용자 합의: 전세가율·입주물량 2종만).

결정성: 본문 날짜는 전부 데이터 시점에서 유도한다(오늘 날짜 금지).
데이터가 안 바뀐 실행은 바이트 동일 출력 → git diff 없음 → 커밋 없음.
(옛 make_zone_pages가 keep_dates로 배운 것과 같은 교훈, 여기선 애초에 오늘을 안 쓴다)

실행: python tools/make_indicator_pages.py   # 생성 + sitemap 갱신
"""
import io
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sido_zones as SZ  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = 'https://www.agongmap.co.kr'
PUBLISHED = '2026-07-29'   # 페이지 최초 공개일(고정)

# 2026-09-10 광주·전남 통합으로 16곳이 됐다(이름은 이력상 SIDO17을 유지).
# ⚠️ 순서는 화면 표시용이라 손으로 둔다. 다만 **집합**은 모델과 같아야 한다 —
# 여기서 한 곳이 빠지면 아래 nat26/nat27 전국 합계가 그만큼 적게 나오는데, 표는
# 멀쩡해 보인다. 2026-09-12 에 같은 유형이 세 군데서 나왔다(사이클 전세가율 차트
# 355d767 · 홈 표 모드 MATRIX_REGIONS · 홈 주간 타일). 전부 '모르는 지역을 조용히
# 건너뛰는' 구조였고 아무것도 빨개지지 않았다. 그래서 시작할 때 대조하고 죽는다.
SIDO17 = ['서울', '경기', '인천', '부산', '대구', '전남광주', '대전', '울산', '세종',
          '강원', '충북', '충남', '전북', '경북', '경남', '제주']
_MODEL = set(z for z in SZ.ORDER if z not in SZ.AGG)
if set(SIDO17) != _MODEL:
    raise SystemExit('SIDO17이 모델과 다르다 — 차이 %s (sido_zones.ORDER 기준으로 맞출 것)'
                     % sorted(set(SIDO17) ^ _MODEL))


def load():
    s = io.open(os.path.join(ROOT, 'data.js'), encoding='utf-8').read()
    adv = json.loads(re.search(
        r'/\*ADV_DATA_START\*/\s*const ADV=(\{.*?\});?\s*/\*ADV_DATA_END\*/', s, re.S).group(1))
    c = io.open(os.path.join(ROOT, 'data-core.js'), encoding='utf-8').read()
    sts = json.loads(re.search(
        r'const STATS=(\{.*?\});\nwindow\.__DATA_CORE__', c, re.S).group(1))
    return adv, sts


def num(v):
    # JS Math.round와 같은 half-up. 파이썬 기본 round()는 은행가 반올림이라
    # 같은 값이 홈과 1 차이가 났다(2026-08-08 감사, zone 페이지와 같은 원인).
    import math as _m
    return format(int(_m.floor(float(v) + 0.5)), ',')


def updown(a, b, tol=0.03):
    """방향어는 반드시 데이터로 판정한다.

    ⚠️ 2026-08-01 실사고: '줄어든다'를 본문에 박아뒀는데 데이터가 105,950 →
    115,411(증가)로 바뀌어 라이브에 정반대 문장이 걸렸다. 매주 재생성되는
    페이지에 방향·비교 단정어를 하드코딩하면 언젠가 반드시 뒤집힌다.
    변화폭이 tol(기본 3%) 안이면 '거의 그대로'로 — 1% 차이를 '늘어난다'고
    쓰면 그것도 과장이다."""
    if not a or not b:
        return '이어진다'
    if abs(b - a) <= abs(a) * tol:
        return '거의 그대로다'
    return '늘어난다' if b > a else '줄어든다'


def ga(w):
    """주격 조사 — 받침 있으면 '이', 없으면 '가' (전남이/경기가)."""
    c = ord(w[-1])
    return w + ('이' if 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 else '가')


def neun(w):
    """보조사 — 받침 있으면 '은', 없으면 '는' (세종은/제주는)."""
    c = ord(w[-1])
    return w + ('은' if 0xAC00 <= c <= 0xD7A3 and (c - 0xAC00) % 28 else '는')


# ---- 공통 템플릿 ----------------------------------------------------------
# zone 페이지와 같은 뼈대·팔레트. CSS 인라인(자기완결) — app.css에 묶지 않는 건
# zone 페이지와 같은 이유(페이지 단독 캐시·앱 셸과 수명 분리).
SHELL = """<!DOCTYPE html>
<html lang="ko">
<head>
<!-- charset은 <head> 첫 줄이어야 한다 — 인코딩 프리스캔이 앞 1024바이트만 보는데
     아래 한글 주석이 앞에 끼면 선언이 그 밖으로 밀린다(2026-08-15 리뷰). -->
<meta charset="UTF-8">
<!-- 기기 단위 GA 제외: ?ga_off=1 로 한 번 들어온 기기는 이후 전송하지 않는다
     (되돌리기 ?ga_off=0). 개발자 본인 트래픽이 Direct 세션의 절반을 차지해
     블로그 유입 측정이 불가능했다. GA 콘솔의 IP 제외는 데스크톱만 커버되고
     모바일 데이터는 CGNAT이라 불가능해서 기기 쪽에 스위치를 둔다.
     ⚠️ gtag 로더보다 반드시 먼저 실행돼야 한다 — 뒤에 두면 안 먹는다. -->
<script>
try{var _p=new URLSearchParams(location.search);
if(_p.has('ga_off')){if(_p.get('ga_off')==='0')localStorage.removeItem('ga_off');
else localStorage.setItem('ga_off','1');}
if(localStorage.getItem('ga_off'))window['ga-disable-G-3FJNG6G1F3']=true;
}catch(e){}
</script>
<script async src="https://www.googletagmanager.com/gtag/js?id=G-3FJNG6G1F3"></script>
<script>window.dataLayer=window.dataLayer||[];function gtag(){dataLayer.push(arguments);}gtag('js',new Date());gtag('config','G-3FJNG6G1F3');</script>
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<link rel="preconnect" href="https://cdn.jsdelivr.net" crossorigin>
<link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css" media="print" onload="this.media='all'">
<noscript><link rel="stylesheet" href="https://cdn.jsdelivr.net/gh/orioncactus/pretendard@v1.3.9/dist/web/variable/pretendardvariable-dynamic-subset.css"></noscript>
<title>__TITLE__</title>
<meta name="description" content="__DESC__">
<link rel="canonical" href="__URL__">
<link rel="icon" type="image/svg+xml" href="/favicon.svg">
<link rel="icon" type="image/png" href="/app_icon.png">
<meta name="theme-color" content="#16203a">
<meta property="og:type" content="article">
<meta property="og:title" content="__OGTITLE__">
<meta property="og:description" content="__DESC__">
<meta property="og:url" content="__URL__">
<meta property="og:image" content="https://www.agongmap.co.kr/og-brand.png">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">__LD__</script>
<style>
:root{--ink:#131e24;--ink2:#4c5f66;--paper:#f4f6f5;--paper2:#e9edeb;--muted:#5e6f74;--line:#c4cec9;--up:#b23b2e;--dn:#2f6db3;__TOKENS__}
*{margin:0;padding:0;box-sizing:border-box}
b,strong{font-weight:600}
body{background:var(--paper);color:var(--ink);word-break:keep-all;overflow-wrap:break-word;
 font-family:'Pretendard Variable','Pretendard',-apple-system,BlinkMacSystemFont,'Apple SD Gothic Neo','Malgun Gothic',sans-serif;
 line-height:1.75;-webkit-font-smoothing:antialiased;padding-bottom:66px}
.wrap{max-width:var(--col-read);margin:0 auto;padding:0 22px}
header{padding:44px 0 24px;text-align:center}
.chip{display:inline-block;font-size:12.5px;font-weight:600;color:#fff;background:var(--ink);padding:5px 14px;margin-bottom:14px}
h1{font-size:var(--h1-doc);font-weight:700;letter-spacing:-.02em;line-height:1.28;margin-bottom:12px}
.lead{font-size:var(--fs-read);color:var(--ink2)}
.big{font-size:clamp(34px,9vw,48px);font-weight:700;letter-spacing:-.02em;margin:6px 0 2px}
.bigsub{font-size:13.5px;color:var(--muted)}
section{padding:20px 0}
h2{font-size:20px;font-weight:700;letter-spacing:-.02em;margin-bottom:10px}
p{margin-bottom:12px;font-size:var(--fs-read)}
p:last-child{margin-bottom:0}
.note{font-size:13px;color:var(--muted);line-height:1.6;margin-top:8px}
.tbl-wrap{overflow-x:auto;margin:6px 0 2px}
table{width:100%;border-collapse:collapse;font-size:14px;font-variant-numeric:tabular-nums}
/* ⚠️ thead에 한정한다. 행 머리(지역명)를 th로 바꾸면서 이 규칙이 tbody까지 먹어
   모든 줄이 표두처럼 렌더됐다(2026-08-08 감사). */
thead th{font-size:12.5px;font-weight:600;color:var(--muted);text-align:right;padding:7px 8px;border-bottom:1.5px solid var(--ink);white-space:nowrap;cursor:pointer;user-select:none}
tbody th{font-weight:400;color:var(--ink);font-size:14px;padding:7px 8px;border-bottom:1px solid var(--line);white-space:nowrap}
th:first-child,td:first-child{text-align:left}
td{padding:7px 8px;border-bottom:1px solid var(--line);text-align:right;white-space:nowrap}
tr.agg td,tr.agg th{background:var(--paper2);font-weight:600}
.up{color:var(--up)}.dn{color:var(--dn)}.mut{color:var(--muted)}
.links{display:grid;gap:10px;margin-top:6px}
.links a{display:block;background:#fff;border:1px solid var(--line);padding:13px 16px;text-decoration:none;color:var(--ink);font-weight:600;font-size:14.5px}
.links a span{display:block;font-weight:400;font-size:13px;color:var(--muted);margin-top:2px}
.links a:hover{border-color:var(--ink)}
footer{padding:28px 0 40px;font-size:13px;color:var(--muted);text-align:center}
footer a{color:var(--ink)}
.disc{margin-top:10px;font-size:11.5px;line-height:1.6;color:var(--muted)}
.bottomnav{position:fixed;bottom:0;left:0;right:0;height:62px;background:var(--ink);display:flex;justify-content:center;z-index:100;box-shadow:0 -4px 18px rgba(22,32,58,.28)}
.nav-btn{flex:1;max-width:220px;display:flex;flex-direction:column;align-items:center;justify-content:center;gap:3px;color:#97a0b8;font-size:11.5px;font-weight:600;text-decoration:none}
.nav-btn svg{display:block}
.nav-btn:hover{color:#fff}
.nav-btn:focus-visible{outline:2px solid #fff;outline-offset:-3px}
@media (prefers-reduced-motion:reduce){*{scroll-behavior:auto!important}}
.skip{position:absolute;left:8px;top:-60px;z-index:100;padding:10px 14px;background:var(--ink);color:#fff;font-weight:600;font-size:14px;text-decoration:none;border-radius:3px}
.skip:focus{top:8px;outline:2px solid #fff;outline-offset:2px}
</style>
</head>
<body>
<a class="skip" href="#main">본문으로 건너뛰기</a>
__BODY__
<footer><div class="wrap">
  <b>아공맵</b> — 아파트 · 공급량 · 투자지도<br>
  <a href="/">agongmap.co.kr</a> · 자료: __SRC__
  <div class="disc">공공 데이터를 가공한 참고 자료이며 투자자문이 아닙니다. 투자 판단과 책임은 이용자에게 있습니다.</div>
</div></footer>

<nav class="bottomnav">
  <a class="nav-btn" href="/"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M3 11l9-8 9 8M5 10v10h14V10" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>홈</span></a>
  <a class="nav-btn" href="/zone/"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M12 21s-7-5.8-7-11a7 7 0 0 1 14 0c0 5.2-7 11-7 11z" fill="none" stroke="currentColor" stroke-width="2" stroke-linejoin="round"/><circle cx="12" cy="10" r="2.5" fill="none" stroke="currentColor" stroke-width="2"/></svg><span>지역</span></a>
  <a class="nav-btn" href="/#stats"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M4 20V10M10 20V4M16 20v-7M22 20H2" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/></svg><span>통계</span></a>
  <a class="nav-btn" href="/cycle/"><svg viewBox="0 0 24 24" width="22" height="22" aria-hidden="true"><path d="M20 12a8 8 0 1 1-2.34-5.66" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round"/><path d="M20.3 3.7v5h-5" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"/></svg><span>사이클</span></a>
</nav>

<script>
(function(){
  var t=document.getElementById('utable'); if(!t) return;
  var tb=t.tBodies[0], ths=t.tHead.rows[0].cells, cur=-1, dir=1;
  function val(row,k,isNum){
    var s=row.cells[k].textContent.trim();
    return isNum ? (parseFloat(s.replace(/[^0-9.-]/g,''))||-1e9) : s;
  }
  /* 마우스로만 정렬되던 것을 키보드에서도 되게 한다 — 안내문이 '표두를 누르면 정렬'인데
     탭으로는 표두에 닿지도 않았다(2026-08-08 감사). aria-sort로 현재 정렬 상태도 알린다. */
  Array.prototype.forEach.call(ths, function(h,i){
    h.setAttribute('scope','col');
    /* ⚠️ role="button"을 주면 columnheader 역할이 사라져 열 머리 연결이 끊기고
       aria-sort도 무효가 된다(columnheader/rowheader에서만 유효). 키보드 접근은
       tabindex + keydown으로 충분하다(2026-08-08 감사). */
    h.tabIndex=0;
    h.setAttribute('aria-sort','none');
    h.title='누르면 이 열로 정렬';
    function sort(){
      var isNum=h.hasAttribute('data-num');
      dir=(cur===i)?-dir:-1; cur=i;
      var rows=Array.prototype.slice.call(tb.rows).filter(function(r){return !r.classList.contains('agg')});
      var aggs=Array.prototype.slice.call(tb.rows).filter(function(r){return r.classList.contains('agg')});
      rows.sort(function(a,b){var x=val(a,i,isNum),y=val(b,i,isNum);return (x<y?-1:x>y?1:0)*dir;});
      aggs.concat(rows).forEach(function(r){tb.appendChild(r);});
      Array.prototype.forEach.call(ths,function(o){o.setAttribute('aria-sort','none');});
      h.setAttribute('aria-sort', dir>0?'ascending':'descending');
    }
    h.addEventListener('click', sort);
    h.addEventListener('keydown', function(e){
      if(e.key==='Enter'||e.key===' '){ e.preventDefault(); sort(); }
    });
  });
  /* 행 머리(지역명)를 프로그램적으로 붙인다 — 20열 표에서 이게 없으면 스크린리더가
     칸을 읽을 때 어느 지역인지 말하지 않는다. */
  Array.prototype.forEach.call(tb.rows, function(r){
    var c=r.cells[0]; if(!c || c.tagName==='TH') return;
    var th=document.createElement('th'); th.scope='row'; th.innerHTML=c.innerHTML;
    th.className=c.className; c.parentNode.replaceChild(th,c);
  });
})();
</script>
</body>
</html>
"""


# 조판 치수 토큰(백로그 24-6)은 app.css :root 가 정본이다. 이 껍데기는 app.css 를 읽지 않으므로
# 생성할 때 그 선언을 그대로 옮겨 싣는다 — 손으로 옮긴 사본은 정본이 바뀌어도 조용히 남는다.
TYPE_TOKENS = ('--h1-report', '--h1-doc', '--col-read', '--col-wide', '--fs-read', '--fs-dense')


def type_tokens(css=None):
    if css is None:
        css = io.open(os.path.join(ROOT, 'app.css'), encoding='utf-8').read()
    out = []
    for name in TYPE_TOKENS:
        got = re.findall(r'(?<![\w-])' + re.escape(name) + r'\s*:\s*([^;]+);', css)
        if len(got) != 1:
            raise SystemExit('app.css 에서 %s 선언을 하나로 찾지 못했다(%d개)' % (name, len(got)))
        out.append('%s:%s' % (name, got[0].strip()))
    return ';'.join(out)


def fill(shell, **kw):
    out = shell.replace('__TOKENS__', type_tokens())
    for k, v in kw.items():
        out = out.replace('__' + k.upper() + '__', v)
    # 랜드마크: 머리글 뒤부터 바닥글 앞까지가 본문이다(2026-09-18 접근성 점검 — 어느 페이지에도 <main> 이 없었다).
    if '<main' not in out and '</header>' in out and '<footer' in out:
        out = out.replace('</header>', '</header>\n<main id="main">', 1).replace('<footer', '</main>\n<footer', 1)
    return out


def not_before_pub(iso):
    """dateModified가 datePublished보다 과거가 되지 않게 막는다.
    두 페이지의 lastmod는 '마지막 실적 분기'에서 오는데(데이터가 안 바뀌면
    안 움직이게 하려는 의도), 그 분기가 페이지 공개일보다 앞서면
    '2026-07-29 발행 · 2026-06-01 수정'이라는 불가능한 조합이 나간다
    (2026-08-07 감사에서 실제로 그 상태였다)."""
    return max(iso, PUBLISHED)


def ld_pack(headline, desc, url, crumb_name, modified):
    modified = not_before_pub(modified)
    return json.dumps([{
        "@context": "https://schema.org", "@type": "Article",
        "headline": headline,
        "description": desc,
        "datePublished": PUBLISHED, "dateModified": modified,
        "author": {"@type": "Organization", "name": "아공맵"},
        "publisher": {"@type": "Organization", "name": "아공맵"},
        "mainEntityOfPage": url,
    }, {
        "@context": "https://schema.org", "@type": "BreadcrumbList",
        "itemListElement": [
            {"@type": "ListItem", "position": 1, "name": "아공맵", "item": SITE + '/'},
            {"@type": "ListItem", "position": 2, "name": crumb_name},
        ],
    }], ensure_ascii=False, indent=2)


# ---- 전세가율 (/jeonse-ratio/) --------------------------------------------
# 전세가율 기준월에 값이 전부 있어야 하는 지역. /jeonse-ratio/ 는 전국 머리 숫자와 시도 표를 그린다.
JEONSE_NEED = ('전국',) + tuple(SIDO17)


def _warn(msg):
    """배치 로그에 경고를 남긴다. GitHub Actions 에서는 실행 화면의 주석(::warning::)으로도 뜬다."""
    print(('::warning::' if os.environ.get('GITHUB_ACTIONS') else '  ⚠️ ') + msg)


def jeonse_ref_index(j, need):
    """전세가율 기준월의 열 번호 — need 의 지역이 **전부** 채워진 마지막 달.

    /jeonse-ratio/(build_jeonse)와 /cycle/ 전세가율 차트(refresh_cycle_data.build_jratio)가 이 규칙 하나로
    달을 고른다. merge_basic 은 새 달을 전 지역 None 열로 먼저 만들고 원천이 준 지역만 채운다. 원천이 행
    이름을 바꾸거나(2026.06 지방권, 2026.07 6대광역시·9개도가 그렇게 비었다) 통합 지역을 다시 쪼개면 최신
    열에 필요한 지역이 빈다. 예전엔 dates[-1] 을 그대로 읽어 build_jeonse 가 TypeError, build_jratio 가 0
    나누기·RuntimeError 로 죽었고, 둘 다 배치에서 `exit 1` 이라 그날 데이터 커밋 전체가 막혔다(2026-09-26
    데이터 감사). '원천 분류가 바뀐 달은 보류한다'는 원칙대로 직전 완비 달을 쓰고 건너뛴 달은 경고로 남긴다.
    화면에는 실제로 읽은 달이 찍히므로 감시(check_freshness 파생 페이지 대조)가 데이터 최신월과의 차이를
    경보로 올린다. 완비 달이 하나도 없으면 멈춘다 — 모델과 원천이 통째로 어긋났다는 뜻이다.
    """
    dates, ser = j['dates'], j['series']

    def ok(r, k):
        s = ser.get(r) or []
        return k < len(s) and s[k] is not None
    for k in range(len(dates) - 1, -1, -1):
        if all(ok(r, k) for r in need):
            if k != len(dates) - 1:
                held = ['%s(%s 없음)' % (dates[i], ', '.join(r for r in need if not ok(r, i)))
                        for i in range(k + 1, len(dates))]
                _warn('전세가율 최신 %d개월을 보류하고 %s 기준으로 굽는다 — %s'
                      % (len(held), dates[k], '; '.join(held)))
            return k
    raise RuntimeError('전세가율에 %s 이(가) 전부 채워진 달이 없다 — 원천 분류가 바뀌었는지 확인'
                       % ', '.join(need))


def build_jeonse(sts):
    j = sts['전세가율']
    dates, ser = j['dates'], j['series']
    li = jeonse_ref_index(j, JEONSE_NEED)
    prd = dates[li]                       # '2026.05'
    prd_iso = prd.replace('.', '-') + '-01'

    # 1년 전 칸은 인덱스 차(li-12)가 아니라 라벨로 찾는다 — 빠진 달이 있으면 13달 전과 견주게 된다(감사 #17).
    ya = SZ.month_back(dates, li, 12)

    def at(name, i):
        if i is None or name not in ser:
            return None
        v = ser.get(name) or []
        return v[i] if i < len(v) else None

    aggs = ['전국', '수도권', '지방']
    rows, vals = [], []
    for name in aggs + SIDO17:
        cur, ago = at(name, li), at(name, ya)
        if cur is None:
            continue
        d = None if ago is None else round(cur - ago, 1)
        if name in SIDO17:
            vals.append((name, cur, d))
        rows.append((name, cur, ago, d))
    # 시도는 현재값 내림차순, 집계 3행은 상단 고정
    body_rows = [r for r in rows if r[0] in aggs] + \
        sorted([r for r in rows if r[0] not in aggs], key=lambda r: -r[1])

    def cell_d(d):
        if d is None:
            return '<td class="mut">·</td>'
        cls = 'up' if d > 0 else 'dn' if d < 0 else 'mut'
        return '<td class="%s">%+.1f%%p</td>' % (cls, d)

    trs = []
    for name, cur, ago, d in body_rows:
        trs.append('<tr%s><td>%s</td><td>%.1f%%</td><td>%s</td>%s</tr>' % (
            ' class="agg"' if name in aggs else '', name, cur,
            '·' if ago is None else '%.1f%%' % ago, cell_d(d)))

    nat = at('전국', li)
    nat_ago = at('전국', ya)
    # 1년 전 값이 없으면 그 비교 문구만 뺀다. 예전엔 None 과 빼기를 해 생성기가 죽었고, 배치는 그날 커밋을 통째로 막았다.
    nat_d = None if nat_ago is None else round(nat - nat_ago, 1)
    hi = max(vals, key=lambda v: v[1])
    lo = min(vals, key=lambda v: v[1])
    moved = [v for v in vals if v[2] is not None]
    up_most = max(moved, key=lambda v: v[2]) if moved else None
    natd_desc = '' if nat_d is None else '로 1년 전보다 %+.1f%%p' % nat_d
    natd_sub = '' if nat_d is None else ' · 1년 전 대비 %+.1f%%p' % nat_d
    upm_p = ('' if up_most is None else
             '1년 새 가장 크게 오른 곳은 <strong>%s(%+.1f%%p)</strong>. ' % (up_most[0], up_most[2]))

    title = '전세가율이란 — 전국·시도별 아파트 전세가율 현황 %s | 아공맵' % prd
    desc = ('전세가율은 매매가 대비 전세가 비율. %s 기준 전국 아파트 전세가율은 %.1f%%%s. '
            '%s %.1f%%로 가장 높고 %s %.1f%%. 시도별 현황과 사이클 신호로서의 의미를 데이터로 정리했다.'
            ) % (prd, nat, natd_desc or '다', ga(hi[0]), hi[1], neun(lo[0]), lo[1])
    url = SITE + '/jeonse-ratio/'

    body = """<header class="wrap">
  <div class="chip">지표 해설</div>
  <h1>전세가율 — 매매가 대비 전세가,<br>실수요의 체온계</h1>
  <div class="big">%(nat).1f%%</div>
  <div class="bigsub">전국 아파트 전세가율 · %(prd)s 기준%(natd)s</div>
</header>

<section class="wrap">
  <h2>전세가율이란</h2>
  <p><strong>전세가율 = 전세가 ÷ 매매가 × 100.</strong> 매매가 10억 아파트의 전세가 6억이면 전세가율 60%%다.</p>
  <p>전세가에는 시세차익 기대가 없다 — 세입자는 오를 것 같다고 전세금을 더 내지 않는다. 그래서 전세가는 <strong>거주 가치의 순수한 값</strong>이고, 전세가율은 매매가에 낀 기대(프리미엄)가 얼마나 되는지를 보여준다. 전세가율이 낮을수록 매매가에 미래 기대가 많이 반영된 것이고, 높을수록 가격이 실거주 가치에 붙어 있는 것이다.</p>
</section>

<section class="wrap">
  <h2>시도별 현황 (%(prd)s)</h2>
  <div class="tbl-wrap"><table id="utable" aria-label="시도별 전세가율 현황">
    <thead><tr><th>지역</th><th data-num>전세가율</th><th data-num>1년 전</th><th data-num>변화</th></tr></thead>
    <tbody>
%(trs)s
    </tbody>
  </table></div>
  <div class="note">표두를 누르면 정렬. 자료: KOSIS·한국부동산원 「매매가격 대비 전세가격비」, 매월 갱신.</div>
</section>

<section class="wrap">
  <h2>지금 표에서 읽히는 것</h2>
  <p>가장 높은 곳은 <strong>%(hi)s %(hiv).1f%%</strong>, 가장 낮은 곳은 <strong>%(lo)s %(lov).1f%%</strong>다. 서울처럼 전세가율이 낮은 시장은 매매가가 거주 가치보다 기대에 기대어 있다는 뜻이고(투자성 시장), 전세가율이 높은 지방 시장은 가격이 실수요에 붙어 있어 갭이 작다(실거주성 시장).</p>
  <p>%(upm)s전세가율 상승은 사이클에서 중요한 신호다 — <strong>공급이 부족하면 전세가 먼저 오르고, 전세가율이 차오르면 매매를 밀어 올린다.</strong> 갭투자 비용이 줄어드는 지점이기도 하다. 이 연결고리는 20년 국가 통계로 검증해 리포트에 정리해 뒀다.</p>
</section>

<section class="wrap">
  <h2>더 보기</h2>
  <div class="links">
    <a href="/#stats-adv-bubble">버블밴드<span>전세가율로 계산한 지역별 고평가·저평가 밴드</span></a>
    <a href="/#stats-basic">기본통계 차트<span>전세가율 2012년부터 월별 추이를 지역별로</span></a>
    <a href="/moveins/">아파트 입주물량<span>전세가율을 움직이는 원인 — 시도별 입주 예정</span></a>
    <a href="/zone/">시도별 공급 분석<span>__NSIDO__개 시도를 부족·과잉 등급으로</span></a>
    <a href="/cycle/">아파트 사이클 리포트<span>전세가율이 매매를 미는 고리, 데이터 검증</span></a>
  </div>
</section>
""" % dict(nat=nat, natd=natd_sub, prd=prd, trs='\n'.join(trs),
           hi=hi[0], hiv=hi[1], lo=lo[0], lov=lo[1], upm=upm_p)

    html = fill(SHELL, title=title, ogtitle='전세가율 — 전국 %.1f%%, 시도별 현황' % nat,
                desc=desc, url=url, body=body,
                ld=ld_pack('전세가율 — 전국·시도별 현황과 의미', desc, url, '전세가율', prd_iso),
                src='KOSIS 한국부동산원 매매가격 대비 전세가격비',
                nsido=str(len(SIDO17)))   # 본문을 넣은 뒤에 치환되도록 마지막에 둔다
    return html, not_before_pub(prd_iso)


# ---- 입주물량 (/moveins/) --------------------------------------------------
def build_moveins(adv):
    o = adv['occupancy']
    regs, rows = o['regions'], o['rows']
    # ⚠️ o['ref']는 '분기' 수요 기준선이다(통계탭 occCls가 분기값과 직접 비교,
    # UI 문구도 '분기 수요 기준선'). 연간 표에서는 반드시 ×4로 환산할 것 —
    # 안 하면 수도권이 '과잉 224%'로 나와 사이트 전체 서사와 정반대가 된다.
    ref = {k: (v * 4 if v else None) for k, v in o['ref'].items()}
    idx = {r: i for i, r in enumerate(regs)}
    last_act = [r['p'] for r in rows if not r.get('e')][-1]     # 마지막 실적 분기 '2026Q2'
    # ⚠️ 분기를 버리지 말 것. prd=last_act[:4]로 연도만 남기면 '.' 분기가 영영
    # 거짓이 되어 mod_iso가 그 해 1월 1일로 굳는다 — /moveins/의 dateModified가
    # datePublished보다 과거가 되고(불가능한 조합) sitemap lastmod가 1년 내내
    # 안 움직였다(2026-08-07 감사). 분기의 마지막 달 1일로 찍는다.
    prd = last_act
    m = re.match(r'^(\d{4})Q([1-4])$', prd)
    if m:
        mod_iso = '%s-%02d-01' % (m.group(1), int(m.group(2)) * 3)
    elif '.' in prd:
        mod_iso = prd.replace('.', '-') + '-01'
    else:
        mod_iso = prd[:4] + '-01-01'
    # 머리 연도(Y)는 **마지막 실적 분기의 해**다. 표는 Y−1(실적)·Y(실적+예정)·Y+1(예정) 세 해.
    # 예전엔 '2026'을 문자로 박아 2027년이 와도 2026년을 머리로 내걸었다(2026-09-23 전체 점검).
    # 달력 날짜가 아니라 데이터에서 읽는 이유: 1~5월에는 그해 1분기 실적이 아직 없어, 달력을
    # 따르면 실적이 한 분기도 없는 해를 '올해 입주물량'으로 내건다. Y+1 은 착공을 12분기 밀어
    # 추정하므로 늘 채워진다.
    y0 = int(last_act[:4])
    years = [str(y0 - 1), str(y0), str(y0 + 1)]
    Y, Y1 = years[1], years[2]

    def ytot(name, y):
        i = idx[name]
        vs = [r['v'][i] for r in rows if r['p'].startswith(y) and r['v'][i] is not None]
        return sum(vs) if vs else None

    def pct_cell(t, rf):
        if t is None or not rf:
            return '<td class="mut">·</td>'
        p = t / rf * 100
        # ⚠️ 이 값은 '적정 대비 얼마나 채웠나'(충족률)다. 39%에 ' 부족'을 붙이면
        # '39% 모자라다'로 읽히는데 실제로는 61% 모자란 것이다(2026-08-07 감사).
        # ⚠️ 색은 **표시값 기준**으로 판정한다. raw로 가르면 69.6%가 '70% 충족'으로
        # 찍히면서 '70% 미만' 색을 받아, 같은 페이지의 범례와 어긋난다
        # (충남이 실제로 그랬다, 2026-08-08 감사).
        shown = num(p)
        p = float(shown.replace(',', ''))
        cls = 'up' if p < 70 else 'dn' if p > 130 else 'mut'
        return '<td class="%s">%s%% 충족</td>' % (cls, shown)

    # ⚠️ regs에는 전국·수도권·지방 집계 3종이 섞여 있다. 그대로 정렬하면 '시도별'
    # 표에 전국·지방이 시도인 척 들어가 이중계상된다(2026-08-07 감사).
    # 수도권만 맨 위 집계행으로 두고 나머지 집계는 뺀다.
    order = ['수도권', '서울', '경기', '인천'] + sorted(
        [r for r in SIDO17 if r not in ('서울', '경기', '인천')],
        key=lambda r: -(ytot(r, Y) or 0))
    trs = []
    for name in order:
        t = {y: ytot(name, y) for y in years}
        rf = ref.get(name)
        trs.append('<tr%s><td>%s</td>%s<td>%s</td>%s</tr>' % (
            ' class="agg"' if name == '수도권' else '', name,
            ''.join('<td>%s</td>' % ('·' if t[y] is None else num(t[y])) for y in years),
            '·' if not rf else num(rf), pct_cell(t[Y], rf)))

    nat26 = sum(ytot(r, Y) or 0 for r in SIDO17)       # 이름은 이력상 26·27 — 값은 Y·Y+1 이다
    nat27 = sum(ytot(r, Y1) or 0 for r in SIDO17)
    sudo = {y: ytot('수도권', y) for y in years}
    shorts = sorted([(r, (ytot(r, Y) or 0) / ref[r] * 100)
                     for r in SIDO17 if ref.get(r)], key=lambda x: x[1])
    lo1, hi1 = shorts[0], shorts[-1]

    title = '아파트 입주물량 — %s·%s 전국 시도별 입주 예정 | 아공맵' % (Y, Y1)
    desc = ('아파트 입주물량은 준공(사용승인) 뒤 실제로 입주가 시작되는 물량. %s년 전국 %s세대, '
            '%s년 %s세대 예정. 수도권은 %s→%s세대. 적정수요와 비교한 시도별 부족·과잉과 '
            '전세·매매에 미치는 영향을 정리했다.') % (
        Y, num(nat26), Y1, num(nat27), num(sudo[Y] or 0), num(sudo[Y1] or 0))
    url = SITE + '/moveins/'

    body = """<header class="wrap">
  <div class="chip">지표 해설</div>
  <h1>아파트 입주물량 —<br>공급이 시장에 도착하는 순간</h1>
  <div class="big">%(nat26)s</div>
  <div class="bigsub">%(Y)s년 전국 입주물량(실적+예정, 세대) · %(Y1)s년 %(nat27)s세대</div>
</header>

<section class="wrap">
  <h2>입주물량이란</h2>
  <p><strong>준공(사용승인)을 마치고 실제 입주가 시작되는 아파트 물량</strong>이다. 인허가·착공이 '공급 예고'라면 입주는 <strong>공급의 도착</strong>이다 — 열쇠를 받은 집주인과 세입자가 시장에 실물로 등장한다.</p>
  <p>입주가 몰리면 가장 먼저 눌리는 건 매매가 아니라 <strong>전세</strong>다. 잔금을 치르려는 집주인들이 전세를 한꺼번에 내놓기 때문이다. 반대로 입주 절벽이 오면 전세부터 마르고, 전세가율이 차오르며 매매를 민다. 그래서 입주물량은 아파트 사이클의 타이밍을 읽는 핵심 지표다.</p>
</section>

<section class="wrap">
  <h2>시도별 연간 입주물량 (세대)</h2>
  <div class="tbl-wrap"><table id="utable" aria-label="시도별 연간 입주물량">
    <thead><tr><th>지역</th><th data-num>%(Y0)s</th><th data-num>%(Y)s</th><th data-num>%(Y1)s</th><th data-num>적정수요/년</th><th data-num>%(Y)s 충족률</th></tr></thead>
    <tbody>
%(trs)s
    </tbody>
  </table></div>
  <div class="note">표두를 누르면 정렬. %(lastact)s까지 준공 실적, 이후는 <b>착공 실적을 3년 뒤로 밀어</b> 추정한 값입니다(전환율 %(conv)s — 착공한 물량의 약 %(convp)d%%가 3년 뒤 준공). 적정수요는 가격이 하락에서 상승으로 돌아선 시점의 입주물량을 실측해 잡은 분기 기준선을 연환산(×4)한 고정 상수이며, 서울·경기·인천과 세종·제주는 추정치입니다. 자료: 국토교통부 주택건설실적(준공·착공), 분기마다 갱신.</div>
</section>

<section class="wrap">
  <h2>지금 표에서 읽히는 것</h2>
  <p>%(Y)s년 적정수요를 가장 덜 채운 곳은 <strong>%(lo1)s(%(lo1p)d%% 충족)</strong>, 가장 많이 채운 곳은 <strong>%(hi1)s(%(hi1p)d%% 충족)</strong>다. 공급이 적정선의 70%%를 밑돌면 전세부터 조여드는 구간, 130%%를 넘으면 입주장이 전세를 누르는 구간으로 본다. 이 충족률은 한 해의 입주만 보므로, 지난 4년 쌓인 부족과 앞으로 3년을 함께 보는 <a href="/zone/">지역 판정</a>과 다를 수 있다.</p>
  <p>수도권은 %(Y)s년 %(sudo26)s세대에서 %(Y1)s년 %(sudo27)s세대로 %(sudodir)s. 시도 안에서도 시군구별로 사정이 갈리므로, 이 수치는 시장의 방향을 보는 값이지 개별 단지의 사정을 말해 주지 않는다.</p>
</section>

<section class="wrap">
  <h2>더 보기</h2>
  <div class="links">
    <a href="/#stats-adv-occ">입주물량 차트<span>분기별 추이를 적정수요와 견줘 지역별로</span></a>
    <a href="/zone/">시도별 공급 분석<span>__NSIDO__개 시도의 부족·과잉을 등급으로</span></a>
    <a href="/jeonse-ratio/">전세가율<span>입주물량이 움직이는 결과 — 시도별 현황</span></a>
    <a href="/cycle/">아파트 사이클 리포트<span>입주 → 전세 → 매매로 이어지는 고리, 데이터 검증</span></a>
  </div>
</section>
""" % dict(nat26=num(nat26), nat27=num(nat27), trs='\n'.join(trs),
           lastact=last_act.replace('Q', '년 ') + '분기',
           conv='%.3f' % SZ.CONV, convp=int(round(SZ.CONV * 100)),
           lo1=lo1[0], lo1p=round(lo1[1]), hi1=hi1[0], hi1p=round(hi1[1]),
           sudo26=num(sudo[Y] or 0), sudo27=num(sudo[Y1] or 0),
           sudodir=updown(sudo[Y], sudo[Y1]), Y0=years[0], Y=Y, Y1=Y1)

    html = fill(SHELL, title=title,
                ogtitle='아파트 입주물량 — %s년 전국 %s세대' % (Y, num(nat26)),
                desc=desc, url=url, body=body,
                ld=ld_pack('아파트 입주물량 — 시도별 입주 예정과 의미', desc, url, '입주물량', mod_iso),
                src='국토교통부 주택건설실적(준공·착공)',
                nsido=str(len(SIDO17)))   # 본문을 넣은 뒤에 치환되도록 마지막에 둔다
    return html, not_before_pub(mod_iso)


# ---- sitemap ---------------------------------------------------------------
def update_sitemap(entries):
    """entries: [(path('/moveins/'), lastmod_iso)] — 있으면 lastmod 갱신, 없으면 추가."""
    p = os.path.join(ROOT, 'sitemap.xml')
    x = io.open(p, encoding='utf-8').read()
    for path, lm in entries:
        loc = SITE + path
        pat = r'(<loc>%s</loc>\s*<lastmod>)[^<]*(</lastmod>)' % re.escape(loc)
        if re.search(pat, x):
            x = re.sub(pat, r'\g<1>%s\g<2>' % lm, x)
        else:
            block = ('\n  <url>\n    <loc>%s</loc>\n    <lastmod>%s</lastmod>\n'
                     '    <changefreq>weekly</changefreq>\n    <priority>0.8</priority>\n  </url>'
                     % (loc, lm))
            x = x.replace('</urlset>', block + '\n</urlset>')
    io.open(p, 'w', encoding='utf-8', newline='\n').write(x)


# 손으로 관리하는 페이지 — 생성기가 없어서 sitemap lastmod 를 아무도 안 고쳤다. /faq/ 는 08-06 모델
# 개편으로 본문이 바뀌었는데 07-16 에 멈춰 있었고, /privacy/ 는 lastmod 가 아예 없었다(2026-09-23 점검,
# 백로그 29). 배치마다 그 파일의 마지막 커밋 날짜로 따라간다. /cycle/ 는 데이터 칸을 배치가 갈아끼우므로
# refresh_cycle_data 가 따로 맞춘다.
HAND_PAGES = (('/faq/', 'faq/index.html'), ('/about/', 'about/index.html'),
              ('/privacy/', 'privacy/index.html'), ('/burini-test/', 'burini-test/index.html'),
              ('/investor-test/', 'investor-test/index.html'), ('/redev-test/', 'redev-test/index.html'))


def _git(root, *args):
    import subprocess
    try:
        r = subprocess.run(['git'] + list(args), cwd=root, capture_output=True, timeout=30,
                           encoding='utf-8', errors='replace')
    except Exception:
        return None
    return r.stdout.strip() if r.returncode == 0 else None


def hand_lastmods(root=None):
    """[(경로, 마지막 커밋 날짜)] — 날짜를 믿을 수 없는 파일은 뺀다.

    ⚠️ 얕은 클론(배치 커밋 잡은 fetch-depth 200)에서 창 밖의 파일은 경계 커밋이 파일을 통째로
    '추가'한 것처럼 보여, 그 커밋 날짜가 마지막 수정일로 잘못 나온다. 경계 커밋(.git/shallow)이면 뺀다.
    ⚠️ shallow 파일 위치는 `--git-path shallow` 로 묻는다. `--git-dir` 에 'shallow' 를 붙이면 작업
    트리(git worktree)에서는 .git/worktrees/<이름>/shallow 라는 없는 파일을 보게 되어 경계 커밋을
    믿었다 — shallow 는 공통 디렉터리에 있다(2026-09-26 데이터 감사).
    """
    root = root or ROOT
    shallow = set()
    sp = _git(root, 'rev-parse', '--git-path', 'shallow')
    if sp:
        sp = sp if os.path.isabs(sp) else os.path.join(root, sp)
        if os.path.exists(sp):
            shallow = set(io.open(sp, encoding='utf-8').read().split())
    out = []
    for path, rel in HAND_PAGES:
        got = _git(root, 'log', '-1', '--format=%H %cs', '--', rel)
        if not got:
            continue
        sha, day = got.split()
        if sha in shallow:
            continue
        out.append((path, day))
    return out


def bump_sitemap(entries, root=None):
    """entries 의 lastmod 를 **앞으로만** 옮긴다(없으면 넣는다). 날짜가 뒤로 가는 일은 없다."""
    p = os.path.join(root or ROOT, 'sitemap.xml')
    x = io.open(p, encoding='utf-8').read()
    for path, lm in entries:
        loc = SITE + path
        m = re.search(r'<loc>%s</loc>\s*<lastmod>([^<]*)</lastmod>' % re.escape(loc), x)
        if m:
            if m.group(1) < lm:
                x = x[:m.start(1)] + lm + x[m.end(1):]
            continue
        # lastmod 가 없는 항목(한 줄로 적힌 /privacy/ 등)은 loc 뒤에 넣는다
        m = re.search(r'<loc>%s</loc>' % re.escape(loc), x)
        if m:
            x = x[:m.end()] + '<lastmod>%s</lastmod>' % lm + x[m.end():]
    io.open(p, 'w', encoding='utf-8', newline='\n').write(x)


def main():
    adv, sts = load()
    out = []
    for sub, (html, lm) in (
            ('jeonse-ratio', build_jeonse(sts)),
            ('moveins', build_moveins(adv))):
        d = os.path.join(ROOT, sub)
        os.makedirs(d, exist_ok=True)
        io.open(os.path.join(d, 'index.html'), 'w', encoding='utf-8', newline='\n').write(html)
        out.append(('/%s/' % sub, lm))
    update_sitemap(out)
    hand = hand_lastmods()
    bump_sitemap(hand)
    print('indicator pages: %s' % ', '.join('%s(%s)' % e for e in out))
    print('hand pages lastmod: %s' % ', '.join('%s(%s)' % e for e in hand))


if __name__ == '__main__':
    main()
