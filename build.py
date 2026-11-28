#!/usr/bin/env python3
"""相信土地 believeland.tw 靜態網站產生器

用法：python3 build.py
讀取 data/ 內的資料，輸出整個網站到 dist/。
- data/site.json      網站設定（網域、經紀業名稱、聯絡方式、表單網址）
- data/projects.json  開發案資料
- data/news.json      每月新聞（排程任務自動更新）
- data/listings.json  上架物件（手動維護）
"""
import json, os, re, shutil, html, math, datetime
from urllib.parse import quote

ROOT = os.path.dirname(os.path.abspath(__file__))
D = lambda *p: os.path.join(ROOT, *p)
OUT = D('dist')

if os.environ.get('CF_PAGES') or os.environ.get('FETCH_AMENITIES'):
    import subprocess, sys
    try:
        subprocess.run([sys.executable, D('fetch_amenities.py')], timeout=150)
    except Exception as ex:
        print('周邊機能抓取略過：', ex)
CFG = json.load(open(D('data/site.json'), encoding='utf-8'))
P = json.load(open(D('data/projects.json'), encoding='utf-8'))
NEWS_ALL = json.load(open(D('data/news.json'), encoding='utf-8'))
NEWS = NEWS_ALL.get('projects', {})
NEWS_AT = NEWS_ALL.get('updatedAt', '')
LIST = json.load(open(D('data/listings.json'), encoding='utf-8'))
GOV = json.load(open(D('data/gov_sources.json'), encoding='utf-8'))
GOVK = {'plan': '計畫書圖', 'record': '審議／公聽會紀錄', 'page': '官方專頁', 'news': '政府新聞稿', 'report': '政府報告', 'agency': '主管機關'}
COL = {}
for _f in sorted(os.listdir(D('data/columns'))):
    if _f.endswith('.json'): COL.update(json.load(open(D('data/columns/' + _f), encoding='utf-8')))
COL_PUB = '2026-11-28'
AMEN = json.load(open(D('data/amenities.json'), encoding='utf-8')) if os.path.exists(D('data/amenities.json')) else {}
ACAT = [('交通', '#2f6db0'), ('學校', '#7a4bb3'), ('醫療', '#d4502a'), ('購物', '#c9a227'), ('公共服務', '#2f8a57'), ('公園綠地', '#5a9e3a')]
SITE = CFG['site'].rstrip('/')
BRAND = CFG['brand']
TODAY = datetime.date.today().isoformat()

e = lambda v: html.escape(str(v if v is not None else ''), quote=True)
STEPS = ['都市計畫擬定', '公益必要性審議', '徵收公告', '補償・抵價地申請', '公共工程', '抵價地分配・標售', '發展成熟']
STAGE = {'pre': '開發前', 'mid': '開發中', 'post': '開發後'}
stage_of = lambda s: 'pre' if s <= 1 else 'mid' if s <= 4 else 'post'
REG = {'北部': ['臺北市', '新北市', '基隆市', '桃園市', '新竹縣', '新竹市', '宜蘭縣'],
       '中部': ['苗栗縣', '臺中市', '彰化縣', '南投縣', '雲林縣'],
       '南部': ['嘉義縣', '嘉義市', '臺南市', '高雄市', '屏東縣'],
       '東部': ['花蓮縣', '臺東縣']}
region_of = lambda c: next((r for r, cs in REG.items() if c in cs), '其他')
CSLUG = {'臺北市': 'taipei', '新北市': 'new-taipei', '基隆市': 'keelung', '桃園市': 'taoyuan', '新竹縣': 'hsinchu-county',
         '新竹市': 'hsinchu-city', '宜蘭縣': 'yilan', '苗栗縣': 'miaoli', '臺中市': 'taichung', '彰化縣': 'changhua',
         '南投縣': 'nantou', '雲林縣': 'yunlin', '嘉義縣': 'chiayi-county', '嘉義市': 'chiayi-city', '臺南市': 'tainan',
         '高雄市': 'kaohsiung', '屏東縣': 'pingtung', '花蓮縣': 'hualien', '臺東縣': 'taitung'}
COUNTIES = [c for r in REG.values() for c in r if any(p['county'] == c for p in P)]


def dkey(d):
    m = re.match(r'^(\d{4})(?:-(\d{1,2}))?(?:-(\d{1,2}))?', str(d or ''))
    return f"{m.group(1)}-{(m.group(2) or '00').zfill(2)}-{(m.group(3) or '00').zfill(2)}" if m else ''


def news_of(pid):
    it = [x for x in (NEWS.get(pid, {}).get('items') or []) if x and x.get('title')]
    return sorted(it, key=lambda x: dkey(x.get('date')), reverse=True)


def is_recent(it):
    k = dkey(it.get('date'))
    if not k: return False
    base = datetime.date.fromisoformat((NEWS_AT or TODAY)[:10]) - datetime.timedelta(days=45)
    return k >= base.isoformat()


def safe_url(u):
    u = str(u or '')
    return u if u.startswith('https://') else ''


def pot(p):
    d, x, why = (p.get('pot') or [3, 3, ''])
    dev = max(0, min(100, round(d * 16 + [0, 3, 6, 8, 10, 12, 14][p['step']] - p['pen'] * .8)))
    base = max(0, min(100, round(x * 18 + [0, 2, 4, 6, 8, 10, 12][p['step']])))
    return {'dev': dev, 'base': base, 'pri': round(dev * .6 + (100 - base) * .4), 'why': why,
            'top': dev >= 60 and base <= 50}


def plan_radius(p):
    m = re.search(r'([\d,\.]+)\s*公頃', p.get('area', ''))
    if not m: return 800, False
    ha = float(m.group(1).replace(',', ''))
    return round(math.sqrt(ha * 10000 / math.pi)), True


def hav(a, b, c, d):
    r = math.radians
    h = math.sin(r(c - a) / 2) ** 2 + math.cos(r(a)) * math.cos(r(c)) * math.sin(r(d - b) / 2) ** 2
    return 2 * 6371 * math.asin(math.sqrt(h))


# ---------- 共用版型 ----------
BASE_CSS = open(D('src/base.css'), encoding='utf-8').read()
EXTRA_CSS = """
.crumb{font-size:14px;color:var(--mute);margin-bottom:10px}.crumb a{color:var(--mute)}
.lede{font-size:18px;max-width:42em}
.kpis{display:grid;grid-template-columns:repeat(auto-fit,minmax(150px,1fr));gap:12px;margin:18px 0}
.kpis div{background:var(--card);border:1px solid var(--line);border-radius:14px;padding:14px 16px}.kpis b{display:block;font-size:26px;font-weight:900;line-height:1.15}.kpis span{font-size:14px;color:var(--mute)}
.pgrid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:14px}
.pcard{display:block;text-decoration:none;background:var(--card);border:1px solid var(--line);border-radius:14px;padding:16px}.pcard:hover{border-color:var(--field)}
.pcard h3{margin:8px 0 4px;font-size:18px}
.news{padding:10px 0;border-bottom:1px solid var(--line)}.news a{font-weight:700}
.newtag{display:inline-block;font-size:12px;font-weight:700;color:#1b2a12;background:var(--rice);border-radius:6px;padding:0 6px;margin-left:4px}
.mapsvg{display:block;width:100%;height:auto;max-height:80vh}
.mapsvg a circle{transition:r .15s}.mapsvg a:hover circle.core,.mapsvg a:focus circle.core{stroke:var(--ink);stroke-width:1}
.foot a{color:var(--fieldInk)}.foot ul{list-style:none;padding:0;margin:6px 0}.foot li{margin:4px 0}
.fgrid{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px}
.article h2{margin-top:36px}.article p,.article li{max-width:44em}
.risk-card ul{padding-left:1.1em;margin:8px 0}.risk-card li{margin:3px 0;font-size:15px}.risk-card .ex{font-size:14px;background:var(--soft);border-radius:8px;padding:8px 10px;margin-top:8px}
.formmsg{padding:12px 14px;border-radius:10px;background:var(--soft);margin-top:12px}
.chart{margin:0;max-width:760px}.charts2{align-items:start}.chart svg{display:block;width:100%;height:auto;color:var(--ink)}.chart figcaption{font-size:14px;color:var(--mute);margin-top:8px}
.charts2{display:grid;grid-template-columns:repeat(auto-fit,minmax(300px,1fr));gap:20px;margin-top:16px}
#pmap{height:480px;border-radius:16px;border:1px solid var(--line);z-index:0}.fn{padding:8px 0;border-bottom:1px solid var(--line)}.fn .dot{margin-right:6px}
.hp{position:absolute;left:-9999px;width:1px;height:1px;overflow:hidden}
.seg{display:flex;gap:8px;flex-wrap:wrap}.seg label{display:flex;align-items:center;gap:8px;font-weight:700;min-height:44px;padding:0 14px;border:1px solid var(--line);border-radius:10px;background:var(--card);cursor:pointer}
.seg input{min-height:auto}
.tldr{background:var(--card);border:1px solid var(--line);border-left:5px solid var(--field);border-radius:12px;padding:14px 18px;margin:18px 0;max-width:46em}.tldr ul{margin:6px 0 0;padding-left:1.2em}.tldr li{margin:5px 0}
.qa h3{font-size:17px;margin:18px 0 4px}.qa p{margin:0}
.colmeta{font-size:14px;color:var(--mute)}.byline{font-size:14px;color:var(--mute);border-top:1px solid var(--line);margin-top:30px;padding-top:12px}
.colcard .k{font-size:14px;color:var(--mute);margin:6px 0 0}
"""
import ig as IG
EXTRA_CSS += IG.CSS + '''
.eyebrow{display:flex;align-items:center;gap:8px;flex-wrap:wrap;font-size:14px;color:var(--mute);margin:0 0 6px}
.related{margin-top:36px;padding-top:20px;border-top:1px solid var(--line)}.related h2{font-size:22px}
.ctab{display:flex;gap:16px;align-items:center;justify-content:space-between;flex-wrap:wrap;background:var(--field);color:var(--fieldInk);border-radius:16px;padding:18px 22px;margin-top:28px}.ctab h3{margin:0}.ctab p{margin:4px 0 0;opacity:.85}
.gcard{display:grid;grid-template-columns:48px 1fr;gap:4px 14px;align-items:start}.gcard .gi{grid-row:span 2;width:48px;height:48px;border-radius:14px;background:var(--field);display:grid;place-items:center}.gcard h3{margin:0}
.cols>div>h2{margin-top:28px}.locator{max-width:340px;margin:0}.colhead{grid-template-columns:minmax(0,1fr) 340px}@media(max-width:860px){.colhead{grid-template-columns:minmax(0,1fr)}}
'''
GSC = (f'<meta name="google-site-verification" content="{e(CFG["gsc_verify"])}">\n' if CFG.get('gsc_verify') else '') + (f'<meta name="msvalidate.01" content="{e(CFG["bing_verify"])}">\n' if CFG.get('bing_verify') else '')
NAV = [('/', '全台動態儀表板'), ('/projects/', '開發案總覽'), ('/column/', '相信土地專欄'), ('/listings/', '在售農地'), ('/guide/', '投資指南'), ('/submit/', '委託刊登')]
LOGO = '<svg width="36" height="36" viewBox="0 0 36 36" aria-hidden="true"><rect x="1" y="1" width="34" height="34" rx="8" fill="#e8d36a"/><g fill="none" stroke="#1d4a33" stroke-linecap="round" stroke-linejoin="round"><path d="M10.5 8.5V27" stroke-width="3.4"/><path d="M10.5 9H16.6a4.1 4.1 0 0 1 0 8.2H10.5" stroke-width="3"/><path d="M10.5 17.2H17.6a4.9 4.9 0 0 1 0 9.8" stroke-width="3"/><path d="M10.5 27H28.5" stroke-width="3.4"/></g><path d="M26 12.2a3.4 3.4 0 0 1 3.4 3.4c0 2.6-3.4 6.2-3.4 6.2s-3.4-3.6-3.4-6.2a3.4 3.4 0 0 1 3.4-3.4z" fill="#d4502a"/><circle cx="26" cy="15.6" r="1.2" fill="#e8d36a"/></svg>'
FAVICON = '<svg xmlns="http://www.w3.org/2000/svg" width="36" height="36" viewBox="0 0 36 36"><rect x="1" y="1" width="34" height="34" rx="8" fill="#1d4a33"/><g fill="none" stroke="#e8d36a" stroke-linecap="round" stroke-linejoin="round"><path d="M10.5 8.5V27" stroke-width="3.4"/><path d="M10.5 9H16.6a4.1 4.1 0 0 1 0 8.2H10.5" stroke-width="3"/><path d="M10.5 17.2H17.6a4.9 4.9 0 0 1 0 9.8" stroke-width="3"/><path d="M10.5 27H28.5" stroke-width="3.4"/></g><path d="M26 12.2a3.4 3.4 0 0 1 3.4 3.4c0 2.6-3.4 6.2-3.4 6.2s-3.4-3.6-3.4-6.2a3.4 3.4 0 0 1 3.4-3.4z" fill="#d4502a"/><circle cx="26" cy="15.6" r="1.2" fill="#1d4a33"/></svg>'


def broker_line():
    s = f"經紀業：{e(CFG.get('broker_name') or '')}"
    if CFG.get('broker_license'): s += f"（{e(CFG['broker_license'])}）"
    if CFG.get('company_address'): s += f"<br>地址：{e(CFG['company_address'])}"
    if CFG.get('agent_license'): s += f"<br>不動產經紀人：{e(CFG.get('agent_name', ''))}（證書 {e(CFG['agent_license'])}）"
    return s


def contact_html():
    out = []
    if CFG.get('contact_name'):
        lic = f"（營業員 {e(CFG['sales_license'])}）" if CFG.get('sales_license') else ''
        out.append(f"<li>聯絡人：{e(CFG['contact_name'])}{lic}</li>")
    if CFG.get('phone'): out.append(f"<li>電話：<a href=\"tel:{e(CFG['phone'].replace('-', ''))}\">{e(CFG['phone'])}</a></li>")
    if CFG.get('line_id'): out.append(f"<li>LINE：{e(CFG['line_id'])}</li>")
    if CFG.get('email'): out.append(f"<li>Email：{e(CFG['email'])}</li>")
    return ''.join(out)


