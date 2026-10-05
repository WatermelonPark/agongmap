/* 아공맵 홈 — 통계(시세·통계) 화면 코드. 홈 마케팅 검수 B11·MOB-8(2026-09-27)에 home-app.js 에서 떼어 냈다.
   대시보드(기본통계)·주간/월간 그래프와 시군구 지도·투자지표(입주물량·인허가)·버블밴드와 그 데이터 로더(시군구 전체 시계열).
   지도 첫 화면은 이 코드를 쓰지 않으므로 통계 화면을 열 때 home-app.js 의 loadPart('stats')가 '/home-stats.js?v=<HOME_BUILD>'
   로 받는다. 그래프 데이터(data-trend.json)와 이 파일이 둘 다 온 뒤에 대기열의 입구(PARTS.stats.api)가 부른 순서대로 돈다
   — 여기의 최상위 function 선언이 전역의 대기 함수를 덮어쓴다. 입구 함수를 없애거나 이름을 바꾸면 PARTS 도 같이 고친다
   (test_home_parts). 통계 해시(statsMode·statsNav·statsHashOf)와 발표 일정(<wk-release>)·지도 색(mapColor)·타일 배치
   (NATION_TILE)는 홈 첫 화면도 써서 home-app.js 에 남았다.
   ⚠️ 홈과 한 몸이다: sw.js 가 home-app.js 와 같은 규칙(network-first)으로 받고 같은 판 주소를 사전 캐시한다.
   판 표식으로 양방향 보호한다(주소의 ?v=판 + 아래 HOME_STATS_BUILD, home-app.js PARTS 주석).
   도구·시험은 이 파일을 직접 열지 말고 tools/home_src.py 의 home_source() 로 읽는다(홈 스크립트에 이어 붙어 온다). */
/* 판 표식 — home-app.js HOME_BUILD·sw.js VERSION 과 같은 값(test_home_build). 받은 뒤 홈이 견줘 다르면 한 번 새로고침한다
   (partBuildOk: 열어 둔 옛 판 탭이 배포 뒤 ?v=옛판 주소로 새 판 파일을 받는 경우). VERSION 을 올리면 여기도 같이. */
var HOME_STATS_BUILD='v179';
/* 착공→준공 시차별 연결 강도(r) — rebuild_cycle_analysis.link45_leadtime 과 **같은 계산**(전국 착공·준공 12개월 이동평균,
   과거 = 2018.01 앞 착공, 최근 = 그 뒤)을 시차 20~50개월에 펼친 곡선. 봉우리(최강 시차)는 박지 않고 곡선에서 찾는다
   (leadPeak) — 예전엔 옛 분석값 peak_old [27,0.96] 을 따로 박아 같은 화면 주석(28개월)·정본과 갈렸다(전수리뷰 #50·#105).
   봉우리가 정본(tools/data/cycle_analysis.json leadtime = sido_zones.START_DONE_MONTHS_*)과 같은지는
   test_home_stats_runtime 이 본다 — 사이클을 재산정하면 이 곡선도 같은 데이터로 다시 굽는다. */
const LEADTIME={"lags": [20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37, 38, 39, 40, 41, 42, 43, 44, 45, 46, 47, 48, 49, 50], "all": [0.511, 0.545, 0.582, 0.621, 0.661, 0.696, 0.731, 0.764, 0.792, 0.813, 0.827, 0.836, 0.839, 0.836, 0.825, 0.805, 0.777, 0.74, 0.697, 0.648, 0.595, 0.535, 0.471, 0.4, 0.321, 0.247, 0.175, 0.106, 0.034, -0.033, -0.1], "old": [0.821, 0.848, 0.874, 0.901, 0.924, 0.941, 0.956, 0.967, 0.971, 0.97, 0.96, 0.947, 0.928, 0.906, 0.883, 0.855, 0.824, 0.79, 0.752, 0.711, 0.666, 0.612, 0.55, 0.484, 0.41, 0.327, 0.243, 0.159, 0.071, -0.011, -0.09], "new": [-0.006, 0.016, 0.059, 0.112, 0.182, 0.25, 0.327, 0.406, 0.483, 0.551, 0.615, 0.677, 0.736, 0.786, 0.823, 0.854, 0.869, 0.876, 0.869, 0.846, 0.813, 0.77, 0.732, 0.65, 0.548, 0.46, 0.394, 0.341, 0.283, 0.227, 0.152]};
/* 시군구·서울구 전체 시계열은 '구를 고른 사람'만 받는다(통계 탭 기본 전송량 유지).
   ⚠️ Object.assign(ADV, d.ADV)를 쓰면 ADV.weekly가 통째로 교체돼 시도 rows를 잃는다 —
   그래서 sgg/seoul만 골라 덮어쓴다. */
let SGG_HIST_READY=false, _sggReq=null;
function ensureSggHist(){
  if(SGG_HIST_READY)return Promise.resolve();
  if(_sggReq)return _sggReq;
  _sggReq=fetch('/data-sgg.json').then(r=>{
    if(!r.ok)throw new Error('HTTP '+r.status);
    return r.json();
  }).then(d=>{
    const src=(d&&d.ADV)||{};
    ['weekly','monthly'].forEach(k=>{
      const s2=src[k]; if(!s2||!ADV[k])return;
      ['sgg','seoul'].forEach(part=>{ if(s2[part]&&s2[part].rows)ADV[k][part]=s2[part]; });
    });
    SGG_HIST_READY=true;
  }).catch(e=>{ _sggReq=null; throw e; });
  return _sggReq;
}
/* 시군구를 고르면 먼저 있는 만큼(12구간) 즉시 그리고, 전체가 도착하면 다시 그린다 */
function onTrendSgg(k){
  const T=TREND[k], sub=document.getElementById(T.sel2);
  trOpenDrop(k);
  TRSHOW[k]=12;
  const render=k==='week'?renderWeekSec:renderMonthSec;
  render();
  if(sub&&sub.value&&!SGG_HIST_READY)ensureSggHist().then(render).catch(()=>{});
}
/* 통계 화면 첫 진입(home-app.js showView). 대기열이 이 파일과 그래프 데이터(data-trend.json)를 둘 다 받은 뒤에 부르므로
   주간·월간 그래프는 곧바로 그린다. 기본통계 세그먼트와 버블밴드는 기본통계 데이터(data-rest.json)를 기다린다 — 버블밴드
   입력(ADV.bubble·STATS 전세가율)은 B11 에 data-core 에서 빠져 trend·rest 로만 온다(예전엔 코어에 있어 기다리지 않았다).
   ⚠️ renderBubbleSec 가 읽는 건 그 둘뿐이다(옛 주석이 주택멸실도 읽는다고 적어 소비자 없는 계열이 코어에 남았던 일,
   2026-08-07 감사). 못 받으면 statsInited 를 되돌려 다음 진입에서 다시 받는다.
   ⚠️ 첫머리에서 그래프 데이터(loadFullData)를 **다시** 기다린다(전수리뷰 #42·#48). 이 파일은 받고 data-trend.json 만
   실패하면 대기열은 실패로 끝나지만 여기 최상위 선언이 이미 대기 함수를 덮어써서, 다시 들어올 때 showView 가 이 함수를
   곧바로 부른다. 예전엔 여기서 trend 를 부르지 않아 코어 4주치를 '전체'로 그렸고 투자지표에서 TypeError 가 났다.
   이미 받았으면 loadData 가 캐시한 약속이 곧바로 풀린다. */
let TREND_P=null;   // 주간·월간 첫 그림이 끝나는 약속 — openTrendRegion 이 이 뒤에 고른 지역을 그린다(첫 그림이 덮지 않게)
function statsOpen(){
  TREND_P=loadFullData().then(()=>{
    renderReleaseInfo();
    renderWeekSec();
    renderMonthSec();
  });
  return TREND_P.then(()=>ensureBasicStats()
      .then(()=>{ renderBubbleSec(); initStats(); }))
    .catch(()=>{statsInited=false;TREND_P=null;});
}
/* 기본통계(13계열)는 이 함수를 거쳐서만 그린다 */
/* ============ 통계 대시보드 ============ */
// 날짜 정규화: "2006.01","2006.01 p)","2007/01","2012.1","2024" -> {y,m}
function parseDate(s){
  s=String(s).replace(/\s*p\)?\s*/g,'').trim();
  let m=s.match(/(\d{4})[.\/]\s*(\d{1,2})/);
  if(m)return{y:+m[1],m:+m[2],label:m[1]+'.'+String(+m[2]).padStart(2,'0')};
  let y=s.match(/^(\d{4})$/);
  if(y)return{y:+y[1],m:12,label:y[1]};
  return{y:0,m:0,label:s};
}
// 보조선 정의 (우리가 리포트에서 논의한 변곡점들)
/* '정점'·'바닥'은 날짜를 박지 않는다 — find('max'|'min')와 구간(from~to)만 두고, 그리는 계열·지역의 원자료에서 그 구간
   최댓값·최솟값 달을 찾아 선을 세우고 날짜를 라벨에 붙인다(auxPos). 예전엔 '2021 정점'을 2021.09 에 박아, 원자료 정점
   (전국·서울 매매 2021.10, 전세 전국 2021.11·서울 2022.06)과 어긋났고 지역을 바꿔도 같은 자리에 섰다(전수리뷰 #59).
   사건(정책·입주장) 표지는 날짜 그대로 둔다. */
const AUXLINES={
  '매매지수':[{y:2018,m:1,t:'2018 수도권 매매만 급등',c:'#e8b84b'},{find:'max',from:'2020.01',to:'2023.12',t:'정점',c:'#e0564a'}],
  '전세지수':[{find:'max',from:'2020.01',to:'2023.12',t:'정점',c:'#e0564a'},{y:2023,m:1,t:'2023 입주장',c:'#3aa17e'}],
  '금리':[{find:'min',from:'2020.01',to:'2021.12',t:'금리 바닥',c:'#3aa17e'},{find:'max',from:'2022.01',to:'2023.12',t:'금리 정점',c:'#e0564a'}],
  '착공':[{y:2022,m:1,t:'착공 급감',c:'#e0564a'}],
  // 준공연도 + 40년 = 재건축 연한 도래 시점. 축은 준공연도라 도래 연도를 라벨에
  // 병기한다(실측: 1988년 16.2만 → 2028년 / 1992년 38.1만 → 2032년 / 1995년 43.0만
  // → 2035년). 40년차 도래는 '헐릴 물량'이 아니라 후보 재고다 — 실현 비율은 별개.
  '아파트건설':[{y:1988,m:12,t:'88올림픽 급증 · 40년차 2028',c:'#e0564a'},
    {y:1992,m:12,t:'38만 돌파 · 40년차 2032',c:'#b5651d'},
    {y:1995,m:12,t:'정점 43만 · 40년차 2035',c:'#9a7000'}],
};
const DS_LABEL={매매지수:'매매 실거래지수',전세지수:'전세 실거래지수',전세가율:'전세가율',
  규모별:'규모별 동향',
  인허가:'인허가',착공:'착공',분양:'신규 분양',준공:'준공',미분양:'미분양',
  금리:'CD금리',보급률:'주택보급률',
  아파트건설:'아파트 건설(연도별)',주택멸실:'주택 멸실',아파트멸실:'아파트 멸실',노후주택30년:'30년이상 노후아파트',
  리드타임:'착공·준공 리드타임'};
const DS_COLOR={매매지수:'#e0564a',전세지수:'#a98be0',전세가율:'#2c7a5b',인허가:'#e8a33b',
  착공:'#3a7bd5',분양:'#3f7d8c',준공:'#7b5ea8',미분양:'#8a6a4a',
  금리:'#e8b84b',보급률:'#2c5f9e',
  아파트건설:'#c0563a',주택멸실:'#9a4a3a',아파트멸실:'#b5563f',노후주택30년:'#b8862c'};
/* 색이 빠진 계열을 고르면 areaGrad가 'undefined38'을 addColorStop에 넘겨 예외로
   차트가 통째로 안 그려진다 — 아파트멸실이 실제로 그랬다(2026-08-07 감사). */
const DS_FALLBACK='#5e6f74';

/* 세그먼트 표시 순서. Object.keys(STATS)를 그대로 쓰면 data-core.js에 먼저
   담긴 전세가율·주택멸실이 앞으로 튀어나와, 기본 선택인 매매지수가 3번째에
   놓인다(모바일에서 선택 칩이 화면 밖). 가격→공급→주거여건→금리 순으로 고정. */
// 공급 파이프라인 순서대로: 인허가→착공→분양→준공→미분양(분양의 잔량)
// '아파트멸실'은 러닝재고(준공−멸실−적정)가 실제로 쓰는 계열이라 준공 옆에 둔다.
// '주택멸실'(계, 단독 포함)은 표시용으로 남긴다 — 둘은 값이 크게 다르므로
// (2024 전국 85,069호 vs 아파트분) 라벨로 구분되게 나란히 세운다.
const DS_ORDER=['매매지수','전세지수','전세가율','규모별','인허가','착공','분양','준공','미분양',
  '아파트건설','노후주택30년','아파트멸실','주택멸실','보급률','금리','리드타임'];
let ST={ds:'매매지수',reg:null,years:0,aux:new Set()};
let statChartObj=null;

