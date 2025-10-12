# データベース設計書

## 1. 概要

本アプリケーションでは、PostgreSQL 15+を使用し、以下のデータを管理します：
- ユーザー情報
- タスク（文字起こしジョブ）
- 文字起こし結果
- 処理履歴
- LLM処理情報（将来的）
- プロンプトテンプレート（将来的）

---

## 2. ER図

```
┌─────────────┐
│   users     │
└──────┬──────┘
       │
       │ 1:N
       ▼
┌─────────────┐        ┌──────────────────┐
│   tasks     │───────►│ transcriptions   │
└──────┬──────┘   1:1  └──────────────────┘
       │
       │ 1:N
       ▼
┌──────────────────┐
│processing_history│
└──────────────────┘
       │
       │ 1:N (将来的)
       ▼
┌──────────────────┐        ┌──────────────────┐
│llm_processings   │        │prompt_templates  │
└──────────────────┘        └──────────────────┘
              │                      ▲
              └──────────────────────┘
                    N:1 (参照)
```

---

## 3. テーブル定義

### 3.1 users テーブル

**目的**: ユーザー情報の管理

```sql
CREATE TABLE users (
    id SERIAL PRIMARY KEY,
    username VARCHAR(255) UNIQUE NOT NULL,
    email VARCHAR(255),
    is_admin BOOLEAN DEFAULT FALSE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    last_login TIMESTAMP,
    
    CONSTRAINT users_username_length CHECK (char_length(username) >= 3),
    CONSTRAINT users_email_format CHECK (email ~* '^[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}$')
);

-- インデックス
CREATE INDEX idx_users_username ON users(username);
CREATE INDEX idx_users_email ON users(email);
CREATE INDEX idx_users_is_admin ON users(is_admin) WHERE is_admin = TRUE;
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | SERIAL | NOT NULL | プライマリキー |
| username | VARCHAR(255) | NOT NULL | ユーザー名（LDAP連携）|
| email | VARCHAR(255) | NULL | メールアドレス |
| is_admin | BOOLEAN | NOT NULL | 管理者フラグ |
| created_at | TIMESTAMP | NOT NULL | アカウント作成日時 |
| last_login | TIMESTAMP | NULL | 最終ログイン日時 |

**制約**:
- username: 3文字以上、ユニーク制約
- email: メールアドレス形式のチェック

---

### 3.2 tasks テーブル

**目的**: 文字起こしタスクの管理

```sql
CREATE TABLE tasks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    filename VARCHAR(500) NOT NULL,
    file_path VARCHAR(1000) NOT NULL,
    file_size BIGINT NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    model_name VARCHAR(50) NOT NULL,
    language VARCHAR(10) NOT NULL DEFAULT 'ja',
    num_speakers INTEGER,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    progress INTEGER DEFAULT 0 NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    error_message TEXT,
    
    CONSTRAINT tasks_file_size_positive CHECK (file_size > 0),
    CONSTRAINT tasks_progress_range CHECK (progress >= 0 AND progress <= 100),
    CONSTRAINT tasks_status_valid CHECK (status IN (
        'pending', 'processing', 'completed', 'failed', 'cancelled'
    )),
    CONSTRAINT tasks_num_speakers_positive CHECK (num_speakers IS NULL OR num_speakers > 0)
);

