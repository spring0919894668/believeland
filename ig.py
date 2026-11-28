# -*- coding: utf-8 -*-
"""相信土地圖解：原創 SVG／HTML 資訊圖表元件。
所有文字都寫在 SVG 的 <text>、<title>、<desc> 或 HTML 內，搜尋引擎可以讀取。"""
from html import escape as _e

e = lambda s: _e(str(s), quote=True)
F = 'font-family="Noto Sans TC,system-ui,sans-serif"'
C = {'field': '#1d4a33', 'rice': '#e8d36a', 'acc': '#d4502a', 'pre': '#2f6db0', 'mid': '#d4502a', 'post': '#2f8a57',
     'leaf': '#5a9e3a', 'gray': '#9aa59c'}
_n = [0]


def _id():
    _n[0] += 1
    return f'g{_n[0]}'


def svg(w, h, title, desc, body, cls=''):
    i = _id()
    return (f'<svg class="igs {cls}" viewBox="0 0 {w} {h}" role="img" aria-labelledby="{i}t {i}d" xmlns="http://www.w3.org/2000/svg" {F}>'
            f'<title id="{i}t">{e(title)}</title><desc id="{i}d">{e(desc)}</desc>{body}</svg>')


def frame(title, inner, caption='', src=''):
    """所有圖解共用外框：品牌標籤＋標題＋圖＋說明＋資料依據。"""
    s = f'<p class="ig-src">資料依據：{e(src)}</p>' if src else ''
    c = f'<figcaption>{e(caption)}</figcaption>' if caption else ''
    return f'<figure class="ig"><div class="ig-h"><span class="ig-b">相信土地圖解</span><b>{e(title)}</b></div>{inner}{c}{s}</figure>'


def T(x, y, s, size=15, w=400, anchor='start', fill='currentColor', op=None):
    o = f' opacity="{op}"' if op else ''
    return f'<text x="{x}" y="{y}" font-size="{size}" font-weight="{w}" text-anchor="{anchor}" fill="{fill}"{o}>{e(s)}</text>'


# ---------- 線條圖示（24×24） ----------
ICON = {
    'plan': 'M5 3h10l4 4v14H5z M15 3v4h4 M8 11h8 M8 15h8 M8 19h5',
    'scale': 'M12 3v18 M5 21h14 M4 8h16 M7 8l-3 7h6z M17 8l-3 7h6z',
    'horn': 'M3 10v4h4l7 5V5L7 10z M17 8a5 5 0 0 1 0 8',
    'coin': 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M9 9h6 M9 13h6 M12 9v8',
    'crane': 'M4 21h16 M7 21V5h2v16 M9 5h11 M18 5v5 M16 10h4v3h-4z M9 9l4-4',
    'grid': 'M4 4h7v7H4z M13 4h7v7h-7z M4 13h7v7H4z M13 13h7v7h-7z',
    'city': 'M3 21h18 M5 21V9h5v12 M10 21V4h6v17 M16 21v-9h4v9 M7 12h1 M7 15h1 M12 7h2 M12 10h2 M12 13h2',
    'shield': 'M12 3l8 3v6c0 5-3.5 8-8 9c-4.5-1-8-4-8-9V6z M8.5 12l2.5 2.5l4.5-5',
    'clock': 'M12 3a9 9 0 1 0 0 18a9 9 0 1 0 0-18 M12 7v5l3 3',
    'map': 'M3 6l6-2l6 2l6-2v14l-6 2l-6-2l-6 2z M9 4v14 M15 6v14',
    'doc': 'M6 3h9l3 3v15H6z M9 9h6 M9 13h6 M9 17h4',
    'tag': 'M3 12V4h8l10 10l-8 8z M7.5 8a.5.5 0 1 0 1 0a.5.5 0 1 0-1 0',
    'drop': 'M12 3c4 5 6 8 6 11a6 6 0 0 1-12 0c0-3 2-6 6-11z',
    'home': 'M3 11l9-7l9 7 M5 10v10h14V10 M10 20v-6h4v6',
    'sprout': 'M12 21v-9 M12 12c0-4 3-7 8-7c0 5-3 7-8 7z M12 14c0-3-2-5-7-5c0 4 2 5 7 5z',
    'people': 'M8 11a3 3 0 1 0 0-6a3 3 0 1 0 0 6 M2 20c0-3.5 2.7-6 6-6s6 2.5 6 6 M17 11a2.5 2.5 0 1 0 0-5 M16 14c3 0 6 2 6 6',
}


