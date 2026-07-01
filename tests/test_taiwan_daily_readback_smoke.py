# -*- coding: utf-8 -*-
from __future__ import annotations

import json
from pathlib import Path

from scripts.taiwan_daily_readback_smoke import main, run_smoke


def _寫入_snapshot(root: Path, trade_date: str = "2026-07-01", status: str = "retained") -> None:
    snapshot_dir = root / "01_market_data" / "daily_snapshot" / f"trade_date={trade_date}"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "snapshot_manifest.json").write_text(
        json.dumps({"status": status, "trade_date": trade_date}, ensure_ascii=False),
        encoding="utf-8",
    )
    (snapshot_dir / "daily_market_normalized.csv").write_text(
        "\n".join(
            [
                "trade_date,market,code,name,open,high,low,close,change,volume_shares,turnover,transactions",
                f"{trade_date},TWSE,2330,台積電,100,111,99,110,1,12000,1320000,120",
                f"{trade_date},TPEX,6488,環球晶,200,225,199,220,2,22000,4840000,88",
            ]
        )
        + "\n",
        encoding="utf-8",
    )


def _寫入_package(root: Path, trade_date: str = "2026-07-01", status: str = "locked") -> None:
    package_dir = root / "05_packages" / f"trade_date={trade_date}"
    package_dir.mkdir(parents=True)
    (package_dir / "package_manifest.json").write_text(
        json.dumps({"status": status, "trade_date": trade_date}, ensure_ascii=False),
        encoding="utf-8",
    )
    sync_dir = root / "06_dashboard_sync"
    sync_dir.mkdir(parents=True)
    package = {
        "metadata": {"status": "success", "tradeDate": trade_date, "schemaVersion": "TW_STOCK_SCREENING_PACKAGE_V1"},
        "screening_results": {
            "potential_stocks": [
                {
                    "market": "TWSE",
                    "code": "2327",
                    "name": "國巨",
                    "trade_date": trade_date,
                    "close": 100,
                    "ma5": 99,
                    "kd_k": 55,
                    "macd": 1.1,
                }
            ],
            "risk_stocks": [],
            "strong_trending": [],
        },
        "chartSeries": {
            "2327": {
                "market": "TWSE",
                "code": "2327",
                "name": "國巨",
                "data": [
                    {"date": "2026-06-30", "open": 90, "high": 91, "low": 89, "close": 90},
                    {"date": trade_date, "open": 99, "high": 101, "low": 98, "close": 100, "ma5": 99, "kdK": 55},
                ],
            }
        },
    }
    (sync_dir / "latest_screening_package.json").write_text(
        json.dumps(package, ensure_ascii=False),
        encoding="utf-8",
    )


def test_正式資料_readback_通過時回傳_pass(tmp_path: Path) -> None:
    _寫入_snapshot(tmp_path)
    _寫入_package(tmp_path)

    result = run_smoke(tmp_path, max_stale_calendar_days=9999)

    assert result.passed
    assert result.checks["snapshot_manifest_status"] == "retained"
    assert result.checks["package_manifest_status"] == "locked"
    assert result.checks["missing_tw_code_fallback_to_china"] is False


def test_正式資料_readback_遇到_failed_manifest_回傳失敗(tmp_path: Path) -> None:
    _寫入_snapshot(tmp_path, status="failed")
    _寫入_package(tmp_path)

    result = run_smoke(tmp_path, max_stale_calendar_days=9999)

    assert not result.passed
    assert any("snapshot manifest 狀態不可用" in error for error in result.errors)


def test_正式資料_readback_cli_失敗時回傳非零(tmp_path: Path, capsys) -> None:
    _寫入_snapshot(tmp_path)

    exit_code = main(["--data-root", str(tmp_path), "--max-stale-calendar-days", "9999"])
    output = json.loads(capsys.readouterr().out)

    assert exit_code == 1
    assert output["status"] == "FAIL"
    assert any("缺檔或空檔" in error for error in output["errors"])
