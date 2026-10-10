/* 아공맵 홈 본문 스크립트 — 2026-09-16 index.html 인라인에서 분리(백로그 10, 동결 창).
   ⚠️ index.html 과 한 몸이다. sw.js 는 이 파일을 network-first 로 받는다(새 마크업 + 옛 스크립트 조합 방지).
   도구·시험은 이 파일을 직접 열지 말고 tools/home_src.py 로 읽는다.
   퀴즈·통계 화면 코드는 home-quiz.js·home-stats.js 로 떼어 그 화면을 열 때 받는다(B11, 아래 PARTS). */
/* 판 표식(홈 마케팅 검수 C11·MOB-9, 2026-09-27). 서비스워커는 HTML 과 이 파일을 **따로** network-first(3.5초
   한도)로 받는다. 배포 직후 느린 망에서 HTML(14KB)은 새 판으로 오고 이 파일(78KB)만 한도를 넘겨 옛 캐시로 오면
   새 마크업 위에서 옛 스크립트가 돈다 — Chromium 에서 home-app.js 응답만 5초 늦춰 재현했다(2초면 안 섞인다).
   그래서 HTML 의 <html data-build> 와 이 파일의 HOME_BUILD 를 견줘 다르면 **한 번** 새로고침한다. 그사이 늦게 온
   응답이 캐시에 들어가 두 번째에는 맞는다. 같은 HTML 판으로는 두 번 새로고침하지 않고(sessionStorage), 저장소를
   못 쓰면 아예 새로고침하지 않는다(무한 반복 방지). 판 표식이 없는 HTML(표식 이전 판)은 비교하지 않는다.
   새로고침 뒤 첫 부팅이 결과를 build_reload 로 한 번 잰다(현장에서 실제로 일어나는지 보려고).
   판 값은 sw.js 의 VERSION 과 같다 — VERSION 을 올리면 index.html data-build 와 여기, 분할 파일(home-quiz.js·home-stats.js)의
   판 표식도 같이(test_home_build). 분할 파일 쪽 대조는 아래 partBuildOk(B11). */
const HOME_BUILD='v188';
let BUILD_RELOAD=false;
(function(){
  try{
    const html=document.documentElement.getAttribute('data-build')||'', k='agongmap-build';
    let seen=sessionStorage.getItem(k)||'';
    if(seen.slice(-1)==='!'){   // 방금 판이 달라 새로고침했다
      seen=seen.slice(0,-1); sessionStorage.setItem(k,seen);
      /* 분할 파일 판이 달라 새로고침했으면 'quiz:v165' 식(B11). 그때는 fixed 를 싣지 않는다 — 분할 파일은 그 화면을 다시
         열어야 받으므로 새로고침 직후엔 맞았는지 모른다(HTML·본문 판만 보고 true 라 적으면 틀린 기록이 된다). */
      const part=sessionStorage.getItem('agongmap-build-part')||'';
      sessionStorage.removeItem('agongmap-build-part');
      track('build_reload',part?{build_html:html,build_js:HOME_BUILD,part:part}
                               :{build_html:html,build_js:HOME_BUILD,fixed:html===HOME_BUILD});
    }
    if(!html||html===HOME_BUILD||seen===html)return;
    sessionStorage.setItem(k,html+'!');
    BUILD_RELOAD=true;
    location.reload();
  }catch(e){}
})();


const FONT="'Pretendard Variable','Pretendard',-apple-system,'Malgun Gothic',sans-serif";
const INK="#131e24",INK2="#4c5f66",GRID="#dde4e1",MUTED="#5e6f74";
const MAEMAE="#c0392b",JEONSE="#6c4ab6",STOCK="#1f8a70",FLOW="#d99a00";
/* Chart.js는 defer라 이 시점엔 아직 없다 — boot()에서 부른다. */
function chartSetup(){
  Chart.defaults.font.family=FONT;Chart.defaults.font.size=12;Chart.defaults.color=INK2;
  Chart.defaults.plugins.legend.display=false;
}
/* 차트 라이브러리(약 70KB)와 카카오 SDK(약 29KB)는 홈 첫 로딩에서 받지 않는다(2026-09-15 점검 후속 ⑦).
   차트는 통계 화면에서만, 카카오는 공유할 때만 쓴다. 그리기·공유 함수는 라이브러리가 없으면 받은 뒤
   자기 자신을 다시 부른다(needChart·needKakao). 동시에 여러 번 불려도 스크립트는 한 번만 붙인다. */
function loadScript(src){
  return new Promise((res,rej)=>{
    const el=document.createElement('script'); el.src=src; el.async=true;
    el.onload=()=>res(); el.onerror=()=>{ el.remove(); rej(new Error('load '+src)); };
    document.head.appendChild(el);
  });
}
let CHART_P=null;
function loadChart(){
  if(window.Chart)return Promise.resolve();
  if(!CHART_P)CHART_P=loadScript('/chart-4.4.1.umd.js').then(chartSetup).catch(e=>{ CHART_P=null; throw e; });
  return CHART_P;
}
function needChart(redo){ if(window.Chart)return false; loadChart().then(redo).catch(()=>{}); return true; }
let KAKAO_P=null, KAKAO_FAIL=false;
function loadKakao(){
  if(window.Kakao)return Promise.resolve();
  if(!KAKAO_P)KAKAO_P=loadScript('https://t1.kakaocdn.net/kakao_js_sdk/2.7.4/kakao.min.js')
    .catch(e=>{ KAKAO_P=null; KAKAO_FAIL=true; throw e; });
  return KAKAO_P;
}
/* ⚠️ 받기에 실패해도 공유는 이어간다 — KAKAO_FAIL 이 서면 kakaoReady()가 false 라 OS 공유·복사로 넘어간다. */
function needKakao(redo){ if(window.Kakao||KAKAO_FAIL)return false; loadKakao().then(redo,redo); return true; }
/* 퀴즈·통계 코드 분할(홈 마케팅 검수 B11·MOB-8, 2026-09-27). 지도 첫 화면은 퀴즈(문항·채점·대결·결과 공유)와
   통계 화면(대시보드·주간/월간 그래프·투자지표·버블밴드) 코드를 쓰지 않는다 — 그 둘을 home-quiz.js·home-stats.js 로
   떼어 그 화면에 들어갈 때 받는다(차트·카카오와 같은 loadScript).
   - 입구(PARTS.*.api): 홈 스크립트·index.html 의 onclick 이 부르는 그 파일의 함수 이름. 파일이 오기 전에는 같은 이름의
     대기 함수가 받아 두었다가 **도착하면 부른 순서대로** 진짜 함수를 부른다 — 느린 망에서 누른 것이 사라지지 않는다.
     분할 파일의 최상위 function 선언이 전역의 대기 함수를 덮어쓴다(대기 함수는 대입으로 만들어 덮어쓸 수 있다).
     목록과 분할 파일의 선언·홈이 부르는 이름이 어긋나지 않는지는 test_home_parts 가 본다.
   - 기다리는 동안: 통계는 #stats-loading 에 '불러오는 중', 퀴즈 시작은 문항 칸에 '불러오는 중'. 못 받으면 알리고
     다음 누름에서 다시 받는다(실패한 약속을 지운다).
   - 판 표식으로 양방향 보호한다. ① 주소에 판(HOME_BUILD)을 붙인다(?v=) — 브라우저 HTTP 캐시(GitHub Pages
     max-age=600)와 서비스워커 캐시가 주소째로 갈려 **옛** 판 분할 파일이 새 홈에 섞이지 않는다. sw.js 는 같은
     주소('?v='+VERSION)를 사전 캐시한다(오프라인). ② 분할 파일도 자기 판(HOME_QUIZ_BUILD·HOME_STATS_BUILD)을 싣고
     받은 뒤 HOME_BUILD 와 견준다(partBuildOk) — GitHub Pages 는 쿼리를 무시하므로, 열어 둔 옛 판 탭이 배포 뒤에
     퀴즈·통계를 열면 ?v=옛판 주소로 **새** 판 파일이 온다(새 서비스워커가 network-first 로 받고 옛 캐시는 activate 때
     지운다 — 검토에서 재현). 다르면 맨 위 판 표식과 같은 길(한 번만 새로고침, 다음 부팅이 build_reload 로 잰다)로
     새로고침한다. 네 판 값(sw VERSION·data-build·HOME_BUILD·분할 파일 둘)이 같은지는 test_home_build 가 본다.
   - 통계는 그래프 데이터(data-trend.json)도 함께 기다린다. 투자지표·버블밴드 입력(occupancy·permits·bubble·전세가율)은
     data-core 에서 빠져 그 파일들로만 온다(B11 data-core 다이어트, tools/split_data.py). */
const PARTS={
  quiz:{src:'/home-quiz.js',api:['startQuiz','backToPick','bootChallenge']},
  stats:{src:'/home-stats.js',api:['statsOpen','setStatsMode','setMarketTab','setAdvTab','gtSet','trFlip',
    'onTrendReg','onTrendSgg','openTrendRegion','renderPermitSec','renderOccSec']},
};
function partURL(n){ return PARTS[n].src+'?v='+HOME_BUILD; }
const PART_P={};
let PART_WAIT=0;   // 받고 있는 분할 파일 수 — loadData 가 그 사이 '불러오는 중'을 걷지 않게
/* 통계 화면 파일(home-stats.js)을 못 받았는가. 그 안내('통계 화면을 불러오지 못했습니다')를 나란히 받던 그래프 데이터의
   성공이 걷으면 통계 화면이 안내 없이 빈 채로 남았다(전수리뷰 A1). 다시 누르면(partBusy 'wait') 푼다. */
let PART_FAIL=false;
function loadPart(n){
  if(!PART_P[n]){
    PART_WAIT++;
    PART_P[n]=loadScript(partURL(n)).then(()=>{ PART_WAIT--;
      if(!partBuildOk(n))return new Promise(()=>{});   // 새로고침하는 중 — 대기열을 풀지 않는다(옛 홈 위에서 새 판 코드를 돌리지 않게)
    },e=>{ PART_WAIT--; delete PART_P[n]; throw e; });
  }
  return PART_P[n];
}
/* 받은 분할 파일의 판이 이 홈 스크립트 판과 같은가(위 PARTS 주석 ②). 다르면 맨 위 판 표식과 같은 저장 키로 **한 번만**
   새로고침한다 — 이 HTML 판으로 이미 한 번 새로고침했거나 저장소를 못 쓰면 새로고침하지 않고 그대로 쓴다(무한 반복 방지).
   판 표식이 없는 분할 파일은 비교하지 않는다. */
function partBuildOk(n){
  const b=window['HOME_'+n.toUpperCase()+'_BUILD'];
  if(!b||b===HOME_BUILD)return true;
  try{
    const html=document.documentElement.getAttribute('data-build')||'', k='agongmap-build';
    if((sessionStorage.getItem(k)||'')===html)return true;
    sessionStorage.setItem(k,html+'!');
    sessionStorage.setItem('agongmap-build-part',n+':'+b);
    location.reload();
    return false;
  }catch(e){return true;}
}
function partReady(n){ return n==='stats'?Promise.all([loadPart(n),loadFullData()]):loadPart(n); }
function partBusy(n,fn,state){
  if(n==='stats'){
    const box=document.getElementById('stats-loading'); if(!box)return;
    if(state==='wait'){PART_FAIL=false;box.textContent='통계 화면을 불러오는 중…';box.style.display='';}
    else if(state==='done'){box.style.display='none';}
    /* '다시 눌러 주세요'라고만 하면 누를 것이 없었다(백로그 36-6) — 같은 자리에 다시 시도 단추를 둔다(statsOpen 은 PARTS 입구라
       누르면 분할 파일을 다시 받는다. 실패한 주소는 loadPart 가 _loaded 에서 지워 둔다). */
    else{PART_FAIL=true;box.textContent='통계 화면을 불러오지 못했습니다. 연결을 확인해 주세요. ';
      if(box.insertAdjacentHTML)box.insertAdjacentHTML('beforeend','<button type="button" class="retry-btn" onclick="statsOpen()">다시 시도</button>');
      box.style.display='';}
    return;
  }
  if(fn!=='startQuiz'&&fn!=='bootChallenge')return;
  const intro=document.getElementById('quiz-intro'), play=document.getElementById('quiz-play'), card=document.getElementById('qcard');
  if(!intro||!play||!card)return;
  if(state==='wait'){
    intro.style.display='none'; play.style.display='';
    card.innerHTML='<p role="status" style="padding:36px 0;text-align:center;color:var(--muted)">테스트를 불러오는 중…</p>';
  }else if(state==='fail'){
    play.style.display='none'; intro.style.display='';
    toast('테스트를 불러오지 못했습니다. 연결을 확인하고 다시 눌러 주세요.');
  }
}
Object.keys(PARTS).forEach(n=>PARTS[n].api.forEach(fn=>{
  const wait=function(){
    const a=arguments;
    partBusy(n,fn,'wait');
    return partReady(n).then(()=>{
      partBusy(n,fn,'done');
      /* 기다리는 사이 다른 화면으로 떠났으면 그 화면용 누름은 버린다 — 예: '시세' → '투자지표'를 누르고 파일이 오기 전에
         뒤로 가기로 홈에 오면, 늦게 돈 setStatsMode 가 주소만 #stats-adv-occ 로 바꿔 화면(홈)과 주소가 갈린다.
         statsOpen(화면 준비)은 숨은 채로라도 돌려 둔다 — 다시 들어올 때 statsInited 가 이미 서 있다. */
      if(fn!=='statsOpen'&&curView!==(n==='stats'?'stats':'test'))return;
      const f=window[fn];
      if(typeof f==='function'&&f!==wait)return f.apply(null,a);
    },()=>{
      partBusy(n,fn,'fail');
      if(n==='stats')statsInited=false;   // 다음 진입에서 statsOpen 을 다시 부르게
      if(fn==='bootChallenge')showView('test',false);   // 부팅 page_view 를 빠뜨리지 않게(boot 는 quiet 로 띄웠다, #46)
    });
  };
  window[fn]=wait;
}));
/* Chart.js는 생성 시점에 텍스트를 한 번 래스터화하고 폰트 로드로 다시 그리지 않는다.
   이게 없으면 웹폰트가 늦게 도착할 때 차트 라벨만 폴백 폰트로 굳어 본문과 어긋난다.
   호출부 14곳을 건드리는 대신 캔버스를 훑는다 — 이 시점 이후 만들어지는 차트는
   이미 로드된 폰트로 그려지므로 한 번의 스윕이면 충분하다. */
if(document.fonts&&document.fonts.ready){
  document.fonts.ready.then(()=>{
    if(typeof Chart==='undefined')return;
    document.querySelectorAll('canvas').forEach(cv=>{
      const c=Chart.getChart(cv); if(c)c.update('none');
    });
  }).catch(()=>{});
}
const fy=t=>Math.floor(t),SUDO=["서울","경기","인천"];



/* ============ 하단 내비 뷰 전환 ============ */
function track(ev,params){try{if(typeof gtag==='function')gtag('event',ev,params||{});}catch(e){}}
const vHome=document.getElementById('view-home'),vStats=document.getElementById('view-stats'),vTest=document.getElementById('view-test');
let statsInited=false,curView=null;
let _fullData=null;
function loadFullData(){
  /* 홈은 core(48KB)만 받고, 주간 155주·기본통계 11계열은 통계 탭을 열 때 받는다.
     data.js를 런타임에 정규식으로 파싱하지 않는다 — 선언 형태가 조금만 바뀌어도
     조용히 깨지므로 분리기가 낸 JSON을 그대로 읽는다. */
  return loadData('/data-trend.json');
}
let _loaded={};
function loadData(url){
  /* 통계 탭 진입 시 trend(그래프) → rest(기본통계 11계열) 순서로 둘 다 받는다.
     둘로 쪼갠 이유는 진입 화면(주간·월간 그래프)이 rest 194KB를 기다리지
     않게 하기 위해서다 — 세그먼트 UI(initStats)만 rest 도착을 기다린다. */
  if(_loaded[url])return _loaded[url];
  /* 화면 위 안내 칸(#stats-loading)은 통계 화면을 막는 그래프 데이터(data-trend.json)만 쓴다(전수리뷰 A2). 뒤에서 받는
     기본통계(data-rest)·규모별(data-size)까지 이 칸을 켜고 끄면 그래프가 다 그려진 뒤 칸이 늦게 열고 닫혀 화면이
     밀렸고, data-rest 만 못 받으면 멀쩡한 그래프 위에 '불러오지 못했습니다'가 계속 남았다. 그 둘의 실패는 기본통계
     구역의 출처 줄(#src-note)에 단다. */
  const gate=url==='/data-trend.json';
  const box=gate?document.getElementById('stats-loading'):null;
  if(box){box.textContent='통계 데이터를 불러오는 중…';box.style.display='';}
  _loaded[url]=fetch(url).then(r=>{
    if(!r.ok)throw new Error('HTTP '+r.status);
    return r.json();
  }).then(d=>{
    Object.assign(ADV,d.ADV); Object.assign(STATS,d.STATS);
    // 통계 화면 파일(home-stats.js)이 아직 오는 중이거나 못 받았으면 그 안내를 남긴다
    if(box&&!PART_WAIT&&!PART_FAIL)box.style.display='none';
  }).catch(e=>{
    delete _loaded[url];   // 다음 진입에서 다시 시도할 수 있게
    const msg='통계 데이터를 불러오지 못했습니다. 새로고침해 주세요.';
    if(box){box.textContent=msg;box.style.display='';}
    else if(!gate){const n=document.getElementById('src-note'); if(n)n.textContent=msg;}
    throw e;
  });
  return _loaded[url];
}
function ensureBasicStats(){ return loadData('/data-rest.json'); }
/* '규모별 동향'(지표4x규모6 피벗)은 혼자 186KB라 rest에서 빼 지연 로드한다 —
   그 세그먼트를 실제로 누른 사람만 받는다(2026-08-01, tools/split_data.py LAZY_STATS). */
function ensureSizeStats(){ return loadData('/data-size.json'); }
/* 감소 모션은 호출 시점에 읽는다 — .matches를 스냅샷으로 잡아두면
   사용자가 세션 중 OS 설정을 바꿔도 따라가지 못한다. */
const _rm=window.matchMedia?matchMedia('(prefers-reduced-motion: reduce)'):null;
const scrollBehavior=()=>(_rm&&_rm.matches)?'auto':'smooth';
/* page_view 의 가상 주소 — 화면(뷰)은 쿼리 view= 로 가른다(A3·MEAS-1 권고, 2026-09-27). GA 는 페이지 경로에
   해시를 넣지 않아서 예전 '/#stats'·'/#test' 는 홈 '/' 과 한 줄로 합쳐졌다. 쿼리는 '페이지 경로 + 쿼리 문자열'과
   '방문 페이지 + 쿼리 문자열'에서 갈린다(page_title 의 view_* 도 그대로 둔다). 홈은 view 를 달지 않는다 — 첫 화면
   '/' 과 홈으로 돌아온 전환이 같은 한 줄이어야 해서다. href 의 경로·다른 쿼리(착지 utm)·해시는 그대로 두고,
   있던 view= 는 바꿔 끼운다(같은 값이 두 번 붙지 않게). 첫 page_view 는 착지 주소에, 전환은 origin+'/' 에 붙인다. */
function viewLoc(v,href){
  const i=href.indexOf('#'), hash=i<0?'':href.slice(i), pre=i<0?href:href.slice(0,i), j=pre.indexOf('?');
  const q=(j<0?'':pre.slice(j+1)).split('&').filter(s=>s&&!/^view(=|$)/.test(s));
  if(v!=='home')q.push('view='+v);
  return (j<0?pre:pre.slice(0,j))+(q.length?'?'+q.join('&'):'')+hash;
}
let PV_SENT=false;   // 부팅 page_view 를 보냈는가(showView)
/* 부팅 page_view 를 보낸 **뒤** 할 일(대결 부팅의 home_visit). 대결 부팅은 page_view 를 home-quiz.js 도착 뒤로 미루므로
   home_visit 이 그 앞에 가지 않게 여기에 걸어 둔다(통합 검토 — '부팅 page_view 뒤' 순서가 대결 경로에서 뒤집혔다). */
