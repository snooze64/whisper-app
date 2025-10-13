# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

An on-premises audio/video transcription application using OpenAI Whisper for enterprise meeting recordings (Zoom, Teams, etc.). The system processes uploaded files through GPU-accelerated transcription with speaker diarization, generating timestamped text and subtitle files.

## Working Guidelines

**IMPORTANT: Always refer to documentation in `/docs` when working on this project.**

Before starting any task:
- Check relevant documentation in `/docs` directory for requirements and specifications
- Review `docs/architecture.md` for system design patterns and API structure
- Consult `docs/database-design.md` for database schema and relationships
- Reference `docs/technology-stack.md` for technology decisions and library usage

When completing a task:
- ✅ Verify the implementation matches requirements in documentation
- ✅ Check that database changes align with `docs/database-design.md`
- ✅ Ensure API endpoints follow patterns in `docs/architecture.md`
- ✅ Update documentation if requirements or design changed
- ✅ Run tests and verify all pass
- ✅ Review code for security issues and performance concerns

## System Architecture

**Multi-service containerized architecture:**
- **Frontend (React)**: User interface for file upload, status monitoring, result viewing/editing
- **Backend (FastAPI)**: API endpoints, authentication (LDAP+JWT), task orchestration
- **Celery Workers (GPU)**: Asynchronous transcription processing with Whisper + Resemblyzer
- **PostgreSQL**: Task metadata, transcription results, processing history
- **Redis**: Celery task queue and message broker
- **Nginx**: Reverse proxy, SSL termination, static file serving

**Key Processing Flow:**
1. User uploads audio/video file → FastAPI validates and saves
2. Task created in PostgreSQL → Celery task queued in Redis
3. Celery worker picks task → Checks GPU memory availability
4. Extracts audio (FFmpeg) → Whisper transcription → Speaker diarization (Resemblyzer)
5. Results saved to PostgreSQL → User polls for status/retrieves results

## Development Commands

### Environment Setup
```bash
# Start all services
docker-compose up -d --build

# Database migration
docker-compose exec backend alembic upgrade head

# Create new migration
docker-compose exec backend alembic revision -m "description"
```

### Backend (FastAPI + Celery)
```bash
# Run backend tests
docker-compose exec backend pytest

# Run specific test
docker-compose exec backend pytest tests/test_auth.py::test_login

# Access backend logs
docker-compose logs -f backend

# Access Celery worker logs
docker-compose logs -f celery-worker

# Python linting
docker-compose exec backend ruff check .
docker-compose exec backend black --check .
docker-compose exec backend mypy app/
```

### Frontend (React + TypeScript)
```bash
# Run frontend tests
docker-compose exec frontend npm test

# Run specific test
docker-compose exec frontend npm test -- FileUploader.test.tsx

# Type checking
docker-compose exec frontend npm run type-check

# Linting
docker-compose exec frontend npm run lint

# Build
docker-compose exec frontend npm run build
```

### Database Operations
```bash
# Access PostgreSQL
docker-compose exec postgres psql -U user -d whisper

# View tables
docker-compose exec postgres psql -U user -d whisper -c "\dt"

# Backup database
docker-compose exec postgres pg_dump -U user whisper > backup.sql
```

## Architecture Patterns

### Backend Structure
- **API v1 Endpoints**: `/api/v1/{resource}` - All endpoints versioned
- **Service Layer**: Business logic separated from API handlers in `app/services/`
- **Dependency Injection**: FastAPI `Depends()` for DB sessions, auth, etc.
- **Pydantic Schemas**: Request/response validation in `app/schemas/`
- **SQLAlchemy Models**: Database models in `app/models/`

### Celery Task Design
- **Task Chain**: `extract_audio_task → transcribe_task → diarize_task → generate_subtitle_task`
- **GPU Memory Management**: Check available VRAM before starting tasks using `pynvml`
- **Dynamic Scheduling**: Tasks queued until GPU memory available (20-30GB shared pool)
- **Retry Strategy**: Exponential backoff with max 3 retries
- **Task States**: pending → processing → completed/failed

### Frontend Patterns
- **State Management**: TanStack Query for server state, Zustand for client state
- **Component Structure**: shadcn/ui components in `src/components/ui/`, feature components separate
- **API Client**: Centralized axios instance in `src/services/api.ts`
- **Polling Pattern**: 3-second interval for task status updates

## Database Schema Key Points

### Primary Tables
- **users**: LDAP-synced users with admin flag
- **tasks**: UUID primary key, tracks transcription jobs with status/progress
- **transcriptions**: 1:1 with tasks, stores full text + JSONB segments with speaker info
- **processing_history**: Permanent record for statistics (GPU usage, processing time)

