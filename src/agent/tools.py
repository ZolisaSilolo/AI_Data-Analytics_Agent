import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import io
import base64
from typing import Dict, Any, Optional, List, Union

def load_data(filepath: str) -> pd.DataFrame:
    """
    Load data from a CSV file into a pandas DataFrame
    
    Args:
        filepath: Path to the CSV file
        
    Returns:
        pandas DataFrame containing the data
    """
    return pd.read_csv(filepath)

def generate_plot(data: Dict[str, List]) -> Dict:
    """
    Generate a line plot using Plotly
    
    Args:
        data: Dictionary with keys "x" and "y" containing data for plotting
        
    Returns:
        Plotly figure as a dictionary
    """
    df = pd.DataFrame(data)
    fig = px.line(df, x="x", y="y")
    return fig.to_dict()

def generate_bar_chart(df: pd.DataFrame, x_column: str, y_column: str, 
                      title: str = "Bar Chart", color: Optional[str] = None) -> Dict:
    """
    Generate a bar chart using Plotly
    
    Args:
        df: pandas DataFrame containing the data
        x_column: Column name for x-axis
        y_column: Column name for y-axis
        title: Chart title
        color: Optional column name for color grouping
        
    Returns:
        Plotly figure as a dictionary
    """
    fig = px.bar(df, x=x_column, y=y_column, color=color, title=title)
    return fig.to_dict()

def generate_heatmap(df: pd.DataFrame, columns: Optional[List[str]] = None) -> str:
    """
    Generate a correlation heatmap using Seaborn and return as base64 encoded string
    
    Args:
        df: pandas DataFrame containing the data
        columns: Optional list of column names to include in correlation
        
    Returns:
        Base64 encoded string of the heatmap image
    """
    # Select only numeric columns if not specified
    if columns:
        numeric_df = df[columns].select_dtypes(include=['number'])
    else:
        numeric_df = df.select_dtypes(include=['number'])
    
    # Calculate correlation
    corr = numeric_df.corr()
    
    # Create figure and axes
    plt.figure(figsize=(10, 8))
    
    # Generate heatmap
    sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)
    plt.title("Correlation Heatmap")
    
    # Save figure to bytes buffer
    buf = io.BytesIO()
    plt.savefig(buf, format='png', bbox_inches='tight')
    plt.close()
    buf.seek(0)
    
    # Encode as base64 string
    img_str = base64.b64encode(buf.read()).decode('utf-8')
    return img_str

def summarize_data(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Generate a summary of the DataFrame including basic statistics and missing values
    
    Args:
        df: pandas DataFrame to summarize
        
    Returns:
        Dictionary containing summary information
    """
    summary = {
        "shape": df.shape,
        "columns": list(df.columns),
        "dtypes": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isna().sum().to_dict(),
        "numeric_summary": df.describe().to_dict(),
    }
    return summary

def detect_outliers(df: pd.DataFrame, column: str, method: str = "iqr") -> pd.DataFrame:
    """
    Detect outliers in a specific column using IQR or Z-score method
    
    Args:
        df: pandas DataFrame
        column: Column name to check for outliers
        method: Method to use for outlier detection ('iqr' or 'zscore')
        
    Returns:
        DataFrame containing only the outlier rows
    """
    if method.lower() == "iqr":
        Q1 = df[column].quantile(0.25)
        Q3 = df[column].quantile(0.75)
        IQR = Q3 - Q1
        lower_bound = Q1 - 1.5 * IQR
        upper_bound = Q3 + 1.5 * IQR
        outliers = df[(df[column] < lower_bound) | (df[column] > upper_bound)]
    elif method.lower() == "zscore":
        from scipy import stats
        z_scores = stats.zscore(df[column])
        abs_z_scores = abs(z_scores)
        filtered_entries = (abs_z_scores > 3)
        outliers = df[filtered_entries]
    else:
        raise ValueError("Method must be either 'iqr' or 'zscore'")
    
    return outliers