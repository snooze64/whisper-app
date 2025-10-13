# 音声文字起こしアプリケーション

オンプレミス環境で動作する、OpenAI Whisperを使用した高精度な音声・動画ファイル文字起こしアプリケーションです。

## 📋 概要

本アプリケーションは、企業内でのオンライン会議（Zoom、Microsoft Teams等）の録画ファイルや音声ファイルを、高精度に文字起こしするWebアプリケーションです。話者分離機能により、複数の話者を識別し、タイムスタンプ付きのテキストや字幕ファイルを生成します。

### 主な機能

- 🎙️ **高精度な音声認識**: OpenAI Whisper Large-v3 / Large-v3-turbo
- 👥 **話者分離**: Resemblyzerによる複数話者の識別
- 📝 **テキスト編集**: 文字起こし結果の編集機能
- 📊 **処理履歴管理**: 処理履歴の記録と閲覧
- 🔐 **LDAP認証**: 社内ユーザー認証
- 📈 **管理者ダッシュボード**: 利用統計の可視化
- 🎬 **字幕ファイル生成**: SRT/VTT形式の字幕ファイル出力

### 対応ファイル形式

- 音声: MP3, WAV
- 動画: MP4

### 対応言語

- 日本語（メイン）
- 英語、中国語、韓国語など多言語対応

---

## 🏗️ システム構成

```
┌─────────────┐
│   Browser   │
│   (React)   │
└──────┬──────┘
       │ HTTPS
       ▼
┌─────────────┐
│    Nginx    │
└──────┬──────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│   FastAPI   │◄────►│    Redis    │
└──────┬──────┘      └─────────────┘
       │
       ▼
┌─────────────┐      ┌─────────────┐
│   Celery    │◄────►│ PostgreSQL  │
│  (+ GPU)    │      └─────────────┘
└─────────────┘
```

### 技術スタック

**バックエンド**:
- Python 3.11+
- FastAPI
- Celery + Redis
- faster-whisper / transformers (切り替え可能)
- Resemblyzer
- SQLAlchemy
- PostgreSQL

**フロントエンド**:
- React 18 + TypeScript
- TailwindCSS + shadcn/ui
- TanStack Query
- Vite

**インフラ**:
- Docker + Docker Compose
- Nginx
- NVIDIA GPU (CUDA 11.4+ for transformers / 11.8+ for faster-whisper)

---

## 📚 ドキュメント

詳細なドキュメントは`docs/`ディレクトリに格納されています。

### 設計ドキュメント

| ドキュメント | 説明 |
|------------|------|
| [要件定義書](./docs/requirement.md) | プロジェクトの要件定義 |
| [技術スタック選定書](./docs/technology-stack.md) | 使用技術の選定理由 |
| [システムアーキテクチャ設計書](./docs/architecture.md) | システム全体の設計 |
| [データベース設計書](./docs/database-design.md) | データベーススキーマ設計 |
| [開発計画書](./docs/development-plan.md) | 開発スケジュールとタスク |

### 開発・運用ドキュメント

| ドキュメント | 説明 |
|------------|------|
| [API仕様書](./docs/api-specification.md) | 全APIエンドポイント仕様 |
| [セットアップガイド](./docs/setup-guide.md) | 開発・本番環境セットアップ手順 |
| [デプロイガイド](./docs/deployment-guide.md) | 本番環境デプロイ手順 |
| [トラブルシューティング](./docs/troubleshooting.md) | よくある問題と解決方法 |
| [最適化レポート](./docs/optimization-report.md) | パフォーマンス最適化の詳細 |

### テスト・リリースドキュメント

| ドキュメント | 説明 |
|------------|------|
| [受け入れテストシナリオ](./docs/acceptance-test-scenarios.md) | 88+テストケース |
| [ユーザーマニュアル](./docs/user-manual.md) | エンドユーザー向けマニュアル（日本語） |
| [リリースノート](./docs/release-notes.md) | v1.0.0リリース情報 |
| [CPU本番環境テストレポート](./docs/cpu-production-test-2025-10-13.md) | CPU本番環境E2Eテスト結果 |
| [Playwright E2Eテスト結果](./docs/playwright-e2e-test-2025-10-13.md) | 実音声ファイルでの完全E2Eテスト ✅ |

---

## 🚀 クイックスタート

### 前提条件

**開発環境（MacBook Air等、GPU不要）**:
- Docker + Docker Compose

**本番環境（GPU必須）**:
- Docker + Docker Compose
- NVIDIA GPU + NVIDIA Container Toolkit
- CUDA 11.4+ (transformers backend) または CUDA 11.8+/12.1+ (faster-whisper backend)

### Docker Composeファイルの使い分け

プロジェクトには用途に応じて3つのDocker Composeファイルがあります：

