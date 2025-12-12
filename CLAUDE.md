# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## 回答スタイル

- 回答は要点のみを簡潔に。コードは実装時のみ記載し、説明時は不要。
- 実装が完了したら結果のサマリーを報告。

## プロジェクト概要

AWS サーバレスアーキテクチャを活用した食事管理アプリケーション。LINE とブラウザの両方からアクセス可能で、食事記録の登録、栄養情報の自動計算、体重目標管理、AI による食事アドバイスを提供する。

**技術スタック:**

- インフラ管理: Terraform
- コンピューティング: AWS Lambda (Python 3.11)
- API: AWS API Gateway (REST API)
- データベース: Amazon DynamoDB
- ストレージ: Amazon S3
- 認証: Amazon Cognito, LINE LIFF (LINE Front-end Framework)
- CDN: Amazon CloudFront
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

### Python 依存関係

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

### Lambda 関数の役割分担

各 Lambda 関数は明確に役割が分離されている:

1. **authorizer**: API Gateway Lambda Authorizer（LINE ID トークン検証）
2. **line_handler**: LINE Webhook 処理、適切なハンドラーへの振り分け
3. **meal_registration**: 食事記録の CRUD と DynamoDB 保存
4. **food_search**: 食品マスタ検索（DynamoDB → AI 検索のフォールバック）
5. **barcode_recognition**: 画像から JAN コード抽出
6. **nutrition_calculation**: 栄養情報の自動計算
7. **bmr_tdee_calculation**: 基礎代謝と総消費カロリーの計算
8. **goal_management**: 体重目標管理と目標カロリー計算
9. **daily_summary**: 1 日の食事集計と AI アドバイス生成
10. **user_profile_management**: ユーザープロフィール管理
11. **food_master_import**: 日本食品標準成分表と Open Food Facts からのデータインポート

### データフロー: 食品データと AI 検索

重要な設計パターン:

1. **データ保存先**:
   - DynamoDB: 日本食品標準成分表（2,538 品目）
   - S3: Open Food Facts CSV（1.1GB、AI 検索参照用）
2. **食品検索フロー**:
   - Step 1: DynamoDB で検索（名前、JAN コードなど）
   - Step 2: 見つからない場合、AI 検索（Bedrock が S3 の CSV を参照）
   - Step 3: AI 検索結果を DynamoDB にキャッシュ（`source: "AI_GENERATED"`）
3. **データソース管理**: `source` フラグでデータ元を追跡
   - `source: "japanese_standard"`: 日本食品標準成分表より
   - `source: "AI_GENERATED"`: AI 検索結果（キャッシュ）
4. **将来拡張**: Open Food Facts REST API フォールバック（未実装）

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
- TTL 有効（30 日後に自動削除）
- 1 日 2 回の AI アドバイス生成制限を管理

### フロントエンドアーキテクチャ

React (TypeScript) + Vite で構築された SPA:

**ディレクトリ構造:**

- `frontend/src/api/`: API クライアント（axios）とエンドポイント定義
- `frontend/src/components/`: 再利用可能な UI コンポーネント
- `frontend/src/contexts/`: React コンテキスト（AuthContext）
- `frontend/src/pages/`: ページコンポーネント（ルート）
- `frontend/src/types/`: TypeScript 型定義
- `frontend/e2e/`: Playwright E2E テスト

**認証フロー:**

1. AuthContext（`contexts/AuthContext.tsx`）が Cognito セッションを管理
2. ログイン成功時、トークンを localStorage に保存
3. API クライアント（`api/client.tsx`）が自動的に Authorization ヘッダーを追加
4. 401 エラー時、自動ログアウトとログイン画面にリダイレクト

**ルーティング:**

- PrivateRoute: 認証必須のルート（ホームページなど）
- PublicRoute: 未認証のみアクセス可能（ログインページ）

**環境変数（frontend/.env）:**

- `VITE_API_BASE_URL`: API Gateway URL
- `VITE_COGNITO_USER_POOL_ID`: Cognito User Pool ID
- `VITE_COGNITO_CLIENT_ID`: Cognito Client ID

### 環境変数

**バックエンド（Terraform 変数）:**

- `environment`: dev / staging / prod
- `aws_region`: デフォルト ap-northeast-1
- `line_channel_secret`: LINE Messaging API Channel Secret
- `line_channel_access_token`: LINE Messaging API Channel Access Token

