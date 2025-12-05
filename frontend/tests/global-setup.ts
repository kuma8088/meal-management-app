/**
 * Playwright グローバルセットアップ
 * テスト実行前にCognitoテストユーザーを作成
 */

import { config } from 'dotenv';
import { CognitoIdentityProviderClient, AdminCreateUserCommand, AdminSetUserPasswordCommand, AdminDeleteUserCommand } from '@aws-sdk/client-cognito-identity-provider';

// .env.testファイルを優先的に読み込み、なければ.envを読み込み
config({ path: '.env.test' });
if (!process.env.VITE_COGNITO_USER_POOL_ID) {
  config({ path: '.env' });
}

const USER_POOL_ID = process.env.VITE_COGNITO_USER_POOL_ID || '';
const TEST_EMAIL = 'e2e-test@example.com';
const TEST_USERNAME = TEST_EMAIL; // Cognitoはメールアドレスをユーザー名として要求
const TEST_PASSWORD = 'TestPassword123!';

async function globalSetup() {
  console.log('グローバルセットアップ: Cognitoテストユーザーを作成中...');

  if (!USER_POOL_ID) {
    console.error('エラー: VITE_COGNITO_USER_POOL_ID が設定されていません');
    return;
  }

  const client = new CognitoIdentityProviderClient({
    region: process.env.VITE_COGNITO_REGION || 'ap-northeast-1',
  });

  try {
    // 既存のテストユーザーを削除（存在する場合）
    try {
      await client.send(
        new AdminDeleteUserCommand({
          UserPoolId: USER_POOL_ID,
          Username: TEST_USERNAME,
        })
      );
      console.log('既存のテストユーザーを削除しました');
    } catch (error: any) {
      // ユーザーが存在しない場合はエラーを無視
      if (error.name !== 'UserNotFoundException') {
        console.warn('警告: ユーザー削除時のエラー:', error.message);
      }
    }

    // テストユーザーを作成
    await client.send(
      new AdminCreateUserCommand({
        UserPoolId: USER_POOL_ID,
        Username: TEST_USERNAME,
        UserAttributes: [
          {
            Name: 'email',
            Value: TEST_EMAIL,
          },
          {
            Name: 'email_verified',
            Value: 'true',
          },
        ],
        MessageAction: 'SUPPRESS', // 確認メールを送信しない
        TemporaryPassword: 'TempPassword123!',
      })
    );

    console.log('テストユーザーを作成しました:', TEST_USERNAME);

    // パスワードを永続的に設定（FORCE_CHANGE_PASSWORD状態を解除）
    await client.send(
      new AdminSetUserPasswordCommand({
        UserPoolId: USER_POOL_ID,
        Username: TEST_USERNAME,
        Password: TEST_PASSWORD,
        Permanent: true,
      })
    );

    console.log('テストユーザーのパスワードを設定しました');

    // テスト用の環境変数を設定
    process.env.E2E_TEST_USERNAME = TEST_USERNAME;
    process.env.E2E_TEST_PASSWORD = TEST_PASSWORD;
    process.env.E2E_TEST_EMAIL = TEST_EMAIL;

    console.log('グローバルセットアップ完了');
  } catch (error: any) {
    console.error('テストユーザー作成エラー:', error.message);
    throw error;
  }
}

export default globalSetup;
