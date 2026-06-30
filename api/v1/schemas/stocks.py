# -*- coding: utf-8 -*-
"""
===================================
股票数据相关模型
===================================

职责：
1. 定义股票实时行情模型
2. 定义历史 K 线数据模型
"""

from typing import Dict, Optional, List

from pydantic import BaseModel, ConfigDict, Field


class StockQuote(BaseModel):
    """股票实时行情"""
    
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    current_price: float = Field(..., description="当前价格")
    change: Optional[float] = Field(None, description="涨跌额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    open: Optional[float] = Field(None, description="开盘价")
    high: Optional[float] = Field(None, description="最高价")
    low: Optional[float] = Field(None, description="最低价")
    prev_close: Optional[float] = Field(None, description="昨收价")
    volume: Optional[float] = Field(None, description="成交量（股）")
    amount: Optional[float] = Field(None, description="成交额（元）")
    update_time: Optional[str] = Field(None, description="更新时间")
    market: Optional[str] = Field(None, description="市場代碼，例如 tw")
    currency: Optional[str] = Field(None, description="幣別，例如 TWD")
    provider: Optional[str] = Field(None, description="實際行情資料來源")
    source: Optional[str] = Field(None, description="實際行情資料來源，向後相容欄位")
    symbol: Optional[str] = Field(None, description="正式 symbol，例如 2330.TW")
    code: Optional[str] = Field(None, description="不含 suffix 的股票代碼")
    exchange: Optional[str] = Field(None, description="交易所，例如 TWSE 或 TPEX")
    trade_date: Optional[str] = Field(None, description="正式資料交易日")
    previous_close: Optional[float] = Field(None, description="昨收價，與 prev_close 同義")
    close: Optional[float] = Field(None, description="收盤價，與 current_price 同義")
    pct_chg: Optional[float] = Field(None, description="漲跌幅百分點，與 change_percent 同義")
    volume_shares: Optional[float] = Field(None, description="成交量（股）")
    volume_lots: Optional[float] = Field(None, description="成交量（張），台股 1 張 = 1000 股")
    turnover_amount: Optional[float] = Field(None, description="成交金額（新台幣）")
    transaction_count: Optional[int] = Field(None, description="成交筆數")
    data_status: Optional[str] = Field(None, description="資料狀態")
    timezone: Optional[str] = Field(None, description="資料時區")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "2330.TW",
            "stock_name": "台積電",
            "current_price": 1000.00,
            "change": 15.00,
            "change_percent": 0.84,
            "open": 985.00,
            "high": 1010.00,
            "low": 980.00,
            "prev_close": 985.00,
            "volume": 10000000,
            "amount": 18000000000,
            "update_time": "2024-01-01T15:00:00",
            "market": "tw",
            "currency": "TWD",
            "provider": "TaiwanDailyDataBridgeFetcher",
            "source": "TaiwanDailyDataBridgeFetcher"
        }
    })


class KLineData(BaseModel):
    """K 线数据点"""
    
    date: str = Field(..., description="日期")
    open: float = Field(..., description="开盘价")
    high: float = Field(..., description="最高价")
    low: float = Field(..., description="最低价")
    close: float = Field(..., description="收盘价")
    volume: Optional[float] = Field(None, description="成交量")
    amount: Optional[float] = Field(None, description="成交额")
    change_percent: Optional[float] = Field(None, description="涨跌幅 (%)")
    transaction_count: Optional[int] = Field(None, description="成交筆數")
    ma5: Optional[float] = Field(None, description="MA5")
    ma10: Optional[float] = Field(None, description="MA10")
    ma20: Optional[float] = Field(None, description="MA20")
    ma60: Optional[float] = Field(None, description="MA60")
    bollinger_upper: Optional[float] = Field(None, description="布林上軌")
    bollinger_middle: Optional[float] = Field(None, description="布林中軌")
    bollinger_lower: Optional[float] = Field(None, description="布林下軌")
    kd_k: Optional[float] = Field(None, description="KD K")
    kd_d: Optional[float] = Field(None, description="KD D")
    macd_dif: Optional[float] = Field(None, description="MACD DIF")
    macd_signal: Optional[float] = Field(None, description="MACD signal/DEA")
    macd_histogram: Optional[float] = Field(None, description="MACD histogram")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "date": "2024-01-01",
            "open": 1785.00,
            "high": 1810.00,
            "low": 1780.00,
            "close": 1800.00,
            "volume": 10000000,
            "amount": 18000000000,
            "change_percent": 0.84
        }
    })


class ExtractItem(BaseModel):
    """单条提取结果（代码、名称、置信度）"""

    code: Optional[str] = Field(None, description="股票代码，None 表示解析失败")
    name: Optional[str] = Field(None, description="股票名称（如有）")
    confidence: str = Field("medium", description="置信度：high/medium/low")


class ExtractFromImageResponse(BaseModel):
    """图片股票代码提取响应"""

    codes: List[str] = Field(..., description="提取的股票代码（已去重，向后兼容）")
    items: List[ExtractItem] = Field(default_factory=list, description="提取结果明细（代码+名称+置信度）")
    raw_text: Optional[str] = Field(None, description="原始 LLM 响应（调试用）")


class StockHistoryResponse(BaseModel):
    """股票历史行情响应"""
    
    stock_code: str = Field(..., description="股票代码")
    stock_name: Optional[str] = Field(None, description="股票名称")
    period: str = Field(..., description="K 线周期")
    data: List[KLineData] = Field(default_factory=list, description="K 线数据列表")
    source: Optional[str] = Field(None, description="歷史資料來源")
    data_status: Optional[str] = Field(None, description="資料狀態")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "stock_code": "600519",
            "stock_name": "贵州茅台",
            "period": "daily",
            "data": []
        }
    })


class StockSearchItem(BaseModel):
    """單筆股票搜尋結果"""

    code: str = Field(..., description="不含 suffix 的股票代碼")
    symbol: str = Field(..., description="可直接交給 quote endpoint 的正式代碼")
    name: str = Field(..., description="正式名稱")
    market: str = Field(..., description="市場代碼，例如 tw")
    exchange: str = Field(..., description="交易所，例如 TWSE 或 TPEX")
    security_type: str = Field(..., description="商品類型")
    is_common_stock: bool = Field(..., description="是否為上市／上櫃普通股")


class StockSearchResponse(BaseModel):
    """股票搜尋回應"""

    query: str = Field(..., description="原始查詢字串")
    count: int = Field(..., description="結果筆數")
    items: List[StockSearchItem] = Field(default_factory=list, description="搜尋結果")


class StockTechnicalResponse(BaseModel):
    """股票技術指標回應"""

    stock_code: str = Field(..., description="股票代碼")
    stock_name: Optional[str] = Field(None, description="股票名稱")
    trade_date: Optional[str] = Field(None, description="指標資料日期")
    source: Optional[str] = Field(None, description="技術指標來源")
    availability: str = Field(..., description="資料可用狀態")
    indicators: Dict[str, Optional[float]] = Field(default_factory=dict, description="技術指標")
