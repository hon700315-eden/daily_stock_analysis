# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import os
import shutil
import sqlite3
import sys
import tempfile
from pathlib import Path
from typing import Sequence


REQUIRED_ANALYSIS_HISTORY_COLUMNS = {
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


class RestoreError(RuntimeError):
    pass


def resolve_source_db(source: Path) -> Path:
    source = source.expanduser()
    if source.is_file():
        return source
    if not source.is_dir():
        raise RestoreError(f"來源不存在：{source}")

    candidates = [
        source / "data" / "stock_analysis.db",
        source / "stock_analysis.db",
    ]
    candidates.extend(sorted(source.glob("**/data/stock_analysis.db")))
    candidates.extend(sorted(source.glob("**/stock_analysis.db")))

    unique_candidates = []
    for candidate in candidates:
        if candidate.is_file() and candidate not in unique_candidates:
            unique_candidates.append(candidate)

    if len(unique_candidates) != 1:
        found = ", ".join(str(item) for item in unique_candidates) or "無"
        raise RestoreError(f"無法唯一定位 artifact 內的 stock_analysis.db，找到：{found}")

    return unique_candidates[0]


def validate_analysis_history_db(db_path: Path, *, require_non_empty: bool = True) -> None:
    if not db_path.is_file():
        raise RestoreError(f"SQLite DB 不存在：{db_path}")
    if db_path.stat().st_size <= 0:
        raise RestoreError(f"SQLite DB 是空檔案：{db_path}")

    try:
        conn = sqlite3.connect(f"file:{db_path}?mode=ro", uri=True)
    except sqlite3.Error as exc:
        raise RestoreError(f"SQLite DB 無法唯讀開啟：{exc}") from exc

    try:
        integrity = conn.execute("PRAGMA integrity_check").fetchone()
        if not integrity or integrity[0] != "ok":
            detail = integrity[0] if integrity else "無結果"
            raise RestoreError(f"SQLite integrity_check 失敗：{detail}")

        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table'"
            ).fetchall()
        }
        if "analysis_history" not in tables:
            raise RestoreError("SQLite DB 缺少 analysis_history 表")

        columns = {
            row[1]
            for row in conn.execute("PRAGMA table_info(analysis_history)").fetchall()
        }
        missing_columns = sorted(REQUIRED_ANALYSIS_HISTORY_COLUMNS - columns)
        if missing_columns:
            raise RestoreError(
                "analysis_history schema 缺少必要欄位：" + ", ".join(missing_columns)
            )

        if require_non_empty:
            count = conn.execute("SELECT COUNT(*) FROM analysis_history").fetchone()[0]
            if int(count or 0) <= 0:
                raise RestoreError("analysis_history 沒有任何歷史資料，拒絕還原空歷史庫")
    except sqlite3.Error as exc:
        raise RestoreError(f"SQLite DB 驗證失敗：{exc}") from exc
    finally:
        conn.close()


def restore_database(
    source: Path,
    target: Path,
    *,
    require_non_empty: bool = True,
) -> Path:
    source_db = resolve_source_db(source).resolve()
    target = target.expanduser().resolve()
    if source_db == target:
        raise RestoreError("來源 DB 與目標 DB 相同，拒絕無效還原")

    validate_analysis_history_db(source_db, require_non_empty=require_non_empty)

    target.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=f".{target.name}.restore.",
        suffix=".tmp",
        dir=str(target.parent),
    )
    os.close(fd)
    temp_path = Path(temp_name)

    try:
        shutil.copy2(source_db, temp_path)
        validate_analysis_history_db(temp_path, require_non_empty=require_non_empty)
        os.replace(temp_path, target)
    except Exception:
        try:
            temp_path.unlink()
        except FileNotFoundError:
            pass
        raise

    return target


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="安全還原每日分析 artifact 中的 SQLite 分析歷史庫",
    )
    parser.add_argument(
        "source",
        type=Path,
        help="來源 DB 檔案或已解壓 artifact 目錄",
    )
    parser.add_argument(
        "--target",
        type=Path,
        default=Path("data/stock_analysis.db"),
        help="目標 DB 路徑，預設為 data/stock_analysis.db",
    )
    parser.add_argument(
        "--allow-empty-history",
        action="store_true",
        help="僅供 schema 偵錯使用；正式還原不得使用",
    )
    parser.add_argument("--source-run-id", help="來源 GitHub Actions run ID，僅寫入執行摘要")
    parser.add_argument("--source-commit", help="來源 commit SHA，僅寫入執行摘要")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    try:
        restored = restore_database(
            args.source,
            args.target,
            require_non_empty=not args.allow_empty_history,
        )
    except RestoreError as exc:
        print(f"還原失敗：{exc}", file=sys.stderr)
        return 1

    metadata = []
    if args.source_run_id:
        metadata.append(f"run_id={args.source_run_id}")
    if args.source_commit:
        metadata.append(f"commit={args.source_commit}")
    suffix = f"（{', '.join(metadata)}）" if metadata else ""
    print(f"已安全還原 SQLite 分析歷史庫：{restored}{suffix}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
