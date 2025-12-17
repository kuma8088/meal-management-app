# Cognito User Pool
resource "aws_cognito_user_pool" "main" {
  name = "${var.project_name}-user-pool-${var.environment}"

  # ユーザー名の設定
  username_attributes      = ["email"]
  auto_verified_attributes = ["email"]

  # パスワードポリシー
  password_policy {
    minimum_length                   = 8
    require_lowercase                = true
    require_uppercase                = true
    require_numbers                  = true
    require_symbols                  = true
    temporary_password_validity_days = 7
  }

  # アカウント復旧設定
  account_recovery_setting {
    recovery_mechanism {
      name     = "verified_email"
      priority = 1
    }
  }

  # ユーザー属性スキーマ
  schema {
    name                = "email"
    attribute_data_type = "String"
    required            = true
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  schema {
    name                = "name"
    attribute_data_type = "String"
    required            = false
    mutable             = true

    string_attribute_constraints {
      min_length = 1
      max_length = 256
    }
  }

  # カスタム属性: LINE User ID
  schema {
    name                     = "line_user_id"
    attribute_data_type      = "String"
    required                 = false
    mutable                  = true
    developer_only_attribute = false

    string_attribute_constraints {
      min_length = 33 # U + 32 hex chars
      max_length = 33
    }
  }

  # MFA設定（オプション）
  mfa_configuration = "OPTIONAL"

  software_token_mfa_configuration {
    enabled = true
  }

  # Lambda Triggers（LIFF カスタム認証フロー用）
  lambda_config {
    define_auth_challenge          = aws_lambda_function.define_auth_challenge.arn
    create_auth_challenge          = aws_lambda_function.create_auth_challenge.arn
    verify_auth_challenge_response = aws_lambda_function.verify_auth_challenge.arn
    post_confirmation              = aws_lambda_function.post_confirmation.arn
  }

  # ユーザープール削除保護
  deletion_protection = var.environment == "prod" ? "ACTIVE" : "INACTIVE"

  tags = {
    Name = "${var.project_name}-user-pool-${var.environment}"
  }
}

# Cognito User Pool Client
resource "aws_cognito_user_pool_client" "web_client" {
  name         = "${var.project_name}-web-client-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id

  # 認証フロー設定
  explicit_auth_flows = [
    "ALLOW_USER_PASSWORD_AUTH",
    "ALLOW_REFRESH_TOKEN_AUTH",
    "ALLOW_USER_SRP_AUTH",
    "ALLOW_CUSTOM_AUTH"
  ]

  # トークンの有効期限
  refresh_token_validity = 30
  access_token_validity  = 60
  id_token_validity      = 60

  token_validity_units {
    refresh_token = "days"
    access_token  = "minutes"
    id_token      = "minutes"
  }

  # OAuth設定
  allowed_oauth_flows_user_pool_client = true
  allowed_oauth_flows                  = ["code", "implicit"]
  allowed_oauth_scopes                 = ["email", "openid", "profile"]

  callback_urls = [
    "http://localhost:3000/callback",
    "http://localhost:5173/callback",
    "https://${var.project_name}-${var.environment}.example.com/callback",
    "https://d2b7c2gzuy0hmt.cloudfront.net/callback"
  ]

  logout_urls = [
    "http://localhost:3000",
    "http://localhost:5173",
    "https://${var.project_name}-${var.environment}.example.com",
    "https://d2b7c2gzuy0hmt.cloudfront.net"
  ]

  # LINE プロバイダーが設定されている場合は追加
  supported_identity_providers = var.line_login_channel_id != "" ? ["COGNITO", "LINE"] : ["COGNITO"]

  depends_on = [aws_cognito_identity_provider.line]

  # セキュリティ設定
  prevent_user_existence_errors = "ENABLED"

  # 読み取り・書き込み属性
  read_attributes = [
    "email",
    "email_verified",
    "name"
  ]

  write_attributes = [
    "email",
    "name"
  ]
}

# Cognito User Pool Domain
resource "aws_cognito_user_pool_domain" "main" {
  domain       = "${var.project_name}-${var.environment}"
  user_pool_id = aws_cognito_user_pool.main.id
}

# LINE Login OIDC Identity Provider
resource "aws_cognito_identity_provider" "line" {
  count         = var.line_login_channel_id != "" ? 1 : 0
  user_pool_id  = aws_cognito_user_pool.main.id
  provider_name = "LINE"
  provider_type = "OIDC"

  provider_details = {
    client_id                 = var.line_login_channel_id
    client_secret             = var.line_login_channel_secret
    attributes_request_method = "GET"
    oidc_issuer               = "https://access.line.me"
    authorize_scopes          = "openid profile"
    authorize_url             = "https://access.line.me/oauth2/v2.1/authorize"
    token_url                 = "https://api.line.me/oauth2/v2.1/token"
    attributes_url            = "https://api.line.me/oauth2/v2.1/userinfo"
    jwks_uri                  = "https://api.line.me/oauth2/v2.1/certs"
  }

  attribute_mapping = {
    username = "sub"
    email    = "email"
    name     = "name"
    picture  = "picture"
  }

  lifecycle {
    ignore_changes = [
      provider_details["authorize_scopes"]
    ]
  }
}

