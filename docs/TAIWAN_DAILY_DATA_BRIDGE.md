# Taiwan Daily Data Bridge

This bridge lets `daily_stock_analysis` read retained Taiwan daily snapshots and
the existing dashboard package without changing either upstream system.

## Data Products

正式接線分成三條唯讀資料路徑：

- Quote：優先讀取最新有效 retained snapshot。
- History：優先讀取 `latest_screening_package.json` 內該股票的 `chartSeries`。
- Technical：優先讀取 `latest_screening_package.json` 內該股票既有技術指標。

Package lookup priority:

1. `06_dashboard_sync/latest_screening_package.json`
2. `dashboard-app/public/dashboard-data/latest_screening_package.json`
3. `01_market_data/daily_snapshot/trade_date=YYYY-MM-DD/daily_market_normalized.csv`

Snapshot selection scans `trade_date=YYYY-MM-DD` directories and only accepts a
directory when both `daily_market_normalized.csv` and `snapshot_manifest.json`
exist, the CSV is non-empty, and the manifest status is one of the formal
allowed statuses such as `retained` or an existing success/complete status.
Rejected, staging, empty, damaged, or incomplete snapshots are skipped. No trade
date is hard-coded.

## Configuration

Taiwan is the formal default market for the application:

- market: `TW` / runtime region `tw`
- language: `zh-TW`
- currency: `TWD`
- timezone: `Asia/Taipei`
- price color: red up, green down
- listed suffix: `.TW`
- OTC suffix: `.TWO`
- primary indices: 加權指數、櫃買指數

`TW_STOCK_DATA_ROOT` is optional for local development. It can point to the
official Drive root, the synchronized `TW_Stock_Dashboard_Clean` root, or a
single `latest_screening_package.json` file.

In GitHub Actions, the daily analysis workflow must not rely on a user Mac
Google Drive mount. It downloads the latest upstream
`tw-stock-daily-official-YYYY-MM-DD` artifact from
`hon700315-eden/TW_Stock_Dashboard_Clean`, extracts it under `RUNNER_TEMP`, sets
`TW_STOCK_DATA_ROOT` to the extracted `TW_Stock_Data_Drive`, and runs the strict
readback smoke before analysis starts. Download or validation failure stops the
workflow; it does not fall back to China market providers.

Cross-repository artifact access uses `UPSTREAM_ARTIFACT_TOKEN` when configured.
The token only needs read access to the upstream repository Actions artifacts.
When the upstream repository is public and GitHub permits it, the workflow can
fall back to the built-in `github.token`; private or restricted upstream access
requires setting `UPSTREAM_ARTIFACT_TOKEN` in the
`daily_stock_analysis` repository secrets.

When unset, the bridge checks:

`/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`

## Symbol Mapping

Only explicit upstream markets are mapped:

- `market=TWSE`, `code=2330` -> `2330.TW`
- `market=TPEX`, `code=6488` -> `6488.TWO`

Codes already ending in `.TW` or `.TWO` are left unchanged. Unknown markets are
not guessed. Bare codes such as `2330` are resolved only when the existing
package or snapshot contains exactly one matching market/code row; ambiguous
matches fail clearly.

The public helper accepts both `(market, code)` and `(code, market)` argument
orders so external smoke checks can verify the same explicit mapping without
changing the bridge's internal row-reading call sites.

## Taiwan Stock Search

`GET /api/v1/stocks/search?q=2330` uses the latest retained official snapshot:

`01_market_data/daily_snapshot/trade_date=YYYY-MM-DD/daily_market_normalized.csv`

The loader automatically selects the newest valid retained snapshot that has
both `daily_market_normalized.csv` and `snapshot_manifest.json`; no trade date is
hard-coded.

Supported query forms:

- `2330`, `2330.TW`, `TWSE:2330`, `台積電`
- `6488`, `6488.TWO`, `TPEX:6488`, `環球晶`
- exact Chinese name and partial Chinese name search

Default results include only TWSE/TPEX common stocks and return:

- `code`
- `symbol`
- `name`
- `market`
- `exchange`
- `security_type`
- `is_common_stock`

`symbol` is the value that can be passed directly to
`GET /api/v1/stocks/{stock_code}/quote`.

The official snapshot currently provides `market`, `code`, and `name`, but does
not provide a dedicated security-type column. Common-stock detection therefore
uses the official TWSE/TPEX market rows first, then a conservative fallback to
exclude non-common-stock products. The fallback excludes ETF, ETN, warrants,
bull/bear products, bonds, convertible bonds, preferred shares, depositary
receipts, beneficiary securities, index products, leveraged/inverse products,
futures-style products, REIT-like products, and other special instruments when
the code or official name indicates that type.

