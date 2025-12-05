# API Gateway REST API
resource "aws_api_gateway_rest_api" "main" {
  name        = "${var.project_name}-${var.environment}"
  description = "Meal Management App REST API"

  endpoint_configuration {
    types = ["REGIONAL"]
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-api"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CORS設定用のGateway Response
resource "aws_api_gateway_gateway_response" "cors_response" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_4XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
  }
}

resource "aws_api_gateway_gateway_response" "cors_response_5xx" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  response_type = "DEFAULT_5XX"

  response_parameters = {
    "gatewayresponse.header.Access-Control-Allow-Origin"  = "'*'"
    "gatewayresponse.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "gatewayresponse.header.Access-Control-Allow-Methods" = "'GET,POST,PUT,DELETE,OPTIONS'"
  }
}

# /line リソース
resource "aws_api_gateway_resource" "line" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "line"
}

# /line/webhook リソース
resource "aws_api_gateway_resource" "line_webhook" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.line.id
  path_part   = "webhook"
}

# POST /line/webhook メソッド
resource "aws_api_gateway_method" "line_webhook_post" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.line_webhook.id
  http_method   = "POST"
  authorization = "NONE" # LINE Webhook は署名検証で認証
}

# LINE Webhook Lambda統合
resource "aws_api_gateway_integration" "line_webhook_lambda" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.line_webhook.id
  http_method             = aws_api_gateway_method.line_webhook_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.line_handler.invoke_arn
}

# Lambda関数: LINE Handler
resource "aws_lambda_function" "line_handler" {
  filename         = "${path.module}/../dist/line_handler.zip"
  function_name    = "${var.project_name}-${var.environment}-line-handler"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "line_handler.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/line_handler.zip") ? filebase64sha256("${path.module}/../dist/line_handler.zip") : ""
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      LINE_CHANNEL_SECRET       = var.line_channel_secret
      LINE_CHANNEL_ACCESS_TOKEN = var.line_channel_access_token
      MEALS_TABLE_NAME          = aws_dynamodb_table.meals.name
      USERS_TABLE_NAME          = aws_dynamodb_table.users.name
      GOALS_TABLE_NAME          = aws_dynamodb_table.goals.name
      ADVICE_USAGE_TABLE_NAME   = aws_dynamodb_table.advice_usage.name
      FOODS_TABLE_NAME          = aws_dynamodb_table.foods.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-line-handler"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda permission for API Gateway
resource "aws_lambda_permission" "line_webhook_api_gateway" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.line_handler.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# Lambda関数: Meal Registration
resource "aws_lambda_function" "meal_registration" {
  filename         = "${path.module}/../dist/meal_registration.zip"
  function_name    = "${var.project_name}-${var.environment}-meal-registration"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "meal_registration.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/meal_registration.zip") ? filebase64sha256("${path.module}/../dist/meal_registration.zip") : ""
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      MEALS_TABLE_NAME = aws_dynamodb_table.meals.name
      USERS_TABLE_NAME = aws_dynamodb_table.users.name
      FOODS_TABLE_NAME = aws_dynamodb_table.foods.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-meal-registration"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Cognitoオーソライザー（ブラウザAPI用）
resource "aws_api_gateway_authorizer" "cognito" {
  name            = "${var.project_name}-${var.environment}-cognito-authorizer"
  rest_api_id     = aws_api_gateway_rest_api.main.id
  type            = "COGNITO_USER_POOLS"
  provider_arns   = [aws_cognito_user_pool.main.arn]
  identity_source = "method.request.header.Authorization"
}

# リクエストバリデーター
resource "aws_api_gateway_request_validator" "body_and_params" {
  name                        = "${var.project_name}-${var.environment}-body-params-validator"
  rest_api_id                 = aws_api_gateway_rest_api.main.id
  validate_request_body       = true
  validate_request_parameters = true
}

