# -*- coding: utf-8 -*-
"""Taiwan stock index built from the retained daily snapshot."""

from __future__ import annotations

import csv
import logging
import os
from dataclasses import dataclass
from pathlib import Path
from threading import RLock
from typing import Iterable, Optional

from data_provider.taiwan_daily_bridge_fetcher import map_tw_symbol

logger = logging.getLogger(__name__)

_DEFAULT_DRIVE_ROOT = Path(
    "/Users/youjunhong/Library/CloudStorage/GoogleDrive-hon700315@gmail.com/"
    "我的雲端硬碟/TW_Stock_Data_Drive"
)
_SNAPSHOT_RELATIVE_ROOT = Path("01_market_data/daily_snapshot")
_SNAPSHOT_FILENAME = "daily_market_normalized.csv"
_SNAPSHOT_REQUIRED_COLUMNS = {"trade_date", "market", "code", "name"}
_SUPPORTED_EXCHANGES = {"TWSE", "TPEX"}
_CACHE_LOCK = RLock()
_INDEX_CACHE: tuple[Path, float, int, tuple["TaiwanStockRecord", ...]] | None = None

_EXCLUDE_NAME_KEYWORDS = (
    "ETF",
    "ETN",
    "權證",
    "認購",
    "認售",
    "債",
    "公司債",
    "特別股",
    "受益證券",
    "指數投資證券",
    "存託憑證",
    "-DR",
    "KY-DR",
    "DR",
    "REIT",
)
_ETF_NAME_HINTS = (
    "台灣50",
    "高股息",
    "富邦台50",
    "元大",
    "國泰",
    "群益",
    "復華",
    "凱基",
    "永豐",
    "中信",
    "兆豐",
    "第一金",
    "街口",
)


@dataclass(frozen=True)
class TaiwanStockRecord:
    code: str
    symbol: str
    name: str
    market: str
    exchange: str
    security_type: str
    is_common_stock: bool
    trade_date: str
    source_path: str


def get_taiwan_stock_data_root() -> Path:
    """Return the Taiwan stock data root used for the official snapshot index."""
    configured = (
        os.getenv("TW_STOCK_INDEX_ROOT", "").strip()
        or os.getenv("TW_STOCK_DATA_ROOT", "").strip()
    )
    return Path(configured).expanduser() if configured else _DEFAULT_DRIVE_ROOT


def find_latest_taiwan_snapshot_path(root: Optional[Path | str] = None) -> Path | None:
    """Find the newest retained daily snapshot with a manifest and non-empty CSV."""
    data_root = Path(root).expanduser() if root is not None else get_taiwan_stock_data_root()
    snapshot_root = data_root / _SNAPSHOT_RELATIVE_ROOT
    if not snapshot_root.is_dir():
        return None

    valid: list[tuple[str, Path]] = []
    for csv_path in snapshot_root.glob(f"trade_date=*/{_SNAPSHOT_FILENAME}"):
        trade_date = csv_path.parent.name.split("trade_date=", 1)[-1]
        manifest = csv_path.with_name("snapshot_manifest.json")
        try:
            if manifest.exists() and csv_path.stat().st_size > 0:
                valid.append((trade_date, csv_path))
        except OSError:
            continue
    if not valid:
        return None
    return sorted(valid, key=lambda item: item[0])[-1][1]


def _normalize_query_text(value: str) -> str:
    return str(value or "").strip().upper()


def _is_tw_symbol(value: str) -> bool:
    upper = _normalize_query_text(value)
    return upper.endswith(".TW") or upper.endswith(".TWO")


def _parse_explicit_symbol(value: str) -> tuple[str, str] | None:
    upper = _normalize_query_text(value)
    if upper.count(".") != 1:
        return None
    base, suffix = upper.rsplit(".", 1)
    if suffix not in {"TW", "TWO"}:
        return None
    if not (base.isdigit() and 4 <= len(base) <= 6):
        return None
    market = "TWSE" if suffix == "TW" else "TPEX"
    return market, base


def _parse_prefixed_code(value: str) -> tuple[str, str] | None:
    upper = _normalize_query_text(value)
    if ":" not in upper:
        return None
    prefix, code = upper.split(":", 1)
    prefix = prefix.strip()
    code = code.strip()
    if prefix not in _SUPPORTED_EXCHANGES:
        return None
    if not (code.isdigit() and 4 <= len(code) <= 6):
        return None
    return prefix, code


def _classify_security(code: str, name: str) -> tuple[str, bool]:
    code_upper = _normalize_query_text(code)
    name_upper = _normalize_query_text(name)

    if code_upper.isdigit() and code_upper.startswith("00"):
        return "etf", False

    if not code_upper.isdigit() or len(code_upper) != 4:
        if "債" in name_upper or "公司債" in name_upper:
            return "bond", False
        if code_upper.startswith("02") or name_upper.endswith("N"):
            return "etn", False
        if code_upper.startswith("00"):
            return "etf", False
        if code_upper.endswith(("A", "B", "C")) or "特別股" in name_upper:
            return "preferred_stock", False
        return "special_instrument", False

    if "-DR" in name_upper or name_upper.endswith("DR"):
        return "depositary_receipt", False

    for keyword in _EXCLUDE_NAME_KEYWORDS:
        if keyword and keyword in name_upper:
            if keyword == "特別股":
                return "preferred_stock", False
            if keyword in {"ETF"} or any(hint in name_upper for hint in _ETF_NAME_HINTS):
                return "etf", False
            if keyword == "ETN":
                return "etn", False
            if keyword in {"債", "公司債"}:
                return "bond", False
            if keyword in {"-DR", "KY-DR", "DR", "存託憑證"}:
                return "depositary_receipt", False
            return "special_instrument", False

    return "common_stock", True


