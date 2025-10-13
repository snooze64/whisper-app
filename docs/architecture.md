# システムアーキテクチャ設計書

## 1. システム全体構成

### 1.1 アーキテクチャ概要

本システムは、マイクロサービスアーキテクチャの原則に基づいた、コンテナベースの分散システムです。

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Browser                             │
│                    (React + TypeScript)                          │
└──────────────────────────┬──────────────────────────────────────┘
                           │ HTTPS
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│                         Nginx                                    │
│              (Reverse Proxy + SSL Termination)                  │
└────────────┬────────────────────────────┬───────────────────────┘
             │                            │
             │ Proxy Pass                 │ Static Files
             ▼                            ▼
┌──────────────────────┐      ┌──────────────────────┐
│   FastAPI Backend    │      │  Frontend (Static)   │
│   (uvicorn workers)  │      │    (React Build)     │
└──────┬───────────────┘      └──────────────────────┘
       │
       │ Task Queue
       ▼
┌──────────────────────┐      ┌──────────────────────┐
│   Celery Workers     │◄────►│       Redis          │
│   (GPU Processing)   │      │  (Message Broker)    │
└──────┬───────────────┘      └──────────────────────┘
       │
       │ Database Access
       ▼
┌──────────────────────┐      ┌──────────────────────┐
│    PostgreSQL        │      │   File Storage       │
│  (Metadata + Logs)   │      │  (Local Volumes)     │
└──────────────────────┘      └──────────────────────┘
       │                              │
       └──────────┬───────────────────┘
                  │
                  ▼
         ┌──────────────────────┐
         │   LDAP Server        │
         │  (External Auth)     │
         └──────────────────────┘
```

---

## 2. コンポーネント設計

### 2.1 フロントエンド (React) ✅ Phase 7まで実装完了

**役割**: ユーザーインターフェースの提供

**主要機能**:
- ✅ ファイルアップロード（ドラッグ&ドロップ）
- ✅ 処理状況のリアルタイム表示
- ✅ 文字起こし結果の表示・編集
- ✅ 処理履歴の閲覧（統計カード、一覧テーブル、ページネーション）
- ✅ 管理者ダッシュボード（システムステータス、統計、時間別グラフ）

**技術スタック**:
- React 18 + TypeScript
- TanStack Query (サーバー状態管理)
- Zustand (クライアント状態管理)
- TailwindCSS + shadcn/ui
- React Router (ルーティング)

**ディレクトリ構造**:
```
frontend/
├── src/
│   ├── components/      # 再利用可能なコンポーネント
│   │   ├── ui/         # shadcn/ui コンポーネント
│   │   ├── FileUploader.tsx
│   │   ├── TranscriptionViewer.tsx
│   │   └── HistoryTable.tsx
│   ├── pages/          # ページコンポーネント
│   │   ├── Login.tsx
│   │   ├── Upload.tsx
│   │   ├── Results.tsx
│   │   ├── History.tsx
│   │   └── Admin.tsx
│   ├── hooks/          # カスタムフック
│   ├── services/       # API通信
│   │   └── api.ts
│   ├── stores/         # Zustand stores
│   ├── types/          # TypeScript型定義
│   └── utils/          # ユーティリティ関数
```

### 2.2 バックエンド (FastAPI)

**役割**: APIエンドポイントの提供、ビジネスロジックの実行

**主要機能**:
- 認証・認可（LDAP + JWT）
- ファイルアップロード受付
- タスクの作成・管理
- 処理結果の返却
- 処理履歴の管理

**ディレクトリ構造**:
```
backend/
├── app/
│   ├── main.py              # FastAPIアプリケーション
│   ├── api/
│   │   ├── v1/
│   │   │   ├── endpoints/
│   │   │   │   ├── auth.py      # 認証
│   │   │   │   ├── upload.py    # ファイルアップロード
│   │   │   │   ├── tasks.py     # タスク管理
│   │   │   │   ├── history.py   # 処理履歴
│   │   │   │   └── admin.py     # 管理者機能
│   │   │   └── api.py
│   ├── core/
│   │   ├── config.py        # 設定管理
│   │   ├── security.py      # 認証・認可
│   │   └── dependencies.py  # 依存性注入
│   ├── models/              # SQLAlchemyモデル
│   │   ├── user.py
│   │   ├── task.py
│   │   └── history.py
│   ├── schemas/             # Pydanticスキーマ
│   │   ├── user.py
│   │   ├── task.py
│   │   └── transcription.py
│   ├── services/            # ビジネスロジック
│   │   ├── auth_service.py
│   │   ├── file_service.py
│   │   └── task_service.py
│   └── db/
│       ├── session.py       # DB接続
│       └── init_db.py       # 初期化
```

### 2.3 Celeryワーカー (非同期処理)

**役割**: 音声文字起こし処理の実行

**主要タスク**:
1. 音声抽出（動画ファイルの場合）
2. Whisper文字起こし
3. 話者分離
4. 字幕ファイル生成
5. 結果の保存

**ディレクトリ構造**:
```
backend/
├── app/
│   ├── celery_app.py        # Celery設定
│   └── tasks/
│       ├── transcription.py # 文字起こしタスク
│       ├── diarization.py   # 話者分離タスク
│       ├── subtitle.py      # 字幕生成タスク
│       └── cleanup.py       # ファイル削除タスク
```

**タスクフロー**:
```
1. extract_audio_task       # 音声抽出（MP4の場合）
   ↓
