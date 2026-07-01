# 台股月營收、基本面與公司事件稽核交接

日期：2026-07-01

分支：`feat/taiwan-fundamental-events-audit`

起始基準：`1764fe720dc2c7c569dd384885e50eb418491961`

## 已證實事實

### 月營收程式與資料現況

- Repository 現行程式未找到台股月營收 reader、fetcher、provider、schema、manifest、API、service、WebUI 或 runtime 接線。
- 關鍵詞 `monthly revenue`、`monthly_revenue`、`月營收`、`當月營收`、`累計營收`、`年增率`、`月增率`、`MOPS`、`公開資訊觀測站` 只命中搜尋語境、Prompt 限制與既有稽核文件。
- Git 歷史未找到月營收相關提交證據。
- 正式資料根目錄未找到月營收正式檔、manifest、reader、writer 或 validator。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 財報程式與資料現況

- 現行基本面管線位於 `data_provider/base.py` 的 `DataFetcherManager.get_fundamental_context()`。
- A 股基本面由 `data_provider/fundamental_adapter.py` 的 AkShare adapter 提供，並非台股正式資料來源。
- 台股 `2330.TW` runtime smoke 顯示 `market=tw`，走 offshore/yfinance 基本面路徑；未進入中國 AkShare 基本面 adapter。
- `data_provider/yfinance_fundamental_adapter.py` 現有財報欄位支援 `financial_report`，但文件與來源語義是 HK/US yfinance 基本面，未找到台股正式財報資料產品或台股專用財報 reader。
- 正式 Drive 未找到財務報表正式檔、manifest、reader、writer 或 validator。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 財務比率現況

- 現行 A 股 AkShare adapter 可抽取 `ROE`、毛利率等欄位；HK/US yfinance adapter 可抽取 `returnOnEquity`、`grossMargins` 等欄位。
- 未找到台股正式財務比率資料檔、schema、manifest、API 或 WebUI 接線。
- 正式 Drive 未找到財務比率正式檔。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 估值現況

- 台股正式 raw TWSE/TPEX 檔內可見交易日行情附帶的 `本益比` 字樣，但 `feature_matrix.csv` schema 未整理出 PE/PB/殖利率欄位。
- `feature_matrix.csv` 最新正式檔：`TW_Stock_Data_Drive/02_features/trade_date=2026-07-01/feature_matrix.csv`，row count 為 11,347 筆資料列；欄位為交易、量價與技術指標，未包含正式估值欄位。
- `snapshot_manifest.json` 最新正式檔：`TW_Stock_Data_Drive/01_market_data/daily_snapshot/trade_date=2026-07-01/snapshot_manifest.json`，row count 為 total 11,347、TPEX 9,979、TWSE 1,368，schema 為 `L2B_DAILY_SNAPSHOT_RETENTION_V1`。
- 未找到 EPS 期間、每股淨值、股利、計算日期與估值資料來源的完整正式契約。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 股利與除權息現況

- 現行 portfolio 有手動 `cash_dividend` 與 `split_adjustment` 模型與 API，屬於使用者手動事件，不是台股正式股利或除權息資料來源。
- raw TPEX/TWSE 日行情檔中可見 `Change` 欄帶出 `除息`、`除權`、`除權息` 字樣，但未找到正式股利／除權息 reader、schema、manifest、validator、API 或 WebUI 接線。
- 正式 Drive 未找到股利與除權息正式檔。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 重大訊息現況

- `src/search_service.py` 只將重大訊息、公司公告、TWSE、TPEx、公開資訊觀測站作為搜尋查詢語境。
- 未找到重大訊息 fetcher、reader、正式來源 schema、manifest、API、WebUI、測試或 runtime 接線。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 法說會與股東會現況

- Repository 關鍵詞搜尋未找到法說會或股東會正式 reader、fetcher、schema、API、WebUI 或測試。
- 搜尋詞或 Prompt 語境不得視為正式資料能力。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 增減資與庫藏股現況

- Repository 關鍵詞搜尋未找到增資、減資或庫藏股正式 reader、fetcher、schema、API、WebUI 或測試。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### 停復牌現況

- 現行程式只有行情 provider 對停牌資料缺失的註解與防護，未找到台股停復牌正式事件 reader、schema、manifest、API 或 WebUI 接線。
- 裁決：不可用。
- 未找到可驗證證據，因此未實作。

