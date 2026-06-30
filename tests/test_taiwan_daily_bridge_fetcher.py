# -*- coding: utf-8 -*-

import json

import pandas as pd
import pytest

from data_provider.base import BaseFetcher, DataFetchError, DataFetcherManager
from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher, map_tw_symbol


def _write_package(root, payload):
    path = root / "dashboard-app/public/dashboard-data"
    path.mkdir(parents=True)
    package = path / "latest_screening_package.json"
    package.write_text(json.dumps(payload), encoding="utf-8")
    return package


def _package_payload():
    return {
        "metadata": {"schemaVersion": "TW_STOCK_SCREENING_PACKAGE_V1", "volumeUnit": "lots"},
        "screening_results": {
            "potential_stocks": [
                {
                    "market": "TWSE",
                    "code": "2330",
                    "name": "台積電",
                    "close": 110.0,
                    "volume": 12.0,
                    "volume_shares": 12000,
                    "amount": 1320000,
                    "pct_chg": 1.23,
                    "change": 9.0,
                    "ma5": 108.0,
                }
            ],
            "strong_trending": [
                {
                    "market": "TPEX",
                    "code": "6488",
                    "name": "環球晶",
                    "close": 220.0,
                    "volume": 22.0,
                    "volume_shares": 22000,
                    "amount": 4840000,
                }
            ],
            "risk_stocks": [],
        },
        "chartSeries": {
            "2330": {
                "code": "2330",
                "market": "TWSE",
                "name": "台積電",
                "data": [
                    {"date": "2026-06-26", "open": 100, "high": 105, "low": 99, "close": 100, "volumeShares": 10000},
                    {"date": "2026-06-29", "open": 106, "high": 111, "low": 105, "close": 110, "volumeShares": 12000},
                ],
            },
            "6488": {
                "code": "6488",
                "market": "TPEX",
                "name": "環球晶",
                "data": [
                    {"date": "2026-06-26", "open": 200, "high": 205, "low": 199, "close": 200, "volumeShares": 20000},
                    {"date": "2026-06-29", "open": 210, "high": 225, "low": 209, "close": 220, "volumeShares": 22000},
                ],
            },
        },
    }


def test_map_tw_symbol_requires_explicit_market() -> None:
    assert map_tw_symbol("TWSE", "2330") == "2330.TW"
    assert map_tw_symbol("TPEX", "6488") == "6488.TWO"
    assert map_tw_symbol("TWSE", "2330.TW") == "2330.TW"
    assert map_tw_symbol("TPEX", "6488.TWO") == "6488.TWO"
    assert map_tw_symbol("2330", "TWSE") == "2330.TW"
    assert map_tw_symbol("6488", "TPEX") == "6488.TWO"
    with pytest.raises(ValueError):
        map_tw_symbol("UNKNOWN", "2330")


def test_package_reads_name_quote_volume_indicators_and_existing_pct(tmp_path) -> None:
    _write_package(tmp_path, _package_payload())
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    quote = fetcher.get_realtime_quote("2330.TW")
    assert quote is not None
    assert quote.code == "2330.TW"
    assert quote.name == "台積電"
    assert quote.price == 110.0
    assert quote.volume == 12000
    # pct_chg is percentage points, not a decimal ratio, and package value wins.
    assert quote.change_pct == 1.23
    assert quote.change_amount is None
    assert fetcher.get_stock_name("2330") == "台積電"

    df = fetcher.get_daily_data("2330.TW", days=5)
    assert len(df) == 2
    assert "ma5" in df.columns
    assert df["close"].iloc[-1] == 110.0


def test_package_computes_pct_from_chart_series_and_does_not_use_change(tmp_path) -> None:
    payload = _package_payload()
    row = payload["screening_results"]["strong_trending"][0]
    row["change"] = -43.0
    _write_package(tmp_path, payload)
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    quote = fetcher.get_realtime_quote("6488.TWO")
    assert quote is not None
    assert quote.change_pct == 10.0
    assert quote.change_amount is None


@pytest.mark.parametrize("previous_close", [None, 0])
def test_package_pct_missing_or_zero_previous_close_is_not_fabricated(tmp_path, previous_close) -> None:
    payload = _package_payload()
    payload["screening_results"]["strong_trending"][0].pop("pct_chg", None)
    payload["chartSeries"]["6488"]["data"][0]["close"] = previous_close
    _write_package(tmp_path, payload)
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    quote = fetcher.get_realtime_quote("6488.TWO")
    assert quote is not None
    assert quote.change_pct is None