2. transcribe_task          # Whisper文字起こし
   ↓
3. diarize_task             # 話者分離
   ↓
4. generate_subtitle_task   # 字幕ファイル生成
   ↓
5. save_results_task        # 結果保存
```

### 2.4 データベース (PostgreSQL)

**役割**: 永続データの保存

**テーブル設計**:

#### users テーブル
```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_login TIMESTAMP
);
```

#### tasks テーブル
```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER REFERENCES users(id),
    filename VARCHAR(500) NOT NULL,
    file_size BIGINT NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL,
    num_speakers INTEGER,
    status VARCHAR(50) DEFAULT 'pending',
    progress INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

#### transcriptions テーブル
```sql
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    transcription_text TEXT NOT NULL,
    segments JSONB,
    subtitle_path VARCHAR(500),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

#### processing_history テーブル
```sql
CREATE TABLE processing_history (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id),
    user_id INTEGER REFERENCES users(id),
    processing_time_seconds INTEGER,
    gpu_memory_used_mb INTEGER,
    success BOOLEAN NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

---

## 3. データフロー

### 3.1 ファイルアップロード〜文字起こしフロー

```
[ユーザー]
    │
    │ 1. ファイル選択 + パラメータ設定
    ▼
[React Frontend]
    │
    │ 2. POST /api/v1/upload (multipart/form-data)
    ▼
[FastAPI Backend]
    │
    │ 3. ファイル検証 + 保存
    │ 4. タスクレコード作成 (DB)
    │ 5. Celeryタスク投入
    ▼
[Redis] ← タスクキュー
    │
    │ 6. タスク取得
    ▼
[Celery Worker + GPU]
    │
    │ 7. 音声抽出 (FFmpeg)
    │ 8. Whisper文字起こし
    │ 9. 話者分離 (Resemblyzer)
    │ 10. 結果保存
    ▼
[PostgreSQL + File Storage]
    │
    │ 11. 処理完了通知
    ▼
[FastAPI Backend]
    │
    │ 12. GET /api/v1/tasks/{task_id}
    ▼
[React Frontend]
    │
    │ 13. 結果表示
    ▼
[ユーザー]
```

### 3.2 処理状況ポーリング

```
[React Frontend]
    │
    │ 定期的に (3秒ごと)
    │ GET /api/v1/tasks/{task_id}/status
    ▼
[FastAPI Backend]
    │
    │ タスク状態を取得
    ▼
[PostgreSQL]
```

