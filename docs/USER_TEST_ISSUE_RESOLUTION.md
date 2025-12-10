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

## 問題 #3: 食品検索で「ご飯」が見つからない

### 発生日時
2025-12-10

### 症状
LINE Botに「ご飯 150g」と送信すると、以下のメッセージが返される：
```
「ご飯」に該当する食品が見つかりませんでした。別の名前で試してください。
```

### 根本原因
1. **シノニム（同義語）未対応**: DynamoDB の Foods テーブルには「めし」「精白米」などで登録されているが、ユーザーは「ご飯」で検索
2. **DynamoDB scan のページネーション問題**: `Limit` パラメータがフィルタ後の結果数ではなく、スキャンするアイテム数を制限していた

### 解決方法

#### 1. シノニムマッピング追加（src/lambda/food_search/__init__.py）
```python
FOOD_SYNONYMS = {
    # ご飯・米関連
    'ご飯': ['めし', '米', 'ごはん', '飯', 'ライス'],
    'ごはん': ['めし', '米', 'ご飯', '飯', 'ライス'],
    '白米': ['めし', '精白米', 'ご飯', '米'],
    # パン関連
    'パン': ['食パン', 'ブレッド'],
    # 麺類
    'うどん': ['饂飩'],
    'ラーメン': ['らーめん', '拉麺', '中華めん'],
    # ... その他多数
}
```

`search_by_name()` メソッドで複数の検索語を OR 条件で検索するように変更。

#### 2. scan ページネーション修正（src/lambda/common/dynamodb_helper.py）
```python
def scan(self, filter_expression=None, expression_attribute_values=None,
         limit=100, max_pages=10):
    all_items = []
    pages_scanned = 0
    last_evaluated_key = None

    while pages_scanned < max_pages:
        if last_evaluated_key:
            scan_params["ExclusiveStartKey"] = last_evaluated_key

        response = self.table.scan(**scan_params)
        all_items.extend(response.get("Items", []))
        pages_scanned += 1

        # limit に達したら終了
        if limit and len(all_items) >= limit:
            all_items = all_items[:limit]
            break

        # 次のページがなければ終了
        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return all_items
```

### 教訓
- 日本語には同じ食品を指す複数の表現がある（「ご飯」「めし」「米」など）
- DynamoDB の `Limit` はスキャンするアイテム数を制限する（フィルタ前）
- フィルタ後の結果数を制限したい場合は、ページネーションループで結果を収集する

---

## 問題 #4: MealFood 引数エラー

### 発生日時
2025-12-10

### 症状
食事登録中に以下のエラーが発生：
```
MealFood.__init__() got an unexpected keyword argument 'amount_g'
```

### 根本原因
`line_handler` が `amount_g` フィールドを送信していたが、`MealFood` モデルは `amount` を期待していた。

### 解決方法

#### コード修正（src/lambda/line_handler/__init__.py 682行目付近）
```python
# 修正前
"amount_g": amount_g,

# 修正後
"amount": amount_g,
```

### 教訓
- API のリクエストボディフィールド名とモデルのフィールド名を一致させる
- 命名規則の統一が重要

---

## 問題 #5: FoodSource enum エラー

### 発生日時
2025-12-10

### 症状
食事登録中に以下のエラーが発生：
```
'japanese_standard' is not a valid FoodSource
```

### 根本原因
DynamoDB の Foods テーブルに `source: "japanese_standard"` として保存されているが、`FoodSource` enum にこの値が定義されていなかった。

### 解決方法

#### コード修正（src/lambda/common/models.py）
```python
class FoodSource(str, Enum):
    STANDARD = "standard"
    AI_GENERATED = "ai_generated"
    USER_ADDED = "user_added"
    JAPANESE_STANDARD = "japanese_standard"  # 追加
```

### 教訓
- データベースに保存される値と Enum 定義を同期させる
- 新しいデータソースを追加した場合は Enum にも追加する

---

## 問題 #6: Food モデルのフィールドマッピングエラー

### 発生日時
2025-12-10

### 症状
食事登録中に以下のエラーが発生：
```
Food.__init__() got an unexpected keyword argument 'carbs'
```

### 根本原因
DynamoDB のフィールド名と Python モデルのフィールド名が不一致：

| DynamoDB フィールド | モデルフィールド |
|---------------------|------------------|
| `food_name` | `name` |
| `calories` | `calories_per_100g` |
| `protein` | `protein_per_100g` |
| `fat` | `fat_per_100g` |
| `carbs` | `carbs_per_100g` |

### 解決方法

