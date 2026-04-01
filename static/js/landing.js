const TK=[41.311,69.279];
const MS=[
  {n:'Азиз К.',s:'Электрик',lt:41.315,ln:69.285,r:4.9,c:'#1a56db'},
  {n:'Дмитрий Л.',s:'Сантехник',lt:41.308,ln:69.265,r:4.8,c:'#059669'},
  {n:'Бахром У.',s:'Ремонт',lt:41.318,ln:69.295,r:4.9,c:'#d97706'},
  {n:'Сардор М.',s:'Кондиционеры',lt:41.305,ln:69.250,r:4.7,c:'#6366f1'},
  {n:'Нодир А.',s:'Электрик',lt:41.322,ln:69.270,r:4.6,c:'#1a56db'},
  {n:'Олег П.',s:'Мебель',lt:41.300,ln:69.290,r:4.8,c:'#d97706'},
  {n:'Жасур Т.',s:'Сантехник',lt:41.325,ln:69.260,r:4.5,c:'#059669'},
  {n:'Ильяс Р.',s:'Ремонт',lt:41.312,ln:69.240,r:4.9,c:'#d97706'},
  {n:'Камол Н.',s:'Электрик',lt:41.328,ln:69.278,r:4.7,c:'#1a56db'},
  {n:'Рустам Х.',s:'Клининг',lt:41.298,ln:69.272,r:4.8,c:'#8b5cf6'},
];
const JOBS=[
  {id:1,icon:'⚡',cat:'Электрик',task:'Установка розеток',type:'Почасовая',price:'80 000 сўм/ч',time:'Сегодня, 14:00',ppl:'1 мастер',addr:'Мирзо Улугбек, ул. Б. Ипак Йули, 42',urg:true,lt:41.3265,ln:69.3050,c:'#dc2626'},
  {id:2,icon:'🔧',cat:'Сантехник',task:'Замена смесителя',type:'Сдельная',price:'120 000 сўм',time:'Завтра, 10:00',ppl:'1 мастер',addr:'Чиланзар, кв. 7, д. 15',urg:false,lt:41.3055,ln:69.2280,c:'#059669'},
  {id:3,icon:'🏠',cat:'Ремонт',task:'Укладка плитки',type:'Сдельная',price:'350 000 сўм',time:'Пн–Ср',ppl:'2 мастера',addr:'Юнусабад, кв. 4, ул. Янги Шахар',urg:false,lt:41.3380,ln:69.2750,c:'#d97706'},
  {id:4,icon:'❄️',cat:'Кондиционеры',task:'Монтаж сплит-системы',type:'Сдельная',price:'250 000 сўм',time:'Сегодня, 16:00',ppl:'1 мастер',addr:'Сергели, ул. Зарафшон, 22',urg:true,lt:41.2550,ln:69.2280,c:'#6366f1'},
  {id:5,icon:'🪑',cat:'Мебель',task:'Сборка кухни IKEA',type:'Сдельная',price:'200 000 сўм',time:'Завтра, 09:00',ppl:'1 мастер',addr:'Шайхантахур, ул. Навои, 48',urg:false,lt:41.3200,ln:69.2520,c:'#92400e'},
  {id:6,icon:'🧹',cat:'Клининг',task:'Генеральная уборка',type:'3 комнаты',price:'180 000 сўм',time:'Сегодня, 12:00',ppl:'2 мастера',addr:'Яккасарай, ул. Ш. Руставели, 12',urg:true,lt:41.2980,ln:69.2680,c:'#16a34a'},
];

let hM,jM,mM,uMk,mMk,st,jobMarkers={};

// ====== TILE LAYER — using CartoDB (no 403!) ======
const TILES='https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png';
const TILE_ATTR='&copy; <a href="https://carto.com">CARTO</a>';

