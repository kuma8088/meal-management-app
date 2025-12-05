# 食事管理アプリケーション

AWS サーバレスアーキテクチャを活用した食事管理アプリケーションです。LINE とブラウザの両方からアクセス可能で、食事記録の登録、栄養情報の自動計算、体重目標管理、AI による食事アドバイスを提供します。

## 技術スタック

- **インフラ管理**: Terraform
- **コンピューティング**: AWS Lambda (Python 3.11)
- **API**: AWS API Gateway (REST API)
- **データベース**: Amazon DynamoDB
- **ストレージ**: Amazon S3
- **認証**: Amazon Cognito, LINE User ID
- **AI**: Amazon Bedrock (Claude 3)
- **画像認識**: Amazon Rekognition / Amazon Textract
- **メッセージング**: LINE Messaging API
- **ロギング**: Amazon CloudWatch Logs
- **フロントエンド**: React (TypeScript)

## プロジェクト構成

```
.
├── terraform/              # Terraformインフラ定義
│   ├── provider.tf        # プロバイダー設定
│   ├── variables.tf       # 変数定義
│   ├── dynamodb.tf        # DynamoDBテーブル定義
│   ├── s3.tf              # S3バケット定義
│   ├── cognito.tf         # Cognito User Pool定義
│   ├── iam.tf             # IAMロールとポリシー定義
│   ├── api_gateway.tf     # API Gateway定義
│   ├── monitoring.tf      # CloudWatch監視設定
│   └── outputs.tf         # 出力定義
├── src/
│   └── lambda/            # Lambda関数
│       ├── common/        # 共通ライブラリ
│       ├── line_handler/  # LINE Webhook Handler
│       ├── meal_registration/  # 食事登録
│       ├── food_search/   # 食品検索
│       ├── daily_summary/ # 1日の総評とAIアドバイス
│       └── goal_management/  # 体重目標管理
├── frontend/              # Reactフロントエンド
│   ├── src/              # ソースコード
│   │   ├── api/          # APIクライアント
│   │   ├── components/   # UIコンポーネント
│   │   ├── contexts/     # Reactコンテキスト
│   │   ├── pages/        # ページコンポーネント
│   │   └── types/        # TypeScript型定義
│   ├── e2e/              # E2Eテスト（Playwright）
│   └── package.json      # npm設定
├── tests/                 # Pythonテスト
│   ├── unit/             # ユニットテスト
│   ├── integration/      # 統合テスト
│   └── property/         # プロパティベーステスト
├── scripts/               # ユーティリティスクリプト
└── README.md
```

## セットアップ手順

### 前提条件

- AWS CLI がインストールされ、設定されていること
- Terraform >= 1.0 がインストールされていること
- Python 3.11 がインストールされていること
- Node.js >= 18 がインストールされていること
- AWS アカウントと適切な権限

### 1. リポジトリのクローン

```bash
git clone <repository-url>
cd meal-management-app
```

### 2. Terraform 変数の設定

```bash
cd terraform
cp terraform.tfvars.example terraform.tfvars
# terraform.tfvars を編集して実際の値を設定
```

### 3. Terraform の初期化と適用

```bash
terraform init
terraform plan
terraform apply
```

このステップで以下のリソースが作成されます：

- DynamoDB テーブル（Users, Meals, Foods, Goals, AdviceUsage）
- S3 バケット（terraform-state, food-master, barcode-images, frontend）
- Cognito User Pool と User Pool Client
- Lambda 実行用 IAM ロール（DynamoDB、S3、Bedrock、Rekognition へのアクセス権限付き）
- API Gateway CloudWatch ロール

### 4. Python 依存関係のインストール

```bash
cd ../src/lambda
pip install -r requirements.txt
```

### 5. フロントエンドのセットアップ

```bash
cd ../../frontend
npm install

# 環境変数ファイルを作成
cp .env.example .env
# .env を編集して以下を設定:
# - VITE_API_BASE_URL: API Gateway URL（terraform outputsから取得）
# - VITE_COGNITO_USER_POOL_ID: Cognito User Pool ID（terraform outputsから取得）
# - VITE_COGNITO_CLIENT_ID: Cognito Client ID（terraform outputsから取得）
```

## 開発

### バックエンド開発

#### ローカルテスト

```bash
# ユニットテストの実行
pytest tests/

# プロパティベーステストの実行
pytest tests/ -k property

# 統合テストの実行
pytest tests/ -m integration

# カバレッジ付きでテスト実行
pytest tests/ --cov
```

#### Lambda関数のパッケージング

```bash
# Lambda関数をZIPファイルにパッケージング
bash scripts/package_lambda.sh
```

### フロントエンド開発

```bash
cd frontend

# 開発サーバーの起動（http://localhost:5173）
npm run dev

# プロダクションビルド
npm run build

# E2Eテストの実行
npm run test:e2e              # ヘッドレスモード
npm run test:e2e:ui           # UIモード（インタラクティブ）
npm run test:e2e:headed       # ブラウザを表示して実行

# Linting
npm run lint
```

詳細なフロントエンド開発ガイドは [frontend/README.md](frontend/README.md) を参照してください。

### デプロイ

```bash
cd terraform
terraform apply
```

## 環境変数

### バックエンド（Terraform変数）

`terraform/terraform.tfvars` に設定:

- `environment`: 環境名（dev / staging / prod）
- `aws_region`: AWS リージョン（デフォルト: ap-northeast-1）
- `line_channel_secret`: LINE Messaging API Channel Secret
- `line_channel_access_token`: LINE Messaging API Channel Access Token

### フロントエンド（frontend/.env）

- `VITE_API_BASE_URL`: API Gateway URL
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito Client ID

## ドキュメント

詳細な設計書と要件定義書は `.kiro/specs/meal-management-app/` ディレクトリを参照してください。

- [要件定義書](.kiro/specs/meal-management-app/requirements.md)
- [設計書](.kiro/specs/meal-management-app/design.md)
- [実装計画](.kiro/specs/meal-management-app/tasks.md)
- [フロントエンド開発ガイド](frontend/README.md)
- [プロジェクトガイド（Claude Code用）](CLAUDE.md)

## ライセンス

MIT License
