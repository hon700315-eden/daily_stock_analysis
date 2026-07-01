# -*- coding: utf-8 -*-

import json

import pandas as pd
import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from data_provider.base import BaseFetcher, DataFetchError, DataFetcherManager
from data_provider.realtime_types import RealtimeSource, UnifiedRealtimeQuote
from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher, map_tw_symbol
from src.services.stock_service import StockService
from src.data.taiwan_stock_index import clear_taiwan_stock_index_cache


def _write_package(root, payload):
    path = root / "dashboard-app/public/dashboard-data"
    path.mkdir(parents=True)
    package = path / "latest_screening_package.json"
    package.write_text(json.dumps(payload), encoding="utf-8")
    return package


def _write_index_snapshot(root):
    snapshot_dir = root / "01_market_data/daily_snapshot/trade_date=2026-06-29"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    (snapshot_dir / "daily_market_normalized.csv").write_text(
        "trade_date,market,code,name,open,high,low,close\n"
        "2026-06-29,TWSE,2330,台積電,100,111,99,110\n"
        "2026-06-29,TPEX,6488,環球晶,200,225,199,220\n",
        encoding="utf-8",
    )


def _write_snapshot(root, trade_date, status, rows):
    snapshot_dir = root / f"01_market_data/daily_snapshot/trade_date={trade_date}"
    snapshot_dir.mkdir(parents=True, exist_ok=True)
    (snapshot_dir / "snapshot_manifest.json").write_text(
        json.dumps({"status": status, "trade_date": trade_date}),
        encoding="utf-8",
    )
    header = "trade_date,market,code,name,open,high,low,close,change,volume,amount,transactions,source,source_status\n"
    body = "\n".join(
        ",".join(str(value) for value in row)
        for row in rows
    )
    (snapshot_dir / "daily_market_normalized.csv").write_text(header + body + "\n", encoding="utf-8")
    return snapshot_dir


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
                    "bollinger_upper": 120.0,
                    "bollinger_mid": 109.0,
                    "bollinger_lower": 98.0,
                    "kd_k": 55.0,
                    "kd_d": 50.0,
                    "macd": 1.2,
                    "macd_signal": 0.8,
                    "macd_hist": 0.4,
                    "rr": 1.8,
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
                    {
                        "date": "2026-06-29",
                        "open": 106,
                        "high": 111,
                        "low": 105,
                        "close": 110,
                        "volumeShares": 12000,
                        "ma5": 108.0,
                        "bollingerUpper": 120.0,
                        "bollingerMiddle": 109.0,
                        "bollingerLower": 98.0,
                        "kdK": 55.0,
                        "kdD": 50.0,
                        "macdDif": 1.2,
                        "macdSignal": 0.8,
                        "macdHistogram": 0.4,
                    },
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
    assert quote.change_amount == 9.0
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
    assert quote.change_amount == -43.0


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


