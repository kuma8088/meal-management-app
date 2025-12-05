# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## プロジェクト概要

AWS サーバレスアーキテクチャを活用した食事管理アプリケーション。LINE とブラウザの両方からアクセス可能で、食事記録の登録、栄養情報の自動計算、体重目標管理、AI による食事アドバイスを提供する。

**技術スタック:**
- インフラ管理: Terraform
- コンピューティング: AWS Lambda (Python 3.11)
- API: AWS API Gateway (REST API)
- データベース: Amazon DynamoDB
- ストレージ: Amazon S3
- 認証: Amazon Cognito, LINE User ID
- AI: Amazon Bedrock (Claude 3)
- 画像認識: Amazon Rekognition / Amazon Textract
- メッセージング: LINE Messaging API
- フロントエンド: React (TypeScript)

## 主要コマンド

### インフラ管理
```bash
# Terraform初期化
make init

# インフラ変更の確認
make plan

# インフラのデプロイ
make apply

# インフラの削除
make destroy
```

### テスト実行
```bash
# 全テスト実行
make test

# または直接pytest
pytest tests/ -v

# ユニットテストのみ
pytest tests/ -m unit

# 統合テストのみ
pytest tests/ -m integration

# プロパティベーステストのみ
pytest tests/ -m property

# 特定のテストファイルを実行
pytest tests/unit/test_nutrition_calculation.py -v

# カバレッジ付きでテスト実行（pytest.iniで設定済み）
pytest tests/
```

### コード品質
```bash
# コードフォーマット
black src/ tests/

# インポート順序の整理
isort src/ tests/

# Linting
flake8 src/ tests/
pylint src/

# 型チェック
mypy src/

# 一時ファイルのクリーンアップ
make clean
```

### Python依存関係
```bash
# 本番依存関係のインストール
pip install -r requirements.txt

# 開発依存関係のインストール（本番依存関係を含む）
pip install -r requirements-dev.txt
```

### フロントエンド開発

```bash
# frontendディレクトリに移動
cd frontend

# 依存関係のインストール
npm install

# 開発サーバーの起動 (http://localhost:5173)
npm run dev

# プロダクションビルド
npm run build

# E2Eテストの実行
npm run test:e2e              # ヘッドレスモード
npm run test:e2e:ui           # UIモード（インタラクティブ）
npm run test:e2e:headed       # ヘッド付きモード（ブラウザ表示）

# Linting
npm run lint
```

## アーキテクチャの重要ポイント

### Lambda関数の役割分担

各Lambda関数は明確に役割が分離されている:

1. **line_handler**: LINE Webhook処理、適切なハンドラーへの振り分け
2. **meal_registration**: 食事記録の作成とDynamoDB保存
3. **food_search**: 食品マスタ検索（DynamoDB → AI検索のフォールバック）
4. **barcode_recognition**: 画像からJANコード抽出
5. **nutrition_calculation**: 栄養情報の自動計算
6. **bmr_tdee_calculation**: 基礎代謝と総消費カロリーの計算
7. **goal_management**: 体重目標管理と目標カロリー計算
8. **daily_summary_advice**: 1日の食事集計とAIアドバイス生成
9. **user_profile_management**: ユーザープロフィール管理
10. **food_master_import**: 日本食品標準成分表とOpen Food Factsからのデータインポート

### データフロー: AI検索とキャッシング

重要な設計パターン:
1. 食品検索時、まずDynamoDBを検索
2. 見つからない場合、Bedrock Claude がS3の食品マスタCSVを参照してAI検索
3. AI検索結果は `source: "AI_GENERATED"` フラグ付きでDynamoDBにキャッシュ
4. 次回同じ食品の検索時はキャッシュを返し、Bedrock APIコストを削減

### DynamoDB テーブル設計

#### Users テーブル
- PK: user_id
- GSI1: line_user_id → user_id
- GSI2: cognito_user_id → user_id

#### Meals テーブル
- PK: meal_id
- SK: user_id#timestamp
- GSI1: user_id (PK) + timestamp (SK) - ユーザーの食事履歴クエリ用

#### Foods テーブル
- PK: food_id
- GSI1: name (PK) + food_id (SK) - 食品名検索用
- GSI2: jan_code (PK) + food_id (SK) - JAN コード検索用

#### Goals テーブル
- PK: goal_id
- SK: user_id
- GSI1: user_id (PK) + created_at (SK)

#### AdviceUsage テーブル
- PK: user_id#date
- TTL有効（30日後に自動削除）
- 1日2回のAIアドバイス生成制限を管理

### フロントエンドアーキテクチャ

React (TypeScript) + Vite で構築されたSPA:

**ディレクトリ構造:**
- `frontend/src/api/`: APIクライアント（axios）とエンドポイント定義
- `frontend/src/components/`: 再利用可能なUIコンポーネント
- `frontend/src/contexts/`: Reactコンテキスト（AuthContext）
- `frontend/src/pages/`: ページコンポーネント（ルート）
- `frontend/src/types/`: TypeScript型定義
- `frontend/e2e/`: Playwright E2Eテスト

**認証フロー:**
1. AuthContext（`contexts/AuthContext.tsx`）がCognitoセッションを管理
2. ログイン成功時、トークンをlocalStorageに保存
3. APIクライアント（`api/client.tsx`）が自動的にAuthorizationヘッダーを追加
4. 401エラー時、自動ログアウトとログイン画面にリダイレクト

**ルーティング:**
- PrivateRoute: 認証必須のルート（ホームページなど）
- PublicRoute: 未認証のみアクセス可能（ログインページ）

**環境変数（frontend/.env）:**
- `VITE_API_BASE_URL`: API Gateway URL
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito Client ID

