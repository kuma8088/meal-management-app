# EventBridge Rule for Weekly Report
# 毎週日曜日 20:00 JST (UTC 11:00) に実行
resource "aws_cloudwatch_event_rule" "weekly_report_schedule" {
  name                = "${var.project_name}-${var.environment}-weekly-report-schedule"
  description         = "Weekly report generation schedule (Every Sunday at 20:00 JST)"
  schedule_expression = "cron(0 11 ? * SUN *)"
  state               = "ENABLED"

  tags = {
    Name        = "${var.project_name}-${var.environment}-weekly-report-schedule"
    Environment = var.environment
    Project     = var.project_name
  }
}

# EventBridge Target: Lambda Function
resource "aws_cloudwatch_event_target" "weekly_report_lambda" {
  rule      = aws_cloudwatch_event_rule.weekly_report_schedule.name
  target_id = "WeeklyReportLambda"
  arn       = aws_lambda_function.weekly_report.arn
  role_arn  = aws_iam_role.eventbridge_invoke_lambda_role.arn

}

# IAM Role for EventBridge to invoke Lambda
resource "aws_iam_role" "eventbridge_invoke_lambda_role" {
  name = "${var.project_name}-${var.environment}-eventbridge-invoke-lambda"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "events.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-eventbridge-invoke-lambda"
    Environment = var.environment
    Project     = var.project_name
  }
}

# IAM Policy for EventBridge to invoke Lambda
resource "aws_iam_role_policy" "eventbridge_invoke_lambda_policy" {
  name = "${var.project_name}-${var.environment}-eventbridge-invoke-lambda-policy"
  role = aws_iam_role.eventbridge_invoke_lambda_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = [
          "lambda:InvokeFunction"
        ]
        Effect = "Allow"
        Resource = [
          aws_lambda_function.weekly_report.arn,
          "${aws_lambda_function.weekly_report.arn}:*"
        ]
      }
    ]
  })
}

# Outputs
output "eventbridge_rule_arn" {
  description = "EventBridge Rule ARN for weekly report"
  value       = aws_cloudwatch_event_rule.weekly_report_schedule.arn
}

output "eventbridge_rule_name" {
  description = "EventBridge Rule name for weekly report"
  value       = aws_cloudwatch_event_rule.weekly_report_schedule.name
}
