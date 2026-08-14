import io

from python.src.config import GCS_BUCKET_NAME


def upload_dataframe_as_csv(client, dataframe, gcs_file_path):
    bucket = client.bucket(GCS_BUCKET_NAME)
    blob = bucket.blob(gcs_file_path)

    csv_buffer = io.StringIO()
    dataframe.to_csv(csv_buffer, index=False)

    blob.upload_from_string(
        csv_buffer.getvalue(),
        content_type="text/csv",
    )

    print(f"Uploaded: gs://{GCS_BUCKET_NAME}/{gcs_file_path}")