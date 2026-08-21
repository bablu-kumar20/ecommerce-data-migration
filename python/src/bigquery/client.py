import logging
from functools import lru_cache
from time import perf_counter

from google.cloud import bigquery
from google.oauth2 import service_account

from python.src.config import GCP_PROJECT_ID, GCP_CREDENTIALS_FILE


LOGGER = logging.getLogger(__name__)


@lru_cache(maxsize=1)
def create_bigquery_client() -> bigquery.Client:
    """Create one reusable authenticated BigQuery client per process."""
    started_at = perf_counter()
    credentials = service_account.Credentials.from_service_account_file(
        GCP_CREDENTIALS_FILE
    )

    client = bigquery.Client(
        project=GCP_PROJECT_ID,
        credentials=credentials,
    )

    LOGGER.info(
        "Created reusable BigQuery client in %.2f seconds.",
        perf_counter() - started_at,
    )
    return client
