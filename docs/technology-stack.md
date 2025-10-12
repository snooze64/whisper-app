# 技術スタック選定書

## 1. 技術スタック概要

本プロジェクトでは、以下の技術スタックを採用します。

### 1.1 選定方針
- **Python中心のエコシステム**: Whisper、Resemblyzerが公式にPythonをサポート
- **モダンで保守性の高い技術**: 活発にメンテナンスされているライブラリを優先
- **GPU最適化**: CUDA対応のPyTorchを使用
- **スケーラビリティ**: 非同期処理とタスクキューによる拡張性確保
- **コンテナベース**: Dockerによる環境の一貫性確保

---

## 2. バックエンド

### 2.1 Webフレームワーク
**選定: FastAPI**

**理由**:
- 非同期処理(async/await)のネイティブサポート
- 自動APIドキュメント生成(OpenAPI/Swagger)
- 型ヒントによる堅牢性
- 高速なパフォーマンス
- WebSocketサポート（将来のリアルタイム機能に対応可能）

**代替案**:
- Flask: シンプルだが非同期処理が弱い
- Django: 高機能だがオーバースペック

### 2.2 プログラミング言語
**選定: Python 3.11+**

**理由**:
- Whisper、Resemblyzerの公式サポート言語
- 機械学習エコシステムの充実
- CUDA/PyTorchとの親和性が高い
- 豊富なライブラリ

---

## 3. 音声処理

### 3.1 音声認識エンジン
**選定: OpenAI Whisper (faster-whisper)**

- **ライブラリ**: `faster-whisper`
- **モデル**: Large-v3, Large-v3-turbo
- **理由**: CTranslate2ベースの高速実装、メモリ効率が良い

**依存ライブラリ**:
```
faster-whisper==1.0.0
torch==2.1.0+cu118  # CUDA 11.8対応
```

### 3.2 話者分離
**選定: Resemblyzer**

- **ライブラリ**: `resemblyzer`
- **理由**: 軽量で高精度、拡張性を考慮した設計
- **将来の代替候補**: pyannote.audio

### 3.3 音声/動画処理
**選定: FFmpeg + PyAV**

- **FFmpeg**: 音声・動画ファイルの変換、抽出
- **PyAV**: PythonからFFmpegを操作
- **理由**: 幅広いフォーマット対応、高速処理

---

## 4. タスクキュー・非同期処理

### 4.1 タスクキュー
**選定: Celery + Redis**

**理由**:
- Pythonとの統合が容易
- 分散タスクキューの実績が豊富
- タスクの優先度制御、リトライ機能
- Redisによる高速なメッセージブローカー

**設定**:
- タスク結果の保存: Redis
- ワーカー数: GPU数に応じて動的調整
- タスクタイムアウト: 3時間（長時間ファイル対応）

### 4.2 GPUメモリ監視
**選定: pynvml (NVIDIA Management Library)**

**理由**:
- GPUメモリ使用率のリアルタイム監視
- タスクスケジューリングの動的制御

---

## 5. データベース

### 5.1 メインデータベース
**選定: PostgreSQL 15+**

**理由**:
- ACID準拠の高い信頼性
- JSON型サポート（柔軟なデータ保存）
- 処理履歴、ユーザー情報の永続化に最適
- Docker環境での運用が容易

**管理データ**:
- ユーザー情報（LDAP連携）
- 処理履歴
- ファイルメタデータ
- システム設定

### 5.2 ORM
**選定: SQLAlchemy 2.0+**

**理由**:
- 型安全なクエリビルダー
- FastAPIとの親和性が高い
- 非同期処理対応

---

## 6. フロントエンド

### 6.1 フレームワーク
**選定: React 18+ + TypeScript**

**理由**:
- 豊富なエコシステム
- 型安全性（TypeScript）
- コンポーネントベースの再利用性
- 大規模アプリケーションに対応可能

### 6.2 ビルドツール
**選定: Vite**

**理由**:
- 高速な開発サーバー
- HMR（Hot Module Replacement）
- モダンなビルドツール

