# Device Farm E2E テスト統合ガイド

## 概要

このドキュメントは、AWS Device Farm を使用した E2E テスト統合の実装と運用方法を説明します。

## 実装状況

### ✅ 完了したタスク

#### Task 2.1-2.3: インフラ整備
- **CloudFront Distribution**: フロントエンド配信用の CDN 設定
  - `frontend/s3_oai.cloudfront_access_identity` でセキュアな S3 アクセス
  - キャッシュポリシー (CachingOptimized, CachingDisabled) で最適化
  - マルチキャッシュ動作: デフォルト/index.html/API 別設定

- **S3 Buckets**: テスト成果物保存用
  - `test_artifacts`: テストレポート・スクリーンショット・トレース保存
  - バージョニング・暗号化・ライフサイクル管理対応

#### Task 2.4-2.6: テストユーザー管理とIAM
- **Lambda 関数**: `test_user_management`
  - Cognito ユーザー管理 API
  - 操作: create, delete, get, list, reset_password
  - E2E テスト用テストユーザーの自動作成

- **IAM ポリシー**: 最小権限の原則に従う
  - Cognito Admin API (7 アクション)
  - S3 へのテスト成果物アップロード
  - CloudWatch Logs へのログ出力

- **API Gateway 統合**:
  ```
  POST /test-users?operation=create&email=test@example.com&password=Test123!
  DELETE /test-users?operation=delete&email=test@example.com
  GET /test-users?operation=list&filter_prefix=testuser-
  ```

#### Task 2.8: Test Specification (testspec.yml)
```yaml
phases:
  pre_test:      # Node.js 依存関係、Playwright ブラウザインストール
  test:          # Playwright E2E テスト実行 (Chromium ブラウザ)
  post_test:     # テスト結果・スクリーンショット・トレース収集

artifacts:       # HTML レポート、JSON 結果、スクリーンショット保存
env:             # APIベースURL、Cognito 設定、テストユーザー認証情報
```

#### Task 2.9: GitHub Actions ワークフロー (.github/workflows/device-farm.yml)
**トリガー条件**:
- PR がオープン・同期・再オープンされた時
- 毎週日曜日 9:00 UTC (日本時間 18:00)
- 手動トリガー (`workflow_dispatch`)

**実行フロー**:
1. **Build & Upload**: Node.js ビルド → Device Farm へアップロード
2. **Run Tests**: Android デバイスプール上でテスト実行
3. **Collect Results**: テストアーティファクト収集
4. **Report**: GitHub PR へコメント、Slack 通知

### ⚠️ Device Farm サービス利用可能性

**現在の状況**: Device Farm サービスはこのリージョンで **利用不可**

- **利用不可リージョン**: ap-northeast-1, us-east-1
- **利用可能リージョン**: us-west-2 のみ

**代替案**: Playwright E2E テスト (GitHub Actions で実行)
- Device Farm 不要
- クロスブラウザテスト対応 (Chrome, Firefox, Safari)
- ローカル開発でも同じテストを実行可能

## 実装詳細

### 20 個のクリティカルパス Playwright E2E テスト

ファイル: `frontend/e2e/critical-path.spec.ts`

#### セクション 1: 認証フロー (4テスト)
- `test 1`: ホームページが正しく表示される
- `test 2`: プロフィール情報が表示される
- `test 3`: プロフィール編集が可能
- `test 4`: ログアウト機能が動作する

#### セクション 2: 食事登録フロー (6テスト)
- `test 5`: 食事登録ページにアクセスできる
- `test 6`: 食事タイプを選択できる
- `test 7`: 食品検索が動作する
- `test 8`: 食品を選択して数量を入力できる
- `test 9`: 複数の食品を追加できる
- `test 10`: 食事を登録できる

#### セクション 3: 食事履歴と統計 (4テスト)
- `test 11`: 本日の食事一覧が表示される
- `test 12`: 日付を指定して食事を検索できる
- `test 13`: 栄養バランスが表示される
- `test 14`: 本日の摂取カロリーが表示される

#### セクション 4: 目標設定と AI アドバイス (4テスト)
- `test 15`: 目標設定ページにアクセスできる
- `test 16`: 体重目標を設定できる
- `test 17`: 現在の目標が表示される
- `test 18`: AI アドバイスを取得できる

#### セクション 5: 統合フロー (2テスト)
- `test 19`: 完全な一日のフロー実行
- `test 20`: ネットワークエラーが適切に処理される

### Terraform リソース構成

```hcl
# テスト成果物保存用 S3
aws_s3_bucket.test_artifacts
├── versioning (バージョン管理)
├── encryption (AES256 暗号化)
├── public_access_block (プライベート化)
└── lifecycle (30日後に自動削除)

# Lambda 関数: テストユーザー管理
aws_lambda_function.test_user_management
├── IAM ロール
├── Cognito Admin IAM ポリシー
└── API Gateway 統合 (/test-users エンドポイント)

# CloudFront: フロントエンド配信
aws_cloudfront_distribution.test_environment
├── キャッシュ動作 (default, index.html, /api/*)
├── Origin Access Identity (S3 セキュアアクセス)
└── Managed Cache Policies (AWS管理)
```

## Device Farm を有効にするための手順

### 1. 前提条件

- AWS アカウントで Device Farm をサポートするリージョン (us-west-2) へのアクセス権限
- AWS CLI v2 インストール済み
- 十分な AWS サービスクォータ

