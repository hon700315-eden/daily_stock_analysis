# -*- coding: utf-8 -*-
from __future__ import annotations

import io
import json
import zipfile
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import taiwan_daily_artifact_bridge as bridge


def _completed(stdout: str = "", stderr: str = "", returncode: int = 0):
    return SimpleNamespace(stdout=stdout, stderr=stderr, returncode=returncode)


def test_download_latest_沒有_artifact_時失敗(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, text=True, capture_output=True, check=False):
        if command[:3] == ["gh", "run", "list"]:
            return _completed(json.dumps([{"databaseId": 123, "headSha": "abc"}]))
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/runs/123/artifacts"]:
            return _completed(json.dumps({"total_count": 0, "artifacts": []}))
        raise AssertionError(command)

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    with pytest.raises(bridge.ArtifactBridgeError, match="未找到可用的上游台股正式日更 artifact"):
        bridge.download_latest("owner/repo", "Daily Quant Pipeline", "tw-stock-daily-official-", tmp_path)


def test_download_latest_解壓正式資料根目錄(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, text=True, capture_output=True, check=False):
        if command[:3] == ["gh", "run", "list"]:
            return _completed(json.dumps([{"databaseId": 123, "headSha": "abc", "url": "https://example.test/run"}]))
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/runs/123/artifacts"]:
            return _completed(
                json.dumps(
                    {
                        "total_count": 1,
                        "artifacts": [
                            {
                                "id": 456,
                                "name": "tw-stock-daily-official-2026-07-01",
                                "expired": False,
                                "size_in_bytes": 100,
                                "created_at": "2026-07-01T12:00:00Z",
                            }
                        ],
                    }
                )
            )
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/artifacts/456/zip"]:
            output = Path(command[-1])
            output.parent.mkdir(parents=True, exist_ok=True)
            buffer = io.BytesIO()
            with zipfile.ZipFile(buffer, "w") as zf:
                zf.writestr("TW_Stock_Data_Drive/06_dashboard_sync/latest_screening_package.json", "{}")
            output.write_bytes(buffer.getvalue())
            return _completed()
        raise AssertionError(command)

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    result = bridge.download_latest("owner/repo", "Daily Quant Pipeline", "tw-stock-daily-official-", tmp_path)

    assert result["run_id"] == 123
    assert result["artifact_name"] == "tw-stock-daily-official-2026-07-01"
    assert Path(result["data_root"]).name == "TW_Stock_Data_Drive"
    assert Path(result["data_root"]).is_dir()
