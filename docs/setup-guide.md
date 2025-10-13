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

このプロジェクトでは、開発環境と本番環境で別々のDocker Composeファイルを使用します:

### `docker-compose.yml` (開発環境)

**目的**: GPU要件なしのローカル開発環境

**機能**:
- CPUのみのfaster-whisper(またはモックモード)
- バックエンドとフロントエンドのホットリロード有効
- モック認証(LDAPが不要)
- 開発用Dockerfile
- ポートマッピング: フロントエンド 5174、バックエンド 8001
- HuggingFaceモデル用のモデルキャッシュボリューム

**使用方法**:
```bash
docker-compose up -d
docker-compose logs -f
docker-compose down
```

### `docker-compose.prod.yml` (本番環境)

**目的**: 完全なGPUサポートと最適化された設定による本番デプロイ

**機能**:
- GPUサポート(NVIDIA CUDA)
- Let's Encryptを使用したSSL/HTTPS
- LDAP認証
- 自動バックアップ
- 自動ファイルクリーンアップ
- リソース制限と監視
- 本番用Dockerfile
- Nginxリバースプロキシ

**使用方法**:
```bash
docker-compose -f docker-compose.prod.yml up -d
docker-compose -f docker-compose.prod.yml logs -f
docker-compose -f docker-compose.prod.yml down
```

**主な違い**:

| 機能 | 開発環境 (`docker-compose.yml`) | 本番環境 (`docker-compose.prod.yml`) |
|---------|-----------------------------------|----------------------------------------|
| GPU | オプション(CPUモード利用可) | 必須(NVIDIA GPU) |
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

`docker-compose.yml`または`.env`ファイルを編集:
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
docker-compose exec backend python -c "import transformers; print(transformers.__version__)"

# 期待される出力: 4.35.2
```

5. **transformersバックエンドのテスト**:
```bash
# 簡単な文字起こしテストを実行
docker-compose exec backend python -c "
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
# Database
POSTGRES_USER=whisper_dev
POSTGRES_PASSWORD=dev_password_123
POSTGRES_DB=whisper_dev
DATABASE_URL=postgresql+asyncpg://whisper_dev:dev_password_123@postgres:5432/whisper_dev

# Redis
REDIS_URL=redis://redis:6379

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=your_dev_secret_key_here

# LDAP (configure for your LDAP server)
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=example,dc=com
LDAP_BIND_DN=cn=admin,dc=example,dc=com
LDAP_BIND_PASSWORD=ldap_password
LDAP_USER_SEARCH_BASE=ou=users,dc=example,dc=com
LDAP_USER_OBJECT_CLASS=inetOrgPerson

# File Settings
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# Environment
ENVIRONMENT=development
```

### 3. 開発サービスの起動

```bash
# すべてのサービスをビルドして起動
docker-compose up -d --build

# ログの表示
docker-compose logs -f

# サービスステータスの確認
docker-compose ps
```

### 4. データベースの初期化

```bash
# マイグレーションの実行
docker-compose exec backend alembic upgrade head

# テーブルが作成されたことを確認
docker-compose exec postgres psql -U whisper_dev -d whisper_dev -c "\dt"
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
# Database (use strong passwords!)
POSTGRES_USER=whisper_prod
POSTGRES_PASSWORD=$(openssl rand -base64 32)
POSTGRES_DB=whisper_prod
DATABASE_URL=postgresql+asyncpg://whisper_prod:${POSTGRES_PASSWORD}@postgres:5432/whisper_prod

# Redis
REDIS_URL=redis://redis:6379

# Security (generate with: openssl rand -hex 32)
SECRET_KEY=$(openssl rand -hex 32)
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# LDAP (configure for your LDAP server)
LDAP_SERVER=ldap://your-ldap-server:389
LDAP_BASE_DN=dc=company,dc=com
LDAP_BIND_DN=cn=admin,dc=company,dc=com
LDAP_BIND_PASSWORD=strong_ldap_password
LDAP_USER_SEARCH_BASE=ou=users,dc=company,dc=com
LDAP_USER_OBJECT_CLASS=inetOrgPerson

# File Settings
MAX_FILE_SIZE=1073741824  # 1GB
FILE_RETENTION_HOURS=24

# Backup
BACKUP_RETENTION_DAYS=7

# SSL/TLS
SSL_DOMAIN=yourdomain.com
SSL_EMAIL=admin@yourdomain.com

# Environment
ENVIRONMENT=production

# GPU
CUDA_VISIBLE_DEVICES=0
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
docker-compose -f docker-compose.prod.yml up -d nginx