def _record_from_row(row: dict[str, str], source_path: Path) -> TaiwanStockRecord | None:
    market = _normalize_query_text(row.get("market", ""))
    if market not in _SUPPORTED_EXCHANGES:
        return None
    code = str(row.get("code") or "").strip().upper()
    name = str(row.get("name") or "").strip()
    if not code or not name:
        return None
    try:
        symbol = map_tw_symbol(market, code)
    except ValueError:
        return None
    security_type, is_common_stock = _classify_security(code, name)
    return TaiwanStockRecord(
        code=code,
        symbol=symbol,
        name=name,
        market="tw",
        exchange=market,
        security_type=security_type,
        is_common_stock=is_common_stock,
        trade_date=str(row.get("trade_date") or "").strip(),
        source_path=str(source_path),
    )


def _load_snapshot_records(snapshot_path: Path) -> tuple[TaiwanStockRecord, ...]:
    with snapshot_path.open("r", encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh)
        columns = {str(col or "").lstrip("\ufeff") for col in (reader.fieldnames or [])}
        missing = _SNAPSHOT_REQUIRED_COLUMNS - columns
        if missing:
            raise ValueError(f"Taiwan snapshot missing columns: {', '.join(sorted(missing))}")
        records = [
            record
            for row in reader
            if (record := _record_from_row(row, snapshot_path)) is not None
        ]
    return tuple(records)


def get_taiwan_stock_index(snapshot_path: Optional[Path | str] = None) -> tuple[TaiwanStockRecord, ...]:
    """Load and cache Taiwan stock records from the latest official snapshot."""
    global _INDEX_CACHE

    selected_path = (
        Path(snapshot_path).expanduser()
        if snapshot_path is not None
        else find_latest_taiwan_snapshot_path()
    )
    if selected_path is None:
        return ()

    try:
        stat_result = selected_path.stat()
    except OSError as exc:
        logger.debug("[台股索引] 讀取 snapshot metadata 失敗 %s: %s", selected_path, exc)
        return ()

    signature = (selected_path, stat_result.st_mtime, stat_result.st_size)
    cached = _INDEX_CACHE
    if cached is not None and cached[:3] == signature:
        return cached[3]

    with _CACHE_LOCK:
        cached = _INDEX_CACHE
        if cached is not None and cached[:3] == signature:
            return cached[3]
        try:
            records = _load_snapshot_records(selected_path)
        except (OSError, ValueError) as exc:
            logger.warning("[台股索引] 載入正式 snapshot 失敗 %s: %s", selected_path, exc)
            records = ()
        _INDEX_CACHE = (*signature, records)
        return records


def _candidate_records(include_excluded: bool) -> Iterable[TaiwanStockRecord]:
    for record in get_taiwan_stock_index():
        if include_excluded or record.is_common_stock:
            yield record


def _match_score(query: str, record: TaiwanStockRecord) -> int:
    q = query.strip()
    upper = _normalize_query_text(q)
    name_upper = _normalize_query_text(record.name)
    symbol_upper = record.symbol.upper()
    code_upper = record.code.upper()

    prefixed = _parse_prefixed_code(q)
    if prefixed is not None:
        exchange, code = prefixed
        return 100 if record.exchange == exchange and record.code == code else 0

    explicit = _parse_explicit_symbol(q)
    if explicit is not None:
        exchange, code = explicit
        return 100 if record.exchange == exchange and record.code == code else 0
    if _is_tw_symbol(q):
        return 0

    if upper == symbol_upper:
        return 100
    if upper == code_upper:
        return 99
    if upper == name_upper:
        return 98
    if name_upper.startswith(upper):
        return 80
    if upper in name_upper:
        return 60
    return 0


def search_taiwan_stocks(
    query: str,
    *,
    limit: int = 20,
    include_excluded: bool = False,
) -> list[TaiwanStockRecord]:
    """Search Taiwan stocks by code, suffix symbol, exchange-prefixed code, or Chinese name."""
    text = str(query or "").strip()
    if not text:
        return []

    matched: list[tuple[int, int, TaiwanStockRecord]] = []
    for index, record in enumerate(_candidate_records(include_excluded)):
        score = _match_score(text, record)
        if score <= 0:
            continue
        matched.append((score, index, record))

    matched.sort(key=lambda item: (-item[0], item[1]))
    return [record for _score, _index, record in matched[: max(1, limit)]]


def resolve_taiwan_stock_symbol(query: str, *, include_excluded: bool = False) -> str | None:
    """Resolve an exact Taiwan stock code/name input to the canonical Yahoo suffix symbol."""
    text = str(query or "").strip()
    if not text:
        return None

    records = search_taiwan_stocks(text, limit=2, include_excluded=include_excluded)
    if not records:
        return None
    first_score = _match_score(text, records[0])
    if first_score < 98:
        return None
    if len(records) > 1 and _match_score(text, records[1]) == first_score:
        return None
    return records[0].symbol


def clear_taiwan_stock_index_cache() -> None:
    global _INDEX_CACHE
    with _CACHE_LOCK:
        _INDEX_CACHE = None


def _clear_taiwan_stock_index_cache_for_tests() -> None:
    clear_taiwan_stock_index_cache()
