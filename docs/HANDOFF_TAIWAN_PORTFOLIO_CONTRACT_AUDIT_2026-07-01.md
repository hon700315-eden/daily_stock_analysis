# Taiwan Portfolio 契約稽核交接文件（2026-07-01）

## 已證實事實

### 實際 Portfolio 架構

- 後端服務：`src/services/portfolio_service.py` 負責帳戶、交易、現金流水、公司行動、持倉快照重放、匯率快取與即時行情讀取。
- 資料存取：`src/repositories/portfolio_repo.py` 封裝 Portfolio SQLAlchemy 寫入與查詢。
- API route：`api/v1/endpoints/portfolio.py` 掛載於 `/api/v1/portfolio`，包含 accounts、trades、cash-ledger、corporate-actions、snapshot、positions/{symbol}/analysis、imports/csv、fx/refresh、risk。
- API schema：`api/v1/schemas/portfolio.py` 定義 request / response。
- Web 入口：`apps/dsa-web/src/pages/PortfolioPage.tsx`、`apps/dsa-web/src/api/portfolio.ts`、`apps/dsa-web/src/types/portfolio.ts`、`apps/dsa-web/src/utils/portfolioFormat.ts`。

### 實際資料模型

- `src/storage.py` 中已存在 `PortfolioAccount`、`PortfolioTrade`、`PortfolioCashLedger`、`PortfolioCorporateAction`、`PortfolioPosition`、`PortfolioPositionLot`、`PortfolioDailySnapshot`、`PortfolioFxRate`。
- `PortfolioTrade` 有 `trade_uid`、`dedup_hash`、`trade_date`、`market`、`currency`、`fee`、`tax`。
- `PortfolioTrade` 在同一 account 內有 `trade_uid` 與 `dedup_hash` unique constraint。
- `PortfolioPosition` 與 `PortfolioDailySnapshot` 是快照快取，不是第二套帳本。

### 實際儲存方式

- 使用 SQLAlchemy ORM 與 SQLite 路徑設定，初始化由 `Base.metadata.create_all()` 建表。
- 交易、現金流水與公司行動寫入資料庫；快照讀取時重放事件，並原子更新持倉與每日快照快取。
- 未找到獨立 migration 檔案；目前只找到 `schema_migrations` baseline 記錄表與 create_all 初始化證據。

### 實際成本算法

- `get_portfolio_snapshot()` 預設 `cost_method="fifo"`，允許 `fifo` 與 `avg`。
- FIFO：買入建立 lot，賣出由 `_consume_fifo_lots()` 依先進先出扣除成本。
- AVG：買入累加 `_AvgState.quantity` 與 `total_cost`，賣出由 `_consume_avg_position()` 以移動平均成本扣除。
- 買入成本含 `gross + fee + tax`；賣出已實現損益以 `gross - fee - tax - cost_basis` 計算。
- 清倉後持倉不輸出，但 `realized_pnl` 仍在快照中保留。
- 超賣由 `_validate_sell_quantity()` 與 `_consume_fifo_lots()` / `_consume_avg_position()` 防禦，API 回 `409 portfolio_oversell`。
- 精度以 float 計算，公開快照欄位多數在輸出時 round 到 6 或 8 位。

### 實際行情來源

- Portfolio 今日快照會呼叫 `DataFetcherManager.get_realtime_quote()`；歷史快照使用 `StockDaily` 最近收盤價。
- `data_provider/base.py` 對台股裸 4 碼與 `.TW/.TWO` 先走 `TaiwanDailyDataBridgeFetcher`。
- 台股裸碼查無資料時，`get_daily_data()` 與 `get_realtime_quote()` 皆有「未切換至中國市場資料源」的實作證據。
- 查無價格時，Portfolio 以 `price_source="missing"`、`price_available=false`、`price_stale=true` 表示。

### 實際代碼格式

- Portfolio 儲存前會透過 `PortfolioService._normalize_symbol_for_storage()` 呼叫 `src.data.taiwan_stock_index.resolve_taiwan_stock_symbol()`。
- `2330`、`2330.TW`、`TWSE:2330` 在台股索引命中時會收斂為 `2330.TW`。
- `6488`、`6488.TWO`、`TPEX:6488` 在台股索引命中時會收斂為 `6488.TWO`。
- Web 端 `apps/dsa-web/src/utils/stockCode.ts` 的 `areStockCodesEquivalent()` 會把台股 `.TW/.TWO` 與裸碼折疊成相同 match key，用於避免同標的顯示重複。

### 實際幣別

- API 建立帳戶 schema 預設 `market="tw"`、`base_currency="TWD"`。
- `PortfolioService._default_currency_for_market("tw")` 回傳 `TWD`。
- 全組合彙總幣別讀取 `get_config().default_currency`，專案預設為 `TWD`。
- ORM 欄位仍保留舊 default `cn/CNY`，但 API 與 service 建立路徑已有 `tw/TWD` 預設證據。

