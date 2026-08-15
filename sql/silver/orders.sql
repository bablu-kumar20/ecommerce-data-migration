CREATE OR REPLACE TABLE
  `{PROJECT_ID}.ecommerce_silver.orders`
AS

SELECT
  o.order_id,
  o.customer_id,

  CASE
    WHEN SAFE_CAST(o.order_date AS DATE) IS NULL
      THEN NULL
    WHEN SAFE_CAST(o.order_date AS DATE) > CURRENT_DATE()
      THEN NULL
    ELSE SAFE_CAST(o.order_date AS DATE)
  END AS order_date,

  CASE
    WHEN o.order_status IS NULL
      OR TRIM(o.order_status) = ''
      THEN 'UNKNOWN'

    WHEN UPPER(TRIM(o.order_status)) IN (
      'PENDING',
      'CONFIRMED',
      'SHIPPED',
      'DELIVERED',
      'COMPLETED',
      'CANCELLED'
    )
      THEN UPPER(TRIM(o.order_status))

    ELSE 'UNKNOWN'
  END AS order_status,

  CASE
    WHEN SAFE_CAST(o.order_date AS DATE) IS NULL
      THEN FALSE
    WHEN SAFE_CAST(o.order_date AS DATE) > CURRENT_DATE()
      THEN FALSE
    ELSE TRUE
  END AS is_valid_order_date,

  CASE
    WHEN UPPER(TRIM(o.order_status)) IN (
      'PENDING',
      'CONFIRMED',
      'SHIPPED',
      'DELIVERED',
      'COMPLETED',
      'CANCELLED'
    )
      THEN TRUE
    ELSE FALSE
  END AS is_valid_order_status,

  CASE
    WHEN c.customer_id IS NOT NULL
      THEN TRUE
    ELSE FALSE
  END AS is_valid_customer

FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY order_id
      ORDER BY order_date
    ) AS row_num

  FROM `{PROJECT_ID}.ecommerce_staging.orders`

  WHERE order_id IS NOT NULL
) AS o

LEFT JOIN `{PROJECT_ID}.ecommerce_staging.customers` AS c
  ON o.customer_id = c.customer_id

WHERE o.row_num = 1;