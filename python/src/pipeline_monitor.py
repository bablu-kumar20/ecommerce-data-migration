"""Post-pipeline trigger and local monitoring report persistence."""

from __future__ import annotations

import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from python.src.agent_tools.monitoring_tools import get_pipeline_health_report


PROJECT_ROOT = Path(__file__).resolve().parents[2]
RUNTIME_DIRECTORY = PROJECT_ROOT / "runtime"
HEALTH_REPORT_PATH = RUNTIME_DIRECTORY / "latest_pipeline_health.json"
FAILURE_LOG_PATH = RUNTIME_DIRECTORY / "pipeline_failures.jsonl"

_SENSITIVE_VALUE_PATTERN = re.compile(
    r"(?i)\b(password|api[_-]?key|access[_-]?token|secret)\b"
    r"(\s*[=:]\s*)([^\s,;]+)"
)


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary_path = path.with_suffix(path.suffix + ".tmp")
    temporary_path.write_text(
        json.dumps(payload, indent=2, default=str),
        encoding="utf-8",
    )
    temporary_path.replace(path)


def _sanitize_error_message(error: Exception) -> str:
    message = " ".join(str(error).split())[:500]
    return _SENSITIVE_VALUE_PATTERN.sub(
        lambda match: f"{match.group(1)}{match.group(2)}[REDACTED]",
        message,
    )


def run_post_pipeline_monitor() -> dict[str, Any]:
    """Run deterministic checks after Gold and persist the latest report."""
    report = get_pipeline_health_report(include_anomalies=True)
    report["generated_at"] = datetime.now(timezone.utc).isoformat()
    _write_json(HEALTH_REPORT_PATH, report)
    print(
        "Post-pipeline health: "
        f"{report['status']} ({report['issue_count']} issues)"
    )
    return report


def record_pipeline_failure(stage: str, error: Exception) -> dict[str, Any]:
    """Append a sanitized ETL failure event for later monitor-agent analysis."""
    event = {
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "stage": stage,
        "error_type": type(error).__name__,
        "message": _sanitize_error_message(error),
    }
    FAILURE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    with FAILURE_LOG_PATH.open("a", encoding="utf-8") as failure_log:
        failure_log.write(json.dumps(event, default=str) + "\n")
    return event


def get_recent_pipeline_failures(limit: int = 10) -> dict[str, Any]:
    """Return recent sanitized ETL failure events from the ignored local log."""
    try:
        safe_limit = min(max(int(limit), 1), 50)
    except (TypeError, ValueError):
        safe_limit = 10

    if not FAILURE_LOG_PATH.exists():
        return {
            "status": "not_available",
            "failure_count": 0,
            "failures": [],
            "message": "No local pipeline failure events have been recorded.",
        }

    failures = []
    lines = FAILURE_LOG_PATH.read_text(encoding="utf-8").splitlines()
    for line in reversed(lines):
        if not line.strip():
            continue
        try:
            failures.append(json.loads(line))
        except json.JSONDecodeError:
            continue
        if len(failures) == safe_limit:
            break

    return {
        "status": "success",
        "limit": safe_limit,
        "failure_count": len(failures),
        "failures": failures,
    }


def get_latest_local_pipeline_report() -> dict[str, Any]:
    """Return the latest locally persisted health report without querying BigQuery."""
    if not HEALTH_REPORT_PATH.exists():
        return {
            "status": "not_available",
            "message": "No post-pipeline health report has been generated yet.",
        }
    return json.loads(HEALTH_REPORT_PATH.read_text(encoding="utf-8"))