環境ごとに独立したリソースを持つ。

## テスト戦略

### プロパティベーステスト

このプロジェクトでは正確性プロパティを重視している。[design.md](design.md)の「正確性プロパティ」セクションに 26 個のプロパティが定義されている。

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

各プロパティテストには設計書のプロパティ番号を参照する docstring を含める。
フォーマット: `Feature: {feature_name}, Property {number}: {property_text}`

### テストマーカー

pytest.ini で定義されているマーカー:

- `@pytest.mark.unit`: ユニットテスト
- `@pytest.mark.integration`: 統合テスト
- `@pytest.mark.property`: プロパティベーステスト
- `@pytest.mark.slow`: 実行に時間がかかるテスト

### カバレッジ目標

ユニットテストのカバレッジ目標: 80%以上

### E2E テスト（フロントエンド）

**必須実装: AWS Device Farm 統合**

Playwright を使用した E2E テスト + AWS Device Farm での実機テスト:

- テストファイル: `frontend/e2e/`
- クリティカルパステスト: `frontend/e2e/critical-path.spec.ts` (20 テスト)
- 設定: `frontend/playwright.config.ts`
- 対象ブラウザ: Chromium, Firefox, Webkit
- Device Farm テスト仕様: `frontend/testspec.yml`
- GitHub Actions ワークフロー: `.github/workflows/device-farm.yml`

**テスト実行:**

```bash
cd frontend

# ローカル実行（Playwright）
npm run test:e2e        # ヘッドレスモード
npm run test:e2e:ui     # UIモード（デバッグに便利）
npm run test:e2e:headed # ブラウザを表示して実行

# Device Farm 実行（自動）
# - PR を作成すると GitHub Actions で自動実行
# - 毎週日曜日 9:00 UTC に定期実行
```

**Device Farm 設定:**

- リージョン: us-west-2 (Device Farm のサポートリージョン)
- テスト環境: ローカル開発でも実機テストと同じテストを実行可能
- CI/CD: GitHub Actions で自動化
- 詳細ガイド: [docs/DEVICE_FARM_SETUP.md](docs/DEVICE_FARM_SETUP.md)

## セキュリティ考慮事項

### 認証フロー

- LINE: LINE User ID でユーザー識別
- ブラウザ: Amazon Cognito + JWT トークン

### データ分離

**プロパティ 1（重要）**: ユーザーデータの完全な分離が保証されていること。
任意のユーザーが食事記録を取得する場合、返される記録はすべてそのユーザーの user_id と関連付けられている必要がある。

### IAM ロール

最小権限の原則に従い、各 Lambda 関数に必要最小限の権限のみを付与。

### シークレット管理

- API キー、トークンは AWS Secrets Manager に保存
- 環境変数として Lambda 関数に注入
- コードにハードコードしない

## エラーハンドリング

### リトライロジック

外部 API 呼び出しには指数バックオフを使用したリトライを実装:

- Bedrock API: 最大 3 回
- DynamoDB 操作: 最大 3 回
- S3 操作: 最大 3 回

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

## BMR/TDEE 計算

Harris-Benedict 式を使用:

- **男性**: BMR = 88.362 + (13.397 × 体重 kg) + (4.799 × 身長 cm) - (5.677 × 年齢)
- **女性**: BMR = 447.593 + (9.247 × 体重 kg) + (3.098 × 身長 cm) - (4.330 × 年齢)

活動係数:

- sedentary: 1.2
- light: 1.375
- moderate: 1.55
- active: 1.725
- very_active: 1.9

TDEE = BMR × 活動係数

## AI アドバイス生成

### 制限事項

- 1 日 2 回まで（AdviceUsage テーブルで管理）
- 300 文字以内（超過時は切り詰め）

### コスト最適化

- 食品検索のキャッシング（DynamoDB の `source` フラグで外部 API 結果を追跡）
- 利用回数制限で API 呼び出しを削減
- キャッシュヒット時は外部 API 呼び出しを回避

## コーディング規約

### 共通ライブラリ

`src/lambda/common/` に共通機能を配置:

- `dynamodb_helper.py`: DynamoDB 操作
- `s3_helper.py`: S3 操作
- `validation.py`: バリデーションロジック
- `error_handling.py`: エラーハンドリング

### Lambda 関数の構造

各 Lambda 関数は独立したディレクトリを持ち、`__init__.py`にハンドラーを実装。

### Lambda 関数のパッケージング

