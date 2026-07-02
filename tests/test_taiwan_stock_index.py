# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.app import create_app
from data_provider.base import normalize_stock_code
from src.data.taiwan_stock_index import (
    _clear_taiwan_stock_index_cache_for_tests,
    resolve_taiwan_stock_symbol,
    search_taiwan_stocks,
)
from src.services.portfolio_service import PortfolioService
from src.services.stock_code_utils import normalize_code, resolve_index_stock_code_for_analysis


def _write_snapshot(root: Path) -> Path:
    snapshot_dir = root / "01_market_data/daily_snapshot/trade_date=2026-06-29"
    snapshot_dir.mkdir(parents=True)
    (snapshot_dir / "snapshot_manifest.json").write_text('{"status":"success"}', encoding="utf-8")
    csv_path = snapshot_dir / "daily_market_normalized.csv"
    csv_path.write_text(
        "\n".join(
            [
                "trade_date,market,code,name,open,high,low,close,change,volume,amount,transactions,source,source_status",
                "2026-06-29,TWSE,2330,台積電,2330,2395,2330,2370,30,38133782,90337385683,93276,twse,success",
                "2026-06-29,TPEX,6488,環球晶,915,915,866,915,-21,2852894,2547969929,5549,tpex,success",
                "2026-06-29,TWSE,2303,聯電,45,46,44,45.5,0.5,1000,45500,20,twse,success",
                "2026-06-29,TPEX,3264,欣銓,60,61,59,60.5,0.5,1000,60500,20,tpex,success",
                "2026-06-29,TWSE,2945,三商家購,40,41,39,40.5,0.5,1000,40500,20,twse,success",
                "2026-06-29,TWSE,0050,元大台灣50,103.35,105.35,103.30,104.45,1.35,106661221,11134777810,101519,twse,success",
                "2026-06-29,TPEX,700019,宏捷科統一5C購01,1,1.1,0.9,1.0,0,1000,1000,1,tpex,success",
                "2026-06-29,TWSE,2881A,富邦特,63.70,63.80,63.60,63.80,0.10,80295,5117499,40,twse,success",
                "2026-06-29,TWSE,00710B,復華彭博非投等債,18,18.1,17.9,18,0,1000,18000,1,twse,success",
                "2026-06-29,TWSE,020000,富邦特選蘋果N,,,,,0,0,0,0,twse,success",
                "2026-06-29,TWSE,9105,泰金寶-DR,9.32,9.51,9.20,9.33,0.01,30095251,281550084,7816,twse,success",
            ]
        )
        + "\n",
        encoding="utf-8",
    )
    return csv_path


@pytest.fixture()
def taiwan_snapshot(tmp_path, monkeypatch):
    _write_snapshot(tmp_path)
    monkeypatch.setenv("TW_STOCK_INDEX_ROOT", str(tmp_path))
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(tmp_path))
    _clear_taiwan_stock_index_cache_for_tests()
    yield tmp_path
    _clear_taiwan_stock_index_cache_for_tests()


def test_search_supports_twse_tpex_codes_and_chinese_names(taiwan_snapshot) -> None:
    assert search_taiwan_stocks("2330")[0].symbol == "2330.TW"
    assert search_taiwan_stocks("2330.TW")[0].name == "台積電"
    assert search_taiwan_stocks("TWSE:2330")[0].symbol == "2330.TW"
    assert search_taiwan_stocks(" 台積電 ")[0].symbol == "2330.TW"
    assert search_taiwan_stocks("積電")[0].symbol == "2330.TW"

    assert search_taiwan_stocks("6488")[0].symbol == "6488.TWO"
    assert search_taiwan_stocks("6488.two")[0].name == "環球晶"
    assert search_taiwan_stocks("TPEX:6488")[0].symbol == "6488.TWO"
    assert search_taiwan_stocks("環球")[0].symbol == "6488.TWO"


