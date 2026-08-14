from google.cloud import bigquery

from python.src.config import (
    BQ_DATASET,
    GCP_PROJECT_ID,
    GCS_BUCKET_NAME,
)



def load_csv_from_gcs(
    client,
    gcs_file_path,
    table_name,
):
    table_id = f"{GCP_PROJECT_ID}.{BQ_DATASET}.{table_name}"

    uri = f"gs://{GCS_BUCKET_NAME}/{gcs_file_path}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = client.load_table_from_uri(
        uri,
        table_id,
        job_config=job_config,
    )

    load_job.result()

    print(f"Loaded {table_name} into {BQ_DATASET}")