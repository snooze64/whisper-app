# デプロイガイド

このガイドでは、Whisper Appを本番環境にデプロイする際のベストプラクティス、監視、メンテナンス、更新について説明します。

## 目次

1. [デプロイ前チェックリスト](#pre-deployment-checklist)
2. [初期デプロイ](#initial-deployment)
3. [SSL/TLS設定](#ssltls-configuration)
4. [監視設定](#monitoring-setup)
5. [バックアップ設定](#backup-configuration)
6. [スケーリングの考慮事項](#scaling-considerations)
7. [更新手順](#update-procedures)
8. [ロールバック手順](#rollback-procedures)
9. [メンテナンスタスク](#maintenance-tasks)

## Pre-deployment Checklist

### インフラストラクチャ要件

- [ ] **サーバーの準備完了** 最小スペック:
  - 8コア以上のCPU
  - 32GB以上のRAM
  - 100GB以上のディスク容量
  - 20-30GB VRAMのNVIDIA GPU
- [ ] **NVIDIAドライバのインストール完了** (バージョン 525.60.13以降)
- [ ] **NVIDIA Container Toolkit**のインストールと設定完了
- [ ] **Docker** (24.0以降) と Docker Compose (2.20以降) のインストール完了
- [ ] **ドメイン名**の登録とDNS設定完了
- [ ] **ファイアウォール**の設定完了 (ポート80, 443を開放)
- [ ] **SSL証明書**の準備完了 (Let's Encryptまたは商用証明書)

### 設定

- [ ] 本番環境の値で`.env`ファイルを作成済み
- [ ] データベースとRedisの強力なパスワードを生成済み
- [ ] `SECRET_KEY`を生成済み (32バイト以上のランダム値)
- [ ] LDAPサーバーの詳細を設定済み
- [ ] Nginxでドメイン名を設定済み
- [ ] Let's EncryptのSSLメール設定完了
- [ ] バックアップ保持ポリシーを設定済み
- [ ] ファイル保持時間を設定済み

### セキュリティ

- [ ] すべてのパスワードが強力なランダム値を使用
- [ ] `SECRET_KEY`が一意で外部に公開されていない
- [ ] LDAPバインド認証情報が保護されている
- [ ] データベースがDockerネットワークのみに公開されている
- [ ] RedisがDockerネットワークのみに公開されている
- [ ] ファイアウォールルールをテスト済み
- [ ] SSL/TLS証明書が有効

### テスト

- [ ] 開発環境でテスト済み
- [ ] すべてのマイグレーションが正常に適用済み
- [ ] バックエンドテストが合格 (pytest)
- [ ] フロントエンドテストが合格 (npm test)
- [ ] 統合テストが合格
- [ ] LDAP認証をテスト済み

## Initial Deployment

### ステップ1: サーバーの準備

```bash
# システムの更新
sudo apt-get update && sudo apt-get upgrade -y

# 必要なパッケージのインストール
sudo apt-get install -y git curl wget ufw

# ファイアウォールの設定
sudo ufw allow 22/tcp   # SSH
sudo ufw allow 80/tcp   # HTTP
sudo ufw allow 443/tcp  # HTTPS
sudo ufw enable

# Dockerのインストール (未インストールの場合)
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER
```

### ステップ2: クローンと設定

```bash
# リポジトリのクローン
git clone https://github.com/your-org/whisper-app.git
cd whisper-app

# 安定版ブランチ/タグに切り替え
git checkout tags/v1.0.0  # または: git checkout main

# 環境設定のコピーと編集
cp .env.example .env
nano .env  # 本番環境の値で編集

# セキュアなシークレットの生成
export SECRET_KEY=$(openssl rand -hex 32)
export POSTGRES_PASSWORD=$(openssl rand -base64 32)

# 生成されたシークレットで.envを更新
sed -i "s/your_secret_key_here/$SECRET_KEY/" .env
sed -i "s/your_postgres_password/$POSTGRES_PASSWORD/" .env

# ドメイン名の更新
export DOMAIN=yourdomain.com
sed -i "s/yourdomain.com/$DOMAIN/g" .env
sed -i "s/yourdomain.com/$DOMAIN/g" nginx/nginx.prod.conf
```

### ステップ3: フロントエンドのビルド

```bash
cd frontend

# 依存関係のインストール
npm install

# 本番環境用のビルド
npm run build

cd ..
```

### ステップ4: データディレクトリの準備

```bash
# ディレクトリの作成
mkdir -p data/uploads data/results data/temp
mkdir -p backup
mkdir -p logs/nginx logs/backend logs/celery
mkdir -p certbot/conf certbot/www

# パーミッションの設定
chmod 755 data backup logs certbot
```

### ステップ5: SSL証明書の取得

#### Let's Encryptを使用する場合

```bash
# nginxを一時的に起動 (HTTPのみ)
docker-compose -f docker-compose.prod.yml up -d nginx postgres redis

# nginxの準備ができるまで待機
sleep 10

# 証明書の取得
docker-compose -f docker-compose.prod.yml run --rm certbot certonly \
  --webroot \
  --webroot-path=/var/www/certbot \
  --email admin@yourdomain.com \
  --agree-tos \
  --no-eff-email \
  -d yourdomain.com

# 証明書の確認
ls -la certbot/conf/live/yourdomain.com/

# 一時的なnginxの停止
docker-compose -f docker-compose.prod.yml down
```

#### 既存の証明書を使用する場合

```bash
# 証明書のコピー
mkdir -p certbot/conf/live/yourdomain.com
cp /path/to/fullchain.pem certbot/conf/live/yourdomain.com/
cp /path/to/privkey.pem certbot/conf/live/yourdomain.com/
cp /path/to/chain.pem certbot/conf/live/yourdomain.com/

# パーミッションの設定
chmod 600 certbot/conf/live/yourdomain.com/*.pem
```

### ステップ6: サービスのデプロイ

```bash
# すべてのサービスをビルドして起動
docker-compose -f docker-compose.prod.yml up -d --build

# 起動状況の監視
docker-compose -f docker-compose.prod.yml logs -f

# サービスがヘルシーになるまで待機
docker-compose -f docker-compose.prod.yml ps
```

### ステップ7: データベースの初期化

```bash
# マイグレーションの適用
docker-compose -f docker-compose.prod.yml exec backend alembic upgrade head

# テーブルが作成されたことを確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "\dt"

# マイグレーションステータスの確認
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

### ステップ8: 管理者ユーザーの作成

```bash
# データベースへのアクセス
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod

# 管理者ユーザーの作成 (最初のLDAPログイン時に作成され、その後昇格)
# 最初のLDAPログイン後、以下を実行:
UPDATE users SET is_admin = true WHERE username = 'admin_username';

# 確認
SELECT id, username, email, is_admin FROM users;

# 終了
\q
```

### ステップ9: デプロイの確認

以下の[確認手順](#verification-steps)セクションのすべての検証ステップを実行してください。

## SSL/TLS Configuration

### Let's Encrypt証明書の更新

証明書はcertbotコンテナによって自動的に更新されます。更新をテストするには:

```bash
# 更新のテスト (ドライラン)
docker-compose -f docker-compose.prod.yml run --rm certbot renew --dry-run

# 強制更新 (必要な場合)
docker-compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# 更新後にnginxをリロード
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### 証明書更新のCronジョブ

certbotコンテナは1日2回自動的に更新を試みます。ログの監視:

```bash
docker-compose -f docker-compose.prod.yml logs certbot
```

### SSL設定の更新

NginxのSSL設定を更新するには:

```bash
# nginx設定の編集
nano nginx/nginx.prod.conf

# 設定のテスト
docker-compose -f docker-compose.prod.yml exec nginx nginx -t

# nginxのリロード
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

## Monitoring Setup

### アプリケーション監視

#### ログ監視

```bash
# リアルタイムログの表示
docker-compose -f docker-compose.prod.yml logs -f

# 特定のサービスログの表示
docker-compose -f docker-compose.prod.yml logs -f backend
docker-compose -f docker-compose.prod.yml logs -f celery-worker
docker-compose -f docker-compose.prod.yml logs -f nginx

# ログをファイルに保存
docker-compose -f docker-compose.prod.yml logs --no-color > logs/application-$(date +%Y%m%d).log
```

#### ヘルスチェック監視

監視スクリプトを作成 (`scripts/health-check.sh`):

```bash
#!/bin/bash
# ヘルスチェックスクリプト

DOMAIN="https://yourdomain.com"
ALERT_EMAIL="admin@yourdomain.com"

# ヘルスエンドポイントのチェック
if ! curl -sf "$DOMAIN/health" > /dev/null; then
    echo "Health check failed at $(date)" | mail -s "Whisper App Health Check Failed" $ALERT_EMAIL
    exit 1
fi

# SSL証明書の有効期限チェック
EXPIRY_DATE=$(echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -enddate | cut -d= -f2)
EXPIRY_EPOCH=$(date -d "$EXPIRY_DATE" +%s)
CURRENT_EPOCH=$(date +%s)
DAYS_UNTIL_EXPIRY=$(( ($EXPIRY_EPOCH - $CURRENT_EPOCH) / 86400 ))

if [ $DAYS_UNTIL_EXPIRY -lt 7 ]; then
    echo "SSL certificate expires in $DAYS_UNTIL_EXPIRY days" | mail -s "Whisper App SSL Certificate Expiring" $ALERT_EMAIL
fi

echo "Health check passed at $(date)"
```

cronに追加:
```bash
# 5分ごとに実行
*/5 * * * * /path/to/whisper-app/scripts/health-check.sh >> /var/log/whisper-health.log 2>&1
```

### システムリソース監視

#### GPU監視

```bash
# GPU使用状況の監視
watch -n 1 docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# GPU統計をファイルに記録
while true; do
    docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi --query-gpu=timestamp,temperature.gpu,utilization.gpu,utilization.memory,memory.used,memory.free --format=csv >> logs/gpu-stats-$(date +%Y%m%d).csv
    sleep 60
done
```

#### コンテナリソース使用状況

```bash
# コンテナ統計の表示
docker stats

# コンテナ統計のログ記録
docker stats --no-stream >> logs/container-stats-$(date +%Y%m%d).log
```

### データベース監視

```bash
# データベースサイズの確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT pg_size_pretty(pg_database_size('whisper_prod')) AS db_size;
"

# テーブルサイズの確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname = 'public'
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"

# アクティブな接続数の確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT count(*) as active_connections FROM pg_stat_activity WHERE state = 'active';
"

# スロークエリの確認 (pg_stat_statementsが有効な場合)
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT query, calls, mean_exec_time, stddev_exec_time
FROM pg_stat_statements
ORDER BY mean_exec_time DESC
LIMIT 10;
"
```

### アラート

監視ツールとの統合を検討してください:
- **Prometheus + Grafana**: メトリクスの可視化
- **ELK Stack (Elasticsearch, Logstash, Kibana)**: ログ集約
- **Sentry**: エラートラッキング
- **PagerDuty/Opsgenie**: インシデント管理

## Backup Configuration

### 自動バックアップ

バックアップサービスは毎日午前3時(UTC)に実行されます。設定:

```bash
# バックアップサービスのステータス表示
docker-compose -f docker-compose.prod.yml ps backup

# バックアップログの表示
docker-compose -f docker-compose.prod.yml logs backup

# バックアップの一覧表示
ls -lh backup/

# 最新バックアップの確認
ls -lh backup/whisper_backup_latest.sql.gz
```

### 手動バックアップ

```bash
# 手動バックアップの作成
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# カスタムファイル名でのバックアップ
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
docker-compose -f docker-compose.prod.yml exec postgres pg_dump -U whisper_prod whisper_prod | gzip > backup/manual_backup_${TIMESTAMP}.sql.gz
```

### オフサイトバックアップ

自動オフサイトバックアップの設定:

```bash
#!/bin/bash
# scripts/offsite-backup.sh

BACKUP_DIR="/path/to/whisper-app/backup"
REMOTE_HOST="backup-server.example.com"
REMOTE_PATH="/backups/whisper-app"

# リモートサーバーにバックアップを同期
rsync -avz --delete \
  $BACKUP_DIR/ \
  user@$REMOTE_HOST:$REMOTE_PATH/

# または、クラウドストレージにアップロード (S3の例)
# aws s3 sync $BACKUP_DIR s3://your-bucket/whisper-backups/
```

cronに追加:
```bash
# 毎日午前4時に実行 (バックアップ完了後)
0 4 * * * /path/to/whisper-app/scripts/offsite-backup.sh >> /var/log/offsite-backup.log 2>&1
```

### バックアップからの復元

```bash
# サービスの停止
docker-compose -f docker-compose.prod.yml stop backend celery-worker

# データベースの復元
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# サービスの再起動
docker-compose -f docker-compose.prod.yml start backend celery-worker

# 復元の確認
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

## Scaling Considerations

### 垂直スケーリング

#### コンテナリソースの増加

`docker-compose.prod.yml`を編集:

```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '8'      # 4から増加
          memory: 8G     # 4Gから増加

  celery-worker:
    deploy:
      resources:
        limits:
          cpus: '16'     # 8から増加
          memory: 64G    # 32Gから増加
```

#### ワーカープロセスの増加

```yaml
services:
  backend:
    command: uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 8  # 4から増加
```

### 水平スケーリング

#### 複数のCeleryワーカー

Celeryワーカーコンテナを追加:

```yaml
services:
  celery-worker-1:
    <<: *celery-worker-config
    container_name: whisper-celery-worker-1
    environment:
      - CUDA_VISIBLE_DEVICES=0

  celery-worker-2:
    <<: *celery-worker-config
    container_name: whisper-celery-worker-2
    environment:
      - CUDA_VISIBLE_DEVICES=1  # 2番目のGPU
```

#### ロードバランシング

複数のバックエンドインスタンスの場合、ロードバランサーを追加:

```yaml
services:
  backend-1:
    <<: *backend-config

  backend-2:
    <<: *backend-config

  nginx:
    # upstream設定を更新
    volumes:
      - ./nginx/nginx.lb.conf:/etc/nginx/nginx.conf:ro
```

`nginx/nginx.lb.conf`を更新:
```nginx
upstream backend {
    least_conn;
    server backend-1:8000 max_fails=3 fail_timeout=30s;
    server backend-2:8000 max_fails=3 fail_timeout=30s;
    keepalive 32;
}
```

### データベースのスケーリング

高負荷の場合、以下を検討してください:
- **リードレプリカ**: 分析クエリ用
- **コネクションプーリング**: PgBouncer
- **パーティショニング**: 大きなテーブル用

## Update Procedures

### 更新前チェックリスト

- [ ] **バックアップの作成**と確認完了
- [ ] **変更履歴を確認**し、破壊的変更がないか確認
- [ ] **メンテナンスウィンドウのスケジュール**完了
- [ ] **ロールバック計画**の準備完了
- [ ] **チームへの通知**完了

### 更新手順

```bash
# 1. バックアップの作成
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# 2. メンテナンスモードの有効化 (オプション)
# nginx/html/にmaintenance.htmlを作成
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 3. 最新コードのプル
git fetch origin
git checkout tags/v1.1.0  # または特定のバージョン

# 4. 変更内容の確認
git log v1.0.0..v1.1.0

# 5. フロントエンドの更新
cd frontend
npm install
npm run build
cd ..

# 6. サービスの停止
docker-compose -f docker-compose.prod.yml down

# 7. データベースマイグレーションの適用
docker-compose -f docker-compose.prod.yml up -d postgres
sleep 10
docker-compose -f docker-compose.prod.yml run --rm backend alembic upgrade head

# 8. サービスの再ビルドと再起動
docker-compose -f docker-compose.prod.yml up -d --build

# 9. デプロイの確認
curl https://yourdomain.com/health

# 10. メンテナンスモードの無効化
# maintenance.htmlを削除
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload

# 11. ログの監視
docker-compose -f docker-compose.prod.yml logs -f --tail=100
```

### ゼロダウンタイム更新

重要なサービスの場合、ブルーグリーンデプロイメントを使用:

```bash
# 1. 新しいスタックへのデプロイ
docker-compose -f docker-compose.blue.yml up -d --build

# 2. 新しいスタックの確認
curl https://blue.yourdomain.com/health

# 3. トラフィックの切り替え (DNSまたはロードバランサーを更新)

# 4. 問題がないか監視

# 5. 安定している場合、古いスタックを停止
docker-compose -f docker-compose.green.yml down
```

## Rollback Procedures

### 即座のロールバック

更新中に問題が検出された場合:

```bash
# 1. 現在のサービスを停止
docker-compose -f docker-compose.prod.yml down

# 2. 前のバージョンにチェックアウト
git checkout tags/v1.0.0

# 3. データベースの復元 (マイグレーションが適用された場合)
gunzip -c backup/whisper_backup_YYYYMMDD_HHMMSS.sql.gz | \
  docker-compose -f docker-compose.prod.yml exec -T postgres psql -U whisper_prod -d whisper_prod

# 4. サービスの再ビルドと起動
docker-compose -f docker-compose.prod.yml up -d --build

# 5. ロールバックの確認
curl https://yourdomain.com/health
```

### データベースのロールバック

マイグレーションをロールバックするには:

```bash
# 特定のリビジョンにダウングレード
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade <revision>

# または1つ前のバージョンにダウングレード
docker-compose -f docker-compose.prod.yml exec backend alembic downgrade -1

# 確認
docker-compose -f docker-compose.prod.yml exec backend alembic current
```

## Maintenance Tasks

### 日次タスク

- [ ] サービスの健全性確認 (`docker-compose ps`)
- [ ] エラーログの確認
- [ ] ディスク使用量の監視
- [ ] バックアップの完了確認

### 週次タスク

- [ ] システムリソース使用状況の確認
- [ ] SSL証明書の有効期限確認
- [ ] スロークエリログの確認
- [ ] タスク処理時間の分析
- [ ] ユーザーフィードバック/問題の確認

### 月次タスク

- [ ] システムパッケージの更新
- [ ] Dockerイメージの確認と更新
- [ ] データベースメンテナンス (VACUUM, ANALYZE)
- [ ] アクセスログの異常確認
- [ ] 災害復旧手順のテスト
- [ ] ドキュメントの確認と更新

### データベースメンテナンス

```bash
# VACUUMとANALYZEの実行
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "VACUUM ANALYZE;"

# 肥大化したテーブルの確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "
SELECT schemaname, tablename,
       pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size,
       n_dead_tup
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC
LIMIT 10;
"

# 必要に応じて再インデックス
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "REINDEX DATABASE whisper_prod;"
```

### ログローテーション

Dockerログのログローテーション設定:

```json
// /etc/docker/daemon.json
{
  "log-driver": "json-file",
  "log-opts": {
    "max-size": "10m",
    "max-file": "3"
  }
}
```

Dockerデーモンの再起動:
```bash
sudo systemctl restart docker
```

### 古いデータのクリーンアップ

クリーンアップサービスは自動的に実行されますが、手動でトリガーするには:

```bash
# クリーンアップサービスの実行
docker-compose -f docker-compose.prod.yml exec cleanup python -m app.scripts.cleanup_files

# クリーンアップログの確認
docker-compose -f docker-compose.prod.yml logs cleanup
```

## Verification Steps

### デプロイ後の確認

```bash
# 1. すべてのサービスが実行中か確認
docker-compose -f docker-compose.prod.yml ps

# 2. HTTPSエンドポイントのテスト
curl https://yourdomain.com/health

# 3. 認証のテスト
curl -X POST https://yourdomain.com/api/v1/auth/login \
  -H "Content-Type: application/json" \
  -d '{"username": "test_user", "password": "test_pass"}'

# 4. データベースの確認
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT COUNT(*) FROM users;"

# 5. GPUアクセスの確認
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# 6. ファイルアップロードのテスト (UIまたはAPI経由)

# 7. エラーのログ監視
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# 8. SSL証明書の確認
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates

# 9. バックアップシステムのテスト
docker-compose -f docker-compose.prod.yml exec backup /scripts/backup.sh

# 10. クリーンアップサービスの確認
docker-compose -f docker-compose.prod.yml logs cleanup
```

## Troubleshooting

詳細なトラブルシューティング手順については、[troubleshooting.md](./troubleshooting.md)を参照してください。

### クイック診断

```bash
# サービスステータスの確認
docker-compose -f docker-compose.prod.yml ps

# 最近のエラーの表示
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# リソース使用状況の確認
docker stats

# ディスク容量の確認
df -h

# GPUステータスの確認
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi

# データベース接続のテスト
docker-compose -f docker-compose.prod.yml exec backend python -c "from app.core.database import test_connection; import asyncio; asyncio.run(test_connection())"
```

## Support and Documentation

- [セットアップガイド](./setup-guide.md) - 初期セットアップ手順
- [API仕様](./api-specification.md) - APIエンドポイントのドキュメント
- [トラブルシューティングガイド](./troubleshooting.md) - 一般的な問題と解決方法
- [アーキテクチャドキュメント](./architecture.md) - システム設計とアーキテクチャ
- [データベース設計](./database-design.md) - データベーススキーマとリレーションシップ

問題報告: https://github.com/your-org/whisper-app/issues