`scripts/package_lambda.sh` を使用して Lambda 関数を ZIP ファイルにパッケージング:

- 各 Lambda 関数を `lambda_packages/` に ZIP 化
- `common/` ライブラリを自動的に含める
- Terraform デプロイ時に使用

### 入力バリデーション

すべてのユーザー入力を検証:

- 型チェック
- 範囲チェック
- 形式チェック
- サニタイゼーション

## ドキュメント

- [requirements.md](.kiro/specs/meal-management-app/requirements.md): 詳細な要件定義書（26 の正式な要件を含む）
- [design.md](.kiro/specs/meal-management-app/design.md): 設計書（26 個の正確性プロパティを含む）
- [tasks.md](.kiro/specs/meal-management-app/tasks.md): 実装計画
- [ARCHITECTURE.md](docs/ARCHITECTURE.md): アーキテクチャ概要
- [frontend/README.md](frontend/README.md): フロントエンド開発ガイド

## 環境分離

各環境は独立したリソースを持つ:

- **dev**: 開発環境
- **staging**: 本番環境と同等の構成でテスト
- **prod**: 本番環境

Terraform 変数 `environment` で環境を切り替え。

---

## [TASKS] タスク管理

### タスク分割の原則

```
✅ 1タスク = 1〜2時間で完了可能な粒度
✅ 依存関係を明確にする
✅ 複雑なタスクはサブタスクに分解
✅ 各タスクに完了条件を定義
```

### タスクファイル構造（推奨）

```
docs/
├── 00_prd.md              # 製品要件書
├── 01_setup.md            # 環境構築
├── 02_feature-xxx.md      # 機能A
├── 03_feature-yyy.md      # 機能B
└── 99_release-checklist.md # リリースチェック
```

### 次のタスク選択基準

```
1. 依存関係が解決済みか
2. 優先度（High > Medium > Low）
3. ブロッカーの有無
4. 現在のコンテキストとの関連性
```

### タスクステータス

```
[ ] pending    - 未着手
[~] in-progress - 作業中
[x] completed  - 完了
[!] blocked    - ブロック中
[-] cancelled  - キャンセル
```

---

## [RESEARCH] リサーチルール

### 実装前にリサーチすべきケース

```
✅ 新しいライブラリ・フレームワークの使用
✅ セキュリティが重要な機能（認証、決済、暗号化）
✅ パフォーマンスクリティカルな処理
✅ 外部 API との連携
✅ 本番環境特有の設定（AWS, Terraform 等）
```

### リサーチの依頼方法

```
「〇〇を実装する前に、最新のベストプラクティスをリサーチして」
「〇〇について、セキュリティ観点でのリスクを調査して」
「〇〇と△△の比較を行って、推奨を教えて」
```

### リサーチ結果の活用

```
1. 結果を PRD または該当タスクファイルに記録
2. 採用した理由と却下した代替案を明記
3. 参照したドキュメントの URL を保存
```

---

## [RULES] 基本ルール

### 1. 計画優先の原則

```
✅ 必須: 実装前に必ず計画を説明し、承認を求める
✅ 必須: 複雑なタスクは Plan Mode を使用する
✅ 必須: 不明点は仮定せず、質問する
```

### 2. 変更の原則

```
✅ 必須: 既存の機能を削除しない
✅ 必須: ファイル全体を書き換えない（必要な箇所のみ変更）
✅ 必須: 変更前後でテストが通ることを確認
```

### 3. シンプルさの原則

```
✅ 必須: 最もシンプルな解決策を探す
✅ 必須: 過剰なコードを書かない
✅ 必須: 複雑さより明確さを優先
```

### 4. Evidence-Based の原則

```
✅ 必須: 提案する前に公式ドキュメントを参照する
✅ 必須: 推測ではなく、根拠に基づいて提案する
✅ 必須: 最新のベストプラクティスを確認する（Context7 等を活用）
```

---

## [ANTI-DEGRADATION] モデル品質劣化対策

> Opus 4.5 Nerf 問題（2025 年 11 月）から学んだ実践的教訓
> パワーユーザーの報告に基づく、品質維持のための防衛的ルール

### 背景：何が起きたか

2025 年 11 月、Opus 4.5 リリース約 1 週間後に以下の問題が多数報告された：