function init(){
  if(typeof L==='undefined')return;

  // Hero map
  hM=L.map('heroMap',{zoomControl:false,attributionControl:false}).setView(TK,14);
  L.tileLayer(TILES,{maxZoom:19,attribution:TILE_ATTR}).addTo(hM);
  MS.forEach(m=>{
    const ic=L.divIcon({className:'m-mk',html:m.n[0],iconSize:[34,34]});
    ic.options.className+=' ';
    const el=L.marker([m.lt,m.ln],{icon:L.divIcon({className:'m-mk',html:m.n[0],iconSize:[34,34]})}).addTo(hM);
    el.bindPopup(`<div style="font-family:Manrope,sans-serif;text-align:center"><b>${m.n}</b><br><span style="color:#6b7280;font-size:12px">${m.s} · ★${m.r}</span></div>`);
    el.getElement().style.background=m.c;
  });

  // Jobs map
  jM=L.map('jobsMap',{zoomControl:true,attributionControl:false}).setView(TK,13);
  L.tileLayer(TILES,{maxZoom:19,attribution:TILE_ATTR}).addTo(jM);

  JOBS.forEach(j=>{
    const mk=L.marker([j.lt,j.ln],{icon:L.divIcon({className:'j-mk',html:j.icon,iconSize:[38,38]})}).addTo(jM);
    mk.bindPopup(`<div style="font-family:Manrope,sans-serif"><b>${j.task}</b><br><span style="color:#6b7280;font-size:12px">${j.cat} · ${j.price}</span><br><span style="font-size:11px;color:#9ca3af">📍 ${j.addr}</span></div>`);
    mk.getElement().style.background=j.c;
    jobMarkers[j.id]=mk;
  });

  // Add user location marker
  L.marker(TK,{icon:L.divIcon({className:'c-mk',html:'📍',iconSize:[36,36]})}).addTo(jM).bindPopup('<b>Ваше местоположение</b>');

  // Build job cards
  const jl=document.getElementById('jobList');
  jl.innerHTML=JOBS.map(j=>`
    <div class="job-card" data-id="${j.id}" onmouseenter="hlJob(${j.id})" onmouseleave="ulJob(${j.id})" onclick="flyJob(${j.id})">
      <div class="job-top"><div class="job-cat"><div class="job-ic ${j.urg?'ji-r':'ji-g'}">${j.icon}</div><div><div class="job-cn">${j.task}</div><div class="job-cs">${j.cat} · ${j.type}</div></div></div><div class="job-pr">${j.price}</div></div>
      <div class="job-det"><span class="job-d">🕐 ${j.time}</span><span class="job-d">👤 ${j.ppl}</span>${j.urg?'<span class="job-urg">🔴 Срочный</span>':'<span class="job-pln">🟢 Плановый</span>'}</div>
      <div class="job-bottom"><span class="job-addr">📍 ${j.addr}</span><button class="job-btn">Принять →</button></div>
    </div>`).join('');

  if(navigator.geolocation)navigator.geolocation.getCurrentPosition(p=>sLoc(p.coords.latitude,p.coords.longitude),()=>{},{timeout:5000});
}

function hlJob(id){
  document.querySelectorAll('.job-card').forEach(c=>c.classList.remove('active'));
  document.querySelector('[data-id="'+id+'"]').classList.add('active');
  const mk=jobMarkers[id];
  if(mk&&mk.getElement())mk.getElement().classList.add('hl');
  if(mk)mk.openPopup();
}
function ulJob(id){
  const mk=jobMarkers[id];if(mk&&mk.getElement())mk.getElement().classList.remove('hl');
}
function flyJob(id){
  const j=JOBS.find(x=>x.id===id);if(j)jM.flyTo([j.lt,j.ln],16,{duration:0.8});
}

function sLoc(lat,lng){hM.setView([lat,lng],15)}

function dGPS(){
  if(!navigator.geolocation)return;
  navigator.geolocation.getCurrentPosition(p=>{
    const lat=p.coords.latitude,lng=p.coords.longitude;
    hM.setView([lat,lng],15);
    jM.setView([lat,lng],15);
    L.marker([lat,lng],{icon:L.divIcon({className:'c-mk',html:'📍',iconSize:[36,36]})}).addTo(hM).bindPopup('<b>Вы здесь</b>').openPopup();
  },()=>{},{timeout:10000,enableHighAccuracy:true});
}

// Address search — using Photon (no 403 like Nominatim)
function aS(v,rid){clearTimeout(st);const b=document.getElementById(rid);if(v.length<3){b.classList.remove('on');b.innerHTML='';return}
  st=setTimeout(()=>{fetch(`https://photon.komoot.io/api/?q=${encodeURIComponent(v+' Tashkent')}&limit=5&lang=default`).then(r=>r.json()).then(d=>{
    const res=d.features||[];if(!res.length){b.classList.remove('on');return}
    window['_'+rid]=res;
    b.innerHTML=res.map((r,i)=>{const p=r.properties;return`<div class="sr-i" onclick="pA('${rid}',${i})">${p.name||''} ${p.street||''} ${p.city||'Tashkent'}</div>`}).join('');
    b.classList.add('on');
  }).catch(()=>{})},500)}

