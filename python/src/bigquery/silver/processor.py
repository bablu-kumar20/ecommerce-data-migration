from pathlib import Path
from google.cloud import bigquery
from python.src.bigquery.job_runner import run_query


from python.src.config import (
    GCP_PROJECT_ID,
    BQ_BRONZE_DATASET, 
    BQ_SILVER_DATASET, 
)


def transform(
    bigquery_client: bigquery.Client,
    table: str
) -> None:
    """
    Create the Silver layer using the SQL transformation.
    """

    sql_file = Path(f"sql/silver/{table}.sql")

    query = sql_file.read_text(encoding="utf-8")

    # query = query.replace("{PROJECT_ID}",   GCP_PROJECT_ID )
    query = query.format( 
        PROJECT_ID  = GCP_PROJECT_ID, 
        BQ_BRONZE_DATASET = BQ_BRONZE_DATASET,
        BQ_SILVER_DATASET = BQ_SILVER_DATASET 
    )

    print(f"\nCreating Silver {table} table...")

    run_query(bigquery_client, query)

    print(f"✅ silver {table} table created successfully")


tables = ['orders', 'products', 'order_items', 'customers']


def silver_transformation(bigquery_client: bigquery.Client ):
    for table in tables:
        transform( bigquery_client, table )