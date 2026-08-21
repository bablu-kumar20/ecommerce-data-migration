CREATE OR REPLACE TABLE
  `{PROJECT_ID}.{BQ_GOLD_DATASET}.customer_sales`
AS

SELECT
  customer_id,

  COUNT(DISTINCT order_id) AS total_orders,

  SUM(quantity) AS total_items_purchased,

  ROUND(
    SUM(line_revenue),
    2
  ) AS total_spending

FROM `{PROJECT_ID}.{BQ_GOLD_DATASET}.sales`

GROUP BY
  customer_id

ORDER BY
  total_spending DESC;