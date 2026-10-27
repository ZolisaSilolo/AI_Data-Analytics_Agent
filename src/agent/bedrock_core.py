"""
Amazon Bedrock AgentCore Integration.
Uses the Bedrock Converse API with native tool-use, structured reasoning, and multi-model fallback.
"""

from __future__ import annotations
import json
import logging
import os
import boto3
from typing import Dict, Any, List, Optional
from botocore.exceptions import ClientError
from engine.sandbox import DeterministicSandbox
from tools.playwright_tool import run_extract_tables

logger = logging.getLogger(__name__)


class BedrockAgentCore:
    """
    AWS Bedrock AgentCore client providing tool-calling, deterministic execution loops,
    and multi-model fallbacks (Claude 3.5 Sonnet / Amazon Nova Pro).
    """

    DEFAULT_PRIMARY_MODEL = "anthropic.claude-3-5-sonnet-20241022-v2:0"
    DEFAULT_FALLBACK_MODEL = "amazon.nova-pro-v1:0"

    SYSTEM_PROMPT = """You are an elite, highly deterministic Lead Data Analyst Agent.
Your mandate is to provide rigorous, mathematically sound, reproducible analysis across disciplines (Product, Finance, Operations, Growth, Clinical).

CRITICAL INSTRUCTIONS:
1. NEVER calculate numbers, percentages, p-values, or statistical aggregations mentally in your text generation.
2. ALWAYS use the `execute_sql_query` or `execute_python_analysis` tools to compute all metrics.
3. Every claim in your final answer MUST reference exact values returned by tool executions.
4. If the user provides a web URL or requests data extraction, use the `extract_web_data` tool.
5. Highlight data quality invariants, sample size limitations, and potential biases explicitly.
"""

    def __init__(
        self,
        region_name: Optional[str] = None,
        primary_model: Optional[str] = None,
        fallback_model: Optional[str] = None,
        sandbox: Optional[DeterministicSandbox] = None
    ):
        self.region = region_name or os.environ.get("AWS_REGION", "us-east-1")
        self.primary_model = primary_model or os.environ.get("BEDROCK_PRIMARY_MODEL", self.DEFAULT_PRIMARY_MODEL)
        self.fallback_model = fallback_model or os.environ.get("BEDROCK_FALLBACK_MODEL", self.DEFAULT_FALLBACK_MODEL)
        self.client = boto3.client("bedrock-runtime", region_name=self.region)
        self.sandbox = sandbox or DeterministicSandbox()

    def get_tool_specs(self) -> List[Dict[str, Any]]:
        """Define tool configuration schemas for the Bedrock Converse API."""
        return [
            {
                "toolSpec": {
                    "name": "execute_sql_query",
                    "description": "Execute a deterministic SQL query in DuckDB against registered tables. Ideal for filtering, aggregations, joins, and window functions.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "sql": {
                                    "type": "string",
                                    "description": "The valid SQL query to execute in DuckDB."
                                }
                            },
                            "required": ["sql"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "execute_python_analysis",
                    "description": "Execute safe Python code for statistical modeling, regression, hypothesis tests, or data reshaping. Output must set `result` variable.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "code": {
                                    "type": "string",
                                    "description": "Python code snippet using polars, pandas, or duckdb. Store final output in 'result'."
                                }
                            },
                            "required": ["code"]
                        }
                    }
                }
            },
            {
                "toolSpec": {
                    "name": "extract_web_data",
                    "description": "Extract tabular data from any web URL or dashboard using Playwright headless browser.",
                    "inputSchema": {
                        "json": {
                            "type": "object",
                            "properties": {
                                "url": {
                                    "type": "string",
                                    "description": "The URL of the webpage or web portal to extract data from."
                                },
                                "table_selector": {
                                    "type": "string",
                                    "description": "CSS selector for the table (defaults to 'table')."
                                }
                            },
                            "required": ["url"]
                        }
                    }
                }
            }
        ]

    def _execute_tool(self, tool_name: str, tool_args: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch tool calls to deterministic local handlers."""
        logger.info(f"Executing tool: {tool_name} with args: {tool_args}")
        if tool_name == "execute_sql_query":
            return self.sandbox.execute_sql(tool_args.get("sql", ""))
        elif tool_name == "execute_python_analysis":
            return self.sandbox.execute_python(tool_args.get("code", ""))
        elif tool_name == "extract_web_data":
            return run_extract_tables(tool_args.get("url", ""), tool_args.get("table_selector", "table"))
        else:
            return {"error": f"Unknown tool: {tool_name}"}

    def run_conversation(
        self,
        user_prompt: str,
        chat_history: Optional[List[Dict[str, Any]]] = None,
        max_tool_rounds: int = 5
    ) -> Dict[str, Any]:
        """
        Execute an autonomous reasoning & tool execution loop with Bedrock.
        """
        messages = list(chat_history) if chat_history else []
        messages.append({
            "role": "user",
            "content": [{"text": user_prompt}]
        })

        tools_used: List[Dict[str, Any]] = []
        active_model = self.primary_model
        total_tokens = 0

        for round_idx in range(max_tool_rounds):
            try:
                response = self.client.converse(
                    modelId=active_model,
                    messages=messages,
                    system=[{"text": self.SYSTEM_PROMPT}],
                    toolConfig={"tools": self.get_tool_specs()},
                    inferenceConfig={"temperature": 0.1, "maxTokens": 4096}
                )
            except ClientError as ce:
                # If primary model fails or is un-provisioned, try fallback model
                if active_model != self.fallback_model:
                    logger.warning(f"Primary model {active_model} failed: {ce}. Falling back to {self.fallback_model}")
                    active_model = self.fallback_model
                    response = self.client.converse(
                        modelId=active_model,
                        messages=messages,
                        system=[{"text": self.SYSTEM_PROMPT}],
                        toolConfig={"tools": self.get_tool_specs()},
                        inferenceConfig={"temperature": 0.1, "maxTokens": 4096}
                    )
                else:
                    raise

            usage = response.get("usage", {})
            total_tokens += usage.get("totalTokens", 0)
            output_msg = response["output"]["message"]
            messages.append(output_msg)

            stop_reason = response.get("stopReason")
            if stop_reason != "tool_use":
                # Agent completed analysis without requesting further tools
                final_text = "".join(
                    block.get("text", "") for block in output_msg.get("content", []) if "text" in block
                )
                return {
                    "status": "SUCCESS",
                    "analysis": final_text,
                    "model_used": active_model,
                    "total_tokens": total_tokens,
                    "tool_executions": tools_used,
                    "rounds": round_idx + 1
                }

            # Process tool calls
            tool_requests = [block["toolUse"] for block in output_msg.get("content", []) if "toolUse" in block]
            tool_results_blocks = []

            for tool_req in tool_requests:
                tool_use_id = tool_req["toolUseId"]
                tool_name = tool_req["name"]
                tool_input = tool_req.get("input", {})

                # Execute
                execution_result = self._execute_tool(tool_name, tool_input)
                tools_used.append({
                    "tool": tool_name,
                    "input": tool_input,
                    "output": execution_result
                })

                tool_results_blocks.append({
                    "toolResult": {
                        "toolUseId": tool_use_id,
                        "content": [{"json": execution_result}],
                        "status": "success" if execution_result.get("status") != "ERROR" else "error"
                    }
                })

            # Append tool results back to conversation
            messages.append({
                "role": "user",
                "content": tool_results_blocks
            })

        return {
            "status": "MAX_ROUNDS_REACHED",
            "analysis": "Agent reached maximum tool iterations without finishing.",
            "tool_executions": tools_used,
            "model_used": active_model
        }
