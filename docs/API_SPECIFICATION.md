# API 仕様書

## 概要

食事管理アプリケーション REST API の仕様書です。

- **Base URL**: `https://{api-id}.execute-api.{region}.amazonaws.com/{stage}`
  - `terraform output api_gateway_url` で取得可能
- **認証**: Amazon Cognito JWT トークン（Authorization ヘッダー）

## 認証

すべてのエンドポイント（`/health` を除く）は Cognito JWT トークンによる認証が必要です。

```
Authorization: Bearer <id_token>
```

## エンドポイント一覧

### ユーザープロフィール

#### POST /users

ユーザープロフィールを作成

**リクエスト**:
```json
{
  "age": 30,
  "height": 170.0,
  "weight": 65.0,
  "gender": "male",
  "activity_level": "moderate"
}
```

**activity_level の値**:
- `sedentary`: 座り仕事中心（係数 1.2）
- `light`: 軽い運動（係数 1.375）
- `moderate`: 中程度の運動（係数 1.55）
- `active`: 活発な運動（係数 1.725）
- `very_active`: 非常に活発（係数 1.9）

#### GET /users/{user_id}

ユーザープロフィールを取得

**レスポンス (200)**:
```json
{
  "user_id": "string",
  "age": 30,
  "height": 170.0,
  "weight": 65.0,
  "gender": "male",
  "activity_level": "moderate",
  "bmr": 1600.5,
  "tdee": 2480.8,
  "created_at": "2025-01-01T00:00:00Z",
  "updated_at": "2025-01-01T00:00:00Z"
}
```

#### PUT /users/{user_id}

ユーザープロフィールを更新（BMR/TDEE 自動再計算）

---

### 食品検索

#### GET /foods/search

食品を検索

**クエリパラメータ**:
- `query` (必須): 検索クエリ
- `search_type`: `name` | `jan_code` (デフォルト: `name`)
- `limit`: 最大件数 (デフォルト: 20)

**レスポンス (200)**:
```json
{
  "foods": [
    {
      "food_id": "uuid",
      "name": "白米",
      "calories_per_100g": 168.0,
      "protein_per_100g": 2.5,
      "fat_per_100g": 0.3,
      "carbs_per_100g": 37.1,
      "jan_code": null,
      "source": "japanese_standard"
    }
  ],
  "count": 1,
  "ai_search_available": false
}
```

**source の値**:
- `japanese_standard`: 日本食品標準成分表
- `AI_GENERATED`: AI検索結果（キャッシュ）

#### GET /foods/{food_id}

食品詳細を取得

---

### 食事記録

#### POST /meals

食事記録を作成

**リクエスト**:
```json
{
  "user_id": "uuid",
  "meal_type": "lunch",
  "foods": [
    {
      "food_id": "uuid",
      "amount_g": 150.0
    }
  ],
  "recorded_at": "2025-01-01T12:00:00Z"
}
```

**meal_type の値**:
- `breakfast`: 朝食
- `lunch`: 昼食
- `dinner`: 夕食
- `snack`: 間食

#### GET /meals

食事記録一覧を取得

**クエリパラメータ**:
- `user_id` (必須): ユーザーID
- `start_date`: 開始日 (YYYY-MM-DD)
- `end_date`: 終了日 (YYYY-MM-DD)
- `limit`: 最大件数 (デフォルト: 50)

#### GET /meals/{meal_id}

特定の食事記録を取得

#### PUT /meals/{meal_id}

食事記録を更新

#### DELETE /meals/{meal_id}

食事記録を削除

---

### 体重目標

#### POST /goals

体重目標を作成

**リクエスト**:
```json
{
  "user_id": "uuid",
  "goal_type": "lose",
  "target_weight": 60.0,
  "target_date": "2025-06-01"
}
```

**goal_type の値**:
- `lose`: 減量
- `maintain`: 維持
- `gain`: 増量

**レスポンス (201)**:
```json
{
  "goal_id": "uuid",
  "goal_type": "lose",
  "target_weight": 60.0,
  "target_date": "2025-06-01",
  "target_calories": 1800,
  "recommended_pfc": {
    "protein_g": 90,
    "fat_g": 50,
    "carbs_g": 225
  },
  "warnings": []
}
```

#### GET /goals/{goal_id}

目標を取得

#### GET /users/{user_id}/goals

ユーザーの目標一覧を取得

---

### 1日の総評

#### GET /advice/daily

1日の食事サマリーとAIアドバイスを取得

**クエリパラメータ**:
- `user_id` (必須): ユーザーID
- `date` (必須): 日付 (YYYY-MM-DD)

**レスポンス (200)**:
```json
{
  "date": "2025-01-01",
  "total_calories": 1850,
  "total_protein": 75.5,
  "total_fat": 55.2,
  "total_carbs": 230.0,
  "target_calories": 2000,
  "meals_count": 3,
  "advice": "今日の食事は良いバランスでした...",
  "advice_usage": {
    "used": 1,
    "limit": 2
  }
}
```

---

### LINE Webhook

#### POST /line/webhook

LINE Messaging API からの Webhook を受信

- 署名検証で認証（LINE Channel Secret を使用）
- リクエストボディは LINE プラットフォームからの Webhook イベント

---

### 認証（LINE ID 連携）

#### POST /auth/liff-login

LIFF から Cognito Custom Auth を開始

**リクエスト**:
```json
{
  "line_id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

**レスポンス (200)**:
```json
{
  "id_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "refresh_token": "eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9...",
  "expires_in": 3600
}
```

**処理フロー**:
1. LINE ID Token を受信
2. Cognito `InitiateAuth` (CUSTOM_AUTH) を呼び出し
3. Lambda Triggers で LINE ID Token を検証
4. 検証成功後、Cognito JWT Token を返却

---

### テストユーザー管理（開発環境のみ）

#### GET /test-users

E2E テスト用のテストユーザー一覧を取得

**レスポンス (200)**:
```json
{
  "users": [
    {
      "email": "e2e-test@example.com",
      "user_id": "uuid"
    }
  ]
}
```

---

## エラーレスポンス

```json
{
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Invalid request body",
    "details": {},
    "request_id": "uuid"
  }
}
```

**エラーコード**:
- `400`: バリデーションエラー
- `401`: 認証エラー
- `403`: 権限エラー
- `404`: リソースが見つからない
- `429`: レート制限超過
- `500`: サーバーエラー

---

## レート制限

- AIアドバイス生成: 1日2回まで
- API全体: 1000 req/sec（API Gateway デフォルト）
