import os
import json
import pandas as pd
import logging
from typing import Dict, Any, List, Optional, Union
import requests
from dotenv import load_dotenv

# Set up logging
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

# Load environment variables
load_dotenv()

class NemotronAnalyzer:
    """
    Class for analyzing data using NVIDIA's Nemotron model
    """
    
    def __init__(self, api_key: Optional[str] = None):
        """
        Initialize the NemotronAnalyzer with API key
        
        Args:
            api_key: NVIDIA API key (optional, will use environment variable if not provided)
        """
        self.api_key = api_key or os.environ.get("NVIDIA_API_KEY")
        if not self.api_key:
            raise ValueError("NVIDIA API key is required. Set NVIDIA_API_KEY environment variable or pass it to the constructor.")
        
        self.api_url = os.environ.get("NVIDIA_API_URL", "https://api.nvidia.com/v1/nemotron/completions")
    
    def analyze_data(self, df: pd.DataFrame, query: str) -> Dict[str, Any]:
        """
        Analyze data using NVIDIA's Nemotron model
        
        Args:
            df: pandas DataFrame to analyze
            query: User query about the data
            
        Returns:
            Dictionary containing analysis results
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Prepare data summary for Nemotron
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
            
            # Call NVIDIA Nemotron API
            response = self._call_nemotron_api(prompt)
            
            return {
                "analysis": response["text"],
                "token_usage": response.get("usage", {}).get("total_tokens", 0)
            }
        
        except Exception as e:
            logger.error(f"NVIDIA API error: {str(e)}")
            raise
    
    def _call_nemotron_api(self, prompt: str) -> Dict[str, Any]:
        """
        Call NVIDIA's Nemotron API
        
        Args:
            prompt: Prompt to send to the API
            
        Returns:
            API response as a dictionary
            
        Raises:
            Exception: If API call fails
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "nemotron-4-340b-instruct",
                "messages": [
                    {"role": "system", "content": "You are a data analysis expert."},
                    {"role": "user", "content": prompt}
                ],
                "max_tokens": 1500,
                "temperature": 0.2
            }
            
            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()
            
            result = response.json()
            
            # Extract the generated text from the response
            # Note: This structure might need adjustment based on actual NVIDIA API response format
            text = result.get("choices", [{}])[0].get("message", {}).get("content", "")
            
            return {
                "text": text,
                "usage": result.get("usage", {})
            }
        
        except requests.exceptions.RequestException as e:
            logger.error(f"API request error: {str(e)}")
            raise Exception(f"Failed to call NVIDIA API: {str(e)}")
        
        except Exception as e:
            logger.error(f"Unexpected error: {str(e)}")
            raise

    def generate_visualization_code(self, df: pd.DataFrame, chart_type: str, columns: List[str]) -> str:
        """
        Generate Python code for visualization using NVIDIA's Nemotron model
        
        Args:
            df: pandas DataFrame to visualize
            chart_type: Type of chart to generate
            columns: List of columns to include in visualization
            
        Returns:
            Python code as a string
            
        Raises:
            Exception: If API call fails
        """
        try:
            # Prepare data summary
            data_summary = f"DataFrame has {len(df)} rows and columns: {', '.join(df.columns)}.\n"
            data_summary += f"Data types:\n{df.dtypes.to_string()}\n"
            
            # Prepare the prompt
            prompt = f"""
            Generate Python code using Plotly to create a {chart_type} chart for the following data.
            
            DATA SUMMARY:
            {data_summary}
            
            COLUMNS TO INCLUDE:
            {', '.join(columns)}
            
            Return only the Python code without any explanations.
            """
            
            # Call NVIDIA Nemotron API
            response = self._call_nemotron_api(prompt)
            
            # Extract code from response
            code = response["text"]
            
            # Clean up the code (remove markdown code blocks if present)
            if "```python" in code:
                code = code.split("```python")[1].split("```")[0].strip()
            elif "```" in code:
                code = code.split("```")[1].split("```")[0].strip()
            
            return code
        
        except Exception as e:
            logger.error(f"Error generating visualization code: {str(e)}")
            raise