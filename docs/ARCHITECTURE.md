# アーキテクチャドキュメント

## プロジェクト構成

```
meal-management-app/
├── .kiro/
│   └── specs/
│       └── meal-management-app/
│           ├── requirements.md    # 要件定義書
│           ├── design.md          # 設計書
│           └── tasks.md           # 実装計画
├── terraform/                     # インフラストラクチャコード
│   ├── provider.tf               # AWSプロバイダー設定
│   ├── variables.tf              # 変数定義
│   ├── dynamodb.tf               # DynamoDBテーブル定義
│   ├── s3.tf                     # S3バケット定義
│   ├── outputs.tf                # 出力定義
│   └── terraform.tfvars.example  # 変数設定例
├── src/
│   └── lambda/                   # Lambda関数
│       ├── common/               # 共通ライブラリ
│       │   ├── __init__.py
│       │   ├── dynamodb_helper.py
│       │   ├── s3_helper.py
│       │   ├── validation.py
│       │   └── error_handling.py
│       ├── line_handler/         # LINE Webhook Handler
│       ├── meal_registration/    # 食事登録
│       ├── food_search/          # 食品検索
│       ├── barcode_recognition/  # バーコード認識
│       ├── nutrition_calculation/ # 栄養計算
│       ├── bmr_tdee_calculation/ # BMR/TDEE計算
│       ├── goal_management/      # 目標管理
│       ├── daily_summary_advice/ # 総評とアドバイス
│       ├── user_profile_management/ # ユーザープロフィール管理
│       └── food_master_import/   # 食品マスタインポート
├── tests/                        # テスト
│   ├── __init__.py
│   ├── conftest.py              # 共通フィクスチャ
│   ├── unit/                    # ユニットテスト
│   ├── integration/             # 統合テスト
│   └── property/                # プロパティベーステスト
├── docs/                        # ドキュメント
│   └── ARCHITECTURE.md
├── .gitignore
├── README.md
├── Makefile
├── requirements.txt             # Python依存関係
├── requirements-dev.txt         # 開発用依存関係
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

- 食品マスタ CSV ファイルの保存
- バージョニング有効
- ライフサイクルポリシー（古いバージョンを Glacier に移動）

### barcode-images バケット

- バーコード画像の一時保存
- ライフサイクルポリシー（30 日後に自動削除）

### frontend バケット

- React フロントエンドの静的ホスティング
- 静的ウェブサイトホスティング有効

## セキュリティ設定

- すべての S3 バケットで暗号化を有効化
- DynamoDB テーブルでポイントインタイムリカバリを有効化
- パブリックアクセスブロック設定（frontend バケット以外）
- IAM 最小権限の原則に従ったロール設定

## 環境分離

- dev: 開発環境
- staging: ステージング環境
- prod: 本番環境

各環境は独立したリソースを持ち、環境変数で切り替え可能。
