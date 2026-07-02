# -*- coding: utf-8 -*-
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Optional, Set

from src.config import Config, get_config


REQUIRED_ANALYSIS_HISTORY_COLUMNS: Set[str] = {
    "id",
    "query_id",
    "code",
    "name",
    "report_type",
    "sentiment_score",
    "operation_advice",
    "trend_prediction",
    "analysis_summary",
    "raw_result",
    "news_content",
    "context_snapshot",
    "ideal_buy",
    "secondary_buy",
    "stop_loss",
    "take_profit",
    "created_at",
}


@dataclass(frozen=True)
class DatabaseRuntimeStatus:
    status: str
    database_ready: bool
    history_available: bool
    reason: Optional[str]
    database_path: Path
    history_count: Optional[int] = None


def resolve_database_path(config: Optional[Config] = None) -> Path:
    cfg = config or get_config()
    db_path = Path(cfg.database_path).expanduser()
    if not db_path.is_absolute():
        db_path = Path(__file__).resolve().parents[2] / db_path
    return db_path.resolve()


def inspect_analysis_database(
    *,
    require_history_rows: bool = False,
    config: Optional[Config] = None,
) -> DatabaseRuntimeStatus:
    db_path = resolve_database_path(config)
    if not db_path.is_file():
        return DatabaseRuntimeStatus(
            status="unavailable",
            database_ready=False,
            history_available=False,
            reason="database_missing",
            database_path=db_path,
        )
    if db_path.stat().st_size <= 0:
        return DatabaseRuntimeStatus(
            status="unavailable",
            database_ready=False,
            history_available=False,
            reason="database_empty_file",
            database_path=db_path,
        )

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error:
        return DatabaseRuntimeStatus(
            status="unavailable",
            database_ready=False,
            history_available=False,
            reason="database_open_failed",
            database_path=db_path,
        )

    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            return DatabaseRuntimeStatus(
                status="unavailable",
                database_ready=False,
                history_available=False,
                reason="database_integrity_failed",
                database_path=db_path,
            )

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "analysis_history" not in tables:
            return DatabaseRuntimeStatus(
                status="unavailable",
                database_ready=False,
                history_available=False,
                reason="analysis_history_missing",
                database_path=db_path,
            )

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(analysis_history)").fetchall()
        }
        if not REQUIRED_ANALYSIS_HISTORY_COLUMNS.issubset(columns):
            return DatabaseRuntimeStatus(
                status="unavailable",
                database_ready=False,
                history_available=False,
                reason="analysis_history_schema_invalid",
                database_path=db_path,
            )

        count = int(conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0] or 0)
        if require_history_rows and count <= 0:
            return DatabaseRuntimeStatus(
                status="unavailable",
                database_ready=True,
                history_available=False,
                reason="analysis_history_empty",
                database_path=db_path,
                history_count=count,
            )

        return DatabaseRuntimeStatus(
            status="ok" if count > 0 else "degraded",
            database_ready=True,
            history_available=count > 0,
            reason=None if count > 0 else "analysis_history_empty",
            database_path=db_path,
            history_count=count,
        )
    except sqlite3.Error:
        return DatabaseRuntimeStatus(
            status="unavailable",
            database_ready=False,
            history_available=False,
            reason="database_query_failed",
            database_path=db_path,
        )
    finally:
        conn.close()
