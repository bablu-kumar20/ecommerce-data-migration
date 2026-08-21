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