# API Gatewayデプロイメント
resource "aws_api_gateway_deployment" "main" {
  rest_api_id = aws_api_gateway_rest_api.main.id

  triggers = {
    redeployment = sha1(jsonencode([
      aws_api_gateway_resource.line_webhook.id,
      aws_api_gateway_method.line_webhook_post.id,
      aws_api_gateway_integration.line_webhook_lambda.id,
      aws_api_gateway_resource.meals.id,
      aws_api_gateway_resource.meals_item.id,
      aws_api_gateway_resource.users.id,
      aws_api_gateway_resource.users_item.id,
      aws_api_gateway_resource.advice_daily.id,
      aws_api_gateway_authorizer.cognito.id,
    ]))
  }

  lifecycle {
    create_before_destroy = true
  }

  depends_on = [
    aws_api_gateway_integration.line_webhook_lambda,
    aws_api_gateway_integration.meals_post,
    aws_api_gateway_integration.meals_get,
    aws_api_gateway_integration.meals_item_get,
    aws_api_gateway_integration.meals_item_put,
    aws_api_gateway_integration.meals_item_delete,
    aws_api_gateway_integration.users_post,
    aws_api_gateway_integration.users_item_get,
    aws_api_gateway_integration.users_item_put,
    aws_api_gateway_integration.advice_daily_post,
  ]
}

# API Gatewayステージ
resource "aws_api_gateway_stage" "main" {
  deployment_id = aws_api_gateway_deployment.main.id
  rest_api_id   = aws_api_gateway_rest_api.main.id
  stage_name    = var.environment

  tags = {
    Name        = "${var.project_name}-${var.environment}-stage"
    Environment = var.environment
    Project     = var.project_name
  }
}

# CloudWatch Logs for API Gateway
# Note: Requires CloudWatch Logs role ARN to be set in account settings
# Uncomment after setting up account-level CloudWatch Logs role
# resource "aws_api_gateway_method_settings" "all" {
#   rest_api_id = aws_api_gateway_rest_api.main.id
#   stage_name  = aws_api_gateway_stage.main.stage_name
#   method_path = "*/*"
#
#   settings {
#     logging_level      = "INFO"
#     data_trace_enabled = true
#     metrics_enabled    = true
#   }
# }

# ========================================
# ブラウザAPI用エンドポイント
# ========================================

# /meals リソース
resource "aws_api_gateway_resource" "meals" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "meals"
}

# POST /meals - 食事記録作成
resource "aws_api_gateway_method" "meals_post" {
  rest_api_id          = aws_api_gateway_rest_api.main.id
  resource_id          = aws_api_gateway_resource.meals.id
  http_method          = "POST"
  authorization        = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.cognito.id
  request_validator_id = aws_api_gateway_request_validator.body_and_params.id
}

resource "aws_api_gateway_integration" "meals_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.meals.id
  http_method             = aws_api_gateway_method.meals_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.meal_registration.invoke_arn
}

# GET /meals - 食事記録一覧取得
resource "aws_api_gateway_method" "meals_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.meals.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.querystring.start_date" = false
    "method.request.querystring.end_date"   = false
    "method.request.querystring.limit"      = false
  }
}

resource "aws_api_gateway_integration" "meals_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.meals.id
  http_method             = aws_api_gateway_method.meals_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.meal_registration.invoke_arn
}

# /meals/{meal_id} リソース
resource "aws_api_gateway_resource" "meals_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.meals.id
  path_part   = "{meal_id}"
}

# GET /meals/{meal_id} - 特定の食事記録取得
resource "aws_api_gateway_method" "meals_item_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.meals_item.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.meal_id" = true
  }
}

resource "aws_api_gateway_integration" "meals_item_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.meals_item.id
  http_method             = aws_api_gateway_method.meals_item_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.meal_registration.invoke_arn
}

# PUT /meals/{meal_id} - 食事記録更新
resource "aws_api_gateway_method" "meals_item_put" {
  rest_api_id          = aws_api_gateway_rest_api.main.id
  resource_id          = aws_api_gateway_resource.meals_item.id
  http_method          = "PUT"
  authorization        = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.cognito.id
  request_validator_id = aws_api_gateway_request_validator.body_and_params.id

  request_parameters = {
    "method.request.path.meal_id" = true
  }
}

resource "aws_api_gateway_integration" "meals_item_put" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.meals_item.id
  http_method             = aws_api_gateway_method.meals_item_put.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.meal_registration.invoke_arn
}

# DELETE /meals/{meal_id} - 食事記録削除
resource "aws_api_gateway_method" "meals_item_delete" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.meals_item.id
  http_method   = "DELETE"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.meal_id" = true
  }
}

resource "aws_api_gateway_integration" "meals_item_delete" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.meals_item.id
  http_method             = aws_api_gateway_method.meals_item_delete.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.meal_registration.invoke_arn
}

