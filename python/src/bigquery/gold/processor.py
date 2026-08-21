from pathlib import Path
from google.cloud import bigquery
from python.src.bigquery.job_runner import run_query

from python.src.config import (
    GCP_PROJECT_ID, 
    BQ_SILVER_DATASET, 
    BQ_GOLD_DATASET
)

def transform(
    bigquery_client: bigquery.Client,
    table: str
) -> None:
    """
    Create the gold layer using the SQL transformation.
    """

    sql_file = Path(f"sql/gold/{table}.sql")

    query = sql_file.read_text(encoding="utf-8")

    # query = query.replace("{PROJECT_ID}", project_id)
    query = query.format( 
            PROJECT_ID  = GCP_PROJECT_ID, 
            BQ_SILVER_DATASET = BQ_SILVER_DATASET ,
            BQ_GOLD_DATASET = BQ_GOLD_DATASET
        )

    print(f"\nCreating gold {table} table...")

    run_query(bigquery_client, query)

    print(f"✅ gold {table} table created successfully")


gold_tables = [
    "sales",
    "product_performance",
    "customer_sales",
    "daily_sales",
    "sales_summary"
]

def gold_transformation( bigquery_client: bigquery.Client ):
    for table in gold_tables:
        transform( bigquery_client, table)