#!/bin/bash
# Database Backup Script for Whisper App
# This script creates daily backups of the PostgreSQL database

set -e

# Configuration
BACKUP_DIR="/backup"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
BACKUP_FILE="${BACKUP_DIR}/whisper_backup_${TIMESTAMP}.sql.gz"
RETENTION_DAYS=${BACKUP_RETENTION_DAYS:-7}

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Logging function
log() {
    echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"
}

error() {
    echo -e "${RED}[$(date +'%Y-%m-%d %H:%M:%S')] ERROR:${NC} $1" >&2
}

warn() {
    echo -e "${YELLOW}[$(date +'%Y-%m-%d %H:%M:%S')] WARNING:${NC} $1"
}

# Check required environment variables
if [ -z "$POSTGRES_HOST" ] || [ -z "$POSTGRES_USER" ] || [ -z "$POSTGRES_DB" ]; then
    error "Required environment variables are not set"
    exit 1
fi

# Create backup directory if it doesn't exist
mkdir -p "$BACKUP_DIR"

# Perform backup
log "Starting database backup..."
log "Database: $POSTGRES_DB on $POSTGRES_HOST"

if PGPASSWORD="$POSTGRES_PASSWORD" pg_dump \
    -h "$POSTGRES_HOST" \
    -U "$POSTGRES_USER" \
    -d "$POSTGRES_DB" \
    --verbose \
    --no-owner \
    --no-acl \
    | gzip > "$BACKUP_FILE"; then

    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    log "Backup completed successfully: $BACKUP_FILE ($BACKUP_SIZE)"
else
    error "Backup failed"
    rm -f "$BACKUP_FILE"
    exit 1
fi

# Verify backup integrity
log "Verifying backup integrity..."
if gunzip -t "$BACKUP_FILE"; then
    log "Backup verification successful"
else
    error "Backup verification failed"
    exit 1
fi

# Remove old backups
log "Cleaning up old backups (retention: $RETENTION_DAYS days)..."
find "$BACKUP_DIR" -name "whisper_backup_*.sql.gz" -type f -mtime "+$RETENTION_DAYS" -delete
REMAINING_BACKUPS=$(find "$BACKUP_DIR" -name "whisper_backup_*.sql.gz" -type f | wc -l)
log "Cleanup complete. Remaining backups: $REMAINING_BACKUPS"

# Create a "latest" symlink
ln -sf "$BACKUP_FILE" "${BACKUP_DIR}/whisper_backup_latest.sql.gz"

# Summary
log "==================================="
log "Backup Summary:"
log "  File: $BACKUP_FILE"
log "  Size: $BACKUP_SIZE"
log "  Retention: $RETENTION_DAYS days"
log "  Total backups: $REMAINING_BACKUPS"
log "==================================="

exit 0
