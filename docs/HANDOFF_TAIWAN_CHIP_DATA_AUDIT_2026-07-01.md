# 台股籌碼資料稽核交接（2026-07-01）

## 已證實事實

### Git 歷史中的法人功能現況

- 歷史 commit `7715896fe4cc14f856a3e769dfdbf5c51cd1957d` 存在於目前 Repository 歷史，標題為 `feat(market): tw institutional-flows (三大法人) data-layer fetcher (#1829)`。
- 該 commit 新增 `data_provider/tw_institutional_fetcher.py`、`tests/test_tw_institutional_fetcher.py`，並修改 `docs/CHANGELOG.md`、`docs/market-support.md`。
- 目前 `data_provider/tw_institutional_fetcher.py` 與 `tests/test_tw_institutional_fetcher.py` 仍存在。
- 目前全倉搜尋只找到測試、文件與該 fetcher 本身引用 `TwInstitutionalFetcher` / `get_institutional_net`；未找到 service、API route、Web UI 或分析流程註冊呼叫。
- 該功能現況是線上資料層 fetcher/parser/cache，不是正式日更 Drive reader，也不是報告、Portfolio、API 或 WebUI 的已接線能力。

### 現行檔案與 runtime 路徑

- 三大法人程式證據：`data_provider/tw_institutional_fetcher.py`。
- 三大法人測試證據：`tests/test_tw_institutional_fetcher.py`。
- 三大法人來源證據：TWSE T86 `https://www.twse.com.tw/rwd/zh/fund/T86`、TPEx OpenAPI `https://www.tpex.org.tw/openapi/v1/tpex_3insti_daily_trading`。
- 三大法人 schema 證據：fetcher 解析 `stock_code`、`date`、`market`、`source`、`unit`、`foreign_net`、`trust_net`、`dealer_net`、`total_net`，單位為股。
- 三大法人 runtime 邊界：`.TW` 走 TWSE，`.TWO` 走 TPEx；非台股 suffix 回傳 `None`；缺欄、空資料、網路錯誤或無法轉換日期皆 fail-open 回傳 `None`。本次只以既有離線測試驗證 parser 與 fail-open 契約，未把線上端點視為正式日更資料。
- 籌碼分布現行 runtime：`DataFetcherManager.get_chip_distribution()` 消費 A 股專屬 AkShare/Tushare 籌碼資料。本次已修正台股 `.TW/.TWO` 直接回傳 `None`，不再嘗試中國市場資料源。

### 正式資料根目錄盤點

- `TW_STOCK_DATA_ROOT` 環境變數本次執行環境未設定。
- 唯讀盤點的正式資料根目錄為 `/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`。
- 該目錄目前有 567 個檔案，主要目錄為 `00_staging`、`01_market_data`、`02_features`、`03_screening`、`04_validation`、`05_packages`、`06_dashboard_sync`、`07_logs`。
- 檔名關鍵字搜尋未找到三大法人、融資融券、借券、當沖、注意股票、處置股票相關實體檔案。
- 最新正式日更日期為 `2026-06-30`。
- `00_staging/trade_date=2026-06-30/fetch_manifest.json` status 為 `success`，TWSE row count `1369`、TPEX row count `9978`、total `11347`。
- `02_features/trade_date=2026-06-30/feature_manifest.json` status 為 `success`，feature rows `11347`。
- `03_screening/trade_date=2026-06-30/screening_manifest.json` status 為 `success`。
- `05_packages/trade_date=2026-06-30/package_manifest.json` status 為 `locked`，package schema version 為 `TW_STOCK_SCREENING_PACKAGE_V1`。

### 各類資料最新日期

- 日線行情與技術資料最新日期：`2026-06-30`。
- 三大法人正式 Drive 資料：未找到可驗證證據，因此未實作。
- 融資融券正式 Drive 資料：未找到可驗證證據，因此未實作。
- 借券正式 Drive 資料：未找到可驗證證據，因此未實作。
- 當沖正式 Drive 資料：未找到可驗證證據，因此未實作。
- 注意股票正式 Drive 資料：未找到可驗證證據，因此未實作。
- 處置股票正式 Drive 資料：未找到可驗證證據，因此未實作。

### schema

- `00_staging/trade_date=2026-06-30/normalized/daily_market_normalized.csv` 欄位：`trade_date, market, code, name, open, high, low, close, change, volume, amount, transactions, source, source_status`。
- `02_features/trade_date=2026-06-30/feature_matrix.csv` 欄位：`trade_date, market, code, name, close, volume, amount, transactions, volume_lots, volume_3d_avg, volume_10d_avg, volume_20d_avg, ma5, ma10, ma20, ma60, bollinger_mid, bollinger_upper, bollinger_lower, bollinger_width, kd_k, kd_d, prev_kd_k, macd, macd_signal, macd_hist, prev_macd_hist, s1, r1, rr, funnel_passed, funnel_exclusion_reason, history_status`。
- `02_features/trade_date=2026-06-30/technical_indicators.csv` 欄位：`trade_date, market, code, name, close, volume, volume_lots, volume_3d_avg, volume_10d_avg, volume_20d_avg, past_3d_max_volume, ma5, ma10, ma20, ma60, bollinger_mid, bollinger_upper, bollinger_lower, bollinger_width, kd_k, kd_d, prev_kd_k, macd, macd_signal, macd_hist, prev_macd_hist, s1, r1, rr, history_status`。
- 上述 schema 未包含三大法人、融資融券、借券、當沖、注意股票或處置股票欄位。

