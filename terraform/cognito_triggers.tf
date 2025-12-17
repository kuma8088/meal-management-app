# ========================================
# Cognito Lambda Triggers for LIFF Custom Auth
# ========================================

# Lambda実行ロール（Cognito Triggers用）
resource "aws_iam_role" "cognito_triggers_role" {
  name = "${var.project_name}-${var.environment}-cognito-triggers-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "lambda.amazonaws.com"
        }
      }
    ]
  })

  tags = {
    Name        = "${var.project_name}-${var.environment}-cognito-triggers-role"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Logs ポリシー
resource "aws_iam_role_policy_attachment" "cognito_triggers_logs" {
  role       = aws_iam_role.cognito_triggers_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# DynamoDB アクセスポリシー（Nonce と Users テーブル）
resource "aws_iam_role_policy" "cognito_triggers_dynamodb" {
  name = "${var.project_name}-${var.environment}-cognito-triggers-dynamodb"
  role = aws_iam_role.cognito_triggers_role.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query"
        ]
        Resource = [
          aws_dynamodb_table.nonce.arn,
          aws_dynamodb_table.users.arn,
          "${aws_dynamodb_table.users.arn}/index/*"
        ]
      }
    ]
  })
}

# ========================================
# Lambda Functions
# ========================================

# Define Auth Challenge
resource "aws_lambda_function" "define_auth_challenge" {
  filename         = "${path.module}/../dist/define_auth_challenge.zip"
  function_name    = "${var.project_name}-${var.environment}-define-auth-challenge"
  role             = aws_iam_role.cognito_triggers_role.arn
  handler          = "define_auth_challenge.__init__.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/define_auth_challenge.zip") ? filebase64sha256("${path.module}/../dist/define_auth_challenge.zip") : ""
  runtime          = "python3.11"
  timeout          = 10

  tags = {
    Name        = "${var.project_name}-${var.environment}-define-auth-challenge"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Create Auth Challenge
resource "aws_lambda_function" "create_auth_challenge" {
  filename         = "${path.module}/../dist/create_auth_challenge.zip"
  function_name    = "${var.project_name}-${var.environment}-create-auth-challenge"
  role             = aws_iam_role.cognito_triggers_role.arn
  handler          = "create_auth_challenge.__init__.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/create_auth_challenge.zip") ? filebase64sha256("${path.module}/../dist/create_auth_challenge.zip") : ""
  runtime          = "python3.11"
  timeout          = 10

  environment {
    variables = {
      LINE_CHANNEL_ID  = var.line_login_channel_id
      NONCE_TABLE_NAME = aws_dynamodb_table.nonce.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-create-auth-challenge"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Verify Auth Challenge
resource "aws_lambda_function" "verify_auth_challenge" {
  filename         = "${path.module}/../dist/verify_auth_challenge.zip"
  function_name    = "${var.project_name}-${var.environment}-verify-auth-challenge"
  role             = aws_iam_role.cognito_triggers_role.arn
  handler          = "verify_auth_challenge.__init__.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/verify_auth_challenge.zip") ? filebase64sha256("${path.module}/../dist/verify_auth_challenge.zip") : ""
  runtime          = "python3.11"
  timeout          = 30
  memory_size      = 256

  environment {
    variables = {
      LINE_CHANNEL_ID  = var.line_login_channel_id
      NONCE_TABLE_NAME = aws_dynamodb_table.nonce.name
      USERS_TABLE_NAME = aws_dynamodb_table.users.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-verify-auth-challenge"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Post Confirmation
resource "aws_lambda_function" "post_confirmation" {
  filename         = "${path.module}/../dist/post_confirmation.zip"
  function_name    = "${var.project_name}-${var.environment}-post-confirmation"
  role             = aws_iam_role.cognito_triggers_role.arn
  handler          = "post_confirmation.__init__.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/post_confirmation.zip") ? filebase64sha256("${path.module}/../dist/post_confirmation.zip") : ""
  runtime          = "python3.11"
  timeout          = 10

  environment {
    variables = {
      USERS_TABLE_NAME = aws_dynamodb_table.users.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-post-confirmation"
    Environment = var.environment
    Project     = var.project_name
  }
}

# ========================================
# Lambda Permissions for Cognito
# ========================================

resource "aws_lambda_permission" "define_auth_challenge_cognito" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.define_auth_challenge.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

resource "aws_lambda_permission" "create_auth_challenge_cognito" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.create_auth_challenge.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

resource "aws_lambda_permission" "verify_auth_challenge_cognito" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.verify_auth_challenge.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}

resource "aws_lambda_permission" "post_confirmation_cognito" {
  statement_id  = "AllowCognitoInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.post_confirmation.function_name
  principal     = "cognito-idp.amazonaws.com"
  source_arn    = aws_cognito_user_pool.main.arn
}
