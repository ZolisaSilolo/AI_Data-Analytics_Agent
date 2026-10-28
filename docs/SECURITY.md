# Security Policy

## Reporting Security Issues

If you discover a security vulnerability within this project, please send an email to the project maintainers. **Do NOT create a public issue.**

## Security Best Practices

### 1. Credential Management
- Never commit API keys, passwords, or secrets to Git
- Use environment variables for sensitive configuration
- Example `.env.example` shows required variables without actual values
- Implement AWS IAM roles with least privilege

### 2. Input Validation
- All user input must be validated
- SQL queries use parameterized queries via DuckDB sandbox
- File uploads have size limits and content type validation

### 3. Secure Execution
- Use the DuckDB sandbox for all SQL execution
- Language model (Bedrock) only plans, never computes results
- All computations are traceable to tool executions

### 4. AWS Security
- Implement proper IAM roles and policies
- Use AWS KMS for encryption at rest
- Enable CloudTrail logging for audit trails
- Use VPC endpoints for private S3 access

### 5. Dependency Security
- Pin dependencies to specific versions (`requirements_lock.txt`)
- Regularly update dependencies to patch vulnerabilities
- Use Dependabot alerts for vulnerability detection
- Run security scans on dependencies

### 6. Network Security
- Use TLS/SSL for all external communications
- Implement rate limiting to prevent abuse
- Use security groups and network ACLs in AWS

## Security Controls

### Preventive Controls
- `.gitignore` blocks sensitive files
- Linting rules catch security anti-patterns
- Unit tests verify security invariants

### Detective Controls
- CloudWatch monitoring for anomalies
- S3 access logging
- Code scanning for secrets in commits

### Corrective Controls
- Automated rollback on deployment failures
- Incident response procedures
- Regular security audits

## Data Protection

### Data in Transit
- TLS 1.2+ for all external communications
- HTTPS for API endpoints
- S3 transfer acceleration for large files

### Data at Rest
- S3 bucket encryption enabled by default
- DynamoDB table encryption
- Regular backup and snapshot procedures

## Compliance Considerations

- AWS Well-Architected Framework
- SOC 2 principles
- GDPR data protection requirements

## Regular Security Activities

1. **Monthly**: Dependency vulnerability scanning
2. **Quarterly**: Security audit and IAM role review
3. **Bi-annually**: Penetration testing
4. **Annually**: Full security assessment

## Incident Response

- Maintain incident response plan
- Document security incidents
- Conduct post-incident reviews
- Implement corrective actions

## Developer Guidelines

1. Never hardcode credentials
2. Validate all user inputs
3. Use prepared statements for database queries
4. Implement proper error handling without information leakage
5. Log security-relevant events appropriately
6. Keep dependencies updated
7. Review code for security vulnerabilities
8. Follow the principle of least privilege