#### コード修正（src/lambda/common/models.py）
`Food.from_dict()` メソッドにフィールドマッピングを追加：
```python
@classmethod
def from_dict(cls, data: dict) -> "Food":
    data = data.copy()

    # DynamoDB フィールド名 → モデルフィールド名のマッピング
    field_mapping = {
        'food_name': 'name',
        'calories': 'calories_per_100g',
        'protein': 'protein_per_100g',
        'fat': 'fat_per_100g',
        'carbs': 'carbs_per_100g',
    }

    for db_field, model_field in field_mapping.items():
        if db_field in data and model_field not in data:
            data[model_field] = data.pop(db_field)

    # 無効なフィールドを除去
    valid_fields = {'food_id', 'name', 'calories_per_100g', 'protein_per_100g',
                    'fat_per_100g', 'carbs_per_100g', 'jan_code', 'source',
                    'created_at', 'updated_at'}
    data = {k: v for k, v in data.items() if k in valid_fields}

    # ... enum変換などの処理
    return cls(**data)
```

### 教訓
- データモデルと永続化層のスキーマが異なる場合、明示的なマッピングが必要
- `from_dict()` メソッドでマッピングロジックを一元管理する

---

## 問題 #7: DynamoDB ソートキー欠落エラー

### 発生日時
2025-12-10

### 症状
食事登録中に以下のエラーが発生：
```
ValidationException: One or more parameter values were invalid: Missing the key user_id_timestamp in the item
```

### 根本原因
Meals テーブルの複合キー構造：
- パーティションキー: `meal_id`
- ソートキー: `user_id_timestamp`

しかし `meal_registration` Lambda が `sk` という誤ったフィールド名を使用していた。

### 解決方法

#### コード修正（src/lambda/meal_registration/__init__.py）

**create_meal 関数 (176行目)**:
```python
# 修正前
meal_data["sk"] = f"{user_id}#{timestamp.isoformat()}"

# 修正後
meal_data["user_id_timestamp"] = f"{user_id}#{timestamp.isoformat()}"
```

**update_meal 関数 (448行目)**:
```python
# 修正前
updated_data["sk"] = f"{existing_meal_data['user_id']}#{timestamp.isoformat()}"

# 修正後
updated_data["user_id_timestamp"] = f"{existing_meal_data['user_id']}#{timestamp.isoformat()}"
```

### 教訓
- Terraform で定義したキー名と Lambda コードで使用するフィールド名は**厳密に一致**させる必要がある
- `range_key = "user_id_timestamp"` なら、コードでも `user_id_timestamp` を使用する

---

## デプロイ手順（問題 #3〜#7）

修正後、以下のコマンドで Lambda 関数を更新：

```bash
# パッケージング
./scripts/package_lambda.sh

# 各 Lambda 関数を更新
aws lambda update-function-code \
  --function-name meal-management-app-dev-food-search \
  --zip-file fileb://dist/food_search.zip \
  --region ap-northeast-1

aws lambda update-function-code \
  --function-name meal-management-app-dev-line-handler \
  --zip-file fileb://dist/line_handler.zip \
  --region ap-northeast-1

aws lambda update-function-code \
  --function-name meal-management-app-dev-meal-registration \
  --zip-file fileb://dist/meal_registration.zip \
  --region ap-northeast-1
```

---

## 修正サマリー（2025-12-10）

| # | エラー | 原因 | 修正ファイル |
|---|--------|------|-------------|
| 3 | 「ご飯」が見つからない | シノニム未対応 + scan ページネーション | `food_search/__init__.py`, `dynamodb_helper.py` |
| 4 | `amount_g` 引数エラー | フィールド名不一致 | `line_handler/__init__.py:682` |
| 5 | `japanese_standard` enum | FoodSource に値がない | `models.py` |
| 6 | `carbs` 引数エラー | DB→Model マッピング欠如 | `models.py` |
| 7 | `user_id_timestamp` 欠落 | ソートキー名の不一致 | `meal_registration/__init__.py:176,448` |

---

## チェックリスト（更新）

将来の同様の問題を防ぐためのチェック項目：

### Lambda間呼び出し
- [ ] IAMロールに `lambda:InvokeFunction` 権限があるか
- [ ] 関数名は環境変数経由で渡しているか（ハードコードしていないか）
- [ ] 呼び出し先関数のARNパターンが正しいか

### DynamoDB アクセス
- [ ] コード内のテーブルキー名がTerraform定義と一致しているか
- [ ] コード内のGSI名がTerraform定義と一致しているか
- [ ] GSIのキー属性（HASH, RANGE）が正しいか
- [ ] **複合キーテーブルでは両方のキー（PK + SK）を指定しているか**

### データモデル
- [ ] DynamoDB フィールド名と Python モデルフィールド名の対応が正しいか
- [ ] `from_dict()` にマッピングロジックが実装されているか
- [ ] Enum 値がデータベースに保存される値と一致しているか

