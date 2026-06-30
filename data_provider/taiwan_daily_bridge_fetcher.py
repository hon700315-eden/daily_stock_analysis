# -*- coding: utf-8 -*-
"""Read-only bridge for the external Taiwan daily dashboard data package."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple

import pandas as pd

from .base import BaseFetcher, DataFetchError
from .realtime_types import RealtimeSource, UnifiedRealtimeQuote, safe_float, safe_int

_DEFAULT_SOURCE_ROOT = Path(
    "/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/"
    "我的雲端硬碟/TW_Stock_Data_Drive"
)
_PACKAGE_CANDIDATES = (
    Path("06_dashboard_sync/latest_screening_package.json"),
    Path("dashboard-app/public/dashboard-data/latest_screening_package.json"),
)
_SNAPSHOT_REQUIRED = {"trade_date", "market", "code", "name", "open", "high", "low", "close"}
_SNAPSHOT_ALLOWED_STATUSES = {"retained", "success", "completed", "complete", "ok"}
_PACKAGE_PCT_FIELDS = ("pct_chg", "change_pct", "changePercent", "change_pct_value")
_TECHNICAL_FIELD_ALIASES = {
    "ma5": ("ma5", "MA5"),
    "ma10": ("ma10", "MA10"),
    "ma20": ("ma20", "MA20"),
    "ma60": ("ma60", "MA60"),
    "bollinger_upper": ("bollinger_upper", "bollingerUpper", "bbUpper"),
    "bollinger_middle": ("bollinger_mid", "bollinger_middle", "bollingerMiddle", "bbMid"),
    "bollinger_lower": ("bollinger_lower", "bollingerLower", "bbLower"),
    "kd_k": ("kd_k", "kdK"),
    "kd_d": ("kd_d", "kdD"),
    "macd_dif": ("macd_dif", "macdDif", "macd", "dif"),
    "macd_signal": ("macd_signal", "macdSignal", "macdDea", "dea"),
    "macd_histogram": ("macd_hist", "macdHistogram", "macdHist", "histogram"),
    "rr": ("rr", "RR"),
    "volume_lots": ("volume_lots", "volumeLots", "volume"),
    "volume_shares": ("volume_shares", "volumeShares"),
    "volume_3d_avg": ("volume_3d_avg",),
    "volume_10d_avg": ("volume_10d_avg",),
    "volume_20d_avg": ("volume_20d_avg",),
}


def map_tw_symbol(market: Any, code: Any) -> str:
    """Map explicit TWSE/TPEX market rows to Yahoo suffix symbols.

    The original bridge call sites pass ``(market, code)``. Keep that order
    while also accepting ``(code, market)`` for external smoke checks.
    """
    first = str(market or "").strip().upper()
    second = str(code or "").strip().upper()
    if first in {"TWSE", "TPEX"}:
        market_text, code_text = first, second
    elif second in {"TWSE", "TPEX"}:
        market_text, code_text = second, first
    else:
        market_text, code_text = first, second
    if not code_text:
        raise ValueError("Taiwan stock code is empty")
    if code_text.endswith((".TW", ".TWO")):
        return code_text
    if market_text == "TWSE":
        return f"{code_text}.TW"
    if market_text == "TPEX":
        return f"{code_text}.TWO"
    raise ValueError(f"Unsupported Taiwan market: {market}")


def _base_code(symbol: Any) -> str:
    return str(symbol or "").strip().upper().rsplit(".", 1)[0]


def _is_tw_symbol(symbol: Any) -> bool:
    upper = str(symbol or "").strip().upper()
    return upper.endswith(".TW") or upper.endswith(".TWO")


def _configured_root() -> Path:
    root = os.getenv("TW_STOCK_DATA_ROOT", "").strip()
    return Path(root).expanduser() if root else _DEFAULT_SOURCE_ROOT


def _to_float(value: Any) -> Optional[float]:
    return safe_float(value, default=None)


def _pct_from_closes(latest_close: Any, previous_close: Any) -> Optional[float]:
    latest = _to_float(latest_close)
    previous = _to_float(previous_close)
    if latest is None or previous is None or previous == 0:
        return None
    # Unit is percentage points, matching this repository's pct_chg/change_pct contract.
    return ((latest - previous) / previous) * 100


def _first_present(row: Dict[str, Any], fields: Iterable[str]) -> Any:
    for field in fields:
        if field in row and row.get(field) is not None:
            return row.get(field)
    return None


class TaiwanDailyDataBridgeFetcher(BaseFetcher):
    """Minimal read-only adapter for TW_Stock_Dashboard_Clean package/snapshot files."""

    name = "TaiwanDailyDataBridgeFetcher"
    priority = 3
    allow_empty_daily_data = True

    def __init__(self, data_root: Optional[Path | str] = None) -> None:
        self.data_root = Path(data_root).expanduser() if data_root else _configured_root()

    def is_available_for_request(self, capability: str) -> bool:
        if capability not in {"daily_data", "realtime_quote", "stock_name"}:
            return True
        return self._find_package_path() is not None or self._latest_snapshot_path() is not None

    def get_quote_payload(self, stock_code: str) -> Optional[Dict[str, Any]]:
        record = self._lookup_snapshot_record(stock_code) or self._lookup_package_record(stock_code)
        if record is None:
            return None
        latest = record.get("latest_bar") or record
        close = _to_float(latest.get("close"))
        if close is None:
            return None
        volume_shares = _to_float(latest.get("volumeShares", latest.get("volume_shares")))
        volume_lots = _to_float(latest.get("volumeLots", latest.get("volume_lots")))
        if volume_lots is None and volume_shares is not None:
            volume_lots = volume_shares / 1000
        exchange = record["symbol"].rsplit(".", 1)[-1]
        return {
            "symbol": record["symbol"],
            "code": _base_code(record["symbol"]),
            "name": str(record.get("name") or ""),
            "market": record.get("exchange") or ("TWSE" if exchange == "TW" else "TPEX"),
            "exchange": record.get("exchange") or ("TWSE" if exchange == "TW" else "TPEX"),
            "trade_date": latest.get("date") or latest.get("trade_date") or record.get("trade_date"),
            "open": _to_float(latest.get("open")),
            "high": _to_float(latest.get("high")),
            "low": _to_float(latest.get("low")),
            "close": close,
            "previous_close": _to_float(record.get("previous_close")),
            "change": _to_float(record.get("change")),
            "pct_chg": _to_float(record.get("pct_chg")),
            "volume_shares": volume_shares,
            "volume_lots": volume_lots,
            "turnover_amount": _to_float(latest.get("amount", record.get("amount"))),
            "transaction_count": safe_int(latest.get("transaction_count", latest.get("transactions"))),
            "currency": "TWD",
            "timezone": "Asia/Taipei",
            "source": self.name,
            "data_status": record.get("data_status") or "available",
        }

    def get_history_payload(self, stock_code: str, days: int = 30) -> Optional[Dict[str, Any]]:
        record = self._lookup_package_record(stock_code)
        status = "history_unavailable"
        rows: List[Dict[str, Any]] = []
        if record is not None and len(record.get("history") or []) > 1:
            status = "available"
            rows = record.get("history") or []
        else:
            snapshot = self._lookup_snapshot_record(stock_code)
            if snapshot is None:
                return None
            status = "snapshot_only"
            rows = snapshot.get("history") or []
            record = snapshot

        normalized = self._normalize_history_rows(rows)
        if days > 0:
            normalized = normalized[-days:]
        return {
            "stock_code": record["symbol"],
            "stock_name": record.get("name"),
            "period": "daily",
            "source": self.name if status == "snapshot_only" else "latest_screening_package.chartSeries",
            "data_status": status,
            "data": normalized,
        }

    def get_technical_payload(self, stock_code: str) -> Optional[Dict[str, Any]]:
        record = self._lookup_package_record(stock_code)
        if record is None:
            if self._lookup_snapshot_record(stock_code) is not None:
                quote = self.get_quote_payload(stock_code)
                return {
                    "stock_code": quote["symbol"] if quote else stock_code,
                    "stock_name": quote.get("name") if quote else None,
                    "trade_date": quote.get("trade_date") if quote else None,
                    "source": "latest_screening_package.json",
                    "availability": "technical_unavailable",
                    "indicators": {key: None for key in _TECHNICAL_FIELD_ALIASES},
                }
            return None
        latest = record.get("latest_bar") or {}
        indicators = {
            key: _to_float(_first_present(record.get("technical_source") or latest, aliases))
            for key, aliases in _TECHNICAL_FIELD_ALIASES.items()
        }
        non_volume_keys = [key for key in indicators if not key.startswith("volume_")]
        availability = (
            "available"
            if any(indicators.get(key) is not None for key in non_volume_keys)
            else "technical_unavailable"
        )
        return {
            "stock_code": record["symbol"],
            "stock_name": record.get("name"),
            "trade_date": latest.get("date") or latest.get("trade_date") or record.get("trade_date"),
            "source": "latest_screening_package.json",
            "availability": availability,
            "indicators": indicators,
        }

    def get_stock_name(self, stock_code: str) -> Optional[str]:
        record = self._lookup_record(stock_code)
        if record is None:
            return None
        return str(record.get("name") or "").strip() or None

    def get_realtime_quote(self, stock_code: str) -> Optional[UnifiedRealtimeQuote]:
        payload = self.get_quote_payload(stock_code)
        if payload is None:
            return None
        price = payload.get("close")
        if price is None:
            return None
        return UnifiedRealtimeQuote(
            code=payload["symbol"],
            name=str(payload.get("name") or ""),
            source=RealtimeSource.FALLBACK,
            market="tw",
            currency="TWD",
            data_quality="ok",
            price=price,
            change_pct=payload.get("pct_chg"),
            change_amount=payload.get("change"),
            volume=safe_int(payload.get("volume_shares")),
            amount=payload.get("turnover_amount"),
            open_price=payload.get("open"),
            high=payload.get("high"),
            low=payload.get("low"),
            pre_close=payload.get("previous_close"),
            provider_timestamp=str(payload.get("trade_date") or ""),
        )

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        record = self._lookup_record(stock_code)
        if record is None:
            return pd.DataFrame()
        rows = record.get("history") or []
        if not rows and record.get("latest_bar"):
            rows = [record["latest_bar"]]
        return pd.DataFrame(rows)

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        if df.empty:
            return pd.DataFrame(columns=["date", "open", "high", "low", "close", "volume", "amount", "pct_chg"])
        normalized = pd.DataFrame()
        normalized["date"] = df.get("date", df.get("trade_date"))
        for col in ("open", "high", "low", "close"):
            normalized[col] = df.get(col)
        normalized["volume"] = df.get("volumeShares", df.get("volume_shares", df.get("volume")))
        normalized["amount"] = df.get("amount")
        if "pct_chg" in df.columns:
            normalized["pct_chg"] = df["pct_chg"]
        else:
            closes = pd.to_numeric(df.get("close"), errors="coerce")
            normalized["pct_chg"] = closes.pct_change() * 100
        return normalized

    def _lookup_record(self, stock_code: str) -> Optional[Dict[str, Any]]:
        return self._lookup_package_record(stock_code) or self._lookup_snapshot_record(stock_code)

    def _lookup_package_record(self, stock_code: str) -> Optional[Dict[str, Any]]:
        package_path = self._find_package_path()
        if package_path is not None:
            record = self._lookup_package(stock_code, package_path)
            if record is not None:
                return record
        return None

    def _lookup_snapshot_record(self, stock_code: str) -> Optional[Dict[str, Any]]:
        snapshot_path = self._latest_snapshot_path()
        if snapshot_path is not None:
            return self._lookup_snapshot(stock_code, snapshot_path)
        return None

    def _find_package_path(self) -> Optional[Path]:
        candidates: List[Path] = []
        root = self.data_root
        if root.is_file():
            candidates.append(root)
        candidates.extend(root / candidate for candidate in _PACKAGE_CANDIDATES)
        for path in candidates:
            if path.is_file():
                return path
        return None

    def _latest_snapshot_path(self) -> Optional[Path]:
        root = self.data_root
        snapshot_root = root / "01_market_data/daily_snapshot"
        if not snapshot_root.is_dir():
            return None
        valid: List[Tuple[str, Path]] = []
        for csv_path in snapshot_root.glob("trade_date=*/daily_market_normalized.csv"):
            trade_date = csv_path.parent.name.split("trade_date=", 1)[-1]
            manifest = csv_path.with_name("snapshot_manifest.json")
            if self._is_retained_snapshot(csv_path, manifest):
                valid.append((trade_date, csv_path))
        if not valid:
            return None
        return sorted(valid, key=lambda item: item[0])[-1][1]

    def _is_retained_snapshot(self, csv_path: Path, manifest: Path) -> bool:
        if not manifest.exists() or not csv_path.exists() or csv_path.stat().st_size <= 0:
            return False
        try:
            payload = json.loads(manifest.read_text(encoding="utf-8"))
        except Exception:
            return False
        status = str(payload.get("status") or payload.get("snapshot_status") or payload.get("state") or "").lower()
        return status in _SNAPSHOT_ALLOWED_STATUSES

    def _lookup_package(self, stock_code: str, path: Path) -> Optional[Dict[str, Any]]:
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except Exception as exc:  # noqa: BLE001
            raise DataFetchError(f"{self.name} package unreadable: {path}") from exc
        matches = self._package_matches(payload, stock_code)
        if not matches:
            return None
        if len({item["symbol"] for item in matches}) > 1:
            raise DataFetchError(f"Ambiguous Taiwan stock code: {stock_code}")
        return matches[0]

    def _package_matches(self, payload: Dict[str, Any], stock_code: str) -> List[Dict[str, Any]]:
        base = _base_code(stock_code)
        explicit = str(stock_code or "").strip().upper() if _is_tw_symbol(stock_code) else None
        records: Dict[str, Dict[str, Any]] = {}
        chart_series = payload.get("chartSeries") if isinstance(payload, dict) else {}

        for candidate in self._iter_candidates(payload):
            try:
                symbol = map_tw_symbol(candidate.get("market"), candidate.get("code"))
            except ValueError:
                continue
            if explicit and symbol != explicit:
                continue
            if not explicit and _base_code(symbol) != base:
                continue
            record = self._record_from_candidate(candidate, symbol, chart_series)
            records[symbol] = record

        if isinstance(chart_series, dict):
            for code, series in chart_series.items():
                if not isinstance(series, dict):
                    continue
                try:
                    symbol = map_tw_symbol(series.get("market"), series.get("code", code))
                except ValueError:
                    continue
                if explicit and symbol != explicit:
                    continue
                if not explicit and _base_code(symbol) != base:
                    continue
                records.setdefault(symbol, self._record_from_series(series, symbol))
        return list(records.values())

    def _iter_candidates(self, payload: Dict[str, Any]) -> Iterable[Dict[str, Any]]:
        screening = payload.get("screening_results") if isinstance(payload, dict) else {}
        if not isinstance(screening, dict):
            return []
        rows: List[Dict[str, Any]] = []
        for bucket in screening.values():
            if isinstance(bucket, list):
                rows.extend(item for item in bucket if isinstance(item, dict))
        return rows

    def _record_from_candidate(
        self,
        candidate: Dict[str, Any],
        symbol: str,
        chart_series: Any,
    ) -> Dict[str, Any]:
        history = self._history_from_chart(chart_series, _base_code(symbol))
        latest_bar = history[-1] if history else candidate
        pct_chg, pct_source = self._candidate_pct(candidate, history)
        return {
            "symbol": symbol,
            "name": candidate.get("name") or (latest_bar or {}).get("name"),
            "trade_date": candidate.get("trade_date") or (latest_bar or {}).get("date"),
            "latest_bar": latest_bar,
            "history": history,
            "pct_chg": pct_chg,
            "pct_chg_source": pct_source,
            "change": _to_float(candidate.get("change")),
            "previous_close": history[-2].get("close") if len(history) >= 2 else None,
            "amount": candidate.get("amount"),
            "technical_source": candidate,
            "exchange": candidate.get("market"),
            "data_status": "available" if history else "partial",
        }

    def _record_from_series(self, series: Dict[str, Any], symbol: str) -> Dict[str, Any]:
        history = self._history_from_series(series)
        latest_bar = history[-1] if history else {}
        pct_chg, pct_source = self._candidate_pct(series, history)
        return {
            "symbol": symbol,
            "name": series.get("name") or latest_bar.get("name"),
            "trade_date": latest_bar.get("date") or latest_bar.get("trade_date"),
            "latest_bar": latest_bar,
            "history": history,
            "pct_chg": pct_chg,
            "pct_chg_source": pct_source,
            "change": None,
            "previous_close": history[-2].get("close") if len(history) >= 2 else None,
            "amount": latest_bar.get("amount"),
            "technical_source": latest_bar,
            "exchange": series.get("market"),
            "data_status": "available" if history else "technical_unavailable",
        }

    def _candidate_pct(self, row: Dict[str, Any], history: List[Dict[str, Any]]) -> Tuple[Optional[float], str]:
        for field in _PACKAGE_PCT_FIELDS:
            pct = _to_float(row.get(field))
            if pct is not None:
                return pct, f"package.{field}"
        if len(history) >= 2:
            pct = _pct_from_closes(history[-1].get("close"), history[-2].get("close"))
            return pct, "chartSeries.close" if pct is not None else "missing_previous_close"
        return None, "missing_previous_close"

    def _history_from_chart(self, chart_series: Any, code: str) -> List[Dict[str, Any]]:
        if not isinstance(chart_series, dict):
            return []
        series = chart_series.get(code)
        if not isinstance(series, dict):
            return []
        return self._history_from_series(series)

    def _history_from_series(self, series: Dict[str, Any]) -> List[Dict[str, Any]]:
        data = series.get("data")
        if not isinstance(data, list):
            day = series.get("day")
            data = day.get("data") if isinstance(day, dict) else day
        if not isinstance(data, list):
            return []
        return [item for item in data if isinstance(item, dict)]

    def _lookup_snapshot(self, stock_code: str, path: Path) -> Optional[Dict[str, Any]]:
        try:
            df = pd.read_csv(path, dtype={"code": str}, encoding="utf-8-sig")
        except Exception as exc:  # noqa: BLE001
            raise DataFetchError(f"{self.name} snapshot unreadable: {path}") from exc
        df.columns = [str(col).lstrip("\ufeff") for col in df.columns]
        missing = _SNAPSHOT_REQUIRED - set(df.columns)
        if missing:
            raise DataFetchError(f"{self.name} snapshot missing columns: {', '.join(sorted(missing))}")
        matches = []
        for _, row in df.iterrows():
            try:
                symbol = map_tw_symbol(row.get("market"), row.get("code"))
            except ValueError:
                continue
            if _is_tw_symbol(stock_code):
                if symbol != str(stock_code).strip().upper():
                    continue
            elif _base_code(symbol) != _base_code(stock_code):
                continue
            matches.append((symbol, row.to_dict()))
        if not matches:
            return None
        if len({symbol for symbol, _ in matches}) > 1:
            raise DataFetchError(f"Ambiguous Taiwan stock code: {stock_code}")
        symbol, row = matches[0]
        previous_close = self._previous_snapshot_close(symbol, path)
        pct_chg = _pct_from_closes(row.get("close"), previous_close)
        pct_source = "snapshot.close" if pct_chg is not None else "unavailable_no_previous_close"
        latest = {
            "date": row.get("trade_date"),
            "open": row.get("open"),
            "high": row.get("high"),
            "low": row.get("low"),
            "close": row.get("close"),
            "volumeShares": row.get("volume_shares", row.get("volume")),
            "volumeLots": _to_float(row.get("volume_lots")),
            "amount": row.get("amount", row.get("turnover")),
            "transactions": row.get("transactions", row.get("transaction_count")),
        }
        return {
            "symbol": symbol,
            "name": row.get("name"),
            "trade_date": row.get("trade_date"),
            "latest_bar": latest,
            "history": [latest],
            "pct_chg": pct_chg,
            "pct_chg_source": pct_source,
            "change": _to_float(row.get("change")),
            "previous_close": previous_close,
            "amount": latest.get("amount"),
            "exchange": row.get("market"),
            "data_status": "snapshot_only",
        }

    def _previous_snapshot_close(self, symbol: str, current_path: Path) -> Optional[float]:
        snapshot_root = current_path.parent.parent
        current_trade_date = current_path.parent.name.split("trade_date=", 1)[-1]
        candidates: List[Tuple[str, Path]] = []
        for csv_path in snapshot_root.glob("trade_date=*/daily_market_normalized.csv"):
            trade_date = csv_path.parent.name.split("trade_date=", 1)[-1]
            if trade_date >= current_trade_date:
                continue
            manifest = csv_path.with_name("snapshot_manifest.json")
            if self._is_retained_snapshot(csv_path, manifest):
                candidates.append((trade_date, csv_path))
        for _, csv_path in sorted(candidates, key=lambda item: item[0], reverse=True):
            try:
                df = pd.read_csv(csv_path, dtype={"code": str}, encoding="utf-8-sig")
            except Exception:
                continue
            df.columns = [str(col).lstrip("\ufeff") for col in df.columns]
            if not {"market", "code", "close"}.issubset(df.columns):
                continue
            for _, row in df.iterrows():
                try:
                    previous_symbol = map_tw_symbol(row.get("market"), row.get("code"))
                except ValueError:
                    continue
                if previous_symbol == symbol:
                    return _to_float(row.get("close"))
        return None

    def _normalize_history_rows(self, rows: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        dedup: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            trade_date = str(row.get("date") or row.get("trade_date") or "").strip()
            if not trade_date:
                continue
            item = {
                "date": trade_date,
                "open": _to_float(row.get("open")),
                "high": _to_float(row.get("high")),
                "low": _to_float(row.get("low")),
                "close": _to_float(row.get("close")),
                "volume": _to_float(row.get("volumeShares", row.get("volume_shares", row.get("volume")))),
                "amount": _to_float(row.get("amount")),
                "transaction_count": safe_int(row.get("transaction_count", row.get("transactions"))),
                "ma5": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["ma5"])),
                "ma10": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["ma10"])),
                "ma20": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["ma20"])),
                "ma60": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["ma60"])),
                "bollinger_upper": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["bollinger_upper"])),
                "bollinger_middle": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["bollinger_middle"])),
                "bollinger_lower": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["bollinger_lower"])),
                "kd_k": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["kd_k"])),
                "kd_d": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["kd_d"])),
                "macd_dif": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["macd_dif"])),
                "macd_signal": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["macd_signal"])),
                "macd_histogram": _to_float(_first_present(row, _TECHNICAL_FIELD_ALIASES["macd_histogram"])),
            }
            if all(item.get(field) is not None for field in ("open", "high", "low", "close")):
                dedup[trade_date] = item
        return [dedup[key] for key in sorted(dedup)]
