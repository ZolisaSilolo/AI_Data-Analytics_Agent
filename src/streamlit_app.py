"""
OmniAnalyst - Modern Multi-Discipline Streamlit Interface.
Powered by Amazon Bedrock AgentCore, DuckDB, Polars, and Playwright.
"""

import os
import json
import time
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

# Modular imports
from core.data_handler import DataHandler
from core.visualizations import VisualizationGenerator
from engine.sandbox import DeterministicSandbox
from agent.bedrock_core import BedrockAgentCore
from tools.playwright_tool import run_extract_tables

# Discipline analytical modules
from disciplines.product import ProductAnalytics
from disciplines.financial import FinancialAnalytics
from disciplines.operations import OperationsAnalytics
from disciplines.growth import GrowthAnalytics
from disciplines.clinical import ClinicalAnalytics

load_dotenv()

st.set_page_config(
    page_title="OmniAnalyst - AI Data Analyst Platform",
    page_icon="🦁",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Initialize session state
if "data" not in st.session_state:
    st.session_state.data = None
if "analysis_history" not in st.session_state:
    st.session_state.analysis_history = []
if "active_sandbox" not in st.session_state:
    st.session_state.active_sandbox = DeterministicSandbox()


def load_file(uploaded_file) -> pd.DataFrame | None:
    try:
        if uploaded_file.name.endswith(".csv"):
            return pd.read_csv(uploaded_file)
        elif uploaded_file.name.endswith((".xls", ".xlsx")):
            return pd.read_excel(uploaded_file)
        elif uploaded_file.name.endswith(".parquet"):
            return pd.read_parquet(uploaded_file)
        else:
            st.error("Unsupported format. Please upload CSV, Excel, or Parquet.")
            return None
    except Exception as e:
        st.error(f"Error loading file: {e}")
        return None


def main():
    st.title("🦁 OmniAnalyst: Autonomous Data Analyst Platform")
    st.caption("Deterministic, Serverless & Multi-Disciplinary Analytics Powered by Amazon Bedrock AgentCore")

    # Sidebar configuration
    with st.sidebar:
        st.header("⚙️ Configuration")

        # Model selection
        model_choice = st.selectbox(
            "Amazon Bedrock Model",
            [
                "anthropic.claude-3-5-sonnet-20241022-v2:0",
                "amazon.nova-pro-v1:0",
                "amazon.nova-lite-v1:0"
            ],
            index=0
        )

        # Discipline mode
        discipline = st.selectbox(
            "Analytical Discipline",
            ["General Exploratory", "Product Analytics", "Financial & RevOps", "Operations & Supply Chain", "Marketing & Growth", "Clinical & Biotech"]
        )

        st.divider()
        st.subheader("📁 Data Source")
        source_type = st.radio("Ingestion Method", ["File Upload", "Playwright Web Scrape", "S3 Lakehouse"])

        if source_type == "File Upload":
            uploaded = st.file_uploader("Upload dataset", type=["csv", "xlsx", "parquet"])
            if uploaded:
                st.session_state.data = load_file(uploaded)
                if st.session_state.data is not None:
                    st.session_state.active_sandbox.register_dataframe("dataset", st.session_state.data)

        elif source_type == "Playwright Web Scrape":
            scrape_url = st.text_input("Enter Dashboard / Web Portal URL:")
            table_sel = st.text_input("CSS Selector", value="table")
            if st.button("🌐 Extract Web Tables") and scrape_url:
                with st.spinner("Playwright navigating and extracting DOM tables..."):
                    res = run_extract_tables(scrape_url, table_sel)
                    if res.get("status") == "SUCCESS" and res.get("tables"):
                        first_tbl = res["tables"][0]
                        st.session_state.data = pd.DataFrame(first_tbl["sample_records"])
                        st.session_state.active_sandbox.register_dataframe("dataset", st.session_state.data)
                        st.success(f"Extracted {len(st.session_state.data)} rows from {res.get('page_title')}!")
                    else:
                        st.error(f"Scrape failed: {res.get('error', 'No tables found')}")

        elif source_type == "S3 Lakehouse":
            bucket = st.text_input("S3 Bucket", value=os.environ.get("DATA_BUCKET", ""))
            s3_key = st.text_input("Dataset Key", value="datasets/sales_data.parquet")
            if st.button("Load from S3") and bucket and s3_key:
                try:
                    dh = DataHandler()
                    st.session_state.data = dh.load_from_s3(bucket, s3_key)
                    st.session_state.active_sandbox.register_dataframe("dataset", st.session_state.data)
                    st.success("S3 dataset loaded into DuckDB!")
                except Exception as e:
                    st.error(f"S3 Load Error: {e}")

    # Main Area
    if st.session_state.data is not None:
        df = st.session_state.data

        # Top Metric Cards
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Rows", f"{len(df):,}")
        col2.metric("Columns", len(df.columns))
        col3.metric("Memory", f"{df.memory_usage(deep=True).sum() / 1024:.1f} KB")
        col4.metric("Discipline", discipline)

        tabs = st.tabs(["🤖 Autonomous Agent", "📊 Declarative Visualizations", "🔬 Discipline Calculator", "📋 Dataset Preview"])

        # Tab 1: Autonomous Bedrock Agent
        with tabs[0]:
            st.subheader("Autonomous Reasoning & Deterministic Execution")
            user_prompt = st.text_area(
                "Ask a business or analytical question:",
                placeholder="e.g. Identify anomalies in churn, calculate cohort retention, or find correlations with conversion rate..."
            )

            if st.button("🚀 Run Analysis", type="primary") and user_prompt:
                with st.spinner("Agent formulating hypothesis and compiling DuckDB SQL..."):
                    agent = BedrockAgentCore(
                        primary_model=model_choice,
                        sandbox=st.session_state.active_sandbox
                    )
                    try:
                        agent_res = agent.run_conversation(user_prompt)
                        st.markdown("### 📋 Executive Analytical Report")
                        st.markdown(agent_res.get("analysis", "No output generated."))

                        # Execution Audit Trail
                        with st.expander("🔍 Transparent Execution Trace (Code Compiled & Invariants Checked)"):
                            tools_executed = agent_res.get("tool_executions", [])
                            if not tools_executed:
                                st.info("Analysis completed directly.")
                            for idx, t in enumerate(tools_executed):
                                st.markdown(f"**Step {idx+1}: Tool `{t['tool']}`**")
                                st.json(t["input"])
                                st.caption("Result:")
                                st.json(t["output"])

                    except Exception as err:
                        st.error(f"Agent Execution Failed: {err}")

        # Tab 2: Declarative Visualizations
        with tabs[1]:
            st.subheader("Declarative Visual Grammar")
            vcol1, vcol2, vcol3 = st.columns(3)
            chart_type = vcol1.selectbox("Chart Type", ["histogram", "bar", "scatter", "line", "box", "correlation_matrix", "waterfall"])
            numeric_cols = list(df.select_dtypes(include=["number"]).columns)
            all_cols = list(df.columns)

            x_c = vcol2.selectbox("X Axis", all_cols, index=0)
            y_c = vcol3.selectbox("Y Axis", numeric_cols if numeric_cols else all_cols, index=min(1, len(numeric_cols)-1) if numeric_cols else 0)

            if st.button("Generate Chart"):
                try:
                    fig = VisualizationGenerator.generate_chart(df, chart_type, x_c, y_c)
                    st.plotly_chart(fig, use_container_width=True)
                except Exception as ve:
                    st.error(f"Visualization error: {ve}")

        # Tab 3: Discipline Calculator
        with tabs[2]:
            st.subheader(f"Specialized {discipline} Mathematical Tools")
            if discipline == "Product Analytics":
                st.write("**Funnel & Cohort Retention Engine**")
                cols_selected = st.multiselect("Select Funnel Steps in Order", all_cols)
                if st.button("Compute Funnel") and cols_selected:
                    res = ProductAnalytics.calculate_funnel(df, cols_selected)
                    st.json(res)

            elif discipline == "Financial & RevOps":
                st.write("**ARR Waterfall & NRR Reconciler**")
                fc1, fc2, fc3, fc4, fc5 = st.columns(5)
                b_arr = fc1.number_input("Beginning ARR ($)", value=1000000.0)
                n_arr = fc2.number_input("New ARR ($)", value=250000.0)
                e_arr = fc3.number_input("Expansion ARR ($)", value=150000.0)
                c_arr = fc4.number_input("Contraction ARR ($)", value=30000.0)
                ch_arr = fc5.number_input("Churn ARR ($)", value=70000.0)

                if st.button("Compute Waterfall"):
                    res = FinancialAnalytics.calculate_arr_waterfall(b_arr, n_arr, e_arr, c_arr, ch_arr)
                    st.json(res)

            elif discipline == "Operations & Supply Chain":
                st.write("**Lead Time Variance & Little's Law**")
                num_col = st.selectbox("Select Duration / Lead-Time Column", numeric_cols if numeric_cols else all_cols)
                if st.button("Analyze Lead Times") and num_col:
                    res = OperationsAnalytics.analyze_lead_times(df[num_col].tolist())
                    st.json(res)

            elif discipline == "Clinical & Biotech":
                st.write("**Fisher's Exact Test & Odds Ratio Calculator**")
                cc1, cc2 = st.columns(2)
                exp_cases = cc1.number_input("Exposed Cases", value=25)
                exp_non = cc1.number_input("Exposed Non-Cases", value=75)
                unexp_cases = cc2.number_input("Unexposed Cases", value=10)
                unexp_non = cc2.number_input("Unexposed Non-Cases", value=90)
                if st.button("Compute Biostatistics"):
                    res = ClinicalAnalytics.calculate_contingency_statistics(exp_cases, exp_non, unexp_cases, unexp_non)
                    st.json(res)
            else:
                st.info("Select a specialized discipline from the sidebar to access domain calculators.")

        # Tab 4: Dataset Preview
        with tabs[3]:
            st.subheader("Raw Data Preview")
            st.dataframe(df.head(100), use_container_width=True)

    else:
        st.info("👈 Please upload a dataset or provide a web URL in the sidebar to get started.")


if __name__ == "__main__":
    main()