### 6.3 UIライブラリ
**選定: TailwindCSS + shadcn/ui**

**理由**:
- ユーティリティファーストで開発効率が高い
- カスタマイズ性が高い
- shadcn/uiで美しいコンポーネントを提供

### 6.4 状態管理
**選定: TanStack Query (React Query) + Zustand**

**理由**:
- サーバー状態管理に最適（React Query）
- シンプルなクライアント状態管理（Zustand）
- キャッシュ、リフェッチの自動制御

### 6.5 ファイルアップロード
**選定: react-dropzone**

**理由**:
- ドラッグ&ドロップ対応
- 大容量ファイルのチャンク送信対応
- プログレス表示

---

## 7. 認証・セキュリティ

### 7.1 認証
**選定: python-ldap3 + JWT**

**理由**:
- LDAP認証の実装が容易
- JWT（JSON Web Token）によるステートレス認証
- FastAPIとの統合が容易

**ライブラリ**:
- `ldap3`: LDAP認証
- `python-jose[cryptography]`: JWT生成・検証
- `passlib[bcrypt]`: パスワードハッシュ化（管理者用）

### 7.2 セキュリティ
- **HTTPS**: Nginx + Let's Encrypt
- **CORS**: FastAPI CORSMiddleware
- **Rate Limiting**: SlowAPI

---

## 8. ストレージ

### 8.1 ファイルストレージ
**選定: ローカルファイルシステム + Docker Volume**

**理由**:
- シンプルで運用が容易
- オンプレミス環境に適している
- 24時間後の自動削除が容易

**ディレクトリ構成**:
```
/data/
  ├── uploads/       # アップロードファイル
  ├── results/       # 処理結果
  └── temp/          # 一時ファイル
```

### 8.2 ファイル管理
**選定: APScheduler**

**理由**:
- Pythonネイティブのスケジューラー
- 24時間後の自動削除タスクに最適
- Cronライクな設定が可能

---

## 9. リバースプロキシ・Webサーバー

### 9.1 リバースプロキシ
**選定: Nginx**

**理由**:
- 高速で安定したリバースプロキシ
- 静的ファイル配信
- HTTPS対応
- ファイルアップロードの最適化

**設定**:
- `client_max_body_size`: 1GB
- タイムアウト設定: 600秒

---

## 10. コンテナ・オーケストレーション

### 10.1 コンテナ化
**選定: Docker + Docker Compose**

**理由**:
- 環境の再現性
- 開発・本番環境の一貫性
- GPUサポート（NVIDIA Container Toolkit）

**コンテナ構成**:
```
services:
  - frontend       # React (Nginx)
  - backend        # FastAPI (Uvicorn)
  - celery-worker  # Celeryワーカー
  - redis          # タスクキュー
  - postgres       # データベース
  - nginx          # リバースプロキシ
```

### 10.2 GPUサポート
**選定: NVIDIA Container Toolkit**

**理由**:
- DockerコンテナからGPUを利用可能
- CUDA 11.4/12.4対応

---

## 11. 開発ツール

### 11.1 コード品質
- **Linter (Python)**: Ruff
- **Formatter (Python)**: Black
- **Type Checker (Python)**: mypy
- **Linter (TypeScript)**: ESLint
- **Formatter (TypeScript)**: Prettier

### 11.2 テスト
- **Backend**: pytest, pytest-asyncio
- **Frontend**: Vitest, React Testing Library

### 11.3 バージョン管理
- **Git**: ソースコード管理
- **Git Flow**: ブランチ戦略

---

## 12. モニタリング・ログ

### 12.1 ログ管理
**選定: Python logging + JSON formatter**

**理由**:
- 構造化ログ（JSON形式）
- Dockerログドライバーとの連携
- 集約が容易

### 12.2 メトリクス監視（将来的）
- Prometheus + Grafana
- GPU使用率、タスク処理時間などの可視化

---

## 13. 依存ライブラリ一覧

### 13.1 バックエンド (Python)
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6

