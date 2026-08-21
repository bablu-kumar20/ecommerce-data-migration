import unittest
from datetime import date
from unittest.mock import patch

from python.src.agent_tools import advanced_analytics_tools
from python.src.agent_tools import bigquery_tools


class AdvancedAnalyticsToolsTests(unittest.TestCase):
    def test_period_comparison_uses_four_typed_dates(self):
        captured = {}

        def fake_query(query, query_parameters):
            captured["query"] = query
            captured["parameters"] = query_parameters
            return [{"revenue_change_percent": "10.00"}]

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(
                advanced_analytics_tools,
                "_run_query",
                side_effect=fake_query,
            ),
        ):
            result = advanced_analytics_tools.compare_sales_periods(
                "2025-01-01",
                "2025-01-31",
                "2025-02-01",
                "2025-02-28",
            )

        parameters = {
            parameter.name: parameter.value
            for parameter in captured["parameters"]
        }
        self.assertEqual(result["status"], "success")
        self.assertEqual(parameters["first_start_date"], date(2025, 1, 1))
        self.assertEqual(parameters["second_end_date"], date(2025, 2, 28))
        self.assertIn("SAFE_DIVIDE", captured["query"])

    def test_product_ranking_clamps_limit_and_allowlists_sort_column(self):
        captured = {}

        def fake_query(query, query_parameters):
            captured["query"] = query
            captured["parameters"] = query_parameters
            return []

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(
                advanced_analytics_tools,
                "_run_query",
                side_effect=fake_query,
            ),
        ):
            result = advanced_analytics_tools.get_top_products_for_date_range(
                "2025-01-01",
                "2025-02-28",
                limit=200,
                sort_by="units",
            )

        parameters = {
            parameter.name: parameter.value
            for parameter in captured["parameters"]
        }
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["limit"], 20)
        self.assertEqual(parameters["row_limit"], 20)
        self.assertIn("ORDER BY total_units_sold DESC", captured["query"])

    def test_product_ranking_rejects_unknown_sort_before_querying(self):
        with patch.object(advanced_analytics_tools, "_run_query") as run_query:
            result = advanced_analytics_tools.get_top_products_for_date_range(
                "2025-01-01",
                "2025-02-28",
                sort_by="total_revenue; DROP TABLE sales",
            )

        self.assertEqual(result["status"], "error")
        self.assertEqual(
            result["message"],
            "sort_by must be revenue, units, or orders.",
        )
        run_query.assert_not_called()


if __name__ == "__main__":
    unittest.main()
