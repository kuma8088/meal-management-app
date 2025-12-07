# AWS ポートフォリオ強化 - 実装計画書

## 📋 プロジェクト概要

**目的**: 食事管理アプリケーションをAWSポートフォリオとして価値を高める

**主要タスク**:
1. 週次レポート機能の実装（Lambda + EventBridge）
2. AWS Device Farm への E2E テスト移行
3. Next.js へのフロントエンド移行

**実施順序**: タスク1 → タスク2 → タスク3

---

## タスク1: 週次レポート機能実装（優先度：最高）

### 1.1 概要

**目標**: ユーザーに週次の食事レポートをLINEで自動配信

**機能要件**:
- 毎週日曜日 20:00 JST に自動実行
- 過去7日間の食事データを集計
- Bedrock Claude API で週次アドバイス生成
- LINE Push Message で配信
- ユーザー設定で配信ON/OFF可能（優先実装、難しければ全ユーザー対象）

**技術スタック**:
- AWS Lambda (Python 3.11)
- Amazon EventBridge Scheduler
- Amazon Bedrock (Claude 3)
- LINE Messaging API
- Amazon DynamoDB

### 1.2 設計

#### 1.2.1 アーキテクチャ

```
EventBridge Scheduler (毎週日曜 20:00 JST)
    ↓
Lambda: weekly_report
    ↓
DynamoDB (Users, Meals, Goals)
    ↓
週次集計計算
    ↓
Bedrock Claude API (週次アドバイス生成)
    ↓
LINE Messaging API (Push Message)
```

#### 1.2.2 データフロー

1. **ユーザー取得**
   - Users テーブルから全アクティブユーザーを取得
   - `weekly_report_enabled` フラグで配信対象を絞り込み（オプション）

2. **週次集計**
   - 各ユーザーの過去7日間の食事データを取得（GSI1使用）
   - 以下を計算:
     - 日平均カロリー摂取量
     - 日平均PFC (タンパク質・脂質・炭水化物)
     - 目標達成日数
     - 最も多い食事タイプ

3. **アドバイス生成**
   - Bedrock Claude API に集計データを渡す
   - プロンプト: 週次レポート形式（300文字以内）
   - 目標達成率、改善点、励まし

4. **配信**
   - LINE Push Message API で送信
   - Flex Message でリッチ表示（オプション）

#### 1.2.3 データベーススキーマ拡張（オプション）

**Users テーブルに属性追加**:
```python
{
  "user_id": "xxx",
  "weekly_report_enabled": true,  # 週次レポート配信ON/OFF
  "report_delivery_time": "20:00" # 配信時刻（将来拡張用）
}
```

**WeeklyReports テーブル（履歴保存用・オプション）**:
```python
{
  "report_id": "xxx",
  "user_id": "xxx",
  "week_start_date": "2025-01-06",
  "week_end_date": "2025-01-12",
  "avg_daily_calories": 2100.5,
  "avg_daily_protein": 85.2,
  "avg_daily_fat": 70.3,
  "avg_daily_carbs": 250.0,
  "target_achievement_days": 5,
  "advice": "今週は5日間目標を達成...",
  "created_at": "2025-01-12T20:00:00Z"
}
```

### 1.3 実装ステップ

#### Phase 1: Lambda 関数実装（4-6時間）

**ファイル**: `src/lambda/weekly_report/__init__.py`

```python
def lambda_handler(event, context):
    """週次レポート生成・配信"""
    # 1. ユーザー一覧取得
    users = get_active_users()

    # 2. 各ユーザーの週次レポート生成
    for user in users:
        if not user.get('weekly_report_enabled', True):
            continue  # 配信無効ならスキップ

        # 3. 週次集計
        weekly_stats = aggregate_weekly_data(user['user_id'])

        # 4. アドバイス生成
        advice = generate_weekly_advice(weekly_stats)

        # 5. LINE配信
        send_line_push_message(user['line_user_id'], weekly_stats, advice)

        # 6. レポート履歴保存（オプション）
        save_weekly_report(user['user_id'], weekly_stats, advice)
```

