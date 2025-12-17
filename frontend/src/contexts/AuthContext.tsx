/**
 * 認証コンテキスト
 *
 * Amazon Cognito を使用した統一認証管理
 * - 通常ブラウザ: Cognito 認証（メール/パスワード）
 * - LIFF 経由: Cognito 認証（/auth/liff-login API でトークン取得）
 *
 * すべての API 呼び出しは Cognito JWT トークンを使用
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
import { setAuthTokens, clearAuthTokens, apiClient } from '../api/client';

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

export interface User {
  userId: string;
  username: string;
  email: string;
}

interface AuthContextType {
  user: User | null;
  loading: boolean;
  signUp: (username: string, email: string, password: string) => Promise<void>;
  confirmSignUp: (username: string, code: string) => Promise<void>;
  signIn: (username: string, password: string) => Promise<void>;
  signInWithLiff: (lineIdToken: string) => Promise<void>;
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
   *
   * Cognito セッションを確認し、有効なら復元
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
                });

                setLoading(false);
              });
            } else {
              setLoading(false);
            }
          });
        } else {
          // Cognito セッションがない場合、localStorage の idToken から復元
          // (Playwright 環境、LIFF ログイン後の復元)
          const idToken = localStorage.getItem('idToken');
          if (idToken) {
            try {
              // JWT をデコード
              const payload = JSON.parse(atob(idToken.split('.')[1]));
              setUser({
                userId: payload.sub || '',
                username: payload['cognito:username'] || payload.email || '',
                email: payload.email || '',
              });
            } catch (decodeError) {
              console.error('Token decode error:', decodeError);
            }
          }
          setLoading(false);
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
   * LIFF ログイン
   *
   * LINE ID Token を /auth/liff-login API に送信し、Cognito トークンを取得
   *
   * @param lineIdToken - LIFF から取得した LINE ID Token
   */
  const signInWithLiff = async (lineIdToken: string): Promise<void> => {
    // /auth/liff-login API を呼び出して Cognito トークンを取得
    const response = await apiClient.post('/auth/liff-login', {
      line_id_token: lineIdToken,
    });

    const { id_token, access_token, refresh_token, user_id, email } = response.data;

    // Cognito トークンを保存
    setAuthTokens(access_token, refresh_token, id_token);

    // JWT からユーザー情報を取得
    try {
      const payload = JSON.parse(atob(id_token.split('.')[1]));
      setUser({
        userId: user_id || payload.sub || '',
        username: payload['cognito:username'] || email || '',
        email: email || payload.email || '',
      });
    } catch (decodeError) {
      console.error('Token decode error:', decodeError);
      setUser({
        userId: user_id || '',
        username: email || '',
        email: email || '',
      });
    }

    console.log('LIFF auth successful, user_id:', user_id);
  };

  /**
   * ログアウト
   */
  const signOut = () => {
    // Cognito セッションをクリア
    const cognitoUser = userPool.getCurrentUser();
    if (cognitoUser) {
      cognitoUser.signOut();
    }
    clearAuthTokens();
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
    signUp,
    confirmSignUp,
    signIn,
    signInWithLiff,
    signOut,
    refreshSession,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
};
