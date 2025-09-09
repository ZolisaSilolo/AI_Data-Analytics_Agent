import os
import json
import boto3
import openai
import pandas as pd
import plotly.express as px
import logging
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from botocore.exceptions import ClientError
from time import time
from typing import Dict, Any, List, Optional, Union

# Set up logging
logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialize AWS S3 client
s3_client = boto3.client('s3')

def validate_environment():
    """
    Validate that the required environment variables are set.
    
    Raises:
        EnvironmentError: If any required environment variable is missing
    """
    required_vars = ["OPENAI_API_KEY", "DATA_BUCKET"]
    missing = [var for var in required_vars if not os.environ.get(var)]
    if missing:
        raise EnvironmentError(f"Missing required environment variables: {', '.join(missing)}")

def load_data_from_s3(bucket_name: str, object_key: str) -> pd.DataFrame:
    """
    Load data from S3 into a pandas DataFrame
    
    Args:
        bucket_name: S3 bucket name
        object_key: S3 object key (path to file)
        
    Returns:
        pandas DataFrame loaded from S3
        
    Raises:
        ClientError: If S3 operation fails
    """
    try:
        csv_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        return pd.read_csv(csv_obj['Body'])
    except ClientError as e:
        logger.error(f"S3 error: {str(e)}")
        raise

def generate_visualization(df: pd.DataFrame, chart_type: str = "histogram", 
                          x_column: Optional[str] = None, 
                          y_column: Optional[str] = None) -> bytes:
    """
    Generate visualization based on the specified chart type
    
    Args:
        df: pandas DataFrame containing the data
        chart_type: Type of chart to generate (histogram, bar, scatter, line, heatmap)
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        
    Returns:
        Bytes of the generated chart image
        
    Raises:
        ValueError: If invalid chart type or missing required columns
    """
    # Use first column if x_column not specified
    if not x_column and len(df.columns) > 0:
        x_column = df.columns[0]
    
    # Use second column if y_column not specified and chart requires it
    if not y_column and len(df.columns) > 1 and chart_type in ["scatter", "line", "bar"]:
        y_column = df.columns[1]
    
    if chart_type == "histogram":
        fig = px.histogram(df, x=x_column, title=f"Histogram of {x_column}")
    elif chart_type == "bar":
        if not y_column:
            raise ValueError("y_column is required for bar chart")
        fig = px.bar(df, x=x_column, y=y_column, title=f"Bar Chart: {y_column} by {x_column}")
    elif chart_type == "scatter":
        if not y_column:
            raise ValueError("y_column is required for scatter plot")
        fig = px.scatter(df, x=x_column, y=y_column, title=f"Scatter Plot: {y_column} vs {x_column}")
    elif chart_type == "line":
        if not y_column:
            raise ValueError("y_column is required for line chart")
        fig = px.line(df, x=x_column, y=y_column, title=f"Line Chart: {y_column} over {x_column}")
    elif chart_type == "heatmap":
        # For heatmap, use seaborn and matplotlib
        plt.figure(figsize=(10, 8))
        numeric_df = df.select_dtypes(include=['number'])
        if numeric_df.empty:
            raise ValueError("No numeric columns available for heatmap")
        
        corr = numeric_df.corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f")
        plt.title("Correlation Heatmap")
        
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        plt.close()
        buf.seek(0)
        return buf.getvalue()
    else:
        raise ValueError(f"Unsupported chart type: {chart_type}")
    
    return fig.to_image(format="png")

def save_to_s3(bucket_name: str, key: str, data: bytes, content_type: str) -> str:
    """
    Save data to S3
    
    Args:
        bucket_name: S3 bucket name
        key: S3 object key
        data: Data to save
        content_type: Content type of the data
        
    Returns:
        URL of the saved object
        
    Raises:
        ClientError: If S3 operation fails
    """
    s3_client.put_object(
        Bucket=bucket_name,
        Key=key,
        Body=data,
        ContentType=content_type
    )
    return f"https://{bucket_name}.s3.amazonaws.com/{key}"

def analyze_data(df: pd.DataFrame, query: str) -> Dict[str, Any]:
    """
    Analyze data using OpenAI API
    
    Args:
        df: pandas DataFrame to analyze
        query: User query about the data
        
    Returns:
        Dictionary containing analysis results
        
    Raises:
        Exception: If OpenAI API call fails
    """
    # Prepare data summary for OpenAI
    data_summary = f"DataFrame has {len(df)} rows and {len(df.columns)} columns: {', '.join(df.columns)}.\n"
    data_summary += f"Sample data (first 5 rows):\n{df.head().to_string()}\n"
    data_summary += f"Data types:\n{df.dtypes.to_string()}\n"
    data_summary += f"Summary statistics:\n{df.describe().to_string()}\n"
    
    # Prepare the prompt
    prompt = f"""
    You are a data analyst expert. Analyze the following data and answer the query.
    
    DATA SUMMARY:
    {data_summary}
    
    USER QUERY:
    {query}
    
    Provide a detailed analysis with insights and recommendations. Include Python code snippets that could be used to perform this analysis.
    """
    
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": "You are a data analysis expert."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=1500
        )
        
        analysis = response.choices[0].message.content
        return {
            "analysis": analysis,
            "token_usage": response.usage.total_tokens
        }
    except Exception as e:
        logger.error(f"OpenAI API error: {str(e)}")
        raise

def lambda_handler(event, context):
    """
    AWS Lambda function handler
    
    Args:
        event: Lambda event
        context: Lambda context
        
    Returns:
        API Gateway response
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

        # Get the S3 bucket name and object key
        bucket_name = os.environ["DATA_BUCKET"]
        object_key = body.get("dataset_path", "datasets/my_data.csv")
        
        # Load data from S3
        try:
            df = load_data_from_s3(bucket_name, object_key)
        except ClientError:
            return {
                "statusCode": 500, 
                "body": json.dumps({"error": "Failed to load data from S3"}),
                "headers": {"Content-Type": "application/json"}
            }
        
        try:
            # Generate analysis
            analysis_result = analyze_data(df, user_query)
            
            # Generate visualization
            chart_type = body.get("chart_type", "histogram")
            x_column = body.get("x_column", df.columns[0] if len(df.columns) > 0 else None)
            y_column = body.get("y_column")
            
            chart_bytes = generate_visualization(df, chart_type, x_column, y_column)
            
            # Save chart to S3
            chart_key = f"charts/chart_{context.aws_request_id}.png"
            chart_url = save_to_s3(bucket_name, chart_key, chart_bytes, "image/png")
            
            # Prepare response
            response = {
                "analysis": analysis_result["analysis"],
                "chart_url": chart_url,
                "token_usage": analysis_result["token_usage"],
                "execution_time_seconds": time() - start_time
            }
            
            # Record metrics for successful processing
            publish_metrics(time() - start_time, "success")
            
            return {
                "statusCode": 200,
                "body": json.dumps(response),
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
        
    except ValueError as e:
        publish_metrics(time() - start_time, "invalid_input")
        return {
            "statusCode": 400, 
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        publish_metrics(time() - start_time, "unexpected_error")
        return {
            "statusCode": 500, 
            "body": json.dumps({"error": f"Unexpected error: {str(e)}"}),
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