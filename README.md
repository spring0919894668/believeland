# 相信土地 believeland.tw

全台農地開發動態儀表板：區段徵收、特定區、新訂擴大都市計畫與產業園區進度，每月更新新聞。

- 產生網站：`python3 build.py`，輸出到 `dist/`
- Cloudflare Pages 建置設定：Build command `python3 build.py`、Build output directory `dist`
- 資料：`data/projects.json`（開發案）、`data/news.json`（每月新聞，由排程自動更新）、`data/listings.json`（上架物件）、`data/site.json`（網站設定）

詳細說明見 [部署說明.md](部署說明.md)。
