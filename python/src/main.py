from python.src.bigquery.client import create_bigquery_client
from python.src.bigquery.get_tables import get_bronze_tables
from python.src.bigquery.loader import load_csv_from_gcs
from python.src.bigquery.processor import (
    gold_transformation,
    ml_transformation,
    silver_transformation,
)
from python.src.config import (
    BQML_TRAINING_ENABLED,
    BQ_ML_DATASET,
    GCP_PROJECT_ID,
    POST_PIPELINE_MONITOR_ENABLED,
)
from python.src.mysql_to_gcs_loading.database.connection import (
    create_mysql_connection,
    get_tables,
)
from python.src.mysql_to_gcs_loading.extraction.extractor import extract_table
from python.src.mysql_to_gcs_loading.gcs.client import create_gcs_client
from python.src.mysql_to_gcs_loading.gcs.uploader import upload_dataframe_as_csv
from python.src.pipeline_monitor import (
    record_pipeline_failure,
    run_post_pipeline_monitor,
)


GCS_RAW_PREFIX = "Anurag/raw"
SILVER_TABLES = ["orders", "products", "order_items", "customers"]
GOLD_TABLES = [
    "sales",
    "product_performance",
    "customer_sales",
    "daily_sales",
    "sales_summary",
]


def run_pipeline() -> None:
    """Run the ecommerce ETL pipeline and its configured post-run triggers."""
    stage = "initialization"
    mysql_connection = None

    try:
        mysql_connection = create_mysql_connection()
        gcs_client = create_gcs_client()
        bigquery_client = create_bigquery_client()

        if not mysql_connection.is_connected():
            raise RuntimeError("MySQL connection was not established.")
        print("MySQL connection successful")

        stage = "mysql_to_gcs_and_staging"
        for table in get_tables(mysql_connection):
            print(f"Extracting table: {table}")
            dataframe = extract_table(mysql_connection, table)
            gcs_file_path = f"{GCS_RAW_PREFIX}/{table}/{table}.csv"

            upload_dataframe_as_csv(gcs_client, dataframe, gcs_file_path)
            load_csv_from_gcs(
                bigquery_client,
                gcs_file_path,
                table,
            )
            print(f"Completed: {table} ({len(dataframe)} rows)")

        stage = "silver_transformations"
        print("Starting Silver transformation...")
        get_bronze_tables(bigquery_client)
        for table in SILVER_TABLES:
            silver_transformation(bigquery_client, GCP_PROJECT_ID, table)
        print("Silver transformation is completed.")

        stage = "gold_transformations"
        print("Starting Gold transformation...")
        for table in GOLD_TABLES:
            gold_transformation(bigquery_client, GCP_PROJECT_ID, table)
        print("Gold transformation is completed.")

        if BQML_TRAINING_ENABLED:
            stage = "bigquery_ml_training"
            ml_transformation(
                bigquery_client,
                GCP_PROJECT_ID,
                BQ_ML_DATASET,
                "create_ml_dataset",
            )
            ml_transformation(
                bigquery_client,
                GCP_PROJECT_ID,
                BQ_ML_DATASET,
                "create_daily_revenue_forecast_model",
            )

        if POST_PIPELINE_MONITOR_ENABLED:
            stage = "post_pipeline_monitor"
            run_post_pipeline_monitor()

    except Exception as error:
        try:
            record_pipeline_failure(stage, error)
        except Exception:
            pass
        raise
    finally:
        if mysql_connection is not None and mysql_connection.is_connected():
            mysql_connection.close()


if __name__ == "__main__":
    run_pipeline()
