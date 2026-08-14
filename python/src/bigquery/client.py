from google.cloud import bigquery
from google.oauth2 import service_account

from python.src.config import GCP_PROJECT_ID, GCP_CREDENTIALS_FILE

def create_bigquery_client():
    credentials = service_account.Credentials.from_service_account_file(
        GCP_CREDENTIALS_FILE
    )

    client = bigquery.Client(
        project=GCP_PROJECT_ID,
        credentials=credentials,
    )

    return client