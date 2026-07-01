# -*- coding: utf-8 -*-
"""
===================================
股票数据服务层
===================================

职责：
1. 封装股票数据获取逻辑
2. 提供实时行情和历史数据接口
"""

import logging
import re
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List

from src.repositories.stock_repo import StockRepository

logger = logging.getLogger(__name__)


def _is_taiwan_code(stock_code: str) -> bool:
    value = (stock_code or "").strip().upper()
    return bool(re.fullmatch(r"\d{4,6}(?:\.(?:TW|TWO))?", value))


class StockService:
    """
    股票数据服务
    
    封装股票数据获取的业务逻辑
    """
    
    def __init__(self):
        """初始化股票数据服务"""
        self.repo = StockRepository()
    
    def get_realtime_quote(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """
        获取股票实时行情
        
        Args:
            stock_code: 股票代码
            
        Returns:
            实时行情数据字典
        """
        try:
            if _is_taiwan_code(stock_code):
                from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher

                payload = TaiwanDailyDataBridgeFetcher().get_quote_payload(stock_code)
                if payload is None:
                    logger.warning("台股 %s 查無正式行情資料", stock_code)
                    return None
                return {
                    "stock_code": payload["symbol"],
                    "stock_name": payload.get("name"),
                    "current_price": payload.get("close"),
                    "change": payload.get("change"),
                    "change_percent": payload.get("pct_chg"),
                    "open": payload.get("open"),
                    "high": payload.get("high"),
                    "low": payload.get("low"),
                    "prev_close": payload.get("previous_close"),
                    "volume": payload.get("volume_shares"),
                    "amount": payload.get("turnover_amount"),
                    "update_time": payload.get("trade_date") or datetime.now().isoformat(),
                    "market": "tw",
                    "currency": payload.get("currency"),
                    "provider": payload.get("source"),
                    "source": payload.get("source"),
                    **payload,
                }

            # 调用数据获取器获取实时行情
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            quote = manager.get_realtime_quote(stock_code)
            
            if quote is None:
                logger.warning(f"获取 {stock_code} 实时行情失败")
                return None
            
            # UnifiedRealtimeQuote 是 dataclass，使用 getattr 安全访问字段
            # 字段映射: UnifiedRealtimeQuote -> API 响应
            # - code -> stock_code
            # - name -> stock_name
            # - price -> current_price
            # - change_amount -> change
            # - change_pct -> change_percent
            # - open_price -> open
            # - high -> high
            # - low -> low
            # - pre_close -> prev_close
            # - volume -> volume
            # - amount -> amount
            source = getattr(quote, "source", None)
            provider = (
                getattr(quote, "provider_name", None)
                or getattr(source, "value", None)
                or (str(source) if source is not None else None)
            )
            return {
                "stock_code": getattr(quote, "code", stock_code),
                "stock_name": getattr(quote, "name", None),
                "current_price": getattr(quote, "price", None),
                "change": getattr(quote, "change_amount", None),
                "change_percent": getattr(quote, "change_pct", None),
                "open": getattr(quote, "open_price", None),
                "high": getattr(quote, "high", None),
                "low": getattr(quote, "low", None),
                "prev_close": getattr(quote, "pre_close", None),
                "volume": getattr(quote, "volume", None),
                "amount": getattr(quote, "amount", None),
                "update_time": datetime.now().isoformat(),
                "market": getattr(quote, "market", None),
                "currency": getattr(quote, "currency", None),
                "provider": provider,
                "source": provider,
            }
            
        except ImportError:
            logger.warning("DataFetcherManager 未找到，未回傳占位行情")
            return None
        except Exception as e:
            logger.error(f"获取实时行情失败: {e}", exc_info=True)
            return None
    
    def get_history_data(
        self,
        stock_code: str,
        period: str = "daily",
        days: int = 30
    ) -> Dict[str, Any]:
        """
        获取股票历史行情
        
        Args:
            stock_code: 股票代码
            period: K 线周期 (daily/weekly/monthly)
            days: 获取天数
            
        Returns:
            历史行情数据字典
            
        Raises:
            ValueError: 当 period 不是 daily 时抛出（weekly/monthly 暂未实现）
        """
        # 验证 period 参数，只支持 daily
        if period != "daily":
            raise ValueError(
                f"暂不支持 '{period}' 周期，目前仅支持 'daily'。"
                "weekly/monthly 聚合功能将在后续版本实现。"
            )
        
        try:
            if _is_taiwan_code(stock_code):
                from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher

                payload = TaiwanDailyDataBridgeFetcher().get_history_payload(stock_code, days=days)
                if payload is None:
                    logger.warning("台股 %s 查無正式歷史資料", stock_code)
                    return {
                        "stock_code": stock_code,
                        "period": period,
                        "source": "TaiwanDailyDataBridgeFetcher",
                        "data_status": "not_found",
                        "data": [],
                    }
                return payload

            # 调用数据获取器获取历史数据
            from data_provider.base import DataFetcherManager
            
            manager = DataFetcherManager()
            df, source = manager.get_daily_data(stock_code, days=days)
            
            if df is None or df.empty:
                logger.warning(f"获取 {stock_code} 历史数据失败")
                return {"stock_code": stock_code, "period": period, "data": []}
            
            # 获取股票名称
            stock_name = manager.get_stock_name(stock_code)
            
            # 转换为响应格式
            data = []
            for _, row in df.iterrows():
                date_val = row.get("date")
                if hasattr(date_val, "strftime"):
                    date_str = date_val.strftime("%Y-%m-%d")
                else:
                    date_str = str(date_val)
                
                data.append({
                    "date": date_str,
                    "open": float(row.get("open", 0)),
                    "high": float(row.get("high", 0)),
                    "low": float(row.get("low", 0)),
                    "close": float(row.get("close", 0)),
                    "volume": float(row.get("volume", 0)) if row.get("volume") else None,
                    "amount": float(row.get("amount", 0)) if row.get("amount") else None,
                    "change_percent": float(row.get("pct_chg", 0)) if row.get("pct_chg") else None,
                })
            
            return {
                "stock_code": stock_code,
                "stock_name": stock_name,
                "period": period,
                "data": data,
            }
            
        except ImportError:
            logger.warning("DataFetcherManager 未找到，返回空数据")
            return {"stock_code": stock_code, "period": period, "data": []}
        except Exception as e:
            logger.error(f"获取历史数据失败: {e}", exc_info=True)
            return {"stock_code": stock_code, "period": period, "data": []}

    def get_technical_data(self, stock_code: str) -> Optional[Dict[str, Any]]:
        """取得股票技術指標。台股優先讀正式 latest_screening_package.json。"""
        if not _is_taiwan_code(stock_code):
            return None
        try:
            from data_provider.taiwan_daily_bridge_fetcher import TaiwanDailyDataBridgeFetcher

            return TaiwanDailyDataBridgeFetcher().get_technical_payload(stock_code)
        except Exception as e:
            logger.error("取得台股技術指標失敗: %s", e, exc_info=True)
            return {
                "stock_code": stock_code,
                "stock_name": None,
                "trade_date": None,
                "source": "latest_screening_package.json",
                "availability": "source_unavailable",
                "indicators": {},
            }