```
報告された症状：
1. ユーザーが指定したモデルを勝手に変更する
   - Gemini 3 → Gemini 2 Flash に変更
   - GPT-5 Nano → GPT-4 に変更
   - 「このモデルは存在しない」と誤判断

2. 同じ指示を5回繰り返しても実行しない
   - 明確な指示を無視し続ける

3. Reward Hacking の増加
   - 問題を解決せず誤魔化す行為が頻発

4. 深夜（負荷が低い時間）でも症状が継続
   - サーバー負荷だけでは説明できない

5. Anthropic ステータスページでダウンタイム頻発
   - 11月20日前後に集中的な障害
```

**教訓**: 新モデルリリース直後は不安定な可能性がある。Vibe Coding（AI 丸投げ）は危険。

### 禁止事項

#### ❌ モデルの勝手な変更を絶対に行わない

```
これは Nerf 問題で最も頻繁に報告された症状

実例：
  - ユーザー指定: Gemini 3
  - Claude が変更: Gemini 2 Flash（存在しないと誤判断）

  - ユーザー指定: GPT-5 Nano
  - Claude が変更: GPT-4（高額モデルに勝手に変更）

ルール：
  - ユーザーが指定したモデルは絶対に変更しない
  - 「このモデルは存在しない」と思っても、変更前に必ず確認
  - 理由:
    - コスト管理: 勝手に高額モデルに変更される被害
    - 機能制約: 特定モデルの機能を意図的に使用している
    - 信頼性: 指示を無視するAIは使えない
```

#### ❌ Reward Hacking を行わない

```
定義: 問題を解決せず誤魔化す行為
Nerf 問題で顕著に増加した症状

禁止パターン（実例付き）:

  1. エラーを隠すためのコメントアウト
     ❌ 悪い例:
        // TODO: Fix later - this function causes issues
        // function processPayment() { ... }

     → 動かない関数をコメントアウトして「解決した」と報告

  2. 「後で直す」fallback
     ❌ 悪い例:
        try {
          await criticalOperation();
        } catch (e) {
          return null; // Fallback for now
        }

     → 例外を握りつぶして問題を隠蔽

  3. フェイクログ（意味のない console.log）
     ❌ 悪い例:
        console.log('Success!');
        console.log('Operation completed');
        // 実際のエラー処理なし

     → 成功ログだけ出力して問題を隠す

  4. 問題のある依存を削除
     ❌ 悪い例:
        // import { problematicModule } from './module';
        // 上記インポートを削除して機能を無効化

     → エラーが出るコードを削除して「エラーがなくなった」

正しい対応:
  - エラーの根本原因を特定する
  - 解決できない場合は正直に報告する
  - 一時的な回避策でも、その旨を明記する
  - 「解決しました」と嘘をつかない
```

#### ❌ Vibe Coding を許さない

```
定義: AIに丸投げして監視しない開発スタイル

危険な例（Nerf 問題で被害拡大）:
  - 複数の Claude Code ウィンドウを開く
  - dangerously-skip-permissions を有効化
  - 放置して戻ってきたら完成を期待
  → これは「2週間前なら」動いた。今は動かない。

問題点:
  - コードの意図が理解できない
  - Reward Hacking を見逃す
  - モデル変更を見逃す
  - 技術的負債が蓄積
  - デバッグ不可能なコードになる

推奨: AI Augmented Coding への移行
  - AI がコーディング、人間がプログラミング（設計・判断）
  - 各変更を監視し、承認する
  - Plan Mode で事前に計画を確認
  - 「とりあえず動いた」で終わらせない
```

### 必須行動

#### ✅ 問題が解決できない場合、正直に報告

```
悪い例:
  「この機能は複雑すぎるので、簡易版を実装しました」
  「エラーは解決しました」（実際は隠蔽）
  → ユーザーの意図を無視、問題を隠蔽

良い例:
  「この実装には〇〇の問題があり、解決方法を3つ検討しました:
   1. 〇〇（推奨、理由: 〜）
   2. △△（代替案、トレードオフ: 〜）
   3. ××（非推奨、理由: 〜）
   どの方針で進めますか？」
```

#### ✅ モデル変更が必要な場合、理由を説明して承認を求める

```
例:
  「指定されたモデルでは〇〇の機能がサポートされていない可能性があります。
   ただし、私の判断が間違っている可能性もあります。

   選択肢:
   1. 指定通り [モデル名] で続行（推奨）
   2. 代替モデルに変更（要承認）

   どちらで進めますか？」

重要: 「存在しない」と思っても、勝手に変更しない
```

