# 🔒 Security Documentation - AI Data Analytics Agent

## Security Overview

The AI Data Analytics Agent implements comprehensive security measures across all layers of the architecture, following AWS Well-Architected Framework security principles and industry best practices.

## Security Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   CloudFront    │    │      WAF         │    │  API Gateway    │
│   + Shield      │◄──►│   Protection     │◄──►│  Rate Limiting  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   TLS 1.2+      │    │   JWT/API Keys   │    │   IAM Roles     │
│   Encryption    │    │   Authentication │    │   Permissions   │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
         │                       │                       │
         ▼                       ▼                       ▼
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Lambda VPC    │    │  Secrets Manager │    │   S3 Encryption │
│   Isolation     │    │   Key Storage    │    │   + Versioning  │
│                 │    │                  │    │                 │
└─────────────────┘    └──────────────────┘    └─────────────────┘
```

## Authentication & Authorization

### API Authentication Methods

#### 1. API Key Authentication
```http
X-API-Key: ak_1234567890abcdef
```

**Features:**
- Unique keys per client
- Automatic rotation capability
- Usage tracking and analytics
- Rate limiting per key

#### 2. JWT Token Authentication
```http
Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
```

**JWT Claims:**
```json
{
  "sub": "user-12345",
  "iss": "ai-analytics-agent",
  "aud": "api.analytics.com",
  "exp": 1640995200,
  "iat": 1640991600,
  "scope": ["read:data", "write:analysis"],
  "role": "analyst"
}
```

### IAM Roles and Policies

#### Lambda Execution Role
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "logs:CreateLogGroup",
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": "arn:aws:logs:*:*:*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject",
        "s3:PutObject",
        "s3:DeleteObject"
      ],
      "Resource": "arn:aws:s3:::ai-analytics-data-bucket/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:*:*:secret:nvidia-api-key-*"
    }
  ]
}
```

#### API Gateway Resource Policy
```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": "*",
      "Action": "execute-api:Invoke",
      "Resource": "arn:aws:execute-api:*:*:*/*/POST/analyze",
      "Condition": {
        "IpAddress": {
          "aws:SourceIp": ["203.0.113.0/24", "198.51.100.0/24"]
        }
      }
    }
  ]
}
```

## Data Protection

### Encryption at Rest

#### S3 Bucket Encryption
```yaml
BucketEncryption:
  ServerSideEncryptionConfiguration:
    - ServerSideEncryptionByDefault:
        SSEAlgorithm: AES256
        KMSMasterKeyID: alias/ai-analytics-key
      BucketKeyEnabled: true
```

#### Lambda Environment Variables
```yaml
Environment:
  Variables:
    NVIDIA_API_SECRET_NAME: !Ref NvidiaApiKeySecret
    DATA_BUCKET: !Ref DataBucket
  KmsKeyArn: !GetAtt LambdaKMSKey.Arn
```

### Encryption in Transit

#### TLS Configuration
- **Minimum Version**: TLS 1.2
- **Cipher Suites**: ECDHE-RSA-AES256-GCM-SHA384, ECDHE-RSA-AES128-GCM-SHA256
- **Certificate**: AWS Certificate Manager (ACM)
- **HSTS**: Enabled with max-age=31536000

#### API Gateway SSL
```yaml
DomainName:
  Type: AWS::ApiGateway::DomainName
  Properties:
    DomainName: api.analytics.com
    CertificateArn: !Ref SSLCertificate
    SecurityPolicy: TLS_1_2
    EndpointConfiguration:
      Types:
        - EDGE
```

### Data Classification

#### Sensitivity Levels
1. **Public**: Non-sensitive operational data
2. **Internal**: Business data for internal use
3. **Confidential**: Sensitive business data
4. **Restricted**: Highly sensitive data requiring special handling

#### Data Handling Matrix
| Level | Encryption | Access Control | Retention | Monitoring |
|-------|------------|----------------|-----------|------------|
| Public | Optional | Basic | 1 year | Standard |
| Internal | Required | Role-based | 3 years | Enhanced |
| Confidential | Required + KMS | Strict RBAC | 7 years | Full audit |
| Restricted | Required + HSM | Multi-factor | 10 years | Real-time |

