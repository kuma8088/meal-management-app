# 設計書

## 概要

本システムは、AWS サーバレスアーキテクチャを活用した食事管理アプリケーションです。LINE とブラウザの両方からアクセス可能で、食事記録の登録、栄養情報の自動計算、体重目標管理、AI による食事アドバイスを提供します。

主要な技術スタック：

- **インフラ管理**: Terraform
- **コンピューティング**: AWS Lambda (Python 3.11)
- **API**: AWS API Gateway (REST API)
- **データベース**: Amazon DynamoDB
- **ストレージ**: Amazon S3
- **認証**: Amazon Cognito, LINE User ID
- **AI**: Amazon Bedrock (Claude 3)
- **画像認識**: Amazon Rekognition または Amazon Textract
- **メッセージング**: LINE Messaging API
- **ロギング**: Amazon CloudWatch Logs
- **フロントエンド**: React (TypeScript)

## アーキテクチャ

### システム構成図

```
┌─────────────────┐         ┌─────────────────┐
│  LINE Client    │         │  Browser Client │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │                           │
         ├───────────────────────────┤
         │                           │
         ▼                           ▼
┌─────────────────────────────────────────────┐
│           AWS API Gateway                    │
│  ┌──────────────┐    ┌──────────────┐      │
│  │ LINE Webhook │    │  REST API    │      │
│  └──────────────┘    └──────────────┘      │
└────────┬──────────────────────┬─────────────┘
         │                      │
         ▼                      ▼
┌─────────────────────────────────────────────┐
│           AWS Lambda Functions               │
│  ┌──────────────────────────────────────┐   │
│  │ - LINE Handler                       │   │
│  │ - Meal Registration                  │   │
│  │ - Food Search                        │   │
│  │ - Barcode Recognition                │   │
│  │ - Nutrition Calculation              │   │
│  │ - BMR/TDEE Calculation               │   │
│  │ - Goal Management                    │   │
│  │ - Daily Summary & AI Advice          │   │
│  │ - User Profile Management            │   │
│  │ - Food Master Data Import            │   │
│  └──────────────────────────────────────┘   │
└────┬────────────┬────────────┬──────────────┘
     │            │            │
     ▼            ▼            ▼
┌─────────┐  ┌─────────┐  ┌──────────────┐
│DynamoDB │  │   S3    │  │   Bedrock    │
│         │  │         │  │   Claude 3   │
│- Users  │  │- Food   │  │              │
│- Meals  │  │  Master │  └──────────────┘
│- Foods  │  │  CSV    │
│- Goals  │  │- Images │
└─────────┘  └─────────┘
     │
     ▼
┌─────────────────┐
│  CloudWatch     │
│  Logs/Metrics   │
└─────────────────┘
```

### データフロー

1. **食事登録フロー（LINE）**

   - ユーザーが LINE Bot にメッセージまたは画像を送信
   - API Gateway が Webhook を受信
   - LINE Handler Lambda がメッセージを解析
   - バーコード画像の場合、Rekognition で JAN コード抽出
   - Food Search Lambda で食品マスタを検索
   - 見つからない場合、Bedrock で AI 検索
   - Meal Registration Lambda で食事記録を作成
   - Nutrition Calculation Lambda で栄養情報を計算
   - DynamoDB に保存
   - LINE Messaging API で確認メッセージを返信

2. **食事登録フロー（ブラウザ）**

   - ユーザーがブラウザで食品を検索
   - API Gateway 経由で Food Search Lambda を呼び出し
   - 食品マスタから候補を取得
   - ユーザーが食品と量を選択
   - Meal Registration Lambda で食事記録を作成
   - Nutrition Calculation Lambda で栄養情報を計算
   - DynamoDB に保存
   - ブラウザに確認メッセージを表示

3. **AI アドバイス生成フロー**
   - ユーザーが総評をリクエスト
   - Daily Summary Lambda が 1 日の食事記録を集計
   - 利用回数制限（1 日 2 回）をチェック
   - 目標カロリーとの差分を計算
   - Bedrock Claude API を呼び出し
   - S3 の食品マスタ CSV を参照情報として提供
   - 300 文字以内のアドバイスを生成
   - DynamoDB に利用回数を記録
   - ユーザーにアドバイスを返す

