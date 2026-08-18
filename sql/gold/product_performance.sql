CREATE OR REPLACE TABLE
  `{PROJECT_ID}.ecommerce_gold.product_performance`
AS

SELECT
  product_id,
  product_name,
  category,

  SUM(quantity) AS total_units_sold,

  COUNT(DISTINCT order_id) AS total_orders,

  ROUND(
    SUM(line_revenue),
    2
  ) AS total_revenue

FROM `{PROJECT_ID}.ecommerce_gold.sales`

GROUP BY
  product_id,
  product_name,
  category

ORDER BY
  total_revenue DESC;