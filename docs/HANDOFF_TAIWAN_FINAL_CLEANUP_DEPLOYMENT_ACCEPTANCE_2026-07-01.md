# 台股最終清理與部署驗收交接

分支：`feat/taiwan-final-cleanup-deployment-acceptance`

起始基準：`68faea8e1d8899056f2c73dc86b63f461ce06e11`

## 已證實事實

- 本機 `main`、`origin/main`、本機 `refs/heads/main` 與遠端 `refs/heads/main` 起始皆為 `68faea8e1d8899056f2c73dc86b63f461ce06e11`。
- 主倉庫起始工作區乾淨，未找到進行中的 merge、rebase、cherry-pick 或衝突狀態。
- `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean` 本批次未修改。
- Google Drive 正式資料本批次僅透過既有 readback smoke 與 API runtime 唯讀讀取，未修改。
- 中國語境搜尋命中 `319` 個檔案、`2826` 處文字命中；多數屬於顯式中國市場、既有多市場 Provider、測試、歷史文件、設定 registry 或相容欄位，無完整刪除證據。
- 正式資料根目錄：`/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`。
- 最新交易日：`2026-07-01`。
- snapshot manifest：`retained`。
- package manifest：`locked`。
- package metadata：`success`。

## 中國殘留裁決表

| 檔案／模組 | 中國語境 | 台股路徑是否使用 | 其他市場是否使用 | 裁決 |
| --- | --- | --- | --- | --- |
| `data_provider/*_fetcher.py`、`data_provider/base.py` | AkShare、Tushare、Baostock、Sina、EastMoney、A 股資料源 | 台股 bridge 先行；缺碼未切中國 provider | 是 | 保留 |
| `src/market_context.py`、`src/core/market_review.py`、`src/core/trading_calendar.py` | 顯式 `cn` 市場、A 股 prompt 與交易日曆 | 台股有 `tw`、`TWD`、`Asia/Taipei` 語境 | 是 | 保留 |
| `src/storage.py` 舊 ORM default | 舊資料欄位 default `cn` | API 與 service 建立路徑已有 `tw/TWD` 預設 | 是 | 保留，缺少安全 migration 證據 |
| `apps/dsa-web/src/components/alerts/AlertRuleForm.tsx` | 大盤紅綠燈告警選項 `cn/hk/us` | 台股正式大盤告警未支援 | 是 | 保留，標示不可用 |
| `docker/Dockerfile` | `TZ=Asia/Shanghai` | 是，容器預設時區 | 否 | 修正為 `Asia/Taipei` |
| `docker/docker-compose.yml` | `TZ=Asia/Shanghai` | 是，Compose runtime 預設時區 | 否 | 修正為 `Asia/Taipei` |
| `.github/workflows/00-daily-analysis.yml` | `MARKET_REVIEW_REGION=cn`、`green_up`、上海時間顯示 | 是，每日分析預設 | 否 | 修正為 `tw`、`red_up`、`Asia/Taipei` |
| `docs/*` 舊歷史與既有說明 | 多市場、歷史版本或既有中國市場描述 | 不作 runtime | 是 | 保留 |

## 保留模組與原因

- 顯式中國市場功能、Provider、測試與文件仍有 `cn`、A 股、Tushare、AkShare、Baostock 等使用證據；移除會破壞既有 CN/HK/US/JP/KR 或多市場相容路徑。
- `apps/dsa-web` 告警大盤紅綠燈目前後端只允許 `cn/hk/us`；未找到台股 Market Light alert runtime 支援證據，因此未把前端硬改成台股。
- `NOTIFICATION_TIMEZONE=Asia/Shanghai` 僅作通知時區範例，不是正式台股預設；未找到會覆蓋 `DEFAULT_TIMEZONE=Asia/Taipei` 的證據，因此未修改。

## 修正模組與原因

- `docker/Dockerfile`：容器預設時區改為 `Asia/Taipei`。
- `docker/docker-compose.yml`：Compose runtime `TZ` 改為 `Asia/Taipei`。
- `.github/workflows/00-daily-analysis.yml`：每日分析預設市場改為 `tw`，配色改為 `red_up`，顯示時間改為台北時區。
- `docs/CHANGELOG.md`：補本批次修正與交接文件紀錄。

## 刪除模組與證據