function initStats(){
  // 데이터셋 세그먼트 (+리드타임 특수항목)
  const seg=document.getElementById('ds-seg');
  // DS_ORDER 기준 정렬 — 목록에 없는 신규 계열이 생겨도 빠지지 않게 뒤에 붙인다
  // 지연 로드 계열(규모별)은 아직 STATS에 없어도 목록에 세운다 — 누르면 그때 받는다
  // (2026-08-01 분리. 안 넣으면 세그먼트에서 통째로 사라진다).
  const avail=[...new Set([...Object.keys(STATS),'규모별','리드타임'])];
  const keys=DS_ORDER.filter(k=>avail.includes(k))
    .concat(avail.filter(k=>!DS_ORDER.includes(k)));
  seg.innerHTML=keys.map(k=>
    `<button data-ds="${k}"${k===ST.ds?' class="on"':''}>${DS_LABEL[k]}</button>`).join('');
  seg.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
    ST.ds=b.dataset.ds;ST.aux.clear();ST.reg=null;
    track('stats_dataset',{dataset:ST.ds});
    seg.querySelectorAll('button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
    const isLead=ST.ds==='리드타임', isSize=ST.ds==='규모별';
    document.getElementById('reg-sel').parentElement.style.display=isLead?'none':'';
    document.getElementById('period-seg').style.display=isLead?'none':'';
    document.getElementById('aux-seg').style.display=(isLead||isSize)?'none':'';
    document.getElementById('size-ctl').style.display=isSize?'':'none';
    // 규모별은 표 전용(피벗) — 그래프/표 토글을 숨기고 표 모드로 고정
    const gth=document.querySelector('#sec-basicmain .gt-head');
    if(gth)gth.style.display=isSize?'none':'';
    if(isSize)gtSet('basicmain','t');
    // 지연 계열(규모별)은 fillRegions가 STATS[ST.ds]를 바로 읽으므로 여기서 먼저 받는다
    const go=()=>{ if(isLead){drawLeadtime();}else{fillRegions();renderAux();drawStat();} };
    if(!isLead&&!STATS[ST.ds]) ensureSizeStats().then(go).catch(()=>{}); else go();
  }));
  // 기간 프리셋
  document.querySelectorAll('#period-seg button').forEach(b=>b.addEventListener('click',()=>{
    ST.years=+b.dataset.y;
    document.querySelectorAll('#period-seg button').forEach(x=>x.classList.remove('on'));b.classList.add('on');
    drawStat();
  }));
  document.getElementById('reg-sel').addEventListener('change',e=>{ST.reg=e.target.value;drawStat();});
  fillRegions();renderAux();drawStat();
  // 주간·월간·버블밴드는 탭 진입 시 이미 그렸다 —
  // 여기는 STATS 11계열(data-rest.json)이 있어야만 가능한 것만 남긴다.
}
/* 지역 목록 정렬은 사이트 전체가 하나여야 한다 — 예전엔 목록마다 데이터 적재 순서를
   그대로 써서 화면마다 순서가 달랐고, 내 지역을 찾으려면 매번 훑어야 했다(2026-08-01).
   인구순도 후보였지만 통계 드롭다운엔 지역명만 있고 인구가 없다. 모든 목록에 적용할 수
   있는 건 가나다순뿐이고, 찾는 목적에도 그게 낫다(위치가 이름으로 정해진다).
   전국·수도권 같은 집계 항목은 시도의 동료가 아니므로 맨 앞에 원래 순서로 남긴다. */
const REG_AGG=['전국','수도권','지방','6대광역시','5대광역시','9개도','8개도'];
function regSort(list,label){
  const nameOf=label||(x=>x);
  const agg=list.filter(x=>REG_AGG.indexOf(nameOf(x))>=0);
  const rest=list.filter(x=>REG_AGG.indexOf(nameOf(x))<0)
                 .sort((a,b)=>String(nameOf(a)).localeCompare(String(nameOf(b)),'ko'));
  return agg.concat(rest);
}
function fillRegions(){
  const sel=document.getElementById('reg-sel');
  const D=STATS[ST.ds];
  // 규모별은 series가 지표 키라 regions 목록을 따로 싣는다. 기본 지역도 전국.
  /* 값이 하나도 없는 지역은 세우지 않는다. 분양·미분양은 계열을 만들 때 준공의
     지역 키를 복사하는데 R-ONE 원표에 '기타광역시'·'기타지방' 집계가 없어
     전 구간 null인 선택지가 떴다 — 고르면 표는 머리글만, 차트는 빈 화면이었다. */
  const has=r=>{const s=D.series[r]; return !s||s.some(v=>v!=null);};
  const regs=regSort(ST.ds==='규모별'?(D.regions||[]):Object.keys(D.series).filter(has));
  if(!regs.includes(ST.reg)) ST.reg = ST.ds==='규모별'?regs[0]:(regs.includes('서울')?'서울':regs[0]);
  sel.innerHTML=regs.map(r=>`<option${r===ST.reg?' selected':''}>${r}</option>`).join('');
}
/* 보조선 위치(차트 칸 번호). find 가 있으면 labels·vals 의 from~to 구간에서 최댓값·최솟값 칸, 없으면 그 연월 칸. */
function auxPos(l,labels,vals){
  if(!l.find)return labels.findIndex(lb=>lb===l.y+'.'+String(l.m).padStart(2,'0')||lb===String(l.y));
  let b=-1;
  labels.forEach((lb,i)=>{
    if(lb<l.from||lb>l.to||vals[i]==null)return;
    if(b<0||(l.find==='max'?vals[i]>vals[b]:vals[i]<vals[b]))b=i;
  });
  return b;
}
function renderAux(){
  const box=document.getElementById('aux-seg');
  const lines=AUXLINES[ST.ds]||[];
  box.innerHTML=lines.map((l,i)=>`<button data-i="${i}">― ${l.t}</button>`).join('');
  box.querySelectorAll('button').forEach(b=>b.addEventListener('click',()=>{
    const i=b.dataset.i; if(ST.aux.has(i)){ST.aux.delete(i);b.classList.remove('on');}
    else{ST.aux.add(i);b.classList.add('on');} drawStat();
  }));
}
/* 기본통계 표·메타·출처는 차트 라이브러리와 무관하다 — 라이브러리를 못 받아도 표는 그리고, 그래프 자리에만 안내를
   단다(전수리뷰 #53). 예전엔 drawStat 첫 줄에서 라이브러리를 기다려, 못 받으면 표·피벗·출처까지 안내 없이 비었다. */
function chartFailNote(){
  loadChart().catch(()=>{
    const n=document.getElementById('src-note');
    if(n&&!n.querySelector('.chart-fail'))n.insertAdjacentHTML('beforeend',' <b class="chart-fail">그래프를 불러오지 못했습니다. 연결을 확인하고 다시 눌러 주세요.</b>');
  });
}
function drawStat(){
  if(ST.ds==='규모별'){
    if(!STATS['규모별']){ ensureSizeStats().then(drawStat).catch(()=>{}); return; }
    drawSizePivot();return;
  }
  document.getElementById('stat-tbl').classList.remove('szpivot');
  const D=STATS[ST.ds], raw=D.series[ST.reg]||[];
  const parsed=D.dates.map(parseDate);
  // 기간 필터
  let idx=parsed.map((p,i)=>i);
  if(ST.years>0){
    const last=parsed[parsed.length-1];
    const cutY=last.y-ST.years, cutM=last.m;
    idx=idx.filter(i=>parsed[i].y>cutY||(parsed[i].y===cutY&&parsed[i].m>=cutM));
  }
  const labels=idx.map(i=>parsed[i].label);
  const rawFirst=dsFirst(raw);
  const vals=idx.map(i=>dsV(raw[i],i,rawFirst));   // 진짜 0인 달을 차트가 건너뛰지 않게
  /* 표를 차트보다 먼저 그린다(2026-08-03). 예전엔 차트 생성이 먼저라, 캔버스
     소유권이 꼬여 'Canvas is already in use'가 터지면 buildMatrix까지 못 가서
     행열 전환이 조용히 죽었다(인허가·착공·분양·준공·미분양에서 실측). */
  document.getElementById('meta-bar').innerHTML=
    `<span>단위 <b>${D.unit}</b></span><span>지역 <b>${ST.reg}</b></span><span>출처 <b>${D.source}</b></span>`;
  buildTable(D,labels,vals,idx,parsed);
  buildMatrix(D,idx,parsed);
  document.getElementById('src-note').innerHTML=
    `※ ${D.note?D.note+'. ':''}가공 없는 원자료다.`;
  if(needChart(()=>drawStat())){ chartFailNote(); return; }   // 그래프만 라이브러리를 기다린다(#53)
  /* statChartObj만 믿고 destroy하면 참조가 어긋났을 때(비동기 재진입 등) 캔버스에
     고아 차트가 남아 이후 모든 생성이 실패한다 — 실소유 차트를 찾아 파괴한다. */
  const _own=Chart.getChart('statChart'); if(_own)_own.destroy();
  statChartObj=null;
  const col=DS_COLOR[ST.ds]||DS_FALLBACK;
  statChartObj=new Chart(document.getElementById('statChart'),{
    type:'line',
    data:{labels,datasets:[{label:DS_LABEL[ST.ds],data:vals,borderColor:col,
      backgroundColor:areaGrad(col),borderWidth:2,pointRadius:0,pointHoverRadius:4,
      tension:.25,fill:true,spanGaps:true}]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},
        tooltip:{callbacks:{label:c=>`${DS_LABEL[ST.ds]}: ${fmtN(c.raw)} ${D.unit.split(' ')[0]}`}}},
      scales:{x:{grid:{display:false},ticks:{maxTicksLimit:8,maxRotation:0,autoSkip:true}},
        y:{grid:{color:GRID},title:{display:true,text:D.unit}}}},
    plugins:[{id:'vlines',afterDraw(ch){
      const ctx=ch.ctx,ya=ch.scales.y,xa=ch.scales.x;
      let drawn=[];
      (AUXLINES[ST.ds]||[]).forEach((l,i)=>{
        if(!ST.aux.has(String(i)))return;
        const pos=auxPos(l,labels,vals);
        if(pos<0)return;
        const x=xa.getPixelForValue(pos);
        ctx.save();ctx.strokeStyle=l.c;ctx.lineWidth=1.5;ctx.setLineDash([5,4]);
        ctx.beginPath();ctx.moveTo(x,ya.top);ctx.lineTo(x,ya.bottom);ctx.stroke();
        ctx.setLineDash([]);ctx.fillStyle=l.c;ctx.font='700 10px '+FONT;
        // 인접 라벨과 겹치면 빈 줄을 찾을 때까지 내린다. 예전엔 2행 고정이라
        // 보조선이 3개 이상 붙어 있으면(아파트건설 1988/1992/1995) 3번째가
        // 2번째 위에 그대로 겹쳐 찍혔다.
        let row=0;
        while(drawn.some(d=>d.row===row&&Math.abs(d.x-x)<70))row++;
        const ty=ya.top+11+row*14;
        ctx.textAlign=x>xa.right-50?'right':'left';
        ctx.fillText(' '+l.t+(l.find?' '+labels[pos]:''),x,ty);drawn.push({x:x,row:row});ctx.restore();
      });
    }}]
  });
  // 기간 표시
  document.getElementById('prange').innerHTML=labels.length?
    `<b>${labels[0]}</b> ~ <b>${labels[labels.length-1]}</b> · ${labels.length}개 시점`:'데이터 없음';
}
function fmtN(v,dec){return (v==null||isNaN(v))?'-':Number(v).toLocaleString('ko-KR',{maximumFractionDigits:dec==null?2:dec});}
/* PC 표 모드: 전 지역(광역시도) 매트릭스 — 투자지표 인허가 표와 같은 형식 */
const MATRIX_REGIONS=['전국','수도권','지방','서울','경기','인천','부산','대구','전남광주','대전','울산','세종','강원','충북','충남','전북','경북','경남','제주'];
function buildMatrix(D,idx,parsed){
  const box=document.getElementById('stat-matrix');
  /* ⚠️ filter 는 목록에 없는 지역을 **조용히** 걸러낸다. 모델이 바뀌었는데 위
     목록만 옛것이면 그 지역이 표에서 통째로 사라지는데 아무것도 빨개지지 않는다.
     2026-09-12 에 실제로 그랬다 — 광주·전남이 '전남광주'로 합쳐진 뒤에도 목록이
     옛 이름을 들고 있어, 데이터에 있는 전남광주가 PC 표 모드에서 안 보였다.
     같은 사고가 사이클 전세가율 차트에도 있었다(355d767). 조용히 빠뜨리지 않도록
     데이터에만 있는 지역은 뒤에 붙이고 콘솔에 남긴다. */
  const regs=MATRIX_REGIONS.filter(r=>D.series[r]);
  /* ⚠️ 경고만 하고 **표에 넣지는 않는다.** 넣었더니 전세가율의 권역 집계
     (6대광역시·5대광역시·9개도·8개도)까지 시도 표 끝에 붙었다 — 원래 여기 오면
     안 되는 행이다. 데이터에만 있다고 다 시도인 것이 아니라서, 무엇을 넣을지는
     JS 쪽에서 판단할 수가 없다.
     빠지는 것을 막는 주 방어는 시험이다(tools/tests/test_region_lists.py 가
     MATRIX_REGIONS 를 sido_zones.ORDER 와 대조해 배포 전에 잡는다). 이 경고는
     그 시험이 없는 경로로 데이터가 바뀌었을 때를 위한 보조 신호다. */
  /* ⚠️ 집계 행은 제외하고 센다. 원천이 주는 권역 묶음(6대광역시·9개도·도심권 등)은
     시도가 아니라 여기 올 일이 없는데, 그걸 그대로 세면 경고가 **매 방문 뜬다**.
     항상 켜진 경고는 아무것도 가리키지 못해 진짜 누락을 묻는다(2026-09-12 리뷰:
     전세가율 4개·매매지수 8개가 늘 걸렸다). 시도처럼 생긴 것만 남긴다. */
  const NON_SIDO=['6대광역시','5대광역시','광역시','지방광역시','9개도','8개도','지방도',
    '기타광역시','기타지방','도심권','동북권','동남권','서북권','서남권','CD(91일)'];
  const missed=Object.keys(D.series||{})
    .filter(r=>MATRIX_REGIONS.indexOf(r)<0 && NON_SIDO.indexOf(r)<0);
  if(missed.length)
    console.warn('MATRIX_REGIONS에 없는 지역이 데이터에 있다 — 시도라면 목록에 넣을 것:',missed);
  const single=regs.length<=1;
  document.getElementById('sec-basicmain').classList.toggle('single',single);
  if(single){box.innerHTML='';return;}
  const isMonthly=!D.annual&&parsed[idx[0]].m>0;
  let h;
  if(TRANSP.basicmain){
    h=['<table class="adv"><thead><tr><th>지역</th>'+idx.map(i=>`<th>${parsed[i].label}</th>`).join('')+'</tr></thead><tbody>'];
    regs.forEach(r=>{
      const f=dsFirst(D.series[r]);
      h.push(`<tr><td>${r}</td>`+idx.map(i=>{
        const v=dsV(D.series[r][i],i,f);
        return `<td>${v==null?'·':fmtN(v)}</td>`;
      }).join('')+'</tr>');
    });
  }else{
    h=['<table class="adv"><thead><tr><th>'+(isMonthly?'연월':'연도')+'</th>'+regs.map(r=>`<th>${r}</th>`).join('')+'</tr></thead><tbody>'];
    for(let k=idx.length-1;k>=0;k--){
      const i=idx[k];
      h.push(`<tr><td>${parsed[i].label}</td>`+regs.map(r=>{
        const v=dsV(D.series[r][i],i,dsFirst(D.series[r]));
        return `<td>${v==null?'·':fmtN(v)}</td>`;
      }).join('')+'</tr>');
    }
  }
  h.push('</tbody></table>');
  box.innerHTML=h.join('');
}
/* ⚠️ KOSIS는 값 0을 '-'로 준다. 아래 4계열의 null은 결측이 아니라 **진짜 0**이다 —
   17시도 합(null→0)이 원천의 독립 '전국' 행과 준공 191/191개월·착공 186/186개월
   전부 일치한다(2026-08-08 감사). 예전엔 그 달의 행이 표에서 통째로 사라지고
   차트가 0 골짜기를 직선으로 덮었으며, 같은 표 안에서 명시적 0은 '0'으로 뜨는데
   null은 '·'로 떠 자기모순이었다. tools/sido_zones.py _series가 이미 (v or 0)으로
   세고 있어, 안 맞추면 홈 공급표·등급과 통계 탭이 같은 원천을 반대로 해석한다. */
