/**
 * LIFF エントリーポイントページ
 *
 * LINE アプリ内ブラウザからアクセスした場合のエントリーポイント。
 * 自動的に LINE 認証を行い、Cognito トークンを取得してホームにリダイレクト。
 */

import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import './LIFFEntry.css';

type LIFFStatus =
  | 'initializing'
  | 'authenticating'
  | 'success'
  | 'error';

const LIFFEntry: React.FC = () => {
  const navigate = useNavigate();
  const {
    user,
    loading,
    isInLiff,
    isLiffInitialized,
    signInWithLIFF,
  } = useUnifiedAuth();

  const [status, setStatus] = useState<LIFFStatus>('initializing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  // 認証実行済みフラグ（再実行を防ぐ）
  const [authAttempted, setAuthAttempted] = useState(false);
  // 認証完了フラグ（遷移のトリガー）
  const [authCompleted, setAuthCompleted] = useState(false);

  // ユーザーがログイン済みになったら自動遷移
  useEffect(() => {
    console.log('LIFFEntry useEffect[user]:', { user: user?.userId, status, authCompleted });
    if (user && authCompleted && status !== 'error') {
      console.log('User logged in and authCompleted, navigating to home:', user.userId);
      setStatus('success');
      // 認証完了フラグをクリア
      sessionStorage.removeItem('liffAuthInProgress');
      // React Router の navigate を使用（ページリロードせず状態を保持）
      const timer = setTimeout(() => {
        console.log('Navigating to home via React Router...');
        navigate('/', { replace: true });
      }, 300);
      return () => clearTimeout(timer);
    }
  }, [user, status, authCompleted, navigate]);

  // LIFF 認証の実行
  useEffect(() => {
    const performLiffLogin = async () => {
      // 既にログイン済みの場合は何もしない（上の useEffect で遷移）
      if (user) {
        return;
      }

      // LIFF 初期化待ち
      if (!isLiffInitialized || loading) {
        setStatus('initializing');
        return;
      }

      // LIFF 環境でない場合は通常ログインにリダイレクト
      if (!isInLiff) {
        console.log('Not in LIFF environment, redirecting to login');
        navigate('/login', { replace: true });
        return;
      }

      // 既に認証を試みた場合はスキップ（二重実行防止）
      if (authAttempted) {
        console.log('Already attempted authentication, waiting for user state...');
        return;
      }

      // LIFF 認証を実行
      setAuthAttempted(true);
      setStatus('authenticating');
      console.log('Starting LIFF authentication...');

      // 認証開始フラグを設定（PrivateRoute での無限ループを防ぐ）
      sessionStorage.setItem('liffAuthInProgress', 'true');

      try {
        await signInWithLIFF();
        console.log('signInWithLIFF completed successfully');
        // 認証成功フラグを設定（user 状態の更新を待つトリガー）
        setAuthCompleted(true);
        setStatus('success');
        console.log('Authentication successful, waiting for user state update...');
      } catch (error) {
        console.error('LIFF login failed:', error);
        // 認証失敗時はフラグをクリア
        sessionStorage.removeItem('liffAuthInProgress');
        setStatus('error');
        setErrorMessage(
          error instanceof Error
            ? error.message
            : 'LINE 認証に失敗しました。もう一度お試しください。'
        );
      }
    };

    performLiffLogin();
  }, [user, loading, isLiffInitialized, isInLiff, authAttempted, navigate, signInWithLIFF]);

  /**
   * リトライ処理
   */
  const handleRetry = async () => {
    setStatus('authenticating');
    setErrorMessage('');
    try {
      await signInWithLIFF();
      setStatus('success');
      navigate('/', { replace: true });
    } catch (error) {
      console.error('LIFF login retry failed:', error);
      setStatus('error');
      setErrorMessage(
        error instanceof Error
          ? error.message
          : 'LINE 認証に失敗しました。もう一度お試しください。'
      );
    }
  };

  return (
    <div className="liff-entry-page">
      <div className="liff-entry-container">
        <h1 className="app-title">食事管理アプリ</h1>

        {status === 'initializing' && (
          <div className="liff-status">
            <div className="spinner" />
            <p>LINE 接続を準備中...</p>
          </div>
        )}

        {status === 'authenticating' && (
          <div className="liff-status">
            <div className="spinner" />
            <p>LINE アカウントで認証中...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="liff-status success">
            <div className="checkmark">✓</div>
            <p>認証成功！リダイレクト中...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="liff-status error">
            <div className="error-icon">!</div>
            <p className="error-message">{errorMessage}</p>
            <button className="retry-button" onClick={handleRetry}>
              再試行
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default LIFFEntry;