- 未找到可驗證證據，因此未實作。

## 台股主流程驗收

- 搜尋 PASS：`2330`、`2330.TW`、`TWSE:2330`、`台積電` 均回 `2330.TW/TWSE/台積電` 且各 1 筆。
- 搜尋 PASS：`6488`、`6488.TWO`、`TPEX:6488`、`環球晶` 均回 `6488.TWO/TPEX/環球晶` 且各 1 筆。
- Quote PASS：`2330` 與 `6488` 皆由 `TaiwanDailyDataBridgeFetcher` 回傳 `TWD`、`Asia/Taipei`、`snapshot_only`；不存在台股 `9999` 回 404，未 fallback 中國市場。
- History PASS：`2327.TW` 回 `latest_screening_package.chartSeries`、`available`、30 筆；`2330.TW` 回 `snapshot_only`、1 筆；`9999` 回 `not_found`、0 筆。
- Technical PASS：`3036.TW` 為 `available`；`2330.TW` 為 `technical_unavailable`，缺值維持 `null`。
- Portfolio PASS：既有 API schema 預設 `market=tw`、`base_currency=TWD`；先前交接與測試證明裸碼與 `.TW/.TWO` 會正規化且缺價維持 `null`。
- 新聞與 LLM PASS：既有稽核證明台股新聞查詢使用台灣語境，台股 prompt 禁止改寫成 A 股、滬深或人民幣語境，無 LLM Key 回傳 unavailable 錯誤而非假報告。
- 籌碼 PASS：`DataFetcherManager.get_chip_distribution("6488.TWO")` 回 `None`。
- 基本面 PASS：既有稽核證明台股 `get_fundamental_context("2330.TW", budget_seconds=0)` 為 `market=tw`、`status=not_supported`，未進入中國 AkShare adapter。

## API 驗收

- `/api/health` PASS：HTTP 200。
- `/openapi.json` PASS：HTTP 200。
- OpenAPI static spec 對齊：API runtime smoke 通過，`/api/health` 與 `/openapi.json` 皆回傳 HTTP 200。
- API app import smoke PASS：`api.app.create_app()` 可建立 TestClient。

## Web 驗收

- 前端 API base URL：由既有 Web 設定與建置流程驗證。
- 台股預設市場：Portfolio 頁面與後端 schema 已使用 `TWD/tw`；大盤紅綠燈告警不支援台股，未找到可驗證證據，因此未實作。
- `npm test -- --run`：85 個測試檔通過，881 passed、2 skipped。
- `npm run lint`：通過，0 errors、1 warning。
- `npm run build`：通過，Vite build 成功。

## Docker 驗收

- Dockerfile 可建置：本機找不到 `docker` CLI，未找到可驗證證據，因此未實作。
- health check 不是固定成功：`curl -f http://localhost:8000/api/health || curl -f http://localhost:8000/health || exit 1`。
- container 啟動入口：`/usr/local/bin/docker-entrypoint.sh`，預設 `python main.py --schedule`，server 服務以 `python main.py --serve-only --host 0.0.0.0 --port ${API_PORT:-8000}`。
- 環境變數：本批次修正 `TZ=Asia/Taipei`，保留 `WEBUI_HOST=0.0.0.0`、`API_PORT=8000`。
- 正式資料掛載為唯讀：未找到可驗證證據，因此未實作。

## workflow 驗收

- CI 鏈：`.github/workflows/ci.yml` 包含 `ai-governance`、`backend-gate`、`docker-build`、`web-gate`。
- network-smoke 失敗中止：既有 changelog 記錄已修正 network smoke 與 Docker health check 吞失敗問題；本批次未重建該工作流。
- 每日 workflow 預設修正為 `MARKET_REVIEW_REGION=tw`、`MARKET_REVIEW_COLOR_SCHEME=red_up`、台北時間顯示。
- 遠端是否啟用與近期是否成功：未找到可驗證證據，因此未實作。

## 正式部署證據

- 雲端主機：未找到可驗證證據，因此未實作。
- Render：未找到可驗證證據，因此未實作。
- Railway：未找到可驗證證據，因此未實作。
- Fly.io：未找到可驗證證據，因此未實作。
- Vercel：未找到可驗證證據，因此未實作。
- Netlify：未找到可驗證證據，因此未實作。
- Docker host：未找到可驗證證據，因此未實作。
- Kubernetes：未找到可驗證證據，因此未實作。

