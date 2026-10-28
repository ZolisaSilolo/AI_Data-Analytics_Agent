"""AWS-specific integrations and utilities."""

from typing import Dict, Any
import boto3
from botocore.config import Config
from botocore.exceptions import ClientError

class AWSClientFactory:
    """Factory for AWS service clients with proper configuration."""
    
    def __init__(self, region: str = 'us-east-1'):
        self.region = region
        self.config = Config(
            region_name=region,
            retries={
                'max_attempts': 3,
                'mode': 'standard'
            },
            connect_timeout=10,
            read_timeout=30
        )
        
    def get_bedrock_client(self):
        """Get Bedrock runtime client."""
        return boto3.client('bedrock-runtime', config=self.config)
    
    def get_s3_client(self):
        """Get S3 client."""
        return boto3.client('s3', config=self.config)
    
    def get_sqs_client(self):
        """Get SQS client."""
        return boto3.client('sqs', config=self.config)
    
    def get_dynamodb_client(self):
        """Get DynamoDB client."""
        return boto3.client('dynamodb', config=self.config)
    
    def get_lambda_client(self):
        """Get Lambda client."""
        return boto3.client('lambda', config=self.config)
    
    def get_cloudwatch_client(self):
        """Get CloudWatch client."""
        return boto3.client('cloudwatch', config=self.config)

__all__ = ['AWSClientFactory']