def site_header(active):
    call = f'<a class="btn" style="min-height:40px;background:var(--rice);color:#1b2a12;border:0;flex:none" href="tel:{e(CFG["phone"].replace("-", ""))}">來電 {e(CFG["phone"])}</a>' if CFG.get('phone') else ''
    nav = ''.join(f'<a href="{h}"{" class=on" if h == active else ""}>{t}</a>' for h, t in NAV)
    return (f'<header><div class="bar"><a class="logo" href="/">{LOGO}<span><b>{e(BRAND)}</b><small>{e(CFG.get("brand_en", ""))}・{e(CFG.get("tagline", ""))}</small></span></a>'
            f'<nav aria-label="主選單">{nav}</nav>{call}</div></header>')


def page(path, title, desc, body, jsonld=None, active='/', robots='index,follow', og_type='website', head_extra='', og=None):
    url = SITE + path
    ogi = f'{SITE}/assets/og/{og}.png' if og else f'{SITE}/assets/og.png'
    ld = ''
    for j in (jsonld or []):
        ld += '<script type="application/ld+json">' + json.dumps(j, ensure_ascii=False).replace('<', '\\u003c') + '</script>\n'
    return f"""<!DOCTYPE html>
<html lang="zh-Hant-TW">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{e(title)}</title>
<meta name="description" content="{e(desc)}">
<meta name="robots" content="{robots}{",max-image-preview:large" if robots.startswith("index") else ""}">
<link rel="canonical" href="{e(url)}">
<meta property="og:type" content="{og_type}">
<meta property="og:site_name" content="{e(BRAND)}">
<meta property="og:title" content="{e(title)}">
<meta property="og:description" content="{e(desc)}">
<meta property="og:url" content="{e(url)}">
<meta property="og:image" content="{ogi}">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta property="og:image:alt" content="{e(title)}">
<meta name="twitter:image" content="{ogi}">
<meta property="og:locale" content="zh_TW">
<meta name="twitter:card" content="summary_large_image">
<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">
{GSC}<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Sans+TC:wght@400;500;700;900&display=swap" rel="stylesheet">
<link rel="stylesheet" href="/assets/site.css">
{head_extra}{ld}</head>
<body>
{site_header(active)}
<main>
{body}
</main>
<footer class="band foot" style="background:var(--field);color:var(--fieldInk);font-size:14px"><div class="wrap fgrid">
<div><b style="font-size:17px">{e(BRAND)}｜{e(CFG.get('tagline', ''))}</b><p>整理全台區段徵收、特定區、新訂擴大都市計畫與產業園區進度，協助投資人評估農地的未來發展潛力。</p><p>{broker_line()}</p><ul>{contact_html()}</ul></div>
<div><b>依區域</b><ul>{''.join(f'<li><a href="/county/{CSLUG[c]}/">{e(c)}農地開發案</a></li>' for c in COUNTIES[:10])}</ul></div>
<div><b>&nbsp;</b><ul>{''.join(f'<li><a href="/county/{CSLUG[c]}/">{e(c)}農地開發案</a></li>' for c in COUNTIES[10:])}</ul></div>
<div><b>投資指南</b><ul><li><a href="/guide/expropriation/">區段徵收與重劃差在哪</a></li><li><a href="/guide/risk/">投資風險與長期佈局</a></li><li><a href="/guide/tax/">農地稅負一張圖</a></li><li><a href="/guide/family-office/">家族辦公室與資產傳承</a></li><li><a href="/about/">關於與免責聲明</a></li></ul></div>
</div><p class="wrap note" style="color:var(--fieldInk);opacity:.8;margin-top:18px">本網站提供資訊整理與試算，非投資建議；開發案資訊以政府公告為準。新聞資料更新於 {e(NEWS_AT)}。</p></footer>
</body>
</html>"""


def hero(cb, eyebrow, title, lede, kpis=None):
    """所有頁面共用頁首：導覽路徑、分類標籤、標題、導言、關鍵數字。"""
    k = ('<div class="kpis">' + ''.join(f'<div><b>{v}</b><span>{e(l)}</span></div>' for v, l in kpis) + '</div>') if kpis else ''
    return f'{cb}<p class="eyebrow">{eyebrow}</p><h1>{e(title)}</h1><p class="lede muted">{e(lede)}</p>{k}'


def cta(title, sub, href, btn='填寫委託表單'):
    return f'<div class="ctab"><div><h3>{e(title)}</h3><p>{e(sub)}</p></div><a class="btn" style="background:var(--rice);color:#1b2a12;border:0" href="{href}">{e(btn)} →</a></div>'


def related(items, title='延伸閱讀'):
    """items: [(href, title, sub)]"""
    if not items: return ''
    return f'<nav class="related" aria-label="{e(title)}"><h2>{e(title)}</h2><div class="pgrid">' + ''.join(f'<a class="pcard" href="{h}"><h3>{e(t)}</h3><p class="small muted" style="margin:0">{e(s)}</p></a>' for h, t, s in items) + '</div></nav>'


GUIDE_IC = {'/guide/expropriation/': 'grid', '/guide/risk/': 'shield', '/guide/tax/': 'coin', '/guide/family-office/': 'people'}


# ---------- 台灣地圖（SVG） ----------
OUTLINE = [[121.537, 25.297], [121.75, 25.15], [122.0, 25.01], [121.84, 24.86], [121.87, 24.6], [121.8, 24.45], [121.62, 23.98], [121.52, 23.6], [121.4, 23.1], [121.15, 22.75], [120.9, 22.35], [120.85, 21.9], [120.72, 21.93], [120.58, 22.37], [120.44, 22.47], [120.27, 22.6], [120.18, 22.88], [120.15, 23.0], [120.07, 23.15], [120.15, 23.38], [120.2, 23.78], [120.3, 23.93], [120.42, 24.07], [120.5, 24.27], [120.58, 24.4], [120.63, 24.5], [120.85, 24.7], [120.92, 24.85], [121.08, 25.05], [121.18, 25.08], [121.35, 25.12], [121.41, 25.18], [121.52, 25.29]]
X = lambda lng: (lng - 119.9) * 91.5
Y = lambda lat: (25.45 - lat) * 100


def map_svg(projects, view=(0, 0, 200, 370), highlight=None):
    vx, vy, vw, vh = view
    r = vw * .02
    land = 'M' + 'L'.join(f'{X(a):.1f} {Y(b):.1f}' for a, b in OUTLINE) + 'Z'
    ridge = 'M' + 'L'.join(f'{X(a):.1f} {Y(b):.1f}' for a, b in [[121.55, 24.9], [121.35, 24.4], [121.1, 23.9], [120.95, 23.4], [120.8, 22.9], [120.78, 22.3]])
    pins = ''
    for p in projects:
        s = stage_of(p['step'])
        x, y = X(p['lng']), Y(p['lat'])
        rr = r * 1.4 if p['id'] == highlight else r
        pins += (f'<a href="/project/{p["id"]}/" aria-label="{e(p["name"])}"><title>{e(p["name"])}（{STAGE[s]}）</title>'
                 f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rr * 2:.2f}" fill="var(--{s})" opacity=".22"/>'
                 f'<circle class="core" cx="{x:.1f}" cy="{y:.1f}" r="{rr:.2f}" fill="var(--{s})" stroke="#fff" stroke-width="{rr * .3:.2f}"/></a>')
    return (f'<svg class="mapsvg" viewBox="{vx} {vy} {vw} {vh}" role="img" aria-label="台灣開發案分布地圖">'
            f'<rect x="-50" y="-50" width="300" height="470" fill="var(--soft)"/>'
            f'<path d="{land}" fill="light-dark(#d9e6cf,#203a2a)" stroke="light-dark(#9db592,#3e6b4d)" stroke-width=".6"/>'
            f'<path d="{ridge}" fill="none" stroke="light-dark(#b7cba8,#2e5039)" stroke-width="2.2" stroke-linecap="round"/>{pins}</svg>')


def legend():
    return ('<div class="legend"><span><i class="dot" style="background:var(--pre)"></i>開發前（規劃・審議）</span>'
            '<span><i class="dot" style="background:var(--mid)"></i>開發中（公告・工程）</span>'
            '<span><i class="dot" style="background:var(--post)"></i>開發後（配地・成熟）</span></div>')


def tag(p):
    s = stage_of(p['step'])
    return f'<span class="tag t-{s}">{STAGE[s]}</span>'


def pcard(p):
    n = news_of(p['id'])
    latest = f'<p class="small" style="margin:6px 0 0">最新：{e(n[0]["title"])}{"<span class=newtag>新</span>" if is_recent(n[0]) else ""}</p>' if n else ''
    return (f'<a class="pcard" href="/project/{p["id"]}/">{tag(p)} <span class="small muted">{e(p["county"])}・{e(p["town"])}</span>'
            f'<h3>{e(p["name"])}</h3><span class="small muted">{e(p["type"])}・目前：{STEPS[p["step"]]}</span>{latest}</a>')


def news_html(items, limit=6):
    if not items: return '<p class="note">目前尚無收錄報導，每月 1 日自動更新。</p>'
    out = ''
    for it in items[:limit]:
        u = safe_url(it.get('url'))
        t = f'<a href="{e(u)}" target="_blank" rel="nofollow noopener noreferrer">{e(it["title"])}</a>' if u else f'<b>{e(it["title"])}</b>'
        summ = '<p class="small muted" style="margin:2px 0 0">' + e(it['summary']) + '</p>' if it.get('summary') else ''
        newt = '<span class=newtag>新</span>' if is_recent(it) else ''
        out += (f'<div class="news"><span class="small muted">{e(it.get("date"))}・{e(it.get("source"))}</span>'
                f'{newt}<br>{t}{summ}</div>')
    return out


def crumbs(items):
    html_ = ' › '.join(f'<a href="{h}">{e(t)}</a>' if h else e(t) for t, h in items)
    ld = {'@context': 'https://schema.org', '@type': 'BreadcrumbList', 'itemListElement': [
        {'@type': 'ListItem', 'position': i + 1, 'name': t, **({'item': SITE + h} if h else {})} for i, (t, h) in enumerate(items)]}
    return f'<div class="crumb" role="navigation" aria-label="導覽路徑">{html_}</div>', ld


ORG = {'@context': 'https://schema.org', '@type': 'RealEstateAgent', 'name': f"{BRAND}｜{CFG.get('broker_name', '')}",
       'url': SITE + '/', 'areaServed': '台灣', 'description': '全台區段徵收與農地開發潛力資訊平台'}
if CFG.get('phone'): ORG['telephone'] = CFG['phone']
if CFG.get('company_address'): ORG['address'] = {'@type': 'PostalAddress', 'streetAddress': CFG['company_address'], 'addressRegion': '臺中市', 'addressCountry': 'TW'}
if CFG.get('contact_name'): ORG['employee'] = {'@type': 'Person', 'name': CFG['contact_name'], 'telephone': CFG.get('phone', '')}
ORG['legalName'] = CFG.get('broker_name', '')
if CFG.get('email'): ORG['email'] = CFG['email']

PAGES = []  # (path, lastmod, priority)
OGQ = {}  # slug -> (title, sub, color)


def og(slug, title, sub, col='#1d4a33'):
    OGQ[slug] = (title, sub, col)
    return slug


def write(path, content, lastmod=None, prio='0.6', sitemap=True):
    fp = os.path.join(OUT, path.lstrip('/'))
    if path.endswith('/'): fp = os.path.join(fp, 'index.html')
    os.makedirs(os.path.dirname(fp), exist_ok=True)
    open(fp, 'w', encoding='utf-8').write(content)
    if sitemap: PAGES.append((path, lastmod or NEWS_AT or TODAY, prio))



# ---------- SEO 圖表（伺服器端產生的 SVG，文字可被搜尋引擎讀取） ----------
SC = {'pre': '#2f6db0', 'mid': '#d4502a', 'post': '#2f8a57'}
_cid = [0]


def _nid():
    _cid[0] += 1
    return f'c{_cid[0]}'


def figure(svg, caption):
    return f'<figure class="chart">{svg}<figcaption>{e(caption)}</figcaption></figure>'


def svg_open(w, h, title, desc):
    i = _nid()
    return (f'<svg viewBox="0 0 {w} {h}" role="img" aria-labelledby="{i}t {i}d" xmlns="http://www.w3.org/2000/svg" font-family="Noto Sans TC,system-ui,sans-serif">'
            f'<title id="{i}t">{e(title)}</title><desc id="{i}d">{e(desc)}</desc>')


def chart_hbar(rows, title, desc, caption, unit='', w=480, lab=150, href=None):
    """rows: [(label, value, color, link)]"""
    rh, top = 30, 8
    h = top + rh * len(rows) + 8
    mx = max([r[1] for r in rows] + [1])
    s = svg_open(w, h, title, desc)
    for i, (label, v, col, link) in enumerate(rows):
        y = top + i * rh
        bw = (w - lab - 46) * v / mx
        t = f'<text x="{lab - 8}" y="{y + 19}" text-anchor="end" font-size="14" fill="currentColor">{e(label)}</text>'
        if link: t = f'<a href="{e(link)}">{t}</a>'
        s += t + f'<rect x="{lab}" y="{y + 6}" width="{bw:.1f}" height="18" rx="4" fill="{col}"/><text x="{lab + bw + 6:.1f}" y="{y + 20}" font-size="14" font-weight="700" fill="currentColor">{v}{e(unit)}</text>'
    return figure(s + '</svg>', caption)


def chart_stacked_regions(caption):
    rows = [(r, [sum(1 for p in P if region_of(p['county']) == r and stage_of(p['step']) == k) for k in STAGE]) for r in REG]
    w, lab, rh, top = 480, 60, 34, 34
    h = top + rh * len(rows) + 10
    mx = max(sum(v) for _, v in rows) or 1
    desc = '；'.join(f"{r}：開發前 {v[0]} 案、開發中 {v[1]} 案、開發後 {v[2]} 案" for r, v in rows)
    s = svg_open(w, h, '全台各區農地開發案階段分布', desc)
    lx = lab
    for k, t in STAGE.items():
        s += f'<rect x="{lx}" y="6" width="12" height="12" rx="3" fill="{SC[k]}"/><text x="{lx + 17}" y="17" font-size="13" fill="currentColor">{t}</text>'
        lx += 90
    for i, (r, v) in enumerate(rows):
        y = top + i * rh; x = lab
        s += f'<text x="{lab - 8}" y="{y + 19}" text-anchor="end" font-size="14" fill="currentColor">{r}</text>'
        for k, n in zip(STAGE, v):
            bw = (w - lab - 50) * n / mx
            if n: s += f'<rect x="{x:.1f}" y="{y + 5}" width="{bw:.1f}" height="20" fill="{SC[k]}"/><text x="{x + bw / 2:.1f}" y="{y + 19}" text-anchor="middle" font-size="12" fill="#fff" font-weight="700">{n}</text>'
            x += bw
        s += f'<text x="{x + 6:.1f}" y="{y + 20}" font-size="14" font-weight="700" fill="currentColor">{sum(v)} 案</text>'
    return figure(s + '</svg>', caption)


