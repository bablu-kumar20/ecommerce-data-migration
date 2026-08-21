from sqlalchemy import text
from python.src.mysql_to_gcs_loading.database.connection import create_mysql_connection
from python.src.mysql_to_gcs_loading.database.extractor import extract_table
from python.src.mysql_to_gcs_loading.gcs.client import create_gcs_client
from python.src.mysql_to_gcs_loading.gcs.uploader import upload_dataframe_as_csv


mysql_engine = create_mysql_connection()
gcs_client = create_gcs_client()

GCS_RAW_PREFIX = "testing"


def get_tables(engine):
    with engine.connect() as connection:
        result = connection.execute(text("SHOW TABLES"))

        tables = [row[0] for row in result]

    return tables


def load_tables_mysql_to_gcs():

    try:
        with mysql_engine.connect() as connection:
            connection.execute(text("SELECT 1"))

        print("MySQL connection successful")

    except Exception as e:
        print(f"MySQL connection failed: {e}")
        return

    tables = get_tables(mysql_engine)

    for table in tables:
        print(f"\nExtracting table: {table}")

        csv_data = extract_table(mysql_engine, table)

        gcs_file_path = f"{GCS_RAW_PREFIX}/{table}/{table}.csv"

        upload_dataframe_as_csv(
            gcs_client,
            csv_data,
            gcs_file_path,
        )

        print(f"Completed: {table} (XXX rows)")