function pA(rid,i){const r=window['_'+rid][i],b=document.getElementById(rid);b.classList.remove('on');
  const p=r.properties,c=r.geometry.coordinates,name=`${p.name||''} ${p.street||''} ${p.city||''}`.trim();
  const inp=b.parentElement.querySelector('input');if(inp)inp.value=name;
  if(rid==='hR'){hM.setView([c[1],c[0]],16);L.marker([c[1],c[0]],{icon:L.divIcon({className:'c-mk',html:'📍',iconSize:[36,36]})}).addTo(hM).bindPopup(name).openPopup()}}

// AI Analysis
const ADB={'электрик|розетк|проводк|свет|щит|люстр':{c:'Электрик',p:'60 000 — 150 000 сўм',t:'1–3 ч',x:'Допуск',tip:'Мастер с сертификатом'},'сантехн|смесител|кран|труб|унитаз|бойлер|течь':{c:'Сантехник',p:'50 000 — 200 000 сўм',t:'1–4 ч',x:'',tip:'Фото поможет оценить точнее'},'мебел|сборк|шкаф|кроват|стол|полк|комод':{c:'Сборка мебели',p:'80 000 — 250 000 сўм',t:'2–5 ч',x:'',tip:'Укажите количество единиц'},'ремонт|штукатур|покрас|обо|плитк|гипсокартон|потолок|пол|стен':{c:'Ремонт квартир',p:'200 000 — 1 500 000 сўм',t:'1–14 дн',x:'',tip:'Рекомендуем командный заказ'},'кондиционер|сплит|климат|фреон':{c:'Кондиционеры',p:'150 000 — 400 000 сўм',t:'2–4 ч',x:'Сертификат',tip:'Заказывайте заранее'},'уборк|клининг|мойк|чистк|генеральн':{c:'Клининг',p:'100 000 — 350 000 сўм',t:'2–6 ч',x:'',tip:'Укажите площадь'}};
let aTO;
function aiAn(v){clearTimeout(aTO);const p=document.getElementById('aiA');if(v.length<5){p.classList.remove('on');return}
  aTO=setTimeout(()=>{const l=v.toLowerCase();let m=null;for(const[k,d]of Object.entries(ADB)){if(k.split('|').some(w=>l.includes(w))){m=d;break}}if(!m){p.classList.remove('on');return}
  p.classList.add('on');let t=`<span class="ai-tg ai-tc">📁 ${m.c}</span><span class="ai-tg ai-tp">💰 ${m.p}</span><span class="ai-tg ai-tt">⏱ ${m.t}</span>`;if(m.x)t+=`<span class="ai-tg ai-tx">📜 ${m.x}</span>`;document.getElementById('aiTg').innerHTML=t;document.getElementById('aiDt').textContent='💡 '+m.tip;document.getElementById('mCat').value=m.c;document.getElementById('mPr').textContent=m.p},500)}

// AI Chat
const AR={'электрик|розетк|свет':['420+ электриков! ⚡\nОт 60 000 сўм · ~12 мин',1],'сантехн|кран|труб':['380+ сантехников! 🔧\nОт 50 000 сўм',0],'цен|стоимост|сколько':['⚡ Электрик: от 60 000\n🔧 Сантехник: от 50 000\n🪑 Мебель: от 80 000\n🏠 Ремонт: от 200 000',0],'заказ|оформит|как':['1️⃣ Опишите задачу\n2️⃣ Укажите адрес\n3️⃣ Нажмите «Заказать»\nИИ подберёт за 15 мин!',1],'гарант|безопас':['✅ Верификация\n✅ Лицензии\n✅ Арбитраж 🛡',0],'привет|салам|хай':['Привет! 👋\n🔍 Найти мастера\n💰 Цены\n📝 Заказать',0]};
function tC(){const c=document.getElementById('aC'),f=document.getElementById('aF');c.classList.toggle('on');f.classList.toggle('hid',c.classList.contains('on'));if(c.classList.contains('on'))document.getElementById('aIn').focus()}
function aSI(){const i=document.getElementById('aIn');if(!i.value.trim())return;aI(i.value.trim());i.value=''}
function aI(t){const bd=document.getElementById('aBd');bd.innerHTML+=`<div class="ai-m usr">${t}</div>`;bd.scrollTop=bd.scrollHeight;document.getElementById('aSg').style.display='none';bd.innerHTML+=`<div class="ai-ty" id="aiT"><span></span><span></span><span></span></div>`;bd.scrollTop=bd.scrollHeight;
  let rsp='🤔 Уточните: мастер, цена или заказ?',act=0;const l=t.toLowerCase();for(const[k,d]of Object.entries(AR)){if(k.split('|').some(w=>l.includes(w))){rsp=d[0];act=d[1];break}}
  setTimeout(()=>{const tp=document.getElementById('aiT');if(tp)tp.remove();let h=`<div class="ai-m bot"><div class="ai-ml">🤖 InTask AI</div>${rsp.replace(/\n/g,'<br>')}`;if(act)h+=`<br><br><button onclick="tC();oM()" style="padding:6px 12px;border-radius:8px;border:none;background:linear-gradient(135deg,#1a56db,#142563);color:#fff;font-weight:700;font-size:11px;cursor:pointer">📝 Заказать →</button>`;h+=`</div>`;bd.innerHTML+=h;bd.scrollTop=bd.scrollHeight},600+Math.random()*500)}

