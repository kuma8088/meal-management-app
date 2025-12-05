/**
 * 目標設定フォームコンポーネント
 */

import React, { useState } from 'react';
import type { GoalType, CreateGoalRequest, Goal } from '../types/api';
import './GoalForm.css';

interface GoalFormProps {
  currentWeight: number;
  onSubmit: (data: CreateGoalRequest) => Promise<void>;
  createdGoal?: Goal | null;
}

const GoalForm: React.FC<GoalFormProps> = ({
  currentWeight,
  onSubmit,
  createdGoal,
}) => {
  const [goalType, setGoalType] = useState<GoalType>('maintain');
  const [targetWeight, setTargetWeight] = useState<string>('');
  const [targetDate, setTargetDate] = useState<string>('');
  const [error, setError] = useState<string>('');
  const [warning, setWarning] = useState<string>('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  /**
   * 目標の妥当性をチェック
   */
  const validateGoal = (
    type: GoalType,
    target: number,
    current: number,
    date: string
  ): { valid: boolean; warning?: string } => {
    const weightDiff = target - current;
    const today = new Date();
    const targetDateObj = new Date(date);
    const daysDiff = Math.ceil(
      (targetDateObj.getTime() - today.getTime()) / (1000 * 60 * 60 * 24)
    );

    // 過去の日付チェック
    if (daysDiff < 0) {
      return { valid: false, warning: '目標日は今日以降の日付を選択してください' };
    }

    // 最低1日必要
    if (daysDiff < 1) {
      return { valid: false, warning: '目標日は少なくとも明日以降を選択してください' };
    }

    // 増量目標のチェック
    if (type === 'gain' && weightDiff <= 0) {
      return { valid: false, warning: '増量目標の場合、目標体重は現在の体重より大きくする必要があります' };
    }

    // 減量目標のチェック
    if (type === 'lose' && weightDiff >= 0) {
      return { valid: false, warning: '減量目標の場合、目標体重は現在の体重より小さくする必要があります' };
    }

    // 維持目標のチェック
    if (type === 'maintain' && Math.abs(weightDiff) > 2) {
      return {
        valid: false,
        warning: '維持目標の場合、目標体重は現在の体重の±2kg以内にする必要があります',
      };
    }

    // 急激な減量のチェック (1週間で1kg以上)
    const weeklyWeightChange = Math.abs(weightDiff) / (daysDiff / 7);
    if (type === 'lose' && weeklyWeightChange > 1) {
      return {
        valid: true,
        warning: '警告: 1週間で1kg以上の減量は健康リスクがあります。より長い期間での目標設定を推奨します。',
      };
    }

    // 急激な増量のチェック (1週間で0.5kg以上)
    if (type === 'gain' && weeklyWeightChange > 0.5) {
      return {
        valid: true,
        warning: '警告: 1週間で0.5kg以上の増量は過剰です。より長い期間での目標設定を推奨します。',
      };
    }

    return { valid: true };
  };

  /**
   * フォーム送信
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');
    setWarning('');

    const targetWeightNum = parseFloat(targetWeight);

    // 入力値の検証
    if (!targetWeightNum || targetWeightNum <= 0) {
      setError('目標体重を正しく入力してください');
      return;
    }

    if (targetWeightNum < 20 || targetWeightNum > 500) {
      setError('目標体重は20〜500kgの範囲で入力してください');
      return;
    }

    if (!targetDate) {
      setError('目標日を入力してください');
      return;
    }

    // 目標の妥当性チェック
    const validation = validateGoal(
      goalType,
      targetWeightNum,
      currentWeight,
      targetDate
    );

    if (!validation.valid) {
      setError(validation.warning || '目標の設定が不正です');
      return;
    }

    if (validation.warning) {
      setWarning(validation.warning);
    }

    // APIリクエスト
    try {
      setIsSubmitting(true);
      await onSubmit({
        goal_type: goalType,
        target_weight: targetWeightNum,
        target_date: targetDate,
      });
    } catch (err: any) {
      setError(err.error?.message || '目標の作成に失敗しました');
    } finally {
      setIsSubmitting(false);
    }
  };

  /**
   * 今日の日付（最小値）
   */
  const getMinDate = () => {
    const today = new Date();
    today.setDate(today.getDate() + 1); // 明日以降
    return today.toISOString().split('T')[0];
  };

  return (
    <div className="goal-form-container">
      <form onSubmit={handleSubmit} className="goal-form">
        {error && <div className="error-message">{error}</div>}
        {warning && <div className="warning-message">{warning}</div>}

        <div className="form-section">
          <h3>現在の体重</h3>
          <div className="current-weight">
            <span className="weight-value">{currentWeight}</span>
            <span className="weight-unit">kg</span>
          </div>
        </div>

        <div className="form-section">
          <div className="form-group full-width">
            <label htmlFor="goal_type">目標タイプ</label>
            <select
              id="goal_type"
              value={goalType}
              onChange={(e) => setGoalType(e.target.value as GoalType)}
              disabled={isSubmitting}
            >
              <option value="gain">増量</option>
              <option value="maintain">維持</option>
              <option value="lose">減量</option>
            </select>
          </div>

          <div className="form-row">
            <div className="form-group">
              <label htmlFor="target_weight">
                目標体重 <span className="required">*</span>
              </label>
              <input
                type="number"
                id="target_weight"
                value={targetWeight}
                onChange={(e) => setTargetWeight(e.target.value)}
                step="0.1"
                min="20"
                max="500"
                required
                disabled={isSubmitting}
              />
              <span className="unit">kg</span>
            </div>

            <div className="form-group">
              <label htmlFor="target_date">
                目標日 <span className="required">*</span>
              </label>
              <input
                type="date"
                id="target_date"
                value={targetDate}
                onChange={(e) => setTargetDate(e.target.value)}
                min={getMinDate()}
                required
                disabled={isSubmitting}
              />
            </div>
          </div>
        </div>

        <button
          type="submit"
          className="submit-button"
          disabled={isSubmitting}
        >
          {isSubmitting ? '作成中...' : '目標を作成'}
        </button>
      </form>

      {createdGoal && (
        <div className="goal-result">
          <h3>目標計算結果</h3>

          <div className="result-grid">
            <div className="result-card">
              <div className="result-label">目標カロリー</div>
              <div className="result-value">
                {createdGoal.target_calories.toLocaleString()}
                <span className="result-unit">kcal/日</span>
              </div>
            </div>

            <div className="result-card">
              <div className="result-label">推奨タンパク質</div>
              <div className="result-value">
                {createdGoal.recommended_protein.toFixed(1)}
                <span className="result-unit">g/日</span>
              </div>
            </div>

            <div className="result-card">
              <div className="result-label">推奨脂質</div>
              <div className="result-value">
                {createdGoal.recommended_fat.toFixed(1)}
                <span className="result-unit">g/日</span>
              </div>
            </div>

            <div className="result-card">
              <div className="result-label">推奨炭水化物</div>
              <div className="result-value">
                {createdGoal.recommended_carbs.toFixed(1)}
                <span className="result-unit">g/日</span>
              </div>
            </div>

            {createdGoal.recommended_exercise_minutes && (
              <div className="result-card highlight">
                <div className="result-label">推奨運動時間</div>
                <div className="result-value">
                  {createdGoal.recommended_exercise_minutes}
                  <span className="result-unit">分/日</span>
                </div>
                <div className="result-description">
                  有酸素運動（ウォーキング、ジョギングなど）
                </div>
              </div>
            )}
          </div>

          <div className="goal-summary">
            <p>
              <strong>{goalType === 'gain' ? '増量' : goalType === 'lose' ? '減量' : '維持'}</strong>
              目標: {currentWeight}kg → {createdGoal.target_weight}kg
            </p>
            <p>
              期限: {new Date(createdGoal.target_date).toLocaleDateString('ja-JP')}
            </p>
          </div>
        </div>
      )}
    </div>
  );
};

export default GoalForm;
