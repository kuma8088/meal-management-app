# アーキテクチャドキュメント

## プロジェクト構成

```
meal-management-app/
├── terraform/                     # インフラストラクチャコード
│   ├── provider.tf               # AWSプロバイダー設定
│   ├── variables.tf              # 変数定義
│   ├── dynamodb.tf               # DynamoDBテーブル定義
│   ├── s3.tf                     # S3バケット定義
│   ├── cognito.tf                # Cognito User Pool定義
│   ├── cognito_triggers.tf       # Cognito Lambda Triggers定義
│   ├── cloudfront.tf             # CloudFront CDN定義
│   ├── iam.tf                    # IAMロールとポリシー定義
│   ├── api_gateway.tf            # API Gateway定義
│   ├── eventbridge.tf            # EventBridgeスケジュール定義
│   ├── device-farm.tf            # AWS Device Farm設定
│   ├── monitoring.tf             # CloudWatch監視設定
│   ├── outputs.tf                # 出力定義
│   └── terraform.tfvars.example  # 変数設定例
├── src/
│   └── lambda/                   # Lambda関数
│       ├── common/               # 共通ライブラリ
│       │   ├── __init__.py
│       │   ├── dynamodb_helper.py
│       │   ├── auth.py           # 認証ヘルパー（Cognito/LINE両対応）
│       │   ├── validation.py
│       │   └── error_handling.py
│       ├── authorizer/           # API Gateway Lambda Authorizer
│       ├── line_handler/         # LINE Webhook Handler
│       ├── liff_login/           # LIFF → Cognito Custom Auth 開始
│       ├── define_auth_challenge/  # Cognito Custom Auth: チャレンジ定義
│       ├── create_auth_challenge/  # Cognito Custom Auth: チャレンジ生成
│       ├── verify_auth_challenge/  # Cognito Custom Auth: LINE ID Token 検証
│       ├── post_confirmation/    # Cognito: ユーザー作成後処理
│       ├── meal_registration/    # 食事登録・ユーザー管理
│       ├── food_search/          # 食品検索
│       ├── goal_management/      # 目標管理
│       ├── daily_summary/        # 1日の総評とAIアドバイス
│       ├── weekly_report/        # 週次レポート生成（EventBridge起動）
│       ├── food_master_import/   # 食品マスタインポート
│       └── test_user_management/ # テストユーザー管理
├── frontend/                     # Reactフロントエンド
│   ├── src/                     # ソースコード
│   ├── e2e/                     # E2Eテスト（Playwright）
│   └── package.json
├── tests/                        # Pythonテスト
│   ├── __init__.py
│   ├── conftest.py              # 共通フィクスチャ
│   └── test_*.py                # ユニット/統合/プロパティテスト
├── docs/                        # ドキュメント
│   ├── ARCHITECTURE.md          # アーキテクチャ概要
│   ├── API_SPECIFICATION.md     # API仕様書
│   ├── DEPLOYMENT.md            # デプロイ手順
│   └── DEVICE_FARM_SETUP.md     # Device Farm設定ガイド
├── .github/
│   └── workflows/               # GitHub Actions
│       └── device-farm.yml      # Device Farm E2Eテスト
├── .gitignore
├── README.md
├── Makefile
└── pytest.ini                   # pytest設定
```

## DynamoDB テーブル設計

### Users テーブル

- **PK**: user_id
- **GSI1**: line_user_id
- **GSI2**: cognito_user_id

### Meals テーブル

- **PK**: meal_id
- **SK**: user_id_timestamp
- **GSI1**: user_id (PK), timestamp (SK)

### Foods テーブル

- **PK**: food_id
- **GSI1**: name (PK), food_id (SK)
- **GSI2**: jan_code (PK), food_id (SK)

### Goals テーブル

- **PK**: goal_id
- **SK**: user_id
- **GSI1**: user_id (PK), created_at (SK)

### AdviceUsage テーブル

- **PK**: user_id_date
- **TTL**: 有効期限付き（30 日後に自動削除）

## S3 バケット構成

### terraform-state バケット

- Terraform state ファイルの保存
- バージョニング有効
- 暗号化有効

### food-master バケット

- 食品マスタ CSV ファイルのアーカイブ保存（オプション、バックアップ用）
- バージョニング有効
- ライフサイクルポリシー（古いバージョンを Glacier に移動）
- **注**: プライマリキャッシュは DynamoDB を使用（要求ベース課金で効率的）

### barcode-images バケット

- バーコード画像の一時保存
- ライフサイクルポリシー（30 日後に自動削除）

### frontend バケット

- React フロントエンドの静的ホスティング
- 静的ウェブサイトホスティング有効

