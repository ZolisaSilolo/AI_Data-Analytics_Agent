import os
import json
import boto3
import logging
from time import time
from typing import Dict, Any

from core.data_handler import DataHandler
from core.visualizations import VisualizationGenerator
from nvidia_integration import NemotronAnalyzer

logger = logging.getLogger()
logger.setLevel(logging.INFO)

def validate_environment():
    """Validate required environment variables"""
    required_vars = ["NVIDIA_API_KEY", "DATA_BUCKET"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def lambda_handler(event, context):
    """AWS Lambda function handler"""
    start_time = time()
    
    try:
        validate_environment()
        
        if not event.get("body"):
            raise ValueError("Missing request body")
            
        body = json.loads(event.get("body"))
        user_query = body.get("query")
        if not user_query:
            raise ValueError("Missing query parameter")

        bucket_name = os.environ["DATA_BUCKET"]
        object_key = body.get("dataset_path", "datasets/my_data.csv")
        
        # Initialize components
        data_handler = DataHandler()
        viz_generator = VisualizationGenerator()
        analyzer = NemotronAnalyzer()
        
        # Load data
        df = data_handler.load_from_s3(bucket_name, object_key)
        
        # Generate analysis
        analysis_result = analyzer.analyze_data(df, user_query)
        
        # Generate visualization
        chart_type = body.get("chart_type", "histogram")
        x_column = body.get("x_column")
        y_column = body.get("y_column")
        
        chart_bytes = viz_generator.generate_chart(df, chart_type, x_column, y_column)
        
        # Save chart to S3
        chart_key = f"charts/chart_{context.aws_request_id}.png"
        chart_url = data_handler.save_to_s3(bucket_name, chart_key, chart_bytes, "image/png")
        
        response = {
            "analysis": analysis_result["analysis"],
            "chart_url": chart_url,
            "token_usage": analysis_result["token_usage"],
            "execution_time_seconds": time() - start_time
        }
        
        publish_metrics(time() - start_time, "success")
        
        return {
            "statusCode": 200,
            "body": json.dumps(response),
            "headers": {"Content-Type": "application/json"}
        }
        
    except ValueError as e:
        publish_metrics(time() - start_time, "invalid_input")
        return {
            "statusCode": 400, 
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        logger.error(f"Processing error: {str(e)}")
        publish_metrics(time() - start_time, "error")
        return {
            "statusCode": 500, 
            "body": json.dumps({"error": f"Processing failed: {str(e)}"}),
            "headers": {"Content-Type": "application/json"}
        }

def publish_metrics(duration: float, status: str):
    """
    Publish custom metrics to AWS CloudWatch
    
    Args:
        duration: Processing time in seconds
        status: Status of the processing (success, error, invalid_input, unexpected_error)
    """
    try:
        cloudwatch = boto3.client('cloudwatch')
        cloudwatch.put_metric_data(
            Namespace='PandasAnalyst',
            MetricData=[
                {
                    'MetricName': 'ProcessingTime',
                    'Value': duration * 1000,  # Convert to milliseconds
                    'Unit': 'Milliseconds',
                    'Dimensions': [
                        {
                            'Name': 'Status',
                            'Value': status
                        }
                    ]
                },
                {
                    'MetricName': 'Invocations',
                    'Value': 1,
                    'Unit': 'Count',
                    'Dimensions': [
                        {
                            'Name': 'Status',
                            'Value': status
                        }
                    ]
                }
            ]
        )
    except Exception as e:
        logger.error(f"Failed to publish metrics: {str(e)}")
        # Don't raise the exception as this is a non-critical operation