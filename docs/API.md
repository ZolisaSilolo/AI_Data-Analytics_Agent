# 🔌 API Documentation - AI Data Analytics Agent

## Overview

The AI Data Analytics Agent provides a RESTful API for data analysis and visualization powered by NVIDIA Nemotron AI. The API is built on AWS API Gateway and Lambda for serverless scalability.

## Base URL

```
https://{api-id}.execute-api.{region}.amazonaws.com/Prod
```

## Authentication

### API Key Authentication
```http
X-API-Key: your-api-key-here
```

### JWT Token Authentication
```http
Authorization: Bearer your-jwt-token-here
```

## Rate Limiting

- **Requests per minute**: 100
- **Requests per hour**: 1000
- **Burst limit**: 200

Rate limit headers are included in responses:
```http
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
X-RateLimit-Reset: 1640995200
```

## Endpoints

### 1. Data Analysis

#### POST /analyze
Analyze uploaded data with natural language queries.

**Request:**
```http
POST /analyze
Content-Type: multipart/form-data

{
  "file": [binary data],
  "query": "What are the top 5 sales regions?",
  "analysis_type": "descriptive",
  "output_format": "json"
}
```

**Parameters:**
- `file` (required): CSV or Excel file (max 10MB)
- `query` (required): Natural language analysis query
- `analysis_type` (optional): `descriptive`, `predictive`, `diagnostic`
- `output_format` (optional): `json`, `csv`, `html`

**Response:**
```json
{
  "status": "success",
  "analysis_id": "uuid-12345",
  "query": "What are the top 5 sales regions?",
  "results": {
    "summary": "Analysis of sales data by region",
    "insights": [
      "North America leads with 45% of total sales",
      "Europe follows with 32% of total sales",
      "Asia-Pacific shows 18% growth year-over-year"
    ],
    "data": [
      {"region": "North America", "sales": 450000, "percentage": 45},
      {"region": "Europe", "sales": 320000, "percentage": 32},
      {"region": "Asia-Pacific", "sales": 180000, "percentage": 18}
    ],
    "visualizations": [
      {
        "type": "bar_chart",
        "title": "Sales by Region",
        "data_url": "https://s3.amazonaws.com/bucket/charts/chart-123.json"
      }
    ]
  },
  "metadata": {
    "processing_time": 2.5,
    "rows_processed": 10000,
    "columns_analyzed": 8,
    "ai_model": "nvidia-nemotron-4-340b"
  }
}
```

### 2. Data Upload

#### POST /upload
Upload data files for analysis.

**Request:**
```http
POST /upload
Content-Type: multipart/form-data

{
  "file": [binary data],
  "filename": "sales_data.csv",
  "description": "Q3 sales data for analysis"
}
```

**Response:**
```json
{
  "status": "success",
  "file_id": "uuid-67890",
  "filename": "sales_data.csv",
  "size": 2048576,
  "rows": 10000,
  "columns": 8,
  "upload_url": "https://s3.amazonaws.com/bucket/uploads/uuid-67890.csv",
  "preview": [
    {"region": "North America", "sales": 45000, "date": "2024-01-01"},
    {"region": "Europe", "sales": 32000, "date": "2024-01-01"}
  ]
}
```

### 3. Visualization

#### GET /visualize/{analysis_id}
Generate visualizations for analysis results.

**Request:**
```http
GET /visualize/uuid-12345?chart_type=bar&format=plotly
```

**Parameters:**
- `chart_type` (optional): `bar`, `line`, `scatter`, `pie`, `heatmap`
- `format` (optional): `plotly`, `matplotlib`, `d3`
- `width` (optional): Chart width in pixels
- `height` (optional): Chart height in pixels

**Response:**
```json
{
  "status": "success",
  "chart_id": "chart-123",
  "chart_type": "bar",
  "chart_url": "https://s3.amazonaws.com/bucket/charts/chart-123.html",
  "chart_data": {
    "data": [...],
    "layout": {...},
    "config": {...}
  },
  "metadata": {
    "generated_at": "2024-01-01T12:00:00Z",
    "format": "plotly",
    "dimensions": {"width": 800, "height": 600}
  }
}
```

### 4. Query History

#### GET /history
Retrieve analysis history for the user.

**Request:**
```http
GET /history?limit=10&offset=0&start_date=2024-01-01&end_date=2024-01-31
```

**Parameters:**
- `limit` (optional): Number of results (default: 10, max: 100)
- `offset` (optional): Pagination offset (default: 0)
- `start_date` (optional): Filter by start date (ISO 8601)
- `end_date` (optional): Filter by end date (ISO 8601)

**Response:**
```json
{
  "status": "success",
  "total": 25,
  "limit": 10,
  "offset": 0,
  "analyses": [
    {
      "analysis_id": "uuid-12345",
      "query": "What are the top 5 sales regions?",
      "created_at": "2024-01-01T12:00:00Z",
      "status": "completed",
      "processing_time": 2.5,
      "file_name": "sales_data.csv"
    }
  ]
}
```

### 5. Health Check

#### GET /health
Check API health and status.