// VIEW TOGGLES
function heroView(mode){
  const map=document.getElementById('heroSec'),list=document.getElementById('heroList');
  if(mode==='map'){map.style.display='block';list.classList.remove('on')}
  else{map.style.display='none';list.classList.add('on');buildMasterGrid()}
  document.querySelectorAll('.view-tog-float .vt-btn, #heroList .vt-btn').forEach(b=>{b.classList.remove('on');if(b.textContent.includes(mode==='map'?'Карта':'Список'))b.classList.add('on')});
}
function jobsView(mode){
  const mc=document.getElementById('jobsMapContent'),lf=document.getElementById('jobsListFull');
  if(mode==='map'){mc.classList.remove('off');mc.style.display='block';lf.classList.remove('on');lf.style.display='none';if(jM)jM.invalidateSize()}
  else{mc.classList.add('off');mc.style.display='none';lf.classList.add('on');lf.style.display='block';buildJobsGrid()}
  document.querySelectorAll('#jobsSec .vt-btn').forEach(b=>{b.classList.remove('on');if(b.textContent.includes(mode==='map'?'Карта':'Список'))b.classList.add('on')});
}

function buildMasterGrid(){
  const g=document.getElementById('masterGrid');
  if(g.children.length>0)return;
  g.innerHTML=MS.map(m=>`
    <div class="ml-card" onclick="oM()">
      <div class="ml-top">
        <div class="ml-av" style="background:${m.c}">${m.n[0]}</div>
        <div><div class="ml-nm">${m.n}</div><div class="ml-sp">${m.s}</div></div>
      </div>
      <div class="ml-meta">
        <div><span class="ml-rt"><span class="ml-star">★</span> ${m.r}</span> <span class="ml-rv">(${Math.floor(50+Math.random()*150)} отзывов)</span></div>
        <div class="ml-pr">от ${Math.floor(60+Math.random()*60)} 000 сўм/ч</div>
      </div>
      <div class="ml-det">
        <span class="ml-d">📍 ${Math.floor(5+Math.random()*20)} мин от вас</span>
        <span class="ml-d">✅ Верифицирован</span>
        <span class="ml-d">📋 ${Math.floor(50+Math.random()*200)} заказов</span>
      </div>
      <button class="ml-btn">Выбрать мастера →</button>
    </div>`).join('');
  // Filter buttons
  document.querySelectorAll('.hl-fil').forEach(b=>b.addEventListener('click',function(){
    document.querySelectorAll('.hl-fil').forEach(x=>x.classList.remove('on'));this.classList.add('on');
    const filter=this.textContent.trim();
    document.querySelectorAll('.ml-card').forEach(c=>{
      if(filter==='Все')c.style.display='';
      else c.style.display=c.querySelector('.ml-sp').textContent.includes(filter.slice(2))?'':'none';
    });
  }));
}

