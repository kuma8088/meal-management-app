/**
 * ホームページ
 */

import React from 'react';
import { Link } from 'react-router-dom';
import { useAuth } from '../contexts/AuthContext';
import './HomePage.css';

const HomePage: React.FC = () => {
  const { user, signOut } = useAuth();

  return (
    <div className="home-page">
      <div className="home-container">
        <h1>食事管理アプリ</h1>

        <div className="user-info">
          <p>ようこそ、{user?.username}さん</p>
        </div>

        <nav className="navigation">
          <Link to="/profile" className="nav-link">
            プロフィール設定
          </Link>
          <button onClick={signOut} className="logout-button">
            ログアウト
          </button>
        </nav>

        <div className="content">
          <p>ここに食事記録や目標管理などの機能が表示されます。</p>
        </div>
      </div>
    </div>
  );
};

export default HomePage;
