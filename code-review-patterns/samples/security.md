# Review Pattern: Infrastructure Security

## What to Check

### Secrets management
- No hardcoded secrets, passwords, or API keys in CDK code
- Secrets are managed via AWS Secrets Manager
- Secret ARNs are referenced, not secret values
- Environment variables for secrets reference Secrets Manager, not plaintext

### Network security
- Security groups follow least-privilege (only necessary ports open)
- RDS is not publicly accessible
- Database is in private subnets
- ALB security group only allows necessary inbound traffic (80, 443)
- ECS tasks have minimal required network access

### S3 security
- S3 buckets block public access
- Bucket policies follow least-privilege
- Encryption is enabled (at rest)

### IAM
- ECS task roles follow least-privilege
- No wildcard (`*`) resource permissions unless justified
- No `AdministratorAccess` or overly broad managed policies

### Database
- RDS encryption at rest is enabled
- Deletion protection is considered
- Backup retention is configured

## How to Review

1. Use Glob to find CDK stack files under `infra/`
2. Read the main stack definition
3. Use Grep to search for hardcoded strings that look like secrets
4. Use Grep to search for `publiclyAccessible`, `blockPublicAccess`, security group rules
5. Check IAM policy statements for overly broad permissions
6. Verify Secrets Manager references