def test_search_defaults_to_common_stocks_and_can_include_excluded(taiwan_snapshot) -> None:
    assert search_taiwan_stocks("0050") == []
    assert search_taiwan_stocks("700019") == []
    assert search_taiwan_stocks("2881A") == []
    assert search_taiwan_stocks("00710B") == []
    assert search_taiwan_stocks("020000") == []
    assert search_taiwan_stocks("9105") == []
    assert search_taiwan_stocks("9999") == []

    etf = search_taiwan_stocks("0050", include_excluded=True)[0]
    assert search_taiwan_stocks("2945")[0].symbol == "2945.TW"
    warrant = search_taiwan_stocks("700019", include_excluded=True)[0]
    preferred = search_taiwan_stocks("2881A", include_excluded=True)[0]
    bond = search_taiwan_stocks("00710B", include_excluded=True)[0]
    etn = search_taiwan_stocks("020000", include_excluded=True)[0]
    assert etf.security_type == "etf"
    assert warrant.security_type == "special_instrument"
    assert preferred.security_type == "preferred_stock"
    assert bond.security_type == "bond"
    assert etn.security_type == "etn"
    assert not etf.is_common_stock
    assert not warrant.is_common_stock
    assert not preferred.is_common_stock
    assert not bond.is_common_stock
    assert not etn.is_common_stock


def test_taiwan_normalization_is_shared_by_services(taiwan_snapshot) -> None:
    assert resolve_taiwan_stock_symbol("2330") == "2330.TW"
    assert resolve_taiwan_stock_symbol("2330.TW") == "2330.TW"
    assert resolve_taiwan_stock_symbol("TWSE:2330") == "2330.TW"
    assert resolve_taiwan_stock_symbol("2330.TW.TW") is None
    assert resolve_taiwan_stock_symbol("6488") == "6488.TWO"
    assert resolve_taiwan_stock_symbol("6488.TWO") == "6488.TWO"
    assert resolve_taiwan_stock_symbol("TPEX:6488") == "6488.TWO"

    assert normalize_code("TWSE:2330") == "2330.TW"
    assert normalize_code("TPEX:6488") == "6488.TWO"
    assert normalize_stock_code("2330") == "2330.TW"
    assert normalize_stock_code("6488") == "6488.TWO"
    assert resolve_index_stock_code_for_analysis("台積電") == "2330.TW"
    assert PortfolioService._normalize_symbol_for_storage("6488") == "6488.TWO"


def test_api_search_and_quote_use_same_taiwan_symbol(taiwan_snapshot, tmp_path) -> None:
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    client = TestClient(create_app(static_dir=static_dir))

    response = client.get("/api/v1/stocks/search", params={"q": "台積電"})
    assert response.status_code == 200
    body = response.json()
    assert body["count"] >= 1
    first = body["items"][0]
    assert first == {
        "code": "2330",
        "symbol": "2330.TW",
        "name": "台積電",
        "market": "tw",
        "exchange": "TWSE",
        "security_type": "common_stock",
        "is_common_stock": True,
    }

    quote_response = client.get(f"/api/v1/stocks/{first['symbol']}/quote")
    assert quote_response.status_code == 200
    quote = quote_response.json()
    assert quote["stock_code"] == "2330.TW"
    assert quote["stock_name"] == "台積電"
    assert quote["current_price"] == 2370.0


def test_explicit_taiwan_symbols_normalize_without_snapshot_index(tmp_path, monkeypatch) -> None:
    missing_root = tmp_path / "missing"
    monkeypatch.setenv("TW_STOCK_INDEX_ROOT", str(missing_root))
    monkeypatch.setenv("TW_STOCK_DATA_ROOT", str(missing_root))
    _clear_taiwan_stock_index_cache_for_tests()

    assert resolve_taiwan_stock_symbol("2330.TW") == "2330.TW"
    assert resolve_taiwan_stock_symbol("TWSE:2330") == "2330.TW"
    assert resolve_taiwan_stock_symbol("6488.TWO") == "6488.TWO"
    assert resolve_taiwan_stock_symbol("TPEX:6488") == "6488.TWO"
    assert resolve_taiwan_stock_symbol("2330") is None
    assert resolve_taiwan_stock_symbol("6488") is None
