"""Configuration module for application settings and environment variables."""

import os
from typing import Dict, Any

class Config:
    """Application configuration."""
    
    def __init__(self):
        self.aws_region = os.getenv('AWS_REGION', 'us-east-1')
        self.bedrock_primary_model = os.getenv('BEDROCK_PRIMARY_MODEL', 'global.moonshotai.kimi-k3')
        self.bedrock_fallback_model = os.getenv('BEDROCK_FALLBACK_MODEL', 'global.moonshotai.kimi-k3')
        
        # Lambda settings
        self.lambda_timeout = int(os.getenv('LAMBDA_TIMEOUT', '300'))
        self.lambda_memory_size = int(os.getenv('LAMBDA_MEMORY_SIZE', '1024'))
        
        # Database settings
        self.max_connections = int(os.getenv('MAX_CONNECTIONS', '100'))
        
        # API settings
        self.api_timeout = int(os.getenv('API_TIMEOUT', '30'))
        self.max_file_size = int(os.getenv('MAX_FILE_SIZE', '10485760'))  # 10MB
        
    def to_dict(self) -> Dict[str, Any]:
        """Return configuration as dictionary."""
        return {
            'aws_region': self.aws_region,
            'bedrock_primary_model': self.bedrock_primary_model,
            'bedrock_fallback_model': self.bedrock_fallback_model,
            'lambda_timeout': self.lambda_timeout,
            'lambda_memory_size': self.lambda_memory_size,
            'max_connections': self.max_connections,
            'api_timeout': self.api_timeout,
            'max_file_size': self.max_file_size
        }

config = Config()
__all__ = ['config', 'Config']