-- インデックス
CREATE INDEX idx_tasks_user_id ON tasks(user_id);
CREATE INDEX idx_tasks_status ON tasks(status);
CREATE INDEX idx_tasks_created_at ON tasks(created_at DESC);
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);
CREATE INDEX idx_tasks_completed_at ON tasks(completed_at) WHERE completed_at IS NOT NULL;
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | UUID | NOT NULL | プライマリキー（UUID） |
| user_id | INTEGER | NOT NULL | ユーザーID（外部キー） |
| filename | VARCHAR(500) | NOT NULL | 元のファイル名 |
| file_path | VARCHAR(1000) | NOT NULL | サーバー上のファイルパス |
| file_size | BIGINT | NOT NULL | ファイルサイズ（バイト） |
| file_format | VARCHAR(50) | NOT NULL | ファイル形式（mp3, wav, mp4） |
| model_name | VARCHAR(50) | NOT NULL | Whisperモデル名 |
| language | VARCHAR(10) | NOT NULL | 言語コード（ja, en等） |
| num_speakers | INTEGER | NULL | 話者数 |
| status | VARCHAR(50) | NOT NULL | タスク状態 |
| progress | INTEGER | NOT NULL | 進捗率（0-100） |
| created_at | TIMESTAMP | NOT NULL | タスク作成日時 |
| started_at | TIMESTAMP | NULL | 処理開始日時 |
| completed_at | TIMESTAMP | NULL | 処理完了日時 |
| error_message | TEXT | NULL | エラーメッセージ |

**status の値**:
- `pending`: 処理待ち
- `processing`: 処理中
- `completed`: 完了
- `failed`: 失敗
- `cancelled`: キャンセル

---

### 3.3 transcriptions テーブル

**目的**: 文字起こし結果の保存

```sql
CREATE TABLE transcriptions (
    id SERIAL PRIMARY KEY,
    task_id UUID UNIQUE NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    transcription_text TEXT NOT NULL,
    segments JSONB NOT NULL,
    subtitle_path VARCHAR(500),
    word_count INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT transcriptions_word_count_positive CHECK (word_count IS NULL OR word_count >= 0)
);

-- インデックス
CREATE UNIQUE INDEX idx_transcriptions_task_id ON transcriptions(task_id);
CREATE INDEX idx_transcriptions_created_at ON transcriptions(created_at DESC);
CREATE INDEX idx_transcriptions_segments_gin ON transcriptions USING gin(segments jsonb_path_ops);
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | SERIAL | NOT NULL | プライマリキー |
| task_id | UUID | NOT NULL | タスクID（外部キー、ユニーク） |
| transcription_text | TEXT | NOT NULL | 文字起こし結果（全文） |
| segments | JSONB | NOT NULL | セグメント情報（JSON形式） |
| subtitle_path | VARCHAR(500) | NULL | 字幕ファイルパス |
| word_count | INTEGER | NULL | 単語数 |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | 更新日時 |

**segments の JSON 構造**:
```json
[
  {
    "id": 0,
    "start": 0.0,
    "end": 5.5,
    "text": "こんにちは、今日は会議を始めます。",
    "speaker_id": 1,
    "speaker_label": "Speaker 1",
    "confidence": 0.95
  },
  {
    "id": 1,
    "start": 5.5,
    "end": 10.2,
    "text": "よろしくお願いします。",
    "speaker_id": 2,
    "speaker_label": "Speaker 2",
    "confidence": 0.92
  }
]
```

---

### 3.4 processing_history テーブル

**目的**: 処理履歴と統計情報の記録

```sql
CREATE TABLE processing_history (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    processing_time_seconds INTEGER NOT NULL,
    gpu_memory_used_mb INTEGER,
    model_name VARCHAR(50) NOT NULL,
    file_format VARCHAR(50) NOT NULL,
    file_size_mb DECIMAL(10, 2) NOT NULL,
    success BOOLEAN NOT NULL,
    error_type VARCHAR(100),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT processing_history_time_positive CHECK (processing_time_seconds >= 0),
    CONSTRAINT processing_history_gpu_positive CHECK (gpu_memory_used_mb IS NULL OR gpu_memory_used_mb > 0),
    CONSTRAINT processing_history_size_positive CHECK (file_size_mb > 0)
);

