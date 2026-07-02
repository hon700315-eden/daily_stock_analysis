#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""只讀驗證台股日更正式資料契約。"""

from __future__ import annotations

import argparse
import csv
import json
import os
import sys
from dataclasses import dataclass
from datetime import date, datetime, time
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

_REPO_ROOT = Path(__file__).resolve().parents[1]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from data_provider.base import DataFetcherManager
from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher
from src.core.trading_calendar import get_effective_trading_date


_DEFAULT_DATA_ROOT = Path(
    "/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/"
    "我的雲端硬碟/TW_Stock_Data_Drive"
)
_ALLOWED_SNAPSHOT_STATUS = {"retained", "success", "completed", "complete", "ok"}
_ALLOWED_PACKAGE_STATUS = {"locked", "success", "completed", "complete", "ok"}
_TAIPEI_TZ = ZoneInfo("Asia/Taipei")


@dataclass
class SmokeResult:
    checks: dict[str, Any]
    errors: list[str]

    @property
    def passed(self) -> bool:
        return not self.errors


def _resolve_data_root(value: str | None) -> Path:
    configured = value or os.getenv("TW_STOCK_DATA_ROOT", "").strip()
    return Path(configured).expanduser() if configured else _DEFAULT_DATA_ROOT


def _read_json(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as fh:
        payload = json.load(fh)
    if not isinstance(payload, dict):
        raise ValueError(f"{path} 內容不是 JSON object")
    return payload


def _find_latest_snapshot(root: Path) -> Path | None:
    snapshot_root = root / "01_market_data" / "daily_snapshot"
    candidates: list[tuple[str, Path]] = []
    for csv_path in snapshot_root.glob("trade_date=*/daily_market_normalized.csv"):
        trade_date = csv_path.parent.name.split("trade_date=", 1)[-1]
        candidates.append((trade_date, csv_path))
    if not candidates:
        return None
    return sorted(candidates, key=lambda item: item[0])[-1][1]


def _parse_trade_date(value: str) -> date:
    return datetime.strptime(value, "%Y-%m-%d").date()


def _status_text(payload: dict[str, Any]) -> str:
    return str(
        payload.get("status")
        or payload.get("snapshot_status")
        or payload.get("package_status")
        or payload.get("state")
        or ""
    ).strip().lower()


def _read_snapshot_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        return [{str(k).lstrip("\ufeff"): v for k, v in row.items()} for row in reader]


def _manifest_row_count(payload: dict[str, Any]) -> int | None:
    row_counts = payload.get("row_counts")
    if isinstance(row_counts, dict):
        value = row_counts.get("total")
        try:
            return int(value)
        except (TypeError, ValueError):
            return None
    for key in ("row_count", "rowCount", "total_rows", "totalRows"):
        if key in payload:
            try:
                return int(payload[key])
            except (TypeError, ValueError):
                return None
    return None


def _csv_trade_dates(rows: list[dict[str, str]]) -> set[str]:
    return {str(row.get("trade_date") or row.get("date") or "").strip() for row in rows if row}


def _expected_tw_trade_date(as_of_date: date | None = None) -> date:
    base = as_of_date or datetime.now(_TAIPEI_TZ).date()
    check_time = datetime.combine(base, time(18, 0), tzinfo=_TAIPEI_TZ)
    return get_effective_trading_date("tw", check_time)


def _iter_package_rows(payload: dict[str, Any]) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    screening = payload.get("screening_results")
    if isinstance(screening, dict):
        for bucket in screening.values():
            if isinstance(bucket, list):
                rows.extend(item for item in bucket if isinstance(item, dict))
    return rows


def _chart_series(payload: dict[str, Any]) -> dict[str, Any]:
    series = payload.get("chartSeries")
    return series if isinstance(series, dict) else {}


def _has_technical(row: dict[str, Any]) -> bool:
    keys = ("ma5", "ma10", "ma20", "ma60", "kd_k", "kd_d", "macd", "macd_hist", "macd_signal")
    return any(row.get(key) not in (None, "") for key in keys)


def _validate_quote(fetcher: TaiwanDailyDataBridgeFetcher, symbol: str) -> dict[str, Any]:
    quote = fetcher.get_quote_payload(symbol)
    if quote is None:
        raise AssertionError(f"{symbol} 查無正式行情")
    if quote.get("close") is None:
        raise AssertionError(f"{symbol} 正式行情缺少 close")
    return quote


def run_smoke(
    data_root: Path,
    *,
    max_stale_calendar_days: int,
    strict_official: bool = False,
    as_of_date: date | None = None,
) -> SmokeResult:
    checks: dict[str, Any] = {"data_root": str(data_root)}
    errors: list[str] = []

    snapshot_csv = _find_latest_snapshot(data_root)
    if snapshot_csv is None:
        return SmokeResult(checks, ["找不到 daily_market_normalized.csv"])
    snapshot_manifest_path = snapshot_csv.with_name("snapshot_manifest.json")
    package_path = data_root / "06_dashboard_sync" / "latest_screening_package.json"
    package_manifest_path = data_root / "05_packages" / snapshot_csv.parent.name / "package_manifest.json"
    checks.update(
        {
            "snapshot_csv": str(snapshot_csv),
            "snapshot_manifest": str(snapshot_manifest_path),
            "latest_screening_package": str(package_path),
            "package_manifest": str(package_manifest_path),
        }
    )

    for label, path in (
        ("snapshot_manifest", snapshot_manifest_path),
        ("daily_market_normalized", snapshot_csv),
        ("latest_screening_package", package_path),
        ("package_manifest", package_manifest_path),
    ):
        checks[f"{label}_exists"] = path.is_file()
        checks[f"{label}_size"] = path.stat().st_size if path.is_file() else 0
        if not path.is_file() or checks[f"{label}_size"] <= 0:
            errors.append(f"{label} 缺檔或空檔")

    if errors:
        return SmokeResult(checks, errors)

    try:
        snapshot_manifest = _read_json(snapshot_manifest_path)
        package_manifest = _read_json(package_manifest_path)
        package = _read_json(package_path)
        rows = _read_snapshot_rows(snapshot_csv)
    except Exception as exc:  # noqa: BLE001 - smoke 需轉為明確失敗。
        return SmokeResult(checks, [f"正式資料不可解析：{type(exc).__name__}: {exc}"])

    snapshot_status = _status_text(snapshot_manifest)
    package_status = _status_text(package_manifest)
    package_metadata = package.get("metadata") if isinstance(package.get("metadata"), dict) else {}
    package_metadata_status = str(package_metadata.get("status") or "").strip().lower()
    path_trade_date = snapshot_csv.parent.name.split("trade_date=", 1)[-1]
    package_trade_date = str(package_metadata.get("tradeDate") or package_metadata.get("trade_date") or "")
    snapshot_manifest_trade_date = str(snapshot_manifest.get("trade_date") or "")
    package_manifest_trade_date = str(package_manifest.get("trade_date") or "")
    csv_trade_dates = _csv_trade_dates(rows)
    manifest_row_count = _manifest_row_count(snapshot_manifest)
    trade_date = str(
        snapshot_manifest.get("trade_date")
        or package_manifest.get("trade_date")
        or package_metadata.get("tradeDate")
        or path_trade_date
    )
    checks.update(
        {
            "latest_trade_date": trade_date,
            "path_trade_date": path_trade_date,
            "snapshot_manifest_trade_date": snapshot_manifest_trade_date,
            "package_manifest_trade_date": package_manifest_trade_date,
            "package_metadata_trade_date": package_trade_date,
            "csv_trade_dates": sorted(csv_trade_dates),
            "snapshot_manifest_status": snapshot_status,
            "package_manifest_status": package_status,
            "package_metadata_status": package_metadata_status,
            "snapshot_row_count": len(rows),
            "snapshot_manifest_row_count": manifest_row_count,
        }
    )

    if strict_official and snapshot_status != "retained":
        errors.append(f"snapshot manifest 狀態必須為 retained，實際為：{snapshot_status or 'missing'}")
    elif snapshot_status not in _ALLOWED_SNAPSHOT_STATUS:
        errors.append(f"snapshot manifest 狀態不可用：{snapshot_status or 'missing'}")
    if strict_official and package_status != "locked":
        errors.append(f"package manifest 狀態必須為 locked，實際為：{package_status or 'missing'}")
    elif package_status not in _ALLOWED_PACKAGE_STATUS:
        errors.append(f"package manifest 狀態不可用：{package_status or 'missing'}")
    if strict_official and package_metadata_status != "success":
        errors.append(f"package metadata 狀態必須為 success，實際為：{package_metadata_status or 'missing'}")
    elif package_metadata_status and package_metadata_status not in _ALLOWED_SNAPSHOT_STATUS:
        errors.append(f"package metadata 狀態不可用：{package_metadata_status}")
    if len(rows) <= 0:
        errors.append("snapshot CSV row count 必須大於 0")
    if manifest_row_count is not None and manifest_row_count != len(rows):
        errors.append(f"snapshot CSV row count 與 manifest 不一致：csv={len(rows)} manifest={manifest_row_count}")
    expected_trade_dates = {
        path_trade_date,
        snapshot_manifest_trade_date,
        package_manifest_trade_date,
        package_trade_date,
        *csv_trade_dates,
    }
    if "" in expected_trade_dates:
        errors.append("正式資料 trade_date 欄位缺漏")
    if len(expected_trade_dates - {""}) != 1:
        errors.append(f"正式資料 trade_date 不一致：{sorted(expected_trade_dates)}")

    try:
        parsed_trade_date = _parse_trade_date(trade_date)
    except ValueError:
        errors.append(f"資料日期不是 YYYY-MM-DD：{trade_date}")
        parsed_trade_date = None
    if parsed_trade_date is not None:
        checks["latest_trade_date_weekday"] = parsed_trade_date.weekday()
        expected_tw_date = _expected_tw_trade_date(as_of_date)
        checks["expected_tw_trade_date"] = expected_tw_date.isoformat()
        checks["latest_trade_date_age_calendar_days"] = (expected_tw_date - parsed_trade_date).days
        if parsed_trade_date.weekday() >= 5:
            errors.append(f"資料日期不是週一至週五：{trade_date}")
        if strict_official and parsed_trade_date != expected_tw_date:
            errors.append(f"正式資料日期 stale：latest={trade_date} expected={expected_tw_date.isoformat()}")
        elif (date.today() - parsed_trade_date).days > max_stale_calendar_days:
            errors.append(f"資料日期 stale：{trade_date}")

    markets = {str(row.get("market") or "").strip().upper() for row in rows}
    checks["snapshot_markets"] = sorted(markets)
    if "TWSE" not in markets:
        errors.append("snapshot 缺少 TWSE 資料")
    if "TPEX" not in markets:
        errors.append("snapshot 缺少 TPEX 資料")

    fetcher = TaiwanDailyDataBridgeFetcher(data_root)
    try:
        quote_2330 = _validate_quote(fetcher, "2330.TW")
        quote_6488 = _validate_quote(fetcher, "6488.TWO")
        checks["quote_2330_trade_date"] = quote_2330.get("trade_date")
        checks["quote_6488_trade_date"] = quote_6488.get("trade_date")
    except Exception as exc:  # noqa: BLE001
        errors.append(str(exc))

    package_rows = _iter_package_rows(package)
    technical_row = next((row for row in package_rows if _has_technical(row)), None)
    checks["package_screening_row_count"] = len(package_rows)
    checks["technical_available_symbol"] = None
    if technical_row is None:
        errors.append("latest_screening_package 缺少可用 technical 樣本")
    else:
        symbol = f"{technical_row.get('code')}.{'TW' if technical_row.get('market') == 'TWSE' else 'TWO'}"
        checks["technical_available_symbol"] = symbol
        technical = fetcher.get_technical_payload(symbol)
        if not technical or technical.get("availability") != "available":
            errors.append(f"{symbol} technical 未回 available")

    chart = _chart_series(package)
    history_symbol = None
    for code, series in chart.items():
        data = series.get("data") if isinstance(series, dict) else None
        if isinstance(data, list) and len(data) > 1:
            market = series.get("market")
            history_symbol = f"{series.get('code') or code}.{'TW' if market == 'TWSE' else 'TWO'}"
            break
    checks["multi_day_history_symbol"] = history_symbol
    if history_symbol is None:
        errors.append("latest_screening_package 缺少多日 history 樣本")
    else:
        history = fetcher.get_history_payload(history_symbol)
        if not history or history.get("data_status") != "available":
            errors.append(f"{history_symbol} history 未回 available")

    snapshot_only = fetcher.get_history_payload("2330.TW")
    checks["snapshot_only_symbol"] = "2330.TW"
    checks["snapshot_only_status"] = snapshot_only.get("data_status") if snapshot_only else None
    if not snapshot_only or snapshot_only.get("data_status") != "snapshot_only":
        errors.append("2330.TW 未呈現 snapshot_only 契約")

    unavailable = fetcher.get_technical_payload("2330.TW")
    checks["technical_unavailable_symbol"] = "2330.TW"
    checks["technical_unavailable_status"] = unavailable.get("availability") if unavailable else None
    if not unavailable or unavailable.get("availability") != "technical_unavailable":
        errors.append("2330.TW 未呈現 technical_unavailable 契約")

    manager = DataFetcherManager(fetchers=[fetcher])
    missing_quote = manager.get_realtime_quote("9999", log_final_failure=False)
    checks["missing_tw_code_fallback_to_china"] = bool(missing_quote)
    if missing_quote is not None:
        errors.append("不存在台股裸碼回傳了行情，疑似 fallback 到非正式資料")

    return SmokeResult(checks, errors)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="只讀驗證台股日更正式資料")
    parser.add_argument("--data-root", help="TW_Stock_Data_Drive 根目錄；未提供時讀 TW_STOCK_DATA_ROOT 或既有預設路徑")
    parser.add_argument("--max-stale-calendar-days", type=int, default=7)
    parser.add_argument("--strict-official", action="store_true", help="啟用 workflow artifact 正式資料嚴格契約")
    parser.add_argument("--as-of-date", help="以 YYYY-MM-DD 指定台北日期，供 workflow 與測試驗證 stale")
    args = parser.parse_args(argv)

    result = run_smoke(
        _resolve_data_root(args.data_root),
        max_stale_calendar_days=args.max_stale_calendar_days,
        strict_official=args.strict_official,
        as_of_date=_parse_trade_date(args.as_of_date) if args.as_of_date else None,
    )
    payload = {
        "status": "PASS" if result.passed else "FAIL",
        "checks": result.checks,
        "errors": result.errors,
    }
    print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
    return 0 if result.passed else 1


if __name__ == "__main__":
    sys.exit(main())