### 食品検索
- [ ] 日本語のシノニム（同義語）が考慮されているか
- [ ] scan のページネーションが正しく実装されているか

---

## 問題 #8: LIFF Web App リダイレクトループ（API Gateway 401）

### 発生日時
2025-12-10

### 症状
LIFF Web App で全てのボタンを押すとトップページにリダイレクトされ、何も操作できない状態になった。

```
ボタン押すとトップページに遷移するようになってる。何もできない。
ほぼ全部リダイレクトしているようだ
```

### 根本原因
API Gateway のステージが古いデプロイメント（`112mma`）を参照していた。最新のデプロイメント（`nhvj8e`）に更新されていなかったため、API Gateway がすべてのリクエストに対して `{"message":"Unauthorized"}` を返していた。

フロントエンドの 401 エラーハンドリングが `unauthorized` イベントを発火 → `signOut()` → リダイレクト、というループが発生。

### 調査過程

1. **Lambda直接呼び出しテスト**: 成功（データは正常に返却）
2. **API Gateway経由テスト**: `{"message":"Unauthorized"}` が返却
3. **API Gateway メソッド設定確認**: `authorization = "NONE"` で正しく設定されている
4. **デプロイメント確認**: ステージが古いデプロイメントを参照

```bash
# ステージ情報
aws apigateway get-stage --rest-api-id 868t2tljy9 --stage-name dev
# deploymentId: "112mma" ← 古い

# デプロイメント一覧
aws apigateway get-deployments --rest-api-id 868t2tljy9
# nhvj8e (14:10:44) ← 最新
# 112mma (13:19:30) ← ステージが参照
```

### 解決方法

```bash
# ステージを最新のデプロイメントに更新
aws apigateway update-stage \
  --rest-api-id 868t2tljy9 \
  --stage-name dev \
  --patch-operations op=replace,path=/deploymentId,value=nhvj8e \
  --region ap-northeast-1
```

### 教訓
- Terraform の `triggers` で自動再デプロイが設定されていても、ステージへの反映が遅れることがある
- API Gateway の問題を調査する際は、Lambda 直接呼び出しとの比較が有効
- `{"message":"Unauthorized"}` は API Gateway 固有のレスポンス形式（Lambda の認証エラーとは異なる）

---

## 問題 #9: DynamoDB Query ValidationException（未使用の ExpressionAttributeNames）

### 発生日時
2025-12-10

### 症状
`/meals` エンドポイントへのリクエストで内部エラーが発生。

```json
{"error": {"code": "INTERNAL_ERROR", "message": "内部エラーが発生しました"}}
```

### CloudWatchログ
```
ValidationException: Value provided in ExpressionAttributeNames unused in expressions: keys: {#ts}
```

### 根本原因
`meal_registration/__init__.py` の `list_meals` 関数で、`ExpressionAttributeNames` に `{"#ts": "timestamp"}` を常に設定していたが、日付フィルタ（`start_date`, `end_date`）がない場合は `#ts` を使用しない。

DynamoDB は未使用の ExpressionAttributeNames があるとエラーを返す。

### 解決方法

#### コード修正（src/lambda/meal_registration/__init__.py 251行目〜）
```python
# 修正前
query_params_dict = {
    "IndexName": "UserIdTimestampIndex",
    "KeyConditionExpression": key_condition,
    "ExpressionAttributeNames": {"#ts": "timestamp"},  # ← 常に設定
    ...
}

# 修正後
expression_attr_names = {}
if start_date and end_date:
    key_condition += " AND #ts BETWEEN :start_date AND :end_date"
    expression_attr_names["#ts"] = "timestamp"
elif start_date:
    key_condition += " AND #ts >= :start_date"
    expression_attr_names["#ts"] = "timestamp"
elif end_date:
    key_condition += " AND #ts <= :end_date"
    expression_attr_names["#ts"] = "timestamp"

query_params_dict = {
    "IndexName": "UserIdTimestampIndex",
    "KeyConditionExpression": key_condition,
    "ExpressionAttributeValues": expression_values,
    ...
}

# ExpressionAttributeNames は使用時のみ追加
if expression_attr_names:
    query_params_dict["ExpressionAttributeNames"] = expression_attr_names
```

### 教訓
- DynamoDB の `ExpressionAttributeNames` や `ExpressionAttributeValues` は、実際に式で使用する場合のみ追加する
- クエリ条件が動的に変わる場合は、付随するパラメータも動的に構築する

---

## 問題 #10: JSON Serialization Error（Decimal 型）

### 発生日時
2025-12-10

