# デプロイ手順書

## 前提条件

- AWS CLI 設定済み
- Terraform >= 1.0
- Node.js >= 18
- Python 3.11

## 環境一覧

| 環境 | 用途 | API URL |
|------|------|---------|
| dev | 開発 | `terraform output api_gateway_url` で取得 |
| staging | ステージング | (未作成) |
| prod | 本番 | (未作成) |

## デプロイ手順

### 1. インフラのデプロイ（Terraform）

```bash
cd terraform

# 初期化（初回のみ）
terraform init

# 変更確認
terraform plan

# 適用
terraform apply
```

### 2. Lambda 関数のパッケージングとデプロイ

```bash
# Lambda関数をZIPにパッケージング
./scripts/package_lambda.sh

# Terraformで再デプロイ
cd terraform && terraform apply
```

### 3. フロントエンドのビルドとデプロイ

```bash
cd frontend

# 環境変数設定
cp .env.example .env
# .env を編集

# ビルド
npm run build

# S3にアップロード（CloudFront経由で配信）
aws s3 sync dist/ s3://meal-management-app-frontend-dev/ --delete
```

## 環境変数

### Terraform (terraform/terraform.tfvars)

```hcl
environment              = "dev"
aws_region               = "ap-northeast-1"
line_channel_secret      = "your-secret"
line_channel_access_token = "your-token"
```

### Frontend (frontend/.env)

```bash
# terraform output で取得した値を設定
VITE_API_BASE_URL=https://{api-id}.execute-api.{region}.amazonaws.com/{stage}
VITE_COGNITO_USER_POOL_ID={user-pool-id}
VITE_COGNITO_CLIENT_ID={client-id}
```

## テスト実行

```bash
# バックエンドテスト
pytest tests/ -v

# E2Eテスト
cd frontend && npm run test:e2e

# パフォーマンステスト
locust -f tests/performance/locustfile.py --headless -u 10 -r 2 -t 60s

# セキュリティスキャン
bandit -r src/
```

## ロールバック手順

```bash
cd terraform

# 直前の状態に戻す
terraform apply -target=<resource> -var="version=previous"

# 完全ロールバック
terraform destroy
terraform apply
```

## 監視

- **CloudWatch Logs**: `/aws/lambda/meal-management-app-*`
- **CloudWatch Alarms**: Lambda エラー率 > 1%
- **X-Ray**: 分散トレーシング（有効化済み）

## トラブルシューティング

### Lambda タイムアウト

```bash
# ログ確認
aws logs tail /aws/lambda/meal-management-app-food-search-dev --follow
```

### DynamoDB スロットリング

- オンデマンドキャパシティモード使用中
- 必要に応じてプロビジョニングモードに変更

### Cognito 認証エラー

```bash
# User Pool ID を取得
terraform -chdir=terraform output cognito_user_pool_id

# ユーザー確認
aws cognito-idp list-users --user-pool-id $(terraform -chdir=terraform output -raw cognito_user_pool_id)
```

### Lambda 間呼び出しエラー (AccessDeniedException)

LINE Bot の総評機能などで `AccessDeniedException` が発生する場合:

**症状:**
```
User: arn:aws:sts::ACCOUNT:assumed-role/...-lambda-execution-role-dev/...-line-handler
is not authorized to perform: lambda:InvokeFunction on resource: ...
```

**原因:**
1. IAM ロールに `lambda:InvokeFunction` 権限がない
2. 呼び出し先の Lambda 関数名が間違っている（ハードコード）

**解決方法:**

1. IAM 権限の確認:
```bash
aws iam list-role-policies --role-name meal-management-app-lambda-execution-role-dev
# lambda-invoke-lambda ポリシーが存在することを確認
```

2. 環境変数の確認:
```bash
aws lambda get-function-configuration \
  --function-name meal-management-app-dev-line-handler \
  --query 'Environment.Variables'
# DAILY_SUMMARY_FUNCTION_NAME が正しく設定されていることを確認
```

3. Terraform での修正:
- `terraform/iam.tf`: `aws_iam_role_policy.lambda_invoke_lambda` リソースを追加
- `terraform/api_gateway.tf`: Lambda 環境変数に関数名を追加

**重要**: Lambda 関数名は `${project}-${env}-${name}` 形式で動的生成されるため、ハードコードせず環境変数で渡す。
