"""Read-only BigQuery tools for the ecommerce ADK agent."""

from __future__ import annotations

import logging
import os
import re
from datetime import date, datetime
from decimal import Decimal
from time import perf_counter
from typing import Any

from google.api_core.exceptions import NotFound
from google.cloud import bigquery

from python.src.bigquery.client import create_bigquery_client
from python.src.config import BQ_DATASET, BQ_SILVER_DATASET, GCP_PROJECT_ID


LOGGER = logging.getLogger(__name__)

DEFAULT_MAXIMUM_BYTES_BILLED = 100 * 1024 * 1024
MAX_LIST_LIMIT = 20
MAX_DAILY_LIMIT = 90

STAGING_DATASET = BQ_DATASET or "ecommerce_staging"
SILVER_DATASET = BQ_SILVER_DATASET or "ecommerce_silver"
GOLD_DATASET = os.getenv("BQ_GOLD_DATASET", "ecommerce_gold")

EXPECTED_TABLES = {
    "staging": (
        "customers",
        "orders",
        "products",
        "order_items",
    ),
    "silver": (
        "customers",
        "orders",
        "products",
        "order_items",
    ),
    "gold": (
        "sales",
        "product_performance",
        "customer_sales",
        "daily_sales",
        "sales_summary",
    ),
}

DATASETS = {
    "staging": STAGING_DATASET,
    "silver": SILVER_DATASET,
    "gold": GOLD_DATASET,
}

_PROJECT_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]*$")
_DATASET_PATTERN = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")


class AgentConfigurationError(RuntimeError):
    """Raised when required agent configuration is missing or unsafe."""


class AgentInputError(ValueError):
    """Raised when an agent tool receives invalid user input."""


def _maximum_bytes_billed() -> int:
    raw_value = os.getenv(
        "ADK_BQ_MAXIMUM_BYTES_BILLED",
        str(DEFAULT_MAXIMUM_BYTES_BILLED),
    )
    try:
        value = int(raw_value)
    except (TypeError, ValueError):
        return DEFAULT_MAXIMUM_BYTES_BILLED
    return max(1, value)


def _bounded_integer(value: int, minimum: int, maximum: int) -> int:
    try:
        parsed_value = int(value)
    except (TypeError, ValueError):
        parsed_value = minimum
    return min(max(parsed_value, minimum), maximum)


def _table_id(dataset: str, table: str) -> str:
    if not GCP_PROJECT_ID:
        raise AgentConfigurationError("GCP_PROJECT_ID is not configured.")
    if not _PROJECT_ID_PATTERN.fullmatch(GCP_PROJECT_ID):
        raise AgentConfigurationError("GCP_PROJECT_ID contains unsupported characters.")
    if not _DATASET_PATTERN.fullmatch(dataset):
        raise AgentConfigurationError("A BigQuery dataset name is invalid.")
    if not _DATASET_PATTERN.fullmatch(table):
        raise AgentConfigurationError("A BigQuery table name is invalid.")
    return f"{GCP_PROJECT_ID}.{dataset}.{table}"


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return str(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, bytes):
        return value.decode("utf-8", errors="replace")
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(item) for item in value]
    return value


def _error_response(action: str, error: Exception) -> dict[str, Any]:
    if isinstance(error, (AgentConfigurationError, AgentInputError)):
        LOGGER.info("Agent tool could not %s: %s", action, error)
        message = str(error)
    else:
        LOGGER.exception("BigQuery agent tool failed while attempting to %s", action)
        message = (
            f"Could not {action}. Check BigQuery table availability, credentials, "
            "and read permissions."
        )
    return {
        "status": "error",
        "action": action,
        "error_type": type(error).__name__,
        "message": message,
    }


def _run_query(
    query: str,
    query_parameters: list[bigquery.ScalarQueryParameter] | None = None,
) -> list[dict[str, Any]]:
    job_config = bigquery.QueryJobConfig(
        maximum_bytes_billed=_maximum_bytes_billed(),
        query_parameters=query_parameters or [],
        use_query_cache=True,
    )
    started_at = perf_counter()
    client_started_at = perf_counter()
    client = create_bigquery_client()
    client_seconds = perf_counter() - client_started_at
    query_job = client.query(query, job_config=job_config)
    rows = [
        {key: _json_safe(value) for key, value in row.items()}
        for row in query_job.result()
    ]
    LOGGER.info(
        "BigQuery request completed in %.2f seconds "
        "(client %.2f seconds, rows=%d).",
        perf_counter() - started_at,
        client_seconds,
        len(rows),
    )
    return rows


