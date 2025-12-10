# LINE Bot 食事登録機能（シンプル版）

## 概要

LINE Bot から「食品名 + 量」形式のメッセージを送信することで、食事を登録できる機能。

**実装日**: 2025-12-09

---

## 機能仕様

### 入力形式

以下の形式でメッセージを送信：

```
ご飯 150g
朝食 白米 200g
昼食 サラダ 100g
夕食 鶏むね肉 150g
```

### 対応する量の単位

| 単位 | 例 |
|------|----|
| `g` | 150g |
| `グラム` | 150グラム |
| `ml` | 200ml |
| `ミリリットル` | 200ミリリットル |

### 食事タイプの自動判定

| キーワード | 食事タイプ |
|------------|------------|
| 朝食, 朝 | breakfast |
| 昼食, 昼 | lunch |
| 夕食, 夕, 夜 | dinner |
| おやつ, 間食 | snack |
| (指定なし) | snack |

### 処理フロー

```
ユーザー: 「朝食 ご飯 150g」
    ↓
1. テキストパース
   - 食事タイプ: breakfast
   - 食品名: ご飯
   - 量: 150g
    ↓
2. food_search Lambda 呼び出し
   - クエリ: "ご飯"
   - 最初の検索結果を使用
    ↓
3. meal_registration Lambda 呼び出し
   - user_id: LINE User ID
   - meal_type: breakfast
   - foods: [{food_id, amount_g: 150}]
    ↓
4. 結果を返信
   「✅ 食事を登録しました！
   【朝食】白米 150g
   カロリー: 252 kcal
   たんぱく質: 3.9 g
   脂質: 0.5 g
   炭水化物: 55.7 g」
```

---

## 実装詳細

### 変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `src/lambda/line_handler/__init__.py` | 食品登録ロジック追加 |
| `terraform/api_gateway.tf` | 環境変数追加 |

### 追加した関数

#### `get_or_create_user(line_user_id: str)`

LINE User ID からユーザーを取得または作成する。初回メッセージ時に自動でユーザー登録。

```python
def get_or_create_user(line_user_id: str) -> str:
    """
    Args:
        line_user_id: LINE User ID

    Returns:
        user_id: システム内部のユーザーID
    """
```

#### `parse_food_and_amount(text: str)`

テキストから食品名、量、食事タイプを抽出する。

```python
def parse_food_and_amount(text: str) -> Tuple[Optional[str], Optional[float], str]:
    """
    Args:
        text: "朝食 白米 200g"

    Returns:
        ("白米", 200.0, "breakfast")
    """
```

#### `handle_food_registration_request(user_id, text, reply_token)`

1. `parse_food_and_amount()` でテキストをパース
2. `food_search` Lambda で食品検索
3. `meal_registration` Lambda で登録
4. 結果を LINE 返信

### 追加した環境変数

| 環境変数 | 値 |
|----------|-----|
| `FOOD_SEARCH_FUNCTION_NAME` | `aws_lambda_function.food_search.function_name` |
| `MEAL_REGISTRATION_FUNCTION_NAME` | `aws_lambda_function.meal_registration.function_name` |

---

## Lambda 間呼び出し

```
line_handler
    ├── food_search (食品検索)
    ├── meal_registration (食事登録)
    └── daily_summary (総評生成)
```

### IAM 権限

`lambda:InvokeFunction` 権限は `terraform/iam.tf` で定義済み：

```hcl
resource "aws_iam_role_policy" "lambda_invoke_lambda" {
  # ...
  Action   = ["lambda:InvokeFunction"]
  Resource = "arn:aws:lambda:${var.aws_region}:*:function:${var.project_name}-${var.environment}-*"
}
```

---

## 制限事項・既知の課題

### 1. 複数食品の同時登録は未対応

現在は1メッセージ1食品のみ対応。

```
❌ 「ご飯 150g と 納豆 50g」  → 未対応
✅ 「ご飯 150g」              → 対応
✅ 「納豆 50g」               → 対応（別メッセージ）
```

### 2. LINE ユーザーのプロフィール設定

LINE ユーザーが初めてメッセージを送信した際に、自動的に Users テーブルにエントリを作成する。

**自動作成されるデータ**:
```json
{
  "user_id": "uuid",
  "line_user_id": "LINE User ID",
  "tdee": 2000.0,      // デフォルト値
  "bmr": 1500.0,       // デフォルト値
  "source": "line",
  "created_at": "ISO8601"
}
```

**現在の制限**:
- プロフィール（身長・体重・活動量）は LINE から設定できない
- TDEE はデフォルト値（2000kcal）を使用
- 個人に最適化されたアドバイスは Web アプリからプロフィール設定後に利用可能

### 3. 検索結果の選択は未対応

検索結果の最初の1件を自動的に使用。複数候補からの選択機能は未実装。

---

## テスト方法

### LINE Bot でテスト

1. LINE Bot を友だち追加
2. 以下のメッセージを送信：
   - `白米 150g`
   - `朝食 ご飯 200g`
   - `昼食 サラダ 100g`
3. 登録完了メッセージを確認

### 期待される返信（成功時）

```
✅ 食事を登録しました！

【朝食】白米 150g

カロリー: 252 kcal
たんぱく質: 3.9 g
脂質: 0.5 g
炭水化物: 55.7 g
```

### 期待される返信（食品未発見時）

```
「ほげほげ」に該当する食品が見つかりませんでした。別の名前で試してください。
```

---

## デプロイ手順