def chart_progress(projects, title, caption):
    """每個開發案一列，七步驟進度格。"""
    w, lab, rh, top = 560, 190, 30, 44
    cw = (w - lab - 10) / 7
    h = top + rh * len(projects) + 8
    desc = '；'.join(f"{p['name']}：{STEPS[p['step']]}" for p in projects)
    s = svg_open(w, h, title, desc)
    for j, t in enumerate(['都計', '公益審議', '徵收公告', '補償配地', '工程', '分配標售', '成熟']):
        s += f'<text x="{lab + j * cw + cw / 2:.1f}" y="{top - 12}" text-anchor="middle" font-size="12" fill="currentColor" opacity=".75">{t}</text>'
    for i, p in enumerate(projects):
        y = top + i * rh
        nm = re.sub(r'（.*?）', '', p['name'])
        nm = nm if len(nm) <= 12 else nm[:11] + '…'
        s += f'<a href="/project/{p["id"]}/"><text x="{lab - 8}" y="{y + 19}" text-anchor="end" font-size="13" fill="currentColor">{e(nm)}</text></a>'
        for j in range(7):
            col = SC[stage_of(p['step'])] if j <= p['step'] else 'rgba(127,127,127,.18)'
            op = '1' if j == p['step'] else '.55' if j < p['step'] else '1'
            s += f'<rect x="{lab + j * cw + 1:.1f}" y="{y + 6}" width="{cw - 2:.1f}" height="18" rx="3" fill="{col}" opacity="{op}"/>'
    return figure(s + '</svg>', caption)


def chart_scatter(projects, title, caption, highlight=None, label_n=8, w=520, h=400, focus=None):
    m = {'l': 44, 'r': 14, 't': 14, 'b': 40}
    iw, ih = w - m['l'] - m['r'], h - m['t'] - m['b']
    X_ = lambda v: m['l'] + v / 100 * iw
    Y_ = lambda v: m['t'] + (1 - v / 100) * ih
    pts = [(p, pot(p)) for p in projects]
    desc = '；'.join(f"{p['name']}：發展性 {t['dev']}、基期 {t['base']}" for p, t in sorted(pts, key=lambda x: -x[1]['pri'])[:15])
    s = svg_open(w, h, title, desc)
    s += f'<rect x="{X_(0)}" y="{Y_(100)}" width="{X_(50) - X_(0)}" height="{Y_(60) - Y_(100)}" fill="{SC["post"]}" opacity=".12"/>'
    s += f'<rect x="{X_(0)}" y="{Y_(100)}" width="{iw}" height="{ih}" fill="none" stroke="currentColor" stroke-opacity=".25"/>'
    s += f'<line x1="{X_(50)}" y1="{Y_(0)}" x2="{X_(50)}" y2="{Y_(100)}" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="4 4"/><line x1="{X_(0)}" y1="{Y_(60)}" x2="{X_(100)}" y2="{Y_(60)}" stroke="currentColor" stroke-opacity=".3" stroke-dasharray="4 4"/>'
    s += f'<text x="{X_(2)}" y="{Y_(95)}" font-size="13" font-weight="700" fill="{SC["post"]}">優先長期佈局</text><text x="{X_(98)}" y="{Y_(95)}" text-anchor="end" font-size="12" fill="currentColor" opacity=".7">動能強・價格已反映</text>'
    s += f'<text x="{X_(2)}" y="{Y_(3)}" font-size="12" fill="currentColor" opacity=".7">低價但動能弱</text><text x="{X_(98)}" y="{Y_(3)}" text-anchor="end" font-size="12" fill="currentColor" opacity=".7">避開</text>'
    s += f'<text x="{X_(50)}" y="{h - 10}" text-anchor="middle" font-size="13" fill="currentColor">價格基期（低 → 高）</text><text transform="translate(16 {Y_(50)}) rotate(-90)" text-anchor="middle" font-size="13" fill="currentColor">發展性（低 → 高）</text>'
    placed = []
    lab = set(p['id'] for p, _ in sorted(pts, key=lambda x: -x[1]['pri'])[:label_n])
    if highlight: lab = {highlight}
    if focus: lab = set(focus)
    for p, t in sorted(pts, key=lambda x: x[0]['id'] == highlight or bool(focus and x[0]['id'] in focus)):
        jx = (ord(p['id'][0]) % 7 - 3) * .6; jy = (ord(p['id'][1]) % 7 - 3) * .6
        cx, cy = X_(t['base'] + jx), Y_(t['dev'] + jy)
        hl = p['id'] == highlight or bool(focus and p['id'] in focus)
        r = 9 if hl else 6
        op = '1' if (not (highlight or focus) or hl) else '.3'
        s += f'<a href="/project/{p["id"]}/"><circle cx="{cx:.1f}" cy="{cy:.1f}" r="{r}" fill="{SC[stage_of(p["step"])]}" opacity="{op}" stroke="#fff" stroke-width="{2 if hl else 1.2}"><title>{e(p["name"])}</title></circle></a>'
        if p['id'] in lab:
            nm = re.sub(r'（.*?）', '', p['name'])[:10]
            anchor = 'end' if cx > w - 140 else 'start'
            dx = -12 if anchor == 'end' else 12
            tw = len(nm) * 13.5
            x0 = cx + dx - (tw if anchor == 'end' else 0)
            ty = cy + 4
            for off in (0, -16, 16, -32, 32, -48, 48, -64, 64):
                ty = cy + 4 + off
                if all(not (x0 < bx + bw and bx < x0 + tw and abs(ty - by) < 16) for bx, by, bw in placed): break
            placed.append((x0, ty, tw))
            if abs(ty - cy - 4) > 1: s += f'<line x1="{cx:.1f}" y1="{cy:.1f}" x2="{cx + dx * .6:.1f}" y2="{ty - 4:.1f}" stroke="currentColor" stroke-opacity=".4"/>'
            s += f'<text x="{cx + dx:.1f}" y="{ty:.1f}" text-anchor="{anchor}" font-size="13" font-weight="{700 if hl else 400}" fill="currentColor" stroke="var(--bg,#fff)" stroke-width="3" paint-order="stroke">{e(nm)}</text>'
    return figure(s + '</svg>', caption)


LEAF = ('<link rel="stylesheet" href="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.css">\n'
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/leaflet.min.js" defer></script>\n'
        '<script src="/assets/pmap.js?v=' + __import__('hashlib').md5(open(D('src/pmap.js'), 'rb').read()).hexdigest()[:8] + '" defer></script>\n')

# ---------- 開始輸出 ----------
if os.path.exists(OUT): shutil.rmtree(OUT)
os.makedirs(D('dist/assets'))
open(D('dist/assets/site.css'), 'w', encoding='utf-8').write(BASE_CSS + EXTRA_CSS)
shutil.copy(D('src/pmap.js'), D('dist/assets/pmap.js'))
open(D('dist/assets/favicon.svg'), 'w', encoding='utf-8').write(FAVICON)
os.makedirs(D('dist/data'))
for f in ('news.json', 'listings.json', 'projects.json') + (('amenities.json',) if AMEN else ()):
    shutil.copy(D('data', f), D('dist/data', f))

counts = {k: sum(1 for p in P if stage_of(p['step']) == k) for k in STAGE}
ranked_news = sorted(((p, it) for p in P for it in news_of(p['id'])), key=lambda t: dkey(t[1].get('date')), reverse=True)

# ===== 首頁 =====
GUIDES_HOME = [('/guide/expropriation/', '區段徵收七步驟與三種開發方式', '一塊地最後變成什麼？用 100 格方塊看懂領回比例。'),
               ('/guide/risk/', '範圍內還是外溢圈？', '六個風險面向與外溢圈示意，找出低基期、高發展性的地。'),
               ('/guide/tax/', '農地稅負一張圖', '持有、徵收、抵價地、建地四階段的稅負與 5 年列管。'),
               ('/guide/family-office/', '家族傳承怎麼配置農地', '給代書、會計師與家辦的三層配置與傳承順序。')]
rows = ''
for p in sorted(P, key=lambda p: dkey((news_of(p['id']) or [{}])[0].get('date')), reverse=True):
    n = news_of(p['id'])
    lat = (f'<span class="small muted">{e(n[0].get("date"))}・{e(n[0].get("source"))}</span>{"<span class=newtag>新</span>" if is_recent(n[0]) else ""}<br>{e(n[0]["title"])}') if n else '<span class="small muted">尚無報導</span>'
    rows += (f'<tr data-r="{region_of(p["county"])}" data-s="{stage_of(p["step"])}"><td><a href="/project/{p["id"]}/"><b>{e(p["name"])}</b></a><br>'
             f'<span class="small muted">{region_of(p["county"])}・{e(p["county"])}{e(p["town"])}・{e(p["type"])}</span></td>'
             f'<td>{tag(p)}<br><span class="small muted">{STEPS[p["step"]]}</span></td><td>{lat}</td></tr>')
feed = ''.join(f'<div class="news"><span class="small muted">{e(it.get("date"))}・{e(it.get("source"))}・{e(p["county"])}</span>{"<span class=newtag>新</span>" if is_recent(it) else ""}<br><a href="/project/{p["id"]}/">{e(it["title"])}</a></div>' for p, it in ranked_news[:8])
top = sorted(P, key=lambda p: pot(p)['pri'], reverse=True)[:6]
home = f"""
<section class="band"><div class="wrap hero">
<div>
<p class="small" style="font-weight:700;color:var(--field);margin:0 0 8px">會變成建地的農地，先看它離哪個開發案多近</p>
<h1>全台農地開發動態儀表板</h1>
<p class="lead">{BRAND}整理全台 {len(P)} 個規劃中、辦理中與已完成的區段徵收、特定區、新訂擴大都市計畫與產業園區，每月更新最新報導，幫助投資人找出基期低、發展性高的農地。</p>
<div class="chips" style="margin-top:20px"><a class="btn pri" href="/projects/">看全部開發案 →</a><a class="btn" href="#dash">看最新動態 ↓</a><a class="btn" href="/tools/#report">潛力報告試算</a><a class="btn" href="/submit/">委託刊登農地</a></div>
<div class="stats"><div><b>{counts['pre']}</b><span>開發前案件</span></div><div><b>{counts['mid']}</b><span>開發中案件</span></div><div><b>{counts['post']}</b><span>開發後案件</span></div><div><b>{len(COUNTIES)}</b><span>涵蓋縣市</span></div></div>
</div>
<div class="mapbox">{map_svg(P)}{legend()}</div>
</div></section>
<section class="band" id="dash"><div class="wrap">
<h2>市場動態儀表板</h2>
<p class="muted">依北、中、南、東區與開發階段篩選，最新報導排在最前面。新聞更新於 <b>{e(NEWS_AT)}</b>，每月 1 日自動更新。</p>
<div class="chips" id="fR" style="margin:12px 0"><button class="chip on" data-v="">全台</button>{''.join(f'<button class="chip" data-v="{r}">{r}</button>' for r in REG)}</div>
<div class="chips" id="fS" style="margin-bottom:12px"><button class="chip on" data-v="">全部階段</button>{''.join(f'<button class="chip" data-v="{k}">{v}</button>' for k, v in STAGE.items())}</div>
<div class="cols">
<div class="scroll" style="max-height:640px;overflow:auto;border:1px solid var(--line);border-radius:14px;padding:0 10px"><table class="stack" id="dT"><thead><tr><th>開發案</th><th>階段</th><th>最新消息</th></tr></thead><tbody>{rows}</tbody></table></div>
<div class="card"><h3>最新消息</h3>{feed}</div>
</div>
</div></section>
<section class="band"><div class="wrap">
<h2>三分鐘看懂農地開發</h2>
<p class="muted">相信土地把最常被問的觀念畫成圖解，先看懂再看案子。</p>
<div class="pgrid" style="margin:14px 0 30px">{''.join(f'<a class="pcard gcard" href="{h}"><span class="gi">{IG.icon_svg(GUIDE_IC[h], 26, '#fff')}</span><h3>{e(t)}</h3><p class="small muted" style="margin:0">{e(d)}</p></a>' for h, t, d in GUIDES_HOME)}</div>
<h2>全台開發案分布</h2>
<div class="charts2">{chart_stacked_regions(f'圖：全台各區區段徵收與農地開發案階段分布（{NEWS_AT}）。中部案件最多，開發前階段的案子占多數。')}
{chart_hbar([(c, sum(1 for p in P if p['county'] == c), SC['mid'] if c == '彰化縣' else '#1d4a33', f'/county/{CSLUG[c]}/') for c in sorted(COUNTIES, key=lambda c: -sum(1 for p in P if p['county'] == c))], '各縣市農地開發案數量', '；'.join(f"{c} {sum(1 for p in P if p['county'] == c)} 案" for c in COUNTIES), '圖：各縣市收錄的區段徵收與特定區開發案數量，點縣市名稱可看該縣市進度。', ' 案', lab=80)}</div>
</div></section>
<section class="band" style="background:var(--soft)"><div class="wrap">
<h2>低基期、高發展性：優先長期佈局</h2>
<p class="muted">依發展動能與價格基期評分，左上象限的開發案最值得長期觀察。<a href="/guide/risk/">看評估方法 →</a></p>
<div class="cols" style="margin-top:14px"><div class="pgrid">{''.join(pcard(p) for p in top)}</div>
{chart_scatter(P, '全台開發案價格基期與發展性矩陣', '圖：全台開發案的價格基期與發展性矩陣，左上角綠色區塊為低基期、高發展性的優先佈局區。')}</div>
<h2 style="margin-top:36px">相信土地專欄：最新評估</h2>
<p class="muted">整理政府公告與新聞，寫給投資者與從業人員的開發評估。<a href="/column/">看全部 {len(COL)} 篇 →</a></p>
<div class="pgrid" style="margin-top:12px">{''.join(f'<a class="pcard colcard" href="/column/{q["id"]}/">{tag(q)}<h3>{e(COL[q["id"]]["t"])}</h3><p class="k">{e(q["county"])}{e(q["town"])}</p></a>' for q in sorted([q for q in P if q['id'] in COL], key=lambda q: (q['county'] != '彰化縣', -pot(q)['pri']))[:6])}</div>
</div></section>
<script>{{const st={{r:'',s:''}};const f=()=>document.querySelectorAll('#dT tbody tr').forEach(t=>t.hidden=!((!st.r||t.dataset.r===st.r)&&(!st.s||t.dataset.s===st.s)));
for(const [id,k] of [['fR','r'],['fS','s']])document.getElementById(id).addEventListener('click',ev=>{{const b=ev.target.closest('[data-v]');if(!b)return;st[k]=b.dataset.v;b.parentNode.querySelectorAll('.chip').forEach(c=>c.classList.toggle('on',c===b));f()}})}}</script>
"""
write('/', page('/', f'全台農地開發動態儀表板：區段徵收、特定區進度與最新消息｜{BRAND}',
                f'整理全台 {len(P)} 個區段徵收、特定區與產業園區開發案的進度與每月最新報導，依北中南東區篩選，找出基期低、發展性高的農地投資機會。',
                home, [ORG, {'@context': 'https://schema.org', '@type': 'WebSite', 'name': BRAND, 'url': SITE + '/'}], og=og('home', '全台農地開發動態儀表板', f'{len(P)} 個區段徵收・特定區進度，每月更新')), prio='1.0')