let PV_AFTER=null;
function showView(v,updateHash,quiet){
  /* 퀴즈 뷰는 전용 탭이 없다(퀴즈 탭 → 지역 탭 교체, d6fe72e). 아무 탭도 안 켜면
     '지금 어디인가' 표시가 사라진다(2026-08-10 리뷰) — 퀴즈는 홈에서 진입하는
     하위 화면이므로 홈을 켠 채 둔다. */
  // 아래 page_view 용 — 첫 호출의 착지 주소는 이 함수가 주소를 바꾸기(pushState) 전에 잡는다
  /* quiet: 부팅이 대결 링크를 풀기 전에 퀴즈 화면만 먼저 띄울 때(boot). page_view 를 보내지 않고, 다음 호출을 여전히
     '첫 호출'로 둔다 — 값이 틀린 대결 링크가 홈으로 돌아가면 부팅 page_view 가 두 번(view_test·view_home) 갔다(전수리뷰 #46). */
  const first=!PV_SENT, changed=v!==curView||!PV_SENT, landing=location.href;
  const nv=(v==='test')?'home':v;
  /* 켠 탭은 aria-current="page" 도 단다 — 다른 페이지 탭바(site_nav.bottomnav)와 같은 의미(전수리뷰 #47) */
  document.querySelectorAll('.nav-btn').forEach(x=>{const on=x.dataset.view===nv;x.classList.toggle('on',on);
    if(on)x.setAttribute('aria-current','page');else x.removeAttribute('aria-current');});
  vHome.style.display=v==='home'?'':'none';
  vStats.style.display=v==='stats'?'':'none';
  vTest.style.display=v==='test'?'':'none';
  document.body.classList.toggle('in-test',v==='test');   // 푸터 색인은 퀴즈 중엔 감춘다(2026-09-18 오딧 9번)
  window.scrollTo(0,0);
  if(v==='stats'&&!statsInited){
    /* 통계 화면 코드는 home-stats.js 에 있다(B11). statsOpen 은 그 파일과 그래프 데이터(data-trend.json)가 둘 다
       온 뒤에 돈다(아래 분할 파일 대기열) — 못 받으면 statsInited 를 되돌려 다음 진입에서 다시 받는다. */
    statsInited=true;
    statsOpen();
  }
  if(updateHash!==false){
    // 통계는 모드·하위탭까지 정규화한 해시로 — 뒤로가기 복원이 화면과 일치하게
    const full=v==='stats'?statsHashOf(statsMode):'#'+v;
    /* 홈으로 갈 때도 쿼리는 남긴다. 예전엔 location.pathname 만 써서 쿼리 착지(블로그 '/?utm…#stats-market',
       설치 앱 start_url '/?utm_source=pwa…')에서 홈 → 뒤로 가기를 하면 쿼리까지 바뀌어 hashchange 가 오지 않았고,
       주소는 통계인데 화면은 홈에 머물렀다(홈 마케팅 검수 1차 배포 검증, 2026-09-27). */
    /* 대결 쿼리(c·s·q)는 퀴즈 화면에서만 남긴다 — 홈·시세로 옮기면서 걷지 않으면 그 화면에서 새로고침·탭 복원·주소 복사 때
       부팅이 해시 대신 대결 퀴즈를 띄웠다(전수리뷰 #44·#49). utm 등 다른 쿼리는 둔다. */
    /* 퀴즈를 떠날 때는 지금 항목(퀴즈)의 주소에서도 대결 쿼리를 먼저 걷는다. 새 항목만 걷어 pushState 하면 두 항목의
       쿼리가 달라져, 뒤로 가기에 hashchange 가 오지 않고(popstate 만) 주소는 퀴즈인데 화면은 홈·시세에 머물렀다 —
       위 2026-09-27 결함이 대결 경로에서 되살아난 모양(통합 검토). */
    if(curView==='test'&&v!=='test'&&chalInURL(location.search))history.replaceState(null,'',location.pathname+chalSearch()+location.hash);
    const q=v==='test'?location.search:chalSearch();
    const tgtHash=v==='home'?'':full, tgtUrl=v==='home'?location.pathname+q:(q===location.search?full:location.pathname+q+full);
    if(v===curView)history.replaceState(null,'',tgtUrl);
    else if(location.hash!==tgtHash)history.pushState(null,'',tgtUrl);
  }
  /* page_view 는 화면이 실제로 바뀔 때만, 부팅 때는 한 번만(A3·MEAS-1, 2026-09-27). 예전엔 gtag config 의 자동
     page_view 와 이것이 부팅마다 겹쳐 두 번 갔고, 같은 탭을 다시 눌러도 또 갔다 — GA4 는 '페이지 2회 이상'을
     참여 세션으로 세므로 홈에 와서 첫 화면만 보고 나간 방문도 참여로 잡혀 이탈률이 0에 가까웠다.
     config 는 자동 전송을 끄고(index.html 머리 ④), 첫 호출(부팅)은 착지 주소(머리 ① 이 옮긴 utm 쿼리와 해시까지)에
     view= 만 더해 싣는다 — origin 에서 새로 만들면 쿼리가 빠져 블로그 캠페인이 안 잡힌다. 그 뒤 화면 전환은
     origin+'/' 에 view= 를 단 가상 주소다(viewLoc): 세션 출처는 첫 hit 가 정하므로 utm 을 매 전환에 되풀이할
     까닭이 없고, 착지 쿼리를 실으면 같은 화면이 착지 쿼리마다 다른 주소로 갈라진다. */
  else if(v!=='test'&&chalInURL(location.search))history.replaceState(null,'',location.pathname+chalSearch()+location.hash);
  curView=v;
  if(changed&&!quiet){PV_SENT=true;track('page_view',{page_title:'view_'+v,page_location:viewLoc(v,first?landing:location.origin+'/')});
    if(first&&PV_AFTER){const f=PV_AFTER;PV_AFTER=null;f();}}
}
/* 대결 쿼리(c·s·q)를 걷은 쿼리 문자열. 대결 링크가 아니면 그대로. */
function chalSearch(){
  if(!chalInURL(location.search))return location.search;
  const q=location.search.slice(1).split('&').filter(x=>x&&!/^(c|s|q)(=|$)/.test(x));
  return q.length?'?'+q.join('&'):'';
}
/* 부팅이 대결로 들어갈 주소인가 — 대결 쿼리가 있고, 해시가 없거나 그 대결 세트의 퀴즈(#test-<s>)일 때만. 다른 화면의
   해시(#stats-… 등)가 붙어 있으면 그 화면이 이긴다(전수리뷰 #44 — 옛 탭·복사한 주소에 남은 쿼리). */
function chalBootable(){
  if(!chalInURL(location.search))return false;
  const m=location.search.match(/[?&]s=(beginner|investor|calc)/);
  return !location.hash||location.hash==='#test-'+m[1];
}
// 리포트 탭은 <a href="/cycle/">라 dataset.view가 없다. 가드가 없으면
// showView(undefined)가 불려 네 뷰가 전부 사라진다.
document.querySelectorAll('.nav-btn').forEach(b=>{if(b.dataset.view)
  b.addEventListener('click',()=>showView(b.dataset.view));});
/* 하단 탭 클릭 수(홈 마케팅 검수 C2, 2026-09-27). '통계' 탭 이름을 '시세'로 바꾼 전후를 GA 에서 비교하려고 탭 클릭만
   따로 센다 — page_view(view_stats)는 주간 링크·goStats 도 같이 내서 탭을 눌러 온 것만 가를 수 없었다. 값은 표시
   문자열이 아니라 식별자다(버튼은 data-view, 링크는 주소의 영문 경로 → home·zone·stats·cycle). 이름을 다시 바꿔도
   같은 줄에 쌓인다(매개변수 이름 tab 은 adv_tab·market_tab 과 같다). 링크 탭(지역·사이클)은 페이지를 떠나지만
   GA4 는 이벤트를 beacon 으로 보내 떠나는 클릭도 남는다. */
document.querySelectorAll('.bottomnav .nav-btn').forEach(b=>b.addEventListener('click',()=>
  track('nav_tab',{tab:b.dataset.view||(b.getAttribute('href')||'').replace(/[^a-z]/g,'')})));
function goQuiz(k){showView('test');startQuiz(k);}
// 해시는 setStatsMode가 한 번만 쌓는다(showView까지 쌓으면 한 클릭에 두 칸)
function goStats(m){showView('stats',false);setStatsMode(m);}
// 리포트가 /cycle/로 가져간 앵커들. score는 일부러 뺐다 — zone 37장이
// /#score로 홈의 sec-score를 가리키고 있어서, 여기 넣으면 그 링크가
// /cycle/로 튕긴다(위 score 분기가 먼저 잡지만 순서에 기대지 않는다).
const R2C=new Set(["report", "c4", "c5", "c6", "cFlow", "cL1", "cL3", "cL6", "cMelt", "cRate", "cStr", "cSuper", "link1", "link2", "link3", "link45", "link6", "ref1", "ref2", "ref3", "ref4", "summary", "ztog"]);
/* '레이아웃이 잡힌 뒤에' 할 일. rAF 대신 타이머를 쓰는 이유는 rAF가 배경 탭·
   비렌더링 맥락에서 아예 돌지 않기 때문이다 — 표 초기 위치에서 실제로 그
   함정을 밟았다(IntersectionObserver 콜백 0건, 커밋 0677fb0).
   ⚠️ 다만 여기 세 곳(해시 앵커 2·차트 리플로 1)이 rAF 때문에 고장 나 있었다는
   증거는 없다. 전환은 예방적 통일이다 — 2026-08-08에 '/#score가 안 된다'고
   판단했던 건 측정 환경 탓이었다(그 창은 window.scrollTo(0,500)조차 무시했다).
   같은 실수를 반복하지 않으려고 남긴다: 창 스크롤을 재기 전에 창이 스크롤
   되는지부터 확인할 것. */
function afterLayout(fn){ setTimeout(fn, 0); }
function applyHash(){
  /* '#화면?utm_…'(발행한 주간 블로그 글의 옛 링크 모양)은 index.html 머리가 먼저 '?…#화면'으로 고친다(A1).
     여기서도 '?' 뒤를 잘라 둔다 — 머리 스크립트가 못 돈 경우(옛 캐시의 HTML 등)에도 화면은 열리게. */
  const h=location.hash.replace('#','').split('?')[0];
  if(!h){showView('home',false);return;}
  if(h==='test-beginner'||h==='test-investor'||h==='test-calc'){showView('test',false);startQuiz(h.slice(5),undefined,true);return;}
  /* '~코드'(시장동향만): 지도 칸·TOP 10 지역명에서 고른 지역의 그래프(openTrendRegion). 코드 없는 시장동향 주소는 그 함수가
     연 그래프를 열기 전 보기(순위·지도 — TR_BACK)로 되돌린다(뒤로 가기). */
  const sm=h.match(/^stats-(market|adv|basic|more)(?:-(week|month|occ|permit|bubble))?(-rank)?(?:~([a-c][0-9]{1,8})(-t)?)?$/);
  if(sm){
    showView('stats',false);setStatsMode(sm[1],false);
    // 하위탭 미지정 해시는 기본탭으로 — 뒤로가기가 항상 같은 화면을 재현하도록
    /* '-rank'(시장동향만): 순위 보기로 바로 연다 — 홈 '시군구 상승·하락 TOP 10 보기'·/weekly/ 'TOP 10' 링크·블로그 캡처의 입구
       (2026-10-10, 시장동향 기본 보기는 지도). 다른 보기(그래프·표)처럼 주소에는 남기지 않는다 — 열고 나면 #stats-market-<주기>.
       순위로 바꾸는 일은 openTrendRegion(셋째 인자 'r')이 데이터가 온 뒤에 한다 — 연 지역 그래프가 있으면 닫고, 받는 사이 사람이
       고른 보기는 덮지 않는다. 여기서 따로 gtSet 을 부르면 통계 파일을 못 받은 날 그 부름이 파일만 다시 받아 statsOpen 없이 빈
       화면을 남기고(다시 시도 단추까지 걷힌다), 받는 사이 누른 '그래프'를 늦게 덮었다(10-10 코드 리뷰). */
    if(sm[1]==='market'){const t=sm[2]==='month'?'month':'week';setMarketTab(t,false);
      if(sm[3]){openTrendRegion(t,null,'r',GT_SEQ[t]);history.replaceState(null,'','#stats-market-'+t);}
      else openTrendRegion(t,sm[4]||null,sm[5]?'t':'g');}
    else if(sm[1]==='adv')setAdvTab(sm[2]||'occ',false);
    return;
  }
  if(h==='score'){showView('home',false);afterLayout(()=>{const el=document.getElementById('sec-score');if(el)el.scrollIntoView();});return;}
  if(h==='test'){showView('test',false);backToPick(true);return;}
  /* 맨 #stats(모든 페이지 탭바의 '시세' 링크·PWA 바로가기)는 #stats-market 과 같게 모드·하위 탭까지 맞추고 주소도 정규
     해시로 바꿔 둔다 — 예전엔 화면만 열어, 투자지표로 옮긴 뒤 뒤로 가면 주소만 #stats 로 돌아오고 화면은 그대로였다
     (전수리뷰 #45). */
  if(h==='stats'){showView('stats',false);setStatsMode('market',false);setMarketTab('week',false);openTrendRegion('week',null);
    history.replaceState(null,'','#stats-market-week');return;}
  if(h==='home'||h==='test'){showView(h,false);return;}
  // 리포트는 /cycle/로 이전했다. 옛 해시로 들어온 링크·북마크를 넘긴다.
  // replace를 쓰는 이유: push면 뒤로가기가 이 페이지로 되돌아와 무한 왕복한다.
  if(R2C.has(h)){location.replace('/cycle/'+(h==='report'?'':'#'+h));return;}
  const el=document.getElementById(h);
  if(el){afterLayout(()=>el.scrollIntoView());}
}
window.addEventListener('hashchange',applyHash);

/* ============ 통계 대시보드 → home-stats.js(B11 코드 분할, 통계 화면을 열 때 받는다) ============ */

/* ============ 부동산 테스트 (부린이 / 투자자) ============ */
/* 부린이 테스트 레벨 10단계 (점수 0~10 → 태아부터 교수님까지).
   share/beginner-{0..10}.png 카드의 스탬프·이모지·문구와 1:1로 대응한다. */
const BLV=[
  {lv:'LV1',emoji:'\u{1F95A}',g:'무주택 달걀',
   d:'아직 청약도 임장도 낯선 단계. 용어부터 하나씩 익히면 금방 깨어납니다.',
   taunt:'아직 껍데기 속 무주택입니다'},
  {lv:'LV1',emoji:'\u{1F423}',g:'부화 임박',
   d:'금이 가기 시작했습니다. 조금만 더 읽으면 세상 밖으로 나옵니다.',
   taunt:'곧 세상 밖으로 나올 참입니다'},
  {lv:'LV2',emoji:'\u{1F424}',g:'갓 깬 삐약이',
   d:'이제 막 눈을 떴습니다. 전세와 월세 차이부터 하나씩 익혀보세요.',
   taunt:'전세 계약서가 아직 무섭죠?'},
  {lv:'LV3',emoji:'\u{1F425}',g:'솜털 병아리',
   d:'단어는 들어봤는데 뜻은 아직. 해설만 읽어도 두 계단은 올라갑니다.',
   taunt:'용어는 외웠는데 실전은 아직이죠'},
  {lv:'LV4',emoji:'\u{1FA99}',g:'첫 발품 영계',
   d:'임장은 다녀봤지만 LTV·DSR만 정리해도 확 달라집니다.',
   taunt:'임장은 이제 다녀보셨나요?'},
  {lv:'LV5',emoji:'\u{1FAB9}',g:'알 낳는 암탉',
   d:'슬슬 감이 잡히는 단계. 동전도 하나둘 모이기 시작합니다.',
   taunt:'슬슬 감이 잡히시죠?'},
  {lv:'LV6',emoji:'\u{1F413}',g:'목청 좋은 장닭',
   d:'기본기는 탄탄합니다. 헷갈린 한두 개 제도만 챙기면 곧 내 집 마련입니다.',
   taunt:'이제 아무도 못 말리겠는데요?'},
  {lv:'LV7',emoji:'\u{1F3E0}',g:'내 집 마련',
   d:'대출·세금·임대차를 또렷이 꿰고 있습니다. 계약서 앞에서 안 떨릴 수준.',
   taunt:'드디어 첫 둥지 축하합니다!'},
  {lv:'LV8',emoji:'\u{1F3D8}\u{FE0F}',g:'다주택자',
   d:'한 채로는 성에 안 차는 실력. 이쯤 되면 중개사에게 되묻는 쪽입니다.',
   taunt:'한 채로는 성에 안 차죠?'},
  {lv:'LV9',emoji:'\u{1F3D9}\u{FE0F}',g:'부동산 거물',
   d:'시장이 손안에 들어왔습니다. 투자자 테스트로 넘어갈 때입니다.',
   taunt:'시장이 손안에 들어왔네요'},
  {lv:'LV10',emoji:'\u{1F985}',g:'부동산 봉황',
   d:'부린이는 무슨 — 금은보화 위에 앉으셔도 됩니다. 이제 투자자 테스트에서 통념을 깨보세요.',
   taunt:'금은보화 위에 앉으셨네요'}
];
/* 퀴즈 본체(QUIZSETS~showResult·친구 대결·결과 공유) → home-quiz.js(B11 코드 분할, 퀴즈를 열 때 받는다) */
// 공유 링크는 퀴즈 전용 OG(og-test.png)를 가진 /burini-test/로 보낸다.
// 해시(#test)나 루트(?c=)로 보내면 홈 OG(og-brand.png)로 언펄돼 퀴즈 훅이 사라진다.
const SHARE_URL='https://www.agongmap.co.kr/burini-test/';
// GA 어트리뷰션 규약: utm_source는 유입 장치(quiz_invite/quiz_challenge), utm_medium=viral 고정,
// utm_campaign은 퀴즈 세트. 랜딩의 location.replace('/'+q)가 쿼리를 보존하므로 홈까지 전달된다.
const SHARE_URL_UTM=SHARE_URL+'?utm_source=quiz_invite&utm_medium=viral&utm_campaign=quiz3set';
/* 대결 링크 모양인가 — 퀴즈 랜딩 3종이 홈으로 넘기는 조건과 같다(burini-test/index.html 등). 값 검사(점수 상한·시드)는
   home-quiz.js 의 readChallenge 몫이다. 부팅이 이걸로 퀴즈 화면을 먼저 띄우고 그 파일을 받는다(B11). */
function chalInURL(q){ return /[?&]c=\d/.test(q)&&/[?&]s=(beginner|investor|calc)/.test(q); }
const KAKAO_KEY='1bd3370cb08703d1450ddb0e7726ab98';
function kakaoReady(){
  if(!window.Kakao)return false;
  try{if(!Kakao.isInitialized())Kakao.init(KAKAO_KEY);return Kakao.isInitialized();}
  catch(e){return false;}
}
/* 카카오 채널(_hRjxnX) 추가 버튼은 2026-08-01 제거.
   사업자등록이 없어 비즈니스 채널 전환이 불가하고, 그러면 알림톡·친구톡을
   못 쓴다. 즉 채널을 추가해도 "매주 시세 알림"이 실제로 가지 않는다.
   지키지 못할 약속을 CTA로 거는 셈이라 버튼 자체를 뺐다.
   Kakao SDK는 공유(kakaoFeed)에 계속 쓰므로 유지. */
function kakaoFeed(title,desc,img,link,btn){
  const L=link||SHARE_URL_UTM;
  Kakao.Share.sendDefault({objectType:'feed',
    content:{title:title,description:desc,
      imageUrl:img||'https://www.agongmap.co.kr/og-test.png',imageWidth:img?800:1200,imageHeight:img?800:630,
      link:{mobileWebUrl:L,webUrl:L}},
    buttons:[{title:btn||'나도 도전하기',link:{mobileWebUrl:L,webUrl:L}},
      {title:'풀 리포트 보기',link:{mobileWebUrl:'https://www.agongmap.co.kr/?utm_source=quiz_share&utm_medium=viral&utm_campaign=full_report',webUrl:'https://www.agongmap.co.kr/?utm_source=quiz_share&utm_medium=viral&utm_campaign=full_report'}}]});
}
function shareTest(){
  if(needKakao(shareTest))return;
  track('share',{content_type:'quiz_invite',method:kakaoReady()?'kakao':(navigator.share?'os_share':'copy')});
  if(kakaoReady()){
    try{kakaoFeed('내 부동산 감각, 몇 점일까?','부린이·투자자·재건축 3종 테스트 — 10문항 5분, 즉시 채점·해설');return;}
    catch(e){}
  }
  const txt='내 부동산 감각, 몇 점일까? 부린이·투자자·재건축 3종 테스트 — 10문항 5분\n'+SHARE_URL_UTM;
  if(navigator.share){
    navigator.share({title:'부동산 사이클 테스트',
      text:'내 부동산 감각, 몇 점일까? 10문항 5분 테스트 — 같이 풀어보자!',
      url:SHARE_URL_UTM}).catch(e=>{if(e&&e.name!=='AbortError')copyText(txt);});
  }else{copyText(txt);}
}
function copyText(txt){
  if(navigator.clipboard&&navigator.clipboard.writeText){
    navigator.clipboard.writeText(txt).then(()=>toast('복사됐어요! 친구에게 붙여넣기 하세요')).catch(()=>fallbackCopy(txt));
  }else fallbackCopy(txt);
}
function fallbackCopy(txt){
  const ta=document.createElement('textarea');ta.value=txt;document.body.appendChild(ta);
  ta.select();try{document.execCommand('copy');toast('복사됐어요!');}catch(e){toast('복사 실패 — 길게 눌러 복사하세요');}
  document.body.removeChild(ta);
}
function toast(msg){
  let t=document.querySelector('.qtoast');
  if(!t){t=document.createElement('div');t.className='qtoast';document.body.appendChild(t);}
  t.textContent=msg;t.classList.add('show');
  setTimeout(()=>t.classList.remove('show'),2200);
}


/* ============ 투자지표(구 심화통계) — 화면 코드는 home-stats.js(B11). 여기엔 통계 해시만 남는다 ============ */
let statsMode='market';   // 통계 해시(statsHashOf)가 읽는다 — 부팅·뒤로 가기에서 분할 파일을 기다리지 않게 여기 둔다
/* 통계 백버튼: 사용자 클릭 1회 = 히스토리 1칸. 화면이 실제로 바뀐 클릭만
   push하고, 이미 보이던 상태의 해시 정규화(#stats-adv → #stats-adv-occ)는
   replace로 접는다. 복원은 applyHash가 해시만 보고 전체 화면을 재현한다. */
function statsNav(hh,replace){
  if(location.hash===hh)return;
  if(replace)history.replaceState(null,'',hh);
  else history.pushState(null,'',hh);
}
/* 모드의 정규 해시 — market/adv는 지금 켜져 있는 하위탭까지 포함한다.
   모드 진입 해시가 하위탭을 생략하면 뒤로가기 복원이 기본탭으로 튀어,
   화면에 남아 있던 하위탭과 어긋난다. */
/* 시장동향은 지도 칸·TOP 10 지역명으로 연 그래프(TR_OPEN)의 '~코드'(표로 보고 있으면 '-t')까지 싣는다 — 빼면 같은 탭·하단
   '시세'를 다시 누르거나 주간 → 월간 → 주간으로 오갈 때 주소가 '#stats-market-week' 로 바뀌는데 화면은 그 지역(서울 등)을
   그대로 보여, 새로고침·주소 복사가 다른 화면을 연다(전수리뷰 A3). */
const TR_OPEN={week:null,month:null};   // 주기별로 openTrendRegion(home-stats.js)이 연 그래프의 코드(주간·월간을 따로 연다)
/* 사람이 누른 시장동향 보기 전환 수(home-stats.js gtSet 이 센다). 순위 입구('-rank')는 요청한 때의 수를 openTrendRegion 에 넘기고,
   데이터가 온 뒤에도 수가 같을 때만 순위로 바꾼다 — 통계 파일은 왔는데 데이터가 늦는 사이 누른 '그래프'를 덮지 않게(10-10 코드
   리뷰). 요청한 때를 재야 해서 분할 파일이 아니라 여기 둔다. */