### 2. リージョン移行手順

#### ステップ 1: Terraform 設定を更新

```hcl
# terraform/provider.tf
provider "aws" {
  region = "us-west-2"  # Device Farm をサポートするリージョンに変更
}

# Device Farm provider を有効化
provider "aws" {
  alias  = "devicefarm"
  region = "us-west-2"
}
```

#### ステップ 2: Device Farm リソースを有効化

`terraform/device-farm.tf` ファイルの Device Farm リソース定義をコメント解除:

```hcl
# # Device Farm Project
# resource "aws_devicefarm_project" "mealmgtsystem" {
#   ...
# }

# # Device Farm Device Pools
# resource "aws_devicefarm_device_pool" "android" { ... }
```

#### ステップ 3: Terraform 適用

```bash
cd terraform
terraform plan
terraform apply
```

#### ステップ 4: GitHub Actions シークレットを設定

```bash
# AWS 認証情報を GitHub Secrets に追加
gh secret set AWS_ACCESS_KEY_ID
gh secret set AWS_SECRET_ACCESS_KEY
gh secret set AWS_ACCOUNT_ID
```

#### ステップ 5: GitHub Actions ワークフローを有効化

`.github/workflows/device-farm.yml` ファイルは既に設定済み。
PR 作成またはスケジュール実行で自動的に実行されます。

### 3. テスト実行

#### ローカル実行 (Playwright)

```bash
cd frontend

# 全テスト実行
npm run test:e2e

# 特定のテストファイルのみ
npm run test:e2e e2e/critical-path.spec.ts

# UI モードでインタラクティブ実行
npm run test:e2e:ui

# ヘッド付きモード (ブラウザ表示)
npm run test:e2e:headed
```

#### Device Farm で実行 (PR 作成時)

```bash
# PR を作成して自動実行
git push origin feature-branch
# → GitHub Actions が自動で Device Farm テストをトリガー
```

## トラブルシューティング

### Device Farm 接続エラー

**問題**: `dial tcp: lookup devicefarm.us-west-2.amazonaws.com: no such host`

**解決策**:
1. AWS CLI 認証情報を確認: `aws sts get-caller-identity`
2. リージョンが us-west-2 に設定されているか確認
3. IAM ユーザーに DeviceFarm 権限があるか確認

### テストアーティファクトが保存されない

**問題**: S3 に テスト成果物がアップロードされていない

**解決策**:
1. IAM ロールに S3 権限があるか確認
2. S3 バケット ポリシーを確認
3. CloudWatch Logs でエラーを確認

### Playwright テストがタイムアウト

**問題**: テスト実行中に API 呼び出しがタイムアウト

**解決策**:
1. `playwright.config.ts` の `timeout` 値を増加
2. API 依存モックが正しく設定されているか確認
3. ローカルで `npm run test:e2e:ui` で実行してデバッグ

## ベストプラクティス

### テスト記述

```typescript
// ❌ 固定の待機時間を使わない
await page.waitForTimeout(1000);

// ✅ 要素の出現を待つ
await expect(page.locator('text=Success')).toBeVisible({ timeout: 5000 });
```

### エラーハンドリング

```typescript
// ❌ 例外を無視する
try { /* ... */ } catch (e) { }

// ✅ エラーを明示的に処理
if (error instanceof NetworkError) {
  console.error('Network request failed:', error.message);
}
```

### パフォーマンス

```typescript
// ❌ 個別にクリック・入力
await page.locator('#field1').click();
await page.locator('#field1').fill('value1');

// ✅ 一度に複数フィールド入力
await page.fill('#field1', 'value1');
await page.fill('#field2', 'value2');
```

## リファレンス

- **Playwright Documentation**: https://playwright.dev/docs/intro
- **Device Farm Console**: https://us-west-2.console.aws.amazon.com/devicefarm/
- **GitHub Actions**: https://docs.github.com/en/actions
- **Terraform AWS Provider**: https://registry.terraform.io/providers/hashicorp/aws/latest/docs

## Q&A

### Q: Device Farm がサポートされたら自動で実行される？

**A**: はい。`terraform/device-farm.tf` のリソース定義をコメント解除して `terraform apply` すれば、GitHub Actions ワークフロー (`.github/workflows/device-farm.yml`) が自動的に Device Farm にテストを送信します。

### Q: ローカル開発でも Device Farm テストを実行できる？

**A**: いいえ。Device Farm はマネージドサービスのため、ローカルでは Playwright で同等のテストを実行できます。テストコードは同じため、Device Farm との切り替えは設定変更のみです。

### Q: テスト失敗時の通知方法は？

**A**: 設定方法により異なります:
- **GitHub**: PR にコメント自動追加
- **Slack**: `.github/workflows/device-farm.yml` の `SLACK_WEBHOOK_URL` に webhook を設定

### Q: 複数のデバイスで同時実行できる？

**A**: はい。`device-farm.yml` の `strategy.matrix` で複数のデバイスを指定すると、Device Farm 上で並列実行できます。現在は Android デバイスプールのみを使用しています（Web アプリのため iOS テストは不要）。

## 関連ドキュメント

- [CLAUDE.md](../CLAUDE.md): プロジェクト設定と開発ガイド
- [ARCHITECTURE.md](./ARCHITECTURE.md): システムアーキテクチャ
- [frontend/README.md](../frontend/README.md): フロントエンド開発ガイド