## コンポーネントとインターフェース

### Lambda 関数

#### 1. LINE Handler (`line_handler`)

**責務**: LINE Webhook を処理し、適切なハンドラーに振り分ける

**入力**:

```python
{
    "events": [
        {
            "type": "message",
            "message": {
                "type": "text" | "image",
                "text": str,  # テキストメッセージの場合
                "id": str     # 画像メッセージの場合
            },
            "source": {
                "userId": str
            }
        }
    ]
}
```

**出力**:

```python
{
    "statusCode": 200,
    "body": str
}
```

#### 2. Meal Registration (`meal_registration`)

**責務**: 食事記録を作成し、DynamoDB に保存する

**入力**:

```python
{
    "user_id": str,
    "foods": [
        {
            "food_id": str,
            "amount": float  # グラム単位
        }
    ],
    "meal_type": str,  # "breakfast", "lunch", "dinner", "snack"
    "timestamp": str   # ISO 8601形式
}
```

**出力**:

```python
{
    "meal_id": str,
    "total_calories": float,
    "total_protein": float,
    "total_fat": float,
    "total_carbs": float,
    "created_at": str
}
```

#### 3. Food Search (`food_search`)

**責務**: 食品マスタを検索し、候補リストを返す

**入力**:

```python
{
    "query": str,           # 食品名またはJANコード
    "search_type": str,     # "name" | "jan_code"
    "use_ai": bool          # AI検索を使用するか
}
```

**出力**:

```python
{
    "foods": [
        {
            "food_id": str,
            "name": str,
            "calories_per_100g": float,
            "protein_per_100g": float,
            "fat_per_100g": float,
            "carbs_per_100g": float,
            "jan_code": str | None,
            "source": str  # "STANDARD" | "OPEN_FOOD_FACTS" | "AI_GENERATED"
        }
    ]
}
```

#### 4. Barcode Recognition (`barcode_recognition`)

**責務**: 画像から JAN コードを抽出する

**入力**:

```python
{
    "image_url": str  # LINE Content APIのURL
}
```

**出力**:

```python
{
    "jan_code": str | None,
    "confidence": float
}
```

#### 5. Nutrition Calculation (`nutrition_calculation`)

**責務**: 食事の栄養情報を計算する

**入力**:

```python
{
    "foods": [
        {
            "food_id": str,
            "amount": float
        }
    ]
}
```

**出力**:

```python
{
    "total_calories": float,
    "total_protein": float,
    "total_fat": float,
    "total_carbs": float
}
```

#### 6. BMR/TDEE Calculation (`bmr_tdee_calculation`)

**責務**: 基礎代謝と総消費カロリーを計算する

**入力**:

```python
{
    "age": int,
    "height": float,  # cm
    "weight": float,  # kg
    "gender": str,    # "male" | "female"
    "activity_level": str  # "sedentary" | "light" | "moderate" | "active" | "very_active"
}
```

**出力**:

```python
{
    "bmr": float,
    "tdee": float
}
```

#### 7. Goal Management (`goal_management`)

**責務**: 体重目標を管理し、目標カロリーを計算する

**入力**:

```python
{
    "user_id": str,
    "current_weight": float,
    "target_weight": float,
    "target_date": str,  # ISO 8601形式
    "goal_type": str     # "gain" | "maintain" | "lose"
}
```

**出力**:

```python
{
    "goal_id": str,
    "daily_calorie_adjustment": float,
    "target_calories": float,
    "recommended_protein": float,
    "recommended_fat": float,
    "recommended_carbs": float,
    "recommended_exercise_minutes": int,
    "warning": str | None  # 非現実的な目標の場合
}
```

#### 8. Daily Summary & AI Advice (`daily_summary_advice`)

**責務**: 1 日の食事を集計し、AI アドバイスを生成する

**入力**:

```python
{
    "user_id": str,
    "date": str  # YYYY-MM-DD形式
}
```

**出力**:

```python
{
    "total_calories": float,
    "total_protein": float,
    "total_fat": float,
    "total_carbs": float,
    "target_calories": float,
    "calorie_difference": float,
    "advice": str,  # 300文字以内
    "usage_count": int,  # 今日の利用回数
    "usage_limit_reached": bool
}
```

#### 9. User Profile Management (`user_profile_management`)