# ===== 開發案總覽 =====
blocks = ''
for r, cs in REG.items():
    ps = [p for p in P if p['county'] in cs]
    if not ps: continue
    blocks += f'<h2 style="margin-top:32px">{r}（{len(ps)} 案）</h2>'
    for c in cs:
        cp = [p for p in ps if p['county'] == c]
        if cp:
            blocks += f'<h3 style="margin-top:18px"><a href="/county/{CSLUG[c]}/">{e(c)}</a></h3><div class="pgrid">{"".join(pcard(p) for p in cp)}</div>'
cb, cld = crumbs([('首頁', '/'), ('開發案總覽', None)])
write('/projects/', page('/projects/', f'全台區段徵收與農地開發案總覽（{len(P)} 案）｜{BRAND}',
                         '依北、中、南、東區與縣市整理全台區段徵收、特定區、新訂擴大都市計畫與產業園區開發案，附開發階段與最新報導。',
                         f'<section class="band"><div class="wrap">' + hero(cb, '開發案總覽・每月更新', '全台農地開發案總覽', f'共 {len(P)} 案，依北、中、南、東區與縣市排列。點選開發案可看七步驟進度圖、政府出處、地圖與最新報導。', [(len(P), '開發案'), (counts['pre'], '開發前'), (counts['mid'], '開發中'), (counts['post'], '開發後')])
                         + IG.ig_steps(STEPS, title='每個開發案都用這七步驟標示進度') +
                         f'<div class="charts2">{chart_progress(sorted(P, key=lambda p: -p["step"])[:16], "開發進度最快的 16 個開發案", "圖：進度最快的開發案，從都市計畫到發展成熟共七個步驟。")}</div>'
                         f'<div class="cols" style="margin-top:12px"><div>{blocks}</div><div class="mapbox" style="position:sticky;top:90px">{map_svg(P)}{legend()}</div></div></div></section>',
                         [cld, {'@context': 'https://schema.org', '@type': 'Dataset', 'name': '全台區段徵收與農地開發案資料集',
                                'description': f'整理全台 {len(P)} 個區段徵收、特定區、新訂擴大都市計畫與產業園區開發案的位置、規模、開發階段、重點事實與資料來源，每月更新。',
                                'url': SITE + '/projects/', 'keywords': ['區段徵收', '農地', '特定區', '都市計畫', '土地開發'], 'inLanguage': 'zh-TW',
                                'creator': {'@type': 'Organization', 'name': BRAND, 'url': SITE + '/'}, 'dateModified': NEWS_AT or TODAY,
                                'spatialCoverage': {'@type': 'Place', 'name': '台灣'},
                                'distribution': [{'@type': 'DataDownload', 'encodingFormat': 'application/json', 'contentUrl': SITE + '/data/projects.json'}]},
                          {'@context': 'https://schema.org', '@type': 'ItemList', 'name': '全台農地開發案', 'numberOfItems': len(P),
                           'itemListElement': [{'@type': 'ListItem', 'position': i + 1, 'url': f'{SITE}/project/{p["id"]}/', 'name': p['name']} for i, p in enumerate(P)]}],
                         active='/projects/', og=og('projects', '全台農地開發案總覽', f'{len(P)} 案・區段徵收・特定區・產業園區')), prio='0.9')

# ===== 縣市頁 =====
for c in COUNTIES:
    cp = [p for p in P if p['county'] == c]
    xs = [X(p['lng']) for p in cp]; ys = [Y(p['lat']) for p in cp]
    cx, cy = (min(xs) + max(xs)) / 2, (min(ys) + max(ys)) / 2
    w = max(40, max(xs) - min(xs) + 30)
    view = (cx - w / 2, cy - w * .6, w, w * 1.2)
    cnt = {k: sum(1 for p in cp if stage_of(p['step']) == k) for k in STAGE}
    lat_news = sorted(((p, it) for p in cp for it in news_of(p['id'])), key=lambda t: dkey(t[1].get('date')), reverse=True)[:6]
    cn_html = ''.join(f'<div class="news"><span class="small muted">{e(it.get("date"))}・{e(it.get("source"))}</span><br><a href="/project/{p["id"]}/">{e(it["title"])}</a></div>' for p, it in lat_news) or '<p class="note">尚無報導。</p>'
    cb, cld = crumbs([('首頁', '/'), ('開發案總覽', '/projects/'), (c, None)])
    names = '、'.join(p['name'] for p in cp[:4])
    body = (f'<section class="band"><div class="wrap">' + hero(cb, f'{e(region_of(c))}・縣市開發案', f'{c}農地開發案：區段徵收與特定區進度', f'{c}目前收錄 {len(cp)} 個開發案，包括{names}{"等" if len(cp) > 4 else ""}。以下依開發階段整理進度、圖表與最新報導。', [(len(cp), '開發案'), (cnt['pre'], '開發前'), (cnt['mid'], '開發中'), (cnt['post'], '開發後')]) +
            f'<div class="cols"><div><div class="pgrid">{"".join(pcard(p) for p in cp)}</div>'
            f'<h2 style="margin-top:28px">{e(c)}最新開發消息</h2>{cn_html}</div>'
            f'<div class="mapbox">{map_svg(cp, view)}{legend()}</div></div>'
            f'<h2 style="margin-top:32px">{e(c)}開發案進度與潛力圖表</h2><div class="charts2">'
            + chart_progress(sorted(cp, key=lambda p: -p['step']), f'{c}開發案進度圖', f'圖：{c}{len(cp)}個開發案的七步驟進度，顏色代表開發前、開發中與開發後。')
            + chart_scatter(P, f'{c}開發案價格基期與發展性', f'圖：{c}開發案（深色、標名稱）在全台價格基期與發展性矩陣中的位置。', focus=[p['id'] for p in cp])
            + '</div>'
            + cta(f'想在{c}找有開發潛力的農地？', '告訴我們預算與需求，或委託刊登您的農地。', f'/submit/?county={quote(c)}')
            + related([(f'/column/{p["id"]}/', COL[p['id']]['t'], p['name']) for p in cp if p['id'] in COL][:3] + [('/guide/risk/', '範圍內還是外溢圈？', '投資風險六面向')], f'{c}相關專欄與指南')
            + '</div></section>')
    write(f'/county/{CSLUG[c]}/', page(f'/county/{CSLUG[c]}/', f'{c}區段徵收與農地開發案進度（{len(cp)} 案）｜{BRAND}',
                                      f'{c}{len(cp)}個區段徵收、特定區與產業園區開發案的最新進度、階段與報導：{names}。附七步驟進度圖、基期與發展性圖表。', body, [cld], active='/projects/', og=og('county-' + CSLUG[c], f'{c}農地開發案', f'{len(cp)} 案・開發前 {cnt["pre"]}・開發中 {cnt["mid"]}・開發後 {cnt["post"]}')), prio='0.8')

# ===== 開發案頁 =====
for p in P:
    s = stage_of(p['step'])
    pt = pot(p)
    n = news_of(p['id'])
    pr, pr_ok = plan_radius(p)
    am = AMEN.get(p['id']) or {}
    amen_pts = [[x['c'], x['n'], x['lat'], x['lng'], x['d']] for x in am.get('items', [])]
    if am.get('items'):
        amen_html = f'<p class="small muted" style="margin:0 0 8px">計畫中心周邊 {am["radius"] / 1000:.1f} 公里內的生活機能（OpenStreetMap，{e(am.get("updated", ""))} 更新）</p>'
        for cname, ccol in ACAT:
            xs = [x for x in am['items'] if x['c'] == cname]
            top3 = '、'.join(f'{e(x["n"])} {x["d"] / 1000:.1f} 公里' for x in xs[:3]) or '範圍內未標示'
            amen_html += f'<div class="fn"><span class="dot" style="background:{ccol}"></span><b>{cname}</b> <span class="muted small">{len(xs)}{"+" if len(xs) >= 25 else ""} 處</span><br><span class="small">{top3}</span></div>'
    else:
        amen_html = '<p class="note">周邊機能清單逐步建置中；上方地圖預設為臺灣通用電子地圖，已標示學校、車站、醫院與公所等設施。</p>'
    gl = GOV.get(p['id'], [])
    gov_items = ''.join(f'<li><span style="font-size:11px;padding:1px 6px;border-radius:6px;background:var(--soft);border:1px solid var(--line);white-space:nowrap">{GOVK.get(g["k"], "")}</span> <a href="{e(safe_url(g["u"]))}" target="_blank" rel="noopener">{e(g["t"])}</a> <span class="small muted">— {e(g["o"])}</span></li>' for g in gl)
    gov_html = f'<ul class="facts small">{gov_items}</ul>' if gl else '<p class="note">政府出處整理中。</p>'
    if gl and all(g['k'] == 'agency' for g in gl):
        gov_html += '<p class="note">本案尚未找到可直接引用的計畫書圖網址，先列主管機關網站；計畫書圖公開後會補上。</p>'
    near = sorted(((l, hav(p['lat'], p['lng'], float(l['lat']), float(l['lng']))) for l in LIST if l.get('lat') and l.get('lng')), key=lambda t: t[1])
    near = [t for t in near if t[1] <= 5][:6]
    same = [q for q in P if q['county'] == p['county'] and q['id'] != p['id']]
    track = ''.join(f'<div class="{"done" if i < p["step"] else "now" if i == p["step"] else ""}">{t}</div>' for i, t in enumerate(STEPS))
    note = '' if p['type'] == '區段徵收' else f'<p class="note">本案屬「{e(p["type"])}」，非典型區段徵收，進度軌道為近似對照；地主能否領回抵價地依實際開發方式而定。</p>'
    quad = '優先長期佈局（發展性高、基期低）' if pt['top'] else '動能強、價格已部分反映' if pt['dev'] >= 60 else '價格低但動能較弱' if pt['base'] <= 50 else '觀察'
    near_html = ''.join(f'<p style="margin:6px 0"><a href="/tools/#item-{e(l.get("id"))}">{e(l.get("county"))}{e(l.get("town"))} {e(l.get("area"))} 坪・{e(l.get("price"))} 萬/坪</a> <span class="small muted">距 {d:.1f} km</span></p>' for l, d in near) or '<p class="muted small">目前沒有上架物件。有意出售周邊農地的地主，歡迎委託刊登。</p>'
    intro = f'{p["name"]}位於{p["county"]}{p["town"]}，屬{p["type"]}，規模{p["area"] if p["area"] != "—" else "依計畫書公告"}，目前進度為「{STEPS[p["step"]]}」（{STAGE[s]}）。'
    cb, cld = crumbs([('首頁', '/'), (p['county'], f'/county/{CSLUG[p["county"]]}/'), (p['name'], None)])
    col_link = f'<div class="tldr"><b>相信土地專欄</b>：<a href="/column/{p["id"]}/">{e(COL[p["id"]]["t"])}</a><br><span class="small muted">政府公告怎麼說、新聞透露什麼、我們怎麼看，一篇讀完。</span></div>' if p['id'] in COL else ''
    body = f"""<section class="band"><div class="wrap">
{hero(cb, f'{tag(p)} {e(p["type"])}・{e(p["county"])}{e(p["town"])}', p['name'], intro, [(STAGE[s], '開發階段'), (f'{p["step"] + 1}/7', '目前步驟'), (e(p['type']), '開發方式'), (pt['pri'], '佈局優先分數')])}
{IG.ig_steps(STEPS, p['step'], title=f"{p['name']}開發進度", name=p['name'])}{note}
<div class="cols"><div>
{col_link}
<h2>重點事實</h2><ul class="facts">{''.join(f'<li>{e(f)}</li>' for f in p['facts'])}</ul>
{f'<div class="risk"><b>風險提示：</b>{e(p["risk"])}</div>' if p.get('risk') else ''}
<h2>政府出處</h2>{gov_html}
<h2>相關新聞</h2>{news_html(n)}
<p class="note">新聞每月 1 日自動更新；新聞來源：<a href="{e(safe_url(p['src']))}" target="_blank" rel="nofollow noopener noreferrer">{e(p['srcN'])}</a></p>
</div><div>
<div class="card"><h3>相信土地評分</h3>{IG.ig_gauges(p['name'], pt['dev'], pt['base'], pt['pri'])}<p style="margin:10px 0 4px"><b>{quad}</b></p><p class="muted small" style="margin:0">{e(pt['why'])}</p><p class="note">分數為平台初步判斷，請以實價登錄校正。<a href="/guide/risk/">評估方法</a></p></div>
<div class="card" style="margin-top:16px"><h3>周邊 5 公里在售農地</h3>{near_html}<div class="chips" style="margin-top:10px"><a class="btn acc" href="/submit/?project={p['id']}&county={quote(p['county'])}">委託刊登 / 我想找地</a></div></div>
{f'<div class="card" style="margin-top:16px"><h3>{e(p["county"])}其他開發案</h3>' + ''.join(f'<p style="margin:6px 0"><a href="/project/{q["id"]}/">{e(q["name"])}</a> <span class="small muted">{STAGE[stage_of(q["step"])]}</span></p>' for q in same) + '</div>' if same else ''}
</div></div></div></section>
<section class="band" style="background:var(--soft)"><div class="wrap">
<h2>{e(p['name'])}位置與政府土地使用分區圖</h2>
<p class="muted">底圖為內政部國土測繪中心的<b>非都市土地使用分區圖</b>與<b>段籍圖</b>{'，並疊加<b>嘉義市政府都市計畫使用分區圖</b>' if p['county'] == '嘉義市' else ''}：有顏色的是非都市土地，<b>空白區塊是既有都市計畫區</b>。新訂、擴大中的計畫尚未公告，正式範圍請以上方「政府出處」的計畫書圖為準；藍色標記只是位置參考點。</p>
<div class="cols" style="margin-top:14px"><div id="pmap" data-lat="{p['lat']}" data-lng="{p['lng']}" data-cyc="{1 if p['county'] == '嘉義市' else 0}" data-name="{e(p['name'])}" data-amen="{e(json.dumps(amen_pts, ensure_ascii=False, separators=(',', ':')))}" role="region" aria-label="{e(p['name'])}位置與政府土地使用分區圖"></div>
<div class="card"><h3>周邊生活機能</h3><div id="pmapList">{amen_html}</div>
<h3 style="margin-top:16px">自行查詢地號分區</h3><ul class="facts small">
<li><a href="https://luz.tcd.gov.tw/web/" target="_blank" rel="noopener">全國土地使用分區資料查詢系統</a>（內政部國土管理署）</li>
<li><a href="https://maps.nlsc.gov.tw/" target="_blank" rel="noopener">國土測繪圖資服務雲</a>（內政部國土測繪中心）</li>
<li><a href="https://nsp.tcd.gov.tw/tcdgis/" target="_blank" rel="noopener">國土規劃地理資訊圖台</a>：國土功能分區與環境敏感地區</li></ul></div></div>
{related(([(f'/column/{p["id"]}/', COL[p['id']]['t'], '相信土地專欄')] if p['id'] in COL else []) + [('/guide/expropriation/', '區段徵收七步驟與三種開發方式', '圖解領回比例'), ('/guide/risk/', '範圍內還是外溢圈？', '投資風險六面向')])}
</div></section>"""
    desc = f'{p["name"]}（{p["county"]}{p["town"]}）最新進度：{STEPS[p["step"]]}。{p["facts"][0]}。附每月相關新聞、風險提示與周邊農地投資觀點。'
    ld = {'@context': 'https://schema.org', '@type': 'WebPage', 'name': p['name'], 'description': desc, 'url': f'{SITE}/project/{p["id"]}/',
          'dateModified': (NEWS.get(p['id'], {}).get('updatedAt') or NEWS_AT or TODAY),
          'about': {'@type': 'Place', 'name': p['name'], 'address': {'@type': 'PostalAddress', 'addressRegion': p['county'], 'addressLocality': p['town'], 'addressCountry': 'TW'},
                    'geo': {'@type': 'GeoCoordinates', 'latitude': p['lat'], 'longitude': p['lng']}}}
    write(f'/project/{p["id"]}/', page(f'/project/{p["id"]}/', f'{p["name"]}進度與最新消息｜{p["county"]}{p["town"]}｜{BRAND}', desc[:150], body, [cld, ld],
                                      active='/projects/', og_type='article', head_extra=LEAF, og=og('p-' + p['id'], p['name'], f"{p['county']}{p['town']}・{p['type']}・{STEPS[p['step']]}", SC[s])), lastmod=(NEWS.get(p['id'], {}).get('updatedAt') or NEWS_AT), prio='0.8')


