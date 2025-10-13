# Setup Guide

This guide walks you through setting up the Whisper App for both development and production environments.

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [System Requirements](#system-requirements)
3. [Development Setup](#development-setup)
4. [Production Setup](#production-setup)
5. [Initial Configuration](#initial-configuration)
6. [Database Setup](#database-setup)
7. [Verification](#verification)

## Prerequisites

### Required Software

#### Development Environment
- **Docker** (version 24.0+) and Docker Compose (version 2.20+)
- **Git** (version 2.30+)
- **Node.js** (version 18+ for local frontend development)
- **Python** (version 3.11+ for local backend development)

#### Production Environment
- **Docker** (version 24.0+) and Docker Compose (version 2.20+)
- **NVIDIA GPU** with CUDA support (compute capability 7.0+)
- **NVIDIA Driver** (version 525.60.13+)
- **NVIDIA Container Toolkit** for GPU access in Docker
- **Domain name** with DNS configured (for SSL/TLS)
- **Minimum 50GB** free disk space

### Hardware Requirements

#### Development
- **CPU**: 4 cores minimum
- **RAM**: 8GB minimum (16GB recommended)
- **GPU**: Optional (CPU-only mode available)
- **Disk**: 20GB free space

#### Production
- **CPU**: 8 cores minimum (16 cores recommended)
- **RAM**: 32GB minimum (64GB recommended for large models)
- **GPU**: NVIDIA GPU with 20-30GB VRAM (e.g., RTX 3090, RTX 4090, A100)
  - For large-v3 model: 12GB VRAM minimum
  - For large-v3-turbo model: 10GB VRAM minimum
- **Disk**: 100GB+ free space (for uploads, results, and backups)

### Network Requirements

#### Development
- Ports: 3000 (frontend), 8000 (backend), 5432 (postgres), 6379 (redis)

#### Production
- Ports: 80 (HTTP), 443 (HTTPS)
- Firewall configured to allow inbound traffic on ports 80 and 443
- Outbound access to Let's Encrypt servers for SSL certificate renewal

## System Requirements

### NVIDIA GPU Setup (Production)

1. **Install NVIDIA Driver**:
```bash
# Check current driver version
nvidia-smi

# If not installed or outdated, install latest driver
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nvidia-driver-535

# Verify installation
nvidia-smi
```

2. **Install NVIDIA Container Toolkit**:
```bash
# Add repository
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# Install
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# Configure Docker to use NVIDIA runtime
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# Verify
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Docker Installation

#### Ubuntu/Debian
```bash
# Uninstall old versions
sudo apt-get remove docker docker-engine docker.io containerd runc

# Install using convenience script
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# Add user to docker group (optional, for non-root access)
sudo usermod -aG docker $USER
newgrp docker

# Verify installation
docker --version
docker compose version
```

#### Other Linux Distributions
See official Docker documentation: https://docs.docker.com/engine/install/

## Development Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/whisper-app.git
cd whisper-app
```

### 2. Create Environment File

```bash
cp .env.example .env
```

Edit `.env` with development settings:

```bash
# Database
POSTGRES_USER=whisper_dev
POSTGRES_PASSWORD=dev_password_123
POSTGRES_DB=whisper_dev
DATABASE_URL=postgresql+asyncpg://whisper_dev:dev_password_123@postgres:5432/whisper_dev

# Redis
REDIS_URL=redis://redis:6379

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your_dev_secret_key_here

# LDAP (configure for your LDAP server)
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=ldap_password
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_OBJECT_CLASS=inetOrgPerson

# File Settings
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# Environment
ENVIRONMENT=development
```

### 3. Start Development Services

```bash
# Build and start all services
docker-compose up -d --build

# View logs
docker-compose logs -f

# Check service status
docker-compose ps
```

### 4. Initialize Database

```bash
# Run migrations
docker-compose exec backend alembic upgrade head

# Verify tables were created
docker-compose exec postgres psql -U whisper_dev -d whisper_dev -c "\dt"
```

### 5. Access Services

- **Frontend**: http://localhost:3000
- **Backend API**: http://localhost:8000
- **API Docs**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## Production Setup

### 1. Clone Repository

```bash
git clone https://github.com/your-org/whisper-app.git
cd whisper-app
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
```

Edit `.env` with production settings:

```bash
# Database (use strong passwords!)
POSTGRES_USER=whisper_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=whisper_prod
DATABASE_URL=postgresql+asyncpg://whisper_prod:${POSTGRES_PASSWORD}@postgres:5432/whisper_prod

# Redis
REDIS_URL=redis://redis:6379

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# LDAP (configure for your LDAP server)
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=company,dc=com
LDAP_BIND_DN=cn=admin,dc=company,dc=com
LDAP_BIND_PASSWORD=strong_ldap_password
LDAP_USER_SEARCH_BASE=ou=users,dc=company,dc=com
LDAP_USER_OBJECT_CLASS=inetOrgPerson

# File Settings
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# Backup
BACKUP_RETENTION_DAYS=7

# SSL/TLS
SSL_DOMAIN=yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# Environment
ENVIRONMENT=production

# GPU
CUDA_VISIBLE_DEVICES=0
```

**Important**: Replace `yourdomain.com` with your actual domain name!

### 3. Set Up SSL Certificates

#### Option A: Using Let's Encrypt (Recommended)

1. **Update Nginx configuration** with your domain:
```bash
# Edit nginx/nginx.prod.conf
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/nginx.prod.conf
```

2. **Obtain SSL certificate**:
```bash
# Start nginx temporarily without SSL
docker-compose -f docker-compose.prod.yml up -d nginx

# Run certbot to obtain certificate
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# Restart nginx with SSL
docker-compose -f docker-compose.prod.yml restart nginx
```

#### Option B: Using Existing Certificates

Copy your SSL certificates to the appropriate location:
```bash
mkdir -p ./certbot/conf/live/yourdomain.com
cp /path/to/fullchain.pem ./certbot/conf/live/yourdomain.com/
cp /path/to/privkey.pem ./certbot/conf/live/yourdomain.com/
cp /path/to/chain.pem ./certbot/conf/live/yourdomain.com/
```

### 4. Create Required Directories

```bash
# Create data directories
mkdir -p data/uploads data/results data/temp

# Create backup directory
mkdir -p backup

# Create log directories
mkdir -p logs/nginx logs/backend logs/celery

# Set permissions
chmod 755 data backup logs
```

### 5. Build Frontend for Production

```bash
cd frontend
npm install
npm run build
cd ..

# The build output (dist/) will be copied into the nginx container
```

### 6. Start Production Services

```bash
# Build and start all services
docker-compose -f docker-compose.prod.yml up -d --build

# View logs
docker-compose -f docker-compose.prod.yml logs -f

# Check service status
docker-compose -f docker-compose.prod.yml ps
```

### 7. Initialize Database

```bash
# Run migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Verify tables
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "\dt"
```

### 8. Create Initial Admin User

The first LDAP user to log in will be created in the database. To make them an admin:

```bash
# Access database
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod

# Update user to admin (replace 'username' with actual username)
UPDATE users SET is_admin = true WHERE username = 'admin_username';

# Verify
SELECT id, username, email, is_admin FROM users;

# Exit
\q
```

## Initial Configuration

### LDAP Configuration

Ensure your LDAP server is accessible from the Docker network:

1. **Test LDAP connectivity**:
```bash
# From host machine
ldapsearch -x -H ldap://your-ldap-server:389 -D "cn=admin,dc=example,dc=com" -w password -b "dc=example,dc=com"

# From Docker container
docker-compose exec backend ldapsearch -x -H ldap://your-ldap-server:389 -D "cn=admin,dc=example,dc=com" -w password -b "dc=example,dc=com"
```

2. **Adjust LDAP settings** in `.env` if needed:
   - `LDAP_USER_SEARCH_BASE`: Where to search for users
   - `LDAP_USER_OBJECT_CLASS`: LDAP object class for users
   - `LDAP_USER_UID_ATTRIBUTE`: Attribute containing username (default: uid)

### File Retention Policy

Configure automatic file cleanup:

```bash
# Edit .env
FILE_RETENTION_HOURS=24  # Delete files older than 24 hours

# Restart cleanup service
docker-compose -f docker-compose.prod.yml restart cleanup
```

### Backup Schedule

The backup service runs daily at 3:00 AM UTC. To adjust:

```bash
# Edit docker-compose.prod.yml
services:
  backup:
    # ... existing config ...
    # Adjust cron schedule in entrypoint or use Docker restart policies
```

For manual backup:
```bash
# Run backup manually
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh
```

## Database Setup

### Development Database

The development database is automatically created and initialized when starting services:

```bash
# Apply all migrations
docker-compose exec backend alembic upgrade head

# Check migration status
docker-compose exec backend alembic current

# View migration history
docker-compose exec backend alembic history
```

### Production Database

#### Initial Setup

```bash
# Apply all migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

#### Backup and Restore

**Create backup**:
```bash
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh
```

**Restore from backup**:
```bash
# Stop services
docker-compose -f docker-compose.prod.yml stop backend celery-worker

# Restore database
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# Start services
docker-compose -f docker-compose.prod.yml start backend celery-worker
```

#### Database Migrations

When updating the application:

```bash
# Pull latest code
git pull origin main

# Apply new migrations
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# Restart services
docker-compose -f docker-compose.prod.yml restart backend celery-worker
```

## Verification

### Development Environment

1. **Check all services are running**:
```bash
docker-compose ps

# Expected output:
# NAME                   STATUS
# whisper-backend        Up
# whisper-celery-worker  Up
# whisper-frontend       Up
# whisper-postgres       Up (healthy)
# whisper-redis          Up (healthy)
```

2. **Test backend API**:
```bash
curl http://localhost:8000/health

# Expected: {"status": "healthy"}
```

3. **Test frontend**:
```bash
curl http://localhost:3000

# Expected: HTML content
```

4. **Test database**:
```bash
docker-compose exec postgres psql -U whisper_dev -d whisper_dev -c "SELECT 1;"

# Expected: 1 row returned
```

5. **Test Redis**:
```bash
docker-compose exec redis redis-cli ping

# Expected: PONG
```

### Production Environment

1. **Check all services are running**:
```bash
docker-compose -f docker-compose.prod.yml ps
```

2. **Test HTTPS endpoint**:
```bash
curl https://yourdomain.com/health

# Expected: {"status": "healthy"}
```

3. **Test SSL certificate**:
```bash
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# Check certificate validity and expiration
```

4. **Test GPU access**:
```bash
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# Should show GPU information
```

5. **Test authentication** (via UI or API):
```bash
# Login via API
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# Expected: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

6. **Check logs for errors**:
```bash
# Backend logs
docker-compose -f docker-compose.prod.yml logs backend | grep ERROR

# Celery logs
docker-compose -f docker-compose.prod.yml logs celery-worker | grep ERROR

# Nginx logs
docker-compose -f docker-compose.prod.yml logs nginx | grep error
```

### Performance Tests

1. **Test file upload**:
```bash
# Upload a small audio file
curl -X POST https://yourdomain.com/api/v1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_audio.mp3" \
  -F "model_name=large-v3-turbo" \
  -F "language=ja"

# Check task status
curl https://yourdomain.com/api/v1/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. **Monitor GPU usage**:
```bash
# Watch GPU utilization
watch -n 1 docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi
```

3. **Check database performance**:
```bash
# View slow queries (if enabled)
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

## Next Steps

After successful setup:

1. Review [deployment-guide.md](./deployment-guide.md) for ongoing operations
2. Review [api-specification.md](./api-specification.md) for API details
3. Review [troubleshooting.md](./troubleshooting.md) for common issues
4. Configure monitoring and alerting (see deployment guide)
5. Set up automated backups (see deployment guide)

## Common Issues

See [troubleshooting.md](./troubleshooting.md) for detailed troubleshooting steps.

### Quick Fixes

**Services won't start**:
```bash
# Check logs
docker-compose logs

# Rebuild containers
docker-compose down
docker-compose up -d --build
```

**Database connection errors**:
```bash
# Verify database is running
docker-compose exec postgres pg_isready -U whisper_dev

# Reset database (CAUTION: destroys data!)
docker-compose down -v
docker-compose up -d
```

**GPU not detected**:
```bash
# Verify NVIDIA Container Toolkit
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Check Docker daemon configuration
cat /etc/docker/daemon.json
```

## Support

For issues and questions:
- GitHub Issues: https://github.com/your-org/whisper-app/issues
- Documentation: https://github.com/your-org/whisper-app/tree/main/docs
