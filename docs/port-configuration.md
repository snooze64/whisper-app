# ポート設定ガイド

このドキュメントでは、Whisper Appのポート設定のカスタマイズ方法について説明します。

## 概要

すべての docker-compose ファイル（dev, CPU, GPU）で、ホストポートを環境変数で設定できるようになっています。これにより、ポート競合を避けたり、セキュリティ要件に合わせてポートを変更したりすることが可能です。

## デフォルトポート設定

### 開発環境（docker-compose.dev.yml）

| サービス | コンテナポート | デフォルトホストポート | 環境変数 |
|---------|--------------|---------------------|---------|
| PostgreSQL | 5432 | 5434 | `POSTGRES_HOST_PORT` |
| Redis | 6379 | 6380 | `REDIS_HOST_PORT` |
| Backend (FastAPI) | 8000 | 8001 | `BACKEND_HOST_PORT` |
| Frontend (Vite) | 5173 | 5174 | `FRONTEND_HOST_PORT` |

**ホストポートをずらしている理由**:
- 開発環境では、ローカルマシンで他のプロジェクトが標準ポートを使用している可能性があるため
- 本番環境との混同を避けるため

### 本番環境（docker-compose.cpu.yml / docker-compose.gpu.yml）

| サービス | コンテナポート | デフォルトホストポート | 環境変数 |
|---------|--------------|---------------------|---------|
| Nginx (HTTP) | 80 | 80 | `NGINX_HTTP_PORT` |
| Nginx (HTTPS) | 443 | 443 | `NGINX_HTTPS_PORT` |

**注意**:
- PostgreSQL, Redis, Backend は本番環境では Nginx 経由でのみアクセスされるため、外部ポートは公開されません
- Frontend は Nginx が静的ファイルとして配信するため、個別のポートは不要です

## ポート設定のカスタマイズ方法

### 1. 環境変数ファイルの作成

まず、対応する `.env.*.example` ファイルをコピーして使用します。

```bash
# 開発環境
cp .env.dev.example .env.dev

# CPU本番環境
cp .env.cpu.example .env.cpu

# GPU本番環境
cp .env.gpu.example .env.gpu
```

### 2. ポート設定の編集

#### 開発環境の例 (.env.dev)

```bash
# ================================
# Port Configuration
# ================================
# デフォルトから変更したい場合のみ編集
POSTGRES_HOST_PORT=5435       # デフォルト: 5434
REDIS_HOST_PORT=6381          # デフォルト: 6380
BACKEND_HOST_PORT=8002        # デフォルト: 8001
FRONTEND_HOST_PORT=5175       # デフォルト: 5174
```

#### 本番環境の例 (.env.cpu または .env.gpu)

```bash
# ================================
# Port Configuration
# ================================
# 標準ポート以外を使用したい場合のみ編集
NGINX_HTTP_PORT=8080          # デフォルト: 80
NGINX_HTTPS_PORT=8443         # デフォルト: 443
```

### 3. 起動

```bash
# 開発環境
docker-compose -f docker-compose.dev.yml --env-file .env.dev up -d

# CPU本番環境
docker-compose -f docker-compose.cpu.yml --env-file .env.cpu up -d

# GPU本番環境
docker-compose -f docker-compose.gpu.yml --env-file .env.gpu up -d
```

## ポート変更時の注意事項

### 1. VITE_API_URL の更新

フロントエンドがバックエンドに接続するためのURLも更新する必要があります。

**開発環境の場合**:
```bash
# .env.dev
BACKEND_HOST_PORT=8002
VITE_API_URL=http://localhost:8002
```

**本番環境の場合**:
```bash
# .env.cpu または .env.gpu
NGINX_HTTP_PORT=8080
NGINX_HTTPS_PORT=8443
VITE_API_URL=https://your-domain.com:8443
```

### 2. CORS設定の更新

バックエンドのCORS設定も更新が必要な場合があります。

```bash
# .env.dev
BACKEND_CORS_ORIGINS=["http://localhost:5175","http://localhost:8002"]
```

### 3. ファイアウォール設定

本番環境でポートを変更した場合、ファイアウォール設定も更新してください。

