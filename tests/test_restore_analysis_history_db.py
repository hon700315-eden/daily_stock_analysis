# -*- coding: utf-8 -*-
from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest

from scripts.restore_analysis_history_db import (
    RestoreError,
    resolve_source_db,
    restore_database,
    validate_analysis_history_db,
)


REQUIRED_COLUMNS_SQL = """
CREATE TABLE analysis_history (
    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
    query_id VARCHAR(64),
    code VARCHAR(10) NOT NULL,
    name VARCHAR(50),
    report_type VARCHAR(16),
    sentiment_score INTEGER,
    operation_advice VARCHAR(20),
    trend_prediction VARCHAR(50),
    analysis_summary TEXT,
    raw_result TEXT,
    news_content TEXT,
    context_snapshot TEXT,
    ideal_buy FLOAT,
    secondary_buy FLOAT,
    stop_loss FLOAT,
    take_profit FLOAT,
    created_at DATETIME
)
"""


def _make_db(path: Path, *, rows: int = 1, missing_column: bool = False) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        if missing_column:
            conn.execute(
                """
                CREATE TABLE analysis_history (
                    id INTEGER NOT NULL PRIMARY KEY AUTOINCREMENT,
                    code VARCHAR(10) NOT NULL
                )
                """
            )
        else:
            conn.execute(REQUIRED_COLUMNS_SQL)
            conn.execute("CREATE INDEX ix_analysis_code_time ON analysis_history (code, created_at)")
            for index in range(rows):
                conn.execute(
                    """
                    INSERT INTO analysis_history (
                        query_id, code, name, report_type, sentiment_score,
                        operation_advice, trend_prediction, analysis_summary,
                        raw_result, news_content, context_snapshot, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        f"query-{index}",
                        "2330.TW",
                        "台積電",
                        "simple",
                        80,
                        "持有",
                        "震盪",
                        "測試歷史",
                        "{}",
                        None,
                        '{"enhanced_context":{"date":"2026-07-01"}}',
                        "2026-07-01 10:00:00",
                    ),
                )
        conn.commit()
    finally:
        conn.close()


def _row_count(path: Path) -> int:
    conn = sqlite3.connect(path)
    try:
        return int(conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0])
    finally:
        conn.close()


def test_validate_analysis_history_db_有效_db_通過(tmp_path: Path) -> None:
    db = tmp_path / "stock_analysis.db"
    _make_db(db)

    validate_analysis_history_db(db)


def test_validate_analysis_history_db_corrupt_失敗(tmp_path: Path) -> None:
    db = tmp_path / "stock_analysis.db"
    db.write_bytes(b"not sqlite")

    with pytest.raises(RestoreError, match="SQLite DB 驗證失敗|SQLite integrity_check 失敗"):
        validate_analysis_history_db(db)


def test_validate_analysis_history_db_缺表_失敗(tmp_path: Path) -> None:
    db = tmp_path / "stock_analysis.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE other_table (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()

    with pytest.raises(RestoreError, match="缺少 analysis_history 表"):
        validate_analysis_history_db(db)


def test_validate_analysis_history_db_空歷史_失敗(tmp_path: Path) -> None:
    db = tmp_path / "stock_analysis.db"
    _make_db(db, rows=0)

    with pytest.raises(RestoreError, match="沒有任何歷史資料"):
        validate_analysis_history_db(db)


def test_validate_analysis_history_db_缺欄位_失敗(tmp_path: Path) -> None:
    db = tmp_path / "stock_analysis.db"
    _make_db(db, missing_column=True)

    with pytest.raises(RestoreError, match="schema 缺少必要欄位"):
        validate_analysis_history_db(db)


def test_resolve_source_db_可從_artifact_data_目錄定位(tmp_path: Path) -> None:
    source = tmp_path / "artifact"
    db = source / "data" / "stock_analysis.db"
    _make_db(db)

    assert resolve_source_db(source) == db


def test_restore_database_原子替換有效_db(tmp_path: Path) -> None:
    source = tmp_path / "artifact" / "data" / "stock_analysis.db"
    target = tmp_path / "runtime" / "data" / "stock_analysis.db"
    _make_db(source, rows=2)
    _make_db(target, rows=1)

    restored = restore_database(source.parent.parent, target)

    assert restored == target.resolve()
    assert _row_count(target) == 2


def test_restore_database_來源失敗時保留既有_db(tmp_path: Path) -> None:
    source = tmp_path / "artifact" / "data" / "stock_analysis.db"
    target = tmp_path / "runtime" / "data" / "stock_analysis.db"
    _make_db(source, rows=0)
    _make_db(target, rows=1)

    with pytest.raises(RestoreError, match="沒有任何歷史資料"):
        restore_database(source.parent.parent, target)

    assert _row_count(target) == 1


def test_restore_database_替換失敗時保留既有_db(monkeypatch, tmp_path: Path) -> None:
    source = tmp_path / "artifact" / "data" / "stock_analysis.db"
    target = tmp_path / "runtime" / "data" / "stock_analysis.db"
    _make_db(source, rows=2)
    _make_db(target, rows=1)

    def fail_replace(_src: Path, _dst: Path) -> None:
        raise OSError("replace failed")

    monkeypatch.setattr(os, "replace", fail_replace)

    with pytest.raises(OSError, match="replace failed"):
        restore_database(source.parent.parent, target)

    assert _row_count(target) == 1
