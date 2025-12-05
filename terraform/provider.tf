terraform {
  required_version = ">= 1.0"

  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }

  # 初回セットアップ時はローカルバックエンドを使用
  # S3バケット作成後、以下のS3バックエンドに切り替えてください:
  # backend "s3" {
  #   bucket       = "meal-management-app-terraform-state"
  #   key          = "terraform.tfstate"
  #   region       = "ap-northeast-1"
  #   encrypt      = true
  #   use_lockfile = true
  # }
}

provider "aws" {
  region = var.aws_region

  default_tags {
    tags = {
      Project     = "meal-management-app"
      Environment = var.environment
      ManagedBy   = "Terraform"
    }
  }
}