---

## 4. API設計概要

### 4.1 認証API

```
POST   /api/v1/auth/login          # ログイン (LDAP認証)
POST   /api/v1/auth/refresh         # トークンリフレッシュ
POST   /api/v1/auth/logout          # ログアウト
GET    /api/v1/auth/me              # 現在のユーザー情報
```

### 4.2 アップロードAPI

```
POST   /api/v1/upload               # ファイルアップロード
```

**リクエスト例**:
```json
{
  "file": "<binary>",
  "model": "large-v3-turbo",
  "language": "ja",
  "num_speakers": 2
}
```

**レスポンス例**:
```json
{
  "task_id": "uuid-string",
  "status": "pending",
  "message": "Task created successfully"
}
```

### 4.3 タスク管理API

```
GET    /api/v1/tasks/{task_id}         # タスク詳細取得
GET    /api/v1/tasks/{task_id}/status  # タスク状態取得
GET    /api/v1/tasks                   # タスク一覧（ユーザー）
DELETE /api/v1/tasks/{task_id}         # タスク削除
```

### 4.4 結果取得API ✅ 実装済み (Phase 6)

```
GET    /api/v1/tasks/{task_id}/transcription              # 文字起こし結果取得
PUT    /api/v1/tasks/{task_id}/transcription              # 文字起こし結果更新（全体）
PATCH  /api/v1/tasks/{task_id}/transcription/segments     # セグメント単位更新
GET    /api/v1/tasks/{task_id}/subtitle?format=srt|vtt   # 字幕ファイルダウンロード
```

**実装詳細**:
- TranscriptionResponse: 全文、セグメント（JSONB）、メタデータを含む
- 権限チェック: ユーザー自身または管理者のみアクセス可能
- 字幕形式: SRT（SubRip）とWebVTT形式をサポート
- 話者ラベル: 字幕ファイルに自動埋め込み（`[Speaker 1]`、`<v Speaker 1>`）
- 動的生成: 字幕ファイルはリクエスト時に生成

### 4.5 履歴API ✅ 実装済み (Phase 7)

```
GET    /api/v1/history                    # 処理履歴一覧
GET    /api/v1/history/{id}               # 履歴詳細
GET    /api/v1/history/stats/me           # ユーザー統計
```

**実装詳細**:
- ProcessingHistoryResponse: 処理時間、GPUメモリ使用量、モデル名、ファイル情報、成功/失敗を含む
- ページネーション対応: page, page_size パラメータ（デフォルト: page=1, page_size=20）
- フィルタリング対応: success（成功/失敗）、model_name（モデル名）でフィルタ可能
- 権限チェック: ユーザーは自分の履歴のみ閲覧可能（管理者は全履歴閲覧可能）
- ユーザー統計: 指定期間内の統計情報（成功率、平均処理時間、GPU使用量など）
- 自動記録: タスク完了時（成功・失敗両方）に自動でProcessingHistoryレコード作成

**統計情報レスポンス例**:
```json
{
  "total_tasks": 50,
  "successful_tasks": 48,
  "failed_tasks": 2,
  "success_rate": 96.0,
  "avg_processing_time": 125.5,
  "total_processing_time": 6275,
  "avg_gpu_memory": 8500.0,
  "total_file_size": 1250.5
}
```

### 4.6 管理者API ✅ 実装済み (Phase 7)

```
GET    /api/v1/admin/dashboard         # ダッシュボード統計
GET    /api/v1/admin/system-status     # システムステータス
GET    /api/v1/admin/users             # ユーザー一覧
GET    /api/v1/admin/tasks             # 全タスク一覧
GET    /api/v1/admin/stats             # 全体統計
```

**実装詳細**:

#### GET /api/v1/admin/dashboard
ダッシュボード統計情報を取得（管理者のみ）