**責務**: ユーザープロフィールを管理する

**入力**:

```python
{
    "user_id": str,
    "action": str,  # "create" | "get" | "update"
    "profile": {
        "age": int,
        "height": float,
        "weight": float,
        "gender": str,
        "activity_level": str
    }
}
```

**出力**:

```python
{
    "user_id": str,
    "profile": {...},
    "bmr": float,
    "tdee": float,
    "updated_at": str
}
```

#### 10. Food Master Data Import (`food_master_import`)

**責務**: 日本食品標準成分表と Open Food Facts からデータをインポートする

**入力**:

```python
{
    "source": str,  # "standard" | "open_food_facts"
    "batch_size": int
}
```

**出力**:

```python
{
    "imported_count": int,
    "failed_count": int,
    "errors": [str]
}
```

### DynamoDB テーブル設計

#### 1. Users テーブル

```
PK: user_id (String)
Attributes:
- line_user_id (String, optional)
- cognito_user_id (String, optional)
- age (Number)
- height (Number)
- weight (Number)
- gender (String)
- activity_level (String)
- bmr (Number)
- tdee (Number)
- created_at (String)
- updated_at (String)
```

#### 2. Meals テーブル

```
PK: meal_id (String)
SK: user_id#timestamp (String)
Attributes:
- user_id (String)
- meal_type (String)
- foods (List)
  - food_id (String)
  - amount (Number)
- total_calories (Number)
- total_protein (Number)
- total_fat (Number)
- total_carbs (Number)
- timestamp (String)
- created_at (String)

GSI1:
- PK: user_id (String)
- SK: timestamp (String)
```

#### 3. Foods テーブル

```
PK: food_id (String)
Attributes:
- name (String)
- calories_per_100g (Number)
- protein_per_100g (Number)
- fat_per_100g (Number)
- carbs_per_100g (Number)
- jan_code (String, optional)
- source (String)  # "STANDARD" | "OPEN_FOOD_FACTS" | "AI_GENERATED"
- created_at (String)
- updated_at (String)

GSI1:
- PK: name (String)
- SK: food_id (String)

GSI2:
- PK: jan_code (String)
- SK: food_id (String)
```

#### 4. Goals テーブル

```
PK: goal_id (String)
SK: user_id (String)
Attributes:
- user_id (String)
- current_weight (Number)
- target_weight (Number)
- target_date (String)
- goal_type (String)
- daily_calorie_adjustment (Number)
- target_calories (Number)
- recommended_protein (Number)
- recommended_fat (Number)
- recommended_carbs (Number)
- recommended_exercise_minutes (Number)
- created_at (String)
- updated_at (String)

GSI1:
- PK: user_id (String)
- SK: created_at (String)
```

#### 5. AdviceUsage テーブル

```
PK: user_id#date (String)
Attributes:
- user_id (String)
- date (String)  # YYYY-MM-DD
- usage_count (Number)
- last_used_at (String)
```

### S3 バケット構成

```
meal-management-app-{environment}/
├── food-master/
│   ├── standard_foods.csv
│   └── open_food_facts.csv
├── barcode-images/
│   └── {user_id}/
│       └── {timestamp}.jpg
└── terraform-state/
    └── terraform.tfstate
```

### API Gateway エンドポイント

#### REST API エンドポイント

```
POST   /meals                    # 食事記録を作成
GET    /meals                    # 食事記録を取得
GET    /meals/{meal_id}          # 特定の食事記録を取得
PUT    /meals/{meal_id}          # 食事記録を更新
DELETE /meals/{meal_id}          # 食事記録を削除

GET    /foods/search             # 食品を検索
GET    /foods/{food_id}          # 特定の食品を取得

POST   /users/profile            # ユーザープロフィールを作成
GET    /users/profile            # ユーザープロフィールを取得
PUT    /users/profile            # ユーザープロフィールを更新

POST   /goals                    # 体重目標を作成
GET    /goals                    # 体重目標を取得
PUT    /goals/{goal_id}          # 体重目標を更新

POST   /advice/daily             # 1日の総評とアドバイスを取得

POST   /line/webhook             # LINE Webhook
```

## データモデル

### エンティティ関係図

