# 台股市場概況正式資料可用性稽核

本文件記錄 Batch 5A 對台股市場概況正式資料與既有程式碼的唯讀稽核結果。

## 稽核範圍

- Repository：`/Users/youjunhong/Documents/daily_stock_analysis`
- 起始 HEAD：`36c82a911587995de69ca1443f9a65c42e330a8d`
- 功能分支：`feat/taiwan-market-overview-audit`
- 環境變數 `TW_STOCK_DATA_ROOT`：未設定
- 程式預設正式資料根目錄：
  `/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`
- 只讀候選同步目錄：
  `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean`

本次未修改 `TW_Stock_Dashboard_Clean`，未修改 Google Drive 正式資料，未重新抓取 TWSE／TPEX，未新增外部資料來源。

## 找到的正式檔案

### `latest_screening_package.json`

- 路徑：
  `/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive/06_dashboard_sync/latest_screening_package.json`
- 檔案大小：`1513941` bytes
- 資料日期：`metadata.tradeDate = 2026-06-30`
- 產生時間：`metadata.generatedAt = 2026-06-30T20:08:14.676191+08:00`
- 狀態：`metadata.status = success`
- schema：`metadata.schemaVersion = TW_STOCK_SCREENING_PACKAGE_V1`
- 單位：`metadata.volumeUnit = lots`，`metadata.sharesPerLot = 1000`
- 頂層欄位：`chartSeries`、`emptyStates`、`metadata`、`productionChartManifest`、`screening_results`、`summary`
- `metadata.historySource.marketCoverage`：`["TWSE"]`
- `chartSeries` 筆數：`11`
- `chartSeries` 股票代碼：`1402`、`1708`、`2308`、`2317`、`2886`、`2890`、`2892`、`3005`、`4916`、`4927`、`6285`

判定：

- 是否包含市場指數：未找到可驗證證據，因此未接線。
- 是否包含官方漲跌家數：未找到可驗證證據，因此未接線。
- 是否包含官方成交金額：未找到可驗證證據，因此未接線。
- 是否包含官方漲停／跌停統計：未找到可驗證證據，因此未接線。
- 是否能區分 TWSE／TPEX：`chartSeries` 個股列有 `market` 欄位；本檔 `metadata.historySource.marketCoverage` 只列 `TWSE`。
- 是否有明確單位：量能單位有 `volumeUnit = lots` 與 `sharesPerLot = 1000`；市場成交金額統計未找到可驗證證據。

### `daily_market_normalized.csv`

- 路徑：
  `/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive/01_market_data/daily_snapshot/trade_date=2026-06-30/daily_market_normalized.csv`
- 檔案大小：`967969` bytes
- 資料日期：`2026-06-30`
- 欄位：`trade_date`、`market`、`code`、`name`、`open`、`high`、`low`、`close`、`change`、`volume`、`amount`、`transactions`、`source`、`source_status`
- 總列數：`11347`
- TWSE 列數：`1369`
- TPEX 列數：`9978`
- `source_status`：全部為 `success`
- 重複鍵檢查：`market + code` 重複數為 `0`
- 來源分類：`source = twse` 有 `1369` 列，`source = tpex` 有 `9978` 列

關鍵字檢查結果：

- 找到名稱含 `臺灣加權` 或 `指數` 的商品列，例如 `006204 永豐臺灣加權`、`00663L 國泰臺灣加權正2`、`00664R 國泰臺灣加權反1`、`020039 元大加權N`。
- 上述列為 ETF、槓桿反向商品或 ETN 類商品，不是臺灣加權指數或櫃買指數本身。

判定：

- 是否包含市場指數：未找到可驗證證據，因此未接線。
- 是否包含官方漲跌家數：未找到可驗證證據，因此未接線。
- 是否包含成交金額：逐檔 `amount` 欄位存在；官方市場成交金額統計未找到可驗證證據，因此未接線。
- 是否包含漲停／跌停統計：未找到可驗證證據，因此未接線。
- 是否能區分 TWSE／TPEX：可以，依 `market` 欄位區分。
- 是否有明確單位：逐檔 `amount` 單位由既有 quote 接線核定為 TWD；逐檔 `volume` 單位由既有 quote 接線核定為股。官方市場概況統計單位未找到可驗證證據。

### `snapshot_manifest.json`

- 路徑：
  `/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive/01_market_data/daily_snapshot/trade_date=2026-06-30/snapshot_manifest.json`
- 檔案大小：`506` bytes
- 資料日期：`trade_date = 2026-06-30`
- 保留時間：`retained_at = 2026-06-30T20:07:10.164198+08:00`
- 狀態：`status = retained`
- schema：`schema_version = L2B_DAILY_SNAPSHOT_RETENTION_V1`
- 擷取狀態：`source_fetch_status = success`
- 來源 stage：`00_staging/trade_date=2026-06-30/`
- 列數：`total = 11347`，`twse = 1369`，`tpex = 9978`
- sha256：`input_sha256` 與 `output_sha256` 同為 `7b9d53c8ca71bb29fa607caff4e04eb003fb05bc2d1cf805d6c13c939893d50b`

判定：

- manifest 可證明 snapshot retained 狀態、日期、列數與 TWSE／TPEX 列數。
- manifest 未提供市場指數、官方漲跌家數、官方成交金額、官方漲停／跌停統計或統計口徑。

## 其他找到的候選檔案

- `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean/dashboard-app/public/dashboard-data/latest_screening_package.json`
  - 大小：`1622116` bytes
  - 頂層欄位同為 `chartSeries`、`emptyStates`、`metadata`、`productionChartManifest`、`screening_results`、`summary`
  - `chartSeries` 筆數：`12`
