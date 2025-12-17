"""
LIFF Login API - LINE Access Token を使用して Cognito トークンを発行

フロー:
1. LIFF から LINE Access Token + line_user_id を受信
2. LINE API で Access Token を検証
3. line_user_id の一致を確認
4. Cognito ユーザーを検索/作成
5. AdminInitiateAuth で Cognito トークンを発行

注: openid スコープは申請が必要なため、Access Token 方式を使用
"""

import json
import logging
import os
import urllib.request
import urllib.error
import boto3
from botocore.exceptions import ClientError

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# AWS クライアント
cognito_client = boto3.client('cognito-idp')
dynamodb = boto3.resource('dynamodb')

# 環境変数
USER_POOL_ID = os.environ.get('USER_POOL_ID')
CLIENT_ID = os.environ.get('CLIENT_ID')
LINE_CHANNEL_ID = os.environ.get('LINE_CHANNEL_ID')
USERS_TABLE_NAME = os.environ.get('USERS_TABLE_NAME', 'meal-management-app-users-dev')


def lambda_handler(event: dict, context) -> dict:
    """
    LIFF Login API ハンドラー

    Request Body:
        {
            "line_access_token": "xxx...",
            "line_user_id": "U1234567890abcdef..."
        }

    Response:
        {
            "id_token": "eyJ...",
            "access_token": "eyJ...",
            "refresh_token": "eyJ...",
            "expires_in": 3600,
            "token_type": "Bearer"
        }
    """
    logger.info("LIFF Login API called")

    try:
        # リクエストボディをパース
        body = _parse_request_body(event)

        line_access_token = body.get('line_access_token')
        line_user_id = body.get('line_user_id')

        # 後方互換性: line_id_token が送られた場合はエラー
        if body.get('line_id_token') and not line_access_token:
            return _error_response(
                400,
                'DEPRECATED_TOKEN_TYPE',
                'line_id_token is deprecated. Please use line_access_token instead.'
            )

        if not line_access_token:
            return _error_response(400, 'MISSING_TOKEN', 'line_access_token is required')

        if not line_user_id:
            return _error_response(400, 'MISSING_USER_ID', 'line_user_id is required')

        # LINE API で Access Token を検証
        verified_user_id = _verify_line_access_token(line_access_token)
        if not verified_user_id:
            return _error_response(401, 'INVALID_TOKEN', 'LINE Access Token verification failed')

        # line_user_id の一致を確認
        if verified_user_id != line_user_id:
            logger.error(f"User ID mismatch: expected {verified_user_id}, got {line_user_id}")
            return _error_response(401, 'USER_ID_MISMATCH', 'LINE user ID does not match')

        # Cognito ユーザー名を生成（email 形式が必須）
        username = f"{line_user_id}@line.local"

        # Cognito トークンを発行
        tokens = _get_or_create_cognito_tokens(username, line_user_id)

        if not tokens:
            return _error_response(500, 'TOKEN_GENERATION_FAILED', 'Failed to generate Cognito tokens')

        logger.info(f"LIFF Login successful for user: {username}")

        return {
            'statusCode': 200,
            'headers': _cors_headers(),
            'body': json.dumps(tokens)
        }

    except ClientError as e:
        error_code = e.response['Error']['Code']
        error_message = e.response['Error']['Message']
        logger.error(f"Cognito error: {error_code} - {error_message}")
        return _error_response(500, 'COGNITO_ERROR', error_message)

    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        return _error_response(500, 'INTERNAL_ERROR', 'Internal server error')


def _parse_request_body(event: dict) -> dict:
    """リクエストボディをパース"""
    body = event.get('body', '{}')
    if isinstance(body, str):
        return json.loads(body) if body else {}
    return body or {}


