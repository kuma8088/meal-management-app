/**
 * 食事記録一覧ページ
 */

import React, { useState, useEffect } from 'react';
import { useUnifiedAuth } from '../contexts/UnifiedAuthContext';
import { getMeals } from '../api/meals';
import MealsList from '../components/MealsList';
import type { Meal } from '../types/api';
import './MealsPage.css';

const MealsPage: React.FC = () => {
  const { user: _user } = useUnifiedAuth();
  const [meals, setMeals] = useState<Meal[]>([]);
  const [startDate, setStartDate] = useState<string>('');
  const [endDate, setEndDate] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string>('');
  const [hasSearched, setHasSearched] = useState(false);

  /**
   * 初期化: デフォルト日付を設定（過去7日間）
   */
  useEffect(() => {
    const today = new Date();
    const sevenDaysAgo = new Date(today);
    sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);

    setEndDate(today.toISOString().split('T')[0]);
    setStartDate(sevenDaysAgo.toISOString().split('T')[0]);
  }, []);

  /**
   * 食事記録を取得
   */
  const handleSearch = async () => {
    if (!startDate || !endDate) {
      setError('開始日と終了日を入力してください');
      return;
    }

    if (new Date(startDate) > new Date(endDate)) {
      setError('開始日は終了日より前である必要があります');
      return;
    }

    try {
      setLoading(true);
      setError('');
      setMeals([]);

      const fetchedMeals = await getMeals({
        start_date: startDate,
        end_date: endDate,
      });

      setMeals(fetchedMeals);
      setHasSearched(true);

      if (fetchedMeals.length === 0) {
        setError('該当する食事記録がありません');
      }
    } catch (err: any) {
      setError(err.error?.message || '食事記録の取得に失敗しました');
      setHasSearched(true);
    } finally {
      setLoading(false);
    }
  };

  /**
   * Enterキー押下時に検索
   */
  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch();
    }
  };

  /**
   * 再読み込み
   */
  const handleReload = () => {
    handleSearch();
  };

  return (
    <div className="meals-page">
      <div className="meals-container">
        <h1 className="page-title">食事記録</h1>

        <div className="filter-section">
          <div className="date-filter">
            <div className="form-group">
              <label htmlFor="start-date">開始日</label>
              <input
                type="date"
                id="start-date"
                value={startDate}
                onChange={(e) => setStartDate(e.target.value)}
                disabled={loading}
              />
            </div>

            <div className="form-group">
              <label htmlFor="end-date">終了日</label>
              <input
                type="date"
                id="end-date"
                value={endDate}
                onChange={(e) => setEndDate(e.target.value)}
                disabled={loading}
                onKeyPress={handleKeyPress}
              />
            </div>

            <button
              className="search-button"
              onClick={handleSearch}
              disabled={loading}
            >
              {loading ? '検索中...' : '検索'}
            </button>
          </div>

          <div className="quick-filters">
            <button
              className="quick-button"
              onClick={() => {
                const today = new Date();
                setEndDate(today.toISOString().split('T')[0]);
                setStartDate(today.toISOString().split('T')[0]);
              }}
              disabled={loading}
            >
              今日
            </button>
            <button
              className="quick-button"
              onClick={() => {
                const today = new Date();
                const sevenDaysAgo = new Date(today);
                sevenDaysAgo.setDate(sevenDaysAgo.getDate() - 7);
                setEndDate(today.toISOString().split('T')[0]);
                setStartDate(sevenDaysAgo.toISOString().split('T')[0]);
              }}
              disabled={loading}
            >
              過去7日間
            </button>
            <button
              className="quick-button"
              onClick={() => {
                const today = new Date();
                const thirtyDaysAgo = new Date(today);
                thirtyDaysAgo.setDate(thirtyDaysAgo.getDate() - 30);
                setEndDate(today.toISOString().split('T')[0]);
                setStartDate(thirtyDaysAgo.toISOString().split('T')[0]);
              }}
              disabled={loading}
            >
              過去30日間
            </button>
          </div>
        </div>

        {error && (
          <div className="error-section">
            <div className="error-message">{error}</div>
          </div>
        )}

        {hasSearched && meals.length > 0 && (
          <div className="results-info">
            <p>
              {startDate} 〜 {endDate} の食事記録（全{meals.length}件）
            </p>
            <button className="reload-button" onClick={handleReload} disabled={loading}>
              再読み込み
            </button>
          </div>
        )}

        <MealsList meals={meals} loading={loading} onDeleteSuccess={handleReload} />
      </div>
    </div>
  );
};

export default MealsPage;