**再利用コード**:
- `src/lambda/daily_summary/__init__.py` の集計ロジック
- `src/lambda/common/dynamodb_helper.py` の DynamoDB 操作

**新規実装**:
- `aggregate_weekly_data()` - 7日分のデータ集計
- `generate_weekly_advice()` - Bedrock API 呼び出し
- `send_line_push_message()` - LINE Push API 呼び出し

#### Phase 2: EventBridge スケジュール設定（2-3時間）

**ファイル**: `terraform/eventbridge.tf`

```hcl
# EventBridge Scheduler ルール（毎週日曜 11:00 UTC = 20:00 JST）
resource "aws_cloudwatch_event_rule" "weekly_report_schedule" {
  name                = "${var.project_name}-weekly-report-${var.environment}"
  description         = "週次レポート自動生成（毎週日曜 20:00 JST）"
  schedule_expression = "cron(0 11 ? * SUN *)"  # UTC時間

  tags = {
    Name = "${var.project_name}-weekly-report-schedule-${var.environment}"
  }
}

# Lambda トリガー設定
resource "aws_cloudwatch_event_target" "weekly_report_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly_report_schedule.name
  target_id = "WeeklyReportLambda"
  arn       = aws_lambda_function.weekly_report.arn
}

# Lambda 実行権限
resource "aws_lambda_permission" "allow_eventbridge" {
  statement_id  = "AllowExecutionFromEventBridge"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.weekly_report.function_name
  principal     = "events.amazonaws.com"
  source_arn    = aws_cloudwatch_event_rule.weekly_report_schedule.arn
}
```

#### Phase 3: Lambda リソース定義（2-3時間）

**ファイル**: `terraform/lambda_weekly_report.tf`

```hcl
resource "aws_lambda_function" "weekly_report" {
  function_name = "${var.project_name}-weekly-report-${var.environment}"
  handler       = "weekly_report.lambda_handler"
  runtime       = "python3.11"
  role          = aws_iam_role.lambda_execution_role.arn
  timeout       = 300  # 5分（ユーザー数増加を考慮）
  memory_size   = 512

  filename         = "${path.module}/../dist/weekly_report.zip"
  source_code_hash = filebase64sha256("${path.module}/../dist/weekly_report.zip")

  environment {
    variables = {
      MEALS_TABLE_NAME            = aws_dynamodb_table.meals.name
      USERS_TABLE_NAME            = aws_dynamodb_table.users.name
      GOALS_TABLE_NAME            = aws_dynamodb_table.goals.name
      LINE_CHANNEL_ACCESS_TOKEN   = var.line_channel_access_token
      BEDROCK_MODEL_ID            = "anthropic.claude-3-haiku-20240307-v1:0"
      AWS_REGION                  = var.aws_region
    }
  }

  tags = {
    Name = "${var.project_name}-weekly-report-${var.environment}"
  }
}
```

#### Phase 4: IAM ポリシー追加（1-2時間）

**ファイル**: `terraform/iam.tf` に追加

```hcl
# Bedrock 実行権限（既存の場合はスキップ）
resource "aws_iam_role_policy" "lambda_bedrock" {
  name = "${var.project_name}-lambda-bedrock-${var.environment}"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = "arn:aws:bedrock:${var.aws_region}::foundation-model/anthropic.claude-3-haiku-20240307-v1:0"
      }
    ]
  })
}
```

#### Phase 5: LINE Push Message 実装（3-4時間）

**ファイル**: `src/lambda/common/line_client.py`（新規または拡張）

