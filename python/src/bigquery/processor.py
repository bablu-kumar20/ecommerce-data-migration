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

    print("BigQuery query executed successfully")


def create_silver_customers(
    bigquery_client: bigquery.Client,
    project_id: str,
) -> None:
    """
    Create the Silver customers table using the SQL transformation.
    """

    sql_file = Path("sql/silver/customers.sql")

    query = sql_file.read_text(encoding="utf-8")

    query = query.replace("{PROJECT_ID}", project_id)

    print("Creating Silver customers table...")

    run_query(bigquery_client, query)

    print("Silver customers table created successfully")

def create_silver_products(
    bigquery_client: bigquery.Client,
    project_id: str,
) -> None:
    """
    Create the Silver products table using the SQL transformation.
    """

    sql_file = Path("sql/silver/products.sql")

    query = sql_file.read_text(encoding="utf-8")

    query = query.replace("{PROJECT_ID}", project_id)

    print("Creating Silver products table...")

    run_query(bigquery_client, query)

    print("Silver products table created successfully")

def create_silver_orders(
    bigquery_client: bigquery.Client,
    project_id: str,
) -> None:
    """
    Create the Silver orders table using the SQL transformation.
    """

    sql_file = Path("sql/silver/orders.sql")

    query = sql_file.read_text(encoding="utf-8")

    query = query.replace("{PROJECT_ID}", project_id)

    print("Creating Silver orders table...")

    run_query(bigquery_client, query)

    print("Silver orders table created successfully")

def create_silver_order_items(
    bigquery_client: bigquery.Client,
    project_id: str,
) -> None:
    """
    Create the Silver order_items table using the SQL transformation.
    """

    sql_file = Path("sql/silver/order_items.sql")

    query = sql_file.read_text(encoding="utf-8")

    query = query.replace("{PROJECT_ID}", project_id)

    print("Creating Silver order_items table...")

    run_query(bigquery_client, query)

    print("Silver order_items table created successfully")