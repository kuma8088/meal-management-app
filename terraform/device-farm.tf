# E2E Testing Infrastructure with Device Farm Integration
# Device Farm is only available in us-west-2
# Main infrastructure (ap-northeast-1) can be accessed via public API endpoints
#
# Architecture:
# - ap-northeast-1: Lambda, API Gateway, DynamoDB (main application)
# - us-west-2: Device Farm project, device pools (testing infrastructure)
# - No VPC peering needed: Device Farm accesses public API Gateway endpoints

# ============================================================================
# S3 Bucket for Test Artifacts and Reports (ap-northeast-1)
# ============================================================================

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

# ============================================================================
# Device Farm Resources (us-west-2)
# ============================================================================

# Device Farm Project
resource "aws_devicefarm_project" "mealmgtsystem" {
  name     = "${var.project_name}-e2e-tests-${var.environment}"
  provider = aws.us_west_2

  tags = {
    Name        = "${var.project_name}-e2e-tests-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Device Pool: Android
# max_devices = 1 for cost optimization (1 device per test run)
resource "aws_devicefarm_device_pool" "android" {
  name        = "${var.project_name}-android-pool-${var.environment}"
  project_arn = aws_devicefarm_project.mealmgtsystem.arn
  provider    = aws.us_west_2
  max_devices = 1

  # Use PLATFORM instead of MANUFACTURER for better APPIUM_WEB_NODE compatibility
  rule {
    attribute = "PLATFORM"
    operator  = "EQUALS"
    value     = "\"ANDROID\""
  }

  rule {
    attribute = "OS_VERSION"
    operator  = "GREATER_THAN_OR_EQUALS"
    value     = "\"11\""
  }

  tags = {
    Name        = "${var.project_name}-android-pool-${var.environment}"
    Environment = var.environment
    DeviceType  = "Android"
  }
}

# Device Pool: iOS
# max_devices = 1 for cost optimization (1 device per test run)
resource "aws_devicefarm_device_pool" "ios" {
  name        = "${var.project_name}-ios-pool-${var.environment}"
  project_arn = aws_devicefarm_project.mealmgtsystem.arn
  provider    = aws.us_west_2
  max_devices = 1

  rule {
    attribute = "PLATFORM"
    operator  = "EQUALS"
    value     = "\"IOS\""
  }

  rule {
    attribute = "OS_VERSION"
    operator  = "GREATER_THAN_OR_EQUALS"
    value     = "\"15\""
  }

  tags = {
    Name        = "${var.project_name}-ios-pool-${var.environment}"
    Environment = var.environment
    DeviceType  = "iOS"
  }
}

# ============================================================================
# IAM Role for Device Farm (us-west-2)
# ============================================================================

resource "aws_iam_role" "device_farm" {
  name_prefix = "${var.project_name}-device-farm-"
  provider    = aws.us_west_2

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Principal = {
          Service = "devicefarm.amazonaws.com"
        }
        Action = "sts:AssumeRole"
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-device-farm-role-${var.environment}"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for Device Farm: S3 access
resource "aws_iam_role_policy" "device_farm_s3" {
  name_prefix = "${var.project_name}-device-farm-s3-"
  role        = aws_iam_role.device_farm.id
  provider    = aws.us_west_2

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:ListBucket",
          "s3:DeleteObject"
        ]
        Resource = [
          aws_s3_bucket.test_artifacts.arn,
          "${aws_s3_bucket.test_artifacts.arn}/*"
        ]
      }
    ]
  })
}

# ============================================================================
# Outputs
# ============================================================================

output "test_artifacts_bucket" {
  description = "S3 Bucket for test artifacts and reports"
  value       = aws_s3_bucket.test_artifacts.id
}

output "device_farm_project_arn" {
  description = "Device Farm Project ARN"
  value       = aws_devicefarm_project.mealmgtsystem.arn
}

output "device_farm_android_pool_arn" {
  description = "Device Farm Android Device Pool ARN"
  value       = aws_devicefarm_device_pool.android.arn
}

output "device_farm_ios_pool_arn" {
  description = "Device Farm iOS Device Pool ARN"
  value       = aws_devicefarm_device_pool.ios.arn
}
