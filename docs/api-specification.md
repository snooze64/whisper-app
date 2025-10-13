# API Specification

Complete API documentation for the Whisper App backend.

## Table of Contents

1. [Overview](#overview)
2. [Authentication](#authentication)
3. [API Endpoints](#api-endpoints)
   - [Authentication API](#authentication-api)
   - [Upload API](#upload-api)
   - [Task Management API](#task-management-api)
   - [Transcription API](#transcription-api)
   - [History API](#history-api)
   - [Admin API](#admin-api)
4. [Data Models](#data-models)
5. [Error Responses](#error-responses)
6. [Rate Limiting](#rate-limiting)

## Overview

**Base URL**: `https://yourdomain.com/api/v1`

**Content Type**: `application/json` (except file uploads: `multipart/form-data`)

**Authentication**: Bearer Token (JWT)

**API Version**: v1

### HTTP Status Codes

| Code | Description |
|------|-------------|
| 200 | Success (OK) |
| 201 | Created |
| 204 | No Content (successful deletion) |
| 400 | Bad Request (validation error) |
| 401 | Unauthorized (invalid/missing token) |
| 403 | Forbidden (insufficient permissions) |
| 404 | Not Found |
| 413 | Payload Too Large (file size exceeds limit) |
| 422 | Unprocessable Entity (validation failed) |
| 429 | Too Many Requests (rate limit exceeded) |
| 500 | Internal Server Error |
| 503 | Service Unavailable |

## Authentication

All API endpoints (except `/auth/login`) require a valid JWT token.

### Token Types

- **Access Token**: Valid for 30 minutes, used for API requests
- **Refresh Token**: Valid for 7 days, used to obtain new access tokens

### Including Token in Requests

```http
GET /api/v1/tasks HTTP/1.1
Host: yourdomain.com
Authorization: Bearer <access_token>
```

### Token Refresh Flow

When access token expires (401 response):
1. Call `/api/v1/auth/refresh` with refresh token
2. Receive new access token and refresh token
3. Retry original request with new access token

## API Endpoints

### Authentication API

#### POST /api/v1/auth/login

Authenticate user via LDAP and receive JWT tokens.

**Request Body**:
```json
{
  "username": "john.doe",
  "password": "secure_password"
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800,
  "user": {
    "id": 1,
    "username": "john.doe",
    "email": "john.doe@company.com",
    "is_admin": false
  }
}
```

**Error Responses**:
- `401`: Invalid credentials
- `503`: LDAP server unavailable

---

#### POST /api/v1/auth/refresh

Refresh access token using refresh token.

**Request Body**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**Response** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**Error Responses**:
- `401`: Invalid or expired refresh token

---

#### POST /api/v1/auth/logout

Logout user (invalidate tokens on client side).

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

#### GET /api/v1/auth/me

Get current user information.

**Headers**: `Authorization: Bearer <token>`

**Response** (200 OK):
```json
{
  "id": 1,
  "username": "john.doe",
  "email": "john.doe@company.com",
  "is_admin": false,
  "created_at": "2025-10-01T10:00:00Z",
  "last_login": "2025-10-13T15:30:00Z"
}
```

---

### Upload API

#### POST /api/v1/upload

Upload audio/video file for transcription.

**Headers**:
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**Request Body** (multipart/form-data):
```
file: <binary file>
model_name: "large-v3-turbo" | "large-v3"
language: "ja" | "en" | "auto" (optional, default: "ja")
num_speakers: 2 (optional, for speaker diarization)
```

**Example cURL**:
```bash
curl -X POST https://yourdomain.com/api/v1/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@meeting_recording.mp3" \
  -F "model_name=large-v3-turbo" \
  -F "language=ja" \
  -F "num_speakers=3"
```

**Response** (201 Created):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "meeting_recording.mp3",
  "status": "pending",
  "message": "File uploaded successfully. Processing started."
}
```

**Validation Rules**:
- **Supported formats**: MP3, WAV, M4A, FLAC, OGG, MP4, AVI, MOV, MKV
- **Max file size**: 1GB (configurable via `MAX_FILE_SIZE` env var)
- **Model names**: `large-v3`, `large-v3-turbo`
- **Languages**: ISO 639-1 codes (ja, en, zh, etc.) or "auto"
- **Num speakers**: 1-20

**Error Responses**:
- `400`: Invalid file format or missing required fields
- `413`: File too large
- `422`: Validation failed

---

### Task Management API

#### GET /api/v1/tasks

Get list of user's tasks.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `status` (optional): Filter by status (`pending`, `processing`, `completed`, `failed`)
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `sort_by` (optional): Sort field (`created_at`, `status`), default: `created_at`
- `sort_order` (optional): Sort order (`asc`, `desc`), default: `desc`

**Response** (200 OK):
```json
{
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "filename": "meeting_recording.mp3",
      "file_size": 15728640,
      "file_format": "mp3",
      "model_name": "large-v3-turbo",
      "language": "ja",
      "num_speakers": 2,
      "status": "completed",
      "progress": 100,
      "created_at": "2025-10-13T10:00:00Z",
      "started_at": "2025-10-13T10:00:15Z",
      "completed_at": "2025-10-13T10:03:45Z",
      "error_message": null
    }
  ],
  "pagination": {
    "total": 25,
    "page": 1,
    "page_size": 20,
    "total_pages": 2
  }
}
```

---

#### GET /api/v1/tasks/{task_id}

Get detailed task information.

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `task_id`: UUID of the task

**Response** (200 OK):
```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "filename": "meeting_recording.mp3",
  "file_path": "/data/uploads/1/550e8400_meeting_recording.mp3",
  "file_size": 15728640,
  "file_format": "mp3",
  "model_name": "large-v3-turbo",
  "language": "ja",
  "num_speakers": 2,
  "status": "completed",
  "progress": 100,
  "created_at": "2025-10-13T10:00:00Z",
  "started_at": "2025-10-13T10:00:15Z",
  "completed_at": "2025-10-13T10:03:45Z",
  "error_message": null
}
```

**Error Responses**:
- `403`: User does not have permission to access this task
- `404`: Task not found

---

#### GET /api/v1/tasks/{task_id}/status

Get task status (lightweight endpoint for polling).

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `task_id`: UUID of the task

**Response** (200 OK):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "message": "Performing speaker diarization..."
}
```

**Status Values**:
- `pending`: Waiting in queue
- `processing`: Currently being processed
- `completed`: Successfully completed
- `failed`: Processing failed

---

#### DELETE /api/v1/tasks/{task_id}

Delete a task and associated files.

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `task_id`: UUID of the task

**Response** (204 No Content)

**Error Responses**:
- `403`: User does not have permission to delete this task
- `404`: Task not found

---

### Transcription API

#### GET /api/v1/tasks/{task_id}/transcription

Get transcription result for a completed task.

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `task_id`: UUID of the task

**Response** (200 OK):
```json
{
  "id": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription_text": "こんにちは。今日の会議を始めます...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.5,
      "text": "こんにちは。今日の会議を始めます。",
      "speaker_id": 1,
      "speaker_label": "Speaker 1",
      "confidence": 0.95
    },
    {
      "id": 1,
      "start": 6.0,
      "end": 12.3,
      "text": "では、まずプロジェクトの進捗について報告します。",
      "speaker_id": 2,
      "speaker_label": "Speaker 2",
      "confidence": 0.92
    }
  ],
  "subtitle_path": "/data/results/550e8400/subtitles.srt",
  "created_at": "2025-10-13T10:03:45Z"
}
```

**Error Responses**:
- `403`: User does not have permission to access this transcription
- `404`: Task not found or transcription not available yet

---

#### PUT /api/v1/tasks/{task_id}/transcription

Update entire transcription text.

**Headers**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Path Parameters**:
- `task_id`: UUID of the task

**Request Body**:
```json
{
  "transcription_text": "Updated full transcription text..."
}
```

**Response** (200 OK):
```json
{
  "id": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription_text": "Updated full transcription text...",
  "segments": [...],
  "subtitle_path": "/data/results/550e8400/subtitles.srt",
  "created_at": "2025-10-13T10:03:45Z",
  "updated_at": "2025-10-13T11:15:30Z"
}
```

---

#### PATCH /api/v1/tasks/{task_id}/transcription/segments

Update specific segments of transcription.

**Headers**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**Path Parameters**:
- `task_id`: UUID of the task

**Request Body**:
```json
{
  "segments": [
    {
      "id": 0,
      "text": "Updated segment text",
      "speaker_label": "John Doe"
    },
    {
      "id": 5,
      "text": "Another updated segment"
    }
  ]
}
```

**Response** (200 OK):
```json
{
  "updated_count": 2,
  "segments": [...]
}
```

---

#### GET /api/v1/tasks/{task_id}/subtitle

Download subtitle file.

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `task_id`: UUID of the task

**Query Parameters**:
- `format`: Subtitle format (`srt` or `vtt`), default: `srt`

**Response** (200 OK):
- **Content-Type**: `text/plain` (SRT) or `text/vtt` (WebVTT)
- **Content-Disposition**: `attachment; filename="transcription.srt"`

**SRT Format Example**:
```
1
00:00:00,000 --> 00:00:05,500
[Speaker 1] こんにちは。今日の会議を始めます。

2
00:00:06,000 --> 00:00:12,300
[Speaker 2] では、まずプロジェクトの進捗について報告します。
```

**WebVTT Format Example**:
```
WEBVTT

00:00:00.000 --> 00:00:05.500
<v Speaker 1>こんにちは。今日の会議を始めます。

00:00:06.000 --> 00:00:12.300
<v Speaker 2>では、まずプロジェクトの進捗について報告します。
```

---

### History API

#### GET /api/v1/history

Get processing history for current user.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `success` (optional): Filter by success status (`true`, `false`)
- `model_name` (optional): Filter by model name
- `start_date` (optional): Filter by start date (ISO 8601 format)
- `end_date` (optional): Filter by end date (ISO 8601 format)

**Response** (200 OK):
```json
{
  "history": [
    {
      "id": 1,
      "task_id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": 1,
      "processing_time_seconds": 210,
      "gpu_memory_used_mb": 8500,
      "model_name": "large-v3-turbo",
      "file_format": "mp3",
      "file_size_mb": 15.0,
      "success": true,
      "error_type": null,
      "created_at": "2025-10-13T10:03:45Z"
    }
  ],
  "pagination": {
    "total": 50,
    "page": 1,
    "page_size": 20,
    "total_pages": 3
  }
}
```

---

#### GET /api/v1/history/{id}

Get detailed processing history entry.

**Headers**: `Authorization: Bearer <token>`

**Path Parameters**:
- `id`: History entry ID

**Response** (200 OK):
```json
{
  "id": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "processing_time_seconds": 210,
  "gpu_memory_used_mb": 8500,
  "model_name": "large-v3-turbo",
  "file_format": "mp3",
  "file_size_mb": 15.0,
  "success": true,
  "error_type": null,
  "created_at": "2025-10-13T10:03:45Z",
  "task": {
    "id": "550e8400-e29b-41d4-a716-446655440000",
    "filename": "meeting_recording.mp3",
    "language": "ja"
  }
}
```

---

#### GET /api/v1/history/stats/me

Get processing statistics for current user.

**Headers**: `Authorization: Bearer <token>`

**Query Parameters**:
- `start_date` (optional): Start date for statistics (ISO 8601 format)
- `end_date` (optional): End date for statistics (ISO 8601 format)
- `period` (optional): Predefined period (`today`, `week`, `month`, `year`)

**Response** (200 OK):
```json
{
  "total_tasks": 50,
  "successful_tasks": 48,
  "failed_tasks": 2,
  "success_rate": 96.0,
  "avg_processing_time": 125.5,
  "total_processing_time": 6275,
  "avg_gpu_memory": 8500.0,
  "total_file_size": 1250.5,
  "model_usage": {
    "large-v3": 30,
    "large-v3-turbo": 20
  },
  "format_usage": {
    "mp3": 35,
    "mp4": 10,
    "wav": 5
  }
}
```

---

### Admin API

All admin endpoints require `is_admin: true` in user profile.

#### GET /api/v1/admin/dashboard

Get dashboard statistics (admin only).

**Headers**: `Authorization: Bearer <admin_token>`

**Response** (200 OK):
```json
{
  "total_users": 20,
  "total_tasks": 150,
  "active_tasks": 5,
  "completed_tasks_today": 12,
  "failed_tasks_today": 1,
  "avg_processing_time_today": 85.5,
  "model_usage": {
    "large-v3": 80,
    "large-v3-turbo": 65,
    "tiny": 5
  },
  "format_usage": {
    "mp3": 90,
    "wav": 40,
    "mp4": 20
  },
  "hourly_stats": [
    {
      "hour": "2025-10-13T08:00:00Z",
      "total": 3,
      "successful": 3,
      "failed": 0
    },
    {
      "hour": "2025-10-13T09:00:00Z",
      "total": 5,
      "successful": 4,
      "failed": 1
    }
  ]
}
```

**Error Responses**:
- `403`: User is not an admin

---

#### GET /api/v1/admin/system-status

Get system status information (admin only).

**Headers**: `Authorization: Bearer <admin_token>`

**Response** (200 OK):
```json
{
  "gpu_available": true,
  "gpu_memory_total": 40960,
  "gpu_memory_used": 12500,
  "gpu_memory_free": 28460,
  "gpu_utilization": 35.5,
  "gpu_temperature": 65,
  "active_workers": 2,
  "pending_tasks": 3,
  "processing_tasks": 2,
  "redis_connected": true,
  "database_connected": true,
  "ldap_connected": true
}
```

---

#### GET /api/v1/admin/users

Get list of all users (admin only).

**Headers**: `Authorization: Bearer <admin_token>`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `is_admin` (optional): Filter by admin status (`true`, `false`)

**Response** (200 OK):
```json
{
  "users": [
    {
      "id": 1,
      "username": "john.doe",
      "email": "john.doe@company.com",
      "is_admin": false,
      "created_at": "2025-10-01T10:00:00Z",
      "last_login": "2025-10-13T15:30:00Z",
      "total_tasks": 25,
      "successful_tasks": 24,
      "failed_tasks": 1
    }
  ],
  "pagination": {
    "total": 20,
    "page": 1,
    "page_size": 20,
    "total_pages": 1
  }
}
```

---

#### GET /api/v1/admin/tasks

Get all tasks from all users (admin only).

**Headers**: `Authorization: Bearer <admin_token>`

**Query Parameters**:
- `page` (optional): Page number (default: 1)
- `page_size` (optional): Items per page (default: 20, max: 100)
- `status` (optional): Filter by status
- `user_id` (optional): Filter by user ID
- `start_date` (optional): Filter by start date
- `end_date` (optional): Filter by end date

**Response** (200 OK):
```json
{
  "tasks": [
    {
      "id": "550e8400-e29b-41d4-a716-446655440000",
      "user_id": 1,
      "username": "john.doe",
      "filename": "meeting_recording.mp3",
      "file_size": 15728640,
      "status": "completed",
      "created_at": "2025-10-13T10:00:00Z",
      "completed_at": "2025-10-13T10:03:45Z"
    }
  ],
  "pagination": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

---

#### GET /api/v1/admin/stats

Get overall system statistics (admin only).

**Headers**: `Authorization: Bearer <admin_token>`

**Query Parameters**:
- `start_date` (optional): Start date (ISO 8601)
- `end_date` (optional): End date (ISO 8601)
- `period` (optional): Predefined period (`today`, `week`, `month`, `year`)

**Response** (200 OK):
```json
{
  "total_tasks": 150,
  "successful_tasks": 145,
  "failed_tasks": 5,
  "success_rate": 96.7,
  "avg_processing_time": 105.5,
  "total_processing_time": 15825,
  "avg_gpu_memory": 8750.0,
  "total_file_size": 2500.5,
  "active_users": 15,
  "most_used_model": "large-v3-turbo",
  "peak_usage_hour": "14:00"
}
```

---

### Health Check API

#### GET /health

Check API health status (no authentication required).

**Response** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T15:30:00Z",
  "version": "1.0.0"
}
```

---

## Data Models

### User

```json
{
  "id": 1,
  "username": "john.doe",
  "email": "john.doe@company.com",
  "is_admin": false,
  "created_at": "2025-10-01T10:00:00Z",
  "last_login": "2025-10-13T15:30:00Z"
}
```

### Task

```json
{
  "id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "filename": "meeting_recording.mp3",
  "file_path": "/data/uploads/1/550e8400_meeting_recording.mp3",
  "file_size": 15728640,
  "file_format": "mp3",
  "model_name": "large-v3-turbo",
  "language": "ja",
  "num_speakers": 2,
  "status": "completed",
  "progress": 100,
  "created_at": "2025-10-13T10:00:00Z",
  "started_at": "2025-10-13T10:00:15Z",
  "completed_at": "2025-10-13T10:03:45Z",
  "error_message": null
}
```

### Transcription

```json
{
  "id": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "transcription_text": "Full transcription text...",
  "segments": [
    {
      "id": 0,
      "start": 0.0,
      "end": 5.5,
      "text": "Segment text",
      "speaker_id": 1,
      "speaker_label": "Speaker 1",
      "confidence": 0.95
    }
  ],
  "subtitle_path": "/data/results/550e8400/subtitles.srt",
  "created_at": "2025-10-13T10:03:45Z"
}
```

### Processing History

```json
{
  "id": 1,
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "user_id": 1,
  "processing_time_seconds": 210,
  "gpu_memory_used_mb": 8500,
  "model_name": "large-v3-turbo",
  "file_format": "mp3",
  "file_size_mb": 15.0,
  "success": true,
  "error_type": null,
  "created_at": "2025-10-13T10:03:45Z"
}
```

## Error Responses

All error responses follow this format:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-10-13T15:30:00Z"
}
```

### Common Error Codes

| Code | HTTP Status | Description |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | Invalid username or password |
| `TOKEN_EXPIRED` | 401 | Access token has expired |
| `INVALID_TOKEN` | 401 | Invalid or malformed token |
| `INSUFFICIENT_PERMISSIONS` | 403 | User lacks required permissions |
| `RESOURCE_NOT_FOUND` | 404 | Requested resource does not exist |
| `FILE_TOO_LARGE` | 413 | Uploaded file exceeds size limit |
| `INVALID_FILE_FORMAT` | 400 | Unsupported file format |
| `VALIDATION_ERROR` | 422 | Request validation failed |
| `RATE_LIMIT_EXCEEDED` | 429 | Too many requests |
| `GPU_UNAVAILABLE` | 503 | GPU is not available |
| `LDAP_UNAVAILABLE` | 503 | LDAP server is unavailable |

### Validation Error Response

```json
{
  "detail": [
    {
      "loc": ["body", "model_name"],
      "msg": "field required",
      "type": "value_error.missing"
    }
  ]
}
```

## Rate Limiting

### API Rate Limits

- **General API endpoints**: 10 requests/second per IP
- **File upload endpoint**: 2 requests/second per IP
- **Burst limit**: 20 requests for general endpoints, 5 for uploads

### Rate Limit Headers

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1634132400
```

### Rate Limit Exceeded Response

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

## Pagination

Endpoints that return lists support pagination with these parameters:

- `page`: Page number (starting from 1)
- `page_size`: Number of items per page (max: 100)

Pagination response format:

```json
{
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 1,
    "page_size": 20,
    "total_pages": 8
  }
}
```

## Filtering and Sorting

Many list endpoints support filtering and sorting:

**Filtering**:
- `status=completed`
- `success=true`
- `model_name=large-v3-turbo`

**Sorting**:
- `sort_by=created_at`
- `sort_order=desc`

**Example**:
```
GET /api/v1/tasks?status=completed&sort_by=created_at&sort_order=desc&page=1&page_size=20
```

## WebSocket API (Future Feature)

Real-time transcription status updates will be available via WebSocket in a future release.

**Endpoint**: `wss://yourdomain.com/ws/tasks/{task_id}`

**Authentication**: Token passed as query parameter (`?token=<access_token>`)

## SDK and Client Libraries

Official client libraries:
- Python SDK (coming soon)
- JavaScript/TypeScript SDK (coming soon)
- Go SDK (coming soon)

## API Changelog

### Version 1.0.0 (2025-10-13)
- Initial API release
- Authentication API
- Upload API
- Task Management API
- Transcription API
- History API
- Admin API

## Support

- **API Documentation**: https://yourdomain.com/docs (Swagger UI)
- **GitHub Issues**: https://github.com/your-org/whisper-app/issues
- **Contact**: api-support@company.com