def _parse_iso_date(value: str, field_name: str) -> date:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError) as error:
        raise AgentInputError(
            f"{field_name} must use YYYY-MM-DD format."
        ) from error


def get_all_time_sales_summary() -> dict[str, Any]:
    """Return all-time Gold totals; never use this tool for a requested date range."""
    try:
        table_id = _table_id(GOLD_DATASET, "sales_summary")
        rows = _run_query(
            f"""
            SELECT
              total_orders,
              total_items_sold,
              total_revenue,
              average_order_value
            FROM `{table_id}`
            LIMIT 1
            """
        )
        return {
            "status": "success",
            "source": table_id,
            "summary": rows[0] if rows else None,
        }
    except Exception as error:  # Tool errors must be returned to the agent.
        return _error_response("read the Gold sales summary", error)


def get_sales_metrics_for_date_range(
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return Gold sales metrics for an inclusive YYYY-MM-DD date range."""
    try:
        parsed_start_date = _parse_iso_date(start_date, "start_date")
        parsed_end_date = _parse_iso_date(end_date, "end_date")
        if parsed_end_date < parsed_start_date:
            raise AgentInputError("end_date must be on or after start_date.")

        table_id = _table_id(GOLD_DATASET, "daily_sales")
        rows = _run_query(
            f"""
            SELECT
              @start_date AS start_date,
              @end_date AS end_date,
              COUNT(*) AS dates_with_sales,
              COALESCE(SUM(total_orders), 0) AS total_orders,
              COALESCE(SUM(total_items_sold), 0) AS total_items_sold,
              ROUND(COALESCE(SUM(total_revenue), 0), 2) AS total_revenue,
              ROUND(
                SAFE_DIVIDE(
                  COALESCE(SUM(total_revenue), 0),
                  COALESCE(SUM(total_orders), 0)
                ),
                2
              ) AS average_order_value
            FROM `{table_id}`
            WHERE order_date BETWEEN @start_date AND @end_date
            """,
            [
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", parsed_start_date
                ),
                bigquery.ScalarQueryParameter(
                    "end_date", "DATE", parsed_end_date
                ),
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "requested_days": (parsed_end_date - parsed_start_date).days + 1,
            "metrics": rows[0] if rows else None,
        }
    except Exception as error:
        return _error_response("read Gold sales metrics for a date range", error)


def get_top_products(limit: int = 5) -> dict[str, Any]:
    """Return the highest-revenue products from Gold, limited to 1 through 20 rows."""
    safe_limit = _bounded_integer(limit, 1, MAX_LIST_LIMIT)
    try:
        table_id = _table_id(GOLD_DATASET, "product_performance")
        rows = _run_query(
            f"""
            SELECT
              product_id,
              product_name,
              category,
              total_units_sold,
              total_orders,
              total_revenue
            FROM `{table_id}`
            ORDER BY total_revenue DESC
            LIMIT @row_limit
            """,
            [bigquery.ScalarQueryParameter("row_limit", "INT64", safe_limit)],
        )
        return {
            "status": "success",
            "source": table_id,
            "limit": safe_limit,
            "products": rows,
        }
    except Exception as error:
        return _error_response("read top products", error)


def get_top_customers(limit: int = 5) -> dict[str, Any]:
    """Return the highest-spending customer IDs from Gold, limited to 1 through 20 rows."""
    safe_limit = _bounded_integer(limit, 1, MAX_LIST_LIMIT)
    try:
        table_id = _table_id(GOLD_DATASET, "customer_sales")
        rows = _run_query(
            f"""
            SELECT
              customer_id,
              total_orders,
              total_items_purchased,
              total_spending
            FROM `{table_id}`
            ORDER BY total_spending DESC
            LIMIT @row_limit
            """,
            [bigquery.ScalarQueryParameter("row_limit", "INT64", safe_limit)],
        )
        return {
            "status": "success",
            "source": table_id,
            "limit": safe_limit,
            "customers": rows,
        }
    except Exception as error:
        return _error_response("read top customers", error)


def get_recent_daily_sales(limit: int = 30) -> dict[str, Any]:
    """Return the latest available daily sales rows, limited to 1 through 90 dates."""
    safe_limit = _bounded_integer(limit, 1, MAX_DAILY_LIMIT)
    try:
        table_id = _table_id(GOLD_DATASET, "daily_sales")
        rows = _run_query(
            f"""
            SELECT
              order_date,
              total_orders,
              total_items_sold,
              total_revenue
            FROM `{table_id}`
            ORDER BY order_date DESC
            LIMIT @row_limit
            """,
            [bigquery.ScalarQueryParameter("row_limit", "INT64", safe_limit)],
        )
        return {
            "status": "success",
            "source": table_id,
            "limit": safe_limit,
            "daily_sales": rows,
        }
    except Exception as error:
        return _error_response("read recent daily sales", error)


def get_data_quality_report() -> dict[str, Any]:
    """Count rows failing each validation check in the Silver ecommerce tables."""
    try:
        customers = _table_id(SILVER_DATASET, "customers")
        orders = _table_id(SILVER_DATASET, "orders")
        products = _table_id(SILVER_DATASET, "products")
        order_items = _table_id(SILVER_DATASET, "order_items")
        rows = _run_query(
            f"""
            SELECT 'customers' AS table_name, 'valid_email' AS check_name,
                   COUNT(*) AS total_rows,
                   COUNTIF(is_valid_email IS NOT TRUE) AS invalid_rows
            FROM `{customers}`
            UNION ALL
            SELECT 'customers', 'valid_signup_date', COUNT(*),
                   COUNTIF(is_valid_signup_date IS NOT TRUE)
            FROM `{customers}`
            UNION ALL
            SELECT 'orders', 'valid_order_date', COUNT(*),
                   COUNTIF(is_valid_order_date IS NOT TRUE)
            FROM `{orders}`
            UNION ALL
            SELECT 'orders', 'valid_order_status', COUNT(*),
                   COUNTIF(is_valid_order_status IS NOT TRUE)
            FROM `{orders}`
            UNION ALL
            SELECT 'orders', 'valid_customer', COUNT(*),
                   COUNTIF(is_valid_customer IS NOT TRUE)
            FROM `{orders}`
            UNION ALL
            SELECT 'products', 'valid_price', COUNT(*),
                   COUNTIF(is_valid_price IS NOT TRUE)
            FROM `{products}`
            UNION ALL
            SELECT 'order_items', 'valid_quantity', COUNT(*),
                   COUNTIF(is_valid_quantity IS NOT TRUE)
            FROM `{order_items}`
            UNION ALL
            SELECT 'order_items', 'valid_order', COUNT(*),
                   COUNTIF(is_valid_order IS NOT TRUE)
            FROM `{order_items}`
            UNION ALL
            SELECT 'order_items', 'valid_product', COUNT(*),
                   COUNTIF(is_valid_product IS NOT TRUE)
            FROM `{order_items}`
            ORDER BY table_name, check_name
            """
        )
        return {
            "status": "success",
            "source": f"{GCP_PROJECT_ID}.{SILVER_DATASET}",
            "checks": rows,
        }
    except Exception as error:
        return _error_response("build the Silver data-quality report", error)


def get_pipeline_row_counts() -> dict[str, Any]:
    """Return metadata row counts and missing-table status for all expected ETL tables."""
    try:
        started_at = perf_counter()
        client = create_bigquery_client()
        table_results: list[dict[str, Any]] = []
        layer_totals = {layer: 0 for layer in EXPECTED_TABLES}

        for layer, tables in EXPECTED_TABLES.items():
            dataset = DATASETS[layer]
            for table in tables:
                table_id = _table_id(dataset, table)
                try:
                    table_metadata = client.get_table(table_id)
                    row_count = int(table_metadata.num_rows)
                    layer_totals[layer] += row_count
                    table_results.append(
                        {
                            "layer": layer,
                            "table": table,
                            "row_count": row_count,
                            "table_status": "available",
                        }
                    )
                except NotFound:
                    table_results.append(
                        {
                            "layer": layer,
                            "table": table,
                            "row_count": None,
                            "table_status": "missing",
                        }
                    )
                except Exception as error:
                    LOGGER.exception("Could not read metadata for %s", table_id)
                    table_results.append(
                        {
                            "layer": layer,
                            "table": table,
                            "row_count": None,
                            "table_status": "error",
                            "error_type": type(error).__name__,
                        }
                    )

        complete = all(
            table["table_status"] == "available" for table in table_results
        )
        LOGGER.info(
            "Pipeline metadata check completed in %.2f seconds for %d tables.",
            perf_counter() - started_at,
            len(table_results),
        )
        return {
            "status": "success" if complete else "partial",
            "project": GCP_PROJECT_ID,
            "layer_totals": layer_totals,
            "tables": table_results,
        }
    except Exception as error:
        return _error_response("read pipeline table metadata", error)
