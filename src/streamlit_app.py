import streamlit as st
import pandas as pd
import os
import json
from dotenv import load_dotenv
from typing import Dict, Any, List, Optional, Union
import time

# Import consolidated modules
from core.data_handler import DataHandler
from core.visualizations import VisualizationGenerator
from nvidia_integration import NemotronAnalyzer

# Load environment variables
load_dotenv()

# Set page configuration
st.set_page_config(
    page_title="Pandas Data Analyst Agent",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = None
if "analysis_results" not in st.session_state:
    st.session_state.analysis_results = None

def load_data_from_file(uploaded_file):
    """Load data from uploaded file"""
    try:
        if uploaded_file.name.endswith('.csv'):
            df = pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith(('.xls', '.xlsx')):
            df = pd.read_excel(uploaded_file)
        else:
            st.error("Unsupported file format. Please upload CSV or Excel files.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading file: {str(e)}")
        return None

def main():
    st.title("🦁 Pandas Data Analyst Agent")
    st.markdown("AI-powered data analysis with NVIDIA Nemotron")
    
    # Sidebar for configuration
    with st.sidebar:
        st.header("Configuration")
        
        # Data source selection
        data_source = st.radio("Data Source", ["Upload File", "S3 Bucket"])
        
        if data_source == "Upload File":
            uploaded_file = st.file_uploader("Choose a file", type=['csv', 'xlsx', 'xls'])
            if uploaded_file:
                st.session_state.data = load_data_from_file(uploaded_file)
        
        elif data_source == "S3 Bucket":
            bucket_name = st.text_input("S3 Bucket Name", value=os.environ.get("DATA_BUCKET", ""))
            object_key = st.text_input("Object Key", value="datasets/my_data.csv")
            
            if st.button("Load from S3") and bucket_name and object_key:
                try:
                    data_handler = DataHandler()
                    st.session_state.data = data_handler.load_from_s3(bucket_name, object_key)
                    st.success("Data loaded successfully!")
                except Exception as e:
                    st.error(f"Error loading from S3: {str(e)}")
    
    # Main content area
    if st.session_state.data is not None:
        df = st.session_state.data
        
        # Display data overview
        st.subheader("Data Overview")
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("Rows", len(df))
        with col2:
            st.metric("Columns", len(df.columns))
        with col3:
            st.metric("Memory Usage", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        
        # Display sample data
        st.subheader("Sample Data")
        st.dataframe(df.head())
        
        # Analysis section
        st.subheader("AI Analysis")
        
        query = st.text_area("Ask a question about your data:", 
                           placeholder="e.g., What are the main trends in this dataset?")
        
        col1, col2 = st.columns(2)
        
        with col1:
            chart_type = st.selectbox("Chart Type", 
                                    ["histogram", "bar", "scatter", "line", "heatmap"])
        
        with col2:
            if chart_type in ["bar", "scatter", "line"]:
                x_column = st.selectbox("X Column", df.columns)
                y_column = st.selectbox("Y Column", df.columns)
            else:
                x_column = st.selectbox("Column", df.columns) if chart_type == "histogram" else None
                y_column = None
        
        if st.button("Analyze", type="primary"):
            if query:
                with st.spinner("Analyzing data..."):
                    try:
                        # Initialize analyzer
                        analyzer = NemotronAnalyzer()
                        
                        # Generate analysis
                        analysis_result = analyzer.analyze_data(df, query)
                        
                        # Generate visualization
                        viz_generator = VisualizationGenerator()
                        chart_bytes = viz_generator.generate_chart(df, chart_type, x_column, y_column)
                        
                        # Display results
                        st.subheader("Analysis Results")
                        st.write(analysis_result["analysis"])
                        
                        st.subheader("Visualization")
                        st.image(chart_bytes, caption=f"{chart_type.title()} Chart")
                        
                        # Display metrics
                        st.info(f"Token usage: {analysis_result.get('token_usage', 'N/A')}")
                        
                    except Exception as e:
                        st.error(f"Analysis failed: {str(e)}")
            else:
                st.warning("Please enter a query to analyze the data.")
    
    else:
        st.info("Please upload a file or load data from S3 to get started.")

if __name__ == "__main__":
    main()
        else:
            st.error("Unsupported file format. Please upload a CSV or Excel file.")
            return None
        return df
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return None

# Function to load data from S3
def load_data_from_s3(bucket_name, object_key):
    try:
        s3_client = boto3.client('s3')
        csv_obj = s3_client.get_object(Bucket=bucket_name, Key=object_key)
        df = pd.read_csv(csv_obj['Body'])
        return df
    except Exception as e:
        st.error(f"Error loading data from S3: {str(e)}")
        return None

# Function to display data summary
def display_data_summary(df):
    st.subheader("Data Summary")
    summary = summarize_data(df)
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Rows:** {summary['shape'][0]}")
        st.write(f"**Columns:** {summary['shape'][1]}")
        st.write("**Column Types:**")
        for col, dtype in summary['dtypes'].items():
            st.write(f"- {col}: {dtype}")
    
    with col2:
        st.write("**Missing Values:**")
        missing_df = pd.DataFrame.from_dict(summary['missing_values'], orient='index', columns=['Count'])
        missing_df = missing_df[missing_df['Count'] > 0]
        if not missing_df.empty:
            st.dataframe(missing_df)
        else:
            st.write("No missing values")
    
    st.subheader("Data Preview")
    st.dataframe(df.head())

# Function to create visualization
def create_visualization(df, chart_type, x_column, y_column=None, color_column=None):
    try:
        if chart_type == "histogram":
            fig = px.histogram(df, x=x_column, title=f"Histogram of {x_column}")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "bar":
            if not y_column:
                st.error("Y-axis column is required for bar chart")
                return
            fig = px.bar(df, x=x_column, y=y_column, color=color_column, 
                        title=f"Bar Chart: {y_column} by {x_column}")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "scatter":
            if not y_column:
                st.error("Y-axis column is required for scatter plot")
                return
            fig = px.scatter(df, x=x_column, y=y_column, color=color_column,
                            title=f"Scatter Plot: {y_column} vs {x_column}")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "line":
            if not y_column:
                st.error("Y-axis column is required for line chart")
                return
            fig = px.line(df, x=x_column, y=y_column, color=color_column,
                        title=f"Line Chart: {y_column} over {x_column}")
            st.plotly_chart(fig, use_container_width=True)
        
        elif chart_type == "heatmap":
            # For heatmap, use seaborn and matplotlib
            numeric_df = df.select_dtypes(include=['number'])
            if numeric_df.empty:
                st.error("No numeric columns available for heatmap")
                return
            
            fig, ax = plt.subplots(figsize=(10, 8))
            corr = numeric_df.corr()
            sns.heatmap(corr, annot=True, cmap='coolwarm', fmt=".2f", ax=ax)
            plt.title("Correlation Heatmap")
            st.pyplot(fig)
        
        else:
            st.error(f"Unsupported chart type: {chart_type}")
    
    except Exception as e:
        st.error(f"Error creating visualization: {str(e)}")

# Main app layout
def main():
    # Sidebar
    st.sidebar.title("🦁 Pandas Data Analyst")
    st.sidebar.markdown("Data solutions as vibrant as a Cape Town sunset")
    
    # Data source selection
    data_source = st.sidebar.radio("Select Data Source", ["Upload File", "S3 Bucket"])
    
    if data_source == "Upload File":
        uploaded_file = st.sidebar.file_uploader("Upload CSV or Excel file", type=["csv", "xlsx", "xls"])
        if uploaded_file is not None:
            st.session_state.data = load_data_from_file(uploaded_file)
    else:
        bucket_name = st.sidebar.text_input("S3 Bucket Name")
        object_key = st.sidebar.text_input("S3 Object Key (path to file)")
        if st.sidebar.button("Load Data") and bucket_name and object_key:
            st.session_state.data = load_data_from_s3(bucket_name, object_key)
    
    # Main content
    st.title("🦁 Pandas Data Analyst Agent")
    st.markdown("Transform your data into actionable insights with AI-powered analysis")
    
    if st.session_state.data is not None:
        df = st.session_state.data
        
        # Display tabs
        tab1, tab2, tab3, tab4 = st.tabs(["Data Summary", "Visualization", "AI Analysis", "Outlier Detection"])
        
        with tab1:
            display_data_summary(df)
        
        with tab2:
            st.subheader("Data Visualization")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                chart_type = st.selectbox("Chart Type", 
                                        ["histogram", "bar", "scatter", "line", "heatmap"],
                                        index=["histogram", "bar", "scatter", "line", "heatmap"].index(st.session_state.chart_type))
                st.session_state.chart_type = chart_type
            
            with col2:
                x_column = st.selectbox("X-axis Column", df.columns)
            
            with col3:
                y_column = None
                color_column = None
                if chart_type in ["bar", "scatter", "line"]:
                    y_column = st.selectbox("Y-axis Column", df.columns)
                    color_column = st.selectbox("Color By (optional)", ["None"] + list(df.columns))
                    if color_column == "None":
                        color_column = None
            
            create_visualization(df, chart_type, x_column, y_column, color_column)
        
        with tab3:
            st.subheader("AI Analysis with NVIDIA Nemotron")
            
            query = st.text_area("What would you like to know about your data?", 
                                "Analyze this dataset and provide key insights.")
            
            if st.button("Analyze"):
                with st.spinner("Analyzing data with NVIDIA Nemotron..."):
                    try:
                        # Initialize the Nemotron analyzer
                        analyzer = NemotronAnalyzer()
                        
                        # Get analysis results
                        start_time = time.time()
                        results = analyzer.analyze_data(df, query)
                        execution_time = time.time() - start_time
                        
                        # Store results in session state
                        st.session_state.analysis_results = {
                            "analysis": results["analysis"],
                            "execution_time": execution_time
                        }
                    except Exception as e:
                        st.error(f"Error during analysis: {str(e)}")
            
            if st.session_state.analysis_results:
                st.markdown("### Analysis Results")
                st.markdown(st.session_state.analysis_results["analysis"])
                st.info(f"Analysis completed in {st.session_state.analysis_results['execution_time']:.2f} seconds")
        
        with tab4:
            st.subheader("Outlier Detection")
            
            col1, col2 = st.columns(2)
            with col1:
                outlier_column = st.selectbox("Select Column for Outlier Detection", 
                                            df.select_dtypes(include=['number']).columns)
            
            with col2:
                outlier_method = st.selectbox("Detection Method", ["IQR", "Z-Score"], 
                                            index=0)
            
            if st.button("Detect Outliers"):
                with st.spinner("Detecting outliers..."):
                    try:
                        outliers = detect_outliers(df, outlier_column, method=outlier_method.lower())
                        
                        if outliers.empty:
                            st.success("No outliers detected!")
                        else:
                            st.markdown(f"**{len(outliers)} outliers detected:**")
                            st.dataframe(outliers)
                            
                            # Visualize outliers
                            fig = px.box(df, y=outlier_column, title=f"Box Plot of {outlier_column} showing outliers")
                            st.plotly_chart(fig, use_container_width=True)
                    except Exception as e:
                        st.error(f"Error detecting outliers: {str(e)}")
    
    else:
        st.info("Please upload a file or provide S3 bucket details to get started.")
    
    # Footer
    st.sidebar.markdown("---")
    st.sidebar.markdown("### About")
    st.sidebar.markdown(
        "This tool uses NVIDIA Nemotron to analyze your data and provide insights. "
        "Upload your data and ask questions in natural language."
    )

if __name__ == "__main__":
    main()