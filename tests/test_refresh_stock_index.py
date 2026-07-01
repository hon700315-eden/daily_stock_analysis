# -*- coding: utf-8 -*-
"""Tests for scripts.refresh_stock_index default fetch behavior."""

from __future__ import annotations

import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import call, patch

ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = ROOT / "scripts"
if str(SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPTS_DIR))

import generate_index_from_csv

refresh_stock_index = importlib.import_module("refresh_stock_index")


def test_main_fetches_tushare_with_a_rk_by_default():
    with (
        patch.object(refresh_stock_index, "_has_tushare_token", return_value=True),
        patch.object(refresh_stock_index, "_run") as run,
        patch.object(refresh_stock_index, "_sync_static_index"),
    ):
        exit_code = refresh_stock_index.main([])

    assert exit_code == 0
    assert run.call_args_list[0].args[0] == [
        sys.executable,
        "scripts/fetch_tushare_stock_list.py",
        "--a-rk",
    ]
    assert run.call_args_list[1].args[0] == [
        sys.executable,
        "scripts/generate_index_from_csv.py",
        "--source",
        "tushare",
    ]


def test_skip_fetch_reuses_existing_index_when_generating():
    with (
        patch.object(refresh_stock_index, "_run") as run,
        patch.object(refresh_stock_index, "_sync_static_index"),
    ):
        exit_code = refresh_stock_index.main(["--skip-fetch"])

    assert exit_code == 0
    assert run.call_args_list == [
        call([
            sys.executable,
            "scripts/generate_index_from_csv.py",
            "--source",
            "tushare",
            "--reuse-existing-index",
        ])
    ]


def test_load_taiwan_snapshot_data_keeps_common_stocks_only():
    records = [
        SimpleNamespace(
            symbol="2330.TW",
            code="2330",
            name="台積電",
            exchange="TWSE",
            is_common_stock=True,
        ),
        SimpleNamespace(
            symbol="0050.TW",
            code="0050",
            name="元大台灣50",
            exchange="TWSE",
            is_common_stock=False,
        ),
    ]

    with patch(
        "src.data.taiwan_stock_index.get_taiwan_stock_index",
        return_value=records,
    ):
        stocks = generate_index_from_csv.load_taiwan_snapshot_data()

    assert stocks == [
        {
            "ts_code": "2330.TW",
            "symbol": "2330",
            "name": "台積電",
            "market": "TW",
            "aliases": ["TWSE:2330"],
        }
    ]
