CREATE OR REPLACE TABLE
  `{PROJECT_ID}.{BQ_SILVER_DATASET}.order_items`
AS

SELECT
  oi.order_item_id,
  oi.order_id,
  oi.product_id,

  CASE
    WHEN oi.quantity IS NULL OR oi.quantity <= 0
      THEN NULL
    ELSE oi.quantity
  END AS quantity,

  CASE
    WHEN oi.quantity IS NULL OR oi.quantity <= 0
      THEN FALSE
    ELSE TRUE
  END AS is_valid_quantity,

  CASE
    WHEN o.order_id IS NOT NULL
      THEN TRUE
    ELSE FALSE
  END AS is_valid_order,

  CASE
    WHEN p.product_id IS NOT NULL
      THEN TRUE
    ELSE FALSE
  END AS is_valid_product

FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY order_item_id
      ORDER BY order_id, product_id
    ) AS row_num

  FROM `{PROJECT_ID}.{BQ_BRONZE_DATASET}.order_items`

  WHERE order_item_id IS NOT NULL
) AS oi

LEFT JOIN `{PROJECT_ID}.{BQ_SILVER_DATASET}.orders` AS o
  ON oi.order_id = o.order_id

LEFT JOIN `{PROJECT_ID}.{BQ_SILVER_DATASET}.products` AS p
  ON oi.product_id = p.product_id

WHERE oi.row_num = 1;