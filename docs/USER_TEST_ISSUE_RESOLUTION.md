# ユーザーテスト 問題解決記録

## 概要

ユーザーテスト中に発見された問題とその解決方法を記録したドキュメントです。

---

## 問題 #1: LINE Bot 総評機能 - Lambda呼び出し権限エラー

### 発生日時
2025-12-09

### 症状
LINE Botに「総評」「まとめ」「今日のアドバイス」と送信すると、以下のエラーが返される：
```
総評の生成中にエラーが発生しました。後ほど再度お試しください。
```

### 根本原因
`line_handler` Lambda関数が `daily_summary` Lambda関数を呼び出す際に、以下の2つの問題が発生：

1. **IAM権限不足**: `lambda:InvokeFunction` 権限がLambda実行ロールに付与されていなかった
2. **関数名ハードコード**: 関数名が `"daily_summary"` とハードコードされていたが、実際の関数名は `meal-management-app-dev-daily-summary`

### CloudWatchログ（エラー）
```
AccessDeniedException: User: arn:aws:sts::552927148143:assumed-role/meal-management-app-lambda-execution-role-dev/meal-management-app-dev-line-handler
is not authorized to perform: lambda:InvokeFunction on resource: arn:aws:lambda:ap-northeast-1:552927148143:function:daily_summary
```

### 解決方法

#### 1. IAMポリシー追加（terraform/iam.tf）
```hcl
# Lambda間呼び出し権限（LINE Handler → Daily Summary など）
resource "aws_iam_role_policy" "lambda_invoke_lambda" {
  name = "${var.project_name}-lambda-invoke-lambda-${var.environment}"
  role = aws_iam_role.lambda_execution_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "lambda:InvokeFunction"
        ]
        Resource = "arn:aws:lambda:${var.aws_region}:*:function:${var.project_name}-${var.environment}-*"
      }
    ]
  })
}
```

#### 2. 環境変数追加（terraform/api_gateway.tf）
```hcl
environment {
  variables = {
    # ... 他の環境変数 ...
    DAILY_SUMMARY_FUNCTION_NAME = aws_lambda_function.daily_summary.function_name
  }
}
```

#### 3. コード修正（src/lambda/line_handler/__init__.py）
```python
# 環境変数から関数名を取得
DAILY_SUMMARY_FUNCTION_NAME = os.environ.get("DAILY_SUMMARY_FUNCTION_NAME", "")

# Lambda関数を同期的に呼び出し
response = lambda_client.invoke(
    FunctionName=DAILY_SUMMARY_FUNCTION_NAME,  # ハードコードではなく環境変数を使用
    InvocationType="RequestResponse",
    Payload=json.dumps(payload)
)
```

### 教訓
- Lambda関数名はTerraformで動的に生成されるため、ハードコードせず環境変数で渡す
- Lambda間呼び出しには明示的なIAM権限が必要

### 関連コミット
- `6464d1b` - fix: Add Lambda-to-Lambda invocation permission for LINE Bot daily advice

---

## 問題 #2: LINE Bot 総評機能 - DynamoDBスキーマ不一致

### 発生日時
2025-12-09

### 症状
問題#1の修正後も、LINE Botに「総評」と送信すると同じエラーが返される：
```
総評の生成中にエラーが発生しました。後ほど再度お試しください。
```

### 根本原因
`daily_summary` Lambda関数内のDynamoDBアクセスコードが、実際のテーブルスキーマと一致していなかった。

| テーブル | コード使用名 | 実際の名前 |
|----------|-------------|-----------|
| AdviceUsage キー | `usage_key` | `user_id_date` |
| Meals GSI | `GSI1` | `UserIdTimestampIndex` |
| Goals GSI | `GSI1` | `UserIdCreatedAtIndex` |

### CloudWatchログ（エラー）
```
ValidationException: The provided key element does not match the schema
ValidationException: The table does not have the specified index: GSI1
```

### 解決方法

