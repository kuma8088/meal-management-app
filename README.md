# 食事管理アプリケーション

AWS サーバレスアーキテクチャを活用した食事管理アプリケーションです。LINE とブラウザの両方からアクセス可能で、食事記録の登録、栄養情報の自動計算、体重目標管理、AI による食事アドバイスを提供します。

## 技術スタック

- **インフラ管理**: Terraform
- **コンピューティング**: AWS Lambda (Python 3.11)
- **API**: AWS API Gateway (REST API)
- **データベース**: Amazon DynamoDB
- **ストレージ**: Amazon S3
- **認証**: Amazon Cognito, LINE LIFF (LINE Front-end Framework)
- **AI**: Amazon Bedrock (Claude 3)
- **CDN**: Amazon CloudFront
- **スケジューラ**: Amazon EventBridge (定期実行タスク)
- **画像認識**: Amazon Rekognition / Amazon Textract
- **メッセージング**: LINE Messaging API
- **ロギング**: Amazon CloudWatch Logs
- **E2Eテスト**: AWS Device Farm (モバイルブラウザテスト)
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
│   ├── cloudfront.tf      # CloudFront CDN定義
│   ├── iam.tf             # IAMロールとポリシー定義
│   ├── api_gateway.tf     # API Gateway定義
│   ├── eventbridge.tf     # EventBridgeスケジュール定義
│   ├── device-farm.tf     # AWS Device Farm設定
│   ├── monitoring.tf      # CloudWatch監視設定
│   └── outputs.tf         # 出力定義
├── src/
│   └── lambda/            # Lambda関数
│       ├── common/        # 共通ライブラリ
│       │   └── auth.py    # 認証ヘルパー（Cognito/LINE両対応）
│       ├── authorizer/    # API Gateway Lambda Authorizer
│       ├── line_handler/  # LINE Webhook Handler
│       ├── meal_registration/  # 食事登録・ユーザー管理
│       ├── food_search/   # 食品検索
│       ├── daily_summary/ # 1日の総評とAIアドバイス
│       ├── goal_management/  # 体重目標管理
│       ├── weekly_report/ # 週次レポート生成
│       ├── food_master_import/  # 食品マスタインポート
│       └── test_user_management/  # テストユーザー管理
├── frontend/              # Reactフロントエンド
│   ├── src/              # ソースコード
│   │   ├── api/          # APIクライアント
│   │   ├── assets/       # 静的アセット
│   │   ├── components/   # UIコンポーネント
│   │   ├── contexts/     # Reactコンテキスト
│   │   │   ├── AuthContext.tsx   # Cognito認証
│   │   │   └── LiffContext.tsx   # LINE LIFF認証
│   │   ├── hooks/        # カスタムフック
│   │   ├── pages/        # ページコンポーネント
│   │   ├── types/        # TypeScript型定義
│   │   └── utils/        # ユーティリティ関数
│   ├── e2e/              # E2Eテスト（Playwright）
│   │   ├── auth.spec.ts           # 認証テスト
│   │   ├── critical-path.spec.ts  # クリティカルパステスト
│   │   ├── food-search.spec.ts    # 食品検索テスト
│   │   ├── goals.spec.ts          # 目標管理テスト
│   │   ├── meal-registration.spec.ts  # 食事登録テスト
│   │   ├── meals.spec.ts          # 食事一覧テスト
│   │   ├── profile.spec.ts        # プロフィールテスト
│   │   └── summary.spec.ts        # サマリーテスト
│   └── package.json      # npm設定
├── tests/                 # Pythonテスト（ユニット/統合/プロパティ）
│   ├── conftest.py       # 共通フィクスチャ
│   └── test_*.py         # テストファイル群
├── scripts/               # ユーティリティスクリプト
├── docs/                  # ドキュメント
│   ├── ARCHITECTURE.md   # アーキテクチャ概要
│   ├── API_SPECIFICATION.md  # API仕様書
│   ├── DEPLOYMENT.md     # デプロイ手順
│   ├── DEVICE_FARM_SETUP.md  # Device Farm設定ガイド
│   └── USER_TEST_GUIDE.md    # ユーザーテストガイド
├── .github/
│   └── workflows/        # GitHub Actions
│       └── device-farm.yml  # Device Farm E2Eテストワークフロー
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
  - **Foods テーブル**: 日本食品標準成分表（2,538品目）と外部API検索結果のキャッシュを保存
- S3 バケット（terraform-state, barcode-images, frontend）
  - 食品マスタは DynamoDB をプライマリ使用（要求ベース課金で効率的）
- Cognito User Pool と User Pool Client
- Lambda 実行用 IAM ロール
  - DynamoDB、S3、Bedrock、Rekognition へのアクセス権限
  - **Lambda 間呼び出し権限**: LINE Handler → Daily Summary 等
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
- `VITE_LIFF_ID`: LINE LIFF アプリケーション ID（LIFF認証使用時）

## LINE Bot アーキテクチャ

LINE Bot は以下の Lambda 関数連携で動作します：

```
LINE App → API Gateway → line_handler → daily_summary (総評機能)
                                      → food_search (食品検索)
```

**重要な設計ポイント:**
- Lambda 関数名は Terraform で動的生成（`${project}-${env}-${name}` 形式）
- 関数名はハードコードせず、環境変数で渡す
- Lambda 間呼び出しには IAM の `lambda:InvokeFunction` 権限が必要

詳細は [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) を参照。

## 認証アーキテクチャ

本アプリケーションは2つの認証方式をサポートしています：

### 1. Cognito 認証（ブラウザアクセス）

```
ブラウザ → CloudFront → React App → Cognito → API Gateway → Lambda
```

- 標準的なメール/パスワード認証
- JWT トークンを `Authorization: Bearer <token>` ヘッダーで送信

### 2. LIFF 認証（LINE アプリ内ブラウザ）

```
LINE App → LIFF → React App → LINE ID Token → API Gateway → Lambda Authorizer → Lambda
```

- LINE Login による認証
- LIFF SDK で取得した ID トークンを使用
- Lambda Authorizer が LINE ID トークンを検証し、user_id を抽出

### 認証の自動切り替え

フロントエンドは実行環境を自動検出し、適切な認証方式を選択します：

- LIFF 環境内: LINE ID トークンを使用
- ブラウザ: Cognito JWT トークンを使用

## ドキュメント

詳細な設計書と要件定義書は `.kiro/specs/meal-management-app/` ディレクトリを参照してください。

- [要件定義書](.kiro/specs/meal-management-app/requirements.md)
- [設計書](.kiro/specs/meal-management-app/design.md)
- [実装計画](.kiro/specs/meal-management-app/tasks.md)
- [アーキテクチャ](docs/ARCHITECTURE.md)
- [デプロイ手順](docs/DEPLOYMENT.md)
- [ユーザーテストガイド](docs/USER_TEST_GUIDE.md)
- [フロントエンド開発ガイド](frontend/README.md)
- [プロジェクトガイド（Claude Code用）](CLAUDE.md)

## ライセンス

MIT License