def _verify_line_access_token(access_token: str) -> str | None:
    """
    LINE API で Access Token を検証し、user_id を返す

    API: GET https://api.line.me/oauth2/v2.1/verify?access_token=xxx

    Response:
        {
            "scope": "profile",
            "client_id": "1234567890",
            "expires_in": 2591659
        }

    その後、Profile API で user_id を取得:
    API: GET https://api.line.me/v2/profile
    Headers: Authorization: Bearer {access_token}

    Response:
        {
            "userId": "U1234567890abcdef...",
            "displayName": "User Name",
            "pictureUrl": "https://..."
        }
    """
    try:
        # Step 1: Access Token を検証
        verify_url = f"https://api.line.me/oauth2/v2.1/verify?access_token={access_token}"
        req = urllib.request.Request(verify_url)

        with urllib.request.urlopen(req, timeout=10) as response:
            verify_data = json.loads(response.read().decode('utf-8'))

        # Channel ID の検証（オプション: 設定されている場合のみ）
        if LINE_CHANNEL_ID:
            if verify_data.get('client_id') != LINE_CHANNEL_ID:
                logger.error(f"Channel ID mismatch: expected {LINE_CHANNEL_ID}, got {verify_data.get('client_id')}")
                return None

        # expires_in を確認
        if verify_data.get('expires_in', 0) <= 0:
            logger.error("Access token has expired")
            return None

        logger.info(f"Access token verified, expires_in: {verify_data.get('expires_in')}")

        # Step 2: Profile API で user_id を取得
        profile_url = "https://api.line.me/v2/profile"
        profile_req = urllib.request.Request(
            profile_url,
            headers={'Authorization': f'Bearer {access_token}'}
        )

        with urllib.request.urlopen(profile_req, timeout=10) as response:
            profile_data = json.loads(response.read().decode('utf-8'))

        user_id = profile_data.get('userId')
        if not user_id:
            logger.error("No userId in profile response")
            return None

        logger.info(f"LINE user verified: {user_id[:10]}...")
        return user_id

    except urllib.error.HTTPError as e:
        logger.error(f"LINE API error: {e.code} - {e.reason}")
        return None
    except Exception as e:
        logger.error(f"Failed to verify LINE access token: {e}")
        return None


def _get_or_create_cognito_tokens(username: str, line_user_id: str) -> dict | None:
    """
    Cognito ユーザーを検索/作成し、トークンを発行

    Custom Auth フローを使用:
    1. AdminInitiateAuth で CUSTOM_AUTH 開始
    2. CreateAuthChallenge が nonce を生成
    3. RespondToAuthChallenge で検証済み line_user_id を送信
    4. VerifyAuthChallengeResponse で検証（既に検証済みなのでパススルー）
    """
    try:
        # ユーザーの存在確認
        try:
            user_response = cognito_client.admin_get_user(
                UserPoolId=USER_POOL_ID,
                Username=username
            )
            logger.info(f"Existing user found: {username}")

            # 既存ユーザーでも DynamoDB にレコードがない場合は作成
            user_attrs = user_response.get('UserAttributes', [])
            cognito_sub = None
            for attr in user_attrs:
                if attr['Name'] == 'sub':
                    cognito_sub = attr['Value']
                    break

            if cognito_sub:
                _ensure_dynamodb_user(cognito_sub, line_user_id, username)

        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                # 新規ユーザー作成
                logger.info(f"Creating new user: {username}")
                if not _create_cognito_user(username, line_user_id):
                    return None
            else:
                raise

        # Custom Auth フローでトークンを取得
        return _execute_custom_auth_flow(username, line_user_id)

    except Exception as e:
        logger.error(f"Failed to get/create Cognito tokens: {e}")
        return None


def _ensure_dynamodb_user(cognito_sub: str, line_user_id: str, email: str) -> bool:
    """
    DynamoDB にユーザーレコードが存在することを確認、なければ作成
    既存 LINE ユーザーがいる場合は cognito_user_id を更新

    Args:
        cognito_sub: Cognito の sub (UUID)
        line_user_id: LINE ユーザー ID
        email: メールアドレス（ダミー含む）

    Returns:
        存在確認/作成成功時 True
    """
    try:
        table = dynamodb.Table(USERS_TABLE_NAME)

        # 1. まず Cognito sub で検索
        response = table.get_item(Key={'user_id': cognito_sub})
        if 'Item' in response:
            logger.info(f"DynamoDB user already exists with cognito_sub: {cognito_sub}")
            return True

        # 2. LINE user ID で既存ユーザーを検索（GSI: LineUserIdIndex）
        existing_user = _find_user_by_line_id(line_user_id)
        if existing_user:
            # 既存ユーザーの cognito_user_id を更新
            old_user_id = existing_user.get('user_id')
            logger.info(f"Found existing LINE user: {old_user_id}, updating cognito_user_id to {cognito_sub}")
            return _update_user_cognito_id(old_user_id, cognito_sub)

        # 3. 存在しない場合は新規作成
        return _create_dynamodb_user(cognito_sub, line_user_id, email)

    except ClientError as e:
        logger.error(f"Failed to ensure DynamoDB user: {e.response['Error']['Message']}")
        return False