const DS_ZERO=new Set(['준공','착공','인허가','분양']);
/* ⚠️ null 두 종류를 갈라야 한다. 계열이 그 지역에서 **시작되기 전**의 null은
   '진짜 0'이 아니라 '아직 없던 지역·기간'이다 — 세종은 2012.07 출범이라
   준공 null 73개 중 23개, 미분양 null 76개 중 73개가 출범 이전이다.
   전부 0으로 찍으면 없던 도시의 0이 그래프에 그려진다. 첫 실측값 **이후**의
   null만 0으로 본다(2026-08-08 자체 점검). */
function dsFirst(arr){ for(let i=0;i<arr.length;i++) if(arr[i]!=null) return i; return -1; }
function dsV(v,i,first){
  if(v!=null) return v;
  if(!DS_ZERO.has(ST.ds)) return null;
  return (first>=0&&i>=first)?0:null;
}
/* 인허가는 **연내 누계**다(1월부터 누적, 12월이 연간 합계). 여기에 flow용
   '전기 대비'를 그대로 적용하면 12월 누계 → 1월 누계에서 -98%짜리 없는 급락이
   찍히고, 2월 이후 %도 분자는 그 달 실적·분모는 전월까지 누적이라 의미가 없다
   (2026-08-08 감사). 누계 계열은 **전년 동월 대비**로 견준다. */
const DS_CUM=new Set(['인허가']);
function buildTable(D,labels,vals,idx,parsed){
  const thead=document.querySelector('#stat-tbl thead'),tbody=document.querySelector('#stat-tbl tbody');
  const isMonthly=!D.annual && parsed[0].m>0;
  const cum=DS_CUM.has(ST.ds), lag=cum?(isMonthly?12:1):1;
  thead.innerHTML=`<tr><th>${isMonthly?'연월':'연도'}</th><th>${DS_LABEL[ST.ds]}</th><th>${cum?'전년 동월 대비':'전기 대비'}</th></tr>`;
  /* 비교 칸은 인덱스 차(k-lag)가 아니라 연월로 찾는다. 배치가 보류한 달(미분양 2026.07)이 끝내
     안 채워지면 dates에 그 달 칸이 없어 k-1이 두 달 전이 되고 '전기 대비'에 두 달 치가 실린다
     (2026-09-26 데이터 감사 #17, 생성기는 sido_zones.month_back). 연 자료는 12달 = 1기다. */
  const ymk=p=>p.y*12+p.m, step=isMonthly?1:12;
  const at=new Map(idx.map((i,k)=>[ymk(parsed[i]),k]));
  let html='';
  for(let k=labels.length-1;k>=0;k--){
    const v=vals[k]; if(v==null)continue;   // drawStat에서 이미 dsV를 거쳤다
    let chg='';
    let pk=at.get(ymk(parsed[idx[k]])-lag*step);
    /* 미분양은 2000~2006년이 해마다 12월 한 점이다. 그 구간의 '전기'는 전년 12월이므로, 바로 앞 칸이
       정확히 12달 앞이면 그 칸과 견준다(빠진 달은 1~11달 차라 여기에 걸리지 않는다). */
    if(pk==null&&k>=1&&ymk(parsed[idx[k]])-ymk(parsed[idx[k-1]])===12)pk=k-1;
    const prev=pk==null?null:vals[pk];
    if(prev!=null){
      const d=v-prev;
      const cls=d>0?'chg-up':(d<0?'chg-dn':'');
      /* 직전이 0이면 증가율은 정의되지 않는다. 예전엔 0을 대입해 '+5,129 (0%)'처럼
         '변화 없음'으로 읽히게 찍었다(637셀, 2026-08-08 감사). 증감폭만 낸다. */
      const pct=prev!==0?fmtN(d/prev*100,1)+'%':'–';
      chg=`<span class="${cls}">${d>0?'+':''}${fmtN(d)} (${prev!==0&&d/prev>0?'+':''}${pct})</span>`;
    }
    html+=`<tr><td>${labels[k]}</td><td>${fmtN(v)}</td><td>${chg}</td></tr>`;
  }
  tbody.innerHTML=html;
}

/* 착공→준공 리드타임 시차곡선 (시기별 비교) */
function leadPeak(a){ let b=-1; a.forEach((v,i)=>{ if(v!=null&&(b<0||v>a[b]))b=i; }); return b<0?null:[LEADTIME.lags[b],a[b]]; }
function drawLeadtime(){
  const L=LEADTIME, pOld=leadPeak(L.old), pNew=leadPeak(L.new);
  document.getElementById('stat-tbl').classList.remove('szpivot');
  document.getElementById('sec-basicmain').classList.add('single');
  document.getElementById('stat-matrix').innerHTML='';
  /* 표·메타·출처를 먼저 그리고 그래프만 라이브러리를 기다린다(drawStat 과 같은 규칙, 전수리뷰 #53). 예전엔 첫 줄에서
     돌아가, 라이브러리를 못 받으면 단추는 '리드타임'인데 표·메타는 앞 데이터셋(매매 실거래지수 248행)이 남았다(통합 검토). */
  document.getElementById('prange').innerHTML=
    `과거 최강 시차 <b>${pOld[0]}개월</b> → 최근 <b>${pNew[0]}개월</b>`;
  document.getElementById('meta-bar').innerHTML=
    `<span>단위 <b>상관계수 r</b></span><span>대상 <b>전국 착공·준공(12개월 이동평균)</b></span><span>출처 <b>국토교통부</b></span>`;
  // 테이블: 시차별 r 비교
  const thead=document.querySelector('#stat-tbl thead'),tbody=document.querySelector('#stat-tbl tbody');
  thead.innerHTML=`<tr><th>시차(개월)</th><th>2011~2017</th><th>2018~</th></tr>`;
  let h='';
  L.lags.forEach((lg,i)=>{
    if(lg<24||lg>44||lg%2)return;
    h+=`<tr><td>${lg}</td><td>${L.old[i]??'-'}</td><td>${L.new[i]??'-'}</td></tr>`;
  });
  tbody.innerHTML=h;
  document.getElementById('src-note').innerHTML=
    `※ 착공량과 준공량의 12개월 이동평균을 시차를 두고 비교한 것. 곡선의 봉우리가 평균 공사기간을 뜻한다. 과거 약 ${pOld[0]}개월에서 최근 약 ${pNew[0]}개월로 길어졌다 — 공사비·인력·안전기준 변화 등이 원인으로 추정된다.`;
  if(needChart(()=>drawLeadtime())){ chartFailNote(); return; }
  {const _o=Chart.getChart('statChart'); if(_o)_o.destroy();}
  statChartObj=new Chart(document.getElementById('statChart'),{
    type:'line',
    data:{labels:L.lags,datasets:[
      {label:'2011~2017 (과거)',data:L.old,borderColor:'#3a7bd5',backgroundColor:'transparent',
        borderWidth:2.5,pointRadius:0,tension:.3,spanGaps:true},
      {label:'2018~ (최근)',data:L.new,borderColor:'#e0564a',backgroundColor:'transparent',
        borderWidth:2.5,pointRadius:0,tension:.3,spanGaps:true}
    ]},
    options:{responsive:true,maintainAspectRatio:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:true,position:'top',labels:{boxWidth:14,font:{size:12}}},
        tooltip:{callbacks:{title:c=>c[0].label+'개월 시차',label:c=>`${c.dataset.label}: r=${c.raw??'-'}`}}},
      scales:{x:{grid:{display:false},title:{display:true,text:'착공→준공 시차 (개월)'},
          ticks:{callback:(v,i)=>L.lags[i]%4===0?L.lags[i]:''}},
        y:{grid:{color:GRID},title:{display:true,text:'연결 강도 (r)'},min:0,max:1}}},
    plugins:[{id:'peaks',afterDraw(ch){
      const ctx=ch.ctx,xa=ch.scales.x,ya=ch.scales.y;
      [[pOld,'#3a7bd5'],[pNew,'#e0564a']].forEach(([pk,c])=>{
        if(!pk)return; const xi=L.lags.indexOf(pk[0]); if(xi<0)return;
        const x=xa.getPixelForValue(xi),y=ya.getPixelForValue(pk[1]);
        ctx.save();ctx.fillStyle=c;ctx.beginPath();ctx.arc(x,y,4,0,7);ctx.fill();
        ctx.font='700 11px '+FONT;ctx.textAlign='center';
        ctx.fillText(pk[0]+'개월',x,y-9);ctx.restore();
      });
    }}]
  });
}

/* ── 규모별 동향 피벗 (지표×규모 멀티선택, 전월비% 표) ──
   series[지표][지역] = 월별 [규모6 값] (지수 3종=전월비%, 전환율=수준%).
   지표를 바깥 그룹으로 묶는다 — 전환율(단위 %)이 블록으로 격리되고,
   바깥 그룹 수(지표≤4)가 규모(≤6)보다 적어 헤더가 안정적이다. */
