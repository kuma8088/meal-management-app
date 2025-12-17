/**
 * ログインページ
 *
 * 認証方式:
 * - Email/Password: Cognito 直接認証
 * - LINE でログイン: Cognito Hosted UI 経由
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import LoginForm from '../components/LoginForm';
import SignUpForm from '../components/SignUpForm';
import './LoginPage.css';

type TabType = 'login' | 'signup';

const LoginPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('login');
  const navigate = useNavigate();
  const { signIn, signUp, confirmSignUp, signInWithLineHostedUI } = useUnifiedAuth();
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  /**
   * ログイン処理
   */
  const handleLogin = async (username: string, password: string) => {
    try {
      setError('');
      await signIn(username, password);
      navigate('/');
    } catch (err: any) {
      console.error('Login error:', err);
      setError(err.message || 'ログインに失敗しました');
    }
  };

  /**
   * ユーザー登録処理
   */
  const handleSignUp = async (username: string, email: string, password: string) => {
    try {
      setError('');
      await signUp(username, email, password);
      setSuccessMessage('確認コードがメールに送信されました。確認コードを入力してください。');
    } catch (err: any) {
      console.error('Sign up error:', err);
      setError(err.message || 'ユーザー登録に失敗しました');
    }
  };

  /**
   * 確認コード送信処理
   */
  const handleConfirmSignUp = async (username: string, code: string) => {
    try {
      setError('');
      await confirmSignUp(username, code);
      setSuccessMessage('ユーザー登録が完了しました。ログインしてください。');
      setActiveTab('login');
    } catch (err: any) {
      console.error('Confirm sign up error:', err);
      setError(err.message || '確認コードの検証に失敗しました');
    }
  };

  return (
    <div className="login-page">
      <div className="login-container">
        <h1 className="app-title">食事管理アプリ</h1>

        <div className="tabs">
          <button
            className={`tab ${activeTab === 'login' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('login');
              setError('');
              setSuccessMessage('');
            }}
          >
            ログイン
          </button>
          <button
            className={`tab ${activeTab === 'signup' ? 'active' : ''}`}
            onClick={() => {
              setActiveTab('signup');
              setError('');
              setSuccessMessage('');
            }}
          >
            ユーザー登録
          </button>
        </div>

        {error && <div className="error-message">{error}</div>}
        {successMessage && <div className="success-message">{successMessage}</div>}

        {activeTab === 'login' ? (
          <>
            <LoginForm onSubmit={handleLogin} />

            <div className="social-login-divider">
              <span>または</span>
            </div>

            <button
              className="line-login-button"
              onClick={signInWithLineHostedUI}
              type="button"
            >
              <svg className="line-icon" viewBox="0 0 24 24" width="24" height="24">
                <path
                  fill="currentColor"
                  d="M19.365 9.863c.349 0 .63.285.63.631 0 .345-.281.63-.63.63H17.61v1.125h1.755c.349 0 .63.283.63.63 0 .344-.281.629-.63.629h-2.386c-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63h2.386c.349 0 .63.285.63.63 0 .349-.281.63-.63.63H17.61v1.125h1.755zm-3.855 3.016c0 .27-.174.51-.432.596-.064.021-.133.031-.199.031-.211 0-.391-.09-.51-.25l-2.443-3.317v2.94c0 .344-.279.629-.631.629-.346 0-.626-.285-.626-.629V8.108c0-.27.173-.51.43-.595.06-.023.136-.033.194-.033.195 0 .375.104.495.254l2.462 3.33V8.108c0-.345.282-.63.63-.63.345 0 .63.285.63.63v4.771zm-5.741 0c0 .344-.282.629-.631.629-.345 0-.627-.285-.627-.629V8.108c0-.345.282-.63.627-.63.349 0 .631.285.631.63v4.771zm-2.466.629H4.917c-.345 0-.63-.285-.63-.629V8.108c0-.345.285-.63.63-.63.348 0 .63.285.63.63v4.141h1.756c.348 0 .629.283.629.63 0 .344-.281.629-.629.629M24 10.314C24 4.943 18.615.572 12 .572S0 4.943 0 10.314c0 4.811 4.27 8.842 10.035 9.608.391.082.923.258 1.058.59.12.301.079.766.038 1.08l-.164 1.02c-.045.301-.24 1.186 1.049.645 1.291-.539 6.916-4.078 9.436-6.975C23.176 14.393 24 12.458 24 10.314"
                />
              </svg>
              LINE でログイン
            </button>
          </>
        ) : (
          <SignUpForm
            onSubmit={handleSignUp}
            onConfirm={handleConfirmSignUp}
          />
        )}
      </div>
    </div>
  );
};

export default LoginPage;
