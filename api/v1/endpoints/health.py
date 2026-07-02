# -*- coding: utf-8 -*-
"""
===================================
健康检查接口
===================================

职责：
1. 提供 /api/v1/health 健康检查接口
2. 用于负载均衡器和监控系统
"""

from datetime import datetime

from fastapi import APIRouter, Response, status

from api.v1.schemas.common import HealthResponse, ReadinessResponse
from src.services.database_runtime import inspect_analysis_database

router = APIRouter()


@router.get("/health", response_model=HealthResponse)
async def health_check() -> HealthResponse:
    """
    健康检查接口
    
    用于负载均衡器或监控系统检查服务状态
    
    Returns:
        HealthResponse: 包含服务状态和时间戳
    """
    return HealthResponse(
        status="ok",
        timestamp=datetime.now().isoformat()
    )


@router.get("/ready", response_model=ReadinessResponse)
async def readiness_check(response: Response) -> ReadinessResponse:
    """
    資料服務 readiness。

    與 process health 分離：API process 存活不代表正式 SQLite 分析歷史可用。
    """
    db_status = inspect_analysis_database()
    if not db_status.database_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
    return ReadinessResponse(
        status=db_status.status,
        timestamp=datetime.now().isoformat(),
        database_ready=db_status.database_ready,
        history_available=db_status.history_available,
        reason=db_status.reason,
    )
