import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from python.src.agent_tools import monitoring_tools
from python.src import pipeline_monitor


class MonitoringToolsTests(unittest.TestCase):
    def test_health_report_is_healthy_when_checks_pass(self):
        row_counts = {
            "status": "success",
            "tables": [
                {
                    "layer": "gold",
                    "table": "sales",
                    "row_count": 10,
                    "table_status": "available",
                }
            ],
        }
        quality = {
            "status": "success",
            "checks": [
                {
                    "table_name": "products",
                    "check_name": "valid_price",
                    "invalid_rows": 0,
                }
            ],
        }
        anomalies = {
            "status": "success",
            "anomaly_count": 0,
            "anomalies": [],
        }

        with (
            patch.object(
                monitoring_tools,
                "get_pipeline_row_counts",
                return_value=row_counts,
            ),
            patch.object(
                monitoring_tools,
                "get_data_quality_report",
                return_value=quality,
            ),
            patch.object(
                monitoring_tools,
                "detect_recent_sales_anomalies",
                return_value=anomalies,
            ),
        ):
            result = monitoring_tools.get_pipeline_health_report()

        self.assertEqual(result["status"], "healthy")
        self.assertEqual(result["issue_count"], 0)

    def test_health_report_surfaces_missing_tables_and_invalid_rows(self):
        with (
            patch.object(
                monitoring_tools,
                "get_pipeline_row_counts",
                return_value={
                    "status": "partial",
                    "tables": [
                        {
                            "layer": "gold",
                            "table": "sales",
                            "row_count": None,
                            "table_status": "missing",
                        }
                    ],
                },
            ),
            patch.object(
                monitoring_tools,
                "get_data_quality_report",
                return_value={
                    "status": "success",
                    "checks": [
                        {
                            "table_name": "products",
                            "check_name": "valid_price",
                            "invalid_rows": 2,
                        }
                    ],
                },
            ),
        ):
            result = monitoring_tools.get_pipeline_health_report(
                include_anomalies=False
            )

        issue_types = {issue["type"] for issue in result["issues"]}
        self.assertEqual(result["status"], "critical")
        self.assertIn("table_unavailable", issue_types)
        self.assertIn("data_quality_failure", issue_types)

    def test_post_pipeline_monitor_persists_latest_report(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            report_path = Path(temporary_directory) / "health.json"
            with (
                patch.object(
                    pipeline_monitor,
                    "HEALTH_REPORT_PATH",
                    report_path,
                ),
                patch.object(
                    pipeline_monitor,
                    "get_pipeline_health_report",
                    return_value={
                        "status": "healthy",
                        "issue_count": 0,
                        "issues": [],
                    },
                ),
            ):
                result = pipeline_monitor.run_post_pipeline_monitor()

            self.assertEqual(result["status"], "healthy")
            self.assertTrue(report_path.exists())
            self.assertIn("generated_at", report_path.read_text(encoding="utf-8"))

    def test_failure_log_redacts_secrets_and_returns_latest_first(self):
        with tempfile.TemporaryDirectory() as temporary_directory:
            failure_path = Path(temporary_directory) / "failures.jsonl"
            with patch.object(
                pipeline_monitor,
                "FAILURE_LOG_PATH",
                failure_path,
            ):
                pipeline_monitor.record_pipeline_failure(
                    "extract",
                    RuntimeError("password=visible failed"),
                )
                pipeline_monitor.record_pipeline_failure(
                    "gold",
                    RuntimeError("second failure"),
                )
                result = pipeline_monitor.get_recent_pipeline_failures(limit=1)

            first_event = json.loads(
                failure_path.read_text(encoding="utf-8").splitlines()[0]
            )
            self.assertNotIn("visible", first_event["message"])
            self.assertIn("[REDACTED]", first_event["message"])
            self.assertEqual(result["failure_count"], 1)
            self.assertEqual(result["failures"][0]["stage"], "gold")


if __name__ == "__main__":
    unittest.main()
