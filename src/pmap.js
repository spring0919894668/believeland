/* 開發案位置與政府土地使用分區圖（Leaflet）
   底圖：內政部國土測繪中心 臺灣通用電子地圖／正射影像
   疊圖：非都市土地使用分區圖（未上色處多為既有都市計畫區）、段籍圖、鄉鎮界；嘉義市另疊都市計畫使用分區 */
(function(){
const el=document.getElementById('pmap');if(!el||!window.L)return;
const lat=+el.dataset.lat,lng=+el.dataset.lng,name=el.dataset.name;
let pts=[];try{pts=JSON.parse(el.dataset.amen||'[]')}catch(e){}
const map=L.map(el,{scrollWheelZoom:false}).setView([lat,lng],15);
const N=id=>'https://wmts.nlsc.gov.tw/wmts/'+id+'/default/GoogleMapsCompatible/{z}/{y}/{x}';
const A='&copy; 內政部國土測繪中心';
const emap=L.tileLayer(N('EMAP'),{maxZoom:19,attribution:A}).addTo(map);
const photo=L.tileLayer(N('PHOTO2'),{maxZoom:19,attribution:A+' 正射影像'});
const osm=L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'&copy; OpenStreetMap 貢獻者'});
const nurban=L.tileLayer(N('nURBAN1'),{maxZoom:19,opacity:.55,attribution:A+'（非都市土地使用分區）'}).addTo(map);
const sect=L.tileLayer(N('LANDSECT'),{maxZoom:19,minZoom:13,attribution:A+'（段籍圖）'}).addTo(map);
const town=L.tileLayer(N('TOWN'),{maxZoom:19,attribution:A});
const over={'非都市土地使用分區圖（空白＝都市計畫區）':nurban,'地段界線（段籍圖）':sect,'鄉鎮區界':town};
if(el.dataset.cyc==='1'){
  over['嘉義市都市計畫使用分區']=L.tileLayer('https://3dmap.chiayi.gov.tw/arcgis/rest/services/UP/UPZONE/MapServer/WMTS/tile/1.0.0/UP_UPZONE/default/GoogleMapsCompatible/{z}/{y}/{x}.png',{maxZoom:19,opacity:.7,attribution:'嘉義市都發處：嘉義市3D空間資訊展示系統'}).addTo(map);
}
L.control.layers({'臺灣通用電子地圖':emap,'正射影像（空照）':photo,'街道地圖（OSM）':osm},over,{collapsed:false}).addTo(map);
L.control.scale({imperial:false}).addTo(map);
L.marker([lat,lng]).addTo(map).bindPopup('<b>'+name.replace(/</g,'&lt;')+'</b><br>計畫位置參考點（非範圍線）');
const C={'交通':'#2f6db0','學校':'#7a4bb3','醫療':'#d4502a','購物':'#c9a227','公共服務':'#2f8a57','公園綠地':'#5a9e3a'};
const esc=v=>String(v??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
for(const [c,n,la,lo,d] of pts){if(!C[c])continue;L.circleMarker([la,lo],{radius:6,color:'#fff',weight:1.5,fillColor:C[c],fillOpacity:.95}).addTo(map).bindTooltip(esc(n+'（'+c+'，'+(d/1000).toFixed(1)+' 公里）'))}
})();