```python
import json
import urllib.request

LINE_PUSH_API_URL = "https://api.line.me/v2/bot/message/push"

def send_push_message(line_user_id: str, messages: list):
    """LINE Push Message 送信"""
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {LINE_CHANNEL_ACCESS_TOKEN}"
    }

    data = {
        "to": line_user_id,
        "messages": messages
    }

    req = urllib.request.Request(
        LINE_PUSH_API_URL,
        data=json.dumps(data).encode(),
        headers=headers,
        method="POST"
    )

    with urllib.request.urlopen(req) as response:
        return response.read()

def format_weekly_report_message(stats: dict, advice: str) -> list:
    """週次レポートメッセージのフォーマット"""
    return [
        {
            "type": "text",
            "text": f"""📊 今週の食事レポート（{stats['week_start']} 〜 {stats['week_end']}）

平均カロリー: {stats['avg_calories']:.0f} kcal/日
平均タンパク質: {stats['avg_protein']:.1f} g/日
平均脂質: {stats['avg_fat']:.1f} g/日
平均炭水化物: {stats['avg_carbs']:.1f} g/日

目標達成: {stats['achievement_days']}/7日 🎯

💡 アドバイス:
{advice}"""
        }
    ]
```

#### Phase 6: テスト実装（4-6時間）

**ファイル**: `tests/unit/test_weekly_report.py`

```python
def test_aggregate_weekly_data():
    """週次集計の正確性テスト"""
    # 7日分のテストデータ作成
    # 集計結果の検証

def test_weekly_advice_generation():
    """週次アドバイス生成テスト"""
    # Bedrock API のモック
    # アドバイス文字数制限の検証

def test_line_push_message():
    """LINE配信テスト"""
    # LINE API のモック
    # エラーハンドリングの検証
```

**ファイル**: `tests/property/test_weekly_aggregation.py`

```python
from hypothesis import given, strategies as st

@given(
    daily_calories=st.lists(
        st.floats(min_value=0, max_value=5000),
        min_size=7,
        max_size=7
    )
)
def test_weekly_average_property(daily_calories):
    """週次平均計算のプロパティテスト"""
    avg = sum(daily_calories) / 7
    result = calculate_weekly_average(daily_calories)
    assert abs(result - avg) < 0.01
```

#### Phase 7: デプロイと検証（2-3時間）

1. Lambda パッケージング
   ```bash
   ./scripts/package_lambda.sh
   ```

2. Terraform デプロイ
   ```bash
   cd terraform
   terraform plan
   terraform apply
   ```

3. 手動テスト実行
   ```bash
   aws lambda invoke \
     --function-name meal-management-app-weekly-report-dev \
     --payload '{}' \
     /tmp/response.json
   ```

4. CloudWatch Logs 確認

5. LINE 配信確認

### 1.4 変更ファイル一覧

#### 新規作成
```
src/lambda/weekly_report/
├── __init__.py                             # Lambda ハンドラー

src/lambda/common/
└── line_client.py                          # LINE Push Message クライアント（新規 or 拡張）

terraform/
├── eventbridge.tf                          # EventBridge スケジュール
└── lambda_weekly_report.tf                 # Lambda リソース定義

tests/unit/
└── test_weekly_report.py                   # ユニットテスト

tests/property/
└── test_weekly_aggregation.py              # プロパティテスト

scripts/
└── package_lambda.sh                       # weekly_report を追加（修正）
```

#### 修正
```
terraform/iam.tf                            # Bedrock 権限追加（必要に応じて）
terraform/dynamodb.tf                       # Users テーブルに属性追加（オプション）
```

### 1.5 リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| Lambda タイムアウト（ユーザー数増加） | 高 | タイムアウト5分、将来はStep Functionsへ移行 |
| Bedrock API コスト超過 | 中 | 月間利用上限設定、キャッシング検討 |
| LINE配信失敗 | 中 | リトライロジック、DLQでエラー通知 |
| 週次集計の計算誤差 | 高 | プロパティテストで担保 |

### 1.6 工数見積もり