let SZ={met:new Set(['매매','전세']),siz:new Set([2]),desc:true,tr:false};
function renderSizeCtl(){
  const D=STATS['규모별'];if(!D)return;
  const box=document.getElementById('size-ctl');
  const short=s=>s.replace(/㎡/g,'');
  box.innerHTML=
    '<div class="period szrow szmet">'+D.metrics.map(m=>
      `<button data-m="${m}"${SZ.met.has(m)?' class="on"':''}>${m}</button>`).join('')+'</div>'+
    '<div class="period szrow szsiz">'+D.sizes.map((s,i)=>
      `<button data-s="${i}"${SZ.siz.has(i)?' class="on"':''}>${short(s)}</button>`).join('')+'</div>'+
    '<div class="szops">'+
      `<button class="trbtn" data-o="sort">${SZ.desc?'최신순 ↓':'과거순 ↑'}</button>`+
      `<button class="trbtn${SZ.tr?' on':''}" data-o="tr">⇄ 행열 전환</button></div>`;
  box.querySelectorAll('button[data-m]').forEach(b=>b.addEventListener('click',()=>{
    const m=b.dataset.m;
    if(SZ.met.has(m)){if(SZ.met.size<=1)return;SZ.met.delete(m);b.classList.remove('on');}
    else{SZ.met.add(m);b.classList.add('on');}
    track('stats_size',{met:[...SZ.met].join('/')});drawSizePivot();
  }));
  box.querySelectorAll('button[data-s]').forEach(b=>b.addEventListener('click',()=>{
    const s=+b.dataset.s;
    if(SZ.siz.has(s)){if(SZ.siz.size<=1)return;SZ.siz.delete(s);b.classList.remove('on');}
    else{SZ.siz.add(s);b.classList.add('on');}
    track('stats_size',{siz:[...SZ.siz].sort().join(',')});drawSizePivot();
  }));
  box.querySelector('button[data-o="sort"]').addEventListener('click',e=>{
    SZ.desc=!SZ.desc;e.target.textContent=SZ.desc?'최신순 ↓':'과거순 ↑';
    track('stats_size',{sort:SZ.desc?'desc':'asc'});drawSizePivot();
  });
  box.querySelector('button[data-o="tr"]').addEventListener('click',e=>{
    SZ.tr=!SZ.tr;e.target.classList.toggle('on',SZ.tr);
    track('stats_size',{tr:SZ.tr?1:0});drawSizePivot();
  });
}
function drawSizePivot(){
  const D=STATS['규모별'];if(!D)return;
  if(!document.getElementById('size-ctl').innerHTML)renderSizeCtl();
  document.getElementById('sec-basicmain').classList.add('single');
  document.getElementById('stat-matrix').innerHTML='';
  {const _o=window.Chart&&Chart.getChart('statChart'); if(_o)_o.destroy();} statChartObj=null;   // 표만 그린다(#53)
  const reg=ST.reg||D.regions[0];
  let idx=D.dates.map((_,i)=>i);
  if(ST.years>0)idx=idx.filter(i=>i>=D.dates.length-ST.years*12);
  const mets=D.metrics.filter(m=>SZ.met.has(m));
  const sizes=[...SZ.siz].sort((a,b)=>a-b);
  const short=s=>s.replace(/㎡/g,'');
  // 열 구성 — 전환율은 자체 3구간(0→40↓,1→40-60,2+→60↑)으로 매핑·중복 제거
  const cols=[];
  mets.forEach(m=>{
    if(m==='전환율'){
      /* 전환율 구간(60↓/60~85/85↑)에 6개 규모를 맞춘다. 옛 매핑 si>=2?2:si는
     '40↓/40~60/60↑' 전제라 si1·si2가 한 칸씩 밀렸다(2026-08-07 감사). */
    const tiers=[...new Set(sizes.map(si=>si<=1?0:(si===2?1:2)))];
      tiers.forEach((t,j)=>cols.push({m,si:t,lab:short(D.conv_sizes[t]),first:j===0,pct:false}));
    }else{
      sizes.forEach((si,j)=>cols.push({m,si,lab:short(D.sizes[si]),first:j===0,pct:true}));
    }
  });
  const val=c=>i=>{const a=(D.series[c.m][reg]||[])[i];return a?a[c.si]:null;};
  // grp: 세로 블록 경계(szgrp)를 붙일지 — 세로 모드에서만 참. 전치 모드는 행이
  // 한 조합이라 c.first를 그대로 쓰면 그 행 전체에 세로선이 그려진다(실사고).
  const cell=(c,v,grp)=>{
    if(v==null)return '<td'+(grp?' class="szgrp"':'')+'>·</td>';
    const rc=c.pct?pvSign(v):v;
    const col=c.pct?(rc>0?';color:#c0392b':(rc<0?';color:#1a5276':'')):'';
    const t=c.pct?pv2(v):v.toFixed(2);
    return `<td${grp?' class="szgrp"':''} style="white-space:nowrap${col}">${t}</td>`;
  };
  const tbl=document.getElementById('stat-tbl');tbl.classList.add('szpivot');
  const thead=tbl.querySelector('thead'),tbody=tbl.querySelector('tbody');
  const ord=SZ.desc?[...idx].reverse():idx;   // 정렬 토글: 최신순↓ / 과거순↑
  let h='';
  if(SZ.tr){
    thead.innerHTML='<tr><th style="text-align:center">지표 · 규모</th>'+
      ord.map(i=>`<th>${D.dates[i].replace(/^20/,'')}</th>`).join('')+'</tr>';
    cols.forEach((c,ci)=>{
      h+=`<tr${c.first&&ci>0?' class="szgrp-r"':''}><td>${c.m} ${c.lab}${c.pct?'':' <span class="szu">%</span>'}</td>`+
        ord.map(i=>cell(c,val(c)(i),false)).join('')+'</tr>';
    });
  }else{
    thead.innerHTML='<tr><th>연월</th>'+cols.map(c=>
      `<th${c.first?' class="szgrp"':''}>${c.m}<span class="szsub">${c.lab}${c.pct?'':' %'}</span></th>`).join('')+'</tr>';
    ord.forEach(i=>{
      h+=`<tr><td>${D.dates[i]}</td>`+cols.map(c=>cell(c,val(c)(i),c.first)).join('')+'</tr>';
    });
  }
  tbody.innerHTML=h;
  document.getElementById('prange').innerHTML=idx.length?
    `<b>${D.dates[idx[0]]}</b> ~ <b>${D.dates[idx[idx.length-1]]}</b> · ${idx.length}개월`:'';
  document.getElementById('meta-bar').innerHTML=
    `<span>단위 <b>${D.unit}</b></span><span>지역 <b>${reg}</b></span><span>출처 <b>${D.source}</b></span>`;
  document.getElementById('src-note').innerHTML=
    `※ ${D.note}. 총계 대신 규모별로 보면 초소형(오피스텔성) 물량의 왜곡 없이 시장을 읽을 수 있다.`;
}
/* ============ 투자지표(구 심화통계) ============ */
let advRendered=false;
const SMODES=['market','basic','adv','more'];
function setStatsMode(m,push){
  if(!SMODES.includes(m))m='market';
  statsMode=m;
  SMODES.forEach(k=>{
    document.getElementById('smode-'+k).classList.toggle('on', k===m);
    document.getElementById('smode-'+k).setAttribute('aria-selected', k===m?'true':'false');
    document.getElementById('stats-'+k).style.display = k===m ? '' : 'none';
  });
  /* 투자지표 입력(permits·occupancy)은 data-trend 로만 온다. 아직 없으면(다시 받는 중) 온 뒤에 그린다 — 없는 채로
     그리면 renderAdvPermits 가 TypeError 로 이 함수를 중간에 끊어 화면과 주소가 갈렸다(전수리뷰 #42). */
  /* 첫 진입(statsOpen)이 그래프 데이터를 못 받아 statsInited 가 풀린 채면, 재진입 없이 모드 탭을 눌러도 다시 연다 —
     예전엔 투자지표 분기만 데이터를 다시 받아 그 화면만 그리고, loadData 성공이 '불러오지 못했습니다' 안내를 숨겨
     시장동향·기본통계가 안내 없이 빈 채로 남았다(통합 검토, #42 잔여). */
  if(curView==='stats'&&!statsInited){ statsInited=true; statsOpen(); }
  if(m==='adv' && !advRendered){
    if(advReady()){ renderAdvAll(); advRendered=true; }
    else loadFullData().then(()=>{ if(!advRendered&&advReady()){ renderAdvAll(curAdvTab()); advRendered=true; } }).catch(()=>{});
  }
  if(m==='basic'||m==='market'){ afterLayout(()=>window.dispatchEvent(new Event('resize'))); }
  /* 이벤트는 사람이 누른 전환만(push!==false) 센다 — 착지·뒤로 가기(applyHash)·내부 호출(renderAdvAll)까지 세면
     탭 전환 지표가 부푼다(전수리뷰 #52). setAdvTab·setMarketTab 도 같다. */
  if(push!==false){ track('stats_mode',{mode:m}); statsNav(statsHashOf(m)); }
}
function advReady(){ return typeof ADV!=='undefined'&&!!(ADV.permits&&ADV.occupancy); }   // 코어 데이터(data-core.js)를 못 받아 ADV 가 없을 때도 던지지 않게(A5)
function curAdvTab(){ return ['occ','permit','bubble'].find(k=>{const b=document.getElementById('atab-'+k);return b&&b.classList.contains('on');})||'occ'; }
function advFmt(v){ return v==null ? '·' : Number(v).toLocaleString('ko-KR'); }
/* 입주물량 미래 분기는 소수 한 자리로 실려 온다(분기마다 반올림하면 소비자가
   그걸 다시 더해 홈과 갈리기 때문). 화면에는 정수로 찍는다. */
