#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""下載上游台股正式日更 artifact，並解析為唯讀資料根目錄。"""

from __future__ import annotations

import argparse
import json
import os
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path
from typing import Any


DEFAULT_REPO = "hon700315-eden/TW_Stock_Dashboard_Clean"
DEFAULT_WORKFLOW = "Daily Quant Pipeline"
DEFAULT_ARTIFACT_PREFIX = "tw-stock-daily-official-"
DATA_ROOT_NAME = "TW_Stock_Data_Drive"


class ArtifactBridgeError(RuntimeError):
    pass


def _run_gh_json(args: list[str]) -> dict[str, Any]:
    completed = subprocess.run(["gh", *args], text=True, capture_output=True, check=False)
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise ArtifactBridgeError(f"GitHub CLI 查詢失敗：{message}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ArtifactBridgeError("GitHub CLI 回傳內容不是 JSON") from exc
    if not isinstance(payload, dict):
        raise ArtifactBridgeError("GitHub CLI 回傳 JSON 不是物件")
    return payload


def _run_list(repo: str, workflow: str) -> list[dict[str, Any]]:
    completed = subprocess.run(
        [
            "gh",
            "run",
            "list",
            "--repo",
            repo,
            "--workflow",
            workflow,
            "--status",
            "success",
            "--limit",
            "20",
            "--json",
            "databaseId,headSha,createdAt,conclusion,status,event,url",
        ],
        text=True,
        capture_output=True,
        check=False,
    )
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "").strip()
        raise ArtifactBridgeError(f"GitHub CLI 查詢失敗：{message}")
    try:
        payload = json.loads(completed.stdout)
    except json.JSONDecodeError as exc:
        raise ArtifactBridgeError("GitHub CLI run list 回傳內容不是 JSON") from exc
    if not isinstance(payload, list):
        raise ArtifactBridgeError("GitHub CLI run list 回傳 JSON 不是陣列")
    return [item for item in payload if isinstance(item, dict)]


def _list_artifacts(repo: str, run_id: int) -> list[dict[str, Any]]:
    payload = _run_gh_json(["api", f"repos/{repo}/actions/runs/{run_id}/artifacts"])
    artifacts = payload.get("artifacts")
    if not isinstance(artifacts, list):
        raise ArtifactBridgeError("上游 artifacts 回傳格式不正確")
    return [item for item in artifacts if isinstance(item, dict)]


def _select_artifact(artifacts: list[dict[str, Any]], prefix: str) -> dict[str, Any]:
    matches = [
        item
        for item in artifacts
        if str(item.get("name") or "").startswith(prefix)
        and item.get("expired") is not True
        and int(item.get("size_in_bytes") or 0) > 0
    ]
    if not matches:
        raise ArtifactBridgeError("未找到可用的上游台股正式日更 artifact")
    return sorted(matches, key=lambda item: str(item.get("created_at") or ""), reverse=True)[0]


def _download_artifact(repo: str, artifact: dict[str, Any], output_root: Path) -> Path:
    archive = output_root / f"{artifact['name']}.zip"
    output_root.mkdir(parents=True, exist_ok=True)
    archive_endpoint = f"repos/{repo}/actions/artifacts/{artifact['id']}/zip"
    with archive.open("wb") as output:
        completed = subprocess.run(
            ["gh", "api", archive_endpoint],
            stdout=output,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode != 0:
        archive.unlink(missing_ok=True)
        stderr = completed.stderr or b""
        message = stderr.decode("utf-8", errors="replace").strip()
        raise ArtifactBridgeError(f"下載上游 artifact 失敗：{message}")
    if not archive.is_file() or archive.stat().st_size <= 0:
        archive.unlink(missing_ok=True)
        raise ArtifactBridgeError("下載後的上游 artifact 是空檔")
    if not zipfile.is_zipfile(archive):
        archive.unlink(missing_ok=True)
        raise ArtifactBridgeError("下載後的上游 artifact 不是有效 ZIP")
    extract_dir = output_root / str(artifact["name"])
    if extract_dir.exists():
        shutil.rmtree(extract_dir)
    extract_dir.mkdir(parents=True)
    with zipfile.ZipFile(archive) as zf:
        zf.extractall(extract_dir)
    data_root = extract_dir / DATA_ROOT_NAME
    if not data_root.is_dir():
        raise ArtifactBridgeError(f"artifact 未包含 {DATA_ROOT_NAME} 資料根目錄")
    return data_root


def download_latest(repo: str, workflow: str, artifact_prefix: str, output_root: Path) -> dict[str, Any]:
    last_error = "未找到可驗證證據，因此未實作。"
    for run in _run_list(repo, workflow):
        run_id = int(run["databaseId"])
        try:
            artifact = _select_artifact(_list_artifacts(repo, run_id), artifact_prefix)
        except ArtifactBridgeError as exc:
            last_error = str(exc)
            continue
        data_root = _download_artifact(repo, artifact, output_root)
        return {
            "status": "success",
            "repo": repo,
            "workflow": workflow,
            "run_id": run_id,
            "run_url": run.get("url"),
            "run_head_sha": run.get("headSha"),
            "artifact_id": artifact.get("id"),
            "artifact_name": artifact.get("name"),
            "artifact_size_in_bytes": artifact.get("size_in_bytes"),
            "data_root": str(data_root),
        }
    raise ArtifactBridgeError(last_error)


def _append_github_env(path: str | None, data_root: str) -> None:
    if not path:
        return
    with Path(path).open("a", encoding="utf-8") as fh:
        fh.write(f"TW_STOCK_DATA_ROOT={data_root}\n")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="下載上游台股正式日更 artifact")
    parser.add_argument("command", choices=["download"])
    parser.add_argument("--repo", default=os.getenv("UPSTREAM_TW_STOCK_REPO", DEFAULT_REPO))
    parser.add_argument("--workflow", default=os.getenv("UPSTREAM_TW_STOCK_WORKFLOW", DEFAULT_WORKFLOW))
    parser.add_argument("--artifact-prefix", default=DEFAULT_ARTIFACT_PREFIX)
    parser.add_argument("--output-root", type=Path, required=True)
    parser.add_argument("--github-env", default=os.getenv("GITHUB_ENV"))
    args = parser.parse_args(argv)

    try:
        result = download_latest(args.repo, args.workflow, args.artifact_prefix, args.output_root)
    except ArtifactBridgeError as exc:
        print(json.dumps({"status": "FAIL", "error": str(exc)}, ensure_ascii=False, indent=2), file=sys.stderr)
        return 1
    _append_github_env(args.github_env, result["data_root"])
    print(json.dumps(result, ensure_ascii=False, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
