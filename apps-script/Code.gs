/**
 * 相信土地 believeland.tw 委託表單後端
 * 貼到「Google 試算表 → 擴充功能 → Apps Script」，再部署為網頁應用程式。
 * 每次有人送出表單，就在試算表新增一列，並可寄 Email 通知你。
 */
const SHEET_NAME = '表單回覆';
const NOTIFY_EMAIL = 'spring0919894668@gmail.com';   // 新委託寄通知到這個信箱，留空則不寄

const FIELDS = ['type', 'name', 'phone', 'line', 'email', 'county', 'town', 'section', 'zone',
                'area', 'price', 'own', 'project', 'listing', 'message', 'page'];
const HEADERS = ['送出時間', '類型', '稱呼', '電話', 'LINE', 'Email', '縣市', '鄉鎮', '地段地號', '使用分區',
                 '面積(坪)', '價格(萬/坪)', '產權', '鄰近開發案', '物件編號', '說明', '來源頁', '處理狀態'];

function doPost(e) {
  const p = (e && e.parameter) || {};
  if (p.website) return json_({ ok: true });            // 防機器人欄位被填，直接忽略
  if (!p.name || !p.phone) return json_({ ok: false });

  const lock = LockService.getScriptLock();
  lock.waitLock(10000);
  try {
    const ss = SpreadsheetApp.getActiveSpreadsheet();
    const sh = ss.getSheetByName(SHEET_NAME) || ss.insertSheet(SHEET_NAME);
    if (sh.getLastRow() === 0) { sh.appendRow(HEADERS); sh.setFrozenRows(1); }
    sh.appendRow([new Date()].concat(FIELDS.map(f => clean_(p[f]))).concat(['未處理']));

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

// 截斷長度，並避免以 = + - @ 開頭的內容被試算表當成公式執行
function clean_(v) {
  return String(v == null ? '' : v).slice(0, 600).replace(/^[=+\-@]/, "'$&");
}

function json_(o) {
  return ContentService.createTextOutput(JSON.stringify(o)).setMimeType(ContentService.MimeType.JSON);
}
