# Deployment Guide

This guide covers deploying the Whisper App to production environments with best practices for monitoring, maintenance, and updates.

## Table of Contents

1. [Pre-deployment Checklist](#pre-deployment-checklist)
2. [Initial Deployment](#initial-deployment)
3. [SSL/TLS Configuration](#ssltls-configuration)
4. [Monitoring Setup](#monitoring-setup)
5. [Backup Configuration](#backup-configuration)
6. [Scaling Considerations](#scaling-considerations)
7. [Update Procedures](#update-procedures)
8. [Rollback Procedures](#rollback-procedures)
9. [Maintenance Tasks](#maintenance-tasks)

## Pre-deployment Checklist

### Infrastructure Requirements

- [ ] **Server provisioned** with minimum specs:
  - 8+ CPU cores
  - 32GB+ RAM
  - 100GB+ disk space
  - NVIDIA GPU with 20-30GB VRAM
- [ ] **NVIDIA drivers installed** (version 525.60.13+)
- [ ] **NVIDIA Container Toolkit** installed and configured
- [ ] **Docker** (24.0+) and Docker Compose (2.20+) installed
- [ ] **Domain name** registered and DNS configured
- [ ] **Firewall** configured (ports 80, 443 open)
- [ ] **SSL certificates** ready (Let's Encrypt or commercial)

### Configuration

- [ ] `.env` file created with production values
- [ ] Strong passwords generated for database and Redis
- [ ] `SECRET_KEY` generated (32+ random bytes)
- [ ] LDAP server details configured
- [ ] Domain name configured in Nginx
- [ ] SSL email configured for Let's Encrypt
- [ ] Backup retention policy set
- [ ] File retention hours configured

### Security

- [ ] All passwords use strong random values
- [ ] `SECRET_KEY` is unique and not exposed
- [ ] LDAP bind credentials secured
- [ ] Database exposed only to Docker network
- [ ] Redis exposed only to Docker network
- [ ] Firewall rules tested
- [ ] SSL/TLS certificates valid

### Testing

- [ ] Development environment tested
- [ ] All migrations applied successfully
- [ ] Backend tests passing (pytest)
- [ ] Frontend tests passing (npm test)
- [ ] Integration tests passing
- [ ] LDAP authentication tested

## Initial Deployment

### Step 1: Prepare the Server

```bash
# Update system
sudo apt-get update && sudo apt-get upgrade -y

# Install required packages
sudo apt-get install -y git curl wget ufw

# Configure firewall
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Install Docker (if not already installed)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### Step 2: Clone and Configure

```bash
# Clone repository
git clone https://github.com/your-org/whisper-app.git
cd whisper-app

# Switch to stable branch/tag
git checkout tags/v1.0.0  # Or: git checkout main

# Copy and configure environment
cp .env.example .env
nano .env  # Edit with production values

# Generate secure secrets
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -base64 32)

# Update .env with generated secrets
sed -i "s/your_secret_key_here/$SECRET_KEY/" .env
sed -i "s/your_postgres_password/$POSTGRES_PASSWORD/" .env

# Update domain name
export DOMAIN=yourdomain.com
sed -i "s/yourdomain.com/$DOMAIN/g" .env
sed -i "s/yourdomain.com/$DOMAIN/g" nginx/nginx.prod.conf
```

### Step 3: Build Frontend

```bash
cd frontend

# Install dependencies
npm install

# Build for production
npm run build

cd ..
```

### Step 4: Prepare Data Directories

```bash
# Create directories
mkdir -p data/uploads data/results data/temp
mkdir -p backup
mkdir -p logs/nginx logs/backend logs/celery
mkdir -p certbot/conf certbot/www

# Set permissions
chmod 755 data backup logs certbot
```

### Step 5: Obtain SSL Certificate

#### Using Let's Encrypt

```bash
# Start nginx temporarily (HTTP only)
docker-compose -f docker-compose.prod.yml up -d nginx postgres redis

# Wait for nginx to be ready
sleep 10

# Obtain certificate
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# Verify certificate
ls -la certbot/conf/live/yourdomain.com/

# Stop temporary nginx
docker-compose -f docker-compose.prod.yml down
```

#### Using Existing Certificates

```bash
# Copy certificates
mkdir -p certbot/conf/live/yourdomain.com
cp /path/to/fullchain.pem certbot/conf/live/yourdomain.com/
cp /path/to/privkey.pem certbot/conf/live/yourdomain.com/
cp /path/to/chain.pem certbot/conf/live/yourdomain.com/

# Set permissions
chmod 600 certbot/conf/live/yourdomain.com/*.pem
```

### Step 6: Deploy Services

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# Monitor startup
docker-compose -f docker-compose.prod.yml logs -f

# Wait for services to be healthy
docker-compose -f docker-compose.prod.yml ps
```

### Step 7: Initialize Database

```bash
# Apply migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify tables created
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "\dt"

# Check migration status
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

### Step 8: Create Admin User

```bash
# Access database
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod

# Create admin user (will be created on first LDAP login, then promoted)
# After first LDAP login, run:
UPDATE users SET is_admin = true WHERE username = 'admin_username';

# Verify
SELECT id, username, email, is_admin FROM users;

# Exit
\q
```

### Step 9: Verify Deployment

Run all verification steps from [Verification](#verification-steps) section below.

## SSL/TLS Configuration

### Let's Encrypt Certificate Renewal

Certificates are automatically renewed by the certbot container. To test renewal:

```bash
# Test renewal (dry run)
docker-compose -f docker-compose.prod.yml run --rm certbot renew --dry-run

# Force renewal (if needed)
docker-compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Reload nginx after renewal
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### Certificate Renewal Cron Job

The certbot container automatically attempts renewal twice daily. Monitor logs:

```bash
docker-compose -f docker-compose.prod.yml logs certbot
```

### SSL Configuration Updates

To update SSL settings in Nginx:

```bash
# Edit nginx configuration
nano nginx/nginx.prod.conf

# Test configuration
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# Reload nginx
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Monitoring Setup

### Application Monitoring

#### Log Monitoring

```bash
# View real-time logs
docker-compose -f docker-compose.prod.yml logs -f

# View specific service logs
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
docker-compose -f docker-compose.prod.yml logs -f nginx

# Save logs to file
docker-compose -f docker-compose.prod.yml logs --no-color > logs/application-$(date +%Y%m%d).log
```

#### Health Check Monitoring

Create a monitoring script (`scripts/health-check.sh`):

```bash
#!/bin/bash
# Health check script for monitoring

DOMAIN="https://yourdomain.com"
ALERT_EMAIL="admin@yourdomain.com"

# Check health endpoint
if ! curl -sf "$DOMAIN/health" > /dev/null; then
    echo "Health check failed at $(date)" | mail -s "Whisper App Health Check Failed" $ALERT_EMAIL
    exit 1
fi

# Check SSL certificate expiration
EXPIRY_DATE=$(echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 7 ]; then
    echo "SSL certificate expires in $DAYS_UNTIL_EXPIRY days" | mail -s "Whisper App SSL Certificate Expiring" $ALERT_EMAIL
fi

echo "Health check passed at $(date)"
```

Add to cron:
```bash
# Run every 5 minutes
*/5 * * * * /path/to/whisper-app/scripts/health-check.sh >> /var/log/whisper-health.log 2>&1
```

### System Resource Monitoring

#### GPU Monitoring

```bash
# Watch GPU usage
watch -n 1 docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# Log GPU stats to file
while true; do
    docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi --query-gpu=timestamp,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.free --format=csv >> logs/gpu-stats-$(date +%Y%m%d).csv
    sleep 60
done
```

#### Container Resource Usage

```bash
# View container stats
docker stats

# Log container stats
docker stats --no-stream >> logs/container-stats-$(date +%Y%m%d).log
```

### Database Monitoring

```bash
# Check database size
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT pg_size_pretty(pg_database_size('whisper_prod')) AS db_size;
"

# Check table sizes
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# Check active connections
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';
"

# Check slow queries (if pg_stat_statements enabled)
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT query, calls, mean_exec_time, stddev_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

### Alerting

Consider integrating with monitoring tools:
- **Prometheus + Grafana**: For metrics visualization
- **ELK Stack (Elasticsearch, Logstash, Kibana)**: For log aggregation
- **Sentry**: For error tracking
- **PagerDuty/Opsgenie**: For incident management

## Backup Configuration

### Automated Backups

The backup service runs daily at 3:00 AM UTC. Configuration:

```bash
# View backup service status
docker-compose -f docker-compose.prod.yml ps backup

# View backup logs
docker-compose -f docker-compose.prod.yml logs backup

# List backups
ls -lh backup/

# Check latest backup
ls -lh backup/whisper_backup_latest.sql.gz
```

### Manual Backup

```bash
# Create manual backup
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# Backup with custom filename
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U whisper_prod whisper_prod | gzip > backup/manual_backup_${TIMESTAMP}.sql.gz
```

### Off-site Backup

Set up automated off-site backup:

```bash
#!/bin/bash
# scripts/offsite-backup.sh

BACKUP_DIR="/path/to/whisper-app/backup"
REMOTE_HOST="backup-server.example.com"
REMOTE_PATH="/backups/whisper-app"

# Sync backups to remote server
rsync -avz --delete \
  $BACKUP_DIR/ \
  user@$REMOTE_HOST:$REMOTE_PATH/

# Or upload to cloud storage (S3 example)
# aws s3 sync $BACKUP_DIR s3://your-bucket/whisper-backups/
```

Add to cron:
```bash
# Run daily at 4:00 AM (after backup completes)
0 4 * * * /path/to/whisper-app/scripts/offsite-backup.sh >> /var/log/offsite-backup.log 2>&1
```

### Restore from Backup

```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop backend celery-worker

# Restore database
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# Restart services
docker-compose -f docker-compose.prod.yml start backend celery-worker

# Verify restore
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

## Scaling Considerations

### Vertical Scaling

#### Increase Container Resources

Edit `docker-compose.prod.yml`:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '8'      # Increase from 4
          memory: 8G     # Increase from 4G

  celery-worker:
    deploy:
      resources:
        limits:
          cpus: '16'     # Increase from 8
          memory: 64G    # Increase from 32G
```

#### Increase Worker Processes

```yaml
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8  # Increase from 4
```

### Horizontal Scaling

#### Multiple Celery Workers

Add more Celery worker containers:

```yaml
services:
  celery-worker-1:
    <<: *celery-worker-config
    container_name: whisper-celery-worker-1
    environment:
      - CUDA_VISIBLE_DEVICES=0

  celery-worker-2:
    <<: *celery-worker-config
    container_name: whisper-celery-worker-2
    environment:
      - CUDA_VISIBLE_DEVICES=1  # Second GPU
```

#### Load Balancing

For multiple backend instances, add load balancer:

```yaml
services:
  backend-1:
    <<: *backend-config

  backend-2:
    <<: *backend-config

  nginx:
    # Update upstream configuration
    volumes:
      - ./nginx/nginx.lb.conf:/etc/nginx/nginx.conf:ro
```

Update `nginx/nginx.lb.conf`:
```nginx
upstream backend {
    least_conn;
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### Database Scaling

For high load, consider:
- **Read replicas**: For analytics queries
- **Connection pooling**: PgBouncer
- **Partitioning**: For large tables

## Update Procedures

### Pre-update Checklist

- [ ] **Backup created** and verified
- [ ] **Changelog reviewed** for breaking changes
- [ ] **Maintenance window scheduled**
- [ ] **Rollback plan prepared**
- [ ] **Team notified**

### Update Steps

```bash
# 1. Create backup
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# 2. Enable maintenance mode (optional)
# Create maintenance.html in nginx/html/
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 3. Pull latest code
git fetch origin
git checkout tags/v1.1.0  # Or specific version

# 4. Review changes
git log v1.0.0..v1.1.0

# 5. Update frontend
cd frontend
npm install
npm run build
cd ..

# 6. Stop services
docker-compose -f docker-compose.prod.yml down

# 7. Apply database migrations
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 8. Rebuild and restart services
docker-compose -f docker-compose.prod.yml up -d --build

# 9. Verify deployment
curl https://yourdomain.com/health

# 10. Disable maintenance mode
# Remove maintenance.html
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 11. Monitor logs
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### Zero-downtime Updates

For critical services, use blue-green deployment:

```bash
# 1. Deploy to new stack
docker-compose -f docker-compose.blue.yml up -d --build

# 2. Verify new stack
curl https://blue.yourdomain.com/health

# 3. Switch traffic (update DNS or load balancer)

# 4. Monitor for issues

# 5. If stable, decommission old stack
docker-compose -f docker-compose.green.yml down
```

## Rollback Procedures

### Immediate Rollback

If issues detected during update:

```bash
# 1. Stop current services
docker-compose -f docker-compose.prod.yml down

# 2. Checkout previous version
git checkout tags/v1.0.0

# 3. Restore database (if migrations applied)
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# 4. Rebuild and start services
docker-compose -f docker-compose.prod.yml up -d --build

# 5. Verify rollback
curl https://yourdomain.com/health
```

### Database Rollback

To rollback migrations:

```bash
# Downgrade to specific revision
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>

# Or downgrade one version
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# Verify
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

## Maintenance Tasks

### Daily Tasks

- [ ] Check service health (`docker-compose ps`)
- [ ] Review error logs
- [ ] Monitor disk usage
- [ ] Verify backup completed

### Weekly Tasks

- [ ] Review system resource usage
- [ ] Check SSL certificate expiration
- [ ] Review slow query logs
- [ ] Analyze task processing times
- [ ] Review user feedback/issues

### Monthly Tasks

- [ ] Update system packages
- [ ] Review and update Docker images
- [ ] Database maintenance (VACUUM, ANALYZE)
- [ ] Review access logs for anomalies
- [ ] Test disaster recovery procedures
- [ ] Review and update documentation

### Database Maintenance

```bash
# Run VACUUM and ANALYZE
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "VACUUM ANALYZE;"

# Check for bloated tables
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
"

# Reindex if needed
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "REINDEX DATABASE whisper_prod;"
```

### Log Rotation

Configure log rotation for Docker logs:

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Restart Docker daemon:
```bash
sudo systemctl restart docker
```

### Cleanup Old Data

The cleanup service runs automatically, but to manually trigger:

```bash
# Run cleanup service
docker-compose -f docker-compose.prod.yml exec cleanup python -m app.scripts.cleanup_files

# Check cleanup logs
docker-compose -f docker-compose.prod.yml logs cleanup
```

## Verification Steps

### Post-deployment Verification

```bash
# 1. Check all services running
docker-compose -f docker-compose.prod.yml ps

# 2. Test HTTPS endpoint
curl https://yourdomain.com/health

# 3. Test authentication
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "password": "test_pass"}'

# 4. Check database
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT COUNT(*) FROM users;"

# 5. Check GPU access
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# 6. Test file upload (via UI or API)

# 7. Monitor logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# 8. Check SSL certificate
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# 9. Test backup system
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# 10. Verify cleanup service
docker-compose -f docker-compose.prod.yml logs cleanup
```

## Troubleshooting

For detailed troubleshooting steps, see [troubleshooting.md](./troubleshooting.md).

### Quick Diagnostics

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# View recent errors
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# Check resource usage
docker stats

# Check disk space
df -h

# Check GPU status
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# Test database connection
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.core.database import test_connection; import asyncio; asyncio.run(test_connection())"
```

## Support and Documentation

- [Setup Guide](./setup-guide.md) - Initial setup instructions
- [API Specification](./api-specification.md) - API endpoint documentation
- [Troubleshooting Guide](./troubleshooting.md) - Common issues and solutions
- [Architecture Documentation](./architecture.md) - System design and architecture
- [Database Design](./database-design.md) - Database schema and relationships

For issues: https://github.com/your-org/whisper-app/issues