def icon(name, x, y, s=24, col='currentColor', sw=1.8):
    k = s / 24
    return f'<path d="{ICON[name]}" transform="translate({x} {y}) scale({k})" fill="none" stroke="{col}" stroke-width="{sw / k:.2f}" stroke-linecap="round" stroke-linejoin="round"/>'


def icon_svg(name, size=28, col='currentColor'):
    return f'<svg width="{size}" height="{size}" viewBox="0 0 24 24" aria-hidden="true"><path d="{ICON[name]}" fill="none" stroke="{col}" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round"/></svg>'


# ---------- 1. 區段徵收七步驟 ----------
STEP_IC = ['plan', 'scale', 'horn', 'coin', 'crane', 'grid', 'city']
STEP_SUB = ['擬定或變更都市計畫', '土徵小組審公益性', '公告 30 天、通知地主', '選現金或申請抵價地', '道路、水電、公園', '抽籤配地、標售土地', '建地交易、人口進駐']
PH = [('開發前', 'pre', 0, 1), ('開發中', 'mid', 2, 4), ('開發後', 'post', 5, 6)]


def ig_steps(steps, cur=None, title='區段徵收七步驟', caption='', name=''):
    who = f'{name}目前在第 {cur + 1} 步「{steps[cur]}」。' if cur is not None else ''
    desc = who + '；'.join(f'第{i + 1}步 {s}：{STEP_SUB[i]}' for i, s in enumerate(steps))
    # 寬版
    W, H, x0, gap = 840, (210 if cur is not None else 168), 60, 120
    b = ''
    for t, k, a, z in PH:
        xa, xz = x0 + a * gap - 46, x0 + z * gap + 46
        b += f'<rect x="{xa}" y="8" width="{xz - xa}" height="26" rx="13" fill="{C[k]}" opacity=".14"/>' + T((xa + xz) / 2, 26, t, 14, 700, 'middle', C[k])
    b += f'<line x1="{x0}" y1="80" x2="{x0 + 6 * gap}" y2="80" stroke="currentColor" stroke-opacity=".18" stroke-width="6" stroke-linecap="round"/>'
    if cur is not None:
        b += f'<line x1="{x0}" y1="80" x2="{x0 + cur * gap}" y2="80" stroke="{C["field"]}" stroke-width="6" stroke-linecap="round"/>'
    for i, s in enumerate(steps):
        x = x0 + i * gap
        done = cur is not None and i < cur
        now = cur is not None and i == cur
        fill = C['acc'] if now else C['field'] if (done or cur is None) else 'var(--card,#fff)'
        stroke = C['acc'] if now else C['field'] if (done or cur is None) else 'currentColor'
        ic = '#fff' if (done or now or cur is None) else 'currentColor'
        b += f'<circle cx="{x}" cy="80" r="{30 if now else 26}" fill="{fill}" stroke="{stroke}" stroke-opacity="{1 if (done or now or cur is None) else .35}" stroke-width="2"/>'
        b += icon(STEP_IC[i], x - 12, 68, 24, ic, 1.9)
        b += T(x, 134, f'{i + 1}. {s}', 14, 700 if now else 600, 'middle', C['acc'] if now else 'currentColor')
        b += T(x, 154, STEP_SUB[i], 12, 400, 'middle', op='.7')
        if now:
            b += f'<path d="M{x - 26} 176h52l-26 -12z" fill="{C["acc"]}"/>' + f'<rect x="{x - 34}" y="174" width="68" height="26" rx="13" fill="{C["acc"]}"/>' + T(x, 192, '目前', 13, 700, 'middle', '#fff')
    wide = svg(W, H, title, desc, b, 'ig-wide')
    # 直式（手機）
    W2, rh = 360, 64
    H2 = 30 + 7 * rh
    b = ''
    for t, k, a, z in PH:
        b += f'<rect x="6" y="{18 + a * rh}" width="6" height="{(z - a + 1) * rh - 12}" rx="3" fill="{C[k]}"/>' + f'<text transform="translate(24 {18 + (a + z + 1) * rh / 2 - 6}) rotate(-90)" font-size="12" font-weight="700" text-anchor="middle" fill="{C[k]}">{t}</text>'
    b += f'<line x1="66" y1="42" x2="66" y2="{30 + 6 * rh + 12}" stroke="currentColor" stroke-opacity=".18" stroke-width="5"/>'
    for i, s in enumerate(steps):
        y = 42 + i * rh
        done = cur is not None and i < cur
        now = cur is not None and i == cur
        fill = C['acc'] if now else C['field'] if (done or cur is None) else 'var(--card,#fff)'
        ic = '#fff' if (done or now or cur is None) else 'currentColor'
        b += f'<circle cx="66" cy="{y}" r="22" fill="{fill}" stroke="{C["acc"] if now else C["field"] if (done or cur is None) else "currentColor"}" stroke-opacity="{1 if (done or now or cur is None) else .35}" stroke-width="2"/>'
        b += icon(STEP_IC[i], 56, y - 10, 20, ic, 1.9)
        b += T(100, y - 2, f'{i + 1}. {s}' + ('　◀ 目前' if now else ''), 16, 700, fill=C['acc'] if now else 'currentColor')
        b += T(100, y + 18, STEP_SUB[i], 13, 400, op='.7')
    tall = svg(W2, H2, title, desc, b, 'ig-tall')
    return frame(title, wide + tall, caption)