function occFmt(v){ return v==null ? '·' : Math.round(v).toLocaleString('ko-KR'); }
function advSel(id, regions){
  const s=document.getElementById(id);
  if(s.options.length) return s.value;
  const list=regSort(regions);
  s.innerHTML=list.map(r=>`<option value="${r}">${r}</option>`).join('');
  return list[0];
}
/* --- 인허가 --- */
function permitCls(region, v){
  if(v==null) return '';
  const ref=ADV.permits.ref[region]; if(!ref) return '';
  if(v <= ref[0]/2) return 'lo';
  if(v >= ref[1]/2) return 'hi';
  return '';
}
function renderAdvPermits(){
  const P=ADV.permits, regs=P.regions;
  const plab=p=>p.replace('H1',' 상').replace('H2',' 하');
  let mx;
  if(TRANSP.permit){
    mx=['<table class="adv"><thead><tr><th>지역</th>'+P.rows.map(r=>`<th>${plab(r.p)}</th>`).join('')+'</tr></thead><tbody>'];
    regs.forEach((r,j)=>{
      mx.push(`<tr><td>${r}</td>`+P.rows.map(row=>`<td class="${permitCls(r,row.v[j])}">${advFmt(row.v[j])}</td>`).join('')+'</tr>');
    });
  }else{
    mx=['<table class="adv"><thead><tr><th>반기</th>'+regs.map(r=>`<th>${r}</th>`).join('')+'</tr></thead><tbody>'];
    for(let i=P.rows.length-1;i>=0;i--){
      const row=P.rows[i];
      mx.push(`<tr><td>${plab(row.p)}</td>`+
        row.v.map((v,j)=>`<td class="${permitCls(regs[j],v)}">${advFmt(v)}</td>`).join('')+'</tr>');
    }
  }
  mx.push('</tbody></table>');
  document.getElementById('adv-permit-matrix').innerHTML=mx.join('');
  const reg=advSel('adv-permit-reg',regs), ri=regs.indexOf(reg), ref=P.ref[reg];
  const cp=['<table class="adv"><thead><tr><th>반기</th><th>'+reg+'</th></tr></thead><tbody>'];
  for(let i=P.rows.length-1;i>=Math.max(0,P.rows.length-12);i--){
    const row=P.rows[i], v=row.v[ri];
    cp.push(`<tr><td>${row.p.replace('H1',' 상').replace('H2',' 하')}</td><td class="${permitCls(reg,v)}">${advFmt(v)}</td></tr>`);
  }
  cp.push(`</tbody></table>`);
  document.getElementById('adv-permit-compact').innerHTML=cp.join('')+
    (ref?`<div class="src-note" style="padding:8px 12px">과거 연간 저점 ${advFmt(ref[0])} · 고점 ${advFmt(ref[1])} (반기 환산 ½)</div>`:'');
}
/* --- 입주물량 --- */
function occCls(region,v){
  if(v==null) return '';
  /* 기준선은 분기 적정물량 하나다. 2026-08-07까지 여기에 '적정밴드'가 하나 더
     있어서, 같은 제주를 홈·존 페이지는 '매우 부족'이라 하고 이 표는 '밴드 상단
     초과(과잉)'라고 칠했다(감사 확인 23칸). 밴드는 걷었다. */
  /* 문턱은 /moveins/ 와 같은 정본(sido_zones.OCC_LO_PCT·OCC_HI_PCT, 대표 결정 ③)을 split_data 가 ADV.occupancy.band 로
     실어 준 값이다 — 여기 숫자를 적지 않는다(예전 60%·100% 는 /moveins/ 70%·130% 와 같은 칸을 다르게 칠했다, 전수 리뷰 #60).
     판정은 /moveins/ 처럼 표시 정수 퍼센트로 한다: 부족 = 문턱(lo) 미만, 과잉 = 문턱(hi) 초과. */
  const ref=ADV.occupancy.ref[region], band=ADV.occupancy.band; if(!ref||!band) return '';
  const p=Math.round(v/ref*100);
  if(p>band.hi) return 'hi';
  if(p<band.lo) return 'lo';
  return '';
}
function occFut(p){
  const y=+p.slice(0,4), q=+p.slice(5);
  const now=new Date(), cy=now.getFullYear(), cq=Math.floor(now.getMonth()/3)+1;
  return y>cy || (y===cy && q>cq);
}
function occEst(row){ return row.e===1 || (row.e===undefined && occFut(row.p)); }
function renderAdvOcc(){
  const O=ADV.occupancy, regs=O.regions;
  let mx;
  if(TRANSP.occ){
    /* 추정 분기임을 색으로만 알리면 색각이상·스크린리더 사용자가 실적으로 읽는다.
       현재 분기가 이미 추정 구간이라 특히 그렇다(2026-08-08 감사). 글로도 붙인다. */
    mx=['<table class="adv"><caption class="sr-only">지역별 분기 입주물량. 별표(*)가 붙은 분기는 착공 실적으로 추정한 값입니다.</caption><thead><tr><th scope="col">지역</th>'+O.rows.map(r=>`<th scope="col"${occEst(r)?' style="color:#9a7000" title="착공 기준 추정"':''}>${r.p}${occEst(r)?'<abbr title="착공 기준 추정">*</abbr>':''}</th>`).join('')+'</tr></thead><tbody>'];
    regs.forEach((r,j)=>{
      mx.push(`<tr><td>${r}</td>`+O.rows.map(row=>{
        const cls=[occCls(r,row.v[j]),occEst(row)?'fut':''].filter(Boolean).join(' ');
        return `<td class="${cls}">${occFmt(row.v[j])}</td>`;
      }).join('')+'</tr>');
    });
  }else{
    mx=['<table class="adv"><thead><tr><th>분기</th>'+regs.map(r=>`<th>${r}</th>`).join('')+'</tr></thead><tbody>'];
    for(let i=O.rows.length-1;i>=0;i--){
      const row=O.rows[i];
      mx.push(`<tr class="${occEst(row)?'fut':''}"><th scope="row"${occEst(row)?' title="착공 기준 추정"':''}>${row.p}${occEst(row)?'<abbr title="착공 기준 추정">*</abbr>':''}</th>`+
        row.v.map((v,j)=>`<td class="${occCls(regs[j],v)}">${occFmt(v)}</td>`).join('')+'</tr>');
    }
  }
  mx.push('</tbody></table>');
  document.getElementById('adv-occ-matrix').innerHTML=mx.join('');
  const reg=advSel('adv-occ-reg',regs), ri=regs.indexOf(reg), ref=O.ref[reg];
  const rows=O.rows, ci=rows.findIndex(r=>occEst(r));
  const start=Math.max(0,(ci<0?rows.length:ci)-6), end=Math.min(rows.length,(ci<0?rows.length:ci)+6);
  const cp=['<table class="adv"><thead><tr><th>분기</th><th>'+reg+'</th></tr></thead><tbody>'];
  for(let i=end-1;i>=start;i--){
    const row=rows[i], v=row.v[ri];
    cp.push(`<tr class="${occEst(row)?'fut':''}"><th scope="row">${row.p}${occEst(row)?'<abbr title="착공 기준 추정">*</abbr>':''}</th><td class="${occCls(reg,v)}">${occFmt(v)}</td></tr>`);
  }
  cp.push('</tbody></table>');
  const b=null;   // 적정밴드 폐지(2026-08-07) — 기준선은 적정물량 하나
  document.getElementById('adv-occ-compact').innerHTML=cp.join('')+
    (b?`<div class="src-note" style="padding:8px 12px">적정밴드 ${advFmt(b[0])}~${advFmt(b[1])} · 아래면 공급부족, 위면 공급과잉</div>`:
       (ref?`<div class="src-note" style="padding:8px 12px">분기 수요 기준선 ${advFmt(ref)}</div>`:''));
}
function wkCell(v){
  if(v==null) return '<td>·</td>';
  const r=pvSign(v);
  const cls=r>0?'up':(r<0?'dn':'');
  return `<td class="${cls}">${pv2(v)}%</td>`;
}
/* --- 주간·월간 동향 (기본통계) — 표 + 막대 차트 공용 --- */
const TREND={
  week:{sel:'adv-week-reg',sel2:'adv-week-sgg',matrix:'adv-week-matrix',compact:'adv-week-compact',chart:'weekChart',col:'주간',lab:p=>p.slice(2),tick:l=>l.slice(3),periods:[['3개월',13],['1년',52],['3년',156],['전체',0]],map:'week-map',maplab:'week-maplab',unit:'전주 대비'},
  month:{sel:'adv-month-reg',sel2:'adv-month-sgg',matrix:'adv-month-matrix',compact:'adv-month-compact',chart:'monthChart',col:'월간',lab:p=>p,tick:l=>l.slice(2),periods:[['3개월',3],['1년',12],['3년',36],['전체',0]],map:'month-map',maplab:'month-maplab',unit:'전월 대비'}
};
/* --- 시도 타일 지도 (빨강=상승 · 파랑=하락, 진할수록 변동 큼) --- */
const SGG_QNAME={"a80703": "양주", "a80702": "동두천", "a80701": "포천", "a80603": "파주", "a80704": "의정부", "a80402": "구리", "a80401": "남양주", "a7010301": "서울 은평구", "a7010206": "서울 강북구", "a7010207": "서울 도봉구", "a7010208": "서울 노원구", "a7010302": "서울 서대문구", "a7010101": "서울 종로구", "a7010205": "서울 성북구", "a7010203": "서울 동대문구", "a7010204": "서울 중랑구", "a7010303": "서울 마포구", "a7010102": "서울 중구", "a7010103": "서울 용산구", "a7010201": "서울 성동구", "a7010202": "서울 광진구", "a7020102": "서울 강서구", "a7020101": "서울 양천구", "a7020105": "서울 영등포구", "a7020106": "서울 동작구", "a7020202": "서울 강남구", "a7020203": "서울 송파구", "a7020204": "서울 강동구", "a7020103": "서울 구로구", "a7020104": "서울 금천구", "a7020107": "서울 관악구", "a7020201": "서울 서초구", "a80403": "하남", "a80404": "광주", "a80601": "김포", "a908": "인천 검단구", "a909": "인천 서해구", "a907": "인천 계양구", "a902": "인천 영종구", "a906": "인천 부평구", "a901": "인천 제물포구", "a903": "인천 미추홀구", "a905": "인천 남동구", "a904": "인천 연수구", "a80303": "시흥", "a80304": "광명", "a80101": "과천", "a80105": "의왕", "a80104": "군포", "a80501": "이천", "a80502": "여주", "a80306": "오산", "a80201": "안성", "a80307": "평택", "c106": "속초", "c101": "춘천", "c103": "강릉", "c102": "원주", "c104": "동해", "c105": "태백", "c107": "삼척", "c313": "당진", "c306": "아산", "c206": "음성", "c203": "충주", "c204": "제천", "c307": "서산", "c312": "예산", "c302": "천안 동남구", "c303": "천안 서북구", "c20103": "청주 흥덕구", "c20104": "청주 청원구", "c311": "홍성", "c304": "공주", "b6": "세종", "c20101": "청주 상당구", "c20102": "청주 서원구", "c305": "보령", "c309": "계룡", "b404": "대전 유성구", "b405": "대전 대덕구", "c308": "논산", "b403": "대전 서구", "b402": "대전 중구", "b401": "대전 동구", "c404": "군산", "c405": "익산", "c402": "전주 완산구", "c403": "전주 덕진구", "c408": "김제", "c406": "정읍", "c407": "남원", "c606": "영주", "c609": "문경", "c605": "안동", "c60302": "포항 북구", "c608": "상주", "c602": "구미", "c611": "칠곡", "c60301": "포항 남구", "c604": "김천", "c610": "경산", "c607": "영천", "c601": "경주", "b304": "광주 북구", "b305": "광주 광산구", "b302": "광주 서구", "b301": "광주 동구", "b303": "광주 남구", "b205": "대구 북구", "b202": "대구 동구", "b203": "대구 서구", "b201": "대구 중구", "b206": "대구 수성구", "b208": "대구 달성군", "b207": "대구 달서구", "b204": "대구 남구", "b504": "울산 북구", "b501": "울산 중구", "b503": "울산 동구", "b505": "울산 울주군", "b502": "울산 남구", "c504": "나주", "c503": "순천", "c505": "광양", "c506": "무안", "c501": "목포", "c502": "여수", "c707": "밀양", "c709": "양산", "c70101": "창원 의창구", "c70102": "창원 성산구", "c706": "김해", "c70104": "창원 마산회원구", "c70103": "창원 마산합포구", "c702": "창원 진해구", "c703": "진주", "c705": "사천", "c704": "통영", "c708": "거제", "b10301": "부산 북구", "b10202": "부산 금정구", "b10204": "부산 기장군", "b10302": "부산 강서구", "b10303": "부산 사상구", "b10203": "부산 동래구", "b10201": "부산 해운대구", "b10304": "부산 사하구", "b10105": "부산 부산진구", "b10107": "부산 연제구", "b10108": "부산 수영구", "b10102": "부산 서구", "b10101": "부산 중구", "b10106": "부산 남구", "b10103": "부산 동구", "b10104": "부산 영도구", "c801": "제주", "c802": "서귀포", "a802031": "수원 장안구", "a802032": "수원 권선구", "a802033": "수원 팔달구", "a802034": "수원 영통구", "a801031": "성남 수정구", "a801032": "성남 중원구", "a801033": "성남 분당구", "a802021": "용인 처인구", "a802022": "용인 기흥구", "a802023": "용인 수지구", "a801021": "안양 만안구", "a801022": "안양 동안구", "a806021": "고양 덕양구", "a806022": "고양 일산동구", "a806023": "고양 일산서구", "a803011": "부천 원미구", "a803012": "부천 소사구", "a803013": "부천 오정구", "a803021": "안산 상록구", "a803022": "안산 단원구", "a803051": "화성 동탄구", "a803052": "화성 만세구", "a803053": "화성 병점구", "a803054": "화성 효행구"};
/* 기준일 배너 — 지도 위 유일한 메타 표기(옛 map-lab 텍스트 줄은 중복이라 제거,
   사용자 선택으로 배너 쪽을 살림). sggOnly=시군구 지도만 이 주차일 때. */
function mapDateChip(p,unit,sggOnly){
  return '<div class="map-datechip"><span>📅 '+(sggOnly?'시군구 ':'')+'기준일 '+p+' · '+unit+'</span></div>';
}
function sggRanks(S,row,met){
  const arr=[];
  const src=row[met]||[];
  S.codes.forEach((c,i)=>{
    if(SGG_QNAME[c]&&src[i]!=null)arr.push([c,src[i]]);
  });
  arr.sort((a,b)=>b[1]-a[1]);
  const rk={};
  arr.forEach(([c],i)=>rk[c]=i+1);
  return {order:arr,rk};
}
/* TOP10 정렬 기준 — 지도별로 매매/전세/월세 중 하나. 방향은 박스가 정한다
   (상승 박스=내림차순, 하락 박스=오름차순). 헤더를 누르면 기준만 바뀐다. */
const RANKMET={week:'ma',month:'ma'};
function setRankMet(k,met){ RANKMET[k]=met; drawNationMap(k); }
function rankTables(S,unit,k){
  const rows=S.rows, cur=rows[rows.length-1];
  const prev=rows.length>1?rows[rows.length-2]:null;
  const hasWo=Array.isArray(cur.wo);
  let met=RANKMET[k]||'ma';
  if(met==='wo'&&!hasWo)met='ma';        // 주간엔 월세가 없다
  const MLAB={ma:'매매',je:'전세',wo:'월세'};
  const cr=sggRanks(S,cur,met), pr=prev?sggRanks(S,prev,met).rk:null;
  const val={};
  ['ma','je','wo'].forEach(m=>{ val[m]={}; S.codes.forEach((c,i)=>{ val[m][c]=(cur[m]||[])[i]; }); });
  function dcell(c){
    if(!pr||!(c in pr))return '<span class="rk-new">NEW</span>';
    const d=pr[c]-cr.rk[c];
    if(d>0)return '<span class="rk-up">▲'+d+'위</span>';
    if(d<0)return '<span class="rk-dn">▼'+(-d)+'위</span>';
    return '<span class="rk-same">–</span>';
  }
  function vcell(c,m){
    const v=val[m][c];
    const r=pvSign(v);
    const cls=(r>0?'up':(r<0?'dn':''))+(m===met?' sortcol':'');
    return '<td class="'+cls.trim()+'">'+(v==null?'·':pv2(v)+'%')+'</td>';
  }
  const cols=hasWo?['ma','je','wo']:['ma','je'];
  function tbl(title,items,base){
    const th=cols.map(m=>'<th class="rk-sort'+(m===met?' on':'')+'" role="button" tabindex="0" data-k="'+k+'" data-met="'+m+'" title="'+MLAB[m]+' 기준으로 정렬">'+MLAB[m]+'</th>').join('');
    const h=['<div class="rank-box"><div class="rank-h">'+title+'</div><div class="rank-wrap"><table class="rank-tbl'+(hasWo?' wide':'')+'">',
      '<thead><tr><th>순위</th><th>지역</th>'+th+'<th>'+unit+'</th></tr></thead><tbody>'];
    items.forEach(([c,v],i)=>{
      const rank=base+i;
      const medal=rank<=3?'<span class="rk-medal">'+['🥇','🥈','🥉'][rank-1]+'</span>':'';
      h.push('<tr><td>'+medal+rank+'</td><td><a class="rk-go" href="#stats-market-'+k+'~'+c+'" data-code="'+c+'">'+SGG_QNAME[c]+'</a></td>'+
        cols.map(m=>vcell(c,m)).join('')+'<td>'+dcell(c)+'</td></tr>');
    });
    h.push('</tbody></table></div></div>');
    return h.join('');
  }
  const basis='<span style="font-weight:600;color:var(--muted);font-size:11px">'+MLAB[met]+' 기준</span>';
  return '<div class="map-rank">'+
    tbl('<span style="color:#e0564a">▲</span> 상승 TOP 10 '+basis,cr.order.slice(0,10),1)+
    tbl('<span style="color:#3a7bd5">▼</span> 하락 TOP 10 '+basis,cr.order.slice(-10).reverse(),1)+
    '</div>';
}
/* 지도 '옆으로 밀어 전체 보기' 안내 — 상자가 지도보다 좁을 때만. 숨은 상태(폭 0)에서는 판정하지 않고, 보일 때
   (setMarketTab·gtSet(…,'m')) 다시 판정한다. 예전엔 그릴 때 한 번만 재서, 숨은 채 그려진 월간 지도는 375px 에서 넘치는데도
   안내가 꺼진 채 굳었다(전수리뷰 #54). */
