# 台股新聞與 LLM 語境稽核交接

日期：2026-07-01

## 已確認

- 實際新聞搜尋 Service：`src/search_service.py` 的 `SearchService`。
- 實際新聞搜尋 Provider：`SearchService` 依設定使用既有 `BaseSearchProvider` 子類，包含 Anspire、Tavily、Bocha、Brave、SerpAPI、SearXNG 等既有 Provider；本批次未新增 Provider。
- 實際台股單股新聞查詢模板：`{stock_name} {query_stock_code} 台股 最新消息 台灣`。
- 實際台股多維情報查詢模板：
  - 最新消息：`{stock_name} {query_stock_code} 台股 最新消息 重大 事件`
  - 機構分析：`{stock_name} 台股 研究報告 目標價 評等 分析`
  - 風險排查：`{stock_name} 處分 裁罰 違規 訴訟 利空 風險 台股`
  - 公司公告：`{stock_name} {query_stock_code} 公司公告 重大訊息 TWSE TPEx 公開資訊觀測站`
  - 財務資訊：`{stock_name} 財報 月營收 營收 淨利 每股盈餘`
  - 產業分析：`{stock_name} 產業 競爭對手 市占率 產業前景 台灣`
- 實際台股代碼辨識路徑：
  - `.TW`、`.TWO` 先由既有 `src.market_context.detect_market` 辨識為台股。
  - `TWSE:`、`TPEX:` 與四碼裸碼改由既有 `src.data.taiwan_stock_index.resolve_taiwan_stock_symbol` 解析；解析成功才視為台股。
  - 搜尋字串中的台股代碼使用解析後的 Yahoo suffix 代碼，例如 `TWSE:2330` 轉為 `2330.TW`。
- 四碼裸碼防誤判方式：不再用「四碼數字」正規表示式直接判定；年份、驗證碼、金額、日期片段或其他四碼數字若無法被既有台股索引解析，會維持非台股。
- 實際 LLM Prompt 路徑：`src/analyzer.py` 的 `GeminiAnalyzer._format_prompt`。
- 台股幣別語境：台股 prompt 中價格、成交額、市值使用 `新台幣`；非台股仍維持原市場語境。
- 中國市場 fallback 防禦：台股新聞 prompt 明確要求不得把台股新聞失敗改寫成中國市場、A 股、滬深或人民幣語境；台股搜尋查詢不使用上交所、深交所、cninfo、A股或人民幣語境。
- 顯式中國市場查詢：`600519` 等中國市場輸入仍保留上交所、深交所、cninfo 與業績預告等既有中國市場搜尋語境。
- 搜尋摘要財務邊界：台股 prompt 明確要求搜尋摘要中的數字只可視為外部網頁線索，不得當成已驗證財務資料；缺少來源、日期或可驗證內容時必須標為 `unavailable`。

## 本次修改檔案

- `docs/CHANGELOG.md`
- `docs/HANDOFF_TAIWAN_NEWS_LLM_CONTEXT_AUDIT_2026-07-01.md`
- `src/analyzer.py`
- `src/search_service.py`
- `tests/test_analyzer_news_prompt.py`
- `tests/test_search_news_freshness.py`

## 驗證結果

- 直接相關測試：`./.venv/bin/python -m pytest tests/test_search_news_freshness.py tests/test_analyzer_news_prompt.py`
  - 結果：`104 passed, 1 warning, 10 subtests passed`
- 全量 pytest：`./.venv/bin/python -m pytest`
  - 結果：`4066 passed, 3 skipped, 46 warnings, 362 subtests passed`
- 後端 gate：`PATH="/Users/youjunhong/Documents/daily_stock_analysis/.venv/bin:$PATH" ./scripts/ci_gate.sh`
  - 結果：`backend-gate: all checks passed`
  - 備註：直接執行 `./scripts/ci_gate.sh` 時目前 shell 找不到 `python`，腳本在 Python syntax check 停止；補入同一 `.venv/bin` 後完整執行腳本並通過。
- `git diff --check`
  - 結果：通過
- py_compile：
  - 指令：`PYTHONPYCACHEPREFIX=/private/tmp/dsa_pycache ./.venv/bin/python -m py_compile src/search_service.py src/analyzer.py tests/test_search_news_freshness.py tests/test_analyzer_news_prompt.py`
  - 結果：通過
- import smoke：
  - 指令：匯入 `src.search_service`、`src.analyzer`、`tests.test_search_news_freshness`、`tests.test_analyzer_news_prompt`
  - 結果：通過

## Warning 狀態

- 直接相關測試保留既有 Starlette/httpx deprecation warning。
- 全量 pytest 與 `ci_gate.sh` 皆保留既有 warning，包含 Starlette/httpx deprecation、lark/protobuf datetime deprecation、pytest collection warning、benchmark mark warning、SQLAlchemy `Column.copy()` deprecation 與 FastAPI `on_event` deprecation。
- import smoke 時 LiteLLM 在受限網路環境下無法取得遠端 model cost map，回落本地備份；該 warning 未造成匯入失敗。

## 明確限制

- 公開資訊觀測站、月營收與財報目前只作為搜尋查詢語境；本批次未證實存在正式結構化資料接線，因此不得視為正式資料來源。
- 未找到可驗證證據，因此未實作正式公開資訊觀測站資料接線。
- 未找到可驗證證據，因此未實作正式月營收資料來源。
- 未找到可驗證證據，因此未實作正式財報資料接線。
- 未找到可驗證證據，因此未實作新的結構化新聞資料契約。
- 搜尋結果仍只能作為外部新聞或網頁搜尋結果；搜尋摘要不等同已驗證財務事實。
- 本批次未新增資料 Provider、爬蟲或 schema。