**レスポンス例**:
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
      "hour": "2025-10-13T08:00:00",
      "total": 3,
      "successful": 3,
      "failed": 0
    }
  ]
}
```

#### GET /api/v1/admin/system-status
システムステータス情報を取得（管理者のみ）

**レスポンス例**:
```json
{
  "gpu_available": true,
  "gpu_memory_total": 40960,
  "gpu_memory_used": 12500,
  "gpu_memory_free": 28460,
  "gpu_utilization": 35.5,
  "active_workers": 2,
  "pending_tasks": 3,
  "processing_tasks": 2
}
```

#### GET /api/v1/admin/users
全ユーザー一覧を取得（管理者のみ、ページネーション対応）

#### GET /api/v1/admin/tasks
全ユーザーの全タスク一覧を取得（管理者のみ、ページネーション・フィルタリング対応）

#### GET /api/v1/admin/stats
全ユーザーの処理統計を取得（管理者のみ、期間指定可能）

**権限チェック**: 全エンドポイントで`require_admin`依存関係により管理者権限を検証

---

## 5. セキュリティ設計

### 5.1 認証フロー

```
[ユーザー]
    │
    │ 1. ユーザー名 + パスワード
    ▼
[FastAPI Backend]
    │
    │ 2. LDAP認証
    ▼
[LDAP Server]
    │
    │ 3. 認証成功
    ▼
[FastAPI Backend]
    │
    │ 4. JWT生成 (access_token + refresh_token)
    │    - access_token: 15分有効
    │    - refresh_token: 7日有効
    ▼
[ユーザー]
    │
    │ 5. 以降のリクエストにBearer token付与
    ▼
[FastAPI Backend]
    │
    │ 6. JWT検証 + ユーザー情報取得
    ▼
[APIエンドポイント]
```

### 5.2 認可

**ロール**:
- `user`: 一般ユーザー（自分のタスクのみアクセス可能）
- `admin`: 管理者（全ユーザーのタスクにアクセス可能）

**実装**:
```python
from fastapi import Depends, HTTPException
from app.core.security import get_current_user

@router.get("/tasks/{task_id}")
async def get_task(
    task_id: str,
    current_user: User = Depends(get_current_user)
):
    task = get_task_from_db(task_id)
    if task.user_id != current_user.id and not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Forbidden")
    return task
```

### 5.3 ファイルアップロードセキュリティ

- ファイルタイプ検証（MIME type + 拡張子）
- ファイルサイズ制限（1GB）
- ファイル名サニタイゼーション
- UUID使用による予測不可能なファイル名

---

## 6. GPU処理とスケーラビリティ

### 6.1 GPU メモリ管理

**動的スケジューリング**:

```python
import pynvml

def get_available_gpu_memory():
    """GPUの空きメモリを取得 (MB単位)"""
    pynvml.nvmlInit()
    handle = pynvml.nvmlDeviceGetHandleByIndex(0)
    info = pynvml.nvmlDeviceGetMemoryInfo(handle)
    return info.free // (1024 ** 2)

def can_start_task(model_name: str):
    """タスクを開始できるか判定"""
    required_memory = {
        "large-v3": 12000,  # 12GB
        "large-v3-turbo": 10000  # 10GB
    }
    available = get_available_gpu_memory()
    return available >= required_memory.get(model_name, 12000)
```

**Celeryワーカー設定**:
```python
# celeryconfig.py
worker_prefetch_multiplier = 1  # 1タスクずつ取得
task_acks_late = True           # タスク完了後にACK
```

### 6.2 タスクキューの優先度

```python
# 優先度設定
HIGH_PRIORITY = 9    # 管理者タスク
NORMAL_PRIORITY = 5  # 通常タスク
LOW_PRIORITY = 1     # バックグラウンドタスク

