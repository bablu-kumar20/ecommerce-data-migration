"""Deterministic pipeline monitoring tools used by agents and ETL triggers."""

from __future__ import annotations

import os
from typing import Any

from python.src.agent_tools.bigquery_tools import (
    get_data_quality_report,
    get_pipeline_row_counts,
)
from python.src.agent_tools.ml_tools import detect_recent_sales_anomalies


def _invalid_row_threshold() -> int:
    try:
        return max(0, int(os.getenv("PIPELINE_INVALID_ROW_THRESHOLD", "0")))
    except ValueError:
        return 0


def get_pipeline_health_report(
    include_anomalies: bool = True,
) -> dict[str, Any]:
    """Return one health report for tables, Silver validation, and recent sales."""
    row_counts = get_pipeline_row_counts()
    quality = get_data_quality_report()
    anomaly_report = (
        detect_recent_sales_anomalies()
        if include_anomalies
        else {"status": "skipped", "anomaly_count": 0, "anomalies": []}
    )

    issues: list[dict[str, Any]] = []
    threshold = _invalid_row_threshold()

    for table in row_counts.get("tables", []):
        table_status = table.get("table_status")
        row_count = table.get("row_count")
        if table_status != "available":
            issues.append(
                {
                    "severity": "critical",
                    "type": "table_unavailable",
                    "layer": table.get("layer"),
                    "table": table.get("table"),
                    "status": table_status,
                }
            )
        elif row_count == 0:
            issues.append(
                {
                    "severity": "critical",
                    "type": "empty_table",
                    "layer": table.get("layer"),
                    "table": table.get("table"),
                }
            )

    invalid_rows_total = 0
    for check in quality.get("checks", []):
        invalid_rows = int(check.get("invalid_rows") or 0)
        invalid_rows_total += invalid_rows
        if invalid_rows > threshold:
            issues.append(
                {
                    "severity": "warning",
                    "type": "data_quality_failure",
                    "table": check.get("table_name"),
                    "check": check.get("check_name"),
                    "invalid_rows": invalid_rows,
                    "threshold": threshold,
                }
            )

    if anomaly_report.get("status") == "success":
        for anomaly in anomaly_report.get("anomalies", []):
            issues.append(
                {
                    "severity": "warning",
                    "type": "sales_anomaly",
                    "order_date": anomaly.get("order_date"),
                    "direction": anomaly.get("anomaly_direction"),
                    "revenue_z_score": anomaly.get("revenue_z_score"),
                    "orders_z_score": anomaly.get("orders_z_score"),
                }
            )
    elif anomaly_report.get("status") == "error":
        issues.append(
            {
                "severity": "warning",
                "type": "anomaly_check_failed",
                "message": anomaly_report.get("message"),
            }
        )

    component_error = any(
        component.get("status") == "error"
        for component in (row_counts, quality)
    )
    critical = any(issue["severity"] == "critical" for issue in issues)
    warning = bool(issues)
    if component_error:
        health_status = "error"
    elif critical:
        health_status = "critical"
    elif warning:
        health_status = "warning"
    else:
        health_status = "healthy"

    return {
        "status": health_status,
        "invalid_row_threshold": threshold,
        "invalid_rows_total": invalid_rows_total,
        "issue_count": len(issues),
        "issues": issues,
        "row_counts": row_counts,
        "data_quality": quality,
        "anomaly_report": anomaly_report,
    }