### 症状
問題 #9 修正後も `/meals` エンドポイントで内部エラーが発生。

### CloudWatchログ
```
TypeError: Object of type Decimal is not JSON serializable
```

ログには「食事記録リストを取得しました: 1件」と表示されており、DynamoDB からのデータ取得は成功していた。

### 根本原因
DynamoDB は数値を Python の `Decimal` 型で返すが、標準の `json.dumps()` は `Decimal` をシリアライズできない。

### 解決方法

#### コード修正（src/lambda/common/response.py）
```python
import json
from decimal import Decimal

class DecimalEncoder(json.JSONEncoder):
    """DynamoDB Decimal型をJSONシリアライズするためのエンコーダー"""

    def default(self, obj):
        if isinstance(obj, Decimal):
            # 整数の場合はintに、それ以外はfloatに変換
            if obj % 1 == 0:
                return int(obj)
            return float(obj)
        return super().default(obj)


def create_response(status_code, body, headers=None):
    ...
    return {
        "statusCode": status_code,
        "headers": default_headers,
        "body": json.dumps(body, ensure_ascii=False, cls=DecimalEncoder)  # カスタムエンコーダー使用
    }
```

### 教訓
- DynamoDB を使用する場合、レスポンス生成時に `Decimal` 型の処理が必要
- 共通のレスポンスヘルパーに処理を入れておくと、すべての Lambda 関数で自動的に適用される

---

## デプロイ手順（問題 #8〜#10）

```bash
# パッケージング
./scripts/package_lambda.sh

# 影響を受ける Lambda 関数を更新
for func in meal_registration food_search goal_management daily_summary; do
  func_name="meal-management-app-dev-${func//_/-}"
  aws lambda update-function-code \
    --function-name "$func_name" \
    --zip-file "fileb://dist/${func}.zip" \
    --region ap-northeast-1
done
```

---

## 修正サマリー（2025-12-10 追加分）

| # | エラー | 原因 | 修正ファイル/操作 |
|---|--------|------|------------------|
| 8 | API Gateway 401 リダイレクトループ | ステージが古いデプロイメントを参照 | `aws apigateway update-stage` |
| 9 | ExpressionAttributeNames unused | 未使用の `#ts` を常に設定 | `meal_registration/__init__.py:251-278` |
| 10 | Decimal not JSON serializable | DynamoDB の Decimal 型未対応 | `common/response.py` |

---

## チェックリスト（更新）

### API Gateway デプロイメント
- [ ] Terraform apply 後、ステージが最新のデプロイメントを参照しているか
- [ ] `{"message":"Unauthorized"}` が返る場合、Lambda ではなく API Gateway の問題を疑う

### DynamoDB クエリ
- [ ] `ExpressionAttributeNames` に未使用の名前が含まれていないか
- [ ] `ExpressionAttributeValues` に未使用の値が含まれていないか
- [ ] 動的なクエリ条件を構築する場合、付随パラメータも動的に構築しているか

### JSON シリアライズ
- [ ] DynamoDB からの Decimal 型データがレスポンスに含まれる場合、カスタムエンコーダーを使用しているか

---

## 問題 #11: 目標設定 - 「user_idは必須です」エラー

### 発生日時
2025-12-10

### 症状
LIFF Web App で目標設定ボタンを押すと以下のエラーが表示される：
```
user_idは必須です
```

### 根本原因
`goal_management` Lambda の `create_goal` 関数が、リクエストボディから `user_id` と `current_weight` を取得しようとしていたが、フロントエンドはこれらを送信していなかった。

- `user_id`: 認証済みユーザーの ID は `@require_auth` デコレータによって `event["auth_user"]["user_id"]` に設定される
- `current_weight`: ユーザープロフィールにすでに保存されている

### 解決方法

#### コード修正（src/lambda/goal_management/__init__.py）

```python
def create_goal(event: Dict[str, Any]) -> Dict[str, Any]:
    # 修正前: リクエストボディから user_id を取得
    # body = json.loads(event.get("body", "{}"))
    # user_id = body.get("user_id")
    # if not user_id:
    #     raise ValidationError("user_idは必須です")

    # 修正後: 認証ユーザーから user_id を取得
    auth_user = event.get("auth_user", {})
    user_id = auth_user.get("user_id")
    if not user_id:
        raise ValidationError("認証が必要です", details={"field": "user_id"})

    # ユーザー情報を取得
    user_data = users_db.get_item({"user_id": user_id})

    # current_weight はオプション（指定がなければプロフィールから取得）
    current_weight = body.get("current_weight")
    if current_weight is None:
        current_weight = user_data.get("weight")
        if current_weight is None:
            raise ValidationError(
                "current_weightが指定されておらず、プロフィールにも体重が設定されていません",
                details={"user_id": user_id}
            )
        logger.info(f"current_weightをプロフィールから取得: {current_weight}kg")
```

