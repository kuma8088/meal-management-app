# ========================================
# モニタリング設定
# Task 19: エラーハンドリングとロギングの実装
# 要件: 14.1, 14.2, 14.3, 14.4, 14.5
# ========================================

# ========================================
# SNS通知設定
# ========================================

# SNSトピック - アラート通知用
resource "aws_sns_topic" "alerts" {
  name = "${var.project_name}-${var.environment}-alerts"

  tags = {
    Name        = "${var.project_name}-${var.environment}-alerts"
    Environment = var.environment
    Project     = var.project_name
  }
}

# SNSトピックサブスクリプション（メール）
# 注意: 実際の運用では、メールアドレスは変数で管理し、
# サブスクリプションは手動で確認する必要があります
resource "aws_sns_topic_subscription" "alerts_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.alerts.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# ========================================
# CloudWatch Log Groups
# ========================================

# Lambda関数のログは自動的に /aws/lambda/<function_name> に作成されますが、
# 保持期間を明示的に設定します

resource "aws_cloudwatch_log_group" "line_handler" {
  name              = "/aws/lambda/${aws_lambda_function.line_handler.function_name}"
  retention_in_days = var.log_retention_days
  skip_destroy      = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-line-handler-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "meal_registration" {
  name              = "/aws/lambda/${aws_lambda_function.meal_registration.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-meal-registration-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "goal_management" {
  name              = "/aws/lambda/${aws_lambda_function.goal_management.function_name}"
  retention_in_days = var.log_retention_days
  skip_destroy      = true

  tags = {
    Name        = "${var.project_name}-${var.environment}-goal-management-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

resource "aws_cloudwatch_log_group" "daily_summary" {
  name              = "/aws/lambda/${aws_lambda_function.daily_summary.function_name}"
  retention_in_days = var.log_retention_days

  tags = {
    Name        = "${var.project_name}-${var.environment}-daily-summary-logs"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ========================================
# CloudWatch Alarms - Lambda関数
# ========================================

# LINE Handler Lambda - エラー率アラーム
resource "aws_cloudwatch_metric_alarm" "line_handler_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-line-handler-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300 # 5分
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "LINE Handler Lambda関数のエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.line_handler.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-line-handler-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# LINE Handler Lambda - 実行時間アラーム
resource "aws_cloudwatch_metric_alarm" "line_handler_duration" {
  alarm_name          = "${var.project_name}-${var.environment}-line-handler-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 25000 # 25秒（タイムアウト30秒の80%）
  alarm_description   = "LINE Handler Lambda関数の実行時間が閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.line_handler.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-line-handler-duration"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Meal Registration Lambda - エラー率アラーム
resource "aws_cloudwatch_metric_alarm" "meal_registration_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-meal-registration-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Meal Registration Lambda関数のエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.meal_registration.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-meal-registration-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Goal Management Lambda - エラー率アラーム
resource "aws_cloudwatch_metric_alarm" "goal_management_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-goal-management-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Goal Management Lambda関数のエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.goal_management.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-goal-management-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Daily Summary Lambda - エラー率アラーム
resource "aws_cloudwatch_metric_alarm" "daily_summary_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-daily-summary-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Errors"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "Daily Summary Lambda関数のエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.daily_summary.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-daily-summary-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Daily Summary Lambda - 実行時間アラーム（Bedrock呼び出しがあるため）
resource "aws_cloudwatch_metric_alarm" "daily_summary_duration" {
  alarm_name          = "${var.project_name}-${var.environment}-daily-summary-duration"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Duration"
  namespace           = "AWS/Lambda"
  period              = 300
  statistic           = "Average"
  threshold           = 48000 # 48秒（タイムアウト60秒の80%）
  alarm_description   = "Daily Summary Lambda関数の実行時間が閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    FunctionName = aws_lambda_function.daily_summary.function_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-daily-summary-duration"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ========================================
# CloudWatch Alarms - API Gateway
# ========================================

# API Gateway - 4xxエラー率アラーム
resource "aws_cloudwatch_metric_alarm" "api_gateway_4xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-api-gateway-4xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "4XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 50
  alarm_description   = "API Gatewayの4xxエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-gateway-4xx-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway - 5xxエラー率アラーム
resource "aws_cloudwatch_metric_alarm" "api_gateway_5xx_errors" {
  alarm_name          = "${var.project_name}-${var.environment}-api-gateway-5xx-errors"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "5XXError"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "API Gatewayの5xxエラーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-gateway-5xx-errors"
    Environment = var.environment
    Project     = var.project_name
  }
}

# API Gateway - レイテンシーアラーム
resource "aws_cloudwatch_metric_alarm" "api_gateway_latency" {
  alarm_name          = "${var.project_name}-${var.environment}-api-gateway-latency"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 2
  metric_name         = "Latency"
  namespace           = "AWS/ApiGateway"
  period              = 300
  statistic           = "Average"
  threshold           = 10000 # 10秒
  alarm_description   = "API Gatewayのレイテンシーが閾値を超えました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    ApiName = aws_api_gateway_rest_api.main.name
    Stage   = aws_api_gateway_stage.main.stage_name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-api-gateway-latency"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ========================================
# CloudWatch Alarms - DynamoDB
# ========================================

# DynamoDB Users Table - Read Throttle Events
resource "aws_cloudwatch_metric_alarm" "dynamodb_users_read_throttle" {
  alarm_name          = "${var.project_name}-${var.environment}-dynamodb-users-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 5
  alarm_description   = "DynamoDB Users テーブルの読み取りスロットリングが発生しました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.users.name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-dynamodb-users-read-throttle"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB Meals Table - Read Throttle Events
resource "aws_cloudwatch_metric_alarm" "dynamodb_meals_read_throttle" {
  alarm_name          = "${var.project_name}-${var.environment}-dynamodb-meals-read-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "ReadThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB Meals テーブルの読み取りスロットリングが発生しました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.meals.name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-dynamodb-meals-read-throttle"
    Environment = var.environment
    Project     = var.project_name
  }
}

# DynamoDB Meals Table - Write Throttle Events
resource "aws_cloudwatch_metric_alarm" "dynamodb_meals_write_throttle" {
  alarm_name          = "${var.project_name}-${var.environment}-dynamodb-meals-write-throttle"
  comparison_operator = "GreaterThanThreshold"
  evaluation_periods  = 1
  metric_name         = "WriteThrottleEvents"
  namespace           = "AWS/DynamoDB"
  period              = 300
  statistic           = "Sum"
  threshold           = 10
  alarm_description   = "DynamoDB Meals テーブルの書き込みスロットリングが発生しました"
  alarm_actions       = [aws_sns_topic.alerts.arn]
  treat_missing_data  = "notBreaching"

  dimensions = {
    TableName = aws_dynamodb_table.meals.name
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-dynamodb-meals-write-throttle"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ========================================
# Outputs
# ========================================

output "sns_topic_arn" {
  description = "SNSトピックのARN"
  value       = aws_sns_topic.alerts.arn
}

output "sns_topic_name" {
  description = "SNSトピック名"
  value       = aws_sns_topic.alerts.name
}