## 正式驗收清單

| 項目 | 結果 | 證據 |
| --- | --- | --- |
| 台股搜尋 | PASS | TestClient 搜尋 8 組查詢 |
| Quote | PASS | `2330`、`6488`、`9999` |
| History | PASS | `2327.TW`、`2330.TW`、`9999` |
| Technical | PASS | `3036.TW`、`2330.TW` |
| Portfolio | PASS | schema 與既有交接測試證據 |
| 新聞 | PASS | 既有新聞與 prompt 稽核 |
| LLM 報告 | PASS | 無 Key 不產生假報告；prompt 防中國語境 |
| 籌碼 unavailable 防禦 | PASS | `6488.TWO` 回 `None` |
| 基本面 unavailable 防禦 | PASS | 既有 runtime smoke 為 `not_supported` |
| API schema | PASS | schema 預設 `tw/TWD` |
| 台股預設設定 | PASS | `tw`、`zh-TW`、`TWD`、`Asia/Taipei`、`red_up` |
| 無中國 fallback | PASS | 缺碼 quote/history 與 readback smoke |
| 正式資料 readback | PASS | `scripts/taiwan_daily_readback_smoke.py` |
| API health | PASS | HTTP 200 |
| OpenAPI | PASS | HTTP 200 |
| Web test | PASS | `npm test -- --run` 通過，85 個測試檔、881 passed、2 skipped |
| Web lint | PASS | `npm run lint` 通過，0 errors、1 warning |
| Web build | PASS | `npm run build` 通過，Vite build 成功 |
| Docker health check | UNAVAILABLE | 本機找不到 `docker` CLI，未找到可驗證證據，因此未實作。 |
| GitHub Actions 本地靜態驗證 | PASS | workflow YAML parse 通過 |
| 遠端 GitHub Actions 狀態 | UNAVAILABLE | 未找到可驗證證據，因此未實作。 |
| 正式部署平台 | UNAVAILABLE | 未找到可驗證證據，因此未實作。 |
| Google Drive 唯讀 | PASS | readback smoke 與 API runtime 無寫入 |
| 工作區乾淨 | 待補 | commit 後確認 |
| 三方 Git HEAD 一致 | 待補 | push 與 main fast-forward 後確認 |

## 不可用或未驗證

- 遠端 workflow 啟用與近期成功狀態：未找到可驗證證據，因此未實作。
- 正式部署平台：未找到可驗證證據，因此未實作。
- 遠端 secrets：未找到可驗證證據，因此未實作。
- 無法執行的 Docker build：`docker` CLI 不存在，未找到可驗證證據，因此未實作。
- 法人、融資融券、月營收、財報與公司事件正式資料：未找到可驗證證據，因此未實作。

## 測試結果

- `PATH="$PWD/.venv/bin:$PATH" ./.venv/bin/python scripts/taiwan_daily_readback_smoke.py`：PASS。
- API TestClient smoke：PASS。
- `./.venv/bin/python -m pytest`：4073 passed、3 skipped、46 warnings、362 subtests passed。
- `PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh`：PASS；gate 內離線 pytest 為 4073 passed、1 skipped、2 deselected、46 warnings、362 subtests passed。
- `npm test -- --run`：85 個測試檔，881 passed、2 skipped。
- `npm run lint`：PASS，0 errors、1 warning。
- `npm run build`：PASS，Vite build 成功。
- `git diff --check`：PASS。
- workflow YAML parse：PASS。
- API runtime smoke：`/api/health` HTTP 200、`/openapi.json` HTTP 200。
- 核心 import smoke：PASS。

## warnings

- LiteLLM 在受限網路環境無法抓遠端 model cost map，已 fallback local backup；未造成 API import 或 smoke 失敗。
- 大盤紅綠燈告警尚未支援台股，未找到可驗證證據，因此未實作。
- 正式資料掛載為唯讀的 Docker 部署證據不足，未找到可驗證證據，因此未實作。

## 本次修改

- 修正 Docker 與 Compose 預設時區。
- 修正每日分析 workflow 台股預設市場、紅漲綠跌配色與台北時間顯示。
- 更新 changelog。
- 新增本交接文件。
