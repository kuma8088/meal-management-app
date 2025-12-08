# AWS ポートフォリオ強化 - 追加機能ドキュメント

完成した食事管理アプリケーションを AWS ポートフォリオとして高度化する 3 つの大型タスクの詳細設計。

## 📋 ドキュメント一覧

### [TASK1_WEEKLY_REPORT.md](./TASK1_WEEKLY_REPORT.md)
**タスク1: 週次レポート機能**（優先度: 最高）

毎週日曜 20:00 JST にユーザーに LINE で自動配信される週次食事レポート。

**主要内容**:
- EventBridge Scheduler による自動実行
- Bedrock Claude での週次アドバイス生成
- LINE Push Message API での配信
- 新規 IAM 権限・Lambda 環境変数

**工数**: 9-16 時間（計画から 50% 削減）  
**完了定義**: Lambda が毎週自動実行 + LINE 配信確認

---

### [TASK2_DEVICE_FARM.md](./TASK2_DEVICE_FARM.md)
**タスク2: AWS Device Farm E2E テスト統合**（優先度: 中）

クリティカルパスの 20 テストケースを AWS Device Farm で自動実行。

**主要内容**:
- S3 + CloudFront によるテスト環境ホスティング
- Device Farm での自動テスト実行
- Cognito テストユーザー管理 Lambda
- GitHub Actions との CI/CD 統合
- testspec.yml 設定

**工数**: 10-13 時間（計画から大幅削減）  
**テストケース**: 20（認証5、プロフィール3、目標3、食事5、総評4）  
**完了定義**: Device Farm で PR 作成時に自動実行 + テスト結果確認

---

### [TASK3_NEXTJS_MIGRATION.md](./TASK3_NEXTJS_MIGRATION.md)
**タスク3: Next.js フロントエンド移行**（優先度: 中）

React → Next.js Pages Router への段階的移行。

**主要内容**:
- Next.js 14 Pages Router での初期化
- NextAuth.js + Cognito 認証統合
- 既存 React コンポーネントの移植
- 7 ページの段階的実装（フェーズ A-C）
- AWS Amplify Hosting デプロイ
- 既存 Playwright テストとの互換性確保

**工数**: 25-35 時間（計画から 45% 削減）  
**移行フェーズ**:
- Phase A: 認証層（4-6h）
- Phase B: SEO 重点ページ（8-10h）
- Phase C: 残りのページ（8-10h）

**完了定義**: Amplify で本番デプロイ + Playwright テスト成功

---

## 🎯 実装スケジュール

### Week 1: タスク1 実装 + タスク2 環境構築

**Monday-Wednesday**: タスク1 Lambda 実装（4-6h）
**Wednesday-Thursday**: タスク2 環境構築（4-5h）
**Friday**: タスク1 デプロイ・検証（2-3h）

### Week 2: タスク1 検証 + タスク2 完了 + タスク3 開始

**Monday-Tuesday**: タスク2 テスト・CI 統合（6-8h）
**Wednesday-Friday**: タスク3 Phase A-B（8-10h）

### Week 3: タスク3 完了 + ユーザーテスト

**Monday-Wednesday**: タスク3 Phase C（6-8h）
**Thursday-Friday**: ユーザーテスト + 本番デプロイ（4-6h）

**合計**: 14-20 日間（並行実行による短縮）

---

## 📊 統計

### 工数サマリー

| タスク | 計画 | 最適化 | 削減率 |
|--------|------|--------|--------|
| タスク1 | 18-27h | 9-16h | 50% |
| タスク2 | 22-31h | 10-13h | 大幅 |
| タスク3 | 48-65h | 25-35h | 45% |
| **合計** | **88-123h** | **44-64h** | **45%** |

### コスト見積もり（月額）

| サービス | 推定コスト |
|---------|----------|
| EventBridge Scheduler | $0.01 |
| Lambda（週次レポート） | $1-5 |
| Bedrock（週次アドバイス） | $5-10 |
| Device Farm（週次テスト） | $10-20 |
| Amplify Hosting | $5-15 |
| **合計** | **$21-51/月** |

---

## 🔍 クイックガイド

### 「この実装計画の全体像を知りたい」
→ このファイルの「実装スケジュール」セクション

### 「タスク1 の実装を始めたい」
→ [TASK1_WEEKLY_REPORT.md](./TASK1_WEEKLY_REPORT.md)

### 「Device Farm の設定を知りたい」
→ [TASK2_DEVICE_FARM.md](./TASK2_DEVICE_FARM.md)

### 「Next.js 移行の詳細を知りたい」
→ [TASK3_NEXTJS_MIGRATION.md](./TASK3_NEXTJS_MIGRATION.md)

### 「工数を短縮する工夫を知りたい」
→ 各ドキュメントの「工数見積もり」セクション

---

## 📌 実装開始チェックリスト

- [ ] タスク1-3 の要件を確認した
- [ ] 3 つのタスクの新規 IAM 権限を把握した
- [ ] 各タスクの新規リソース（Lambda、テーブル等）を理解した
- [ ] 工数見積もりと並行実行スケジュールを確認した
- [ ] 各タスクの完了基準を把握した

---

## 🚀 依存関係

### 実装順序（推奨）

1. **タスク1**: 週次レポート機能（独立、最速着手可能）
2. **タスク2**: Device Farm 統合（タスク1 と並行可能）
3. **タスク3**: Next.js 移行（タスク2 完了後を推奨）

### 並行実行の工夫

- タスク1・2 は Week 1-2 で並行実行
- タスク3 は Week 2-3 で段階的実装
- テスト環境（Device Farm）完成後に Next.js テスト調整

---

## ✅ 完了定義

**環境構築完了** + **ユーザーテスト合格**（1 日）

- [ ] タスク1: 本番環境で週次レポート 1 回分実行完了
- [ ] タスク2: Device Farm で PR 作成時に自動テスト実行確認
- [ ] タスク3: Amplify で Next.js 本番デプロイ完了
- [ ] ユーザーテスト: LINE・ブラウザの全ユースケース検証完了

---

**最終更新**: 2025年12月8日  
**バージョン**: 1.0

---

**参考**: 詳細は各タスクドキュメントを参照