-- インデックス
CREATE INDEX idx_processing_history_user_id ON processing_history(user_id);
CREATE INDEX idx_processing_history_task_id ON processing_history(task_id);
CREATE INDEX idx_processing_history_created_at ON processing_history(created_at DESC);
CREATE INDEX idx_processing_history_success ON processing_history(success);
CREATE INDEX idx_processing_history_model ON processing_history(model_name);
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | SERIAL | NOT NULL | プライマリキー |
| task_id | UUID | NOT NULL | タスクID（外部キー） |
| user_id | INTEGER | NOT NULL | ユーザーID（外部キー） |
| processing_time_seconds | INTEGER | NOT NULL | 処理時間（秒） |
| gpu_memory_used_mb | INTEGER | NULL | 使用GPUメモリ（MB） |
| model_name | VARCHAR(50) | NOT NULL | 使用モデル名 |
| file_format | VARCHAR(50) | NOT NULL | ファイル形式 |
| file_size_mb | DECIMAL(10, 2) | NOT NULL | ファイルサイズ（MB） |
| success | BOOLEAN | NOT NULL | 成功フラグ |
| error_type | VARCHAR(100) | NULL | エラー種別 |
| created_at | TIMESTAMP | NOT NULL | 記録日時 |

---

### 3.5 llm_processings テーブル（将来的）

**目的**: LLM処理の履歴管理

```sql
CREATE TABLE llm_processings (
    id SERIAL PRIMARY KEY,
    task_id UUID NOT NULL REFERENCES tasks(id) ON DELETE CASCADE,
    user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    prompt_template_id INTEGER REFERENCES prompt_templates(id) ON DELETE SET NULL,
    custom_prompt TEXT,
    model_name VARCHAR(100) NOT NULL,
    input_text TEXT NOT NULL,
    output_text TEXT,
    status VARCHAR(50) DEFAULT 'pending' NOT NULL,
    tokens_used INTEGER,
    processing_time_seconds INTEGER,
    cost_usd DECIMAL(10, 4),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    completed_at TIMESTAMP,
    error_message TEXT,
    
    CONSTRAINT llm_processings_status_valid CHECK (status IN (
        'pending', 'processing', 'completed', 'failed'
    )),
    CONSTRAINT llm_processings_tokens_positive CHECK (tokens_used IS NULL OR tokens_used > 0),
    CONSTRAINT llm_processings_time_positive CHECK (processing_time_seconds IS NULL OR processing_time_seconds >= 0),
    CONSTRAINT llm_processings_cost_positive CHECK (cost_usd IS NULL OR cost_usd >= 0)
);

-- インデックス
CREATE INDEX idx_llm_processings_task_id ON llm_processings(task_id);
CREATE INDEX idx_llm_processings_user_id ON llm_processings(user_id);
CREATE INDEX idx_llm_processings_template_id ON llm_processings(prompt_template_id);
CREATE INDEX idx_llm_processings_status ON llm_processings(status);
CREATE INDEX idx_llm_processings_created_at ON llm_processings(created_at DESC);
CREATE INDEX idx_llm_processings_model ON llm_processings(model_name);
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | SERIAL | NOT NULL | プライマリキー |
| task_id | UUID | NOT NULL | タスクID（外部キー） |
| user_id | INTEGER | NOT NULL | ユーザーID（外部キー） |
| prompt_template_id | INTEGER | NULL | プロンプトテンプレートID |
| custom_prompt | TEXT | NULL | カスタムプロンプト |
| model_name | VARCHAR(100) | NOT NULL | LLMモデル名 |
| input_text | TEXT | NOT NULL | 入力テキスト |
| output_text | TEXT | NULL | 出力テキスト |
| status | VARCHAR(50) | NOT NULL | 処理状態 |
| tokens_used | INTEGER | NULL | 使用トークン数 |
| processing_time_seconds | INTEGER | NULL | 処理時間（秒） |
| cost_usd | DECIMAL(10, 4) | NULL | コスト（USD） |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| completed_at | TIMESTAMP | NULL | 完了日時 |
| error_message | TEXT | NULL | エラーメッセージ |

---

### 3.6 prompt_templates テーブル（将来的）

**目的**: プロンプトテンプレートの管理

```sql
CREATE TABLE prompt_templates (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL,
    display_name VARCHAR(200) NOT NULL,
    description TEXT,
    template TEXT NOT NULL,
    is_default BOOLEAN DEFAULT FALSE NOT NULL,
    user_id INTEGER REFERENCES users(id) ON DELETE CASCADE,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP NOT NULL,
    
    CONSTRAINT prompt_templates_name_length CHECK (char_length(name) >= 3),
    CONSTRAINT prompt_templates_template_not_empty CHECK (char_length(template) > 0),
    CONSTRAINT prompt_templates_system_or_user CHECK (
        (is_default = TRUE AND user_id IS NULL) OR
        (is_default = FALSE AND user_id IS NOT NULL)
    )
);

