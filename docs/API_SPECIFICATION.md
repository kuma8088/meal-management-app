# API 仕様書

## 概要

食事管理アプリケーション REST API の仕様書です。

- **Base URL**: `https://868t2tljy9.execute-api.ap-northeast-1.amazonaws.com/dev`
- **認証**: Amazon Cognito JWT トークン（Authorization ヘッダー）

## 認証

すべてのエンドポイント（`/health` を除く）は Cognito JWT トークンによる認証が必要です。

```
Authorization: Bearer <id_token>
```

## エンドポイント一覧

### ユーザープロフィール

#### GET /users/{user_id}/profile

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

#### POST /users/{user_id}/profile

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

#### PUT /users/{user_id}/profile

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

---

### 食事記録

#### POST /users/{user_id}/meals

食事記録を作成

**リクエスト**:
```json
{
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

#### GET /users/{user_id}/meals

食事記録一覧を取得

**クエリパラメータ**:
- `start_date`: 開始日 (YYYY-MM-DD)
- `end_date`: 終了日 (YYYY-MM-DD)
- `limit`: 最大件数 (デフォルト: 50)

#### PUT /users/{user_id}/meals/{meal_id}

食事記録を更新

#### DELETE /users/{user_id}/meals/{meal_id}

食事記録を削除

---

### 体重目標

#### POST /users/{user_id}/goals

体重目標を作成

**リクエスト**:
```json
{
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

#### GET /users/{user_id}/goals

目標を取得

---

### 1日の総評

#### GET /users/{user_id}/summary/{date}

1日の食事サマリーとAIアドバイスを取得

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