```bash
# 1. Lambda パッケージング
./scripts/package_lambda.sh

# 2. Terraform plan
make plan

# 3. Terraform apply
make apply
```

---

## 関連ドキュメント

- [USER_TEST_GUIDE.md](USER_TEST_GUIDE.md) - ユーザーテスト手順
- [USER_TEST_ISSUE_RESOLUTION.md](USER_TEST_ISSUE_RESOLUTION.md) - 問題解決記録
- [ARCHITECTURE.md](ARCHITECTURE.md) - システムアーキテクチャ

---

# LIFF (LINE Front-end Framework) 統合

## 概要

LINE アプリ内ブラウザから食事管理アプリにアクセスできる機能。
LIFF 経由でアクセスした場合は LINE 認証を使用し、通常ブラウザでは Cognito 認証を使用。

**実装日**: 2025-12-09

---

## LIFF 設定情報

| 項目 | 値 |
|------|-----|
| **LIFF ID** | `2008658695-M1gQv1N3` |
| **LIFF URL** | `https://liff.line.me/2008658695-M1gQv1N3` |
| **サイズ** | Tall |
| **エンドポイント** | `https://d2b7c2gzuy0hmt.cloudfront.net` |

---

## 認証フロー

### 通常ブラウザ (Cognito 認証)

```
ユーザー → CloudFront → React App → Cognito 認証 → API Gateway (JWT)
```

### LIFF 経由 (LINE 認証)

```
LINE App → LIFF URL → React App → LINE 認証 (LIFF SDK)
                                      ↓
                              LINE User ID 取得
                                      ↓
                              API Gateway (X-Line-User-Id ヘッダー)
```

---

## 実装詳細

### フロントエンド変更ファイル

| ファイル | 変更内容 |
|----------|----------|
| `frontend/src/contexts/LiffContext.tsx` | LIFF SDK 管理コンテキスト（新規） |
| `frontend/src/contexts/AuthContext.tsx` | LINE 認証対応追加 |
| `frontend/src/api/client.ts` | LINE User ID ヘッダー対応 |
| `frontend/package.json` | `@line/liff` パッケージ追加 |

### 追加した依存パッケージ

```bash
npm install @line/liff
```

### 環境変数

`frontend/.env` に以下を追加:

```bash
# LINE LIFF設定
VITE_LIFF_ID=2008658695-M1gQv1N3
```

---

## 認証タイプの判定

フロントエンドは `localStorage.authType` で認証タイプを判定:

| authType | 認証方式 | API ヘッダー |
|----------|----------|--------------|
| `cognito` | Cognito JWT | `Authorization: Bearer {idToken}` |
| `line` | LINE User ID | `X-Line-User-Id: {lineUserId}` |

### API クライアントの動作

```typescript
// api/client.ts - リクエストインターセプター
if (authType === 'line') {
  // LINE認証: X-Line-User-Id ヘッダーを使用
  headers['X-Line-User-Id'] = lineUserId;
} else {
  // Cognito認証: Bearer トークンを使用
  headers.Authorization = `Bearer ${idToken}`;
}
```

---

## LiffContext の使用方法

### プロバイダーの設定

```tsx
// App.tsx
import { LiffProvider } from './contexts/LiffContext';
import { AuthProvider } from './contexts/AuthContext';

function App() {
  return (
    <LiffProvider>
      <AuthProvider>
        {/* アプリケーション */}
      </AuthProvider>
    </LiffProvider>
  );
}
```

### LIFF 状態の取得

```tsx
import { useLiff } from './contexts/LiffContext';
import { useAuth } from './contexts/AuthContext';

function MyComponent() {
  const { isInLiff, isLoggedIn, profile } = useLiff();
  const { signInWithLine } = useAuth();

  // LIFF 環境で自動ログイン
  useEffect(() => {
    if (isInLiff && isLoggedIn && profile) {
      signInWithLine(profile.userId, profile.displayName);
    }
  }, [isInLiff, isLoggedIn, profile]);

  return (
    <div>
      {isInLiff ? (
        <p>LINE アプリからアクセス中: {profile?.displayName}</p>
      ) : (
        <p>通常ブラウザからアクセス中</p>
      )}
    </div>
  );
}
```

---

## バックエンド対応

### 現状

バックエンドは既に LINE User ID での操作をサポート:

- `line_handler` Lambda: LINE User ID でユーザー作成/取得
- `meal_registration` Lambda: `user_id` パラメータで食事登録
- `daily_summary` Lambda: `user_id` パラメータで総評生成

### 将来の拡張（オプション）

API Gateway で `X-Line-User-Id` ヘッダーを検証する場合:

1. Lambda Authorizer で LINE User ID を検証
2. DynamoDB の `LineUserIdIndex` GSI で存在確認

---

## テスト方法

### LIFF 環境でのテスト

1. LINE アプリで LIFF URL を開く:
   ```
   https://liff.line.me/2008658695-M1gQv1N3
   ```

2. 自動的に LINE 認証が行われる

3. 食事記録の確認・プロフィール設定が可能

### 通常ブラウザでのテスト

1. CloudFront URL を開く:
   ```
   https://d2b7c2gzuy0hmt.cloudfront.net
   ```

2. Cognito 認証でログイン

3. 従来通りの操作が可能

---

## Rich Menu 連携（将来対応）

LINE Bot の Rich Menu から LIFF を起動する設定:

```json
{
  "type": "uri",
  "uri": "https://liff.line.me/2008658695-M1gQv1N3",
  "label": "食事管理アプリ"
}
```

---

**更新日**: 2025-12-09
