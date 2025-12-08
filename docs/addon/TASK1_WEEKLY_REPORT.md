# タスク1: 週次レポート機能

## 概要

毎週日曜日 20:00 JST にユーザーに LINE で自動配信される週次の食事レポートを実装。

## 新規要件

| 要件ID | 説明 |
|--------|------|
| 要件1.1 | EventBridge Scheduler による毎週日曜 20:00 JST の自動実行 |
| 要件1.2 | 過去7日間の食事データを集計し週次統計を生成 |
| 要件1.3 | Bedrock Claude API で週次アドバイスを生成（300文字以内） |
| 要件1.4 | LINE Push Message API で全ユーザーに自動配信 |
| 要件1.5 | ユーザー設定で配信ON/OFF を制御（オプション） |
| 要件1.6 | 配信失敗時のリトライと通知機能 |

## 新規設計

### アーキテクチャ

```
EventBridge Scheduler
  (毎週日曜 20:00 JST)
         │
         ▼
  Lambda: weekly_report
         │
    ┌────┴────┬────────┬─────────┐
    ▼         ▼        ▼         ▼
 Users    Meals    Goals    DynamoDB
   テ      テ       テ       データ
   ーブ    ーブ     ーブ    取得
   ル      ル       ル
         │
         ▼
  集計: 平均カロリー、PFC、目標達成日数
         │
         ▼
  Bedrock Claude API
  週次アドバイス生成
         │
         ▼
  LINE Messaging API
  Push Message 配信
         │
         ▼
  WeeklyReports テーブル（履歴保存）
```

### データフロー

1. **ユーザー取得**: Users テーブルから全アクティブユーザーを取得
2. **週次集計**: 
   - 過去7日間の食事データをGSI1で取得
   - 日平均カロリー、タンパク質、脂質、炭水化物を計算
   - 目標達成日数をカウント
   - 最も多い食事タイプを分析
3. **アドバイス生成**: Bedrock Claude にプロンプトを送信
4. **LINE配信**: 各ユーザーに Push Message で送信
5. **履歴保存**: WeeklyReports テーブルに記録（オプション）

### 新規リソース

#### Lambda 関数
- **関数名**: `meal-management-app-weekly-report-{env}`
- **ハンドラー**: `weekly_report.lambda_handler`
- **実行時間**: Python 3.11
- **タイムアウト**: 300 秒（5分）
- **メモリ**: 512 MB

#### 環境変数
```
USERS_TABLE_NAME=Users
MEALS_TABLE_NAME=Meals
GOALS_TABLE_NAME=Goals
LINE_CHANNEL_ACCESS_TOKEN={LINE_TOKEN}
BEDROCK_MODEL_ID=anthropic.claude-3-haiku-20240307-v1:0
AWS_REGION=ap-northeast-1
```

#### IAM 権限（追加）
```
- dynamodb:Scan (Users テーブル)
- dynamodb:Query (Meals テーブル、GSI1 使用)
- dynamodb:GetItem (Goals テーブル)
- dynamodb:PutItem (WeeklyReports テーブル)
- bedrock:InvokeModel (Claude 3 Haiku)
- logs:CreateLogGroup, logs:CreateLogStream, logs:PutLogEvents
```

#### EventBridge ルール
- **スケジュール**: `cron(0 11 ? * SUN *)` (毎週日曜 20:00 JST = UTC 11:00)
- **ターゲット**: Lambda 関数 `weekly_report`

### 新規テーブル属性

**Users テーブルに追加**:
```
weekly_report_enabled: boolean  # 配信ON/OFF（デフォルト: true）
report_delivery_time: string    # 配信時刻（将来拡張用、デフォルト: "20:00"）
```

**新規テーブル: WeeklyReports**（履歴保存用、オプション）
```
PK: report_id (UUID)
SK: user_id#week_start_date

Attributes:
- user_id: string
- week_start_date: string (YYYY-MM-DD)
- week_end_date: string (YYYY-MM-DD)
- avg_daily_calories: number
- avg_daily_protein: number
- avg_daily_fat: number
- avg_daily_carbs: number
- target_achievement_days: number (0-7)
- advice: string (300文字以内)
- created_at: string (ISO8601)
```

## 工数見積もり（最適化版）

| フェーズ | 工数 | 詳細 |
|---------|------|------|
| Phase 1: Lambda実装 | 2-3h | weekly_report ハンドラー、ヘルパー関数 |
| Phase 2: EventBridge | 1-2h | スケジュール設定、Lambda トリガー |
| Phase 3: Lambda リソース | 1-2h | Terraform リソース定義 |
| Phase 4: IAM ポリシー | 0.5-1h | Bedrock 権限追加 |
| Phase 5: LINE 実装 | 2-3h | Push Message クライアント |
| Phase 6: テスト | 2-3h | ユニット、統合テスト |
| Phase 7: デプロイ | 1-2h | Terraform apply、検証 |
| **合計** | **9-16h** | 元の計画から50%削減 |

## 完了基準

- [ ] Lambda 関数が毎週日曜 20:00 JST に自動実行される
- [ ] 週次集計が正確に計算される
- [ ] Bedrock で 300 文字以内のアドバイスが生成される
- [ ] LINE Push Message が全ユーザーに配信される
- [ ] CloudWatch Logs で実行ログが確認できる
- [ ] 配信失敗時のリトライが機能する

## リスク管理

| リスク | 影響 | 対策 |
|--------|------|------|
| Lambda タイムアウト（ユーザー数増加） | 高 | タイムアウト5分、将来は Step Functions へ移行 |
| Bedrock API コスト超過 | 中 | 月間利用上限設定、キャッシング検討 |
| LINE 配信失敗 | 中 | リトライロジック、DLQ でエラー通知 |
| 週次集計の計算誤差 | 高 | プロパティテストで担保 |

---

**次**: タスク2（Device Farm）に進む
