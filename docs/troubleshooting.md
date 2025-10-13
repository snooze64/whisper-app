# Troubleshooting Guide

Common issues and solutions for the Whisper App production deployment.

## Table of Contents

1. [Quick Diagnostics](#quick-diagnostics)
2. [Service Issues](#service-issues)
3. [Authentication Issues](#authentication-issues)
4. [File Upload Issues](#file-upload-issues)
5. [Transcription Issues](#transcription-issues)
6. [GPU Issues](#gpu-issues)
7. [Database Issues](#database-issues)
8. [Network Issues](#network-issues)
9. [Performance Issues](#performance-issues)
10. [Frontend Issues](#frontend-issues)

## Quick Diagnostics

### Check All Services

```bash
# Check service status
docker-compose -f docker-compose.prod.yml ps

# Check logs for errors
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# Check resource usage
docker stats

# Check disk space
df -h
```

### Test API Health

```bash
# Test health endpoint
curl https://yourdomain.com/health

# Expected: {"status": "healthy"}
```

## Service Issues

### Issue: Services Won't Start

**Symptoms**:
- `docker-compose up` fails
- Containers exit immediately
- "Port already in use" errors

**Solutions**:

1. **Check for port conflicts**:
```bash
# Check if ports are in use
lsof -i :80  # HTTP
lsof -i :443 # HTTPS
lsof -i :5432 # PostgreSQL
lsof -i :6379 # Redis

# Kill conflicting processes if needed
kill -9 <PID>
```

2. **Check Docker daemon**:
```bash
sudo systemctl status docker
sudo systemctl restart docker
```

3. **Rebuild containers**:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### Issue: Container Keeps Restarting

**Symptoms**:
- Container status shows "Restarting"
- Service is unstable

**Solutions**:

1. **Check container logs**:
```bash
docker-compose -f docker-compose.prod.yml logs --tail=200 <service_name>
```

2. **Check environment variables**:
```bash
# Verify .env file exists and has correct values
cat .env | grep -v PASSWORD | grep -v SECRET
```

3. **Increase memory limits** in `docker-compose.prod.yml`:
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 8G  # Increase from 4G
```

## Authentication Issues

### Issue: Cannot Login

**Symptoms**:
- "Invalid credentials" error
- Login succeeds but immediately fails

**Solutions**:

1. **Check LDAP connectivity**:
```bash
# Test LDAP connection from backend container
docker-compose -f docker-compose.prod.yml exec backend ldapsearch \
  -x \
  -H ldap://your-ldap-server:389 \
  -D "cn=admin,dc=example,dc=com" \
  -w "password" \
  -b "dc=example,dc=com"
```

2. **Verify LDAP configuration** in `.env`:
```bash
cat .env | grep LDAP
```

3. **Check backend logs for LDAP errors**:
```bash
docker-compose -f docker-compose.prod.yml logs backend | grep -i ldap
```

### Issue: Admin Functions Not Working

**Symptoms**:
- "Forbidden" errors on admin endpoints
- Admin user cannot access admin dashboard

**Solutions**:

1. **Verify user is admin**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT id, username, is_admin FROM users WHERE username = 'admin_user';"
```

2. **Set user as admin**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "UPDATE users SET is_admin = true WHERE username = 'admin_user';"
```

## File Upload Issues

### Issue: File Upload Fails

**Symptoms**:
- "413 Payload Too Large" error
- Upload progress sticks at certain percentage
- "Unsupported file format" error

**Solutions**:

1. **Check file size limit**:
```bash
# Check MAX_FILE_SIZE in .env
cat .env | grep MAX_FILE_SIZE

# Default is 1GB (1073741824 bytes)
```

2. **Check Nginx upload limit**:
```bash
# Check client_max_body_size in nginx.prod.conf
grep client_max_body_size nginx/nginx.prod.conf

# Should be slightly larger than MAX_FILE_SIZE (e.g., 1100M)
```

3. **Verify file format is supported**:
```
Supported audio: MP3, WAV, M4A, FLAC, OGG
Supported video: MP4, AVI, MOV, MKV
```

## Transcription Issues

### Issue: Transcription Fails

**Symptoms**:
- Task status shows "failed"
- No transcription result available

**Solutions**:

1. **Check Celery worker logs**:
```bash
docker-compose -f docker-compose.prod.yml logs celery-worker --tail=200
```

2. **Check task error message**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT id, filename, status, error_message FROM tasks WHERE status = 'failed' ORDER BY created_at DESC LIMIT 5;"
```

3. **Common errors**:

**Error: "Out of memory"**
- Solution: Reduce concurrent tasks or increase GPU memory

**Error: "FFmpeg failed"**
- Solution: Check audio extraction
```bash
docker-compose -f docker-compose.prod.yml exec celery-worker ffmpeg -i /data/uploads/1/file.mp4 -vn -acodec pcm_s16le -ar 16000 /tmp/test.wav
```

## GPU Issues

### Issue: GPU Not Detected

**Symptoms**:
- "GPU unavailable" error
- Tasks use CPU instead of GPU (very slow)

**Solutions**:

1. **Check NVIDIA driver on host**:
```bash
nvidia-smi
```

2. **Install NVIDIA Container Toolkit**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

3. **Test GPU access in Docker**:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### Issue: Out of GPU Memory

**Symptoms**:
- Tasks fail with "CUDA out of memory"
- GPU memory full

**Solutions**:

1. **Check GPU memory usage**:
```bash
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi
```

2. **Reduce concurrent tasks**:
```yaml
# docker-compose.prod.yml
services:
  celery-worker:
    command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

3. **Use smaller Whisper model**:
- `large-v3-turbo` uses ~10GB VRAM
- `large-v3` uses ~12GB VRAM

## Database Issues

### Issue: Database Connection Errors

**Symptoms**:
- "Could not connect to database"
- Connection timeout errors

**Solutions**:

1. **Check PostgreSQL is running**:
```bash
docker-compose -f docker-compose.prod.yml ps postgres
docker-compose -f docker-compose.prod.yml logs postgres
```

2. **Check DATABASE_URL** in `.env`:
```bash
cat .env | grep DATABASE_URL
# Should be: postgresql+asyncpg://user:pass@postgres:5432/whisper_prod
```

3. **Test connection manually**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT 1;"
```

### Issue: Database Running Slowly

**Symptoms**:
- Slow API responses
- Query timeouts

**Solutions**:

1. **Run VACUUM and ANALYZE**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "VACUUM ANALYZE;"
```

2. **Check database size**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT pg_size_pretty(pg_database_size('whisper_prod'));"
```

3. **Restart PostgreSQL**:
```bash
docker-compose -f docker-compose.prod.yml restart postgres
```

## Network Issues

### Issue: Cannot Access Application

**Symptoms**:
- Cannot open https://yourdomain.com
- Connection timeout

**Solutions**:

1. **Check Nginx is running**:
```bash
docker-compose -f docker-compose.prod.yml ps nginx
docker-compose -f docker-compose.prod.yml logs nginx
```

2. **Check firewall rules**:
```bash
sudo ufw status
# Should allow ports 80 and 443
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

3. **Check DNS resolution**:
```bash
nslookup yourdomain.com
dig yourdomain.com
```

### Issue: SSL Certificate Errors

**Symptoms**:
- "Certificate not trusted" error
- SSL handshake failure

**Solutions**:

1. **Check certificate validity**:
```bash
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

2. **Renew Let's Encrypt certificate**:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot renew
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

3. **Check certificate files exist**:
```bash
ls -la certbot/conf/live/yourdomain.com/
```

## Performance Issues

### Issue: High CPU Usage

**Symptoms**:
- Server running hot
- Slow response times

**Solutions**:

1. **Check CPU usage**:
```bash
docker stats
top
```

2. **Reduce concurrent tasks**:
```yaml
# docker-compose.prod.yml
services:
  celery-worker:
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
```

### Issue: Disk Space Running Out

**Symptoms**:
- "No space left on device" errors
- Slow performance

**Solutions**:

1. **Check disk usage**:
```bash
df -h
du -sh /data/*
```

2. **Run cleanup service manually**:
```bash
docker-compose -f docker-compose.prod.yml exec cleanup python -m app.scripts.cleanup_files
```

3. **Reduce file retention period** in `.env`:
```bash
FILE_RETENTION_HOURS=12  # Reduce from 24
```

4. **Clean old Docker images and volumes**:
```bash
docker system prune -a --volumes
```

## Frontend Issues

### Issue: Frontend Not Loading

**Symptoms**:
- Blank page
- "Cannot GET /" error

**Solutions**:

1. **Check Nginx is serving frontend**:
```bash
docker-compose -f docker-compose.prod.yml exec nginx ls -la /usr/share/nginx/html/
```

2. **Verify frontend build exists**:
```bash
ls -la frontend/dist/
```

3. **Rebuild frontend**:
```bash
cd frontend
npm install
npm run build
cd ..

# Restart nginx
docker-compose -f docker-compose.prod.yml restart nginx
```

4. **Check browser console** for JavaScript errors

### Issue: API Requests Failing (CORS)

**Symptoms**:
- "CORS error" in browser console
- API requests blocked

**Solutions**:

1. **Check CORS configuration** in `backend/app/main.py`:
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. **Verify request is going to correct URL**:
- Frontend should use relative paths (`/api/v1/...`)

## Getting Help

### Gather Information

Before reporting an issue, collect:

1. **System information**:
```bash
uname -a
docker --version
nvidia-smi
```

2. **Service status**:
```bash
docker-compose -f docker-compose.prod.yml ps
```

3. **Recent logs**:
```bash
docker-compose -f docker-compose.prod.yml logs --tail=200 > logs.txt
```

### Report Issue

- **GitHub Issues**: https://github.com/your-org/whisper-app/issues
- **Include**: Steps to reproduce, expected vs actual behavior, logs, system info

## Additional Resources

- [Setup Guide](./setup-guide.md)
- [Deployment Guide](./deployment-guide.md)
- [API Specification](./api-specification.md)
- [Architecture Documentation](./architecture.md)

**Last Updated**: 2025-10-13
**Phase**: Phase 9 - Deployment Preparation