| Phase | 工数 |
|-------|------|
| Phase 1: Lambda 実装 | 4-6時間 |
| Phase 2: EventBridge | 2-3時間 |
| Phase 3: Lambda リソース | 2-3時間 |
| Phase 4: IAM ポリシー | 1-2時間 |
| Phase 5: LINE 実装 | 3-4時間 |
| Phase 6: テスト | 4-6時間 |
| Phase 7: デプロイ | 2-3時間 |

**合計: 18-27時間（約2-3日間）**

---

## タスク2: AWS Device Farm E2E テスト移行（優先度：中）

### 2.1 概要

**目標**: Playwright E2Eテストを AWS Device Farm で実行（コスト極小化）

**対象テスト**: クリティカルパスのみ（約20テストケース）
- 認証（ログイン・サインアップ）
- プロフィール設定
- 目標設定
- 食事登録
- 総評表示

**技術スタック**:
- AWS Device Farm
- Playwright (WebDriver Protocol)
- S3 + CloudFront（テスト環境ホスティング）
- Cognito（テストユーザー管理）

### 2.2 設計

#### 2.2.1 アーキテクトャ

```
GitHub Actions (トリガー: PR作成時)
    ↓
1. フロントエンドビルド
    ↓
2. S3 にデプロイ
    ↓
3. Cognito テストユーザー作成（Lambda）
    ↓
4. Device Farm テスト実行
    ↓
5. テスト結果を S3 保存
    ↓
6. GitHub PR にコメント
```

#### 2.2.2 テスト環境

**オプション: S3 + CloudFront 静的ホスティング（推奨）**
- フロントエンドを S3 にビルド・デプロイ
- CloudFront で配信
- テストURL: `https://d1234567890.cloudfront.net`
- コスト: 最小限（S3ストレージ + CloudFront転送量）

#### 2.2.3 認証フロー

**Lambda: test_user_management**
- Cognito Admin SDK でテストユーザーを作成
- パスワード永続化
- Device Farm の Pre-test フェーズで実行

### 2.3 実装ステップ

#### Phase 1: Device Farm 環境構築（2-3時間）

1. AWS Device Farm プロジェクト作成
   ```bash
   aws devicefarm create-project \
     --name "meal-management-app-e2e-tests"
   ```

2. Terraform リソース定義
   ```hcl
   # terraform/device_farm.tf
   resource "aws_devicefarm_project" "main" {
     name = "${var.project_name}-e2e-tests-${var.environment}"
   }
   ```

#### Phase 2: テスト環境ホスティング（4-6時間）

**ファイル**: `terraform/s3_test_hosting.tf`

```hcl
# S3 バケット（テスト環境用）
resource "aws_s3_bucket" "test_hosting" {
  bucket = "${var.project_name}-test-hosting-${var.environment}"
}

# CloudFront ディストリビューション
resource "aws_cloudfront_distribution" "test" {
  origin {
    domain_name = aws_s3_bucket.test_hosting.bucket_regional_domain_name
    origin_id   = "S3-${aws_s3_bucket.test_hosting.id}"
  }

  enabled             = true
  default_root_object = "index.html"

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-${aws_s3_bucket.test_hosting.id}"

    forwarded_values {
      query_string = false
      cookies {
        forward = "none"
      }
    }

    viewer_protocol_policy = "redirect-to-https"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }
}
```

#### Phase 3: クリティカルパステスト選定（3-4時間）

**選定基準**: 主要ユーザーフローをカバー

**ファイル**: `frontend/devicefarm/tests/critical-path.spec.ts`

