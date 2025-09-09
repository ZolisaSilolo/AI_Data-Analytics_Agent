# 🚀 Deployment Guide - AI Data Analytics Agent

## Prerequisites

### Required Tools
- AWS CLI v2.x
- SAM CLI v1.x
- Python 3.12+
- Docker (for local testing)
- Git

### AWS Account Setup
- AWS Account with appropriate permissions
- IAM user with deployment privileges
- AWS CLI configured with credentials

## Environment Configuration

### 1. Clone Repository
```bash
git clone https://github.com/ZolisaSilolo/AI_Data-Analytics_Agent.git
cd AI_Data-Analytics_Agent
```

### 2. Environment Variables
```bash
# Copy environment template
cp .env.example .env

# Configure required variables
NVIDIA_API_KEY=your_nvidia_api_key_here
AWS_ACCESS_KEY_ID=your_aws_access_key
AWS_SECRET_ACCESS_KEY=your_aws_secret_key
AWS_DEFAULT_REGION=us-east-1
DATA_BUCKET=ai-analytics-data-bucket-unique-name
```

### 3. Clean Setup
```bash
# Run automated setup script
./clean-setup.sh

# Activate virtual environment
source venv/bin/activate

# Install dependencies
make install
```

## Local Development

### Start Development Environment
```bash
# Start Streamlit application
make streamlit

# Run in development mode with hot reload
streamlit run src/streamlit_app.py --server.runOnSave true
```

### Local Testing
```bash
# Run unit tests
make test

# Run integration tests
pytest tests/ -v

# Test Lambda function locally
sam local start-api
```

## AWS Deployment

### 1. Build Application
```bash
# Build SAM application
sam build

# Validate CloudFormation template
sam validate
```

### 2. Deploy to AWS

#### First-time Deployment
```bash
# Guided deployment (interactive)
sam deploy --guided

# Follow prompts:
# - Stack Name: ai-data-analytics-agent
# - AWS Region: us-east-1
# - Parameter NvidiaApiKey: [Your API Key]
# - Parameter DataBucketName: [Unique bucket name]
# - Confirm changes before deploy: Y
# - Allow SAM CLI IAM role creation: Y
# - Save parameters to samconfig.toml: Y
```

#### Subsequent Deployments
```bash
# Deploy with saved configuration
sam deploy

# Deploy with parameter overrides
sam deploy --parameter-overrides \
  NvidiaApiKey=new_api_key \
  DataBucketName=new-bucket-name
```

### 3. Secure Deployment (Production)
```bash
# Deploy with security template
sam deploy --template-file template-secure.yaml \
  --stack-name ai-analytics-agent-prod \
  --capabilities CAPABILITY_IAM \
  --parameter-overrides \
    Environment=production \
    EnableVPC=true \
    EnableWAF=true
```

## Deployment Configurations

### Development Environment
```yaml
# samconfig-dev.toml
[default.deploy.parameters]
stack_name = "ai-analytics-agent-dev"
s3_bucket = "sam-deployment-bucket-dev"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
  "Environment=development",
  "LambdaMemorySize=512",
  "LambdaTimeout=60"
]
```

### Staging Environment
```yaml
# samconfig-staging.toml
[default.deploy.parameters]
stack_name = "ai-analytics-agent-staging"
s3_bucket = "sam-deployment-bucket-staging"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
  "Environment=staging",
  "LambdaMemorySize=1024",
  "LambdaTimeout=300",
  "EnableXRayTracing=true"
]
```

### Production Environment
```yaml
# samconfig-prod.toml
[default.deploy.parameters]
stack_name = "ai-analytics-agent-prod"
s3_bucket = "sam-deployment-bucket-prod"
region = "us-east-1"
capabilities = "CAPABILITY_IAM"
parameter_overrides = [
  "Environment=production",
  "LambdaMemorySize=1024",
  "LambdaTimeout=300",
  "EnableVPC=true",
  "EnableWAF=true",
  "EnableXRayTracing=true"
]
```

## Multi-Environment Deployment

### Deploy to Multiple Environments
```bash
# Development
sam deploy --config-env dev

# Staging
sam deploy --config-env staging

# Production
sam deploy --config-env prod
```

## Post-Deployment Configuration

### 1. Verify Deployment
```bash
# Check stack status
aws cloudformation describe-stacks \
  --stack-name ai-data-analytics-agent

# Test API endpoint
curl -X POST https://your-api-id.execute-api.region.amazonaws.com/Prod/analyze \
  -H "Content-Type: application/json" \
  -d '{"query": "test"}'
```

### 2. Configure Secrets
```bash
# Store NVIDIA API key in Secrets Manager
aws secretsmanager create-secret \
  --name nvidia-api-key \
  --description "NVIDIA Nemotron API Key" \
  --secret-string "your_api_key_here"

# Update Lambda environment variables
aws lambda update-function-configuration \
  --function-name ai-data-analytics-function \
  --environment Variables='{
    "NVIDIA_API_SECRET_NAME": "nvidia-api-key",
    "DATA_BUCKET": "your-data-bucket-name"
  }'
```