# AI/ML
faster-whisper==1.0.0
torch==2.1.0+cu118
torchaudio==2.1.0+cu118
resemblyzer==0.1.1.dev0

# Media Processing
ffmpeg-python==0.2.0
av==11.0.0

# Task Queue
celery==5.3.4
redis==5.0.1

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1

# Authentication
ldap3==2.9.1
python-jose[cryptography]==3.3.0
passlib[bcrypt]==1.7.4

# GPU Monitoring
pynvml==11.5.0

# Utilities
pydantic==2.5.0
pydantic-settings==2.1.0
python-dotenv==1.0.0
apscheduler==3.10.4

# LLM Integration (将来的に追加)
# openai==1.6.0
# httpx==0.25.2  # OpenAI APIコール用

# Testing
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

### 13.2 フロントエンド (Node.js)
```json
{
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "typescript": "^5.3.0",
    "@tanstack/react-query": "^5.12.0",
    "zustand": "^4.4.7",
    "react-router-dom": "^6.20.0",
    "react-dropzone": "^14.2.3",
    "axios": "^1.6.2",
    "tailwindcss": "^3.3.6",
    "@radix-ui/react-*": "latest",
    "lucide-react": "^0.294.0"
  },
  "devDependencies": {
    "vite": "^5.0.0",
    "@vitejs/plugin-react": "^4.2.0",
    "eslint": "^8.55.0",
    "prettier": "^3.1.0",
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.1.0"
  }
}
```

---

## 14. CUDA/PyTorchバージョン対応

### 14.1 CUDA 11.4対応
```
torch==2.1.0+cu118
torchaudio==2.1.0+cu118
```

### 14.2 CUDA 12.4対応
```
torch==2.1.0+cu121
torchaudio==2.1.0+cu121
```

**注意**: Dockerイメージのベースを`nvidia/cuda:11.8.0-cudnn8-runtime-ubuntu22.04`とする

---

## 15. 技術選定の優先順位

### 15.1 必須（MVP）
- ✅ FastAPI
- ✅ faster-whisper
- ✅ Resemblyzer
- ✅ PostgreSQL
- ✅ Celery + Redis
- ✅ React + TypeScript
- ✅ Docker + Docker Compose
- ✅ LDAP認証

### 15.2 推奨
- TailwindCSS + shadcn/ui
- TanStack Query
- Nginx

### 15.3 将来的に追加
- **ChatGPT連携**: OpenAI SDK (openai==1.6.0)、OpenAI互換API対応
- **リアルタイム文字起こし**: WebSocket対応
- **モニタリング**: Prometheus + Grafana
- **ストレージ拡張**: S3互換ストレージ（MinIO）

---

## 16. ChatGPT連携（将来的な拡張）

### 16.1 LLM統合
**選定: OpenAI Python SDK**

**理由**:
- OpenAI、Azure OpenAI、ローカルLLM（Ollama等）の統一的な接続
- 非同期処理対応（AsyncOpenAI）
- ストリーミング、関数呼び出しなどの高度な機能をサポート

**ライブラリ**:
```
openai==1.6.0
httpx==0.25.2  # HTTPクライアント
```

### 16.2 対応API
- **OpenAI API**: GPT-4, GPT-3.5-turbo
- **Azure OpenAI**: 企業向けOpenAI
- **ローカルLLM**: Ollama, LM Studio, text-generation-webui（OpenAI互換エンドポイント）

### 16.3 環境変数
```bash
OPENAI_BASE_URL=https://api.openai.com/v1  # Base URL
OPENAI_API_KEY=sk-xxxxxxxxxxxxxxxx         # API Key
```

### 16.4 機能概要
- プロンプトテンプレート管理（デフォルト + カスタム）
- モデル一覧の動的取得（`{baseurl}/api/models`）
- 議事録要約、アクションアイテム抽出、重要トピックのハイライト
- トークン使用量の記録とコスト管理

---

**文書作成日**: 2025-10-13
**最終更新日**: 2025-10-13
**バージョン**: 1.1
**変更履歴**:
- v1.1 (2025-10-13): ChatGPT連携機能の技術選定を追加
