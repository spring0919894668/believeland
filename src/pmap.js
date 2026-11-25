/* 開發案範圍與周邊機能地圖（Leaflet + OpenStreetMap + Overpass） */
(function(){
const el=document.getElementById('pmap');if(!el||!window.L)return;
const lat=+el.dataset.lat,lng=+el.dataset.lng,r=+el.dataset.r,name=el.dataset.name;
const map=L.map(el,{scrollWheelZoom:false}).setView([lat,lng],r>2500?12:r>1200?13:14);
const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap 貢獻者'}).addTo(map);
const emap=L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}',{maxZoom:19,attribution:'內政部國土測繪中心'});
const photo=L.tileLayer('https://wmts.nlsc.gov.tw/wmts/PHOTO2/default/GoogleMapsCompatible/{z}/{y}/{x}',{maxZoom:19,attribution:'內政部國土測繪中心 正射影像'});
L.control.layers({'街道地圖':osm,'臺灣通用電子地圖':emap,'正射影像（空照）':photo},null,{collapsed:false}).addTo(map);
L.circle([lat,lng],{radius:r,color:'#d4502a',weight:2,dashArray:'6 6',fillColor:'#d4502a',fillOpacity:.08}).addTo(map).bindTooltip('計畫範圍示意（依面積推估）');
L.marker([lat,lng]).addTo(map).bindPopup('<b>'+name+'</b><br>計畫中心參考點');
const CAT=[
 {k:'交通',c:'#2f6db0',t:t=>t.railway==='station'||t.public_transport==='station'||t.highway==='motorway_junction'||t.amenity==='bus_station'},
 {k:'學校',c:'#7a4bb3',t:t=>/^(school|university|college|kindergarten)$/.test(t.amenity||'')},
 {k:'醫療',c:'#d4502a',t:t=>/^(hospital|clinic)$/.test(t.amenity||'')},
 {k:'購物',c:'#c9a227',t:t=>/^(supermarket|mall|department_store)$/.test(t.shop||'')||t.amenity==='marketplace'},
 {k:'公共服務',c:'#2f8a57',t:t=>/^(townhall|police|fire_station|post_office|library)$/.test(t.amenity||'')},
 {k:'公園綠地',c:'#5a9e3a',t:t=>t.leisure==='park'}];
const R=Math.round(r+2000),box=document.getElementById('pmapList');
const q=`[out:json][timeout:25];(node["railway"="station"](around:${R},${lat},${lng});node["public_transport"="station"](around:${R},${lat},${lng});node["highway"="motorway_junction"](around:${R},${lat},${lng});nwr["amenity"~"^(school|university|college|kindergarten|hospital|clinic|marketplace|townhall|police|fire_station|post_office|library|bus_station)$"](around:${R},${lat},${lng});nwr["shop"~"^(supermarket|mall|department_store)$"](around:${R},${lat},${lng});way["leisure"="park"](around:${R},${lat},${lng}););out center 400;`;
const dist=(a,b,c,d)=>{const t=x=>x*Math.PI/180,h=Math.sin(t(c-a)/2)**2+Math.cos(t(a))*Math.cos(t(c))*Math.sin(t(d-b)/2)**2;return 2*6371000*Math.asin(Math.sqrt(h))};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
fetch('https://overpass-api.de/api/interpreter',{method:'POST',body:'data='+encodeURIComponent(q)}).then(x=>x.ok?x.json():Promise.reject()).then(j=>{
 const g={};CAT.forEach(c=>g[c.k]=[]);
 for(const el of j.elements||[]){const t=el.tags||{},la=el.lat??el.center?.lat,lo=el.lon??el.center?.lon;if(la==null)continue;
  const c=CAT.find(c=>c.t(t));if(!c)continue;const nm=t['name:zh']||t.name||(c.k==='交通'&&t.highway?'交流道':'');if(!nm&&c.k!=='公園綠地')continue;
  const d=dist(lat,lng,la,lo);g[c.k].push({nm:nm||'公園',d});
  L.circleMarker([la,lo],{radius:6,color:'#fff',weight:1.5,fillColor:c.c,fillOpacity:.95}).addTo(map).bindTooltip(esc((nm||'公園')+'（'+c.k+'，'+(d/1000).toFixed(1)+' km）'))}
 box.innerHTML='<p class="small muted" style="margin:0 0 8px">計畫中心周邊 '+(R/1000).toFixed(1)+' 公里內的生活機能（資料來源：OpenStreetMap）</p>'+CAT.map(c=>{const a=g[c.k].sort((x,y)=>x.d-y.d);
  return '<div class="fn"><span class="dot" style="background:'+c.c+'"></span><b>'+c.k+'</b> <span class="muted small">'+a.length+' 處</span><br><span class="small">'+(a.length?a.slice(0,3).map(x=>esc(x.nm)+' '+(x.d/1000).toFixed(1)+' km').join('、'):'範圍內未標示')+'</span></div>'}).join('');
}).catch(()=>{box.innerHTML='<p class="note">周邊機能資料暫時無法載入，請稍後重新整理。</p>'});
})();
