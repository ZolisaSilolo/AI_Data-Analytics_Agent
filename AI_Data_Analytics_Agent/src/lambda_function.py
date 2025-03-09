# Yes you must Import necessary modules
import os #.To interact with the operating system
import json  # To handle JSON data
import boto3  # AWS SDK for Python to interact with AWS services
import openai  # OpenAI API to interact with GPT-o1/o3 mini depending on your subscription of the OpanAI-API-Service
import pandas as pd  # Pandas library for data manipulation
import plotly.express as px  # Plotly Express for data visualization
import logging  # To log messages
from botocore.exceptions import ClientError  # To handle AWS client errors
from time import time  # To measure execution time

# First task is to set up the logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Then we are gonna initialise the AWS S3 client
s3_client = boto3.client('s3')

def validate_environment():
    """
    Validate that the required environment variables are set.
    Raises an EnvironmentError if any required environment variable is missing.
    """
    required_vars = ["OPENAI_API_KEY", "DATA_BUCKET"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def lambda_handler(event, context):
    """
    AWS Lambda function handler.
    Processes the incoming event, interacts with S3 and OpenAI, and returns a response.
    """
    start_time = time()
    try:
        # Validate environment variables
        validate_environment()
        openai.api_key = os.environ["OPENAI_API_KEY"]
        
        # Ensure the request body is present
        if not event.get("body"):
            raise ValueError("Missing request body")
            
        # Parse the request body
        body = json.loads(event.get("body"))
        user_query = body.get("query")
        if not user_query:
            raise ValueError("Missing query parameter")

        # Get the S3 bucket name and object key from environment and request body
        bucket_name = os.environ["DATA_BUCKET"]
        object_key = body.get("dataset_path", "datasets/my_data.csv")
        
        try:
            # Retrieve the CSV file from S3
            csv_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
            df = pd.read_csv(csv_obj['Body'])
        except ClientError as e:
            logger.error(f"S3 error: {str(e)}")
            return {"statusCode": 500, "body": json.dumps({"error": "Failed to load data"})}
        
        try:
            # Process the data and generate a summary and a chart
            summary = f"DataFrame has {len(df)} rows and columns: {list(df.columns)}."
            fig = px.histogram(df, x=df.columns[0])
            chart_bytes = fig.to_image(format="png")
            
            # Save the chart to S3
            chart_key = f"charts/chart_{context.aws_request_id}.png"
            s3_client.put_object(
                Bucket=bucket_name,
                Key=chart_key,
                Body=chart_bytes,
                ContentType='image/png'
            )
            
            # Prepare the response
            response = {
                "summary": summary,
                "chart_url": f"https://{bucket_name}.s3.amazonaws.com/{chart_key}"
            }
            
            # Afterwards-Record metrics for successful processing
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
    """
    Publish custom metrics to AWS CloudWatch.
    Records the processing time and status.
    """
    cloudwatch = boto3.client('cloudwatch')
    cloudwatch.put_metric_data(
        Namespace='PandasAnalyst',
        MetricData=[{
            'MetricName': 'ProcessingTime',
            'Value': duration,
            'Unit': 'Milliseconds'
        }]
    )
    #And voila, we are right at the end, feel free to pull issues and contribute to this wonderful project.