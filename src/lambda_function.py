"""
Production Serverless Data Analyst Lambda Handler.
Scale-to-zero compute powered by AWS Lambda Powertools, Amazon Bedrock AgentCore, and DuckDB.
"""

from __future__ import annotations
import json
import os
import time
from typing import Dict, Any
from aws_lambda_powertools import Logger, Metrics, Tracer
from aws_lambda_powertools.metrics import MetricUnit
from aws_lambda_powertools.utilities.typing import LambdaContext

from core.data_handler import DataHandler
from core.visualizations import VisualizationGenerator
from engine.sandbox import DeterministicSandbox
from agent.bedrock_core import BedrockAgentCore
from tools.playwright_tool import run_extract_tables

logger = Logger(service="data-analyst-agent")
metrics = Metrics(namespace="DataAnalystAgent")
tracer = Tracer(service="data-analyst-agent")


def build_response(status_code: int, body: Dict[str, Any]) -> Dict[str, Any]:
    """Helper to format API Gateway HTTP response."""
    return {
        "statusCode": status_code,
        "headers": {
            "Content-Type": "application/json",
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Methods": "POST, GET, OPTIONS",
            "Access-Control-Allow-Headers": "Content-Type,Authorization"
        },
        "body": json.dumps(body, default=str)
    }


@logger.inject_lambda_context(correlation_id_path="headers.x-correlation-id")
@metrics.log_metrics(capture_cold_start_metric=True)
@tracer.capture_lambda_handler
def lambda_handler(event: Dict[str, Any], context: LambdaContext) -> Dict[str, Any]:
    """
    Main Lambda entry point. Handles /analyze, /query, and /browser/extract.
    """
    start_time = time.time()
    
    # Handle API Gateway CORS preflight
    http_method = event.get("requestContext", {}).get("http", {}).get("method", event.get("httpMethod", "POST"))
    if http_method == "OPTIONS":
        return build_response(200, {"status": "OK"})

    try:
        # Parse payload
        raw_body = event.get("body")
        if isinstance(raw_body, str):
            payload = json.loads(raw_body)
        elif isinstance(raw_body, dict):
            payload = raw_body
        else:
            payload = event

        path = event.get("rawPath", event.get("path", "/analyze"))
        bucket_name = os.environ.get("DATA_BUCKET", "data-analyst-lakehouse")
        data_handler = DataHandler()

        # Route 1: Playwright Browser Web Scraper
        if "/browser/extract" in path:
            url = payload.get("url")
            if not url:
                return build_response(400, {"error": "Missing 'url' in payload."})
            table_selector = payload.get("table_selector", "table")
            result = run_extract_tables(url, table_selector)
            metrics.add_metric(name="BrowserExtractions", unit=MetricUnit.Count, value=1)
            return build_response(200, result)

        # Route 2: Pure SQL Query (Direct DuckDB execution, zero LLM cost)
        if "/query" in path:
            sql_query = payload.get("sql")
            dataset_path = payload.get("dataset_path")
            if not sql_query:
                return build_response(400, {"error": "Missing 'sql' query parameter."})

            sandbox = DeterministicSandbox()
            if dataset_path:
                df = data_handler.load_from_s3(bucket_name, dataset_path)
                sandbox.register_dataframe("dataset", df)

            exec_result = sandbox.execute_sql(sql_query)
            metrics.add_metric(name="DirectSqlQueries", unit=MetricUnit.Count, value=1)
            return build_response(200, exec_result)

        # Route 3: Bedrock Agentic Data Analysis
        user_query = payload.get("query")
        dataset_path = payload.get("dataset_path")
        if not user_query:
            return build_response(400, {"error": "Missing 'query' parameter."})

        sandbox = DeterministicSandbox()
        if dataset_path:
            df = data_handler.load_from_s3(bucket_name, dataset_path)
            sandbox.register_dataframe("dataset", df)

        # Initialize Bedrock Agent Core with deterministic sandbox
        agent = BedrockAgentCore(sandbox=sandbox)
        agent_output = agent.run_conversation(user_prompt=user_query)

        # Generate Plotly visualization if requested
        chart_spec = None
        if payload.get("generate_chart") and dataset_path:
            chart_type = payload.get("chart_type", "histogram")
            x_col = payload.get("x_column")
            y_col = payload.get("y_column")
            fig = VisualizationGenerator.generate_chart(df, chart_type, x_col, y_col)
            chart_spec = VisualizationGenerator.export_figure_json(fig)

        duration = time.time() - start_time
        metrics.add_metric(name="AnalystExecutions", unit=MetricUnit.Count, value=1)
        metrics.add_metric(name="ExecutionDuration", unit=MetricUnit.Seconds, value=duration)

        return build_response(200, {
            "status": "SUCCESS",
            "analysis": agent_output.get("analysis"),
            "model_used": agent_output.get("model_used"),
            "tool_executions": agent_output.get("tool_executions"),
            "chart_spec": chart_spec,
            "execution_time_seconds": round(duration, 3)
        })

    except Exception as e:
        logger.exception("Error processing data analyst request")
        metrics.add_metric(name="ExecutionErrors", unit=MetricUnit.Count, value=1)
        return build_response(500, {
            "status": "ERROR",
            "error": str(e)
        })
