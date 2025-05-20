import os
import json
import pandas as pd
import boto3
from langchain.llms import OpenAI
from langchain.agents import create_pandas_dataframe_agent
from langchain.callbacks import get_openai_callback
from langchain.tools import PythonAstREPLTool
import logging
from typing import Dict, Any, Optional, Union
import time

logger = logging.getLogger(__name__)

class PandasAnalystChain:
    def __init__(self, openai_api_key: Optional[str] = None):
        """
        Initialize the PandasAnalystChain with OpenAI API key and S3 client
        
        Args:
            openai_api_key: OpenAI API key (optional, will use environment variable if not provided)
        """
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        if not self.openai_api_key:
            raise ValueError("OpenAI API key is required. Set OPENAI_API_KEY environment variable or pass it to the constructor.")
        
        self.s3_client = boto3.client('s3')
        
    def load_data(self, bucket_name: str, object_key: str) -> pd.DataFrame:
        """
        Load DataFrame from S3
        
        Args:
            bucket_name: S3 bucket name
            object_key: S3 object key (path to file)
            
        Returns:
            pandas DataFrame loaded from S3
            
        Raises:
            Exception: If loading data fails
        """
        try:
            logger.info(f"Loading data from s3://{bucket_name}/{object_key}")
            csv_obj = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            return pd.read_csv(csv_obj['Body'])
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise

    def create_agent(self, df: pd.DataFrame):
        """
        Create LangChain Pandas agent
        
        Args:
            df: pandas DataFrame to analyze
            
        Returns:
            LangChain agent for pandas DataFrame analysis
        """
        llm = OpenAI(
            temperature=0.2,
            openai_api_key=self.openai_api_key,
            model_name="gpt-3.5-turbo"
        )
        return create_pandas_dataframe_agent(
            llm,
            df,
            verbose=True,
            extra_tools=[PythonAstREPLTool()]
        )

    def process_query(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """
        Process user query using the agent
        
        Args:
            df: pandas DataFrame to analyze
            query: User query string
            
        Returns:
            Dictionary containing response and token usage
            
        Raises:
            Exception: If agent execution fails
        """
        start_time = time.time()
        agent = self.create_agent(df)
        
        with get_openai_callback() as cb:
            try:
                response = agent.run(query)
                processing_time = time.time() - start_time
                
                logger.info(f"Query processed in {processing_time:.2f} seconds")
                logger.info(f"Token usage: {cb.total_tokens}")
                
                return {
                    "response": response,
                    "token_usage": cb.total_tokens,
                    "processing_time_seconds": processing_time
                }
            except Exception as e:
                logger.error(f"Agent execution failed: {str(e)}")
                raise
    
    def save_result_to_s3(self, bucket_name: str, result: Dict[str, Any], request_id: str) -> str:
        """
        Save analysis result to S3
        
        Args:
            bucket_name: S3 bucket name
            result: Analysis result to save
            request_id: Unique request ID
            
        Returns:
            S3 object key where result was saved
        """
        try:
            result_key = f"results/analysis_{request_id}.json"
            self.s3_client.put_object(
                Bucket=bucket_name,
                Key=result_key,
                Body=json.dumps(result),
                ContentType='application/json'
            )
            return result_key
        except Exception as e:
            logger.error(f"Failed to save result to S3: {str(e)}")
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
    try:
        # Initialize the chain
        chain = PandasAnalystChain()
        
        # Parse request body
        body = json.loads(event.get("body", "{}"))
        user_query = body.get("query", "Show me some data analysis")
        
        # Get S3 bucket and object key
        bucket_name = os.environ.get("DATA_BUCKET")
        if not bucket_name:
            raise ValueError("DATA_BUCKET environment variable is not set")
            
        object_key = body.get("dataset_path", "datasets/my_data.csv")

        # Load data and process query
        df = chain.load_data(bucket_name, object_key)
        result = chain.process_query(df, user_query)
        
        # Save result to S3 if requested
        if body.get("save_result", False):
            result_key = chain.save_result_to_s3(bucket_name, result, context.aws_request_id)
            result["result_location"] = f"s3://{bucket_name}/{result_key}"

        return {
            "statusCode": 200,
            "body": json.dumps(result),
            "headers": {"Content-Type": "application/json"}
        }
    except ValueError as e:
        logger.error(f"Value error: {str(e)}")
        return {
            "statusCode": 400,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }