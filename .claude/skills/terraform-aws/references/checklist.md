# Terraform AWS レビューチェックリスト

PR / apply 前に確認する項目。

---

## 1. 基本確認

- [ ] `terraform fmt -recursive` を実行済み
- [ ] `terraform validate` がパス
- [ ] `terraform plan` で意図しない destroy がない
- [ ] 変更内容がコミットメッセージと一致

---

## 2. State 管理

- [ ] backend.tf で S3 + DynamoDB を設定
- [ ] state ファイルが暗号化されている（`encrypt = true`）
- [ ] 環境ごとに state が分離されている

---

## 3. タグ付け

- [ ] 全リソースに必須タグがある
  - [ ] `Environment`
  - [ ] `Project`
  - [ ] `Owner`
  - [ ] `ManagedBy = "terraform"`
- [ ] `Name` タグが命名規則に従っている

---

## 4. セキュリティ（Critical）

### IAM

- [ ] `Resource = "*"` + `Action = "*"` がない
- [ ] 最小権限の原則に従っている
- [ ] サービスロールに適切な信頼ポリシーがある

### Security Group

- [ ] `0.0.0.0/0` への不要なポート開放がない
- [ ] SSH (22) / RDP (3389) がインターネットに開放されていない
- [ ] Security Group 間の参照で制御している

### データ保護

- [ ] S3: `server_side_encryption_configuration` あり
- [ ] RDS: `storage_encrypted = true`
- [ ] EBS: `encrypted = true`
- [ ] Secrets Manager / Parameter Store で認証情報管理

### ネットワーク

- [ ] RDS / ElastiCache: `publicly_accessible = false`
- [ ] Lambda / ECS: Private Subnet に配置
- [ ] VPC Flow Logs が有効（prod 環境）

---

## 5. 高可用性（prod 環境）

- [ ] RDS: `multi_az = true`
- [ ] ECS: 複数 AZ にタスク分散
- [ ] ALB: 複数 AZ の Subnet を指定
- [ ] NAT Gateway: 複数 AZ（またはシングル AZ を許容する判断）

---

## 6. コスト最適化

- [ ] dev/stg で過剰なスペックになっていない
- [ ] 不要なリソース（古い AMI、未使用 EIP）がない
- [ ] NAT Gateway: dev では単一 AZ で十分か検討
- [ ] RDS: dev では `db.t3.micro` / `db.t4g.micro` で十分か検討

---

## 7. 運用性

- [ ] CloudWatch Logs が設定されている
- [ ] CloudWatch Alarms（CPU、メモリ、エラー率）
- [ ] リソース削除保護（prod 環境）
  - [ ] RDS: `deletion_protection = true`
  - [ ] S3: `lifecycle { prevent_destroy = true }`
  - [ ] ALB: `enable_deletion_protection = true`

---

## 8. バックアップ

- [ ] RDS: `backup_retention_period` が適切（prod: 30日推奨）
- [ ] S3: バージョニング有効（必要な場合）
- [ ] EBS: スナップショットポリシー（必要な場合）

---

## 9. 変数管理

- [ ] 機密情報が `terraform.tfvars` にハードコードされていない
- [ ] sensitive な変数に `sensitive = true`
- [ ] 環境ごとの差分が `tfvars` で管理されている

---

## 10. ドキュメント

- [ ] README.md に構成図がある
- [ ] 手動で実行が必要な手順が記載されている
- [ ] outputs.tf で必要な値が出力されている

---

## クイックコマンド

```bash
# フォーマット
terraform fmt -recursive

# 検証
terraform validate

# 計画
terraform plan -out=tfplan

# セキュリティスキャン
tfsec .

# コスト見積もり
infracost breakdown --path .
```
