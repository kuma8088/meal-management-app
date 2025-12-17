output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    users        = aws_dynamodb_table.users.name
    meals        = aws_dynamodb_table.meals.name
    foods        = aws_dynamodb_table.foods.name
    goals        = aws_dynamodb_table.goals.name
    advice_usage = aws_dynamodb_table.advice_usage.name
    nonce        = aws_dynamodb_table.nonce.name
  }
}

output "s3_buckets" {
  description = "S3 bucket names"
  value = {
    terraform_state = aws_s3_bucket.terraform_state.bucket
    food_master     = aws_s3_bucket.food_master.bucket
    barcode_images  = aws_s3_bucket.barcode_images.bucket
    frontend        = aws_s3_bucket.frontend.bucket
  }
}

output "s3_bucket_arns" {
  description = "S3 bucket ARNs"
  value = {
    terraform_state = aws_s3_bucket.terraform_state.arn
    food_master     = aws_s3_bucket.food_master.arn
    barcode_images  = aws_s3_bucket.barcode_images.arn
    frontend        = aws_s3_bucket.frontend.arn
  }
}

output "frontend_website_endpoint" {
  description = "Frontend S3 website endpoint"
  value       = aws_s3_bucket_website_configuration.frontend.website_endpoint
}

# Cognito outputs
output "cognito_user_pool_id" {
  description = "Cognito User Pool ID"
  value       = aws_cognito_user_pool.main.id
}

output "cognito_user_pool_arn" {
  description = "Cognito User Pool ARN"
  value       = aws_cognito_user_pool.main.arn
}

output "cognito_user_pool_endpoint" {
  description = "Cognito User Pool endpoint"
  value       = aws_cognito_user_pool.main.endpoint
}

output "cognito_user_pool_client_id" {
  description = "Cognito User Pool Client ID"
  value       = aws_cognito_user_pool_client.web_client.id
  sensitive   = true
}

output "cognito_user_pool_domain" {
  description = "Cognito User Pool domain"
  value       = aws_cognito_user_pool_domain.main.domain
}

# IAM outputs
output "lambda_execution_role_arn" {
  description = "Lambda execution role ARN"
  value       = aws_iam_role.lambda_execution_role.arn
}

output "lambda_execution_role_name" {
  description = "Lambda execution role name"
  value       = aws_iam_role.lambda_execution_role.name
}

output "api_gateway_cloudwatch_role_arn" {
  description = "API Gateway CloudWatch role ARN"
  value       = aws_iam_role.api_gateway_cloudwatch_role.arn
}
