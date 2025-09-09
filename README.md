# 🦁 Pandas Data Analyst Agent

[![AWS](https://img.shields.io/badge/AWS-Lambda-orange)](https://aws.amazon.com/lambda/)
[![Python](https://img.shields.io/badge/Python-3.12-blue)](https://python.org)
[![NVIDIA](https://img.shields.io/badge/AI-NVIDIA%20Nemotron-green)](https://nvidia.com)

> *AI-powered data analysis agent built with AWS serverless architecture*

## 🚀 Quick Start

```bash
# Clone and setup
git clone https://github.com/ZolisaSilolo/AI_Data-Analytics_Agent.git
cd AI_Data-Analytics_Agent

# Run clean setup
./clean-setup.sh

# Configure environment
cp .env.example .env
# Edit .env with your API keys

# Start development
source venv/bin/activate
make streamlit
```

## ✨ Features

- 🤖 **NVIDIA Nemotron AI** for natural language data analysis
- ⚡ **AWS Lambda** serverless compute with optimized performance
- 🎨 **Streamlit** interactive web interface
- 📊 **Plotly** advanced visualizations
- 🔒 **Enterprise security** with rate limiting and JWT
- 🚀 **High performance** with caching and PyArrow optimization
- 🛡️ **Security hardened** with cfn-nag compliance

## 📊 Architecture

- **Frontend**: Streamlit web application with caching
- **Backend**: AWS Lambda with connection pooling and container reuse
- **AI**: NVIDIA Nemotron for analysis
- **Storage**: AWS S3 with encryption and lifecycle policies
- **Security**: AWS Secrets Manager, VPC, and comprehensive logging

## 🛠 Development

```bash
# Install dependencies
make install

# Run tests
make test

# Start local development
make streamlit

# Deploy to AWS
sam build && sam deploy --guided
```

## 📝 Environment Variables

Copy `.env.example` to `.env` and configure:

- `NVIDIA_API_KEY`: Your NVIDIA API key
- `AWS_ACCESS_KEY_ID`: AWS access key
- `AWS_SECRET_ACCESS_KEY`: AWS secret key
- `DATA_BUCKET`: S3 bucket name

## 🔒 Security

- Environment variables in `.env` (gitignored)
- AWS credentials stored separately
- API keys managed via AWS Secrets Manager
- Rate limiting and input validation
- VPC configuration and comprehensive logging

## 📄 License

MIT License - See LICENSE file for details
