/**
 * ユーザー登録フォームコンポーネント
 */

import React, { useState } from 'react';
import './SignUpForm.css';

interface SignUpFormProps {
  onSubmit: (username: string, email: string, password: string) => Promise<void>;
  onConfirm: (username: string, code: string) => Promise<void>;
}

const SignUpForm: React.FC<SignUpFormProps> = ({ onSubmit, onConfirm }) => {
  const [username, setUsername] = useState('');
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [confirmationCode, setConfirmationCode] = useState('');
  const [loading, setLoading] = useState(false);
  const [showConfirmation, setShowConfirmation] = useState(false);
  const [error, setError] = useState('');

  /**
   * ユーザー登録
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // バリデーション
    if (!username || !email || !password || !confirmPassword) {
      setError('すべての項目を入力してください');
      return;
    }

    if (password !== confirmPassword) {
      setError('パスワードが一致しません');
      return;
    }

    if (password.length < 8) {
      setError('パスワードは8文字以上で入力してください');
      return;
    }

    setLoading(true);
    try {
      await onSubmit(username, email, password);
      setShowConfirmation(true);
    } catch (err: any) {
      setError(err.message || 'ユーザー登録に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  /**
   * 確認コード送信
   */
  const handleConfirmSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    if (!confirmationCode) {
      setError('確認コードを入力してください');
      return;
    }

    setLoading(true);
    try {
      await onConfirm(username, confirmationCode);
      // 成功時は親コンポーネントでログインタブに切り替え
    } catch (err: any) {
      setError(err.message || '確認コードの検証に失敗しました');
    } finally {
      setLoading(false);
    }
  };

  if (showConfirmation) {
    return (
      <form className="signup-form" onSubmit={handleConfirmSubmit}>
        <div className="confirmation-message">
          確認コードがメールアドレス <strong>{email}</strong> に送信されました。
        </div>

        {error && <div className="error-message">{error}</div>}

        <div className="form-group">
          <label htmlFor="confirmationCode">確認コード</label>
          <input
            type="text"
            id="confirmationCode"
            value={confirmationCode}
            onChange={(e) => setConfirmationCode(e.target.value)}
            placeholder="確認コードを入力"
            required
            disabled={loading}
          />
        </div>

        <button type="submit" className="submit-button" disabled={loading}>
          {loading ? '確認中...' : '確認'}
        </button>

        <button
          type="button"
          className="back-button"
          onClick={() => setShowConfirmation(false)}
          disabled={loading}
        >
          戻る
        </button>
      </form>
    );
  }

  return (
    <form className="signup-form" onSubmit={handleSubmit}>
      {error && <div className="error-message">{error}</div>}

      <div className="form-group">
        <label htmlFor="signup-username">ユーザー名</label>
        <input
          type="text"
          id="signup-username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="ユーザー名を入力"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="email">メールアドレス</label>
        <input
          type="email"
          id="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="メールアドレスを入力"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="signup-password">パスワード</label>
        <input
          type="password"
          id="signup-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="パスワードを入力（8文字以上）"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="confirm-password">パスワード（確認）</label>
        <input
          type="password"
          id="confirm-password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          placeholder="パスワードを再入力"
          required
          disabled={loading}
        />
      </div>

      <button type="submit" className="submit-button" disabled={loading}>
        {loading ? '登録中...' : 'ユーザー登録'}
      </button>
    </form>
  );
};

export default SignUpForm;
