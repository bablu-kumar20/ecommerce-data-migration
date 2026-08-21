"""Advanced, read-only ecommerce analytics tools."""

from __future__ import annotations

from typing import Any

from google.cloud import bigquery

from python.src.agent_tools.bigquery_tools import (
    GOLD_DATASET,
    MAX_LIST_LIMIT,
    AgentInputError,
    _bounded_integer,
    _error_response,
    _parse_iso_date,
    _run_query,
    _table_id,
)


_PRODUCT_SORT_COLUMNS = {
    "revenue": "total_revenue",
    "units": "total_units_sold",
    "orders": "total_orders",
}


def _validated_period(start_date: str, end_date: str):
    parsed_start_date = _parse_iso_date(start_date, "start_date")
    parsed_end_date = _parse_iso_date(end_date, "end_date")
    if parsed_end_date < parsed_start_date:
        raise AgentInputError("end_date must be on or after start_date.")
    return parsed_start_date, parsed_end_date


def compare_sales_periods(
    first_start_date: str,
    first_end_date: str,
    second_start_date: str,
    second_end_date: str,
) -> dict[str, Any]:
    """Compare Gold sales KPIs for two inclusive YYYY-MM-DD periods."""
    try:
        first_start, first_end = _validated_period(
            first_start_date, first_end_date
        )
        second_start, second_end = _validated_period(
            second_start_date, second_end_date
        )
        table_id = _table_id(GOLD_DATASET, "daily_sales")
        rows = _run_query(
            f"""
            WITH first_period AS (
              SELECT
                COALESCE(SUM(total_orders), 0) AS total_orders,
                COALESCE(SUM(total_items_sold), 0) AS total_items_sold,
                ROUND(COALESCE(SUM(total_revenue), 0), 2) AS total_revenue
              FROM `{table_id}`
              WHERE order_date BETWEEN @first_start_date AND @first_end_date
            ),
            second_period AS (
              SELECT
                COALESCE(SUM(total_orders), 0) AS total_orders,
                COALESCE(SUM(total_items_sold), 0) AS total_items_sold,
                ROUND(COALESCE(SUM(total_revenue), 0), 2) AS total_revenue
              FROM `{table_id}`
              WHERE order_date BETWEEN @second_start_date AND @second_end_date
            )
            SELECT
              @first_start_date AS first_start_date,
              @first_end_date AS first_end_date,
              first_period.total_orders AS first_total_orders,
              first_period.total_items_sold AS first_total_items_sold,
              first_period.total_revenue AS first_total_revenue,
              ROUND(
                SAFE_DIVIDE(
                  first_period.total_revenue,
                  first_period.total_orders
                ), 2
              ) AS first_average_order_value,
              @second_start_date AS second_start_date,
              @second_end_date AS second_end_date,
              second_period.total_orders AS second_total_orders,
              second_period.total_items_sold AS second_total_items_sold,
              second_period.total_revenue AS second_total_revenue,
              ROUND(
                SAFE_DIVIDE(
                  second_period.total_revenue,
                  second_period.total_orders
                ), 2
              ) AS second_average_order_value,
              ROUND(
                SAFE_DIVIDE(
                  second_period.total_orders - first_period.total_orders,
                  first_period.total_orders
                ) * 100, 2
              ) AS orders_change_percent,
              ROUND(
                SAFE_DIVIDE(
                  second_period.total_items_sold - first_period.total_items_sold,
                  first_period.total_items_sold
                ) * 100, 2
              ) AS items_change_percent,
              ROUND(
                SAFE_DIVIDE(
                  second_period.total_revenue - first_period.total_revenue,
                  first_period.total_revenue
                ) * 100, 2
              ) AS revenue_change_percent
            FROM first_period
            CROSS JOIN second_period
            """,
            [
                bigquery.ScalarQueryParameter(
                    "first_start_date", "DATE", first_start
                ),
                bigquery.ScalarQueryParameter(
                    "first_end_date", "DATE", first_end
                ),
                bigquery.ScalarQueryParameter(
                    "second_start_date", "DATE", second_start
                ),
                bigquery.ScalarQueryParameter(
                    "second_end_date", "DATE", second_end
                ),
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "comparison": rows[0] if rows else None,
        }
    except Exception as error:
        return _error_response("compare Gold sales periods", error)


def get_top_products_for_date_range(
    start_date: str,
    end_date: str,
    limit: int = 5,
    sort_by: str = "revenue",
) -> dict[str, Any]:
    """Rank products within an inclusive date range by revenue, units, or orders."""
    try:
        parsed_start, parsed_end = _validated_period(start_date, end_date)
        safe_limit = _bounded_integer(limit, 1, MAX_LIST_LIMIT)
        normalized_sort = str(sort_by).strip().lower()
        if normalized_sort not in _PRODUCT_SORT_COLUMNS:
            raise AgentInputError("sort_by must be revenue, units, or orders.")
        order_column = _PRODUCT_SORT_COLUMNS[normalized_sort]
        table_id = _table_id(GOLD_DATASET, "sales")
        rows = _run_query(
            f"""
            SELECT
              product_id,
              product_name,
              category,
              SUM(quantity) AS total_units_sold,
              COUNT(DISTINCT order_id) AS total_orders,
              ROUND(SUM(line_revenue), 2) AS total_revenue
            FROM `{table_id}`
            WHERE order_date BETWEEN @start_date AND @end_date
            GROUP BY product_id, product_name, category
            ORDER BY {order_column} DESC, product_id
            LIMIT @row_limit
            """,
            [
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", parsed_start
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", parsed_end),
                bigquery.ScalarQueryParameter("row_limit", "INT64", safe_limit),
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "start_date": parsed_start.isoformat(),
            "end_date": parsed_end.isoformat(),
            "sort_by": normalized_sort,
            "limit": safe_limit,
            "products": rows,
        }
    except Exception as error:
        return _error_response("rank products for a date range", error)


def get_top_customers_for_date_range(
    start_date: str,
    end_date: str,
    limit: int = 5,
) -> dict[str, Any]:
    """Return the highest-spending customer IDs for an inclusive date range."""
    try:
        parsed_start, parsed_end = _validated_period(start_date, end_date)
        safe_limit = _bounded_integer(limit, 1, MAX_LIST_LIMIT)
        table_id = _table_id(GOLD_DATASET, "sales")
        rows = _run_query(
            f"""
            SELECT
              customer_id,
              COUNT(DISTINCT order_id) AS total_orders,
              SUM(quantity) AS total_items_purchased,
              ROUND(SUM(line_revenue), 2) AS total_spending
            FROM `{table_id}`
            WHERE order_date BETWEEN @start_date AND @end_date
            GROUP BY customer_id
            ORDER BY total_spending DESC, customer_id
            LIMIT @row_limit
            """,
            [
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", parsed_start
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", parsed_end),
                bigquery.ScalarQueryParameter("row_limit", "INT64", safe_limit),
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "start_date": parsed_start.isoformat(),
            "end_date": parsed_end.isoformat(),
            "limit": safe_limit,
            "customers": rows,
        }
    except Exception as error:
        return _error_response("rank customers for a date range", error)


def get_category_sales_for_date_range(
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Return category sales KPIs for an inclusive YYYY-MM-DD date range."""
    try:
        parsed_start, parsed_end = _validated_period(start_date, end_date)
        table_id = _table_id(GOLD_DATASET, "sales")
        rows = _run_query(
            f"""
            SELECT
              category,
              COUNT(DISTINCT product_id) AS distinct_products,
              COUNT(DISTINCT order_id) AS total_orders,
              SUM(quantity) AS total_units_sold,
              ROUND(SUM(line_revenue), 2) AS total_revenue
            FROM `{table_id}`
            WHERE order_date BETWEEN @start_date AND @end_date
            GROUP BY category
            ORDER BY total_revenue DESC, category
            """,
            [
                bigquery.ScalarQueryParameter(
                    "start_date", "DATE", parsed_start
                ),
                bigquery.ScalarQueryParameter("end_date", "DATE", parsed_end),
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "start_date": parsed_start.isoformat(),
            "end_date": parsed_end.isoformat(),
            "categories": rows,
        }
    except Exception as error:
        return _error_response("read category sales for a date range", error)
