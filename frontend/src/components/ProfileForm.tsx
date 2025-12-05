/**
 * プロフィールフォームコンポーネント
 */

import React, { useState, useEffect } from 'react';
import type { UserProfile, CreateUserProfileRequest, Gender, ActivityLevel } from '../types/api';
import './ProfileForm.css';

interface ProfileFormProps {
  initialData?: UserProfile;
  onSubmit: (data: CreateUserProfileRequest) => Promise<void>;
  loading: boolean;
}

const ProfileForm: React.FC<ProfileFormProps> = ({ initialData, onSubmit, loading }) => {
  const [age, setAge] = useState(initialData?.age?.toString() || '');
  const [height, setHeight] = useState(initialData?.height?.toString() || '');
  const [weight, setWeight] = useState(initialData?.weight?.toString() || '');
  const [gender, setGender] = useState<Gender>(initialData?.gender || 'male');
  const [activityLevel, setActivityLevel] = useState<ActivityLevel>(
    initialData?.activity_level || 'moderate'
  );
  const [bmr, setBmr] = useState<number | null>(null);
  const [tdee, setTdee] = useState<number | null>(null);
  const [error, setError] = useState<string>('');

  /**
   * BMR（基礎代謝量）を計算
   * Harris-Benedict式を使用
   */
  const calculateBMR = (
    ageNum: number,
    heightNum: number,
    weightNum: number,
    genderVal: Gender
  ): number => {
    if (genderVal === 'male') {
      return 88.362 + 13.397 * weightNum + 4.799 * heightNum - 5.677 * ageNum;
    } else {
      return 447.593 + 9.247 * weightNum + 3.098 * heightNum - 4.33 * ageNum;
    }
  };

  /**
   * TDEE（総消費カロリー）を計算
   */
  const calculateTDEE = (bmrVal: number, activityVal: ActivityLevel): number => {
    const activityMultipliers: Record<ActivityLevel, number> = {
      sedentary: 1.2,
      light: 1.375,
      moderate: 1.55,
      active: 1.725,
      very_active: 1.9,
    };

    return bmrVal * activityMultipliers[activityVal];
  };

  /**
   * BMRとTDEEを再計算
   */
  useEffect(() => {
    const ageNum = parseInt(age);
    const heightNum = parseFloat(height);
    const weightNum = parseFloat(weight);

    if (ageNum > 0 && heightNum > 0 && weightNum > 0) {
      const calculatedBmr = calculateBMR(ageNum, heightNum, weightNum, gender);
      const calculatedTdee = calculateTDEE(calculatedBmr, activityLevel);

      setBmr(Math.round(calculatedBmr));
      setTdee(Math.round(calculatedTdee));
    } else {
      setBmr(null);
      setTdee(null);
    }
  }, [age, height, weight, gender, activityLevel]);

  /**
   * フォーム送信
   */
  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setError('');

    // バリデーション
    const ageNum = parseInt(age);
    const heightNum = parseFloat(height);
    const weightNum = parseFloat(weight);

    if (!ageNum || ageNum < 1 || ageNum > 150) {
      setError('年齢は1〜150の範囲で入力してください');
      return;
    }

    if (!heightNum || heightNum < 50 || heightNum > 300) {
      setError('身長は50〜300cmの範囲で入力してください');
      return;
    }

    if (!weightNum || weightNum < 20 || weightNum > 500) {
      setError('体重は20〜500kgの範囲で入力してください');
      return;
    }

    try {
      await onSubmit({
        age: ageNum,
        height: heightNum,
        weight: weightNum,
        gender,
        activity_level: activityLevel,
      });
    } catch (err: any) {
      setError(err.message || '保存に失敗しました');
    }
  };

  return (
    <form className="profile-form" onSubmit={handleSubmit}>
      {error && <div className="error-message">{error}</div>}

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="age">年齢</label>
          <input
            type="number"
            id="age"
            value={age}
            onChange={(e) => setAge(e.target.value)}
            placeholder="例: 30"
            min="1"
            max="150"
            required
            disabled={loading}
          />
          <span className="unit">歳</span>
        </div>

        <div className="form-group">
          <label htmlFor="gender">性別</label>
          <select
            id="gender"
            value={gender}
            onChange={(e) => setGender(e.target.value as Gender)}
            required
            disabled={loading}
          >
            <option value="male">男性</option>
            <option value="female">女性</option>
          </select>
        </div>
      </div>

      <div className="form-row">
        <div className="form-group">
          <label htmlFor="height">身長</label>
          <input
            type="number"
            id="height"
            value={height}
            onChange={(e) => setHeight(e.target.value)}
            placeholder="例: 170"
            min="50"
            max="300"
            step="0.1"
            required
            disabled={loading}
          />
          <span className="unit">cm</span>
        </div>

        <div className="form-group">
          <label htmlFor="weight">体重</label>
          <input
            type="number"
            id="weight"
            value={weight}
            onChange={(e) => setWeight(e.target.value)}
            placeholder="例: 65"
            min="20"
            max="500"
            step="0.1"
            required
            disabled={loading}
          />
          <span className="unit">kg</span>
        </div>
      </div>

      <div className="form-group full-width">
        <label htmlFor="activity_level">活動レベル</label>
        <select
          id="activity_level"
          value={activityLevel}
          onChange={(e) => setActivityLevel(e.target.value as ActivityLevel)}
          required
          disabled={loading}
        >
          <option value="sedentary">座りがち（ほとんど運動しない）</option>
          <option value="light">軽い活動（週1-3日の軽い運動）</option>
          <option value="moderate">適度な活動（週3-5日の中程度の運動）</option>
          <option value="active">活発（週6-7日の激しい運動）</option>
          <option value="very_active">非常に活発（1日2回の激しい運動）</option>
        </select>
      </div>

      {bmr !== null && tdee !== null && (
        <div className="metabolism-display">
          <h3>代謝情報</h3>
          <div className="metabolism-stats">
            <div className="stat-card">
              <div className="stat-label">基礎代謝量（BMR）</div>
              <div className="stat-value">{bmr} kcal/日</div>
              <div className="stat-description">
                何もしなくても消費されるカロリー
              </div>
            </div>
            <div className="stat-card">
              <div className="stat-label">総消費カロリー（TDEE）</div>
              <div className="stat-value">{tdee} kcal/日</div>
              <div className="stat-description">
                活動を含めた1日の総消費カロリー
              </div>
            </div>
          </div>
        </div>
      )}

      <button type="submit" className="submit-button" disabled={loading}>
        {loading ? '保存中...' : initialData ? 'プロフィールを更新' : 'プロフィールを作成'}
      </button>
    </form>
  );
};

export default ProfileForm;
