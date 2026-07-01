# 台股日更自動化與測試收斂交接

## 已證實事實

- 起始正式基準：`1b33309e40084482385099af756c6742f3875dfb`。
- 本批次功能分支：`feat/taiwan-daily-automation-test-convergence`。
- 主倉庫起始狀態：本地 `main`、`origin/main`、`refs/heads/main` 均為 `1b33309e40084482385099af756c6742f3875dfb`，工作區乾淨，未偵測到 merge、rebase、cherry-pick 或 conflict 狀態。
- 來源日更專案 `/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean` 起始狀態：已存在本批次外的 modified 與 untracked 檔案，本批次未修改。
- Google Drive 正式資料根目錄：`/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/我的雲端硬碟/TW_Stock_Data_Drive`。
- `TW_STOCK_DATA_ROOT` 環境變數：目前 shell 未設定；主倉庫台股橋接器使用既有預設 Drive 路徑。
- 最新正式資料日期：`2026-07-01`。
- 最新 snapshot manifest：`01_market_data/daily_snapshot/trade_date=2026-07-01/snapshot_manifest.json`，status=`retained`，size=`506` bytes。
- 最新 snapshot CSV：`01_market_data/daily_snapshot/trade_date=2026-07-01/daily_market_normalized.csv`，size=`973130` bytes，row_count=`11347`，包含 `TWSE` 與 `TPEX`。
- 最新 package manifest：`05_packages/trade_date=2026-07-01/package_manifest.json`，status=`locked`，size=`527` bytes。
- 最新 package：`06_dashboard_sync/latest_screening_package.json`，size=`2087328` bytes，metadata.status=`success`，metadata.tradeDate=`2026-07-01`。
- 正式 readback smoke：`scripts/taiwan_daily_readback_smoke.py` 只讀取正式 Drive，不寫入、不抓取、不覆蓋資料。
- 正式 readback smoke 實測 PASS：驗證 `2330.TW` quote、`6488.TWO` quote、多日 history 樣本 `2327.TW`、technical available 樣本 `3036.TW`、snapshot-only 樣本 `2330.TW`、technical unavailable 樣本 `2330.TW`，以及不存在台股裸碼 `9999` 不 fallback 中國市場。

## 現有 Workflow 清單

| workflow | 觸發條件 | schedule 與時區 | manual dispatch | secrets / variables | 實際工作 |
| --- | --- | --- | --- | --- | --- |
| `.github/workflows/00-daily-analysis.yml` | `schedule`、`workflow_dispatch` | `0 10 * * 1-5`，GitHub Actions cron 為 UTC，台北時間 18:00，週一至週五 | 有 | 多組 LLM、搜尋、通知、股票清單與 Longbridge 等 secrets / variables | 執行 `main.py` 股票分析，不是來源日更資料抓取流程 |
| `.github/workflows/auto-tag.yml` | `push` 到 `main` 且 commit message 含 `#patch/#minor/#major` | 無 | 無 | `GITHUB_TOKEN` | 自動 tag，opt-in |
| `.github/workflows/ci.yml` | `pull_request` 到 `main` | 無 | 無 | 無業務 secret | AI governance、`scripts/ci_gate.sh` 分段、Docker build/import smoke、前端變更時 lint/build |
| `.github/workflows/create-release.yml` | `push` tag `v*.*.*` | 無 | 無 | `GITHUB_TOKEN` | 建立 GitHub Release |
| `.github/workflows/desktop-release.yml` | `push` tag、`workflow_dispatch` | 無 | 有 | release 相關 token | 桌面端 release |
| `.github/workflows/docker-publish.yml` | `push` tag、`workflow_dispatch` | 無 | 有 | `GITHUB_TOKEN`、`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN` | 發布 Docker image |
| `.github/workflows/ghcr-dockerhub.yml` | `workflow_dispatch` | 無 | 有 | `GITHUB_TOKEN`、`DOCKERHUB_USERNAME`、`DOCKERHUB_TOKEN` | 手動 Docker 發布 |
| `.github/workflows/network-smoke.yml` | `schedule`、`workflow_dispatch` | `0 2 * * 1-5`，GitHub Actions cron 為 UTC，台北時間 10:00，週一至週五 | 有 | 無 | 執行 network pytest 與 `scripts/test.sh quick --no-notify` |
| `.github/workflows/pr-review.yml` | `pull_request_target`、`workflow_dispatch` | 無 | 有 | `GITHUB_TOKEN`、AI review 相關 secrets / variables | PR 靜態檢查與 AI review |
| `.github/workflows/stale.yml` | `schedule`、`workflow_dispatch` | `0 0 * * *`，GitHub Actions cron 為 UTC，台北時間 08:00，每日 | 有 | `GITHUB_TOKEN` 權限 | 標記/關閉 stale issues 與 PRs |

## 來源日更專案邊界

- 來源日更專案存在 workflow：`/Users/youjunhong/Documents/Codex/TW_Stock_Dashboard_Clean/.github/workflows/daily_quant_pipeline.yml`。
- 來源 workflow 觸發條件：`workflow_dispatch` 與 `schedule`。
- 來源 workflow 排程：`30 9 * * 1-5`，GitHub Actions cron 為 UTC，台北時間 17:30，週一至週五。
- 來源 workflow 使用 `RCLONE_CONFIG_B64` secret 建立暫時 rclone config，解析 Drive remote，執行 `python3 -m scripts.l7_daily_automation_runner --drive-root "$TW_STOCK_DRIVE_ROOT" --drive-remote "$TW_STOCK_RCLONE_REMOTE" --mode staging-write`。
- 來源 L7 runner 會驗證 package metadata status=`success`、package manifest status=`locked`、validation status=`PASS`，並進行 Drive writeback/readback 與 dashboard package commit/push。
- 本批次未修改來源日更專案、未複製來源抓取流程、未在主倉庫新增 TWSE/TPEX crawler。
- 本專案依賴來源既有輸出：`01_market_data/daily_snapshot/trade_date=*/daily_market_normalized.csv`、`snapshot_manifest.json`、`05_packages/trade_date=*/package_manifest.json`、`06_dashboard_sync/latest_screening_package.json`。