### manifest

- `00_staging/trade_date=2026-06-30/fetch_manifest.json`：`L2A_FETCH_MANIFEST_V1`。
- `02_features/trade_date=2026-06-30/feature_manifest.json`：`L3A_FEATURE_MANIFEST_V1`。
- `03_screening/trade_date=2026-06-30/screening_manifest.json`：`L3A_SCREENING_MANIFEST_V1`。
- `05_packages/trade_date=2026-06-30/package_manifest.json`：`L3B_PACKAGE_MANIFEST_V1`。
- 未找到三大法人、融資融券、借券、當沖、注意股票或處置股票 manifest。

### API／UI 接線

- 未找到三大法人或籌碼專用 API route。
- 未找到三大法人資料被註冊進分析 context、報告 schema、Portfolio 或 WebUI 的現行證據。
- 既有分析 context 有 `chip` 區塊，但來源是 A 股籌碼分布，不是台股三大法人、融資融券、借券、當沖、注意或處置資料。
- 來源日更專案只讀搜尋顯示前端存在法人與融資融券「待補」文字，以及舊交接文件記錄 Drive 無正式法人／融資融券路徑；此為缺口證據，不是可用資料證據。

### 本次修改

- `data_provider/base.py`：台股 `.TW/.TWO` 進入 `get_chip_distribution()` 時直接回傳 `None`，避免落入 A 股專屬 AkShare/Tushare 籌碼資料源。
- `tests/test_chip_distribution_manager.py`：新增台股籌碼不走中國資料源回歸測試。
- `docs/HANDOFF_TAIWAN_CHIP_DATA_AUDIT_2026-07-01.md`：新增本交接文件。
- `docs/CHANGELOG.md`：新增本次修復與文件紀錄。

### 測試結果

- 直接相關測試：`./.venv/bin/python -m pytest tests/test_chip_distribution_manager.py tests/test_tw_institutional_fetcher.py`，24 passed，1 warning。
- 全量 pytest：`./.venv/bin/python -m pytest`，4067 passed，3 skipped，46 warnings，362 subtests passed。
- `ci_gate.sh`：`PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh`，backend-gate all checks passed；4067 passed，1 skipped，2 deselected，46 warnings，362 subtests passed。
- `git diff --check`：通過。
- 受影響 Python 檔案 py_compile 與 import smoke：通過。
- Runtime smoke：`DataFetcherManager.get_chip_distribution("6488.TWO")` 搭配測試用中國籌碼 fetcher，結果 `chip=None` 且 fetcher calls 為 `0`。

## 不可用或待查

### 裁決表

| 資料類別 | 程式證據 | 正式資料證據 | Runtime 可用 | API／UI 使用 | 裁決 |
| --- | --- | --- | --- | --- | --- |
| 三大法人 | 有 | 無 | 是，僅離線測試既有 fetcher 契約 | 無 | 不可用 |
| 融資融券 | 無 | 無 | 否 | 無 | 不可用 |
| 借券 | 無 | 無 | 否 | 無 | 不可用 |
| 當沖 | 無 | 無 | 否 | 無 | 不可用 |
| 注意股票 | 無 | 無 | 否 | 無 | 不可用 |
| 處置股票 | 無 | 無 | 否 | 無 | 不可用 |

### 沒有正式資料的項目

- 三大法人：未找到可驗證證據，因此未實作。
- 融資融券：未找到可驗證證據，因此未實作。
- 借券：未找到可驗證證據，因此未實作。
- 當沖：未找到可驗證證據，因此未實作。
- 注意股票：未找到可驗證證據，因此未實作。
- 處置股票：未找到可驗證證據，因此未實作。

### 端點失效的項目

- 本次未將任一端點判定為可用正式日更資料源。
- 三大法人雖有 TWSE/TPEx fetcher 程式，但未找到 Drive writer、reader、manifest、schema 或 API/UI 接線，因此不得宣告為目前正式能力。

### 只有歷史 commit 的項目

- 三大法人接線：`7715896` 只證明資料層 fetcher 曾被加入且目前檔案仍存在，不證明報告、API、WebUI 或正式日更資料已可用。

### 只有測試樣本的項目

- `tests/test_tw_institutional_fetcher.py` 使用離線 fixtures 驗證 parser 行為；fixtures 不是正式資料檔，也不是 Drive 日更資料。

### 只有 UI 殼層的項目

- 來源日更專案存在法人與融資融券待補顯示文字，但未找到正式資料、manifest、reader 或 writer。未找到可驗證證據，因此未實作。

### 未接線項目與原因

- 三大法人未接線：缺 Drive 正式資料、reader/writer/manifest/schema、service/API/WebUI 消費證據。
- 融資融券未接線：未找到程式與正式資料證據。
- 借券未接線：未找到程式與正式資料證據。
- 當沖未接線：未找到程式與正式資料證據。
- 注意股票未接線：未找到程式與正式資料證據。
- 處置股票未接線：未找到程式與正式資料證據。
