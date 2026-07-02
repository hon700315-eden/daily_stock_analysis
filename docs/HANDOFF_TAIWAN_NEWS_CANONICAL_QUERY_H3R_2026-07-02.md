# 台股新聞 canonical query H-3R 修正紀錄

日期：2026-07-02

## 結論

- 台股新聞查詢內部正式 canonical code 使用 Yahoo suffix：TWSE 股票為 `.TW`，TPEX 股票為 `.TWO`。
- `.TW` / `.TWO` 是正式內部查詢輸出格式；`TWSE:` / `TPEX:` 是可接受輸入格式。
- 顯式 suffix / prefix 格式轉換不依賴正式 Drive snapshot 或台股索引檔。
- 裸碼例如 `2330`、`6488` 的交易所判定仍需既有台股索引證據；無索引時不猜測交易所。

## 根因

GitHub runner 沒有使用者本機 Google Drive 的正式台股索引。修正前 `resolve_taiwan_stock_symbol()` 會直接進入索引搜尋，導致無索引環境下 `TWSE:2330`、`TPEX:6488` 無法解析。新聞查詢因此未被辨識為台股，落回一般中文股票查詢並保留原始前綴，例如：

- `台積電 TWSE:2330 股票 最新消息`
- `環球晶 TPEX:6488 股票 最新消息`

## 修正

- `resolve_taiwan_stock_symbol()` 先處理不需要索引即可確定的顯式格式：
  - `2330.TW` -> `2330.TW`
  - `TWSE:2330` -> `2330.TW`
  - `6488.TWO` -> `6488.TWO`
  - `TPEX:6488` -> `6488.TWO`
- 裸碼與名稱查詢仍沿用正式台股索引，不新增資料來源，不要求 runner 存取 Google Drive。
- 新增無 Drive subprocess 測試，防止本機 module cache 或正式資料污染測試結果。