### Segments JSONB Structure
```json
[{"id": 0, "start": 0.0, "end": 5.5, "text": "...", "speaker_id": 1, "speaker_label": "Speaker 1", "confidence": 0.95}]
```

### Critical Indexes
- `idx_tasks_user_status` on `(user_id, status)` - User's active tasks
- `idx_transcriptions_segments_gin` on `segments` - Fast JSONB queries
- Partial indexes on admin users, completed tasks (WHERE clauses)

## Configuration & Environment

### Required Environment Variables
```bash
# Database
DATABASE_URL=postgresql://user:pass@postgres:5432/whisper

# Task Queue
REDIS_URL=redis://redis:6379

# Authentication
LDAP_SERVER=ldap://ldap-server:389

# GPU (CUDA 11.8 or 12.1+ required)
CUDA_VISIBLE_DEVICES=0

# File Storage
MAX_FILE_SIZE=1073741824  # 1GB in bytes
FILE_RETENTION_HOURS=24
```

### Model Configuration
- **Whisper Models**: large-v3 (~12GB VRAM), large-v3-turbo (~10GB VRAM)
- **User Selection**: Model chosen per-task via API parameter
- **Language**: Default `ja` (Japanese), supports multi-language mode

## Future Extensions (Documented but Not Implemented)

### ChatGPT Integration (Section 5.2 in requirement.md, Section 11 in architecture.md)
- **Tables**: `llm_processings`, `prompt_templates` (in database-design.md)
- **Environment**: `OPENAI_BASE_URL`, `OPENAI_API_KEY` (system-wide)
- **Model Discovery**: Dynamic fetch from `{baseurl}/api/models`
- **Templates**: Default prompts (summary, action items) + user custom
- **API Design**: `POST /api/v1/tasks/{task_id}/llm-process`

### Real-time Transcription (Section 5.1 in requirement.md)
- WebSocket streaming for live meeting transcription
- System audio capture (virtual audio device) or Electron desktop app
- Deferred to post-MVP

## Important Constraints

- **GPU Memory**: Shared 20-30GB pool, dynamic task scheduling required
- **File Retention**: Automatic 24-hour deletion (uploads + results)
- **Concurrent Users**: Max 20 users, queue-based processing
- **File Limits**: 1GB max (configurable via env var)
- **CUDA Version**: 11.8 or 12.1+ (impacts PyTorch build)

## Testing Strategy

- **Backend Unit Tests**: `pytest` with async support, mock GPU operations
- **Frontend Tests**: Vitest + React Testing Library
- **Integration Tests**: Full stack tests with Docker test containers
- **Coverage Target**: 80%+ for MVP

## Documentation Reference

**⚠️ ALWAYS consult these documents before and during development:**

Critical docs in `docs/`:
- 📋 **`requirement.md`**: Complete functional and non-functional requirements
  - Use case details, file formats, user roles, feature specifications
  - Future extensions (ChatGPT integration, real-time transcription)

- 🏗️ **`architecture.md`**: Full system design (26KB, most comprehensive)
  - Multi-service architecture diagram and data flow
  - Complete API endpoint specifications with request/response schemas
  - Celery task chain design and error handling patterns
  - Section 11: ChatGPT integration architecture (for future implementation)

- 🗄️ **`database-design.md`**: Complete database schema (23KB, 737 lines)
  - All 6 tables with full SQL DDL statements
  - Index strategies, constraints, and relationships
  - JSONB segment structure for transcriptions
  - Migration strategy with Alembic

- 🔧 **`technology-stack.md`**: Technology selection with rationale
  - Library versions and compatibility (CUDA, PyTorch, FastAPI, React)
  - Why each technology was chosen over alternatives
  - Section 16: LLM integration technical details

- 📅 **`development-plan.md`**: 10-phase development schedule (Week 1-12)
  - Phase priorities and task breakdown
  - Milestone dependencies

**When to reference:**
- Starting a new feature → Check `requirement.md` and `architecture.md`
- Database work → Always check `database-design.md` for schema
- Library installation → Reference `technology-stack.md` for versions
- API development → Follow patterns in `architecture.md`
- Planning work → Consult `development-plan.md` for phase structure

## Git Workflow

- **Branch Strategy**: Git Flow (main → develop → feature/*)
- **Commit Convention**: Conventional Commits (`feat:`, `fix:`, `docs:`, etc.)
- **PR Process**: feature → develop (with tests + code review)