## 食品検索フロー

食品検索は以下の 2 段階方式で実装:

1. **DynamoDB 検索（プライマリ）**
   - 日本食品標準成分表（2,538品目）
   - `source` フラグ: `japanese_standard`

2. **AI 検索（フォールバック）**
   - DynamoDB で結果が 0 件の場合
   - `AIFoodSearch` クラス（[ai_food_search.py](../src/lambda/common/ai_food_search.py)）
   - Bedrock Claude が S3 の食品マスタ CSV を参照
   - AI 検索結果を DynamoDB にキャッシュ
   - `source` フラグ: `AI_GENERATED`

3. **将来拡張（未実装）**
   - Open Food Facts REST API フォールバック

## 認証・認可

### 認証アーキテクチャ概要

本アプリケーションは **LINE ユーザー** と **ブラウザユーザー** の両方に対応した統合認証基盤を提供します。

```
┌─────────────────────────────────────────────────────────────────────┐
│                        認証フロー                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  【LINE アプリ】                    【ブラウザ】                        │
│       │                                 │                             │
│       ▼                                 ▼                             │
│  ┌─────────┐                      ┌──────────┐                       │
│  │  LIFF   │                      │  Cognito │                       │
│  │  SDK    │                      │ Hosted UI│                       │
│  └────┬────┘                      └────┬─────┘                       │
│       │ LINE ID Token                  │ Email/Password              │
│       ▼                                 ▼                             │
│  ┌─────────────────────────────────────────────────────┐             │
│  │              Cognito User Pool                       │             │
│  │         (Custom Auth Flow / Standard Auth)           │             │
│  └───────────────────────┬─────────────────────────────┘             │
│                          │                                            │
│                          ▼ Cognito JWT                                │
│  ┌─────────────────────────────────────────────────────┐             │
│  │              API Gateway + Lambda Authorizer         │             │
│  └───────────────────────┬─────────────────────────────┘             │
│                          │                                            │
│                          ▼                                            │
│  ┌─────────────────────────────────────────────────────┐             │
│  │                    Lambda Functions                  │             │
│  └─────────────────────────────────────────────────────┘             │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### LINE ID 連携（Cognito Custom Auth Flow）

LINE ユーザーが Cognito の認証基盤を利用できるよう、Custom Authentication Flow を実装しています。

#### 認証シーケンス

```
LINE App          LIFF          API Gateway      Cognito         Lambda Triggers
   │                │                │               │                │
   │  1. LIFF起動   │                │               │                │
   │───────────────>│                │               │                │
   │                │                │               │                │
   │  2. LINE Login │                │               │                │
   │<───────────────│                │               │                │
   │                │                │               │                │
   │  3. ID Token   │                │               │                │
   │───────────────>│                │               │                │
   │                │                │               │                │
   │                │ 4. POST /auth/liff-login       │                │
   │                │───────────────>│               │                │
   │                │                │               │                │
   │                │                │ 5. InitiateAuth (CUSTOM_AUTH)  │
   │                │                │──────────────>│                │
   │                │                │               │                │
   │                │                │               │ 6. DefineAuthChallenge
   │                │                │               │───────────────>│
   │                │                │               │<───────────────│
   │                │                │               │                │
   │                │                │               │ 7. CreateAuthChallenge
   │                │                │               │───────────────>│
   │                │                │               │<───────────────│
   │                │                │               │                │
   │                │                │ 8. RespondToAuthChallenge      │
   │                │                │──────────────>│                │
   │                │                │               │                │
   │                │                │               │ 9. VerifyAuthChallenge
   │                │                │               │───────────────>│
   │                │                │               │  (LINE ID Token検証)
   │                │                │               │<───────────────│
   │                │                │               │                │
   │                │                │ 10. Cognito JWT Token          │
   │                │                │<──────────────│                │
   │                │                │               │                │
   │                │ 11. JWT Token  │               │                │
   │                │<───────────────│               │                │
   │                │                │               │                │
```

#### Lambda Triggers

| Lambda 関数 | 役割 |
|-------------|------|
| `liff_login` | LIFF から呼び出され、Cognito Custom Auth を開始 |
| `define_auth_challenge` | 認証チャレンジの種類を定義 |
| `create_auth_challenge` | チャレンジを生成（LINE ID Token を期待） |
| `verify_auth_challenge` | LINE ID Token を検証し、ユーザーを認証 |
| `post_confirmation` | ユーザー作成後に Users テーブルへ登録 |

#### LINE ID Token 検証

`verify_auth_challenge` Lambda で以下を検証:

1. **署名検証**: LINE の公開鍵（JWKS）で JWT 署名を検証
2. **有効期限**: `exp` クレームをチェック
3. **発行者**: `iss` が `https://access.line.me` であることを確認
4. **Audience**: `aud` が LIFF Channel ID と一致することを確認