# ===== 相信土地專欄 =====
def column_page(p, c):
    pt = pot(p)
    s_ = stage_of(p['step'])
    path = f'/column/{p["id"]}/'
    upd = NEWS.get(p['id'], {}).get('updatedAt') or NEWS_AT or TODAY
    gl = GOV.get(p['id'], [])
    n = news_of(p['id'])
    tbl = (f'<div class="scroll"><table><tbody>'
           f'<tr><th scope="row">計畫名稱</th><td><a href="/project/{p["id"]}/">{e(p["name"])}</a></td></tr>'
           f'<tr><th scope="row">位置</th><td>{e(p["county"])}{e(p["town"])}</td></tr>'
           f'<tr><th scope="row">開發方式</th><td>{e(p["type"])}</td></tr>'
           f'<tr><th scope="row">規模</th><td>{e(p["area"] if p["area"] != "—" else "依計畫書公告")}</td></tr>'
           f'<tr><th scope="row">目前進度</th><td>{e(STEPS[p["step"]])}（{STAGE[s_]}）</td></tr>'
           f'<tr><th scope="row">相信土地評分</th><td>發展性 {pt["dev"]}・價格基期 {pt["base"]}・佈局優先 {pt["pri"]}（滿分 100，<a href="/guide/risk/">評分方法</a>）</td></tr>'
           f'</tbody></table></div>')
    secs = ''.join(f'<h2>{e(h)}</h2><p>{e(t)}</p>' for h, t in c['s'])
    pro = ''.join(f'<li>{e(x)}</li>' for x in c['pro'])
    faq = ''.join(f'<div class="qa"><h3>{e(q)}</h3><p>{e(a)}</p></div>' for q, a in c['faq'])
    gov = ''.join(f'<li><a href="{e(safe_url(g["u"]))}" target="_blank" rel="noopener">{e(g["t"])}</a> <span class="small muted">— {e(g["o"])}</span></li>' for g in gl)
    nws = ''.join(f'<li>{e(it.get("date", ""))}・{e(it.get("source", ""))}：<a href="{e(safe_url(it.get("url", "")))}" target="_blank" rel="nofollow noopener noreferrer">{e(it.get("title", ""))}</a></li>' for it in n[:6])
    same = [q for q in P if q['county'] == p['county'] and q['id'] != p['id'] and q['id'] in COL]
    cb, cld = crumbs([('首頁', '/'), ('相信土地專欄', '/column/'), (p['county'], f'/county/{CSLUG[p["county"]]}/'), (p['name'], None)])
    xs, ys = X(p['lng']), Y(p['lat'])
    loc = (f'<figure class="ig locator"><div class="ig-h"><span class="ig-b">相信土地圖解</span><b>{e(p["name"])}在哪裡</b></div><div class="mapbox">{map_svg(P, (xs - 30, ys - 30, 60, 60), highlight=p["id"])}</div>'
           f'<figcaption>{e(p["county"])}{e(p["town"])}，目前在七步驟中的第 {p["step"] + 1} 步「{e(STEPS[p["step"]])}」。<a href="/project/{p["id"]}/">看完整進度圖與政府分區地圖 →</a></figcaption></figure>')
    body = f"""<section class="band"><div class="wrap article">
{hero(cb, f'{tag(p)} 相信土地專欄・{e(p["county"])}{e(p["town"])}・資料更新 {e(upd)}', c['t'], c['d'])}
<div class="tldr"><b>重點摘要</b><ul>{''.join(f'<li>{e(x)}</li>' for x in c['k'])}</ul></div>
<div class="cols colhead"><div>{tbl}</div>{loc}</div>
{secs}
<h2>給從業人員的評估清單</h2><ol>{pro}</ol>
{f'<div class="risk"><b>風險提示：</b>{e(p["risk"])}</div>' if p.get('risk') else ''}
<h2>常見問題</h2>{faq}
<h2>資料來源</h2>
<h3 style="font-size:17px">政府出處</h3><ul class="small">{gov or '<li>整理中</li>'}</ul>
{f'<h3 style="font-size:17px">新聞報導</h3><ul class="small">{nws}</ul>' if nws else ''}
{cta(f'想找{p["name"]}周邊的農地？', '委託刊登或告訴我們預算，由相信土地協助評估。', f'/submit/?project={p["id"]}&county={quote(p["county"])}')}
{related([(f'/column/{q["id"]}/', COL[q['id']]['t'], q['name']) for q in same[:3]] + [(f'/project/{p["id"]}/', f'{p["name"]}進度與地圖', '七步驟進度圖・政府分區地圖・最新新聞')], f'{p["county"]}其他專欄')}
<p class="byline">本文由{e(BRAND)}依政府公開資料與新聞報導整理撰寫，內容以撰寫時點為準，非投資建議；範圍、分區與時程請以主管機關公告為準。{broker_line()}</p>
</div></section>"""
    cites = [g['u'] for g in gl] + [it.get('url') for it in n[:6] if it.get('url')]
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': c['t'], 'description': c['d'], 'inLanguage': 'zh-TW',
          'datePublished': COL_PUB, 'dateModified': max(upd, COL_PUB), 'author': {'@type': 'Organization', 'name': BRAND, 'url': SITE + '/'},
          'publisher': {'@type': 'Organization', 'name': BRAND, 'logo': {'@type': 'ImageObject', 'url': SITE + '/assets/favicon.svg'}},
          'mainEntityOfPage': SITE + path, 'image': f'{SITE}/assets/og/c-{p["id"]}.png', 'articleSection': '相信土地專欄',
          'keywords': ', '.join([p['name'], p['county'] + p['town'], p['type'], '區段徵收', '農地投資', '開發評估']),
          'about': {'@type': 'Place', 'name': p['name'], 'geo': {'@type': 'GeoCoordinates', 'latitude': p['lat'], 'longitude': p['lng']},
                    'address': {'@type': 'PostalAddress', 'addressRegion': p['county'], 'addressLocality': p['town'], 'addressCountry': 'TW'}},
          'citation': cites, 'abstract': ' '.join(c['k'])}
    fq = {'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in c['faq']]}
    write(path, page(path, f'{c["t"]}｜{BRAND}專欄', c['d'][:150], body, [cld, ld, fq], active='/column/', og_type='article', og=og('c-' + p['id'], c['t'], f"相信土地專欄・{p['county']}{p['town']}", SC[s_])), lastmod=max(upd, COL_PUB), prio='0.8')


for p in P:
    if p['id'] in COL: column_page(p, COL[p['id']])

blocks = ''
for r, cs in REG.items():
    ps = [p for p in P if p['county'] in cs and p['id'] in COL]
    if not ps: continue
    blocks += f'<h2>{r}</h2><div class="pgrid" style="margin-top:12px">' + ''.join(
        f'<a class="pcard colcard" href="/column/{p["id"]}/">{tag(p)}<h3>{e(COL[p["id"]]["t"])}</h3><p class="k">{e(p["county"])}{e(p["town"])}・{e(STEPS[p["step"]])}</p></a>' for p in ps) + '</div>'
cb, cld = crumbs([('首頁', '/'), ('相信土地專欄', None)])
cdesc = f'相信土地專欄：依各縣市政府公告與新聞，逐案評估全台 {len(COL)} 個區段徵收、特定區與產業園區的進度、價格與風險，給農地投資者與不動產從業人員參考。'
write('/column/', page('/column/', f'相信土地專欄：全台區段徵收與農地開發評估｜{BRAND}', cdesc,
      f'<section class="band"><div class="wrap">' + hero(cb, '專欄・逐案評估', '相信土地專欄', cdesc, [(len(COL), '篇評估'), (len(REG), '個區域'), (COL_PUB, '最近撰寫')]) +
      f'<div class="tldr"><b>怎麼讀這些文章</b><ul><li>每篇都先列「重點摘要」，再分「官方怎麼說」「新聞透露什麼」「相信土地怎麼看」。</li><li>文末附政府出處與新聞連結，可以自行查證。</li><li>「給從業人員的評估清單」整理帶看與簽約前要確認的事項。</li></ul></div>{blocks}</div></section>',
      [cld, {'@context': 'https://schema.org', '@type': 'CollectionPage', 'name': '相信土地專欄', 'description': cdesc, 'url': SITE + '/column/',
             'hasPart': [{'@type': 'Article', 'headline': COL[p['id']]['t'], 'url': f'{SITE}/column/{p["id"]}/'} for p in P if p['id'] in COL]}],
      active='/column/', og=og('column', '相信土地專欄', f'{len(COL)} 篇區段徵收與農地開發評估')), prio='0.9')

# ===== 投資指南 =====
GUIDES = [('/guide/expropriation/', '區段徵收、市地重劃、農地重劃差在哪？', '一次看懂三種土地開發方式的法源、領回比例、增值空間與風險，以及區段徵收的七個步驟。'),
          ('/guide/risk/', '農地投資風險評估與長期佈局策略', '六個面向評估開發題材農地的風險，用外溢圈圖解範圍內外差異，並依低基期、高發展性排序全台優先佈局的開發案。'),
          ('/guide/tax/', '農地稅負一張圖：土增稅、遺產贈與稅與 5 年列管', '持有、被徵收、領回抵價地、變更為建地四個階段的稅負，以及遺贈稅級距與 5 年列管圖解。'),
          ('/guide/family-office/', '家族辦公室與資產傳承：高資產客戶的農地長期佈局', '寫給代書、會計師、財務顧問與家族辦公室：農地在傳承配置中的角色、持有結構、稅負時間軸、贈與與繼承順序，以及 2026 年特留分修法後的遺囑安排。')]
cb, cld = crumbs([('首頁', '/'), ('投資指南', None)])
write('/guide/', page('/guide/', f'農地投資指南：區段徵收、風險、稅負與傳承圖解｜{BRAND}', '用相信土地圖解看懂區段徵收七步驟、三種開發方式、外溢圈、農地稅負時間軸、5 年列管與家族傳承配置。',
                      f'<section class="band"><div class="wrap">' + hero(cb, '投資指南・圖解', '農地投資指南', '四篇圖解，從開發方式、風險、稅負到家族傳承，先看懂觀念再看案子。') + '<div class="pgrid" style="margin-top:16px">' +
                      ''.join(f'<a class="pcard gcard" href="{h}"><span class="gi">{IG.icon_svg(GUIDE_IC[h], 26, "#fff")}</span><h3>{e(t)}</h3><p class="muted small" style="margin:0">{e(d)}</p></a>' for h, t, d in GUIDES) + '</div></div></section>',
                      [cld], active='/guide/', og=og('guide', '農地投資指南', '區段徵收・風險・稅負・傳承圖解')), prio='0.7')


def article(path, title, desc, inner, extra_ld=None, tldr=None):
    cb, cld = crumbs([('首頁', '/'), ('投資指南', '/guide/'), (title, None)])
    slug = 'g-' + path.strip('/').split('/')[-1]
    ld = {'@context': 'https://schema.org', '@type': 'Article', 'headline': title, 'description': desc, 'inLanguage': 'zh-TW', 'image': f'{SITE}/assets/og/{slug}.png',
          'datePublished': '2026-11-20', 'dateModified': NEWS_AT or TODAY, 'author': {'@type': 'Organization', 'name': BRAND, 'url': SITE + '/'}, 'publisher': {'@type': 'Organization', 'name': BRAND}, 'mainEntityOfPage': SITE + path}
    tl = f'<div class="tldr"><b>重點摘要</b><ul>{"".join(f"<li>{x}</li>" for x in tldr)}</ul></div>' if tldr else ''
    rel = related([(h, t, d) for h, t, d in GUIDES if h != path], '其他圖解指南')
    write(path, page(path, f'{title}｜{BRAND}', desc[:155], f'<section class="band"><div class="wrap article">' + hero(cb, '投資指南・相信土地圖解', title, desc) + tl + inner
                     + cta('想評估手上的農地？', '告訴我們地段地號，相信土地協助查分區、範圍與行情。', '/submit/') + rel + '</div></section>',
                     [cld, ld] + (extra_ld or []), active='/guide/', og_type='article', og=og(slug, title, '相信土地圖解・投資指南')), prio='0.7')


FAQ = [('區段徵收可以領回多少土地？', '抵價地總面積以徵收總面積 50% 為原則，不得少於 40%；曾經農地重劃者不得少於 45%。實際比例以內政部核定為準。'),
       ('區段徵收和市地重劃最大的差別是什麼？', '區段徵收會先把土地全部徵收，再發還抵價地，並可把農地變更為住宅、商業或產業用地；市地重劃不移轉所有權，只重新分配位置，地主扣除負擔後領回建築用地。'),
       ('不想領回土地可以嗎？', '可以選擇領取現金補償，補償按徵收當期市價計算。'),
       ('區段徵收領回抵價地要繳土地增值稅嗎？', '被區段徵收的土地免徵土地增值稅；領回抵價地後第一次移轉，土地增值稅減徵 40%。')]
article('/guide/expropriation/', '區段徵收、市地重劃、農地重劃差在哪？', GUIDES[0][2], f"""
{IG.ig_land_split()}
<h2>三種開發方式比較表</h2>
<div class="scroll"><table><thead><tr><th></th><th>區段徵收</th><th>市地重劃</th><th>農地重劃</th></tr></thead><tbody>
<tr><td><b>法源</b></td><td>土地徵收條例</td><td>平均地權條例</td><td>農地重劃條例</td></tr>
<tr><td><b>土地所有權</b></td><td>先全部徵收，再發還一部分</td><td>不移轉，重新分配位置</td><td>不移轉，重新分配位置</td></tr>
<tr><td><b>地主拿回什麼</b></td><td>現金補償（按市價）或申請領回抵價地</td><td>扣除負擔後的建築用地</td><td>扣除負擔後的農地</td></tr>
<tr><td><b>領回比例</b></td><td>抵價地以 50% 為原則，不得少於 40%（曾經農地重劃者不少於 45%）</td><td>公共設施及費用負擔原則上不超過 45%</td><td>負擔較低，多為農路、水路用地</td></tr>
<tr><td><b>使用分區變化</b></td><td>農地 → 住宅、商業、產業用地</td><td>多已是都市土地</td><td>仍為農地</td></tr>
<tr><td><b>增值空間</b></td><td>最大（地目變更）</td><td>中等（公設完善）</td><td>小</td></tr>
<tr><td><b>主要風險</b></td><td>期程長、爭議訴訟、配地位置</td><td>期程、負擔比例</td><td>變現性受農地限制</td></tr></tbody></table></div>
<h2>區段徵收的七個步驟</h2>{IG.ig_steps(STEPS, caption='本站每個開發案頁都用這張圖標示目前進度。')}
<p>本站每個開發案頁面都用這七個步驟標示目前進度，例如 <a href="/project/chhsr/">高鐵彰化車站特定區</a> 已進入發展成熟階段，<a href="/project/nanke/">南科特定區開發區塊</a> 正在補償與抵價地申請階段。</p>
<h2>常見問題</h2>{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in FAQ)}
<p class="note">比例數字為法規原則，實際以內政部核定與各案公告為準。</p>""", tldr=['區段徵收會把農地變更為建地，地主領回 40–50% 抵價地，增值空間最大、期程最長。', '市地重劃不移轉所有權，扣除負擔後領回建築用地；農地重劃仍是農地。', '每個開發案都用同一張七步驟圖標示進度，越後面價格越已反映。'], extra_ld=
        [{'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FAQ]}])

RISKS = [('開發確定性', '計畫會不會真的做？', ['是否已通過都委會、內政部土徵小組（公益性與必要性）', '環評是否通過、有無被退回或要求補正', '地主同意比例（常見門檻：回收 6 成、同意 7 成）', '是否有行政訴訟或自救會抗爭'], '二林精機園區環評 12 年仍「補正後再審」；台中大里夏田地主同意約 56%，未達門檻。'),
         ('期程與資金', '要等多久、撐不撐得住？', ['從都市計畫擬定到配地，常見 8–15 年', '計算資金成本：利息或機會成本 × 年數', '避免用短期貸款買長期題材', '預留期程延宕 3–5 年的緩衝'], '桃園航空城拆遷期限一路從 2024 年延到 2026 年底。'),
         ('範圍與分配', '地在範圍內還是外？能配回什麼？', ['以都市計畫圖套繪地籍，確認是否在範圍線內', '範圍內：抵價地 40–50%，配地位置抽籤，可能要補差額地價', '範圍外：無徵收風險，但要確認外溢路網會不會接過來', '留意是否被劃為公設、滯洪池或斷層帶'], '高雄大社案把旗山斷層錯動帶規劃為綠帶與道路。'),
         ('產權與法規', '能不能順利交易、變更？', ['謄本：單獨所有或持分、有無抵押、限制登記', '使用分區：特定農業區最難變更', '國土功能分區（農 1～農 5、城 2-3）劃設結果', '現況違規（鐵皮、填土）會讓農業使用證明申請不過'], '持分農地流動性與貸款條件都明顯較差。'),
         ('價格與基期', '利多是不是已經漲完了？', ['比較周邊農地實價與未來建地行情的差距', '留意選址公布後的急漲', '參考已開發區的標售底價與流標情況', '算出損益兩平的建地單價'], '宜蘭高鐵特定區農地選址後從每坪約 2 萬喊到 7–10 萬；彰化高鐵特區產專區底價 14.2 萬後連續流標。'),
         ('流動性與融資', '想賣時賣不賣得掉？', ['農地貸款成數較低', '大面積總價高，買方族群少', '無臨路、畸零地轉手困難', '先想好接手的人是誰'], '總價上億的土地，買方多半只剩開發商或法人。')]
rank = sorted(P, key=lambda p: pot(p)['pri'], reverse=True)
article('/guide/risk/', '農地投資風險評估與長期佈局策略', GUIDES[1][2], f"""
<h2>六個面向評估投資風險</h2>{IG.ig_risk6(RISKS)}<div class="grid2">{''.join(f'<div class="card risk-card"><h3>{i + 1}. {t}</h3><p class="muted" style="margin:0">{q}</p><ul>{"".join(f"<li>{x}</li>" for x in l)}</ul><div class="ex"><b>案例：</b>{ex}</div></div>' for i, (t, q, l, ex) in enumerate(RISKS))}</div>
<h2>低基期 × 高發展性排行</h2>
{chart_hbar([(re.sub(r'（.*?）', '', p['name'])[:11], pot(p)['pri'], SC[stage_of(p['step'])], f"/project/{p['id']}/") for p in rank[:10]], '佈局優先分數前 10 名開發案', '；'.join(f"{p['name']} {pot(p)['pri']} 分" for p in rank[:10]), '圖：佈局優先分數前 10 名（發展性 60%＋低基期 40%），顏色代表開發階段。', ' 分', w=560, lab=190)}
<p>排序分數＝發展性 60%＋低基期 40%。發展性＝帶動力道（產業、交通、人口）＋開發確定性－風險扣分；價格基期＝區域價格帶＋進度（越後期價格越已反映）。等級為平台初步判斷，請以實價登錄校正。</p>
<div class="scroll"><table class="stack"><thead><tr><th>排名</th><th>開發案</th><th>發展性</th><th>基期</th><th>優先分數</th><th>判斷依據</th></tr></thead><tbody>
{''.join(f'<tr><td class="n">{i + 1}</td><td><a href="/project/{p["id"]}/">{e(p["name"])}</a>{"<span class=newtag>優先</span>" if pot(p)["top"] else ""}<br><span class="small muted">{e(p["county"])}・{STAGE[stage_of(p["step"])]}</span></td><td class="n">{pot(p)["dev"]}</td><td class="n">{pot(p)["base"]}</td><td class="n"><b>{pot(p)["pri"]}</b></td><td>{e(pot(p)["why"])}</td></tr>' for i, p in enumerate(rank))}
</tbody></table></div>
<h2>長期佈局的六個做法</h2>
<h3>1. 選「早期＋強動能」</h3><p>開發前、但背後有科學園區、高鐵或國家重大建設撐腰的案子，增值空間最大。</p>
<h3>2. 範圍外 1–3 公里卡位</h3><p>範圍內的地只能領回 4–5 成抵價地；範圍外的外溢圈保留全部持分，又能吃到道路與人口紅利。</p>{IG.ig_ring()}
<h3>3. 挑容易變更的地</h3><p>都市計畫農業區、一般農業區優先，特定農業區最難變更；單獨所有、臨 6 米以上道路、方整的地最好賣。</p>
<h3>4. 分批進場</h3><p>依開發里程碑分段加碼：都委會通過、土徵小組通過、徵收公告、工程開工。</p>
<h3>5. 用農業使用壓低持有成本</h3><p>持續作農業使用可適用田賦停徵、移轉免土增稅等優惠；資金以自有為主。</p>
<h3>6. 先想好出場點</h3><p>徵收公告前後、公共工程完工、配地後建地行情確立，是三個常見出場點。</p>
<p class="note">以上為一般性分析架構，非投資建議。全台開發案的基期與發展性矩陣，請見<a href="/">首頁儀表板</a>。</p>""", tldr=['先看六件事：開發確定性、期程資金、範圍分配、產權法規、價格基期、流動性。', '範圍外 1–3 公里的外溢圈，保有全部面積又能分享路網與人口紅利。', '佈局優先分數＝發展性 60%＋低基期 40%，排行每月隨新聞更新。'])

article('/guide/tax/', '農地稅負一張圖：土增稅、遺產贈與稅與 5 年列管', GUIDES[2][2], f"""
<p>農地的稅負優惠，前提幾乎都是「作農業使用」並取得<b>農業用地作農業使用證明書</b>。同一塊地在持有、被徵收、領回抵價地、變更為建地四個階段，適用的規則完全不同：</p>
{IG.ig_tax_flow()}
<h2>遺產稅與贈與稅</h2>
{IG.ig_brackets()}
<p>作農業使用的農業用地，繼承或贈與民法第 1138 條所定繼承人時，土地與地上農作物價值可全數扣除，但承受人要繼續農用 5 年。</p>
<h2>5 年列管：什麼情況會被追繳</h2>
{IG.ig_lock5()}
<h2>土地增值稅與房地合一稅</h2>
<p>作農業使用的農業用地移轉給<b>自然人</b>，可申請不課徵土地增值稅；即使稅額為 0 元也要提出申請。105 年後取得、符合不課徵土增稅要件的農地，出售時免納房地合一稅。賣給公司法人則兩項都不適用。</p>
<h2>區段徵收時</h2>
<p>被區段徵收的土地免徵土地增值稅；領回抵價地後第一次移轉，土地增值稅減徵 40%。</p>
<h2>農舍與違規使用</h2>
<p>農舍不適用農地的稅負優惠，出售時房屋部分併入綜合所得稅。鐵皮、填土、阻斷灌排或堆放雜物，會讓證明書申請不過，等於失去所有優惠，購買前務必現勘。</p>
<p class="note">以上為法規原則與 2026 年數字，個案請洽地政士或會計師；免稅額以財政部公告為準。高資產家族的傳承順序請見<a href="/guide/family-office/">家族辦公室與資產傳承</a>。</p>""",
        tldr=['四個階段四套規則：農用持有、被徵收、領回抵價地、變更為建地。', '農用優惠的入場券是「農業用地作農業使用證明書」，而且要移轉給自然人。', '免稅繼承或受贈的農地列管 5 年，轉給自己的子女可能被追繳。'])

# ----- 家族辦公室與資產傳承 -----
def _tier(stg, n=4):
    ps = [p for p in rank if stage_of(p['step']) == stg][:n]
    return '、'.join(f'<a href="/project/{p["id"]}/">{e(re.sub(r"（.*?）", "", p["name"]))}</a>' for p in ps)

FO_FAQ = [('高資產客戶可以用公司名義買農地嗎？', '依農業發展條例第 33 條，私法人不得承受「耕地」（非都市土地特定農業區、一般農業區、山坡地保育區、森林區的農牧用地），只有依第 34 條取得許可的農民團體、農業企業機構或農業試驗研究機構例外。都市計畫農業區不屬於耕地定義，不受此限，但仍受使用管制。'),
          ('農地贈與子女真的免贈與稅嗎？', '作農業使用的農業用地，贈與民法第 1138 條所定繼承人時，土地及地上農作物價值不計入贈與總額；但須取得農業用地作農業使用證明書，且受贈人自受贈日起 5 年內須繼續作農業使用，否則追繳。'),
          ('繼承的免稅農地，5 年內可以再轉給自己的小孩嗎？', '要小心。移轉給同一被繼承人的其他繼承人並繼續農用，免追繳遺產稅，但仍續列管；若贈與給自己的子女，子女並非原被繼承人的繼承人，已不符原免稅要件，可能被追繳遺產稅。'),
          ('農地賣給公司會怎樣？', '農地移轉不課徵土地增值稅，必須同時符合「作農業使用」與「移轉給自然人」。賣給公司法人即不符要件，房地合一稅的免稅也一併失去；國稅局曾有個案補稅 400 餘萬元、罰鍰 200 餘萬元。'),
          ('兄弟姊妹特留分刪除後，遺囑要重寫嗎？', '2026 年 7 月 28 日立法院三讀刪除民法第 1223 條兄弟姊妹特留分，自公布後滿 6 個月施行。兄弟姊妹仍是法定繼承人，只是有效遺囑下不能再主張特留分；父母的特留分仍在。單身、無子女的客戶最值得重新檢視遺囑。'),
          ('2027 年遺產稅、贈與稅免稅額會調高嗎？', '物價累計漲幅已超過 10% 法定門檻，媒體依目前漲幅估算明年遺產稅免稅額約 1,492 萬元、贈與稅約 273 萬元，實際以財政部公告為準。贈與時點可視公告結果調整。')]

article('/guide/family-office/', '家族辦公室與資產傳承：高資產客戶的農地長期佈局', GUIDES[3][2], f"""

<p>這篇寫給經營家族辦公室、做資產傳承規劃的從業人員：地政士（代書）、會計師、律師、財務顧問與保險規劃師。我們從農地仲介的現場經驗出發，把散在各法規裡的條件串成一條時間軸，方便您與高資產客戶討論「農地要放多少、放哪裡、用誰的名字、何時移轉」。以下為一般性分析架構，個案請由專業人員依最新法令與事實判斷。</p>

<h2>一、農地在高資產配置中的定位</h2>
<div class="scroll"><table><thead><tr><th>角色</th><th>對家族的價值</th><th>前提條件</th><th>會失效的情況</th></tr></thead><tbody>
<tr><td><b>稅負緩衝</b></td><td>遺產、贈與時農地價值可全數扣除；移轉給自然人可不課土增稅</td><td>作農業使用並取得證明書；承受人為繼承人或自然人</td><td>違規使用、閒置、5 年內未續農用、賣給法人</td></tr>
<tr><td><b>長期增值</b></td><td>開發案範圍內或外溢圈農地，變更為建地後價值重估</td><td>選對開發案與時點，能承受 8–15 年期程</td><td>計畫延宕或撤案；變更後失去農用優惠</td></tr>
<tr><td><b>實物保值</b></td><td>不受股市波動、可分割分配、持有成本低（田賦停徵）</td><td>產權單純、臨路、可分割</td><td>持分過碎、無路地、共有人僵局</td></tr></tbody></table></div>
<p>實務建議：農地不宜是家族唯一的傳承工具，而是與現金、保險、金融資產搭配的「長天期部位」。流動性需求（遺產稅現金、手足找補）要用其他資產準備，不要指望臨時賣地。</p>

<h2>二、依開發階段分三層配置</h2>
<p>本站把 45 個開發案依進度分為開發前、開發中、開發後。對傳承規劃而言，三個階段對應的是不同的稅負狀態與風險：</p>
{IG.ig_tiers({'pre': _tier('pre'), 'mid': _tier('mid'), 'post': _tier('post')})}
<p>第四個位置是<b>範圍外 1–3 公里的外溢圈</b>：不會被徵收、保有全部面積，又仍是農地，是「優惠與增值兼得」最常見的位置，示意圖見<a href="/guide/risk/">投資風險與外溢圈</a>。</p>
<p>每個開發案的發展性、基期與佈局分數，請見 <a href="/guide/risk/">投資風險與長期佈局</a>；個案深度評估請見 <a href="/column/">相信土地專欄</a>。</p>

<h2>三、持有結構：誰的名字最合適？</h2>
<div class="scroll"><table><thead><tr><th>結構</th><th>可否持有耕地</th><th>農用傳承優惠</th><th>適合情境</th><th>注意</th></tr></thead><tbody>
<tr><td><b>個人單獨所有</b></td><td>可</td><td>完整適用</td><td>主要持有方式</td><td>依持有人規劃贈與與遺囑</td></tr>
<tr><td><b>家族成員共有</b></td><td>可</td><td>適用，按持分</td><td>分年贈與持分</td><td>持分太碎影響流動性與貸款；建議同時簽分管契約</td></tr>
<tr><td><b>一般公司</b></td><td>耕地不可（農發條例 §33）；都市計畫農業區不屬耕地</td><td>不適用</td><td>已變更的建地、開發後土地</td><td>移轉給公司不適用不課徵土增稅與房地合一免稅</td></tr>
<tr><td><b>許可之農企業法人</b></td><td>經許可可承受耕地</td><td>依個案</td><td>真正經營農業的家族事業</td><td>須符合技術或資本密集類目並送經營利用計畫，受主管機關查核</td></tr>
<tr><td><b>信託</b></td><td colspan="2">農地信託涉及受託人資格與農用認定，各地實務不一，需事先向地政與稅捐機關確認</td><td>失能照顧、分期給付</td><td>規劃前務必個案詢問</td></tr></tbody></table></div>
<p>共有農地有一個常被忽略的好處：繼承後辦理分別共有登記，若有人在 5 年內賣掉自己的持分，只要能提出面積相當的有效分管契約，僅就移轉的那部分補稅，不會拖累其他手足。</p>

<h2>四、稅負時間軸：同一塊地，不同階段不同規則</h2>
<p>對傳承規劃最重要的分界線，是土地「還是不是作農業使用的農業用地」。仍是農地時，贈與繼承人或繼承可全數扣除、移轉給自然人可不課土增稅；被區段徵收時土增稅免徵；領回抵價地第一次移轉減徵 40%；變更為建地後則全部回到一般規定。四個階段的完整圖解、2026 年遺產稅與贈與稅級距，以及 5 年列管的追繳情形，整理在<a href="/guide/tax/">農地稅負一張圖</a>。</p>
<h2>五、傳承順序：五個常見安排</h2>
<h3>1. 先確認「農用狀態」，再談移轉</h3><p>取得農業用地作農業使用證明書是所有優惠的入場券。鐵皮、填土、阻斷灌排、堆放雜物都會讓申請不過。規劃第一步是現勘與整地，而不是簽贈與契約。</p>
<h3>2. 增值題材的地，趁還是農地時先移轉</h3><p>開發前的農地，價值低、又能適用農用扣除，是贈與下一代的最佳時點。等到變更為建地才移轉，既失去農用優惠，又是以較高的公告現值計稅。</p>
<h3>3. 5 年列管要排進家族行事曆</h3><p>繼承取得的免稅農地，5 年內轉給同一被繼承人的其他繼承人並續農用不會被追繳；但轉給自己的子女，就可能被追繳遺產稅。贈與取得的農地同樣列管 5 年。建議家辦把每筆農地的列管到期日做成清單。</p>
<h3>4. 變更後的地，用「分年＋分人」攤平</h3><p>失去農用優惠後，可搭配每年贈與免稅額、夫妻各自贈與、土增稅與契稅列為扣除額等方式分年移轉；需要現金的繼承人，可分配已開發完成、價值明確的建地或抵價地。</p>
<h3>5. 永遠不要把農地直接賣給公司</h3><p>即使持有證明書，賣給法人就不符不課徵土增稅要件，房地合一的免稅也一起失去。若家族要以公司開發，應先確認土地已變更為非農業用地，或由個人先持有到變更完成。</p>

<h2>六、2026 年特留分修法對遺囑的影響</h2>
<p>立法院於 2026 年 7 月 28 日三讀刪除民法第 1223 條兄弟姊妹特留分，自公布後滿 6 個月施行。重點有三：兄弟姊妹仍是法定繼承人，沒有遺囑時照樣繼承；有效遺囑下，兄弟姊妹不能再主張特留分；父母的特留分仍然保留。對持有大筆農地、單身或無子女的客戶，這是用遺囑把農地指定給實際耕作或照顧者的好時機，也能避免農地因手足主張持分而被切碎。</p>

<h2>七、給從業人員的檢查清單</h2>
<div class="grid2">
<div class="card"><h3>地政士（代書）</h3><ul><li>調閱謄本、地籍圖，確認單獨或持分、他項權利、限制登記</li><li>使用分區證明：耕地或都市計畫農業區，是否在開發案範圍內</li><li>申請農業用地作農業使用證明書，排除違規使用</li><li>移轉現值申報書註明農業用地，申請不課徵土增稅</li><li>共有農地協助簽訂分管契約</li></ul></div>
<div class="card"><h3>會計師</h3><ul><li>試算遺產總額、扣除額與不同年度贈與的稅負</li><li>建立每筆農地的 5 年列管到期表</li><li>確認 105 年前後取得、房地合一適用與申報期限</li><li>抵價地第一次移轉減徵 40% 的時點與申報</li><li>評估公司持有對已變更土地的影響</li></ul></div>
<div class="card"><h3>財務顧問・保險規劃</h3><ul><li>估算遺產稅與手足找補的現金需求，以保險或流動資產準備</li><li>設定農地佔家族資產比重與持有年限</li><li>以開發階段分散佈局，避免集中單一案件</li><li>每年檢視開發進度與實價登錄</li></ul></div>
<div class="card"><h3>律師・家族辦公室</h3><ul><li>依特留分新制檢視既有遺囑</li><li>設計農地分配與耕作／管理責任的家族協議</li><li>評估信託、遺囑執行人與失能安排</li><li>整合各專業的時間表與決策紀錄</li></ul></div>
</div>

<h2>常見問題</h2>{''.join(f'<h3>{e(q)}</h3><p>{e(a)}</p>' for q, a in FO_FAQ)}
<p class="note">本文為一般性資訊整理，依 2026 年 11 月可查得之法令與報導撰寫，不構成法律、稅務或投資建議。法令與免稅額可能變動，實際適用請洽地政士、會計師或律師依個案判斷。</p>""",
        [{'@context': 'https://schema.org', '@type': 'FAQPage', 'mainEntity': [{'@type': 'Question', 'name': q, 'acceptedAnswer': {'@type': 'Answer', 'text': a}} for q, a in FO_FAQ]}],
        tldr=['農地在傳承配置裡同時扮演三個角色：<b>稅負緩衝</b>（農用可扣除遺產、贈與）、<b>長期增值</b>（區段徵收、特定區變更）、<b>實物保值</b>。三者的條件互相衝突，順序排錯就會失去優惠。', '關鍵分界線是「是否仍為農業用地並作農業使用」。變更為建地前，用農用優惠傳承；變更後，改用抵價地減徵、分年贈與與遺囑安排。', '持有主體以<b>自然人</b>為主：私法人原則上不得承受耕地，賣給公司也會同時失去土增稅與房地合一的免稅。', '每一次免稅傳承都帶著 <b>5 年列管</b>。家族要排的不是「給誰」，而是「什麼時候、在什麼狀態下給誰」。'])

# ===== 在售農地 =====
lrows = ''.join(f'<div class="pcard"><span class="small muted">{e(l.get("county"))}{e(l.get("town"))}・{e(l.get("zone"))}</span><h3>{e(l.get("title") or (str(l.get("area")) + " 坪農地"))}</h3><p class="small muted">開價 {e(l.get("price"))} 萬/坪・{e(l.get("own"))}</p><a class="btn" href="/submit/?listing={quote(str(l.get("id", "")))}&county={quote(str(l.get("county", "")))}">我想了解</a></div>' for l in LIST)
cb, cld = crumbs([('首頁', '/'), ('在售農地', None)])
write('/listings/', page('/listings/', f'在售農地：鄰近開發案的農地物件｜{BRAND}', '鄰近區段徵收、特定區與產業園區的在售農地，附與開發案的距離與潛力分析。',
                         f'<section class="band"><div class="wrap">' + hero(cb, '在售農地・委託物件', '在售農地', f'每筆物件都標示與最近開發案的距離與潛力分數。物件委由{CFG.get("broker_name")}辦理，資訊以現況與謄本為準。')
                         + (f'<div class="pgrid" style="margin-top:16px">{lrows}</div>' if LIST else '<div class="card" style="margin-top:16px"><h3>物件陸續上架中</h3><p class="muted">我們正在整理鄰近開發案的優質農地。想出售農地，或想找特定區域的土地，請填寫表單，我們會主動與您聯繫。</p><a class="btn acc" href="/submit/">填寫委託表單</a></div>')
                         + '</div></section>', [cld], active='/listings/', og=og('listings', '在售農地', '鄰近開發案的農地物件')), prio='0.7')

# ===== 委託表單 =====
opts = ''.join(f'<option value="{p["id"]}">{e(p["county"])}｜{e(p["name"])}</option>' for p in P)
cty = ''.join(f'<option{" selected" if c == "彰化縣" else ""}>{c}</option>' for c in ['臺北市', '新北市', '基隆市', '桃園市', '新竹縣', '新竹市', '苗栗縣', '臺中市', '彰化縣', '南投縣', '雲林縣', '嘉義縣', '嘉義市', '臺南市', '高雄市', '屏東縣', '宜蘭縣', '花蓮縣', '臺東縣', '澎湖縣', '金門縣', '連江縣'])
endpoint = CFG.get('form_endpoint', '')
cb, cld = crumbs([('首頁', '/'), ('委託刊登', None)])
form = f"""<section class="band"><div class="wrap" style="max-width:860px">{cb}
<h1>委託刊登・我想找地</h1>
<p class="lede muted">填寫後由{e(CFG.get('broker_name'))}專人與您聯繫。刊登物件會先經過謄本與現況確認，再上架到在售農地。</p>
<form class="card form" id="F" novalidate>
<div class="full seg" role="radiogroup" aria-label="需求類型"><label><input type="radio" name="type" value="委託刊登" checked> 我要賣地／委託刊登</label><label><input type="radio" name="type" value="我想找地"> 我想買地／找地</label><label><input type="radio" name="type" value="物件詢問"> 詢問物件</label></div>
<label>您的稱呼<input name="name" required maxlength="30" autocomplete="name"></label>
<label>聯絡電話<input name="phone" required maxlength="20" inputmode="tel" autocomplete="tel"></label>
<label>LINE ID（選填）<input name="line" maxlength="40"></label>
<label>Email（選填）<input name="email" type="email" maxlength="80" autocomplete="email"></label>
<label>縣市<select name="county">{cty}</select></label>
<label>鄉鎮市區<input name="town" maxlength="20" placeholder="例：田中鎮"></label>
<label class="sell">地段・地號（選填）<input name="section" maxlength="60" placeholder="例：○○段 123 地號"></label>
<label class="sell">使用分區<select name="zone"><option>不確定</option><option>都市計畫農業區</option><option>一般農業區</option><option>特定農業區</option><option>山坡地保育區</option><option>其他</option></select></label>
<label>面積（坪，可估）<input name="area" type="number" min="0" step="1"></label>
<label><span class="sell-t">期望售價（萬元/坪）</span><input name="price" type="number" min="0" step="0.1"></label>
<label class="sell">產權<select name="own"><option>單獨所有</option><option>持分</option><option>不確定</option></select></label>
<label class="full">鄰近的開發案（選填）<select name="project"><option value="">— 不指定 —</option>{opts}</select></label>
<label class="full">補充說明<textarea name="message" maxlength="600" placeholder="現況、臨路、水電、可否建農舍、預算或用途…"></textarea></label>
<input type="hidden" name="listing"><input type="hidden" name="page">
<div class="hp" aria-hidden="true"><label>請勿填寫<input name="website" tabindex="-1" autocomplete="off"></label></div>
<label class="full" style="font-weight:400;display:flex;gap:10px;align-items:flex-start"><input type="checkbox" name="agree" required style="min-height:auto;margin-top:5px"> 我同意{e(CFG.get('broker_name'))}使用以上資料與我聯繫，資料僅用於本次委託與諮詢。</label>
<div class="full chips"><button class="btn acc" type="submit" id="Fbtn">送出</button></div>
<div class="full formmsg" id="Fmsg" hidden></div>
</form></div></section>
<script>{{const EP={json.dumps(endpoint)};const F=document.getElementById('F'),M=document.getElementById('Fmsg'),B=document.getElementById('Fbtn');
const PC={json.dumps({p['id']: p['county'] for p in P}, ensure_ascii=False)};const q=new URLSearchParams(location.search);if(q.get('project')){{F.project.value=q.get('project');if(PC[q.get('project')])F.county.value=PC[q.get('project')]}}if(q.get('county')&&[...F.county.options].some(o=>o.value===q.get('county')))F.county.value=q.get('county');if(q.get('listing')){{F.listing.value=q.get('listing');F.querySelector('input[value="物件詢問"]').checked=true}}
F.page.value=document.referrer||'';
const sync=()=>{{const sell=F.type.value==='委託刊登';F.querySelectorAll('.sell').forEach(x=>x.hidden=!sell);F.querySelector('.sell-t').textContent=sell?'期望售價（萬元/坪）':'預算（萬元/坪，可估）'}};F.addEventListener('change',sync);sync();
const show=(t,ok)=>{{M.hidden=false;M.textContent=t;M.style.background=ok?'':'light-dark(#fff1ec,#2a1710)'}};
F.addEventListener('submit',async ev=>{{ev.preventDefault();if(F.website.value)return;
if(!F.name.value.trim()||!F.phone.value.trim()){{show('請填寫稱呼與聯絡電話。');return}}if(!F.agree.checked){{show('請勾選同意聯繫。');return}}
if(!EP){{show('表單尚未啟用，請改用電話或 LINE 與我們聯繫。');return}}
B.disabled=true;B.textContent='送出中…';
try{{await fetch(EP,{{method:'POST',mode:'no-cors',body:new URLSearchParams(new FormData(F))}});show('已收到您的資料，我們會盡快與您聯繫。',1);F.reset();sync()}}
catch(e){{show('送出失敗，請稍後再試或直接來電。')}}B.disabled=false;B.textContent='送出'}})}}</script>"""
write('/submit/', page('/submit/', f'委託刊登農地・我想找地｜{BRAND}', '委託刊登您的農地，或告訴我們想找的區域與預算，由相信土地專人協助查詢分區、開發範圍與周邊行情，評估開發潛力。', form, [cld], active='/submit/'), prio='0.6')

# ===== 關於 =====
cb, cld = crumbs([('首頁', '/'), ('關於與免責聲明', None)])
write('/about/', page('/about/', f'關於{BRAND}與免責聲明', f'{BRAND}由{CFG.get("broker_name")}經營，整理全台農地開發資訊。',
                      f'<section class="band"><div class="wrap article" style="max-width:860px">{cb}<h1>關於{e(BRAND)}</h1>'
                      f'<p>{e(BRAND)}由{e(CFG.get("broker_name"))}經營，專注南彰化與全台開發題材農地。我們整理政府公開資料與新聞報導，追蹤區段徵收、特定區與產業園區的進度，並每月更新。</p>'
                      f'<h2>聯絡我們</h2><ul>{contact_html() or "<li>請透過<a href=/submit/>委託表單</a>與我們聯繫。</li>"}</ul><p>{broker_line()}</p>'
                      '<h2>免責聲明</h2><p>本網站內容為資訊整理與一般性分析，不構成投資建議。開發案範圍、期程、分區與價格請以主管機關公告、都市計畫書圖、土地登記謄本與實價登錄為準。潛力分數與基期等級為平台初步判斷，可能與實際情況不同。</p>'
                      '<p>新聞連結指向原始媒體，著作權屬原媒體所有，本站僅摘要重點並附原文連結。</p></div></section>', [cld], active=None), prio='0.3')

# ===== 互動工具（原單頁應用） =====
app = open(D('src/app.html'), encoding='utf-8').read()


def rep(a, b, cnt=1):
    global app
    assert app.count(a) >= 1, a[:60]
    app = app.replace(a, b, cnt)


rep('<meta name="viewport" content="width=device-width,initial-scale=1">', f'<meta name="viewport" content="width=device-width,initial-scale=1">\n<meta name="robots" content="noindex,follow">\n<link rel="canonical" href="{SITE}/tools/">\n<link rel="icon" href="/assets/favicon.svg" type="image/svg+xml">')
app = re.sub(r'<title>.*?</title>', f'<title>互動工具：開發地圖、潛力報告、價差試算｜{BRAND}</title>', app, count=1)
rep('<a class="logo" href="#home">', '<a class="logo" href="/">')
app = re.sub(r'<a class="logo" href="/"><svg.*?</svg>', lambda m: '<a class="logo" href="/">' + LOGO, app, count=1, flags=re.S)
app = app.replace('<b>地未來</b>', '<b>' + BRAND + '</b>')
rep('<a href="#home">首頁</a>', '<a href="/">← 網站首頁</a><a href="#home">工具首頁</a>')
rep('<a href="#post">我要刊登</a>', '<a href="/submit/">委託刊登</a>')
h0 = app.index('<header>'); h1 = app.index('</header>', h0) + len('</header>')
TOOLNAV = '<div class="band" style="padding-top:18px;padding-bottom:0"><div class="wrap"><div class="chips" role="tablist" aria-label="工具"><a class="chip" style="display:inline-flex;align-items:center;text-decoration:none" href="#map">開發地圖</a><a class="chip" style="display:inline-flex;align-items:center;text-decoration:none" href="#report">潛力報告</a><a class="chip" style="display:inline-flex;align-items:center;text-decoration:none" href="#calc">價差試算</a><a class="chip" style="display:inline-flex;align-items:center;text-decoration:none" href="#listings">物件列表</a></div></div></div>'
app = app[:h0] + site_header(None) + TOOLNAV + app[h1:]
app = app.replace("const h=(location.hash||'#home').slice(1);let v=VIEWS.includes(h)?h:'home';", "const h=(location.hash||'#map').slice(1);let v=VIEWS.includes(h)?h:'map';")
app = app.replace("document.querySelectorAll('#nav a')", "document.querySelectorAll('.chips[role=tablist] a')")
a0 = app.index('<!-- 刊登 -->'); a1 = app.index('<!-- 徵收與重劃 -->')
app = app[:a0] + '<section class="view band" id="v-post"><div class="wrap"><h2>委託刊登</h2><p class="muted">刊登與找地需求請使用網站表單。</p><a class="btn acc" href="/submit/">前往委託表單</a><div id="myListings"></div></div></section>\n' + app[a1:]
d0 = app.index('const DEMO=['); d1 = app.index('];', d0)
app = app[:d0] + 'const DEMO=[' + app[d1:]
b0 = app.index('/* 資料庫：會員刊登與詢問 */'); b1 = app.index('function renderMine(')
b2 = app.index('\n', b1)
app = app[:b0] + """/* 物件資料：讀取 /data/listings.json */
function renderMine(){}
async function initDb(){try{const r=await fetch('/data/listings.json',{cache:'no-store'});const a=await r.json();MEMBER=(Array.isArray(a)?a:[]).filter(it=>it&&isFinite(+it.lat)&&isFinite(+it.lng)&&+it.area>0).map(it=>({...it,id:String(it.id||'')}));$('#dbNote').textContent=MEMBER.length?`目前上架 ${MEMBER.length} 筆。`:'物件陸續上架中，委託刊登請填網站表單。';refresh()}catch(e){$('#dbNote').textContent='物件資料暫時無法載入。'}}""" + app[b2:]
rep("$('#pCounty').innerHTML=counties.map(c=>`<option>${c}</option>`).join('');", '')
app = app.replace('<a href="${esc(u)}">', '<a href="${esc(u)}" target="_blank" rel="nofollow noopener noreferrer">').replace('<a href="${esc(p.src)}">', '<a href="${esc(p.src)}" target="_blank" rel="nofollow noopener noreferrer">')
rep("fetch('news.json'", "fetch('/data/news.json'")
rep("'<span class=\"tag\" style=\"background:var(--rice);color:#1b2a12\">會員刊登</span>'", "'<span class=\"tag\" style=\"background:var(--rice);color:#1b2a12\">委託物件</span>'")
rep('${l.demo?\'<p class="note">示範物件，數字僅供展示功能，並非真實委託。</p>\':`<p class="note">由會員刊登，平台未審核。聯絡：${esc(l.contact)}</p>`}',
    '<p class="note">委託物件，資訊以現況與謄本為準。</p>')
i0 = app.index('<div class="card" style="margin-top:16px"><h3>對這塊地有興趣？</h3>'); i1 = app.index('</div></div></div>`;', i0)
app = app[:i0] + '<div class="card" style="margin-top:16px"><h3>對這塊地有興趣？</h3><a class="btn acc" href="/submit/?listing=${encodeURIComponent(l.id)}">填寫詢問表單</a>' + app[i1:]
rep('每筆物件會自動算出離最近開發案的距離。標「示範」的物件只用來展示功能；標「會員刊登」的物件由刊登者提供，平台尚未審核，交易前請自行查證謄本與地籍圖。',
    '每筆物件會自動算出離最近開發案的距離與潛力分數。物件資訊以現況與謄本為準。')
os.makedirs(D('dist/tools'), exist_ok=True)
open(D('dist/tools/index.html'), 'w', encoding='utf-8').write(app)

# ===== 404 / robots / sitemap / CNAME =====
open(D('dist/404.html'), 'w', encoding='utf-8').write(page('/404.html', f'找不到頁面｜{BRAND}', '找不到這個頁面。', '<section class="band"><div class="wrap"><h1>找不到這個頁面</h1><p class="muted">頁面可能已移動。</p><a class="btn pri" href="/">回首頁</a> <a class="btn" href="/projects/">看全部開發案</a></div></section>', robots='noindex', active=None))
open(D('dist/robots.txt'), 'w').write(f'User-agent: *\nAllow: /\nDisallow: /tools/\n\nSitemap: {SITE}/sitemap.xml\n')
sm = '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
for path, lm, pr in PAGES:
    sm += f'<url><loc>{SITE}{quote(path)}</loc><lastmod>{(lm or TODAY)[:10]}</lastmod><priority>{pr}</priority></url>\n'
open(D('dist/sitemap.xml'), 'w', encoding='utf-8').write(sm + '</urlset>\n')
open(D('dist/CNAME'), 'w').write(SITE.split('://')[1] + '\n')
for _vf in os.listdir(D('src/verify')) if os.path.isdir(D('src/verify')) else []:
    shutil.copy(D('src/verify', _vf), D('dist', _vf))

# ===== 社群分享圖 =====
if os.path.exists(D('src/og.png')):
    shutil.copy(D('src/og.png'), D('dist/assets/og.png'))
else:
  try:
      from PIL import Image, ImageDraw, ImageFont
      font = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
      if not os.path.exists(font):
          import glob
          font = (glob.glob('/usr/share/fonts/**/NotoSansCJK*Bold*.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/NotoSansCJK*.tt*', recursive=True))[0]
      im = Image.new('RGB', (1200, 630), '#1d4a33'); dr = ImageDraw.Draw(im)
      dr.rectangle([0, 560, 1200, 630], fill='#e8d36a')
      for i in range(6): dr.line([(760 + i * 70, 60), (760 + i * 70, 520)], fill='#2b5c42', width=3)
      for j in range(7): dr.line([(760, 60 + j * 76), (1110, 60 + j * 76)], fill='#2b5c42', width=3)
      dr.ellipse([900, 230, 980, 310], fill='#d4502a')
      F1 = ImageFont.truetype(font, 92); F2 = ImageFont.truetype(font, 40); F3 = ImageFont.truetype(font, 30)
      dr.text((70, 120), BRAND, font=F1, fill='#f2f7f3')
      dr.text((70, 250), '全台農地開發潛力平台', font=F2, fill='#e8d36a')
      dr.text((70, 320), f'{len(P)} 個區段徵收・特定區進度', font=F3, fill='#f2f7f3')
      dr.text((70, 365), '每月更新最新消息', font=F3, fill='#f2f7f3')
      dr.text((70, 578), SITE.split('://')[1], font=F3, fill='#1d4a33')
      im.save(D('dist/assets/og.png'), optimize=True); shutil.copy(D('dist/assets/og.png'), D('src/og.png'))
  except Exception as ex:
      print('og.png 產生失敗：', ex)

# ===== 每頁專屬分享圖（SEO／社群預覽） =====
try:
    from PIL import Image, ImageDraw, ImageFont
    import glob, textwrap
    _f = '/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc'
    if not os.path.exists(_f):
        _f = (glob.glob('/usr/share/fonts/**/NotoSansCJK*Bold*.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/NotoSansCJK*.tt*', recursive=True) + glob.glob('/usr/share/fonts/**/*CJK*.tt*', recursive=True))[0]
    FB, FS, FT = ImageFont.truetype(_f, 64), ImageFont.truetype(_f, 34), ImageFont.truetype(_f, 28)
    os.makedirs(D('dist/assets/og'), exist_ok=True)
    def _wrap(dr, s, font, width):
        lines, cur = [], ''
        for ch in s:
            if dr.textlength(cur + ch, font=font) > width: lines.append(cur); cur = ch
            else: cur += ch
        return lines + [cur]
    for slug, (title, sub, col) in OGQ.items():
        im = Image.new('RGB', (1200, 630), '#1d4a33'); dr = ImageDraw.Draw(im)
        dr.rectangle([0, 0, 1200, 14], fill=col)
        for i in range(5): dr.line([(880 + i * 70, 120), (880 + i * 70, 470)], fill='#2b5c42', width=3)
        for j in range(6): dr.line([(880, 120 + j * 70), (1160, 120 + j * 70)], fill='#2b5c42', width=3)
        dr.ellipse([990, 250, 1060, 320], fill=col if col != '#1d4a33' else '#d4502a')
        dr.rounded_rectangle([70, 70, 300, 120], 10, fill='#e8d36a'); dr.text((88, 74), '相信土地', font=FT, fill='#1d4a33')
        y = 160
        for ln in _wrap(dr, title, FB, 760)[:3]:
            dr.text((70, y), ln, font=FB, fill='#f2f7f3'); y += 84
        dr.text((70, y + 16), sub[:30], font=FS, fill='#e8d36a')
        dr.rectangle([0, 560, 1200, 630], fill='#e8d36a')
        dr.text((70, 576), f'{SITE.split("://")[1]}｜全台農地開發潛力平台', font=FT, fill='#1d4a33')
        im.save(D(f'dist/assets/og/{slug}.png'), optimize=True)
    print(f'分享圖：{len(OGQ)} 張')
except Exception as ex:
    print('分享圖產生失敗：', ex)

print(f'完成：{len(PAGES)} 個頁面寫入 sitemap，輸出在 dist/')