| ファイル | 用途 | 使用方法 |
|---------|------|---------|
| `docker-compose.dev.yml` | **開発環境（CPU）** | `docker-compose -f docker-compose.dev.yml up -d --build` |
| `docker-compose.cpu.yml` | **本番環境（CPU専用サーバー）** | `docker-compose -f docker-compose.cpu.yml up -d --build` |
| `docker-compose.gpu.yml` | **本番環境（GPUサーバー）** | `docker-compose -f docker-compose.gpu.yml up -d --build` |

**開発環境（docker-compose.dev.yml）の特徴**:
- CPU環境（GPU不要、MacなどGPUなし環境）
- ホットリロード対応（コード変更が即座に反映）
- ボリュームマウント有効（ローカルコードをコンテナに直接マウント）
- モック認証有効（LDAP不要）
- ポート: フロントエンド 5174、バックエンド 8001
- Vite開発サーバー（npm run dev）

**本番環境・CPU専用サーバー（docker-compose.cpu.yml）の特徴**:
- CPU環境専用（GPU不要）
- 本番用ビルド（最適化済み静的ファイル）
- SSL/HTTPS対応
- 自動バックアップ
- ファイル自動クリーンアップ
- リソース制限設定

**本番環境・GPUサーバー（docker-compose.gpu.yml）の特徴**:
- GPU必須（CUDA対応サーバー）
- GPU版faster-whisper（高速処理）
- 本番用ビルド（最適化済み静的ファイル）
- SSL/HTTPS対応
- 自動バックアップ
- ファイル自動クリーンアップ
- リソース制限設定

### セットアップ（開発環境）

```bash
# リポジトリのクローン
git clone https://github.com/snooze64/whisper-app.git
cd whisper-app

# 環境変数ファイルの作成
cp .env.dev.example .env.dev
# 必要に応じて.env.devを編集（プロキシ設定など）
# 詳細は docs/setup-guide.md を参照

# 開発環境用Dockerコンテナのビルドと起動
docker-compose -f docker-compose.dev.yml --env-file .env.dev up -d --build

# データベースマイグレーション
docker-compose -f docker-compose.dev.yml exec backend alembic upgrade head

# アクセス
# フロントエンド: http://localhost:5174
# バックエンドAPI: http://localhost:8001
# API ドキュメント: http://localhost:8001/api/docs
```

### ログイン（開発環境）

開発環境ではモック認証が有効になっており、以下のアカウントでログイン可能です：

| ユーザー名 | パスワード | 権限 |
|----------|----------|------|
| admin | admin123 | 管理者 |
| user1 | user123 | 一般ユーザー |

**ログイン手順**:
1. ブラウザで http://localhost:5174 にアクセス
2. ログインページで上記のアカウント情報を入力
3. ログイン成功後、ダッシュボードが表示される

### Whisper Backend選択

本プロジェクトでは、環境に応じて2つのWhisperバックエンドを選択できます：

| バックエンド | CUDA要件 | 処理速度 | VRAM使用量 | 用途 |
|------------|---------|---------|-----------|------|
| **faster-whisper** (デフォルト) | 11.8+ / 12.x | ⚡ 高速 | 少 | 推奨 |
| **transformers** | 11.4+ | 🐌 2-4倍遅い | 1.5-2倍 | CUDA 11.4環境向け |

**切り替え方法**:

`docker-compose.dev.yml`、`docker-compose.cpu.yml`、または `docker-compose.gpu.yml` の `celery-worker` サービスに環境変数を設定：

```yaml
celery-worker:
  environment:
    - WHISPER_BACKEND=faster-whisper  # デフォルト（推奨）
    # または
    - WHISPER_BACKEND=transformers    # CUDA 11.4環境向け
```

**CUDA 11.4環境での注意**:
- faster-whisperはCUDA 11.8以上が必要
- CUDA 11.4環境では必ず `WHISPER_BACKEND=transformers` を設定
- 詳細は[技術スタック選定書](./docs/technology-stack.md)の Section 14.3を参照

### トラブルシューティング

問題が発生した場合は、[トラブルシューティングガイド](./docs/troubleshooting.md)を参照してください。

主な解決方法：
- ポート競合エラー → ポート番号を変更
- GPU/CUDA関連エラー → 開発用Dockerfileを使用
- CORS設定エラー → 環境変数の修正

### セットアップ（本番環境）

本番環境では、サーバーのGPU有無に応じて適切なDocker Composeファイルを選択します：

**本番環境（GPUサーバー）**:

