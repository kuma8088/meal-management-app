output "dynamodb_tables" {
  description = "DynamoDB table names"
  value = {
    users        = aws_dynamodb_table.users.name
    meals        = aws_dynamodb_table.meals.name
    foods        = aws_dynamodb_table.foods.name
    goals        = aws_dynamodb_table.goals.name
    advice_usage = aws_dynamodb_table.advice_usage.name
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
