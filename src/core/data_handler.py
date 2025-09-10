import boto3
import pandas as pd
import logging
from botocore.exceptions import ClientError
from typing import Optional

logger = logging.getLogger(__name__)

class DataHandler:
    """Unified data loading and S3 operations"""
    
    def __init__(self):
        self.s3_client = boto3.client('s3')
    
    def load_from_s3(self, bucket_name: str, object_key: str) -> pd.DataFrame:
        """Load data from S3 into pandas DataFrame"""
        try:
            csv_obj = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            return pd.read_csv(csv_obj['Body'])
        except ClientError as e:
            logger.error(f"S3 error: {str(e)}")
            raise
    
    def save_to_s3(self, bucket_name: str, key: str, data: bytes, content_type: str) -> str:
        """Save data to S3"""
        self.s3_client.put_object(
            Bucket=bucket_name,
            Key=key,
            Body=data,
            ContentType=content_type
        )
        return f"https://{bucket_name}.s3.amazonaws.com/{key}"
