# -*- coding: utf-8 -*-
from __future__ import annotations

from pathlib import Path

import yaml


REPO_ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = REPO_ROOT / ".github" / "workflows" / "00-daily-analysis.yml"


def _workflow() -> dict:
    data = yaml.safe_load(WORKFLOW.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def test_daily_analysis_workflow_先驗證上游正式資料再分析() -> None:
    data = _workflow()
    steps = data["jobs"]["analyze"]["steps"]
    names = [step.get("name") for step in steps]

    assert names.index("取得上游台股正式資料 artifact") < names.index("驗證上游台股正式資料")
    assert names.index("驗證上游台股正式資料") < names.index("執行股票分析")

    workflow = WORKFLOW.read_text(encoding="utf-8")
    assert "scripts/taiwan_daily_artifact_bridge.py download" in workflow
    assert "scripts/taiwan_daily_readback_smoke.py" in workflow
    assert "--strict-official" in workflow
    assert "UPSTREAM_ARTIFACT_TOKEN" in workflow
    assert "TW_STOCK_DATA_ROOT=$TW_STOCK_DATA_ROOT" in workflow
    assert "continue-on-error" not in workflow
    assert "|| true" not in workflow


def test_daily_analysis_workflow_台股預設與_stock_list_契約() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert 'export STOCK_LIST="2330.TW"' in workflow
    assert 'export STOCK_LIST="600519"' not in workflow
    assert "A股自选股智能分析系统" not in workflow
    assert "台股自選股智能分析系統" in workflow
    assert "MARKET_REVIEW_REGION: ${{ vars.MARKET_REVIEW_REGION || secrets.MARKET_REVIEW_REGION || 'tw' }}" in workflow
    assert "MARKET_REVIEW_COLOR_SCHEME: ${{ vars.MARKET_REVIEW_COLOR_SCHEME || secrets.MARKET_REVIEW_COLOR_SCHEME || 'red_up' }}" in workflow


def test_daily_analysis_workflow_最小權限() -> None:
    data = _workflow()

    assert data["permissions"] == {"contents": "read", "actions": "read"}
