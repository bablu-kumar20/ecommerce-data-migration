"""Read-only anomaly detection and forecasting tools."""

from __future__ import annotations

import os
from typing import Any

from google.cloud import bigquery

from python.src.agent_tools.bigquery_tools import (
    GOLD_DATASET,
    AgentInputError,
    _bounded_integer,
    _error_response,
    _run_query,
    _table_id,
)


ML_DATASET = os.getenv("BQ_ML_DATASET", "ecommerce_ml")
FORECAST_MODEL = "daily_revenue_forecast"


def _bounded_float(
    value: float,
    minimum: float,
    maximum: float,
    field_name: str,
) -> float:
    try:
        parsed_value = float(value)
    except (TypeError, ValueError) as error:
        raise AgentInputError(f"{field_name} must be a number.") from error
    if not minimum <= parsed_value <= maximum:
        raise AgentInputError(
            f"{field_name} must be between {minimum} and {maximum}."
        )
    return parsed_value


def detect_recent_sales_anomalies(
    lookback_days: int = 90,
    baseline_days: int = 14,
    z_score_threshold: float = 2.5,
) -> dict[str, Any]:
    """Detect unusual recent revenue or order counts using rolling z-scores."""
    try:
        safe_lookback = _bounded_integer(lookback_days, 14, 365)
        safe_baseline = _bounded_integer(baseline_days, 3, 60)
        if safe_baseline >= safe_lookback:
            raise AgentInputError("baseline_days must be less than lookback_days.")
        safe_threshold = _bounded_float(
            z_score_threshold,
            1.0,
            10.0,
            "z_score_threshold",
        )
        table_id = _table_id(GOLD_DATASET, "daily_sales")
        rows = _run_query(
            f"""
            WITH recent_daily_sales AS (
              SELECT
                order_date,
                total_orders,
                total_items_sold,
                total_revenue
              FROM `{table_id}`
              WHERE order_date >= DATE_SUB(
                (SELECT MAX(order_date) FROM `{table_id}`),
                INTERVAL {safe_lookback} DAY
              )
            ),
            baselines AS (
              SELECT
                *,
                AVG(total_revenue) OVER (
                  ORDER BY order_date
                  ROWS BETWEEN {safe_baseline} PRECEDING AND 1 PRECEDING
                ) AS revenue_baseline,
                STDDEV_POP(total_revenue) OVER (
                  ORDER BY order_date
                  ROWS BETWEEN {safe_baseline} PRECEDING AND 1 PRECEDING
                ) AS revenue_stddev,
                AVG(total_orders) OVER (
                  ORDER BY order_date
                  ROWS BETWEEN {safe_baseline} PRECEDING AND 1 PRECEDING
                ) AS orders_baseline,
                STDDEV_POP(total_orders) OVER (
                  ORDER BY order_date
                  ROWS BETWEEN {safe_baseline} PRECEDING AND 1 PRECEDING
                ) AS orders_stddev
              FROM recent_daily_sales
            ),
            scored AS (
              SELECT
                *,
                SAFE_DIVIDE(
                  total_revenue - revenue_baseline,
                  revenue_stddev
                ) AS revenue_z_score,
                SAFE_DIVIDE(
                  total_orders - orders_baseline,
                  orders_stddev
                ) AS orders_z_score
              FROM baselines
            )
            SELECT
              order_date,
              total_orders,
              total_items_sold,
              total_revenue,
              ROUND(revenue_baseline, 2) AS revenue_baseline,
              ROUND(revenue_z_score, 2) AS revenue_z_score,
              ROUND(orders_baseline, 2) AS orders_baseline,
              ROUND(orders_z_score, 2) AS orders_z_score,
              CASE
                WHEN revenue_z_score <= -@z_score_threshold
                  OR orders_z_score <= -@z_score_threshold THEN 'DROP'
                ELSE 'SPIKE'
              END AS anomaly_direction
            FROM scored
            WHERE
              ABS(revenue_z_score) >= @z_score_threshold
              OR ABS(orders_z_score) >= @z_score_threshold
            ORDER BY order_date DESC
            LIMIT 50
            """,
            [
                bigquery.ScalarQueryParameter(
                    "z_score_threshold", "FLOAT64", safe_threshold
                )
            ],
        )
        return {
            "status": "success",
            "source": table_id,
            "method": "rolling_z_score",
            "lookback_days": safe_lookback,
            "baseline_days": safe_baseline,
            "z_score_threshold": safe_threshold,
            "anomaly_count": len(rows),
            "anomalies": rows,
        }
    except Exception as error:
        return _error_response("detect recent sales anomalies", error)


