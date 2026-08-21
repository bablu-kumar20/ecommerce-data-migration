CREATE OR REPLACE MODEL
  `{PROJECT_ID}.{ML_DATASET}.daily_revenue_forecast`
OPTIONS (
  MODEL_TYPE = 'ARIMA_PLUS',
  TIME_SERIES_TIMESTAMP_COL = 'order_date',
  TIME_SERIES_DATA_COL = 'total_revenue',
  DATA_FREQUENCY = 'DAILY',
  HORIZON = 30,
  DECOMPOSE_TIME_SERIES = TRUE
)
AS
SELECT
  order_date,
  CAST(total_revenue AS FLOAT64) AS total_revenue
FROM `{PROJECT_ID}.ecommerce_gold.daily_sales`
WHERE total_revenue IS NOT NULL
ORDER BY order_date;