def _find_user_by_line_id(line_user_id: str) -> dict | None:
    """
    LINE user ID で DynamoDB ユーザーを検索（GSI 使用）

    Args:
        line_user_id: LINE ユーザー ID

    Returns:
        ユーザーレコード（存在する場合）または None
    """
    try:
        table = dynamodb.Table(USERS_TABLE_NAME)
        response = table.query(
            IndexName='LineUserIdIndex',
            KeyConditionExpression='line_user_id = :lid',
            ExpressionAttributeValues={':lid': line_user_id}
        )
        items = response.get('Items', [])
        if items:
            logger.info(f"Found existing user by LINE ID: {items[0].get('user_id')}")
            return items[0]
        return None
    except ClientError as e:
        logger.error(f"Failed to find user by LINE ID: {e.response['Error']['Message']}")
        return None


def _update_user_cognito_id(user_id: str, cognito_sub: str) -> bool:
    """
    既存ユーザーの cognito_user_id を更新

    Args:
        user_id: 既存の user_id
        cognito_sub: 新しい Cognito sub

    Returns:
        更新成功時 True
    """
    try:
        from datetime import datetime

        table = dynamodb.Table(USERS_TABLE_NAME)
        now = datetime.utcnow().isoformat() + 'Z'

        table.update_item(
            Key={'user_id': user_id},
            UpdateExpression='SET cognito_user_id = :cid, updated_at = :now',
            ExpressionAttributeValues={
                ':cid': cognito_sub,
                ':now': now
            }
        )
        logger.info(f"Updated cognito_user_id for user {user_id} to {cognito_sub}")
        return True

    except ClientError as e:
        logger.error(f"Failed to update cognito_user_id: {e.response['Error']['Message']}")
        return False


def _create_cognito_user(username: str, line_user_id: str) -> bool:
    """
    Cognito に新規ユーザーを作成し、DynamoDB にもレコードを作成

    Args:
        username: メールアドレス形式のユーザー名 (例: {line_user_id}@line.local)
        line_user_id: LINE ユーザー ID

    Returns:
        作成成功時 True
    """
    try:
        import secrets
        from datetime import datetime

        # ランダムな仮パスワード（Custom Auth では使用しない）
        temp_password = secrets.token_urlsafe(32)

        # Cognito にユーザーを作成
        create_response = cognito_client.admin_create_user(
            UserPoolId=USER_POOL_ID,
            Username=username,  # email 形式のユーザー名
            UserAttributes=[
                {
                    'Name': 'email',
                    'Value': username  # username がダミーメールアドレス
                },
                {
                    'Name': 'email_verified',
                    'Value': 'true'  # LINE 経由なので検証済みとする
                },
                {
                    'Name': 'custom:line_user_id',
                    'Value': line_user_id
                }
            ],
            TemporaryPassword=temp_password,
            MessageAction='SUPPRESS'  # ウェルカムメールを送信しない
        )

        # パスワードを確定（FORCE_CHANGE_PASSWORD 状態を解除）
        cognito_client.admin_set_user_password(
            UserPoolId=USER_POOL_ID,
            Username=username,
            Password=temp_password,
            Permanent=True
        )

        # Cognito の sub（user_id）を取得
        user_attrs = create_response.get('User', {}).get('Attributes', [])
        cognito_sub = None
        for attr in user_attrs:
            if attr['Name'] == 'sub':
                cognito_sub = attr['Value']
                break

        if cognito_sub:
            # DynamoDB にユーザーレコードを作成
            _create_dynamodb_user(cognito_sub, line_user_id, username)

        logger.info(f"Created new Cognito user: {username}")
        return True

    except ClientError as e:
        logger.error(f"Failed to create user: {e.response['Error']['Message']}")
        return False