## Network Security

### VPC Configuration
```yaml
VPC:
  Type: AWS::EC2::VPC
  Properties:
    CidrBlock: 10.0.0.0/16
    EnableDnsHostnames: true
    EnableDnsSupport: true

PrivateSubnet:
  Type: AWS::EC2::Subnet
  Properties:
    VpcId: !Ref VPC
    CidrBlock: 10.0.1.0/24
    AvailabilityZone: !Select [0, !GetAZs '']

SecurityGroup:
  Type: AWS::EC2::SecurityGroup
  Properties:
    GroupDescription: Lambda security group
    VpcId: !Ref VPC
    SecurityGroupEgress:
      - IpProtocol: tcp
        FromPort: 443
        ToPort: 443
        CidrIp: 0.0.0.0/0
        Description: HTTPS outbound
```

### Web Application Firewall (WAF)

#### WAF Rules
```json
{
  "Rules": [
    {
      "Name": "AWSManagedRulesCommonRuleSet",
      "Priority": 1,
      "Statement": {
        "ManagedRuleGroupStatement": {
          "VendorName": "AWS",
          "Name": "AWSManagedRulesCommonRuleSet"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "CommonRuleSetMetric"
      }
    },
    {
      "Name": "RateLimitRule",
      "Priority": 2,
      "Statement": {
        "RateBasedStatement": {
          "Limit": 2000,
          "AggregateKeyType": "IP"
        }
      },
      "Action": {"Block": {}},
      "VisibilityConfig": {
        "SampledRequestsEnabled": true,
        "CloudWatchMetricsEnabled": true,
        "MetricName": "RateLimitMetric"
      }
    }
  ]
}
```

### DDoS Protection
- **AWS Shield Standard**: Automatic protection against common attacks
- **AWS Shield Advanced**: Enhanced protection with 24/7 DRT support
- **CloudFront**: Geographic distribution and caching
- **Route 53**: DNS-level protection

## Input Validation & Sanitization

### File Upload Validation
```python
import magic
import pandas as pd
from typing import List, Dict, Any

class FileValidator:
    ALLOWED_TYPES = ['text/csv', 'application/vnd.ms-excel', 
                     'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet']
    MAX_FILE_SIZE = 10 * 1024 * 1024  # 10MB
    MAX_ROWS = 100000
    MAX_COLUMNS = 1000
    
    @staticmethod
    def validate_file(file_content: bytes, filename: str) -> Dict[str, Any]:
        # Check file size
        if len(file_content) > FileValidator.MAX_FILE_SIZE:
            raise ValueError("File size exceeds maximum limit")
        
        # Check MIME type
        mime_type = magic.from_buffer(file_content, mime=True)
        if mime_type not in FileValidator.ALLOWED_TYPES:
            raise ValueError(f"Unsupported file type: {mime_type}")
        
        # Validate file structure
        try:
            if filename.endswith('.csv'):
                df = pd.read_csv(io.BytesIO(file_content))
            else:
                df = pd.read_excel(io.BytesIO(file_content))
            
            if len(df) > FileValidator.MAX_ROWS:
                raise ValueError("File contains too many rows")
            
            if len(df.columns) > FileValidator.MAX_COLUMNS:
                raise ValueError("File contains too many columns")
                
            return {"valid": True, "rows": len(df), "columns": len(df.columns)}
            
        except Exception as e:
            raise ValueError(f"Invalid file format: {str(e)}")
```

### Query Sanitization
```python
import re
from typing import str

class QuerySanitizer:
    # Dangerous patterns to block
    BLOCKED_PATTERNS = [
        r'<script.*?>.*?</script>',  # XSS
        r'javascript:',              # JavaScript injection
        r'data:text/html',          # Data URI XSS
        r'vbscript:',               # VBScript injection
        r'on\w+\s*=',               # Event handlers
    ]
    
    @staticmethod
    def sanitize_query(query: str) -> str:
        # Remove potentially dangerous patterns
        for pattern in QuerySanitizer.BLOCKED_PATTERNS:
            query = re.sub(pattern, '', query, flags=re.IGNORECASE)
        
        # Limit query length
        if len(query) > 1000:
            raise ValueError("Query too long")
        
        # Basic HTML encoding
        query = query.replace('<', '&lt;').replace('>', '&gt;')
        
        return query.strip()
```