- `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean/dashboard-app/dist/dashboard-data/latest_screening_package.json`
  - 大小：`1622116` bytes
  - 頂層欄位同為 `chartSeries`、`emptyStates`、`metadata`、`productionChartManifest`、`screening_results`、`summary`
  - `chartSeries` 筆數：`12`

這兩個檔案位於禁止修改的候選同步專案內。本次只讀檢查，未作為正式接線來源。

## 既有程式碼盤點

- 市場概況 service：
  - `src/market_analyzer.py` 有 `MarketAnalyzer.get_market_overview()` 與 `MarketOverview`。
  - 狀態：已存在且正在使用於大盤復盤／Market Light；本次前不接受 `tw`，`tw` 會降回 `cn`。
- 市場概況 endpoint：
  - `api/v1/router.py` 未掛載獨立市場概況 endpoint。
  - 狀態：完全不存在。
- 市場概況 schema：
  - `src/market_analyzer.py` 有內部 dataclass `MarketOverview`。
  - `api/v1/schemas` 未找到獨立台股市場概況公開 schema。
  - 狀態：內部模型已存在；公開 API schema 完全不存在。
- 臺灣指數 fetcher：
  - `data_provider/yfinance_fetcher.py` 有 `_get_tw_main_indices()`，使用 Yahoo Finance `^TWII` 與 `^TWOII`。
  - 狀態：已存在但不是本批次正式 Drive／TWSE／TPEX 資料來源，因此未接線為正式市場概況。
- 臺灣市場統計 reader：
  - 未找到讀取正式 Drive 市場統計的 reader。
  - 狀態：完全不存在。
- WebUI 市場概況 API client：
  - `apps/dsa-web/src/api/stocks.ts` 只有股票級 quote/history/technical。
  - 狀態：完全不存在。
- WebUI 市場概況元件：
  - 未找到台股市場概況元件。
  - 狀態：完全不存在。
- 分析流程中的市場概況注入：
  - `src/services/daily_market_context.py` 會讀取或生成大盤上下文。
  - `src/core/market_review.py` 與 `api/v1/endpoints/analysis.py` 預設 region 可為 `tw`。
  - 狀態：已存在且正在使用於大盤上下文；本次修正 `MarketAnalyzer` 避免 `tw` 初始化降回 `cn`。

## 目標欄位可用性判定

| 欄位 | 判定 | 證據與處置 |
| --- | --- | --- |
| 臺灣加權指數 | `confirmed_unavailable` | 正式 package 與 retained snapshot 未找到指數列或指數欄位；Yahoo Finance 既有 fetcher 不是本批次正式來源，因此未接線。 |
| 櫃買指數 | `confirmed_unavailable` | 正式 package 與 retained snapshot 未找到指數列或指數欄位；Yahoo Finance 既有 fetcher 不是本批次正式來源，因此未接線。 |
| TWSE 上漲／下跌／平盤家數 | `available_but_scope_unclear` | snapshot 有逐檔 `change` 與 `market = TWSE`，但未證明 snapshot 是官方統計口徑，且沒有官方漲跌家數欄位，因此未接線。 |
| TPEX 上漲／下跌／平盤家數 | `available_but_scope_unclear` | snapshot 有逐檔 `change` 與 `market = TPEX`，但未證明 snapshot 是官方統計口徑，且沒有官方漲跌家數欄位，因此未接線。 |
| TWSE 成交金額 | `available_but_scope_unclear` | snapshot 有逐檔 `amount` 與 `market = TWSE`，但未提供官方市場成交金額統計欄位，因此未接線。 |
| TPEX 成交金額 | `available_but_scope_unclear` | snapshot 有逐檔 `amount` 與 `market = TPEX`，但未提供官方市場成交金額統計欄位，因此未接線。 |
| 漲停家數 | `confirmed_unavailable` | 未找到官方漲停家數欄位，也未找到可靠漲停價欄位，因此未接線。 |
| 跌停家數 | `confirmed_unavailable` | 未找到官方跌停家數欄位，也未找到可靠跌停價欄位，因此未接線。 |
| 最新有效交易日 | `confirmed_available` | manifest `trade_date = 2026-06-30`，package `metadata.tradeDate = 2026-06-30`。 |
| 資料更新狀態 | `confirmed_available` | manifest `status = retained`、`source_fetch_status = success`；package `metadata.status = success`、`metadata.isValidated = true`。 |

## 已接線欄位

本批次沒有新增市場概況 API 或 WebUI 接線。

本批次只做最小防禦修正：`MarketAnalyzer(region="tw")` 保留 `tw`，不再初始化為 `cn`。此修正避免台股預設市場下的大盤復盤流程誤用中國市場區域。

## 未接線欄位

- 臺灣加權指數：未找到可驗證證據，因此未實作。
- 櫃買指數：未找到可驗證證據，因此未實作。
- 官方 TWSE 漲跌家數：未找到可驗證證據，因此未實作。
- 官方 TPEX 漲跌家數：未找到可驗證證據，因此未實作。
- 官方 TWSE 成交金額：未找到可驗證證據，因此未實作。
- 官方 TPEX 成交金額：未找到可驗證證據，因此未實作。
- 官方漲停家數：未找到可驗證證據，因此未實作。
- 官方跌停家數：未找到可驗證證據，因此未實作。

## 不採用 snapshot 彙總的原因

retained snapshot 的逐檔資料可驗證 `market`、`change`、`amount`、`source_status` 與 row count，但本次未找到以下證據：

- snapshot 是官方市場統計口徑。
- 特殊商品納入範圍可對齊官方漲跌家數。
- 逐檔 `amount` 彙總可對齊官方市場成交金額。
- 漲停／跌停價欄位或官方漲跌停統計欄位存在。

因此本批次不從 snapshot 彙總漲跌家數、成交金額、漲停家數或跌停家數。