The default API response does not silently fall back to China stock lookup. A
missing Taiwan query returns an empty `items` list. Internal callers may set
`include_excluded=true` to inspect excluded products, but the default analysis
flow only admits TWSE/TPEX common stocks.

## `pct_chg`

`pct_chg` is a percentage-point number, matching the existing
`daily_stock_analysis` `pct_chg` / `change_pct` contract.

Source priority:

1. Existing package percentage fields: `pct_chg`, `change_pct`,
   `changePercent`, `change_pct_value`
2. Latest two `chartSeries` closes:
   `((latest_close - previous_close) / previous_close) * 100`
3. For snapshot fallback, latest close and the previous valid snapshot close:
   `((latest_close - previous_close) / previous_close) * 100`
4. `None` when previous close is missing, zero, or invalid

The upstream snapshot `change` field is a price delta and is not used as
`pct_chg`.

## Quote Contract

`GET /api/v1/stocks/{stock_code}/quote` 對台股回傳正式 snapshot 欄位，並保留
既有欄位向後相容：

- `symbol` / `stock_code`: `2330.TW`、`6488.TWO`
- `code`: 不含 suffix 的代碼
- `name` / `stock_name`: 正式名稱
- `market` / `exchange`: `TWSE` 或 `TPEX`；既有 `market=tw` 欄位仍保留在舊語意
- `trade_date`: retained snapshot 的正式交易日
- `open` / `high` / `low` / `close`
- `previous_close`
- `change`: 價差，不作為 `pct_chg`
- `pct_chg`: 百分點
- `volume_shares`: 股
- `volume_lots`: 張，台股 `1 張 = 1000 股`
- `turnover_amount`: 新台幣成交金額
- `transaction_count`: 成交筆數
- `currency`: `TWD`
- `timezone`: `Asia/Taipei`
- `source`: `TaiwanDailyDataBridgeFetcher`
- `data_status`: `available` 或 `snapshot_only`

正式 snapshot 的 `volume` 欄位經實體資料核對為股數口徑；若來源同時提供
`volume_lots` 才直接沿用，否則 `volume_lots = volume_shares / 1000`。缺少欄位
時回傳 `null`，不以 `0` 冒充正式數字。

## History And Technical

`GET /api/v1/stocks/{stock_code}/history` 對台股的來源順序：

1. `latest_screening_package.json` 的該股票 `chartSeries`
2. 找不到正式多日序列時，只回傳最新 snapshot 並標記 `data_status=snapshot_only`
3. 股票完全不存在時回傳查無資料狀態或 404，由呼叫端依既有 API 語意處理

`snapshot_only` 代表只有最新 retained snapshot，不代表完整多日歷史；API 不會
把單日 snapshot 偽裝成多日 K 線。

`GET /api/v1/stocks/{stock_code}/technical` 讀取 package 中該股票實際存在的
MA5、MA10、MA20、MA60、Bollinger、KD、MACD、RR 與量能欄位。缺少 package、
缺少該股票或缺少單一指標時，回傳 `technical_unavailable` 或 `null`，不使用
其他股票資料，也不以單日 snapshot 重新計算 MA、KD、MACD 或 Bollinger。

## Missing Data

If a Taiwan stock is absent from the package/snapshot, the bridge returns no
result. Explicit `.TW` / `.TWO` requests may continue only to verified Taiwan
fallback sources such as Yahoo Finance. Bare Taiwan common-stock queries and
Taiwan name queries do not fall back to AkShare, Tushare, Pytdx, Baostock,
TickFlow, China stock indexes, capital-flow data, or dragon-tiger-list data.
Damaged package/snapshot files or missing required snapshot columns raise a
provider error so fake market data is not produced.

Snapshot `volume` / `volume_shares` is preserved as shares. Package
`volumeShares` is used when present. API responses additionally expose
`volume_lots` for Taiwan stocks using the formal `1 lot = 1000 shares` rule.

Taiwan bridge failures do not fall back to China market providers. Bare Taiwan
common-stock quote/history requests stop at the Taiwan bridge when no formal
Taiwan data is available.

## Daily Workflow Watchlist Contract

`STOCK_LIST` precedence in `.github/workflows/00-daily-analysis.yml` is:

1. `vars.STOCK_LIST` or `secrets.STOCK_LIST`, exposed internally as
   `STOCK_LIST_CONFIG`
2. an existing runner `STOCK_LIST` environment variable from the optional
   `STOCK_LIST` Environment
3. the minimal Taiwan default `2330.TW`