## Secrets Management

### AWS Secrets Manager Integration
```python
import boto3
import json
from botocore.exceptions import ClientError

class SecretsManager:
    def __init__(self, region_name: str):
        self.client = boto3.client('secretsmanager', region_name=region_name)
    
    def get_secret(self, secret_name: str) -> str:
        try:
            response = self.client.get_secret_value(SecretId=secret_name)
            return response['SecretString']
        except ClientError as e:
            if e.response['Error']['Code'] == 'DecryptionFailureException':
                raise e
            elif e.response['Error']['Code'] == 'InternalServiceErrorException':
                raise e
            elif e.response['Error']['Code'] == 'InvalidParameterException':
                raise e
            elif e.response['Error']['Code'] == 'InvalidRequestException':
                raise e
            elif e.response['Error']['Code'] == 'ResourceNotFoundException':
                raise e
    
    def rotate_secret(self, secret_name: str) -> bool:
        try:
            self.client.rotate_secret(SecretId=secret_name)
            return True
        except ClientError:
            return False
```

### Secret Rotation Policy
```yaml
NvidiaApiKeySecret:
  Type: AWS::SecretsManager::Secret
  Properties:
    Name: nvidia-api-key
    Description: NVIDIA Nemotron API Key
    GenerateSecretString:
      SecretStringTemplate: '{"api_key": ""}'
      GenerateStringKey: api_key
      PasswordLength: 64
      ExcludeCharacters: '"@/\'
    ReplicaRegions:
      - Region: us-west-2
        KmsKeyId: alias/secrets-key

SecretRotationSchedule:
  Type: AWS::SecretsManager::RotationSchedule
  Properties:
    SecretId: !Ref NvidiaApiKeySecret
    RotationLambdaArn: !GetAtt RotationLambda.Arn
    RotationRules:
      AutomaticallyAfterDays: 30
```

## Monitoring & Alerting

### Security Monitoring
```yaml
SecurityAlarms:
  UnauthorizedAPICallsAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: UnauthorizedAPICalls
      AlarmDescription: Unauthorized API calls detected
      MetricName: 4XXError
      Namespace: AWS/ApiGateway
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 2
      Threshold: 10
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SecurityTopic

  HighErrorRateAlarm:
    Type: AWS::CloudWatch::Alarm
    Properties:
      AlarmName: HighErrorRate
      AlarmDescription: High error rate detected
      MetricName: 5XXError
      Namespace: AWS/ApiGateway
      Statistic: Sum
      Period: 300
      EvaluationPeriods: 3
      Threshold: 5
      ComparisonOperator: GreaterThanThreshold
      AlarmActions:
        - !Ref SecurityTopic
```

### Audit Logging
```python
import json
import logging
from datetime import datetime
from typing import Dict, Any

class SecurityLogger:
    def __init__(self):
        self.logger = logging.getLogger('security')
        self.logger.setLevel(logging.INFO)
    
    def log_authentication_event(self, user_id: str, event_type: str, 
                                success: bool, ip_address: str, 
                                user_agent: str) -> None:
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'authentication',
            'sub_type': event_type,
            'user_id': user_id,
            'success': success,
            'ip_address': ip_address,
            'user_agent': user_agent,
            'severity': 'INFO' if success else 'WARNING'
        }
        self.logger.info(json.dumps(event))
    
    def log_data_access(self, user_id: str, resource: str, 
                       action: str, success: bool) -> None:
        event = {
            'timestamp': datetime.utcnow().isoformat(),
            'event_type': 'data_access',
            'user_id': user_id,
            'resource': resource,
            'action': action,
            'success': success,
            'severity': 'INFO' if success else 'ERROR'
        }
        self.logger.info(json.dumps(event))
```

## Compliance & Governance

### Compliance Frameworks
- **SOC 2 Type II**: Security, availability, processing integrity
- **ISO 27001**: Information security management
- **GDPR**: Data protection and privacy
- **HIPAA**: Healthcare data protection (if applicable)
- **PCI DSS**: Payment card data security (if applicable)