```
┌─────────────┐
│    User     │
└──────┬──────┘
       │
       │ 1:N
       │
       ▼
┌─────────────┐      N:M      ┌─────────────┐
│    Meal     │◄──────────────►│    Food     │
└─────────────┘                └─────────────┘
       │
       │ 1:1
       │
       ▼
┌─────────────┐
│    Goal     │
└─────────────┘
```

### ドメインモデル

#### User

```python
class User:
    user_id: str
    line_user_id: Optional[str]
    cognito_user_id: Optional[str]
    age: int
    height: float  # cm
    weight: float  # kg
    gender: Literal["male", "female"]
    activity_level: Literal["sedentary", "light", "moderate", "active", "very_active"]
    bmr: float
    tdee: float
    created_at: datetime
    updated_at: datetime
```

#### Meal

```python
class MealFood:
    food_id: str
    amount: float  # グラム

class Meal:
    meal_id: str
    user_id: str
    meal_type: Literal["breakfast", "lunch", "dinner", "snack"]
    foods: List[MealFood]
    total_calories: float
    total_protein: float
    total_fat: float
    total_carbs: float
    timestamp: datetime
    created_at: datetime
```

#### Food

```python
class Food:
    food_id: str
    name: str
    calories_per_100g: float
    protein_per_100g: float
    fat_per_100g: float
    carbs_per_100g: float
    jan_code: Optional[str]
    source: Literal["STANDARD", "OPEN_FOOD_FACTS", "AI_GENERATED"]
    created_at: datetime
    updated_at: datetime
```

#### Goal

```python
class Goal:
    goal_id: str
    user_id: str
    current_weight: float
    target_weight: float
    target_date: date
    goal_type: Literal["gain", "maintain", "lose"]
    daily_calorie_adjustment: float
    target_calories: float
    recommended_protein: float
    recommended_fat: float
    recommended_carbs: float
    recommended_exercise_minutes: int
    created_at: datetime
    updated_at: datetime
```

#### AdviceUsage

```python
class AdviceUsage:
    user_id: str
    date: date
    usage_count: int
    last_used_at: datetime
```

## 正確性プロパティ

_プロパティとは、システムのすべての有効な実行において真であるべき特性または動作のことです。本質的には、システムが何をすべきかについての形式的な記述です。プロパティは、人間が読める仕様と機械で検証可能な正確性保証との橋渡しとなります。_

### プロパティ 1: ユーザーデータ分離

*任意の*ユーザーが食事記録を取得する場合、返される記録はすべてそのユーザーの user_id と関連付けられている必要があります。他のユーザーの記録が含まれてはいけません。

**検証: 要件 1.4**

### プロパティ 2: 食事記録とユーザーの関連付け

*任意の*食事記録が作成される場合、その記録は認証されたユーザー ID と関連付けられて保存される必要があります。

**検証: 要件 1.3**

### プロパティ 3: 食品マスタのデータ同期

*任意の*食品データが DynamoDB に登録される場合、同じデータが CSV 形式で S3 バケットにも保存される必要があります。

**検証: 要件 2.3**

### プロパティ 4: 食品マスタの必須フィールド

*任意の*食品レコードは、食品名、カロリー（100g あたり）、タンパク質（g）、脂質（g）、炭水化物（g）のすべてのフィールドを持つ必要があります。

**検証: 要件 2.5**

### プロパティ 5: AI 検索結果のマーキング

*任意の*AI 検索によって見つかった食品は、DynamoDB に保存される際にデータソースフィールドが「AI_GENERATED」に設定される必要があります。

**検証: 要件 3.4, 3.5**

### プロパティ 6: 食品検索のキャッシング

*任意の*食品が一度 AI 検索で見つかった場合、同じ食品の 2 回目の検索では DynamoDB のキャッシュから結果が返され、Bedrock API は呼び出されない必要があります。

**検証: 要件 3.6**

### プロパティ 7: 食品名の部分一致検索

*任意の*検索クエリに対して、食品名に検索クエリが部分文字列として含まれるすべての食品が検索結果に含まれる必要があります。

**検証: 要件 4.1**

### プロパティ 8: JAN コードの完全一致検索

*任意の*JAN コード検索に対して、その JAN コードと完全に一致する食品のみが検索結果に含まれる必要があります。

**検証: 要件 4.2**

### プロパティ 9: 検索結果の必須情報

