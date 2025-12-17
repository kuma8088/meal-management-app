#!/usr/bin/env python3
"""
LINE ユーザーを Cognito に移行するスクリプト

Feature: Cognito ID Federation, Phase 4.1

既存の LINE ユーザー（line_user_id のみ）を Cognito に移行し、
cognito_user_id を DynamoDB に保存する。

使用方法:
    # ドライラン（実際には変更しない）
    python scripts/migrate_line_users.py --dry-run

    # 本番実行
    python scripts/migrate_line_users.py

    # 特定の環境を指定
    python scripts/migrate_line_users.py --environment prod

環境変数:
    AWS_REGION: AWSリージョン（デフォルト: ap-northeast-1）
"""

import argparse
import json
import logging
import secrets
import sys
from dataclasses import dataclass
from typing import Iterator

import boto3
from botocore.exceptions import ClientError

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


@dataclass
class MigrationResult:
    """移行結果"""
    total_scanned: int = 0
    already_migrated: int = 0
    migrated: int = 0
    failed: int = 0
    skipped: int = 0


class LineUserMigrator:
    """LINE ユーザーを Cognito に移行するクラス"""

    def __init__(
        self,
        environment: str = 'dev',
        region: str = 'ap-northeast-1',
        dry_run: bool = False
    ):
        self.environment = environment
        self.region = region
        self.dry_run = dry_run
        self.project_name = 'meal-management-app'

        # AWS クライアント
        self.dynamodb = boto3.resource('dynamodb', region_name=region)
        self.cognito = boto3.client('cognito-idp', region_name=region)

        # テーブル名
        self.users_table_name = f'{self.project_name}-users-{environment}'
        self.users_table = self.dynamodb.Table(self.users_table_name)

        # Cognito User Pool ID を取得
        self.user_pool_id = self._get_user_pool_id()
        self.client_id = self._get_client_id()

        logger.info(f"Environment: {environment}")
        logger.info(f"Users Table: {self.users_table_name}")
        logger.info(f"User Pool ID: {self.user_pool_id}")
        logger.info(f"Dry Run: {dry_run}")

    def _get_user_pool_id(self) -> str:
        """Cognito User Pool ID を取得"""
        user_pool_name = f'{self.project_name}-user-pool-{self.environment}'

        response = self.cognito.list_user_pools(MaxResults=60)
        for pool in response.get('UserPools', []):
            if pool['Name'] == user_pool_name:
                return pool['Id']

        raise ValueError(f"User Pool not found: {user_pool_name}")

    def _get_client_id(self) -> str:
        """Cognito App Client ID を取得"""
        client_name = f'{self.project_name}-web-client-{self.environment}'

        response = self.cognito.list_user_pool_clients(
            UserPoolId=self.user_pool_id,
            MaxResults=60
        )
        for client in response.get('UserPoolClients', []):
            if client['ClientName'] == client_name:
                return client['ClientId']

        raise ValueError(f"App Client not found: {client_name}")

    def scan_users_to_migrate(self) -> Iterator[dict]:
        """
        移行対象のユーザーをスキャン

        条件:
        - line_user_id が存在する
        - cognito_user_id が存在しない、または空
        """
        logger.info("Scanning users to migrate...")

        scan_kwargs = {
            'FilterExpression': 'attribute_exists(line_user_id) AND '
                               '(attribute_not_exists(cognito_user_id) OR cognito_user_id = :empty)',
            'ExpressionAttributeValues': {':empty': ''}
        }

        while True:
            response = self.users_table.scan(**scan_kwargs)
            for item in response.get('Items', []):
                yield item

            # ページネーション
            if 'LastEvaluatedKey' not in response:
                break
            scan_kwargs['ExclusiveStartKey'] = response['LastEvaluatedKey']

    def check_cognito_user_exists(self, username: str) -> str | None:
        """
        Cognito にユーザーが存在するか確認

        Returns:
            存在する場合は sub (cognito_user_id)、存在しない場合は None
        """
        try:
            response = self.cognito.admin_get_user(
                UserPoolId=self.user_pool_id,
                Username=username
            )
            # sub 属性を取得
            for attr in response.get('UserAttributes', []):
                if attr['Name'] == 'sub':
                    return attr['Value']
            return None
        except ClientError as e:
            if e.response['Error']['Code'] == 'UserNotFoundException':
                return None
            raise

    def create_cognito_user(self, line_user_id: str) -> str | None:
        """
        Cognito に新規ユーザーを作成

        Args:
            line_user_id: LINE User ID (U + 32 hex chars)

        Returns:
            成功時は cognito_user_id (sub)、失敗時は None
        """
        # Cognito は email を username として使用する設定のため、
        # LINE ユーザー用にプレースホルダーメールを生成
        placeholder_email = f'{line_user_id}@line.placeholder.local'

        # 既存ユーザーをチェック（メールアドレスで検索）
        existing_sub = self.check_cognito_user_exists(placeholder_email)
        if existing_sub:
            logger.info(f"  User already exists in Cognito: {placeholder_email}")
            return existing_sub

        if self.dry_run:
            logger.info(f"  [DRY RUN] Would create Cognito user: {placeholder_email}")
            return f"dry-run-sub-{line_user_id[:8]}"

        try:
            # ランダムな仮パスワード（Custom Auth では使用しない）
            temp_password = secrets.token_urlsafe(32) + "Aa1!"

            # ユーザー作成（email を username として使用）
            response = self.cognito.admin_create_user(
                UserPoolId=self.user_pool_id,
                Username=placeholder_email,
                UserAttributes=[
                    {
                        'Name': 'email',
                        'Value': placeholder_email
                    },
                    {
                        'Name': 'custom:line_user_id',
                        'Value': line_user_id
                    },
                    {
                        'Name': 'email_verified',
                        'Value': 'true'
                    }
                ],
                TemporaryPassword=temp_password,
                MessageAction='SUPPRESS'  # ウェルカムメールを送信しない
            )

            # パスワードを確定（FORCE_CHANGE_PASSWORD 状態を解除）
            self.cognito.admin_set_user_password(
                UserPoolId=self.user_pool_id,
                Username=placeholder_email,
                Password=temp_password,
                Permanent=True
            )

            # sub 属性を取得
            for attr in response['User'].get('Attributes', []):
                if attr['Name'] == 'sub':
                    logger.info(f"  Created Cognito user: {placeholder_email} -> {attr['Value']}")
                    return attr['Value']

            logger.error(f"  Failed to get sub for user: {placeholder_email}")
            return None

        except ClientError as e:
            error_code = e.response['Error']['Code']
            error_message = e.response['Error']['Message']

            if error_code == 'UsernameExistsException':
                # レース条件で既に作成されていた場合
                return self.check_cognito_user_exists(placeholder_email)

            logger.error(f"  Failed to create Cognito user: {error_code} - {error_message}")
            return None

    def update_dynamodb_user(self, user_id: str, cognito_user_id: str) -> bool:
        """
        DynamoDB の cognito_user_id を更新

        Args:
            user_id: DynamoDB の user_id (PK)
            cognito_user_id: Cognito の sub

        Returns:
            成功時は True
        """
        if self.dry_run:
            logger.info(f"  [DRY RUN] Would update DynamoDB: {user_id} -> {cognito_user_id}")
            return True

        try:
            self.users_table.update_item(
                Key={'user_id': user_id},
                UpdateExpression='SET cognito_user_id = :cid',
                ExpressionAttributeValues={':cid': cognito_user_id}
            )
            logger.info(f"  Updated DynamoDB: {user_id} -> {cognito_user_id}")
            return True
        except ClientError as e:
            logger.error(f"  Failed to update DynamoDB: {e.response['Error']['Message']}")
            return False

    def migrate_user(self, user: dict) -> bool:
        """
        単一ユーザーを移行

        Args:
            user: DynamoDB ユーザーレコード

        Returns:
            成功時は True
        """
        user_id = user['user_id']
        line_user_id = user.get('line_user_id')

        if not line_user_id:
            logger.warning(f"Skipping user without line_user_id: {user_id}")
            return False

        logger.info(f"Migrating user: {user_id} (LINE: {line_user_id[:10]}...)")

        # Step 1: Cognito ユーザー作成
        cognito_user_id = self.create_cognito_user(line_user_id)
        if not cognito_user_id:
            return False

        # Step 2: DynamoDB 更新
        return self.update_dynamodb_user(user_id, cognito_user_id)

    def run(self) -> MigrationResult:
        """移行を実行"""
        result = MigrationResult()

        logger.info("=" * 60)
        logger.info("LINE User Migration to Cognito")
        logger.info("=" * 60)

        for user in self.scan_users_to_migrate():
            result.total_scanned += 1

            # 既に移行済みかチェック
            if user.get('cognito_user_id'):
                result.already_migrated += 1
                continue

            # 移行実行
            if self.migrate_user(user):
                result.migrated += 1
            else:
                result.failed += 1

        # 結果サマリー
        logger.info("=" * 60)
        logger.info("Migration Summary")
        logger.info("=" * 60)
        logger.info(f"Total scanned:     {result.total_scanned}")
        logger.info(f"Already migrated:  {result.already_migrated}")
        logger.info(f"Newly migrated:    {result.migrated}")
        logger.info(f"Failed:            {result.failed}")
        logger.info(f"Skipped:           {result.skipped}")

        if self.dry_run:
            logger.info("")
            logger.info("*** DRY RUN - No actual changes were made ***")

        return result


def main():
    parser = argparse.ArgumentParser(
        description='LINE ユーザーを Cognito に移行'
    )
    parser.add_argument(
        '--environment', '-e',
        default='dev',
        choices=['dev', 'staging', 'prod'],
        help='対象環境 (default: dev)'
    )
    parser.add_argument(
        '--region', '-r',
        default='ap-northeast-1',
        help='AWS リージョン (default: ap-northeast-1)'
    )
    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='ドライラン（実際には変更しない）'
    )
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='詳細ログを出力'
    )

    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    try:
        migrator = LineUserMigrator(
            environment=args.environment,
            region=args.region,
            dry_run=args.dry_run
        )
        result = migrator.run()

        # 失敗があれば非ゼロで終了
        sys.exit(1 if result.failed > 0 else 0)

    except Exception as e:
        logger.error(f"Migration failed: {e}", exc_info=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