# タスク投入時に優先度指定
transcribe_task.apply_async(
    args=[file_path, model],
    priority=NORMAL_PRIORITY
)
```

### 6.3 水平スケーリング（将来的）

```
┌─────────────────┐
│  Load Balancer  │
└────────┬────────┘
         │
    ┌────┴────┐
    │         │
    ▼         ▼
┌──────┐  ┌──────┐
│ GPU1 │  │ GPU2 │
└──────┘  └──────┘
```

- 複数のGPUサーバーを追加
- Celeryワーカーを各GPUサーバーで起動
- Redisで一元管理

---

## 7. エラーハンドリング

### 7.1 タスク失敗時の処理

```python
@celery.task(bind=True, max_retries=3)
def transcribe_task(self, file_path, model):
    try:
        # 処理実行
        result = perform_transcription(file_path, model)
        return result
    except Exception as exc:
        # リトライ（指数バックオフ）
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 7.2 エラー通知

- タスク失敗時、DBにエラーメッセージを記録
- フロントエンドでエラー表示
- 管理者向けにエラーログを集約

---

## 8. ファイル削除スケジュール

### 8.1 定期削除タスク

```python
from apscheduler.schedulers.background import BackgroundScheduler

def delete_old_files():
    """24時間以上経過したファイルを削除"""
    threshold = datetime.now() - timedelta(hours=24)
    old_tasks = get_tasks_before(threshold)
    
    for task in old_tasks:
        delete_file(task.file_path)
        delete_file(task.result_path)
        delete_task_from_db(task.id)

scheduler = BackgroundScheduler()
scheduler.add_job(delete_old_files, 'interval', hours=1)
scheduler.start()
```

---

## 9. モニタリング・ログ

### 9.1 ログフォーマット

```json
{
  "timestamp": "2025-10-13T12:34:56Z",
  "level": "INFO",
  "service": "fastapi",
  "task_id": "uuid",
  "user_id": 123,
  "message": "Task started",
  "metadata": {}
}
```

### 9.2 メトリクス（将来的）

- タスク処理時間
- GPU使用率
- タスク成功率
- API応答時間

---

## 10. デプロイメント構成

### 10.1 Docker Compose構成

```yaml
version: '3.8'

services:
  nginx:
    image: nginx:alpine
    ports:
      - "443:443"
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
      - ./frontend/dist:/usr/share/nginx/html
    depends_on:
      - backend

  backend:
    build: ./backend
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/whisper
      - REDIS_URL=redis://redis:6379
      - LDAP_SERVER=ldap://ldap-server:389
    depends_on:
      - postgres
      - redis

  celery-worker:
    build: ./backend
    command: celery -A app.celery_app worker --loglevel=info
    deploy:
      resources:
        reservations:
          devices:
            - driver: nvidia
              count: 1
              capabilities: [gpu]
    environment:
      - DATABASE_URL=postgresql://user:pass@postgres:5432/whisper
      - REDIS_URL=redis://redis:6379
    depends_on:
      - redis
      - postgres

  redis:
    image: redis:7-alpine
    volumes:
      - redis-data:/data

  postgres:
    image: postgres:15-alpine
    environment:
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=pass
      - POSTGRES_DB=whisper
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
  redis-data:
  upload-data:
  result-data:
```

---

**文書作成日**: 2025-10-13
**最終更新日**: 2025-10-13
**バージョン**: 1.0

## 11. 将来的な拡張: ChatGPT連携機能

### 11.1 概要

文字起こし結果をChatGPT（またはOpenAI互換API）で自動処理し、議事録の要約や整形を行う機能。

### 11.2 アーキテクチャ

