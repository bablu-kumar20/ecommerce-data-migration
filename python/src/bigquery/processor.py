from pathlib import Path

from google.cloud import bigquery


def run_query(
    bigquery_client: bigquery.Client,
    query: str,
) -> None:
    """
    Execute a SQL query in BigQuery and wait for completion.
    """

    query_job = bigquery_client.query(query)
    query_job.result()

    # print("BigQuery query executed successfully")


def silver_transformation(
    bigquery_client: bigquery.Client,
    project_id: str,
    table: str
) -> None:
    """
    Create the Silver layer using the SQL transformation.
    """

    sql_file = Path(f"sql/silver/{table}.sql")

    query = sql_file.read_text(encoding="utf-8")

    query = query.replace("{PROJECT_ID}", project_id)

    print(f"Creating Silver {table} table...")

    run_query(bigquery_client, query)

    print(f"Silver {table} table created successfully")
