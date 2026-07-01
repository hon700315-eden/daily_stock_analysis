# 台股 API 與設定契約收斂交接

日期：2026-07-01

## 已證實事實

起始基準：

- 本機 `HEAD`、`main`、`origin/main`、遠端 `refs/heads/main` 皆為 `99423107485c038762534843672f073426aae090`。
- 主倉庫起始工作區乾淨，未偵測到 merge、rebase、cherry-pick。
- 來源日更專案 `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean` 既有 dirty 與未追蹤項目未納入本批次，且本批次未修改該專案。

實際 API route 來源：

- `api.app.create_app().openapi()` 匯出的 runtime route 數量為 117。
- FastAPI 目前會把 include router 延遲為 `_IncludedRouter`，因此直接列 `app.routes` 不足以作為 v1 子路由證據。

股票搜尋與行情 route：

| Route | Method | Schema | Service | 正式資料來源 | 前端使用 | 裁決 |
| --- | --- | --- | --- | --- | --- | --- |
| `/api/v1/stocks/search` | GET | `StockSearchResponse` | `search_taiwan_stocks` | retained daily snapshot | 無直接 client；自動完成使用本地索引 | 保留 |
| `/api/v1/stocks/{stock_code}/quote` | GET | `StockQuote` | `StockService.get_realtime_quote` | `TaiwanDailyDataBridgeFetcher` | `apps/dsa-web/src/api/stocks.ts` | 修正缺價補零 |
| `/api/v1/stocks/{stock_code}/history` | GET | `StockHistoryResponse` | `StockService.get_history_data` | package `chartSeries` 或 snapshot | `apps/dsa-web/src/api/stocks.ts` | 保留 |
| `/api/v1/stocks/{stock_code}/technical` | GET | `StockTechnicalResponse` | `StockService.get_technical_data` | package technical fields | `apps/dsa-web/src/api/stocks.ts` | 保留 |
| `/api/v1/stocks/watchlist` | GET | `WatchlistResponse` | system config service | `STOCK_LIST` | `apps/dsa-web/src/api/systemConfig.ts` | 保留 |
| `/api/v1/stocks/watchlist/add` | POST | `WatchlistResponse` | system config service | `STOCK_LIST` | `apps/dsa-web/src/api/systemConfig.ts` | 保留 |
| `/api/v1/stocks/watchlist/remove` | POST | `WatchlistResponse` | system config service | `STOCK_LIST` | `apps/dsa-web/src/api/systemConfig.ts` | 保留 |

搜尋契約：

- 支援 `2330`、`2330.TW`、`TWSE:2330`、`台積電`、`6488`、`6488.TWO`、`TPEX:6488`、`環球晶`。
- 台股代碼正規化入口包含 `data_provider.base.normalize_stock_code` 與 `src.data.taiwan_stock_index.resolve_taiwan_stock_symbol`。
- 未找到台股搜尋資料時不宣告功能可用。

Quote 契約：

- `StockQuote.current_price` 現在允許 `null`，缺價不再補 `0.0`。
- `StockService` 在 `DataFetcherManager` 不可匯入時不再回傳占位行情。
- 台股 quote 回傳 `TWD`、`Asia/Taipei`、`symbol`、`exchange`、`source`、`data_status`。

History 契約：

- 台股 history 保留 `available`、`snapshot_only`、`not_found`。
- snapshot-only 標的不編造多日 history。

Technical 契約：

- 台股 technical 保留 `available` 或 `technical_unavailable`。
- 指標缺值保留 `null`。

Portfolio route：

| Route | Method | Schema | 前端使用 | 裁決 |
| --- | --- | --- | --- | --- |
| `/api/v1/portfolio/accounts` | GET/POST | account schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/accounts/{account_id}` | PUT/DELETE | account/delete schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/snapshot` | GET | `PortfolioSnapshotResponse` | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/trades` | GET/POST | trade schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/trades/{trade_id}` | DELETE | delete schema | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/cash-ledger` | GET/POST | cash schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/cash-ledger/{entry_id}` | DELETE | delete schema | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/corporate-actions` | GET/POST | corporate action schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/corporate-actions/{action_id}` | DELETE | delete schema | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/fx/refresh` | POST | `PortfolioFxRefreshResponse` | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/risk` | GET | `PortfolioRiskResponse` | `apps/dsa-web/src/api/portfolio.ts` | 保留 |
| `/api/v1/portfolio/imports/csv/*` | GET/POST | import schemas | `apps/dsa-web/src/api/portfolio.ts` | 保留 |

Portfolio 契約：

- account 預設 `market=tw`、`base_currency=TWD`。
- `tw` 已存在於 service/API schema 市場枚舉。
- 缺失價格已由既有 Portfolio 契約回傳 `null` 與受限資料品質，本批次未重做。

新聞與分析 route：

- `/api/v1/analysis/analyze`、`/api/v1/analysis/market-review`、`/api/v1/analysis/status/{task_id}`、`/api/v1/analysis/tasks`、`/api/v1/analysis/tasks/stream`、`/api/v1/analysis/tasks/{task_id}/flow` 實際存在。
- `/api/v1/history/{record_id}/news` 實際存在，讀取歷史報告新聞。
- `/api/v1/intelligence/sources*` 與 `/api/v1/intelligence/items` 實際存在，屬情報來源管理與資料查詢，不等同即時新聞搜尋 API。
- 無 LLM API Key 時，`src/analyzer.py` 既有契約回 `success=False` 與 `error_message='LLM API Key 未配置'`，不是成功假報告。