```
[文字起こし完了]
      │
      │ ユーザーがChatGPT処理をリクエスト
      ▼
[React Frontend]
      │
      │ POST /api/v1/tasks/{task_id}/llm-process
      │ {
      │   "prompt_template_id": "summary" or "custom",
      │   "custom_prompt": "...",
      │   "model": "gpt-4"
      │ }
      ▼
[FastAPI Backend]
      │
      │ 1. 文字起こし結果取得
      │ 2. プロンプトテンプレート適用
      │ 3. Celeryタスク投入
      ▼
[Celery Worker]
      │
      │ 4. OpenAI API呼び出し
      │    - Base URL: 環境変数 OPENAI_BASE_URL
      │    - API Key: 環境変数 OPENAI_API_KEY
      │    - モデル一覧取得: GET {OPENAI_BASE_URL}/api/models
      ▼
[OpenAI API / Azure OpenAI / ローカルLLM]
      │
      │ 5. LLM処理結果
      ▼
[Celery Worker]
      │
      │ 6. 結果保存
      ▼
[PostgreSQL]
      │
      │ 7. 処理完了通知
      ▼
[FastAPI Backend]
      │
      │ 8. GET /api/v1/tasks/{task_id}/llm-result
      ▼
[React Frontend]
      │
      │ 9. 処理前後の結果を表示
      ▼
[ユーザー]
```

### 11.3 データベース拡張

#### llm_processings テーブル
```sql
CREATE TABLE llm_processings (
    id SERIAL PRIMARY KEY,
    task_id UUID REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER REFERENCES users(id),
    prompt_template_id VARCHAR(100),
    custom_prompt TEXT,
    model_name VARCHAR(100) NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT,
    status VARCHAR(50) DEFAULT 'pending',
    tokens_used INTEGER,
    processing_time_seconds INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT
);
```

#### prompt_templates テーブル
```sql
CREATE TABLE prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE,
    user_id INTEGER REFERENCES users(id),  -- NULL for system templates
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- デフォルトプロンプトテンプレート例
INSERT INTO prompt_templates (name, display_name, description, template, is_default) VALUES
('summary', '議事録要約', '会議の内容を要約します', 
 '以下は会議の文字起こし結果です。重要なポイントを箇条書きで要約してください。\n\n{transcription}', 
 TRUE),
('action_items', 'アクションアイテム抽出', 'アクションアイテムを抽出します',
 '以下は会議の文字起こし結果です。アクションアイテムを抽出し、担当者と期限を特定してください。\n\n{transcription}',
 TRUE),
('highlights', '重要トピックのハイライト', '重要な議論をハイライトします',
 '以下は会議の文字起こし結果です。重要なトピックや決定事項をハイライトしてください。\n\n{transcription}',
 TRUE);
```

### 11.4 API設計

#### LLM処理API

```
POST   /api/v1/tasks/{task_id}/llm-process        # LLM処理開始
GET    /api/v1/tasks/{task_id}/llm-result         # LLM処理結果取得
GET    /api/v1/llm/models                         # 利用可能モデル一覧
GET    /api/v1/llm/templates                      # プロンプトテンプレート一覧
POST   /api/v1/llm/templates                      # カスタムテンプレート作成
PUT    /api/v1/llm/templates/{id}                 # テンプレート更新
DELETE /api/v1/llm/templates/{id}                 # テンプレート削除
```

**POST /api/v1/tasks/{task_id}/llm-process リクエスト例**:
```json
{
  "prompt_template_id": "summary",
  "model": "gpt-4",
  "custom_parameters": {
    "temperature": 0.7,
    "max_tokens": 2000
  }
}
```

**カスタムプロンプト使用例**:
```json
{
  "prompt_template_id": "custom",
  "custom_prompt": "以下の会議内容から、技術的な議論のみを抽出してください。\n\n{transcription}",
  "model": "gpt-4-turbo"
}
```

### 11.5 環境変数設定

```bash
# OpenAI互換API設定（システム全体で共通）
OPENAI_BASE_URL=https://api.openai.com/v1
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx

# または Azure OpenAI
OPENAI_BASE_URL=https://your-resource.openai.azure.com
OPENAI_API_KEY=your-azure-key

# またはローカルLLM（Ollama, LM Studioなど）
OPENAI_BASE_URL=http://localhost:11434/v1
OPENAI_API_KEY=dummy  # ローカルの場合は不要だが設定
```

