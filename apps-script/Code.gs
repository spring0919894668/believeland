/**
 * 相信土地 委託表單與從業人員自行刊登後端
 * 貼到「Google 試算表 → 擴充功能 → Apps Script」，再部署為網頁應用程式（所有人）。
 * - doPost：委託表單寫入「表單回覆」；從業人員刊登寫入「自行刊登」並立即上架。
 * - doGet?action=listings：回傳「自行刊登」中狀態為「上架」且未過期的物件（只含公開欄位）。
 *   要下架某筆物件，把該列「狀態」改成「下架」即可，網站 5 分鐘內同步。
 */
const SHEET_NAME = '表單回覆';
const LIST_SHEET = '自行刊登';
const NOTIFY_EMAIL = 'spring0919894668@gmail.com';   // 新委託、新刊登寄通知到這個信箱，留空則不寄
const LIST_DAYS = 90;                                  // 自行刊登物件上架天數，到期自動不顯示

const FIELDS = ['type', 'name', 'phone', 'line', 'email', 'county', 'town', 'section', 'zone',
                'area', 'price', 'own', 'project', 'listing', 'message', 'page'];
const HEADERS = ['送出時間', '類型', '稱呼', '電話', 'LINE', 'Email', '縣市', '鄉鎮', '地段地號', '使用分區',
                 '面積(坪)', '價格(萬/坪)', '產權', '鄰近開發案', '物件編號', '說明', '來源頁', '處理狀態'];

// 自行刊登：欄位代號、試算表標題、是否公開到網站
const L_FIELDS = [
  ['id', '編號', 1], ['ts', '刊登時間', 1], ['role', '刊登人身分', 1], ['name', '刊登人姓名', 1],
  ['company', '所屬經紀業／事務所', 1], ['license', '證照字號', 1], ['phone', '手機', 1], ['line', 'LINE ID', 1],
  ['title', '物件標題', 1], ['kind', '物件類型', 1], ['county', '縣市', 1], ['town', '鄉鎮市區', 1], ['section', '地段', 1],
  ['zone', '使用分區', 1], ['area', '面積(坪)', 1], ['total', '總價(萬)', 1], ['price', '單價(萬/坪)', 1], ['own', '產權', 1],
  ['road', '臨路', 1], ['project', '鄰近開發案', 1], ['desc', '物件說明', 1],
  ['email', 'Email(不公開)', 0], ['status', '狀態', 0], ['note', '管理備註', 0]];

function doPost(e) {
  const p = (e && e.parameter) || {};
  if (p.website) return json_({ ok: true });            // 防機器人欄位被填，直接忽略
  if (p.type === '從業人員刊登') return postListing_(p);
  if (!p.name || !p.phone) return json_({ ok: false });

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sh.getLastRow() === 0) { sh.appendRow(HEADERS); sh.setFrozenRows(1); }
    sh.appendRow([new Date()].concat(FIELDS.map(f => keepText_(f, clean_(p[f])))).concat(['未處理']));
    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(NOTIFY_EMAIL,
        '【相信土地】新' + clean_(p.type) + '：' + clean_(p.name) + ' ' + clean_(p.county) + clean_(p.town),
        FIELDS.map((f, i) => HEADERS[i + 1] + '：' + clean_(p[f])).join('\n') + '\n\n試算表：' + ss.getUrl());
    }
  } finally {
    lock.releaseLock();
  }
  return json_({ ok: true });
}

function postListing_(p) {
  const phone = String(p.phone || '').replace(/[\s-]/g, '');
  if (!p.name || !p.title || !p.role || !/^09\d{8}$/.test(phone) || p.agree !== 'on') return json_({ ok: false, error: 'invalid' });
  if ((p.role === '不動產經紀人' || p.role === '不動產營業員') && !p.company) return json_({ ok: false, error: 'company' });
  if (p.line && !/^[A-Za-z0-9._@-]{1,40}$/.test(p.line)) p.line = '';

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(LIST_SHEET) || ss.insertSheet(LIST_SHEET);
    if (sh.getLastRow() === 0) { sh.appendRow(L_FIELDS.map(f => f[1])); sh.setFrozenRows(1); }
    // 同一支手機 24 小時內最多 5 筆，避免灌版
    const recent = sh.getLastRow() > 1 ? sh.getRange(2, 2, sh.getLastRow() - 1, 6).getValues() : [];
    const day = Date.now() - 86400000;
    if (recent.filter(r => String(r[5]).replace(/^'/, '') === phone && new Date(r[0]).getTime() > day).length >= 5) return json_({ ok: false, error: 'limit' });
    const id = 'U' + Utilities.formatDate(new Date(), 'Asia/Taipei', 'yyMMddHHmmss') + Math.floor(Math.random() * 90 + 10);
    const v = Object.assign({}, p, { id: id, ts: new Date(), phone: phone, status: '上架', note: '' });
    sh.appendRow(L_FIELDS.map(f => f[0] === 'ts' ? v.ts : keepText_(f[0], clean_(v[f[0]]))));
    CacheService.getScriptCache().remove('listings');
    if (NOTIFY_EMAIL) {
      MailApp.sendEmail(NOTIFY_EMAIL, '【相信土地】新自行刊登：' + clean_(p.title) + '（' + clean_(p.role) + ' ' + clean_(p.name) + '）',
        L_FIELDS.map(f => f[1] + '：' + clean_(v[f[0]])).join('\n') + '\n\n要下架請把試算表該列「狀態」改成「下架」。\n' + ss.getUrl());
    }
    return json_({ ok: true, id: id });
  } finally {
    lock.releaseLock();
  }
}

function doGet(e) {
  const a = (e && e.parameter && e.parameter.action) || '';
  if (a !== 'listings') return json_({ ok: true });
  const cache = CacheService.getScriptCache();
  const hit = cache.get('listings');
  if (hit) return ContentService.createTextOutput(hit).setMimeType(ContentService.MimeType.JSON);
  const sh = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(LIST_SHEET);
  let out = [];
  if (sh && sh.getLastRow() > 1) {
    const rows = sh.getRange(2, 1, sh.getLastRow() - 1, L_FIELDS.length).getValues();
    const si = L_FIELDS.findIndex(f => f[0] === 'status');
    const cut = Date.now() - LIST_DAYS * 86400000;
    out = rows.filter(r => r[si] === '上架' && new Date(r[1]).getTime() > cut).map(r => {
      const o = {};
      L_FIELDS.forEach((f, i) => { if (f[2]) o[f[0]] = f[0] === 'ts' ? Utilities.formatDate(new Date(r[i]), 'Asia/Taipei', 'yyyy-MM-dd') : String(r[i]).replace(/^'/, ''); });
      return o;
    }).reverse();
  }
  const body = JSON.stringify({ ok: true, items: out });
  cache.put('listings', body, 300);
  return ContentService.createTextOutput(body).setMimeType(ContentService.MimeType.JSON);
}

// 截斷長度，並避免以 = + - @ 開頭的內容被試算表當成公式執行
// 電話、LINE 開頭的 0 不被試算表吃掉
function keepText_(f, v) {
  return (f === 'phone' || f === 'line' || f === 'license') && /^\d/.test(v) ? "'" + v : v;
}

function clean_(v) {
  return String(v == null ? '' : v).slice(0, 600).replace(/^[=+\-@]/, "'$&");
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
