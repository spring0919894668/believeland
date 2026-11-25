/* 開發案範圍與周邊機能地圖（Leaflet；周邊機能於建置時由 OpenStreetMap 取得） */
(function(){
const el=document.getElementById('pmap');if(!el||!window.L)return;
const lat=+el.dataset.lat,lng=+el.dataset.lng,r=+el.dataset.r,name=el.dataset.name;
let pts=[];try{pts=JSON.parse(el.dataset.amen||'[]')}catch(e){}
const map=L.map(el,{scrollWheelZoom:false}).setView([lat,lng],r>2500?12:r>1200?13:14);
const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap 貢獻者'}).addTo(map);
const emap=L.tileLayer('https://wmts.nlsc.gov.tw/wmts/EMAP/default/GoogleMapsCompatible/{z}/{y}/{x}',{maxZoom:19,attribution:'內政部國土測繪中心'});
const photo=L.tileLayer('https://wmts.nlsc.gov.tw/wmts/PHOTO2/default/GoogleMapsCompatible/{z}/{y}/{x}',{maxZoom:19,attribution:'內政部國土測繪中心 正射影像'});
L.control.layers({'街道地圖':osm,'臺灣通用電子地圖':emap,'正射影像（空照）':photo},null,{collapsed:true}).addTo(map);
L.circle([lat,lng],{radius:r,color:'#d4502a',weight:2,dashArray:'6 6',fillColor:'#d4502a',fillOpacity:.08}).addTo(map).bindTooltip('計畫範圍示意（依面積推估）');
L.marker([lat,lng]).addTo(map).bindPopup('<b>'+name.replace(/</g,'&lt;')+'</b><br>計畫中心參考點');
const C={'交通':'#2f6db0','學校':'#7a4bb3','醫療':'#d4502a','購物':'#c9a227','公共服務':'#2f8a57','公園綠地':'#5a9e3a'};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const [c,n,la,lo,d] of pts){if(!C[c])continue;L.circleMarker([la,lo],{radius:6,color:'#fff',weight:1.5,fillColor:C[c],fillOpacity:.95}).addTo(map).bindTooltip(esc(n+'（'+c+'，'+(d/1000).toFixed(1)+' 公里）'))}
})();