const GT_SEQ={week:0,month:0};
function statsHashOf(m){
  if(m==='market'){const t=document.getElementById('mtab-month').classList.contains('on')?'month':'week', c=TR_OPEN[t];
    return '#stats-market-'+t+(c?'~'+c+(document.getElementById('sec-'+t).classList.contains('gm-t')?'-t':''):'');}
  if(m==='adv'){const t=['occ','permit','bubble'].find(k=>document.getElementById('atab-'+k).classList.contains('on'))||'occ';return '#stats-adv-'+t;}
  return '#stats-'+m;
}
const NATION_TILE={cols:12,rows:20,t:[["c3","충남",0,9,1],["c313","당진",1,9,0],["c306","아산",2,9,0],["c301","천안",3,9,1],["c302","동남",4,9,0],["c303","서북",5,9,0],["c2","충북",6,9,1],["c206","음성",7,9,0],["c203","충주",8,9,0],["c204","제천",9,9,0],["c307","서산",0,10,0],["c311","홍성",1,10,0],["c312","예산",2,10,0],["c304","공주",3,10,0],["c309","계룡",4,10,0],["b6","세종",5,10,1],["c201","청주",6,10,1],["c20103","흥덕",7,10,0],["c20104","청원",8,10,0],["c20101","상당",9,10,0],["c20102","서원",10,10,0],["c305","보령",0,11,0],["c308","논산",1,11,0],["b4","대전",3,11,1],["b404","유성",4,11,0],["b405","대덕",5,11,0],["b403","서",6,11,0],["b402","중",7,11,0],["b401","동",8,11,0],["c4","전북",0,12,1],["c404","군산",1,12,0],["c405","익산",2,12,0],["c401","전주",3,12,1],["c402","완산",4,12,0],["c403","덕진",5,12,0],["c6","경북",6,12,1],["c606","영주",7,12,0],["c609","문경",8,12,0],["c605","안동",9,12,0],["c603","포항",10,12,1],["c60302","북",11,12,0],["c408","김제",0,13,0],["c406","정읍",1,13,0],["c407","남원",2,13,0],["c608","상주",6,13,0],["c602","구미",7,13,0],["c611","칠곡",8,13,0],["c604","김천",9,13,0],["c610","경산",10,13,0],["c60301","남",11,13,0],["b3","광주",0,14,1],["b304","북",1,14,0],["b305","광산",2,14,0],["b302","서",3,14,0],["b301","동",4,14,0],["b303","남",5,14,0],["b2","대구",6,14,1],["b205","북",7,14,0],["b202","동",8,14,0],["b206","수성",9,14,0],["c607","영천",10,14,0],["c601","경주",11,14,0],["c5","전남",0,15,1],["c504","나주",1,15,0],["c503","순천",2,15,0],["c505","광양",3,15,0],["c506","무안",4,15,0],["c501","목포",5,15,0],["c502","여수",6,15,0],["b203","서",7,15,0],["b201","중",8,15,0],["b207","달서",9,15,0],["b208","달성",10,15,0],["b204","남",11,15,0],["c7","경남",0,16,1],["c703","진주",1,16,0],["c705","사천",2,16,0],["c704","통영",3,16,0],["c708","거제",4,16,0],["c707","밀양",5,16,0],["b5","울산",6,16,1],["b501","중",7,16,0],["b503","동",8,16,0],["b504","북",9,16,0],["b505","울주",10,16,0],["b502","남",11,16,0],["c701","창원",1,17,1],["c70101","의창",2,17,0],["c70102","성산",3,17,0],["c70104","마산회원",4,17,0],["c70103","마산합포",5,17,0],["c702","진해",6,17,0],["c706","김해",7,17,0],["c709","양산",8,17,0],["b1","부산",9,17,1],["b10202","금정",10,17,0],["b10204","기장",11,17,0],["b10302","강서",4,18,0],["b10303","사상",5,18,0],["b10301","북",6,18,0],["b10203","동래",7,18,0],["b10201","해운대",8,18,0],["b10105","부산진",9,18,0],["b10107","연제",10,18,0],["b10108","수영",11,18,0],["b10304","사하",5,19,0],["b10102","서",6,19,0],["b10101","중",7,19,0],["b10106","남",8,19,0],["b10103","동",9,19,0],["b10104","영도",10,19,0],["c8","제주",0,19,1],["c801","제주",1,19,0],["c802","서귀포",2,19,0],["a0","전국",0,0,1],["a8","경기",1,0,1],["c1","강원",9,0,1],["a7","서울",3,1,1],["a9","인천",0,3,1],["a80603","파주",2,0,0],["a80704","의정부",6,0,0],["a80703","양주",3,0,0],["a80702","동두천",4,0,0],["a80701","포천",5,0,0],["a80402","구리",7,0,0],["a80401","남양주",8,0,0],["c106","속초",10,0,0],["c101","춘천",8,1,0],["c103","강릉",10,1,0],["c102","원주",9,1,0],["c104","동해",9,2,0],["c105","태백",8,2,0],["c107","삼척",8,3,0],["a806023","일산서",1,1,0],["a80602","고양",2,2,0],["a806022","일산동",1,2,0],["a806021","덕양",2,1,0],["a80601","김포",0,2,0],["a7010301","은평",4,1,0],["a7010206","강북",5,1,0],["a7010207","도봉",6,1,0],["a7010208","노원",7,1,0],["a7010302","서대문",3,2,0],["a7010101","종로",4,2,0],["a7010205","성북",5,2,0],["a7010203","동대문",6,2,0],["a7010204","중랑",7,2,0],["a7010303","마포",3,3,0],["a7010102","중",4,3,0],["a7010103","용산",5,3,0],["a7010201","성동",6,3,0],["a7010202","광진",7,3,0],["a7020102","강서",3,4,0],["a7020101","양천",4,4,0],["a7020105","영등포",5,4,0],["a7020106","동작",6,4,0],["a7020202","강남",7,4,0],["a7020203","송파",8,4,0],["a7020204","강동",9,4,0],["a7020103","구로",3,5,0],["a7020104","금천",4,5,0],["a7020107","관악",5,5,0],["a7020201","서초",6,5,0],["a80403","하남",10,4,0],["a908","검단",1,3,0],["a902","영종",2,3,0],["a901","제물포",0,4,0],["a903","미추홀",1,4,0],["a906","부평",2,4,0],["a904","연수",0,5,0],["a909","서해",1,5,0],["a907","계양",2,5,0],["a905","남동",0,6,0],["a80301","부천",1,6,0],["a803011","원미",2,6,0],["a803012","소사",3,6,0],["a803013","오정",4,6,0],["a80304","광명",5,6,0],["a80303","시흥",0,7,0],["a80302","안산",1,8,0],["a803021","상록",2,8,0],["a803022","단원",3,8,0],["a80101","과천",6,6,0],["a80102","안양",1,7,0],["a801021","만안",2,7,0],["a801022","동안",3,7,0],["a80104","군포",5,7,0],["a80105","의왕",4,7,0],["a80203","수원",6,7,0],["a802031","장안",7,7,0],["a802032","권선",8,7,0],["a802033","팔달",9,7,0],["a802034","영통",10,7,0],["a80103","성남",7,5,0],["a801031","수정",8,5,0],["a801032","중원",9,5,0],["a801033","분당",10,5,0],["a80202","용인",7,6,0],["a802021","처인",8,6,0],["a802022","기흥",9,6,0],["a802023","수지",10,6,0],["a80404","광주",11,6,0],["a80501","이천",11,7,0],["a80502","여주",11,8,0],["a80305","화성",4,8,0],["a803051","동탄",5,8,0],["a803052","만세",6,8,0],["a803053","병점",7,8,0],["a803054","효행",8,8,0],["a80306","오산",9,8,0],["a80201","안성",10,8,0],["a80307","평택",0,8,0]]};
function mapColor(v,ref){
  /* 글자가 '0.00'인 칸은 배경도 무색이어야 한다 — 안 그러면 같은 '0.00'이
     빨강·파랑·회색 세 가지로 칠해진다(2026-08-08 감사). */
  if(v!=null&&typeof pvSign==='function'&&pvSign(v)===0)return '#e8ecea';
  if(v==null||v===0)return '#e8ecea';
  const a=Math.min(Math.abs(v)/(ref||0.4),1);
  return v>0?`rgba(224,86,74,${(0.14+0.72*a).toFixed(3)})`:`rgba(58,123,213,${(0.14+0.72*a).toFixed(3)})`;
}
/* 전국 시군구 타일 지도 SVG — 통계 시장동향 지도(drawNationMap)와 홈 주간 구역(renderWeeklyGrid)이 같이 그린다. /weekly/ 머리
   지도는 파이썬 거울(tools/make_weekly_page.sgg_map_svg)이 같은 마크업을 굽는다 — 둘이 같은지는 test_sgg_map 이 node 로 대조한다.
   vals: 값 줄마다 {코드: 값}(1~3줄, 위부터 o.names 순서 — 매매·전세·월세). o.ref: 만색 기준(mapColor). o.href(코드): 칸이 갈
   주소 — 있으면 칸 전체(이름·값)가 링크다(그 지역 주간·월간 그래프, applyHash 의 '~코드'). 링크가 있으면 role="img" 를 달지
   않는다(img 안의 링크는 보조기기에 보이지 않는다).
   글자 하한 11px(2026-09-18 오딧 1번). viewBox 를 폭에 맞춰 줄이는 지도라 SVG 글자 크기가 곧 화면 크기가 아니다 — 375px
   에서는 0.88배라 값 9 → 7.9px, 이름 7 → 6.1px 로 그려졌다(2026-09-23 실측). 12열 타일은 375px 에서 칸당 27px 라 11px
   이름·값이 들어갈 수 없다. 값을 숨기면 TOP 10 밖 200여 곳의 숫자를 볼 길이 없고(title 은 터치에서 안 뜬다), 부호·소수를
   줄이면 값이 달라진다. 그래서 지도가 MAP_FS 가 MAP_MIN_PX 로 그려질 최소 폭을 갖고, 좁은 화면에서는 표처럼
   상자(.map-scroll) 안에서 옆으로 민다(test_stats_map_labels). */
function sggMapSvg(vals,o){
  const N=NATION_TILE, ref=o.ref, names=o.names, n=vals.length, TW=30, NH=15, G=2;
  /* 3단(월간)은 값 칸을 1px 낮춰 세로가 길어지는 걸 억제한다. 9px 숫자에 12px 칸이면 충분하고, 1·2단은 13px 그대로 둔다. */
  const VH=n>2?12:13;
  const rowH=NH+n*(VH+1);   // 이름칸 + 값칸(각 VH, 사이 1px)
  const W=N.cols*(TW+G)-G, H=N.rows*(rowH+G)-G;
  const MAP_FS=9, MAP_MIN_PX=11, minW=Math.ceil((W+4)*MAP_MIN_PX/MAP_FS);
  const sv=['<svg viewBox="-2 -2 '+(W+4)+' '+(H+4)+'" xmlns="http://www.w3.org/2000/svg" style="width:100%;max-width:640px;min-width:'+minW+'px;margin:0 auto;display:block"'+(o.href?' role="group"':' role="img"')+' aria-label="전국 시군구 변동률 지도">'];
  const grpOf=c=>{
    if(c[0]==='a'){
      if(c==='a0')return 'a0';
      if(c.indexOf('a7')===0)return 'a7';
      if(c.indexOf('a8')===0)return 'a8';
      return 'a9';
    }
    return c.slice(0,2);
  };
  const SI_PARENT=new Set(['a80203','a80103','a80202','a80102','a80602','a80301','a80302','a80305']);
  const clOf=c=>{ if(SI_PARENT.has(c))return c; for(const p of SI_PARENT)if(c.indexOf(p)===0)return p; return null; };
  const tcol=v=>{const r=pvSign(v);return r>0?'#8f2318':(r<0?'#123c5c':'#5e6f74');};
  /* 칸 설명의 앞말 — 짧은 이름('북'·'중'·'강서')이 여러 시도에 겹쳐 보조기기에서 같은 소리로 읽히지 않게, 구는 소속 시
     (수원 장안), 그 밖의 칸은 소속 시도(서울 강남·부산 북)를 붙인다. 시도 머리 칸(두 글자 코드)은 붙이지 않는다. */
  const HN={}; N.t.forEach(([c,nm,,,h])=>{ if(h&&c.length===2)HN[c]=nm; });
  N.t.forEach(([c,nm])=>{ if(SI_PARENT.has(c))HN[c]=nm; });
  const pre=c=>{ if(c.length<=2)return ''; const cl=clOf(c), p=(cl&&cl!==c)?HN[cl]:HN[grpOf(c)]; return p?p+' ':''; };
  /* 값칸 y는 칸 높이에서 계산 — 베이스라인도 칸 중앙 기준이라 VH를 바꿔도 숫자가 위로 치우치지 않는다. */
  const tb=Math.round(VH/2)+3;
  /* 값이 한 줄도 없는 칸은 세우지 않는다(시도 머리 칸은 늘 세운다) — 추세 그래프 지역 목록(sggOfSido)과 같은 규칙. 인천 신설
     4구(제물포·영종·검단·서해, 2026-07 개편)는 주간표에는 있고 월간표에는 아직 없어 월간 지도에 '·' 빈 칸 넷이 섰다(2026-10-07
     대표 지적). 원천이 그 칸을 내기 시작하면 저절로 다시 선다. 경계선·점선 묶음도 세운 칸만으로 긋는다. */
  const T=N.t.filter(([c,,,,h])=>h||vals.some(m=>m[c]!=null));
  T.forEach(([c,nm,x,y,h])=>{
    const px=x*(TW+G), py=y*(rowH+G), href=o.href?o.href(c):null;
    /* 칸 설명(이름·값). 링크 칸은 aria-label 로 — SVG <title> 을 쓰면 /weekly/ 처럼 구운 페이지에서 문서 <title> 을 찾는
       도구·시험이 지도 칸까지 센다. 링크가 없으면 풍선 도움말(<title>). */
    const lab=pre(c)+nm+' '+vals.map((m,j)=>names[j]+' '+pv2(m[c])+'%').join(' · ');
    const g=`<g transform="translate(${px},${py})">`+
      `<rect width="${TW}" height="${NH}" rx="4" fill="${h?'#1e2846':(SI_PARENT.has(c)?'#34456b':'#eef1f8')}" stroke="${h?'#1e2846':'#d6dced'}"/>`+
      /* 이름도 값과 같은 MAP_FS. 네 글자(마산회원·마산합포)만 칸 폭에 맞춰 자간·글자 폭을 눌러 담는다 —
         글자 크기를 7로 줄이면 높이까지 줄어 하한 아래로 내려간다. */
      `<text x="${TW/2}" y="${NH-4}" text-anchor="middle" font-size="${MAP_FS}"${nm.length>=4?` textLength="${TW-3}" lengthAdjust="spacingAndGlyphs"`:''} font-weight="600" fill="${(h||SI_PARENT.has(c))?'#fff':'#1b2426'}">${nm}</text>`+
      vals.map((m,j)=>{ const v=m[c], ry=NH+1+j*(VH+1);
        return `<rect y="${ry}" width="${TW}" height="${VH}" rx="3" fill="${mapColor(v,ref)}" stroke="#d8dfdc"/>`+
          `<text x="${TW/2}" y="${ry+tb}" text-anchor="middle" font-size="${MAP_FS}" font-weight="600" fill="${tcol(v)}">${pv2(v)}</text>`; }).join('')+
      (href?'':`<title>${lab}</title>`)+'</g>';
    sv.push(href?`<a href="${href}" data-code="${c}" aria-label="${lab}">${g}</a>`:g);
  });
  // 시도(광역) 경계선 — 같은 시도가 아닌 이웃과 접한 변만 그린다
  const posGrp={};
  T.forEach(([c,,x,y])=>{posGrp[x+','+y]=grpOf(c);});
  const bl=[];
  T.forEach(([c,,x,y])=>{
    const g=grpOf(c), px=x*(TW+G), py=y*(rowH+G);
    const nb=(dx,dy)=>posGrp[(x+dx)+','+(y+dy)];
    if(nb(0,-1)!==g)bl.push('M'+(px-1.5)+' '+(py-1.5)+'H'+(px+TW+1.5));
    if(nb(0,1)!==g)bl.push('M'+(px-1.5)+' '+(py+rowH+1.5)+'H'+(px+TW+1.5));
    if(nb(-1,0)!==g)bl.push('M'+(px-1.5)+' '+(py-1.5)+'V'+(py+rowH+1.5));
    if(nb(1,0)!==g)bl.push('M'+(px+TW+1.5)+' '+(py-1.5)+'V'+(py+rowH+1.5));
  });
  sv.push('<path d="'+bl.join('')+'" stroke="#5e6f74" stroke-width="1.4" fill="none" opacity=".9" pointer-events="none"/>');
  // 구를 가진 시 = 점선 테두리로 묶기 (시+소속 구)
  const posCl={}; T.forEach(([c,,x,y])=>{posCl[x+','+y]=clOf(c);});
  const dl=[];
  T.forEach(([c,,x,y])=>{
    const cl=clOf(c); if(!cl)return;
    const px=x*(TW+G), py=y*(rowH+G), nb=(dx,dy)=>posCl[(x+dx)+','+(y+dy)];
    if(nb(0,-1)!==cl)dl.push('M'+(px+0.5)+' '+(py+0.5)+'H'+(px+TW-0.5));
    if(nb(0,1)!==cl)dl.push('M'+(px+0.5)+' '+(py+rowH-0.5)+'H'+(px+TW-0.5));
    if(nb(-1,0)!==cl)dl.push('M'+(px+0.5)+' '+(py+0.5)+'V'+(py+rowH-0.5));
    if(nb(1,0)!==cl)dl.push('M'+(px+TW-0.5)+' '+(py+0.5)+'V'+(py+rowH-0.5));
  });
  sv.push('<path d="'+dl.join('')+'" stroke="#34456b" stroke-width="0.8" stroke-dasharray="0.6 1" stroke-linecap="round" fill="none" opacity=".85" pointer-events="none"/>');
  sv.push('</svg>');
  return sv.join('');
}
/* 지도·TOP 10 의 지역 링크를 누를 때(홈 주간 구역·통계 시장동향). 주소는 '#stats-market-week~코드'라 hashchange →
   applyHash → openTrendRegion 이 그 지역 그래프를 연다. 이미 같은 주소면 hashchange 가 오지 않으므로 여기서 바로 연다
   (그래프를 본 뒤 '지도' 버튼으로 돌아와 같은 곳을 다시 누를 때). from: 어디서 눌렀나(home_map·stats_map·rank). */
