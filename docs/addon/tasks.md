# 実装作業タスク一覧

AWS ポートフォリオ強化の 3 つのタスク（週次レポート、Device Farm、Next.js移行）を実装作業として細分化。

## タスク凡例

- **タスクID**: Task X.Y 形式
- **説明**: 実装する内容
- **ファイル**: 作成・変更対象のファイルパス
- **工数**: 時間単位
- **依存**: 前提となるタスク（「なし」は独立、「X.Y」は該当タスク完了後）
- **完了条件**: 明確な完了基準

---

## Task 1: 週次レポート機能（11タスク、9-16時間）

### ✅ Task 1.1: Lambda関数骨組み作成

- **説明**: weekly_report Lambda関数の基本構造を実装
- **ファイル**: `src/lambda/weekly_report/__init__.py`
- **工数**: 1.5h
- **依存**: なし
- **完了条件**: lambda_handler が定義され、環境変数が読み込まれる

### ✅ Task 1.2: ユーザー取得ロジック実装

- **説明**: Users テーブルから全アクティブユーザーを取得
- **ファイル**: `src/lambda/weekly_report/__init__.py`
- **工数**: 1h
- **依存**: 1.1
- **完了条件**: weekly_report_enabled=true のユーザーリストが取得できる

### ✅ Task 1.3: 週次集計ロジック実装

- **説明**: 過去7日間の食事データを集計（平均カロリー、PFC、目標達成日数）
- **ファイル**: `src/lambda/weekly_report/__init__.py`
- **工数**: 2-3h
- **依存**: 1.2
- **完了条件**: 週次統計（avg_daily_calories, avg_daily_protein等）が計算される

### ✅ Task 1.4: Bedrock統合実装

- **説明**: Claude 3 Haiku API でアドバイス生成（300文字制限）
- **ファイル**: `src/lambda/weekly_report/__init__.py`, `src/lambda/common/bedrock_helper.py` (新規)
- **工数**: 1.5-2h
- **依存**: 1.3
- **完了条件**: Bedrock から300文字以内のアドバイスが返される

### ✅ Task 1.5: LINE Push Message統合

- **説明**: LINE Messaging API で各ユーザーに配信
- **ファイル**: `src/lambda/weekly_report/__init__.py`, `src/lambda/common/line_helper.py` (拡張)
- **工数**: 1.5-2h
- **依存**: 1.4
- **完了条件**: LINE Push Message が送信される

### ✅ Task 1.6: Terraform Lambda定義

- **説明**: weekly_report Lambda リソースを定義
- **ファイル**: `terraform/api_gateway.tf` (追加)
- **工数**: 1h
- **依存**: なし（Task 1.1-1.5と並行可能）
- **完了条件**: Terraform plan で weekly_report Lambda が表示される

### ✅ Task 1.7: EventBridge スケジューラー設定

- **説明**: 毎週日曜 20:00 JST (cron: 0 11 ? * SUN *)
- **ファイル**: `terraform/eventbridge.tf` (新規)
- **工数**: 1h
- **依存**: 1.6
- **完了条件**: EventBridge ルールが作成され、Lambda がターゲットになる

### ✅ Task 1.8: IAM 権限追加

- **説明**: Bedrock、DynamoDB、CloudWatch 権限を追加
- **ファイル**: `terraform/iam.tf` (追加)
- **工数**: 0.5h
- **依存**: 1.6
- **完了条件**: Terraform plan で IAM ポリシーが表示される

### ✅ Task 1.9: テスト実装

- **説明**: ユニットテスト（集計ロジック）、統合テスト（Bedrock、LINE）
- **ファイル**: `tests/test_weekly_report.py` (新規)
- **工数**: 2-3h
- **依存**: 1.5
- **完了条件**: pytest が成功、カバレッジ 80% 以上

### ✅ Task 1.10: パッケージング設定更新

- **説明**: weekly_report を package_lambda.sh に追加
- **ファイル**: `scripts/package_lambda.sh`
- **工数**: 0.5h
- **依存**: なし（Task 1.1-1.5と並行可能）
- **完了条件**: make package でZIPファイルが生成される

