import unittest
from datetime import date
from decimal import Decimal
from types import SimpleNamespace
from unittest.mock import patch

from google.api_core.exceptions import NotFound

from python.src.agent_tools import bigquery_tools


class FakeQueryClient:
    def __init__(self, rows):
        self.rows = rows
        self.query_text = None
        self.job_config = None

    def query(self, query, job_config):
        self.query_text = query
        self.job_config = job_config
        return SimpleNamespace(result=lambda: self.rows)


class FakeMetadataClient:
    def __init__(self, missing_suffix=None):
        self.missing_suffix = missing_suffix

    def get_table(self, table_id):
        if self.missing_suffix and table_id.endswith(self.missing_suffix):
            raise NotFound("table not found")
        return SimpleNamespace(num_rows=3)


class BigQueryAgentToolsTests(unittest.TestCase):
    def test_sales_summary_is_json_safe_and_query_is_cost_limited(self):
        client = FakeQueryClient(
            [
                {
                    "total_orders": 2,
                    "total_items_sold": 4,
                    "total_revenue": Decimal("125.50"),
                    "average_order_value": Decimal("62.75"),
                    "unused_date": date(2026, 1, 2),
                }
            ]
        )

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(
                bigquery_tools,
                "create_bigquery_client",
                return_value=client,
            ),
            patch.dict(
                "os.environ",
                {"ADK_BQ_MAXIMUM_BYTES_BILLED": "2048"},
            ),
        ):
            result = bigquery_tools.get_sales_summary()

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["summary"]["total_revenue"], "125.50")
        self.assertEqual(result["summary"]["unused_date"], "2026-01-02")
        self.assertEqual(client.job_config.maximum_bytes_billed, 2048)

    def test_top_products_clamps_limit_to_twenty(self):
        client = FakeQueryClient([])

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(
                bigquery_tools,
                "create_bigquery_client",
                return_value=client,
            ),
        ):
            result = bigquery_tools.get_top_products(limit=200)

        self.assertEqual(result["status"], "success")
        self.assertEqual(result["limit"], 20)
        self.assertEqual(client.job_config.query_parameters[0].value, 20)

    def test_pipeline_counts_report_missing_tables_without_failing(self):
        client = FakeMetadataClient(missing_suffix=".sales")

        with (
            patch.object(bigquery_tools, "GCP_PROJECT_ID", "test-project"),
            patch.object(
                bigquery_tools,
                "create_bigquery_client",
                return_value=client,
            ),
        ):
            result = bigquery_tools.get_pipeline_row_counts()

        sales_table = next(
            table
            for table in result["tables"]
            if table["layer"] == "gold" and table["table"] == "sales"
        )
        self.assertEqual(result["status"], "partial")
        self.assertEqual(sales_table["table_status"], "missing")
        self.assertEqual(result["layer_totals"]["staging"], 12)
        self.assertEqual(result["layer_totals"]["silver"], 12)
        self.assertEqual(result["layer_totals"]["gold"], 12)


if __name__ == "__main__":
    unittest.main()