### 教訓
- `@require_auth` デコレータを使用している場合、`user_id` はリクエストボディではなく `event["auth_user"]["user_id"]` から取得する
- ユーザープロフィールに保存済みの情報（体重など）は、再度入力を求める代わりにプロフィールから取得することでUXを向上させる

---

## 問題 #12: 食事記録・総評ページの画面真っ白問題

### 発生日時
2025-12-10

### 症状
LIFF Web App で「食事記録」「総評」ボタンを押すと、画面が真っ白になり戻るボタンも表示されない。

### 根本原因
**APIレスポンス形式とフロントエンドの期待値の不一致**

| API | バックエンドの返却形式 | フロントエンドの期待形式 |
|-----|----------------------|----------------------|
| `GET /meals` | `{ "meals": [...], "count": N, "has_more": bool }` | `Meal[]` |

フロントエンドの `getMeals` 関数が `response.data` をそのまま返していたため、オブジェクト `{ meals: [...] }` が配列として扱われ、`meals.map()` などの配列メソッド呼び出しで JavaScript エラーが発生。

React がエラーをキャッチできずにクラッシュし、画面が真っ白になった。

### 解決方法

#### コード修正（frontend/src/api/meals.ts）
```typescript
// 修正前
export const getMeals = async (params?: GetMealsParams): Promise<Meal[]> => {
  const response = await apiClient.get<Meal[]>('/meals', { params });
  return response.data;  // ← { meals: [...] } が返される
};

// 修正後
export const getMeals = async (params?: GetMealsParams): Promise<Meal[]> => {
  const response = await apiClient.get<{ meals: Meal[]; count: number; has_more: boolean }>('/meals', { params });
  return response.data.meals;  // ← meals 配列を抽出
};
```

### 影響範囲
- `MealsPage.tsx`: `getMeals` を直接呼び出し
- `DailySummary.tsx`: `getMeals` を呼び出し（SummaryPage で使用）

両方のページがこの修正で同時に解決。

### デプロイ手順
```bash
# フロントエンドをビルド
npm --prefix frontend run build

# S3 にデプロイ
aws s3 sync frontend/dist/ s3://meal-management-app-frontend-dev/ --delete

# CloudFront キャッシュを無効化
aws cloudfront create-invalidation \
  --distribution-id E36GJ9UHD72DBK \
  --paths "/*"
```

### 教訓
- フロントエンドの型定義（`Promise<Meal[]>`）とバックエンドのレスポンス形式が一致しているか確認する
- 配列を返すAPIでも、メタデータ（count, has_more など）を含める場合はオブジェクトでラップされる
- React アプリの画面真っ白は通常 JavaScript ランタイムエラー。ブラウザのコンソールを確認する

---

## 修正サマリー（2025-12-10 追加分 #2）

| # | エラー | 原因 | 修正ファイル/操作 |
|---|--------|------|------------------|
| 11 | 「user_idは必須です」 | user_id をボディから取得しようとした | `goal_management/__init__.py:133-189` |
| 12 | 食事記録・総評が画面真っ白 | APIレスポンス形式の不一致 | `frontend/src/api/meals.ts:24-28` |

---

## チェックリスト（更新）

### 認証・認可
- [ ] `@require_auth` デコレータを使用している場合、`user_id` は `event["auth_user"]["user_id"]` から取得しているか
- [ ] リクエストボディに `user_id` を要求しない（認証情報から取得）

### API レスポンス形式
- [ ] バックエンドのレスポンス形式とフロントエンドの型定義が一致しているか
- [ ] 配列を返す API で `{ items: [...], count, has_more }` 形式を使用している場合、フロントエンドで `.items` を抽出しているか

---

## 問題 #13: 目標作成 - 減量目標が空、期限がInvalid Date

### 発生日時
2025-12-10

### 症状
目標を作成すると成功するが、画面に表示される「減量目標」が空で、「期限」が "Invalid Date" と表示される。

### 根本原因
`create_goal` のレスポンスに `target_weight`、`target_date`、`goal_type` が含まれていなかった。

フロントエンド (`GoalForm.tsx:286-289`) は以下のフィールドを参照：
```tsx
<p>目標: {currentWeight}kg → {createdGoal.target_weight}kg</p>
<p>期限: {new Date(createdGoal.target_date).toLocaleDateString('ja-JP')}</p>
```

`createdGoal.target_date` が `undefined` → `new Date(undefined)` → "Invalid Date"

### 解決方法