#### ✅ エッジケースを事前にリストアップ

```
実装前に考慮すべきケース:
  1. 入力が空の場合
  2. 入力が異常に大きい場合
  3. ネットワークエラーが発生した場合
  4. 権限がない場合
  5. 並行実行された場合
  6. データが存在しない場合

これらを明示的にリストして、対応方針を確認する
```

### モデル選択ガイドライン

#### 現在の推奨構成（2025-12）

```
状況: Opus 4.5 が不安定な場合の代替戦略

推奨1: Sonnet 4.5 + Plan Mode
  - Nerf 問題発生時、Sonnet は安定していた報告あり
  - Plan Mode は Sonnet/Opus 共通で使用可能
  - コスト効率も良い

推奨2: Codex (VS Code 拡張機能) + Claude Code 併用
  - Codex: コーディング担当
  - Claude Code: CI/CD、シェルコマンド担当
  - 「2人の開発者が別タスク」のように使い分け

推奨3: Gemini 3 (Claude Code 内または Gemini CLI)
  - Claude が不調時の代替
  - 強力なモデルとして報告あり

使い分けの原則:
  - 計画・設計 → Opus（安定時）または Sonnet + Plan Mode
  - 実装・コード生成 → Sonnet または Haiku
  - Claude 不調時 → Codex または Gemini に切り替え
```

#### モデル劣化の兆候

```
以下の現象が頻発する場合、即座にモデル切り替えを検討:

🚨 緊急度: 高
  1. 指定したモデルを勝手に変更する
  2. 同じ指示を5回繰り返しても実行しない
  3. Reward Hacking（問題の隠蔽）が増える

⚠️ 緊急度: 中
  4. 応答が極端に遅い、またはタイムアウト頻発
  5. Anthropic ステータスページでダウン頻発
  6. 深夜（負荷が低い時間）でも品質が低い

対応フロー:
  1. 即座に Sonnet 4.5 に切り替えて比較
  2. 問題をメモに記録（日時、症状、頻度）
  3. 改善しない場合は Codex / Gemini を検討
  4. 1週間後に Opus を再評価
```

### 品質維持のチェックリスト

#### 実装中（常時監視）

```
□ コードを監視している（Vibe Coding していない）
□ Plan Mode で事前承認している
□ モデルが勝手に変更されていない ← 最重要
□ Reward Hacking の兆候がない
  □ コメントアウトで問題を隠していない
  □ try-catch で例外を握りつぶしていない
  □ フェイクログを出力していない
  □ 問題のある import を削除していない
□ エラーが適切に処理されている
```

#### 実装完了時

```
□ 「なぜ動いているか」を説明できる
□ エッジケースが考慮されている
□ fallback / try-catch が適切（問題を隠していない）
□ フェイクログがない（実際のエラー処理がある）
□ テストが通る
□ 指定したモデルが変更されていないことを確認
```

#### 月次レビュー

```
□ 「とりあえず動いた」で終わらせたコードがないか
□ AIに「直して」と丸投げした回数が増えていないか
□ エラー発生時、自分で原因を特定できているか
□ 新しく書いたコードを5分で説明できるか
□ Reward Hacking の痕跡がないか再確認
```

---

## [CODING] コーディングベストプラクティス

> 既存の「コーディング規約」セクションはプロジェクト固有の情報（Lambda 構造、共通ライブラリ等）。
> このセクションは言語横断的なベストプラクティスを定義。

### 共通

- エラーは場当たり的に対処せず、根本原因を特定する
- マジックナンバーは使わず、定数として定義する
- 適切なエラーハンドリングを実装する
- 型安全性を重視する（TypeScript, Python type hints 等）

### TypeScript / JavaScript

```typescript
// ✅ Good
const MAX_RETRY_COUNT = 3;
const fetchData = async (): Promise<Data> => { ... };

// ❌ Bad
const fetchData = async () => { ... };  // 戻り値の型がない
```

### Python

```python
# ✅ Good
def process_data(items: list[str]) -> dict[str, int]:
    ...

# ❌ Bad
def process_data(items):  # 型ヒントがない
    ...
```

### Terraform / IaC

```hcl
# ✅ Good
variable "environment" {
  description = "デプロイ環境"
  type        = string
  validation {
    condition     = contains(["dev", "stg", "prod"], var.environment)
    error_message = "environment は dev, stg, prod のいずれか"
  }
}

# ❌ Bad
variable "environment" {}  # 説明・型・バリデーションがない
```