def _create_dynamodb_user(user_id: str, line_user_id: str, email: str) -> bool:
    """
    DynamoDB にユーザーレコードを作成

    Args:
        user_id: Cognito の sub (UUID)
        line_user_id: LINE ユーザー ID
        email: メールアドレス（ダミー含む）

    Returns:
        作成成功時 True
    """
    try:
        from datetime import datetime

        table = dynamodb.Table(USERS_TABLE_NAME)
        now = datetime.utcnow().isoformat() + 'Z'

        table.put_item(
            Item={
                'user_id': user_id,
                'line_user_id': line_user_id,
                'email': email,
                'created_at': now,
                'updated_at': now,
                # プロフィール情報は後でユーザーが設定
                # height, weight, age, gender, activity_level などは未設定
            },
            ConditionExpression='attribute_not_exists(user_id)'
        )

        logger.info(f"Created DynamoDB user record: {user_id}")
        return True

    except ClientError as e:
        if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
            logger.info(f"DynamoDB user already exists: {user_id}")
            return True  # 既存ユーザーは問題なし
        logger.error(f"Failed to create DynamoDB user: {e.response['Error']['Message']}")
        return False


def _execute_custom_auth_flow(username: str, line_user_id: str) -> dict | None:
    """
    Cognito Custom Auth フローを実行してトークンを取得

    Access Token 方式では既に LINE API で検証済みなので、
    VerifyAuthChallengeResponse は line_user_id の一致のみ確認
    """
    try:
        # Step 1: AdminInitiateAuth でカスタム認証を開始
        init_response = cognito_client.admin_initiate_auth(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            AuthFlow='CUSTOM_AUTH',
            AuthParameters={
                'USERNAME': username
            },
            ClientMetadata={
                'line_user_id': line_user_id,
                'auth_method': 'access_token'  # Access Token 方式を示すフラグ
            }
        )

        # Step 2: チャレンジレスポンスを確認
        if 'AuthenticationResult' in init_response:
            return _extract_tokens(init_response['AuthenticationResult'])

        if 'ChallengeName' not in init_response:
            logger.error("Unexpected response: no challenge and no tokens")
            return None

        challenge_name = init_response['ChallengeName']
        session = init_response['Session']
        challenge_params = init_response.get('ChallengeParameters', {})

        if challenge_name != 'CUSTOM_CHALLENGE':
            logger.error(f"Unexpected challenge type: {challenge_name}")
            return None

        # nonce を取得
        nonce = challenge_params.get('nonce', '')

        # Step 3: AdminRespondToAuthChallenge
        # Access Token 方式: 既に検証済みの line_user_id を送信
        # Answer format: "ACCESS_TOKEN_VERIFIED:{line_user_id}:{nonce}"
        answer = f"ACCESS_TOKEN_VERIFIED:{line_user_id}:{nonce}"

        respond_response = cognito_client.admin_respond_to_auth_challenge(
            UserPoolId=USER_POOL_ID,
            ClientId=CLIENT_ID,
            ChallengeName='CUSTOM_CHALLENGE',
            Session=session,
            ChallengeResponses={
                'USERNAME': username,
                'ANSWER': answer
            },
            ClientMetadata={
                'line_user_id': line_user_id,
                'auth_method': 'access_token'
            }
        )

        # Step 4: 認証結果を確認
        if 'AuthenticationResult' in respond_response:
            logger.info("Custom auth completed successfully")
            return _extract_tokens(respond_response['AuthenticationResult'])

        logger.error("Authentication failed: no tokens returned")
        return None

    except ClientError as e:
        logger.error(f"Custom auth flow error: {e.response['Error']['Message']}")
        return None


def _extract_tokens(auth_result: dict) -> dict:
    """認証結果からトークン情報を抽出"""
    return {
        'id_token': auth_result.get('IdToken'),
        'access_token': auth_result.get('AccessToken'),
        'refresh_token': auth_result.get('RefreshToken'),
        'expires_in': auth_result.get('ExpiresIn', 3600),
        'token_type': auth_result.get('TokenType', 'Bearer')
    }


def _cors_headers() -> dict:
    """CORS ヘッダーを返却"""
    return {
        'Content-Type': 'application/json',
        'Access-Control-Allow-Origin': '*',
        'Access-Control-Allow-Headers': 'Content-Type,Authorization',
        'Access-Control-Allow-Methods': 'POST,OPTIONS'
    }


def _error_response(status_code: int, error_code: str, message: str) -> dict:
    """エラーレスポンスを生成"""
    return {
        'statusCode': status_code,
        'headers': _cors_headers(),
        'body': json.dumps({
            'error': {
                'code': error_code,
                'message': message
            }
        })
    }