# certbotを実行して証明書を取得
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# SSLでnginxを再起動
docker-compose -f docker-compose.prod.yml restart nginx
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

```bash
cd frontend
npm install
npm run build
cd ..

# ビルド出力(dist/)はnginxコンテナにコピーされます
```

### 6. 本番サービスの起動

```bash
# すべてのサービスをビルドして起動
docker-compose -f docker-compose.prod.yml up -d --build

# ログの表示
docker-compose -f docker-compose.prod.yml logs -f

# サービスステータスの確認
docker-compose -f docker-compose.prod.yml ps
```

### 7. データベースの初期化

```bash
# マイグレーションの実行
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# テーブルの確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "\dt"
```

### 8. 初期管理者ユーザーの作成

最初にログインしたLDAPユーザーがデータベースに作成されます。管理者にするには:

```bash
# データベースへアクセス
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod

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
docker-compose exec backend ldapsearch -x -H ldap://your-ldap-server:389 -D "cn=admin,dc=example,dc=com" -w password -b "dc=example,dc=com"
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
docker-compose -f docker-compose.prod.yml restart cleanup
```

### バックアップスケジュール

バックアップサービスは毎日UTC午前3時に実行されます。調整するには:

```bash
# docker-compose.prod.ymlを編集
services:
  backup:
    # ... 既存の設定 ...
    # エントリーポイントでcronスケジュールを調整するか、Docker再起動ポリシーを使用
```

手動バックアップの場合:
```bash
# バックアップを手動で実行
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh
```

## データベースのセットアップ

### 開発データベース

開発データベースは、サービス起動時に自動的に作成され初期化されます:

```bash
# すべてのマイグレーションを適用
docker-compose exec backend alembic upgrade head

# マイグレーション状態の確認
docker-compose exec backend alembic current

# マイグレーション履歴の表示
docker-compose exec backend alembic history
```

### 本番データベース

#### 初期セットアップ

```bash
# すべてのマイグレーションを適用
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head
```

#### バックアップと復元

**バックアップの作成**:
```bash
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh
```

**バックアップからの復元**:
```bash
# サービスの停止
docker-compose -f docker-compose.prod.yml stop backend celery-worker

# データベースの復元
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# サービスの起動
docker-compose -f docker-compose.prod.yml start backend celery-worker
```

#### データベースマイグレーション

アプリケーションを更新する際:

```bash
# 最新コードの取得
git pull origin main

# 新しいマイグレーションの適用
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# サービスの再起動
docker-compose -f docker-compose.prod.yml restart backend celery-worker
```

## 動作確認

### 開発環境

1. **すべてのサービスが実行中か確認**:
```bash
docker-compose ps

# 期待される出力:
# NAME                   STATUS
# whisper-backend        Up
# whisper-celery-worker  Up
# whisper-frontend       Up
# whisper-postgres       Up (healthy)
# whisper-redis          Up (healthy)
```

2. **バックエンドAPIのテスト**:
```bash
curl http://localhost:8000/health

# 期待される結果: {"status": "healthy"}
```

3. **フロントエンドのテスト**:
```bash
curl http://localhost:3000

# 期待される結果: HTMLコンテンツ
```

4. **データベースのテスト**:
```bash
docker-compose exec postgres psql -U whisper_dev -d whisper_dev -c "SELECT 1;"

# 期待される結果: 1行が返される
```

5. **Redisのテスト**:
```bash
docker-compose exec redis redis-cli ping

# 期待される結果: PONG
```

### 本番環境

1. **すべてのサービスが実行中か確認**:
```bash
docker-compose -f docker-compose.prod.yml ps
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
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

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
docker-compose -f docker-compose.prod.yml logs backend | grep ERROR

# Celeryログ
docker-compose -f docker-compose.prod.yml logs celery-worker | grep ERROR

# Nginxログ
docker-compose -f docker-compose.prod.yml logs nginx | grep error
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
watch -n 1 docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi
```

3. **データベースパフォーマンスの確認**:
```bash
# 遅いクエリの表示(有効な場合)
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT * FROM pg_stat_statements ORDER BY mean_exec_time DESC LIMIT 10;"
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
docker-compose logs

# コンテナの再ビルド
docker-compose down
docker-compose up -d --build
```

**データベース接続エラー**:
```bash
# データベースが実行中か確認
docker-compose exec postgres pg_isready -U whisper_dev

# データベースのリセット(注意: データが破壊されます!)
docker-compose down -v
docker-compose up -d
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