設定來源：

- runtime 預設：`DEFAULT_MARKET=tw`、`DEFAULT_LANGUAGE=zh-TW`、`DEFAULT_CURRENCY=TWD`、`DEFAULT_TIMEZONE=Asia/Taipei`、`DEFAULT_PRICE_COLOR_SCHEME=red_up`。
- `MARKET_REVIEW_REGION` runtime 預設與非法值回退皆為 `tw`。
- `.env.example` 先前仍示例 `MARKET_REVIEW_REGION=cn` 並描述回退為 `cn`，本批次修正為 `tw`。
- `TW_STOCK_DATA_ROOT` 由 `TaiwanDailyDataBridgeFetcher` 與 `src.data.taiwan_stock_index` 讀取；缺失時使用既有 Google Drive 預設路徑。本批次未修改 Google Drive 正式資料。

日更狀態與資料可用性：

- 健康檢查 route：`/api/health`、`/health`、`/api/v1/health`。
- 設定 readiness route：`/api/v1/system/config/setup/status`。
- 台股 snapshot 最新交易日目前由 `src.data.taiwan_stock_index.find_latest_taiwan_snapshot_path` 與 `TaiwanDailyDataBridgeFetcher._latest_snapshot_path` 內部讀取，未找到獨立 latest trade date API。
- quote/history/technical 目前以各自 response 的 `data_status` 或 `availability` 表達 `snapshot_only`、`not_found`、`technical_unavailable`。

中國 fallback 現況：

- 台股裸 4 位代碼與 `.TW`/`.TWO` route 已有測試證明不切到中國行情 provider。
- 本批次新增 quote 缺價測試，避免缺值被補成 `0.0`。

本次修改：

- `api/v1/schemas/stocks.py`：`StockQuote.current_price` 改為可空。
- `api/v1/endpoints/stocks.py`：quote endpoint 不再把缺失 `current_price` 補為 `0.0`。
- `src/services/stock_service.py`：service 不再把 quote 缺價補為 `0.0`，也不再回傳占位行情。
- `apps/dsa-web/src/api/stocks.ts`：前端 quote 型別同步允許 `current_price: null`。
- `.env.example`：`MARKET_REVIEW_REGION` 範例與註解改為 `tw` 回退。
- `docs/CHANGELOG.md`：新增 `[Unreleased]` 扁平條目。
- `tests/test_api_schema_pydantic.py`、`tests/test_taiwan_daily_bridge_fetcher.py`：補缺價保留 `null` 測試。

## 不可用或待查

- latest trade date API：未找到可驗證證據，因此未實作。
- data status API：未找到可驗證證據，因此未實作。
- snapshot status API：未找到可驗證證據，因此未實作。
- screening package status API：未找到可驗證證據，因此未實作。
- bridge health API：未找到可驗證證據，因此未實作。
- 市場概況獨立 API：未找到可驗證證據，因此未實作。
- 三大法人 API：未找到可驗證證據，因此未實作。
- 融資融券 API：未找到可驗證證據，因此未實作。
- 借券／當沖 API：未找到可驗證證據，因此未實作。
- 月營收 API：未找到可驗證證據，因此未實作。
- 財報 API：未找到可驗證證據，因此未實作。
- 估值 API：未找到可驗證證據，因此未實作。
- 公司事件 API：未找到可驗證證據，因此未實作。
- 可安全刪除的重複 route：未找到可驗證證據，因此未實作。

## Runtime smoke 結果

- 搜尋：`2330`、`2330.TW`、`TWSE:2330`、`台積電`、`6488`、`6488.TWO`、`TPEX:6488`、`環球晶` 皆回 200，且各 1 筆。
- Quote：`2330.TW`、`6488.TWO` 皆回 200，`currency=TWD`，`timezone=Asia/Taipei`，目前 `data_status=snapshot_only`。
- History：`2330.TW`、`6488.TWO` 皆回 200，目前 `data_status=snapshot_only`。
- Technical：`2330.TW`、`6488.TWO` 皆回 200，目前 `availability=technical_unavailable`。
- 不存在台股裸碼：`9999` quote 回 404，未切換至中國 provider。
- 設定 runtime 預設：`tw`、`zh-TW`、`TWD`、`Asia/Taipei`、`red_up`。

## 裁決表

| 項目 | 現行證據 | 問題 | 是否需要修正 | 允許修改範圍 |
| --- | --- | --- | --- | --- |
| 搜尋 API | runtime route、schema、smoke | 未找到需修正問題 | 否 | 無 |
| Quote API | runtime route、schema、service | 缺價被補 `0.0` | 是 | schema、endpoint、service、前端型別、測試 |
| History API | runtime route、schema、smoke | 未找到需修正問題 | 否 | 無 |
| Technical API | runtime route、schema、smoke | 未找到需修正問題 | 否 | 無 |
| Portfolio API | route、schema、client | 本批次未找到新問題 | 否 | 無 |
| 分析 API | route、analyzer runtime 分支 | 無 API Key 已回失敗契約 | 否 | 無 |
| 市場設定 | `src/config.py`、`.env.example` | 範例與 runtime 預設不一致 | 是 | `.env.example`、變更紀錄 |
| 資料狀態 | quote/history/technical response | 未找到獨立狀態 API | 否 | 無 |
| 重複 route | OpenAPI exact method/path 檢查 | 未找到可安全刪除證據 | 否 | 無 |
| 中國 fallback | 既有測試與 smoke | 本批次未找到新 fallback | 否 | 無 |
