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
- faster-whisper
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
- NVIDIA GPU (CUDA 11.4/12.4)

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

### 開発・運用ドキュメント（作成予定）

- API仕様書
- セットアップガイド
- デプロイガイド
- トラブルシューティング

---

## 🚀 クイックスタート

### 前提条件

- Docker + Docker Compose
- NVIDIA GPU + NVIDIA Container Toolkit
- CUDA 11.4 または 12.4

### セットアップ（開発環境）

```bash
# リポジトリのクローン
git clone https://github.com/snooze64/whisper-app.git
cd whisper-app

# 環境変数の設定
cp backend/.env.example backend/.env
# backend/.env ファイルを編集（必要に応じて）

# 開発用Dockerコンテナのビルドと起動
docker-compose up -d postgres redis backend frontend-dev

# データベースマイグレーション
docker-compose exec backend alembic upgrade head

# アクセス
# フロントエンド: http://localhost:5173
# バックエンドAPI: http://localhost:8000
# API ドキュメント: http://localhost:8000/api/docs
```

### 本番環境デプロイ

詳細は[デプロイガイド](./docs/deployment-guide.md)を参照してください。

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
│   ├── Dockerfile
│   └── requirements.txt
├── frontend/            # React フロントエンド
│   ├── src/
│   │   ├── components/  # コンポーネント
│   │   ├── pages/       # ページ
│   │   ├── hooks/       # カスタムフック
│   │   ├── services/    # API クライアント
│   │   └── stores/      # 状態管理
│   ├── Dockerfile
│   └── package.json
├── nginx/               # Nginx 設定
├── docs/                # ドキュメント
├── docker-compose.yml   # Docker Compose 設定
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
docker-compose exec backend pytest

# フロントエンドテスト
docker-compose exec frontend npm test

# E2Eテスト
docker-compose exec frontend npm run test:e2e
```

---

## 📊 システム要件

### 本番環境

- **OS**: Linux (Ubuntu 22.04推奨)
- **CPU**: 8コア以上
- **メモリ**: 32GB以上
- **GPU**: NVIDIA A100 40GB（実質利用可能メモリ: 20-30GB）
- **ストレージ**: 500GB以上
- **CUDA**: 11.4 または 12.4

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

**最終更新日**: 2025-10-13
**バージョン**: 1.0.0