#### コード修正（src/lambda/daily_summary/__init__.py）

**AdviceUsageテーブルのキー名修正:**
```python
# Before
usage_key = f"{user_id}#{advice_date.isoformat()}"
advice_usage_db.get_item({"usage_key": usage_key})

# After
user_id_date = f"{user_id}#{advice_date.isoformat()}"
advice_usage_db.get_item({"user_id_date": user_id_date})
```

**MealsテーブルのGSI名修正:**
```python
# Before
response = meals_db.table.query(
    IndexName="GSI1",
    ...
)

# After
response = meals_db.table.query(
    IndexName="UserIdTimestampIndex",
    ...
)
```

**GoalsテーブルのGSI名修正:**
```python
# Before
response = goals_db.table.query(
    IndexName="GSI1",
    ...
)

# After
response = goals_db.table.query(
    IndexName="UserIdCreatedAtIndex",
    ...
)
```

### 教訓
- TerraformでのDynamoDBテーブル定義と、Lambdaコードでのアクセスパターンの整合性を確認する
- GSI名やキー名はドキュメント化して、コードとインフラの不一致を防ぐ
- コード内の「GSI1」のような汎用名ではなく、実際のインデックス名を使用する

### 確認コマンド
```bash
# テーブルスキーマの確認
aws dynamodb describe-table --table-name meal-management-app-advice-usage-dev \
  --query 'Table.KeySchema'

# GSI名の確認
aws dynamodb describe-table --table-name meal-management-app-meals-dev \
  --query 'Table.GlobalSecondaryIndexes[*].IndexName'
```

---

## ドキュメント更新

これらの問題解決に伴い、以下のドキュメントを更新しました：

| ファイル | 追加内容 |
|----------|----------|
| [docs/ARCHITECTURE.md](ARCHITECTURE.md) | Lambda間呼び出し権限セクション（IAMパターン、環境変数対応表） |
| [docs/DEPLOYMENT.md](DEPLOYMENT.md) | `AccessDeniedException` トラブルシューティング手順 |
| [README.md](../README.md) | LINE Botアーキテクチャ図、ドキュメントリンク追加 |

### ARCHITECTURE.md 追加内容

```markdown
#### Lambda 間呼び出し権限

LINE Handler から他の Lambda 関数を呼び出すための権限:

- **対象関数**: `${project_name}-${environment}-*` パターンにマッチする全関数
- **アクション**: `lambda:InvokeFunction`
- **用途**: LINE Bot → Daily Summary（総評機能）など

| 呼び出し元 | 呼び出し先 | 環境変数 |
|------------|------------|----------|
| line_handler | daily_summary | `DAILY_SUMMARY_FUNCTION_NAME` |
| line_handler | food_search | `FOOD_SEARCH_FUNCTION_NAME` |
```

### README.md 追加内容

```markdown
## LINE Bot アーキテクチャ

LINE Bot は以下の Lambda 関数連携で動作します：

LINE App → API Gateway → line_handler → daily_summary (総評機能)
                                      → food_search (食品検索)

**重要な設計ポイント:**
- Lambda 関数名は Terraform で動的生成（`${project}-${env}-${name}` 形式）
- 関数名はハードコードせず、環境変数で渡す
- Lambda 間呼び出しには IAM の `lambda:InvokeFunction` 権限が必要
```

---

## チェックリスト

将来の同様の問題を防ぐためのチェック項目：

### Lambda間呼び出し
- [ ] IAMロールに `lambda:InvokeFunction` 権限があるか
- [ ] 関数名は環境変数経由で渡しているか（ハードコードしていないか）
- [ ] 呼び出し先関数のARNパターンが正しいか

### DynamoDB アクセス
- [ ] コード内のテーブルキー名がTerraform定義と一致しているか
- [ ] コード内のGSI名がTerraform定義と一致しているか
- [ ] GSIのキー属性（HASH, RANGE）が正しいか

---

**更新日**: 2025-12-09