def get_revenue_forecast(
    horizon_days: int = 30,
    confidence_level: float = 0.9,
) -> dict[str, Any]:
    """Return an ARIMA_PLUS daily revenue forecast from a pre-trained model."""
    try:
        safe_horizon = _bounded_integer(horizon_days, 1, 365)
        safe_confidence = _bounded_float(
            confidence_level,
            0.5,
            0.99,
            "confidence_level",
        )
        model_id = _table_id(ML_DATASET, FORECAST_MODEL)
        rows = _run_query(
            f"""
            SELECT
              DATE(forecast_timestamp) AS forecast_date,
              ROUND(forecast_value, 2) AS forecast_revenue,
              ROUND(prediction_interval_lower_bound, 2) AS lower_bound,
              ROUND(prediction_interval_upper_bound, 2) AS upper_bound,
              confidence_level
            FROM ML.FORECAST(
              MODEL `{model_id}`,
              STRUCT(
                @horizon_days AS horizon,
                @confidence_level AS confidence_level
              )
            )
            ORDER BY forecast_timestamp
            """,
            [
                bigquery.ScalarQueryParameter(
                    "horizon_days", "INT64", safe_horizon
                ),
                bigquery.ScalarQueryParameter(
                    "confidence_level", "FLOAT64", safe_confidence
                ),
            ],
        )
        return {
            "status": "success",
            "source": model_id,
            "horizon_days": safe_horizon,
            "confidence_level": safe_confidence,
            "forecast": rows,
        }
    except Exception as error:
        return _error_response(
            "read the revenue forecast; train the BigQuery ML model first",
            error,
        )


def get_ml_revenue_anomalies(
    anomaly_probability_threshold: float = 0.95,
) -> dict[str, Any]:
    """Return historical revenue anomalies from the pre-trained ARIMA_PLUS model."""
    try:
        safe_threshold = _bounded_float(
            anomaly_probability_threshold,
            0.5,
            0.999,
            "anomaly_probability_threshold",
        )
        model_id = _table_id(ML_DATASET, FORECAST_MODEL)
        rows = _run_query(
            f"""
            SELECT
              DATE(order_date) AS order_date,
              ROUND(total_revenue, 2) AS total_revenue,
              ROUND(lower_bound, 2) AS lower_bound,
              ROUND(upper_bound, 2) AS upper_bound,
              ROUND(anomaly_probability, 4) AS anomaly_probability
            FROM ML.DETECT_ANOMALIES(
              MODEL `{model_id}`,
              STRUCT(@anomaly_probability_threshold AS anomaly_prob_threshold)
            )
            WHERE is_anomaly = TRUE
            ORDER BY order_date DESC
            LIMIT 100
            """,
            [
                bigquery.ScalarQueryParameter(
                    "anomaly_probability_threshold",
                    "FLOAT64",
                    safe_threshold,
                )
            ],
        )
        return {
            "status": "success",
            "source": model_id,
            "method": "arima_plus",
            "anomaly_probability_threshold": safe_threshold,
            "anomaly_count": len(rows),
            "anomalies": rows,
        }
    except Exception as error:
        return _error_response(
            "read BigQuery ML anomalies; train the model first",
            error,
        )
