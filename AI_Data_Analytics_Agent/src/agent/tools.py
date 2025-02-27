import pandas as pd
import plotly.express as px

def load_data(filepath):
    return pd.read_csv(filepath)

def generate_plot(data):
    # Assuming data is a dict with keys "x" and "y"
    df = pd.DataFrame(data)
    fig = px.line(df, x="x", y="y")
    # Return the figure as a dict for testing purposes
    return fig.to_dict()
