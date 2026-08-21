CREATE OR REPLACE TABLE
  `{PROJECT_ID}.{BQ_GOLD_DATASET}.daily_sales`
AS

SELECT
  order_date,

  COUNT(DISTINCT order_id) AS total_orders,

  SUM(quantity) AS total_items_sold,

  ROUND(
    SUM(line_revenue),
    2
  ) AS total_revenue

FROM `{PROJECT_ID}.{BQ_GOLD_DATASET}.sales`

GROUP BY
  order_date

ORDER BY
  order_date;