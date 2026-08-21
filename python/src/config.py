import os
from dotenv import load_dotenv

load_dotenv()

MYSQL_HOST = os.getenv("MYSQL_HOST")
MYSQL_PORT = os.getenv("MYSQL_PORT")
MYSQL_DATABASE = os.getenv("MYSQL_DATABASE")
MYSQL_USER = os.getenv("MYSQL_USER")
MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD")

GCP_PROJECT_ID = os.getenv("GCP_PROJECT_ID")
GCP_CREDENTIALS_FILE = os.getenv("GCP_CREDENTIALS_FILE")
GCS_BUCKET_NAME = os.getenv("GCS_BUCKET_NAME")
BQ_DATASET = os.getenv("BQ_DATASET")
BQ_SILVER_DATASET = os.getenv("BQ_SILVER_DATASET")
BQ_GOLD_DATASET = os.getenv("BQ_GOLD_DATASET", "ecommerce_gold")
BQ_ML_DATASET = os.getenv("BQ_ML_DATASET", "ecommerce_ml")

POST_PIPELINE_MONITOR_ENABLED = (
    os.getenv("POST_PIPELINE_MONITOR_ENABLED", "TRUE").upper() == "TRUE"
)
BQML_TRAINING_ENABLED = (
    os.getenv("BQML_TRAINING_ENABLED", "FALSE").upper() == "TRUE"
)

