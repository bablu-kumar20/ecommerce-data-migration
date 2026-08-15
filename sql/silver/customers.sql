CREATE OR REPLACE TABLE
  `{PROJECT_ID}.ecommerce_silver.customers`
AS

SELECT
  customer_id,

  COALESCE(
    NULLIF(TRIM(name), ''),
    'Unknown'
  ) AS name,

  CASE
    WHEN REGEXP_CONTAINS(
      LOWER(TRIM(email)),
      r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
    THEN LOWER(TRIM(email))
    ELSE NULL
  END AS email,

  CASE
    WHEN city IS NULL OR TRIM(city) = ''
      THEN 'Unknown'
    ELSE INITCAP(TRIM(city))
  END AS city,

  CASE
    WHEN signup_data > CURRENT_DATE()
      THEN NULL
    ELSE signup_data
  END AS signup_date,

  CASE
    WHEN email IS NULL THEN FALSE
    WHEN REGEXP_CONTAINS(
      LOWER(TRIM(email)),
      r'^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$'
    )
    THEN TRUE
    ELSE FALSE
  END AS is_valid_email,

  CASE
    WHEN signup_data IS NULL THEN FALSE
    WHEN signup_data > CURRENT_DATE() THEN FALSE
    ELSE TRUE
  END AS is_valid_signup_date

FROM (
  SELECT
    *,
    ROW_NUMBER() OVER (
      PARTITION BY customer_id
      ORDER BY signup_data
    ) AS row_num

  FROM `{PROJECT_ID}.ecommerce_staging.customers`

  WHERE customer_id IS NOT NULL
)

WHERE row_num = 1;