# Lambda permission for meals endpoints
resource "aws_lambda_permission" "meals_api_gateway" {
  statement_id  = "AllowAPIGatewayInvokeMeals"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.meal_registration.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /users リソース
resource "aws_api_gateway_resource" "users" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "users"
}

# POST /users - ユーザープロフィール作成
resource "aws_api_gateway_method" "users_post" {
  rest_api_id          = aws_api_gateway_rest_api.main.id
  resource_id          = aws_api_gateway_resource.users.id
  http_method          = "POST"
  authorization        = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.cognito.id
  request_validator_id = aws_api_gateway_request_validator.body_and_params.id
}

resource "aws_api_gateway_integration" "users_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.users.id
  http_method             = aws_api_gateway_method.users_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.goal_management.invoke_arn
}

# /users/{user_id} リソース
resource "aws_api_gateway_resource" "users_item" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.users.id
  path_part   = "{user_id}"
}

# GET /users/{user_id} - ユーザープロフィール取得
resource "aws_api_gateway_method" "users_item_get" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.users_item.id
  http_method   = "GET"
  authorization = "COGNITO_USER_POOLS"
  authorizer_id = aws_api_gateway_authorizer.cognito.id

  request_parameters = {
    "method.request.path.user_id" = true
  }
}

resource "aws_api_gateway_integration" "users_item_get" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.users_item.id
  http_method             = aws_api_gateway_method.users_item_get.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.goal_management.invoke_arn
}

# PUT /users/{user_id} - ユーザープロフィール更新
resource "aws_api_gateway_method" "users_item_put" {
  rest_api_id          = aws_api_gateway_rest_api.main.id
  resource_id          = aws_api_gateway_resource.users_item.id
  http_method          = "PUT"
  authorization        = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.cognito.id
  request_validator_id = aws_api_gateway_request_validator.body_and_params.id

  request_parameters = {
    "method.request.path.user_id" = true
  }
}

resource "aws_api_gateway_integration" "users_item_put" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.users_item.id
  http_method             = aws_api_gateway_method.users_item_put.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.goal_management.invoke_arn
}