### ✅ Task 1.11: デプロイと検証

- **説明**: Terraform apply、手動トリガーでテスト実行
- **ファイル**: -
- **工数**: 1-2h
- **依存**: 1.7, 1.8, 1.10
- **完了条件**: CloudWatch Logs で実行ログが確認できる、LINE メッセージが配信される

---

## Task 2: Device Farm E2E テスト統合（10タスク、10-13時間）

### ✅ Task 2.1: Device Farm プロジェクト作成

- **説明**: AWS Console で Device Farm プロジェクト作成
- **ファイル**: -
- **工数**: 0.5h
- **依存**: なし
- **完了条件**: Device Farm プロジェクトが存在する

### ✅ Task 2.2: S3 バケット定義

- **説明**: テスト環境ホスティング用 S3 バケット
- **ファイル**: `terraform/s3.tf` (追加)
- **工数**: 0.5h
- **依存**: なし
- **完了条件**: Terraform plan でバケットが表示される

### ✅ Task 2.3: CloudFront Distribution定義

- **説明**: S3 バケットを Origin にした CloudFront
- **ファイル**: `terraform/cloudfront.tf` (新規)
- **工数**: 1h
- **依存**: 2.2
- **完了条件**: CloudFront Distribution URL が出力される

### ✅ Task 2.4: テストユーザー管理 Lambda作成

- **説明**: Cognito でテストユーザーを作成・削除
- **ファイル**: `src/lambda/test_user_management/__init__.py` (新規)
- **工数**: 2-3h
- **依存**: なし（Task 2.2-2.3と並行可能）
- **完了条件**: テストユーザーが作成・削除される

### ✅ Task 2.5: Terraform Lambda定義

- **説明**: test_user_management Lambda リソース
- **ファイル**: `terraform/api_gateway.tf` (追加)
- **工数**: 1h
- **依存**: 2.4
- **完了条件**: Terraform plan で Lambda が表示される

### ✅ Task 2.6: IAM 権限追加

- **説明**: Cognito Admin 権限を付与
- **ファイル**: `terraform/iam.tf` (追加)
- **工数**: 0.5h
- **依存**: 2.5
- **完了条件**: IAM ロールに cognito-idp:* 権限が追加される

### ✅ Task 2.7: クリティカルパステスト実装

- **説明**: 20テストケースを frontend/e2e/critical/ に実装
- **ファイル**: `frontend/e2e/critical/*.spec.ts` (新規)
- **工数**: 3-4h
- **依存**: なし（Task 2.2-2.6と並行可能）
- **完了条件**: 20テストが個別に実行できる

### ✅ Task 2.8: Device Farm YAML設定

- **説明**: testspec.yml 作成
- **ファイル**: `frontend/testspec.yml` (新規)
- **工数**: 1-1.5h
- **依存**: 2.7
- **完了条件**: YAML がバリデーションを通過する

### ✅ Task 2.9: GitHub Actions ワークフロー作成

- **説明**: PR 作成時 + 毎週日曜に実行
- **ファイル**: `.github/workflows/device-farm.yml` (新規)
- **工数**: 2-3h
- **依存**: 2.3, 2.8
- **完了条件**: ワークフローが GitHub Actions でトリガーされる

### ✅ Task 2.10: デプロイと検証

- **説明**: Terraform apply、Device Farm テスト実行
- **ファイル**: -
- **工数**: 1-2h
- **依存**: 2.6, 2.9
- **完了条件**: Device Farm でテストが成功する

---

## Task 3: Next.js フロントエンド移行（18タスク、25-35時間）

### ✅ Task 3.1: Next.js プロジェクト初期化

- **説明**: Pages Router プロジェクトの作成
- **ファイル**: `frontend-nextjs/` (新規ディレクトリ)
- **工数**: 1.5h
- **依存**: なし
- **完了条件**: npm run dev でサーバーが起動する

### ✅ Task 3.2: 依存関係インストール

- **説明**: Next.js 14, NextAuth.js v5, Tailwind CSS
- **ファイル**: `frontend-nextjs/package.json`
- **工数**: 0.5h
- **依存**: 3.1
- **完了条件**: npm install が成功する