```typescript
// 認証フロー（5テスト）
test('ログイン成功', async ({ page }) => { ... });
test('パスワード不一致エラー', async ({ page }) => { ... });
test('ユーザー登録成功', async ({ page }) => { ... });
test('確認コード入力', async ({ page }) => { ... });
test('ログアウト', async ({ page }) => { ... });

// プロフィール設定（3テスト）
test('プロフィール表示', async ({ page }) => { ... });
test('BMR/TDEE計算', async ({ page }) => { ... });
test('プロフィール更新', async ({ page }) => { ... });

// 目標設定（3テスト）
test('目標設定フォーム表示', async ({ page }) => { ... });
test('減量目標設定', async ({ page }) => { ... });
test('目標体重バリデーション', async ({ page }) => { ... });

// 食事登録（5テスト）
test('食事登録ページ表示', async ({ page }) => { ... });
test('食品検索', async ({ page }) => { ... });
test('食品追加', async ({ page }) => { ... });
test('栄養情報計算', async ({ page }) => { ... });
test('食事登録完了', async ({ page }) => { ... });

// 総評（4テスト）
test('総評ページ表示', async ({ page }) => { ... });
test('日付選択', async ({ page }) => { ... });
test('栄養サマリー表示', async ({ page }) => { ... });
test('AIアドバイス表示', async ({ page }) => { ... });
```

**合計: 20テストケース**

#### Phase 4: Device Farm YAML 設定（3-4時間）

**ファイル**: `frontend/devicefarm/testspec.yml`

```yaml
version: 0.1

# テスト環境変数
env:
  variables:
    TEST_URL: "https://d1234567890.cloudfront.net"
    COGNITO_USER_POOL_ID: "ap-northeast-1_xxxxxxxxx"
    COGNITO_CLIENT_ID: "xxxxxxxxxxxxxxxxxxxxxxxxxx"

# テストフェーズ
phases:
  install:
    commands:
      - echo "Installing dependencies..."
      - npm ci

  pre_test:
    commands:
      - echo "Creating test user..."
      - aws lambda invoke \
          --function-name test-user-management \
          --payload '{"action":"create"}' \
          /tmp/user.json

  test:
    commands:
      - echo "Running critical path tests..."
      - npx playwright test devicefarm/tests/critical-path.spec.ts \
          --config=playwright.config.devicefarm.ts

  post_test:
    commands:
      - echo "Cleaning up test user..."
      - aws lambda invoke \
          --function-name test-user-management \
          --payload '{"action":"delete"}' \
          /tmp/cleanup.json

# テスト成果物
artifacts:
  - playwright-report/**/*
  - test-results/**/*
  - screenshots/**/*
```

#### Phase 5: テストユーザー管理 Lambda（6-8時間）

**ファイル**: `src/lambda/test_user_management/__init__.py`

```python
import boto3
from botocore.exceptions import ClientError

cognito = boto3.client('cognito-idp')

def lambda_handler(event, context):
    action = event.get('action')

    if action == 'create':
        return create_test_user()
    elif action == 'delete':
        return delete_test_user()
    else:
        return {'statusCode': 400, 'body': 'Invalid action'}

def create_test_user():
    """テストユーザーを作成"""
    try:
        # 既存ユーザー削除
        try:
            cognito.admin_delete_user(
                UserPoolId=USER_POOL_ID,
                Username=TEST_USERNAME
            )
        except ClientError:
            pass

        # 新規ユーザー作成
        cognito.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=TEST_USERNAME,
            TemporaryPassword=TEST_PASSWORD,
            MessageAction='SUPPRESS'
        )

        # パスワード永続化
        cognito.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=TEST_USERNAME,
            Password=TEST_PASSWORD,
            Permanent=True
        )

        return {
            'statusCode': 200,
            'body': {'username': TEST_USERNAME, 'password': TEST_PASSWORD}
        }
    except Exception as e:
        return {'statusCode': 500, 'body': str(e)}
```

#### Phase 6: CI/CD 統合（4-6時間）

**ファイル**: `.github/workflows/device-farm-tests.yml`

