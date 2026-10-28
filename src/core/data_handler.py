"""
High-Performance Unified Data Handler.

Loads CSV, Parquet and Excel from S3 with zero-copy/PyArrow acceleration. Heavy
optional engines (polars, pyarrow.parquet) are imported lazily so Lambda cold
starts only pay for the path actually used.
"""

from __future__ import annotations

import io
import logging
from typing import Optional, Union

import boto3
import pandas as pd
from botocore.config import Config
from botocore.exceptions import ClientError

logger = logging.getLogger(__name__)

_BOTO_CONFIG = Config(
    retries={"max_attempts": 3, "mode": "standard"},
    connect_timeout=3,
    read_timeout=30,
)


class DataHandler:
    """Enterprise-grade data ingestion and S3 Lakehouse persistence."""

    def __init__(self, s3_client: Optional[boto3.client] = None):
        self.s3_client = s3_client or boto3.client("s3", config=_BOTO_CONFIG)

    def load_from_s3(self, bucket_name: str, object_key: str) -> pd.DataFrame:
        """Load a CSV, Parquet or Excel object from S3 into a DataFrame."""
        try:
            resp = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            body = resp["Body"].read()
        except ClientError as exc:
            logger.error("Failed to load s3://%s/%s: %s", bucket_name, object_key, exc)
            raise

        if object_key.endswith(".parquet"):
            import pyarrow.parquet as pq

            table = pq.read_table(io.BytesIO(body))
            return table.to_pandas()
        if object_key.endswith((".xls", ".xlsx")):
            return pd.read_excel(io.BytesIO(body))
        try:
            return pd.read_csv(io.BytesIO(body), engine="pyarrow")
        except (ImportError, ValueError):
            return pd.read_csv(io.BytesIO(body))

    def save_to_s3(
        self,
        bucket_name: str,
        key: str,
        data: Union[bytes, str, pd.DataFrame],
        content_type: str = "application/octet-stream",
    ) -> str:
        """Persist a data artifact to the lakehouse with SSE encryption."""
        if isinstance(data, pd.DataFrame):
            buf = io.BytesIO()
            data.to_parquet(buf, index=False)
            data_bytes = buf.getvalue()
            content_type = "application/x-parquet"
        elif isinstance(data, str):
            data_bytes = data.encode("utf-8")
        else:
            data_bytes = data

        try:
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=key,
                Body=data_bytes,
                ContentType=content_type,
                ServerSideEncryption="AES256",
            )
        except ClientError as exc:
            logger.error("Failed to save s3://%s/%s: %s", bucket_name, key, exc)
            raise
        return f"s3://{bucket_name}/{key}"