#### コード修正（src/lambda/goal_management/__init__.py 242-256行目）
```python
# 修正前
response_data = {
    "goal_id": goal_id,
    "daily_calorie_adjustment": ...,
    "target_calories": ...,
    ...
}

# 修正後 - フロントエンドが参照するフィールドを追加
response_data = {
    "goal_id": goal_id,
    "goal_type": goal_type.value,           # 追加
    "current_weight": float(current_weight), # 追加
    "target_weight": float(target_weight),   # 追加
    "target_date": target_date.isoformat(),  # 追加
    "daily_calorie_adjustment": ...,
    "target_calories": ...,
    ...
}
```

### 教訓
- API のレスポンスには、フロントエンドが表示に使用する全てのフィールドを含める
- 特に入力値（target_weight, target_date など）はレスポンスにエコーバックすると確認しやすい

---

## 問題 #14: 食事記録 - 登録したが表示されない

### 発生日時
2025-12-10

### 症状
食事記録（ご飯など）を追加したが、食事記録一覧で「該当する食事記録がありません」と表示される。

### 調査結果
CloudWatch ログで食事記録の作成は成功（meal_id が発行されている）。DynamoDB にもデータが存在。しかしリスト取得クエリが 0 件を返す。

### 根本原因
DynamoDB の日付範囲クエリで、文字列比較の問題が発生。

| 変数 | 値 |
|------|-----|
| `start_date` (クエリ) | `"2025-12-10"` |
| `end_date` (クエリ) | `"2025-12-10"` |
| `timestamp` (DB) | `"2025-12-10T08:23:38.957100"` |

BETWEEN 条件 `"2025-12-10" <= "2025-12-10T..." <= "2025-12-10"` は **FALSE**。

理由: 文字列比較では `"2025-12-10T..." > "2025-12-10"` （"T" > 空文字）

### 解決方法

#### コード修正（src/lambda/meal_registration/__init__.py 239-244行目）
```python
# 日付のみの形式（YYYY-MM-DD）の場合、時刻を付与
# start_date は 00:00:00 から、end_date は 23:59:59.999999 までを含める
if start_date and "T" not in start_date:
    start_date = f"{start_date}T00:00:00"
if end_date and "T" not in end_date:
    end_date = f"{end_date}T23:59:59.999999"
```

### 教訓
- ISO 8601 形式の日付文字列比較では、日付のみ（YYYY-MM-DD）とタイムスタンプ（YYYY-MM-DDTHH:MM:SS）の混在に注意
- 日付範囲クエリでは、`end_date` に時刻を含めて「その日の終わり」まで含めるようにする
- DynamoDB の文字列比較は辞書順であることを忘れない

---

## 修正サマリー（2025-12-10 追加分 #3）

| # | エラー | 原因 | 修正ファイル |
|---|--------|------|-------------|
| 13 | 目標作成で "Invalid Date" | レスポンスに target_date 等が欠落 | `goal_management/__init__.py:243-256` |
| 14 | 食事記録が表示されない | 日付文字列比較の不一致 | `meal_registration/__init__.py:239-244` |

---

## チェックリスト（更新）

### 日付・時刻処理
- [ ] 日付範囲クエリで `YYYY-MM-DD` 形式を使用する場合、`end_date` に時刻を付与して「その日の終わり」まで含めているか
- [ ] ISO 8601 形式の文字列比較が意図した通りに動作するか確認したか

---

## 問題 #15: 食事記録UIで食品名・単位・栄養情報が表示されない

### 発生日時
2025-12-10

### 症状
LIFF Web App の食事記録一覧で以下の問題が発生：
1. 何を食べたか分からない（食品名が表示されない）
2. 「100」「150」など数字だけで単位が不明
3. 時間が日本時間ではない
4. 更新日時が「Invalid Date」と表示される

### 根本原因
`MealFood` および `Meal` モデルに必要なフィールドが定義されていなかった。

| モデル | 欠落フィールド | 問題 |
|--------|--------------|------|
| `MealFood` | `name` | 食品名が保存されない |
| `MealFood` | `unit` | 単位が保存されない |
| `MealFood` | `calories`, `protein`, `fat`, `carbs` | 各食品の栄養情報が保存されない |
| `Meal` | `updated_at` | 更新日時が保存されない |

食事記録作成時に食品マスタから名前を取得して保存する処理も欠落していた。

### 解決方法

#### 1. MealFood モデル拡張（src/lambda/common/models.py）
```python
@dataclass
class MealFood:
    food_id: str
    amount: float
    name: Optional[str] = None           # 追加
    unit: str = "g"                       # 追加
    calories: Optional[float] = None     # 追加
    protein: Optional[float] = None      # 追加
    fat: Optional[float] = None          # 追加
    carbs: Optional[float] = None        # 追加
```