```yaml
name: Device Farm E2E Tests

on:
  pull_request:
    branches: [main]
  schedule:
    - cron: '0 0 * * 0'  # 毎週日曜 0:00 UTC

jobs:
  device-farm-tests:
    runs-on: ubuntu-latest

    steps:
      - uses: actions/checkout@v4

      - name: Setup Node.js
        uses: actions/setup-node@v4
        with:
          node-version: '18'

      - name: Install dependencies
        run: |
          cd frontend
          npm ci

      - name: Build frontend
        run: |
          cd frontend
          npm run build

      - name: Deploy to S3
        run: |
          aws s3 sync frontend/dist/ s3://test-hosting-bucket/ --delete

      - name: Run Device Farm tests
        run: |
          aws devicefarm schedule-run \
            --project-arn ${{ secrets.DEVICE_FARM_PROJECT_ARN }} \
            --test-spec-arn ${{ secrets.DEVICE_FARM_TEST_SPEC_ARN }} \
            --device-pool-arn ${{ secrets.DEVICE_FARM_DEVICE_POOL_ARN }}

      - name: Wait for test results
        run: |
          # テスト完了まで待機
          # 結果取得

      - name: Comment PR
        uses: actions/github-script@v7
        with:
          script: |
            github.rest.issues.createComment({
              issue_number: context.issue.number,
              owner: context.repo.owner,
              repo: context.repo.repo,
              body: 'Device Farm テスト結果: ...'
            })
```

### 2.4 変更ファイル一覧

#### 新規作成
```
terraform/
├── device_farm.tf                          # Device Farm リソース
└── s3_test_hosting.tf                      # テスト環境ホスティング

src/lambda/test_user_management/
└── __init__.py                             # テストユーザー管理

frontend/devicefarm/
├── testspec.yml                            # Device Farm 設定
├── playwright.config.devicefarm.ts         # Playwright 設定（Device Farm用）
└── tests/
    └── critical-path.spec.ts               # クリティカルパステスト

.github/workflows/
└── device-farm-tests.yml                   # CI/CD ワークフロー

scripts/
└── upload-to-devicefarm.sh                 # テストパッケージアップロード
```

### 2.5 リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| Device Farm コスト超過 | 高 | 実行頻度を週次に制限、20テストのみ |
| Cognito Admin 権限エラー | 中 | Lambda に適切な IAM ロール付与 |
| テスト実行時間超過 | 中 | タイムアウト設定、並列実行しない |

### 2.6 工数見積もり

| Phase | 工数 |
|-------|------|
| Phase 1: Device Farm 環境 | 2-3時間 |
| Phase 2: テスト環境ホスティング | 4-6時間 |
| Phase 3: クリティカルパステスト | 3-4時間 |
| Phase 4: YAML 設定 | 3-4時間 |
| Phase 5: テストユーザー管理 | 6-8時間 |
| Phase 6: CI/CD 統合 | 4-6時間 |

**合計: 22-31時間（約3-4日間）**

**コスト最適化**:
- 実行頻度: 週次（日曜0:00 UTC）
- テスト数: 20ケースのみ
- デバイス: Chromium のみ
- 推定コスト: $10-20/月

---

## タスク3: Next.js フロントエンド移行（優先度：中）

### 3.1 概要

**目標**: React + Vite から Next.js App Router への段階的移行

**移行アプローチ**: 段階的移行（リスク最小化）
1. Next.js Pages Router でベース構築
2. 認証システムを NextAuth.js に移行
3. ページを段階的に移行
4. App Router への移行（オプション）

**技術スタック**:
- Next.js 14 (Pages Router → App Router)
- NextAuth.js v5
- Tailwind CSS
- AWS Amplify Hosting

### 3.2 設計

#### 3.2.1 ディレクトリ構造（Pages Router）

