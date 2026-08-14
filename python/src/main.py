# from database.connection import (
#     create_mysql_connection,
#     get_tables,
#     get_table_row_count,
# )
# connection = create_mysql_connection()

# if connection.is_connected():
#     print("MySQL connection successful")

#     tables = get_tables(connection)

#     print("Tables found:")
#     for table in tables:
#         row_count = get_table_row_count(connection, table)
#         print(f"- {table}: {row_count} rows")

# connection.close()
from python.src.mysql_to_gcs_loading.database.connection import create_mysql_connection, get_tables
from python.src.mysql_to_gcs_loading.extraction.extractor import extract_table
from python.src.mysql_to_gcs_loading.gcs.client import create_gcs_client
from python.src.mysql_to_gcs_loading.gcs.uploader import upload_dataframe_as_csv

from python.src.bigquery.client import create_bigquery_client
from python.src.bigquery.loader import load_csv_from_gcs


GCS_RAW_PREFIX = "RAW"


mysql_connection = create_mysql_connection()
gcs_client = create_gcs_client()
bigquery_client = create_bigquery_client()

if mysql_connection.is_connected():
    print("MySQL connection successful")

    tables = get_tables(mysql_connection)

    for table in tables:
        print(f"Extracting table: {table}")

        dataframe = extract_table(mysql_connection, table)

        gcs_file_path = f"{GCS_RAW_PREFIX}/{table}/{table}.csv"

        upload_dataframe_as_csv(
            gcs_client,
            dataframe,
            gcs_file_path,
        )

        load_csv_from_gcs(
            bigquery_client,
            gcs_file_path,
            table
        )

        print(f"Completed: {table} ({len(dataframe)} rows)")

mysql_connection.close()