*任意の*検索結果リストの各食品は、食品名、カロリー、タンパク質、脂質、炭水化物の情報を含む必要があります。

**検証: 要件 4.3**

### プロパティ 10: 食事記録の保存

*任意の*有効な食事情報が送信される場合、システムは食事記録を作成してデータベースに保存する必要があります。

**検証: 要件 6.1**

### プロパティ 11: 栄養情報の自動計算

*任意の*食事記録が作成される場合、システムは食品マスタを参照してカロリー、タンパク質、脂質、炭水化物を自動的に計算する必要があります。

**検証: 要件 6.3, 7.1, 7.2, 7.3, 7.4**

### プロパティ 12: 複数食品の栄養情報合計

*任意の*複数の食品を含む食事記録に対して、総カロリー、総タンパク質、総脂質、総炭水化物は各食品の栄養情報の合計と等しい必要があります。

**検証: 要件 7.5**

### プロパティ 13: BMR 計算の正確性

*任意の*年齢、身長、体重、性別の組み合わせに対して、システムは Harris-Benedict 式を使用して正しく BMR を計算する必要があります。

**検証: 要件 8.1**

### プロパティ 14: TDEE 計算の正確性

*任意の*BMR と活動レベルの組み合わせに対して、システムは正しい活動係数を乗じて TDEE を算出する必要があります。

**検証: 要件 8.2**

### プロパティ 15: プロフィール更新時の再計算

*任意の*ユーザープロフィール更新に対して、システムは自動的に BMR と TDEE を再計算する必要があります。

**検証: 要件 8.3**

### プロパティ 16: カロリー調整量の計算

*任意の*現在の体重、目標体重、目標時期の組み合わせに対して、システムは 1 日あたりの必要カロリー調整量を正しく計算する必要があります。

**検証: 要件 9.2**

### プロパティ 17: 目標カロリーの計算

*任意の*TDEE とカロリー調整量の組み合わせに対して、目標カロリーは TDEE に調整量を加算または減算した値と等しい必要があります。

**検証: 要件 9.3**

### プロパティ 18: PFC バランスの計算

*任意の*目標カロリーに対して、システムは推奨されるタンパク質、脂質、炭水化物のバランスを計算する必要があります。

**検証: 要件 9.4**

### プロパティ 19: 非現実的な目標の警告

*任意の*目標が週あたり 0.5kg を超える体重変化を要求する場合、システムは警告メッセージを表示する必要があります。

**検証: 要件 9.6**

### プロパティ 20: アドバイス生成の利用制限

*任意の*ユーザーが 1 日に 2 回アドバイスを生成した後、3 回目のリクエストは利用制限メッセージを返す必要があります。

**検証: 要件 10.3**

### プロパティ 21: 1 日の食事集計

*任意の*日付に対して、その日のすべての食事記録の総カロリー、総タンパク質、総脂質、総炭水化物は各食事の栄養情報の合計と等しい必要があります。

**検証: 要件 10.4**

### プロパティ 22: アドバイスの文字数制限

*任意の*生成されたアドバイスは 300 文字以内である必要があります。300 文字を超える場合は切り詰められる必要があります。

**検証: 要件 10.6, 10.7**

### プロパティ 23: アドバイス生成回数のカウンター更新

*任意の*アドバイスが正常に生成される場合、ユーザーの 1 日のアドバイス生成回数が 1 増加する必要があります。

**検証: 要件 10.8**

### プロパティ 24: データ整合性の検証

*任意の*データが保存される場合、システムはデータの整合性を検証する必要があります。無効なデータは拒否される必要があります。

**検証: 要件 12.2**

### プロパティ 25: 期間フィルタリング

*任意の*期間指定に対して、返される食事記録はすべて指定された期間内のタイムスタンプを持つ必要があります。

**検証: 要件 12.3**

### プロパティ 26: API リクエストの検証

*任意の*API リクエストに対して、システムはリクエストの形式を検証し、無効なリクエストは適切な HTTP ステータスコードとエラーメッセージを返す必要があります。

**検証: 要件 13.2, 13.3**

## エラーハンドリング

### エラーの分類

1. **バリデーションエラー**

   - 無効な入力データ（負の値、範囲外の値など）
   - 必須フィールドの欠落
   - 不正な形式のデータ

