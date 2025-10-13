# API仕様

Whisper Appバックエンドの完全なAPIドキュメント。

## 目次

1. [概要](#概要)
2. [認証](#認証)
3. [APIエンドポイント](#apiエンドポイント)
   - [認証API](#認証api)
   - [アップロードAPI](#アップロードapi)
   - [タスク管理API](#タスク管理api)
   - [文字起こしAPI](#文字起こしapi)
   - [履歴API](#履歴api)
   - [管理者API](#管理者api)
4. [データモデル](#データモデル)
5. [エラーレスポンス](#エラーレスポンス)
6. [レート制限](#レート制限)

## 概要

**ベースURL**: `https://yourdomain.com/api/v1`

**コンテンツタイプ**: `application/json` (ファイルアップロードを除く: `multipart/form-data`)

**認証**: Bearer Token (JWT)

**APIバージョン**: v1

### HTTPステータスコード

| コード | 説明 |
|------|-------------|
| 200 | 成功 (OK) |
| 201 | 作成完了 |
| 204 | コンテンツなし (削除成功) |
| 400 | 不正なリクエスト (検証エラー) |
| 401 | 認証されていません (トークンが無効または欠落) |
| 403 | 禁止 (権限不足) |
| 404 | 見つかりません |
| 413 | ペイロードが大きすぎます (ファイルサイズが制限を超過) |
| 422 | 処理不可能なエンティティ (検証失敗) |
| 429 | リクエストが多すぎます (レート制限を超過) |
| 500 | 内部サーバーエラー |
| 503 | サービス利用不可 |

## 認証

すべてのAPIエンドポイント（`/auth/login`を除く）には有効なJWTトークンが必要です。

### トークンタイプ

- **アクセストークン**: 30分間有効、APIリクエストに使用
- **リフレッシュトークン**: 7日間有効、新しいアクセストークンを取得するために使用

### リクエストにトークンを含める

```http
GET /api/v1/tasks HTTP/1.1
Host: yourdomain.com
Authorization: Bearer <access_token>
```

### トークンリフレッシュフロー

アクセストークンが期限切れの場合（401レスポンス）:
1. リフレッシュトークンを使用して`/api/v1/auth/refresh`を呼び出す
2. 新しいアクセストークンとリフレッシュトークンを受け取る
3. 新しいアクセストークンで元のリクエストを再試行

## APIエンドポイント

### 認証API

#### POST /api/v1/auth/login

LDAP経由でユーザーを認証し、JWTトークンを受け取ります。

**リクエストボディ**:
```json
{
  "username": "john.doe",
  "password": "secure_password"
}
```

**レスポンス** (200 OK):
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

**エラーレスポンス**:
- `401`: 認証情報が無効
- `503`: LDAPサーバーが利用不可

---

#### POST /api/v1/auth/refresh

リフレッシュトークンを使用してアクセストークンを更新します。

**リクエストボディ**:
```json
{
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**レスポンス** (200 OK):
```json
{
  "access_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "token_type": "bearer",
  "expires_in": 1800
}
```

**エラーレスポンス**:
- `401`: リフレッシュトークンが無効または期限切れ

---

#### POST /api/v1/auth/logout

ユーザーをログアウトします（クライアント側でトークンを無効化）。

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK):
```json
{
  "message": "Logged out successfully"
}
```

---

#### GET /api/v1/auth/me

現在のユーザー情報を取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**レスポンス** (200 OK):
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

### アップロードAPI

#### POST /api/v1/upload

文字起こし用の音声/動画ファイルをアップロードします。

**ヘッダー**:
- `Authorization: Bearer <token>`
- `Content-Type: multipart/form-data`

**リクエストボディ** (multipart/form-data):
```
file: <binary file>
model_name: "large-v3-turbo" | "large-v3"
language: "ja" | "en" | "auto" (オプション、デフォルト: "ja")
num_speakers: 2 (オプション、話者分離用)
```

**cURL例**:
```bash
curl -X POST https://yourdomain.com/api/v1/upload \
  -H "Authorization: Bearer <token>" \
  -F "file=@meeting_recording.mp3" \
  -F "model_name=large-v3-turbo" \
  -F "language=ja" \
  -F "num_speakers=3"
```

**レスポンス** (201 Created):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "filename": "meeting_recording.mp3",
  "status": "pending",
  "message": "File uploaded successfully. Processing started."
}
```

**検証ルール**:
- **サポートされている形式**: MP3, WAV, M4A, FLAC, OGG, MP4, AVI, MOV, MKV
- **最大ファイルサイズ**: 1GB（環境変数`MAX_FILE_SIZE`で設定可能）
- **モデル名**: `large-v3`, `large-v3-turbo`
- **言語**: ISO 639-1コード（ja, en, zhなど）または"auto"
- **話者数**: 1-20

**エラーレスポンス**:
- `400`: ファイル形式が無効または必須フィールドが欠落
- `413`: ファイルが大きすぎる
- `422`: 検証失敗

---

### タスク管理API

#### GET /api/v1/tasks

ユーザーのタスクリストを取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**:
- `status` (オプション): ステータスでフィルタ（`pending`, `processing`, `completed`, `failed`）
- `page` (オプション): ページ番号（デフォルト: 1）
- `page_size` (オプション): 1ページあたりのアイテム数（デフォルト: 20、最大: 100）
- `sort_by` (オプション): ソートフィールド（`created_at`, `status`）、デフォルト: `created_at`
- `sort_order` (オプション): ソート順（`asc`, `desc`）、デフォルト: `desc`

**レスポンス** (200 OK):
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

詳細なタスク情報を取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `task_id`: タスクのUUID

**レスポンス** (200 OK):
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

**エラーレスポンス**:
- `403`: ユーザーにこのタスクへのアクセス権限がありません
- `404`: タスクが見つかりません

---

#### GET /api/v1/tasks/{task_id}/status

タスクのステータスを取得します（ポーリング用の軽量エンドポイント）。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `task_id`: タスクのUUID

**レスポンス** (200 OK):
```json
{
  "task_id": "550e8400-e29b-41d4-a716-446655440000",
  "status": "processing",
  "progress": 45,
  "message": "Performing speaker diarization..."
}
```

**ステータス値**:
- `pending`: キューで待機中
- `processing`: 現在処理中
- `completed`: 正常に完了
- `failed`: 処理失敗

---

#### DELETE /api/v1/tasks/{task_id}

タスクと関連ファイルを削除します。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `task_id`: タスクのUUID

**レスポンス** (204 No Content)

**エラーレスポンス**:
- `403`: ユーザーにこのタスクを削除する権限がありません
- `404`: タスクが見つかりません

---

### 文字起こしAPI

#### GET /api/v1/tasks/{task_id}/transcription

完了したタスクの文字起こし結果を取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `task_id`: タスクのUUID

**レスポンス** (200 OK):
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

**エラーレスポンス**:
- `403`: ユーザーにこの文字起こしへのアクセス権限がありません
- `404`: タスクが見つからないか、文字起こしがまだ利用できません

---

#### PUT /api/v1/tasks/{task_id}/transcription

文字起こしテキスト全体を更新します。

**ヘッダー**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**パスパラメータ**:
- `task_id`: タスクのUUID

**リクエストボディ**:
```json
{
  "transcription_text": "Updated full transcription text..."
}
```

**レスポンス** (200 OK):
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

文字起こしの特定のセグメントを更新します。

**ヘッダー**:
- `Authorization: Bearer <token>`
- `Content-Type: application/json`

**パスパラメータ**:
- `task_id`: タスクのUUID

**リクエストボディ**:
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

**レスポンス** (200 OK):
```json
{
  "updated_count": 2,
  "segments": [...]
}
```

---

#### GET /api/v1/tasks/{task_id}/subtitle

字幕ファイルをダウンロードします。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `task_id`: タスクのUUID

**クエリパラメータ**:
- `format`: 字幕形式（`srt`または`vtt`）、デフォルト: `srt`

**レスポンス** (200 OK):
- **Content-Type**: `text/plain` (SRT) または `text/vtt` (WebVTT)
- **Content-Disposition**: `attachment; filename="transcription.srt"`

**SRT形式の例**:
```
1
00:00:00,000 --> 00:00:05,500
[Speaker 1] こんにちは。今日の会議を始めます。

2
00:00:06,000 --> 00:00:12,300
[Speaker 2] では、まずプロジェクトの進捗について報告します。
```

**WebVTT形式の例**:
```
WEBVTT

00:00:00.000 --> 00:00:05.500
<v Speaker 1>こんにちは。今日の会議を始めます。

00:00:06.000 --> 00:00:12.300
<v Speaker 2>では、まずプロジェクトの進捗について報告します。
```

---

### 履歴API

#### GET /api/v1/history

現在のユーザーの処理履歴を取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**:
- `page` (オプション): ページ番号（デフォルト: 1）
- `page_size` (オプション): 1ページあたりのアイテム数（デフォルト: 20、最大: 100）
- `success` (オプション): 成功ステータスでフィルタ（`true`, `false`）
- `model_name` (オプション): モデル名でフィルタ
- `start_date` (オプション): 開始日でフィルタ（ISO 8601形式）
- `end_date` (オプション): 終了日でフィルタ（ISO 8601形式）

**レスポンス** (200 OK):
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

詳細な処理履歴エントリを取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**パスパラメータ**:
- `id`: 履歴エントリID

**レスポンス** (200 OK):
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

現在のユーザーの処理統計を取得します。

**ヘッダー**: `Authorization: Bearer <token>`

**クエリパラメータ**:
- `start_date` (オプション): 統計の開始日（ISO 8601形式）
- `end_date` (オプション): 統計の終了日（ISO 8601形式）
- `period` (オプション): 事前定義された期間（`today`, `week`, `month`, `year`）

**レスポンス** (200 OK):
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

### 管理者API

すべての管理者エンドポイントにはユーザープロファイルに`is_admin: true`が必要です。

#### GET /api/v1/admin/dashboard

ダッシュボード統計を取得します（管理者のみ）。

**ヘッダー**: `Authorization: Bearer <admin_token>`

**レスポンス** (200 OK):
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

**エラーレスポンス**:
- `403`: ユーザーは管理者ではありません

---

#### GET /api/v1/admin/system-status

システムステータス情報を取得します（管理者のみ）。

**ヘッダー**: `Authorization: Bearer <admin_token>`

**レスポンス** (200 OK):
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

すべてのユーザーのリストを取得します（管理者のみ）。

**ヘッダー**: `Authorization: Bearer <admin_token>`

**クエリパラメータ**:
- `page` (オプション): ページ番号（デフォルト: 1）
- `page_size` (オプション): 1ページあたりのアイテム数（デフォルト: 20、最大: 100）
- `is_admin` (オプション): 管理者ステータスでフィルタ（`true`, `false`）

**レスポンス** (200 OK):
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

すべてのユーザーのすべてのタスクを取得します（管理者のみ）。

**ヘッダー**: `Authorization: Bearer <admin_token>`

**クエリパラメータ**:
- `page` (オプション): ページ番号（デフォルト: 1）
- `page_size` (オプション): 1ページあたりのアイテム数（デフォルト: 20、最大: 100）
- `status` (オプション): ステータスでフィルタ
- `user_id` (オプション): ユーザーIDでフィルタ
- `start_date` (オプション): 開始日でフィルタ
- `end_date` (オプション): 終了日でフィルタ

**レスポンス** (200 OK):
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

全体的なシステム統計を取得します（管理者のみ）。

**ヘッダー**: `Authorization: Bearer <admin_token>`

**クエリパラメータ**:
- `start_date` (オプション): 開始日（ISO 8601）
- `end_date` (オプション): 終了日（ISO 8601）
- `period` (オプション): 事前定義された期間（`today`, `week`, `month`, `year`）

**レスポンス** (200 OK):
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

### ヘルスチェックAPI

#### GET /health

APIのヘルスステータスを確認します（認証不要）。

**レスポンス** (200 OK):
```json
{
  "status": "healthy",
  "timestamp": "2025-10-13T15:30:00Z",
  "version": "1.0.0"
}
```

---

## データモデル

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

## エラーレスポンス

すべてのエラーレスポンスは以下の形式に従います:

```json
{
  "detail": "Error message",
  "error_code": "ERROR_CODE",
  "timestamp": "2025-10-13T15:30:00Z"
}
```

### 一般的なエラーコード

| コード | HTTPステータス | 説明 |
|------|-------------|-------------|
| `INVALID_CREDENTIALS` | 401 | ユーザー名またはパスワードが無効 |
| `TOKEN_EXPIRED` | 401 | アクセストークンが期限切れ |
| `INVALID_TOKEN` | 401 | トークンが無効または不正な形式 |
| `INSUFFICIENT_PERMISSIONS` | 403 | ユーザーに必要な権限がありません |
| `RESOURCE_NOT_FOUND` | 404 | リクエストされたリソースが存在しません |
| `FILE_TOO_LARGE` | 413 | アップロードされたファイルがサイズ制限を超えています |
| `INVALID_FILE_FORMAT` | 400 | サポートされていないファイル形式 |
| `VALIDATION_ERROR` | 422 | リクエストの検証に失敗しました |
| `RATE_LIMIT_EXCEEDED` | 429 | リクエストが多すぎます |
| `GPU_UNAVAILABLE` | 503 | GPUが利用できません |
| `LDAP_UNAVAILABLE` | 503 | LDAPサーバーが利用できません |

### 検証エラーレスポンス

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

## レート制限

### APIレート制限

- **一般的なAPIエンドポイント**: IP毎に10リクエスト/秒
- **ファイルアップロードエンドポイント**: IP毎に2リクエスト/秒
- **バースト制限**: 一般的なエンドポイントで20リクエスト、アップロードで5リクエスト

### レート制限ヘッダー

```http
X-RateLimit-Limit: 10
X-RateLimit-Remaining: 8
X-RateLimit-Reset: 1634132400
```

### レート制限超過レスポンス

```json
{
  "detail": "Rate limit exceeded. Please try again later.",
  "error_code": "RATE_LIMIT_EXCEEDED",
  "retry_after": 60
}
```

## ページネーション

リストを返すエンドポイントは以下のパラメータでページネーションをサポートします:

- `page`: ページ番号（1から開始）
- `page_size`: 1ページあたりのアイテム数（最大: 100）

ページネーションレスポンス形式:

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

## フィルタリングとソート

多くのリストエンドポイントはフィルタリングとソートをサポートしています:

**フィルタリング**:
- `status=completed`
- `success=true`
- `model_name=large-v3-turbo`

**ソート**:
- `sort_by=created_at`
- `sort_order=desc`

**例**:
```
GET /api/v1/tasks?status=completed&sort_by=created_at&sort_order=desc&page=1&page_size=20
```

## WebSocket API（将来の機能）

リアルタイムの文字起こしステータス更新は、将来のリリースでWebSocket経由で利用可能になります。

**エンドポイント**: `wss://yourdomain.com/ws/tasks/{task_id}`

**認証**: トークンをクエリパラメータとして渡します（`?token=<access_token>`）

## SDKとクライアントライブラリ

公式クライアントライブラリ:
- Python SDK（近日公開）
- JavaScript/TypeScript SDK（近日公開）
- Go SDK（近日公開）

## API変更履歴

### バージョン 1.0.0 (2025-10-13)
- 初期APIリリース
- 認証API
- アップロードAPI
- タスク管理API
- 文字起こしAPI
- 履歴API
- 管理者API

## サポート

- **APIドキュメント**: https://yourdomain.com/docs (Swagger UI)
- **GitHub Issues**: https://github.com/your-org/whisper-app/issues
- **お問い合わせ**: api-support@company.com