# ---------- 2. 三種開發方式：土地怎麼分 ----------
def _blocks(cells, size=12, gap=2):
    """10×10 方格，cells=[(數量, 顏色, 標籤)]"""
    out, k = '', 0
    for n, col, _ in cells:
        for _ in range(n):
            r, c = divmod(k, 10)
            out += f'<rect x="{c * (size + gap)}" y="{r * (size + gap)}" width="{size}" height="{size}" rx="2" fill="{col}"/>'
            k += 1
    return out


def ig_land_split():
    panels = [
        ('區段徵收', '農地 → 建地', [(45, C['acc'], '領回抵價地 40–50%'), (40, C['gray'], '道路、公園等公共設施'), (15, C['pre'], '政府標售讓售，回收開發費用')],
         '抵價地以 50% 為原則，不得少於 40%；分區由農業區變更為住宅、商業或產業用地。'),
        ('市地重劃', '已是都市土地', [(58, C['acc'], '領回建築用地約 55% 以上'), (42, C['gray'], '公設與費用負擔 ≤45%')],
         '所有權不移轉，扣除負擔後重新分配位置。'),
        ('農地重劃', '仍是農地', [(90, C['leaf'], '領回農地，坵塊方整'), (10, C['gray'], '農路、水路用地')],
         '改善耕作條件，使用分區不變，增值空間有限。'),
    ]
    out = ''
    for name, sub, cells, note in panels:
        b = f'<g transform="translate(20 52)">{_blocks(cells, 18, 3)}</g>'
        b += T(20, 24, name, 20, 900) + T(20, 44, sub, 14, 400, op='.7')
        y = 272
        for n, col, lab in cells:
            b += f'<rect x="20" y="{y - 12}" width="14" height="14" rx="3" fill="{col}"/>' + T(42, y, lab, 14)
            y += 24
        desc = f'{name}：' + '；'.join(f'{lab}（示意 {n} 格／100 格）' for n, _, lab in cells) + '。' + note
        out += f'<div class="ig-cell">{svg(250, 340, name + "土地分配示意", desc, b)}<p class="small muted">{e(note)}</p></div>'
    return frame('三種開發方式：一塊地最後變成什麼？', f'<div class="ig-row">{out}</div>',
                 '以 100 格代表地主原有土地的示意圖，比例為法規原則，實際依各案核定。', '土地徵收條例、平均地權條例、農地重劃條例')