```bash
# 環境変数ファイルの作成と編集
cp .env.gpu.example .env.gpu
nano .env.gpu  # 本番用の設定に変更
# - CHANGE_MEの値を全て実際の値に置き換え
# - データベース認証情報（POSTGRES_USER, POSTGRES_PASSWORD）
# - 強力なSECRET_KEY（例: openssl rand -hex 32）
# - LDAP設定（LDAP_SERVER, LDAP_BASE_DN等）
# - ドメイン名とSSL設定（DOMAIN_NAME, SSL_EMAIL）
# - GPU設定（CUDA_VISIBLE_DEVICES, GPU_MEMORY_THRESHOLD_MB）
# - Whisperバックエンド選択（WHISPER_BACKEND）
# - プロキシ設定（必要な場合）
# 詳細は docs/deployment-guide.md を参照

# フロントエンドのビルド
./scripts/build-frontend.sh

# GPU環境用Dockerコンテナのビルドと起動
docker-compose -f docker-compose.gpu.yml --env-file .env.gpu up -d --build

# データベースマイグレーション
docker-compose -f docker-compose.gpu.yml exec backend alembic upgrade head

# ログ確認
docker-compose -f docker-compose.gpu.yml logs -f
```

**本番環境（CPU専用サーバー）**:

GPU非搭載サーバーでの本番デプロイには `docker-compose.cpu.yml` を使用します：

```bash
# 環境変数ファイルの作成と編集
cp .env.cpu.example .env.cpu
nano .env.cpu  # 本番用の設定に変更
# - CHANGE_MEの値を全て実際の値に置き換え
# - データベース認証情報（POSTGRES_USER, POSTGRES_PASSWORD）
# - 強力なSECRET_KEY（例: openssl rand -hex 32）
# - LDAP設定（LDAP_SERVER, LDAP_BASE_DN等）
# - ドメイン名とSSL設定（DOMAIN_NAME, SSL_EMAIL）
# - Whisperバックエンド選択（WHISPER_BACKEND）
# - プロキシ設定（必要な場合）
# 詳細は docs/deployment-guide.md を参照

# フロントエンドのビルド
./scripts/build-frontend.sh

# CPU専用環境用Dockerコンテナのビルドと起動
docker-compose -f docker-compose.cpu.yml --env-file .env.cpu up -d --build

# データベースマイグレーション
docker-compose -f docker-compose.cpu.yml exec backend alembic upgrade head

# ログ確認
docker-compose -f docker-compose.cpu.yml logs -f
```

詳細な本番環境セットアップ手順は[デプロイガイド](./docs/deployment-guide.md)を参照してください。

---

## 🛠️ 開発

### ディレクトリ構造

```
whisper-app/
├── backend/              # FastAPI バックエンド
│   ├── app/
│   │   ├── api/         # API エンドポイント
│   │   ├── core/        # コア機能（認証、設定）
│   │   ├── models/      # データベースモデル
│   │   ├── schemas/     # Pydantic スキーマ
│   │   ├── services/    # ビジネスロジック
│   │   └── tasks/       # Celery タスク
│   ├── tests/           # テスト
│   ├── Dockerfile.gpu   # 本番環境用（GPU対応）
│   ├── Dockerfile.cpu   # 本番環境・開発環境用（CPU専用）
│   ├── requirements.txt # GPU版（faster-whisper）
│   ├── requirements-dev.txt  # CPU版
│   └── requirements-transformers-cuda114.txt  # CUDA 11.4用（transformers）
├── frontend/            # React フロントエンド
│   ├── src/
│   │   ├── components/  # コンポーネント
│   │   ├── pages/       # ページ
│   │   ├── hooks/       # カスタムフック
│   │   ├── services/    # API クライアント
│   │   └── stores/      # 状態管理
│   ├── Dockerfile.dev   # 開発用（Vite dev server）
│   ├── Dockerfile.cpu   # 本番ビルド用（CPU環境）
│   ├── Dockerfile.gpu   # 本番ビルド用（GPU環境）
│   └── package.json
├── nginx/               # Nginx 設定
├── docs/                # ドキュメント
│   ├── requirement.md
│   ├── architecture.md
│   ├── database-design.md
│   ├── development-plan.md
│   └── troubleshooting.md
├── docker-compose.dev.yml  # Docker Compose 設定（開発環境・CPU）
├── docker-compose.cpu.yml  # Docker Compose 設定（本番環境・CPU専用サーバー）
├── docker-compose.gpu.yml  # Docker Compose 設定（本番環境・GPUサーバー）
└── README.md
```

### 開発フロー

1. `feature/{機能名}` ブランチを作成
2. 機能開発 + テスト作成
3. プルリクエスト作成
4. コードレビュー
5. `develop` ブランチへマージ

詳細は[開発計画書](./docs/development-plan.md)を参照してください。

### テスト