**Request:**
```http
GET /health
```

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00Z",
  "version": "1.0.0",
  "services": {
    "lambda": "healthy",
    "s3": "healthy",
    "nvidia_api": "healthy",
    "secrets_manager": "healthy"
  },
  "metrics": {
    "uptime": 86400,
    "requests_per_minute": 45,
    "average_response_time": 1.2
  }
}
```

## Error Handling

### Error Response Format
```json
{
  "status": "error",
  "error": {
    "code": "INVALID_REQUEST",
    "message": "The request is invalid or malformed",
    "details": "Missing required parameter: query",
    "timestamp": "2024-01-01T12:00:00Z",
    "request_id": "req-12345"
  }
}
```

### Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_REQUEST` | 400 | Request is malformed or missing required parameters |
| `UNAUTHORIZED` | 401 | Invalid or missing authentication credentials |
| `FORBIDDEN` | 403 | Insufficient permissions for the requested operation |
| `NOT_FOUND` | 404 | Requested resource does not exist |
| `RATE_LIMITED` | 429 | Rate limit exceeded |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds size limit |
| `UNSUPPORTED_FORMAT` | 415 | File format not supported |
| `PROCESSING_ERROR` | 422 | Error processing the data or query |
| `INTERNAL_ERROR` | 500 | Internal server error |
| `SERVICE_UNAVAILABLE` | 503 | Service temporarily unavailable |

## Data Formats

### Supported File Formats
- **CSV**: Comma-separated values
- **Excel**: .xlsx, .xls files
- **JSON**: JavaScript Object Notation
- **Parquet**: Apache Parquet format

### File Size Limits
- **Maximum file size**: 10MB
- **Maximum rows**: 100,000
- **Maximum columns**: 1,000

### Data Types
- **Numeric**: Integer, float, decimal
- **Text**: String, categorical
- **Date/Time**: ISO 8601 format
- **Boolean**: true/false values

## SDK Examples

### Python SDK
```python
import requests
import json

class AnalyticsClient:
    def __init__(self, api_key, base_url):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            'X-API-Key': api_key,
            'Content-Type': 'application/json'
        }
    
    def analyze_data(self, file_path, query):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            data = {'query': query}
            response = requests.post(
                f"{self.base_url}/analyze",
                files=files,
                data=data,
                headers={'X-API-Key': self.api_key}
            )
        return response.json()

# Usage
client = AnalyticsClient('your-api-key', 'https://api.example.com/Prod')
result = client.analyze_data('data.csv', 'Show me sales trends')
print(result)
```

### JavaScript SDK
```javascript
class AnalyticsClient {
    constructor(apiKey, baseUrl) {
        this.apiKey = apiKey;
        this.baseUrl = baseUrl;
    }

    async analyzeData(file, query) {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('query', query);

        const response = await fetch(`${this.baseUrl}/analyze`, {
            method: 'POST',
            headers: {
                'X-API-Key': this.apiKey
            },
            body: formData
        });

        return await response.json();
    }
}

// Usage
const client = new AnalyticsClient('your-api-key', 'https://api.example.com/Prod');
const result = await client.analyzeData(fileInput.files[0], 'Show me sales trends');
console.log(result);
```

### cURL Examples
```bash
# Analyze data
curl -X POST "https://api.example.com/Prod/analyze" \
  -H "X-API-Key: your-api-key" \
  -F "file=@data.csv" \
  -F "query=What are the top performing products?"

# Get analysis history
curl -X GET "https://api.example.com/Prod/history?limit=5" \
  -H "X-API-Key: your-api-key"

# Health check
curl -X GET "https://api.example.com/Prod/health" \
  -H "X-API-Key: your-api-key"
```

## Webhooks

### Webhook Configuration
Configure webhooks to receive notifications when analysis is complete.

```json
{
  "webhook_url": "https://your-app.com/webhook",
  "events": ["analysis.completed", "analysis.failed"],
  "secret": "webhook-secret-key"
}
```

### Webhook Payload
```json
{
  "event": "analysis.completed",
  "analysis_id": "uuid-12345",
  "timestamp": "2024-01-01T12:00:00Z",
  "data": {
    "query": "What are the top 5 sales regions?",
    "status": "completed",
    "results_url": "https://api.example.com/Prod/results/uuid-12345"
  }
}
```

## Best Practices

### Performance Optimization
1. **File Preprocessing**: Clean and optimize data before upload
2. **Query Optimization**: Use specific, focused queries
3. **Caching**: Leverage response caching for repeated queries
4. **Batch Processing**: Group multiple queries when possible

### Security Best Practices
1. **API Key Management**: Rotate keys regularly
2. **HTTPS Only**: Always use encrypted connections
3. **Input Validation**: Validate all input data
4. **Rate Limiting**: Respect rate limits and implement backoff

### Error Handling
1. **Retry Logic**: Implement exponential backoff for retries
2. **Timeout Handling**: Set appropriate request timeouts
3. **Error Logging**: Log errors for debugging
4. **Graceful Degradation**: Handle service unavailability

## Support

For API support and questions:
- **Documentation**: [API Docs](https://docs.example.com)
- **Status Page**: [Status](https://status.example.com)
- **Support Email**: support@example.com
- **GitHub Issues**: [Issues](https://github.com/ZolisaSilolo/AI_Data-Analytics_Agent/issues)