### 實際費用與稅務支援

- 交易 request 支援 `fee` 與 `tax` 欄位，預設為 `0.0`。
- 買入時 `fee` 與 `tax` 納入成本；賣出時從 proceeds 扣除。
- 本批次未找到正式台股券商費率、最低手續費、折扣或證交稅稅率設定。
- 未找到可驗證證據，因此未實作。

### 實際股利與公司行動支援

- 已有手動 `cash_dividend` 與 `split_adjustment` 資料模型、API 與 replay 支援。
- 未找到正式股利 reader、除權息資料來源、公司行動 provider、manifest 或端到端資料測試。
- 未找到可驗證證據，因此未實作。

### 實際測試結果

- 既有測試覆蓋 Portfolio service、API、CSV 匯入、風險、FX stale fallback、台股代碼正規化、Web Portfolio 頁面與格式化工具。
- 本批次新增 / 修改測試覆蓋缺行情公開欄位回傳 `null`、既有快取表相容值、API snapshot 契約與前端缺行情顯示。

### 本次修改內容

- 缺行情公開 Portfolio position 欄位 `last_price`、`market_value_base`、`unrealized_pnl_base` 改為 `null`。
- `price_available=false` 的 position `data_quality` 標為 `partial`。
- 既有 `portfolio_positions` 快取表欄位仍以相容 `0.0` 寫入，避免新增 migration 或破壞既有非空欄位。
- Web Portfolio 型別接受 `null`，格式化函式繼續顯示 `--`。
- 已觸及的缺價 UI 標籤改為繁體 `缺價`。

## 盤點裁決表

| 項目 | 實體證據 | 現況 | 是否需要修正 | 允許施工範圍 |
| --- | --- | --- | --- | --- |
| Portfolio service | `src/services/portfolio_service.py` | 事件重放、快照、匯率與行情入口已存在 | 是 | 僅缺行情公開欄位契約 |
| Portfolio API | `api/v1/endpoints/portfolio.py`、`api/v1/schemas/portfolio.py` | route 與 schema 已存在 | 是 | `PortfolioPositionItem` 缺行情欄位改 Optional |
| 儲存模型 | `src/storage.py`、`src/repositories/portfolio_repo.py` | SQLite / SQLAlchemy；事件表加快照快取 | 否 | 不新增 DB、不新增 migration |
| 成本算法 | `_consume_fifo_lots()`、`_consume_avg_position()`、`tests/test_portfolio_service.py` | FIFO 與 AVG 皆存在；預設 FIFO | 否 | 僅記錄，不改帳務語意 |
| 已實現損益 | `_replay_account()` | 賣出 proceeds 扣 fee/tax 後減成本 | 否 | 僅記錄 |
| 台股代碼 | `resolve_taiwan_stock_symbol()`、`test_taiwan_symbols_normalize_for_portfolio_storage` | 共用既有台股索引正規化 | 否 | 不重做 |
| 行情來源 | `DataFetcherManager.get_realtime_quote()`、`TaiwanDailyDataBridgeFetcher` | 台股優先 Taiwan bridge | 否 | 不新增 provider |
| 中國 fallback | `data_provider/base.py` 台股查無即 return / raise | 台股查無不切中國 provider | 否 | 不修改 |
| TWD | schema、service、config | API/service 預設 tw/TWD | 否 | 不新增設定 |
| 手續費／稅 | `PortfolioTrade`、replay 計算 | 欄位存在，費率契約不存在 | 否 | 未找到可驗證證據，因此未實作。 |
| 股利／公司行動 | `PortfolioCorporateAction`、API、replay | 手動事件存在；正式資料源不存在 | 否 | 未找到可驗證證據，因此未實作。 |
| 前端 Portfolio | `PortfolioPage.tsx`、`portfolioFormat.ts` | 缺行情已顯示 `--`，型別未接受 `null` | 是 | 型別與格式化收斂 |

## 待查或不可用事項

- 未找到正式台股券商費率、最低手續費、折扣或證交稅稅率契約，因此未實作。
- 未找到正式股利 reader、除權息資料來源、公司行動 provider、manifest 或端到端資料測試，因此未實作。
- 未找到需要新 Portfolio 資料庫、第二套帳本、新 Repository abstraction 或大型交易引擎的證據，因此未實作。
- 未找到要求把既有預設成本法從 FIFO 改成移動加權平均的已核准契約，因此未實作。
- 未修改 `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean` 或 Google Drive 正式資料。

## 回滾方式

- 回滾本批次 commit 即可恢復缺行情公開欄位為數值 `0.0` 的舊契約。
- 本批次未新增資料表、migration、provider、費率、股利抓取器或公司行動抓取器，無需資料庫清理。