-- インデックス
CREATE UNIQUE INDEX idx_prompt_templates_name ON prompt_templates(name);
CREATE INDEX idx_prompt_templates_user_id ON prompt_templates(user_id);
CREATE INDEX idx_prompt_templates_is_default ON prompt_templates(is_default) WHERE is_default = TRUE;
```

**カラム説明**:

| カラム名 | データ型 | NULL | 説明 |
|---------|---------|------|------|
| id | SERIAL | NOT NULL | プライマリキー |
| name | VARCHAR(100) | NOT NULL | テンプレート識別名（ユニーク） |
| display_name | VARCHAR(200) | NOT NULL | 表示名 |
| description | TEXT | NULL | 説明 |
| template | TEXT | NOT NULL | プロンプトテンプレート |
| is_default | BOOLEAN | NOT NULL | デフォルトテンプレートフラグ |
| user_id | INTEGER | NULL | 作成者ID（システムテンプレートの場合NULL） |
| created_at | TIMESTAMP | NOT NULL | 作成日時 |
| updated_at | TIMESTAMP | NOT NULL | 更新日時 |

**デフォルトデータ**:
```sql
INSERT INTO prompt_templates (name, display_name, description, template, is_default) VALUES
('summary', '議事録要約', '会議の内容を要約します', 
 '以下は会議の文字起こし結果です。重要なポイントを箇条書きで要約してください。

{transcription}', 
 TRUE),
('action_items', 'アクションアイテム抽出', 'アクションアイテムを抽出します',
 '以下は会議の文字起こし結果です。アクションアイテムを抽出し、担当者と期限を特定してください。

{transcription}',
 TRUE),
('highlights', '重要トピックのハイライト', '重要な議論をハイライトします',
 '以下は会議の文字起こし結果です。重要なトピックや決定事項をハイライトしてください。

{transcription}',
 TRUE);
```

---

## 4. リレーションシップ

### 4.1 主要なリレーション

```
users (1) ─────── (N) tasks
users (1) ─────── (N) processing_history
users (1) ─────── (N) prompt_templates (カスタムのみ)
tasks (1) ─────── (1) transcriptions
tasks (1) ─────── (N) processing_history
tasks (1) ─────── (N) llm_processings
prompt_templates (1) ─────── (N) llm_processings (参照)
```

### 4.2 カスケード削除

- `users` 削除時:
  - 関連する `tasks` を削除（CASCADE）
  - 関連する `processing_history` を削除（CASCADE）
  - 関連する `prompt_templates` を削除（CASCADE）
  - 関連する `llm_processings` を削除（CASCADE）

- `tasks` 削除時:
  - 関連する `transcriptions` を削除（CASCADE）
  - 関連する `processing_history` を削除（CASCADE）
  - 関連する `llm_processings` を削除（CASCADE）

- `prompt_templates` 削除時:
  - 関連する `llm_processings` の `prompt_template_id` を NULL に設定（SET NULL）

---

## 5. インデックス戦略

### 5.1 検索頻度の高いカラム

- **users.username**: ログイン時の検索
- **tasks.user_id**: ユーザー別タスク一覧
- **tasks.status**: ステータス別フィルタ
- **tasks.created_at**: 作成日時順ソート
- **processing_history.created_at**: 履歴の時系列表示

### 5.2 複合インデックス

```sql
-- ユーザー別のステータスフィルタに最適化
CREATE INDEX idx_tasks_user_status ON tasks(user_id, status);