### 環境変数

**バックエンド（Terraform変数）:**
- `environment`: dev / staging / prod
- `aws_region`: デフォルト ap-northeast-1
- `line_channel_secret`: LINE Messaging API Channel Secret
- `line_channel_access_token`: LINE Messaging API Channel Access Token

環境ごとに独立したリソースを持つ。

## テスト戦略

### プロパティベーステスト

このプロジェクトでは正確性プロパティを重視している。[design.md](design.md)の「正確性プロパティ」セクションに26個のプロパティが定義されている。

**プロパティテストの作成規約:**
```python
from hypothesis import given, strategies as st

@given(
    foods=st.lists(
        st.tuples(
            st.floats(min_value=0, max_value=1000),  # calories_per_100g
            st.floats(min_value=0, max_value=100),   # amount in grams
        ),
        min_size=1,
        max_size=10
    )
)
def test_nutrition_sum_property(foods):
    """
    Feature: meal-management-app, Property 12: 複数食品の栄養情報合計
    """
    # プロパティの検証コード
    ...
```

各プロパティテストには設計書のプロパティ番号を参照するdocstringを含める。
フォーマット: `Feature: {feature_name}, Property {number}: {property_text}`

### テストマーカー

pytest.iniで定義されているマーカー:
- `@pytest.mark.unit`: ユニットテスト
- `@pytest.mark.integration`: 統合テスト
- `@pytest.mark.property`: プロパティベーステスト
- `@pytest.mark.slow`: 実行に時間がかかるテスト

### カバレッジ目標

ユニットテストのカバレッジ目標: 80%以上

### E2Eテスト（フロントエンド）

Playwrightを使用したE2Eテスト:
- テストファイル: `frontend/e2e/`
- 設定: `frontend/playwright.config.ts`
- 対象ブラウザ: Chromium, Firefox, Webkit
- 自動的に開発サーバーを起動してテスト実行

**テスト実行:**
```bash
cd frontend
npm run test:e2e        # ヘッドレスモード
npm run test:e2e:ui     # UIモード（デバッグに便利）
npm run test:e2e:headed # ブラウザを表示して実行
```

## セキュリティ考慮事項

### 認証フロー
- LINE: LINE User IDでユーザー識別
- ブラウザ: Amazon Cognito + JWTトークン

### データ分離
**プロパティ1（重要）**: ユーザーデータの完全な分離が保証されていること。
任意のユーザーが食事記録を取得する場合、返される記録はすべてそのユーザーのuser_idと関連付けられている必要がある。

### IAMロール
最小権限の原則に従い、各Lambda関数に必要最小限の権限のみを付与。

### シークレット管理
- APIキー、トークンはAWS Secrets Managerに保存
- 環境変数としてLambda関数に注入
- コードにハードコードしない

## エラーハンドリング

### リトライロジック

外部API呼び出しには指数バックオフを使用したリトライを実装:
- Bedrock API: 最大3回
- DynamoDB操作: 最大3回
- S3操作: 最大3回

リトライ非対象:
- バリデーションエラー
- 認証エラー
- 4xx クライアントエラー

### エラーレスポンス形式

```python
{
    "error": {
        "code": str,        # エラーコード
        "message": str,     # ユーザー向けメッセージ
        "details": dict,    # 詳細情報（オプション）
        "request_id": str   # リクエストID
    }
}
```

## BMR/TDEE計算

Harris-Benedict式を使用:
- **男性**: BMR = 88.362 + (13.397 × 体重kg) + (4.799 × 身長cm) - (5.677 × 年齢)
- **女性**: BMR = 447.593 + (9.247 × 体重kg) + (3.098 × 身長cm) - (4.330 × 年齢)

活動係数:
- sedentary: 1.2
- light: 1.375
- moderate: 1.55
- active: 1.725
- very_active: 1.9

TDEE = BMR × 活動係数

## AI アドバイス生成

### 制限事項
- 1日2回まで（AdviceUsageテーブルで管理）
- 300文字以内（超過時は切り詰め）

### コスト最適化
- 食品検索のキャッシング（AI_GENERATEDフラグ）
- 利用回数制限

## コーディング規約

### 共通ライブラリ
`src/lambda/common/` に共通機能を配置:
- `dynamodb_helper.py`: DynamoDB操作
- `s3_helper.py`: S3操作
- `validation.py`: バリデーションロジック
- `error_handling.py`: エラーハンドリング

### Lambda関数の構造
各Lambda関数は独立したディレクトリを持ち、`__init__.py`にハンドラーを実装。

### Lambda関数のパッケージング
`scripts/package_lambda.sh` を使用してLambda関数をZIPファイルにパッケージング:
- 各Lambda関数を `lambda_packages/` にZIP化
- `common/` ライブラリを自動的に含める
- Terraformデプロイ時に使用

### 入力バリデーション
すべてのユーザー入力を検証:
- 型チェック
- 範囲チェック
- 形式チェック
- サニタイゼーション

## ドキュメント

- [requirements.md](.kiro/specs/meal-management-app/requirements.md): 詳細な要件定義書（26の正式な要件を含む）
- [design.md](.kiro/specs/meal-management-app/design.md): 設計書（26個の正確性プロパティを含む）
- [tasks.md](.kiro/specs/meal-management-app/tasks.md): 実装計画
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): アーキテクチャ概要
- [frontend/README.md](frontend/README.md): フロントエンド開発ガイド

## 環境分離

各環境は独立したリソースを持つ:
- **dev**: 開発環境
- **staging**: 本番環境と同等の構成でテスト
- **prod**: 本番環境

Terraform変数 `environment` で環境を切り替え。