### 11.6 モデル一覧の動的取得

```python
import httpx
from app.core.config import settings

async def get_available_models():
    """利用可能なモデル一覧を取得"""
    url = f"{settings.OPENAI_BASE_URL}/models"
    headers = {"Authorization": f"Bearer {settings.OPENAI_API_KEY}"}
    
    async with httpx.AsyncClient() as client:
        response = await client.get(url, headers=headers)
        response.raise_for_status()
        models = response.json()
        
    # モデル一覧を返す
    return [
        {
            "id": model["id"],
            "name": model.get("name", model["id"]),
            "owned_by": model.get("owned_by", "unknown")
        }
        for model in models.get("data", [])
    ]
```

### 11.7 LLM処理タスク実装

```python
from openai import AsyncOpenAI

@celery.task(bind=True, max_retries=3)
async def llm_process_task(self, task_id: str, prompt: str, model: str):
    """LLM処理タスク"""
    try:
        # OpenAI クライアント初期化
        client = AsyncOpenAI(
            base_url=settings.OPENAI_BASE_URL,
            api_key=settings.OPENAI_API_KEY
        )
        
        # LLM処理実行
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "あなたは議事録作成のアシスタントです。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=2000
        )
        
        # 結果を返す
        result = {
            "output_text": response.choices[0].message.content,
            "tokens_used": response.usage.total_tokens,
            "model": response.model
        }
        
        return result
        
    except Exception as exc:
        # リトライ
        raise self.retry(exc=exc, countdown=60 * (2 ** self.request.retries))
```

### 11.8 フロントエンド UI

**LLM処理画面の構成**:

1. **プロンプトテンプレート選択**:
   - デフォルトテンプレート（要約、アクションアイテム抽出など）
   - ユーザーカスタムテンプレート
   - カスタムプロンプト直接入力

2. **モデル選択**:
   - 利用可能なモデル一覧から選択
   - モデル情報（所有者、説明）を表示

3. **処理結果表示**:
   - 処理前テキスト（文字起こし結果）
   - 処理後テキスト（LLM出力）
   - 両方を並べて表示
   - 使用トークン数、処理時間の表示

4. **結果の保存・ダウンロード**:
   - テキストファイルとしてダウンロード
   - Markdown形式でダウンロード
   - 処理結果の再編集機能

### 11.9 セキュリティ考慮事項

- **APIキーの管理**: 環境変数で管理し、コードに含めない
- **レート制限**: OpenAI APIの使用量制限に注意
- **コスト管理**: トークン使用量の記録と監視
- **データプライバシー**: 機密情報がLLMに送信されることを明示
- **タイムアウト**: 長時間のLLM処理に対するタイムアウト設定

### 11.10 コスト管理

```python
# LLM処理履歴からコスト計算
def calculate_llm_cost(tokens_used: int, model: str) -> float:
    """トークン使用量からコストを計算"""
    # モデル別のトークン単価（例）
    pricing = {
        "gpt-4": {"input": 0.03, "output": 0.06},  # per 1K tokens
        "gpt-3.5-turbo": {"input": 0.001, "output": 0.002}
    }
    
    # 簡易計算（実際は入力・出力を分けて計算）
    rate = pricing.get(model, {"input": 0.001, "output": 0.002})
    cost = (tokens_used / 1000) * rate["output"]
    
    return cost
```

**管理者ダッシュボードに追加**:
- LLM使用統計（ユーザー別、モデル別）
- トークン使用量の推移
- 推定コスト

---

**更新日**: 2025-10-13
**バージョン**: 1.2
**変更履歴**:
- v1.2 (2025-10-13): Phase 6（結果取得API）実装完了を反映
- v1.1 (2025-10-13): ChatGPT連携機能の設計を追加
- v1.0 (2025-10-13): 初版作成
