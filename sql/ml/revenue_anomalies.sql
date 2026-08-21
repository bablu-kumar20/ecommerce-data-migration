SELECT
  DATE(order_date) AS order_date,
  ROUND(total_revenue, 2) AS total_revenue,
  is_anomaly,
  ROUND(lower_bound, 2) AS lower_bound,
  ROUND(upper_bound, 2) AS upper_bound,
  ROUND(anomaly_probability, 4) AS anomaly_probability
FROM ML.DETECT_ANOMALIES(
  MODEL `{PROJECT_ID}.{ML_DATASET}.daily_revenue_forecast`,
  STRUCT(0.95 AS anomaly_prob_threshold)
)
WHERE is_anomaly = TRUE
ORDER BY order_date DESC;
