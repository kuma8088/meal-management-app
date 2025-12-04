# Users テーブル
resource "aws_dynamodb_table" "users" {
  name         = "${var.project_name}-users-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id"

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "line_user_id"
    type = "S"
  }

  attribute {
    name = "cognito_user_id"
    type = "S"
  }

  global_secondary_index {
    name            = "LineUserIdIndex"
    hash_key        = "line_user_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "CognitoUserIdIndex"
    hash_key        = "cognito_user_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-users-${var.environment}"
  }
}

# Meals テーブル
resource "aws_dynamodb_table" "meals" {
  name         = "${var.project_name}-meals-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "meal_id"
  range_key    = "user_id_timestamp"

  attribute {
    name = "meal_id"
    type = "S"
  }

  attribute {
    name = "user_id_timestamp"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "timestamp"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdTimestampIndex"
    hash_key        = "user_id"
    range_key       = "timestamp"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-meals-${var.environment}"
  }
}

# Foods テーブル
resource "aws_dynamodb_table" "foods" {
  name         = "${var.project_name}-foods-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "food_id"

  attribute {
    name = "food_id"
    type = "S"
  }

  attribute {
    name = "name"
    type = "S"
  }

  attribute {
    name = "jan_code"
    type = "S"
  }

  global_secondary_index {
    name            = "NameIndex"
    hash_key        = "name"
    range_key       = "food_id"
    projection_type = "ALL"
  }

  global_secondary_index {
    name            = "JanCodeIndex"
    hash_key        = "jan_code"
    range_key       = "food_id"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-foods-${var.environment}"
  }
}

# Goals テーブル
resource "aws_dynamodb_table" "goals" {
  name         = "${var.project_name}-goals-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "goal_id"
  range_key    = "user_id"

  attribute {
    name = "goal_id"
    type = "S"
  }

  attribute {
    name = "user_id"
    type = "S"
  }

  attribute {
    name = "created_at"
    type = "S"
  }

  global_secondary_index {
    name            = "UserIdCreatedAtIndex"
    hash_key        = "user_id"
    range_key       = "created_at"
    projection_type = "ALL"
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-goals-${var.environment}"
  }
}

# AdviceUsage テーブル
resource "aws_dynamodb_table" "advice_usage" {
  name         = "${var.project_name}-advice-usage-${var.environment}"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "user_id_date"

  attribute {
    name = "user_id_date"
    type = "S"
  }

  ttl {
    attribute_name = "ttl"
    enabled        = true
  }

  point_in_time_recovery {
    enabled = true
  }

  server_side_encryption {
    enabled = true
  }

  tags = {
    Name = "${var.project_name}-advice-usage-${var.environment}"
  }
}