-- 管理者ダッシュボードの統計クエリに最適化
CREATE INDEX idx_processing_history_date_model ON processing_history(
    DATE(created_at), model_name
);
```

### 5.3 部分インデックス

```sql
-- 管理者ユーザーのみにインデックス（少数のため効率的）
CREATE INDEX idx_users_is_admin ON users(is_admin) WHERE is_admin = TRUE;

-- 完了済みタスクのみにインデックス
CREATE INDEX idx_tasks_completed_at ON tasks(completed_at) WHERE completed_at IS NOT NULL;

-- デフォルトテンプレートのみにインデックス
CREATE INDEX idx_prompt_templates_is_default ON prompt_templates(is_default) 
WHERE is_default = TRUE;
```

### 5.4 GINインデックス（JSONB）

```sql
-- segments の高速検索用
CREATE INDEX idx_transcriptions_segments_gin ON transcriptions 
USING gin(segments jsonb_path_ops);
```

---

## 6. データ型の選定理由

### 6.1 プライマリキー

| テーブル | 型 | 理由 |
|---------|---|------|
| users | SERIAL | 順序的なID、内部管理用 |
| tasks | UUID | 外部公開、予測困難性、分散環境対応 |
| その他 | SERIAL | 順序的なID、シンプルな内部管理 |

### 6.2 タイムスタンプ

- **TIMESTAMP**: タイムゾーンを保存しない（アプリケーション層で統一管理）
- **DEFAULT CURRENT_TIMESTAMP**: 自動設定

### 6.3 JSONB vs JSON

- **JSONB**: バイナリ形式、インデックス可能、検索高速
- segments カラムに使用

### 6.4 TEXT vs VARCHAR

- **TEXT**: 長さ制限なし、可変長
- **VARCHAR(N)**: 最大長が明確な場合に使用

---

## 7. パフォーマンス最適化

### 7.1 クエリ最適化

**頻出クエリ例**:

```sql
-- ユーザー別の処理中タスク取得
SELECT * FROM tasks 
WHERE user_id = $1 AND status = 'processing'
ORDER BY created_at DESC;

-- 管理者ダッシュボード: 日別処理統計
SELECT 
    DATE(created_at) as date,
    COUNT(*) as total_count,
    AVG(processing_time_seconds) as avg_time,
    SUM(file_size_mb) as total_size_mb
FROM processing_history
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY DATE(created_at)
ORDER BY date DESC;

-- LLM使用統計
SELECT 
    model_name,
    COUNT(*) as usage_count,
    SUM(tokens_used) as total_tokens,
    SUM(cost_usd) as total_cost
FROM llm_processings
WHERE created_at >= NOW() - INTERVAL '30 days'
GROUP BY model_name;
```

### 7.2 パーティショニング（将来的検討）

データ量が増加した場合、以下のテーブルをパーティショニング：

```sql
-- processing_history を月ごとにパーティション
CREATE TABLE processing_history_2025_01 PARTITION OF processing_history
FOR VALUES FROM ('2025-01-01') TO ('2025-02-01');
```

### 7.3 バキューム戦略

```sql
-- 定期的なバキューム（週次）
VACUUM ANALYZE tasks;
VACUUM ANALYZE transcriptions;
VACUUM ANALYZE processing_history;
```

---

## 8. マイグレーション戦略

### 8.1 Alembic使用

```bash
# マイグレーションファイル作成
alembic revision -m "create_initial_tables"

# マイグレーション実行
alembic upgrade head