#### 2. Meal モデルに updated_at 追加（src/lambda/common/models.py）
```python
@dataclass
class Meal:
    # ... 既存フィールド ...
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None  # 追加
```

#### 3. create_meal で食品名と栄養情報を保存（src/lambda/meal_registration/__init__.py）
```python
# 各食品に名前と計算済み栄養情報を追加（表示用）
for meal_food in meal_foods:
    food = food_database.get(meal_food.food_id)
    if food:
        meal_food.name = food.name
        ratio = meal_food.amount / 100.0
        meal_food.calories = food.calories_per_100g * ratio
        meal_food.protein = food.protein_per_100g * ratio
        meal_food.fat = food.fat_per_100g * ratio
        meal_food.carbs = food.carbs_per_100g * ratio
```

#### 4. update_meal で updated_at を設定
```python
updated_data["updated_at"] = datetime.utcnow().isoformat()
```

### 教訓
- 表示に必要なデータは非正規化して保存する（食品名、計算済み栄養情報）
- リレーショナルDBのような正規化は NoSQL では必ずしも最適ではない
- `updated_at` フィールドは CRUD 操作を行うモデルでは必須

---

## 問題 #16: 食事記録の削除でDynamoDBエラー

### 発生日時
2025-12-10

### 症状
LIFF Web App で食事記録を削除しようとすると以下のエラーが表示される：
```
食事記録の削除：DynamoDB操作に失敗しました：meal-management-app-meals-dev
```

### 根本原因
Meals テーブルは**複合キーテーブル**（PK + SK）だが、`get_item` と `delete_item` が PK（`meal_id`）のみを指定していた。

| キータイプ | 属性名 | 値の例 |
|-----------|--------|--------|
| Partition Key (PK) | `meal_id` | `abc-123-def-456` |
| Sort Key (SK) | `user_id_timestamp` | `user-001#2025-12-10T12:00:00` |

DynamoDB の複合キーテーブルでは、`get_item` と `delete_item` に**両方のキーが必須**。

### CloudWatchログ
```
ValidationException: The provided key element does not match the schema
```

### 解決方法

#### 1. ヘルパー関数 `_find_meal_by_id` を追加（src/lambda/meal_registration/__init__.py）
```python
def _find_meal_by_id(meal_id: str) -> Optional[Dict[str, Any]]:
    """
    meal_id でスキャンして食事記録を取得する

    複合キーテーブル (PK: meal_id, SK: user_id_timestamp) のため、
    meal_id だけでは get_item が使えない。スキャンで検索する。

    Note:
        DynamoDB Scan の Limit はフィルタ適用前に評価されるため、
        Limit を使うとフィルタ条件に一致するアイテムを見つけられない可能性がある。
        そのため Limit を使わず全件スキャンし、一致したら即座に返す。
    """
    last_evaluated_key = None
    while True:
        scan_params = {
            "FilterExpression": "meal_id = :meal_id",
            "ExpressionAttributeValues": {":meal_id": meal_id}
        }
        if last_evaluated_key:
            scan_params["ExclusiveStartKey"] = last_evaluated_key

        response = meals_db.table.scan(**scan_params)
        items = response.get("Items", [])

        if items:
            # Decimal を float に変換して返す
            return convert_decimals(items[0])

        last_evaluated_key = response.get("LastEvaluatedKey")
        if not last_evaluated_key:
            break

    return None
```

#### 2. delete_meal を修正して複合キーで削除
```python
def delete_meal(event: Dict[str, Any]) -> Dict[str, Any]:
    # スキャンで食事記録を取得
    existing_meal_data = _find_meal_by_id(meal_id)

    if not existing_meal_data:
        raise ResourceNotFoundError(...)

    # 複合キーで削除（PK: meal_id, SK: user_id_timestamp）
    user_id_timestamp = existing_meal_data.get("user_id_timestamp")
    meals_db.delete_item({
        "meal_id": meal_id,
        "user_id_timestamp": user_id_timestamp
    })
```

#### 3. get_meal, update_meal も同様に修正
`_find_meal_by_id` を使用してアイテムを取得するように変更。

### DynamoDB Scan の Limit の落とし穴
最初の実装で `Limit=1` を使用したが、これは**フィルタ適用前**に評価される。

```python
# 誤った実装
response = meals_db.table.scan(
    FilterExpression="meal_id = :meal_id",
    ExpressionAttributeValues={":meal_id": meal_id},
    Limit=1  # ← 最初の1件をスキャンして終了（フィルタ後の1件ではない！）
)
```