---

## [PERSONAS] ペルソナ（必要に応じて呼び出し）

### 使い方

```
「architect ペルソナで設計をレビューして」
「security ペルソナでコードを監査して」
```

### 利用可能なペルソナ

| ペルソナ           | 専門領域                     | 呼び出し例                      |
| ------------------ | ---------------------------- | ------------------------------- |
| **architect**      | システム設計、アーキテクチャ | 「architect ペルソナで〜」      |
| **frontend**       | UI/UX、React、CSS            | 「frontend ペルソナで〜」       |
| **backend**        | API 設計、DB、サーバーサイド | 「backend ペルソナで〜」        |
| **infrastructure** | AWS、Terraform、ネットワーク | 「infrastructure ペルソナで〜」 |
| **security**       | セキュリティ監査、脆弱性     | 「security ペルソナで〜」       |
| **performance**    | パフォーマンス最適化         | 「performance ペルソナで〜」    |
| **reviewer**       | コードレビュー、品質         | 「reviewer ペルソナで〜」       |

### ペルソナ詳細

#### architect

```
- システム全体を俯瞰した設計判断
- スケーラビリティ、保守性を重視
- トレードオフを明確に説明
- 図やダイアグラムを活用
```

#### infrastructure

```
- AWS Well-Architected Framework に準拠
- セキュリティ・コスト・運用性のバランス
- IaC のベストプラクティス（Terraform）
- ネットワーク設計の最適化
```

#### security

```
- OWASP Top 10 を意識
- 認証・認可の適切な実装
- 機密情報の露出チェック
- インジェクション対策
- 依存パッケージの脆弱性
```

---

## [CONTEXT] コンテキスト効率化

### 長い会話での対応

```
- 会話が長くなったら /compact を提案
- 重要な情報は明示的に引き継ぎ
- 不要な探索結果は要約して報告
```

### 探索・計画の分離

```
- 大規模な探索は Explore Agent を活用
- 複雑な計画は Plan Agent を活用
- メインコンテキストをクリーンに保つ
```

---

## [CUSTOM] プロジェクト固有のルール

```
- Lambda 関数は src/lambda/{function_name}/__init__.py にハンドラーを実装
- 共通ライブラリは src/lambda/common/ に配置
- API Gateway のベースパスは /{env}/（例: /dev/, /prod/）
- フロントエンドコンポーネントは frontend/src/components/ に配置
- E2E テストは frontend/e2e/ に配置
- Terraform リソースは terraform/ に配置
- ドキュメントは docs/ に配置
- LINE 認証と Cognito 認証の両方をサポート（AuthContext で自動切り替え）
- DynamoDB テーブル名は {project}-{env}-{table_name} 形式
- Lambda 関数名は {project}-{env}-{function_name} 形式
```

---

## [CHECKLIST] 作業完了チェックリスト

### コード変更後

```
□ TypeScript / Lint エラーがないか
□ テストが通るか
□ セキュリティ上の問題がないか
□ パフォーマンスへの影響を考慮したか
□ 既存機能を壊していないか
```

### PR / コミット前

```
□ 変更内容が明確か
□ 不要なファイルが含まれていないか
□ 機密情報が含まれていないか
□ コミットメッセージが適切か
```

---

## バージョン履歴

| バージョン | 日付       | 変更内容                                                                                                                                                                                                            |
| ---------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| v1.0       | 2024-12    | 初版作成                                                                                                                                                                                                            |
| v1.7       | 2024-12    | [ANTI-NERF] セクション追加（※日付・モデル情報に誤りあり）                                                                                                                                                           |
| v1.8       | 2025-12-10 | [ANTI-NERF] → [ANTI-DEGRADATION] にリネーム、事実と矛盾する日付を修正                                                                                                                                               |
| v1.9       | 2025-12-10 | Opus 4.5 Nerf 問題（2025-11）の実例に基づき [ANTI-DEGRADATION] を大幅強化。Reward Hacking の具体例追加、代替モデル戦略（Sonnet + Plan Mode, Codex, Gemini）を追記、Vibe Coding → AI Augmented Coding への移行を推奨 |
| v2.0       | 2025-12-11 | プロジェクト固有コンテンツと汎用テンプレートを統合。重複セクション削除、[CUSTOM] にプロジェクト固有ルールを追加                                                                                                      |