2. **認証・認可エラー**

   - 未認証のリクエスト
   - 権限不足
   - 無効なトークン

3. **データ整合性エラー**

   - 存在しないリソースへの参照
   - 重複データの作成
   - 外部キー制約違反

4. **外部サービスエラー**

   - Bedrock API 呼び出しの失敗
   - LINE Messaging API 呼び出しの失敗
   - Rekognition/Textract 呼び出しの失敗
   - DynamoDB 操作の失敗

5. **システムエラー**
   - タイムアウト
   - メモリ不足
   - 予期しない例外

### エラーハンドリング戦略

#### リトライロジック

外部 API 呼び出しには指数バックオフを使用したリトライを実装：

```python
def exponential_backoff_retry(func, max_retries=3, base_delay=1):
    for attempt in range(max_retries):
        try:
            return func()
        except RetryableError as e:
            if attempt == max_retries - 1:
                raise
            delay = base_delay * (2 ** attempt)
            time.sleep(delay)
```

リトライ対象：

- Bedrock API 呼び出し（最大 3 回）
- DynamoDB 操作（最大 3 回）
- S3 操作（最大 3 回）

リトライ非対象：

- バリデーションエラー
- 認証エラー
- 4xx クライアントエラー

#### エラーレスポンス形式

```python
{
    "error": {
        "code": str,  # エラーコード
        "message": str,  # ユーザー向けメッセージ
        "details": dict,  # 詳細情報（オプション）
        "request_id": str  # リクエストID
    }
}
```

#### ロギング

すべてのエラーは CloudWatch Logs に記録：

```python
logger.error(
    "Error occurred",
    extra={
        "error_type": type(e).__name__,
        "error_message": str(e),
        "user_id": user_id,
        "request_id": request_id,
        "stack_trace": traceback.format_exc()
    }
)
```

#### アラート

重大なエラーは SNS トピックを通じて管理者に通知：

- Lambda 関数のエラー率が 10%を超える
- DynamoDB 操作の失敗率が 5%を超える
- Bedrock API 呼び出しの失敗率が 20%を超える

## テスト戦略

### ユニットテスト

各 Lambda 関数とビジネスロジックに対してユニットテストを実装します。

**対象**:

- 栄養計算ロジック
- BMR/TDEE 計算ロジック
- 目標カロリー計算ロジック
- バリデーションロジック
- データ変換ロジック

**ツール**: pytest

**カバレッジ目標**: 80%以上

### プロパティベーステスト

正確性プロパティを検証するためにプロパティベーステストを実装します。

**ツール**: Hypothesis (Python)

**設定**: 各プロパティテストは最低 100 回の反復を実行

**プロパティテストの実装例**:

```python
from hypothesis import given, strategies as st

# プロパティ 12: 複数食品の栄養情報合計
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
    meal = create_meal(foods)
    expected_total = sum(cal * (amt / 100) for cal, amt in foods)
    assert abs(meal.total_calories - expected_total) < 0.01
```

各プロパティテストには、設計書のプロパティ番号を参照するコメントを含めます：

- フォーマット: `Feature: {feature_name}, Property {number}: {property_text}`

### 統合テスト

エンドツーエンドのフローを検証する統合テストを実装します。

**対象**:

- LINE Webhook からの食事登録フロー
- ブラウザからの食事登録フロー
- バーコード読み取りフロー
- AI アドバイス生成フロー
- 食品マスタインポートフロー

**ツール**: pytest + moto (AWS サービスのモック)

### E2E テスト

ブラウザ UI を含むエンドツーエンドのユーザーフローを検証します。

**対象**:

- ユーザー登録とログインフロー
- 食品検索と食事登録フロー
- 体重目標設定フロー
- 1 日の総評表示フロー
- 過去の食事記録閲覧フロー

**ツール**: Playwright (TypeScript)

### パフォーマンステスト

**目標**:

- Lambda 関数の実行時間: 3 秒以内（Bedrock 呼び出しを除く）
- API Gateway レスポンスタイム: 500ms 以内（Bedrock 呼び出しを除く）
- DynamoDB 読み取り: 100ms 以内
- DynamoDB 書き込み: 200ms 以内

**ツール**: Locust

### セキュリティテスト

**対象**:

