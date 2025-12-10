/**
 * メインアプリケーションコンポーネント
 *
 * 認証方式:
 * - 通常ブラウザ: Cognito 認証
 * - LIFF 経由: LINE 認証 (LINE User ID で API 呼び出し)
 */

import React, { useEffect } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import { LiffProvider, useLiff } from './contexts/LiffContext';
import { AuthProvider, useAuth } from './contexts/AuthContext';
import HomePage from './pages/HomePage';
import LoginPage from './pages/LoginPage';
import ProfilePage from './pages/ProfilePage';
import GoalPage from './pages/GoalPage';
import FoodSearchPage from './pages/FoodSearchPage';
import MealsPage from './pages/MealsPage';
import MealRegistrationPage from './pages/MealRegistrationPage';
import SummaryPage from './pages/SummaryPage';

/**
 * プライベートルート（認証必須）
 */
interface PrivateRouteProps {
  children: React.ReactNode;
}

const PrivateRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
  }

  return user ? <>{children}</> : <Navigate to="/login" replace />;
};

/**
 * パブリックルート（未認証のみ）
 */
const PublicRoute: React.FC<PrivateRouteProps> = ({ children }) => {
  const { user, loading } = useAuth();

  if (loading) {
    return <div>Loading...</div>;
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
 * LIFF 自動ログインコンポーネント
 *
 * LIFF 経由でアクセスした場合、LINE プロフィールを取得して自動ログイン
 */
const LiffAutoLogin: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const { isLiffInitialized, isInLiff, isLoggedIn, profile } = useLiff();
  const { user, signInWithLine } = useAuth();
  const [isSigningIn, setIsSigningIn] = React.useState(false);

  useEffect(() => {
    // LIFF 初期化完了 + LIFF 環境 + LINE ログイン済み + プロフィール取得済み + 未ログイン + 未ログイン中
    if (isLiffInitialized && isInLiff && isLoggedIn && profile && !user && !isSigningIn) {
      const performSignIn = async () => {
        setIsSigningIn(true);
        try {
          await signInWithLine(profile.userId, profile.displayName);
        } catch (error) {
          console.error('LIFF auto-login failed:', error);
        } finally {
          setIsSigningIn(false);
        }
      };
      performSignIn();
    }
  }, [isLiffInitialized, isInLiff, isLoggedIn, profile, user, signInWithLine, isSigningIn]);

  // LIFF 初期化中またはログイン中は読み込み表示
  if (!isLiffInitialized || isSigningIn) {
    return <div>Loading...</div>;
  }

  return <>{children}</>;
};

/**
 * アプリケーション
 */
const App: React.FC = () => {
  return (
    <LiffProvider>
      <AuthProvider>
        <Router>
          <LiffAutoLogin>
            <AppRoutes />
          </LiffAutoLogin>
        </Router>
      </AuthProvider>
    </LiffProvider>
  );
};

export default App;
