/**
 * 1日の総評ページ
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getUserProfile } from '../api/users';
import { getGoals } from '../api/goals';
import DailySummary from '../components/DailySummary';
import type { UserProfile, Goal } from '../types/api';
import './SummaryPage.css';

const SummaryPage: React.FC = () => {
  const { user, loading: authLoading } = useAuth();
  const [selectedDate, setSelectedDate] = useState<string>('');
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [goal, setGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');

  /**
   * 初期化
   */
  useEffect(() => {
    // 本日の日付を設定
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
  }, []);

  /**
   * プロフィールと目標を読み込み
   */
  useEffect(() => {
    const loadData = async () => {
      // AuthContextの初期化を待つ
      if (authLoading) {
        return;
      }

      if (!user) return;

      try {
        setLoading(true);
        setError('');

        // プロフィールを取得
        const profileData = await getUserProfile(user.userId);
        setProfile(profileData);

        // 目標を取得（最新のもの）
        try {
          const goalsData = await getGoals(user.userId);
          if (goalsData.length > 0) {
            setGoal(goalsData[0]);
          }
        } catch (err: any) {
          // 目標が存在しない場合は無視
          if (err.error?.code !== 'NOT_FOUND') {
            throw err;
          }
        }
      } catch (err: any) {
        setError(err.error?.message || 'データの読み込みに失敗しました');
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, authLoading]);

  /**
   * 日付を戻す
   */
  const handlePreviousDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() - 1);
    setSelectedDate(date.toISOString().split('T')[0]);
  };

  /**
   * 日付を進める
   */
  const handleNextDay = () => {
    const date = new Date(selectedDate);
    date.setDate(date.getDate() + 1);
    const today = new Date().toISOString().split('T')[0];
    if (date.toISOString().split('T')[0] <= today) {
      setSelectedDate(date.toISOString().split('T')[0]);
    }
  };

  /**
   * 本日に戻す
   */
  const handleToday = () => {
    const today = new Date().toISOString().split('T')[0];
    setSelectedDate(today);
  };

  if (loading) {
    return (
      <div className="summary-page">
        <div className="loading">読み込み中...</div>
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="summary-page">
        <div className="summary-container">
          <div className="error-message">{error}</div>
        </div>
      </div>
    );
  }

  const today = new Date().toISOString().split('T')[0];
  const isToday = selectedDate === today;

  return (
    <div className="summary-page">
      <div className="summary-container">
        <h1 className="page-title">本日の栄養総評</h1>

        <div className="date-selector">
          <button
            className="nav-button"
            onClick={handlePreviousDay}
            disabled={selectedDate === '2020-01-01'}
          >
            前日
          </button>

          <div className="date-display">
            <input
              type="date"
              value={selectedDate}
              onChange={(e) => {
                const selected = e.target.value;
                if (selected <= today) {
                  setSelectedDate(selected);
                }
              }}
              max={today}
            />
            {!isToday && (
              <button className="today-button" onClick={handleToday}>
                本日に戻す
              </button>
            )}
          </div>

          <button
            className="nav-button"
            onClick={handleNextDay}
            disabled={isToday}
          >
            翌日
          </button>
        </div>

        {profile && (
          <DailySummary
            date={selectedDate}
            userGoal={
              goal
                ? {
                    targetCalories: goal.target_calories,
                    targetProtein: goal.recommended_protein,
                    targetFat: goal.recommended_fat,
                    targetCarbs: goal.recommended_carbs,
                  }
                : undefined
            }
          />
        )}

        {!profile && (
          <div className="profile-missing">
            <p>プロフィールを設定してください。</p>
            <a href="/profile" className="link-button">
              プロフィール設定へ
            </a>
          </div>
        )}
      </div>
    </div>
  );
};

export default SummaryPage;
