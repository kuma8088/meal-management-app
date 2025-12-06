/**
 * 目標設定ページ
 */

import React, { useState, useEffect } from 'react';
import { useAuth } from '../contexts/AuthContext';
import { getUserProfile } from '../api/users';
import { createGoal, getGoals } from '../api/goals';
import GoalForm from '../components/GoalForm';
import type { UserProfile, Goal, CreateGoalRequest } from '../types/api';
import './GoalPage.css';

const GoalPage: React.FC = () => {
  const { user, loading: authLoading } = useAuth();
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [goals, setGoals] = useState<Goal[]>([]);
  const [createdGoal, setCreatedGoal] = useState<Goal | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string>('');
  const [successMessage, setSuccessMessage] = useState<string>('');

  /**
   * プロフィールと既存の目標を読み込み
   */
  useEffect(() => {
    const loadData = async () => {
      // AuthContextの初期化を待つ
      if (authLoading) {
        return;
      }

      if (!user) {
        setLoading(false);
        return;
      }

      try {
        setLoading(true);
        setError('');

        // プロフィールを取得
        const profileData = await getUserProfile(user.userId);
        setProfile(profileData);

        // 既存の目標を取得
        try {
          const goalsData = await getGoals(user.userId);
          setGoals(goalsData);
        } catch (err: any) {
          // 目標が存在しない場合はエラーを無視
          if (err.error?.code !== 'NOT_FOUND') {
            throw err;
          }
        }
      } catch (err: any) {
        if (err.error?.code === 'NOT_FOUND') {
          setError(
            'プロフィールが見つかりません。先にプロフィールを作成してください。'
          );
        } else {
          setError(err.error?.message || 'データの読み込みに失敗しました');
        }
      } finally {
        setLoading(false);
      }
    };

    loadData();
  }, [user, authLoading]);

  /**
   * 目標作成
   */
  const handleCreateGoal = async (data: CreateGoalRequest) => {
    if (!user) return;

    try {
      setError('');
      setSuccessMessage('');
      setCreatedGoal(null);

      const newGoal = await createGoal(data);
      setCreatedGoal(newGoal);
      setGoals([newGoal, ...goals]);
      setSuccessMessage('目標を作成しました');

      // スクロールして結果を表示
      setTimeout(() => {
        const resultElement = document.querySelector('.goal-result');
        if (resultElement) {
          resultElement.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
        }
      }, 100);
    } catch (err: any) {
      setError(err.error?.message || '目標の作成に失敗しました');
      throw err; // GoalFormでもエラーを処理できるように
    }
  };

  if (loading) {
    return (
      <div className="goal-page">
        <div className="loading">読み込み中...</div>
      </div>
    );
  }

  if (error && !profile) {
    return (
      <div className="goal-page">
        <div className="goal-container">
          <div className="error-message">{error}</div>
          <div style={{ textAlign: 'center', marginTop: '20px' }}>
            <a href="/profile" className="link-button">
              プロフィール設定へ
            </a>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="goal-page">
      <div className="goal-container">
        <h1 className="page-title">目標設定</h1>

        {successMessage && (
          <div className="success-message">{successMessage}</div>
        )}
        {error && <div className="error-message">{error}</div>}

        {profile && (
          <>
            <div className="goal-intro">
              <p>
                体重目標を設定すると、目標達成に必要な1日のカロリーと栄養素の推奨量が計算されます。
              </p>
            </div>

            <GoalForm
              currentWeight={profile.weight}
              onSubmit={handleCreateGoal}
              createdGoal={createdGoal}
            />

            {goals.length > 0 && !createdGoal && (
              <div className="previous-goals">
                <h2>過去の目標</h2>
                <div className="goals-list">
                  {goals.map((goal) => (
                    <div key={goal.goal_id} className="goal-item">
                      <div className="goal-header">
                        <span className="goal-type">
                          {goal.goal_type === 'gain'
                            ? '増量'
                            : goal.goal_type === 'lose'
                            ? '減量'
                            : '維持'}
                        </span>
                        <span className="goal-date">
                          作成日:{' '}
                          {new Date(goal.created_at).toLocaleDateString('ja-JP')}
                        </span>
                      </div>
                      <div className="goal-details">
                        <p>
                          目標体重: {goal.target_weight}kg（期限:{' '}
                          {new Date(goal.target_date).toLocaleDateString('ja-JP')}）
                        </p>
                        <p>目標カロリー: {goal.target_calories.toLocaleString()}kcal/日</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            )}
          </>
        )}
      </div>
    </div>
  );
};

export default GoalPage;