### ✅ Task 3.3: NextAuth.js 設定

- **説明**: Cognito Provider 統合
- **ファイル**: `frontend-nextjs/lib/auth.ts` (新規)
- **工数**: 2-3h
- **依存**: 3.2
- **完了条件**: ログイン・ログアウトが動作する

### ✅ Task 3.4: 認証ミドルウェア実装

- **説明**: 保護されたルートの自動リダイレクト
- **ファイル**: `frontend-nextjs/lib/auth-middleware.ts` (新規)
- **工数**: 1h
- **依存**: 3.3
- **完了条件**: 未認証時にログインページへリダイレクトされる

### ✅ Task 3.5: API クライアント移植

- **説明**: 既存 axios クライアントを再利用
- **ファイル**: `frontend-nextjs/lib/api-client.ts` (新規)
- **工数**: 1.5h
- **依存**: 3.3
- **完了条件**: API Gateway への認証付きリクエストが成功する

### ✅ Task 3.6: 共通コンポーネント移植

- **説明**: Button, Input, Card 等を移植
- **ファイル**: `frontend-nextjs/components/`
- **工数**: 2-3h
- **依存**: 3.2（Task 3.3-3.5と並行可能）
- **完了条件**: コンポーネントがレンダリングされる

### ✅ Task 3.7: ログインページ実装

- **説明**: pages/login.tsx
- **ファイル**: `frontend-nextjs/pages/login.tsx` (新規)
- **工数**: 2-3h
- **依存**: 3.3, 3.6
- **完了条件**: Cognito ログインが成功する

### ✅ Task 3.8: ホームページ実装

- **説明**: pages/home.tsx（ダッシュボード）
- **ファイル**: `frontend-nextjs/pages/home.tsx` (新規)
- **工数**: 1.5-2h
- **依存**: 3.7
- **完了条件**: ダッシュボードが表示される

### ✅ Task 3.9: プロフィールページ実装

- **説明**: pages/profile.tsx
- **ファイル**: `frontend-nextjs/pages/profile.tsx` (新規)
- **工数**: 2-3h
- **依存**: 3.8
- **完了条件**: プロフィール更新が成功する

### ✅ Task 3.10: 目標設定ページ実装

- **説明**: pages/goals.tsx
- **ファイル**: `frontend-nextjs/pages/goals.tsx` (新規)
- **工数**: 2-3h
- **依存**: 3.9
- **完了条件**: 目標作成が成功する

### ✅ Task 3.11: 食事登録ページ実装

- **説明**: pages/meals/new.tsx
- **ファイル**: `frontend-nextjs/pages/meals/new.tsx` (新規)
- **工数**: 2-3h
- **依存**: 3.10
- **完了条件**: 食事登録が成功する

### ✅ Task 3.12: 食事一覧ページ実装

- **説明**: pages/meals.tsx
- **ファイル**: `frontend-nextjs/pages/meals.tsx` (新規)
- **工数**: 1.5-2h
- **依存**: 3.11
- **完了条件**: 食事履歴が表示される

### ✅ Task 3.13: 総評ページ実装

- **説明**: pages/summary.tsx
- **ファイル**: `frontend-nextjs/pages/summary.tsx` (新規)
- **工数**: 1.5-2h
- **依存**: 3.12
- **完了条件**: AI アドバイスが表示される

### ✅ Task 3.14: SEO・メタデータ設定

- **説明**: _app.tsx, _document.tsx にメタタグ
- **ファイル**: `frontend-nextjs/pages/_app.tsx`, `_document.tsx`
- **工数**: 1h
- **依存**: 3.13
- **完了条件**: OGP タグが設定される

### ✅ Task 3.15: Amplify Hosting 設定

- **説明**: amplify.yml 作成
- **ファイル**: `frontend-nextjs/amplify.yml` (新規)
- **工数**: 1h
- **依存**: なし（Task 3.1-3.14と並行可能）
- **完了条件**: Amplify でビルドが成功する

### ✅ Task 3.16: 環境変数設定

