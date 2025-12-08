# E2E Testing Infrastructure
# Note: Device Farm is not available in the target region (ap-northeast-1/us-east-1)
# E2E testing is performed using Playwright with GitHub Actions
#
# This file is reserved for future Device Farm configuration if migrating to us-west-2

# AWS Provider for Device Farm (temporary for state cleanup)
provider "aws" {
  alias  = "devicefarm"
  region = "us-east-1"
}

# S3 Bucket for Test Artifacts and Reports
resource "aws_s3_bucket" "test_artifacts" {
  bucket = "${var.project_name}-test-artifacts-${var.environment}"

  tags = {
    Name        = "${var.project_name}-test-artifacts-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# S3 Bucket Versioning
resource "aws_s3_bucket_versioning" "test_artifacts" {
  bucket = aws_s3_bucket.test_artifacts.id

  versioning_configuration {
    status = "Enabled"
  }
}

# S3 Bucket Encryption
resource "aws_s3_bucket_server_side_encryption_configuration" "test_artifacts" {
  bucket = aws_s3_bucket.test_artifacts.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# S3 Bucket Public Access Block
resource "aws_s3_bucket_public_access_block" "test_artifacts" {
  bucket = aws_s3_bucket.test_artifacts.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# S3 Bucket Lifecycle Policy - Auto-delete old test results
resource "aws_s3_bucket_lifecycle_configuration" "test_artifacts" {
  bucket = aws_s3_bucket.test_artifacts.id

  rule {
    id     = "delete-old-test-reports"
    status = "Enabled"

    filter {}

    expiration {
      days = 30
    }
  }
}

# Outputs
output "test_artifacts_bucket" {
  description = "S3 Bucket for test artifacts and reports"
  value       = aws_s3_bucket.test_artifacts.id
}
