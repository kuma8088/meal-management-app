/**
 * Playwright グローバルティアダウン
 * テスト終了後にCognitoテストユーザーを削除
 */

import { config } from 'dotenv';
import { CognitoIdentityProviderClient, AdminDeleteUserCommand } from '@aws-sdk/client-cognito-identity-provider';

// .envファイルを読み込み
config({ path: '.env' });

const USER_POOL_ID = process.env.VITE_COGNITO_USER_POOL_ID || '';
const TEST_EMAIL = 'e2e-test@example.com';
const TEST_USERNAME = TEST_EMAIL; // Cognitoはメールアドレスをユーザー名として要求

async function globalTeardown() {
  console.log('グローバルティアダウン: Cognitoテストユーザーを削除中...');

  if (!USER_POOL_ID) {
    console.error('エラー: VITE_COGNITO_USER_POOL_ID が設定されていません');
    return;
  }

  const client = new CognitoIdentityProviderClient({
    region: process.env.VITE_COGNITO_REGION || 'ap-northeast-1',
  });

  try {
    await client.send(
      new AdminDeleteUserCommand({
        UserPoolId: USER_POOL_ID,
        Username: TEST_USERNAME,
      })
    );

    console.log('テストユーザーを削除しました:', TEST_USERNAME);
    console.log('グローバルティアダウン完了');
  } catch (error: any) {
    if (error.name === 'UserNotFoundException') {
      console.log('テストユーザーは既に存在しません');
    } else {
      console.error('テストユーザー削除エラー:', error.message);
    }
  }
}

export default globalTeardown;
