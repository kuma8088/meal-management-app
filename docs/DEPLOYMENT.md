# デプロイ手順書

## 前提条件

- AWS CLI 設定済み
- Terraform >= 1.0
- Node.js >= 18
- Python 3.11

## 環境一覧

| 環境 | 用途 | API URL |
|------|------|---------|
| dev | 開発 | `https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev` |
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

```
VITE_API_BASE_URL=https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev
VITE_COGNITO_USER_POOL_ID=ap-northeast-1_fmIO9wUwC
VITE_COGNITO_CLIENT_ID=7fjjol84obkgbj4mh29qtjp6i8
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
# ユーザー確認
aws cognito-idp list-users --user-pool-id ap-northeast-1_fmIO9wUwC
```
