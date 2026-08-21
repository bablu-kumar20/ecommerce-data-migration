CREATE OR REPLACE TABLE
  `{PROJECT_ID}.{BQ_GOLD_DATASET}.sales`
AS

SELECT
  oi.order_item_id,
  oi.order_id,

  o.order_date,
  o.customer_id,
  o.order_status,

  oi.product_id,

  p.product_name,
  p.category,

  oi.quantity,

  p.price AS unit_price,

  ROUND(
    oi.quantity * p.price,
    2
  ) AS line_revenue

FROM `{PROJECT_ID}.{BQ_SILVER_DATASET}.order_items` AS oi

JOIN `{PROJECT_ID}.{BQ_SILVER_DATASET}.orders` AS o
  ON oi.order_id = o.order_id

JOIN `{PROJECT_ID}.{BQ_SILVER_DATASET}.products` AS p
  ON oi.product_id = p.product_id

WHERE
  oi.is_valid_quantity = TRUE
  AND oi.is_valid_order = TRUE
  AND oi.is_valid_product = TRUE

  AND o.is_valid_order_date = TRUE
  AND o.is_valid_customer = TRUE
  AND o.is_valid_order_status = TRUE

  AND p.is_valid_price = TRUE

  AND o.order_status IN (
    'COMPLETED',
    'SHIPPED',
    'DELIVERED'
  );