# ---------- 3. 範圍內 vs 外溢圈 ----------
def ig_ring(name=''):
    cx, cy = 230, 220
    b = ''
    for r, col, op in [(200, C['rice'], .25), (140, C['rice'], .35)]:
        b += f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="{col}" opacity="{op}"/>'
    b += f'<circle cx="{cx}" cy="{cy}" r="80" fill="{C["acc"]}" opacity=".85"/>'
    b += f'<path d="M{cx - 200} {cy} H{cx + 200} M{cx} {cy - 200} V{cy + 200}" stroke="currentColor" stroke-opacity=".35" stroke-width="3" stroke-dasharray="2 6"/>'
    b += T(cx, cy - 6, name or '開發案範圍', 17, 900, 'middle', '#fff') + T(cx, cy + 16, '領回 40–50%', 14, 700, 'middle', '#fff')
    b += T(cx, cy - 100, '外溢圈 1 公里', 14, 700, 'middle') + T(cx, cy - 168, '外溢圈 3 公里', 14, 700, 'middle')
    b += T(cx + 205, cy - 6, '延伸道路', 12, 400, 'end', op='.7')
    b += f'<g transform="translate(470 40)">'
    rows = [(C['acc'], '範圍內', ['被徵收，只能領回 40–50% 抵價地', '配地位置抽籤，可能補差額', '分區變更為建地，價值重估']),
            (C['rice'], '範圍外 1–3 公里', ['不被徵收，保有全部面積', '吃到道路、人口、商圈外溢', '仍是農地，可續享農用稅負優惠']),
            ('#ccc', '3 公里以外', ['帶動力道明顯遞減', '價格多由在地供需決定'])]
    y = 0
    for col, t, ls in rows:
        b += f'<rect x="0" y="{y}" width="18" height="18" rx="4" fill="{col}"/>' + T(28, y + 15, t, 17, 900)
        for l in ls:
            y += 24
            b += T(28, y + 14, '・' + l, 14)
        y += 40
    b += '</g>'
    desc = '開發案範圍內與範圍外 1 至 3 公里外溢圈的差異：範圍內被徵收、只能領回 40–50% 抵價地但分區變更；範圍外保有全部面積且仍享農用優惠，又能分享路網與人口紅利。'
    return frame('範圍內還是範圍外？外溢圈示意', svg(820, 440, '開發案範圍與外溢圈示意', desc, b),
                 '距離圈為一般觀察，實際外溢範圍要看道路與產業布局。', '相信土地現場經驗整理')


# ---------- 4. 稅負時間軸（HTML 流程卡） ----------
def ig_tax_flow():
    st = [('sprout', '持有中・作農業使用', C['leaf'], ['田賦停徵，持有成本低', '移轉給自然人可申請不課徵土增稅', '贈與繼承人或繼承：價值全數扣除（列管 5 年）']),
          ('horn', '被區段徵收', C['mid'], ['土地增值稅免徵', '房地合一稅免納', '列管期間因徵收未續農用，不追繳']),
          ('grid', '領回抵價地', C['pre'], ['第一次移轉，土增稅減徵 40%', '遺產、贈與依一般規定計算', '出售依房地合一規定']),
          ('city', '變更為建地後', C['field'], ['不再適用農用優惠', '遺產、贈與與土增稅依一般規定', '可改用分年贈與與遺囑安排'])]
    cards = ''.join(f'<li class="tf" style="--c:{c}"><div class="tf-i">{icon_svg(i, 26, "#fff")}</div><b>{e(t)}</b><ul>{"".join(f"<li>{e(x)}</li>" for x in xs)}</ul></li>' for i, t, c, xs in st)
    return frame('同一塊地，不同階段的稅負', f'<ol class="tflow">{cards}</ol>',
                 '依序為一般區段徵收的時間軸；農舍不適用農地稅負優惠。', '遺產及贈與稅法 §17、§20；土地稅法 §39、§39-2；所得稅法 §4-5；農業發展條例 §37、§38')


# ---------- 5. 遺產稅／贈與稅級距 ----------
def ig_brackets():
    b = ''
    base_y, x0 = 300, 60
    steps = [('10%', '2,811 萬以下', 90, C['leaf']), ('15%', '2,811～5,621 萬', 150, C['rice']), ('20%', '5,621 萬以上', 210, C['acc'])]
    for i, (r, lab, h, col) in enumerate(steps):
        x = x0 + i * 150
        b += f'<rect x="{x}" y="{base_y - h}" width="136" height="{h}" rx="8" fill="{col}"/>'
        b += T(x + 68, base_y - h + 40, r, 30, 900, 'middle', '#14221a') + T(x + 68, base_y + 26, lab, 14, 700, 'middle')
    b += f'<line x1="40" y1="{base_y}" x2="530" y2="{base_y}" stroke="currentColor" stroke-opacity=".4"/>'
    b += T(x0, 40, '課稅淨額＝總額－免稅額－扣除額', 15, 700)
    b += f'<g transform="translate(560 70)">'
    for i, (k, v) in enumerate([('遺產稅免稅額', '1,333 萬'), ('贈與稅免稅額', '244 萬／年'), ('配偶扣除額', '553 萬'), ('子女扣除額', '56 萬／人'), ('農業用地', '全數扣除＊')]):
        y = i * 46
        b += f'<rect x="0" y="{y}" width="240" height="38" rx="8" fill="currentColor" fill-opacity=".06"/>' + T(12, y + 25, k, 14) + T(228, y + 25, v, 16, 900, 'end')
    b += '</g>' + T(560, 330, '＊須作農業使用並列管 5 年', 12, 400, op='.7')
    desc = '2026 年（115 年）遺產稅與贈與稅：課稅淨額 2,811 萬元以下稅率 10%，2,811 萬至 5,621 萬元 15%，5,621 萬元以上 20%。遺產稅免稅額 1,333 萬元，贈與稅每位贈與人每年 244 萬元，配偶扣除額 553 萬元，直系血親卑親屬每人 56 萬元，作農業使用的農業用地可全數扣除。'
    return frame('遺產稅・贈與稅一張圖（2026 年）', svg(820, 350, '遺產稅與贈與稅級距', desc, b),
                 '物價累計漲幅已逾調整門檻，2027 年免稅額與級距以財政部公告為準。', '財政部 115 年遺產稅及贈與稅免稅額、扣除額公告')