### API／WebUI／Prompt 接線

- API 歷史與分析端點可傳遞 `financial_report` 與 `dividend_metrics`，但其來源是既有 `fundamental_context`，不是台股正式財報或事件資料。
- Web 前端只消費既有分析結果型別，未找到台股月營收、正式財報、正式估值或公司事件頁面接線。
- Prompt 先前在 `financial_report={}` 且 `dividend={}` 時仍可能渲染空財報／股利表格。本次已修正為只有有結構化欄位值時才渲染。
- 台股新聞 Prompt 已有明確限制：搜尋摘要中的財務數字只可視為外部網頁線索，不得當成已驗證財務資料；缺少來源、日期或可驗證內容時必須標為 unavailable。

### 正式資料根目錄盤點

根目錄：`/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`

- 最新日線 retained snapshot：`01_market_data/daily_snapshot/trade_date=2026-07-01/snapshot_manifest.json`，schema `L2B_DAILY_SNAPSHOT_RETENTION_V1`，status `retained`，row count total 11,347、TPEX 9,979、TWSE 1,368。
- 最新特徵檔：`02_features/trade_date=2026-07-01/feature_matrix.csv`，schema 由 `02_features/trade_date=2026-07-01/feature_manifest.json` 記錄為 `L3A_FEATURE_MANIFEST_V1`，status `success`，資料列 11,347。
- 最新篩選封包：`05_packages/trade_date=2026-07-01/package_manifest.json`，schema `L3B_PACKAGE_MANIFEST_V1`，status `locked`，candidate_total 16。
- 月營收正式檔：未找到可驗證證據，因此未實作。
- 財務報表正式檔：未找到可驗證證據，因此未實作。
- 財務比率正式檔：未找到可驗證證據，因此未實作。
- 估值正式檔：未找到可驗證證據，因此未實作。
- 股利與除權息正式檔：未找到可驗證證據，因此未實作。
- 公司事件正式檔：未找到可驗證證據，因此未實作。
- 本次未修改任何正式 Drive 資料。

## 本次修改

- 修正 `src/analyzer.py`：只有結構化財報或股利欄位有實際值時，才渲染「財報與股利」Prompt 表格，避免空表被模型誤解為正式財務資料證據。
- 更新 `tests/test_analyzer_news_prompt.py`：新增台股無結構化財報時不渲染財報表格的回歸測試。
- 更新 `docs/CHANGELOG.md`：記錄本次 Prompt 邊界收斂。
- 新增本交接文件。

## 實際測試結果

- `./.venv/bin/python -m pytest tests/test_analyzer_news_prompt.py -q`：30 passed，1 warning。
- `./.venv/bin/python -m pytest`：4068 passed，3 skipped，46 warnings，362 subtests passed。
- `PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh`：backend-gate all checks passed。
- `./.venv/bin/python -m py_compile src/analyzer.py tests/test_analyzer_news_prompt.py`：通過。
- `git diff --check`：通過。
- runtime smoke：`DataFetcherManager().get_fundamental_context("2330.TW", budget_seconds=0)` 回傳 `market=tw`、`status=not_supported`，coverage 全為 `not_supported`，source chain 未出現中國 provider。
- import smoke：`data_provider.base`、`data_provider.yfinance_fundamental_adapter`、`data_provider.fundamental_adapter`、`src.analyzer`、`src.core.pipeline`、`src.services.analysis_context_builder` 匯入成功；LiteLLM 嘗試抓遠端模型成本表因網路不可用而 fallback local backup。

## 不可用或待查

- 月營收：未找到可驗證證據，因此未實作。
- 財報正式資料：未找到可驗證證據，因此未實作。
- 財務比率正式資料：未找到可驗證證據，因此未實作。
- 估值正式資料：未找到可驗證證據，因此未實作。
- 股利與除權息正式資料：未找到可驗證證據，因此未實作。
- 重大訊息正式資料：未找到可驗證證據，因此未實作。
- 法說會與股東會正式資料：未找到可驗證證據，因此未實作。
- 增減資與庫藏股正式資料：未找到可驗證證據，因此未實作。
- 停復牌正式資料：未找到可驗證證據，因此未實作。
