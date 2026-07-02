# -*- coding: utf-8 -*-
from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from src.config import Config
from src.services.database_runtime import inspect_analysis_database, resolve_database_path
from src.storage import DatabaseManager


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


def _reset_runtime() -> None:
    Config.reset_instance()
    DatabaseManager.reset_instance()


@pytest.fixture(autouse=True)
def _isolated_runtime_state():
    _reset_runtime()
    yield
    _reset_runtime()


def _make_history_db(path: Path, *, rows: int = 1) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    try:
        conn.execute(REQUIRED_COLUMNS_SQL)
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
                    "{}",
                    "2026-07-01 10:00:00",
                ),
            )
        conn.commit()
    finally:
        conn.close()


def test_database_path_relative_to_repo_root_not_cwd(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("DATABASE_PATH", "data/stock_analysis.db")
    monkeypatch.chdir(tmp_path)
    _reset_runtime()

    resolved = resolve_database_path()

    assert resolved == Path(__file__).resolve().parents[1] / "data" / "stock_analysis.db"


def test_readiness_missing_db_does_not_create_file(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "missing" / "stock_analysis.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    status = inspect_analysis_database(require_history_rows=True)

    assert status.status == "unavailable"
    assert status.reason == "database_missing"
    assert not db_path.exists()


def test_readiness_reports_missing_table_without_create_all(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "stock_analysis.db"
    conn = sqlite3.connect(db_path)
    conn.execute("CREATE TABLE other_table (id INTEGER PRIMARY KEY)")
    conn.commit()
    conn.close()
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    status = inspect_analysis_database(require_history_rows=True)

    assert status.status == "unavailable"
    assert status.reason == "analysis_history_missing"
    conn = sqlite3.connect(db_path)
    try:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
    finally:
        conn.close()
    assert "analysis_history" not in tables


def test_history_endpoint_empty_history_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "stock_analysis.db"
    _make_history_db(db_path, rows=0)
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    client = TestClient(create_app(static_dir=tmp_path / "static"))
    response = client.get("/api/v1/history")

    assert response.status_code == 503
    assert response.json()["error"] == "history_unavailable"
    assert response.json()["reason"] == "analysis_history_empty"


def test_history_endpoint_malformed_db_returns_unavailable(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "stock_analysis.db"
    db_path.write_bytes(b"not sqlite")
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    client = TestClient(create_app(static_dir=tmp_path / "static"))
    response = client.get("/api/v1/history")

    assert response.status_code == 503
    assert response.json()["error"] == "history_unavailable"


def test_ready_distinguishes_process_health_and_database_readiness(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "missing.db"
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    client = TestClient(create_app(static_dir=tmp_path / "static"))

    health = client.get("/api/health")
    ready = client.get("/api/ready")

    assert health.status_code == 200
    assert health.json()["status"] == "ok"
    assert ready.status_code == 503
    assert ready.json()["database_ready"] is False


def test_history_endpoint_reads_valid_history(monkeypatch, tmp_path: Path) -> None:
    db_path = tmp_path / "stock_analysis.db"
    _make_history_db(db_path, rows=1)
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    client = TestClient(create_app(static_dir=tmp_path / "static"))
    response = client.get("/api/v1/history")

    assert response.status_code == 200
    body = response.json()
    assert body["total"] == 1
    assert body["items"][0]["stock_code"] == "2330.TW"


def test_readiness_valid_empty_history_is_database_ready_but_history_unavailable(
    monkeypatch,
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "stock_analysis.db"
    _make_history_db(db_path, rows=0)
    monkeypatch.setenv("DATABASE_PATH", str(db_path))
    _reset_runtime()

    client = TestClient(create_app(static_dir=tmp_path / "static"))
    response = client.get("/api/ready")

    assert response.status_code == 200
    assert response.json()["status"] == "degraded"
    assert response.json()["database_ready"] is True
    assert response.json()["history_available"] is False
    assert response.json()["reason"] == "analysis_history_empty"


def test_restore_default_target_uses_repo_root() -> None:
    from scripts.restore_analysis_history_db import build_parser

    args = build_parser().parse_args(["/tmp/source"])

    assert args.target == Path(__file__).resolve().parents[1] / "data" / "stock_analysis.db"