# ---------- 6. 5 年列管 ----------
def ig_lock5():
    b = ''
    x0, x1, y = 60, 760, 90
    b += f'<rect x="{x0}" y="{y - 14}" width="{x1 - x0}" height="28" rx="14" fill="{C["leaf"]}" opacity=".18"/>'
    for i in range(6):
        x = x0 + i * (x1 - x0) / 5
        b += f'<circle cx="{x}" cy="{y}" r="7" fill="{C["field"]}"/>' + T(x, y + 36, '承受日' if i == 0 else f'第 {i} 年', 13, 700 if i in (0, 5) else 400, 'middle')
    b += T(x0, 40, '繼承（自死亡日起算）或受贈（自受贈日起算）', 15, 700) + T(x1, 40, '列管結束', 15, 700, 'end', C['post'])
    rows = [(C['post'], '✓', '不追繳', ['繼續作農業使用', '因徵收、依法變更為非農業用地', '承受人死亡', '轉給同一被繼承人的其他繼承人並續農用']),
            (C['acc'], '✕', '追繳稅額', ['閒置、違規使用且未在期限內恢復', '出售他人且未依限回復登記並續農用', '轉給自己的子女（非原被繼承人的繼承人）']),]
    yy = 170
    for i, (col, mk, t, ls) in enumerate(rows):
        x = 60 + i * 380
        b += f'<rect x="{x}" y="{yy}" width="350" height="{52 + 26 * len(ls)}" rx="12" fill="{col}" opacity=".1"/>'
        b += f'<circle cx="{x + 26}" cy="{yy + 26}" r="14" fill="{col}"/>' + T(x + 26, yy + 31, mk, 15, 900, 'middle', '#fff') + T(x + 50, yy + 32, t, 17, 900, fill=col)
        for j, l in enumerate(ls):
            b += T(x + 22, yy + 64 + j * 26, '・' + l, 14)
    desc = '農業用地免徵遺產稅或贈與稅後，自承受日起列管 5 年。期間繼續農用、被徵收、依法變更為非農業用地、承受人死亡，或移轉給同一被繼承人的其他繼承人並續農用，都不會追繳；閒置違規且未恢復、轉給自己的子女，則會被追繳。'
    return frame('農地免稅傳承的 5 年列管', svg(820, 330, '農業用地 5 年列管', desc, b),
                 '共有農地若有部分繼承人移轉持分，提出面積相當的分管契約，只就移轉部分補稅。', '遺產及贈與稅法 §17①6、§20①5；財政部函釋')


# ---------- 7. 風險六面向（HTML 圖卡） ----------
def ig_risk6(items):
    ic = ['shield', 'clock', 'map', 'doc', 'tag', 'drop']
    cards = ''.join(f'<li><span class="rq-i">{icon_svg(ic[i], 26, "#fff")}</span><b>{i + 1}. {e(t)}</b><span class="small muted">{e(q)}</span></li>' for i, (t, q, *_r) in enumerate(items))
    return frame('評估開發題材農地的六個面向', f'<ul class="rq">{cards}</ul>', '每個面向的檢查重點與案例見下方。')


