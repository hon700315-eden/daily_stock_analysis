# -*- coding: utf-8 -*-
"""
===================================
資料源策略層 - 套件初始化
===================================

本套件以策略模式管理多個資料源：
1. 統一的資料取得介面
2. 依市場路由的故障切換
3. 防封禁流控策略

正式預設市場為台灣。台股查詢優先順序：
1. TaiwanDailyDataBridgeFetcher
2. 已驗證的台灣 fallback（例如 suffix 台股可走 YfinanceFetcher）
3. 明確查無資料或可解釋錯誤

中國市場 provider 仍保留，但只在明確中國市場或中國代碼格式時使用：
- EfinanceFetcher / TencentFetcher / AkshareFetcher
- TushareFetcher（需 TUSHARE_TOKEN）
- TickFlowFetcher（需 TICKFLOW_API_KEY）
- PytdxFetcher / BaostockFetcher

提示：priority 數字越小越優先；實際路由仍會先依市場過濾，台股不 fallback 到中國 provider。
"""

from .base import BaseFetcher, DataFetcherManager
from .efinance_fetcher import EfinanceFetcher
from .tencent_fetcher import TencentFetcher
from .akshare_fetcher import AkshareFetcher, is_hk_stock_code
from .tushare_fetcher import TushareFetcher
from .pytdx_fetcher import PytdxFetcher
from .baostock_fetcher import BaostockFetcher
from .taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher
from .yfinance_fetcher import YfinanceFetcher
from .longbridge_fetcher import LongbridgeFetcher
from .finnhub_fetcher import FinnhubFetcher
from .alphavantage_fetcher import AlphaVantageFetcher
from .us_index_mapping import is_us_index_code, is_us_stock_code, get_us_index_yf_symbol, US_INDEX_MAPPING

__all__ = [
    'BaseFetcher',
    'DataFetcherManager',
    'EfinanceFetcher',
    'TencentFetcher',
    'AkshareFetcher',
    'TushareFetcher',
    'PytdxFetcher',
    'BaostockFetcher',
    'TaiwanDailyDataBridgeFetcher',
    'YfinanceFetcher',
    'LongbridgeFetcher',
    'FinnhubFetcher',
    'AlphaVantageFetcher',
    'is_us_index_code',
    'is_us_stock_code',
    'is_hk_stock_code',
    'get_us_index_yf_symbol',
    'US_INDEX_MAPPING',
]
