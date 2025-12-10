/**
 * LIFF (LINE Front-end Framework) コンテキスト
 *
 * LINE アプリ内ブラウザからアクセスした場合の認証管理
 * LIFFで開かれた場合は LINE 認証を使用し、通常ブラウザでは Cognito 認証を使用
 */

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';
import type { ReactNode } from 'react';
import liff from '@line/liff';

// LIFF ID は環境変数から取得
const LIFF_ID = import.meta.env.VITE_LIFF_ID || '';

// ========================================
// 型定義
// ========================================

export interface LiffProfile {
  userId: string;
  displayName: string;
  pictureUrl?: string;
  statusMessage?: string;
}

interface LiffContextType {
  // LIFF 状態
  isLiffInitialized: boolean;
  isInLiff: boolean;
  isLoggedIn: boolean;
  profile: LiffProfile | null;
  error: string | null;

  // LIFF アクション
  login: () => void;
  logout: () => void;
  getAccessToken: () => string | null;

  // ユーティリティ
  closeWindow: () => void;
  openWindow: (url: string, external?: boolean) => void;
}

// ========================================
// コンテキスト
// ========================================

const LiffContext = createContext<LiffContextType | undefined>(undefined);

export const useLiff = () => {
  const context = useContext(LiffContext);
  if (!context) {
    throw new Error('useLiff must be used within LiffProvider');
  }
  return context;
};

// ========================================
// プロバイダー
// ========================================

interface LiffProviderProps {
  children: ReactNode;
}

export const LiffProvider: React.FC<LiffProviderProps> = ({ children }) => {
  const [isLiffInitialized, setIsLiffInitialized] = useState(false);
  const [isInLiff, setIsInLiff] = useState(false);
  const [isLoggedIn, setIsLoggedIn] = useState(false);
  const [profile, setProfile] = useState<LiffProfile | null>(null);
  const [error, setError] = useState<string | null>(null);

  /**
   * LIFF 初期化
   */
  useEffect(() => {
    const initializeLiff = async () => {
      if (!LIFF_ID) {
        console.log('LIFF_ID not configured, skipping LIFF initialization');
        setIsLiffInitialized(true);
        return;
      }

      try {
        await liff.init({ liffId: LIFF_ID });
        setIsLiffInitialized(true);
        setIsInLiff(liff.isInClient());

        // ログイン状態をチェック
        if (liff.isLoggedIn()) {
          setIsLoggedIn(true);

          // プロフィールを取得
          try {
            const liffProfile = await liff.getProfile();
            setProfile({
              userId: liffProfile.userId,
              displayName: liffProfile.displayName,
              pictureUrl: liffProfile.pictureUrl,
              statusMessage: liffProfile.statusMessage,
            });

            // LINE User ID を localStorage に保存（API 認証用）
            localStorage.setItem('lineUserId', liffProfile.userId);
            localStorage.setItem('authType', 'line');
          } catch (profileError) {
            console.error('Failed to get LIFF profile:', profileError);
          }
        }
      } catch (initError) {
        console.error('LIFF initialization failed:', initError);
        setError('LIFF の初期化に失敗しました');
        setIsLiffInitialized(true);
      }
    };

    initializeLiff();
  }, []);

  /**
   * LINE ログイン
   */
  const login = useCallback(() => {
    if (!liff.isLoggedIn()) {
      liff.login();
    }
  }, []);

  /**
   * LINE ログアウト
   */
  const logout = useCallback(() => {
    if (liff.isLoggedIn()) {
      liff.logout();
      setIsLoggedIn(false);
      setProfile(null);
      localStorage.removeItem('lineUserId');
      localStorage.removeItem('authType');
    }
  }, []);

  /**
   * LIFF アクセストークンを取得
   */
  const getAccessToken = useCallback(() => {
    return liff.getAccessToken();
  }, []);

  /**
   * LIFF ウィンドウを閉じる
   */
  const closeWindow = useCallback(() => {
    if (liff.isInClient()) {
      liff.closeWindow();
    }
  }, []);

  /**
   * 外部ウィンドウを開く
   */
  const openWindow = useCallback((url: string, external: boolean = false) => {
    liff.openWindow({ url, external });
  }, []);

  const value: LiffContextType = {
    isLiffInitialized,
    isInLiff,
    isLoggedIn,
    profile,
    error,
    login,
    logout,
    getAccessToken,
    closeWindow,
    openWindow,
  };

  return <LiffContext.Provider value={value}>{children}</LiffContext.Provider>;
};
