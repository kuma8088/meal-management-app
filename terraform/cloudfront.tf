# CloudFront Cache Policies (Managed)
data "aws_cloudfront_cache_policy" "managed_caching_optimized" {
  name = "Managed-CachingOptimized"
}

data "aws_cloudfront_cache_policy" "managed_caching_disabled" {
  name = "Managed-CachingDisabled"
}

# CloudFront Origin Request Policy (Managed)
data "aws_cloudfront_origin_request_policy" "managed_all_viewer" {
  name = "Managed-AllViewerExceptHostHeader"
}

# CloudFront Distribution for Test Environment Hosting
resource "aws_cloudfront_distribution" "test_environment" {
  enabled             = true
  default_root_object = "index.html"

  # SPA用カスタムエラーレスポンス: 403/404時に index.html を返す
  custom_error_response {
    error_code            = 403
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  custom_error_response {
    error_code            = 404
    response_code         = 200
    response_page_path    = "/index.html"
    error_caching_min_ttl = 0
  }

  origin {
    domain_name = aws_s3_bucket.frontend.bucket_regional_domain_name
    origin_id   = "S3-frontend"

    s3_origin_config {
      origin_access_identity = aws_cloudfront_origin_access_identity.s3_oai.cloudfront_access_identity_path
    }
  }

  default_cache_behavior {
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-frontend"
    compress         = true

    cache_policy_id = data.aws_cloudfront_cache_policy.managed_caching_optimized.id

    viewer_protocol_policy = "redirect-to-https"
  }

  # キャッシュ動作: index.html は常に新鮮（テスト環境）
  ordered_cache_behavior {
    path_pattern     = "index.html"
    allowed_methods  = ["GET", "HEAD", "OPTIONS"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-frontend"
    compress         = true

    cache_policy_id          = data.aws_cloudfront_cache_policy.managed_caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.managed_all_viewer.id

    viewer_protocol_policy = "redirect-to-https"
  }

  # キャッシュ動作: API統合の場合
  ordered_cache_behavior {
    path_pattern     = "/api/*"
    allowed_methods  = ["GET", "HEAD", "OPTIONS", "PUT", "POST", "PATCH", "DELETE"]
    cached_methods   = ["GET", "HEAD"]
    target_origin_id = "S3-frontend"
    compress         = true

    cache_policy_id          = data.aws_cloudfront_cache_policy.managed_caching_disabled.id
    origin_request_policy_id = data.aws_cloudfront_origin_request_policy.managed_all_viewer.id

    viewer_protocol_policy = "https-only"
  }

  restrictions {
    geo_restriction {
      restriction_type = "none"
    }
  }

  viewer_certificate {
    cloudfront_default_certificate = true
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-cloudfront"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudFront Origin Access Identity for S3
resource "aws_cloudfront_origin_access_identity" "s3_oai" {
  comment = "${var.project_name}-${var.environment}-s3-oai"
}

# S3 Bucket Policy for CloudFront Access
resource "aws_s3_bucket_policy" "cloudfront_access" {
  bucket = aws_s3_bucket.frontend.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Sid    = "CloudFrontAccess"
        Effect = "Allow"
        Principal = {
          AWS = aws_cloudfront_origin_access_identity.s3_oai.iam_arn
        }
        Action   = "s3:GetObject"
        Resource = "${aws_s3_bucket.frontend.arn}/*"
      }
    ]
  })
}

# Outputs
output "cloudfront_domain_name" {
  description = "CloudFront domain name for test environment"
  value       = aws_cloudfront_distribution.test_environment.domain_name
}

output "cloudfront_distribution_id" {
  description = "CloudFront distribution ID"
  value       = aws_cloudfront_distribution.test_environment.id
}
