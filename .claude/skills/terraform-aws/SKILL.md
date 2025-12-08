---
name: terraform-aws
description: Terraform で AWS インフラを構築する際のベストプラクティスを提供します。インフラ構築、Terraform、AWS、IaC、VPC、ECS、Lambda、RDS について言及している場合に使用してください。
---

# Terraform AWS

AWS インフラを Terraform で構築する際の設計パターン、セキュリティ、運用ベストプラクティス。

## クイックスタート

### 推奨ディレクトリ構成

```
infrastructure/
├── environments/
│   ├── dev/
│   │   ├── main.tf
│   │   ├── variables.tf
│   │   ├── outputs.tf
│   │   ├── terraform.tfvars
│   │   └── backend.tf
│   ├── stg/
│   └── prod/
├── modules/
│   ├── vpc/
│   ├── ecs/
│   └── rds/
└── README.md
```

### backend.tf（必須）

```hcl
terraform {
  backend "s3" {
    bucket         = "your-tfstate-bucket"
    key            = "env/dev/terraform.tfstate"
    region         = "ap-northeast-1"
    encrypt        = true
    dynamodb_table = "terraform-lock"
  }
}
```

## ワークフロー

```bash
# 1. フォーマット
terraform fmt -recursive

# 2. 検証
terraform validate

# 3. 計画（必ず出力保存）
terraform plan -out=tfplan

# 4. 適用（plan 結果を確認後）
terraform apply tfplan
```

## 必須タグ

全リソースに付与：

```hcl
locals {
  common_tags = {
    Environment = var.environment
    Project     = var.project_name
    Owner       = var.owner
    ManagedBy   = "terraform"
  }
}
```

## セキュリティ必須事項

### ❌ 絶対に避ける

- `cidr_blocks = ["0.0.0.0/0"]` で全ポート開放
- `Resource = "*"` + `Action = "*"` の IAM
- ハードコードされた認証情報
- `publicly_accessible = true` の RDS
- 暗号化なしの S3 / EBS / RDS

### ✅ 必ず実施

- S3: `server_side_encryption_configuration`
- RDS: `storage_encrypted = true`
- EBS: `encrypted = true`
- Secrets Manager で認証情報管理
- sensitive 変数に `sensitive = true`

## リファレンス

- **設計パターン**: [references/patterns.md](references/patterns.md) - VPC、ECS、Lambda、RDS のテンプレート
- **チェックリスト**: [references/checklist.md](references/checklist.md) - PR / apply 前の確認項目
