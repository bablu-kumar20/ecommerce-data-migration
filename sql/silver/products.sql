CREATE OR REPLACE TABLE
  `{PROJECT_ID}.ecommerce_silver.products`
AS

SELECT
  product_id,

  COALESCE(
    NULLIF(TRIM(product_name), ''),
    'Unknown Product'
  ) AS product_name,

  CASE
    WHEN category IS NULL OR TRIM(category) = ''
      THEN 'Unknown'
    ELSE INITCAP(TRIM(category))
  END AS category,

  CASE
    WHEN price IS NULL OR price <= 0
      THEN NULL
    ELSE price
  END AS price,

  CASE
    WHEN price IS NULL OR price <= 0
      THEN FALSE
    ELSE TRUE
  END AS is_valid_price

FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY product_id
      ORDER BY product_name
    ) AS row_num

  FROM `{PROJECT_ID}.ecommerce_staging.products`

  WHERE product_id IS NOT NULL
)

WHERE row_num = 1;