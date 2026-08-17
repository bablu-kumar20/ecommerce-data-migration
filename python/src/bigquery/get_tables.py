from python.src.config import GCP_PROJECT_ID, BQ_DATASET


def get_bronze_tables(bigquery_client ):
    query = f"""
        SELECT table_name
        FROM `{GCP_PROJECT_ID}.{BQ_DATASET}.INFORMATION_SCHEMA.TABLES`
        WHERE table_type = 'BASE TABLE'
    """

    query_job = bigquery_client.query(query)

    return [row.table_name for row in query_job.result()]