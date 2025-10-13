# トラブルシューティングガイド

Whisper App本番環境デプロイメントにおける一般的な問題と解決策。

## 目次

1. [クイック診断](#クイック診断)
2. [サービスの問題](#サービスの問題)
3. [認証の問題](#認証の問題)
4. [ファイルアップロードの問題](#ファイルアップロードの問題)
5. [文字起こしの問題](#文字起こしの問題)
6. [GPUの問題](#gpuの問題)
7. [データベースの問題](#データベースの問題)
8. [ネットワークの問題](#ネットワークの問題)
9. [パフォーマンスの問題](#パフォーマンスの問題)
10. [フロントエンドの問題](#フロントエンドの問題)

## クイック診断

### 全サービスの確認

```bash
# サービスのステータス確認
docker-compose -f docker-compose.prod.yml ps

# エラーログの確認
docker-compose -f docker-compose.prod.yml logs --tail=100 | grep -i error

# リソース使用状況の確認
docker stats

# ディスク容量の確認
df -h
```

### API ヘルスチェック

```bash
# ヘルスエンドポイントのテスト
curl https://yourdomain.com/health

# 期待される結果: {"status": "healthy"}
```

## サービスの問題

### 問題: サービスが起動しない

**症状**:
- `docker-compose up` が失敗する
- コンテナがすぐに終了する
- "Port already in use" エラー

**解決策**:

1. **ポートの競合を確認**:
```bash
# ポートが使用中かどうか確認
lsof -i :80  # HTTP
lsof -i :443 # HTTPS
lsof -i :5432 # PostgreSQL
lsof -i :6379 # Redis

# 必要に応じて競合するプロセスを終了
kill -9 <PID>
```

2. **Docker デーモンの確認**:
```bash
sudo systemctl status docker
sudo systemctl restart docker
```

3. **コンテナの再ビルド**:
```bash
docker-compose -f docker-compose.prod.yml down
docker-compose -f docker-compose.prod.yml up -d --build
```

### 問題: コンテナが再起動を繰り返す

**症状**:
- コンテナのステータスが "Restarting" と表示される
- サービスが不安定

**解決策**:

1. **コンテナログの確認**:
```bash
docker-compose -f docker-compose.prod.yml logs --tail=200 <service_name>
```

2. **環境変数の確認**:
```bash
# .env ファイルが存在し、正しい値が設定されているか確認
cat .env | grep -v PASSWORD | grep -v SECRET
```

3. **メモリ制限の増加** (`docker-compose.prod.yml` 内):
```yaml
services:
  backend:
    deploy:
      resources:
        limits:
          memory: 8G  # 4Gから増加
```

## 認証の問題

### 問題: ログインできない

**症状**:
- "Invalid credentials" エラー
- ログインは成功するがすぐに失敗する

**解決策**:

1. **LDAP接続性の確認**:
```bash
# バックエンドコンテナからLDAP接続をテスト
docker-compose -f docker-compose.prod.yml exec backend ldapsearch \
  -x \
  -H ldap://your-ldap-server:389 \
  -D "cn=admin,dc=example,dc=com" \
  -w "password" \
  -b "dc=example,dc=com"
```

2. **LDAP設定の確認** (`.env` ファイル):
```bash
cat .env | grep LDAP
```

3. **LDAPエラーのバックエンドログ確認**:
```bash
docker-compose -f docker-compose.prod.yml logs backend | grep -i ldap
```

### 問題: 管理者機能が動作しない

**症状**:
- 管理者エンドポイントで "Forbidden" エラー
- 管理者ユーザーが管理者ダッシュボードにアクセスできない

**解決策**:

1. **ユーザーが管理者かどうか確認**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT id, username, is_admin FROM users WHERE username = 'admin_user';"
```

2. **ユーザーを管理者に設定**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "UPDATE users SET is_admin = true WHERE username = 'admin_user';"
```

## ファイルアップロードの問題

### 問題: ファイルアップロードが失敗する

**症状**:
- "413 Payload Too Large" エラー
- アップロードの進行状況が特定のパーセンテージで停止する
- "Unsupported file format" エラー

**解決策**:

1. **ファイルサイズ制限の確認**:
```bash
# .envファイルのMAX_FILE_SIZEを確認
cat .env | grep MAX_FILE_SIZE

# デフォルトは1GB (1073741824バイト)
```

2. **Nginxアップロード制限の確認**:
```bash
# nginx.prod.confのclient_max_body_sizeを確認
grep client_max_body_size nginx/nginx.prod.conf

# MAX_FILE_SIZEより少し大きい値である必要があります（例: 1100M）
```

3. **サポートされているファイル形式か確認**:
```
サポートされているオーディオ: MP3, WAV, M4A, FLAC, OGG
サポートされているビデオ: MP4, AVI, MOV, MKV
```

## 文字起こしの問題

### 問題: 文字起こしが失敗する

**症状**:
- タスクのステータスが "failed" と表示される
- 文字起こし結果が利用できない

**解決策**:

1. **Celeryワーカーログの確認**:
```bash
docker-compose -f docker-compose.prod.yml logs celery-worker --tail=200
```

2. **タスクのエラーメッセージを確認**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT id, filename, status, error_message FROM tasks WHERE status = 'failed' ORDER BY created_at DESC LIMIT 5;"
```

3. **よくあるエラー**:

**エラー: "Out of memory"**
- 解決策: 同時実行タスク数を減らすかGPUメモリを増やす

**エラー: "FFmpeg failed"**
- 解決策: 音声抽出を確認
```bash
docker-compose -f docker-compose.prod.yml exec celery-worker ffmpeg -i /data/uploads/1/file.mp4 -vn -acodec pcm_s16le -ar 16000 /tmp/test.wav
```

### 問題: Transformersバックエンドが動作しない

**症状**:
- ログに "transformers library not available" と表示される
- 実際の文字起こしの代わりにモック文字起こしが表示される
- "Can't instantiate WhisperForConditionalGeneration model under dtype=torch.int8"

**解決策**:

1. **transformersがインストールされているか確認**:
```bash
docker-compose exec celery-worker python -c "import transformers; print(transformers.__version__)"

# インストールされていない場合:
docker-compose exec celery-worker pip install transformers==4.35.2 accelerate==0.24.1 safetensors==0.4.1
```

2. **WHISPER_BACKEND環境変数の確認**:
```bash
docker-compose exec celery-worker printenv | grep WHISPER_BACKEND

# 出力されるべき内容: WHISPER_BACKEND=transformers
```

設定されていない場合、`docker-compose.yml` に追加:
```yaml
celery-worker:
  environment:
    - WHISPER_BACKEND=transformers
```

3. **変更後にcelery-workerを再起動**:
```bash
docker-compose restart celery-worker
```

4. **int8 dtypeエラー（すでに修正済み）**:
このエラーは自動的に処理されます。int8が要求された場合、システムはfloat32にフォールバックします。
ログで次の警告を確認: "int8 dtype not supported for Whisper models, using float32 instead"

5. **transformersバックエンドを手動でテスト**:
```bash
docker-compose exec celery-worker python /tmp/test_transformers.py
```

`/tmp/test_transformers.py` を作成:
```python
import os
os.environ['WHISPER_BACKEND'] = 'transformers'

from app.tasks.transcription_tasks import get_transcriber

transcriber = get_transcriber("tiny", "cpu", "float32")
print(f"Backend type: {type(transcriber).__name__}")
transcriber.load_model()
print("✅ Model loaded successfully")
```

### 問題: CUDA 11.4互換性

**症状**:
- faster-whisperが "CUDA 11.8+ required" で失敗する
- CUDAバージョンに関するCTranslate2エラー

**解決策**:

1. **CUDAバージョンの確認**:
```bash
nvidia-smi | grep "CUDA Version"
```

2. **CUDA 11.4の場合、transformersバックエンドに切り替え**:
```yaml
# docker-compose.yml
celery-worker:
  environment:
    - WHISPER_BACKEND=transformers  # CUDA 11.4に必要
```

3. **CUDA 11.4互換の依存関係をインストール**:
```bash
docker-compose exec celery-worker pip install -r requirements-transformers-cuda114.txt
```

詳細な手順については、[setup-guide.md](./setup-guide.md) の「CUDA 11.4固有のセットアップ」セクションを参照してください。

**パフォーマンスに関する注意**:
- transformersバックエンドはfaster-whisperより2〜4倍遅い
- VRAMを1.5〜2倍多く使用する
- CUDA 11.4が必要な場合のみ使用（faster-whisperにはCUDA 11.8+を推奨）

## GPUの問題

### 問題: GPUが検出されない

**症状**:
- "GPU unavailable" エラー
- タスクがGPUではなくCPUを使用（非常に遅い）

**解決策**:

1. **ホスト上のNVIDIAドライバーを確認**:
```bash
nvidia-smi
```

2. **NVIDIA Container Toolkitのインストール**:
```bash
# Ubuntu/Debian
sudo apt-get update
sudo apt-get install -y nvidia-container-toolkit
sudo systemctl restart docker
```

3. **Docker内でのGPUアクセスをテスト**:
```bash
docker run --rm --gpus all nvidia/cuda:11.8.0-base-ubuntu22.04 nvidia-smi
```

### 問題: GPUメモリ不足

**症状**:
- タスクが "CUDA out of memory" で失敗する
- GPUメモリがフル

**解決策**:

1. **GPUメモリ使用状況の確認**:
```bash
docker-compose -f docker-compose.prod.yml exec celery-worker nvidia-smi
```

2. **同時実行タスク数を減らす**:
```yaml
# docker-compose.prod.yml
services:
  celery-worker:
    command: celery -A app.celery_app worker --loglevel=info --concurrency=1
```

3. **より小さいWhisperモデルを使用**:
- `large-v3-turbo` は約10GBのVRAMを使用
- `large-v3` は約12GBのVRAMを使用

## データベースの問題

### 問題: データベース接続エラー

**症状**:
- "Could not connect to database" エラー
- 接続タイムアウトエラー

**解決策**:

1. **PostgreSQLが実行中か確認**:
```bash
docker-compose -f docker-compose.prod.yml ps postgres
docker-compose -f docker-compose.prod.yml logs postgres
```

2. **DATABASE_URLの確認** (`.env` ファイル):
```bash
cat .env | grep DATABASE_URL
# 次のようになっているべき: postgresql+asyncpg://user:pass@postgres:5432/whisper_prod
```

3. **手動で接続をテスト**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT 1;"
```

### 問題: データベースの動作が遅い

**症状**:
- APIレスポンスが遅い
- クエリタイムアウト

**解決策**:

1. **VACUUMとANALYZEの実行**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "VACUUM ANALYZE;"
```

2. **データベースサイズの確認**:
```bash
docker-compose -f docker-compose.prod.yml exec postgres psql -U whisper_prod -d whisper_prod -c "SELECT pg_size_pretty(pg_database_size('whisper_prod'));"
```

3. **PostgreSQLの再起動**:
```bash
docker-compose -f docker-compose.prod.yml restart postgres
```

## ネットワークの問題

### 問題: アプリケーションにアクセスできない

**症状**:
- https://yourdomain.com を開けない
- 接続タイムアウト

**解決策**:

1. **Nginxが実行中か確認**:
```bash
docker-compose -f docker-compose.prod.yml ps nginx
docker-compose -f docker-compose.prod.yml logs nginx
```

2. **ファイアウォールルールの確認**:
```bash
sudo ufw status
# ポート80と443を許可する必要がある
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
```

3. **DNS解決の確認**:
```bash
nslookup yourdomain.com
dig yourdomain.com
```

### 問題: SSL証明書エラー

**症状**:
- "Certificate not trusted" エラー
- SSLハンドシェイク失敗

**解決策**:

1. **証明書の有効性を確認**:
```bash
echo | openssl s_client -servername yourdomain.com -connect yourdomain.com:443 2>/dev/null | openssl x509 -noout -dates
```

2. **Let's Encrypt証明書の更新**:
```bash
docker-compose -f docker-compose.prod.yml run --rm certbot renew
docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

3. **証明書ファイルが存在するか確認**:
```bash
ls -la certbot/conf/live/yourdomain.com/
```

## パフォーマンスの問題

### 問題: CPU使用率が高い

**症状**:
- サーバーが高温になる
- レスポンス時間が遅い

**解決策**:

1. **CPU使用状況の確認**:
```bash
docker stats
top
```

2. **同時実行タスク数を減らす**:
```yaml
# docker-compose.prod.yml
services:
  celery-worker:
    command: celery -A app.celery_app worker --loglevel=info --concurrency=2
```

### 問題: ディスク容量不足

**症状**:
- "No space left on device" エラー
- パフォーマンスの低下

**解決策**:

1. **ディスク使用状況の確認**:
```bash
df -h
du -sh /data/*
```

2. **クリーンアップサービスを手動で実行**:
```bash
docker-compose -f docker-compose.prod.yml exec cleanup python -m app.scripts.cleanup_files
```

3. **ファイル保持期間を短縮** (`.env` ファイル):
```bash
FILE_RETENTION_HOURS=12  # 24から削減
```

4. **古いDockerイメージとボリュームをクリーンアップ**:
```bash
docker system prune -a --volumes
```

## フロントエンドの問題

### 問題: フロントエンドが読み込まれない

**症状**:
- 空白ページ
- "Cannot GET /" エラー

**解決策**:

1. **Nginxがフロントエンドを提供しているか確認**:
```bash
docker-compose -f docker-compose.prod.yml exec nginx ls -la /usr/share/nginx/html/
```

2. **フロントエンドビルドが存在するか確認**:
```bash
ls -la frontend/dist/
```

3. **フロントエンドの再ビルド**:
```bash
cd frontend
npm install
npm run build
cd ..

# nginxを再起動
docker-compose -f docker-compose.prod.yml restart nginx
```

4. **ブラウザコンソール**でJavaScriptエラーを確認

### 問題: APIリクエストが失敗する（CORS）

**症状**:
- ブラウザコンソールに "CORS error"
- APIリクエストがブロックされる

**解決策**:

1. **CORS設定の確認** (`backend/app/main.py`):
```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://yourdomain.com"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

2. **リクエストが正しいURLに送信されているか確認**:
- フロントエンドは相対パス（`/api/v1/...`）を使用する必要がある

## ヘルプの取得

### 情報収集

問題を報告する前に、以下を収集してください:

1. **システム情報**:
```bash
uname -a
docker --version
nvidia-smi
```

2. **サービスステータス**:
```bash
docker-compose -f docker-compose.prod.yml ps
```

3. **最近のログ**:
```bash
docker-compose -f docker-compose.prod.yml logs --tail=200 > logs.txt
```

### 問題の報告

- **GitHub Issues**: https://github.com/your-org/whisper-app/issues
- **含めるべき情報**: 再現手順、期待される動作と実際の動作、ログ、システム情報

## その他のリソース

- [セットアップガイド](./setup-guide.md)
- [デプロイメントガイド](./deployment-guide.md)
- [API仕様](./api-specification.md)
- [アーキテクチャドキュメント](./architecture.md)

**最終更新日**: 2025-10-13
**フェーズ**: フェーズ9 - デプロイメント準備
