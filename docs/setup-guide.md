# セットアップガイド

このガイドでは、開発環境と本番環境の両方でWhisper Appをセットアップする手順を説明します。

## 目次

1. [前提条件](#prerequisites)
2. [システム要件](#system-requirements)
3. [Docker Composeファイル](#docker-compose-files)
4. [開発環境のセットアップ](#development-setup)
5. [本番環境のセットアップ](#production-setup)
6. [初期設定](#initial-configuration)
7. [データベースのセットアップ](#database-setup)
8. [動作確認](#verification)

## Docker Composeファイル

このプロジェクトでは、CPU環境とGPU環境で別々のDocker Composeファイルを使用します:

### `docker-compose.cpu.yml` (CPU環境/開発環境)

**目的**: GPU要件なしのローカル開発環境

**機能**:
- CPUのみのfaster-whisper(またはモックモード)
- バックエンドとフロントエンドのホットリロード有効
- モック認証(LDAPが不要)
- CPU用Dockerfile
- ポートマッピング: フロントエンド 5174、バックエンド 8001
- HuggingFaceモデル用のモデルキャッシュボリューム

**使用方法**:
```bash
docker-compose -f docker-compose.cpu.yml up -d
docker-compose -f docker-compose.cpu.yml logs -f
docker-compose -f docker-compose.cpu.yml down
```

### `docker-compose.gpu.yml` (GPU環境/本番環境)

**目的**: 完全なGPUサポートと最適化された設定による本番デプロイ

**機能**:
- GPUサポート(NVIDIA CUDA)
- Let's Encryptを使用したSSL/HTTPS
- LDAP認証
- 自動バックアップ
- 自動ファイルクリーンアップ
- リソース制限と監視
- GPU用Dockerfile
- Nginxリバースプロキシ

**使用方法**:
```bash
docker-compose -f docker-compose.gpu.yml up -d
docker-compose -f docker-compose.gpu.yml logs -f
docker-compose -f docker-compose.gpu.yml down
```

**主な違い**:

| 機能 | CPU環境 (`docker-compose.cpu.yml`) | GPU環境 (`docker-compose.gpu.yml`) |
|---------|-----------------------------------|----------------------------------------|
| GPU | 不要(CPUモードのみ) | 必須(NVIDIA GPU) |
| SSL/HTTPS | なし(HTTPのみ) | あり(Let's Encrypt使用) |
| 認証 | モック認証有効 | LDAP認証 |
| ホットリロード | あり | なし |
| バックアップ | なし | 毎日自動バックアップ |
| ファイルクリーンアップ | なし | 自動クリーンアップサービス |
| リソース制限 | なし | あり(CPU/メモリ制限) |
| 監視 | 基本 | 完全なログ + メトリクス |

## 前提条件

### 必要なソフトウェア

#### 開発環境
- **Docker** (バージョン24.0+) と Docker Compose (バージョン2.20+)
- **Git** (バージョン2.30+)
- **Node.js** (ローカルフロントエンド開発用にバージョン18+)
- **Python** (ローカルバックエンド開発用にバージョン3.11+)

#### 本番環境
- **Docker** (バージョン24.0+) と Docker Compose (バージョン2.20+)
- **NVIDIA GPU** CUDA対応(計算能力7.0+)
- **NVIDIA Driver** (バージョン525.60.13+)
- **NVIDIA Container Toolkit** Docker内でのGPUアクセス用
- **ドメイン名** DNS設定済み(SSL/TLS用)
- **最低50GB**の空きディスク容量

### ハードウェア要件

#### 開発環境
- **CPU**: 最低4コア
- **RAM**: 最低8GB(16GB推奨)
- **GPU**: オプション(CPUのみモード利用可)
- **ディスク**: 20GBの空き容量

#### 本番環境
- **CPU**: 最低8コア(16コア推奨)
- **RAM**: 最低32GB(大規模モデルには64GB推奨)
- **GPU**: 20-30GB VRAMのNVIDIA GPU(例: RTX 3090、RTX 4090、A100)
  - large-v3モデル: 最低12GB VRAM
  - large-v3-turboモデル: 最低10GB VRAM
- **ディスク**: 100GB以上の空き容量(アップロード、結果、バックアップ用)

### ネットワーク要件

#### 開発環境
- ポート: 3000(フロントエンド)、8000(バックエンド)、5432(postgres)、6379(redis)

#### 本番環境
- ポート: 80(HTTP)、443(HTTPS)
- ポート80と443でのインバウンドトラフィックを許可するファイアウォール設定
- SSL証明書更新のためのLet's Encryptサーバーへのアウトバウンドアクセス

## システム要件

### NVIDIA GPUセットアップ(本番環境)

1. **NVIDIA Driverのインストール**:
```bash
# 現在のドライバーバージョンを確認
nvidia-smi

# インストールされていないか古い場合、最新ドライバーをインストール
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nvidia-driver-535

# インストールの確認
nvidia-smi
```

2. **NVIDIA Container Toolkitのインストール**:
```bash
# リポジトリの追加
distribution=$(. /etc/os-release;echo $ID$VERSION_ID)
curl -fsSL https://nvidia.github.io/libnvidia-container/gpgkey | sudo gpg --dearmor -o /usr/share/keyrings/nvidia-container-toolkit-keyring.gpg
curl -s -L https://nvidia.github.io/libnvidia-container/$distribution/libnvidia-container.list | \
    sed 's#deb https://#deb [signed-by=/usr/share/keyrings/nvidia-container-toolkit-keyring.gpg] https://#g' | \
    sudo tee /etc/apt/sources.list.d/nvidia-container-toolkit.list

# インストール
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit

# DockerがNVIDIAランタイムを使用するように設定
sudo nvidia-ctk runtime configure --runtime=docker
sudo systemctl restart docker

# 確認
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### CUDA 11.4固有のセットアップ(Transformersバックエンド)

環境がCUDA 11.4の場合、faster-whisper(CUDA 11.8+が必要)の代わりにtransformersバックエンドを使用する必要があります。

1. **CUDAバージョンの確認**:
```bash
nvidia-smi

# 出力でCUDAバージョンを確認
# CUDA Version: 11.4.xxx
```

2. **transformersバックエンドの依存関係をインストール**:
```bash
# バックエンドコンテナ内で
docker-compose exec backend pip install -r requirements-transformers-cuda114.txt

# またはビルド時に、このrequirementsファイルを使用するようDockerfileを修正
```

3. **環境変数の設定**:

`docker-compose.cpu.yml`または`docker-compose.gpu.yml`、もしくは`.env`ファイルを編集:
```yaml
celery-worker:
  environment:
    - WHISPER_BACKEND=transformers  # CUDA 11.4には必須
```

または`.env`に追加:
```bash
WHISPER_BACKEND=transformers
```

4. **transformersのインストールを確認**:
```bash
# transformersがインストールされているか確認
docker-compose -f docker-compose.cpu.yml exec backend python -c "import transformers; print(transformers.__version__)"

# 期待される出力: 4.35.2
```

5. **transformersバックエンドのテスト**:
```bash
# 簡単な文字起こしテストを実行
docker-compose -f docker-compose.cpu.yml exec backend python -c "
from app.tasks.whisper_transformers import WhisperTranscriberTransformers
transcriber = WhisperTranscriberTransformers(model_name='tiny', device='cpu', torch_dtype='float32')
print('✅ Transformers backend loaded successfully')
"
```

**重要な注意事項**:
- Transformersバックエンドはfaster-whisperより**2-4倍遅い**
- faster-whisperより**1.5-2倍多くのVRAM**を使用
- CUDA 11.4が必要な場合のみ使用(faster-whisperにはCUDA 11.8+が必要)
- 新規インストールの場合、より良いパフォーマンスのためにCUDA 11.8+または12.xを推奨

**依存関係**:
- `torch==2.0.1+cu117` (CUDA 11.7バイナリはフォワード互換性によりCUDA 11.4ドライバーで動作)
- `transformers==4.35.2`
- `accelerate==0.24.1`
- `safetensors==0.4.1`

詳細については[technology-stack.md](./technology-stack.md)のセクション14.3を参照してください。

### Dockerのインストール

#### Ubuntu/Debian
```bash
# 古いバージョンをアンインストール
sudo apt-get remove docker docker-engine docker.io containerd runc

# 便利スクリプトを使用してインストール
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh

# dockerグループにユーザーを追加(オプション、非root アクセス用)
sudo usermod -aG docker $USER
newgrp docker

# インストールの確認
docker --version
docker compose version
```

#### その他のLinuxディストリビューション
公式Dockerドキュメントを参照: https://docs.docker.com/engine/install/

## 開発環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/whisper-app.git
cd whisper-app
```

### 2. 環境ファイルの作成

```bash
cp .env.example .env
```

`.env`を開発設定で編集:

```bash
# ========================================
# Database Configuration
# ========================================
POSTGRES_USER=whisper_dev
POSTGRES_PASSWORD=dev_password_123
POSTGRES_DB=whisper_dev
DATABASE_URL=postgresql://whisper_dev:dev_password_123@postgres:5432/whisper_dev

# ========================================
# Redis Configuration
# ========================================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ========================================
# Security
# ========================================
# Generate with: openssl rand -hex 32
SECRET_KEY=your_dev_secret_key_here

# JWT Configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ========================================
# CORS Configuration
# ========================================
BACKEND_CORS_ORIGINS=["http://localhost:3000","http://localhost:5173","http://localhost:5174","http://localhost:8001"]

# ========================================
# LDAP Authentication
# ========================================
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=example,dc=com
LDAP_USER_DN_TEMPLATE=uid={username},ou=users,dc=example,dc=com

# Set to true to use mock authentication (development only)
USE_MOCK_AUTH=true

# ========================================
# File Storage Configuration
# ========================================
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# ========================================
# Whisper Configuration
# ========================================
DEFAULT_WHISPER_MODEL=large-v3-turbo
DEFAULT_LANGUAGE=ja

# ========================================
# GPU Configuration
# ========================================
CUDA_VISIBLE_DEVICES=0
GPU_MEMORY_THRESHOLD_MB=10000

# ========================================
# Frontend Configuration
# ========================================
VITE_API_URL=http://localhost:8001

# ========================================
# Proxy Configuration (Optional)
# ========================================
# 企業プロキシ環境の場合は、以下のコメントを外して設定
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080
# NO_PROXY=localhost,127.0.0.1,postgres,redis,backend,celery-worker,frontend-dev

# ========================================
# Application Settings
# ========================================
ENVIRONMENT=development
DEBUG=true
LOG_LEVEL=DEBUG
```

### 3. 開発サービスの起動

```bash
# すべてのサービスをビルドして起動
docker-compose -f docker-compose.cpu.yml up -d --build

# ログの表示
docker-compose -f docker-compose.cpu.yml logs -f

# サービスステータスの確認
docker-compose -f docker-compose.cpu.yml ps
```

### 4. データベースの初期化

```bash
# マイグレーションの実行
docker-compose -f docker-compose.cpu.yml exec backend alembic upgrade head

# テーブルが作成されたことを確認
docker-compose -f docker-compose.cpu.yml exec postgres psql -U whisper_dev -d whisper_dev -c "\dt"
```

### 5. サービスへのアクセス

- **フロントエンド**: http://localhost:3000
- **バックエンドAPI**: http://localhost:8000
- **APIドキュメント**: http://localhost:8000/docs
- **PostgreSQL**: localhost:5432
- **Redis**: localhost:6379

## 本番環境のセットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/your-org/whisper-app.git
cd whisper-app
```

### 2. 環境変数の設定

```bash
cp .env.example .env
```

`.env`を本番設定で編集:

```bash
# ========================================
# Database Configuration
# ========================================
POSTGRES_USER=whisper_prod
POSTGRES_PASSWORD=CHANGE_THIS_STRONG_PASSWORD  # 強力なパスワードを使用
POSTGRES_DB=whisper_prod
DATABASE_URL=postgresql://whisper_prod:${POSTGRES_PASSWORD}@postgres:5432/whisper_prod

# ========================================
# Redis Configuration
# ========================================
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0

# ========================================
# Security
# ========================================
# Generate with: openssl rand -hex 32
SECRET_KEY=CHANGE_THIS_TO_RANDOM_SECRET_KEY

# JWT Configuration
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=15
REFRESH_TOKEN_EXPIRE_DAYS=7

# ========================================
# CORS Configuration
# ========================================
# 実際のドメインに置き換えてください
BACKEND_CORS_ORIGINS=["https://yourdomain.com"]

# ========================================
# LDAP Authentication
# ========================================
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=company,dc=com
LDAP_USER_DN_TEMPLATE=uid={username},ou=users,dc=company,dc=com

# Set to false in production
USE_MOCK_AUTH=false

# ========================================
# File Storage Configuration
# ========================================
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# ========================================
# Whisper Configuration
# ========================================
DEFAULT_WHISPER_MODEL=large-v3-turbo
DEFAULT_LANGUAGE=ja

# ========================================
# GPU Configuration
# ========================================
CUDA_VISIBLE_DEVICES=0
GPU_MEMORY_THRESHOLD_MB=10000

# ========================================
# SSL/TLS Configuration
# ========================================
DOMAIN_NAME=yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# ========================================
# Backup Configuration
# ========================================
BACKUP_RETENTION_DAYS=7

# ========================================
# Frontend Configuration
# ========================================
# 本番環境のAPIエンドポイントを指定
# 例: https://yourdomain.com または https://api.yourdomain.com
VITE_API_URL=https://yourdomain.com

# ========================================
# Proxy Configuration (Optional)
# ========================================
# 企業プロキシ環境の場合は、以下のコメントを外して設定
# HTTP_PROXY=http://proxy.example.com:8080
# HTTPS_PROXY=http://proxy.example.com:8080
# NO_PROXY=localhost,127.0.0.1,postgres,redis,backend,celery-worker

# ========================================
# Application Settings
# ========================================
ENVIRONMENT=production
DEBUG=false
LOG_LEVEL=INFO
```

**重要**: `yourdomain.com`を実際のドメイン名に置き換えてください!

### 3. SSL証明書のセットアップ

#### オプションA: Let's Encryptの使用(推奨)

1. **ドメインでNginx設定を更新**:
```bash
# nginx/nginx.prod.confを編集
sed -i 's/yourdomain.com/your-actual-domain.com/g' nginx/nginx.prod.conf
```

2. **SSL証明書の取得**:
```bash
# SSLなしでnginxを一時的に起動
docker-compose -f docker-compose.gpu.yml up -d nginx

# certbotを実行して証明書を取得
docker-compose -f docker-compose.gpu.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# SSLでnginxを再起動
docker-compose -f docker-compose.gpu.yml restart nginx
```

#### オプションB: 既存の証明書の使用

SSL証明書を適切な場所にコピー:
```bash
mkdir -p ./certbot/conf/live/yourdomain.com
cp /path/to/fullchain.pem ./certbot/conf/live/yourdomain.com/
cp /path/to/privkey.pem ./certbot/conf/live/yourdomain.com/
cp /path/to/chain.pem ./certbot/conf/live/yourdomain.com/
```

### 4. 必要なディレクトリの作成

```bash
# データディレクトリの作成
mkdir -p data/uploads data/results data/temp

# バックアップディレクトリの作成
mkdir -p backup

# ログディレクトリの作成
mkdir -p logs/nginx logs/backend logs/celery

# パーミッションの設定
chmod 755 data backup logs
```

### 5. 本番用フロントエンドのビルド

本番環境用のフロントエンドをビルドします。VITE_API_URLは`.env`ファイルから自動的に読み込まれます。

#### 自動ビルドスクリプトの使用（推奨）

```bash
# ビルドスクリプトに実行権限を付与
chmod +x scripts/build-frontend.sh

# ビルドスクリプトを実行
./scripts/build-frontend.sh
```

このスクリプトは以下を自動的に実行します：
1. `.env`ファイルから`VITE_API_URL`を読み込む
2. フロントエンドのDockerイメージをビルド（VITE_API_URLをbuild引数として渡す）
3. ビルド成果物を`./frontend/dist`に抽出

ビルド出力（`./frontend/dist`）はnginxコンテナによって提供されます。

#### 手動ビルド（オプション）

```bash
# フロントエンドのDockerイメージをビルド
docker-compose -f docker-compose.gpu.yml build frontend-build

# ビルド成果物を抽出
docker-compose -f docker-compose.gpu.yml run --rm frontend-build \
  sh -c "cp -r /usr/share/nginx/html/* /dist/"
```

**注意**:
- ビルド前に`.env`ファイルに`VITE_API_URL`が正しく設定されている必要があります
- プロキシ環境の場合は、`.env`ファイルでプロキシ設定も有効化してください

### 6. 本番サービスの起動

```bash
# すべてのサービスをビルドして起動
docker-compose -f docker-compose.gpu.yml up -d --build

# ログの表示
docker-compose -f docker-compose.gpu.yml logs -f

# サービスステータスの確認
docker-compose -f docker-compose.gpu.yml ps
```

### 7. データベースの初期化

```bash
# マイグレーションの実行
docker-compose -f docker-compose.gpu.yml exec backend alembic upgrade head

# テーブルの確認
docker-compose -f docker-compose.gpu.yml exec postgres psql -U whisper_prod -d whisper_prod -c "\dt"
```

### 8. 初期管理者ユーザーの作成

最初にログインしたLDAPユーザーがデータベースに作成されます。管理者にするには:

```bash
# データベースへアクセス
docker-compose -f docker-compose.gpu.yml exec postgres psql -U whisper_prod -d whisper_prod

# ユーザーを管理者に更新('username'を実際のユーザー名に置き換え)
UPDATE users SET is_admin = true WHERE username = 'admin_username';

# 確認
SELECT id, username, email, is_admin FROM users;

# 終了
\q
```

## 初期設定

### LDAP設定

LDAPサーバーがDockerネットワークからアクセス可能であることを確認:

1. **LDAP接続のテスト**:
```bash
# ホストマシンから
ldapsearch -x -H ldap://your-ldap-server:389 -D "cn=admin,dc=example,dc=com" -w password -b "dc=example,dc=com"

# Dockerコンテナから
docker-compose -f docker-compose.cpu.yml exec backend ldapsearch -x -H ldap://your-ldap-server:389 -D "cn=admin,dc=example,dc=com" -w password -b "dc=example,dc=com"
```

2. **必要に応じて`.env`のLDAP設定を調整**:
   - `LDAP_USER_SEARCH_BASE`: ユーザーを検索する場所
   - `LDAP_USER_OBJECT_CLASS`: ユーザーのLDAPオブジェクトクラス
   - `LDAP_USER_UID_ATTRIBUTE`: ユーザー名を含む属性(デフォルト: uid)

### ファイル保持ポリシー

自動ファイルクリーンアップの設定:

```bash
# .envを編集
FILE_RETENTION_HOURS=24  # 24時間より古いファイルを削除

# クリーンアップサービスの再起動
docker-compose -f docker-compose.gpu.yml restart cleanup
```

### バックアップスケジュール

バックアップサービスは毎日UTC午前3時に実行されます。調整するには:

```bash
# docker-compose.gpu.ymlを編集
services:
  backup:
    # ... 既存の設定 ...
    # エントリーポイントでcronスケジュールを調整するか、Docker再起動ポリシーを使用
```

手動バックアップの場合:
```bash
# バックアップを手動で実行
docker-compose -f docker-compose.gpu.yml exec backup /scripts/backup.sh
```

## データベースのセットアップ

### 開発データベース

開発データベースは、サービス起動時に自動的に作成され初期化されます:

```bash
# すべてのマイグレーションを適用
docker-compose -f docker-compose.cpu.yml exec backend alembic upgrade head

# マイグレーション状態の確認
docker-compose -f docker-compose.cpu.yml exec backend alembic current

# マイグレーション履歴の表示
docker-compose -f docker-compose.cpu.yml exec backend alembic history
```

### 本番データベース

#### 初期セットアップ

```bash
# すべてのマイグレーションを適用
docker-compose -f docker-compose.gpu.yml exec backend alembic upgrade head
```

#### バックアップと復元

**バックアップの作成**:
```bash
docker-compose -f docker-compose.gpu.yml exec backup /scripts/backup.sh
```

**バックアップからの復元**:
```bash
# サービスの停止
docker-compose -f docker-compose.gpu.yml stop backend celery-worker

# データベースの復元
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.gpu.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# サービスの起動
docker-compose -f docker-compose.gpu.yml start backend celery-worker
```

#### データベースマイグレーション

アプリケーションを更新する際:

```bash
# 最新コードの取得
git pull origin main

# 新しいマイグレーションの適用
docker-compose -f docker-compose.gpu.yml exec backend alembic upgrade head

# サービスの再起動
docker-compose -f docker-compose.gpu.yml restart backend celery-worker
```

## 動作確認

### 開発環境

1. **すべてのサービスが実行中か確認**:
```bash
docker-compose -f docker-compose.cpu.yml ps

# 期待される出力:
# NAME                   STATUS
# whisper-backend        Up
# whisper-celery-worker  Up
# whisper-frontend-dev   Up
# whisper-postgres       Up (healthy)
# whisper-redis          Up (healthy)
```

2. **バックエンドAPIのテスト**:
```bash
curl http://localhost:8001/health

# 期待される結果: {"status": "healthy"}
```

3. **フロントエンドのテスト**:
```bash
curl http://localhost:5174

# 期待される結果: HTMLコンテンツ
```

4. **データベースのテスト**:
```bash
docker-compose -f docker-compose.cpu.yml exec postgres psql -U whisper_dev -d whisper_dev -c "SELECT 1;"

# 期待される結果: 1行が返される
```

5. **Redisのテスト**:
```bash
docker-compose -f docker-compose.cpu.yml exec redis redis-cli ping

# 期待される結果: PONG
```

### 本番環境

1. **すべてのサービスが実行中か確認**:
```bash
docker-compose -f docker-compose.gpu.yml ps
```

2. **HTTPSエンドポイントのテスト**:
```bash
curl https://yourdomain.com/health

# 期待される結果: {"status": "healthy"}
```

3. **SSL証明書のテスト**:
```bash
openssl s_client -connect yourdomain.com:443 -servername yourdomain.com

# 証明書の有効性と有効期限を確認
```

4. **GPUアクセスのテスト**:
```bash
docker-compose -f docker-compose.gpu.yml exec celery-worker nvidia-smi

# GPU情報が表示されるはず
```

5. **認証のテスト**(UIまたはAPI経由):
```bash
# API経由でログイン
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "your_username", "password": "your_password"}'

# 期待される結果: {"access_token": "...", "refresh_token": "...", "token_type": "bearer"}
```

6. **ログのエラー確認**:
```bash
# バックエンドログ
docker-compose -f docker-compose.gpu.yml logs backend | grep ERROR

# Celeryログ
docker-compose -f docker-compose.gpu.yml logs celery-worker | grep ERROR

# Nginxログ
docker-compose -f docker-compose.gpu.yml logs nginx | grep error
```

### パフォーマンステスト

1. **ファイルアップロードのテスト**:
```bash
# 小さな音声ファイルをアップロード
curl -X POST https://yourdomain.com/api/v1/upload \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -F "file=@test_audio.mp3" \
  -F "model_name=large-v3-turbo" \
  -F "language=ja"

# タスクステータスの確認
curl https://yourdomain.com/api/v1/tasks/TASK_ID \
  -H "Authorization: Bearer YOUR_TOKEN"
```

2. **GPU使用率の監視**:
```bash
# GPU使用率を監視
watch -n 1 docker-compose -f docker-compose.gpu.yml exec celery-worker nvidia-smi
```

3. **データベースパフォーマンスの確認**:
```bash
# 遅いクエリの表示(有効な場合)
docker-compose -f docker-compose.gpu.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
```

## 次のステップ

セットアップが成功したら:

1. 継続的な運用について[deployment-guide.md](./deployment-guide.md)を確認
2. APIの詳細について[api-specification.md](./api-specification.md)を確認
3. 一般的な問題について[troubleshooting.md](./troubleshooting.md)を確認
4. 監視とアラート設定(デプロイガイドを参照)
5. 自動バックアップの設定(デプロイガイドを参照)

## 一般的な問題

詳細なトラブルシューティング手順については[troubleshooting.md](./troubleshooting.md)を参照してください。

### クイックフィックス

**サービスが起動しない**:
```bash
# ログの確認
docker-compose -f docker-compose.cpu.yml logs

# コンテナの再ビルド
docker-compose -f docker-compose.cpu.yml down
docker-compose -f docker-compose.cpu.yml up -d --build
```

**データベース接続エラー**:
```bash
# データベースが実行中か確認
docker-compose -f docker-compose.cpu.yml exec postgres pg_isready -U whisper_dev

# データベースのリセット(注意: データが破壊されます!)
docker-compose -f docker-compose.cpu.yml down -v
docker-compose -f docker-compose.cpu.yml up -d
```

**GPUが検出されない**:
```bash
# NVIDIA Container Toolkitの確認
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi

# Dockerデーモン設定の確認
cat /etc/docker/daemon.json
```

## サポート

問題や質問について:
- GitHub Issues: https://github.com/your-org/whisper-app/issues
- ドキュメント: https://github.com/your-org/whisper-app/tree/main/docs
