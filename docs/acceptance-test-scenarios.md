# Acceptance Test Scenarios

**Project**: Whisper App - Audio/Video Transcription System
**Version**: 1.0.0
**Date**: 2025-10-13
**Phase**: Phase 10 - Acceptance Testing and Release

## Table of Contents

1. [Test Objectives](#test-objectives)
2. [Test Environment](#test-environment)
3. [Test Criteria](#test-criteria)
4. [User Workflow Scenarios](#user-workflow-scenarios)
5. [Functional Test Scenarios](#functional-test-scenarios)
6. [Performance Test Scenarios](#performance-test-scenarios)
7. [Security Test Scenarios](#security-test-scenarios)
8. [Compatibility Test Scenarios](#compatibility-test-scenarios)
9. [Error Handling Test Scenarios](#error-handling-test-scenarios)
10. [Test Execution Checklist](#test-execution-checklist)

---

## Test Objectives

### Primary Objectives
1. Verify all functional requirements are met per `docs/requirement.md`
2. Validate system performance under expected load (20 concurrent users)
3. Ensure security measures are properly implemented
4. Confirm user interface is intuitive and responsive
5. Validate data integrity and accuracy of transcription results

### Success Criteria
- ✅ All critical user workflows complete successfully
- ✅ System handles 20 concurrent users without degradation
- ✅ All security tests pass without vulnerabilities
- ✅ Cross-browser compatibility confirmed
- ✅ No critical or high-priority bugs remain

---

## Test Environment

### Hardware Requirements
- **GPU**: NVIDIA GPU with 20GB+ VRAM (for production testing)
- **CPU**: 8+ cores
- **RAM**: 32GB+
- **Storage**: 500GB+ SSD

### Software Requirements
- **OS**: Ubuntu 22.04 LTS or equivalent
- **Docker**: 24.0+
- **Docker Compose**: 2.20+
- **NVIDIA Driver**: 535.xx or later
- **CUDA**: 11.8 or 12.4

### Test Data
- **Audio Files**: MP3, WAV, M4A, FLAC, OGG (various sizes: 1MB, 100MB, 500MB, 1GB)
- **Video Files**: MP4, AVI, MOV, MKV (various sizes: 10MB, 500MB, 1GB)
- **Sample Content**:
  - Japanese speech (multiple speakers)
  - English speech (single speaker)
  - Mixed language content
  - Background noise variations

### Test Accounts
- **Admin User**: `admin` / `admin123` (is_admin=true)
- **Regular Users**: `user1` / `user123`, `user2` / `user123`
- **LDAP Test Users**: Configure per environment

---

## Test Criteria

### Pass/Fail Criteria

| Severity | Criteria |
|----------|----------|
| **Critical** | No critical bugs (system crash, data loss, security breach) |
| **High** | ≤ 2 high-priority bugs (major functionality broken) |
| **Medium** | ≤ 10 medium-priority bugs (minor functionality issues) |
| **Low** | ≤ 20 low-priority bugs (cosmetic issues, minor UX problems) |

### Performance Acceptance Criteria
- API response time: < 200ms (95th percentile)
- File upload: Support up to 1GB files
- Transcription processing: Complete within expected time (file duration × 0.5 for GPU)
- Concurrent users: Support 20 simultaneous users
- System uptime: 99.9% during test period

---

## User Workflow Scenarios

### UAT-001: Complete General User Workflow

**Objective**: Validate the complete workflow for a general user from login to result download.

**Preconditions**:
- System is running (`docker-compose -f docker-compose.prod.yml up -d`)
- Test account `user1` / `user123` exists
- Sample audio file ready (e.g., 24-second MP3 with 2 speakers)

**Test Steps**:

1. **Login**
   - Navigate to `https://yourdomain.com`
   - Enter username: `user1`, password: `user123`
   - Click "ログイン" button
   - **Expected**: Redirect to dashboard, welcome message displayed

2. **Navigate to Upload**
   - Click "アップロード" button on dashboard
   - **Expected**: Upload page displays with drag-and-drop area

3. **Upload Audio File**
   - Drag and drop sample MP3 file to upload area
   - Select model: "Large V3 Turbo"
   - Select language: "日本語"
   - Enter number of speakers: "2"
   - Click "アップロード開始" button
   - **Expected**:
     - Upload progress bar shows 0% → 100%
     - Success message displayed
     - Redirect to task detail page

4. **Monitor Task Progress**
   - Observe task status polling (every 3 seconds)
   - **Expected**:
     - Status changes: "待機中" → "処理中" → "完了"
     - Progress bar updates: 0% → 10% → 20% → ... → 100%
     - Processing time displayed
     - No errors in browser console

5. **View Transcription Results**
   - Task status shows "完了" (completed)
   - Transcription viewer automatically appears
   - **Expected**:
     - Full transcription text displayed
     - Segments list shows with timestamps (HH:MM:SS.mmm)
     - Speaker labels displayed (Speaker 1, Speaker 2)
     - Edit buttons visible for each segment

6. **Edit Segment**
   - Click edit icon on first segment
   - Modify text content
   - Click "保存" button
   - **Expected**:
     - Segment text updates in UI
     - Success message displayed
     - Full transcription text refreshes with edit

7. **Download Subtitle Files**
   - Click "SRT ダウンロード" button
   - Click "VTT ダウンロード" button
   - **Expected**:
     - SRT file downloads with correct format (HH:MM:SS,mmm)
     - VTT file downloads with correct format (HH:MM:SS.mmm)
     - Both files contain speaker labels
     - File content matches edited transcription

8. **View Processing History**
   - Click "履歴を見る" button
   - **Expected**:
     - Processing history page displays
     - Statistics cards show correct data
     - Task appears in history table with all details

9. **Logout**
   - Click "ログアウト" button in header
   - **Expected**: Redirect to login page, session cleared

**Pass Criteria**: All steps complete without errors, transcription is accurate, files download correctly.

---

### UAT-002: Administrator Workflow

**Objective**: Validate administrator-specific functionality.

**Preconditions**:
- Admin account `admin` / `admin123` exists (is_admin=true)

**Test Steps**:

1. **Admin Login**
   - Login as admin user
   - **Expected**: Dashboard shows admin-specific button "管理者ダッシュボード"

2. **View Admin Dashboard**
   - Click "管理者ダッシュボード" button
   - **Expected**:
     - System status cards display (GPU info, worker status, queue status)
     - Overall statistics display (total users, total tasks)
     - Model usage statistics table
     - File format statistics table
     - Hourly processing chart (Chart.js)

3. **Monitor System Status**
   - Check GPU memory usage
   - Check Celery worker status
   - Check task queue counts (pending, processing)
   - **Expected**: All metrics display accurate real-time data

4. **View All Users' Tasks**
   - Navigate to task list
   - **Expected**: Can see tasks from all users (not just own tasks)

5. **View All Processing History**
   - Navigate to processing history
   - **Expected**: Can see history from all users

6. **Auto-Refresh Functionality**
   - Wait 30 seconds on admin dashboard
   - **Expected**: Dashboard auto-refreshes with updated data

**Pass Criteria**: All admin features work correctly, proper access control enforced.

---

### UAT-003: Multiple File Upload Workflow

**Objective**: Test handling of multiple file uploads by single user.

**Test Steps**:

1. Login as `user1`
2. Upload 3 files sequentially:
   - File 1: Small MP3 (5MB, model: Tiny)
   - File 2: Medium MP4 (100MB, model: Large V3 Turbo)
   - File 3: Large WAV (500MB, model: Large V3)
3. Monitor all tasks in task list
4. Verify all tasks complete successfully
5. Check processing history shows all 3 tasks

**Expected**:
- All files upload successfully
- Tasks process in queue order
- GPU memory managed properly (no OOM errors)
- Each task completes with correct results
- History shows all 3 tasks with correct metadata

**Pass Criteria**: All 3 files process successfully without system issues.

---

## Functional Test Scenarios

### FT-001: Authentication and Authorization

#### FT-001-1: Valid Login
- **Input**: Valid username and password
- **Expected**: Successful login, JWT token issued, redirect to dashboard
- **Validation**: Check localStorage for auth token, verify API requests include token

#### FT-001-2: Invalid Login
- **Input**: Invalid username or password
- **Expected**: Error message "ログインに失敗しました", remain on login page
- **Validation**: No token stored, no redirect

#### FT-001-3: Session Persistence
- **Test**: Login, close browser, reopen, navigate to app URL
- **Expected**: User remains logged in (if token not expired)

#### FT-001-4: Token Expiration
- **Test**: Wait for access token to expire (15 minutes)
- **Expected**: Refresh token automatically used, new access token issued
- **Validation**: Check network tab for `/api/v1/auth/refresh` call

#### FT-001-5: Authorization - General User
- **Test**: Login as regular user, attempt to access `/admin` route
- **Expected**: Forbidden error or redirect to dashboard
- **Validation**: Admin endpoints return 403 status

#### FT-001-6: Authorization - Admin User
- **Test**: Login as admin, access `/admin` route
- **Expected**: Admin dashboard displays successfully
- **Validation**: Admin endpoints return 200 status

---

### FT-002: File Upload Validation

#### FT-002-1: Supported Audio Formats
- **Test**: Upload files in each supported audio format
- **Formats**: MP3, WAV, M4A, FLAC, OGG
- **Expected**: All formats accepted and processed successfully

#### FT-002-2: Supported Video Formats
- **Test**: Upload files in each supported video format
- **Formats**: MP4, AVI, MOV, MKV
- **Expected**: All formats accepted, audio extracted, transcription successful

#### FT-002-3: Unsupported Format
- **Test**: Attempt to upload .txt, .pdf, .doc files
- **Expected**: Client-side validation error, file rejected before upload

#### FT-002-4: File Size Limit - Within Limit
- **Test**: Upload 1GB file (maximum allowed)
- **Expected**: Upload succeeds, processing begins

#### FT-002-5: File Size Limit - Exceeded
- **Test**: Attempt to upload 1.5GB file
- **Expected**: Client-side error "ファイルサイズは1GB以下である必要があります"

#### FT-002-6: Drag and Drop Upload
- **Test**: Drag file from file system, drop into upload area
- **Expected**: File selected, ready for upload

#### FT-002-7: Click to Upload
- **Test**: Click upload area, select file from file picker
- **Expected**: File selected, ready for upload

---

### FT-003: Transcription Processing

#### FT-003-1: Model Selection - Tiny
- **Test**: Upload audio, select "Tiny" model
- **Expected**: Fast processing (< 5 seconds for 30-second audio), acceptable accuracy

#### FT-003-2: Model Selection - Large V3
- **Test**: Upload audio, select "Large V3" model
- **Expected**: Slower processing, high accuracy

#### FT-003-3: Model Selection - Large V3 Turbo
- **Test**: Upload audio, select "Large V3 Turbo" model
- **Expected**: Balanced speed and accuracy

#### FT-003-4: Language Selection - Japanese
- **Test**: Upload Japanese audio, select "日本語"
- **Expected**: Accurate Japanese transcription

#### FT-003-5: Language Selection - English
- **Test**: Upload English audio, select "English"
- **Expected**: Accurate English transcription

#### FT-003-6: Language Auto-Detection
- **Test**: Upload mixed-language audio, select "Auto"
- **Expected**: Whisper detects language automatically, transcription successful

#### FT-003-7: Progress Tracking
- **Test**: Monitor task progress during processing
- **Expected**: Progress updates at each stage (10%, 20%, 30%, 50%, 80%, 100%)

#### FT-003-8: Processing Failure Handling
- **Test**: Upload corrupted audio file or trigger processing error
- **Expected**: Task status shows "失敗", error message displayed, no system crash

---

### FT-004: Speaker Diarization

#### FT-004-1: Specified Speaker Count
- **Test**: Upload 2-speaker audio, specify "2" speakers
- **Expected**: Segments labeled with Speaker 1 and Speaker 2 correctly

#### FT-004-2: Auto Speaker Detection
- **Test**: Upload multi-speaker audio, leave speaker count empty
- **Expected**: System automatically detects number of speakers

#### FT-004-3: Single Speaker
- **Test**: Upload single-speaker audio, specify "1" speaker
- **Expected**: All segments labeled as Speaker 1

#### FT-004-4: Many Speakers
- **Test**: Upload audio with 5+ speakers, specify count
- **Expected**: Segments labeled with multiple speaker IDs

---

### FT-005: Result Editing

#### FT-005-1: Edit Segment Text
- **Test**: Click edit on segment, modify text, save
- **Expected**: Text updates in UI and database, full transcription refreshes

#### FT-005-2: Edit Timestamp - Start Time
- **Test**: Edit segment start time
- **Expected**: Timestamp updates, validates (start < end)

#### FT-005-3: Edit Timestamp - End Time
- **Test**: Edit segment end time
- **Expected**: Timestamp updates, validates (end > start)

#### FT-005-4: Edit Speaker Label
- **Test**: Change speaker label from "Speaker 1" to "John"
- **Expected**: Label updates for that segment only

#### FT-005-5: Cancel Edit
- **Test**: Click edit, modify values, click cancel
- **Expected**: Changes discarded, original values remain

#### FT-005-6: Edit Permission - Own Task
- **Test**: User edits their own task's transcription
- **Expected**: Edit succeeds

#### FT-005-7: Edit Permission - Other User's Task
- **Test**: User attempts to edit another user's task (if URL known)
- **Expected**: 403 Forbidden error (unless admin)

---

### FT-006: Subtitle File Generation

#### FT-006-1: SRT Format Download
- **Test**: Download SRT subtitle file
- **Expected**:
  - File format: `HH:MM:SS,mmm --> HH:MM:SS,mmm`
  - Speaker labels: `[Speaker 1]`, `[Speaker 2]`
  - Correct encoding (UTF-8)

#### FT-006-2: VTT Format Download
- **Test**: Download WebVTT subtitle file
- **Expected**:
  - File starts with `WEBVTT`
  - Format: `HH:MM:SS.mmm --> HH:MM:SS.mmm`
  - Speaker labels: `<v Speaker 1>`, `<v Speaker 2>`

#### FT-006-3: Subtitle Reflects Edits
- **Test**: Edit transcription, then download subtitle
- **Expected**: Downloaded file includes edited content

---

### FT-007: Task Management

#### FT-007-1: Task List - Own Tasks
- **Test**: Regular user views task list
- **Expected**: Only sees own tasks, pagination works

#### FT-007-2: Task List - All Tasks (Admin)
- **Test**: Admin views task list
- **Expected**: Sees all users' tasks

#### FT-007-3: Task Detail View
- **Test**: Click on task in list
- **Expected**: Navigates to task detail page with all info

#### FT-007-4: Task Deletion - Own Task
- **Test**: User deletes own task
- **Expected**: Task and associated files deleted, removed from list

#### FT-007-5: Task Deletion - Other User's Task
- **Test**: User attempts to delete another user's task
- **Expected**: 403 Forbidden error

#### FT-007-6: Task Status Polling
- **Test**: Monitor network tab during task processing
- **Expected**: Status endpoint polled every 3 seconds

---

### FT-008: Processing History

#### FT-008-1: History List Display
- **Test**: View processing history page
- **Expected**: Table shows all completed tasks with metadata (date, model, format, size, time, GPU usage, status)

#### FT-008-2: Statistics Cards
- **Test**: Check statistics at top of history page
- **Expected**: Accurate counts for total processed, success rate, average time, total file size

#### FT-008-3: History Pagination
- **Test**: Navigate through history pages
- **Expected**: Pagination controls work, shows correct page numbers

#### FT-008-4: History Filtering
- **Test**: Filter by success/failed, or by model name
- **Expected**: Results filtered correctly

---

### FT-009: Admin Dashboard

#### FT-009-1: System Status Display
- **Test**: View system status cards
- **Expected**: Shows GPU memory, Celery worker count, queue counts

#### FT-009-2: Overall Statistics
- **Test**: View overall statistics
- **Expected**: Shows total users, total tasks, average processing time

#### FT-009-3: Model Usage Statistics
- **Test**: View model usage table
- **Expected**: Shows usage count for each Whisper model

#### FT-009-4: File Format Statistics
- **Test**: View file format table
- **Expected**: Shows upload count for each file format

#### FT-009-5: Hourly Processing Chart
- **Test**: View Chart.js graph
- **Expected**: Bar chart shows processing counts by hour for last 24 hours

#### FT-009-6: Manual Refresh
- **Test**: Click "更新" button
- **Expected**: Dashboard data refreshes immediately

#### FT-009-7: Auto Refresh
- **Test**: Wait 30 seconds without interaction
- **Expected**: Dashboard auto-refreshes with updated data

---

## Performance Test Scenarios

### PT-001: Concurrent User Load Test

**Objective**: Validate system handles 20 concurrent users.

**Test Setup**:
- Tool: Locust or Apache JMeter
- Users: 20 virtual users
- Duration: 30 minutes
- Scenario: Each user performs login → upload → monitor → logout cycle

**Metrics to Measure**:
- API response time (p50, p95, p99)
- Upload throughput (MB/s)
- Task processing time
- Error rate
- System resource usage (CPU, RAM, GPU VRAM)

**Pass Criteria**:
- API response time p95 < 500ms
- Error rate < 1%
- All tasks complete successfully
- No system crashes or memory leaks

---

### PT-002: Large File Upload Test

**Test**: Upload 1GB video file

**Expected**:
- Upload completes within reasonable time (depends on network)
- No timeout errors
- Memory usage remains stable
- Processing completes successfully

**Pass Criteria**: File uploads and processes without errors.

---

### PT-003: GPU Memory Management Test

**Test**: Queue multiple large model tasks (Large V3) exceeding GPU memory

**Expected**:
- Tasks queue properly
- GPU memory monitored before task start
- Tasks execute sequentially without OOM errors
- No system crash

**Pass Criteria**: All tasks complete, GPU memory never exceeds available VRAM.

---

### PT-004: Database Query Performance Test

**Objective**: Validate database indexes and caching work effectively.

**Test Steps**:
1. Populate database with 10,000 tasks and 5,000 processing history records
2. Measure query performance for:
   - Task list with pagination
   - Processing history with filters
   - Admin dashboard statistics

**Pass Criteria**:
- Task list query < 100ms
- History query < 150ms
- Dashboard stats query < 50ms (with Redis cache hit)
- Dashboard stats query < 500ms (cache miss)

---

### PT-005: Transcription Processing Speed Test

**Test**: Measure transcription speed for various file sizes and models

**Test Matrix**:

| File Duration | File Size | Model | Expected Time (GPU) |
|--------------|-----------|-------|---------------------|
| 30 seconds | 5MB | Tiny | < 10 seconds |
| 30 seconds | 5MB | Large V3 Turbo | < 20 seconds |
| 5 minutes | 50MB | Large V3 Turbo | < 3 minutes |
| 30 minutes | 300MB | Large V3 | < 20 minutes |

**Pass Criteria**: Processing times within expected ranges (±20%).

---

## Security Test Scenarios

### ST-001: Authentication Security

#### ST-001-1: SQL Injection in Login
- **Test**: Enter SQL injection payloads in username/password fields
- **Examples**: `' OR '1'='1`, `admin'--`, `'; DROP TABLE users--`
- **Expected**: All attempts rejected, no SQL execution, proper error handling

#### ST-001-2: Brute Force Protection
- **Test**: Attempt 50 failed login attempts rapidly
- **Expected**: Rate limiting applies, temporary lockout or CAPTCHA challenge

#### ST-001-3: JWT Token Manipulation
- **Test**: Modify JWT token payload (e.g., change user_id or is_admin flag)
- **Expected**: Token validation fails, 401 Unauthorized error

#### ST-001-4: Expired Token Handling
- **Test**: Use expired access token for API request
- **Expected**: 401 Unauthorized, client should refresh token

#### ST-001-5: Session Hijacking Prevention
- **Test**: Copy JWT token to different browser/machine
- **Expected**: Token works (stateless), but should only work until expiration

---

### ST-002: Authorization Security

#### ST-002-1: Horizontal Privilege Escalation
- **Test**: User1 attempts to access User2's task via direct URL
- **Expected**: 403 Forbidden error, no data leaked

#### ST-002-2: Vertical Privilege Escalation
- **Test**: Regular user attempts to access admin endpoints
- **Expected**: 403 Forbidden error

#### ST-002-3: API Endpoint Enumeration
- **Test**: Attempt to access undocumented or internal endpoints
- **Expected**: 404 Not Found or 403 Forbidden, no information disclosure

---

### ST-003: File Upload Security

#### ST-003-1: Malicious File Upload - Executable
- **Test**: Attempt to upload .exe, .sh, .bat files
- **Expected**: Rejected by file type validation

#### ST-003-2: Malicious File Upload - Path Traversal
- **Test**: Upload file with name like `../../etc/passwd.mp3`
- **Expected**: File name sanitized, no path traversal

#### ST-003-3: File Size Bomb
- **Test**: Upload file with misleading header (claims 10MB, actually 2GB)
- **Expected**: Upload rejected once true size detected

#### ST-003-4: Malformed Media File
- **Test**: Upload file with valid extension but corrupted/malicious content
- **Expected**: FFmpeg or Whisper fails gracefully, error logged, no system compromise

---

### ST-004: Cross-Site Scripting (XSS)

#### ST-004-1: Stored XSS in Transcription
- **Test**: Edit segment text to include `<script>alert('XSS')</script>`
- **Expected**: Text rendered as plain text, no script execution

#### ST-004-2: Reflected XSS in URL Parameters
- **Test**: Add script tags to URL parameters
- **Expected**: Parameters sanitized, no script execution

---

### ST-005: Cross-Site Request Forgery (CSRF)

**Test**: Create malicious page that attempts to trigger API requests while user is authenticated

**Expected**:
- Requests from different origin blocked by CORS
- No state-changing operations succeed without proper authentication

---

### ST-006: Information Disclosure

#### ST-006-1: Error Messages
- **Test**: Trigger various errors, check error messages
- **Expected**: No stack traces, database info, or system paths leaked to client

#### ST-006-2: API Endpoint Documentation
- **Test**: Access `/docs` and `/redoc` endpoints
- **Expected**:
  - Should be disabled in production or require authentication
  - If enabled, should not expose sensitive implementation details

---

## Compatibility Test Scenarios

### CT-001: Browser Compatibility

**Test Matrix**:

| Browser | Version | Platform | Test Result |
|---------|---------|----------|-------------|
| Chrome | Latest | Windows 10 | ✅ |
| Chrome | Latest | macOS | ✅ |
| Chrome | Latest | Linux | ✅ |
| Firefox | Latest | Windows 10 | ✅ |
| Firefox | Latest | macOS | ✅ |
| Safari | Latest | macOS | ✅ |
| Safari | Latest | iOS | ✅ |
| Edge | Latest | Windows 10 | ✅ |

**Test Scenarios for Each Browser**:
1. Login and logout
2. File upload (drag-and-drop and click)
3. View transcription results
4. Edit segment
5. Download subtitle files
6. View processing history
7. View admin dashboard (admin only)

**Pass Criteria**: All core functionality works without errors in each browser.

---

### CT-002: Responsive Design

**Test Viewports**:

| Device | Resolution | Orientation |
|--------|-----------|-------------|
| Desktop | 1920x1080 | Landscape |
| Laptop | 1366x768 | Landscape |
| Tablet (iPad) | 1024x768 | Landscape |
| Tablet (iPad) | 768x1024 | Portrait |
| Mobile (iPhone) | 390x844 | Portrait |
| Mobile (Android) | 360x640 | Portrait |

**Test Cases**:
- Navigation menu adapts to mobile (hamburger menu)
- Tables responsive or horizontally scrollable
- Forms stack vertically on mobile
- Buttons and touch targets ≥ 44x44px on mobile
- Text remains readable without horizontal scroll

**Pass Criteria**: UI is usable and functional on all tested viewports.

---

### CT-003: Network Conditions

**Test Scenarios**:

| Condition | Bandwidth | Latency | Test Result |
|-----------|-----------|---------|-------------|
| Fast 3G | 1.6 Mbps | 150ms | |
| Slow 3G | 400 Kbps | 400ms | |
| Offline | 0 | - | |

**Test Cases**:
- File upload on slow connection (progress tracking works)
- Task status polling on high latency (no errors)
- Offline behavior (graceful error messages)

**Pass Criteria**: App remains functional on slow connections, provides clear feedback.

---

## Error Handling Test Scenarios

### EH-001: Network Errors

#### EH-001-1: Upload Interruption
- **Test**: Start file upload, disconnect network mid-upload
- **Expected**: Error message displayed, user can retry

#### EH-001-2: API Request Timeout
- **Test**: Trigger slow API response (using network throttling)
- **Expected**: Request times out gracefully, error message shown

#### EH-001-3: WebSocket/Polling Failure
- **Test**: Block status polling endpoint
- **Expected**: Polling retries with backoff, error shown if persistent failure

---

### EH-002: Processing Errors

#### EH-002-1: Audio Extraction Failure
- **Test**: Upload video with no audio track
- **Expected**: Task fails with error "音声トラックが見つかりません", error logged

#### EH-002-2: Whisper Model Loading Failure
- **Test**: Simulate model file corruption or missing
- **Expected**: Task fails with error, system remains operational

#### EH-002-3: GPU Out of Memory
- **Test**: Queue many large model tasks simultaneously
- **Expected**: Tasks queue properly, error if OOM occurs, system recovers

#### EH-002-4: Celery Worker Crash
- **Test**: Stop Celery worker during task processing
- **Expected**: Task marked as failed after timeout, can be retried

---

### EH-003: Database Errors

#### EH-003-1: Database Connection Lost
- **Test**: Stop PostgreSQL during API request
- **Expected**: 503 Service Unavailable error, system recovers when DB restarts

#### EH-003-2: Redis Connection Lost
- **Test**: Stop Redis during task queue operation
- **Expected**: Tasks fail to queue, error message shown, system recovers when Redis restarts

---

### EH-004: Validation Errors

#### EH-004-1: Invalid File Format
- **Test**: Rename .txt file to .mp3 and upload
- **Expected**: Validation error during processing, task fails with clear message

#### EH-004-2: Invalid Timestamp Edit
- **Test**: Edit segment with end time < start time
- **Expected**: Client-side validation error before API call

#### EH-004-3: Invalid Speaker Count
- **Test**: Enter speaker count = 0 or > 10
- **Expected**: Form validation error, cannot submit

---

## Test Execution Checklist

### Pre-Test Setup

- [ ] Production environment deployed (`docker-compose -f docker-compose.prod.yml up -d`)
- [ ] All services healthy (backend, celery-worker, postgres, redis, nginx)
- [ ] Test accounts created and verified
- [ ] Test data prepared (audio/video files of various sizes and formats)
- [ ] GPU available and properly configured
- [ ] SSL certificate installed and valid
- [ ] Monitoring tools configured (optional: Grafana, Prometheus)

### Test Execution

#### Day 1: User Workflow Testing
- [ ] UAT-001: Complete General User Workflow
- [ ] UAT-002: Administrator Workflow
- [ ] UAT-003: Multiple File Upload Workflow
- [ ] Document any bugs found with severity labels

#### Day 2: Functional Testing (Part 1)
- [ ] FT-001: Authentication and Authorization (all sub-tests)
- [ ] FT-002: File Upload Validation (all sub-tests)
- [ ] FT-003: Transcription Processing (all sub-tests)
- [ ] Document bugs

#### Day 3: Functional Testing (Part 2)
- [ ] FT-004: Speaker Diarization (all sub-tests)
- [ ] FT-005: Result Editing (all sub-tests)
- [ ] FT-006: Subtitle File Generation (all sub-tests)
- [ ] FT-007: Task Management (all sub-tests)
- [ ] FT-008: Processing History (all sub-tests)
- [ ] FT-009: Admin Dashboard (all sub-tests)
- [ ] Document bugs

#### Day 4: Performance Testing
- [ ] PT-001: Concurrent User Load Test (20 users, 30 minutes)
- [ ] PT-002: Large File Upload Test (1GB file)
- [ ] PT-003: GPU Memory Management Test
- [ ] PT-004: Database Query Performance Test
- [ ] PT-005: Transcription Processing Speed Test
- [ ] Record performance metrics

#### Day 5: Security Testing
- [ ] ST-001: Authentication Security (all sub-tests)
- [ ] ST-002: Authorization Security (all sub-tests)
- [ ] ST-003: File Upload Security (all sub-tests)
- [ ] ST-004: Cross-Site Scripting (XSS)
- [ ] ST-005: Cross-Site Request Forgery (CSRF)
- [ ] ST-006: Information Disclosure
- [ ] Document security findings

#### Day 6: Compatibility and Error Handling
- [ ] CT-001: Browser Compatibility (all browsers)
- [ ] CT-002: Responsive Design (all viewports)
- [ ] CT-003: Network Conditions
- [ ] EH-001: Network Errors (all sub-tests)
- [ ] EH-002: Processing Errors (all sub-tests)
- [ ] EH-003: Database Errors (all sub-tests)
- [ ] EH-004: Validation Errors (all sub-tests)
- [ ] Document compatibility issues and error handling gaps

#### Day 7: Bug Fix and Regression Testing
- [ ] Review all documented bugs
- [ ] Prioritize bugs (Critical, High, Medium, Low)
- [ ] Fix critical and high-priority bugs
- [ ] Re-run affected test scenarios (regression testing)
- [ ] Verify all fixes work correctly

#### Day 8: Final Validation
- [ ] Re-run UAT-001, UAT-002, UAT-003 (end-to-end workflows)
- [ ] Verify no critical or high-priority bugs remain
- [ ] Confirm performance metrics meet acceptance criteria
- [ ] Sign-off on acceptance test completion

### Post-Test Activities

- [ ] Compile test results report
- [ ] Update bug tracking system
- [ ] Document known issues and workarounds
- [ ] Update release notes with bug fixes
- [ ] Prepare for production deployment

---

## Test Results Template

### Test Summary

| Test Category | Total Tests | Passed | Failed | Blocked | Pass Rate |
|--------------|-------------|--------|--------|---------|-----------|
| User Workflows | 3 | | | | |
| Functional Tests | 50+ | | | | |
| Performance Tests | 5 | | | | |
| Security Tests | 15+ | | | | |
| Compatibility Tests | 3 | | | | |
| Error Handling Tests | 12+ | | | | |
| **Total** | **88+** | | | | |

### Bug Summary

| Severity | Open | Fixed | Total |
|----------|------|-------|-------|
| Critical | | | |
| High | | | |
| Medium | | | |
| Low | | | |
| **Total** | | | |

### Performance Metrics

| Metric | Target | Actual | Status |
|--------|--------|--------|--------|
| API Response Time (p95) | < 500ms | | |
| Concurrent Users | 20 | | |
| Large File Upload | 1GB | | |
| Transcription Speed | File duration × 0.5 | | |
| Error Rate | < 1% | | |

### Security Findings

| Finding | Severity | Status |
|---------|----------|--------|
| | | |

### Sign-off

| Role | Name | Signature | Date |
|------|------|-----------|------|
| QA Lead | | | |
| Product Manager | | | |
| Technical Lead | | | |
| Project Manager | | | |

---

## Appendix

### A. Test Data Preparation

**Sample Audio Files**:
```bash
# Download or prepare test files
/data/test-files/
├── audio/
│   ├── japanese-2speakers-24s.mp3 (24 seconds, 2 speakers, Japanese)
│   ├── english-1speaker-60s.wav (1 minute, single speaker, English)
│   ├── mixed-language-5min.m4a (5 minutes, mixed JP/EN)
│   └── large-meeting-30min.flac (30 minutes, 5 speakers)
└── video/
    ├── zoom-recording-10min.mp4 (10 minutes, 2 speakers)
    ├── teams-recording-500mb.avi (500MB video file)
    └── large-video-1gb.mkv (1GB video file for size testing)
```

### B. Test Tools and Scripts

**Load Testing Script (Locust)**:
```python
# locustfile.py
from locust import HttpUser, task, between
import os

class WhisperAppUser(HttpUser):
    wait_time = between(1, 5)

    def on_start(self):
        # Login
        response = self.client.post("/api/v1/auth/login", json={
            "username": "user1",
            "password": "user123"
        })
        self.token = response.json()["access_token"]
        self.client.headers.update({"Authorization": f"Bearer {self.token}"})

    @task(3)
    def view_tasks(self):
        self.client.get("/api/v1/tasks")

    @task(1)
    def upload_file(self):
        # Upload test file
        with open("test.mp3", "rb") as f:
            self.client.post("/api/v1/upload", files={"file": f}, data={
                "model_name": "tiny",
                "language": "ja"
            })
```

### C. Browser Automation Script (Playwright)

```javascript
// e2e-test.spec.js
const { test, expect } = require('@playwright/test');

test('complete user workflow', async ({ page }) => {
  // Login
  await page.goto('https://yourdomain.com');
  await page.fill('input[name="username"]', 'user1');
  await page.fill('input[name="password"]', 'user123');
  await page.click('button[type="submit"]');

  // Wait for dashboard
  await expect(page).toHaveURL(/.*dashboard/);

  // Navigate to upload
  await page.click('text=アップロード');

  // Upload file
  const fileInput = await page.locator('input[type="file"]');
  await fileInput.setInputFiles('test-audio.mp3');

  // Set parameters
  await page.selectOption('select[name="model"]', 'tiny');
  await page.selectOption('select[name="language"]', 'ja');

  // Start upload
  await page.click('text=アップロード開始');

  // Wait for completion
  await page.waitForSelector('text=完了', { timeout: 60000 });

  // Verify results
  const transcriptionText = await page.textContent('.transcription-text');
  expect(transcriptionText).toBeTruthy();
});
```

### D. Security Testing Tools

- **OWASP ZAP**: Automated security scanning
- **Burp Suite**: Manual security testing
- **SQLMap**: SQL injection testing
- **JWT Tool**: JWT token manipulation testing

### E. Performance Monitoring Commands

```bash
# Monitor Docker container resources
docker stats

# Monitor GPU usage
nvidia-smi -l 1

# Monitor PostgreSQL queries
docker exec -it postgres psql -U whisper_prod -d whisper_prod -c "SELECT * FROM pg_stat_activity;"

# Monitor Redis
docker exec -it redis redis-cli INFO stats

# Monitor Celery tasks
docker exec -it celery-worker celery -A app.celery_app inspect active
```

---

**Document Version**: 1.0
**Last Updated**: 2025-10-13
**Status**: Ready for Execution