例: テーブルに A, B, C の順でアイテムがあり、B を検索する場合
- `Limit=1` → A をスキャン → フィルタで除外 → 結果 0 件（B を見つけられない）

正しい実装は `Limit` を使わず、ページネーションで全件スキャンしてフィルタ一致したら終了。

### 教訓
- DynamoDB 複合キーテーブルでは `get_item`/`delete_item` に PK + SK の両方が必要
- PK のみでアイテムを探すには GSI または Scan が必要
- Scan の `Limit` はフィルタ適用**前**に評価される（フィルタ後の件数ではない）
- 大量データがある場合は GSI の方がパフォーマンスが良い

---

## 修正サマリー（2025-12-10 追加分 #4）

| # | エラー | 原因 | 修正ファイル |
|---|--------|------|-------------|
| 15 | 食品名・単位・栄養情報が表示されない | MealFood モデルにフィールド欠落 | `models.py`, `meal_registration/__init__.py` |
| 16 | 食事記録の削除でDynamoDBエラー | 複合キーテーブルで PK のみ指定 | `meal_registration/__init__.py` |

---

## 問題 #17: 食事記録の削除ボタンを押してもUIが更新されない

### 発生日時
2025-12-10

### 症状
LIFF Web App で食事記録の削除ボタンを押しても、画面上から消えない。何度クリックしても同じ状態のまま。

### 調査結果
CloudWatch ログを確認したところ、**削除自体は成功していた**：
```
08:59:05 - 食事記録を削除しました: f6350381-54aa-4f25-b54b-08635d4c6c2a ✅
08:59:21 - 食事記録を削除しました: 0db58b55-e742-4a59-83bf-222a0bc1704b ✅
```

2回目以降のクリックでは「食事記録が見つかりません」（既に削除済み）となっていた。

### 根本原因
`MealsPage.tsx` で `MealsList` コンポーネントに `onDeleteSuccess` コールバックが渡されていなかった。

```tsx
// 問題のコード（MealsPage.tsx:184）
<MealsList meals={meals} loading={loading} />
// onDeleteSuccess が渡されていない！
```

`MealsList` の削除処理：
```tsx
const handleDelete = async (mealId: string) => {
  await deleteMeal(mealId);  // ← 成功する
  onDeleteSuccess?.();       // ← undefined なので何も起きない
};
```

### 解決方法

#### コード修正（frontend/src/pages/MealsPage.tsx 184行目）
```tsx
// 修正前
<MealsList meals={meals} loading={loading} />

// 修正後
<MealsList meals={meals} loading={loading} onDeleteSuccess={handleReload} />
```

`handleReload` は `handleSearch()` を呼び出し、食事記録リストを再取得する。

### デプロイ手順
```bash
# フロントエンドをビルド
npm --prefix frontend run build

# S3 にデプロイ
aws s3 sync frontend/dist/ s3://meal-management-app-frontend-dev/ --delete

# CloudFront キャッシュを無効化
aws cloudfront create-invalidation \
  --distribution-id E36GJ9UHD72DBK \
  --paths "/*"
```

### 教訓
- React でコンポーネントにコールバックを渡す場合、**実際に渡されているか確認**する
- Optional chaining (`onDeleteSuccess?.()`) は便利だが、**コールバック未設定のバグを隠す**可能性がある
- UIが更新されない場合、**バックエンドのログを先に確認**すると原因特定が早い
- 「ボタンが効かない」≠「API が失敗」の場合がある（UIの状態管理の問題）

---

## 修正サマリー（2025-12-10 追加分 #5）

| # | エラー | 原因 | 修正ファイル |
|---|--------|------|-------------|
| 17 | 削除ボタンを押してもUIが更新されない | `onDeleteSuccess` コールバック未設定 | `frontend/src/pages/MealsPage.tsx:184` |

---

## チェックリスト（更新）

### DynamoDB 複合キーテーブル
- [ ] `get_item`/`delete_item` で PK と SK の両方を指定しているか
- [ ] PK のみでアイテムを探す場合、GSI または Scan を使用しているか
- [ ] Scan に `Limit` を使う場合、フィルタ適用前に評価されることを理解しているか

### データモデル設計
- [ ] 表示に必要なデータ（関連テーブルの情報）は非正規化して保存しているか
- [ ] `created_at` と `updated_at` フィールドがあるか

### React コンポーネント間通信
- [ ] 子コンポーネントのアクション後に親の状態更新が必要な場合、コールバック prop を渡しているか
- [ ] Optional chaining (`callback?.()`) を使う場合、コールバック未設定が意図的かどうか確認したか
- [ ] UIが更新されない問題では、まずバックエンドログを確認して API 成功/失敗を切り分けたか

---

**更新日**: 2025-12-10
