CREATE OR REPLACE TABLE
  `{PROJECT_ID}.ecommerce_gold.sales_summary`
AS

SELECT
  COUNT(DISTINCT order_id) AS total_orders,

  SUM(quantity) AS total_items_sold,

  ROUND(
    SUM(line_revenue),
    2
  ) AS total_revenue,

  ROUND(
    SAFE_DIVIDE(
      SUM(line_revenue),
      COUNT(DISTINCT order_id)
    ),
    2
  ) AS average_order_value

FROM `{PROJECT_ID}.ecommerce_gold.sales`;