import unittest
from unittest.mock import patch

from python.src.bigquery import client as client_module


class BigQueryClientTests(unittest.TestCase):
    def setUp(self):
        client_module.create_bigquery_client.cache_clear()

    def tearDown(self):
        client_module.create_bigquery_client.cache_clear()

    def test_client_is_created_once_and_reused(self):
        expected_client = object()
        credentials = object()

        with (
            patch.object(
                client_module.service_account.Credentials,
                "from_service_account_file",
                return_value=credentials,
            ) as credentials_loader,
            patch.object(
                client_module.bigquery,
                "Client",
                return_value=expected_client,
            ) as client_constructor,
        ):
            first_client = client_module.create_bigquery_client()
            second_client = client_module.create_bigquery_client()

        self.assertIs(first_client, expected_client)
        self.assertIs(second_client, expected_client)
        credentials_loader.assert_called_once_with(client_module.GCP_CREDENTIALS_FILE)
        client_constructor.assert_called_once_with(
            project=client_module.GCP_PROJECT_ID,
            credentials=credentials,
        )


if __name__ == "__main__":
    unittest.main()