```bash
# バックエンドテスト
docker-compose -f docker-compose.dev.yml exec backend pytest

# フロントエンドテスト
docker-compose -f docker-compose.dev.yml exec frontend-dev npm test

# E2Eテスト
docker-compose -f docker-compose.dev.yml exec frontend-dev npm run test:e2e
```

---

## 📊 システム要件

### 本番環境

- **OS**: Linux (Ubuntu 22.04推奨)
- **CPU**: 8コア以上
- **メモリ**: 32GB以上
- **GPU**: NVIDIA A100 40GB（実質利用可能メモリ: 20-30GB）
- **ストレージ**: 500GB以上
- **CUDA**: 11.4+ (transformers) または 11.8+/12.1+ (faster-whisper推奨)

### 性能目標

- 処理速度: 1時間の音声ファイルを15分以内で処理
- 同時接続ユーザー数: 最大20ユーザー
- ファイルサイズ上限: 1GB

---

## 🔐 セキュリティ

- **認証**: LDAP認証 + JWT
- **通信**: HTTPS
- **データ保護**: アップロードファイルと処理結果は24時間後に自動削除
- **アクセス制御**: ユーザーは自分のタスクのみアクセス可能

---

## 📄 ライセンス

（ライセンス情報を記載）

---

## 🤝 コントリビューション

（コントリビューションガイドラインを記載）

---

## 📧 お問い合わせ

（お問い合わせ先を記載）

---

## 📝 プロジェクト進捗

| Phase | ステータス | 完了日 |
|-------|----------|--------|
| Phase 1: 環境構築・基盤実装 | ✅ 完了 | 2025-10-13 |
| Phase 2: 認証・ユーザー管理 | ✅ 完了 | 2025-10-13 |
| Phase 3: ファイルアップロード機能 | ✅ 完了 | 2025-10-13 |
| Phase 4: Whisper文字起こし機能 | ✅ 完了 | 2025-10-13 |
| Phase 5: 話者分離機能 (Resemblyzer) | ✅ 完了 | 2025-10-13 |
| Phase 6: 結果表示・編集機能 | ✅ 完了 | 2025-10-13 |
| Phase 7: 処理履歴・管理機能 | ✅ 完了 | 2025-10-13 |
| Phase 8: テスト・最適化 | ✅ 完了 | 2025-10-13 |
| Phase 9: デプロイ準備・本番環境構築 | ✅ 完了 | 2025-10-13 |
| Phase 10: 受け入れテスト・リリース | 🚧 進行中 | - |

**Phase 10進捗**:
- ✅ ドキュメント作成完了（受け入れテストシナリオ、ユーザーマニュアル、リリースノート）
- 📋 本番環境での受け入れテスト実施待ち

詳細は[開発計画書](./docs/development-plan.md)を参照してください。

### 主な実装済み機能

**Phase 1-6**: コア機能
- FastAPI + React基盤、LDAP認証、ファイルアップロード
- Whisper文字起こし（Large-v3/Large-v3-turbo）
- 話者分離（Resemblyzer）、結果表示・編集、字幕生成（SRT/VTT）

**Phase 7**: 管理機能
- 処理履歴一覧・詳細、ユーザー統計
- 管理者ダッシュボード（システムステータス、統計グラフ）

**Phase 8**: テスト・最適化
- バックエンド単体テスト: 57テスト全合格（100%）
- フロントエンド単体テスト: 30テスト全合格（100%）
- データベースクエリ最適化（複合インデックス）
- Redisキャッシュ実装（管理者ダッシュボード統計）
- フロントエンドバンドル最適化（React.lazy、初回ロード29%削減）

**Phase 9**: デプロイ準備
- 本番環境Docker設定（GPU対応、SSL/TLS）
- 自動バックアップ・ファイルクリーンアップ
- Nginxセキュリティ設定（HSTS、CSP、レート制限）
- 包括的ドキュメント（セットアップ、デプロイ、API、トラブルシューティング）

**追加実装**: Transformers Backend
- CUDA 11.4対応のtransformersバックエンド実装
- faster-whisperとの切り替え可能なデュアルバックエンド構成
- 環境変数 `WHISPER_BACKEND` で選択可能

### 重要な技術的注意事項

**Whisper Backend選択**:
- **faster-whisper**（推奨）: CUDA 11.8+/12.x、高速、低VRAM
- **transformers**: CUDA 11.4+、2-4倍遅い、VRAM 1.5-2倍

**Resemblyzer依存関係**:
- `numpy==1.23.5` 必須（1.24+は非互換）
- `librosa==0.9.1` 必須（0.10+は非互換）

詳細は[技術スタック選定書](./docs/technology-stack.md)、[リリースノート](./docs/release-notes.md)を参照してください。

---

**最終更新日**: 2025-10-13
**バージョン**: 1.0.0
