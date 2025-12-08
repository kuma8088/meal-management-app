# タスク2: AWS Device Farm E2E テスト統合

## 概要

現在の Playwright E2E テストをクリティカルパス（20テストケース）に絞り、AWS Device Farm で自動実行する基盤を構築。

## 新規要件

| 要件ID | 説明 |
|--------|------|
| 要件2.1 | AWS Device Farm でのテスト自動実行 |
| 要件2.2 | S3 + CloudFront によるテスト環境ホスティング |
| 要件2.3 | Cognito テストユーザー管理 Lambda |
| 要件2.4 | Device Farm YAML 設定ファイルの作成 |
| 要件2.5 | GitHub Actions による CI/CD 統合 |
| 要件2.6 | クリティカルパステスト（20ケース）の実装 |

## 新規設計

### アーキテクチャ

```
GitHub PR 作成
      │
      ▼
GitHub Actions Workflow
      │
  ┌───┴───┬────────────────┐
  ▼       ▼                ▼
Build  Deploy          Create Test User
React   S3+            Lambda (Cognito)
       CloudFront            │
        │                    │
        └────────┬───────────┘
                 │
                 ▼
        Device Farm Project
                 │
        ┌────────┴────────┬──────────┐
        ▼                 ▼          ▼
    Build Phase    Pre-test Phase   Test Phase
    (npm ci)      (User Create)    (Playwright)
        │                │            │
        └────────────────┴────────────┘
                 │
                 ▼
        CloudWatch Logs
        テスト結果保存
                 │
                 ▼
        GitHub PR に結果コメント
```

### テスト環境構成

**S3 + CloudFront ホスティング**:
```
S3 バケット: {project}-test-hosting-{env}
  ├─ index.html
  ├─ build/ (React 静的ファイル)
  └─ ...

CloudFront Distribution:
  ├─ Origin: S3 バケット
  ├─ Default Root: index.html
  └─ HTTPS のみ
  
URL: https://d1234567890.cloudfront.net
```

### クリティカルパステスト（20ケース）

| カテゴリ | テスト数 | テストケース |
|---------|---------|------------|
| 認証 | 5 | ログイン・登録・確認コード・ログアウト・エラーハンドリング |
| プロフィール | 3 | 表示・BMR計算・更新 |
| 目標設定 | 3 | フォーム表示・減量目標・バリデーション |
| 食事登録 | 5 | ページ表示・食品検索・選択・栄養表示・完了 |
| 総評 | 4 | ページ表示・日付選択・サマリー・AIアドバイス |
| **合計** | **20** | - |

### 新規リソース

#### Lambda 関数
- **関数名**: `meal-management-app-test-user-management-{env}`
- **責務**: Cognito でテストユーザーを作成・削除
- **トリガー**: Device Farm Pre-test フェーズ

#### S3 バケット
- **バケット名**: `{project}-test-hosting-{env}`
- **用途**: React ビルド成果物の静的ホスティング
- **アクセス**: CloudFront のみ

#### CloudFront Distribution
- **オリジン**: S3 バケット
- **キャッシュ戦略**: 短期（5分）
- **HTTPS**: 必須

#### GitHub Actions ワークフロー
- **トリガー**: PR 作成・毎週日曜 0:00 UTC
- **ジョブ**:
  1. React ビルド
  2. S3 にデプロイ
  3. Device Farm テスト実行
  4. PR にコメント

### Device Farm 設定（testspec.yml）

```yaml
version: 0.1

env:
  variables:
    TEST_URL: "https://d1234567890.cloudfront.net"
    COGNITO_USER_POOL_ID: "{USER_POOL_ID}"
    COGNITO_CLIENT_ID: "{CLIENT_ID}"

phases:
  install:
    commands:
      - npm ci
      - npx playwright install

  pre_test:
    commands:
      - echo "Creating test user..."
      - aws lambda invoke --function-name test-user-management /tmp/user.json

  test:
    commands:
      - npx playwright test --config=playwright.config.devicefarm.ts

  post_test:
    commands:
      - echo "Cleanup..."
      - aws lambda invoke --function-name test-user-management /tmp/cleanup.json

artifacts:
  - playwright-report/**/*
  - test-results/**/*
```

## 工数見積もり（最適化版）

| フェーズ | 工数 | 詳細 |
|---------|------|------|
| Phase 1: Device Farm 環境 | 2-3h | プロジェクト作成、リソース定義 |
| Phase 2: テスト環境ホスティング | 4-5h | S3 + CloudFront、Terraform |
| Phase 3: クリティカルパステスト | 3-4h | 20 テストケースの実装 |
| Phase 4: YAML 設定 | 2-3h | Device Farm testspec.yml |
| Phase 5: テストユーザー管理 | 3-4h | Lambda 関数実装 |
| Phase 6: CI/CD 統合 | 2-3h | GitHub Actions ワークフロー |
| **合計** | **10-13h** | 計画から大幅削減 |

## 完了基準

- [ ] Device Farm プロジェクトが作成される
- [ ] S3 + CloudFront でテスト環境がホスティングされる
- [ ] 20 個のクリティカルパステストが実装される
- [ ] Device Farm で自動テスト実行が可能
- [ ] GitHub Actions で PR 作成時に自動実行される
- [ ] CloudWatch Logs にテスト結果が記録される

## コスト最適化

- **テスト実行頻度**: PR 作成時 + 毎週日曜日のみ
- **テストケース数**: 20 のみ（完全テストスイートでなく）
- **デバイス**: Chromium のみ（複数ブラウザ不要）
- **推定月額コスト**: $10-20

## リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| Device Farm コスト超過 | 高 | 実行頻度を制限、20テストのみ |
| Cognito Admin 権限エラー | 中 | Lambda に適切な IAM ロール付与 |
| テスト実行時間超過 | 中 | タイムアウト設定、並列実行しない |

---

**次**: タスク3（Next.js）に進む