# Lambda関数: Goal Management (ユーザープロフィール管理も含む)
resource "aws_lambda_function" "goal_management" {
  filename         = "${path.module}/../dist/goal_management.zip"
  function_name    = "${var.project_name}-${var.environment}-goal-management"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "goal_management.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/goal_management.zip") ? filebase64sha256("${path.module}/../dist/goal_management.zip") : ""
  runtime          = "python3.11"
  timeout          = 30

  environment {
    variables = {
      USERS_TABLE_NAME = aws_dynamodb_table.users.name
      GOALS_TABLE_NAME = aws_dynamodb_table.goals.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-goal-management"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda permission for users endpoints
resource "aws_lambda_permission" "users_api_gateway" {
  statement_id  = "AllowAPIGatewayInvokeUsers"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.goal_management.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# /advice リソース
resource "aws_api_gateway_resource" "advice" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_rest_api.main.root_resource_id
  path_part   = "advice"
}

# /advice/daily リソース
resource "aws_api_gateway_resource" "advice_daily" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  parent_id   = aws_api_gateway_resource.advice.id
  path_part   = "daily"
}

# POST /advice/daily - 日次総評取得
resource "aws_api_gateway_method" "advice_daily_post" {
  rest_api_id          = aws_api_gateway_rest_api.main.id
  resource_id          = aws_api_gateway_resource.advice_daily.id
  http_method          = "POST"
  authorization        = "COGNITO_USER_POOLS"
  authorizer_id        = aws_api_gateway_authorizer.cognito.id
  request_validator_id = aws_api_gateway_request_validator.body_and_params.id
}

resource "aws_api_gateway_integration" "advice_daily_post" {
  rest_api_id             = aws_api_gateway_rest_api.main.id
  resource_id             = aws_api_gateway_resource.advice_daily.id
  http_method             = aws_api_gateway_method.advice_daily_post.http_method
  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.daily_summary.invoke_arn
}

# Lambda関数: Daily Summary
resource "aws_lambda_function" "daily_summary" {
  filename         = "${path.module}/../dist/daily_summary.zip"
  function_name    = "${var.project_name}-${var.environment}-daily-summary"
  role             = aws_iam_role.lambda_execution_role.arn
  handler          = "daily_summary.lambda_handler"
  source_code_hash = fileexists("${path.module}/../dist/daily_summary.zip") ? filebase64sha256("${path.module}/../dist/daily_summary.zip") : ""
  runtime          = "python3.11"
  timeout          = 60

  environment {
    variables = {
      MEALS_TABLE_NAME        = aws_dynamodb_table.meals.name
      USERS_TABLE_NAME        = aws_dynamodb_table.users.name
      GOALS_TABLE_NAME        = aws_dynamodb_table.goals.name
      ADVICE_USAGE_TABLE_NAME = aws_dynamodb_table.advice_usage.name
    }
  }

  tags = {
    Name        = "${var.project_name}-${var.environment}-daily-summary"
    Environment = var.environment
    Project     = var.project_name
  }
}

# Lambda permission for advice endpoints
resource "aws_lambda_permission" "advice_api_gateway" {
  statement_id  = "AllowAPIGatewayInvokeAdvice"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.daily_summary.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn    = "${aws_api_gateway_rest_api.main.execution_arn}/*/*"
}

# ========================================
# CORS設定（OPTIONSメソッド）
# ========================================

# OPTIONS /meals
resource "aws_api_gateway_method" "meals_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.meals.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "meals_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals.id
  http_method = aws_api_gateway_method.meals_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "meals_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals.id
  http_method = aws_api_gateway_method.meals_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "meals_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals.id
  http_method = aws_api_gateway_method.meals_options.http_method
  status_code = aws_api_gateway_method_response.meals_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS /meals/{meal_id}
resource "aws_api_gateway_method" "meals_item_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.meals_item.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "meals_item_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals_item.id
  http_method = aws_api_gateway_method.meals_item_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "meals_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals_item.id
  http_method = aws_api_gateway_method.meals_item_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "meals_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.meals_item.id
  http_method = aws_api_gateway_method.meals_item_options.http_method
  status_code = aws_api_gateway_method_response.meals_item_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,PUT,DELETE,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS /users
resource "aws_api_gateway_method" "users_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.users.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "users_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.users_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "users_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.users_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "users_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users.id
  http_method = aws_api_gateway_method.users_options.http_method
  status_code = aws_api_gateway_method_response.users_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS /users/{user_id}
resource "aws_api_gateway_method" "users_item_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.users_item.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "users_item_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users_item.id
  http_method = aws_api_gateway_method.users_item_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "users_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users_item.id
  http_method = aws_api_gateway_method.users_item_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "users_item_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.users_item.id
  http_method = aws_api_gateway_method.users_item_options.http_method
  status_code = aws_api_gateway_method_response.users_item_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'GET,PUT,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# OPTIONS /advice/daily
resource "aws_api_gateway_method" "advice_daily_options" {
  rest_api_id   = aws_api_gateway_rest_api.main.id
  resource_id   = aws_api_gateway_resource.advice_daily.id
  http_method   = "OPTIONS"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "advice_daily_options" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.advice_daily.id
  http_method = aws_api_gateway_method.advice_daily_options.http_method
  type        = "MOCK"

  request_templates = {
    "application/json" = "{\"statusCode\": 200}"
  }
}

resource "aws_api_gateway_method_response" "advice_daily_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.advice_daily.id
  http_method = aws_api_gateway_method.advice_daily_options.http_method
  status_code = "200"

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = true
    "method.response.header.Access-Control-Allow-Methods" = true
    "method.response.header.Access-Control-Allow-Origin"  = true
  }
}

resource "aws_api_gateway_integration_response" "advice_daily_options_200" {
  rest_api_id = aws_api_gateway_rest_api.main.id
  resource_id = aws_api_gateway_resource.advice_daily.id
  http_method = aws_api_gateway_method.advice_daily_options.http_method
  status_code = aws_api_gateway_method_response.advice_daily_options_200.status_code

  response_parameters = {
    "method.response.header.Access-Control-Allow-Headers" = "'Content-Type,Authorization'"
    "method.response.header.Access-Control-Allow-Methods" = "'POST,OPTIONS'"
    "method.response.header.Access-Control-Allow-Origin"  = "'*'"
  }
}

# Outputs
output "api_gateway_url" {
  description = "API Gateway URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}"
}

output "line_webhook_url" {
  description = "LINE Webhook URL"
  value       = "${aws_api_gateway_stage.main.invoke_url}/line/webhook"
}