```
frontend-nextjs/
├── pages/
│   ├── _app.tsx                            # アプリケーションルート
│   ├── index.tsx                           # リダイレクト
│   ├── login.tsx                           # ログインページ
│   ├── api/
│   │   └── auth/[...nextauth].ts           # NextAuth API Route
│   ├── profile.tsx
│   ├── goals.tsx
│   ├── foods.tsx
│   ├── meals/
│   │   ├── index.tsx
│   │   └── new.tsx
│   └── summary.tsx
├── components/
│   ├── LoginForm.tsx                       # 既存コンポーネント移植
│   ├── ProfileForm.tsx
│   └── ...
├── lib/
│   ├── auth.ts                             # NextAuth 設定
│   └── api-client.ts                       # API クライアント
├── middleware.ts                           # 認証ミドルウェア
├── next.config.js
├── tailwind.config.ts
└── package.json
```

#### 3.2.2 認証フロー（NextAuth.js）

**ファイル**: `lib/auth.ts`

```typescript
import NextAuth from "next-auth"
import CognitoProvider from "next-auth/providers/cognito"

export const { handlers, auth, signIn, signOut } = NextAuth({
  providers: [
    CognitoProvider({
      clientId: process.env.COGNITO_CLIENT_ID,
      clientSecret: process.env.COGNITO_CLIENT_SECRET,
      issuer: process.env.COGNITO_ISSUER,
    })
  ],
  session: {
    strategy: "jwt",
  },
  pages: {
    signIn: '/login',
  },
})
```

**ファイル**: `middleware.ts`

```typescript
export { auth as middleware } from "@/lib/auth"

export const config = {
  matcher: ['/((?!api|_next/static|_next/image|login).*)'],
}
```

### 3.3 実装ステップ

#### Phase 1: Next.js プロジェクト初期化（2-3時間）

```bash
# Next.js プロジェクト作成
npx create-next-app@latest frontend-nextjs \
  --typescript \
  --tailwind \
  --app false  # Pages Router

# NextAuth インストール
cd frontend-nextjs
npm install next-auth@beta
```

**ファイル**: `next.config.js`

```javascript
module.exports = {
  env: {
    NEXT_PUBLIC_API_BASE_URL: process.env.NEXT_PUBLIC_API_BASE_URL,
    NEXT_PUBLIC_COGNITO_USER_POOL_ID: process.env.NEXT_PUBLIC_COGNITO_USER_POOL_ID,
    NEXT_PUBLIC_COGNITO_CLIENT_ID: process.env.NEXT_PUBLIC_COGNITO_CLIENT_ID,
  },
}
```

#### Phase 2: 認証システム移行（8-10時間）

1. NextAuth 設定
2. Cognito プロバイダー設定
3. ミドルウェアで認証チェック
4. ログインページ実装
5. セッション管理

#### Phase 3: コンポーネント移行（12-16時間）

既存の8コンポーネントを移植:
- `'use client'` ディレクティブを追加
- CSS を Tailwind に変換（段階的）
- Props インターフェースは維持

#### Phase 4: ページ移行（12-16時間）

1. `/pages/login.tsx`
2. `/pages/index.tsx` (ホーム)
3. `/pages/profile.tsx`
4. `/pages/goals.tsx`
5. `/pages/foods.tsx`
6. `/pages/meals/index.tsx`
7. `/pages/meals/new.tsx`
8. `/pages/summary.tsx`

#### Phase 5: API クライアント移行（4-6時間）

既存の Axios クライアントを維持:
- NextAuth セッションからトークン取得
- `getServerSideProps` でサーバーサイドフェッチ（オプション）

#### Phase 6: Amplify Hosting 設定（4-6時間）

**ファイル**: `terraform/amplify_hosting.tf`