```bash
# UFWの例（Ubuntu）
sudo ufw allow 8080/tcp
sudo ufw allow 8443/tcp
```

### 4. Let's Encrypt / Certbot

HTTPSポートを変更した場合、Certbot の設定も調整が必要です（標準的な443番以外ではLet's Encryptの検証が複雑になります）。

## 使用例

### 例1: 開発環境でポート競合を回避

別のプロジェクトが 8001番ポートを使用している場合:

```bash
# .env.dev
BACKEND_HOST_PORT=8002
VITE_API_URL=http://localhost:8002
BACKEND_CORS_ORIGINS=["http://localhost:5174","http://localhost:8002"]
```

### 例2: セキュリティ要件で非標準ポートを使用

企業環境で80/443番ポートが制限されている場合:

```bash
# .env.cpu
NGINX_HTTP_PORT=8080
NGINX_HTTPS_PORT=8443
VITE_API_URL=https://your-domain.com:8443
```

### 例3: 複数の環境を同一ホストで起動

開発環境と本番環境を同じマシンで動かす場合:

```bash
# .env.dev
POSTGRES_HOST_PORT=5434
REDIS_HOST_PORT=6380
BACKEND_HOST_PORT=8001
FRONTEND_HOST_PORT=5174

# .env.cpu
NGINX_HTTP_PORT=8080
NGINX_HTTPS_PORT=8443
```

## トラブルシューティング

### ポート競合エラー

```
Error starting userland proxy: listen tcp4 0.0.0.0:8001: bind: address already in use
```

**解決方法**:
1. 使用中のプロセスを確認:
   ```bash
   # macOS/Linux
   lsof -i :8001

   # 使用中のプロセスを停止するか、別のポートを使用
   ```

2. `.env` ファイルでポート番号を変更:
   ```bash
   BACKEND_HOST_PORT=8002
   ```

3. 再起動:
   ```bash
   docker-compose down
   docker-compose up -d
   ```

### フロントエンドがバックエンドに接続できない

**症状**: CORS エラーや接続エラーが発生

**確認事項**:
1. `VITE_API_URL` がバックエンドのホストポートと一致しているか
   ```bash
   # .env.dev
   BACKEND_HOST_PORT=8002
   VITE_API_URL=http://localhost:8002  # ポート番号が一致
   ```

2. CORS設定にフロントエンドのURLが含まれているか
   ```bash
   BACKEND_CORS_ORIGINS=["http://localhost:5174","http://localhost:8002"]
   ```

3. フロントエンドを再ビルド（ビルド時に環境変数が埋め込まれるため）
   ```bash
   docker-compose down
   docker-compose up -d --build
   ```

### 本番環境でSSLが動作しない

非標準ポート（443以外）を使用している場合:

1. Nginx設定を確認
2. ファイアウォールで該当ポートを開放
3. ドメインのDNS設定（SRVレコードなど）が必要な場合がある
4. Let's Encryptの検証が複雑になるため、可能であれば443番を推奨

## 環境変数リファレンス

### 開発環境 (.env.dev)

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `POSTGRES_HOST_PORT` | 5434 | PostgreSQLのホストポート |
| `REDIS_HOST_PORT` | 6380 | Redisのホストポート |
| `BACKEND_HOST_PORT` | 8001 | FastAPIバックエンドのホストポート |
| `FRONTEND_HOST_PORT` | 5174 | Vite開発サーバーのホストポート |

### 本番環境 (.env.cpu / .env.gpu)

| 変数名 | デフォルト値 | 説明 |
|--------|------------|------|
| `NGINX_HTTP_PORT` | 80 | NginxのHTTPホストポート |
| `NGINX_HTTPS_PORT` | 443 | NginxのHTTPSホストポート |

## まとめ

- **開発環境**: 4つのポート設定が可能（PostgreSQL, Redis, Backend, Frontend）
- **本番環境**: 2つのポート設定が可能（Nginx HTTP, HTTPS）
- 環境変数でポートを指定しない場合は、デフォルト値が使用される
- ポート変更時は、`VITE_API_URL` と `BACKEND_CORS_ORIGINS` の更新も忘れずに
- 本番環境では標準ポート（80/443）の使用を推奨（SSL証明書の取得が容易）
