/**
 * 統一認証コンテキスト (UnifiedAuthContext)
 *
 * Cognito 認証と LINE 認証（LIFF 経由）を統合
 * - 通常ブラウザ: Cognito 認証 (Email/Password or LINE Hosted UI)
 * - LIFF 経由: LINE ID Token → /auth/liff-login → Cognito トークン
 *
 * 最終的にすべての API 呼び出しを Cognito JWT で認証
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js';
import liff from '@line/liff';
import { setAuthTokens, clearAuthTokens, apiClient } from '../api/client';

// ========================================
// 環境変数
// ========================================

const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID || '';
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '';
const liffId = import.meta.env.VITE_LIFF_ID || '';
const cognitoDomain = import.meta.env.VITE_COGNITO_DOMAIN || '';
const redirectUri = import.meta.env.VITE_REDIRECT_URI || window.location.origin + '/callback';

const userPool = new CognitoUserPool({
  UserPoolId: userPoolId,
  ClientId: clientId,
});

// ========================================
// 型定義
// ========================================

export type AuthMethod = 'cognito' | 'line-hosted-ui' | 'liff';

export interface User {
  userId: string;
  username: string;
  email: string;
  authMethod: AuthMethod;
  lineUserId?: string;
}

interface UnifiedAuthContextType {
  // 状態
  user: User | null;
  loading: boolean;
  isInLiff: boolean;
  isLiffInitialized: boolean;

  // Cognito 認証
  signUp: (username: string, email: string, password: string) => Promise<void>;
  confirmSignUp: (username: string, code: string) => Promise<void>;
  signIn: (username: string, password: string) => Promise<void>;

  // LINE 認証 (Cognito Hosted UI 経由)
  signInWithLineHostedUI: () => void;

  // LIFF 認証 (/auth/liff-login 経由)
  signInWithLIFF: () => Promise<void>;

  // 共通
  signOut: () => void;
  refreshSession: () => Promise<void>;

  // OAuth コールバック処理
  handleOAuthCallback: (code: string) => Promise<void>;
}

// ========================================
// コンテキスト
// ========================================

const UnifiedAuthContext = createContext<UnifiedAuthContextType | undefined>(undefined);

export const useUnifiedAuth = () => {
  const context = useContext(UnifiedAuthContext);
  if (!context) {
    throw new Error('useUnifiedAuth must be used within UnifiedAuthProvider');
  }
  return context;
};

// ========================================
// プロバイダー
// ========================================

interface UnifiedAuthProviderProps {
  children: ReactNode;
}

export const UnifiedAuthProvider: React.FC<UnifiedAuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);
  const [isInLiff, setIsInLiff] = useState(false);
  const [isLiffInitialized, setIsLiffInitialized] = useState(false);

  // ========================================
  // 初期化
  // ========================================

  useEffect(() => {
    const initialize = async () => {
      try {
        // LIFF 初期化
        if (liffId) {
          try {
            await liff.init({ liffId });
            setIsLiffInitialized(true);
            setIsInLiff(liff.isInClient());
            console.log('LIFF initialized:', {
              isInClient: liff.isInClient(),
              isLoggedIn: liff.isLoggedIn(),
            });

            // 注: liff.login() は LIFFEntry ページで必要に応じて呼ぶ
            // ここで自動ログインすると無限ループになる可能性がある
          } catch (liffError) {
            console.warn('LIFF initialization failed:', liffError);
            setIsLiffInitialized(true);
          }
        } else {
          setIsLiffInitialized(true);
        }

        // セッション復元
        await restoreSession();
      } catch (error) {
        console.error('Initialization error:', error);
      } finally {
        setLoading(false);
      }
    };

    initialize();

    // 401 エラーでログアウト
    const handleUnauthorized = () => {
      signOut();
    };
    window.addEventListener('unauthorized', handleUnauthorized);

    return () => {
      window.removeEventListener('unauthorized', handleUnauthorized);
    };
  }, []);

  /**
   * セッション復元
   */
  const restoreSession = async (): Promise<void> => {
    console.log('restoreSession: starting...');

    // Cognito セッションをチェック
    const cognitoUser = userPool.getCurrentUser();
    console.log('restoreSession: cognitoUser exists:', !!cognitoUser, cognitoUser?.getUsername());
    if (cognitoUser) {
      return new Promise((resolve) => {
        cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
          if (!err && session?.isValid()) {
            // トークンを保存
            setAuthTokens(
              session.getAccessToken().getJwtToken(),
              session.getRefreshToken().getToken(),
              session.getIdToken().getJwtToken()
            );

            // ユーザー情報を取得
            cognitoUser.getUserAttributes((err, attributes) => {
              if (!err && attributes) {
                const emailAttr = attributes.find((attr) => attr.Name === 'email');
                const subAttr = attributes.find((attr) => attr.Name === 'sub');
                const lineUserIdAttr = attributes.find((attr) => attr.Name === 'custom:line_user_id');
                const authMethodStored = localStorage.getItem('authMethod') as AuthMethod;

                setUser({
                  userId: subAttr?.Value || '',
                  username: cognitoUser.getUsername(),
                  email: emailAttr?.Value || '',
                  authMethod: authMethodStored || 'cognito',
                  lineUserId: lineUserIdAttr?.Value,
                });
              }
              resolve();
            });
          } else {
            console.log('restoreSession: Cognito session invalid, falling back to localStorage');
            // localStorage からトークンを復元（Playwright 環境などの互換性のため）
            const idToken = localStorage.getItem('idToken');
            console.log('restoreSession: localStorage idToken exists:', !!idToken);
            if (idToken) {
              try {
                const payload = JSON.parse(atob(idToken.split('.')[1]));
                const authMethodStored = localStorage.getItem('authMethod') as AuthMethod;
                setUser({
                  userId: payload.sub || '',
                  username: payload['cognito:username'] || payload.email || '',
                  email: payload.email || '',
                  authMethod: authMethodStored || 'cognito',
                  lineUserId: payload['custom:line_user_id'],
                });
              } catch (decodeError) {
                console.error('Token decode error:', decodeError);
              }
            }
            resolve();
          }
        });
      });
    }

    // localStorage から復元
    const idToken = localStorage.getItem('idToken');
    console.log('restoreSession: checking localStorage, idToken exists:', !!idToken);
    if (idToken) {
      try {
        const payload = JSON.parse(atob(idToken.split('.')[1]));
        const authMethodStored = localStorage.getItem('authMethod') as AuthMethod;
        console.log('restoreSession: restoring user from localStorage:', payload.sub);
        setUser({
          userId: payload.sub || '',
          username: payload['cognito:username'] || payload.email || '',
          email: payload.email || '',
          authMethod: authMethodStored || 'cognito',
          lineUserId: payload['custom:line_user_id'],
        });
      } catch (decodeError) {
        console.error('Token decode error:', decodeError);
      }
    } else {
      console.log('restoreSession: no idToken found in localStorage');
    }
  };

  // ========================================
  // Cognito 認証
  // ========================================

  /**
   * ユーザー登録
   */
  const signUp = async (username: string, email: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const attributeList = [
        new CognitoUserAttribute({
          Name: 'email',
          Value: email,
        }),
      ];

      // username をユーザー名として使用
      userPool.signUp(username, password, attributeList, [], (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
    });
  };

  /**
   * ユーザー登録の確認
   */
  const confirmSignUp = async (username: string, code: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = new CognitoUser({
        Username: username,
        Pool: userPool,
      });

      cognitoUser.confirmRegistration(code, true, (err) => {
        if (err) {
          reject(err);
          return;
        }
        resolve();
      });
    });
  };

  /**
   * ログイン (Username/Password)
   */
  const signIn = async (username: string, password: string): Promise<void> => {
    return new Promise((resolve, reject) => {
      const authenticationDetails = new AuthenticationDetails({
        Username: username,
        Password: password,
      });

      const cognitoUser = new CognitoUser({
        Username: username,
        Pool: userPool,
      });

      cognitoUser.authenticateUser(authenticationDetails, {
        onSuccess: (session: CognitoUserSession) => {
          setAuthTokens(
            session.getAccessToken().getJwtToken(),
            session.getRefreshToken().getToken(),
            session.getIdToken().getJwtToken()
          );
          localStorage.setItem('authMethod', 'cognito');

          cognitoUser.getUserAttributes((err, attributes) => {
            if (err || !attributes) {
              reject(err);
              return;
            }

            const emailAttr = attributes.find((attr) => attr.Name === 'email');
            const subAttr = attributes.find((attr) => attr.Name === 'sub');

            setUser({
              userId: subAttr?.Value || '',
              username: cognitoUser.getUsername(),
              email: emailAttr?.Value || '',
              authMethod: 'cognito',
            });

            resolve();
          });
        },
        onFailure: (err: Error) => {
          reject(err);
        },
      });
    });
  };

  // ========================================
  // LINE 認証 (Cognito Hosted UI 経由)
  // ========================================

  /**
   * LINE ログイン (Cognito Hosted UI)
   * 通常ブラウザで LINE ログインする場合に使用
   */
  const signInWithLineHostedUI = useCallback(() => {
    if (!cognitoDomain) {
      console.error('VITE_COGNITO_DOMAIN is not configured');
      return;
    }

    const authUrl = `https://${cognitoDomain}.auth.ap-northeast-1.amazoncognito.com/oauth2/authorize`;
    const params = new URLSearchParams({
      response_type: 'code',
      client_id: clientId,
      redirect_uri: redirectUri,
      identity_provider: 'LINE',
      scope: 'openid email profile',
    });

    window.location.href = `${authUrl}?${params.toString()}`;
  }, []);

  /**
   * OAuth コールバック処理
   */
  const handleOAuthCallback = async (code: string): Promise<void> => {
    if (!cognitoDomain) {
      throw new Error('VITE_COGNITO_DOMAIN is not configured');
    }

    const tokenUrl = `https://${cognitoDomain}.auth.ap-northeast-1.amazoncognito.com/oauth2/token`;

    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded',
      },
      body: new URLSearchParams({
        grant_type: 'authorization_code',
        client_id: clientId,
        code: code,
        redirect_uri: redirectUri,
      }),
    });

    if (!response.ok) {
      throw new Error('Token exchange failed');
    }

    const tokens = await response.json();

    setAuthTokens(
      tokens.access_token,
      tokens.refresh_token,
      tokens.id_token
    );
    localStorage.setItem('authMethod', 'line-hosted-ui');

    // ユーザー情報をデコード
    const payload = JSON.parse(atob(tokens.id_token.split('.')[1]));

    setUser({
      userId: payload.sub || '',
      username: payload['cognito:username'] || payload.email || '',
      email: payload.email || '',
      authMethod: 'line-hosted-ui',
      lineUserId: payload['custom:line_user_id'],
    });
  };

  // ========================================
  // LIFF 認証 (/auth/liff-login 経由)
  // ========================================

  /**
   * LIFF ログイン
   * LIFF 環境で LINE Access Token + Profile を使用して Cognito トークンに変換
   *
   * 注: openid スコープは申請が必要なため、Access Token 方式を使用
   */
  const signInWithLIFF = useCallback(async (): Promise<void> => {
    if (!isLiffInitialized) {
      throw new Error('LIFF is not initialized');
    }

    console.log('signInWithLIFF called, isLoggedIn:', liff.isLoggedIn());

    if (!liff.isLoggedIn()) {
      // LIFF 環境で LINE ログインしていない場合
      // liff.login() を呼ぶとリダイレクトループになるため、エラーをスロー
      // 通常、LIFF 環境では LINE に自動ログインされているはず
      console.error('LINE not logged in within LIFF environment');
      throw new Error('LINE ログインが必要です。LINE アプリからアクセスしてください。');
    }

    // LINE Access Token を取得（openid スコープ不要）
    const lineAccessToken = liff.getAccessToken();
    if (!lineAccessToken) {
      const isLoggedIn = liff.isLoggedIn();
      const isInClient = liff.isInClient();
      console.error('LIFF debug info:', { isLoggedIn, isInClient, liffId });
      throw new Error(
        `Failed to get LINE Access Token. (isLoggedIn: ${isLoggedIn}, isInClient: ${isInClient})`
      );
    }

    // LINE プロフィールを取得（必須: line_user_id が必要）
    let lineUserId: string;
    try {
      const profile = await liff.getProfile();
      lineUserId = profile.userId;
    } catch (profileError) {
      console.error('Failed to get LINE profile:', profileError);
      throw new Error('Failed to get LINE profile. Please try again.');
    }

    // /auth/liff-login API を呼び出して Cognito トークンを取得
    // Access Token 方式: バックエンドで LINE API を使って検証
    const response = await apiClient.post('/auth/liff-login', {
      line_access_token: lineAccessToken,
      line_user_id: lineUserId,
    });

    const tokens = response.data;

    if (!tokens.id_token || !tokens.access_token) {
      throw new Error('Invalid response from /auth/liff-login');
    }

    // トークンを保存
    console.log('signInWithLIFF: saving tokens to localStorage');
    setAuthTokens(
      tokens.access_token,
      tokens.refresh_token || '',
      tokens.id_token
    );
    localStorage.setItem('authMethod', 'liff');

    // 保存確認
    const savedToken = localStorage.getItem('idToken');
    console.log('signInWithLIFF: token saved to localStorage:', !!savedToken);

    // ユーザー情報をデコード
    const payload = JSON.parse(atob(tokens.id_token.split('.')[1]));

    const newUser = {
      userId: payload.sub || '',
      username: payload['cognito:username'] || payload.email || 'LINE User',
      email: payload.email || '',
      authMethod: 'liff' as AuthMethod,
      lineUserId: lineUserId,
    };

    setUser(newUser);

    console.log('LIFF login successful, user:', payload.sub);
  }, [isLiffInitialized]);

  // ========================================
  // 共通
  // ========================================

  /**
   * ログアウト
   */
  const signOut = useCallback(() => {
    // Cognito セッションをクリア
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }

    // トークンをクリア
    clearAuthTokens();
    localStorage.removeItem('authMethod');

    // LIFF ログアウト（LIFF 環境の場合）
    if (isInLiff && liff.isLoggedIn()) {
      liff.logout();
    }

    setUser(null);
  }, [isInLiff]);

  /**
   * セッションをリフレッシュ
   */
  const refreshSession = async (): Promise<void> => {
    return new Promise((resolve, reject) => {
      const cognitoUser = userPool.getCurrentUser();
      if (!cognitoUser) {
        reject(new Error('No current user'));
        return;
      }

      cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
        if (err || !session) {
          reject(err);
          return;
        }

        const refreshToken = session.getRefreshToken();
        cognitoUser.refreshSession(refreshToken, (err, session) => {
          if (err) {
            reject(err);
            return;
          }

          setAuthTokens(
            session.getAccessToken().getJwtToken(),
            session.getRefreshToken().getToken(),
            session.getIdToken().getJwtToken()
          );

          resolve();
        });
      });
    });
  };

  // ========================================
  // Context Value
  // ========================================

  const value: UnifiedAuthContextType = {
    user,
    loading,
    isInLiff,
    isLiffInitialized,
    signUp,
    confirmSignUp,
    signIn,
    signInWithLineHostedUI,
    signInWithLIFF,
    signOut,
    refreshSession,
    handleOAuthCallback,
  };

  return (
    <UnifiedAuthContext.Provider value={value}>
      {children}
    </UnifiedAuthContext.Provider>
  );
};

export default UnifiedAuthContext;
