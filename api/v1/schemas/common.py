# -*- coding: utf-8 -*-
"""
===================================
通用响应模型
===================================

职责：
1. 定义通用的响应模型（HealthResponse, ErrorResponse 等）
2. 提供统一的响应格式
"""

from typing import Optional, Any

from pydantic import BaseModel, ConfigDict, Field


class RootResponse(BaseModel):
    """API 根路由响应"""
    
    message: str = Field(..., description="API 运行状态消息", json_schema_extra={"example": "Daily Stock Analysis API is running"})
    version: Optional[str] = Field(None, description="API 版本", json_schema_extra={"example": "1.0.0"})
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "message": "Daily Stock Analysis API is running",
            "version": "1.0.0"
        }
    })


class HealthResponse(BaseModel):
    """健康检查响应"""
    
    status: str = Field(..., description="服务状态", json_schema_extra={"example": "ok"})
    timestamp: Optional[str] = Field(None, description="时间戳")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "timestamp": "2024-01-01T12:00:00"
        }
    })


class ReadinessResponse(BaseModel):
    """資料服務 readiness 響應"""

    status: str = Field(..., description="readiness 狀態")
    timestamp: Optional[str] = Field(None, description="時間戳")
    database_ready: bool = Field(..., description="SQLite DB 是否可讀且 schema 完整")
    history_available: bool = Field(..., description="analysis_history 是否有可用歷史資料")
    reason: Optional[str] = Field(None, description="不可用或降級原因")

    model_config = ConfigDict(json_schema_extra={
        "example": {
            "status": "ok",
            "timestamp": "2024-01-01T12:00:00",
            "database_ready": True,
            "history_available": True,
            "reason": None,
        }
    })


class ErrorResponse(BaseModel):
    """错误响应"""
    
    error: str = Field(..., description="错误类型", json_schema_extra={"example": "validation_error"})
    message: str = Field(..., description="错误详情", json_schema_extra={"example": "请求参数错误"})
    detail: Optional[Any] = Field(None, description="附加错误信息")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "error": "not_found",
            "message": "资源不存在",
            "detail": None
        }
    })


class SuccessResponse(BaseModel):
    """通用成功响应"""
    
    success: bool = Field(True, description="是否成功")
    message: Optional[str] = Field(None, description="成功消息")
    data: Optional[Any] = Field(None, description="响应数据")
    
    model_config = ConfigDict(json_schema_extra={
        "example": {
            "success": True,
            "message": "操作成功",
            "data": None
        }
    })