### Data Retention Policies
```yaml
DataRetentionPolicy:
  UserData:
    RetentionPeriod: 7 years
    ArchiveAfter: 1 year
    DeleteAfter: 7 years
  
  LogData:
    RetentionPeriod: 2 years
    ArchiveAfter: 90 days
    DeleteAfter: 2 years
  
  AnalyticsResults:
    RetentionPeriod: 5 years
    ArchiveAfter: 6 months
    DeleteAfter: 5 years
```

### Privacy Controls
```python
class PrivacyController:
    @staticmethod
    def anonymize_data(df: pd.DataFrame, pii_columns: List[str]) -> pd.DataFrame:
        """Anonymize PII data in DataFrame"""
        for column in pii_columns:
            if column in df.columns:
                df[column] = df[column].apply(lambda x: hashlib.sha256(str(x).encode()).hexdigest()[:8])
        return df
    
    @staticmethod
    def mask_sensitive_data(data: str, mask_char: str = '*') -> str:
        """Mask sensitive data for logging"""
        if len(data) <= 4:
            return mask_char * len(data)
        return data[:2] + mask_char * (len(data) - 4) + data[-2:]
```

## Incident Response

### Security Incident Response Plan

#### 1. Detection & Analysis
- **Automated Detection**: CloudWatch alarms and AWS GuardDuty
- **Manual Detection**: Security team monitoring and user reports
- **Analysis Tools**: AWS CloudTrail, VPC Flow Logs, WAF logs

#### 2. Containment & Eradication
```bash
# Emergency response commands
# Disable compromised API key
aws apigateway update-api-key --api-key compromised-key-id --patch-ops op=replace,path=/enabled,value=false

# Block suspicious IP addresses
aws wafv2 update-ip-set --scope REGIONAL --id suspicious-ips --addresses 203.0.113.1/32,198.51.100.1/32

# Rotate compromised secrets
aws secretsmanager rotate-secret --secret-id nvidia-api-key

# Scale down Lambda concurrency
aws lambda put-provisioned-concurrency-config --function-name analytics-function --provisioned-concurrency-config ProvisionedConcurrencyUnits=0
```

#### 3. Recovery & Post-Incident
- **System Restoration**: Restore from known good backups
- **Monitoring**: Enhanced monitoring during recovery period
- **Documentation**: Incident report and lessons learned
- **Process Improvement**: Update security controls and procedures

## Security Testing

### Automated Security Scanning
```yaml
# cfn-nag security scanning
cfn_nag_scan --input-path template.yaml --output-format json

# OWASP ZAP API security testing
zap-api-scan.py -t https://api.example.com/openapi.json -f openapi

# AWS Config compliance checking
aws configservice get-compliance-details-by-config-rule --config-rule-name required-tags
```

### Penetration Testing
- **Frequency**: Quarterly external penetration testing
- **Scope**: API endpoints, authentication, authorization
- **Tools**: OWASP ZAP, Burp Suite, custom scripts
- **Reporting**: Detailed findings with remediation recommendations

## Security Best Practices

### Development Security
1. **Secure Coding**: Follow OWASP secure coding practices
2. **Code Review**: Mandatory security-focused code reviews
3. **Static Analysis**: Automated SAST scanning in CI/CD
4. **Dependency Scanning**: Regular vulnerability scanning of dependencies

### Operational Security
1. **Principle of Least Privilege**: Minimal required permissions
2. **Defense in Depth**: Multiple layers of security controls
3. **Regular Updates**: Keep all components updated
4. **Security Training**: Regular security awareness training

### Monitoring & Response
1. **Continuous Monitoring**: 24/7 security monitoring
2. **Incident Response**: Documented response procedures
3. **Regular Audits**: Periodic security assessments
4. **Compliance Reporting**: Regular compliance status reports

## Contact Information

### Security Team
- **Security Email**: security@example.com
- **Incident Response**: incident-response@example.com
- **24/7 Hotline**: +1-555-SECURITY
- **PGP Key**: Available at https://example.com/security/pgp-key.asc