### Cognito User Pool

- **ユーザー名属性**: email
- **自動検証**: email
- **パスワードポリシー**:
  - 最小長: 8 文字
  - 大文字、小文字、数字、記号を必須
- **MFA**: オプション（ソフトウェアトークン）
- **アカウント復旧**: メール経由
- **削除保護**: 本番環境で有効
- **カスタム属性**:
  - `custom:line_user_id`: LINE ユーザー ID

### Cognito User Pool Client

- **認証フロー**:
  - USER_PASSWORD_AUTH（ブラウザユーザー）
  - CUSTOM_AUTH（LINE ユーザー）
  - REFRESH_TOKEN_AUTH
  - USER_SRP_AUTH
- **トークン有効期限**:
  - アクセストークン: 60 分
  - ID トークン: 60 分
  - リフレッシュトークン: 30 日
- **OAuth 設定**:
  - フロー: code, implicit
  - スコープ: email, openid, profile

### ユーザー識別

| 認証経路 | ユーザー識別子 | Cognito 属性 |
|----------|---------------|--------------|
| LINE アプリ | LINE User ID | `custom:line_user_id` |
| ブラウザ | Email | `email` |

両方の経路から同じ Cognito User Pool を使用することで、統一された `user_id`（Cognito `sub`）で管理されます。

### IAM ロール

#### Lambda 実行ロール

以下のサービスへのアクセス権限を持つ：

- **CloudWatch Logs**: ログ出力
- **DynamoDB**: 全テーブルへの読み書き
- **S3**: food-master、barcode-images バケットへのアクセス
- **Bedrock**: Claude API の呼び出し
- **Rekognition/Textract**: 画像認識
- **Secrets Manager**: API キーの取得

#### API Gateway CloudWatch ロール

- CloudWatch Logs へのログ出力権限

#### Lambda 間呼び出し権限

LINE Handler から他の Lambda 関数を呼び出すための権限:

- **対象関数**: `${project_name}-${environment}-*` パターンにマッチする全関数
- **アクション**: `lambda:InvokeFunction`
- **用途**: LINE Bot → Daily Summary（総評機能）など

```hcl
# 許可されるリソースパターン
Resource = "arn:aws:lambda:${region}:*:function:${project}-${env}-*"
```

**重要**: Lambda 関数名は Terraform で動的に生成されるため、ハードコードせず環境変数で渡す必要がある。

| 呼び出し元 | 呼び出し先 | 環境変数 |
|------------|------------|----------|
| line_handler | daily_summary | `DAILY_SUMMARY_FUNCTION_NAME` |
| line_handler | food_search | `FOOD_SEARCH_FUNCTION_NAME` |

## セキュリティ設定

- すべての S3 バケットで暗号化を有効化
- DynamoDB テーブルでポイントインタイムリカバリを有効化
- パブリックアクセスブロック設定（frontend バケット以外）
- IAM 最小権限の原則に従ったロール設定
- Cognito User Pool でユーザー存在エラーの防止を有効化
- 本番環境で Cognito 削除保護を有効化

## CloudFront CDN

フロントエンドの配信に CloudFront を使用:

- **オリジン**: S3 frontend バケット
- **SSL/TLS**: AWS Certificate Manager (ACM) 証明書
- **キャッシュ**: 静的アセットのキャッシュ
- **OAI**: Origin Access Identity によるS3直接アクセス防止

## EventBridge スケジュール

定期実行タスクに EventBridge を使用:

### 週次レポート

- **スケジュール**: 毎週日曜 21:00 (JST)
- **対象 Lambda**: `weekly_report`
- **機能**: ユーザーごとの週間栄養摂取サマリーを生成

## E2E テスト環境

### Playwright (ローカル/CI)

- **ブラウザ**: Chromium, Firefox, Webkit
- **実行環境**: GitHub Actions, ローカル開発環境
- **用途**: クロスブラウザ互換性テスト

### AWS Device Farm (オプション)

- **対象**: Android デバイス（実機）のみ
- **用途**: 実機でのレスポンシブ動作確認
- **注意**: Web アプリのため iOS テストは不要（削除済み）

詳細は [DEVICE_FARM_SETUP.md](DEVICE_FARM_SETUP.md) を参照。

## 環境分離

- dev: 開発環境
- staging: ステージング環境
- prod: 本番環境

各環境は独立したリソースを持ち、環境変数で切り替え可能。
