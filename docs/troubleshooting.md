# トラブルシューティング

このドキュメントでは、開発中に発生する可能性のある問題とその解決方法をまとめています。

## 目次
1. [ポート競合エラー](#ポート競合エラー)
2. [GPU/CUDA関連エラー](#gpucuda関連エラー)
3. [環境変数・設定エラー](#環境変数設定エラー)
4. [依存パッケージエラー](#依存パッケージエラー)

---

## ポート競合エラー

### 問題: `Bind for 0.0.0.0:XXXX failed: port is already allocated`

**症状:**
Docker Composeでサービス起動時に以下のようなエラーが発生する：
```
Error response from daemon: failed to set up container networking:
driver failed programming external connectivity on endpoint whisper-redis:
Bind for 0.0.0.0:6379 failed: port is already allocated
```

**原因:**
ホストマシンで既に同じポートを使用している他のサービスが稼働している。

**対処法:**

1. **既存サービスの確認**
```bash
# ポート使用状況の確認
lsof -ti:6379  # Redis
lsof -ti:5432  # PostgreSQL
lsof -ti:8000  # Backend
lsof -ti:5173  # Frontend
```

2. **docker-compose.ymlのポートマッピング変更**

競合しているポートを変更します：

```yaml
services:
  postgres:
    ports:
      - "5434:5432"  # ホスト側のポートを変更

  redis:
    ports:
      - "6380:6379"  # ホスト側のポートを変更

  backend:
    ports:
      - "8001:8000"  # ホスト側のポートを変更

  frontend-dev:
    ports:
      - "5174:5173"  # ホスト側のポートを変更
```

**本プロジェクトでの実装:**
- PostgreSQL: `5434:5432`
- Redis: `6380:6379`
- Backend: `8001:8000`
- Frontend: `5174:5173`

---

## GPU/CUDA関連エラー

### 問題: `torch==2.1.0+cu118` インストール失敗

**症状:**
バックエンドDockerイメージのビルド時に以下のエラーが発生：
```
ERROR: Could not find a version that satisfies the requirement torch==2.1.0+cu118
ERROR: No matching distribution found for torch==2.1.0+cu118
```

**原因:**
- MacBook AirなどGPUを搭載していない環境で、CUDA版のPyTorchをインストールしようとしている
- ARM64アーキテクチャ（Apple Silicon）ではCUDA版のPyTorchが利用できない

**対処法:**

開発環境用に**GPU依存なし**の軽量版requirements.txtとDockerfileを作成：

1. **`backend/requirements-dev.txt` を作成**

```txt
# Development requirements (without GPU dependencies)

# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# Task Queue
celery==5.3.4
redis==5.0.1

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
psycopg2-binary==2.9.9

# Authentication
ldap3==2.9.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
email-validator==2.1.0

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2

# Development
ruff==0.1.6
black==23.11.0
mypy==1.7.1
```

2. **`backend/Dockerfile.dev` を作成**

```dockerfile
# Development Dockerfile (without GPU support)
FROM python:3.11-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    PIP_NO_CACHE_DIR=1

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy requirements
COPY requirements-dev.txt .

# Install Python dependencies
RUN pip install --upgrade pip && \
    pip install -r requirements-dev.txt

COPY . .

RUN mkdir -p /data/uploads /data/results /data/temp

EXPOSE 8000

CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]
```

3. **docker-compose.ymlで開発用Dockerfileを指定**

```yaml
backend:
  build:
    context: ./backend
    dockerfile: Dockerfile.dev  # 開発用Dockerfileを使用
```

**注意:**
- 本番環境（GPU搭載サーバー）では元の`Dockerfile`と`requirements.txt`を使用
- Whisper文字起こし機能はGPU環境でのみ動作（Phase 4以降で実装）

---

## 環境変数・設定エラー

### 問題: Pydantic Settings の CORS パースエラー

**症状:**
Alembic実行時または起動時に以下のエラーが発生：
```
pydantic_settings.sources.SettingsError: error parsing value for field
"BACKEND_CORS_ORIGINS" from source "DotEnvSettingsSource"
json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0)
```

**原因:**
Pydantic Settingsが`List[str]`型のフィールドを`.env`ファイルから読み込む際、JSON形式として自動パースしようとして失敗している。

**対処法:**

1. **バリデータの修正** (`backend/app/core/config.py`)

```python
@field_validator("BACKEND_CORS_ORIGINS", mode="before")
@classmethod
def assemble_cors_origins(cls, v: str | List[str] | None) -> List[str]:
    if v is None or v == "":
        return ["http://localhost:3000", "http://localhost:5173"]
    if isinstance(v, str):
        if v.startswith("["):
            # JSON array string
            import json
            return json.loads(v)
        # Comma-separated string
        return [i.strip() for i in v.split(",")]
    elif isinstance(v, list):
        return v
    raise ValueError(v)
```

2. **環境変数で直接JSON配列を指定** (docker-compose.yml)

```yaml
backend:
  environment:
    - BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:8001"]
```

3. **コンテナ内の.envファイルを削除**

環境変数が優先されるように：
```bash
docker-compose exec backend rm -f .env
docker-compose restart backend
```

**推奨設定:**
- 開発環境: docker-compose.ymlの環境変数でJSON配列形式を使用
- 本番環境: 環境変数ファイルでカンマ区切り文字列を使用

**重要**: フロントエンド開発サーバーのポート（5174）を必ずCORS設定に含める：
```yaml
- BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:5174","http://localhost:8001"]
```

---

## 依存パッケージエラー

### 問題: `email-validator is not installed`

**症状:**
FastAPI起動時に以下のエラーが発生：
```python
ImportError: email-validator is not installed, run `pip install pydantic[email]`
```

**原因:**
Pydantic の`EmailStr`型を使用する場合、`email-validator`パッケージが必要だが、requirements.txtに含まれていない。

**対処法:**

`backend/requirements-dev.txt`に追加：
```txt
# Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
email-validator==2.1.0  # 追加
```

再ビルド：
```bash
docker-compose up -d --build backend
```

**本番環境:**
`backend/requirements.txt`にも同様に追加する必要があります。

---

## データベースマイグレーション

### マイグレーション実行手順

1. **データベースサービスの起動確認**
```bash
docker-compose ps postgres
# STATUS が "healthy" であることを確認
```

2. **マイグレーション実行**
```bash
docker-compose exec backend alembic upgrade head
```

3. **成功時の出力例**
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001, create users table
```

### よくある問題

**問題: `FATAL: database "whisper" does not exist`**

**対処法:**
```bash
# PostgreSQLコンテナに入る
docker-compose exec postgres psql -U user -d postgres

# データベース作成
CREATE DATABASE whisper;

# 終了
\q
```

---

## 開発環境セットアップのチェックリスト

開発環境が正しくセットアップされているか確認：

- [ ] PostgreSQL起動済み (ポート5434)
- [ ] Redis起動済み (ポート6380)
- [ ] Backend起動済み (ポート8001)
- [ ] Frontend起動済み (ポート5174)
- [ ] データベースマイグレーション完了

**確認コマンド:**
```bash
# サービス状態確認
docker-compose ps

# ログ確認
docker-compose logs backend --tail 20
docker-compose logs frontend-dev --tail 20

# API疎通確認
curl http://localhost:8001/
curl http://localhost:8001/health
```

---

## モック認証（開発環境）

### 問題: LDAP サーバーがないためログインできない

**症状:**
開発環境でLDAPサーバーが利用できず、ログイン機能のテストができない。

**対処法:**

開発環境ではモック認証を使用してLDAPサーバーなしでログインが可能です。

**1. モック認証の有効化**

docker-compose.ymlで`USE_MOCK_AUTH=true`を設定（開発環境では既に設定済み）：

```yaml
backend:
  environment:
    - USE_MOCK_AUTH=true
```

**2. テストアカウント**

以下のアカウントでログイン可能：

| ユーザー名 | パスワード | 権限 |
|----------|----------|------|
| admin | admin123 | 管理者 |
| user1 | user123 | 一般ユーザー |

**3. ログイン確認**

```bash
# API経由でログインテスト
curl -X POST http://localhost:8001/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"username":"admin","password":"admin123"}'
```

**4. ブラウザでログイン**

1. http://localhost:5174 にアクセス
2. ログインページで上記のアカウント情報を入力
3. ログイン成功後、ダッシュボードが表示される

**注意:**
- モック認証は開発環境専用です
- 本番環境では`USE_MOCK_AUTH=false`（デフォルト）でLDAP認証を使用
- モックユーザーは`backend/app/services/auth_service.py`で定義されています

---

## その他のTips

### Docker環境のクリーンアップ

問題が解決しない場合、クリーンな状態からやり直す：

```bash
# コンテナ停止・削除
docker-compose down

# ボリューム削除（データベースも削除される）
docker-compose down -v

# イメージも削除
docker-compose down --rmi all

# 再ビルド・起動
docker-compose up -d --build
```

### ログの確認方法

```bash
# 全サービスのログ
docker-compose logs -f

# 特定サービスのログ
docker-compose logs -f backend
docker-compose logs -f frontend-dev

# エラーのみ表示
docker-compose logs backend 2>&1 | grep -i error
```

---

## 本番環境との違い

| 項目 | 開発環境 | 本番環境 |
|------|---------|---------|
| Dockerfile | `Dockerfile.dev` | `Dockerfile` (CUDA対応) |
| Requirements | `requirements-dev.txt` | `requirements.txt` (GPU版) |
| GPU | 不要 | 必須（NVIDIA A100） |
| Whisper | 動作しない | 動作する |
| CORS | 緩い設定 | 厳密な設定 |
| ポート | 8001, 5174 | 80, 443 (Nginx経由) |

開発環境ではPhase 1-2（環境構築・認証）の実装と動作確認を行い、GPU必須のPhase 4（Whisper文字起こし）以降は本番環境で実装・テストを行う想定です。
