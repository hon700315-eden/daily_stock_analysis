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


def _artifact(name: str = "tw-stock-daily-official-2026-07-01") -> dict:
    return {
        "id": 456,
        "name": name,
        "expired": False,
        "size_in_bytes": 100,
        "created_at": "2026-07-01T12:00:00Z",
    }


def _zip_bytes() -> bytes:
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w") as zf:
        zf.writestr("TW_Stock_Data_Drive/06_dashboard_sync/latest_screening_package.json", "{}")
    return buffer.getvalue()


def test_download_latest_沒有_artifact_時失敗(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        if command[:3] == ["gh", "run", "list"]:
            return _completed(json.dumps([{"databaseId": 123, "headSha": "abc"}]))
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/runs/123/artifacts"]:
            return _completed(json.dumps({"total_count": 0, "artifacts": []}))
        raise AssertionError(command)

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    with pytest.raises(bridge.ArtifactBridgeError, match="未找到可用的上游台股正式日更 artifact"):
        bridge.download_latest("owner/repo", "Daily Quant Pipeline", "tw-stock-daily-official-", tmp_path)


def test_download_latest_解壓正式資料根目錄(monkeypatch, tmp_path: Path) -> None:
    download_commands = []

    def fake_run(command, **kwargs):
        if command[:3] == ["gh", "run", "list"]:
            return _completed(json.dumps([{"databaseId": 123, "headSha": "abc", "url": "https://example.test/run"}]))
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/runs/123/artifacts"]:
            return _completed(
                json.dumps(
                    {
                        "total_count": 1,
                        "artifacts": [_artifact()],
                    }
                )
            )
        if command[:3] == ["gh", "api", "repos/owner/repo/actions/artifacts/456/zip"]:
            download_commands.append(command)
            assert "--output" not in command
            assert kwargs["stdout"].writable()
            assert kwargs["stderr"] == bridge.subprocess.PIPE
            assert kwargs["check"] is False
            kwargs["stdout"].write(_zip_bytes())
            return _completed(stderr=b"")
        raise AssertionError(command)

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    result = bridge.download_latest("owner/repo", "Daily Quant Pipeline", "tw-stock-daily-official-", tmp_path)

    assert result["run_id"] == 123
    assert result["artifact_name"] == "tw-stock-daily-official-2026-07-01"
    assert Path(result["data_root"]).name == "TW_Stock_Data_Drive"
    assert Path(result["data_root"]).is_dir()
    assert download_commands == [["gh", "api", "repos/owner/repo/actions/artifacts/456/zip"]]


def test_download_artifact_保留_stdout_二進位_zip(monkeypatch, tmp_path: Path) -> None:
    expected = _zip_bytes()

    def fake_run(command, **kwargs):
        assert command == ["gh", "api", "repos/owner/repo/actions/artifacts/456/zip"]
        kwargs["stdout"].write(expected)
        return _completed(stderr=b"")

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    data_root = bridge._download_artifact("owner/repo", _artifact(), tmp_path)

    archive = tmp_path / "tw-stock-daily-official-2026-07-01.zip"
    assert archive.read_bytes() == expected
    assert data_root.is_dir()


def test_download_artifact_subprocess_失敗時刪除不完整_zip(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        kwargs["stdout"].write(b"partial zip")
        return _completed(stderr="unknown flag: --output".encode("utf-8"), returncode=1)

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    with pytest.raises(bridge.ArtifactBridgeError, match="下載上游 artifact 失敗：unknown flag: --output"):
        bridge._download_artifact("owner/repo", _artifact(), tmp_path)

    assert not (tmp_path / "tw-stock-daily-official-2026-07-01.zip").exists()


def test_download_artifact_拒絕零位元組_zip(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        return _completed(stderr=b"")

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    with pytest.raises(bridge.ArtifactBridgeError, match="下載後的上游 artifact 是空檔"):
        bridge._download_artifact("owner/repo", _artifact(), tmp_path)

    assert not (tmp_path / "tw-stock-daily-official-2026-07-01.zip").exists()


def test_download_artifact_拒絕無效_zip(monkeypatch, tmp_path: Path) -> None:
    def fake_run(command, **kwargs):
        kwargs["stdout"].write(b"not a zip")
        return _completed(stderr=b"")

    monkeypatch.setattr(bridge.subprocess, "run", fake_run)

    with pytest.raises(bridge.ArtifactBridgeError, match="下載後的上游 artifact 不是有效 ZIP"):
        bridge._download_artifact("owner/repo", _artifact(), tmp_path)

    assert not (tmp_path / "tw-stock-daily-official-2026-07-01.zip").exists()