## 自動化裁決表

| 項目 | 實體證據 | Runtime 可用 | 是否需修正 | 允許施工 | 本次處理 |
| --- | --- | --- | --- | --- | --- |
| GitHub Actions | `.github/workflows/*.yml` | 是 | 是 | 既有 workflow | 修正 `network-smoke.yml` 不再吞失敗 |
| 排程 | `00-daily-analysis.yml`、`network-smoke.yml`、`stale.yml` | 是 | 僅 network smoke 失敗行為需修正 | 僅已存在排程 | 未新增排程 |
| Drive readback | `TaiwanDailyDataBridgeFetcher`、正式 Drive 檔案 | 是 | 是 | 唯讀驗證 | 新增只讀 smoke |
| API 啟動 | `python main.py --serve-only`、`uvicorn server:app`、`/api/health` | 是 | 否 | 既有入口 | 未新增 readiness API |
| Web build | `apps/dsa-web/package.json` | 是 | 否 | 既有 build | 未修改前端 |
| 後端測試 | `scripts/ci_gate.sh`、pytest | 是 | 是 | 既有測試 | 新增 readback smoke 測試 |
| 前端測試 | `npm test -- --run`、`npm run lint`、`npm run build` | 是 | 否 | 既有測試 | 未修改前端 |
| 無 LLM Key | 既有 LLM 設定與測試 | 是 | 本批次未找到需修正證據 | 降級契約 | 未找到可驗證證據，因此未實作。 |
| 失敗通知 | workflow env 僅有通知渠道設定 | 否 | 否 | 無證據不新增 | 未找到可驗證證據，因此未實作。 |
| 健康檢查 | `docker/Dockerfile` HEALTHCHECK、`/api/health` | 是 | 是 | 最小修復 | 移除固定成功兜底 |

## 本次修改

- 新增 `scripts/taiwan_daily_readback_smoke.py`：只讀驗證正式台股 Drive 資料，缺檔、不可解析、manifest failed/stale、缺 TWSE/TPEX、缺 quote/history/technical 或台股缺碼被誤補資料時皆回非零。
- 新增 `tests/test_taiwan_daily_readback_smoke.py`：覆蓋 PASS、failed manifest、缺 package 時 CLI 非零。
- 修改 `.github/workflows/network-smoke.yml`：移除 network pytest 與 quick smoke 的 `continue-on-error: true`，讓失敗正確中止 job。
- 修改 `docker/Dockerfile`：健康檢查不再以 `python -c "sys.exit(0)"` 固定成功。
- 修改 `docs/CHANGELOG.md`：記錄 readback smoke 與失敗行為修正。

## 不可用或待查

- 遠端 GitHub Actions 是否已啟用、是否近期成功執行：未找到可驗證證據，因此未實作。
- 主倉庫正式每日台股資料抓取 workflow：未找到可驗證證據，因此未實作。
- 主倉庫正式 Drive 寫回設定：未找到可驗證證據，因此未實作。
- 主倉庫失敗通知正式策略：未找到可驗證證據，因此未實作。
- 主倉庫正式 deployment 平台：未找到可驗證證據，因此未實作。
- 主倉庫遠端 secrets 實際值：未找到可驗證證據，因此未實作。
- Google Drive 遠端同步狀態與 rclone remote 真實啟用狀態：未找到可驗證證據，因此未實作。

## 驗證紀錄

- 已執行：`git diff --check`，結果通過。
- 已執行：`.venv/bin/python -m py_compile scripts/taiwan_daily_readback_smoke.py tests/test_taiwan_daily_readback_smoke.py`，結果通過。
- 已執行：核心 import smoke，覆蓋 config、storage、notification、data provider、Taiwan bridge、analyzer、bot、API，結果通過；過程中 LiteLLM 因無網路改用本地 model cost map 備援。
- 已執行：API health smoke，`GET /api/health` 回傳 `200`。
- 已執行：OpenAPI runtime 與 `docs/architecture/api_spec.json` 對齊檢查，結果通過。
- 已執行：`.venv/bin/python -m pytest tests/test_taiwan_daily_readback_smoke.py tests/test_taiwan_daily_bridge_fetcher.py::test_package_missing_stock_returns_clear_none -q`，結果 `4 passed`。
- 已執行：`.venv/bin/python -m pytest tests/test_taiwan_daily_readback_smoke.py -q`，結果 `3 passed`。
- 已執行：`.venv/bin/python scripts/taiwan_daily_readback_smoke.py --max-stale-calendar-days 7`，結果 `PASS`。
- 已執行：`.venv/bin/python -m pytest`，結果 `4073 passed, 3 skipped, 46 warnings, 362 subtests passed`。
- 已執行：`PATH="$PWD/.venv/bin:$PATH" ./scripts/ci_gate.sh`，結果 `backend-gate: all checks passed`。
- 已執行：`npm test -- --run`，結果 `85 passed`、`881 passed | 2 skipped`。
- 已執行：`npm run lint`，結果 `0 errors, 1 warning`；warning 為既有 `SettingsPage.tsx` React Hook dependency 提醒。
- 已執行：`npm run build`，結果通過，產物輸出至 `static/`。
- 已執行：Web build 產物存在性檢查，確認 `static/index.html` 與 `static/assets/*` 存在。