# ---------- 8. 三層配置 ----------
def ig_tiers(tier_html):
    t = [('pre', '開發前', '長線卡位', '基期最低、確定性最低；仍是農地，可完整享受農用傳承優惠', '適合年輕一代持有'),
         ('mid', '開發中', '等待轉換', '徵收免土增稅、抵價地減徵 40%；推進中仍須維持農用', '注意期程與資金'),
         ('post', '開發後', '收成分配', '價值明確、好分割；改依一般遺贈與房地合一課稅', '用來平衡繼承人分配')]
    cards = ''.join(f'<li class="tr t-{k}x"><span class="tag t-{k}">{a}</span><b>{e(b_)}</b><p>{e(c)}</p><p class="small"><b>{e(d)}</b></p><p class="small muted">參考：{tier_html.get(k, "")}</p></li>' for k, a, b_, c, d in t)
    return frame('依開發階段分三層配置', f'<ol class="tiers">{cards}</ol>', '另可在範圍外 1–3 公里的外溢圈配置，兼顧農用優惠與增值。')


# ---------- 9. 開發案分數儀表 ----------
def ig_gauges(name, dev, base, pri):
    out = ''
    for lab, v, col, tip in [('發展性', dev, C['post'], '產業、交通、人口帶動力道'), ('價格基期', base, C['mid'], '越低越有空間'), ('佈局優先', pri, C['field'], '發展性 60%＋低基期 40%')]:
        import math
        a = math.pi * (1 - v / 100)
        x, y = 90 + 70 * math.cos(a), 92 - 70 * math.sin(a)
        b = f'<path d="M20 92 A70 70 0 0 1 160 92" fill="none" stroke="currentColor" stroke-opacity=".12" stroke-width="14" stroke-linecap="round"/>'
        b += f'<path d="M20 92 A70 70 0 0 1 {x:.1f} {y:.1f}" fill="none" stroke="{col}" stroke-width="14" stroke-linecap="round"/>'
        b += T(90, 86, v, 30, 900, 'middle') + T(90, 122, lab, 15, 700, 'middle') + T(90, 142, tip, 11, 400, 'middle', op='.7')
        out += svg(180, 150, f'{name}{lab}分數', f'{name}{lab} {v} 分（滿分 100）：{tip}', b)
    return f'<div class="gauges">{out}</div>'


CSS = """
.ig{margin:22px 0;padding:16px 18px 14px;background:var(--card);border:1px solid var(--line);border-radius:18px;max-width:900px}
.ig-h{display:flex;align-items:center;gap:10px;flex-wrap:wrap;margin-bottom:10px}.ig-h b{font-size:18px}
.ig-b{font-size:12px;font-weight:700;letter-spacing:.04em;color:#1b2a12;background:var(--rice);border-radius:6px;padding:2px 8px}
.ig figcaption{font-size:14px;color:var(--mute);margin-top:8px}.ig-src{font-size:12.5px;color:var(--mute);margin:4px 0 0;opacity:.85}
.igs{display:block;width:100%;height:auto;color:var(--ink)}
.ig-tall{display:none;max-width:420px}
@media(max-width:640px){.ig-wide{display:none}.ig-tall{display:block}}
.ig-row{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}.ig-cell .igs{max-width:300px}
.tflow{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(190px,1fr));gap:12px;counter-reset:t}
.tf{position:relative;border:1px solid var(--line);border-top:5px solid var(--c);border-radius:12px;padding:12px 14px;background:var(--bg)}
.tf b{display:block;font-size:16px;margin:6px 0 4px}.tf ul{margin:0;padding-left:1.1em;font-size:14.5px}.tf li{margin:3px 0}
.tf-i{width:40px;height:40px;border-radius:50%;background:var(--c);display:grid;place-items:center}
.rq{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:10px}
.rq li{display:grid;grid-template-columns:44px 1fr;gap:2px 10px;align-items:center;padding:10px;border:1px solid var(--line);border-radius:12px;background:var(--bg)}
.rq-i{grid-row:span 2;width:44px;height:44px;border-radius:12px;background:var(--field);display:grid;place-items:center}
.tiers{list-style:none;margin:0;padding:0;display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:12px}
.tr{border:1px solid var(--line);border-radius:14px;padding:14px;background:var(--bg)}.tr>b{display:block;font-size:19px;margin:8px 0 4px}.tr p{margin:6px 0}
.t-prex{border-top:5px solid var(--pre)}.t-midx{border-top:5px solid var(--mid)}.t-postx{border-top:5px solid var(--post)}
.gauges{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:6px}.gauges .igs{max-width:200px;margin:auto}
"""