function syncSwipe(k){
  const T=TREND[k], m=T&&T.map&&document.getElementById(T.map); if(!m)return;
  const box=m.querySelector('.map-scroll'), sw=m.querySelector('.map-swipe');
  if(!box||!sw||!box.clientWidth)return;
  sw.hidden=!(box.scrollWidth>box.clientWidth+1);
}
function drawNationMap(k){
  const T=TREND[k], D=trendData(k), S=D.sgg; if(!S||!S.rows.length)return;
  const row=S.rows[S.rows.length-1];
  const vma={},vje={},vwo={};
  S.codes.forEach((c,i)=>{vma[c]=row.ma[i];vje[c]=row.je[i];vwo[c]=(row.wo||[])[i];});
  /* 월세는 월간 원천에만 있다 — 부동산원 주간조사는 매매·전세만(R-ONE 주간표 8종 전부).
     그래서 주간 지도는 2단, 월간 지도는 3단으로 자동 분기한다. */
  const hasWo=Array.isArray(row.wo);
  // 시군구 지도(KOSIS 등)의 기준일이 시도·서울 지표(R-ONE 최신)보다 뒤처질 때가 있어
  // (예: 주간 시군구는 시도보다 수일 늦음) 오해 없게 두 날짜를 함께 표기한다.
  const natP=(D.rows&&D.rows.length)?D.rows[D.rows.length-1].p:row.p;
  const gap=natP!==row.p;
  const SER=hasWo?'매매·전세·월세':'매매·전세';
  const ref=k==='week'?WK_MAP_REF:MO_MAP_REF;   // 만색 기준은 홈 지도 시세 모드(주간·월간)·히어로 배경과 한 값
  /* 그림은 홈 주간 구역과 같은 sggMapSvg(home-app.js). 칸을 누르면 그 지역 그래프(openTrendRegion). */
  const svg=sggMapSvg(hasWo?[vma,vje,vwo]:[vma,vje],{ref:ref,names:['매매','전세','월세'],href:c=>'#stats-market-'+k+'~'+c});
  const box=document.getElementById(T.map);
  box.innerHTML=
    mapDateChip(row.p,SER+' · '+T.unit,gap)+
    rankTables(S,T.unit,k)+
    '<div class="map-scroll">'+svg+'</div>'+
    '<div class="map-suplegend">타일 값: '+(hasWo?'위 = 매매 · 가운데 = 전세 · 아래 = 월세':'위 = 매매 · 아래 = 전세')+
    ' · 지역을 누르면 그래프<span class="map-swipe" hidden> · 옆으로 밀어 전체 보기</span></div>';
  /* 상자가 지도보다 좁을 때만 민다는 안내를 켠다(데스크톱에서는 안 넘친다). */
  syncSwipe(k);
  /* TOP10 헤더 정렬 — innerHTML 이후에 붙인다(인라인 onclick은 따옴표 중첩이 깨진다) */
  box.querySelectorAll('.rk-sort').forEach(th=>{
    const go=()=>setRankMet(th.dataset.k,th.dataset.met);
    th.addEventListener('click',go);
    th.addEventListener('keydown',e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();go();}});
  });
  /* 지도 칸·TOP 10 지역명 → 그 지역 그래프. 상자는 그대로 두고 안만 갈아 끼우므로 한 번만 붙인다. */
  if(!box.dataset.trLink){
    box.dataset.trLink='1';
    box.addEventListener('click',e=>onTrendLink(e,e.target.closest&&e.target.closest('.map-rank')?'rank':'stats_map'));
  }
}
/* --- 표 행열전환 --- */
let TRANSP={};
const TR_REDRAW={basicmain:()=>drawStat(),week:()=>renderTrendTables('week'),month:()=>renderTrendTables('month'),permit:()=>renderAdvPermits(),occ:()=>renderAdvOcc()};
function trFlip(sec,btn){
  TRANSP[sec]=!TRANSP[sec];
  btn.classList.toggle('on',!!TRANSP[sec]);
  TR_REDRAW[sec]();
  track('stats_transpose',{section:sec,on:!!TRANSP[sec]});
}
function drawTrendMap(k){
  const T=TREND[k], W=trendData(k); if(!W)return;
  if(W.sgg&&W.sgg.rows.length){drawNationMap(k);return;}
  document.getElementById(T.map).innerHTML='<div class="src-note" style="padding:14px">지도 데이터 수집 대기중</div>';
}
function trendData(k){ return k==='week'?ADV.weekly:ADV.monthly; }
/* ── 시도 → 시군구 2단 선택 ─────────────────────────────────────────
   부동산원 앱처럼 시도를 고르면 그 아래 '전체 + 시군구'가 뜬다.
   시군구 시계열은 12구간만 저장하므로(용량) 그래프는 그만큼만 그리고
   기간 탭을 숨긴다 — 표(최근 12개 표시)는 영향 없다. */
const SIDO_PREFIX={a7:'서울',a8:'경기',a9:'인천',b1:'부산',b2:'대구',b3:'광주',b4:'대전',
  b5:'울산',b6:'세종',c1:'강원',c2:'충북',c3:'충남',c4:'전북',c5:'전남',c6:'경북',c7:'경남',c8:'제주'};
function sidoOf(code){
  if(code[0]==='a'){
    if(code==='a0')return null;
    if(code.indexOf('a7')===0)return '서울';
    if(code.indexOf('a8')===0)return '경기';
    return '인천';
  }
  return SIDO_PREFIX[code.slice(0,2)]||null;
}
function sggOfSido(W,sido){
  const S=W.sgg; if(!S)return [];
  /* ⚠️ 값이 하나도 없는 시군구는 세우지 않는다. 인천 신설 4구(제물포·영종·검단·서해)는
     주간표에는 있고 **월간표에는 아직 없어**, 고르면 영원히 빈 그래프가 나오는
     죽은 선택지였다(2026-08-08 감사). 원천이 생기면 자동으로 다시 나타난다. */
  const has=c=>{const i=S.codes.indexOf(c);
    return i>=0&&(S.rows||[]).some(r=>['ma','je','wo'].some(f=>(r[f]||[])[i]!=null));};
  return S.codes.filter(c=>SGG_QNAME[c]&&sggZoneOf(W,c)===sido&&has(c));
}
/* 시군구 코드 → 이 목록(W.regions, 판정 단위)의 지역 이름. 원천 이름(sidoOf)이 목록에 없으면 그 이름을 품은 판정 단위로
   접는다(홈 지도 zoneOf 와 같은 규칙 — 통합 이름을 박지 않는다). 광주·전남 시군구는 '전남광주'로 간다 — 예전엔 원천
   이름끼리만 비교해 전남광주를 고르면 0곳, 광주 5구·전남 6시는 고를 길이 없었다(전수리뷰 #104). 파이썬 거울:
   weekly_moves.sgg_zone(test_home_stats_runtime 이 node 로 대조). */
function sggZoneOf(W,code){
  const s=sidoOf(code); if(!s)return null;
  const R=W.regions||[];
  if(R.indexOf(s)>=0)return s;
  return R.find(k=>k.indexOf(s)>=0)||s;
}
/* 시도 select가 바뀌면 하위 목록을 다시 채우고 '전체'로 되돌린다 */
function onTrendReg(k){
  const T=TREND[k], W=trendData(k); if(!W)return;
  trOpenDrop(k);
  TRSHOW[k]=12;                     // 지역이 바뀌면 표는 기본 개수로
  fillSggSel(k,'');
  (k==='week'?renderWeekSec:renderMonthSec)();
}
function fillSggSel(k,keep){
  const T=TREND[k], W=trendData(k);
  const sub=document.getElementById(T.sel2); if(!sub||!W)return;
  const sido=document.getElementById(T.sel).value;
  const list=sggOfSido(W,sido);
  if(!list.length){ sub.hidden=true; sub.innerHTML=''; return; }
  sub.hidden=false;
  sub.innerHTML='<option value="">'+sido+' 전체</option>'+
    regSort(list,c=>SGG_QNAME[c]||c).map(c=>'<option value="'+c+'">'+SGG_QNAME[c]+'</option>').join('');
  if(keep&&list.indexOf(keep)>=0)sub.value=keep;
}
/* 표·그래프가 함께 쓰는 '현재 선택' — 시도면 W.rows, 시군구면 W.sgg.rows */
/* 시장동향 시도 select — 맨 앞에 '전체'(값 '')를 둔다. 인허가·입주물량이 쓰는
   advSel()은 '전체' 개념이 없으므로 공유하지 않고 여기서만 채운다. */
function fillTrendReg(k,regs){
  const s=document.getElementById(TREND[k].sel); if(!s)return '';
  if(!s.options.length){
    s.innerHTML='<option value="">전체 지역</option>'+
      regSort(regs).map(r=>'<option value="'+r+'">'+r+'</option>').join('');
  }
  return s.value;
}
function trendPick(k){
  const T=TREND[k], W=trendData(k);
  const sv=fillTrendReg(k,W.regions);
  const reg=sv||(W.regions.indexOf('전국')>=0?'전국':W.regions[0]);
  const sub=document.getElementById(T.sel2);
  if(sub&&!sub.hidden&&sub.value&&W.sgg){
    const ci=W.sgg.codes.indexOf(sub.value);
    if(ci>=0)return {name:SGG_QNAME[sub.value]||sub.value,rows:W.sgg.rows,idx:ci,isSgg:true};
  }
  return {name:reg,rows:W.rows,idx:W.regions.indexOf(reg),isSgg:false};
}
/* 지도 칸·TOP 10 지역명에서 고른 지역의 그래프(홈 주간 구역·통계 지도·/weekly/ 머리 지도 → '#stats-market-week~코드',
   applyHash). 새 화면을 만들지 않고 이 구역의 지역 선택·그래프 보기를 그대로 맞춘다 — 시도 칸(서울·경기 등 진한 칸)은 그
   시도, 시군구 칸은 그 시군구, 전국 칸은 전국. 코드가 없으면(뒤로 가기로 '~코드' 없는 주소에 왔을 때) 이 함수가 연 그래프만
   지도로 되돌린다. 사람이 지역을 바꾸거나 '지도'를 누르면 주소의 '~코드'를 걷는다(trOpenDrop — 주소와 화면이 다른 말을
   하지 않게). */
/* TR_OPEN(주기별로 이 함수가 연 그래프의 코드)은 home-app.js 에 있다 — 통계 해시(statsHashOf)가 '~코드'를 싣는다(전수리뷰 A3). */
function trendTarget(W,code){
  const s=sidoOf(code);
  if(!s)return {zone:'',sgg:''};   // 전국(a0)·모르는 코드 → 전체
  const z=sggZoneOf(W,code), zone=(W.regions||[]).indexOf(z)>=0?z:'';
  /* 시군구 목록(sggOfSido — 값이 있는 곳만)에 없는 칸(구를 가진 시의 머리 칸 천안·청주 등, 값 없는 신설 구)은 그 시도로 */
  return {zone:zone,sgg:(code.length>2&&zone&&sggOfSido(W,zone).indexOf(code)>=0)?code:''};
}
function openTrendRegion(k,code,view){
  if(!TREND[k])return;
  return (TREND_P||loadFullData()).then(()=>{
    const T=TREND[k], W=trendData(k); if(!W||!W.regions)return;
    /* 되돌릴 때는 보기만이 아니라 지역 선택도 '전체'로 — 남겨 두면 다음에 '그래프'·'표'를 누를 때 예전 지역이 나온다 */
    if(!code){ if(TR_OPEN[k]){ TR_OPEN[k]=null; document.getElementById(T.sel).value=''; fillSggSel(k,''); TRSHOW[k]=12;
      (k==='week'?renderWeekSec:renderMonthSec)(); gtSet(k,'m',true); } return; }
    const t=trendTarget(W,code);
    fillTrendReg(k,W.regions);
    document.getElementById(T.sel).value=t.zone;
    fillSggSel(k,t.sgg);
    TR_OPEN[k]=code;
    TRSHOW[k]=12;
    const render=k==='week'?renderWeekSec:renderMonthSec;
    render();
    gtSet(k,view==='t'?'t':'g',true);   // 홈 지도 시세 모드의 '표' 단추는 표로 연다('~코드-t')
    if(t.sgg&&!SGG_HIST_READY)ensureSggHist().then(render).catch(()=>{});
    afterLayout(()=>{ const el=document.getElementById('sec-'+k); if(el)el.scrollIntoView(); });
  }).catch(()=>{});
}
function trOpenDrop(k){
  if(!TR_OPEN[k])return;
  TR_OPEN[k]=null;
  if(location.hash.indexOf('~')>=0)statsNav('#stats-market-'+k,true);
}
/* 표 표시 개수 — 기본 12개, '더보기'로 12씩 늘린다. 시군구를 고른 상태면
   전체 시계열(data-sgg.json)이 필요하므로 먼저 받아온 뒤 늘린다. */