- **説明**: Amplify Console で環境変数追加
- **ファイル**: amplify.yml
- **工数**: 0.5h
- **依存**: 3.15
- **完了条件**: NEXT_PUBLIC_* 変数が読み込まれる

### ✅ Task 3.17: Playwright テスト調整

- **説明**: Next.js URL に対応
- **ファイル**: `frontend-nextjs/playwright.config.ts`, `e2e/auth.spec.ts`
- **工数**: 2-3h
- **依存**: 3.14
- **完了条件**: Playwright テストが成功する

### ✅ Task 3.18: デプロイと検証

- **説明**: ビルド検証、本番確認準備
- **ファイル**: -
- **工数**: 1-2h
- **依存**: 3.16, 3.17
- **完了条件**: npm run build が成功、全ページが生成される

---

## 実装スケジュール（3週間）

### Week 1: TASK1 週次レポート + TASK2 準備

| 日程 | タスク | 工数 | 累計 |
|------|--------|------|------|
| Day 1 | Task 1.1-1.3（Lambda骨組み、集計ロジック） | 4-5h | 4-5h |
| Day 2 | Task 1.4-1.5（Bedrock、LINE統合） | 3-4h | 7-9h |
| Day 3 | Task 1.6-1.8（Terraform、IAM） | 2-2.5h | 9-11.5h |
| Day 4 | Task 1.9-1.11（テスト、デプロイ） | 3.5-5.5h | 12.5-17h |
| Day 5 | Task 2.1-2.3（Device Farm、S3、CloudFront） | 2h | 14.5-19h |

**Week 1 合計**: 14.5-19時間

### Week 2: TASK2 完了 + TASK3 準備

| 日程 | タスク | 工数 | 累計 |
|------|--------|------|------|
| Day 6 | Task 2.4-2.6（テストユーザー管理Lambda、IAM） | 3.5-4.5h | 3.5-4.5h |
| Day 7 | Task 2.7-2.8（クリティカルパステスト、YAML） | 4-5.5h | 7.5-10h |
| Day 8 | Task 2.9-2.10（GitHub Actions、検証） | 3-5h | 10.5-15h |
| Day 9 | Task 3.1-3.3（Next.js初期化、NextAuth） | 4-6.5h | 14.5-21.5h |
| Day 10 | Task 3.4-3.6（ミドルウェア、APIクライアント、コンポーネント） | 4.5-7h | 19-28.5h |

**Week 2 合計**: 19-28.5時間

### Week 3: TASK3 完了

| 日程 | タスク | 工数 | 累計 |
|------|--------|------|------|
| Day 11 | Task 3.7-3.8（ログイン、ホーム） | 3.5-5h | 3.5-5h |
| Day 12 | Task 3.9-3.10（プロフィール、目標） | 4-6h | 7.5-11h |
| Day 13 | Task 3.11-3.13（食事登録、一覧、総評） | 5-7h | 12.5-18h |
| Day 14 | Task 3.14-3.16（SEO、Amplify設定） | 2.5-3.5h | 15-21.5h |
| Day 15 | Task 3.17-3.18（Playwrightテスト、デプロイ検証） | 3-5h | 18-26.5h |

**Week 3 合計**: 18-26.5時間

**総工数**: 51.5-74時間（バッファ込み）

---

## 進捗状況

- [x] Task 1: 週次レポート機能（11タスク）
- [x] Task 2: Device Farm E2E テスト統合（10タスク）
- [x] Task 3: Next.js フロントエンド移行（18タスク）

---

## 並行実行の工夫

### Task 1
- **Task 1.6-1.10（Terraform）** は **Task 1.1-1.5（Lambda実装）** と並行可能

### Task 2
- **Task 2.2-2.3（S3、CloudFront）** と **Task 2.4-2.6（Lambda、IAM）** と **Task 2.7-2.8（テスト、YAML）** は並行可能

### Task 3
- **Task 3.6（コンポーネント移植）** は **Task 3.3-3.5（認証、API）** と並行可能
- **Task 3.15-3.16（Amplify設定）** は **Task 3.1-3.14（ページ実装）** と並行可能

---

**最終更新**: 2025年12月8日  
**バージョン**: 1.0
