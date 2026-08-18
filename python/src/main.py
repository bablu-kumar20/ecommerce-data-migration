from python.src.mysql_to_gcs_loading.database.connection import create_mysql_connection, get_tables
from python.src.mysql_to_gcs_loading.extraction.extractor import extract_table
from python.src.mysql_to_gcs_loading.gcs.client import create_gcs_client
from python.src.mysql_to_gcs_loading.gcs.uploader import upload_dataframe_as_csv
from python.src.bigquery.client import create_bigquery_client
from python.src.config import GCP_PROJECT_ID
from python.src.bigquery.loader import load_csv_from_gcs

from python.src.bigquery.processor import silver_transformation
from python.src.bigquery.get_tables import get_bronze_tables

GCS_RAW_PREFIX = "optimization_testing"


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
        print(f"DEBUG PREFIX: {GCS_RAW_PREFIX}")
        print(f"DEBUG PATH: {gcs_file_path}")
        upload_dataframe_as_csv(
            gcs_client,
            dataframe,
            gcs_file_path,
        )
        
        load_csv_from_gcs(
        bigquery_client,
        gcs_file_path,
        table,
        )

        print(f"Completed: {table} ({len(dataframe)} rows)")
        

# silver optimization
print("Starting Silver transformation...")

# fetch all the tables form bronze layer / bronze_dataset
tables = get_bronze_tables( bigquery_client )

"""
get_bronze_tables() returns the table in order : ['order_items', 'products', 'orders', 'customers']
we need in order : ['orders', 'products', 'order_items', 'customers']
because in our silver transformation order_items rely on orders table hence 
i changed the table sequence

"""

tables = ['orders', 'products', 'order_items', 'customers']
for table in tables :
    silver_transformation(  bigquery_client,  GCP_PROJECT_ID, table )  
    
print("Silver transformation is completed.")

mysql_connection.close()