The expected format is comma-separated symbols, for example
`2330.TW,6488.TWO`. Bare Taiwan codes can work when the official index contains
a unique TWSE/TPEX match, but explicit suffixes are preferred in automation.

## Daily Analysis Output Consumption

每日分析 workflow 會先下載並驗證上游台股正式 artifact，再執行
`python main.py`。個股分析成功後，既有分析流程會把正式分析結果寫入
SQLite `data/stock_analysis.db` 的 `analysis_history` 表；API 的
`/api/v1/history` 與 `/api/v1/history/{id}`、Web 歷史列表與報告詳情都讀取
同一份 `analysis_history` 資料。Portfolio 的持倉分析入口只提交分析任務並
傳入只讀持倉 context，不會把分析建議寫入交易帳本。

`analysis_history` 目前使用既有欄位契約：`code`、`name`、`report_type`、
`sentiment_score`、`operation_advice`、`trend_prediction`、
`analysis_summary`、`raw_result`、`news_content`、`context_snapshot` 與
`created_at`。交易日期與資料品質主要保存在
`context_snapshot.enhanced_context.date`、`market_phase_summary` 與
`analysis_context_pack_overview`；現有正式表結構沒有獨立 `schema_version`
欄位。分析失敗時不寫入 `analysis_history` 假成功記錄。

正式 DB 路徑由 `DATABASE_PATH` 決定。本機預設值是
`./data/stock_analysis.db`，相對路徑固定解析到 repository root，不依賴 API
process 的 current working directory；Docker 預設值是
`/app/data/stock_analysis.db`，compose 透過 `../data:/app/data` 保留同一資料卷。
每日 workflow 上傳與 restore script 的預設目標同樣對齊
`data/stock_analysis.db`。測試可用 temporary DB 覆蓋 `DATABASE_PATH`，但不能把
temporary DB 宣告為正式資料。

API 的 process health 與資料 readiness 分開處理：`/health`、`/api/health` 與
`/api/v1/health` 只代表 API process 存活；`/ready`、`/api/ready` 與
`/api/v1/ready` 會以唯讀 SQLite 連線檢查 DB 是否存在、integrity 是否為
`ok`、`analysis_history` 表與必要欄位是否存在。`analysis_history` 為空時
database readiness 可降級通過，但 history availability 必須明確標示為
unavailable；`/api/v1/history` 會回 HTTP 503 與 `history_unavailable`，不得把空
DB、缺表或 malformed DB 回成成功的空列表。

GitHub Actions runner 的本機 SQLite 會隨 runner 消失，因此每日 workflow 的
`analysis-reports-*` artifact 現在一併保留 `data/stock_analysis.db`、`reports/`
與 `logs/`，讓每日批次的既有正式分析歷史產物可被下載稽核。這不新增第二套
分析格式，也不改 H4 上游 artifact 契約。H4-R1 尚未等到 H4 基準後正式交易日
artifact 前，不宣告遠端每日分析端到端已完成。

若要把已下載或已解壓的每日分析 artifact 還原到新的 API runtime 或部署環境，
使用既有 SQLite 目標路徑，不建立第二套資料庫：

```bash
./.venv/bin/python scripts/restore_analysis_history_db.py <artifact-dir-or-db> --target data/stock_analysis.db
```

未傳 `--target` 時，restore script 也會使用 repository root 下的
`data/stock_analysis.db`。還原入口會先以唯讀 SQLite 連線執行
`PRAGMA integrity_check`，確認
`analysis_history` 表、既有欄位契約與非空歷史資料，通過後才把來源 DB 複製到
目標同目錄暫存檔並以 `os.replace` 原子替換。驗證失敗、DB 損壞、缺表、缺欄位
或空歷史資料時會非零退出，且保留既有目標 DB。這只驗證每日分析 artifact 中的
DSA runtime DB；不修改 Google Drive 正式資料，也不改 H4 上游 artifact 契約。

## Upstream Contract

This bridge is read-only. It does not modify `TW_Stock_Dashboard_Clean`, its L2,
L3, L5, L6, or L7 jobs, Drive layout, dashboard package schema, snapshots, or
published fields.

H4 only adds a minimal GitHub Actions artifact publication step to the existing
upstream L7 workflow after the existing formal gates pass. The artifact contains
only the current official trade date files required by this repository:

- `01_market_data/daily_snapshot/trade_date=YYYY-MM-DD/daily_market_normalized.csv`
- `01_market_data/daily_snapshot/trade_date=YYYY-MM-DD/snapshot_manifest.json`
- `05_packages/trade_date=YYYY-MM-DD/package_manifest.json`
- `06_dashboard_sync/latest_screening_package.json`
