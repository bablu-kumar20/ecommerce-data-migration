import unittest
from unittest.mock import patch

from python.src.agent_tools import bigquery_tools
from python.src.agent_tools import ml_tools


class MlToolsTests(unittest.TestCase):
    def test_rolling_anomaly_query_uses_bounded_windows(self):
        captured = {}

        def fake_query(query, query_parameters):
            captured["query"] = query
            captured["parameters"] = query_parameters
            return [{"order_date": "2025-02-01"}]

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(ml_tools, "_run_query", side_effect=fake_query),
        ):
            result = ml_tools.detect_recent_sales_anomalies(
                lookback_days=1000,
                baseline_days=14,
                z_score_threshold=3,
            )

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["lookback_days"], 365)
        self.assertEqual(result["anomaly_count"], 1)
        self.assertIn("INTERVAL 365 DAY", captured["query"])
        self.assertIn("ROWS BETWEEN 14 PRECEDING", captured["query"])
        self.assertEqual(captured["parameters"][0].value, 3.0)

    def test_forecast_caps_horizon_and_parameterizes_confidence(self):
        captured = {}

        def fake_query(query, query_parameters):
            captured["query"] = query
            captured["parameters"] = query_parameters
            return []

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(ml_tools, "_run_query", side_effect=fake_query),
        ):
            result = ml_tools.get_revenue_forecast(
                horizon_days=1000,
                confidence_level=0.9,
            )

        parameters = {
            parameter.name: parameter.value
            for parameter in captured["parameters"]
        }
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["horizon_days"], 365)
        self.assertEqual(parameters["horizon_days"], 365)
        self.assertEqual(parameters["confidence_level"], 0.9)
        self.assertIn("ML.FORECAST", captured["query"])

    def test_ml_anomaly_threshold_is_validated_before_querying(self):
        with patch.object(ml_tools, "_run_query") as run_query:
            result = ml_tools.get_ml_revenue_anomalies(0.1)

        self.assertEqual(result["status"], "error")
        self.assertIn("must be between", result["message"])
        run_query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