def test_snapshot_selects_latest_retained_and_skips_rejected(tmp_path) -> None:
    _write_snapshot(
        tmp_path,
        "2026-06-28",
        "retained",
        [["2026-06-28", "TWSE", "2330", "台積電", 100, 111, 99, 110, 9, 12000, 1320000, 120, "twse", "success"]],
    )
    _write_snapshot(
        tmp_path,
        "2026-06-29",
        "rejected",
        [["2026-06-29", "TWSE", "2330", "台積電", 100, 111, 99, 999, 9, 12000, 1320000, 120, "twse", "success"]],
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    quote = fetcher.get_quote_payload("2330.TW")

    assert quote is not None
    assert quote["trade_date"] == "2026-06-28"
    assert quote["close"] == 110.0
    assert quote["data_status"] == "snapshot_only"


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
    assert quote.change_amount == 9.0


def test_quote_payload_exposes_formal_taiwan_contract(tmp_path) -> None:
    _write_snapshot(
        tmp_path,
        "2026-06-29",
        "retained",
        [["2026-06-29", "TPEX", "6488", "環球晶", 200, 225, 199, 220, -43, 22000, 4840000, 88, "tpex", "success"]],
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    payload = fetcher.get_quote_payload("6488.TWO")

    assert payload is not None
    assert payload["symbol"] == "6488.TWO"
    assert payload["market"] == "TPEX"
    assert payload["currency"] == "TWD"
    assert payload["volume_shares"] == 22000.0
    assert payload["volume_lots"] == 22.0
    assert payload["transaction_count"] == 88
    assert payload["source"] == "TaiwanDailyDataBridgeFetcher"


def test_history_and_technical_use_chart_series_without_fabricating_snapshot_history(tmp_path) -> None:
    payload = _package_payload()
    payload["chartSeries"].pop("6488")
    _write_package(tmp_path, payload)
    _write_snapshot(
        tmp_path,
        "2026-06-29",
        "retained",
        [["2026-06-29", "TPEX", "6488", "環球晶", 200, 225, 199, 220, -43, 22000, 4840000, 88, "tpex", "success"]],
    )
    fetcher = TaiwanDailyDataBridgeFetcher(tmp_path)

    history = fetcher.get_history_payload("2330.TW")
    technical = fetcher.get_technical_payload("2330.TW")
    snapshot_only = fetcher.get_history_payload("6488.TWO")
    snapshot_technical = fetcher.get_technical_payload("6488.TWO")
    missing_history = fetcher.get_history_payload("9999.TW")
    missing_technical = fetcher.get_technical_payload("9999.TW")

    assert history is not None
    assert history["data_status"] == "available"
    assert len(history["data"]) == 2
    assert history["data"][-1]["ma5"] == 108.0
    assert technical is not None
    assert technical["availability"] == "available"
    assert technical["indicators"]["ma5"] == 108.0
    assert technical["indicators"]["bollinger_upper"] == 120.0
    assert technical["indicators"]["kd_k"] == 55.0
    assert technical["indicators"]["macd_histogram"] == 0.4
    assert technical["indicators"]["rr"] == 1.8
    assert snapshot_only is not None
    assert snapshot_only["data_status"] == "snapshot_only"
    assert len(snapshot_only["data"]) == 1
    assert snapshot_technical is not None
    assert snapshot_technical["availability"] == "technical_unavailable"
    assert snapshot_technical["indicators"]["ma5"] is None
    assert snapshot_technical["indicators"]["kd_k"] is None
    assert snapshot_technical["indicators"]["macd_histogram"] is None
    assert missing_history is None
    assert missing_technical is None


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
    clear_taiwan_stock_index_cache()
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


def test_stock_api_quote_history_and_technical_use_formal_taiwan_payload(tmp_path, monkeypatch) -> None:
    payload = _package_payload()
    payload["chartSeries"].pop("6488")
    _write_package(tmp_path, payload)
    _write_snapshot(
        tmp_path,
        "2026-06-29",
        "retained",
        [
            ["2026-06-29", "TWSE", "2330", "台積電", 106, 111, 105, 110, 9, 12000, 1320000, 120, "twse", "success"],
            ["2026-06-29", "TPEX", "6488", "環球晶", 210, 225, 209, 220, -43, 22000, 4840000, 88, "tpex", "success"],
        ],
    )
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    client = TestClient(create_app(static_dir=tmp_path))

    quote = client.get("/api/v1/stocks/2330.TW/quote")
    history = client.get("/api/v1/stocks/2330.TW/history")
    technical = client.get("/api/v1/stocks/2330.TW/technical")
    snapshot_only = client.get("/api/v1/stocks/6488.TWO/history")
    snapshot_technical = client.get("/api/v1/stocks/6488.TWO/technical")
    not_found_history = client.get("/api/v1/stocks/9999.TW/history")
    not_found_technical = client.get("/api/v1/stocks/9999.TW/technical")

    assert quote.status_code == 200
    assert quote.json()["symbol"] == "2330.TW"
    assert quote.json()["trade_date"] == "2026-06-29"
    assert quote.json()["volume_shares"] == 12000.0
    assert quote.json()["volume_lots"] == 12.0
    assert quote.json()["source"] == "TaiwanDailyDataBridgeFetcher"
    assert history.status_code == 200
    assert history.json()["data_status"] == "available"
    assert len(history.json()["data"]) == 2
    assert technical.status_code == 200
    assert technical.json()["availability"] == "available"
    assert technical.json()["indicators"]["ma5"] == 108.0
    assert snapshot_only.status_code == 200
    assert snapshot_only.json()["data_status"] == "snapshot_only"
    assert snapshot_technical.status_code == 200
    assert snapshot_technical.json()["availability"] == "technical_unavailable"
    assert snapshot_technical.json()["indicators"]["ma5"] is None
    assert not_found_history.status_code == 200
    assert not_found_history.json()["data_status"] == "not_found"
    assert not_found_history.json()["data"] == []
    assert not_found_technical.status_code == 404
    assert not_found_technical.json()["error"] == "not_found"


@pytest.mark.parametrize(
    ("query", "expected_symbol"),
    [
        ("2330", "2330.TW"),
        ("2330.TW", "2330.TW"),
        ("TWSE:2330", "2330.TW"),
        ("台積電", "2330.TW"),
        ("6488", "6488.TWO"),
        ("6488.TWO", "6488.TWO"),
        ("TPEX:6488", "6488.TWO"),
        ("環球晶", "6488.TWO"),
    ],
)
def test_manager_routes_taiwan_daily_queries_to_bridge(tmp_path, monkeypatch, query, expected_symbol) -> None:
    _write_package(tmp_path, _package_payload())
    _write_index_snapshot(tmp_path)
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    clear_taiwan_stock_index_cache()
    fallback = _FakeFetcher("YfinanceFetcher")
    manager = DataFetcherManager(fetchers=[fallback, TaiwanDailyDataBridgeFetcher()])

    df, source = manager.get_daily_data(query)

    assert source == "TaiwanDailyDataBridgeFetcher"
    assert not df.empty
    assert fallback.calls == []
    quote = manager.get_realtime_quote(query)
    assert quote is not None
    assert quote.code == expected_symbol
    assert getattr(quote, "provider_name") == "TaiwanDailyDataBridgeFetcher"


def test_bare_taiwan_code_miss_does_not_fallback_to_china_provider(tmp_path, monkeypatch) -> None:
    _write_package(tmp_path, _package_payload())
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    clear_taiwan_stock_index_cache()
    fallback = _FakeFetcher("AkshareFetcher")
    manager = DataFetcherManager(fetchers=[fallback, TaiwanDailyDataBridgeFetcher()])

    with pytest.raises(DataFetchError, match="未切換至中國市場資料源"):
        manager.get_daily_data("9999")

    assert manager.get_realtime_quote("9999") is None
    assert fallback.calls == []


class _QuoteOnlyChinaFetcher(BaseFetcher):
    name = "AkshareFetcher"
    priority = 1

    def __init__(self) -> None:
        self.quote_calls = []

    def _fetch_raw_data(self, stock_code: str, start_date: str, end_date: str) -> pd.DataFrame:
        raise NotImplementedError

    def _normalize_data(self, df: pd.DataFrame, stock_code: str) -> pd.DataFrame:
        raise NotImplementedError

    def get_realtime_quote(self, stock_code: str, **kwargs):
        self.quote_calls.append((stock_code, kwargs))
        return UnifiedRealtimeQuote(
            code=stock_code,
            name="中國 fallback",
            source=RealtimeSource.AKSHARE,
            market="cn",
            currency="CNY",
            data_quality="ok",
            price=1.0,
        )


def test_taiwan_quote_miss_does_not_call_china_realtime_provider(tmp_path, monkeypatch) -> None:
    _write_package(tmp_path, _package_payload())
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    clear_taiwan_stock_index_cache()
    china = _QuoteOnlyChinaFetcher()
    manager = DataFetcherManager(fetchers=[china, TaiwanDailyDataBridgeFetcher()])

    assert manager.get_realtime_quote("9999") is None
    assert china.quote_calls == []


def test_行情服務保留缺失價格而非補零(monkeypatch) -> None:
    class _Manager:
        def get_realtime_quote(self, stock_code):
            return UnifiedRealtimeQuote(
                code=stock_code,
                name="缺價測試",
                source=RealtimeSource.FALLBACK,
                market="us",
                currency="USD",
                data_quality="partial",
                price=None,
            )

    monkeypatch.setattr("data_provider.base.DataFetcherManager", lambda: _Manager())

    payload = StockService().get_realtime_quote("AAPL")

    assert payload is not None
    assert payload["current_price"] is None
