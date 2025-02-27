import os
import json
import boto3
import openai
import pandas as pd
import plotly.express as px
import logging
from botocore.exceptions import ClientError
from time import time

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS clients
s3_client = boto3.client('s3')

def validate_environment():
    required_vars = ["OPENAI_API_KEY", "DATA_BUCKET"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def lambda_handler(event, context):
    start_time = time()
    try:
        validate_environment()
        openai.api_key = os.environ["OPENAI_API_KEY"]
        
        if not event.get("body"):
            raise ValueError("Missing request body")
            
        body = json.loads(event.get("body"))
        user_query = body.get("query")
        if not user_query:
            raise ValueError("Missing query parameter")

        bucket_name = os.environ["DATA_BUCKET"]
        object_key = body.get("dataset_path", "datasets/my_data.csv")
        
        try:
            csv_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            df = pd.read_csv(csv_obj['Body'])
        except ClientError as e:
            logger.error(f"S3 error: {str(e)}")
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to load data"})}
            
        try:
            # Process the data
            summary = f"DataFrame has {len(df)} rows and columns: {list(df.columns)}."
            fig = px.histogram(df, x=df.columns[0])
            chart_bytes = fig.to_image(format="png")
            
            chart_key = f"charts/chart_{context.aws_request_id}.png"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=chart_key,
                Body=chart_bytes,
                ContentType='image/png'
            )
            
            response = {
                "summary": summary,
                "chart_url": f"https://{bucket_name}.s3.amazonaws.com/{chart_key}"
            }
            
            # Record metrics
            publish_metrics(time() - start_time, "success")
            
            return {
                "statusCode": 200,
                "body": json.dumps(response),
                "headers": {"Content-Type": "application/json"}
            }
            
        except Exception as e:
            logger.error(f"Processing error: {str(e)}")
            publish_metrics(time() - start_time, "error")
            return {"statusCode": 500, "body": json.dumps({"error": "Processing failed"})}
            
    except ValueError as e:
        publish_metrics(time() - start_time, "invalid_input")
        return {"statusCode": 400, "body": json.dumps({"error": str(e)})}

def publish_metrics(duration, status):
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='PandasAnalyst',
        MetricData=[{
            'MetricName': 'ProcessingTime',
            'Value': duration,
            'Unit': 'Milliseconds'
        }]
    )