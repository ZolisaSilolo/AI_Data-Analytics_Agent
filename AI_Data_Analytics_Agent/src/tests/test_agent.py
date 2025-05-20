import os
import sys
import unittest
import pandas as pd
import json
from unittest.mock import patch, MagicMock
import pytest

# Add the src directory to the path so we can import our modules
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from agent.tools import (
    load_data, 
    generate_plot, 
    generate_bar_chart, 
    generate_heatmap, 
    summarize_data, 
    detect_outliers
)
from agent.chain import PandasAnalystChain

class TestTools(unittest.TestCase):
    """Test cases for the tools module"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Create a sample DataFrame for testing
        self.test_data = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 30, 40, 50],
            'category': ['A', 'B', 'A', 'B', 'A']
        })
        
        # Save the test data to a temporary CSV file
        self.test_csv_path = 'test_data.csv'
        self.test_data.to_csv(self.test_csv_path, index=False)
    
    def tearDown(self):
        """Tear down test fixtures"""
        # Remove the temporary CSV file
        if os.path.exists(self.test_csv_path):
            os.remove(self.test_csv_path)
    
    def test_load_data(self):
        """Test loading data from a CSV file"""
        df = load_data(self.test_csv_path)
        self.assertEqual(len(df), 5)
        self.assertEqual(list(df.columns), ['x', 'y', 'category'])
    
    def test_generate_plot(self):
        """Test generating a plot"""
        data = {'x': [1, 2, 3], 'y': [10, 20, 30]}
        plot_dict = generate_plot(data)
        self.assertIsInstance(plot_dict, dict)
        self.assertIn('data', plot_dict)
        self.assertIn('layout', plot_dict)
    
    def test_generate_bar_chart(self):
        """Test generating a bar chart"""
        chart_dict = generate_bar_chart(self.test_data, 'x', 'y', title="Test Bar Chart")
        self.assertIsInstance(chart_dict, dict)
        self.assertIn('data', chart_dict)
        self.assertIn('layout', chart_dict)
        self.assertEqual(chart_dict['layout']['title']['text'], "Test Bar Chart")
    
    def test_summarize_data(self):
        """Test summarizing data"""
        summary = summarize_data(self.test_data)
        self.assertEqual(summary['shape'], (5, 3))
        self.assertEqual(summary['columns'], ['x', 'y', 'category'])
        self.assertIn('numeric_summary', summary)
    
    def test_detect_outliers_iqr(self):
        """Test detecting outliers using IQR method"""
        # Create data with outliers
        outlier_data = pd.DataFrame({
            'values': [1, 2, 3, 4, 5, 100]  # 100 is an outlier
        })
        
        outliers = detect_outliers(outlier_data, 'values', method='iqr')
        self.assertEqual(len(outliers), 1)
        self.assertEqual(outliers.iloc[0]['values'], 100)
    
    def test_detect_outliers_invalid_method(self):
        """Test detecting outliers with invalid method"""
        with self.assertRaises(ValueError):
            detect_outliers(self.test_data, 'x', method='invalid_method')


class TestPandasAnalystChain(unittest.TestCase):
    """Test cases for the PandasAnalystChain class"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Mock environment variables
        self.env_patcher = patch.dict('os.environ', {
            'OPENAI_API_KEY': 'test_api_key',
            'DATA_BUCKET': 'test_bucket'
        })
        self.env_patcher.start()
        
        # Create a sample DataFrame for testing
        self.test_data = pd.DataFrame({
            'x': [1, 2, 3, 4, 5],
            'y': [10, 20, 30, 40, 50]
        })
    
    def tearDown(self):
        """Tear down test fixtures"""
        self.env_patcher.stop()
    
    @patch('boto3.client')
    def test_init(self, mock_boto3_client):
        """Test initialization of PandasAnalystChain"""
        chain = PandasAnalystChain()
        self.assertEqual(chain.openai_api_key, 'test_api_key')
        mock_boto3_client.assert_called_once_with('s3')
    
    @patch('boto3.client')
    def test_init_with_api_key(self, mock_boto3_client):
        """Test initialization with explicit API key"""
        chain = PandasAnalystChain(openai_api_key='explicit_key')
        self.assertEqual(chain.openai_api_key, 'explicit_key')
    
    @patch('boto3.client')
    def test_init_no_api_key(self, mock_boto3_client):
        """Test initialization with no API key"""
        # Remove API key from environment
        with patch.dict('os.environ', {}, clear=True):
            with self.assertRaises(ValueError):
                PandasAnalystChain()
    
    @patch('boto3.client')
    def test_load_data(self, mock_boto3_client):
        """Test loading data from S3"""
        # Mock S3 client and response
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        
        # Mock get_object response
        mock_body = MagicMock()
        mock_body.read.return_value = "x,y\n1,10\n2,20\n3,30\n4,40\n5,50"
        mock_s3.get_object.return_value = {'Body': mock_body}
        
        # Create chain and load data
        chain = PandasAnalystChain()
        with patch('pandas.read_csv', return_value=self.test_data):
            df = chain.load_data('test_bucket', 'test_key')
        
        # Verify S3 client was called correctly
        mock_s3.get_object.assert_called_once_with(Bucket='test_bucket', Key='test_key')
        
        # Verify DataFrame was returned
        self.assertIsInstance(df, pd.DataFrame)
        self.assertEqual(len(df), 5)
    
    @patch('boto3.client')
    def test_load_data_error(self, mock_boto3_client):
        """Test error handling when loading data from S3"""
        # Mock S3 client and error response
        mock_s3 = MagicMock()
        mock_boto3_client.return_value = mock_s3
        mock_s3.get_object.side_effect = Exception("S3 error")
        
        # Create chain and attempt to load data
        chain = PandasAnalystChain()
        with self.assertRaises(Exception):
            chain.load_data('test_bucket', 'test_key')


if __name__ == '__main__':
    unittest.main()