import os
import json
import pandas as pd
import boto3
from langchain.llms import OpenAI
from langchain.agents import create_pandas_dataframe_agent
from langchain.callbacks import get_openai_callback
from langchain.tools import PythonAstREPLTool
import logging

logger = logging.getLogger(__name__)

class PandasAnalystChain:
    def __init__(self, openai_api_key=None):
        self.openai_api_key = openai_api_key or os.environ.get("OPENAI_API_KEY")
        self.s3_client = boto3.client('s3')
        
    def load_data(self, bucket_name, object_key):
        """Load DataFrame from S3"""
        try:
            csv_obj = self.s3_client.get_object(Bucket=bucket_name, Key=object_key)
            return pd.read_csv(csv_obj['Body'])
        except Exception as e:
            logger.error(f"Failed to load data: {str(e)}")
            raise

    def create_agent(self, df):
        """Create LangChain Pandas agent"""
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

    def process_query(self, df, query):
        """Process user query using the agent"""
        agent = self.create_agent(df)
        with get_openai_callback() as cb:
            try:
                response = agent.run(query)
                logger.info(f"Token usage: {cb.total_tokens}")
                return {
                    "response": response,
                    "token_usage": cb.total_tokens
                }
            except Exception as e:
                logger.error(f"Agent execution failed: {str(e)}")
                raise

def lambda_handler(event, context):
    try:
        chain = PandasAnalystChain()
        body = json.loads(event.get("body", "{}"))
        user_query = body.get("query", "Show me some data analysis")
        bucket_name = os.environ["DATA_BUCKET"]
        object_key = body.get("dataset_path", "datasets/my_data.csv")

        df = chain.load_data(bucket_name, object_key)
        result = chain.process_query(df, user_query)

        return {
            "statusCode": 200,
            "body": json.dumps(result),
            "headers": {"Content-Type": "application/json"}
        }
    except Exception as e:
        return {
            "statusCode": 500,
            "body": json.dumps({"error": str(e)}),
            "headers": {"Content-Type": "application/json"}
        }