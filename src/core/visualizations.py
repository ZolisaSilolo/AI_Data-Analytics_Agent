import pandas as pd
import plotly.express as px
import matplotlib.pyplot as plt
import seaborn as sns
import io
from typing import Optional

class VisualizationGenerator:
    """Unified visualization generation"""
    
    @staticmethod
    def generate_chart(df: pd.DataFrame, chart_type: str = "histogram", 
                      x_column: Optional[str] = None, 
                      y_column: Optional[str] = None) -> bytes:
        """Generate visualization based on chart type"""
        
        if not x_column and len(df.columns) > 0:
            x_column = df.columns[0]
        
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