def test_package_missing_stock_returns_clear_none(tmp_path) -> None:
    _write_package(tmp_path, _package_payload())
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    assert fetcher.get_realtime_quote("9999.TW") is None
    assert fetcher.get_stock_name("9999.TW") is None


def test_bare_code_ambiguity_is_not_guessed(tmp_path) -> None:
    payload = _package_payload()
    payload["chartSeries"]["2330_tpex"] = {
        "code": "2330",
        "market": "TPEX",
        "name": "同碼測試",
        "data": [{"date": "2026-06-29", "close": 10, "volumeShares": 1000}],
    }
    _write_package(tmp_path, payload)
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    with pytest.raises(DataFetchError):
        fetcher.get_realtime_quote("2330")


def test_snapshot_reads_twse_tpex_and_preserves_volume_shares_unit(tmp_path) -> None:
    snapshot_dir = tmp_path / "01_market_data/daily_snapshot/trade_date=2026-06-29"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    (snapshot_dir / "daily_market_normalized.csv").write_text(
        "trade_date,market,code,name,open,high,low,close,change,volume_shares,turnover\n"
        "2026-06-29,TWSE,2330,台積電,100,111,99,110,9,12000,1320000\n"
        "2026-06-29,TPEX,6488,環球晶,200,225,199,220,-43,22000,4840000\n",
        encoding="utf-8",
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    tw_quote = fetcher.get_realtime_quote("2330.TW")
    two_quote = fetcher.get_realtime_quote("6488.TWO")
    assert tw_quote is not None and tw_quote.volume == 12000
    assert two_quote is not None and two_quote.volume == 22000
    assert tw_quote.change_pct is None


def test_snapshot_computes_pct_from_previous_trade_date_close(tmp_path) -> None:
    previous_dir = tmp_path / "01_market_data/daily_snapshot/trade_date=2026-06-26"
    latest_dir = tmp_path / "01_market_data/daily_snapshot/trade_date=2026-06-29"
    previous_dir.mkdir(parents=True)
    latest_dir.mkdir(parents=True)
    (previous_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    (latest_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    (previous_dir / "daily_market_normalized.csv").write_text(
        "trade_date,market,code,name,open,high,low,close,change,volume_shares,turnover\n"
        "2026-06-26,TWSE,2330,台積電,100,105,99,100,1,10000,1000000\n",
        encoding="utf-8",
    )
    (latest_dir / "daily_market_normalized.csv").write_text(
        "trade_date,market,code,name,open,high,low,close,change,volume_shares,turnover\n"
        "2026-06-29,TWSE,2330,台積電,106,111,105,110,9,12000,1320000\n",
        encoding="utf-8",
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    quote = fetcher.get_realtime_quote("2330.TW")
    assert quote is not None
    assert quote.change_pct == 10.0
    assert quote.change_amount is None


def test_snapshot_rejects_missing_required_columns(tmp_path) -> None:
    snapshot_dir = tmp_path / "01_market_data/daily_snapshot/trade_date=2026-06-29"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    (snapshot_dir / "daily_market_normalized.csv").write_text(
        "trade_date,market,code,name,close\n2026-06-29,TWSE,2330,台積電,110\n",
        encoding="utf-8",
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    with pytest.raises(DataFetchError):
        fetcher.get_realtime_quote("2330.TW")


class _FakeFetcher(BaseFetcher):
    def __init__(self, name: str):
        self.name = name
        self.priority = 4
        self.calls = []

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise NotImplementedError

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        raise NotImplementedError

    def get_daily_data(self, stock_code, start_date=None, end_date=None, days=30):
        self.calls.append(stock_code)
        return pd.DataFrame({"date": ["2026-06-29"], "close": [1], "volume": [1]})


def test_manager_prefers_bridge_for_tw_then_existing_fallback(tmp_path, monkeypatch) -> None:
    _write_package(tmp_path, _package_payload())
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    bridge = TaiwanDailyDataBridgeFetcher()
    fallback = _FakeFetcher("YfinanceFetcher")
    manager = DataFetcherManager(fetchers=[fallback, bridge])

    df, source = manager.get_daily_data("2330.TW")
    assert source == "TaiwanDailyDataBridgeFetcher"
    assert not df.empty
    assert fallback.calls == []

    df, source = manager.get_daily_data("9999.TW")
    assert source == "YfinanceFetcher"
    assert not df.empty
    assert fallback.calls == ["9999.TW"]