- 認証・認可の検証
- SQL インジェクション対策（該当する場合）
- XSS 対策
- CSRF 対策
- 入力バリデーション

**ツール**: OWASP ZAP, Bandit

## デプロイメント戦略

### 環境

- **開発環境 (dev)**: 開発者が機能開発とテストを行う環境
- **ステージング環境 (staging)**: 本番環境と同等の構成でテストを行う環境
- **本番環境 (prod)**: エンドユーザーが使用する環境

### CI/CD パイプライン

```
┌─────────────┐
│  Git Push   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Lint &     │
│  Format     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Unit Tests │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Property   │
│  Tests      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Build      │
│  Lambda     │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Terraform  │
│  Plan       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Deploy to  │
│  Dev        │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Integration│
│  Tests      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Manual     │
│  Approval   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Deploy to  │
│  Staging    │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Smoke      │
│  Tests      │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Manual     │
│  Approval   │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Deploy to  │
│  Prod       │
└──────┬──────┘
       │
       ▼
┌─────────────┐
│  Monitor    │
└─────────────┘
```

### ロールバック戦略

- Lambda 関数のバージョニングとエイリアスを使用
- Terraform の state ファイルをバージョン管理
- 問題発生時は前のバージョンに即座に切り替え可能

### モニタリング

**メトリクス**:

- Lambda 関数の実行時間、エラー率、同時実行数
- API Gateway のリクエスト数、レイテンシ、エラー率
- DynamoDB の読み取り/書き込みキャパシティ、スロットリング
- Bedrock API の呼び出し回数、レイテンシ、エラー率

**ダッシュボード**: CloudWatch Dashboard

**アラート**: CloudWatch Alarms + SNS

## セキュリティ考慮事項

### 認証・認可

- **LINE**: LINE User ID を使用してユーザーを識別
- **ブラウザ**: Amazon Cognito を使用してユーザーを認証
- **API**: JWT トークンを使用して API リクエストを認証

### データ暗号化

- **転送中**: すべての API 通信は HTTPS/TLS を使用
- **保管中**: DynamoDB の暗号化を有効化、S3 バケットの暗号化を有効化

### IAM ロール

最小権限の原則に従い、各 Lambda 関数に必要最小限の権限のみを付与：

```hcl
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_policy"
  role = aws_iam_role.lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:Query"
        ]
        Resource = aws_dynamodb_table.meals.arn
      }
    ]
  })
}
```

### 入力バリデーション

すべてのユーザー入力を検証：

- 型チェック
- 範囲チェック
- 形式チェック
- サニタイゼーション

### シークレット管理

- API キー、トークンは AWS Secrets Manager に保存
- 環境変数として Lambda 関数に注入
- コードにハードコードしない

## スケーラビリティ考慮事項

### Lambda 関数

- 同時実行数の制限を設定（予期しないコスト増加を防ぐ）
- プロビジョニング済み同時実行数を使用（コールドスタート対策）

### DynamoDB

- オンデマンドキャパシティモードを使用（トラフィックの変動に対応）
- GSI を適切に設計（クエリパフォーマンスの最適化）
- TTL を使用（古いデータの自動削除）

### API Gateway

- スロットリング設定（DDoS 対策）
- キャッシング（頻繁にアクセスされるデータ）

### S3

- CloudFront を使用（食品マスタ CSV の配信）
- ライフサイクルポリシー（古い画像の自動削除）

## コスト最適化

### Lambda

- メモリサイズの最適化（実行時間とコストのバランス）
- 不要なログ出力の削減

### DynamoDB

- オンデマンドモードとプロビジョニングモードの選択
- 不要な GSI の削除

### Bedrock

- キャッシング戦略（同じ食品の重複検索を避ける）
- 利用回数制限（1 日 2 回まで）

### S3

- ライフサイクルポリシー（古いデータを Glacier に移動）
- 不要なデータの定期的な削除

## 今後の拡張性

### 機能拡張

- 食事の写真認識（画像から食品を自動識別）
- 体重記録と推移グラフ
- 運動記録と消費カロリー計算
- 友達との食事記録共有
- 栄養士によるアドバイス機能

### 技術的改善

- GraphQL API の導入
- リアルタイム通知（WebSocket）
- マイクロサービス化
- マルチリージョン対応
