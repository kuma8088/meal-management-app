/**
 * ログインフォームコンポーネント
 */

import React, { useState } from 'react';
import './LoginForm.css';

interface LoginFormProps {
  onSubmit: (username: string, password: string) => Promise<void>;
}

const LoginForm: React.FC<LoginFormProps> = ({ onSubmit }) => {
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [loading, setLoading] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();

    if (!username || !password) {
      return;
    }

    setLoading(true);
    try {
      await onSubmit(username, password);
    } finally {
      setLoading(false);
    }
  };

  return (
    <form className="login-form" onSubmit={handleSubmit}>
      <div className="form-group">
        <label htmlFor="username">ユーザー名</label>
        <input
          type="text"
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          placeholder="ユーザー名を入力"
          required
          disabled={loading}
        />
      </div>

      <div className="form-group">
        <label htmlFor="password">パスワード</label>
        <input
          type="password"
          id="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="パスワードを入力"
          required
          disabled={loading}
        />
      </div>

      <button type="submit" className="submit-button" disabled={loading}>
        {loading ? 'ログイン中...' : 'ログイン'}
      </button>
    </form>
  );
};

export default LoginForm;
