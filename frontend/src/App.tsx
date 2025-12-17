/**
 * メインアプリケーションコンポーネント
 *
 * 認証方式:
 * - 通常ブラウザ: Cognito 認証
 * - LINE Hosted UI: Cognito 経由の LINE ログイン
 * - LIFF 経由: LINE ID Token → /auth/liff-login → Cognito JWT
 *
 * すべての API 呼び出しは Cognito JWT で認証
 */

import React from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { UnifiedAuthProvider, useUnifiedAuth } from './contexts/UnifiedAuthContext';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import GoalPage from './pages/GoalPage';
import FoodSearchPage from './pages/FoodSearchPage';
import MealsPage from './pages/MealsPage';
import MealRegistrationPage from './pages/MealRegistrationPage';
import SummaryPage from './pages/SummaryPage';
import LIFFEntry from './pages/LIFFEntry';
import CallbackPage from './pages/CallbackPage';

/**
 * プライベートルート（認証必須）
 */
interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading, isLiffInitialized, isInLiff } = useUnifiedAuth();

  // LIFF 初期化中または認証チェック中は読み込み表示
  if (loading || !isLiffInitialized) {
    return <div className="loading-screen">Loading...</div>;
  }

  // LIFF 認証処理中の場合は読み込み表示（無限ループ防止）
  const liffAuthInProgress = sessionStorage.getItem('liffAuthInProgress') === 'true';
  if (liffAuthInProgress) {
    console.log('PrivateRoute: LIFF auth in progress, showing loading screen');
    return <div className="loading-screen">認証処理中...</div>;
  }

  if (!user) {
    // LIFF 環境の場合は /liff にリダイレクト（/login → /liff の二重リダイレクトを防ぐ）
    return <Navigate to={isInLiff ? '/liff' : '/login'} replace />;
  }

  return <>{children}</>;
};

/**
 * パブリックルート（未認証のみ）
 */
const PublicRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading, isLiffInitialized, isInLiff } = useUnifiedAuth();

  // LIFF 初期化中または認証チェック中は読み込み表示
  if (loading || !isLiffInitialized) {
    return <div className="loading-screen">Loading...</div>;
  }

  // LIFF 環境の場合は /liff にリダイレクト
  if (isInLiff && !user) {
    return <Navigate to="/liff" replace />;
  }

  return !user ? <>{children}</> : <Navigate to="/" replace />;
};

/**
 * アプリケーションルーター
 */
const AppRoutes: React.FC = () => {
  return (
    <Routes>
      {/* パブリックルート */}
      <Route
        path="/login"
        element={
          <PublicRoute>
            <LoginPage />
          </PublicRoute>
        }
      />

      {/* LIFF エントリーポイント */}
      <Route path="/liff" element={<LIFFEntry />} />

      {/* OAuth コールバック */}
      <Route path="/callback" element={<CallbackPage />} />

      {/* プライベートルート */}
      <Route
        path="/"
        element={
          <PrivateRoute>
            <HomePage />
          </PrivateRoute>
        }
      />

      <Route
        path="/profile"
        element={
          <PrivateRoute>
            <ProfilePage />
          </PrivateRoute>
        }
      />

      <Route
        path="/goals"
        element={
          <PrivateRoute>
            <GoalPage />
          </PrivateRoute>
        }
      />

      <Route
        path="/foods"
        element={
          <PrivateRoute>
            <FoodSearchPage />
          </PrivateRoute>
        }
      />

      <Route
        path="/meals"
        element={
          <PrivateRoute>
            <MealsPage />
          </PrivateRoute>
        }
      />

      <Route
        path="/meals/new"
        element={
          <PrivateRoute>
            <MealRegistrationPage />
          </PrivateRoute>
        }
      />

      <Route
        path="/summary"
        element={
          <PrivateRoute>
            <SummaryPage />
          </PrivateRoute>
        }
      />

      {/* 未定義のルートはホームにリダイレクト */}
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
};

/**
 * アプリケーション
 *
 * UnifiedAuthProvider で Cognito + LIFF 認証を統合管理
 */
const App: React.FC = () => {
  return (
    <UnifiedAuthProvider>
      <Router>
        <AppRoutes />
      </Router>
    </UnifiedAuthProvider>
  );
};

export default App;
