import os
import sys
import streamlit.web.cli as stcli
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def main():
    # Get the directory of the current script
    current_dir = os.path.dirname(os.path.abspath(__file__))
    
    # Set the path to the Streamlit app
    streamlit_app_path = os.path.join(current_dir, "src", "streamlit_app.py")
    
    # Check if the file exists
    if not os.path.exists(streamlit_app_path):
        print(f"Error: Streamlit app file not found at {streamlit_app_path}")
        sys.exit(1)
    
    # Run the Streamlit app
    sys.argv = ["streamlit", "run", streamlit_app_path, "--server.port=8501", "--server.address=0.0.0.0"]
    sys.exit(stcli.main())

if __name__ == "__main__":
    main()