# ロールバック
alembic downgrade -1
```

### 8.2 マイグレーション順序

1. **Phase 1: 基本テーブル**
   - users
   - tasks
   - transcriptions
   - processing_history

2. **Phase 2: LLM連携テーブル**（将来的）
   - prompt_templates
   - llm_processings

### 8.3 マイグレーションファイル例

```python
# alembic/versions/001_create_initial_tables.py
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

def upgrade():
    # users テーブル作成
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('username', sa.String(255), nullable=False),
        sa.Column('email', sa.String(255), nullable=True),
        sa.Column('is_admin', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('created_at', sa.TIMESTAMP(), nullable=False, server_default=sa.text('CURRENT_TIMESTAMP')),
        sa.Column('last_login', sa.TIMESTAMP(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('username')
    )
    
    # インデックス作成
    op.create_index('idx_users_username', 'users', ['username'])
    
    # 以下、他のテーブルも同様に作成...

def downgrade():
    op.drop_table('users')
    # 以下、他のテーブルも同様に削除...
```

---

## 9. データ保持ポリシー

### 9.1 自動削除

```sql
-- 24時間以上経過したタスクを削除（CASCADE でtranscriptionsも削除）
DELETE FROM tasks 
WHERE completed_at < NOW() - INTERVAL '24 hours';
```

### 9.2 処理履歴の保持

- **processing_history**: 永続的に保持（統計用）
- **llm_processings**: 永続的に保持（コスト管理用）

### 9.3 アーカイブ戦略（将来的）

長期保存が必要な場合：
```sql
-- アーカイブテーブルへ移動
INSERT INTO processing_history_archive
SELECT * FROM processing_history
WHERE created_at < NOW() - INTERVAL '1 year';

DELETE FROM processing_history
WHERE created_at < NOW() - INTERVAL '1 year';
```

---

## 10. セキュリティ考慮事項

### 10.1 権限管理

```sql
-- アプリケーション用ユーザー作成
CREATE USER whisper_app WITH PASSWORD 'secure_password';

-- 必要最小限の権限付与
GRANT CONNECT ON DATABASE whisper TO whisper_app;
GRANT USAGE ON SCHEMA public TO whisper_app;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO whisper_app;
GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA public TO whisper_app;

-- 管理者用ユーザー（マイグレーション用）
CREATE USER whisper_admin WITH PASSWORD 'admin_password';
GRANT ALL PRIVILEGES ON DATABASE whisper TO whisper_admin;
```

### 10.2 Row Level Security（将来的検討）

```sql
-- ユーザーは自分のタスクのみアクセス可能
ALTER TABLE tasks ENABLE ROW LEVEL SECURITY;

CREATE POLICY tasks_user_policy ON tasks
    FOR ALL
    USING (user_id = current_setting('app.user_id')::integer);
```

---

## 11. バックアップ戦略

### 11.1 定期バックアップ

```bash
# 日次バックアップ（cron設定）
0 2 * * * pg_dump -U whisper_admin whisper > /backup/whisper_$(date +\%Y\%m\%d).sql

# 週次フルバックアップ
0 3 * * 0 pg_basebackup -D /backup/weekly/$(date +\%Y\%m\%d) -Ft -z -P
```

### 11.2 リストア

```bash
# 特定のバックアップから復元
psql -U whisper_admin whisper < /backup/whisper_20250113.sql
```

---

## 12. モニタリング

### 12.1 重要なメトリクス

```sql
-- テーブルサイズ
SELECT 
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;

-- インデックスサイズ
SELECT
    tablename,
    indexname,
    pg_size_pretty(pg_relation_size(indexname::regclass)) AS size
FROM pg_indexes
WHERE schemaname = 'public'
ORDER BY pg_relation_size(indexname::regclass) DESC;

-- スロークエリの確認
SELECT 
    query,
    calls,
    total_time,
    mean_time,
    max_time
FROM pg_stat_statements
ORDER BY mean_time DESC
LIMIT 10;
```

---

**文書作成日**: 2025-10-13
**最終更新日**: 2025-10-13
**バージョン**: 1.0