function onTrendLink(e,from){
  const a=e.target&&e.target.closest&&e.target.closest('a[data-code]'); if(!a)return;
  const h=a.getAttribute('href')||'', m=h.match(/#stats-market-(week|month)~([a-c][0-9]{1,8})$/); if(!m)return;
  track('trend_pick',{period:m[1],region:m[2],from:from});
  if(location.hash==='#stats-market-'+m[1]+'~'+m[2]){e.preventDefault();openTrendRegion(m[1],m[2]);}
}
/* 발표 일정 안내: 부동산원 주간=매주 목요일, 월간=매월 15일(전월분). 낮 12시 공표.
   다음 발표일까지 계산해 보여준다 — 유저가 '언제 새로 나오나'를 알 수 있게. */
// <wk-release> ── 이 구간은 test_weekly_release 가 통째로 node 에 올려 파이썬 정본(tools/weekly_release.py)과
// 대조한다. 여기에는 DOM·ADV 를 만지지 않는 순수 함수만 둔다.
/* 법정공휴일(대체공휴일 포함). 배치가 특일정보 API로 채운 ADV.holidays가 있으면 그걸(_syncHolidays),
   없으면 이 하드코딩으로. const가 아니라 let인 이유는 데이터 도착 시 갈아끼우기 위함이다. */
let _HOLIDAYS=new Set(['2026-01-01','2026-02-16','2026-02-17','2026-02-18',
  '2026-03-01','2026-03-02','2026-05-05','2026-05-25','2026-06-06','2026-08-15',
  '2026-08-17','2026-09-24','2026-09-25','2026-09-26','2026-10-03','2026-10-05',
  '2026-10-09','2026-12-25']);
/* 날짜는 'UTC 자정 기준 일수'(정수)로만 다룬다. Date 의 지역 시간 메서드를 쓰면 방문자 기기의 시간대에
   따라 날짜가 하루 갈린다. '오늘'은 KST(+9, 일광 절약 없음) — tools/kst.py 와 같다. */
const _DAY=864e5;
function _dn(iso){const a=String(iso).split('-');return Date.UTC(+a[0],+a[1]-1,+a[2])/_DAY;}
function _iso(n){return new Date(n*_DAY).toISOString().slice(0,10);}
function _wd(n){return new Date(n*_DAY).getUTCDay();}       // 0=일 … 4=목
function _kst(now){const k=now.getTime()+9*36e5;return {day:Math.floor(k/_DAY),hour:new Date(k).getUTCHours()};}
function _bizDay(n){   // 주말·공휴일이면 다음 영업일까지 민다
  while(_wd(n)===0||_wd(n)===6||_HOLIDAYS.has(_iso(n)))n++;
  return n;
}
/* 주간 발표 상태 — 홈 주간 격자 머리줄과 통계 탭 rel-week 가 **이 함수 하나**를 쓴다(홈 마케팅 검수 A2).
   예전엔 rel-week 만 '오늘 기준 다음 목요일'(_nextThu)을 셌고 홈은 '매주 갱신' 고정 문구였다. 그래서
   09-24~26 배치가 멈춘 동안 홈은 9일 묵은 값을 '매주 갱신' 아래 보였고, rel-week 는 데이터가 아니라 오늘로
   세어 밀린 회차를 건너뛴 날짜를 냈다.
   p: 최신 조사기준일(월). grace: ADV.weekly.grace — 감시(check_freshness)와 같은 상수를 split_data 가 싣는다.
   grace 가 없으면(옛 캐시) 지연을 판정하지 않는다 — 여기 숫자를 따로 적지 않는다.
   · 다음 발표 = 다음 조사분의 목요일(p+10). 그 주 월~목에 공휴일이 끼면 hedge — 날짜를 단정하지 않는다.
     2026 추석에 9/21 조사분은 휴일인 9/24(목) 당일에 올라왔다. 옛 규칙(다음 영업일 9/28)도, '연휴 전에
     당긴다'는 추측도 틀렸다. 관측 한 번으로는 규칙을 못 세우므로 날짜 대신 안내 문구를 쓴다.
   · 지연 = p+grace+1(감시가 실패로 보기 시작하는 날)을 휴일이면 영업일로 민 날이 **다 지났는데** 새 주차가
     없을 때. 감시는 그날 배치 뒤에 돌지만 화면은 발표 당일 아침에도 보이므로 그 하루를 더 준다.
   · 연휴 주(hedge)는 원천이 조사를 한 주 거르기도 해서(2025 설·추석 실측) 기준일을 한 주 늦춘다
     (전수리뷰 #10, 대표 결정 ④ — 파이썬 WR.status 와 같이). */
function weeklyRelease(p,now,grace){
  const b=_dn(p), nx=b+10;
  let hedge=false;
  for(let k=0;k<=3;k++)if(_HOLIDAYS.has(_iso(nx-k)))hedge=true;   // 발표 주 월~목
  const due=(grace==null)?null:_bizDay(b+grace+1+(hedge?7:0));
  return {survey:p,pub:_iso(b+3),next:_iso(nx),hedge:hedge,
          due:due==null?null:_iso(due),stale:due!=null&&_kst(now).day>due};
}
function _md(iso){const a=String(iso).split('-');return (+a[1])+'/'+(+a[2]);}
/* 날짜 표기 두 단계(2026-10-06 대표 결정 — 같은 달이 2026.08·2026-08·26-08·26.08·26.8·2026년 8월 여섯 가지로 나왔다).
   글로 읽는 곳(기준 줄·배너·문장)은 '9/28'(_md)·'2026년 8월'(_ymT)·'2026년 2분기'(_qT), 좁은 곳(표 칸·눈금·말풍선)은 '26.9.28'(_dS)·
   '26.8'(_ymS)·'26Q2'. 파이썬 정본은 sido_zones.day_text·day_short·month_text·month_short·quarter_text(test_date_format 이 node 로 대조한다).
   받는 값은 '2026-08'·'2026.08'·'2026.08 p)'·'2026-09-28' 어느 것이든 된다. */
function _ymP(s){const m=String(s).match(/(\d{4})[.\-\/]\s*(\d{1,2})/);return m?[+m[1],+m[2]]:null;}
function _ymT(s){const p=_ymP(s);return p?p[0]+'년 '+p[1]+'월':String(s);}
function _ymS(s){const p=_ymP(s);return p?String(p[0]).slice(2)+'.'+p[1]:String(s);}
function _qT(k){const m=String(k).match(/^(\d{4})Q([1-4])$/);return m?m[1]+'년 '+m[2]+'분기':String(k);}
function _dS(iso){const a=String(iso).split('-');return a.length<3?String(iso):a[0].slice(2)+'.'+(+a[1])+'.'+(+a[2]);}
/* 연휴 주(hedge)는 날짜를 단정하지 않되 안내 문구도 적지 않는다(빈 문자열 — 2026-10-05 대표 요청으로 '연휴로 발표 일정이
   바뀔 수 있습니다'를 뺐다). 그래서 이어 붙이는 쪽은 빈 조각을 거른다(wkWhenText·통계 탭 rel-week).
   wkWhenText 는 /weekly/ 머리줄(파이썬 weekly_release.when_text)의 JS 거울이다 — 홈 화면은 2026-10-05 부터 '9/28 기준 ·
   한국부동산원'(wkMapModel)을 쓰지만, 두 문장 규칙이 갈리지 않는지 시험(test_weekly_release·test_home_first_screen)이 이 함수로 본다. */
function wkNextText(r){
  if(r.stale)return '이번 주 발표분 반영 대기';
  if(r.hedge)return '';
  return '다음 발표 '+_md(r.next)+'('+'일월화수목금토'[_wd(_dn(r.next))]+')';
}
/* 결론 앞 발표일 머리말 — 평상 '9/24 발표', 늦은 주 '9/17 발표 기준'(파이썬 WR.pub_lead). 주간 구역 머리말(평상)·늦은 주의
   h2·지도 시세 모드 범례가 같이 쓴다(B1·MOB-1). */
function wkPubLead(r){return _md(r.pub)+' 발표'+(r.stale?' 기준':'');}
function wkWhenText(r){
  if(r.stale)return '최근 반영: '+_md(r.pub)+' 발표 · '+wkNextText(r);
  return [_md(r.survey)+' 조사',_md(r.pub)+' 발표',wkNextText(r)].filter(Boolean).join(' · ');
}
// </wk-release>
function _syncHolidays(){
  if(typeof ADV!=="undefined"&&Array.isArray(ADV.holidays)&&ADV.holidays.length)_HOLIDAYS=new Set(ADV.holidays);
}
/* 홈 주간 격자·통계 탭이 같이 읽는 '최신 주 발표 상태'. 데이터가 없으면 null. */
function weeklyReleaseNow(){
  _syncHolidays();
  let W;try{W=ADV.weekly;}catch(e){return null;}
  const row=W&&W.rows&&W.rows[W.rows.length-1];
  if(!row||!/^\d{4}-\d{2}-\d{2}$/.test(row.p||''))return null;
  return weeklyRelease(row.p,new Date(),W.grace);
}
/* 발표 안내 줄(rel-week)·통계 그래프·투자지표·버블밴드 → home-stats.js(B11) */
/* ===== 아공맵 스코어: 시도(집계 포함) 공급 지표 ===== */
/* ── 시도(집계 포함) 공급 지표 ──────────────────────────────────────────────────
   2026-08-06 이전에는 홈이 scCalc()로 순부족을 직접 계산하고 Python과 산식을
   글자 단위로 맞추는 이중구현 미러를 유지했다(check_dual_calc.py가 감시). 산식을
   국토부 준공·착공으로 바꾸면서 계산을 빌드 시점으로 옮겼다 — 화면은 ADV.sido를
   읽기만 하므로 두 구현이 갈릴 일이 없다. 정본은 tools/sido_zones.py 하나다.
   ⚠️ 여기에 sidoOf() 같은 헬퍼를 다시 만들지 말 것 — home-stats.js 에 시군구 코드용
   sidoOf(code)가 이미 있고, 함수 선언은 호이스팅돼 나중 것이 앞의 것을 가린다(분할 파일은 나중에 실행되므로
   거꾸로 홈의 같은 이름 함수를 덮어쓴다 — 두 파일에 같은 최상위 이름을 두지 않는다, test_home_parts).
   실제로 내 지역 기능을 지우고 남은 죽은 sidoOf(nm)가 그걸 가려 통계 탭의
   시군구 선택이 영구히 비어 있었다(2026-08-07 감사). */

/* ── 공급·가격 통합표 ─────────────────────────────────────────────────────
   행=기간, 열=시도(집계 포함), 칸=공급 세대수 + 배경색.
   과거 칸은 세로 3등분(왼쪽부터 매매/전세/월세), 미래 칸은 적정물량 대비 단색.
   ⚠️ 값이 정확히 0.00일 때만 무색이다. 옅은 값을 흰색으로 두면 오류처럼 보인다
   (2026-08-06 사용자 지적) — TB_MIN이 그 바닥을 만든다.

   ⚠️ 표는 **월 단위로 짓고 위로 합친다**. 분기로 고정해 짓던 첫 구현에는 셋이
   같이 있었다(2026-08-06 리뷰): 연 모드의 혼합 표시가 모든 과거 연도에 붙었고,
   부분 기간(2029년 2분기치·2017년 3분기치)이 1년치 적정물량과 비교돼 과대 부족으로
   보였고, '월' 버튼은 눌려도 분기 표를 그렸다. 합치는 칸 수(n)를 들고 다니면
   적정물량도 같은 비율로 따라와 셋이 한꺼번에 해결된다. */
var TB_PER='q';
var TB_MIN=0.13;          // 0이 아니면 최소 이만큼은 물들인다
var TB_PRICE_SCALE=2;     // 가격 변동 ±2%가 만색. ±3%로 넓히지 말 것 —
                          // 최근 서울이 진한 건 실제로 공급부족이라서다(사용자 확인).
var TB_FROM=2017*12;      // 표 시작 = 2017.01 (적정물량 기준표와 같은 구간)
var TB_ANCHOR=true;       // 다음 렌더에서 굵은 줄로 세로 위치를 맞출지
var TB_SIZE={m:1,q:3,y:12};
/* 결측은 '변동 없음(0.00%)'과 구별해야 한다. 광주·전남은 2025-05~2026-06 14개월
   지수가 통째로 결측인데 예전엔 두 경우가 똑같이 무색이라 '1년째 완전 보합'으로
   읽혔다(2026-08-07 감사). 빗금은 평평한 색과 헷갈리지 않는다. */
var TB_NODATA='repeating-linear-gradient(45deg,transparent 0 3px,rgba(120,120,120,.16) 3px 5px)';
/* 월 모드는 150행 × 약 20지역 × 3등분 ≈ 9,000칸이라 이 함수가 만드는 문자열이
   렌더 시간의 큰 몫이다. 색은 알파 3자리로 양자화되니 결과가 몇백 종류뿐 —
   기억해 두면 toFixed와 문자열 조립을 대부분 건너뛴다(2026-08-07 감사). */
var TB_TINTC={};
/* 상승/하락 끝점과 알파 산식의 정본 — 표 칸(tbTint)·지도·그래프(mapFill)가 같이
   쓴다. '색 문법 통일'(21ba32f) 이후에도 산식이 복제돼 있어 한쪽만 튜닝하면
   조용히 갈라지는 상태였다(2026-08-10 리뷰). PAPER_RGB는 CSS --paper의 사본 —
   토큰을 바꾸면 여기도 같이 바꿀 것. */
var TB_UP=[198,58,48], TB_DN=[38,110,180], PAPER_RGB=[244,246,245];
function tintA(v,scale){ return (TB_MIN+(1-TB_MIN)*Math.min(1,Math.abs(v)/scale))*0.8; }
function tbTint(v,scale){
  if(v==null) return TB_NODATA;
  if(v===0) return 'transparent';
  var a=tintA(v,scale);
  var k=(v>0?'r':'b')+a.toFixed(3);
  var c=TB_TINTC[k];
  if(c===undefined){ c='rgba('+(v>0?TB_UP:TB_DN).join(',')+','+a.toFixed(3)+')'; TB_TINTC[k]=c; }
  return c;
}
/* toFixed(1)은 -0.04를 '-0.0'으로 만든다. 0.0인데 부호만 붙은 값은 '변동 없음'으로
   읽히지 않고 오류처럼 보인다(2026-08-08 감사). 반올림 결과로 부호를 정한다. */
/* 소수 둘째 자리로 반올림했더니 0.00인데 부호만 남는 값들이 있었다 —
   '-0.00%'가 주간 지도 9칸·표 16칸에 찍히고 하락(파랑) 색까지 받았다
   (2026-08-08 감사). 표시값 기준으로 부호를 정한다. */
/* Math.round는 half-toward-+Infinity라 -0.085가 -0.08로 **작아진다**(양수는 커진다).
   부호 대칭이 깨져 원자료 대비 마지막 자리가 틀린 칸이 113개 있었다(2026-08-08 감사).
   절대값으로 반올림해 대칭을 지킨다. */
function pv2r(v){ return (v<0?-1:1)*Math.round(Math.abs(v)*100)/100; }
function pv2(v){ if(v==null) return '·';
  var r=pv2r(v);
  return (r>0?'+':'')+r.toFixed(2); }
/* 표시값이 0.00인데 원값 부호로 빨강·파랑을 칠하면 같은 '0.00'이 세 색으로 갈린다
   — 글자와 색이 서로 다른 말을 한다(2026-08-08 감사). 색도 표시값으로 정한다. */
function pvSign(v){ return v==null?0:pv2r(v); }
function tbPv(a){ if(a==null) return '자료 없음';
  var r=Math.round(a*10)/10;
  return (r>0?'+':'')+(r===0?(0).toFixed(1):r.toFixed(1))+'%'; }
/* Number.prototype.toLocaleString은 호출마다 포맷터를 새로 세운다. 월 모드는
   칸이 3,000개라 그것만으로 렌더의 절반을 먹었다(2026-08-07 감사). 천단위
   쉼표는 직접 넣는다 — 이 표의 값은 전부 음수 없는 정수 세대수다. */
function tbNum(x){ return String(x).replace(/\B(?=(\d{3})+(?!\d))/g,','); }
function tbMi(d){ return +d.slice(0,4)*12 + (+d.slice(5,7)-1); }   // 'YYYY.MM'/'YYYY-MM' → 월 인덱스
function tbQLast(q){ return +q.slice(0,4)*12 + (+q.slice(5))*3 - 1; }  // '2026Q2' → 그 분기 마지막 달
function tbLabel(i,per){
  var y=Math.floor(i/12);
  if(per==='y') return String(y);
  if(per==='q') return ('0'+(y%100)).slice(-2)+'Q'+(Math.floor((i%12)/3)+1);
  return ('0'+(y%100)).slice(-2)+'.'+(i%12+1);
}
/* 월별 원장. 여기서만 원자료를 읽고, 아래 tbAgg가 기간 단위로 접는다.
   ⚠️ KOSIS는 값 0을 '-'로 준다. null은 결측이 아니라 진짜 0이다(시도합÷전국이
   모든 연도 1.00). 건너뛰면 그 달이 통째로 사라진다. */
var TB_BCACHE=null;   // 원천(ADV/STATS)은 페이지 수명 내내 불변 — 한 번만 짓는다
function tbBuild(){
  if(TB_BCACHE) return TB_BCACHE;
  /* data-core.js 를 못 받은 부팅(전수리뷰 #43)에도 공급 구역의 '표'·'그래프'·기간 단추는 켜져 있다 — ADV 가 없으면
     ReferenceError 대신 null 로 돌아가 tbDraw 가 구역을 숨긴다(정적 요약은 남는다, 통합 검토). */
  if(typeof ADV==='undefined'||typeof STATS==='undefined') return null;
  var S=ADV.sido; if(!S||!S.zones||!S.zones.length) return null;
  var D=STATS['준공'], K=STATS['착공']; if(!D||!K) return null;
  var regs=S.zones.map(function(z){return z.z;});
  var refs={}, est={}; S.zones.forEach(function(z){ refs[z.z]=z.ref; est[z.z]=z.est; });
  var di={}, ki={};
  D.dates.forEach(function(d,n){ di[tbMi(d)]=n; });
  K.dates.forEach(function(d,n){ ki[tbMi(d)]=n; });
  /* ⚠️ 경계는 **분기 기준**이어야 한다. 준공 시리즈의 마지막 '월'을 쓰면, KOSIS가
     분기 중간까지만 발표한 달(매달 일어난다)에 홈은 그 달을 실적으로 그리고
     지역 페이지(make_sido_pages.series)는 같은 분기를 통째로 착공 추정으로 그려
     두 화면이 같은 분기에 다른 숫자를 보여준다(2026-08-07 리뷰).
     sido_zones가 이미 정한 L(마지막 완결 분기)과 H를 그대로 따른다. */
  var lastD=tbQLast(S.L);
  var LEAD=S.lead*3;                       // 12분기 = 36개월
  var pi={}, P=ADV.monthly||{};
  (P.regions||[]).forEach(function(r,n){ pi[r]=n; });
  var prow={};
  (P.rows||[]).forEach(function(r){ prow[tbMi(r.p)]=r; });
  var rows=[];
  for(var i=TB_FROM;i<=lastD+S.H*3;i++){
    var fut=i>lastD, sup=[];
    for(var k=0;k<regs.length;k++){
      var r=regs[k];
      if(fut){
        /* ⚠️ 여기서 반올림하지 않는다. 월별로 반올림해 더하면 분기 합이
           zone 페이지(분기 착공 합 × conv를 한 번만 반올림)와 어긋난다 —
           미래 240칸 중 51칸이 ±1이었다(2026-08-07 감사). 표시 직전에 한 번만. */
        var j=ki[i-LEAD];
        sup.push(j==null?0:((K.series[r]||[])[j]||0)*S.conv);
      }else{
        var n=di[i];
        sup.push(n==null?0:((D.series[r]||[])[n]||0));
      }
    }
    var pr=fut?null:prow[i];
    rows.push({i:i,fut:fut,s:sup,
      m:pr?regs.map(function(r){return (pr.ma||[])[pi[r]];}):null,
      j:pr?regs.map(function(r){return (pr.je||[])[pi[r]];}):null,
      w:pr?regs.map(function(r){return (pr.wo||[])[pi[r]];}):null});
  }
  /* um·uw(부족+미분양 경고)는 표 정비(2026-08-08 사용자: '참고 행에 색·표식을
     두르지 않는다')로 소비처가 사라져 걷어냈다 — 경고문은 지역 페이지(zwarn)가
     본문으로 말한다. */
  var un={},pm={};
  S.zones.forEach(function(z){ un[z.z]=z.unsold; pm[z.z]=z.pm12; });
  /* 분기·연 가격 합은 split_data 가 원값으로 한 번 더해 실은 ADV.monthly.agg 를 읽는다(tbAgg). pidx 는 regs → 그 배열의 칸. */
  return TB_BCACHE={regs:regs,refs:refs,est:est,rows:rows,H:S.H,L:S.L,
          un:un,pm:pm,uprd:S.unsold_prd,
          pagg:P.agg||null,pidx:regs.map(function(r){return pi[r];})};
}
/* 월 원장 → 기간 단위. n(합친 달 수)을 같이 돌려줘야 부분 기간의 적정물량이
   같은 비율로 줄어든다 — 안 그러면 2029년(2분기치)이 1년치 기준과 비교돼
   과대 부족으로 보인다. */
/* 가격 변동(매매·전세·월세)의 기간 합은 **달이 다 찬 칸만** 낸다(전수 리뷰 #15, 대표 결정 ⑧). 값이 있는 달만 더하면
   전남광주 25Q2(6월 결측)가 두 달 합으로, 연 보기의 마지막 해가 몇 달 합으로 '그 기간 변동률'처럼 칠해졌다. 덜 찬 칸은
   null('자료 없음'·무색). 분기·연 합은 split_data 가 정본 sido_zones.price_periods 로 **원값**을 한 번 더해 실은
   ADV.monthly.agg 를 읽는다(#110 — 소수 둘째 자리로 반올림한 월값을 여기서 더하면 시도 리포트와 칸의 5%에서 갈렸다).
   agg 가 없는 옛 데이터면 같은 규칙(달 수가 모자라면 null)으로 여기서 더한다. */
var TB_PF={m:'ma',j:'je',w:'wo'};
function tbAgg(rows,per){
  var size=TB_SIZE[per]||3, out=[], cur=null, key=null;
  var B=TB_BCACHE, A=(size>1&&B&&B.pagg)?B.pagg[per]:null;
  rows.forEach(function(r){
    var g=Math.floor(r.i/size);
    if(cur===null||g!==key){
      key=g;
      cur={i:g*size,g:g,n:0,nf:0,s:r.s.map(function(){return 0;}),m:null,j:null,w:null,c:{}};
      out.push(cur);
    }
    cur.n++; if(r.fut) cur.nf++;
    r.s.forEach(function(v,k){ cur.s[k]+=v; });
    ['m','j','w'].forEach(function(f){
      if(!r[f]) return;
      if(!cur[f]){ cur[f]=r.s.map(function(){return null;}); cur.c[f]=r.s.map(function(){return 0;}); }
      r[f].forEach(function(v,k){ if(v!=null){ cur[f][k]=(cur[f][k]||0)+v; cur.c[f][k]++; } });
    });
  });
  out.forEach(function(c){
    c.fut=(c.nf===c.n);                 // 전부 미래일 때만 미래 행
    c.mix=(c.nf>0&&c.nf<c.n);           // 실적과 추정이 한 칸에 섞였다
    c.part=(c.n<size);                  // 기간이 덜 찼다(표 시작·끝)
    var lab=per==='q'?(Math.floor(c.g/4)+'Q'+(c.g%4+1)):String(c.g), got=A?(A[lab]||null):null;
    ['m','j','w'].forEach(function(f){
      if(!c[f]) return;
      if(A){ var arr=got&&got[TB_PF[f]]; c[f]=B.pidx.map(function(p){ return (arr&&p!=null&&arr[p]!=null)?arr[p]:null; }); }
      else c[f]=c[f].map(function(v,k){ return c.c[f][k]===size?v:null; });
    });
    delete c.c;
  });
  return out;
}
function tbPer(p){
  if(TB_PER===p) return;
  TB_PER=p;
  TB_ANCHOR=true;      // 행 집합이 통째로 바뀌므로 다시 조준한다
  var seg=document.getElementById('tb-per');
  if(seg) [].forEach.call(seg.children,function(b){
    var on=b.dataset.p===p;
    b.classList.toggle('on',on);
    b.setAttribute('aria-pressed',on?'true':'false');   // 선택 상태를 음성으로도
  });
  tbDraw();
  if(typeof track==='function') track('supply_table',{period:p});
}
function tbDraw(){
  var el=document.getElementById('tb-main'); if(!el) return;
  tbDraw.done=1;                       // 지연 렌더 판정용(tbView 참조)
  var B=tbBuild();
  if(!B){ var sec=document.getElementById('sec-score'); if(sec) sec.style.display='none'; return; }
  var rel=(document.getElementById('tb-rel')||{}).checked;
  var size=TB_SIZE[TB_PER]||3;
  var rows=tbAgg(B.rows,TB_PER);
  /* 접근성: 열 머리에 scope="col", 기간 칸은 행 머리(th scope="row")로 낸다.
     칸 안 가격 변동은 배경색으로만 전달되므로 title에 글로도 넣는다 —
     스크린리더·색각이상 사용자가 공급 세대수만 얻던 문제(2026-08-07 감사). */
  var h='<caption class="sr-only">기간별 시도 아파트 공급 세대수. '
    +'각 칸의 배경색은 과거 구간에서는 매매·전세·월세 변동률, 미래 구간에서는 '
    +'적정물량 대비 부족분을 나타내며, 같은 값을 칸의 설명 텍스트로도 제공합니다.</caption>'
    +'<thead><tr><th scope="col">기간</th>';
  B.regs.forEach(function(r){
    /* 추정 지역 표식(*)은 달지 않는다 — 뜻을 알 길 없는 기호였다(2026-08-08
       사용자). 어느 지역이 추정인지는 '산출 방법' 접힘이 문장으로 말한다. */
    h+='<th scope="col"><a class="tb-zl" href="/zone/'+encodeURIComponent(r)+'/">'+r+'</a></th>';
  });
  /* ⚠️ 적정물량 '수치'까지 th scope="col"로 두면 스크린리더가 그 열의 모든 칸마다
     '95,000'을 헤더로 읽는다. 열 이름은 위 줄(지역명)이고 이 줄은 데이터다
     (2026-08-08 감사). 줄 이름만 행 머리로 두고 수치는 td로 낸다. */
  h+='</tr><tr class="tb-ref"><th scope="row">적정물량</th>';
  B.regs.forEach(function(r){
    h+='<td>'+tbNum(Math.round(B.refs[r]*size/3))+'</td>';
  });
  h+='</tr></thead><tbody>';
  var firstFut=true;
  rows.forEach(function(r){
    var cls=[];
    if(r.fut) cls.push('fut');
    /* 굵은 줄은 '전부 미래인 첫 행'이 아니라 **미래가 처음 섞이는 행** 앞에 긋는다.
       연 모드에서 2026년은 실적 2분기 + 추정 2분기라 fut가 아니고, 줄을 fut 기준으로
       그으면 2027년 앞에 놓여 2026년 절반이 추정이라는 사실이 줄 위로 숨는다
       (2026-08-06 사용자 지정). 분기·월 모드에는 섞인 행이 없어 동작이 같다. */
    if(r.nf>0&&firstFut){
      cls.push('now'); firstFut=false;
      /* 경계는 선이 아니라 말하는 밴드로(2026-08-08 사용자) — "굵은 줄"이 뭘
         가르는지 각주까지 안 가도 그 자리에서 읽힌다. 문구는 붙박이(sticky)로,
         가로 스크롤해도 시야에 남는다. */
      /* ⚠️ 행 전체를 aria-hidden하면 실적/추정 경계가 접근성 트리에서 사라져
         스크린리더가 추정치를 실적처럼 읽는다(2026-08-10 리뷰). 문장은 읽히게,
         장식 화살표만 숨긴다. */
      h+='<tr class="tb-nowrow"><td colspan="'+(B.regs.length+1)
        +'"><span><i aria-hidden="true">▼ </i>아래는 착공 실적으로 추정한 미래입니다</span></td></tr>';
    }
    var mark='';
    if(r.mix) mark='<i class="tb-mx" title="실적과 착공 기준 추정이 섞인 기간">±</i>';
    else if(r.part) mark='<i class="tb-mx" title="'+r.n+'개월치만 있는 기간">·</i>';
    var lab=tbLabel(r.i,TB_PER);     // 칸마다 다시 만들면 6,000번 호출된다
    h+='<tr class="'+cls.join(' ')+'"><th scope="row">'+lab+mark+'</th>';
    for(var k=0;k<B.regs.length;k++){
      var ref=B.refs[B.regs[k]]*r.n/3, v=r.s[k];
      var txt=rel?(ref?Math.round(v/ref*100)+'%':'–'):tbNum(Math.round(v));
      var lay;
      if(r.fut){
        lay='<i class="tl f" style="background:'+tbTint(ref?1-v/ref:null,1)+'"></i>';
      }else{
        lay='<i class="tl a" style="background:'+tbTint(r.m?r.m[k]:null,TB_PRICE_SCALE)+'"></i>'
           +'<i class="tl b" style="background:'+tbTint(r.j?r.j[k]:null,TB_PRICE_SCALE)+'"></i>'
           +'<i class="tl c" style="background:'+tbTint(r.w?r.w[k]:null,TB_PRICE_SCALE)+'"></i>';
      }
      var alt;
      if(r.fut){
        alt = ref ? ('적정물량의 '+Math.round(v/ref*100)+'%, 착공 기준 추정') : '착공 기준 추정';
      }else{
        alt = '매매 '+tbPv(r.m?r.m[k]:null)+' · 전세 '+tbPv(r.j?r.j[k]:null)+' · 월세 '+tbPv(r.w?r.w[k]:null);
      }
      h+='<td title="'+B.regs[k]+' '+lab+' — '+alt+'">'
        +'<span class="tc">'+lay+'<b>'+txt+'</b></span></td>';
    }
    h+='</tr>';
  });
  /* ── 미분양 줄 ────────────────────────────────────────────────────────
     미분양은 **순위 산식에 넣지 않는다**(결과값이라 재고에서 차감하면 부호가
     반대고 이중계상된다). 여기 있는 건 위 칸들을 읽는 맥락이다.
     색·표식도 두르지 않는다(2026-08-08 사용자) — 참고 행이 색을 입으면
     점수 행처럼 읽히고, ⚠ 같은 기호는 뜻을 알 길이 없다. 설명은 '산출 방법'
     접힘이 맡는다. */
  h+='</tbody><tfoot><tr class="tb-un" data-ref="un"><th scope="row" title="'+(B.uprd?_ymT(B.uprd):'')
    +' 기준 · 순위에 넣지 않은 참고 수치">'+refBtn('미분양')+'</th>';
  for(var u=0;u<B.regs.length;u++){
    var uv=B.un[B.regs[u]];
    h+='<td><span class="tc"><b>'+(uv==null?'–':tbNum(uv))+'</b></span></td>';
  }
  h+='</tr>';
  /* 인허가 줄(2026-08-11 사용자) — 미분양과 같은 참고 행. 위 칸들은 분기(또는 토글
     단위) 값인데 인허가는 최근 12개월 합이라 라벨에 창을 박는다. 착공 전 단계로
     이어지는 선행 물량이라, 표의 마지막 분기 너머를 미리 보여주는 유일한 줄이다. */
  h+='<tr class="tb-un" data-ref="pm"><th scope="row" title="최근 12개월 합 · 착공 전 단계의 선행 물량 · 순위에 넣지 않은 참고 수치">'+refBtn('인허가 1년')+'</th>';
  for(var u2=0;u2<B.regs.length;u2++){
    var pv=B.pm[B.regs[u2]];
    h+='<td><span class="tc"><b>'+(pv==null?'–':tbNum(pv))+'</b></span></td>';
  }
  h+='</tr></tfoot>';
  el.innerHTML=h;
  /* 참고 행 탭 안내(2026-08-11 사용자) — title 툴팁은 데스크톱 호버 전용이라
     모바일에서는 뜻을 알 길이 없다. 행을 누르면 표 아래에 설명이 열린다.
     리스너는 테이블 노드에 한 번만 건다(innerHTML은 자식만 갈아끼운다). */
  if(!el.dataset.refbound){
    el.dataset.refbound='1';
    el.addEventListener('click',function(ev){
      var tr=ev.target&&ev.target.closest?ev.target.closest('tr.tb-un'):null;
      if(!tr) return;
      var p=document.getElementById('tb-refnote');
      if(!p) return;
      var k=tr.getAttribute('data-ref');
      if(!p.hidden&&p.dataset.k===k){ p.hidden=true; }
      else{
        /* 미분양의 기준 시점(B.uprd)은 <th>의 title=에만 있었다 — 그건 데스크톱
           호버 전용이라 모바일에서는 뜻을 알 길이 없다. 지역 페이지는 같은 값을
           '2026년 6월 기준'이라고 눈에 보이는 칸으로 찍는데, 홈만 빠져 있어서
           모바일 방문자는 월간 재고를 이번 분기 값으로 읽었다(2026-08-15 리뷰).
           정본 문구(REFNOTE)는 홈·지역이 글자까지 같아야 하므로 상수는 건드리지
           않고, 여는 시점에 시점만 덧붙인다. */
        /* B는 표를 그리는 함수의 지역 변수라 여기선 못 본다 — tbBuild()는
           TB_BCACHE로 메모이즈돼 있어 다시 불러도 같은 객체다. */
        var note=TB_REFNOTE[k]||'', BB=tbBuild();
        if(k==='un'&&BB&&BB.uprd) note=_ymT(BB.uprd)+' 기준. '+note;
        p.dataset.k=k; p.textContent=note; p.hidden=false;
        /* 탭한 행이 화면 맨 밑이면 설명이 폴드 아래 열린다(모바일) —
           nearest라 이미 보이면 안 움직인다. */
        p.scrollIntoView({block:'nearest'});
      }
      tbRefSync();
    });
  }
  /* 기간을 바꾸면 tfoot이 새로 그려져 버튼의 aria-expanded가 false로 돌아간다 —
     설명이 열린 채라면 상태를 다시 맞춘다. */
  tbRefSync();
  var n=document.getElementById('tb-note');
  if(n) n.textContent=TB_PER==='y'?'한 해 합계':TB_PER==='m'?'한 달치':'';
  /* 표는 2017Q1부터라, 그냥 두면 첫 화면이 9년 전 숫자다. 기본 화면을 맨
     아래(최근 실적 → 미래 추정 → 참고 2행)로 연다 — 지역 페이지 표와 같은
     규칙(2026-08-11 사용자, 굵은 줄 1/3 조준을 대체). 스크롤은 열려 있다. */
  if(TB_ANCHOR) tbAnchor();
}
/* 표의 기본 화면을 맨 아래로 민다 — 단, 굵은 줄(현재)이 시야를 벗어나지 않는
   선까지만. 월 모드는 미래가 36행이라 바닥에 그냥 붙이면 '착공 기준 추정'만
   가득하고 실적도 현재 표시선도 안 보인다(2026-08-12 리뷰 실측: 굵은 줄이
   시야 위 482px 밖). 분기·연 모드는 미래 블록이 화면보다 작아 바닥 = 현재가
   같이 보이는 화면이다.
   ⚠️ 렌더링 생명주기에 묶인 것은 쓰지 말 것 — requestAnimationFrame도
   IntersectionObserver도 '그리지 않는 창'에서는 콜백이 영영 안 온다.
   2026-08-07에 rAF를 걷어내면서 뷰가 숨은 경우를 IO로 처리했는데, 같은
   함정을 다시 들인 것이었다(2026-08-08 실측: 명백히 보이는 요소에 새로
   붙인 관찰자도 600ms 동안 콜백 0건 — 그 사이 표는 2017Q1에서 열렸다).
   타이머는 렌더링과 무관하게 돌므로 재시도는 setTimeout으로 한다.
   getBoundingClientRect가 레이아웃을 동기로 강제하니 측정 자체는 즉시 된다. */
var TB_TRY=[0,50,150,400,900,1800];
function tbAnchor(n){
  var sc=document.querySelector('.tb-scroll');
  n=n||0;
  if(sc&&sc.clientHeight&&sc.offsetParent&&sc.scrollHeight>sc.clientHeight){
    TB_ANCHOR=false;
    sc.scrollTop=sc.scrollHeight;
    var nw=sc.querySelector('#tb-main tbody tr.now');
    var hd=sc.querySelector('#tb-main thead');
    if(nw){
      /* 굵은 줄이 붙박이 표두 아래로 들어올 때까지만 도로 내린다(월 모드). */
      var over=sc.getBoundingClientRect().top
              +(hd?hd.getBoundingClientRect().height:0)
              -nw.getBoundingClientRect().top;
      if(over>0) sc.scrollTop-=over;
    }
    return;
  }
  /* 아직 잴 수 없다(뷰가 숨었거나 레이아웃 전). 몇 번만 다시 본다 —
     무한 재시도는 하지 않는다. 그 사이 사용자가 표를 스크롤했다면
     TB_ANCHOR가 false라 자리를 뺏지 않는다. */
  if(n<TB_TRY.length) setTimeout(function(){ if(TB_ANCHOR) tbAnchor(n+1); }, TB_TRY[n]);
}
/* ── 홈 보기 전환: 지도(공간)/그래프(시간)/표(시간×공간) — 2026-08-08 ── */
var TB_VIEW='map';
/* 참고 행 라벨은 진짜 <button>이다 — tr에 tabindex를 얹으면 Enter/Space와
   역할 안내를 직접 다시 만들어야 하는데, 버튼은 브라우저가 다 해준다
   (2026-08-12 리뷰: 클릭 전용이라 키보드로는 설명에 닿을 길이 없었다). */
function refBtn(label){
  return '<button type="button" class="rbtn" aria-expanded="false" '
    +'aria-controls="tb-refnote">'+label+'<i class="ri" aria-hidden="true">ⓘ</i></button>';
}
function tbRefSync(){
  var p=document.getElementById('tb-refnote');
  [].forEach.call(document.querySelectorAll('#tb-main tfoot .rbtn'),function(b){
    var own=b.parentNode.parentNode.getAttribute('data-ref');
    b.setAttribute('aria-expanded',(p&&!p.hidden&&own===p.dataset.k)?'true':'false');
  });
}
/* ⚠️ 아래 두 문구는 tools/make_sido_pages.py의 REFNOTE를 옮긴 거울이다 —
   홈은 정적 파일이라 생성기가 주입할 수 없다. 한쪽만 고치면 테스트가 깨진다
   (test_refnote_copy_is_identical_on_home_and_zone). */
var TB_REFNOTE={
  un:'미분양은 다 짓고도 팔리지 않아 남아 있는 집입니다(국토교통부 월간 집계). 이미 지어진 재고에 들어 있어 순위 계산에 다시 넣으면 이중계산이라, 참고로만 보여줍니다.',
  pm:'인허가는 "짓겠다"고 허가받은 단계의 물량입니다. 착공과 같은 흐름으로 움직이지만 허가 뒤 착공하지 않는 물량이 섞여 있고 입주까지의 시차가 일정하지 않아 참고로만 봅니다. 월별 들쭉날쭉이 커서 최근 12개월 합으로 묶어 연간 적정물량과 견주고, 순위 계산에는 착공만 씁니다.'
};
/* 라벨 사다리 한 칸 올림(2026-08-15 PM 결정). 컷(GRADE_CUTS)은 그대로 —
   등급 키는 파이썬이 계산해 데이터에 굽고 여기선 이름만 붙인다. */
var TB_GRADE={g4:'심각한 부족',g3:'매우 부족',g2:'부족',g1:'균형',g0:'공급 여유'};
function tbView(v,quiet){
  /* 시세 모드(주간·월간)의 그래프·표는 새로 그리지 않고 시세 탭의 그 화면을 연다(전국, 2026-10-04 대표 요청) */
  if(v!=='map'&&MAP_MODE!=='supply'){
    var k=MAP_MODE==='monthly'?'month':'week';
    track('trend_pick',{period:k,region:'a0',from:'score_'+v});
    location.hash='#stats-market-'+k+'~a0'+(v==='table'?'-t':'');
    return;
  }
  if(TB_VIEW===v) return;
  TB_VIEW=v;
  var sec=document.getElementById('sec-score');
  sec.classList.remove('vm-map','vm-graph','vm-table');
  sec.classList.add('vm-'+v);
  var seg=document.getElementById('tb-view');
  if(seg) [].forEach.call(seg.children,function(b){
    var on=b.dataset.v===v;
    b.classList.toggle('on',on);
    b.setAttribute('aria-pressed',on?'true':'false');
  });
  if(v==='table'){
    if(!tbDraw.done) tbDraw();       // 표는 처음 열 때 굽는다(아래 boot 주석 참조)
    TB_ANCHOR=true; tbAnchor();      // 숨김 상태로 로드돼 초기 조준이 무산됐을 수 있다
  }
  if(v==='graph') renderSidoGraph();
  if(v==='map') renderSidoMap();
  /* quiet: 모드 단추가 지도로 돌릴 때(mapMode) — 사람이 보기를 바꾼 게 아니라 map_mode 하나만 잰다(2026-10-05 리뷰) */
  if(!quiet) track('supply_view',{view:v});
}
function tbSigned(v){ return (v>0?'\u2212':v<0?'+':'')+tbNum(Math.abs(v)); }
/* 지도 채움색 — 표의 미래 칸과 같은 규칙(적정 대비, 100%p 만색, TB_MIN 바닥)을
   지면색에 합성해 '불투명'하게 만든다. 시도 도형이 겹쳐 그려지므로(경기 위에
   서울·인천) 반투명을 그대로 쓰면 겹친 곳만 색이 이중으로 쌓인다. */
function mapFill(r,sc){
  if(r==null) return 'var(--paper2)';
  if(r===0) return 'var(--paper)';
  var a=tintA(r,sc||1);
  var C=r>0?TB_UP:TB_DN, P=PAPER_RGB;
  return 'rgb('+Math.round(P[0]+(C[0]-P[0])*a)+','+Math.round(P[1]+(C[1]-P[1])*a)+','
    +Math.round(P[2]+(C[2]-P[2])*a)+')';
}
/* 지도의 시도 채움(홈 마케팅 검수 C4②, 2026-09-27 대표 승인 — 09-13 결정 ② '지도 색 불변'을 바꾼다).
   '균형'(g1) 판정 지역은 중립 회색(--bal)으로 칠한다. 예전엔 비율이 0보다 크면 TB_MIN 바닥 때문에 연한 빨강이라
   균형으로 판정된 충북(1%)·세종(13%)·경기(17%)까지 붉게 보여, 16곳 중 13곳이 '부족'처럼 읽혔다(TRUST-3).
   등급은 파이썬(sido_zones.grade)이 구워 싣는다 — 여기서 비율 경계(0.5)를 다시 적지 않는다. 나머지 등급은
   예전 연속 농도(mapFill) 그대로다. --bal 은 범례 램프 가운데 '균형' 칸, 시도 리포트·허브의 균형 배지(.sc-tier.g1)
   와 같은 회색 계열이다(test_home_first_screen). */
var TB_BAL='var(--bal)';
function supplyFill(z){
  if(z&&z.grade==='g1') return TB_BAL;
  return mapFill(z?z.ratio:null);
}
/* 카드 ⓘ — '어떻게 계산했나' 한 줄을 펼치고 접는다(C4①). 기본은 접힘(첫 화면 높이를 지킨다). */
function aggHow(b){
  var p=document.getElementById(b.getAttribute('aria-controls'));
  if(!p) return;
  var on=b.getAttribute('aria-expanded')!=='true';
  b.setAttribute('aria-expanded',on?'true':'false');
  p.hidden=!on;
}
/* 판정 카드 한 칸(B2·MOB-7·HERO-5②·C4①). 두 줄 고정형: '전국 [부족]' / '686,396세대 →'. 넓은 화면(561px~)은 둘째 줄에
   '부족'을 잇고 셋째 줄에 '1년 적정물량의 1.8배'를 싣는다 — 모바일은 칸이 좁아 둘을 화면에서 감추고 스크린리더에만
   남긴다(비율은 ⓘ 줄과 지도 이름표에도 있다). 칸 끝 '→'는 카드가 링크임을 드러낸다(HERO-5②).
   글자는 전부 sido_zones 가 구운 필드(cnum·cdir·cpct·ctxt·ftxt)를 읽는다 — 이중 구현 금지. 옛 캐시(필드 없음)는
   ctxt 앞 조각이나 세대수만 보이고 ⓘ 는 빠진다. ⓘ 는 링크 밖의 형제 버튼이다(링크 안에 버튼을 넣으면 안 된다) —
   칸 오른쪽 위에 겹쳐 두고, 첫 줄은 그 자리만큼 비워 둔다. */
/* 해마다 입주 신호등(2026-10-05 대표 요청 — 지역 허브 칸과 같은 모양). 판정 배지 아래 제 줄(.agg-lt)에 동그라미 셋(1·2·3년 차).
   배지는 남긴다(2026-10-06 리뷰 — 배지 자리를 신호등이 맡자 560px 이하 카드에서 '부족·여유'가 화면에서 사라졌다. 그 폭은 세대수 뒤
   방향 말을 감춘다).
   값·색 키·읽어 줄 글은 split_data 가 sido_zones(year_lights·lights_aria)로 구워 싣는다(z.yl·z.ya) — 문턱(70·130%)을 여기 적지
   않는다. 옛 캐시(yl 없음)는 예전 배지를 그린다. */
function aggLights(z){
  return '<span class="zl" role="img" aria-label="'+(z.ya||'')+'">'
    +z.yl.map(function(y){ return '<span class="zl-d '+y.k+'">'+y.n+'</span>'; }).join('')+'</span>';
}
/* 신호등 범례 — 짧은 한 줄을 지도 아래 출처 줄(#lt-key)에 둔다(2026-10-06 대표 지적 — 카드 바로 아래 두 줄 범례는 장황하고
   콘텐츠 위를 가렸다. 문턱 70·130%는 지역 탭 '읽는 법'·FAQ 가 말한다). 이름은 ADV.sido.ylg(sido_zones.light_legend). */
function aggLightKey(z){
  var g=ADV.sido&&ADV.sido.ylg; if(!g||!g.length||!z||!z.yl) return '';
  var ns=z.yl.map(function(y){ return y.n; }).join('·');   // 해 수는 실린 값에서 센다(손으로 '1·2·3'을 적지 않는다)
  return '<span class="agg-lk-c">'+ns+'년 차 입주</span>'
    +g.map(function(x){ return '<span class="agg-lk-i"><span class="zl-d '+x[0]+'" aria-hidden="true"></span>'+x[2]+'</span>'; }).join('');
}
function aggCard(n,z,i){
  var num=z.cnum||(z.ctxt?String(z.ctxt).split(' · ')[0]:(tbSigned(z.tot)+'세대'));
  return '<div class="agg-c">'
    +'<a class="agg-a" href="/zone/'+encodeURIComponent(n)+'/">'
    +'<span class="agg-l1"><b>'+n+'</b><span class="sc-tier '+z.grade+'">'+TB_GRADE[z.grade]+'</span></span>'
    +(z.yl?'<span class="agg-lt">'+aggLights(z)+'</span>':'')
    +'<span class="agg-l2"><i class="agg-n'+(z.cnum?'':' agg-old')+'">'+num+(z.cdir?'<span class="agg-dir"> '+z.cdir+'</span>':'')
    +'<span class="agg-go" aria-hidden="true"> →</span></i>'
    +(z.cpct?'<i class="agg-p">'+z.cpct+'</i>':'')+'</span></a>'
    +(z.ftxt?'<button type="button" class="agg-i" aria-expanded="false" aria-controls="agg-how-'+i+'" onclick="aggHow(this)">'
      +'ⓘ<span class="sr-only"> '+n+' 어떻게 계산했나</span></button>':'')
    +'</div>';
}
/* ── 지도 모드: 공급 현황 / 주간 시세 / 월간 시세(홈 마케팅 검수 C3·IA-1 안 B, 2026-09-27 → 2026-10-04 월간·10-05 이름) ──────────────────────────────────────
   한 지도에 세 주기(분기 공급·주간·월간 시세)를 싣는다. 기본은 공급(분기 판정) — 첫 화면의 주인은 공급 지도다(IA-1). 같은 빨강·파랑이 모드마다
   다른 뜻(공급 부족·여유 ↔ 매매 상승·하락)이 되므로 모드마다 범례의 끝말·가운데 칸, 뜻 한 줄(제목과 단위), 지도 이름
   (aria-label)을 바꾸고(mapKeyHtml), 시세 모드는 기준 줄('9/28 기준 · 한국부동산원' — 지도/그래프/표 단추 왼쪽 #tb-when,
   2026-10-05 대표 요청으로 주간·월간 양식 통일)과 범례(wkPubLead)에 날짜를 박는다. 날짜는 통계 탭 발표 줄과 같은
   weeklyRelease/wkPubLead 다 — 여기서 날짜를 다시
   세지 않는다. 주간 값은 ADV.weekly 최신 행의 시도 매매 변동률, 글자는 pv2(표시 반올림 정본), 색은 통계 탭 시군구 주간
   지도·히어로 배경과 같은 mapColor(v, WK_MAP_REF)를 지면색 위에 불투명하게 합성한다(도형이 겹쳐 그려져 반투명이면 경기
   위 서울·인천만 진해진다 — mapFill 과 같은 까닭). 0.00 은 mapColor 가 보합 회색으로 칠한다 — 공급 모드의 '균형' 중립색
   (--bal, C4②)은 주간 모드에 쓰지 않는다(균형은 판정 등급이지 가격이 아니다).
   지역을 누르면 공급 모드는 시도 공급 리포트(/zone/<시도>/), 시세 모드는 그 시도 시세 그래프(#stats-market-<주기>~코드,
   2026-10-04)가 열린다 — 탭 표적(A8 다각형)·라벨 자리는 모드와 무관하게 같다. 시군구 시세는 아래 주간 구역이 맡는다.
   판정 카드 셋·ⓘ 식은 공급 판정의 글이라 주간 모드에서는 같은 자리를 주간 카드 셋(전국·수도권·지방 변동률)과
   발표 줄로 바꾼다 — 공급 카드를 남기면 '부족' 배지 아래 가격 색 지도가 붙어 두 뜻이 섞여 읽힌다. 카드는 같은 틀(.agg-c)
   이다. 주간 모드에만 있는 두 줄(카드 아래 발표 줄, 범례 뜻 한 줄)만큼 전환하면 지도가 내려간다 — 2026-09-28 공급 모드의 분포
   한 줄·범례 뜻 한 줄을 뺀 뒤 Chromium 실측 481px 이하 +55px(두 줄), 482px 이상 +28.9px(뜻 한 줄이 범례 줄에 붙거나 지도 위 오버레이로 간다).
   누른 뒤의 이동이라 CLS 는 아니다. 공급 모드에 같은 높이의 빈 자리를 두지는 않는다(빈 줄이 생긴다). 시험: test_home_map_mode. */
var MAP_MODE='supply';
/* 주간 변동 지도 색의 만색 기준(±0.4%p). 통계 탭 시군구 주간 지도(drawNationMap)·히어로 배경(renderHeroMap)과 한 값이다. */
var WK_MAP_REF=0.4;
/* mapColor 가 낸 반투명 rgba 를 지면색(PAPER_RGB) 위에 합성한 불투명 rgb 로. 회색·#hex 는 그대로 둔다. */
function opaqueOnPaper(c){
  var m=/^rgba\((\d+),\s*(\d+),\s*(\d+),\s*([\d.]+)\)$/.exec(c);
  if(!m) return c;
  var a=+m[4], P=PAPER_RGB;
  return 'rgb('+[0,1,2].map(function(k){ return Math.round(P[k]+(+m[k+1]-P[k])*a); }).join(',')+')';
}
function wkFill(v,ref){ return v==null?'var(--paper2)':opaqueOnPaper(mapColor(v,ref||WK_MAP_REF)); }
/* 월간 변동 지도 색의 만색 기준(±1.0%p) — 통계 탭 시군구 월간 지도(drawNationMap)와 한 값이다. */
var MO_MAP_REF=1.0;
/* '+0.13%' · '−0.03%' · '0.00%' — 값은 pv2(반올림 먼저, 부호는 표시값), 글리프만 하이픈 → 마이너스(주간 격자와 같다). */
function wkPct(v){ return v==null?'자료 없음':pv2(v).replace('-','−')+'%'; }
/* 주간 모드 재료 — 최신 주 시도 변동률과 발표 상태. r 은 weeklyRelease(…)(= weeklyReleaseNow()). 데이터가 없으면 null
   (그때는 주간 버튼을 잠근다). DOM 을 만지지 않는 순수 함수라 시험이 node 로 돌린다. */
function wkMapModel(W,r){
  var row=W&&W.rows&&W.rows[W.rows.length-1];
  if(!r||!row||!row.ma||!W.regions||!W.regions.length) return null;
  var v={};
  W.regions.forEach(function(n,i){ v[n]=row.ma[i]; });
  return {v:v,when:_md(r.survey)+' 기준 · 한국부동산원',lead:wkPubLead(r),stale:!!r.stale,
    k:'week',ref:WK_MAP_REF,unit:'전주 대비',adj:'주간',href:'/weekly/',to:'weekly_map_card'};
}
/* 월간 모드 재료(2026-10-04 대표 요청 — 홈에서 월간도 쉽게). 최신 달 시도 매매 변동률(ADV.monthly, 코어에 실린다).
   색 만색 기준은 통계 탭 시군구 월간 지도와 같은 MO_MAP_REF. 데이터가 없으면 null(월간 버튼을 잠근다). */
function moMapModel(W){
  var row=W&&W.rows&&W.rows[W.rows.length-1];
  if(!row||!row.ma||!W.regions||!W.regions.length||!/^\d{4}-\d{2}$/.test(row.p||'')) return null;
  var v={};
  W.regions.forEach(function(n,i){ v[n]=row.ma[i]; });
  var y=+row.p.slice(0,4), m=+row.p.slice(5,7), lead=m+'월 기준';
  return {v:v,when:y+'년 '+m+'월 기준 · 한국부동산원',lead:lead,stale:false,
    k:'month',ref:MO_MAP_REF,unit:'전월 대비',adj:'월간',href:'/monthly/',to:'monthly_map_card'};
}
/* 지금 모드의 시세 재료 — 공급 모드면 null. data-core 가 안 왔으면(ADV 없음) 시세 모드도 없다(2026-10-05 리뷰). */
function priceModel(mode){
  if(typeof ADV==='undefined') return null;
  if(mode==='weekly') return wkMapModel(ADV.weekly,weeklyReleaseNow());
  if(mode==='monthly') return moMapModel(ADV.monthly);
  return null;
}
/* 범례 한 덩어리 — M 이 없으면 공급, 있으면 그 시세(주간·월간). 끝말·가운데 칸을 모드마다 바꾸고, 주간은 뜻 한 줄(제목과 단위)을 단다.
   공급 범례 아래 뜻 한 줄('지난 4년 덜 지은 몫까지 더해 … · 2026년 2분기 기준')은 뺐다(2026-09-28 대표 결정 — 작은 글씨 정리.
   식은 카드 ⓘ·산출 방법에, 3년 구간은 지도 아래 '앞으로 3년(…~…)' 줄에 있다).
   주간 램프의 양끝·가운데 색은 지도 채움과 같은 wkFill 에서 뽑는다(범례와 지도가 다른 색을 말하지 않게). */
function mapKeyHtml(M){
  /* 공급 범례는 왼쪽 부족 → 오른쪽 여유(2026-10-06 대표 결정 — 지역 칸 막대·신호등과 같은 방향, '오른쪽일수록 공급이 많다').
     시세 범례(왼쪽 하락 → 오른쪽 상승)와도 '오른쪽 = 많음'으로 맞는다. */
  if(!M) return '<div class="tb-key map-key"><span class="mk-r"><span class="tk"><i class="tk-u"></i>공급 부족</span>'
    +'<span class="mk-ramp" aria-hidden="true"><i class="mk-ur"></i><i class="mk-b">균형</i><i class="mk-dr"></i></span>'
    +'<span class="tk"><i class="tk-d"></i>공급 여유</span></span></div>';
  var R=M.ref, lo=wkFill(-R,R), lo0=wkFill(-0.01,R), hi0=wkFill(0.01,R), hi=wkFill(R,R);
  return '<div class="tb-key map-key mk-wk"><span class="mk-r"><span class="tk"><i style="background:'+lo+'"></i>하락</span>'
    +'<span class="mk-ramp" aria-hidden="true"><i class="mk-d" style="background:linear-gradient(90deg,'+lo+','+lo0+')"></i>'
    +'<i class="mk-b" style="background:'+wkFill(0,R)+'">보합</i>'
    +'<i class="mk-u" style="background:linear-gradient(90deg,'+hi0+','+hi+')"></i></span>'
    +'<span class="tk"><i style="background:'+hi+'"></i>상승</span></span>'
    +'<span class="tk-n">아파트 매매가격 '+M.unit+' 변동률(%) · '+M.lead+'</span></div>';
}
/* 지도 이름(aria-label) — 색의 뜻을 모드마다 말한다. */
function mapAria(M){
  return M?'시도별 아파트 매매가격 '+M.adj+' 변동 지도 — 붉을수록 상승, 푸를수록 하락, 회색은 보합 · '+M.lead
    :'시도별 아파트 공급 부족 지도 — 붉을수록 부족, 푸를수록 여유, 회색은 균형';
}
/* 시세 카드 한 칸 — 판정 카드(aggCard)와 같은 틀: '전국 [상승]' / '+0.09% →' (넓은 화면은 셋째 줄 '매매 전주 대비').
   주간은 /weekly/, 월간은 /monthly/(이달의 통계)로 간다. */
function wkAggCard(n,v,M){
  var s=pvSign(v), k=v==null?'':(s>0?'wk-u':s<0?'wk-d':'wk-0'), w=v==null?'자료 없음':(s>0?'상승':s<0?'하락':'보합');
  return '<div class="agg-c"><a class="agg-a" href="'+M.href+'" onclick="track(\'home_cta\',{to:\''+M.to+'\'})">'
    +'<span class="agg-l1"><b>'+n+'</b><span class="sc-tier '+k+'">'+w+'</span></span>'
    +'<span class="agg-l2"><i class="agg-n">'+wkPct(v)+'<span class="agg-go" aria-hidden="true"> →</span></i>'
    +'<i class="agg-p">매매 '+M.unit+'</i></span></a></div>';
}
/* 시세 모드를 켤 수 있나 — 시세 재료가 있고 지도 좌표(sido-geo.js)가 왔을 때만. 시세 모드는 지도 전용이라(그래프·표는 시세 탭)
   좌표가 없으면 지도 폴백(표)과 시세 갈래가 서로 부르며 시세 탭으로 튄다(2026-10-05 리뷰) — 그때는 단추를 잠근다. */
function priceOk(m){ return typeof SIDO_GEO!=='undefined'&&!!priceModel(m); }
/* 모드 전환 — 버튼 상태(aria-pressed)를 맞추고 지도를 다시 그린다. 값 이름은 snake_case(supply·weekly·monthly), 측정은 map_mode. */
function mapMode(m){
  if(m!=='weekly'&&m!=='monthly') m='supply';
  if(m!=='supply'&&!priceOk(m)) return;
  seeFresh(m);   // N 배지는 켜져 있는 단추를 다시 눌러도 지운다(공급 현황은 처음부터 켜져 있다)
  if(MAP_MODE===m) return;
  MAP_MODE=m;
  var seg=document.getElementById('map-mode');
  if(seg) [].forEach.call(seg.querySelectorAll('button'),function(b){
    var on=b.dataset.m===m;
    b.classList.toggle('on',on);
    b.setAttribute('aria-pressed',on?'true':'false');
  });
  var el=document.getElementById('map-wrap');
  if(el) el.dataset.done='';
  /* 지도 아래 공급 출처 줄('앞으로 3년 공급 · 국토교통부 …')은 시세 지도의 출처가 아니다 — 시세 모드에서는 숨긴다(app.css .mm-price, 2026-10-05 리뷰) */
  var sec=document.getElementById('sec-score');
  if(sec) sec.classList.toggle('mm-price',m!=='supply');
  /* 시세 모드의 그래프·표는 시세 탭이 맡는다(tbView) — 공급 그래프·표를 보던 중이면 지도로 돌린다 */
  if(m!=='supply'&&TB_VIEW!=='map') tbView('map',true);
  renderAggCards();
  renderSidoMap();
  track('map_mode',{mode:m});
}
/* 모드 단추의 '새 데이터' N 배지(2026-10-08 대표 요청, B안). 데이터가 이 사이트에 처음 실린 날(KST)부터 ADV.fresh.days[모드] 일
   동안(그날 포함 — 주간 4·월간 7·공급 14, 정본 split_data.FRESH_DAYS) 단다. 처음 ADV.fresh.force 일(그날과 다음 날)은 눌렀든 안
   눌렀든 단다 — 시점과 날은 배치가 split_data.fresh_marks 로 싣는다. 방문자가 그 단추를 누르면 그 시점을 이 기기에만 기억해
   (개인정보처리방침 '브라우저에만 저장') 다시 달지 않는다. 다음 시점이 들어오면 또 단다.
   F: ADV.fresh, today: KST 일수(_kst().day), seen: {모드: 누른 시점} → 배지를 달 모드 목록. */
const MODE_SEEN_KEY='mode_seen';
function freshModes(F,today,seen){
  if(!F||!F.days) return [];
  return Object.keys(F.days).filter(function(m){   // 모드 목록은 데이터(split_data.FRESH_DAYS)가 정본 — 여기 따로 적지 않는다
    var f=F[m], n=F.days[m];
    if(!f||!f.p||!(n>0)||!/^\d{4}-\d{2}-\d{2}$/.test(f.d||'')) return false;
    var age=today-_dn(f.d);
    return age>=0&&age<n&&(age<(F.force||0)||!(seen&&seen[m]===f.p));
  });
}
function modeSeen(){
  try{var o=JSON.parse(lsGet(MODE_SEEN_KEY)||'{}');return o&&typeof o==='object'?o:{};}catch(e){return {};}
}
function markFresh(){
  var F=typeof ADV!=='undefined'?ADV.fresh:null;
  freshModes(F,_kst(new Date()).day,modeSeen()).forEach(function(m){
    var b=document.querySelector('#map-mode [data-m="'+m+'"]');
    /* 열 수 없는 모드(시세 재료·좌표 없음 — mapMode 가 priceOk 에서 돌아간다)에는 달지 않는다. 지울 길이 없는 배지가 되기 때문이다 */
    if(b&&(m==='supply'||priceOk(m))&&!b.querySelector('.nb'))
      b.insertAdjacentHTML('beforeend','<span class="nb"><span aria-hidden="true">N</span><span class="sr-only"> 새 데이터</span></span>');
  });
}
function seeFresh(m){
  var b=document.querySelector('#map-mode [data-m="'+m+'"] .nb');
  if(!b) return;
  b.remove();
  var f=typeof ADV!=='undefined'&&ADV.fresh&&ADV.fresh[m];
  if(!f||!f.p) return;
  var s=modeSeen(); s[m]=f.p; lsSet(MODE_SEEN_KEY,JSON.stringify(s));
}
/* 판정·시세 카드 셋(전국·수도권·지방)과 ⓘ 식·발표 줄 — 모드 버튼 아래, 지도/그래프/표 버튼 위(2026-10-04 대표 요청). 보기
   (지도·그래프·표)와 무관하게 늘 보인다. 공급 모드는 판정 카드, 시세 모드는 같은 자리에 변동률 카드(→ /weekly/·/monthly/)
   — 공급 카드를 남기면 '부족' 배지 아래 가격 색 지도가 붙어 두 뜻이 섞여 읽힌다. */
function renderAggCards(){
  var el=document.getElementById('agg-wrap');
  if(!el||typeof ADV==='undefined'||!ADV.sido||!ADV.sido.zones) return;
  var Z={}; ADV.sido.zones.forEach(function(z){ Z[z.z]=z; });
  ['weekly','monthly'].forEach(function(m){
    var b=document.querySelector('#map-mode [data-m="'+m+'"]');
    if(b&&!priceOk(m)){ b.disabled=true; b.title=(m==='weekly'?'주간':'월간')+' 시세 데이터를 불러오지 못했습니다'; }
  });
  var M=priceModel(MAP_MODE);
  var h='<div class="map-agg">', how='';
  ['전국','수도권','지방'].forEach(function(n,i){
    if(M){ h+=wkAggCard(n,M.v[n],M); return; }
    var z=Z[n]; if(!z) return;
    /* 카드 문구는 sido_zones 가 구워 싣는다(card_parts·zone_texts) — 여기서 다시 만들지 않는다
       (이중 구현 금지). 부호 대신 '부족·여유'를 말로 써 배지와 이중 부정이 되지 않는다(2026-09-15). */
    h+=aggCard(n,z,i);
    if(z.ftxt) how+='<p class="agg-how" id="agg-how-'+i+'" hidden><b>'+n+'</b> '+(z.ctxt||'')
      +'<br><span>어떻게 계산했나 · '+z.ftxt+'</span></p>';
  });
  h+='</div>'+how;
  var lk=document.getElementById('lt-key'); if(lk) lk.innerHTML=M?'':aggLightKey(Z['전국']);
  /* 시세 모드: 기준 줄 — 지도/그래프/표 단추 왼쪽(#tb-when, 2026-10-05 대표 요청). 양식은 주간·월간 하나로
     '9/28 기준 · 한국부동산원'(조사일)·'2026년 8월 기준 · 한국부동산원'(M.when). 공급 모드는 비운다(:empty 로 숨는다). */
  var tw=document.getElementById('tb-when');
  if(tw) tw.textContent=M?M.when:'';
  el.innerHTML=h;
}
/* 시도 이름 → 시군구 지도의 시도 머리 칸 코드(NATION_TILE, 서울 a7·광주 b3 …). 시세 모드 지도에서 지역을 누르면 그 시도
   시세 그래프(openTrendRegion — 광주·전남은 판정 단위 전남광주로 접힌다). */
function sidoCode(n){
  for(var i=0;i<NATION_TILE.t.length;i++){ var t=NATION_TILE.t[i]; if(t[4]&&t[0].length===2&&t[1]===n) return t[0]; }
  return null;
}
function renderSidoMap(){
  var el=document.getElementById('map-wrap');
  if(!el||el.dataset.done) return;
  /* data-core 가 안 오면(ADV 없음) 표도 못 굽는다 — 지도 버튼만 잠그고 돌아가 부팅의 라우팅(대결·해시)이 돌게 한다(전수리뷰 #43) */
  if(typeof ADV==='undefined'){
    var mb0=document.querySelector('#tb-view [data-v="map"]');
    if(mb0){ mb0.disabled=true; mb0.title='지도 데이터를 불러오지 못했습니다'; }
    return;
  }
  if(typeof SIDO_GEO==='undefined'||!ADV.sido||!ADV.sido.zones){
    /* 지도는 기본 모드다 — sido-geo.js가 안 오면(404·차단) 조용히 빠지면
       홈 첫 화면이 빈 상자가 된다(2026-08-08 감사 세션 지적). 표로 폴백하고
       지도 버튼은 잠근다. 그래프·표는 이 파일 없이도 온전하다. */
    if(TB_VIEW==='map'&&MAP_MODE==='supply') tbView('table');   // 시세 모드는 priceOk 가 막아 여기 오지 않는다
    var mb=document.querySelector('#tb-view [data-v="map"]');
    if(mb){ mb.disabled=true; mb.title='지도 데이터를 불러오지 못했습니다'; }
    return;
  }
  var Z={}; ADV.sido.zones.forEach(function(z){ Z[z.z]=z; });
  /* 시세 모드(주간·월간) 재료. 데이터가 없으면 그 버튼은 renderAggCards 가 잠그고 공급으로 그린다. */
  var M=priceModel(MAP_MODE);
  var h='';
  /* 행동 안내는 범례 속 11.5px 회색 각주였다('지역을 누르면 상세 리포트') — 첫 화면의 유일한 행동 안내인데
     읽히지 않았다(홈 마케팅 검수 A6·HERO-5①). 본문색 13.5px 한 줄로 키워 지도 바로 위에 둔다. 범례
     오버레이(데스크톱) 안에 넣으면 폭이 늘어 경기·서울 도형을 덮는다. */
  h+=M?'<p class="map-act">지도에서 지역을 누르면 '+M.adj+' 그래프가 열립니다</p>'
    :'<p class="map-act">지도에서 지역을 누르면 공급 리포트가 열립니다</p>';
  /* 라벨: 도 9곳은 도형 안에 들어가고, 광역시·세종 8곳은 도형이 작아 흰 테두리
     글자(halo)로 위에 얹는다. 탭 표적도 그 8곳만 투명 표적으로 넓힌다(아래 TAP_ 설명). */
  var SMALL={'서울':1,'인천':1,'대전':1,'광주':1,'대구':1,'부산':1,'울산':1,'세종':1};
  /* 탭 표적(A8·MOB-6, 2026-09-27). 예전엔 8곳 모두 r=22 투명 원이었는데 세종·대전(중심 거리 25.7),
     서울·인천(27.5), 부산·울산(39.9)은 반지름 합 44보다 가까워 원이 겹쳤고, 나중에 그린 원이 위에 놓여
     세종 원의 30%·인천 원의 25%·인천 라벨의 29%가 대전·서울 리포트로 열렸다(375px 실측).
     원을 통째로 줄이면 겹침은 풀리지만 라벨 가장자리가 원 밖으로 나가 옆 도(충남·충북·경기)로 샌다(같은 실측).
     그래서 원(반지름 TAP_R)은 그대로 두고, 가까운 작은 지역 쪽만 두 중심의 수직이등분선에서 TAP_GAP 안쪽으로
     잘라 낸다 — 두 표적 사이에 선을 긋는 셈이라 겹칠 수 없고, 라벨과 반대쪽은 예전 크기 그대로다.
     원은 TAP_N 각형으로 근사해 반평면으로 차례로 자른다(Sutherland–Hodgman). 좌표(SIDO_GEO)에서 매번 계산하므로
     경계 데이터가 바뀌어도 따라간다(겹치는 쌍을 손으로 적지 않는다). <path> 가 아니라 <polygon> 인 이유: 지도
     도형용 CSS(.map-box path 의 테두리·hover)가 투명 표적에 선을 그리지 않게. 시험: test_home_map_tap_targets. */
  var TAP_R=22, TAP_GAP=1, TAP_N=32;
  function tapShape(a){
    var pts=[],i;
    for(i=0;i<TAP_N;i++){ var t=2*Math.PI*i/TAP_N; pts.push([a.x+TAP_R*Math.cos(t),a.y+TAP_R*Math.sin(t)]); }
    SIDO_GEO.p.forEach(function(b){
      if(b===a||!SMALL[b.n]) return;
      var d=Math.hypot(b.x-a.x,b.y-a.y); if(d>=2*TAP_R) return;
      var ux=(b.x-a.x)/d, uy=(b.y-a.y)/d, lim=d/2-TAP_GAP, out=[];
      var f=function(p){ return (p[0]-a.x)*ux+(p[1]-a.y)*uy-lim; };   // ≤0 이면 내 쪽
      for(var k=0;k<pts.length;k++){
        var p=pts[k], q=pts[(k+1)%pts.length], fp=f(p), fq=f(q);
        if(fp<=0) out.push(p);
        if((fp<=0)!==(fq<=0)){ var s2=fp/(fp-fq); out.push([p[0]+(q[0]-p[0])*s2,p[1]+(q[1]-p[1])*s2]); }
      }
      pts=out;
    });
    return pts.map(function(p){ return p[0].toFixed(1)+','+p[1].toFixed(1); }).join(' ');
  }
  /* 범례는 지도 좌상단(서해 빈 공간) 오버레이 — 지도 아래 한 줄로 떨어져
     있으면 지도와 안 붙어 읽힌다(2026-08-08 사용자). pointer-events:none이라
     밑의 경기 북부 탭을 막지 않는다. */
  /* 범례: 램프 가운데 '균형' 칸(B2·TRUST-3②, C4② 중립색과 같은 --bal). 주간 모드(M)는 끝말·가운데 칸이 바뀌고 뜻 한 줄이
     붙는다(mapKeyHtml, C3). */
  h+='<div class="map-box">'+mapKeyHtml(M)
    +'<svg viewBox="0 0 '+SIDO_GEO.w+' '+SIDO_GEO.h
    +'" role="group" aria-label="'+mapAria(M)+'">';   /* 안에 링크가 있어 img 가 아니다 — img 는 자식을 읽지 않는다(백로그 36-8) */
  /* 광주·전남은 2026-09-10 판정 단위가 하나로 합쳐졌다(국토부가 공급 통계를
     '전남광주'로만 발표). 지도의 두 도형은 지리 정보라 그대로 두고, 색·링크·라벨은
     통합 지역을 가리킨다 — 한 판정을 두 땅이 나눠 갖는 모양이다.
     ⚠️ 통합 이름을 여기 박지 않는다. 도형 이름이 판정 단위(Z)에 없으면 그 이름을
     품은 판정 단위로 보낸다. 라벨은 묶음마다 한 번, 가장 큰 도형에만 단다 — 도형마다
     원래 이름을 그리면 판정 단위에 없는 '광주'·'전남'이 지도에 따로 남는다
     (2026-09-15 고객 점검). */
  function zoneOf(n){
    if(Z[n])return n;
    for(var k in Z){ if(k.indexOf(n)>=0)return k; }
    return n;
  }
  var labelAt={};
  SIDO_GEO.p.forEach(function(a){
    var k=zoneOf(a.n), b=labelAt[k];
    if(!b||a.d.length>b.d.length)labelAt[k]=a;
  });
  SIDO_GEO.p.forEach(function(a){
    var key=zoneOf(a.n);
    var z=Z[key]||{};
    /* 시세 모드(M)는 색·이름표·링크가 바뀐다 — 지역을 누르면 그 시도의 주간·월간 그래프(시세 탭, 2026-10-04 대표 요청).
       공급 모드는 시도 공급 리포트. 탭 표적·라벨은 모드와 무관하다. */
    var code=M?sidoCode(a.n):null;
    var lab=M?key+' — '+M.lead+' 매매 '+wkPct(M.v[key])+' · 누르면 '+M.adj+' 그래프'
      :key+' — '+(TB_GRADE[z.grade]||'')+' · '+(z.ctxt||('누적 '+tbSigned(z.tot||0)+'세대'));
    var small=SMALL[a.n]||key!==a.n;
    /* 한 판정 단위의 두 번째 도형(전남광주의 작은 쪽)은 같은 곳으로 가는 링크라 초점이 두 번 섰다(백로그 36-8) — 마우스·터치로는
       눌리게 두고 키보드 순서·읽기에서만 뺀다. */
    var dup=labelAt[key]!==a?' tabindex="-1" aria-hidden="true"':'';
    h+=(code?'<a href="#stats-market-'+M.k+'~'+code+'" data-code="'+code+'"'+dup+' aria-label="'+lab+'">'
      :'<a href="/zone/'+encodeURIComponent(key)+'/"'+dup+' aria-label="'+lab+'">')
      +'<path d="'+a.d+'" fill="'+(M?wkFill(M.v[key],M.ref):supplyFill(z))+'"></path>'
      +(SMALL[a.n]?'<polygon class="tap" points="'+tapShape(a)+'" fill="transparent"></polygon>':'')
      +(labelAt[key]===a?'<text x="'+a.x+'" y="'+a.y+'" class="'+(small?'ml-s':'ml')+'">'+key+'</text>':'')
      +'<title>'+lab+'</title></a>';
  });
  h+='</svg></div>';
  el.innerHTML=h;
  el.dataset.done='1';
  /* 시세 모드의 지역 → 그 시도 그래프(같은 주소를 다시 누를 때 포함). 상자는 그대로 두고 안만 갈아 끼우므로 한 번만 붙인다. */
  if(!el.dataset.trLink){ el.dataset.trLink='1'; el.addEventListener('click',function(e){ onTrendLink(e,'score_map'); }); }
}
/* 그래프 = 시간축. 분기 공급 막대 + 적정 기준선. 지도가 잃는 시간축을 이 모드가
   담당한다. 데이터는 표와 같은 tbBuild/tbAgg — 세 모드가 한 원장을 쓴다. */
var GR_REG='전국';
/* 시도 상세를 보고 돌아오면 그래프가 그 지역으로 열린다(2026-08-08 사용자).
   sessionStorage: 탭을 닫으면 사라지는 화면 상태라 영구 수집이 아니다. */
try{ GR_REG=sessionStorage.getItem('agong_gr')||'전국'; }catch(e){}
function grSet(r){
  GR_REG=r;
  try{ sessionStorage.setItem('agong_gr',r); }catch(e){}
  var el=document.getElementById('graph-wrap'); if(el) el.dataset.done='';
  renderSidoGraph();
}
function renderSidoGraph(){
  var el=document.getElementById('graph-wrap');
  if(!el) return;
  /* 좁음/넓음 판정이 done 캐시에 갇히면 모바일에서 그린 360 viewBox가
     데스크톱 전환 뒤에도 남는다(실측) — 렌더 때의 폭 버킷을 기록하고
     달라졌으면 다시 그린다. */
  if(!el.clientWidth) return;          // 숨은 상태 — 측정 불가
  var nb=(el.clientWidth<520)?'1':'0';
  if(el.dataset.done&&el.dataset.nw!==nb) el.dataset.done='';
  if(el.dataset.done) return;
  el.dataset.nw=nb;
  var B=tbBuild(); if(!B) return;
  var rows=tbAgg(B.rows,'q');
  var k=B.regs.indexOf(GR_REG); if(k<0){ GR_REG='전국'; k=0; }
  var ref=B.refs[GR_REG];
  /* 640×210 고정 비율은 327px 화면에서 높이 107px — 너무 작다(2026-08-08
     사용자). 좁으면 360×220으로 그린다(250은 세로가 과했다 — 아래 H). 회전·리사이즈는 아래 재렌더가 받는다. */
  if(!el.clientWidth) return;          // 숨은 상태 — 측정 불가, 보일 때 다시 온다
  var narrow=el.clientWidth<520;
  var W=narrow?360:640, H=narrow?220:210, PT=14,PB=22,PL=8,PR=10;  // 250은 세로가 과했다(사용자)
  var iw=W-PL-PR, ih=H-PT-PB;
  // ⚠️ 상한은 막대가 실제로 그리는 값(분기 환산)으로 잡는다 — 원시 그룹 합으로
  // 잡으면 덜 찬 분기(r.n<3)가 생기는 순간 환산 막대가 차트 위로 뚫린다(2026-08-10 리뷰).
  // 분기 환산의 정본 — 막대 높이·히트 렉트·상한이 전부 이걸 쓴다(복제 금지:
  // 한쪽만 고치면 툴팁 숫자와 막대 높이가 갈린다).
  var qv=function(r){ return Math.round(r.s[k]*3/r.n); };
  var mx=ref; rows.forEach(function(r){ var q=r.s[k]*3/r.n; if(q>mx) mx=q; });
  mx*=1.06;
  var bw=iw/rows.length;
  var h='<div class="gr-bar"><label class="gr-lab" for="gr-reg">지역</label>'
    +'<select id="gr-reg" onchange="grSet(this.value)">'
    +B.regs.map(function(r){ return '<option'+(r===GR_REG?' selected':'')+'>'+r+'</option>'; }).join('')
    +'</select><a class="gr-more" href="/zone/'+encodeURIComponent(GR_REG)+'/">'+GR_REG+' 상세 리포트 →</a></div>';
  h+='<div class="gr-box"><svg viewBox="0 0 '+W+' '+H+'" role="img" aria-label="'
    +GR_REG+' 분기별 아파트 공급과 적정물량">';
  var y0=PT+ih;
  /* y축 눈금 — 적정선 하나로는 막대의 절대 크기를 가늠할 기준이 없다
     (2026-08-08 사용자 승인). 보기 좋은 단위로 2~3줄, 적정선과 겹치면 생략. */
  var st=(function(x){ var p=Math.pow(10,Math.floor(Math.log(x)/Math.LN10));
    var u=x/p; return (u>=5?5:u>=2.5?2.5:u>=2?2:1)*p; })(mx/3);
  /* 라벨은 여기서 모으기만 한다 — 막대보다 먼저 찍으면 막대에 묻힌다
     (2026-08-08 사용자). 선은 뒤층, 라벨은 막대 뒤 위층 + 종이색 후광. */
  var yl='';
  for(var gv=st;gv<mx*0.97;gv+=st){
    if(Math.abs(gv-ref)/mx<0.05) continue;
    var gy=y0-ih*gv/mx;
    h+='<line x1="'+PL+'" y1="'+gy.toFixed(1)+'" x2="'+(PL+iw)+'" y2="'+gy.toFixed(1)+'" class="gr-gl"></line>';
    yl+='<text x="'+(PL+3)+'" y="'+(gy-3).toFixed(1)+'" class="gr-yt">'+tbNum(gv)+'</text>';
  }
  // 실적/추정 경계 — 막대보다 먼저 그려야 워시가 뒤로 깔린다
  var fi=-1; rows.some(function(r,i){ if(r.nf>0){ fi=i; return true; } return false; });
  if(fi>=0){
    var bx=PL+fi*bw;
    h+='<rect class="gr-futbg" x="'+bx.toFixed(1)+'" y="'+PT+'" width="'+(PL+iw-bx).toFixed(1)
      +'" height="'+ih+'"></rect>'
      +'<line x1="'+bx.toFixed(1)+'" y1="'+PT+'" x2="'+bx.toFixed(1)+'" y2="'+y0+'" class="gr-now"></line>';
  }
  rows.forEach(function(r,i){
    var v=qv(r);                               // 덜 찬 분기는 분기치로 환산
    var bh=Math.max(v>0?1:0,ih*v/mx);
    var x=PL+i*bw;
    /* 색 문법은 홈 표 그대로(2026-08-08 사용자): 과거 칸 = 그 분기의 매매가
       등락(±2% 만색), 미래 칸 = 적정 대비 부족. 높이는 공급량 — 표의 '숫자'가
       여기선 높이다. 가격 결측 분기는 회색(paper2). */
    var fill=r.nf>0?mapFill(ref?1-v/ref:null)
      :mapFill(r.m?r.m[k]:null,TB_PRICE_SCALE);
    h+='<rect x="'+(x+0.5).toFixed(1)+'" y="'+(y0-bh).toFixed(1)+'" width="'+(bw-1).toFixed(1)
      +'" height="'+bh.toFixed(1)+'" class="gb" fill="'+fill+'"></rect>';
  });
  // 적정 기준선 — 존 페이지 분기 차트의 파선과 같은 어휘
  var ry=y0-ih*ref/mx;
  h+=yl;   // y 라벨 — 막대 위층
  /* 라벨은 차트 '안쪽' 오른끝 — 여백에 두면 잘린다('적정 95,00' 실측). */
  h+='<line x1="'+PL+'" y1="'+ry.toFixed(1)+'" x2="'+(PL+iw)+'" y2="'+ry.toFixed(1)+'" class="gr-ref"></line>'
    +'<text x="'+(PL+iw-4)+'" y="'+(ry-5).toFixed(1)+'" class="gr-rt">적정 '+tbNum(ref)+'</text>';
  // x축 라벨 — 8분기마다
  rows.forEach(function(r,i){
    var last=i===rows.length-1;
    // 주기 라벨이 마지막 라벨과 4칸 이내로 붙으면 겹친다(29Q1/29Q2 실측) — 생략
    if(!last&&(i%8!==0||i>rows.length-5)) return;
    // 과거는 연도로(2017 · 2019 …), 미래는 분기 표기 유지(2026-08-08 사용자)
    var xl=r.nf>0?tbLabel(r.i,'q'):String(Math.floor(r.i/12));
    h+='<text x="'+(PL+i*bw+bw/2).toFixed(1)+'" y="'+(H-6)+'" class="gr-xt">'+xl+'</text>';
  });
  /* 탭 표적 — 막대는 화면에서 ~3px 폭이라 손가락으로 못 집는다(2026-08-08
     사용자: "눌렀을 때 숫자가 안 보임"). 분기 전체 높이를 덮는 투명 렉트가
     탭·호버·title을 받는다(존 시세 차트 .px-hit와 같은 패턴). 맨 위층. */
  rows.forEach(function(r,i){
    var v=qv(r);
    var pm=(r.nf===0&&r.m&&r.m[k]!=null)?tbPv(r.m[k]):null;
    h+='<rect class="gr-hit" x="'+(PL+i*bw).toFixed(1)+'" y="'+PT+'" width="'+bw.toFixed(1)
      +'" height="'+ih+'" fill="transparent" data-q="'+tbLabel(r.i,'q')
      +'" data-v="'+tbNum(v)+'"'
      +(pm?' data-p="'+pm+'"':'')+(r.nf>0?' data-f="1"':'')+'>'
      +'<title>'+tbLabel(r.i,'q')+' '+tbNum(v)+'세대'
      +(pm?' · 매매 '+pm:'')+(r.nf>0?' · 착공 기준 추정':'')
      +' (적정 '+tbNum(ref)+')</title></rect>';
  });
  h+='</svg><div class="gr-tip" hidden></div></div>'
    +'<p class="gr-note">색은 과거엔 매매가의 등락을, 미래엔 적정물량 대비 남고 모자람을 나타냅니다.</p>';
  el.innerHTML=h;
  el.dataset.done='1';
  grWireTip(el);
}
/* 막대 탭 → 값 표시. title은 데스크톱 호버 전용이라 모바일에서 개별 값을
   볼 수 없었다(2026-08-08 사용자 승인). 규칙은 존 페이지 툴팁에서 실기기로
   다진 그대로: click은 무조건 show, hover는 마우스 포인터일 때만(터치의 합성
   mouseenter 상쇄 함정), 닫기는 바깥 pointerdown(iOS는 비인터랙티브 탭으로
   document click이 안 온다). 문서 레벨 리스너는 한 번만 단다. */
function grWireTip(el){
  var tip=el.querySelector('.gr-tip'),svg=el.querySelector('svg'),box=el.querySelector('.gr-box');
  if(!tip||!svg) return;
  function hide(){ tip.hidden=true; }
  function show(rc){
    tip.innerHTML=rc.getAttribute('data-q')+' <b>'+rc.getAttribute('data-v')+'</b>세대'
      +(rc.getAttribute('data-p')?' <span>· 매매 '+rc.getAttribute('data-p')+'</span>':'')
      +(rc.getAttribute('data-f')?' <span>· 추정</span>':'');
    tip.hidden=false;
    var br=rc.getBoundingClientRect(),wr=box.getBoundingClientRect();
    tip.style.left='0px'; tip.style.top='0px';
    var tw=tip.offsetWidth;
    var x=br.left-wr.left+br.width/2, y=Math.max(br.top-wr.top,14)-6;
    x=Math.max(tw/2+2,Math.min(x,wr.width-tw/2-2));
    tip.style.left=x+'px'; tip.style.top=y+'px';
  }
  svg.addEventListener('click',function(e){
    var rc=e.target.closest&&e.target.closest('rect.gr-hit'); if(!rc)return;
    e.stopPropagation(); show(rc);
  });
  svg.addEventListener('pointerover',function(e){
    if(e.pointerType&&e.pointerType!=='mouse')return;
    var rc=e.target.closest&&e.target.closest('rect.gr-hit'); if(rc)show(rc);
  });
  svg.addEventListener('mouseleave',hide);
  if(!grWireTip.doc){
    grWireTip.doc=1;
    // 회전·창 크기 변경 → 좁음/넓음 판정이 바뀌면 다시 그린다(그래프 표시 중일 때만)
    var rt2;
    window.addEventListener('resize',function(){
      clearTimeout(rt2);
      rt2=setTimeout(function(){
        var w=document.getElementById('graph-wrap');
        if(!w||!w.dataset.done||TB_VIEW!=='graph') return;
        /* ⚠️ 숨은 상태(다른 뷰로 이동)에선 clientWidth가 0이라 측정 자체가 무효 —
           그대로 재렌더하면 데스크톱에 모바일용 360 그래프가 굳는다(2026-08-10 리뷰).
           그리고 버킷이 실제로 바뀌었을 때만 다시 그린다 — 5px 드래그마다
           전체 재빌드하지 않게. */
        if(!w.clientWidth) return;
        var nb=(w.clientWidth<520)?'1':'0';
        if(w.dataset.nw!==nb){ w.dataset.done=''; renderSidoGraph(); }
      },250);
    });
    var out=function(e){
      var w=document.getElementById('graph-wrap');
      if(w&&!w.contains(e.target)){ var t=w.querySelector('.gr-tip'); if(t)t.hidden=true; }
    };
    document.addEventListener('pointerdown',out);
    document.addEventListener('click',out);
  }
}
function renderHeroMap(){
  const el=document.getElementById('hero-map');
  if(!el||typeof NATION_TILE==='undefined'||typeof mapColor!=='function')return;
  let S;try{S=ADV.weekly&&ADV.weekly.sgg;}catch(e){return;}   // data-core 가 안 오면 ADV 가 없다 — 부팅(라우팅)을 끊지 않는다(전수리뷰 #43)
  if(!S||!S.rows||!S.rows.length)return;
  const row=S.rows[S.rows.length-1], v={};
  (S.codes||[]).forEach((c,i)=>{v[c]=row.ma[i];});
  const N=NATION_TILE, T=10, G=1.6;
  const w=N.cols*(T+G)-G, h=N.rows*(T+G)-G;
  const p=['<svg viewBox="0 0 '+w+' '+h+'" width="100%" height="100%" preserveAspectRatio="xMidYMid slice" role="presentation" focusable="false">'];
  N.t.forEach(a=>{
    p.push('<rect x="'+(a[2]*(T+G)).toFixed(1)+'" y="'+(a[3]*(T+G)).toFixed(1)+'" width="'+T+'" height="'+T+'" rx="2.2" fill="'+mapColor(v[a[0]],WK_MAP_REF)+'"/>');   // 통계 탭 시군구 주간 지도·홈 지도 주간 모드와 같은 기준
  });
  p.push('</svg>');
  el.innerHTML=p.join('');
}

/* 모든 선언(QUIZSETS·curSet 등) 이후에 초기 라우팅 실행 — TDZ 방지.
   ⚠️ DOMContentLoaded까지 미루는 이유: applyHash()가 #stats로 들어오면 그 자리에서
   차트를 만드는데, Chart.js가 defer라 파싱 시점엔 아직 없다. defer 스크립트는
   DOMContentLoaded 직전에 실행이 보장되므로 이 훅이 정확한 경계다. */
function renderWeeklyGrid(){
  const box=document.getElementById('home-weekly-grid');
  if(!box)return;
  let S,row;
  try{S=ADV.weekly&&ADV.weekly.sgg;row=S&&S.rows&&S.rows[S.rows.length-1];}catch(e){}
  if(!S||!S.codes||!row||!row.ma){box.style.display='none';return;}
  /* 주간 구역 = 전국 시군구 지도(매매 전주 대비). 예전엔 시도 20칸 격자(집계 3 + 16시도, 방향 표지)였는데 2026-10-02 대표
     요청으로 시도 칸을 모두 걷고 통계 탭과 같은 시군구 지도(sggMapSvg)를 그 자리에 둔다 — 시도 값은 지도의 진한 머리 칸
     (서울·경기 …)이 말한다. 칸(이름·값)을 누르면 그 지역 주간 그래프(통계 시장동향, openTrendRegion). 전세 줄은 싣지 않는다
     (2026-09-28 대표 결정 — 홈 주간 구역은 매매만). 색·값은 통계 지도와 같은 mapColor(…, WK_MAP_REF)·pv2 다.
     요약·공유 주소인 /weekly/ 로 가는 길은 머리줄 오른쪽 링크다(home_cta 의 to 값 weekly_grid 는 GA 값이라 그대로 둔다). */
  const v={}; S.codes.forEach((c,i)=>{v[c]=row.ma[i];});
  const svg=sggMapSvg([v],{ref:WK_MAP_REF,names:['매매'],href:c=>'#stats-market-week~'+c});
  /* 격자 머리 한 줄(B7·RET-5): 지난 방문 이후 새 발표 수(이 기기에만 저장 — 재방문에만 보인다). */
  const rel=weeklyReleaseNow(), since=wkSinceText(wkSeen(),rel);
  if(rel&&wkShouldRemember(wkSeen(),rel.pub))wkRemember(rel.pub);
  const lines=since?'<p class="wg-since">'+since+'</p>':'';
  const sh=weeklyShare(ADV.weekly);
  /* 공유 버튼(B8·VIRAL-1) — 내용은 /weekly/ 공유 버튼과 같은 함수가 구운 ADV.weekly.share. */
  const share=sh?'<div class="wg-share"><button type="button" class="wg-sh wg-sh-k" onclick="shareWeekly(\'kakao\')">'
    +'<svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true"><path fill="currentColor" d="M12 3C6.48 3 2 6.54 2 10.9c0 2.8 1.86 5.26 4.66 6.66-.15.52-.97 3.36-1 3.58 0 0-.02.17.09.24.11.07.24.02.24.02.32-.04 3.66-2.4 4.24-2.81.57.08 1.16.13 1.77.13 5.52 0 10-3.54 10-7.9S17.52 3 12 3z"/></svg>카카오톡 공유</button>'
    +'<button type="button" class="wg-sh" onclick="shareWeekly(\'link\')">'
    +'<svg viewBox="0 0 24 24" width="17" height="17" aria-hidden="true"><path fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" d="M4 12v7a1 1 0 0 0 1 1h14a1 1 0 0 0 1-1v-7M12 3v13M8 7l4-4 4 4"/></svg>링크 공유</button></div>':'';
  /* 머리 = 무엇을 칠했나(· 발표일) + 범례. 발표일을 말하던 첫 화면 띠를 2026-10-05 대표 요청으로 빼서 여기 머리말에 붙인다(wkPubLead).
     늦은 주에는 h2 가 이미 '9/17 발표 기준 · …'로 시작하므로 되풀이하지 않는다. */
  box.innerHTML=lines
    +'<div class="wg-head"><span class="wg-when">매매 전주 대비(%)'+(rel&&!rel.stale?' · '+wkPubLead(rel):'')+'</span>'
    +'<span class="tb-key wg-key"><span class="tk"><i class="tk-d"></i>하락</span>'
    +'<span class="tk-ramp" aria-hidden="true"></span>'
    +'<span class="tk"><i class="tk-u"></i>상승</span></span></div>'
    +'<div class="map-scroll wg-map">'+svg+'</div>'
    +'<div class="wg-foot"><span>지역을 누르면 주간 그래프<span class="wg-swipe"> · 옆으로 밀어 전체 보기</span></span>'
    /* home_cta 의 to 값: 홈에서 /weekly/ 로 가는 입구를 가른다(격자·푸터) — 홈 마케팅 검수 A3·IA-7. */
    +'<a class="wg-link" href="/weekly/" onclick="track(\'home_cta\',{to:\'weekly_grid\'})">이번 주 요약 보기 →</a></div>'
    +share;
  /* 지도 칸 → 그 지역 주간 그래프. 상자는 그대로 두고 안만 갈아 끼우므로 한 번만 붙인다. */
  if(!box.dataset.trLink){ box.dataset.trLink='1'; box.addEventListener('click',e=>onTrendLink(e,'home_map')); }
  /* 카카오 SDK 는 누르려는 순간 받기 시작한다(퀴즈 결과 화면의 선로딩과 같은 뜻 — 첫 로딩에는 받지 않는다). */
  const kb=box.querySelector('.wg-sh-k');
  if(kb)['pointerenter','touchstart','focus'].forEach(t=>kb.addEventListener(t,()=>{loadKakao().catch(()=>{});},{once:true,passive:true}));
  /* 구역 머리줄 = 조사일·발표일·다음 발표(홈 마케팅 검수 A2). 예전엔 '매주 갱신' 고정 문구라 09-24~26 배치가
     멈춘 동안 9일 묵은 값을 그 아래 보였다. 발표가 늦은 주에는 스스로 '반영 대기'라 적고, 제목도 '이번 주'를
     약속하지 않는다. 판정은 통계 탭 rel-week 와 같은 weeklyRelease 하나다. */
  applyWeeklyStatus(weeklyReleaseNow(),weeklyHead(ADV.weekly));
}
/* 주간 구역 h2 에 발표 상태를 적는다(구역 머리줄은 2026-10-03 대표 요청으로 뺐다). 따로 떼어 둔 것은 시험이 직접 돌려 보게 하려는 것이다
   (test_weekly_release·test_home_first_screen).
   h2 = 이번 주 결론 한 줄(hd.text — /weekly/ 제목과 같은 문장, IA-4). 예전엔 매주 같은 질문
   ('이번 주, 어디가 오르고 내렸을까?')이라 지난주 화면과 구별되지 않았다. 늦은 주에는 결론 앞에 발표일을 붙여
   '이번 주' 값처럼 보이지 않게 한다(TRUST-1②, 1차의 '반영 대기' 처리와 같은 조건 r.stale). 결론이 없는 옛 캐시는
   1차 동작 그대로 — 늦은 주에만 질문 앞에 발표일. */
function applyWeeklyStatus(r,hd){
  if(!r)return;
  const h2=document.getElementById('wk-h2');
  if(!h2)return;
  if(hd)h2.textContent=(r.stale?wkPubLead(r)+' · ':'')+hd.text;
  else if(r.stale)h2.textContent=_md(r.pub)+' 발표, 어디가 오르고 내렸을까?';
}
/* 이번 주 결론 한 줄(ADV.weekly.head, 홈 마케팅 검수 B1·IA-4). /weekly/ 제목과 같은 함수(make_weekly_page.conclusion)가
   split_data 에서 구운 문장이다 — 홈은 읽기만 한다. 최신 행과 조사일이 같을 때만 쓴다(옛 캐시·섞인 판이면 null). */
function weeklyHead(W){
  const hd=W&&W.head, row=W&&W.rows&&W.rows[W.rows.length-1];
  return (hd&&hd.text&&row&&hd.p===row.p)?hd:null;
}
/* 공유 내용(ADV.weekly.share, B8). 배치가 파이썬 정본(make_weekly_page.share_payload)으로 구워 싣고 홈은 읽기만 한다.
   최신 행과 조사일이 같을 때만 쓴다(옛 캐시·섞인 판이면 null — 버튼 없이 그린다). */
function weeklyShare(W){
  const s=W&&W.share, row=W&&W.rows&&W.rows[W.rows.length-1];
  return (s&&s.url&&row&&s.p===row.p)?s:null;
}
/* 지난 방문 이후 새 발표(RET-5). 마지막으로 본 발표일을 이 기기에만 둔다(개인정보처리방침 '브라우저에만 저장').
   seen: 지난번에 본 발표일(YYYY-MM-DD), r: weeklyRelease. 새 발표가 없거나 처음 온 기기면 null. 발표는 매주 한 번이라
   두 발표일의 주 차이가 곧 새 발표 수다. */
const WK_SEEN_KEY='wk_seen';
function wkSinceText(seen,r){
  if(!r||!seen||!/^\d{4}-\d{2}-\d{2}$/.test(seen)||!(seen<r.pub))return null;
  const n=Math.round((_dn(r.pub)-_dn(seen))/7);
  return n>=1?'지난 방문('+_md(seen)+' 발표) 이후 새 발표 '+n+'회':null;
}
/* 더 새 발표일만 적는다 — 서비스워커·브라우저 캐시의 옛 data-core 로 그린 화면이 이미 본 새 발표일을 옛 날짜로 덮으면
   다음 방문에 '새 발표'를 한 번 더 센다(3차 검토). */
function wkShouldRemember(seen,pub){return !!pub&&(!seen||!/^\d{4}-\d{2}-\d{2}$/.test(seen)||seen<pub);}
function wkSeen(){try{return localStorage.getItem(WK_SEEN_KEY);}catch(e){return null;}}
function wkRemember(pub){try{localStorage.setItem(WK_SEEN_KEY,pub);}catch(e){}}
/* 주간 시세 공유(B8·VIRAL-1). 카카오는 퀴즈와 같은 지연 로딩(needKakao) — 못 받으면 OS 공유 → 링크 복사.
   링크의 utm_campaign=week_YYYYMMDD 가 주마다 주소를 바꿔 카카오의 페이지 단위 미리보기 보관을 피한다(VIRAL-2). */
function shareWeekly(m){
  let d=null;try{d=weeklyShare(ADV.weekly);}catch(e){}
  if(!d)return;
  if(m==='kakao'){
    if(needKakao(()=>shareWeekly(m)))return;
    if(kakaoReady()){
      try{Kakao.Share.sendDefault({objectType:'feed',
        content:{title:d.title,description:d.text,imageUrl:d.img,imageWidth:d.w,imageHeight:d.h,
          link:{mobileWebUrl:d.url,webUrl:d.url}},
        buttons:[{title:d.btn,link:{mobileWebUrl:d.url,webUrl:d.url}}]});
        track('share',{content_type:'weekly',method:'kakao'});return;}
      catch(e){}
    }
  }
  track('share',{content_type:'weekly',method:navigator.share?'os_share':'copy'});
  const txt=d.title+'\n'+d.url;
  if(navigator.share){
    navigator.share({title:d.title,text:d.text,url:d.url}).catch(e=>{if(e&&e.name!=='AbortError')copyText(txt);});
  }else{copyText(txt);}
}
/* 주간 구역의 해설 글 카드(홈 마케팅 검수 B5·RET-4, 2026-09-27 → 2026-10-03 카드로). 말(meta·head)은 배치가 blog_feed.pick 으로
   골라 data-core 의 ADV.blog 로 구운 것이다 — /weekly/ 하단과 같은 글·같은 말. 여기서 날짜를 다시 셈하지 않는다. 글이 없거나
   (RSS 를 못 읽었거나 오래됨) 옛 캐시면 칸은 숨은 채로 남는다. 제목은 RSS 에서 온 글자라 textContent 로만 넣고, 주소는 네이버
   블로그 주소만 받는다. 이웃 안내 줄은 홈(2026-09-28)·/weekly/(2026-10-03) 모두 뺐다. */
/* 카드 = 작은 머리줄(meta '지난주 해설 · 네이버 블로그 9/27') + 굵은 결론(head — 제목의 '|' 뒤, blog_feed.headline). 매주 같은
   제목 앞부분('[한국부동산원] 주간 아파트가격 동향(…)')과 밑줄 긴 세 줄을 걷었다(2026-10-03 대표 요청). 카드 전체가 링크다. */
function blogLine(B){
  if(!B||!B.url||!B.head||!B.meta||!/^https:\/\/blog\.naver\.com\//.test(B.url))return null;
  return {href:B.url,meta:B.meta,head:B.head};
}
function renderBlogLine(){
  const el=document.getElementById('wk-blog');
  let L;try{L=blogLine(ADV.blog);}catch(e){return;}
  if(!el||!L)return;
  const a=document.createElement('a'), m=document.createElement('span'), h=document.createElement('span');
  a.href=L.href;a.target='_blank';a.rel='noopener';a.className='blog-card';
  m.className='bc-meta';m.textContent=L.meta;h.className='bc-head';h.textContent=L.head+' →';
  a.appendChild(m);a.appendChild(h);
  a.addEventListener('click',()=>track('home_cta',{to:'blog_weekly'}));
  el.textContent='';el.appendChild(a);
  el.hidden=false;
}
/* 퀴즈 카드의 '결과 예시' — 실제 결과 화면(.rcard)과 같은 마크업을 축소해 쓴다.
   티어 문구는 BLV 정본에서 읽는다. 가짜 데이터로 오해되지 않게 라벨을 붙인다.
   예시 점수 3 = 🐥 솜털 병아리. 8(🏘️ 다주택자)로 걸었다가 사용자가 "병아리가
   더 귀엽다"고 해서 낮췄다(2026-08-17). 만점을 걸면 "쉽겠네"가 되고, 부린이
   테스트의 얼굴은 도달점보다 출발점 쪽이 맞다 — 상위 티어는 풀어야 보인다. */
const SAMPLE_SCORE=3, SAMPLE_TOTAL=10;
function quizSample(){
  const box=document.getElementById('quiz-sample');
  /* ⚠️ window.BLV로 보면 안 된다 — 최상위 const는 window에 안 걸린다(2026-08-17
     실측: windowBLV=undefined, BLV는 len=11). 이름 그대로 참조한다. */
  if(!box||typeof BLV==='undefined'||!BLV[SAMPLE_SCORE])return;
  const g=BLV[SAMPLE_SCORE];
  let dots='';
  for(let i=0;i<SAMPLE_TOTAL;i++)dots+='<i class="'+(i<SAMPLE_SCORE?'ok':'no')+'"></i>';
  box.innerHTML='<div class="qs-label">결과 예시</div>'
    +'<div class="rcard rc-sample">'
    +'<div class="rc-head">부린이 테스트</div>'
    +'<div class="rc-emoji">'+g.emoji+'</div>'
    +'<div class="rc-score">'+SAMPLE_SCORE+'<small>/'+SAMPLE_TOTAL+'</small></div>'
    +'<div class="rc-dots">'+dots+'</div>'
    +'<div><span class="rc-lv">'+g.lv+'</span></div>'
    +'<div class="rc-grade">'+g.g+'</div>'
    +'<div class="rc-desc">'+g.d+'</div>'
    +'</div>';
}
// <home-small> ── 이 구간은 test_home_small 이 통째로 node 에 올려 돌린다(DOM·저장소·gtag 는 흉내).
/* ===== 홈 작은 장치(홈 마케팅 검수 3차 묶음 S, 2026-09-27) — 내 지역(C5)·출처 구간(B9)·측정(B10)·설치 안내(C10①) =====
   네 장치 모두 순수 함수(시험이 node 로 돌린다)와 DOM 을 만지는 얇은 함수로 나눴다. 시험: tools/tests/test_home_small.py. */

/* 기기 저장소. 사생활 모드·차단된 사이트 데이터에서는 접근만 해도 던진다 — 모든 장치가 이 셋만 거쳐 조용히 빠진다.
   lsSet 의 v 가 null 이면 지운다. 성공 여부를 돌려준다(저장 못 하면 '한 번만'·'고정'을 약속할 수 없어 장치를 열지 않는다). */
function lsGet(k){try{return localStorage.getItem(k);}catch(e){return null;}}
function lsSet(k,v){try{if(v==null)localStorage.removeItem(k);else localStorage.setItem(k,String(v));return true;}catch(e){return false;}}
function lsOk(){try{localStorage.setItem('agongmap-ls','1');localStorage.removeItem('agongmap-ls');return true;}catch(e){return false;}}

/* ── 측정(B10·MEAS-3) ──────────────────────────────────────────────────────────────────────────────
   ① home_variant 사용자 속성 — 첫 화면을 바꾼 배포를 GA 에서 가르는 값. 홈 첫 화면 구성을 바꾸는 배포에서만 이 한 상수를
      올린다(HOME_BUILD 는 모든 배포에서 오르므로 쓰지 않는다). 동시 A/B 는 하지 않는다 — 배포 전후 비교의 구분값이다.
      이 줄은 부팅(showView 의 첫 page_view)보다 먼저 돈다 — 큐(dataLayer)에서 'set' 이 이벤트 앞에 있어야 속성이 붙는다.
      GA 로더는 늦게 붙어도(C8) 큐를 순서대로 보낸다. */
const HOME_VARIANT='home7';   // home7: 데스크톱 전체 개편 — 전 페이지 상단 내비·이름표(desk.css, 2026-10-06). home6: 첫 화면 '내 지역'·'이번 주' 띠 삭제(2026-10-05)
try{if(typeof gtag==='function')gtag('set','user_properties',{home_variant:HOME_VARIANT});}catch(e){}
/* ② 코호트 재방문 신호 — 기기에 '방문한 날 수(n)·첫 방문일(f)·마지막 방문일(l)'만 센다(KST 날짜 수, 개인 식별 정보 없음, 밖으로
      나가는 것은 GA 이벤트 매개변수뿐). 그날 첫 홈 부팅에 home_visit 을 한 번 보낸다: visit_n(방문한 날 수), gap_days(직전 방문과의
      날 차), first_week(첫 방문 주의 월요일 — 코호트 열쇠). 주 재방문율 = first_week 별로 visit_n ≥ 2 인 기기의 비율.
      저장 못 하는 기기는 세지 않는다(매번 '첫 방문'으로 부풀지 않게). 설치 안내의 '두 번째 방문'도 이 값 하나를 쓴다. */
const VISIT_KEY='agongmap-visit';
function visitNext(prev,day){
  const ok=prev&&typeof prev==='object'&&Number.isInteger(prev.n)&&prev.n>=1&&Number.isInteger(prev.f)&&Number.isInteger(prev.l);
  if(!ok)return {n:1,f:day,l:day,gap:0,fresh:true};
  if(day<=prev.l)return {n:prev.n,f:prev.f,l:prev.l,gap:0,fresh:false};   // 같은 날(기기 시계가 거꾸로 가도 세지 않는다)
  return {n:prev.n+1,f:prev.f,l:day,gap:day-prev.l,fresh:true};
}
function weekOf(day){return _iso(day-(_wd(day)+6)%7);}   // 그 날이 든 주의 월요일(ISO 날짜)
let VISIT=null;
function countVisit(){
  let prev=null;
  const raw=lsGet(VISIT_KEY);
  if(raw){try{prev=JSON.parse(raw);}catch(e){}}
  const v=visitNext(prev,_kst(new Date()).day);
  if(v.fresh){
    if(!lsSet(VISIT_KEY,JSON.stringify({n:v.n,f:v.f,l:v.l})))return null;
    track('home_visit',{visit_n:v.n,gap_days:v.gap,first_week:weekOf(v.f)});
  }
  return v;
}
/* ③ 구역 노출 section_view — 주간 구역(격자)이 화면에 들어오면 한 번(페이지당). 클릭(home_cta)을 이 분모로 나눠 클릭률을 낸다.
      IntersectionObserver 가 아니라 스크롤 위치 계산이다 — 그리지 않는 창에서 IO 콜백이 영영 오지 않은 사고가 있었다(afterLayout
      주석). 판정: 보이는 높이가 (요소 높이와 화면 높이 중 작은 쪽)의 절반 이상. 숨은 뷰(통계·퀴즈)의 요소는 높이 0 이라 안 본 것이다. */
function inView(top,bottom,vh){
  const h=bottom-top;
  if(!(h>0)||!(vh>0))return false;
  return Math.min(bottom,vh)-Math.max(top,0)>=Math.min(h,vh)/2;
}
const SEEN={};
const SECTIONS=[['week',()=>{const g=document.getElementById('home-weekly-grid');
  return (g&&g.style.display!=='none')?g:document.getElementById('wk-h2');}]];   // 격자가 빠진 옛 캐시는 제목으로
let _secT=0;
function checkSections(){
  _secT=0;
  let left=0;
  SECTIONS.forEach(([name,get])=>{
    if(SEEN[name])return;
    const el=get(), r=el&&el.getBoundingClientRect();
    if(r&&inView(r.top,r.bottom,window.innerHeight||document.documentElement.clientHeight)){
      SEEN[name]=true;
      track('section_view',{section:name});
      if(name==='week')installMaybe();
    }else left++;
  });
  if(!left)['scroll','resize','popstate'].forEach(ev=>window.removeEventListener(ev,onSecMove));
}
function onSecMove(){if(!_secT)_secT=setTimeout(checkSections,150);}
function watchSections(){
  ['scroll','resize','popstate'].forEach(ev=>window.addEventListener(ev,onSecMove,{passive:true}));
  document.querySelectorAll('.nav-btn').forEach(b=>b.addEventListener('click',onSecMove));   // 통계 → 홈 탭(스크롤 없이 돌아온 경우)
  setTimeout(checkSections,0);   // 첫 배치가 잡힌 뒤(afterLayout 과 같은 이유로 rAF 가 아니라 타이머)
}

/* ── 설치 안내(C10①·PWA-1) ────────────────────────────────────────────────────────────────────────
   안드로이드는 beforeinstallprompt 를 받아 두었다가, 두 번째 방문(VISIT.n ≥ 2)이거나 주간 구역을 본 뒤(SEEN.week) 한 번만
   "매주 시세를 홈 화면에서 바로 보기" 안내를 띄운다. iOS 는 그 이벤트가 없어 '공유 → 홈 화면에 추가' 문구로 대신한다(인앱 브라우저는
   홈 화면 추가가 없어 뺀다). 띄운 순간 기기에 적어 다시 띄우지 않는다(닫아도, 무시해도). 이미 설치해 앱으로 연 경우(index.html 머리의
   html.pwa — standalone)와 저장소를 못 쓰는 기기는 띄우지 않는다. 첫 화면을 가리지 않게 부팅 뒤 INSTALL_DELAY 가 지나야 뜬다.
   측정: pwa_prompt{step: shown·accept·dismiss·close, platform}, 설치 완료는 appinstalled → pwa_installed{platform}. */
const INSTALL_KEY='agongmap-install', INSTALL_DELAY=3000;
const INSTALL_TEXT='매주 시세를 홈 화면에서 바로 보기';
const INAPP=/KAKAOTALK|NAVER\(inapp|Instagram|FBAN|FBAV|Line\/|DaumApps|everytimeApp|BAND\//i;
function installPlatform(ua,touch){
  if(/Android/i.test(ua))return 'android';
  if(/iPhone|iPad|iPod/.test(ua)||(/Macintosh/.test(ua)&&touch>1))return 'ios';
  return null;
}
/* o: {standalone, storageOk, stored, platform, inapp, hasPrompt, visitN, weekSeen} → 'android' | 'ios' | null */
function installPlan(o){
  if(o.standalone||!o.storageOk||o.stored||!o.platform)return null;
  if(!(o.visitN>=2||o.weekSeen))return null;
  if(o.platform==='android')return o.hasPrompt?'android':null;
  return o.inapp?null:'ios';
}
let _bip=null, _instReady=false;
function _installState(){
  const ua=navigator.userAgent||'';
  return {standalone:document.documentElement.classList.contains('pwa'),storageOk:lsOk(),stored:lsGet(INSTALL_KEY)!=null,
    platform:installPlatform(ua,navigator.maxTouchPoints||0),inapp:INAPP.test(ua),hasPrompt:!!_bip,
    visitN:VISIT?VISIT.n:0,weekSeen:!!SEEN.week};
}
function installMaybe(){
  if(!_instReady||curView!=='home'||document.getElementById('inst'))return;
  const plan=installPlan(_installState());
  if(!plan||!lsSet(INSTALL_KEY,'shown'))return;
  const box=document.createElement('div');
  box.id='inst'; box.className='inst'; box.setAttribute('role','region'); box.setAttribute('aria-label','홈 화면에 추가 안내');
  box.innerHTML='<p class="inst-t">'+INSTALL_TEXT+'</p>'
    +(plan==='ios'?'<p class="inst-d">브라우저의 <b>공유</b> 버튼 → <b>홈 화면에 추가</b></p>'
      :'<button type="button" class="inst-go">홈 화면에 추가</button>')
    +'<button type="button" class="inst-x">닫기</button>';
  box.querySelector('.inst-x').addEventListener('click',()=>{
    lsSet(INSTALL_KEY,'closed'); box.remove(); track('pwa_prompt',{step:'close',platform:plan});
  });
  const go=box.querySelector('.inst-go');
  if(go)go.addEventListener('click',()=>{
    const e=_bip; _bip=null; box.remove();
    if(!e)return;
    e.prompt();
    e.userChoice.then(c=>track('pwa_prompt',{step:c&&c.outcome==='accepted'?'accept':'dismiss',platform:plan})).catch(()=>{});
  });
  document.body.appendChild(box);
  track('pwa_prompt',{step:'shown',platform:plan});
}
window.addEventListener('beforeinstallprompt',e=>{
  const s=_installState();
  if(s.platform!=='android'||s.standalone||s.stored||!s.storageOk)return;   // 안 띄울 기기는 브라우저 기본 동작 그대로
  e.preventDefault(); _bip=e; installMaybe();
});
window.addEventListener('appinstalled',()=>{
  lsSet(INSTALL_KEY,'installed');
  const b=document.getElementById('inst'); if(b)b.remove();
  track('pwa_installed',{platform:installPlatform(navigator.userAgent||'',navigator.maxTouchPoints||0)||'other'});
});

/* 내 지역(C5·RET-6)·첫 화면 '이번 주' 띠(B1)는 2026-10-05 대표 요청으로 뺐다(첫 화면 위쪽을 너무 차지한다). 고정해 둔 기기의
   옛 저장값은 부팅이 지운다(dropOldMyZone) — 더는 쓰지 않는 값을 브라우저에 남기지 않는다. */
const OLD_MYZ_KEY='agongmap-myzone';
function dropOldMyZone(){if(lsGet(OLD_MYZ_KEY)!=null)lsSet(OLD_MYZ_KEY,null);}

/* ── 출처·구간 한 줄(B9·TRUST-5) ─────────────────────────────────────────────────────────────────────
   '3년'의 구간 = 판정 기준 분기 L 다음 분기부터 H 분기(sido_zones.calc 의 미래 창 range(L+1, L+H+1)). 손으로 적지 않는다. */
function qShift(key,k){
  const m=/^(\d{4})Q([1-4])$/.exec(key||'');
  if(!m)return null;
  const i=(+m[1])*4+(+m[2])-1+k;
  return Math.floor(i/4)+'년 '+(i%4+1)+'분기';
}
function supplySpan(S){
  if(!S||!(S.H>0))return null;
  const a=qShift(S.L,1), b=qShift(S.L,S.H);
  return (a&&b)?'앞으로 '+(S.H/4)+'년('+a+'~'+b+')':null;
}
function renderSupplySpan(){
  let S=null;try{S=ADV.sido;}catch(e){}
  const el=document.getElementById('map-span'), t=supplySpan(S);
  if(el&&t)el.textContent=t;
}
// </home-small>

function boot(){
  if(BUILD_RELOAD)return;   // 판이 달라 새로고침하는 중 — 옛 스크립트로 새 마크업을 그리지 않는다(맨 위 판 표식)
  /* chartSetup 은 차트 라이브러리를 받은 뒤 loadChart 가 부른다 */
  renderWeeklyGrid();
  quizSample();
  renderHeroMap();    // 히어로 배경 = 이번 주 전국 시군구 지도
  renderBlogLine();   // 주간 구역 아래 이번 주 해석 글 한 줄(B5)
  renderSupplySpan(); // 지도 아래 '앞으로 3년(…~…)' 구간(B9)
  dropOldMyZone();    // 뺀 '내 지역'의 옛 저장값 정리
  /* ⚠️ 표(분기 1,000칸 HTML 조립)는 여기서 굽지 않는다. 기본 모드가 지도인데
     숨은 표를 먼저 구우면 그 비용(월 모드 실측 200ms+)이 기본 화면 페인트를 막고,
     숨은 상태의 tbAnchor 재시도 타이머 6발이 전부 헛돈다(2026-08-10 리뷰).
     tbView('table')이 처음 열 때 굽는다 — 지도 폴백(tbView('table'))도 같은 경로. */
renderAggCards();   // 판정 카드 셋 — 모드 버튼 아래·지도/그래프/표 버튼 위(보기와 무관하게 늘 보인다)
markFresh();        // 모드 단추 N 배지 — renderAggCards 가 못 쓰는 시세 단추를 잠근 뒤에(잠긴 단추엔 달지 않는다)
renderSidoMap();    // 기본 모드 — 보이는 것부터
  /* 대결 링크(?c=&s=, 퀴즈 랜딩이 넘겨준다)는 퀴즈 화면을 먼저 띄우고 해석·시작은 home-quiz.js 의 bootChallenge 가
     한다(B11 — 점수 상한 QUIZ_LEN 이 그 파일에 있다). 모양만 보는 chalInURL 은 랜딩의 넘김 조건과 같다. */
  if(chalInURL(location.search)&&chalBootable()){
    /* page_view 는 bootChallenge 가 대결을 확정한 뒤(또는 applyHash 가) 한 번 보낸다(#46). 그 사이 머리 스크립트의 idle
       폴백(index.html, dataLayer 에 page_view 가 없으면 보냄)이 먼저 돌면 두 건이 됐다 — 폴백에 미룬다고 알린다(통합 검토). */
    window.__pvDefer=true;
    PV_AFTER=()=>{VISIT=countVisit();};
    showView('test',false,true);
    bootChallenge();
  }else{
    applyHash();
  }
  if(!PV_AFTER)VISIT=countVisit();   // 그날 첫 홈 부팅에 home_visit 한 번(B10) — 부팅 page_view(applyHash·showView) 뒤
  watchSections();      // 주간 구역 노출 section_view(B10)
  setTimeout(()=>{_instReady=true;installMaybe();},INSTALL_DELAY);   // 설치 안내(C10①)는 첫 화면이 자리 잡은 뒤에만
}
if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot);
else boot();

/* PWA: 서비스워커 등록 */
if('serviceWorker' in navigator){
  window.addEventListener('load',()=>{
    navigator.serviceWorker.register('/sw.js').catch(()=>{});
  });
}
