# Review Pattern: Infrastructure Reliability

## What to Check

### Health checks
- ECS services have health check configurations
- ALB target groups have health check paths configured
- Health check intervals and thresholds are reasonable

### Auto-scaling
- ECS service has auto-scaling policies (or a plan for them)
- Min/max task counts are configured appropriately
- Scaling metrics are appropriate (CPU, memory, request count)

### High availability
- Multi-AZ deployment for RDS
- ECS tasks spread across availability zones
- ALB is configured for multiple AZs

### Backup and retention
- RDS automated backups are enabled
- Backup retention period is set
- Point-in-time recovery is considered

### Logging and monitoring
- CloudWatch logging is enabled for ECS tasks
- Log retention periods are set
- ALB access logging is considered

### Deployment safety
- ECS deployment configuration allows rolling updates
- Circuit breaker is enabled for deployments
- Minimum healthy percent is configured

## How to Review

1. Use Glob to find CDK stack files under `infra/`
2. Read the ECS service and task definitions
3. Check ALB and target group health check configuration
4. Review RDS instance configuration for multi-AZ and backups
5. Use Grep to search for auto-scaling configuration
6. Check CloudWatch log group configuration