const TRSHOW={week:12,month:12};
function trMore(k){
  const P=trendPick(k);
  const grow=()=>{ TRSHOW[k]+=12; (k==='week'?renderWeekSec:renderMonthSec)(); };
  if(P.isSgg&&!SGG_HIST_READY){ ensureSggHist().then(grow).catch(grow); return; }
  grow();
}
function renderTrendTables(k){
  const T=TREND[k], W=trendData(k);
  if(!W){document.getElementById(T.matrix).innerHTML='<div class="src-note" style="padding:14px">데이터 수집 대기중</div>';return;}
  const regs=W.regions;
  const LIM=TRSHOW[k]||12;
  const R=W.rows.slice(-LIM);   // 기본 12개, '더보기'로 확장
  // 월세는 월간에만 있다(주간 원천엔 없음). 행이 wo를 가질 때만 3행 구성.
  const hasWo=R.length>0&&Array.isArray(R[R.length-1].wo);
  const nSub=hasWo?3:2;
  let mx;
  if(TRANSP[k]){
    mx=['<table class="adv"><thead><tr><th>지역</th><th></th>'+R.map(r=>`<th>${T.lab(r.p)}</th>`).join('')+'</tr></thead><tbody>'];
    regs.forEach((r,ri)=>{
      mx.push(`<tr><td rowspan="${nSub}">${r}</td><td style="position:static;text-align:left;color:var(--muted);font-weight:600">매매</td>`+R.map(row=>wkCell(row.ma[ri])).join('')+'</tr>');
      mx.push(`<tr><td style="position:static;text-align:left;color:var(--muted);font-weight:600">전세</td>`+R.map(row=>wkCell(row.je[ri])).join('')+'</tr>');
      if(hasWo)mx.push(`<tr><td style="position:static;text-align:left;color:var(--muted);font-weight:600">월세</td>`+R.map(row=>wkCell((row.wo||[])[ri])).join('')+'</tr>');
    });
  }else{
    mx=['<table class="adv"><thead><tr><th>'+T.col+'</th><th></th>'+regs.map(r=>`<th>${r}</th>`).join('')+'</tr></thead><tbody>'];
    for(let i=R.length-1;i>=0;i--){
      const row=R[i], label=T.lab(row.p);
      mx.push(`<tr><td rowspan="${nSub}">${label}</td><td style="position:static;text-align:left;color:var(--muted);font-weight:600">매매</td>`+row.ma.map(wkCell).join('')+'</tr>');
      mx.push(`<tr><td style="position:static;text-align:left;color:var(--muted);font-weight:600">전세</td>`+row.je.map(wkCell).join('')+'</tr>');
      if(hasWo)mx.push(`<tr><td style="position:static;text-align:left;color:var(--muted);font-weight:600">월세</td>`+(row.wo||[]).map(wkCell).join('')+'</tr>');
    }
  }
  mx.push('</tbody></table>');
  if(W.rows.length>R.length)mx.push('<button type="button" class="tr-more" data-more="'+k+'">'+
    '이전 '+Math.min(12,W.rows.length-R.length)+'개 더보기</button>');
  document.getElementById(T.matrix).innerHTML=mx.join('');
  fillTrendReg(k,regs);
  fillSggSel(k,(document.getElementById(T.sel2)||{}).value);
  /* 아무것도 안 고른 상태(''):  전 지역 매트릭스.  1·2차를 고르면 그 지역만.
     PC 표 모드에서 시군구는 매트릭스에 아예 없어 첫 화면만으로는 볼 수 없었다
     (2026-08-01 사용자 지적). 단일 지역 표는 compact가 이미 그리므로 그걸 쓴다. */
  const secEl=document.getElementById(T.matrix).closest('.gsec');
  if(secEl)secEl.classList.toggle('sel-one',!!document.getElementById(T.sel).value);
  const P=trendPick(k), ri=P.idx;
  const CR=P.rows.slice(-LIM);
  const cp=['<table class="adv"><thead><tr><th>'+T.col+'</th><th>매매</th><th>전세</th>'+(hasWo?'<th>월세</th>':'')+'</tr></thead><tbody>'];
  for(let i=CR.length-1;i>=0;i--){
    const row=CR[i];
    cp.push(`<tr><td>${T.lab(row.p)}</td>`+wkCell(row.ma[ri])+wkCell(row.je[ri])+(hasWo?wkCell((row.wo||[])[ri]):'')+'</tr>');
  }
  cp.push('</tbody></table>');
  /* 더 볼 게 남았을 때만 버튼을 낸다. 시군구는 아직 12구간뿐이어도 눌러서
     전체를 받아올 수 있으므로(지연 로드) 버튼을 함께 보여준다. */
  const totalAvail=P.isSgg&&!SGG_HIST_READY?Infinity:P.rows.length;
  const rest=totalAvail-CR.length;
  if(rest>0)cp.push('<button type="button" class="tr-more" data-more="'+k+'">'+
    '이전 '+(isFinite(rest)?Math.min(12,rest):12)+'개 더보기</button>');
  document.getElementById(T.compact).innerHTML=cp.join('');
  /* 더보기 바인딩 — 인라인 onclick은 문자열 안 따옴표가 깨져 data 속성으로 위임 */
  [T.matrix,T.compact].forEach(id=>{
    const b=document.getElementById(id).querySelector('.tr-more');
    if(b)b.addEventListener('click',()=>trMore(b.dataset.more));
  });
}
let GCH={};
function areaGrad(color,topHex){
  topHex=topHex||'38';
  return function(ctx){
    const ch=ctx.chart, area=ch.chartArea;
    if(!area) return color+'00';
    const g=ch.ctx.createLinearGradient(0,area.top,0,area.bottom);
    g.addColorStop(0,color+topHex); g.addColorStop(1,color+'00');
    return g;
  };
}
function mkChart(id,cfg){ if(GCH[id])GCH[id].destroy(); return GCH[id]=new Chart(document.getElementById(id),cfg); }
// 가로 스크롤 추이 차트의 y축을 왼쪽에 고정 복제 (스크롤해도 항상 보이게)
const TRP={week:1,month:1};
/* 월간 다음 발표 — 이번 달 발표일(15일을 영업일로 민 날)을 먼저 구하고, 그날 12시(공표)가 지났을 때만 다음 달로 넘긴다.
   예전엔 달력상 15일로 '지났다'를 판정해, 15일이 주말·휴일로 밀린 달에는 16일~밀린 발표일 사이에 벌써 다음 달 날짜를
   보였다(2026-08-15 토·광복절 → 8/18, 전수리뷰 #55). */
