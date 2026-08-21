import unittest
from unittest.mock import Mock, patch

from python.src import main


class MainPipelineTests(unittest.TestCase):
    def _base_patches(self):
        connection = Mock()
        connection.is_connected.return_value = True
        patches = {
            "connection": connection,
            "mysql": patch.object(main, "create_mysql_connection", return_value=connection),
            "gcs": patch.object(main, "create_gcs_client", return_value=Mock()),
            "bq": patch.object(main, "create_bigquery_client", return_value=Mock()),
            "tables": patch.object(main, "get_tables", return_value=["products"]),
            "extract": patch.object(main, "extract_table", return_value=[{"id": 1}]),
            "upload": patch.object(main, "upload_dataframe_as_csv"),
            "load": patch.object(main, "load_csv_from_gcs"),
            "bronze": patch.object(main, "get_bronze_tables", return_value=[]),
            "silver": patch.object(main, "silver_transformation"),
            "gold": patch.object(main, "gold_transformation"),
            "ml": patch.object(main, "ml_transformation"),
            "monitor": patch.object(main, "run_post_pipeline_monitor"),
            "failure": patch.object(main, "record_pipeline_failure"),
        }
        return patches

    def test_successful_pipeline_runs_post_gold_monitor(self):
        patches = self._base_patches()
        with (
            patches["mysql"],
            patches["gcs"],
            patches["bq"],
            patches["tables"],
            patches["extract"],
            patches["upload"],
            patches["load"],
            patches["bronze"],
            patches["silver"] as silver,
            patches["gold"] as gold,
            patches["ml"] as ml,
            patches["monitor"] as monitor,
            patches["failure"] as failure,
            patch.object(main, "SILVER_TABLES", ["orders"]),
            patch.object(main, "GOLD_TABLES", ["sales"]),
            patch.object(main, "BQML_TRAINING_ENABLED", False),
            patch.object(main, "POST_PIPELINE_MONITOR_ENABLED", True),
        ):
            main.run_pipeline()

        silver.assert_called_once()
        gold.assert_called_once()
        ml.assert_not_called()
        monitor.assert_called_once_with()
        failure.assert_not_called()
        patches["connection"].close.assert_called_once_with()

    def test_ml_training_is_explicitly_flagged(self):
        patches = self._base_patches()
        with (
            patches["mysql"],
            patches["gcs"],
            patches["bq"],
            patches["tables"],
            patches["extract"],
            patches["upload"],
            patches["load"],
            patches["bronze"],
            patches["silver"],
            patches["gold"],
            patches["ml"] as ml,
            patches["monitor"],
            patches["failure"],
            patch.object(main, "SILVER_TABLES", []),
            patch.object(main, "GOLD_TABLES", []),
            patch.object(main, "BQML_TRAINING_ENABLED", True),
            patch.object(main, "POST_PIPELINE_MONITOR_ENABLED", False),
        ):
            main.run_pipeline()

        self.assertEqual(ml.call_count, 2)
        self.assertEqual(
            [item.args[3] for item in ml.call_args_list],
            ["create_ml_dataset", "create_daily_revenue_forecast_model"],
        )

    def test_failure_trigger_records_stage_and_closes_connection(self):
        patches = self._base_patches()
        error = RuntimeError("upload failed")
        with (
            patches["mysql"],
            patches["gcs"],
            patches["bq"],
            patches["tables"],
            patches["extract"],
            patch.object(main, "upload_dataframe_as_csv", side_effect=error),
            patches["load"],
            patches["bronze"],
            patches["silver"],
            patches["gold"],
            patches["ml"],
            patches["monitor"],
            patches["failure"] as failure,
        ):
            with self.assertRaisesRegex(RuntimeError, "upload failed"):
                main.run_pipeline()

        failure.assert_called_once_with("mysql_to_gcs_and_staging", error)
        patches["connection"].close.assert_called_once_with()


if __name__ == "__main__":
    unittest.main()