### 3. Set Up Monitoring
```bash
# Create CloudWatch dashboard
aws cloudwatch put-dashboard \
  --dashboard-name "AI-Analytics-Agent" \
  --dashboard-body file://monitoring/dashboard.json

# Set up alarms
aws cloudwatch put-metric-alarm \
  --alarm-name "Lambda-Errors" \
  --alarm-description "Lambda function errors" \
  --metric-name Errors \
  --namespace AWS/Lambda \
  --statistic Sum \
  --period 300 \
  --threshold 5 \
  --comparison-operator GreaterThanThreshold
```

## Rollback Procedures

### CloudFormation Rollback
```bash
# Automatic rollback on failure
sam deploy --on-failure ROLLBACK

# Manual rollback to previous version
aws cloudformation cancel-update-stack \
  --stack-name ai-data-analytics-agent

# Delete and recreate stack
aws cloudformation delete-stack \
  --stack-name ai-data-analytics-agent
```

### Lambda Function Rollback
```bash
# List function versions
aws lambda list-versions-by-function \
  --function-name ai-data-analytics-function

# Update alias to previous version
aws lambda update-alias \
  --function-name ai-data-analytics-function \
  --name LIVE \
  --function-version 2
```

## Troubleshooting

### Common Deployment Issues

#### 1. IAM Permissions
```bash
# Check IAM role policies
aws iam get-role-policy \
  --role-name ai-analytics-lambda-role \
  --policy-name LambdaExecutionPolicy

# Attach missing policies
aws iam attach-role-policy \
  --role-name ai-analytics-lambda-role \
  --policy-arn arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole
```

#### 2. S3 Bucket Issues
```bash
# Check bucket exists and permissions
aws s3 ls s3://your-bucket-name

# Create bucket if missing
aws s3 mb s3://your-bucket-name --region us-east-1

# Set bucket policy
aws s3api put-bucket-policy \
  --bucket your-bucket-name \
  --policy file://policies/s3-bucket-policy.json
```

#### 3. API Gateway Issues
```bash
# Check API Gateway deployment
aws apigateway get-deployments \
  --rest-api-id your-api-id

# Redeploy API
aws apigateway create-deployment \
  --rest-api-id your-api-id \
  --stage-name Prod
```

### Debugging Commands
```bash
# View CloudFormation events
aws cloudformation describe-stack-events \
  --stack-name ai-data-analytics-agent

# Check Lambda logs
aws logs describe-log-groups \
  --log-group-name-prefix /aws/lambda/ai-data-analytics

# Tail Lambda logs
sam logs --name AnalyticsFunction --stack-name ai-data-analytics-agent --tail
```

## Performance Tuning

### Lambda Optimization
```bash
# Update Lambda memory and timeout
aws lambda update-function-configuration \
  --function-name ai-data-analytics-function \
  --memory-size 1536 \
  --timeout 300

# Enable provisioned concurrency
aws lambda put-provisioned-concurrency-config \
  --function-name ai-data-analytics-function \
  --qualifier $LATEST \
  --provisioned-concurrency-config ProvisionedConcurrencyUnits=5
```

### API Gateway Optimization
```bash
# Enable caching
aws apigateway put-method \
  --rest-api-id your-api-id \
  --resource-id resource-id \
  --http-method POST \
  --caching-enabled \
  --cache-ttl-in-seconds 300
```

## Security Hardening

### Enable VPC
```bash
# Deploy with VPC configuration
sam deploy --parameter-overrides EnableVPC=true

# Update security groups
aws ec2 authorize-security-group-ingress \
  --group-id sg-12345678 \
  --protocol tcp \
  --port 443 \
  --cidr 0.0.0.0/0
```

### Enable WAF
```bash
# Create WAF web ACL
aws wafv2 create-web-acl \
  --name ai-analytics-waf \
  --scope REGIONAL \
  --default-action Allow={} \
  --rules file://security/waf-rules.json

# Associate with API Gateway
aws wafv2 associate-web-acl \
  --web-acl-arn arn:aws:wafv2:region:account:webacl/name/id \
  --resource-arn arn:aws:apigateway:region::/restapis/api-id/stages/stage-name
```

## Cleanup

### Remove Deployment
```bash
# Delete CloudFormation stack
sam delete --stack-name ai-data-analytics-agent

# Clean up S3 bucket
aws s3 rm s3://your-bucket-name --recursive
aws s3 rb s3://your-bucket-name

# Remove secrets
aws secretsmanager delete-secret \
  --secret-id nvidia-api-key \
  --force-delete-without-recovery
```