function _next15(now){
  const k=_kst(now), d=new Date(k.day*_DAY);
  let y=d.getUTCFullYear(),m=d.getUTCMonth();
  let r=_bizDay(Date.UTC(y,m,15)/_DAY);
  if(k.day>r||(k.day===r&&k.hour>=12)){ m++; if(m>11){m=0;y++;} r=_bizDay(Date.UTC(y,m,15)/_DAY); }
  return r;
}
function _fmtRel(n){
  const d=new Date(n*_DAY);
  return (d.getUTCMonth()+1)+'월 '+d.getUTCDate()+'일('+'일월화수목금토'[d.getUTCDay()]+')';
}
function renderReleaseInfo(){
  _syncHolidays();
  const w=document.getElementById('rel-week'), r=weeklyReleaseNow();
  const nx=r?wkNextText(r):'';   // 연휴 주는 빈 문자열(wkNextText) — 꼬리 ' · '를 남기지 않는다
  if(w)w.textContent='한국부동산원 · 매주 목요일 발표'+(nx?' · '+nx:'');
  const m=document.getElementById('rel-month');
  if(m)m.textContent='한국부동산원 · 매월 15일 발표 · 다음 '+_fmtRel(_next15(new Date()));
}   /* 기본: 주간 1년 · 월간 3년 */
function renderTrPeriods(k){
  const T=TREND[k], el=document.getElementById(k+'-period'); if(!el||!T.periods)return;
  const W=trendData(k), have=W&&W.rows?W.rows.length:0;
  const cur=T.periods[TRP[k]];
  if(!cur||(cur[1]>0&&cur[1]>have))TRP[k]=T.periods.length-1;   // 감춰진 칸이 선택돼 있으면 '전체'로
  el.innerHTML=T.periods.map((p,i)=>
    (p[1]>0&&have<p[1]*0.95)?'':
    '<button type="button" class="'+(TRP[k]===i?'on':'')+'" onclick="trSetPeriod(&#39;'+k+'&#39;,'+i+')">'
    +p[0]+'</button>').join('');
}
function trSetPeriod(k,i){
  TRP[k]=i; renderTrPeriods(k); drawTrendChart(k);
  track('stats_period',{section:k,period:TREND[k].periods[i][0]});
}
function drawTrendChart(k){
  if(needChart(()=>drawTrendChart(k)))return;
  const T=TREND[k], W=trendData(k); if(!W)return;
  advSel(T.sel,W.regions);
  fillSggSel(k,(document.getElementById(T.sel2)||{}).value);
  const P=trendPick(k), ri=P.idx;
  renderTrPeriods(k);
  /* 시군구 전체 시계열이 아직 안 왔으면(12구간) 기간 선택이 의미 없어 탭을 감춘다.
     data-sgg.json이 도착하면 시도와 똑같이 기간 탭이 살아난다. */
  const shortSgg=P.isSgg&&P.rows.length<=12;
  const pel=document.getElementById(k+'-period');
  if(pel)pel.style.display=shortSgg?'none':'';
  const cnt=(T.periods&&T.periods[TRP[k]])?T.periods[TRP[k]][1]:0;
  const rows=shortSgg?P.rows:(cnt>0?P.rows.slice(-cnt):P.rows);
  const n=rows.length;
  /* '전체'가 실제로 어디부터인지 밝힌다 — 라벨만으로는 알 수 없다 */
  const uel=document.getElementById(k+'-unit');
  if(uel&&n)uel.textContent='변동률(%) · '+T.lab(rows[0].p)+' ~ '+T.lab(rows[n-1].p);
  /* 월세는 월간에만 있다. 면적 3겹은 서로를 가려 선만 그린다(fill 없음). */
  const dsets=[
    {label:'매매',data:rows.map(r=>r.ma[ri]),borderColor:'#e0564a',backgroundColor:areaGrad('#e0564a','1a'),fill:'origin',
      borderWidth:2,pointRadius:n>40?0:3,pointHoverRadius:5,tension:.18,spanGaps:true},
    {label:'전세',data:rows.map(r=>r.je[ri]),borderColor:'#a98be0',backgroundColor:areaGrad('#a98be0','1a'),fill:'origin',
      borderWidth:2,pointRadius:n>40?0:3,pointHoverRadius:5,tension:.18,spanGaps:true}];
  if(n&&Array.isArray(rows[n-1].wo))dsets.push(
    {label:'월세',data:rows.map(r=>(r.wo||[])[ri]),borderColor:'#1f8a70',fill:false,
      borderWidth:2,pointRadius:n>40?0:3,pointHoverRadius:5,tension:.18,spanGaps:true});
  const chart=mkChart(T.chart,{type:'line',
    data:{labels:rows.map(r=>T.lab(r.p)),datasets:dsets},
    options:{responsive:true,maintainAspectRatio:false,animation:false,interaction:{mode:'index',intersect:false},
      plugins:{legend:{display:false},
        tooltip:{callbacks:{label:c=>`${c.dataset.label}: ${c.raw==null?'-':pv2(Number(c.raw))}%`}}},
      scales:{x:{grid:{display:false},ticks:{maxRotation:45,minRotation:45,autoSkip:true,
          maxTicksLimit:Math.max(8,Math.ceil(n/5)),font:{size:10},
          /* 축은 짧게(04-06), 정확한 날짜는 툴팁이 책임진다 */
          callback:function(v){const l=this.getLabelForValue(v);return T.tick?T.tick(l):l;}}},
        y:{grid:{color:c=>c.tick.value===0?INK:GRID,lineWidth:c=>c.tick.value===0?1.2:1},
          ticks:{callback:v=>String(+Number(v).toFixed(3)),maxTicksLimit:6,padding:2,font:{size:10}},title:{display:false}}}}});
}
function renderWeekSec(){ renderTrendTables('week'); drawTrendChart('week'); drawTrendMap('week'); }
function renderMonthSec(){ renderTrendTables('month'); drawTrendChart('month'); drawTrendMap('month'); }
/* --- 투자지표 차트 --- */
function drawPermitChart(){
  if(needChart(()=>drawPermitChart()))return;
  const P=ADV.permits, regs=P.regions;
  const reg=advSel('adv-permit-reg',regs), ri=regs.indexOf(reg), ref=P.ref[reg];
  const vals=P.rows.map(r=>r.v[ri]);
  const cols=vals.map(v=>{const c=permitCls(reg,v);return c==='hi'?'#3a7bd5':(c==='lo'?'#e0564a':'#c0cbc5');});
  mkChart('permitChart',{type:'bar',
    data:{labels:P.rows.map(r=>r.p.replace('H1',' 상').replace('H2',' 하')),
      datasets:[{label:'아파트 인허가',data:vals,backgroundColor:cols}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${advFmt(c.raw)} 호`}}},
      scales:{x:{grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:10}},
        y:{grid:{color:GRID},title:{display:true,text:'호 (반기)'}}}},
    plugins:[{id:'permitRef',afterDraw(ch){
      if(!ref)return;
      const ctx=ch.ctx,xa=ch.scales.x,ya=ch.scales.y;
      [[ref[0]/2,'#3a7bd5','과거 저점 ½'],[ref[1]/2,'#e0564a','과거 고점 ½']].forEach(([v,c,t])=>{
        if(v<ya.min||v>ya.max)return;
        const y=ya.getPixelForValue(v);
        ctx.save();ctx.strokeStyle=c;ctx.setLineDash([5,4]);ctx.lineWidth=1.5;
        ctx.beginPath();ctx.moveTo(xa.left,y);ctx.lineTo(xa.right,y);ctx.stroke();
        ctx.setLineDash([]);ctx.fillStyle=c;ctx.font='700 10px '+FONT;ctx.textAlign='right';
        ctx.fillText(t,xa.right-4,y-4);ctx.restore();
      });
    }}]});
}
function drawOccChart(){
  if(needChart(()=>drawOccChart()))return;
  const O=ADV.occupancy, regs=O.regions;
  const reg=advSel('adv-occ-reg',regs), ri=regs.indexOf(reg), ref=O.ref[reg];
  const vals=O.rows.map(r=>r.v[ri]);
  const cols=O.rows.map((r,i)=>{
    if(occEst(r))return '#e8ce7a';
    const c=occCls(reg,vals[i]);
    return c==='hi'?'#3a7bd5':(c==='lo'?'#e0564a':'#c0cbc5');
  });
  mkChart('occChart',{type:'bar',
    data:{labels:O.rows.map(r=>r.p),datasets:[{label:'입주물량',data:vals,backgroundColor:cols}]},
    options:{responsive:true,maintainAspectRatio:false,
      plugins:{legend:{display:false},tooltip:{callbacks:{label:c=>`${occFmt(c.raw)} 호`}}},
      scales:{x:{grid:{display:false},ticks:{maxRotation:0,autoSkip:true,maxTicksLimit:10}},
        y:{grid:{color:GRID},title:{display:true,text:'호 (분기)'}}}},
    plugins:[{id:'occRef',afterDraw(ch){
      const b=null;   // 적정밴드 폐지(2026-08-07) — 기준선은 적정물량 하나
      const ctx=ch.ctx,xa=ch.scales.x,ya=ch.scales.y;
      const lines=b?[[b[0],'#3a7bd5','적정 하단'],[b[1],'#e0564a','적정 상단']]:(ref?[[ref,'#9a7000','수요 기준선']]:[]);
      lines.forEach(([v,c,t])=>{
        if(v<ya.min||v>ya.max)return;
        const y=ya.getPixelForValue(v);
        ctx.save();ctx.strokeStyle=c;ctx.setLineDash([5,4]);ctx.lineWidth=1.5;
        ctx.beginPath();ctx.moveTo(xa.left,y);ctx.lineTo(xa.right,y);ctx.stroke();
        ctx.setLineDash([]);ctx.fillStyle=c;ctx.font='700 10px '+FONT;ctx.textAlign='right';
        ctx.fillText(t,xa.right-4,y-4);ctx.restore();
      });
    }}]});
}
function renderPermitSec(){ renderAdvPermits(); drawPermitChart(); }
function renderOccSec(){ renderAdvOcc(); drawOccChart(); }
/* --- 그래프/표 토글 & 투자지표 탭 --- */
function gtSet(sec,v,silent){
  const el=document.getElementById('sec-'+sec);
  el.classList.toggle('gm-g',v==='g');
  el.classList.toggle('gm-t',v==='t');
  el.classList.toggle('gm-m',v==='m');
  el.querySelectorAll('.gt button[data-v]').forEach(b=>{b.classList.toggle('on',b.dataset.v===v);b.setAttribute('aria-pressed',b.dataset.v===v?'true':'false');});
  if(v==='g'){
    const box=document.getElementById(sec+'ChartBox');
    const ch=box&&window.Chart&&Chart.getChart(box.querySelector('canvas'));
    if(ch)ch.resize();   // display:none에서 생성된 차트는 표시 시 직접 리사이즈해야 canvas가 그려짐
  }
  if(v==='m'&&TREND[sec])syncSwipe(sec);
  if(silent)return;   // openTrendRegion 이 바꾼 것 — 사람이 누른 전환만 센다
  if(v==='m')trOpenDrop(sec);
  track('stats_gt',{section:sec,view:v});
}
function setAdvTab(t,push){
  if(!['occ','permit','bubble'].includes(t))t='occ';
  const changed=!document.getElementById('atab-'+t).classList.contains('on');
  ['occ','permit','bubble'].forEach(k=>{
    document.getElementById('sec-'+k).style.display=k===t?'':'none';
    document.getElementById('atab-'+k).classList.toggle('on',k===t);
    document.getElementById('atab-'+k).setAttribute('aria-selected',k===t?'true':'false');
  });
  if(t==='permit'&&advReady())drawPermitChart();
  if(t==='occ'&&advReady())drawOccChart();
  if(push!==false){ track('adv_tab',{tab:t}); statsNav('#stats-adv-'+t,!changed); }
}
function renderAdvAll(tab){ renderAdvPermits(); renderAdvOcc(); setAdvTab(tab||'occ',false); }
/* 시장동향 주간/월간 토글 — 숨김 상태에서 만들어진 차트는 표시 시 리사이즈 필요 */
function setMarketTab(t,push){
  if(!['week','month'].includes(t))t='week';
  const changed=!document.getElementById('mtab-'+t).classList.contains('on');
  ['week','month'].forEach(k=>{
    document.getElementById('sec-'+k).style.display=k===t?'':'none';
    document.getElementById('mtab-'+k).classList.toggle('on',k===t);
    document.getElementById('mtab-'+k).setAttribute('aria-selected',k===t?'true':'false');
  });
  const ch=window.Chart&&Chart.getChart&&Chart.getChart(t+'Chart');
  if(ch)ch.resize();
  syncSwipe(t);
  if(push!==false){ track('market_tab',{tab:t}); statsNav(statsHashOf('market'),!changed); }   // 연 지역('~코드')까지(A3)
}

/* ============ 시장 도구: 버블밴드 ============ */
/* role="button" 행 공용 키 핸들러 — Enter/Space를 클릭으로 위임한다.
   el.click()이 기존 onclick(bbToggle)을 그대로 태우므로
   aria-expanded 갱신 경로가 마우스와 키보드에서 갈라지지 않는다.
   preventDefault는 Space의 페이지 스크롤을 막기 위해 필요하다. */
function rowKey(e,el){ if(e.key==='Enter'||e.key===' '){ e.preventDefault(); el.click(); } }
function bbToggle(row){
  const d=row.nextElementSibling;
  if(!d||!d.classList.contains('bb-det'))return;
  const wasOpen=d.style.display==='block';
  document.querySelectorAll('#bubble-wrap .bb-det').forEach(x=>x.style.display='none');
  document.querySelectorAll('#bubble-wrap .bb-row').forEach(x=>x.setAttribute('aria-expanded','false'));
  if(!wasOpen){
    d.style.display='block';
    row.setAttribute('aria-expanded','true');
    track('bubble_detail',{region:row.querySelector('.bb-lab').textContent});
  }
}
function renderBubbleSec(){
  const sec=document.getElementById('sec-bubble');if(!sec)return;
  const B=ADV.bubble,J=STATS['전세가율'];
  if(!B||!B.conv||!J){sec.style.display='none';return;}
  const loan=B.loan.v;
  const prdEl=document.getElementById('bubble-prd');if(prdEl)prdEl.textContent='기준 '+B.prd;
  const latest=r=>{const s=J.series[r];if(!s)return null;for(let i=s.length-1;i>=0;i--)if(s[i]!=null)return s[i];return null;};
  /* 축 상한을 9%로 못박아 두면 위험선(월세수익률×2)이 그 위인 지역들이 전부
     같은 자리(98%)에 찍혀 서로 구분이 안 된다 — 실측 7곳이 겹쳤다(2026-08-08 감사).
     실제 값에서 상한을 잡되 최소 9%는 유지한다. */
  const MAX=Math.max(9, Math.ceil(Math.max(loan,
    ...(B.regions||Object.keys(B.conv)).map(rg=>{const cv=B.conv[rg],jr=latest(rg);
      return (cv==null||jr==null)?0:jr/100*cv*2;}))*1.04));
  const px=v=>Math.min(98,Math.max(0,v/MAX*100));
  let h='<style>#bubble-wrap .bb-track{overflow:visible}#bubble-wrap .bb-v{position:absolute;top:50%;font-size:11px;font-weight:700;white-space:nowrap;line-height:1}</style><div class="bb-legend">막대 왼쪽 <b style="color:#1a5276">월세수익률</b> ~ 오른쪽 <b style="color:#a93226">위험선(월세수익률 ×2)</b> · 검은 세로선 = <b>대출금리 '+loan.toFixed(2)+'%</b> ('+B.loan.p+' 신규취급 평균)<br>대출금리가 <b style="color:#1a5276">왼쪽</b>이면 매수신호, <b style="color:#a93226">오른쪽</b>이면 위험 · <b>지역을 누르면 상세</b></div>';
  let nHi=0,nLo=0,nNear=0;
  (B.regions||Object.keys(B.conv)).forEach(rg=>{
    const cv=B.conv[rg],jr=latest(rg);
    if(cv==null||jr==null)return;
    /* ⚠️ 소수 한 자리로 찍으면 판정과 표시가 어긋난다. 울산(4.351)과 경남(4.366)이
       둘 다 '4.4%'로 보이는데 대출금리 4.36% 기준으로 판정은 정반대였다
       (2026-08-08 감사). 금리를 두 자리로 쓰므로 밴드도 두 자리로 맞춘다. */
    const lo=jr/100*cv,hi=lo*2;
    let cls='',txt='여유 '+(hi-loan).toFixed(1)+'%p';
    /* 요약 'N개 지역'은 시도만 센다 — 집계(전국·수도권·지방)는 시도의 합이라 같은 조건을 두 번 센다(전수리뷰 #56) */
    const one=REG_AGG.indexOf(rg)<0?1:0;
    if(loan>=hi){cls='hi';txt='상단 초과';nHi+=one;}
    else if(loan<=lo){cls='lo';txt='매수 신호권';nLo+=one;}
    else if(hi-loan<1)nNear+=one;
    let pos;
    if(loan>=hi)pos='대출금리가 위험선(월세수익률 2배)을 넘었습니다 — 이자가 임대수익의 2배를 넘는 과열 구간입니다.';
    else if(loan<=lo)pos='대출금리가 월세수익률보다 낮습니다 — 이자가 임대수익보다 싼 매수 신호권입니다.';
    else pos='대출금리는 밴드 안이고, 위험선까지 '+(hi-loan).toFixed(1)+'%p 남았습니다.';
    const det='밴드: 전세가율 '+jr+'% × 전월세전환율 '+cv+'% = <b>월세수익률 '+lo.toFixed(2)+'%</b> · 그 2배 = <b>위험선 '+hi.toFixed(2)+'%</b>.<br>'
      +'<b>대출금리 '+loan.toFixed(2)+'%</b> — '+pos;
    // 숫자 위치 적응: 파랑=밴드 왼쪽(단 대출금리 검은선과 겹치면 그 선 왼쪽으로), 빨강=밴드 오른쪽(단 우측 공간 없거나 겹치면 밴드 안쪽 왼편). NW=숫자 폭 근사(%)
    const pL=px(lo),pH=px(hi),pN=px(loan),NW=15;
    const blueAnc=(pN<pL&&pN>pL-NW)?pN:pL;
    const redIn=(pH+NW>98)||(pN>pH&&pN<pH+NW);
    const blueSt='left:'+blueAnc+'%;transform:translate(calc(-100% - 3px),-50%);color:#1a5276';
    const redSt=redIn?'left:'+pH+'%;transform:translate(calc(-100% - 3px),-50%);color:#a93226':'left:'+pH+'%;transform:translate(3px,-50%);color:#a93226';
    h+='<div class="bb-row" role="button" tabindex="0" aria-expanded="false" onclick="bbToggle(this)" onkeydown="rowKey(event,this)"><span class="bb-lab">'+rg+'</span>'
      +'<div class="bb-track" title="월세수익률 '+lo.toFixed(2)+'% ~ 위험선 '+hi.toFixed(2)+'% · 대출금리 '+loan.toFixed(2)+'%">'
      +'<div class="bb-band" style="left:'+px(lo)+'%;width:'+Math.max(2,px(hi)-px(lo))+'%"></div>'
      +'<div class="bb-loan" style="left:'+px(loan)+'%"></div>'
      +'<span class="bb-v" style="'+blueSt+'">'+lo.toFixed(2)+'%</span>'
      +'<span class="bb-v" style="'+redSt+'">'+hi.toFixed(2)+'%</span></div>'
      +'<span class="bb-chip '+cls+'">'+txt+'</span>'
      +'</div>'
      +'<div class="bb-det">'+det+'</div>';
  });
  let sum;
  if(nHi>0)sum='<b style="color:#a93226">'+nHi+'개 지역</b>에서 대출금리가 위험선(월세수익률 2배)을 넘었습니다. 과거 급락기(2008·2022)가 이 조건에서 나왔습니다.';
  else if(nLo>0)sum='<b style="color:#1a5276">'+nLo+'개 지역</b>이 매수 신호권(대출금리 ≤ 월세수익률)입니다.';
  else if(nNear>0)sum=nNear+'개 지역이 위험선까지 1%p 미만으로 접근해 있습니다.';
  else sum='현재 대출금리가 위험선을 넘거나 월세수익률 아래인 지역은 없습니다.';
  document.getElementById('bubble-wrap').innerHTML='<p class="adv-note" style="margin:10px 0 4px">'+sum+'</p>'+h;
}
