from python.src.bigquery.client import create_bigquery_client
from python.src.bigquery.silver.processor import silver_transformation
from python.src.bigquery.gold.processor import gold_transformation
from python.src.mysql_to_gcs_loading.load_to_gcs import load_tables_mysql_to_gcs

bigquery_client = create_bigquery_client()


print("\n==================================================================")
print("              MySql legacy database to GCS loading")
print("==================================================================")

load_tables_mysql_to_gcs()

# ==================================================================
# 2         GCS to bronze loading handles the cloud function
# ==================================================================


print("\n==================================================================")
print("              bronze to silver transformation")
print("==================================================================")

silver_transformation( bigquery_client)  

print("\n==================================================================")
print("               silver to gold transformation   ")
print("==================================================================")


gold_transformation( bigquery_client )