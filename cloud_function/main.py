import os

from google.cloud import bigquery
from google.cloud import storage


GCP_PROJECT_ID = os.environ["GCP_PROJECT_ID"]
GCS_BUCKET_NAME = os.environ["GCS_BUCKET_NAME"]
BQ_BRONZE_DATASET = os.environ["BQ_BRONZE_DATASET"]

GCS_PREFIX = "optimization_testing"

REQUIRED_FILES = {
    "customers": f"{GCS_PREFIX}/customers/customers.csv",
    "orders": f"{GCS_PREFIX}/orders/orders.csv",
    "products": f"{GCS_PREFIX}/products/products.csv",
    "order_items": f"{GCS_PREFIX}/order_items/order_items.csv",
}


def load_csv_to_bronze(
    bigquery_client: bigquery.Client,
    gcs_file_path: str,
    table_name: str,
) -> None:
    """Load a CSV file from GCS into a Bronze BigQuery table."""

    table_id = (
        f"{GCP_PROJECT_ID}."
        f"{BQ_BRONZE_DATASET}."
        f"{table_name}"
    )

    gcs_uri = f"gs://{GCS_BUCKET_NAME}/{gcs_file_path}"

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.CSV,
        skip_leading_rows=1,
        autodetect=True,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
    )

    load_job = bigquery_client.load_table_from_uri(
        gcs_uri,
        table_id,
        job_config=job_config,
    )

    load_job.result()

    print(f"Loaded {table_name} into {BQ_BRONZE_DATASET}")


def process_gcs_file(cloud_event) -> None:
    """Process GCS events and load the historical batch into Bronze."""

    bucket_name = cloud_event.data["bucket"]
    file_name = cloud_event.data["name"]

    print(f"File uploaded: gs://{bucket_name}/{file_name}")

    if bucket_name != GCS_BUCKET_NAME:
        print("Unexpected bucket. Ignoring event.")
        return

    if file_name.endswith("_SUCCESS"):
        print("Ignoring _SUCCESS marker.")
        return

    storage_client = storage.Client(
        project=GCP_PROJECT_ID
    )

    bucket = storage_client.bucket(GCS_BUCKET_NAME)

    success_blob = bucket.blob(
        f"{GCS_PREFIX}/_SUCCESS"
    )

    if success_blob.exists():
        print("Historical migration already completed.")
        return

    for table_name, gcs_file_path in REQUIRED_FILES.items():

        blob = bucket.blob(gcs_file_path)

        if not blob.exists():
            print(
                f"Waiting for {table_name}: "
                f"{gcs_file_path}"
            )
            return

    print("All required files are present.")

    bigquery_client = bigquery.Client(
        project=GCP_PROJECT_ID
    )

    for table_name, gcs_file_path in REQUIRED_FILES.items():

        load_csv_to_bronze(
            bigquery_client,
            gcs_file_path,
            table_name,
        )

    success_blob.upload_from_string(
        "Historical migration completed successfully."
    )

    print("Bronze loading completed.")
    print("Created _SUCCESS marker.")
    