/**
 * 認証コンテキスト
 *
 * Amazon Cognito または LINE (LIFF) を使用した認証管理
 * - 通常ブラウザ: Cognito 認証
 * - LIFF 経由: LINE 認証 (LINE User ID で API 呼び出し)
 */

import React, { createContext, useContext, useState, useEffect } from 'react';
import type { ReactNode } from 'react';
import {
  CognitoUserPool,
  CognitoUser,
  AuthenticationDetails,
  CognitoUserSession,
  CognitoUserAttribute,
} from 'amazon-cognito-identity-js';
import { setAuthTokens, clearAuthTokens, setLineAuth, clearLineAuth, apiClient } from '../api/client';

// Cognito設定（環境変数から取得）
const userPoolId = import.meta.env.VITE_COGNITO_USER_POOL_ID || '';
const clientId = import.meta.env.VITE_COGNITO_CLIENT_ID || '';

const userPool = new CognitoUserPool({
  UserPoolId: userPoolId,
  ClientId: clientId,
});

// ========================================
// 型定義
// ========================================

export type AuthType = 'cognito' | 'line';

export interface User {
  userId: string;
  username: string;
  email: string;
  authType: AuthType;
  lineUserId?: string;  // LINE User ID (LIFF経由の場合)
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  authType: AuthType | null;
  signUp: (username: string, email: string, password: string) => Promise<void>;
  confirmSignUp: (username: string, code: string) => Promise<void>;
  signIn: (username: string, password: string) => Promise<void>;
  signInWithLine: (lineUserId: string, displayName: string) => Promise<void>;
  signOut: () => void;
  refreshSession: () => Promise<void>;
}

// ========================================
// コンテキスト
// ========================================

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within AuthProvider');
  }
  return context;
};

// ========================================
// プロバイダー
// ========================================

interface AuthProviderProps {
  children: ReactNode;
}

export const AuthProvider: React.FC<AuthProviderProps> = ({ children }) => {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  /**
   * 現在のセッションをチェック
   */
  useEffect(() => {
    const checkSession = async () => {
      try {
        const cognitoUser = userPool.getCurrentUser();
        if (cognitoUser) {
          cognitoUser.getSession((err: Error | null, session: CognitoUserSession | null) => {
            if (err || !session) {
              setLoading(false);
              return;
            }

            if (session.isValid()) {
              // トークンを保存
              setAuthTokens(
                session.getAccessToken().getJwtToken(),
                session.getRefreshToken().getToken(),
                session.getIdToken().getJwtToken()
              );

              // ユーザー情報を取得
              cognitoUser.getUserAttributes((err, attributes) => {
                if (err || !attributes) {
                  setLoading(false);
                  return;
                }

                const emailAttr = attributes.find((attr) => attr.Name === 'email');
                const subAttr = attributes.find((attr) => attr.Name === 'sub');

                setUser({
                  userId: subAttr?.Value || '',
                  username: cognitoUser.getUsername(),
                  email: emailAttr?.Value || '',
                  authType: 'cognito',
                });

                setLoading(false);
              });
            } else {
              setLoading(false);
            }
          });
        } else {
          // Cognitoセッションが取得できない場合、localStorageから直接復元
          const authType = localStorage.getItem('authType') as AuthType | null;

          if (authType === 'line') {
            // LINE認証の復元
            const lineUserId = localStorage.getItem('lineUserId');
            const lineDisplayName = localStorage.getItem('lineDisplayName');
            const internalUserId = localStorage.getItem('internalUserId');
            if (lineUserId) {
              setUser({
                userId: internalUserId || lineUserId,  // 内部ユーザーID優先
                username: lineDisplayName || 'LINE User',
                email: '',
                authType: 'line',
                lineUserId: lineUserId,
              });
            }
            setLoading(false);
          } else {
            // Cognito認証の復元 (Playwright環境などでの互換性のため)
            const idToken = localStorage.getItem('idToken');
            if (idToken) {
              try {
                // JWTをデコード (base64)
                const payload = JSON.parse(atob(idToken.split('.')[1]));
                setUser({
                  userId: payload.sub || '',
                  username: payload['cognito:username'] || payload.email || '',
                  email: payload.email || '',
                  authType: 'cognito',
                });
              } catch (decodeError) {
                console.error('Token decode error:', decodeError);
              }
            }
            setLoading(false);
          }
        }
      } catch (error) {
        console.error('Session check error:', error);
        setLoading(false);
      }
    };

    checkSession();

    // 401エラーでログアウト
    const handleUnauthorized = () => {
      signOut();
    };
    window.addEventListener('unauthorized', handleUnauthorized);

    return () => {
      window.removeEventListener('unauthorized', handleUnauthorized);
    };
  }, []);

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
   * ログイン
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
          // トークンを保存
          setAuthTokens(
            session.getAccessToken().getJwtToken(),
            session.getRefreshToken().getToken(),
            session.getIdToken().getJwtToken()
          );

          // ユーザー情報を取得
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
              authType: 'cognito',
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

  /**
   * LINE ログイン (LIFF経由)
   *
   * LINE User ID でローカルストレージを設定後、/users/me から内部ユーザーIDを取得
   */
  const signInWithLine = async (lineUserId: string, displayName: string): Promise<void> => {
    // LINE認証情報を保存（API呼び出しに必要）
    setLineAuth(lineUserId);
    localStorage.setItem('lineDisplayName', displayName);

    try {
      // /users/me を呼び出して内部ユーザーIDを取得
      const response = await apiClient.get('/users/me');
      const userData = response.data;

      // 内部ユーザーIDを保存
      const internalUserId = userData.user_id || lineUserId;
      localStorage.setItem('internalUserId', internalUserId);

      setUser({
        userId: internalUserId,  // 内部ユーザーID（API呼び出し用）
        username: displayName,
        email: '',
        authType: 'line',
        lineUserId: lineUserId,  // LINE User ID（認証用）
      });

      console.log('LINE auth successful, internal user_id:', internalUserId);
    } catch (error) {
      console.error('Failed to fetch internal user_id:', error);
      // フォールバック: LINE User ID をそのまま使用
      setUser({
        userId: lineUserId,
        username: displayName,
        email: '',
        authType: 'line',
        lineUserId: lineUserId,
      });
    }
  };

  /**
   * ログアウト
   */
  const signOut = () => {
    const authType = localStorage.getItem('authType') as AuthType | null;

    if (authType === 'line') {
      // LINE認証のクリア
      clearLineAuth();
      localStorage.removeItem('lineDisplayName');
      localStorage.removeItem('internalUserId');
    } else {
      // Cognito認証のクリア
      const cognitoUser = userPool.getCurrentUser();
      if (cognitoUser) {
        cognitoUser.signOut();
      }
      clearAuthTokens();
    }

    setUser(null);
  };

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

          // 新しいトークンを保存
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

  const value: AuthContextType = {
    user,
    loading,
    authType: user?.authType || null,
    signUp,
    confirmSignUp,
    signIn,
    signInWithLine,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
