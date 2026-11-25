#!/usr/bin/env python3
"""建置時抓取各開發案周邊生活機能（OpenStreetMap / Overpass API），寫入 data/amenities.json。
任何一案失敗都保留舊資料，不會讓建置失敗。總時間上限約 2 分鐘（免費 Overpass 伺服器常忙碌，逐次累積）。
資料會發佈到網站 /data/amenities.json；下次建置先從線上取回，只補抓缺的或超過 30 天的案子，逐次累積。
"""
import json, math, os, re, time, urllib.parse, urllib.request

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.join(ROOT, 'data', 'amenities.json')
P = json.load(open(os.path.join(ROOT, 'data', 'projects.json'), encoding='utf-8'))
START, LIMIT = time.time(), 100
LIVE = 'https://believeland-tw.pages.dev/data/amenities.json'
old = json.load(open(OUT, encoding='utf-8')) if os.path.exists(OUT) else {}
try:
    with urllib.request.urlopen(urllib.request.Request(LIVE, headers={'User-Agent': 'believeland.tw build'}), timeout=20) as r:
        for k, v in json.loads(r.read().decode('utf-8')).items():
            if k not in old or v.get('updated', '') > old[k].get('updated', ''): old[k] = v
    print('已取回線上周邊機能', len(old), '案')
except Exception as ex:
    print('線上周邊機能取回略過', type(ex).__name__)
EPS = ['https://overpass-api.de/api/interpreter', 'https://overpass.private.coffee/api/interpreter',
       'https://maps.mail.ru/osm/tools/overpass/api/interpreter']


def radius(p):
    m = re.search(r'([\d,\.]+)\s*公頃', p.get('area', ''))
    return round(math.sqrt(float(m.group(1).replace(',', '')) * 10000 / math.pi)) if m else 800


def dist(a, b, c, d):
    t = math.radians
    h = math.sin(t(c - a) / 2) ** 2 + math.cos(t(a)) * math.cos(t(c)) * math.sin(t(d - b) / 2) ** 2
    return 2 * 6371000 * math.asin(math.sqrt(h))


def cat(t):
    a, s = t.get('amenity', ''), t.get('shop', '')
    if t.get('railway') == 'station' or t.get('public_transport') == 'station' or t.get('highway') == 'motorway_junction' or a == 'bus_station': return '交通'
    if a in ('school', 'university', 'college', 'kindergarten'): return '學校'
    if a in ('hospital', 'clinic'): return '醫療'
    if s in ('supermarket', 'mall', 'department_store') or a == 'marketplace': return '購物'
    if a in ('townhall', 'police', 'fire_station', 'post_office', 'library'): return '公共服務'
    if t.get('leisure') == 'park': return '公園綠地'
    return None


def query(lat, lng, R):
    a = f'(around:{R},{lat},{lng})'
    return ('[out:json][timeout:25];('
            f'node["railway"="station"]{a};node["public_transport"="station"]{a};node["highway"="motorway_junction"]{a};'
            f'nwr["amenity"~"^(school|university|college|kindergarten|hospital|clinic|marketplace|townhall|police|fire_station|post_office|library|bus_station)$"]{a};'
            f'nwr["shop"~"^(supermarket|mall|department_store)$"]{a};way["leisure"="park"]{a};);out center 400;')


def fetch(q):
    body = urllib.parse.urlencode({'data': q}).encode()
    for ep in EPS:
        for _ in range(1):
            if time.time() - START > LIMIT: return None
            try:
                req = urllib.request.Request(ep, data=body, headers={'User-Agent': 'believeland.tw build (amenities)'})
                with urllib.request.urlopen(req, timeout=35) as r:
                    return json.loads(r.read().decode('utf-8'))
            except Exception as ex:
                print('  ', ep.split('/')[2], type(ex).__name__, str(ex)[:80])
                time.sleep(3)
    return None


res = dict(old)
ok = 0
fresh = time.strftime('%Y-%m-%d', time.localtime(time.time() - 30 * 86400))
todo = sorted((p for p in P if res.get(p['id'], {}).get('updated', '') < fresh), key=lambda p: res.get(p['id'], {}).get('updated', ''))
print('需更新', len(todo), '案')
for p in todo:
    if time.time() - START > LIMIT:
        print('時間上限，其餘沿用舊資料'); break
    R = min(radius(p) + 1500, 3500)
    j = fetch(query(p['lat'], p['lng'], R))
    if not j:
        print('失敗', p['id']); continue
    items, seen = [], set()
    for el in j.get('elements', []):
        t = el.get('tags') or {}
        la = el.get('lat') or (el.get('center') or {}).get('lat')
        lo = el.get('lon') or (el.get('center') or {}).get('lon')
        c = cat(t)
        if la is None or not c: continue
        n = t.get('name:zh') or t.get('name') or ('交流道' if t.get('highway') == 'motorway_junction' else '')
        if not n and c != '公園綠地': continue
        n = n or '公園'
        key = (c, n)
        if key in seen: continue
        seen.add(key)
        items.append({'c': c, 'n': n[:40], 'lat': round(la, 5), 'lng': round(lo, 5), 'd': round(dist(p['lat'], p['lng'], la, lo))})
    items.sort(key=lambda x: x['d'])
    by = {}
    for it in items:
        if len(by.setdefault(it['c'], [])) < 25: by[it['c']].append(it)
    res[p['id']] = {'updated': time.strftime('%Y-%m-%d'), 'radius': R, 'items': [x for v in by.values() for x in v]}
    ok += 1
    print('ok', p['id'], len(res[p['id']]['items']))
    json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
    time.sleep(2)

json.dump(res, open(OUT, 'w', encoding='utf-8'), ensure_ascii=False, separators=(',', ':'))
print(f'周邊機能：本次成功 {ok}/{len(P)} 案，共有 {len(res)} 案資料')