```hcl
resource "aws_amplify_app" "main" {
  name       = "${var.project_name}-frontend-${var.environment}"
  repository = "https://github.com/your-org/meal-management-app"

  build_spec = <<-EOT
    version: 1
    frontend:
      phases:
        preBuild:
          commands:
            - cd frontend-nextjs
            - npm ci
        build:
          commands:
            - npm run build
      artifacts:
        baseDirectory: frontend-nextjs/.next
        files:
          - '**/*'
      cache:
        paths:
          - node_modules/**/*
  EOT

  environment_variables = {
    NEXT_PUBLIC_API_BASE_URL          = var.api_gateway_url
    NEXT_PUBLIC_COGNITO_USER_POOL_ID  = aws_cognito_user_pool.main.id
    NEXT_PUBLIC_COGNITO_CLIENT_ID     = aws_cognito_user_pool_client.web_client.id
  }
}
```

#### Phase 7: テスト更新（6-8時間）

Playwright テストを Next.js 用に更新:
- ベースURL変更
- 認証フローの調整

### 3.4 変更ファイル一覧

#### 新規作成
```
frontend-nextjs/                            # 新規プロジェクト
├── pages/                                  # Pages Router
├── components/                             # コンポーネント（移植）
├── lib/                                    # ユーティリティ
├── middleware.ts                           # 認証ミドルウェア
├── next.config.js
├── tailwind.config.ts
└── package.json

terraform/
└── amplify_hosting.tf                      # Amplify Hosting 設定
```

### 3.5 リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| 認証システム移行の複雑性 | 高 | Pages Router で安定化してから App Router へ |
| Tailwind 変換の工数増加 | 中 | 段階的変換、既存 CSS も並行利用 |
| Playwright テストの全面書き換え | 高 | Next.js 移行完了後に Device Farm 再調整 |

### 3.6 工数見積もり

| Phase | 工数 |
|-------|------|
| Phase 1: プロジェクト初期化 | 2-3時間 |
| Phase 2: 認証システム | 8-10時間 |
| Phase 3: コンポーネント | 12-16時間 |
| Phase 4: ページ移行 | 12-16時間 |
| Phase 5: API クライアント | 4-6時間 |
| Phase 6: Amplify Hosting | 4-6時間 |
| Phase 7: テスト更新 | 6-8時間 |

**合計: 48-65時間（約6-8日間）**

---

## 実装スケジュール

### 推奨実施順序

| タスク | 工数 | 依存関係 |
|--------|------|----------|
| タスク1: 週次レポート | 2-3日 | なし |
| タスク2: Device Farm | 3-4日 | なし |
| タスク3: Next.js 移行 | 6-8日 | タスク2完了後（テスト再調整） |

**合計: 11-15日間**

### マイルストーン

- **Week 1-2**: タスク1（週次レポート）完了
- **Week 3-4**: タスク2（Device Farm）完了
- **Week 5-8**: タスク3（Next.js 移行）完了

---

## 補足事項

### ユーザー設定機能（週次レポート配信ON/OFF）

**実装難易度**: 低

**実装方法**:
1. Users テーブルに `weekly_report_enabled` 属性追加
2. プロフィールページにトグルスイッチ追加
3. Lambda で配信前にフラグチェック

**工数**: +2-3時間

**判断**: 優先実装を推奨（ユーザビリティ向上）

### コスト見積もり

| サービス | 月額コスト（推定） |
|----------|-------------------|
| EventBridge Scheduler | $0.01 |
| Lambda（週次レポート） | $1-5 |
| Bedrock（週次アドバイス） | $5-10 |
| Device Farm（週次テスト） | $10-20 |
| Amplify Hosting | $5-15 |
| **合計** | **$21-51/月** |

---

## Critical Files Reference

### タスク1: 週次レポート
- `src/lambda/daily_summary/__init__.py`
- `src/lambda/line_handler/__init__.py`
- `terraform/iam.tf`
- `terraform/dynamodb.tf`

### タスク2: Device Farm
- `frontend/playwright.config.ts`
- `frontend/tests/global-setup.ts`
- `frontend/e2e/*.spec.ts`

### タスク3: Next.js
- `frontend/src/contexts/AuthContext.tsx`
- `frontend/src/App.tsx`
- `frontend/src/api/client.ts`
- `terraform/cognito.tf`
