SELECT
  DATE(forecast_timestamp) AS forecast_date,
  ROUND(forecast_value, 2) AS forecast_revenue,
  ROUND(prediction_interval_lower_bound, 2) AS lower_bound,
  ROUND(prediction_interval_upper_bound, 2) AS upper_bound,
  confidence_level
FROM ML.FORECAST(
  MODEL `{PROJECT_ID}.{ML_DATASET}.daily_revenue_forecast`,
  STRUCT(30 AS horizon, 0.90 AS confidence_level)
)
ORDER BY forecast_timestamp;