function buildJobsGrid(){
  const g=document.getElementById('jobsFullGrid');
  if(g.children.length>0)return;
  g.innerHTML=JOBS.map(j=>`
    <div class="jl-card ${j.urg?'urg-card':'pln-card'}">
      <div class="jl-card-top">
        <div class="jl-card-cat">
          <div class="jl-card-ic" style="background:${j.urg?'#fef2f2':'#f0fdf4'}">${j.icon}</div>
          <div><div class="jl-card-nm">${j.task}</div><div class="jl-card-sub">${j.cat} · ${j.type}</div></div>
        </div>
        <div><div class="jl-card-pr">${j.price}</div>${j.urg?'<div class="jl-card-pr-sub" style="color:#dc2626">🔴 Срочный</div>':'<div class="jl-card-pr-sub" style="color:#22c55e">🟢 Плановый</div>'}</div>
      </div>
      <div class="jl-card-info">
        <span class="jl-card-d">🕐 ${j.time}</span>
        <span class="jl-card-d">👤 ${j.ppl}</span>
        <span class="jl-card-d">📏 ${(Math.random()*5+0.5).toFixed(1)} км</span>
      </div>
      <div class="jl-card-addr">📍 ${j.addr}</div>
      <div class="jl-card-btns">
        <button class="jl-card-btn jl-card-btn-primary" onclick="oM()">Принять заказ →</button>
        <button class="jl-card-btn jl-card-btn-secondary">Подробнее</button>
      </div>
    </div>`).join('');
}

function setL(b){document.querySelectorAll('.lng').forEach(x=>x.classList.remove('on'));b.classList.add('on')}
function tw(b){document.querySelectorAll('.wt-b').forEach(x=>x.classList.remove('on'));b.classList.add('on')}
function oM(){document.getElementById('oMod').classList.add('on');document.body.style.overflow='hidden';setTimeout(()=>{if(typeof L==='undefined')return;if(!mM){mM=L.map('modMap',{zoomControl:false,attributionControl:false}).setView(TK,14);L.tileLayer(TILES,{maxZoom:19}).addTo(mM);MS.slice(0,4).forEach(m=>{L.marker([m.lt,m.ln],{icon:L.divIcon({className:'m-mk',html:m.n[0],iconSize:[34,34]})}).addTo(mM).getElement().style.background=m.c});mM.on('click',function(e){if(mMk)mM.removeLayer(mMk);mMk=L.marker(e.latlng,{icon:L.divIcon({className:'c-mk',html:'📍',iconSize:[36,36]})}).addTo(mM);document.getElementById('mAddr').value=`${e.latlng.lat.toFixed(5)}, ${e.latlng.lng.toFixed(5)}`})}mM.invalidateSize()},150)}
function cM(){document.getElementById('oMod').classList.remove('on');document.body.style.overflow=''}
function sO(){cM();const t=document.getElementById('tst');t.style.display='block';setTimeout(()=>{t.style.display='none'},4000)}
document.addEventListener('keydown',e=>{if(e.key==='Escape')cM()});
window.addEventListener('scroll',()=>{document.getElementById('hdr').classList.toggle('scrolled',window.scrollY>10)});
const obs=new IntersectionObserver(en=>{en.forEach(e=>{if(e.isIntersecting){e.target.classList.add('vis');obs.unobserve(e.target)}})},{threshold:.1,rootMargin:'0px 0px -40px 0px'});
document.querySelectorAll('.reveal').forEach(el=>obs.observe(el));
const cO=new IntersectionObserver(en=>{en.forEach(e=>{if(!e.isIntersecting)return;const el=e.target,tg=+el.dataset.c,d=el.dataset.d,sf=el.dataset.s||'',du=2000,s=performance.now();function tk(n){const p=Math.min((n-s)/du,1),ea=1-Math.pow(1-p,3);if(d)el.textContent=(ea*tg/10).toFixed(1)+sf;else if(tg>=1000)el.textContent=Math.round(ea*tg).toLocaleString('ru-RU')+'+ '+sf;else el.textContent=Math.round(ea*tg)+sf;if(p<1)requestAnimationFrame(tk)}requestAnimationFrame(tk);cO.unobserve(el)})},{threshold:.5});
document.querySelectorAll('.st-n[data-c]').forEach(el=>cO.observe(el));
document.addEventListener('click',e=>{if(!e.target.closest('.sr')&&!e.target.closest('.iw'))document.querySelectorAll('.sr').forEach(d=>d.classList.remove('on'))});

function tryI(n){if(typeof L!=='undefined')init();else if(n>0)setTimeout(()=>tryI(n-1),500);else{['heroMap','jobsMap'].forEach(id=>{const el=document.getElementById(id);if(el)el.innerHTML='<div style="display:flex;align-items:center;justify-content:center;height:100%;background:#e5e7eb;color:#6b7280;font-size:14px;text-align:center;padding:20px">Карта загружается...<br>Проверьте интернет</div>'})}}
window.addEventListener('DOMContentLoaded',()=>tryI(20));