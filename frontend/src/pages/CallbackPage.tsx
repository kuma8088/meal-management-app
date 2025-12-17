/**
 * OAuth コールバックページ
 *
 * Cognito Hosted UI からのリダイレクトを処理。
 * LINE ログイン（Cognito 経由）後の認証コードをトークンに交換。
 */

import React, { useEffect, useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import './CallbackPage.css';

type CallbackStatus =
  | 'processing'
  | 'success'
  | 'error';

const CallbackPage: React.FC = () => {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { handleOAuthCallback } = useUnifiedAuth();

  const [status, setStatus] = useState<CallbackStatus>('processing');
  const [errorMessage, setErrorMessage] = useState<string>('');

  useEffect(() => {
    const processCallback = async () => {
      // 認証コードを取得
      const code = searchParams.get('code');
      const error = searchParams.get('error');
      const errorDescription = searchParams.get('error_description');

      // エラーの場合
      if (error) {
        console.error('OAuth error:', error, errorDescription);
        setStatus('error');
        setErrorMessage(errorDescription || 'ログインがキャンセルされました');
        return;
      }

      // 認証コードがない場合
      if (!code) {
        console.error('No authorization code received');
        setStatus('error');
        setErrorMessage('認証コードが見つかりません');
        return;
      }

      // トークン交換を実行
      try {
        await handleOAuthCallback(code);
        setStatus('success');
        // 少し待ってからリダイレクト（成功表示を見せるため）
        setTimeout(() => {
          navigate('/', { replace: true });
        }, 1000);
      } catch (err) {
        console.error('Token exchange failed:', err);
        setStatus('error');
        setErrorMessage(
          err instanceof Error
            ? err.message
            : 'トークンの取得に失敗しました'
        );
      }
    };

    processCallback();
  }, [searchParams, handleOAuthCallback, navigate]);

  /**
   * ログインページに戻る
   */
  const handleBackToLogin = () => {
    navigate('/login', { replace: true });
  };

  return (
    <div className="callback-page">
      <div className="callback-container">
        <h1 className="app-title">食事管理アプリ</h1>

        {status === 'processing' && (
          <div className="callback-status">
            <div className="spinner" />
            <p>ログイン処理中...</p>
          </div>
        )}

        {status === 'success' && (
          <div className="callback-status success">
            <div className="checkmark">✓</div>
            <p>ログイン成功！リダイレクト中...</p>
          </div>
        )}

        {status === 'error' && (
          <div className="callback-status error">
            <div className="error-icon">!</div>
            <p className="error-message">{errorMessage}</p>
            <button className="back-button" onClick={handleBackToLogin}>
              ログインページに戻る
            </button>
          </div>
        )}
      </div>
    </div>
  );
};

export default CallbackPage;
