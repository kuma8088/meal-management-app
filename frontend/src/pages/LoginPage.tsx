/**
 * ログインページ
 */

import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import LoginForm from '../components/LoginForm';
import SignUpForm from '../components/SignUpForm';
import './LoginPage.css';

type TabType = 'login' | 'signup';

const LoginPage: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('login');
  const navigate = useNavigate();
  const { signIn, signUp, confirmSignUp } = useAuth();
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
          <LoginForm onSubmit={handleLogin} />
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
